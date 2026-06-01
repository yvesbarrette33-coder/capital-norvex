"""
Phase A2 — génère les 2 documents pour Henri Petit à partir de analysis.json :
  1. Brief interne pour Yves (Comité Crédit)
  2. Lettre client (politique, demande correctifs)

Sauve les 2 fichiers HTML dans /tmp/norvex-test/

Usage : python -m agents.refi.render_henri_petit_docs
"""
import json
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/.capitalnorvex/.env'))

import anthropic

OUT = Path("/tmp/norvex-test")
analysis = json.loads((OUT / "analysis.json").read_text(encoding="utf-8"))

# ─────────────────────────────────────────────────────────────────────
# DOCUMENT 1 — BRIEF INTERNE pour Yves
# ─────────────────────────────────────────────────────────────────────

def render_brief_interne(a):
    docs_manquants = a.get("documentsPrimordiauxManquants", []) or []
    risk = a.get("riskAssessment", {}) or {}
    strengths = risk.get("strengths", []) or []
    concerns = risk.get("concerns", []) or []
    redflags = [rf for rf in (risk.get("redFlags", []) or []) if rf and rf.lower() != "aucun"]
    conditions = a.get("finalConditions", []) or []
    talking = a.get("rdvTalkingPoints", []) or []
    docs_pres = a.get("documentsPresents", []) or []

    def li(items):
        return "".join(f"<li>{x}</li>" for x in items)

    def dm_card(dm):
        if not isinstance(dm, dict):
            return f'<div class="dm">{dm}</div>'
        crit = (dm.get("criticite") or "").upper()
        cls = "dm-oblig" if crit == "OBLIGATOIRE" else "dm-utile"
        return (f'<div class="dm {cls}"><strong>[{crit}]</strong> '
                f'{dm.get("document","?")}<br>'
                f'<em>{dm.get("raison","")}</em></div>')

    def tp_card(tp):
        if not isinstance(tp, dict):
            return ""
        return (f'<div class="tp"><strong>{tp.get("topic","")}</strong><br>'
                f'<em>Objectif :</em> {tp.get("objective","")}<br>'
                f'<em>Repli :</em> {tp.get("fallback","")}</div>')

    decision = a.get("finalDecision", "—")
    decision_cls = {"GO": "go", "GO_CONDITIONNEL": "gocond", "NO_GO": "nogo"}.get(decision, "")
    final_amount = a.get("finalAmount") or 0
    ltv = a.get("ltvCalcule")
    ltv_str = f"{ltv}%" if ltv else "—"

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>BRIEF — Henri Petit (CNV-2026-59109)</title>
<style>
body {{ font-family: Georgia, "Times New Roman", serif; max-width: 820px; margin: 32px auto; padding: 0 24px; color: #0A0A0A; line-height: 1.6; }}
h1 {{ color: #9A8554; border-bottom: 2px solid #C8B070; padding-bottom: 10px; font-size: 1.7em; }}
h2 {{ color: #5a4a30; margin-top: 32px; font-size: 1.15em; border-left: 3px solid #C8B070; padding-left: 12px; }}
.kpi-row {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 18px 0 28px; }}
.kpi {{ flex: 1 1 130px; padding: 14px 18px; background: #FBF7EB; border-left: 3px solid #C8B070; }}
.kpi-val {{ font-size: 1.5em; font-weight: 700; }}
.kpi-lbl {{ font-size: .72em; color: #888; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 4px; }}
.go {{ color: #2E7D5C; }} .gocond {{ color: #C8923A; }} .nogo {{ color: #A53A2C; }}
ul, ol {{ padding-left: 24px; }} li {{ margin: 6px 0; }}
.dm {{ background: #FFF8EE; padding: 12px 16px; border-left: 3px solid #C8B070; margin: 8px 0; font-family: Helvetica, Arial, sans-serif; font-size: .95em; }}
.dm-oblig {{ background: #FCE8E5; border-left-color: #A53A2C; }}
.dm em {{ color: #555; font-size: .9em; }}
.tp {{ background: #FBF7EB; padding: 14px 18px; border-left: 3px solid #C8B070; margin: 12px 0; }}
.memo {{ background: #FBF7EB; padding: 18px 22px; border-left: 3px solid #C8B070; font-style: italic; line-height: 1.75; margin-top: 18px; }}
.redflag li {{ color: #A53A2C; font-weight: 600; }}
.meta {{ color: #999; font-size: .85em; font-style: italic; }}
</style></head><body>

<h1>📋 MEMO COMITÉ CRÉDIT</h1>
<p class="meta">Henri Petit / NTA Development Corporation · Refi commercial 27,5 M$ · 6485 14th Line, Alliston (Ontario) · Préparé 2026-05-07</p>

<div class="kpi-row">
  <div class="kpi"><div class="kpi-val">{a.get('finalScore','—')}/100</div><div class="kpi-lbl">Score final</div></div>
  <div class="kpi"><div class="kpi-val {decision_cls}">{decision.replace('_',' ')}</div><div class="kpi-lbl">Décision</div></div>
  <div class="kpi"><div class="kpi-val">{a.get('finalRate','—')} %</div><div class="kpi-lbl">Taux</div></div>
  <div class="kpi"><div class="kpi-val">{final_amount/1e6:.1f} M$</div><div class="kpi-lbl">Montant</div></div>
  <div class="kpi"><div class="kpi-val">{ltv_str}</div><div class="kpi-lbl">LTV</div></div>
  <div class="kpi"><div class="kpi-val">{a.get('negotiationPosture','—')}</div><div class="kpi-lbl">Posture</div></div>
</div>

<h2>Sommaire exécutif</h2>
<p>{a.get('executiveSummary','—')}</p>

<h2>Profil borrower</h2>
<p>{a.get('borrowerProfile','—')}</p>

<h2>Analyse projet</h2>
<p>{a.get('projectAnalysis','—')}</p>

<h2>Analyse financière</h2>
<p>{a.get('financialAnalysis','—')}</p>

<h2>Stress test</h2>
<p>{a.get('stressTestSummary','—')}</p>

<h2>Évaluation des risques</h2>
<p><strong>Forces :</strong></p><ul>{li(strengths)}</ul>
<p><strong>Préoccupations :</strong></p><ul>{li(concerns)}</ul>
{('<p><strong>Red flags :</strong></p><ul class="redflag">' + li(redflags) + '</ul>') if redflags else ''}

<h2>📄 Documents PRIMORDIAUX manquants</h2>
{''.join(dm_card(dm) for dm in docs_manquants)}

<h2>✅ Documents présents au dossier</h2>
<ul>{li(docs_pres)}</ul>

<h2>Conditions à exiger (avant déboursé)</h2>
<ol>{li(conditions)}</ol>

<h2>🎯 Talking points — RDV Teams</h2>
{''.join(tp_card(tp) for tp in talking)}

<h2>📜 Memorandum formel — Comité Crédit</h2>
<div class="memo">{a.get('memorandumComite','—')}</div>

<hr style="margin-top:40px;border:none;border-top:1px solid #ddd">
<p class="meta">Ce memo est généré par Norvex FINAL™ (Claude Opus 4.6 institutionnel) à partir des {len(docs_pres) + len(docs_manquants)} critères évalués sur le dossier Henri Petit.<br>
Le score initial Score Norvex™ était de {(74)} (CONDITIONNEL). L'analyse finale post-documents a ajusté à {a.get('finalScore','—')}.</p>

</body></html>"""
    return html


# ─────────────────────────────────────────────────────────────────────
# DOCUMENT 2 — LETTRE CLIENT (Claude génère le ton diplomatique)
# ─────────────────────────────────────────────────────────────────────

def render_lettre_client(a, lang="en"):
    """Demande à Claude de produire la lettre client diplomatique."""
    docs_manquants = a.get("documentsPrimordiauxManquants", []) or []
    obligatoires = [dm for dm in docs_manquants if isinstance(dm, dict) and (dm.get("criticite") or "").upper() == "OBLIGATOIRE"]
    conditions = a.get("finalConditions", []) or []
    decision = a.get("finalDecision", "GO_CONDITIONNEL")
    final_rate = a.get("finalRate")
    final_amount = a.get("finalAmount")

    system = f"""You are a Senior Credit Officer at Capital Norvex Inc. (private commercial lending, Quebec/Ontario).
You are drafting a polished, diplomatic letter to the borrower (Henri Petit, NTA Development Corporation) regarding their refinancing application of CAD 27,500,000 for the Alliston Ontario property.

The Credit Committee's finding is: {decision}.
- Final amount approved (subject to documentation): CAD {(final_amount or 0):,.0f}
- Final rate: {final_rate}% per annum
- Key conditions to be met before funding

The letter must:
1. Be written in {("English" if lang=="en" else "French")}
2. Use a professional, diplomatic but FACT-BASED tone (not apologetic, not aggressive — institutional)
3. Reference clearly the {len(obligatoires)} MANDATORY documents still required
4. Explain WHY each is needed (briefly, 1 line each)
5. List the conditions precedent
6. Provide a clear path forward (deadline 14 business days, contact info, upload link placeholder)
7. Maintain the borrower's dignity — no condescension
8. End with consideration ("With consideration" / "Avec considération") — NOT "Best regards" or "Sincèrement"
9. Sign as "Yves Barrette, Founder, Capital Norvex Inc." with company contact

Output ONLY the HTML body of the letter (no <html>, no <body>, no <head>, no markdown). Use simple HTML: <p>, <ul>, <strong>. Use inline styles for elegance (Georgia serif, line-height 1.6, color #0A0A0A).
"""

    user = f"""Here are the missing mandatory documents:
{json.dumps(obligatoires, indent=2, ensure_ascii=False)}

Conditions precedent:
{json.dumps(conditions, indent=2, ensure_ascii=False)}

Final amount approved: {final_amount}
Final rate: {final_rate}%
Decision: {decision}

Draft the letter now."""

    print("🤖 Génération lettre client (Claude Sonnet 4.6)...")
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    body_html = resp.content[0].text.strip()
    # Strip markdown if any
    body_html = body_html.replace("```html", "").replace("```", "").strip()

    full_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Capital Norvex — Letter to Borrower</title>
<style>
body {{ font-family: Georgia, "Times New Roman", serif; max-width: 720px; margin: 40px auto; padding: 0 32px; color: #0A0A0A; line-height: 1.7; }}
.letterhead {{ text-align: center; border-bottom: 2px solid #C8B070; padding-bottom: 18px; margin-bottom: 28px; }}
.letterhead h1 {{ color: #9A8554; margin: 0; font-size: 1.8em; letter-spacing: 1.5px; }}
.letterhead p {{ margin: 4px 0; color: #666; font-size: .9em; }}
.date {{ text-align: right; color: #666; margin-bottom: 24px; }}
.recipient {{ margin-bottom: 28px; }}
.body p {{ margin: 14px 0; }}
.body ul {{ padding-left: 24px; }}
.body li {{ margin: 8px 0; }}
.signoff {{ margin-top: 42px; }}
.meta {{ color: #999; font-size: .8em; font-style: italic; margin-top: 50px; border-top: 1px solid #eee; padding-top: 12px; }}
</style></head><body>

<div class="letterhead">
  <h1>CAPITAL NORVEX</h1>
  <p>Private Commercial Lending · Quebec & Ontario</p>
  <p>2705-1000 André-Prévost, Île-des-Sœurs, Montréal QC H3E 0G2 · 438-533-PRÊT (7738)</p>
</div>

<p class="date">May 7, 2026</p>

<div class="recipient">
  <p><strong>Mr. Henri Petit</strong><br>
  NTA Development Corporation<br>
  6485 14th Line<br>
  New Tecumseth (Alliston), Ontario</p>
  <p>By email: hpetit@ghp.ca</p>
</div>

<p style="margin-bottom: 22px;"><strong>Re: Refinancing Application — 6485 14th Line, Alliston (CNV-2026-59109)</strong></p>

<div class="body">
{body_html}
</div>

<p class="meta">⚠️ Test Phase A — généré localement, NON envoyé. Yves valide d'abord.</p>

</body></html>"""
    return full_html


def main():
    print("\n📄 Génération brief interne…")
    brief = render_brief_interne(analysis)
    (OUT / "henri_petit_brief.html").write_text(brief, encoding="utf-8")
    print(f"   ✅ {OUT / 'henri_petit_brief.html'}")

    print("\n📨 Génération lettre client…")
    letter = render_lettre_client(analysis, lang="en")
    (OUT / "henri_petit_lettre_client.html").write_text(letter, encoding="utf-8")
    print(f"   ✅ {OUT / 'henri_petit_lettre_client.html'}")

    # Ouvre les 2 dans le navigateur
    os.system(f"open '{OUT / 'henri_petit_brief.html'}' '{OUT / 'henri_petit_lettre_client.html'}'")
    print("\n✅ Les 2 documents ouverts dans le navigateur.")
    print("   Si OK → on automatise.")


if __name__ == "__main__":
    main()
