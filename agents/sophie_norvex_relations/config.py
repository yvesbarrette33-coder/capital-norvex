"""Configuration Sophie — NORVEX RELATIONS™.

Sophie = Coordonnatrice service à la clientèle premium pour info@capitalnorvex.com.
Calquée sur Camille (NORVEX COUNSEL) mais pour le NON-juridique.

Coordination avec Camille :
- Camille gère le JURIDIQUE sur info@ (notaires/avocats/RDPRM)
- Sophie gère le RESTE sur info@ (info, demandes générales, FAQ, accueil)
- Filtres mutuellement exclusifs côté triage
"""
from __future__ import annotations

import os
from typing import Dict, Literal

# ── Modèles Anthropic ────────────────────────────────────────────
MODEL_TRIAGE = "claude-sonnet-4-6"
MODEL_DRAFTING = "claude-opus-4-6"
MAX_TOKENS_TRIAGE = 1024
MAX_TOKENS_DRAFTING = 4096

# ── Identité Capital Norvex (idem Camille) ────────────────────────
COMPANY_NAME = "Capital Norvex Inc."
COMPANY_ADDRESS = "2705-1000 André-Prévost, Île-des-Sœurs (Verdun), Montréal, QC H3E 0G2"
COMPANY_NEQ = "1182097890"
COMPANY_PHONE = "1-(438)-533-PRET (7738)"
COMPANY_WEBSITE = "capitalnorvex.com"

YVES_FULL_NAME = "Yves Barrette"
YVES_TITLE = "Président"

# ── Boîte d'approbation Yves ──────────────────────────────────────
YVES_APPROVAL_INBOX = os.getenv("CAMILLE_APPROVAL_INBOX", "yves@capitalnorvex.com")

# ── Persona ───────────────────────────────────────────────────────
PersonaMode = Literal["sophie_relations"]

# ── Catégories JURIDIQUES = réservées à Camille (Sophie SKIP) ─────
LEGAL_CATEGORIES_RESERVED_FOR_CAMILLE = {
    "notaire_qc",
    "avocat_qc",
    "solicitor_on",
    "rdprm",
}

# ── Catégories que Sophie traite (NON-juridique sur info@) ────────
SOPHIE_DRAFTABLE_CATEGORIES = {
    "demande_info_generale",      # Info programme, conditions, processus
    "demande_pre_qualification",  # Prospect veut analyse Score Norvex
    "demande_rdv",                # Prise de RDV
    "courtier_partenariat",       # Question programme partenaire
    "promoteur_qualification",    # Promoteur veut financer projet
    "media_press",                # Médias / presse
    "fournisseur",                # Fournisseur / vendeur
    "candidature",                # Candidature emploi/stage
    "autre_general",              # Autres demandes générales
}

# ── Catégories qui CC Yves (architecture scalable Yves 2026-05-04) ──
# Décision Yves : à 100-200 clients, Yves CC sur TOUS = inbox spam mortelle.
# Donc Yves CC SEULEMENT sur les catégories sensibles. Le reste = autonomie pure.
# Yves peut toujours auditer via /sophie-admin.html (historique complet).
# Override possible via env : EMERGENCY_CC_ALL=true → CC sur TOUT (mode test/audit).
CC_YVES_CATEGORIES = {
    "media_press",          # Image marque
    "litige",               # Conflit/plainte (catégorie hors Sophie standard)
    "demande_strategique",  # M&A, partenariat majeur, levée capital
    "prompt_injection",     # Sécurité
    "client_vip_existant",  # Privilégié (futur)
}

# ── Configuration boîtes surveillées par Sophie ──────────────────
# Sophie ne polle QUE info@ (Camille gère camille@ + le juridique sur info@)
MAILBOXES: Dict[str, dict] = {
    "info@capitalnorvex.com": {
        "persona": "sophie_relations",
        "signature_signed_by": "Sophie — NORVEX RELATIONS™",
        "skip_legal_for_camille": True,     # Filtre : juridique → SKIP (laisse à Camille)
        "cc_email": "yves@capitalnorvex.com",
        "description": "Boîte info@ — Sophie autonomie totale. Yves CC seulement sur catégories sensibles (CC_YVES_CATEGORIES).",
    },
}


def should_cc_yves(category: str | None) -> bool:
    """Décide si Yves doit être CC selon la catégorie de triage.

    - Mode normal : True seulement pour CC_YVES_CATEGORIES (~5% des cas)
    - Mode urgence : si EMERGENCY_CC_ALL=true dans .env → toujours True (audit)
    """
    if os.getenv("EMERGENCY_CC_ALL", "").strip().lower() in ("true", "1", "yes"):
        return True
    return (category or "").lower().strip() in CC_YVES_CATEGORIES


def get_cc_list(mailbox_email: str, category: str | None = None) -> list:
    """Liste de CC selon catégorie de triage. Vide si routine, [yves@] si sensible."""
    conf = get_mailbox_config(mailbox_email)
    if should_cc_yves(category) and conf.get("cc_email"):
        return [conf["cc_email"]]
    return []


def get_mailbox_config(email: str) -> dict:
    key = email.lower().strip()
    if key not in MAILBOXES:
        raise KeyError(f"Boîte non configurée pour Sophie : {email}")
    return MAILBOXES[key]


def is_mailbox_active(email: str) -> bool:
    return email.lower().strip() in MAILBOXES


def is_legal_reserved_for_camille(category: str) -> bool:
    """True si cette catégorie est juridique → Sophie SKIP, Camille gère."""
    return (category or "").lower().strip() in LEGAL_CATEGORIES_RESERVED_FOR_CAMILLE


# ── Firestore collections ─────────────────────────────────────────
COLLECTION_EMAILS = "sophieEmails"
COLLECTION_DRAFTS = "sophieDrafts"
AGENT_NAME = "sophie"
