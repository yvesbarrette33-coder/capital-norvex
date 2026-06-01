"""Bloc signature email institutionnel unifié — Capital Norvex Inc.

Décision Yves 2026-05-04 : TOUTES les signatures email (Yves, Suzanne, Sophie,
Camille, futurs Karine/Hugo) doivent partager le MÊME design pour cohérence
institutionnelle. Disparité = pas professionnel.

Design :
    ┌────────────────────────────────────────────┐
    │ BANDEAU NOIR (#0A0A0A)                     │
    │   [Logo M doré centré]                     │
    │   Tagline doré (italique)                  │
    └────────────────────────────────────────────┘
    [Filet doré décoratif]

    Nom (gras)
    Titre (italique gris)
    NORVEX [SUFFIX]™ — Capital Norvex Inc.
    Adresse complète (3 lignes)
    Tél · Email · Web

    [Phrase confidentialité protective italique gris pâle]
    [Disclaimer spécifique persona si applicable]

Usage :
    from agents.shared.signature_block import build_signature_block

    html = build_signature_block(
        name="Yves Barrette",
        title="Fondateur",
        suffix=None,                  # ou "COUNSEL", "RELATIONS", etc.
        email="yves@capitalnorvex.com",
        show_phone=True,              # Yves/Suzanne = True, agents IA = False
        ai_disclosure_fr=None,        # ou phrase IA si agent
        bar_disclaimer_fr=None,       # ou disclaimer art. 132 si Camille
        language="fr",
    )
"""
from __future__ import annotations

import base64
import os
from typing import Optional

# Couleurs officielles Capital Norvex (synchro avec email_template.py)
COLOR_INK = "#0A0A0A"
COLOR_GOLD = "#C8B070"
COLOR_GOLD_DARK = "#9A8554"
COLOR_TEXT = "#222"
COLOR_MUTED = "#666"
COLOR_FAINT = "#888"

# Identité (synchro avec email_template.py)
COMPANY_NAME = "Capital Norvex Inc."
COMPANY_TAGLINE_FR = "Capital structuré. Ambition maîtrisée."
COMPANY_TAGLINE_EN = "Structured capital. Measured ambition."
COMPANY_PHONE_DISPLAY_FR = "438-533-PRÊT (7738)"
COMPANY_PHONE_DISPLAY_EN = "+1 (438) 533-PRÊT (7738)"
COMPANY_PHONE_HREF = "+14385337738"
COMPANY_WEB = "capitalnorvex.com"

COMPANY_ADDRESS_LINES = [
    "2705-1000 André-Prévost",
    "Île-des-Sœurs (Verdun)",
    "Montréal, QC H3E 0G2",
]

# Phrases confidentialité protective (Yves 2026-05-04 : « protège à 100% »)
CONFIDENTIALITY_FR = (
    "Ce message et tout document joint sont strictement confidentiels et "
    "destinés exclusivement au destinataire désigné. Toute diffusion, copie, "
    "distribution ou utilisation non autorisée est interdite et peut faire "
    "l'objet de poursuites. Si vous avez reçu ce courriel par erreur, "
    "veuillez le supprimer immédiatement et en aviser l'expéditeur."
)

CONFIDENTIALITY_EN = (
    "This message and any attached documents are strictly confidential and "
    "intended exclusively for the designated recipient. Any unauthorized "
    "disclosure, copying, distribution or use is prohibited and may be "
    "subject to legal action. If you received this email in error, please "
    "delete it immediately and notify the sender."
)


