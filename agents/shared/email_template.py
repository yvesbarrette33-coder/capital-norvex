"""Template HTML 'Variation A — Maison Crème' pour tous les courriels.

Specs v2 (institutionnel premium, FR + EN):
- Fond crème ivoire (#F5EFE0)
- Bandeau noir en-tête (#0A0A0A) avec logo Norvex officiel
- Tagline doré sous logo "Capital structuré. Ambition maîtrisée."
- Filet doré décoratif entre header et corps
- Surtitre "CONFIDENTIEL — Préparé pour [Nom]" optionnel
- Texte serif Georgia, 13.5px, line-height 1.85
- Date en italique aligné droite
- Boutons CTA stylés (or sur noir) optionnels
- Signature image (Yves) ou texte de fallback
- Pied de page noir avec coordonnées en or

Logo officiel: assets/logo-norvex-officiel.png — encodé en base64 inline.
JAMAIS recréé en SVG (R-BRAND-1).
"""
from __future__ import annotations

import base64
import os
from datetime import datetime
from typing import List, Optional

# Couleurs officielles Capital Norvex
COLOR_CREAM = "#FBF7EB"
COLOR_INK = "#0A0A0A"
COLOR_GOLD = "#C8B070"
COLOR_GOLD_DARK = "#9A8554"

# Adresse officielle (modifiable via env)
COMPANY_NAME = "Capital Norvex Inc."
COMPANY_TAGLINE = "Capital structuré. Ambition maîtrisée."
COMPANY_TAGLINE_EN = "Structured capital. Measured ambition."

COMPANY_ADDRESS_LINES = [
    "2705-1000 André-Prévost",
    "Île-des-Sœurs (Verdun)",
    "Montréal, QC H3E 0G2",
]

# Téléphone via env. Format vanity Yves 2026-05-04 : « 438-533-PRÊT (7738) »
COMPANY_PHONE = os.environ.get("CAPITAL_NORVEX_PHONE", "438-533-PRÊT (7738)")
COMPANY_PHONE_TEL_HREF = "+14385337738"  # Format href tel: (digits seulement)
COMPANY_EMAIL = os.environ.get("CAPITAL_NORVEX_EMAIL", "info@capitalnorvex.com")
COMPANY_WEB = "capitalnorvex.com"

# Titre signature (Yves a confirmé : Directeur-fondateur)
DEFAULT_SIGNATURE_TITLE_FR = "Directeur-fondateur"
DEFAULT_SIGNATURE_TITLE_EN = "Founder & Director"
DEFAULT_SIGNATURE_NAME = "Yves Barrette"


def _logo_data_uri() -> str:
    """Charge le logo officiel et retourne un data:URI base64."""
    path = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "assets", "logo-norvex-officiel.png",
    )
    path = os.path.abspath(path)
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _signature_data_uri() -> str:
    """Charge la signature manuscrite Yves si disponible."""
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "Signature Yves.png"),
    ]
    for p in candidates:
        p = os.path.abspath(p)
        if os.path.exists(p):
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            return f"data:image/png;base64,{b64}"
    return ""


def cta_button(label: str, url: str, sublabel: Optional[str] = None) -> str:
    """Helper: génère un bouton CTA premium (or sur noir).

    Utilisable depuis le body_html des templates.
    """
    sub = (
        f'<div style="font-size:10px;letter-spacing:3px;text-transform:uppercase;'
        f'color:{COLOR_GOLD_DARK};margin-bottom:6px;">{sublabel}</div>'
        if sublabel else ""
    )
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px auto;">
      <tr><td style="background:{COLOR_INK};border:1px solid {COLOR_GOLD};">
        <a href="{url}"
           style="display:block;padding:18px 36px;color:{COLOR_GOLD};
                  text-decoration:none;font-family:Georgia,serif;
                  font-size:15px;letter-spacing:1.5px;text-align:center;">
          {sub}
          <div style="color:#fff;font-size:15px;letter-spacing:1px;">{label} &rarr;</div>
        </a>
      </td></tr>
    </table>"""


def gold_rule() -> str:
    """Helper: filet doré décoratif horizontal."""
    return (
        f'<div style="margin:24px auto;width:80px;height:1px;'
        f'background:{COLOR_GOLD};"></div>'
    )


def info_box(content_html: str, title: Optional[str] = None) -> str:
    """Helper: boîte d'information avec filet doré gauche."""
    title_html = (
        f'<div style="font-size:10px;letter-spacing:2.5px;text-transform:uppercase;'
        f'color:{COLOR_GOLD_DARK};margin-bottom:10px;">{title}</div>'
        if title else ""
    )
    return f"""
    <div style="margin:20px 0;padding:18px 22px;background:#FAF6EA;
                border-left:3px solid {COLOR_GOLD};">
      {title_html}
      <div style="font-size:13px;line-height:1.7;color:#3a3a3a;">
        {content_html}
      </div>
    </div>"""


