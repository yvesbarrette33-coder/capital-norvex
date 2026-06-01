"""
Lettre client Henri Petit — VERSION FR pour validation Yves.

⚠️ RÈGLES STRICTES :
- JAMAIS « approuvé » / « approbation » avant signature finale.
- Ton confraternel (Henri = ami personnel + avocat 35 ans).
- Reconnaître : terrain a de la valeur, mais pas de cash flow présentement,
  charge 8M$ existante, montant ajusté.
- Liste correctifs avec raison brève.
"""
import json
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/.capitalnorvex/.env'))

import anthropic

OUT = Path("/tmp/norvex-test")
analysis = json.loads((OUT / "analysis.json").read_text(encoding="utf-8"))

UPLOAD_LINK_PLACEHOLDER = "https://capitalnorvex.com/upload.html?t=TOKEN_À_GÉNÉRER"

docs_manquants = analysis.get("documentsPrimordiauxManquants", []) or []
obligatoires = [dm for dm in docs_manquants if isinstance(dm, dict) and (dm.get("criticite") or "").upper() == "OBLIGATOIRE"]
utiles = [dm for dm in docs_manquants if isinstance(dm, dict) and (dm.get("criticite") or "").upper() == "UTILE"]
conditions = analysis.get("finalConditions", []) or []
final_amount = analysis.get("finalAmount") or 20_000_000
final_rate = analysis.get("finalRate") or 11.5

system = f"""Tu es Yves Barrette, fondateur de Capital Norvex Inc. Tu écris à Henri Petit (NTA Development Corporation), un avocat de 35 ans de carrière qui est aussi ton ami personnel. Henri a soumis une demande de refinancement de 27,5 M$ pour le terrain de 6485 14th Line à Alliston, Ontario.

CONTEXTE BUSINESS À RECONNAÎTRE :
- Terrain de développement potentiellement valorisable
- Charge hypothécaire actuelle de ~8 M$ (9360-8024 Québec Inc.)
- Pas de cash flow présentement (terrain vacant, en attente de zonage/permis)
- Stratégie de sortie = vente ou refi long terme une fois zonage obtenu
- Borrower = NTA Development Corporation (entité d'Henri)

RÈGLES ABSOLUES POUR LA LETTRE — PRÉ-ENGAGEMENT :

⚠️ CETTE LETTRE EST PRÉ-LETTRE D'ENGAGEMENT. AUCUNE OFFRE FORMELLE. JUSTE INTÉRÊT ET DEMANDE DE COMPLÉTER LE DOSSIER.
   L'engagement formel viendra UNIQUEMENT à la « lettre d'engagement » signée plus tard, et même là, avec des portes de sortie (conditions résolutoires).

1. ❌ INTERDIT TOTAL : « approuvé », « approbation », « accordé », « offrir », « nous offrons », « nous accordons », « financement approuvé ».
2. ❌ INTERDIT : promesse de taux ou de montant. AUCUN engagement écrit.
3. ✅ FORMULATIONS PERMISES :
   - « Capital Norvex pourrait considérer un financement... sous réserve de... »
   - « Sur la base d'une revue préliminaire, nous serions disposés à examiner un financement pouvant atteindre... »
   - « Cette indication demeure indicative et ne constitue ni une offre ni un engagement »
   - « La poursuite de la démarche dépend de la production des documents listés ci-dessous et de la confirmation de notre Comité de crédit »
   - « Les paramètres définitifs seraient le cas échéant établis dans une lettre d'engagement formelle »
4. Ton CONFRATERNEL (Henri est ton ami) mais structure INSTITUTIONNELLE.
5. Reconnaître qualité du terrain SANS s'engager : « le dossier nous intéresse à première vue », « la valeur du terrain semble offrir un coussin pertinent ».
6. Mentionner les paramètres INDICATIFS (jusqu'à 20 M$, taux ~11-12 %, terme à valider) en les qualifiant clairement de PRÉLIMINAIRES, NON-LIANTS.
7. Liste des documents manquants OBLIGATOIRES avec raison brève (1 ligne) en français.
8. Délai de 14 jours ouvrables pour fournir les documents.
9. Lien upload portail à inclure (placeholder : {UPLOAD_LINK_PLACEHOLDER}).
10. Pas de « Maître Petit » (Henri est borrower ici, pas conseiller juridique). « Cher Henri » ou « Monsieur Petit » selon ton.
11. Signature : Yves Barrette, Fondateur, Capital Norvex Inc.
12. Disclaimer obligatoire en fin de lettre :
    « La présente correspondance constitue une expression d'intérêt préliminaire. Elle ne lie pas Capital Norvex et ne constitue ni une offre, ni un engagement de prêt. Tout engagement formel de Capital Norvex ne pourra prendre effet qu'à la signature d'une lettre d'engagement écrite, laquelle pourra contenir ses propres conditions résolutoires. »

OUTPUT : Uniquement le HTML body de la lettre (PAS <html>, <body>, <head>). Utilise <p>, <ul>, <strong>, <em>. Style sobre Georgia serif. Ne mentionne PAS « approuvé » nulle part.

LANGUE : FRANÇAIS UNIQUEMENT. Pas un mot d'anglais sauf noms propres."""