def _logo_data_uri() -> str:
    """Charge le logo M officiel COMPRESSÉ et retourne un data:URI base64.

    🐛 Bug fix 2026-05-05 PM (2e itération) :
    - Avant : logo PNG haute résolution 1.10 MiB → 1.47 MiB base64 → crash Firestore.
    - 1ère tentative : URL hostée → marchait niveau Firestore, MAIS Outlook bloque
      les images externes par défaut → logo invisible jusqu'à clic « Charger les images ».
    - Solution finale : version COMPRESSÉE du logo (`logo-norvex-officiel-mail.png`,
      ~49 KB → 65 KB base64), embed inline. Look strictement identique car le logo
      n'est affiché qu'à 78px de large dans la signature — la compression ne se voit
      pas. S'affiche TOUJOURS dans tous les clients mail.

    Fallback sur le logo original si la version mail n'existe pas.
    """
    base_dir = os.path.dirname(__file__)
    candidates = [
        # Version optimisée pour email (priorité)
        os.path.join(base_dir, "..", "..", "assets", "logo-norvex-officiel-mail.png"),
        # Fallback : version originale haute résolution (utilisé en site web)
        os.path.join(base_dir, "..", "..", "assets", "logo-norvex-officiel.png"),
    ]
    for path in candidates:
        path = os.path.abspath(path)
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    return ""


def _signature_image_data_uri(scan_filename: str) -> str:
    """Charge un scan de signature manuscrite COMPRESSÉ et retourne data:URI base64.

    🐛 Bug fix 2026-05-05 PM (2e itération) :
    - Avant : `Signature Yves.png` original 740 KiB → 990 KiB base64 → crash Firestore.
    - 1ère tentative : URL hostée → bloqué par Outlook (images externes).
    - Solution finale : version COMPRESSÉE (suffix `-mail.png`, ~217 KB → 290 KB base64),
      embed inline. Look identique car affichage limité à 200px max-width.

    Cherche d'abord `<basename>-mail.png` (version compressée), puis fallback sur l'original.
    """
    base_dir = os.path.dirname(__file__)

    # Construit la version "-mail" du nom : ex. "Signature Yves.png" → "Signature Yves-mail.png"
    name_root, ext = os.path.splitext(scan_filename)
    mail_filename = f"{name_root}-mail{ext}"

    candidates = [
        # Version optimisée pour email
        os.path.join(base_dir, "..", "..", mail_filename),
        os.path.join(base_dir, "..", "..", "signatures", mail_filename),
        # Fallback : original haute résolution
        os.path.join(base_dir, "..", "..", scan_filename),
        os.path.join(base_dir, "..", "..", "signatures", scan_filename),
    ]
    for path in candidates:
        path = os.path.abspath(path)
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    return ""


def _header_block(language: str = "fr") -> str:
    """Bandeau noir avec logo M doré + tagline."""
    is_en = language == "en"
    tagline = COMPANY_TAGLINE_EN if is_en else COMPANY_TAGLINE_FR
    logo_uri = _logo_data_uri()

    if logo_uri:
        logo_html = (
            f'<img src="{logo_uri}" alt="Capital Norvex" '
            f'style="max-width:140px;height:auto;display:block;margin:0 auto;">'
        )
    else:
        # Fallback texte si logo manquant
        logo_html = (
            f'<div style="font-family:Georgia,serif;font-size:22px;'
            f'letter-spacing:4px;color:{COLOR_GOLD};font-weight:bold;">'
            f'CAPITAL NORVEX</div>'
        )

    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;width:100%;max-width:560px;">'
        f'<tr><td style="background:{COLOR_INK};padding:18px 24px;text-align:center;">'
        f'{logo_html}'
        f'<div style="margin-top:8px;color:{COLOR_GOLD};font-family:Georgia,serif;'
        f'font-style:italic;font-size:11px;letter-spacing:1.5px;">{tagline}</div>'
        f'</td></tr>'
        # Filet doré décoratif
        f'<tr><td style="height:2px;background:linear-gradient('
        f'90deg, transparent 0%, {COLOR_GOLD} 50%, transparent 100%);"></td></tr>'
        f'</table>'
    )


