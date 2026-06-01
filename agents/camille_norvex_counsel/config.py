"""Configuration centrale Camille — boîtes mail, modèles, signatures.

Architecture extensible : ajouter une boîte = ajouter une entrée dans MAILBOXES.
"""
from __future__ import annotations

import os
from typing import Dict, Literal

# ── Modèles Anthropic ────────────────────────────────────────────
MODEL_TRIAGE = "claude-sonnet-4-6"   # rapide, ~10/jour, $3/$15 per 1M
MODEL_DRAFTING = "claude-opus-4-6"   # qualité top-tier, $5/$25 per 1M
MODEL_TRANSLATION = "claude-opus-4-6"  # FR↔EN juridique précis
MAX_TOKENS_TRIAGE = 2500
MAX_TOKENS_DRAFTING = 4096

# ── Adresse + identité Capital Norvex ─────────────────────────────
COMPANY_NAME = "Capital Norvex Inc."
COMPANY_ADDRESS = "2705-1000 André-Prévost, Île-des-Sœurs (Verdun), Montréal, QC H3E 0G2"
COMPANY_NEQ = "1182097890"
COMPANY_PHONE = "1-(438)-533-PRET (7738)"
COMPANY_WEBSITE = "capitalnorvex.com"

YVES_FULL_NAME = "Yves Barrette"
YVES_TITLE = "Président"

# ── Boîte d'approbation ───────────────────────────────────────────
# Override le défaut (Gmail perso) — règle Yves : pas de Gmail perso
YVES_APPROVAL_INBOX = os.getenv("CAMILLE_APPROVAL_INBOX", "yves@capitalnorvex.com")

# ── Persona modes ─────────────────────────────────────────────────
PersonaMode = Literal["institutional", "ghostwriter"]

# ── Catégories juridiques (Camille = juridique pur) ───────────────
# Sur les boîtes où legal_only_filter=True, tout ce qui n'est PAS dans
# cette liste est ignoré par Camille → réservé à de futurs agents
# (assistante perso pour yves@, agent général pour info@).
LEGAL_CATEGORIES = {
    "notaire_qc",
    "avocat_qc",
    "solicitor_on",
    "rdprm",
}

# ── Configuration des boîtes surveillées ──────────────────────────
# Chaque boîte a :
#   - persona             : signature/style (institutional | ghostwriter)
#   - always_cc_yves      : Yves toujours en CC sur les envois sortants
#   - legal_only_filter   : Camille ne traite QUE les emails juridiques
#   - cc_email            : email à mettre en CC (par défaut yves@capitalnorvex.com)
MAILBOXES: Dict[str, dict] = {
    "info@capitalnorvex.com": {
        "persona": "institutional",
        "signature_signed_by": "Camille — NORVEX COUNSEL™",
        "always_cc_yves": True,            # 🚨 Règle Yves 2026-05-04 : TOUJOURS en CC
        "legal_only_filter": True,         # Camille = juridique uniquement ici
        "cc_email": "yves@capitalnorvex.com",
        "description": "Boîte générale — Camille gère SEULEMENT le juridique. Reste = futur agent général. Yves TOUJOURS en CC.",
    },
    "yves@capitalnorvex.com": {
        "persona": "ghostwriter",
        "signature_signed_by": YVES_FULL_NAME,
        "always_cc_yves": False,           # Yves EST l'expéditeur — pas de self-CC
        "legal_only_filter": True,         # Camille = juridique uniquement ici
        "cc_email": None,
        "description": "Boîte Yves — Camille = ghostwriter juridique uniquement. Reste = futur agent perso.",
    },
    # ── ✅ ACTIVÉE 2026-05-04 (jour 1 officiel Capital Norvex) ─────
    # Boîte M365 créée + permissions Graph accordées + ajoutée Outlook Yves.
    "camille@capitalnorvex.com": {
        "persona": "institutional",
        "signature_signed_by": "Camille — NORVEX COUNSEL™",
        "always_cc_yves": True,          # Règle Yves 2026-05-04 : toujours en CC
        "legal_only_filter": False,      # Boîte 100% juridique : tout est traité
        "cc_email": "yves@capitalnorvex.com",
        "description": "Boîte juridique dédiée Camille. Yves toujours en CC. Workflow approbation obligatoire avant chaque envoi.",
    },
}


def should_cc_yves_camille(triage: dict | None = None) -> bool:
    """Décide si Yves doit être CC sur un envoi Camille selon le triage.

    Architecture scalable Yves 2026-05-04 : à 100-200 clients, Yves CC sur tout
    = inbox spam mortelle. Pour Camille (juridique = zone à risque), CC sur :
    - requiresYvesDecision = True (Camille a flagué « décision Yves nécessaire »)
    - requiresHumanLawyer = True (Camille a flagué « avocat humain nécessaire »)
    - priority = "urgent"
    - category in {"autre", "spam"} (cas inhabituels)
    - Override env : EMERGENCY_CC_ALL=true → CC tout.

    Pour le routinier (notaire QC qui demande un statut, RDPRM standard, etc.) :
    pas de CC. Yves consulte le dashboard /camille-admin.html quand il veut.
    """
    if os.getenv("EMERGENCY_CC_ALL", "").strip().lower() in ("true", "1", "yes"):
        return True
    if not triage:
        return False
    if triage.get("requiresYvesDecision"):
        return True
    if triage.get("requiresHumanLawyer"):
        return True
    if (triage.get("priority") or "").lower().strip() == "urgent":
        return True
    cat = (triage.get("category") or "").lower().strip()
    if cat in {"autre", "spam"}:
        return True
    return False


def get_cc_list(mailbox_email: str, triage: dict | None = None) -> list:
    """Liste de CC selon triage. Vide pour routine, [yves@] pour sensible.

    Param `triage` optionnel : si None, comportement legacy (always_cc_yves).
    Si fourni, applique la logique scalable should_cc_yves_camille().
    """
    conf = get_mailbox_config(mailbox_email)
    if not conf.get("cc_email"):
        return []
    # Comportement scalable si triage fourni
    if triage is not None:
        return [conf["cc_email"]] if should_cc_yves_camille(triage) else []
    # Legacy (appels qui n'ont pas encore de triage) : respecter always_cc_yves
    if conf.get("always_cc_yves"):
        return [conf["cc_email"]]
    return []


def is_legal_only(mailbox_email: str) -> bool:
    """True si la boîte ne doit traiter QUE les emails juridiques."""
    conf = get_mailbox_config(mailbox_email)
    return bool(conf.get("legal_only_filter", False))


def get_mailbox_config(email: str) -> dict:
    """Retourne la config d'une boîte (lowercase-insensitive)."""
    key = email.lower().strip()
    if key not in MAILBOXES:
        raise KeyError(f"Boîte non configurée pour Camille : {email}")
    return MAILBOXES[key]


def is_mailbox_active(email: str) -> bool:
    return email.lower().strip() in MAILBOXES


# ── Firestore collections ─────────────────────────────────────────
COLLECTION_EMAILS = "camilleEmails"          # emails entrants triés
COLLECTION_DRAFTS = "camilleDrafts"          # drafts en attente d'approbation
COLLECTION_TEMPLATES = "camilleTemplates"    # templates réutilisables (future)
AGENT_NAME = "camille"                       # tag pour audit log
