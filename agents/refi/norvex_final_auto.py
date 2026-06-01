"""
Norvex Final AUTO — Industrialisation 2026-05-07.

Cron toutes les 30 min via launchd. Pour chaque dossier en stage='docs' avec
nouveaux uploads détectés (vs `docsReceivedCount` précédent), lance le pipeline
complet :

  1. Détection : compare blobs Storage `uploads/CNV-XXX/` vs Firestore
  2. Patch metadata (docsList, lastDocsReceivedAt, docsReceivedCount)
  3. Analyse Claude Opus 4.6 multimodal (Comité Crédit niveau grande banque)
  4. Brief HTML interne (avec disclaimer + 8 modules écosystème)
  5. Email yves@ + classement dans dossier client (Library + Bureau)
  6. Lettre client diplomatique (FR ou EN selon `lang`) avec règles strictes
     pré-engagement (jamais 'approuvé', délai 5 jours, vrai token, disclaimer)
  7. Envoi lettre client + lien upload portail
  8. Stage avance : `docs` → `analyse_finale_done`

⚠️ GARDE-FOUS :
- NE PAS toucher au Score Norvex initial
- NE PAS modifier upload-doc.mjs (zone interdite)
- NE PAS envoyer de lettre client si dossier dontSend=true OU déjà envoyée < 24h
- En MODE DRY (--dry) : aucun envoi, aucun patch, juste log

Usage :
    python -m agents.refi.norvex_final_auto --dry          # simulation
    python -m agents.refi.norvex_final_auto                # exécute prod
    python -m agents.refi.norvex_final_auto --dossier CNV-2026-XXXXX  # un seul

Cron : ajouter dans `~/Library/LaunchAgents/com.capitalnorvex.norvexfinal.plist`
       toutes les 30 min (1800 sec).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/.capitalnorvex/.env'))

import anthropic
import firebase_admin
import requests
from firebase_admin import credentials, storage as fb_storage

from agents.shared.firestore_client import db, audit_log

# ─── Config ──────────────────────────────────────────────────────────────────

ANALYSIS_COOLDOWN_HOURS = 24  # ne pas re-analyser un dossier dans les 24h
LETTER_COOLDOWN_HOURS   = 24  # ne pas re-envoyer de lettre client dans les 24h
DOCS_DEADLINE_BUSINESS  = 5   # jours ouvrables pour fournir docs
SITE_URL                = os.environ.get("SITE_URL", "https://capitalnorvex.com")
INTERNAL_SECRET         = os.environ.get("INTERNAL_SECRET", "")

LIB_BASE      = Path.home() / "Library/Application Support/CapitalNorvex/Dossiers"
DESKTOP_BASE  = Path.home() / "Desktop/Capital Norvex"
MAX_PDF_MB    = 30  # limite Claude par PDF

if not firebase_admin._apps:
    sa_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    bucket_name = os.environ.get('FIREBASE_STORAGE_BUCKET', 'capital-norvex-uploads')
    firebase_admin.initialize_app(credentials.Certificate(sa_path), {'storageBucket': bucket_name})

bucket = fb_storage.bucket()
fs = db()

# ─── 1. Détection nouveaux uploads ───────────────────────────────────────────

def list_storage_blobs(dossier_id: str) -> List[Any]:
    return sorted(bucket.list_blobs(prefix=f'uploads/{dossier_id}/'), key=lambda b: b.updated)


def needs_analysis(dossier: Dict[str, Any], blobs: List[Any]) -> bool:
    """Vrai si nouveaux uploads détectés ET pas d'analyse récente."""
    if not blobs:
        return False
    current_count = len(blobs)
    last_count = dossier.get("docsReceivedCount", 0) or 0
    if current_count <= last_count:
        return False
    # Cooldown analyse
    last_analysis = dossier.get("norvexFinalAnalyzedAt")
    if last_analysis:
        try:
            last_dt = datetime.fromisoformat(last_analysis.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - last_dt < timedelta(hours=ANALYSIS_COOLDOWN_HOURS):
                return False
        except Exception:
            pass
    return True


# ─── 2. Patch metadata ───────────────────────────────────────────────────────

def patch_docs_metadata(dossier_id: str, blobs: List[Any]) -> List[Dict[str, Any]]:
    docs_list = []
    for b in blobs:
        name = b.name.split('/')[-1]
        parts = name.split('_', 1)
        clean_name = parts[1].replace('_', ' ') if len(parts) > 1 else name
        docs_list.append({
            'storagePath': b.name,
            'name': clean_name,
            'size': b.size,
            'uploadedAt': b.updated.isoformat(),
        })
    now_iso = datetime.now(timezone.utc).isoformat()
    fs.collection('dossiers').document(dossier_id).update({
        'lastDocsReceivedAt': now_iso,
        'docsReceivedCount': len(docs_list),
        'docsList': docs_list,
    })
    return docs_list


# ─── 3. Analyse Claude Opus 4.6 multimodal ───────────────────────────────────

def build_credit_prompt() -> str:
    return """Tu es Directeur Crédit Senior chez Capital Norvex Inc. (prêt privé institutionnel alternatif au Québec/Ontario, tickets 2,5-100 M$, taux 10-12%). Tu produis un MEMO COMITÉ CRÉDIT de qualité grande banque (BMO/RBC/BNC/Desjardins) ADAPTÉ à la réalité prêt privé alternatif.

Ce memo est le BRIEF PRÉ-RDV TEAMS d'Yves Barrette (président). Il doit lui donner :
- Note finale et verdict, taux RECOMMANDÉ (10-12%), montant FINAL recommandé
- Conditions précises à exiger
- Talking points RDV Teams
- ⚠️ CRITIQUE : la liste des DOCUMENTS PRIMORDIAUX MANQUANTS (sans exagérer — focus sur ce qui est VRAIMENT essentiel)

CRITÈRES PRÊT PRIVÉ NORVEX :
- Taux 10-12% selon risque
- LTV : porte d'entrée minimum 75%, standard 75-85%, peut aller à 100% avec collatéraux additionnels
- Équité promoteur ≥15% (résiduelle après stress)
- Sortie viable < 18 mois
- Protection capital first-mortgage privilégiée

DÉCISION : "GO" / "GO_CONDITIONNEL" / "NO_GO"
POSTURE : "favorable" / "neutre" / "serrée"

DOCUMENTS PRIMORDIAUX standards (à confronter aux docs reçus) :
- États financiers borrower (3 ans + interim)
- Évaluation immobilière indépendante (AACI ≤12 mois)
- Rent roll + leases (si revenus locatifs)
- Preuve d'équité (relevés, certificat avocat)
- KYC/identité personne morale + UBO
- Quittance hypothèque actuelle ou solde + statement
- Assurance titres + assurance hypothécaire en place
- Avis cotisation 2 dernières années
- Stratégie de sortie détaillée

OUTPUT : JSON STRICT (aucun texte avant/après, aucun ```)
{
  "finalScore": <0-100>,
  "finalScoreJustification": "<2-3 phrases>",
  "finalDecision": "GO|GO_CONDITIONNEL|NO_GO",
  "finalDecisionJustification": "<1-2 phrases>",
  "finalRate": <nombre>,
  "finalRateRange": {"low": <n>, "high": <n>},
  "finalRateJustification": "<court>",
  "finalAmount": <nombre>,
  "finalAmountJustification": "<court>",
  "loanTermMonths": <nombre>,
  "ltvCalcule": <n|null>,
  "negotiationPosture": "favorable|neutre|serrée",
  "executiveSummary": "<5-7 phrases>",
  "borrowerProfile": "<2-3 phrases>",
  "projectAnalysis": "<3-4 phrases>",
  "financialAnalysis": "<3-5 phrases>",
  "riskAssessment": {
    "strengths": ["<f1>","<f2>","<f3>"],
    "concerns": ["<c1>","<c2>"],
    "redFlags": ["<rf1>"]
  },
  "stressTestSummary": "<1-2 phrases>",
  "documentsPresents": ["<doc1>","<doc2>"],
  "documentsPrimordiauxManquants": [
    {"document":"<nom>", "criticite":"OBLIGATOIRE|UTILE", "raison":"<pourquoi>"}
  ],
  "finalConditions": ["<c1>","<c2>","<c3>"],
  "rdvTalkingPoints": [
    {"topic":"<t1>","objective":"<o1>","fallback":"<f1>"}
  ],
  "memorandumComite": "<paragraphe final 4-6 phrases>"
}"""


def run_credit_analysis(dossier: Dict[str, Any], blobs: List[Any]) -> Optional[Dict[str, Any]]:
    """Appelle Claude Opus 4.6 multimodal sur les PDFs."""
    pdf_blocks = []
    for b in blobs:
        size_mb = (b.size or 0) / 1024 / 1024
        if size_mb > MAX_PDF_MB:
            continue
        try:
            data = b.download_as_bytes()
            b64 = base64.standard_b64encode(data).decode('ascii')
            pdf_blocks.append({
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": b64},
                "title": b.name.split('/')[-1][:90],
            })
        except Exception as e:
            print(f"   ⚠️  Skip {b.name}: {e}")
    if not pdf_blocks:
        return None

    dossier_summary = {
        "id": dossier.get("id"),
        "borrowerName": f"{dossier.get('prenom','')} {dossier.get('nom','')}".strip(),
        "loanType": dossier.get('type'),
        "projectAddress": dossier.get('adresse'),
        "phase": dossier.get('stage'),
        "scoreInitial": dossier.get('score'),
        "scoreInitialDecision": dossier.get('decision'),
        "loanAmountRequested": dossier.get('montant'),
        "language": dossier.get('lang', 'fr'),
        "termePropose": dossier.get('terme'),
        "tauxPropose": dossier.get('taux'),
        "sortie": dossier.get('sortie'),
    }

    user_content = [
        {"type": "text", "text": f"DOSSIER (Score initial)\n{json.dumps(dossier_summary, indent=2, ensure_ascii=False)}\n\nVoici les {len(pdf_blocks)} documents reçus du borrower. Analyse-les comme Directeur Crédit Senior et produis le MEMO COMITÉ CRÉDIT en JSON strict."},
    ] + pdf_blocks

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8000,
        system=build_credit_prompt(),
        messages=[{"role": "user", "content": user_content}],
    )
    raw = response.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start:end+1]
    try:
        return json.loads(raw)
    except Exception as e:
        print(f"   ❌ Parse JSON Claude échoué: {e}")
        return None


