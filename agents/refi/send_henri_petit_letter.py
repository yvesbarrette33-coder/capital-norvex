"""
ENVOI RÉEL — Lettre EN à Henri Petit (hpetit@ghp.ca).

⚠️ AUCUNE mention de test, aucun placeholder, délai 5 jours ouvrables, vrai token.
Envoi via SendGrid depuis yves@capitalnorvex.com.
"""
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/.capitalnorvex/.env'))

import anthropic

OUT = Path("/tmp/norvex-test")
analysis = json.loads((OUT / "analysis.json").read_text(encoding="utf-8"))

# Vrai token généré via /api/create-upload-token
UPLOAD_TOKEN = "abd8401b39767ce7893cba156a70e0f8a016"
UPLOAD_URL = f"https://capitalnorvex.com/upload.html?t={UPLOAD_TOKEN}"
RECIPIENT_EMAIL = "hpetit@ghp.ca"
RECIPIENT_NAME = "Henri Petit"
SENDER_EMAIL = "yves@capitalnorvex.com"
SENDER_NAME = "Yves Barrette — Capital Norvex"
DOSSIER_ID = "CNV-2026-59109"

docs_manquants = analysis.get("documentsPrimordiauxManquants", []) or []
obligatoires = [dm for dm in docs_manquants if isinstance(dm, dict) and (dm.get("criticite") or "").upper() == "OBLIGATOIRE"]
utiles = [dm for dm in docs_manquants if isinstance(dm, dict) and (dm.get("criticite") or "").upper() == "UTILE"]
conditions = analysis.get("finalConditions", []) or []
final_amount = analysis.get("finalAmount") or 20_000_000
final_rate = analysis.get("finalRate") or 11.5

system = f"""You are Yves Barrette, Founder of Capital Norvex Inc. You are writing to Mr. Henri Petit (NTA Development Corporation) regarding a refinancing application of CAD 27.5M for the property at 6485 14th Line, Alliston, Ontario.

CONTEXT — CRITICAL:
- Mr. Petit is a personal acquaintance of Mr. Barrette AND a 35-year-veteran lawyer
- HOWEVER this letter will be presented to the EXECUTIVE COMMITTEE of a PUBLIC COMPANY
- Tone must therefore be STRICTLY INSTITUTIONAL, FORMAL, ARM'S-LENGTH
- "Dear Mr. Petit" — NEVER "Dear Henri"
- Style: Bay Street institutional (Stikeman / RBC Capital Markets / BMO)

BUSINESS CONTEXT:
- Development land with potential value
- Existing first mortgage of ~CAD 8M (9360-8024 Québec Inc.)
- No current cash flow (vacant land, awaiting zoning/permits)
- Exit strategy = sale or long-term refi once zoning obtained

ABSOLUTE RULES — PRE-COMMITMENT LETTER:

⚠️ THIS IS A PRE-COMMITMENT LETTER. NO FORMAL OFFER. ONLY EXPRESSION OF INTEREST AND REQUEST FOR FILE COMPLETION. Formal commitment will only follow upon a signed Commitment Letter.

1. ❌ STRICTLY FORBIDDEN — DO NOT USE THESE WORDS ANYWHERE IN THE LETTER, EVEN IN PROCEDURAL CONTEXT:
   - "approved" / "approval" → use "review" / "decision" instead
   - "granted" → use "considered" instead
   - "we offer" / "we extend" / "we commit" / "hereby grant" / "we accord"
   - "Credit Committee approval" → use "Credit Committee review" or "Credit Committee decision"
   - "subject to approval" → use "subject to formal review" or "subject to satisfactory review"
   The mere appearance of "approve" / "approval" anywhere will trigger automatic rejection. Use synonyms.
2. ❌ FORBIDDEN: firm promise of rate or amount.
3. ✅ PERMITTED:
   - "Capital Norvex would be prepared to consider, on a strictly preliminary and non-binding basis..."
   - "Subject to satisfactory completion of due diligence and the formal review of our Credit Committee..."
   - "The indicative parameters set out below are non-binding and subject to revision..."
   - "Should the file proceed, definitive terms would be set forth in a formal Commitment Letter..."
4. Tone STRICTLY institutional — no first names, no warmth, no informality.
5. Acknowledge file quality WITHOUT committing.
6. Indicative parameters: up to CAD 20M, indicative rate 11-12%, term to be confirmed — clearly qualified as PRELIMINARY, NON-BINDING.
7. List MANDATORY missing documents with one-line rationale each (English).
8. Deadline: **5 business days** for submission.
9. Include the upload portal link: {UPLOAD_URL}
10. Salutation: "Dear Mr. Petit," — NEVER "Dear Henri".
11. Signoff: "With consideration,".
12. Signature: "Yves Barrette, Founder, Capital Norvex Inc."
13. Mandatory disclaimer at end:
    "This correspondence constitutes a preliminary expression of interest. It does not bind Capital Norvex and does not constitute an offer, a term sheet, or a commitment to lend. Any formal commitment of Capital Norvex would only take effect upon execution of a written Commitment Letter, which may include its own conditions precedent or resolutoires."

OUTPUT: Only the HTML body of the letter. Use <p>, <ul>, <strong>, <em>. Sober Georgia serif style. NEVER use "approved" or any informal phrasing.

LANGUAGE: ENGLISH ONLY.
"""