def build_signature_block(
    *,
    name: str,
    title: str,
    suffix: Optional[str] = None,
    email: str,
    show_phone: bool = False,
    manuscript_scan_filename: Optional[str] = None,
    ai_disclosure: Optional[str] = None,
    bar_disclaimer: Optional[str] = None,
    closing: Optional[str] = None,
    language: str = "fr",
) -> str:
    """Construit le bloc signature unifié Capital Norvex.

    Args:
        name: nom complet (ex. "Yves Barrette", "Camille", "Sophie")
        title: titre (ex. "Fondateur", "Administratrice", "Coordonnatrice juridique")
        suffix: suffixe NORVEX (ex. "COUNSEL", "RELATIONS"). None si Yves/Suzanne.
        email: adresse email à afficher
        show_phone: True pour Yves/Suzanne (humains), False pour agents IA
        manuscript_scan_filename: nom du fichier scan signature (ex. "Signature Yves.png").
            Si fichier existe → affiche image manuscrite au-dessus du bloc texte.
        ai_disclosure: phrase « X est une coordonnatrice IA... » (None si humain)
        bar_disclaimer: disclaimer art. 132 QC (Camille uniquement, sinon None)
        closing: salutation finale (ex. "Cordialement"). None = pas de closing.
        language: 'fr' (défaut) ou 'en'
    """
    is_en = language == "en"

    # Closing optionnel
    closing_html = ""
    if closing:
        closing_html = (
            f'<p style="margin:0 0 16px 0;font-family:Georgia,serif;'
            f'font-size:13.5px;color:{COLOR_TEXT};">{closing},</p>'
        )

    # Image manuscrite optionnelle (Yves principalement, Suzanne si dispo plus tard)
    manuscript_html = ""
    if manuscript_scan_filename:
        sig_uri = _signature_image_data_uri(manuscript_scan_filename)
        if sig_uri:
            manuscript_html = (
                f'<div style="margin-bottom:8px;">'
                f'<img src="{sig_uri}" alt="{name}" '
                f'style="max-width:200px;height:auto;display:block;">'
                f'</div>'
            )

    # Bandeau noir + logo
    header_html = _header_block(language=language)

    # Bloc identité
    company_label = (
        f"NORVEX {suffix}™ — {COMPANY_NAME}" if suffix else COMPANY_NAME
    )
    addr_html = "<br>".join(COMPANY_ADDRESS_LINES)
    phone_display = COMPANY_PHONE_DISPLAY_EN if is_en else COMPANY_PHONE_DISPLAY_FR
    web_label = "Visit" if is_en else "Site web"

    # Ligne contact (tel · email · web)
    contact_parts = []
    if show_phone:
        contact_parts.append(
            f'<a href="tel:{COMPANY_PHONE_HREF}" '
            f'style="color:{COLOR_TEXT};text-decoration:none;">{phone_display}</a>'
        )
    contact_parts.append(
        f'<a href="mailto:{email}" '
        f'style="color:{COLOR_TEXT};text-decoration:none;">{email}</a>'
    )
    contact_parts.append(
        f'<a href="https://{COMPANY_WEB}" '
        f'style="color:{COLOR_TEXT};text-decoration:none;">{COMPANY_WEB}</a>'
    )
    contact_line = ' &nbsp;·&nbsp; '.join(contact_parts)

    identity_html = (
        f'<div style="margin-top:14px;font-family:Georgia,serif;'
        f'font-size:13px;line-height:1.55;color:{COLOR_TEXT};">'
        f'<strong style="font-size:14.5px;">{name}</strong><br>'
        f'<em style="color:{COLOR_MUTED};font-style:italic;">{title}</em><br>'
        f'<span style="color:{COLOR_MUTED};">{company_label}</span><br>'
        f'<span style="color:{COLOR_MUTED};font-size:12.5px;">{addr_html}</span><br>'
        f'<span style="font-size:12.5px;margin-top:4px;display:inline-block;">'
        f'{contact_line}</span>'
        f'</div>'
    )

    # Phrase confidentialité (protective)
    confidentiality = CONFIDENTIALITY_EN if is_en else CONFIDENTIALITY_FR

    # Disclaimers persona-spécifiques
    extras = []
    if ai_disclosure:
        extras.append(ai_disclosure)
    if bar_disclaimer:
        extras.append(bar_disclaimer)

    extras_html = ""
    if extras:
        extras_html = (
            f'<p style="margin:8px 0 0 0;font-family:Arial,sans-serif;'
            f'font-size:11px;line-height:1.5;color:{COLOR_FAINT};font-style:italic;">'
            f'{" ".join(extras)}'
            f'</p>'
        )

    confidentiality_html = (
        f'<p style="margin:14px 0 0 0;font-family:Arial,sans-serif;'
        f'font-size:10.5px;line-height:1.5;color:{COLOR_FAINT};font-style:italic;'
        f'border-top:1px solid #DDD;padding-top:10px;">'
        f'{confidentiality}'
        f'</p>'
    )

    # Assemblage final
    return (
        f'<div style="margin-top:32px;max-width:560px;">'
        f'{closing_html}'
        f'{manuscript_html}'
        f'{header_html}'
        f'<div style="padding:0 4px;">'
        f'{identity_html}'
        f'{extras_html}'
        f'{confidentiality_html}'
        f'</div>'
        f'</div>'
    )