def feature_list(items: List[str]) -> str:
    """Helper: liste à puces premium pour énumérer fonctionnalités."""
    items_html = "".join(
        f'<li style="margin:8px 0;padding-left:0;">'
        f'<span style="color:{COLOR_GOLD};margin-right:10px;">&diams;</span>'
        f'{item}</li>'
        for item in items
    )
    return (
        f'<ul style="list-style:none;padding:0;margin:14px 0;">'
        f'{items_html}</ul>'
    )


def video_block(
    youtube_id: str,
    label: str = "Voir la vidéo de présentation",
    duration: Optional[str] = None,
    lang: str = "fr",
) -> str:
    """Helper: bandeau capsule vidéo DISCRET (sans grosse thumbnail YouTube).

    Décision Yves 2026-05-12 matin : retirer la grosse image YouTube
    (hqdefault.jpg) qui prenait trop d'espace dans l'email. Garder juste
    un bandeau noir/or discret cliquable qui mène à la page capsule brandée
    capitalnorvex.com/capsule?v=... où le destinataire choisit play vidéo
    ou exploration du site.

    Décision Yves 2026-05-08 : le lien pointe vers une page hostée sur
    capitalnorvex.com (pas youtu.be directement).
    Bug fix Yves 2026-05-08 PM : ajout `&lang=en` quand l'email est anglais
    pour que la page capsule s'affiche en anglais.
    """
    lang_param = "&lang=en" if lang == "en" else ""
    href = f"https://capitalnorvex.com/capsule?v={youtube_id}{lang_param}"
    dur = f' &middot; {duration}' if duration else ""
    kicker = "Personal capsule" if lang == "en" else "Capsule personnelle"
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:22px auto;max-width:480px;width:100%;">
      <tr><td style="background:{COLOR_INK};border:1px solid {COLOR_GOLD};">
        <a href="{href}" style="display:block;padding:16px 20px;text-decoration:none;font-family:Georgia,serif;text-align:center;">
          <div style="font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#9A8554;margin-bottom:4px;">{kicker}</div>
          <div style="color:{COLOR_GOLD};font-size:14px;letter-spacing:1px;">
            <span style="font-size:15px;">&#9654;</span>&nbsp;&nbsp;{label}{dur} &nbsp;&rarr;
          </div>
        </a>
      </td></tr>
    </table>"""


def render_variation_a(
    body_html: str,
    recipient_name: Optional[str] = None,
    title_line: Optional[str] = None,
    confidential_for: Optional[str] = None,
    date_str: Optional[str] = None,
    show_signature: bool = True,
    signature_title: Optional[str] = None,
    signature_name: Optional[str] = None,
    use_image_signature: bool = True,
    lang: str = "fr",
) -> str:
    """Rend un courriel HTML complet en style Variation A premium.

    Args:
        body_html: contenu central inséré tel quel
        recipient_name: pour la salutation ("Bonjour X," ou "Hello X,")
        title_line: surtitre italique sous le bandeau
        confidential_for: surtitre "CONFIDENTIAL — Prepared for X" en or
        date_str: date custom, sinon date du jour en FR/EN
        show_signature: inclure bloc signature
        signature_title: titre signature (sinon défaut selon langue)
        signature_name: nom signature (sinon "Yves Barrette")
        use_image_signature: True = utilise image manuscrite Yves si dispo.
            False = force le bloc texte (utiliser pour outreach équipe ou
            personas non-Yves). Décision Yves 2026-05-04 : courtiers/promoteurs
            doivent être signés « L'équipe Capital Norvex », pas Yves perso.
        lang: 'fr' (défaut) ou 'en'
    """
    is_en = lang == "en"

    # Date
    if date_str is None:
        try:
            import locale
            try:
                locale.setlocale(
                    locale.LC_TIME,
                    "en_CA.UTF-8" if is_en else "fr_CA.UTF-8",
                )
            except locale.Error:
                pass
        except Exception:
            pass
        date_str = datetime.now().strftime("%B %d, %Y" if is_en else "%d %B %Y")

    # Logo + tagline
    logo_uri = _logo_data_uri()
    # Image manuscrite Yves chargée seulement si demandée explicitement.
    sig_uri = _signature_data_uri() if (show_signature and use_image_signature) else ""
    tagline = COMPANY_TAGLINE_EN if is_en else COMPANY_TAGLINE

    if logo_uri:
        logo_block = (
            f'<img src="{logo_uri}" alt="Capital Norvex" '
            f'style="max-width:200px;height:auto;display:block;margin:0 auto;">'
            f'<div style="margin-top:14px;color:{COLOR_GOLD};'
            f'font-family:Georgia,serif;font-style:italic;font-size:12px;'
            f'letter-spacing:1.5px;">{tagline}</div>'
        )
    else:
        logo_block = (
            f'<div style="color:{COLOR_GOLD};font-family:Georgia,serif;'
            f'font-size:22px;letter-spacing:2px;">CAPITAL NORVEX</div>'
            f'<div style="margin-top:8px;color:{COLOR_GOLD};'
            f'font-family:Georgia,serif;font-style:italic;font-size:12px;'
            f'letter-spacing:1.5px;">{tagline}</div>'
        )

    # Surtitre confidentiel
    confidential_block = ""
    if confidential_for:
        prefix = "CONFIDENTIAL — PREPARED FOR" if is_en else "CONFIDENTIEL — PRÉPARÉ POUR"
        confidential_block = (
            f'<tr><td style="padding:18px 36px 0 36px;text-align:center;">'
            f'<div style="font-size:10px;letter-spacing:3px;color:{COLOR_GOLD_DARK};'
            f'font-family:Georgia,serif;">{prefix}</div>'
            f'<div style="font-family:Georgia,serif;font-size:15px;'
            f'color:{COLOR_INK};margin-top:6px;letter-spacing:1px;">'
            f'{confidential_for}</div></td></tr>'
        )

    # Salutation — détecte les noms génériques pour éviter "Hello à identifier,"
    salut_word = "Hello" if is_en else "Bonjour"
    _name_clean = (recipient_name or "").strip().strip("()").strip().lower()
    # Substrings dangereuses (très spécifiques pour éviter false positives sur vrais noms)
    _generic_substrings = (
        "à identifier", "a identifier", "to identify",
        "à confirmer", "a confirmer", "to confirm",
        "leadership team", "management team", "équipe de direction",
    )
    # Match exact seulement (le nom au complet est juste ce mot)
    _generic_exact = {
        "", "?", "—", "-", "n/a", "na", "tbd",
        "direction", "leadership", "team", "équipe", "equipe",
        "owner", "founder", "ceo", "president", "président",
    }
    _is_generic = (
        _name_clean in _generic_exact
        or any(m in _name_clean for m in _generic_substrings)
        or len(_name_clean) < 3
    )
    if recipient_name and not _is_generic:
        salutation = f"<p style=\"margin:0 0 18px 0;\">{salut_word} {recipient_name},</p>"
    else:
        # Formulation polie sans nom
        salutation = f"<p style=\"margin:0 0 18px 0;\">{salut_word},</p>"

    # Titre italique
    title_block = (
        f'<p style="text-align:center;font-style:italic;color:{COLOR_GOLD_DARK};'
        f'font-size:14px;margin:24px 0 8px 0;">{title_line}</p>'
        if title_line
        else ""
    )

    # Signature
    sig_title = signature_title or (
        DEFAULT_SIGNATURE_TITLE_EN if is_en else DEFAULT_SIGNATURE_TITLE_FR
    )
    sig_name = signature_name or DEFAULT_SIGNATURE_NAME

    signature_html = ""
    if show_signature:
        if sig_uri:
            signature_html = (
                f'<div style="margin-top:36px;">'
                f'<img src="{sig_uri}" alt="{sig_name}" '
                f'style="max-width:220px;height:auto;display:block;">'
                f'</div>'
            )
        else:
            signature_html = (
                f'<div style="margin-top:36px;font-family:Georgia,serif;'
                f'font-size:13.5px;line-height:1.6;">'
                f'<strong>{sig_name}</strong><br>'
                f'<em style="color:#666;">{sig_title}</em><br>'
                f'<span style="color:#666;">{COMPANY_NAME}</span>'
                f'</div>'
            )

    # Pied de page
    addr_html = "<br>".join(COMPANY_ADDRESS_LINES)
    phone_label = "Tel." if is_en else "Tél."

    # Filet doré entre bandeau et corps
    gold_separator = (
        f'<tr><td style="height:3px;background:linear-gradient('
        f'90deg, transparent 0%, {COLOR_GOLD} 50%, transparent 100%);"></td></tr>'
    )

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Capital Norvex</title>
</head>
<body style="margin:0;padding:0;background:{COLOR_CREAM};
  font-family:Georgia,'Times New Roman',serif;color:{COLOR_INK};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background:{COLOR_CREAM};">
    <tr>
      <td align="center" style="padding:0;">
        <table role="presentation" width="640" cellpadding="0" cellspacing="0"
               style="max-width:640px;width:100%;background:{COLOR_CREAM};">

          <!-- BANDEAU NOIR EN-TÊTE -->
          <tr>
            <td style="background:{COLOR_INK};padding:32px 24px 28px 24px;text-align:center;">
              {logo_block}
            </td>
          </tr>

          <!-- FILET DORÉ DÉCORATIF -->
          {gold_separator}

          <!-- SURTITRE CONFIDENTIEL -->
          {confidential_block}

          <!-- TITRE OPTIONNEL -->
          {f'<tr><td style="padding:0 36px;">{title_block}</td></tr>' if title_block else ''}

          <!-- DATE -->
          <tr>
            <td style="padding:24px 36px 0 36px;text-align:right;
                       font-style:italic;font-size:13px;color:#555;">
              {date_str}
            </td>
          </tr>

          <!-- CORPS DE LETTRE -->
          <tr>
            <td style="padding:18px 36px 36px 36px;font-family:Georgia,serif;
                       font-size:13.5px;line-height:1.85;color:{COLOR_INK};">
              {salutation}
              {body_html}
              {signature_html}
            </td>
          </tr>

          <!-- PIED NOIR -->
          <tr>
            <td style="background:{COLOR_INK};padding:24px 36px;text-align:center;
                       font-family:Georgia,serif;font-size:11.5px;
                       line-height:1.7;color:{COLOR_GOLD};">
              <strong style="letter-spacing:1.5px;">{COMPANY_NAME}</strong><br>
              <span style="font-family:Arial,Helvetica,sans-serif;font-variant-numeric:tabular-nums lining-nums;font-size:11px;">{addr_html}</span><br>
              <span style="font-family:Arial,Helvetica,sans-serif;font-variant-numeric:tabular-nums lining-nums;font-size:11px;">{phone_label} : {COMPANY_PHONE} &nbsp;·&nbsp; {COMPANY_EMAIL}</span><br>
              <span style="color:#888;font-family:Arial,Helvetica,sans-serif;font-variant-numeric:tabular-nums lining-nums;">{COMPANY_WEB}</span>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
