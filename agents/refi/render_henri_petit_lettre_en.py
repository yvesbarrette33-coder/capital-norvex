"""
Lettre client Henri Petit — VERSION EN, ton institutionnel formel.

⚠️ CONTEXTE :
- Henri est un ami personnel d'Yves
- MAIS il va lire la lettre à son COMITÉ EXÉCUTIF d'une COMPAGNIE PUBLIQUE
- Donc ton FORMEL, vouvoiement institutionnel anglais, distancié
- "Dear Mr. Petit" PAS "Dear Henri"
- Style Bay Street / Stikeman / RBC / BMO Capital Markets
"""
import json
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/.capitalnorvex/.env'))

import anthropic

OUT = Path("/tmp/norvex-test")
analysis = json.loads((OUT / "analysis.json").read_text(encoding="utf-8"))

UPLOAD_LINK_PLACEHOLDER = "https://capitalnorvex.com/upload.html?t=TOKEN_TO_BE_GENERATED"

docs_manquants = analysis.get("documentsPrimordiauxManquants", []) or []
obligatoires = [dm for dm in docs_manquants if isinstance(dm, dict) and (dm.get("criticite") or "").upper() == "OBLIGATOIRE"]
utiles = [dm for dm in docs_manquants if isinstance(dm, dict) and (dm.get("criticite") or "").upper() == "UTILE"]
conditions = analysis.get("finalConditions", []) or []
final_amount = analysis.get("finalAmount") or 20_000_000
final_rate = analysis.get("finalRate") or 11.5

system = f"""You are Yves Barrette, Founder of Capital Norvex Inc. You are writing to Mr. Henri Petit (NTA Development Corporation) regarding a refinancing application of CAD 27.5M for the property at 6485 14th Line, Alliston, Ontario.

CONTEXT — CRITICAL :
- Mr. Petit is your personal friend AND a lawyer of 35 years standing
- HOWEVER, this letter will be presented to the EXECUTIVE COMMITTEE of a PUBLIC COMPANY
- Tone must therefore be STRICTLY INSTITUTIONAL, FORMAL, ARM'S-LENGTH
- "Dear Mr. Petit" — NEVER "Dear Henri"
- Style : Bay Street institutional (Stikeman / RBC Capital Markets / BMO)
- Vocabulary : precise, measured, no familiarity, no warmth that could embarrass him in committee

BUSINESS CONTEXT :
- Development land with potential value
- Existing first mortgage of ~CAD 8M (9360-8024 Québec Inc.)
- No current cash flow (vacant land, awaiting zoning/permits)
- Exit strategy = sale or long-term refi once zoning obtained
- Borrower = NTA Development Corporation

ABSOLUTE RULES — PRE-ENGAGEMENT LETTER :

⚠️ THIS IS A PRE-COMMITMENT LETTER. NO FORMAL OFFER. ONLY EXPRESSION OF INTEREST AND REQUEST FOR FILE COMPLETION.
   Formal commitment will only follow upon a signed Commitment Letter at a later stage, and even then with conditions precedent / resolutoires.

1. ❌ STRICTLY FORBIDDEN : "approved", "approval", "granted", "offered", "we offer", "we extend", "financing approved", "we hereby commit".
2. ❌ FORBIDDEN : firm promise of rate or amount. NO written commitment.
3. ✅ PERMITTED FORMULATIONS :
   - "Capital Norvex would be prepared to consider, on a strictly preliminary and non-binding basis, a financing facility..."
   - "Subject to satisfactory completion of due diligence and the formal approval of our Credit Committee..."
   - "The indicative parameters set out below are non-binding and subject to revision..."
   - "Should the file proceed, definitive terms would be set forth in a formal Commitment Letter..."
   - "This letter does not constitute an offer, a commitment to lend, or a binding term sheet."
4. Tone STRICTLY institutional — no first names, no warmth, no informality.
5. Acknowledge file quality WITHOUT committing : "The file presents elements of interest at first review", "the underlying property appears to provide a meaningful collateral cushion".
6. Mention INDICATIVE parameters (up to CAD 20M, indicative rate 11-12%, term to be confirmed) — clearly qualified as PRELIMINARY, NON-BINDING.
7. List of MANDATORY missing documents with one-line rationale each, in English.
8. Deadline of 14 business days for submission.
9. Upload link to include (placeholder : {UPLOAD_LINK_PLACEHOLDER}).
10. Salutation : "Dear Mr. Petit," — NEVER "Dear Henri".
11. Signoff : "With consideration," — NOT "Best regards," NOT "Sincerely yours,".
12. Signature : "Yves Barrette, Founder, Capital Norvex Inc."
13. Mandatory disclaimer at end of letter :
    "This correspondence constitutes a preliminary expression of interest. It does not bind Capital Norvex and does not constitute an offer, a term sheet, or a commitment to lend. Any formal commitment of Capital Norvex would only take effect upon execution of a written Commitment Letter, which may include its own conditions precedent or resolutoires."

OUTPUT : Only the HTML body of the letter (NO <html>, <body>, <head>). Use <p>, <ul>, <strong>, <em>. Sober Georgia serif style. Never use the word "approved" anywhere.

LANGUAGE : ENGLISH ONLY. No French except proper names."""