# ─── Style « DARK » — Yves & Suzanne (humains de la direction) ────
# Reproduction du design noir horizontal validé par Yves 2026-05-04 :
# fond noir, logo M doré à gauche, texte (nom + titre + tagline + contacts +
# confidentialité) à droite. Couleurs : noir #0A0A0A + or #C8B070 + blanc cassé.

def build_dark_signature_block(
    *,
    name: str,
    title_main: str,
    title_sub: Optional[str] = None,
    email: str,
    manuscript_scan_filename: Optional[str] = None,
    closing: Optional[str] = None,
    language: str = "fr",
) -> str:
    """Bloc signature ÉLÉGANT fond noir + logo gauche + texte doré à droite.

    Réservé à Yves et Suzanne (la direction humaine). Sophie/Camille utilisent
    build_signature_block() (style clair institutionnel).

    Args:
        name: nom complet (ex. "Yves Barrette")
        title_main: titre principal (ex. "Président")
        title_sub: sous-titre optionnel (ex. "Financement immobilier commercial")
        email: adresse email
        manuscript_scan_filename: scan signature manuscrite (ex. "Signature Yves.png")
        closing: salutation finale (ex. "Cordialement")
        language: 'fr' (défaut) ou 'en'
    """
    is_en = language == "en"
    tagline = COMPANY_TAGLINE_EN if is_en else COMPANY_TAGLINE_FR
    confidentiality = CONFIDENTIALITY_EN if is_en else CONFIDENTIALITY_FR
    phone_display = COMPANY_PHONE_DISPLAY_EN if is_en else COMPANY_PHONE_DISPLAY_FR
    addr_html = "<br>".join(COMPANY_ADDRESS_LINES)
    logo_uri = _logo_data_uri()

    # Closing (au-dessus du bandeau noir, sur fond crème de l'email)
    closing_html = ""
    if closing:
        closing_html = (
            f'<p style="margin:0 0 12px 0;font-family:Georgia,serif;'
            f'font-size:13.5px;color:{COLOR_TEXT};">{closing},</p>'
        )

    # Image manuscrite optionnelle (au-dessus du bandeau noir)
    manuscript_html = ""
    if manuscript_scan_filename:
        sig_uri = _signature_image_data_uri(manuscript_scan_filename)
        if sig_uri:
            manuscript_html = (
                f'<div style="margin-bottom:14px;">'
                f'<img src="{sig_uri}" alt="{name}" '
                f'style="max-width:200px;height:auto;display:block;">'
                f'</div>'
            )

    # Logo gauche (cellule) — Yves 2026-05-04 : version compacte (~30% plus petit)
    if logo_uri:
        logo_cell = (
            f'<td valign="middle" align="center" '
            f'style="width:90px;padding:0 10px 0 4px;background:{COLOR_INK};">'
            f'<img src="{logo_uri}" alt="Capital Norvex" '
            f'style="width:78px;height:auto;display:block;">'
            f'</td>'
        )
    else:
        logo_cell = (
            f'<td valign="middle" align="center" '
            f'style="width:90px;padding:0 10px;background:{COLOR_INK};'
            f'color:{COLOR_GOLD};font-family:Georgia,serif;font-weight:bold;'
            f'font-size:28px;letter-spacing:4px;">M</td>'
        )

    # Sous-titre optionnel
    sub_html = ""
    if title_sub:
        sub_html = (
            f'<span style="color:{COLOR_GOLD};font-style:italic;font-size:10.5px;">'
            f' | {title_sub}</span>'
        )

    # Texte droite (cellule blanc/or sur fond noir) — compact
    text_cell = (
        f'<td valign="middle" '
        f'style="padding:13px 16px 13px 4px;background:{COLOR_INK};'
        f'font-family:Georgia,serif;color:#FFFFFF;line-height:1.45;">'
        # Nom
        f'<div style="font-size:16px;color:#FFFFFF;letter-spacing:0.4px;">{name}</div>'
        # Titre + sous-titre
        f'<div style="font-size:11px;color:{COLOR_GOLD};margin-top:1px;'
        f'font-style:italic;letter-spacing:0.2px;">{title_main}{sub_html}</div>'
        # Compagnie + tagline
        f'<div style="font-size:11.5px;color:#FFFFFF;font-weight:bold;margin-top:6px;'
        f'letter-spacing:0.3px;">{COMPANY_NAME}</div>'
        f'<div style="font-size:10px;color:{COLOR_GOLD};font-style:italic;'
        f'margin-top:1px;letter-spacing:0.4px;">{tagline}</div>'
        # Contacts (tel + email) — Yves 2026-05-04 :
        # 1) Icônes Unicode retirées (cassaient l'alignement)
        # 2) Font sans-serif (Arial) au lieu de Georgia : les chiffres serif
        #    de Georgia sont « old-style » (3, 4, 5, 7, 9 descendent sous la
        #    baseline). Arial = chiffres « lining » alignés par défaut.
        # 3) font-variant-numeric: tabular-nums lining-nums force chiffres égaux.
        f'<div style="font-family:Arial,Helvetica,sans-serif;'
        f'font-variant-numeric:tabular-nums lining-nums;'
        f'font-feature-settings:\'lnum\' 1, \'tnum\' 1;'
        f'font-size:10.5px;color:#E8E8E8;margin-top:7px;'
        f'white-space:nowrap;letter-spacing:0.2px;line-height:1.4;">'
        f'<span style="color:{COLOR_GOLD};font-style:italic;">Tél.</span>&nbsp;'
        f'<a href="tel:{COMPANY_PHONE_HREF}" '
        f'style="color:#E8E8E8;text-decoration:none;">{phone_display}</a>'
        f'<span style="color:{COLOR_GOLD};">&nbsp;&nbsp;·&nbsp;&nbsp;</span>'
        f'<a href="mailto:{email}" '
        f'style="color:#E8E8E8;text-decoration:none;">{email}</a>'
        f'</div>'
        # Adresse — aussi Arial + chiffres alignés (numéro civique 2705 et
        # code postal H3E 0G2 doivent être alignés).
        f'<div style="font-family:Arial,Helvetica,sans-serif;'
        f'font-variant-numeric:tabular-nums lining-nums;'
        f'font-feature-settings:\'lnum\' 1, \'tnum\' 1;'
        f'font-size:9.5px;color:#BBBBBB;margin-top:4px;line-height:1.4;">'
        f'{addr_html}'
        f'</div>'
        # Phrase confidentialité (compacte)
        f'<div style="font-size:8.5px;color:#999999;font-style:italic;'
        f'margin-top:7px;line-height:1.4;border-top:1px solid #333;padding-top:6px;">'
        f'{confidentiality}'
        f'</div>'
        f'</td>'
    )

    # Table 2 colonnes (logo | texte) sur fond noir — compact
    return (
        f'<div style="margin-top:28px;max-width:520px;">'
        f'{closing_html}'
        f'{manuscript_html}'
        f'<table role="presentation" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;background:{COLOR_INK};'
        f'max-width:520px;width:100%;border:1px solid {COLOR_GOLD_DARK};">'
        f'<tr>{logo_cell}{text_cell}</tr>'
        f'</table>'
        f'</div>'
    )


