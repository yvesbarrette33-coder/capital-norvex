"""Génère un aperçu HTML local des 3 templates (FR + EN) pour révision visuelle.

Usage:
    cd ~/Desktop/capitalnorvex-site
    python3 preview_templates.py
    open previews/index.html
"""
from __future__ import annotations

import os
import sys

# Ajoute la racine au sys.path pour les imports `agents.shared`
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from agents.capital.email_template import render_partnership_intro
from agents.shared.email_template import render_variation_a
from agents.promoteurs.email_template import render_project_announcement
from agents.courtiers.email_template import render_cold_outreach

OUT_DIR = os.path.join(ROOT, "previews")
os.makedirs(OUT_DIR, exist_ok=True)


# ─── DONNÉES FICTIVES (mais réalistes) ──────────────────────────────────────

FAKE_PARTNER = {
    "name": "Famille Tremblay",
    "investmentThesis": (
        "Votre engagement de longue date dans la gestion patrimoniale "
        "discrète et structurée s'aligne avec notre approche de "
        "co-financement institutionnel."
    ),
    "approachAngle": (
        "Une rencontre confidentielle de trente minutes pourrait illustrer "
        "concrètement la mécanique de co-financement et la rigueur "
        "opérationnelle de Capital Norvex."
    ),
    "language": "fr",
}

FAKE_RESEARCH = {
    "facts": [
        {
            "fact": "Votre family office privilégie depuis dix ans une "
                    "exposition immobilière à durée définie, alignée sur "
                    "des actifs collatéralisés de premier rang."
        }
    ]
}

FAKE_PROMOTER = {
    "name": "Jean-François Beaulieu",
    "companyName": "Groupe Beaulieu Immobilier",
    "language": "fr",
}

FAKE_PROJECT = {
    "name": "Tour Beaulieu — 142 unités locatives haut de gamme",
}

FAKE_BROKER = {
    "name": "Marie-Claude Dion",
    "agency": "Multi-Prêts Hypothèques",
    "language": "fr",
}


# ─── GÉNÉRATION ─────────────────────────────────────────────────────────────

def _capital_html(lang: str) -> str:
    """Aperçu lettre Partenaire Capital — utilise l'unique render_partnership_intro."""
    target = {
        "name": "Famille Tremblay",
        "organization": "Tremblay Family Office",
        "title": "Direction patrimoniale",
        "investmentThesis": FAKE_PARTNER.get("investmentThesis"),
        "approachAngle": FAKE_PARTNER.get("approachAngle"),
        "language": lang,
    }
    return render_partnership_intro(target, lang=lang, target_id="preview-target-id")


def _promoter_html(lang: str) -> str:
    promoter = dict(FAKE_PROMOTER, language=lang)
    if lang == "en":
        promoter["name"] = "John Beaulieu"
        promoter["companyName"] = "Beaulieu Real Estate Group"
    project = dict(FAKE_PROJECT)
    if lang == "en":
        project["name"] = "Beaulieu Tower — 142 high-end rental units"
    return render_project_announcement(promoter, project, lang=lang)


def _broker_html(lang: str) -> str:
    broker = dict(FAKE_BROKER, language=lang)
    if lang == "en":
        broker["name"] = "Mary Dion"
        broker["agency"] = "Multi-Prêts Mortgages"
    return render_cold_outreach(broker, lang=lang)


PREVIEWS = [
    ("01-partenaires-fr.html", "Partenaires (FR)", _capital_html, "fr"),
    ("02-partenaires-en.html", "Partners (EN)", _capital_html, "en"),
    ("03-promoteurs-fr.html", "Promoteurs (FR)", _promoter_html, "fr"),
    ("04-promoteurs-en.html", "Developers (EN)", _promoter_html, "en"),
    ("05-courtiers-fr.html", "Courtiers (FR)", _broker_html, "fr"),
    ("06-courtiers-en.html", "Brokers (EN)", _broker_html, "en"),
]


