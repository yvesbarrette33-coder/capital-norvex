"""
Phase A — TEST CONCEPT 2026-05-07
Lance Norvex Final-équivalent en local (sans timeout Netlify) sur Henri Petit EN.

But : prouver que Claude Opus 4.6 peut produire un Brief Comité Crédit niveau
banque sur un Refi avec docs PDF, sans Hugo.

⚠️ NE PATCH PAS Firestore. Écrit juste un fichier HTML local pour Yves.
⚠️ N'envoie PAS d'email. Yves regarde le HTML avant.

Usage :
    python -m agents.refi.test_henri_petit_brief
"""
from __future__ import annotations

import os
import json
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/.capitalnorvex/.env'))

import anthropic
import firebase_admin
from firebase_admin import credentials, storage as fb_storage

from agents.shared.firestore_client import db

DOSSIER_ID = "CNV-2026-59109"  # Dossier EN, 8 docs
OUTPUT_DIR = Path("/tmp/norvex-test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if not firebase_admin._apps:
    sa_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    bucket_name = os.environ.get('FIREBASE_STORAGE_BUCKET', 'capital-norvex-uploads')
    firebase_admin.initialize_app(credentials.Certificate(sa_path), {'storageBucket': bucket_name})


def main():
    print(f"\n🔍 Phase A — Test concept Norvex Final sur {DOSSIER_ID}\n")

    fs = db()
    dossier = fs.collection('dossiers').document(DOSSIER_ID).get().to_dict()
    if not dossier:
        print(f"❌ {DOSSIER_ID} introuvable")
        return

    print(f"  Borrower : {dossier.get('prenom')} {dossier.get('nom')}")
    print(f"  Type     : {dossier.get('type')}")
    print(f"  Lang     : {dossier.get('lang')}")
    print(f"  Score initial : {dossier.get('score')}")
    print(f"  Montant demandé : {dossier.get('montant')} $")
    print(f"  Adresse  : {dossier.get('adresse')}")

    # Liste les docs Storage
    bucket = fb_storage.bucket()
    blobs = sorted(bucket.list_blobs(prefix=f'uploads/{DOSSIER_ID}/'), key=lambda b: b.updated)
    print(f"\n📦 {len(blobs)} documents Storage :")
    for b in blobs:
        size_mb = b.size / 1024 / 1024
        print(f"   - {b.name.split('/')[-1][:75]:75s} ({size_mb:.1f} MB)")

    # Télécharge les PDFs (pour multimodal Claude)
    print(f"\n⬇️  Téléchargement des PDFs (max 10 MB chacun pour API Claude)…")
    pdf_blocks = []
    for b in blobs:
        size_mb = (b.size or 0) / 1024 / 1024
        if size_mb > 30:  # Claude limit ~32 MB par doc
            print(f"   ⚠️  Skip {b.name.split('/')[-1]} (>30 MB)")
            continue
        data = b.download_as_bytes()
        import base64
        b64 = base64.standard_b64encode(data).decode('ascii')
        pdf_blocks.append({
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": b64},
            "title": b.name.split('/')[-1][:90],
        })
        print(f"   ✓ {b.name.split('/')[-1][:60]:60s} {size_mb:.1f} MB")

    # Build le prompt (calque sur norvex-final-analyze.mjs)
    dossier_clean = {
        "id": DOSSIER_ID,
        "borrowerName": f"{dossier.get('prenom','')} {dossier.get('nom','')}".strip(),
        "loanType": dossier.get('type'),
        "projectAddress": dossier.get('adresse'),
        "phase": dossier.get('stage'),
        "scoreInitial": dossier.get('score'),
        "scoreInitialDecision": dossier.get('decision'),
        "loanAmountRequested": dossier.get('montant'),
        "language": dossier.get('lang', 'fr'),
        "termeProspoe": dossier.get('terme'),
        "tauxPropose": dossier.get('taux'),
        "deboursesPrévus": dossier.get('debourses'),
        "sortie": dossier.get('sortie'),
    }

    system_prompt = """Tu es Directeur Crédit Senior chez Capital Norvex Inc. (prêt privé institutionnel alternatif au Québec/Ontario, tickets 2,5-100 M$, taux 10-12%). Tu produis un MEMO COMITÉ CRÉDIT de qualité grande banque (BMO/RBC/BNC/Desjardins) ADAPTÉ à la réalité prêt privé alternatif.

Ce memo est le BRIEF PRÉ-RDV TEAMS d'Yves Barrette (président). Il doit lui donner :
- La note finale et le verdict
- Le taux RECOMMANDÉ à proposer (range 10-12%)
- Le montant FINAL recommandé
- Les conditions précises à exiger
- Les talking points pour la conversation Teams
- ⚠️ CRITIQUE : la liste des DOCUMENTS PRIMORDIAUX MANQUANTS (sans exagérer — focus sur ce qui est VRAIMENT essentiel pour décider)

CRITÈRES PRÊT PRIVÉ NORVEX :
- Taux 10-12% selon risque
- LTV : porte d'entrée minimum 75%, standard 75-85%, peut aller à 100% avec collatéraux additionnels
- Équité promoteur ≥15% (résiduelle après stress)
- Sortie viable < 18 mois
- Protection capital first-mortgage privilégiée

DÉCISION : "GO" / "GO_CONDITIONNEL" / "NO_GO"
POSTURE : "favorable" / "neutre" / "serrée"

DOCUMENTS PRIMORDIAUX (ce qu'un banquier exige TOUJOURS pour une décision finale en Refi commercial) :
- États financiers borrower (3 ans + interim)
- Évaluation immobilière indépendante (AACI ≤12 mois)
- Rent roll certifié + leases (si revenus locatifs)
- Preuve d'équité (relevés bancaires, certificat avocat)
- KYC/identité personne morale + UBO
- Quittance hypothèque actuelle ou solde + statement
- Assurance titres + assurance hypothécaire en place
- Documents fiscaux (Avis cotisation 2 dernières années)

Pour ce dossier, tu DOIS identifier ce qui est PRÉSENT vs MANQUANT parmi ces critiques.

OUTPUT : JSON STRICT (aucun texte avant/après, aucun ```)
{
  "finalScore": <0-100>,
  "finalScoreJustification": "<2-3 phrases>",
  "finalDecision": "GO|GO_CONDITIONNEL|NO_GO",
  "finalDecisionJustification": "<1-2 phrases>",
  "finalRate": <nombre, ex 11.25>,
  "finalRateRange": {"low": <n>, "high": <n>},
  "finalRateJustification": "<court>",
  "finalAmount": <nombre>,
  "finalAmountJustification": "<court>",
  "loanTermMonths": <nombre>,
  "ltvCalcule": <n|null>,
  "negotiationPosture": "favorable|neutre|serrée",
  "executiveSummary": "<5-7 phrases ton institutionnel>",
  "borrowerProfile": "<2-3 phrases>",
  "projectAnalysis": "<3-4 phrases>",
  "financialAnalysis": "<3-5 phrases>",
  "riskAssessment": {
    "strengths": ["<f1>","<f2>","<f3>"],
    "concerns": ["<c1>","<c2>"],
    "redFlags": ["<rf1>"]
  },
  "stressTestSummary": "<1-2 phrases>",
  "documentsPresents": ["<doc1>","<doc2>","<doc3>"],
  "documentsPrimordiauxManquants": [
    {"document":"<nom doc>", "criticite":"OBLIGATOIRE|UTILE", "raison":"<pourquoi>"},
    ...
  ],
  "finalConditions": ["<c1>","<c2>","<c3>"],
  "rdvTalkingPoints": [
    {"topic":"<t1>","objective":"<o1>","fallback":"<f1>"},
    {"topic":"<t2>","objective":"<o2>","fallback":"<f2>"}
  ],
  "memorandumComite": "<paragraphe final 4-6 phrases ton institutionnel>"
}"""

    user_content = [
        {"type": "text", "text": f"DOSSIER (Score initial)\n{json.dumps(dossier_clean, indent=2, ensure_ascii=False)}\n\nVoici les {len(pdf_blocks)} documents reçus du borrower. Analyse-les comme Directeur Crédit Senior et produis le MEMO COMITÉ CRÉDIT en JSON strict."},
    ] + pdf_blocks

    print(f"\n🤖 Appel Claude Opus 4.6 multimodal — {len(pdf_blocks)} PDFs… (peut prendre 30-90s)")
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    raw = response.content[0].text
    # Parse JSON
    s = raw.strip()
    s = s.replace("```json", "").replace("```", "").strip()
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        s = s[start:end+1]
    try:
        analysis = json.loads(s)
    except Exception as e:
        print(f"❌ Parse JSON échoué : {e}")
        (OUTPUT_DIR / "raw_output.txt").write_text(raw, encoding="utf-8")
        print(f"   Raw output : {OUTPUT_DIR / 'raw_output.txt'}")
        return

    # Sauver le JSON brut
    (OUTPUT_DIR / "analysis.json").write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Analyse complète :")
    print(f"   Score final  : {analysis.get('finalScore')}")
    print(f"   Décision     : {analysis.get('finalDecision')}")
    print(f"   Taux         : {analysis.get('finalRate')}%")
    print(f"   Montant      : {analysis.get('finalAmount')} $")
    print(f"   Posture      : {analysis.get('negotiationPosture')}")
    print(f"   LTV calc     : {analysis.get('ltvCalcule')}")
    docs_manquants = analysis.get('documentsPrimordiauxManquants', [])
    print(f"\n📄 Docs primordiaux MANQUANTS ({len(docs_manquants)}) :")
    for dm in docs_manquants:
        if isinstance(dm, dict):
            print(f"   [{dm.get('criticite','?')}] {dm.get('document','?')}")
            print(f"      → {dm.get('raison','')[:90]}")
        else:
            print(f"   - {dm}")

    # Sauve un mini HTML preview
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Test Henri Petit Brief</title>
<style>body{{font-family:Georgia,serif;max-width:760px;margin:40px auto;padding:0 20px;color:#0A0A0A}}
h1,h2{{font-family:Georgia,serif}} h1{{color:#9A8554;border-bottom:2px solid #C8B070;padding-bottom:8px}}
.kpi{{display:inline-block;margin:8px 16px 8px 0;padding:12px 18px;background:#FBF7EB;border-left:3px solid #C8B070}}
.kpi-val{{font-size:1.5em;font-weight:700;color:#0A0A0A}} .kpi-lbl{{font-size:.8em;color:#666;text-transform:uppercase;letter-spacing:1px}}
.go{{color:#2E7D5C}} .gocond{{color:#C8923A}} .nogo{{color:#A53A2C}}
ul li{{margin:6px 0;line-height:1.55}}
.doc-manquant{{background:#FFF6E5;padding:10px 14px;border-left:3px solid #C8923A;margin:8px 0}}
.doc-obligatoire{{background:#FCE8E5;border-left-color:#A53A2C}}
table{{width:100%;border-collapse:collapse;margin:12px 0}} td{{padding:8px 12px;border-bottom:1px solid #E8E0CC}}
</style></head><body>
<h1>📋 BRIEF COMITÉ CRÉDIT — Henri Petit (CNV-2026-59109)</h1>
<p style="color:#666"><em>Refi commercial 27,5 M$ · Alliston, Ontario · Test Phase A 2026-05-07</em></p>

<div class="kpi"><div class="kpi-val">{analysis.get('finalScore','—')}/100</div><div class="kpi-lbl">Score final</div></div>
<div class="kpi"><div class="kpi-val {analysis.get('finalDecision','').lower().replace('_','')}">{analysis.get('finalDecision','—')}</div><div class="kpi-lbl">Décision</div></div>
<div class="kpi"><div class="kpi-val">{analysis.get('finalRate','—')}%</div><div class="kpi-lbl">Taux</div></div>
<div class="kpi"><div class="kpi-val">{(analysis.get('finalAmount') or 0)/1e6:.1f} M$</div><div class="kpi-lbl">Montant</div></div>
<div class="kpi"><div class="kpi-val">{analysis.get('ltvCalcule','—') or '—'}{'%' if analysis.get('ltvCalcule') else ''}</div><div class="kpi-lbl">LTV</div></div>

<h2>Sommaire exécutif</h2>
<p>{analysis.get('executiveSummary','—')}</p>

<h2>Profil borrower</h2>
<p>{analysis.get('borrowerProfile','—')}</p>

<h2>Analyse projet</h2>
<p>{analysis.get('projectAnalysis','—')}</p>

<h2>Analyse financière</h2>
<p>{analysis.get('financialAnalysis','—')}</p>

<h2>Risques</h2>
<p><strong>Forces :</strong></p>
<ul>{''.join(f'<li>{s}</li>' for s in analysis.get('riskAssessment',{{}}).get('strengths',[]))}</ul>
<p><strong>Préoccupations :</strong></p>
<ul>{''.join(f'<li>{c}</li>' for c in analysis.get('riskAssessment',{{}}).get('concerns',[]))}</ul>
<p><strong>Red flags :</strong></p>
<ul>{''.join(f'<li style="color:#A53A2C;font-weight:600">{rf}</li>' for rf in analysis.get('riskAssessment',{{}}).get('redFlags',[]) if rf and rf.lower() != 'aucun')}</ul>

<h2>Stress test</h2>
<p>{analysis.get('stressTestSummary','—')}</p>

<h2>📄 Documents PRIMORDIAUX manquants</h2>
{''.join(f'<div class="doc-manquant {("doc-obligatoire" if (dm.get("criticite") if isinstance(dm,dict) else "").upper()=="OBLIGATOIRE" else "")}"><strong>[{(dm.get("criticite") if isinstance(dm,dict) else "—")}]</strong> {(dm.get("document") if isinstance(dm,dict) else dm)}<br><em style="font-size:.9em;color:#666">{(dm.get("raison") if isinstance(dm,dict) else "")}</em></div>' for dm in docs_manquants) or '<p>Aucun document primordial manquant.</p>'}

<h2>✅ Documents présents</h2>
<ul>{''.join(f'<li>{d}</li>' for d in analysis.get('documentsPresents',[]))}</ul>

<h2>Conditions à exiger</h2>
<ol>{''.join(f'<li>{c}</li>' for c in analysis.get('finalConditions',[]))}</ol>

<h2>Talking points RDV Teams</h2>
{''.join(f'<div style="margin:14px 0;padding:14px;background:#FBF7EB;border-left:3px solid #C8B070"><strong>{tp.get("topic","")}</strong><br><em>Objectif :</em> {tp.get("objective","")}<br><em>Repli :</em> {tp.get("fallback","")}</div>' for tp in analysis.get('rdvTalkingPoints',[]))}

<h2>Memorandum Comité</h2>
<p style="background:#FBF7EB;padding:18px;border-left:3px solid #C8B070;font-style:italic;line-height:1.7">{analysis.get('memorandumComite','—')}</p>

<hr><p style="font-size:.8em;color:#999"><em>Test Phase A — généré localement, NON envoyé. Si OK, on automatise.</em></p>
</body></html>"""

    html_path = OUTPUT_DIR / "henri_petit_brief.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"\n📄 Brief HTML écrit : {html_path}")
    print(f"   Ouvre avec : open {html_path}")


if __name__ == "__main__":
    main()