# ─── Helpers prêts-à-l'emploi par persona ────────────────────────

def signature_yves(language: str = "fr") -> str:
    """Signature Yves Barrette — Directeur-Fondateur (style noir horizontal).

    Titre confirmé Yves 2026-05-04 : « Directeur-Fondateur » (PAS Président).
    Sous-titre : « Financement immobilier commercial » (segment d'expertise).
    """
    if language == "en":
        title = "Founder & Director"
        sub = "Commercial real estate financing"
        closing = "Best regards"
    else:
        title = "Directeur-Fondateur"
        sub = "Financement immobilier commercial"
        closing = "Cordialement"
    return build_dark_signature_block(
        name="Yves Barrette",
        title_main=title,
        title_sub=sub,
        email="yves@capitalnorvex.com",
        manuscript_scan_filename=None,  # DÉSACTIVÉ 2026-05-11 PM — préférence Yves : une seule signature visuelle (bandeau noir uniquement, pas de manuscrite scannée). Voir preference_signature_simple_2026-05-11.md.
        closing=closing,
        language=language,
    )


def signature_suzanne(language: str = "fr") -> str:
    """Signature Suzanne Breton — Administratrice (style noir horizontal).

    Titre confirmé Yves 2026-05-04 : « Administratrice » uniquement.
    Pas de signature manuscrite scannée disponible pour l'instant.
    """
    if language == "en":
        title = "Director"
        closing = "Best regards"
    else:
        title = "Administratrice"
        closing = "Cordialement"
    return build_dark_signature_block(
        name="Suzanne Breton",
        title_main=title,
        title_sub=None,  # Pas de sous-titre pour Suzanne
        email="suzanne@capitalnorvex.com",
        manuscript_scan_filename=None,  # Pas de scan dispo (Yves 2026-05-04)
        closing=closing,
        language=language,
    )