def main():
    index_links = []
    for filename, label, fn, lang in PREVIEWS:
        path = os.path.join(OUT_DIR, filename)
        html = fn(lang)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  ✓ {label:25}  →  {path}")
        index_links.append((filename, label))

    # Index chic, crème pâle, esprit institutionnel premium
    cards = ""
    for filename, label in index_links:
        cards += f"""
        <a href="{filename}" class="card">
          <div class="card-label">{label}</div>
          <div class="card-arrow">&rarr;</div>
        </a>
"""

    index_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aperçus — Capital Norvex</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 60px 24px 80px 24px;
    background: #FBF7EB;
    font-family: Georgia, 'Times New Roman', serif;
    color: #0A0A0A;
    min-height: 100vh;
  }}
  .container {{
    max-width: 720px;
    margin: 0 auto;
  }}
  .header {{
    text-align: center;
    padding: 36px 24px 32px 24px;
    background: #0A0A0A;
    color: #C8B070;
    border-radius: 2px;
    margin-bottom: 0;
    box-shadow: 0 1px 0 rgba(200,176,112,0.4);
  }}
  .brand {{
    font-size: 26px;
    letter-spacing: 8px;
    color: #C8B070;
    font-weight: normal;
    margin: 0;
  }}
  .tagline {{
    font-style: italic;
    font-size: 12.5px;
    letter-spacing: 2px;
    color: #C8B070;
    margin-top: 10px;
    opacity: 0.85;
  }}
  .gold-rule {{
    height: 2px;
    background: linear-gradient(90deg,
      transparent 0%, #C8B070 50%, transparent 100%);
    margin: 0;
  }}
  .body-card {{
    background: #FCF8EE;
    padding: 50px 50px 60px 50px;
    border: 1px solid rgba(200,176,112,0.25);
    border-top: none;
  }}
  .surtitle {{
    text-align: center;
    font-size: 11px;
    letter-spacing: 4px;
    color: #9A8554;
    text-transform: uppercase;
    margin-bottom: 12px;
  }}
  h1 {{
    text-align: center;
    font-size: 22px;
    font-weight: normal;
    margin: 0 0 14px 0;
    letter-spacing: 1.5px;
    color: #0A0A0A;
  }}
  .intro {{
    text-align: center;
    color: #555;
    font-size: 13.5px;
    line-height: 1.7;
    margin: 0 auto 36px auto;
    max-width: 480px;
    font-style: italic;
  }}
  .divider {{
    width: 60px;
    height: 1px;
    background: #C8B070;
    margin: 0 auto 36px auto;
  }}
  .cards {{
    display: flex;
    flex-direction: column;
    gap: 14px;
  }}
  .card {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 22px 28px;
    background: #FFFFFF;
    border: 1px solid #E8DFC4;
    border-left: 3px solid #C8B070;
    text-decoration: none;
    color: #0A0A0A;
    transition: all 0.25s ease;
  }}
  .card:hover {{
    background: #FAF4E2;
    border-left-width: 5px;
    transform: translateX(2px);
  }}
  .card-label {{
    font-size: 14.5px;
    letter-spacing: 1.5px;
    font-weight: bold;
  }}
  .card-arrow {{
    color: #9A8554;
    font-size: 18px;
    transition: transform 0.25s ease;
  }}
  .card:hover .card-arrow {{
    transform: translateX(4px);
    color: #C8B070;
  }}
  .footer {{
    text-align: center;
    padding: 24px 24px 0 24px;
    margin-top: 40px;
    color: #9A8554;
    font-size: 11px;
    letter-spacing: 1.5px;
    border-top: 1px solid #E8DFC4;
    font-style: italic;
  }}
  .footer-note {{
    color: #777;
    font-size: 11.5px;
    line-height: 1.6;
    margin-top: 12px;
    font-style: normal;
    letter-spacing: normal;
  }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="brand">CAPITAL NORVEX</div>
      <div class="tagline">Capital structuré. Ambition maîtrisée.</div>
    </div>
    <div class="gold-rule"></div>
    <div class="body-card">
      <div class="surtitle">Norvex Agents&trade; · Aperçus internes</div>
      <h1>Trois lettres. Trois audiences.</h1>
      <p class="intro">
        Ces aperçus présentent le rendu final des courriels destinés
        aux Partenaires en capital, aux Promoteurs et aux Courtiers
        hypothécaires — en français et en anglais.
      </p>
      <div class="divider"></div>
      <div class="cards">{cards}      </div>
      <div class="footer">
        Confidentiel — pour révision interne
        <p class="footer-note">
          Données fictives utilisées pour la prévisualisation.
          Les véritables cibles sont gérées dans Firestore
          (<code>capitalTargets</code>, <code>promoteurTargets</code>,
          <code>brokerTargets</code>).
        </p>
      </div>
    </div>
  </div>
</body>
</html>"""
    index_path = os.path.join(OUT_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"\n✅ Index généré: {index_path}")
    print(f"\nOuvre-le avec:\n  open {index_path}\n")


if __name__ == "__main__":
    main()