user = f"""Documents manquants OBLIGATOIRES :
{json.dumps(obligatoires, indent=2, ensure_ascii=False)}

Documents UTILES (mentionner brièvement) :
{json.dumps(utiles, indent=2, ensure_ascii=False)}

Conditions préalables (à mentionner sans détailler — Yves les revoit en RDV) :
{json.dumps(conditions[:3], indent=2, ensure_ascii=False)}

Montant que Norvex peut envisager (sous réserve) : {final_amount} CAD
Taux indicatif : {final_rate} % per annum
Lien upload portail : {UPLOAD_LINK_PLACEHOLDER}

Rédige maintenant la lettre en français, ton confraternel-institutionnel."""

print("🤖 Génération lettre FR pour validation Yves…")
client = anthropic.Anthropic()
resp = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=3500,
    system=system,
    messages=[{"role": "user", "content": user}],
)
body_html = resp.content[0].text.strip()
body_html = body_html.replace("```html", "").replace("```", "").strip()

# Vérification anti-"approuvé"
forbidden = ["approuvé", "approuvée", "approbation", "approuvons", "accordé", "accordée"]
violations = [w for w in forbidden if w.lower() in body_html.lower()]
if violations:
    print(f"⚠️  ATTENTION — mots interdits détectés : {violations}")
    print("    Le texte sera quand même sauvé pour révision Yves.")
else:
    print("✅ Aucun mot interdit (« approuvé » etc.) détecté.")

full_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Capital Norvex — Lettre Henri Petit (FR)</title>
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
  <p>Prêt commercial privé · Québec et Ontario</p>
  <p>2705-1000 André-Prévost, Île-des-Sœurs, Montréal QC H3E 0G2</p>
  <p>438-533-PRÊT (7738) · yves@capitalnorvex.com</p>
</div>

<p class="date">Le 7 mai 2026</p>

<div class="recipient">
  <p><strong>Monsieur Henri Petit</strong><br>
  NTA Development Corporation<br>
  6485 14th Line<br>
  New Tecumseth (Alliston), Ontario</p>
  <p>Courriel : hpetit@ghp.ca</p>
</div>

<p style="margin-bottom: 24px;"><strong>Objet : Demande de refinancement — 6485 14th Line, Alliston (CNV-2026-59109)</strong></p>

<div class="body">
{body_html}
</div>

<div class="cta-box">
  <p style="margin: 0 0 8px 0;"><strong>Lien sécurisé pour le dépôt des documents :</strong></p>
  <p style="margin: 0; font-family: 'DM Mono', monospace; font-size: .9em;"><a href="{UPLOAD_LINK_PLACEHOLDER}">{UPLOAD_LINK_PLACEHOLDER}</a></p>
  <p style="margin: 12px 0 0 0; font-size: .85em; color: #666;"><em>(Le lien définitif sera généré automatiquement à l'envoi de cette lettre — placeholder pour l'instant.)</em></p>
</div>

<p class="meta">⚠️ Test Phase A — version FR pour validation Yves. NON envoyée. Une fois validée, version EN sera générée + lien upload réel + envoi.</p>

</body></html>"""

(OUT / "henri_petit_lettre_fr.html").write_text(full_html, encoding="utf-8")
print(f"\n📄 Lettre FR : {OUT / 'henri_petit_lettre_fr.html'}")
os.system(f"open '{OUT / 'henri_petit_lettre_fr.html'}'")
print("✅ Ouverte dans le navigateur.")