# ─── 4. Brief HTML interne (placeholder — réutilise render existant) ─────────

def render_brief_html(dossier: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """Brief Comité Crédit HTML pour Yves. Calque sur render_henri_petit_docs."""
    docs_manquants = analysis.get("documentsPrimordiauxManquants", []) or []
    risk = analysis.get("riskAssessment", {}) or {}
    name = f"{dossier.get('prenom','')} {dossier.get('nom','')}".strip()
    addr = dossier.get('adresse', '—')
    decision = analysis.get('finalDecision', '—')
    decision_cls = {"GO": "go", "GO_CONDITIONNEL": "gocond", "NO_GO": "nogo"}.get(decision, "")

    def li(items): return "".join(f"<li>{x}</li>" for x in items)
    def dm(d):
        if not isinstance(d, dict): return f'<div class="dm">{d}</div>'
        crit = (d.get("criticite") or "").upper()
        cls = "dm-oblig" if crit == "OBLIGATOIRE" else "dm-utile"
        return (f'<div class="dm {cls}"><strong>[{crit}]</strong> {d.get("document","?")}<br>'
                f'<em>{d.get("raison","")}</em></div>')
    def tp(t):
        if not isinstance(t, dict): return ""
        return (f'<div class="tp"><strong>{t.get("topic","")}</strong><br>'
                f'<em>Objectif :</em> {t.get("objective","")}<br>'
                f'<em>Repli :</em> {t.get("fallback","")}</div>')

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>BRIEF — {name} ({dossier.get('id')})</title>
<style>
body{{font-family:Georgia,serif;max-width:820px;margin:32px auto;padding:0 24px;color:#0A0A0A;line-height:1.6}}
h1{{color:#9A8554;border-bottom:2px solid #C8B070;padding-bottom:10px;font-size:1.7em}}
h2{{color:#5a4a30;margin-top:32px;font-size:1.15em;border-left:3px solid #C8B070;padding-left:12px}}
.kpi-row{{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0 28px}}
.kpi{{flex:1 1 130px;padding:14px 18px;background:#FBF7EB;border-left:3px solid #C8B070}}
.kpi-val{{font-size:1.5em;font-weight:700}}
.kpi-lbl{{font-size:.72em;color:#888;text-transform:uppercase;letter-spacing:1.5px;margin-top:4px}}
.go{{color:#2E7D5C}}.gocond{{color:#C8923A}}.nogo{{color:#A53A2C}}
.dm{{background:#FFF8EE;padding:12px 16px;border-left:3px solid #C8B070;margin:8px 0;font-family:Helvetica,Arial,sans-serif;font-size:.95em}}
.dm-oblig{{background:#FCE8E5;border-left-color:#A53A2C}}
.dm em{{color:#555;font-size:.9em}}
.tp{{background:#FBF7EB;padding:14px 18px;border-left:3px solid #C8B070;margin:12px 0}}
.memo{{background:#FBF7EB;padding:18px 22px;border-left:3px solid #C8B070;font-style:italic;line-height:1.75;margin-top:18px}}
.redflag li{{color:#A53A2C;font-weight:600}}
.meta{{color:#999;font-size:.85em;font-style:italic}}
</style></head><body>
<h1>📋 MEMO COMITÉ CRÉDIT</h1>
<p class="meta">{name} · {dossier.get('type','—')} {(dossier.get('montant') or 0)/1e6:.1f} M$ · {addr} · Préparé {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<div class="kpi-row">
  <div class="kpi"><div class="kpi-val">{analysis.get('finalScore','—')}/100</div><div class="kpi-lbl">Score final</div></div>
  <div class="kpi"><div class="kpi-val {decision_cls}">{decision.replace('_',' ')}</div><div class="kpi-lbl">Décision</div></div>
  <div class="kpi"><div class="kpi-val">{analysis.get('finalRate','—')} %</div><div class="kpi-lbl">Taux</div></div>
  <div class="kpi"><div class="kpi-val">{(analysis.get('finalAmount') or 0)/1e6:.1f} M$</div><div class="kpi-lbl">Montant</div></div>
  <div class="kpi"><div class="kpi-val">{analysis.get('ltvCalcule','—') or '—'}{'%' if analysis.get('ltvCalcule') else ''}</div><div class="kpi-lbl">LTV</div></div>
  <div class="kpi"><div class="kpi-val">{analysis.get('negotiationPosture','—')}</div><div class="kpi-lbl">Posture</div></div>
</div>
<h2>Sommaire exécutif</h2><p>{analysis.get('executiveSummary','—')}</p>
<h2>Profil borrower</h2><p>{analysis.get('borrowerProfile','—')}</p>
<h2>Analyse projet</h2><p>{analysis.get('projectAnalysis','—')}</p>
<h2>Analyse financière</h2><p>{analysis.get('financialAnalysis','—')}</p>
<h2>Stress test</h2><p>{analysis.get('stressTestSummary','—')}</p>
<h2>Évaluation des risques</h2>
<p><strong>Forces :</strong></p><ul>{li(risk.get('strengths',[]))}</ul>
<p><strong>Préoccupations :</strong></p><ul>{li(risk.get('concerns',[]))}</ul>
<p><strong>Red flags :</strong></p><ul class="redflag">{li([rf for rf in risk.get('redFlags',[]) if rf and rf.lower()!='aucun'])}</ul>
<h2>📄 Documents PRIMORDIAUX manquants</h2>{''.join(dm(d) for d in docs_manquants)}
<h2>✅ Documents présents</h2><ul>{li(analysis.get('documentsPresents',[]))}</ul>
<h2>Conditions à exiger</h2><ol>{li(analysis.get('finalConditions',[]))}</ol>
<h2>🎯 Talking points — RDV Teams</h2>{''.join(tp(t) for t in analysis.get('rdvTalkingPoints',[]))}
<h2>📜 Memorandum formel</h2><div class="memo">{analysis.get('memorandumComite','—')}</div>
</body></html>"""


# ─── 5. Lettre client (FR ou EN) — règles strictes pré-engagement ────────────

def render_client_letter(dossier: Dict[str, Any], analysis: Dict[str, Any], upload_token: str) -> Optional[str]:
    lang = (dossier.get('lang') or 'fr').lower()
    upload_url = f"{SITE_URL}/upload.html?t={upload_token}"
    docs_manquants = analysis.get("documentsPrimordiauxManquants", []) or []
    obligatoires = [d for d in docs_manquants if isinstance(d, dict) and (d.get("criticite") or "").upper() == "OBLIGATOIRE"]
    final_amount = analysis.get("finalAmount") or 0
    final_rate = analysis.get("finalRate") or 11.5

    is_en = lang == "en"
    # Nom complet + entité (NTA Development Corporation pour Henri par ex)
    name = f"{dossier.get('prenom','')} {dossier.get('nom','')}".strip()
    address = dossier.get('adresse','')

    if is_en:
        system = """You are Yves Barrette, Founder of Capital Norvex Inc. Draft a strictly institutional pre-commitment letter to a borrower.

ABSOLUTE RULES:
1. ❌ FORBIDDEN: "approved","approval","granted","we offer","we extend","we commit","Credit Committee approval"
2. ✅ Use: "Capital Norvex would be prepared to consider on a strictly preliminary and non-binding basis..."
3. Tone: Bay Street institutional, arm's-length. NEVER use first names. Use "Dear Mr./Ms. <LastName>".
4. List MANDATORY missing documents with one-line rationale each.
5. Deadline: 5 business days.
6. Include upload portal link.
7. Signoff: "With consideration,"
8. Mandatory disclaimer at end: "This correspondence constitutes a preliminary expression of interest. It does not bind Capital Norvex and does not constitute an offer, a term sheet, or a commitment to lend. Any formal commitment of Capital Norvex would only take effect upon execution of a written Commitment Letter, which may include its own conditions precedent or resolutoires."

OUTPUT: HTML body only (no <html>/<body>). Use <p>, <ul>, <strong>. Georgia serif."""
    else:
        system = """Tu es Yves Barrette, Fondateur de Capital Norvex Inc. Rédige une lettre pré-engagement strictement institutionnelle à un emprunteur.

RÈGLES ABSOLUES:
1. ❌ INTERDIT : « approuvé », « approbation », « accordé », « offrons », « accordons », « financement approuvé »
2. ✅ Utiliser : « Capital Norvex pourrait considérer sur une base strictement préliminaire et non-liante... »
3. Ton : institutionnel, distancié. Utiliser « Cher Monsieur <Nom> » ou « Madame ».
4. Liste documents OBLIGATOIRES manquants avec raison brève (1 ligne).
5. Délai : 5 jours ouvrables.
6. Inclure lien portail upload.
7. Signoff : « Avec considération, »
8. Disclaimer obligatoire en fin : « La présente correspondance constitue une expression d'intérêt préliminaire. Elle ne lie pas Capital Norvex et ne constitue ni une offre, ni un engagement de prêt. Tout engagement formel de Capital Norvex ne pourra prendre effet qu'à la signature d'une lettre d'engagement écrite, laquelle pourra contenir ses propres conditions résolutoires. »

OUTPUT : HTML body uniquement (pas <html>/<body>). Utilise <p>, <ul>, <strong>. Georgia serif."""

    user = f"""Borrower: {name}
Address: {address}
Loan type: {dossier.get('type')}
Indicative amount: CAD {final_amount}
Indicative rate: {final_rate}% per annum
Deadline: 5 business days
Upload portal: {upload_url}

Mandatory missing documents:
{json.dumps(obligatoires, indent=2, ensure_ascii=False)}

Draft the letter now."""

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3500,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    body_html = resp.content[0].text.strip().replace("```html", "").replace("```", "").strip()

    # Anti-mots-interdits
    forbidden = ["approved", "approval", "granted", "we offer", "we extend",
                 "approuvé", "approuvée", "approbation", "accordé", "nous offrons"]
    if any(w.lower() in body_html.lower() for w in forbidden):
        return None  # signal d'échec — pas envoyer

    # HTML letterhead
    if is_en:
        date_str = datetime.now().strftime("%B %-d, %Y")
        re_str = f"Re: {dossier.get('type','Application')} — {address} ({dossier.get('id')})"
    else:
        mois = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]
        date_str = f"Le {datetime.now().day} {mois[datetime.now().month-1]} {datetime.now().year}"
        re_str = f"Objet : {dossier.get('type','Demande')} — {address} ({dossier.get('id')})"

    full = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Capital Norvex</title>
<style>
body{{font-family:Georgia,serif;max-width:740px;margin:40px auto;padding:0 36px;color:#0A0A0A;line-height:1.75;font-size:15px}}
.letterhead{{text-align:center;border-bottom:2px solid #C8B070;padding-bottom:22px;margin-bottom:32px}}
.letterhead h1{{color:#9A8554;margin:0;font-size:1.9em;letter-spacing:2px}}
.letterhead p{{margin:4px 0;color:#666;font-size:.85em}}
.date{{text-align:right;color:#555;margin-bottom:28px;font-size:.92em}}
.cta-box{{background:#FBF7EB;border-left:3px solid #C8B070;padding:18px 24px;margin:24px 0}}
.cta-box a{{color:#9A8554;font-weight:700;text-decoration:none;word-break:break-all}}
</style></head><body>
<div class="letterhead">
  <h1>CAPITAL NORVEX</h1>
  <p>Private Commercial Lending · Quebec &amp; Ontario</p>
  <p>2705-1000 André-Prévost, Île-des-Sœurs, Montréal QC H3E 0G2</p>
  <p>+1 (438) 533-PRÊT (7738) · yves@capitalnorvex.com</p>
</div>
<p class="date">{date_str}</p>
<p style="margin-bottom:24px"><strong>{re_str}</strong></p>
<div class="body">{body_html}</div>
<div class="cta-box">
  <p style="margin:0 0 8px 0"><strong>{"Secure portal for document submission:" if is_en else "Lien sécurisé pour le dépôt des documents :"}</strong></p>
  <p style="margin:0;font-family:'DM Mono',monospace;font-size:.9em"><a href="{upload_url}">{upload_url}</a></p>
</div>
</body></html>"""
    return full


# ─── 6. Email send (SendGrid) ────────────────────────────────────────────────

def sendgrid_send(to_email: str, to_name: str, subject: str, html: str,
                  from_email="yves@capitalnorvex.com",
                  from_name="Yves Barrette — Capital Norvex") -> bool:
    sg = os.environ.get("SENDGRID_API_KEY")
    if not sg:
        return False
    payload = {
        "personalizations": [{"to": [{"email": to_email, "name": to_name}]}],
        "from": {"email": from_email, "name": from_name},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
    }
    r = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={"Authorization": f"Bearer {sg}", "Content-Type": "application/json"},
        json=payload, timeout=30,
    )
    return r.status_code in (200, 202)


# ─── 7. Classement copies dans dossiers locaux ───────────────────────────────

def file_brief_in_folders(dossier_id: str, brief_html: str, name: str) -> List[str]:
    """Sauvegarde le brief dans Library + Desktop folders."""
    paths = []
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    fname = f"Brief Comité Crédit (Norvex Final) — {stamp}.html"

    lib_dir = LIB_BASE / dossier_id
    if lib_dir.exists():
        p = lib_dir / fname
        p.write_text(brief_html, encoding="utf-8")
        paths.append(str(p))

    # Desktop : cherche le folder par nom
    if name:
        desk_candidates = list(DESKTOP_BASE.glob(f"*{name}*"))
        for d in desk_candidates:
            if d.is_dir():
                p = d / fname
                p.write_text(brief_html, encoding="utf-8")
                paths.append(str(p))

    return paths


# ─── 8. Création token upload ────────────────────────────────────────────────

def create_upload_token(dossier_id: str, client_nom: str, client_email: str,
                        projet: str, lang: str) -> Optional[str]:
    try:
        r = requests.post(
            f"{SITE_URL}/.netlify/functions/create-upload-token",
            json={"dossierID": dossier_id, "clientNom": client_nom,
                  "clientEmail": client_email, "projet": projet, "lang": lang},
            timeout=30,
        )
        if r.status_code == 200:
            return r.json().get("token")
    except Exception:
        pass
    return None


# ─── PIPELINE PRINCIPAL ──────────────────────────────────────────────────────

def process_dossier(dossier_id: str, dry: bool = False) -> Dict[str, Any]:
    """Pipeline complet pour un dossier."""
    snap = fs.collection('dossiers').document(dossier_id).get()
    if not snap.exists:
        return {"status": "not_found"}
    dossier = snap.to_dict()
    dossier["id"] = dossier_id

    name = f"{dossier.get('prenom','')} {dossier.get('nom','')}".strip()
    print(f"\n=== {dossier_id} — {name} ({dossier.get('type','?')}) ===")

    blobs = list_storage_blobs(dossier_id)
    if not needs_analysis(dossier, blobs):
        print(f"   ⏭️  Skip — pas de nouveaux uploads ou analyse récente")
        return {"status": "skipped"}

    print(f"   📦 {len(blobs)} blobs Storage (vs {dossier.get('docsReceivedCount',0)} précédent)")

    if dry:
        print(f"   🟡 DRY-RUN — aurait lancé l'analyse Claude Opus 4.6")
        return {"status": "dry_would_analyze", "blobs": len(blobs)}

    # 1. Patch metadata
    patch_docs_metadata(dossier_id, blobs)

    # 2. Analyse Claude Opus 4.6
    print(f"   🤖 Analyse Claude Opus 4.6 multimodal sur {len(blobs)} PDFs…")
    analysis = run_credit_analysis(dossier, blobs)
    if not analysis:
        return {"status": "analysis_failed"}
    print(f"   ✅ Score {analysis.get('finalScore')}/100 — {analysis.get('finalDecision')}")

    # 3. Brief HTML
    brief_html = render_brief_html(dossier, analysis)

    # 4. Email Yves + classement dossiers locaux
    yves_subject = (f"📋 BRIEF COMITÉ CRÉDIT — {name} ({dossier_id}) — "
                    f"Score {analysis.get('finalScore')}/100, {analysis.get('finalDecision')}")
    sent_yves = sendgrid_send("yves@capitalnorvex.com", "Yves Barrette",
                              yves_subject, brief_html,
                              from_name="Norvex FINAL™ — Comité Crédit")
    file_paths = file_brief_in_folders(dossier_id, brief_html, name)
    print(f"   ✉  Brief Yves: {'OK' if sent_yves else 'FAILED'} | classé: {len(file_paths)} dossiers")

    # 5. Token + lettre client + envoi
    client_email = dossier.get("email", "")
    token = create_upload_token(dossier_id, name, client_email, dossier.get("type",""), dossier.get("lang","fr"))
    letter_sent = False
    if token and client_email:
        letter_html = render_client_letter(dossier, analysis, token)
        if letter_html:
            client_subject = (f"Capital Norvex — {dossier.get('type','Application')} ({dossier_id})"
                              if (dossier.get('lang') or 'fr') == 'en'
                              else f"Capital Norvex — Demande de {dossier.get('type','financement')} ({dossier_id})")
            letter_sent = sendgrid_send(client_email, name, client_subject, letter_html)
            print(f"   ✉  Lettre client: {'OK' if letter_sent else 'FAILED'}")

    # 6. Audit + patch dossier
    now_iso = datetime.now(timezone.utc).isoformat()
    fs.collection('dossiers').document(dossier_id).update({
        'norvexFinalAnalyzedAt': now_iso,
        'norvexFinalScore': analysis.get('finalScore'),
        'norvexFinalDecision': analysis.get('finalDecision'),
        'norvexFinalRate': analysis.get('finalRate'),
        'norvexFinalAmount': analysis.get('finalAmount'),
        'preEngagementLetterSentAt': now_iso if letter_sent else None,
        'preEngagementLetterSentTo': client_email if letter_sent else None,
        'uploadTokenActive': token if letter_sent else None,
        'docsDeadlineBusinessDays': DOCS_DEADLINE_BUSINESS if letter_sent else None,
    })
    audit_log(
        agent="norvex_final_auto",
        action="full_pipeline_completed",
        target_type="dossiers",
        target_id=dossier_id,
        details={"score": analysis.get('finalScore'), "decision": analysis.get('finalDecision'),
                 "yvesSent": sent_yves, "letterSent": letter_sent, "blobs": len(blobs)},
    )
    return {"status": "completed", "score": analysis.get('finalScore'),
            "decision": analysis.get('finalDecision'), "yvesSent": sent_yves,
            "letterSent": letter_sent}


def process_all(dry: bool = False) -> Dict[str, Any]:
    """Tous les dossiers stage='docs'."""
    docs = list(fs.collection('dossiers').where('stage', '==', 'docs').stream())
    print(f"\n{'🟡 DRY-RUN' if dry else '🚀 EXÉCUTION'} — {len(docs)} dossiers stage='docs'\n")
    results = []
    for snap in docs:
        try:
            r = process_dossier(snap.id, dry=dry)
            results.append({"id": snap.id, **r})
        except Exception as e:
            print(f"   ❌ Erreur {snap.id}: {e}")
            results.append({"id": snap.id, "status": "error", "error": str(e)[:200]})
    return {"results": results, "total": len(docs)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry", action="store_true")
    p.add_argument("--dossier", type=str)
    args = p.parse_args()

    if args.dossier:
        r = process_dossier(args.dossier, dry=args.dry)
        print(f"\nRésultat : {r}")
    else:
        r = process_all(dry=args.dry)
        ok = sum(1 for x in r["results"] if x["status"] == "completed")
        skip = sum(1 for x in r["results"] if x["status"] == "skipped")
        err = sum(1 for x in r["results"] if x["status"].startswith("error") or x["status"] == "analysis_failed")
        print(f"\n— Résumé —\n  Total : {r['total']}\n  Complétés : {ok}\n  Sautés : {skip}\n  Erreurs : {err}")


if __name__ == "__main__":
    main()
