"""Signatures HTML — générées selon persona et langue.

⚠️ Garde-fou QC art. 132 :
    - Camille = « Coordonnatrice juridique » (PAS « avocate », PAS « notaire »)
    - Disclaimer obligatoire sur info@/camille@ : décision juridique = professionnel mandaté
"""
from __future__ import annotations

from .config import (
    COMPANY_ADDRESS,
    COMPANY_NAME,
    COMPANY_PHONE,
    COMPANY_WEBSITE,
    YVES_FULL_NAME,
    YVES_TITLE,
)


def _signature_camille(language: str = "fr") -> str:
    """Signature institutionnelle Camille — design système unifié 2026-05-04.

    Délègue à `agents.shared.signature_block.signature_camille()` qui retourne :
    - Bandeau or sur fond clair (style « LIGHT » pour agents IA)
    - Mention IA + phrase « validées par la direction »
    - Disclaimer art. 132 QC (obligatoire — Camille n'est pas avocate Barreau)
    - Adresse + email + site (pas de tél = agent IA)
    - Cohérent avec Sophie (LIGHT) / Yves+Suzanne (DARK)
    """
    from agents.shared.signature_block import signature_camille as _shared_camille
    return _shared_camille(language=language)


def _signature_yves(language: str = "fr") -> str:
    """Signature personnelle Yves Barrette pour yves@.

    Pas de mention Camille / IA / assistant — règle absolue ghostwriter.
    """
    if language == "en":
        closing = "Best regards"
    else:
        closing = "Cordialement"

    return (
        '<br><p style="margin-top:24px;font-family:Arial,sans-serif;'
        'font-size:13px;color:#222;line-height:1.5;">'
        f"{closing},<br><br>"
        f"<strong>{YVES_FULL_NAME}</strong><br>"
        f"{YVES_TITLE}<br>"
        f"{COMPANY_NAME}<br>"
        f"{COMPANY_ADDRESS}<br>"
        f"{COMPANY_PHONE} | {COMPANY_WEBSITE}"
        "</p>"
    )


def build_signature_html(*, persona: str, language: str = "fr") -> str:
    """Retourne la signature HTML adaptée à la persona."""
    if persona == "institutional":
        return _signature_camille(language=language)
    elif persona == "ghostwriter":
        return _signature_yves(language=language)
    else:
        raise ValueError(f"Persona inconnue : {persona}")
