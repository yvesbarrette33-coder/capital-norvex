"""Traducteur EN ↔ FR de titres professionnels (institutionnels canadiens).

Bug identifié 2026-05-08 : 90 docs Firestore (advisorTargets + capitalTargets)
ont un title en anglais malgré language=fr + region=QC. Quand on envoie un
courriel FR à ces cibles, leur titre s'affiche en anglais dans le corps du
message → pas pro pour un envoi institutionnel.

Plutôt que patcher 90 docs Firestore (risque de casse), on traduit à la volée
côté template. Si le titre n'est pas dans le mapping, on retourne tel quel.

Mappings basés sur les conventions standard des cabinets institutionnels
canadiens bilingues (Stikeman, McCarthy, Norton Rose, Osler, BMO, RBC, etc.).
"""
from __future__ import annotations
import re

# ─── Mapping EN → FR (titres complets et fragments) ────────────────────────
#
# Ordre = priorité de match. Les expressions plus spécifiques d'abord, les
# génériques ensuite. La fonction de traduction parcourt le mapping et
# remplace SEGMENT par SEGMENT (mot par mot pour les fragments).

EN_TO_FR_FULL = {
    # ── Cabinets juridiques / fiscalité ─────────────────────────────────
    "tax practice group manager": "Gestionnaire du groupe de pratique fiscale",
    "tax incentives and grants partner": "Associé, incitatifs fiscaux et subventions",
    "tax incentives partner": "Associé, incitatifs fiscaux",
    "real estate partner": "Associé, immobilier",
    "tax partner": "Associé, fiscalité",
    "tax manager": "Gestionnaire en fiscalité",
    "estate planner": "Planificateur successoral",
    "tax counsel": "Conseiller en fiscalité",
    "estate counsel": "Conseiller successoral",
    "m&a partner": "Associé, fusions et acquisitions",
    "corporate partner": "Associé, droit corporatif",
    "litigation partner": "Associé, litige",
    "senior partner": "Associé principal",
    "managing partner": "Associé directeur",

    # ── Wealth / patrimoine ────────────────────────────────────────────
    "senior wealth advisor": "Conseiller en patrimoine principal",
    "wealth advisor": "Conseiller en patrimoine",
    "wealth manager": "Gestionnaire de patrimoine",
    "wealth planner": "Planificateur en patrimoine",
    "investment advisor": "Conseiller en placements",
    "investment counsel": "Conseiller en placements",
    "portfolio manager": "Gestionnaire de portefeuille",
    "senior portfolio manager": "Gestionnaire de portefeuille principal",
    "investment counsellor": "Conseiller en placements",
    "private banker": "Banquier privé",
    "senior private banker": "Banquier privé principal",
    "trust officer": "Fiduciaire",

    # ── Direction exécutive ────────────────────────────────────────────
    "president and ceo": "Président et chef de la direction",
    "president & ceo": "Président et chef de la direction",
    "president et ceo": "Président et chef de la direction",
    "chief executive officer": "Chef de la direction",
    "chief financial officer": "Chef de la direction financière",
    "chief operating officer": "Chef de l'exploitation",
    "chief investment officer": "Chef des placements",
    "executive vice president": "Vice-président exécutif",
    "senior vice president": "Vice-président principal",
    "regional vice president": "Vice-président régional",
    "vice president": "Vice-président",
    "managing director": "Directeur général",
    "executive director": "Directeur exécutif",
    "senior director": "Directeur principal",
    "general counsel": "Conseiller juridique principal",
}

# Fragments (un seul mot) — utilisés en fallback si pas de match complet
EN_TO_FR_TOKENS = {
    "partner": "Associé",
    "advisor": "Conseiller",
    "advisor": "Conseiller",
    "counsellor": "Conseiller",
    "counsel": "Conseiller",
    "manager": "Gestionnaire",
    "director": "Directeur",
    "president": "Président",
    "officer": "Dirigeant",
    "founder": "Fondateur",
    "co-founder": "Cofondateur",
    "principal": "Principal",
    "head": "Chef",
    "chief": "Chef",
    "executive": "Exécutif",
    "senior": "Principal",
    "tax": "Fiscalité",
    "real estate": "Immobilier",
    "wealth": "Patrimoine",
    "investment": "Placements",
    "portfolio": "Portefeuille",
}


def _looks_english(text: str) -> bool:
    """Heuristique : titre majoritairement anglais ?

    Détecte les mots-clés EN typiques. Permet de skipper les titres déjà FR
    (« Associé en fiscalité ») pour ne pas les casser.
    """
    if not text:
        return False
    low = text.lower()
    en_markers = (
        "partner", "manager", "advisor", "advisor", "counsellor",
        "counsel", "director", "president", "officer", "founder",
        "head", "chief", "wealth", "tax", "estate", "investment",
        "portfolio", "senior", "executive", "managing", "regional",
        "vice", "ceo", "cfo", "coo", "cio",
    )
    fr_markers = (
        "associé", "conseiller", "gestionnaire", "directeur", "président",
        "fondateur", "principal", "fiscalité", "patrimoine", "placements",
        "portefeuille", "immobilier", "successoral", "fiduciaire",
    )
    has_en = any(m in low for m in en_markers)
    has_fr = any(m in low for m in fr_markers)
    return has_en and not has_fr


def translate_title_to_fr(title: str) -> str:
    """Traduit un titre EN vers FR pour affichage dans courriel français.

    Stratégie :
    1. Si titre vide ou déjà FR → retourner tel quel
    2. Match exact dans EN_TO_FR_FULL (priorité expressions complexes)
    3. Fallback : remplacement token par token via EN_TO_FR_TOKENS
    4. Si rien ne match → retourner tel quel (jamais bloquant)
    """
    if not title:
        return title
    text = title.strip()
    if not _looks_english(text):
        return text  # Déjà FR ou neutre, on touche pas

    low = text.lower()

    # 1. Match complet (le plus long en premier)
    for en_phrase in sorted(EN_TO_FR_FULL.keys(), key=len, reverse=True):
        if en_phrase in low:
            fr_value = EN_TO_FR_FULL[en_phrase]
            # Remplace conservant la casse environnante
            pattern = re.compile(re.escape(en_phrase), re.IGNORECASE)
            text = pattern.sub(fr_value, text, count=1)
            low = text.lower()

    # 2. Fallback token par token (dernière passe)
    if _looks_english(text):
        for en_token in sorted(EN_TO_FR_TOKENS.keys(), key=len, reverse=True):
            fr_token = EN_TO_FR_TOKENS[en_token]
            pattern = re.compile(r"\b" + re.escape(en_token) + r"\b", re.IGNORECASE)
            text = pattern.sub(fr_token, text)

    # Nettoyage : capitalize première lettre, garder le reste
    text = text.strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    return text


def translate_title_for_lang(title: str, lang: str) -> str:
    """Wrapper : traduit selon la langue cible.

    - lang='fr' → traduit EN→FR si titre est EN
    - lang='en' → retourne tel quel (la majorité de Firestore est déjà EN)
    """
    if not title:
        return title
    if lang == "fr":
        return translate_title_to_fr(title)
    return title