def signature_sophie(language: str = "fr") -> str:
    """Signature Sophie — NORVEX RELATIONS™ (agent IA)."""
    if language == "en":
        title = "Customer Relations Coordinator"
        ai = ("Sophie is an AI relations coordinator at Capital Norvex Inc. "
              "All financial and legal decisions are made and approved by management.")
    else:
        title = "Coordonnatrice service à la clientèle"
        ai = ("Sophie est une coordonnatrice IA de Capital Norvex Inc. "
              "Toutes les décisions financières et juridiques sont prises et "
              "validées par la direction.")
    return build_signature_block(
        name="Sophie",
        title=title,
        suffix="RELATIONS",
        email="info@capitalnorvex.com",
        show_phone=False,  # Agent IA → pas de tél naturellement
        ai_disclosure=ai,
        language=language,
    )


def signature_camille(language: str = "fr") -> str:
    """Signature Camille — NORVEX COUNSEL™ (agent IA juridique)."""
    if language == "en":
        title = "Legal Coordinator"
        ai = ("Camille is an AI legal coordinator at Capital Norvex Inc. "
              "All financial and legal decisions are made and approved by management.")
        bar = ("Any legal decision remains that of the retained professional "
               "advisors.")
    else:
        title = "Coordonnatrice juridique"
        ai = ("Camille est une coordonnatrice juridique IA de Capital Norvex Inc. "
              "Toutes les décisions financières et juridiques sont prises et "
              "validées par la direction.")
        bar = ("Toute décision juridique demeure celle des conseillers "
               "professionnels mandatés.")
    return build_signature_block(
        name="Camille",
        title=title,
        suffix="COUNSEL",
        email="camille@capitalnorvex.com",
        show_phone=False,  # Agent IA → pas de tél naturellement
        ai_disclosure=ai,
        bar_disclaimer=bar,
        language=language,
    )


def signature_team_norvex(language: str = "fr", suffix: Optional[str] = None) -> str:
    """Signature « L'équipe Capital Norvex » pour mass outbound (courtiers/promoteurs)."""
    if language == "en":
        name = "The Capital Norvex Team"
        title = "Partner program" if not suffix else f"{suffix} program"
    else:
        name = "L'équipe Capital Norvex"
        title = "Programme partenaires" if not suffix else f"Programme {suffix}"
    return build_signature_block(
        name=name,
        title=title,
        suffix=None,
        email="info@capitalnorvex.com",
        show_phone=True,  # Équipe = OK d'avoir le tél compagnie
        language=language,
    )