user = f"""MANDATORY missing documents :
{json.dumps(obligatoires, indent=2, ensure_ascii=False)}

USEFUL documents (briefly mention) :
{json.dumps(utiles, indent=2, ensure_ascii=False)}

Conditions precedent (mention without detailing — Yves to review at meeting) :
{json.dumps(conditions[:3], indent=2, ensure_ascii=False)}

Indicative amount Norvex could consider : CAD {final_amount}
Indicative rate : {final_rate}% per annum
Upload portal link : {UPLOAD_LINK_PLACEHOLDER}

Draft the letter now in formal institutional English. Strict arm's-length tone — Mr. Petit will read this to his Executive Committee."""

print("🤖 Génération lettre EN (ton Bay Street formel)…")
client = anthropic.Anthropic()
resp = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=3500,
    system=system,
    messages=[{"role": "user", "content": user}],
)
body_html = resp.content[0].text.strip()
body_html = body_html.replace("```html", "").replace("```", "").strip()

# Vérification anti-mots-interdits (EN)
forbidden_en = ["approved", "approval", "granted", "we offer", "we extend",
                "we commit", "hereby grant", "we accord"]
forbidden_fr = ["approuvé", "approuvée", "approbation"]
violations = [w for w in forbidden_en + forbidden_fr if w.lower() in body_html.lower()]
if violations:
    print(f"⚠️  ATTENTION — mots interdits détectés : {violations}")
else:
    print("✅ Aucun mot interdit détecté.")

# Check anti-warmth ("Dear Henri" etc.)
informal = ["dear henri", "hi henri", "hello henri", "dear friend"]
informal_violations = [w for w in informal if w.lower() in body_html.lower()]
if informal_violations:
    print(f"⚠️  TON TROP FAMILIER détecté : {informal_violations}")
else:
    print("✅ Ton institutionnel respecté (pas de 'Dear Henri').")

full_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Capital Norvex — Letter to Mr. Petit (EN)</title>
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
.cta-box a {{ color: #9A8554; font-weight: 700; text-decoration: none; }}
.signoff {{ margin-top: 42px; }}
.meta {{ color: #999; font-size: .8em; font-style: italic; margin-top: 50px; border-top: 1px solid #eee; padding-top: 12px; }}
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
  <p style="margin: 0; font-family: 'DM Mono', monospace; font-size: .9em;"><a href="{UPLOAD_LINK_PLACEHOLDER}">{UPLOAD_LINK_PLACEHOLDER}</a></p>
  <p style="margin: 12px 0 0 0; font-size: .85em; color: #666;"><em>(Final secure link will be generated upon dispatch — placeholder for now.)</em></p>
</div>

<p class="meta">⚠️ Test Phase A — formal EN version for Yves' validation. NOT yet sent. Once approved, real upload token will be generated and dispatched.</p>

</body></html>"""

(OUT / "henri_petit_lettre_en.html").write_text(full_html, encoding="utf-8")
print(f"\n📄 Lettre EN : {OUT / 'henri_petit_lettre_en.html'}")
os.system(f"open '{OUT / 'henri_petit_lettre_en.html'}'")
print("✅ Ouverte dans le navigateur.")