user = f"""MANDATORY missing documents:
{json.dumps(obligatoires, indent=2, ensure_ascii=False)}

USEFUL documents (mention briefly):
{json.dumps(utiles, indent=2, ensure_ascii=False)}

Conditions precedent (mention without detailing):
{json.dumps(conditions[:3], indent=2, ensure_ascii=False)}

Indicative amount: CAD {final_amount}
Indicative rate: {final_rate}% per annum
Deadline: 5 business days
Upload portal: {UPLOAD_URL}

Draft the letter now in formal institutional English."""

print("🤖 Génération lettre EN finale (5 jours ouvrables, vrai token, pas de mention test)…")
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
             "we commit", "hereby grant", "approuvé", "Dear Henri", "Hi Henri"]
violations = [w for w in forbidden if w.lower() in body_html.lower()]
if violations:
    print(f"❌ ARRÊT — mots interdits détectés : {violations}")
    raise SystemExit(1)
print("✅ Aucun mot interdit. Aucune familiarité.")

# HTML final — SANS mention test, SANS placeholder
full_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Capital Norvex — Refinancing Application</title>
<style>
body {{ font-family: Georgia, "Times New Roman", serif; max-width: 740px; margin: 40px auto; padding: 0 36px; color: #0A0A0A; line-height: 1.75; font-size: 15px; }}
.letterhead {{ text-align: center; border-bottom: 2px solid #C8B070; padding-bottom: 22px; margin-bottom: 32px; }}
.letterhead h1 {{ color: #9A8554; margin: 0; font-size: 1.9em; letter-spacing: 2px; font-family: Georgia, serif; }}
.letterhead p {{ margin: 4px 0; color: #666; font-size: .85em; }}
.date {{ text-align: right; color: #555; margin-bottom: 28px; font-size: .92em; }}
.recipient {{ margin-bottom: 32px; }}
.body p {{ margin: 16px 0; }}
.body ul {{ padding-left: 28px; margin: 14px 0; }}
.body li {{ margin: 10px 0; }}
.cta-box {{ background: #FBF7EB; border-left: 3px solid #C8B070; padding: 18px 24px; margin: 24px 0; }}
.cta-box a {{ color: #9A8554; font-weight: 700; text-decoration: none; word-break: break-all; }}
strong {{ color: #0A0A0A; }}
</style></head><body>

<div class="letterhead">
  <h1>CAPITAL NORVEX</h1>
  <p>Private Commercial Lending · Quebec &amp; Ontario</p>
  <p>2705-1000 André-Prévost, Île-des-Sœurs, Montréal QC H3E 0G2</p>
  <p>+1 (438) 533-PRÊT (7738) · yves@capitalnorvex.com</p>
</div>

<p class="date">May 7, 2026</p>

<div class="recipient">
  <p><strong>Mr. Henri Petit</strong><br>
  NTA Development Corporation<br>
  6485 14th Line<br>
  New Tecumseth (Alliston), Ontario</p>
  <p>By email: hpetit@ghp.ca</p>
</div>

<p style="margin-bottom: 24px;"><strong>Re: Refinancing Application — 6485 14th Line, Alliston (CNV-2026-59109)</strong></p>

<div class="body">
{body_html}
</div>

<div class="cta-box">
  <p style="margin: 0 0 8px 0;"><strong>Secure portal for document submission:</strong></p>
  <p style="margin: 0; font-family: 'DM Mono', monospace; font-size: .9em;"><a href="{UPLOAD_URL}">{UPLOAD_URL}</a></p>
</div>

</body></html>"""

# Sauvegarde locale (pour audit/Yves)
final_path = OUT / "henri_petit_lettre_FINALE_envoyee.html"
final_path.write_text(full_html, encoding="utf-8")
print(f"📄 Lettre finale sauvée : {final_path}")

# Confirmation avant envoi RÉEL
print(f"\n{'='*60}")
print(f"  ✉  ENVOI RÉEL")
print(f"  De      : {SENDER_EMAIL}")
print(f"  À       : {RECIPIENT_EMAIL}")
print(f"  Sujet   : Capital Norvex — Refinancing Application (CNV-2026-59109)")
print(f"  Token   : {UPLOAD_TOKEN}")
print(f"  Délai   : 5 business days")
print(f"{'='*60}\n")

# Envoi via SendGrid
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
if not SENDGRID_API_KEY:
    print("❌ SENDGRID_API_KEY absente. STOP.")
    raise SystemExit(1)

import requests
sg_payload = {
    "personalizations": [{
        "to": [{"email": RECIPIENT_EMAIL, "name": RECIPIENT_NAME}],
    }],
    "from": {"email": SENDER_EMAIL, "name": SENDER_NAME},
    "subject": f"Capital Norvex — Refinancing Application (CNV-2026-59109)",
    "content": [{"type": "text/html", "value": full_html}],
}
r = requests.post(
    "https://api.sendgrid.com/v3/mail/send",
    headers={
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    },
    json=sg_payload,
    timeout=30,
)
if r.status_code in (200, 202):
    print(f"✅ ENVOYÉ via SendGrid (HTTP {r.status_code})")
    # Audit log
    try:
        from agents.shared.firestore_client import audit_log, db, now_utc
        audit_log(
            agent="manual_send_henri_petit_letter",
            action="pre_engagement_letter_sent",
            target_type="dossiers",
            target_id=DOSSIER_ID,
            details={
                "to": RECIPIENT_EMAIL,
                "subject": f"Capital Norvex — Refinancing Application ({DOSSIER_ID})",
                "uploadToken": UPLOAD_TOKEN,
                "deadline": "5 business days",
                "indicativeAmount": final_amount,
                "indicativeRate": final_rate,
            },
        )
        # Patch dossier
        db().collection('dossiers').document(DOSSIER_ID).update({
            'preEngagementLetterSentAt': now_utc().isoformat(),
            'preEngagementLetterSentTo': RECIPIENT_EMAIL,
            'uploadTokenActive': UPLOAD_TOKEN,
            'docsDeadlineBusinessDays': 5,
        })
        print("✅ Audit log + dossier patché")
    except Exception as e:
        print(f"⚠️  Audit/patch a échoué (mais email parti) : {e}")
else:
    print(f"❌ Échec envoi : HTTP {r.status_code}")
    print(r.text[:500])
