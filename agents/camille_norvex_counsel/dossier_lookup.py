"""Recherche d'un dossier Firestore à partir des signaux du triage.

Le triage Sonnet identifie des `dossierHints` (mots-clés) et possiblement un
`dossierIdGuess` (numéro de dossier). Ce module cherche le doc Firestore
correspondant dans la collection `dossiers`.

Stratégie de match (par ordre de priorité) :
    1. dossierIdGuess exact (CNV-2026-XXXXX)
    2. Match sur emprunteur, projet, adresse via dossierHints
    3. Match sur notaire/avocat connu (champ notaireQc / solicitorOn du dossier)

Si aucun match → renvoie None (l'orchestrateur escaladera à Yves).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from agents.shared.firestore_client import get, query

COLLECTION_DOSSIERS = "dossiers"

# Stages où Camille peut répondre EN AUTONOMIE (validés par Yves 2026-05-04)
APPROVED_STAGES = {
    "loi_signed",
    "at_notary",
    "closing_in_progress",
    "closing",
    "funded",
    "paid_off",
}

# Stages où Camille DOIT escalader (dossier pas encore approuvé)
ESCALATION_STAGES = {
    "intake",
    "score_pending",
    "score_in_progress",
    "score_completed",
    "loi_draft",
    "loi_sent",
    "default",
    "litigation",
}


def is_stage_approved(stage: Optional[str]) -> bool:
    """True si le stage permet à Camille de répondre en autonomie."""
    if not stage:
        return False
    return stage.lower().strip() in APPROVED_STAGES


def normalize_dossier_id(raw: str) -> Optional[str]:
    """Normalise un ID de dossier (variations possibles : 12345, CNV-2026-12345, etc.)."""
    if not raw:
        return None
    s = str(raw).strip().upper()
    # Pattern CNV-AAAA-NNNNN
    m = re.search(r"(CNV-?\d{4}-?\d{3,6})", s)
    if m:
        clean = m.group(1).replace("CNV", "CNV-").replace("--", "-")
        # Force le format CNV-AAAA-NNNNN
        parts = re.findall(r"\d+", clean)
        if len(parts) >= 2:
            return f"CNV-{parts[0]}-{parts[1]}"
    # Numéro simple (5 chiffres)
    m2 = re.search(r"\b(\d{4,6})\b", s)
    if m2:
        return m2.group(1)
    return None


def lookup_dossier(
    *,
    dossier_id_guess: Optional[str] = None,
    hints: Optional[List[str]] = None,
    from_address: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Recherche un dossier Firestore matchant les signaux fournis.

    Retourne le doc complet (avec _id) ou None si pas de match clair.
    """
    # 1. Tentative ID exact
    if dossier_id_guess:
        normalized = normalize_dossier_id(dossier_id_guess)
        if normalized:
            doc = get(COLLECTION_DOSSIERS, normalized)
            if doc:
                return {"_id": normalized, **doc}
            # Essai préfixé CNV-2026- si juste un numéro
            if not normalized.startswith("CNV"):
                from datetime import datetime
                year = datetime.now().year
                alt = f"CNV-{year}-{normalized}"
                doc = get(COLLECTION_DOSSIERS, alt)
                if doc:
                    return {"_id": alt, **doc}

    # 2. Recherche par hints (mots-clés)
    if not hints and not from_address:
        return None

    # Récupère tous les dossiers (limit raisonnable — on a peu de dossiers
    # actifs à la fois en pratique)
    all_dossiers = query(COLLECTION_DOSSIERS, limit=500)

    if not all_dossiers:
        return None

    # Score chaque dossier : combien de hints matchent
    scored = []
    hints_lower = [h.lower() for h in (hints or []) if h]
    from_lower = (from_address or "").lower()

    for d in all_dossiers:
        score = 0
        # Match sur from_address contre champs notaire/avocat connus + client emprunteur
        for email_field in ("notaireQc", "notaireEmail", "solicitorOnEmail",
                            "avocatQcEmail", "courtierEmail",
                            "email", "borrowerEmail", "clientEmail"):
            v = (d.get(email_field) or "").lower()
            if v and from_lower and v == from_lower:
                score += 5  # match email = très fort

        # Match sur hints contre champs nom/projet/adresse + prénom/nom du client
        searchable = " ".join([
            str(d.get("nomProjet", "")),
            str(d.get("nomEmprunteur", "")),
            str(d.get("client_name", "")),
            str(d.get("adresse", "")),
            str(d.get("address", "")),
            str(d.get("notaireNom", "")),
            str(d.get("notaireQc", "")),
            str(d.get("prenom", "")),
            str(d.get("nom", "")),
            str(d.get("_id", "")),
        ]).lower()

        for hint in hints_lower:
            if hint and len(hint) >= 3 and hint in searchable:
                score += 2

        if score > 0:
            scored.append((score, d))

    if not scored:
        return None

    # Meilleur match
    scored.sort(key=lambda x: x[0], reverse=True)
    top_score, best = scored[0]

    # Seuil minimum pour éviter les faux positifs
    if top_score < 2:
        return None

    # S'il y a une égalité serrée entre 2 dossiers, on retourne None (ambigu → escalade)
    if len(scored) > 1 and scored[1][0] == top_score:
        return None

    return best


def can_camille_auto_send(dossier: Optional[Dict[str, Any]]) -> tuple[bool, str]:
    """Vérifie si Camille peut envoyer en autonomie selon le dossier identifié.

    Retourne (autoriser, raison).
    """
    if not dossier:
        return False, "Dossier non identifié dans Firestore"

    stage = dossier.get("stage") or dossier.get("etape_actuelle") or ""
    stage_norm = stage.lower().strip()

    if stage_norm in ESCALATION_STAGES:
        return False, f"Dossier en stage '{stage}' (pré-approuvé, escalade requise)"

    if not is_stage_approved(stage_norm):
        return False, f"Stage '{stage}' inconnu ou non-autorisé pour autonomie"

    return True, f"Dossier en stage '{stage}' (approuvé, Camille autonome)"


def summarize_dossier_for_drafting(dossier: Dict[str, Any]) -> str:
    """Résumé textuel du dossier à injecter dans le prompt de drafting.

    Présente les éléments factuels APPROUVÉS du dossier (pour que Camille puisse
    répondre avec les vraies données : montant, taux, termes, etc.).
    """
    if not dossier:
        return "(aucun dossier identifié)"

    fields = [
        ("Dossier", dossier.get("_id")),
        ("Emprunteur", dossier.get("nomEmprunteur") or dossier.get("client_name")),
        ("Projet", dossier.get("nomProjet")),
        ("Adresse", dossier.get("adresse") or dossier.get("address")),
        ("Stage actuel", dossier.get("stage") or dossier.get("etape_actuelle")),
        ("Type opération", dossier.get("typeOperation") or dossier.get("loanType")),
        ("Montant prêt approuvé", dossier.get("montantApprouve") or dossier.get("loanAmount")),
        ("Taux annuel", dossier.get("taux") or dossier.get("interestRate")),
        ("Terme (mois)", dossier.get("termeMois") or dossier.get("termMonths")),
        ("Date LOI signée", dossier.get("dateLoiSignee") or dossier.get("loiSignedDate")),
        ("Date closing prévue", dossier.get("dateClosingPrevue") or dossier.get("closingDate")),
        ("Date funded", dossier.get("dateFunded") or dossier.get("fundedDate")),
        ("Notaire au dossier (QC)", dossier.get("notaireNom") or dossier.get("notaireQc")),
        ("Solicitor (ON)", dossier.get("solicitorOn")),
        ("Conditions particulières", dossier.get("conditionsParticulieres")),
        ("Garanties", dossier.get("garanties") or dossier.get("collateral")),
    ]

    lines = []
    for label, value in fields:
        if value not in (None, "", []):
            lines.append(f"  • {label}: {value}")

    summary = "\n".join(lines) if lines else "(dossier identifié mais sans données structurées)"

    # ─── Camille Brain : injection contexte complet si présent ───────────
    # Si le dossier a un champ `camilleContext` (markdown structuré exhaustif :
    # règles dossier-spécifiques, historique, positions Norvex verrouillées,
    # réponses types pré-validées par la direction), on l'injecte EN PLUS du
    # résumé tableau pour que Camille comprenne le dossier à 100 %.
    # Stocké dans Firestore par la direction (pilotage manuel), versionné par dossier.
    # Architecture pilote 2026-05-27 (premier cas : Henri Petit CNV-2026-59109).
    camille_context = dossier.get("camilleContext")
    if (
        camille_context
        and isinstance(camille_context, str)
        and len(camille_context.strip()) > 200
    ):
        version = dossier.get("camilleContextVersion", "?")
        summary += (
            "\n\n═══════════════════════════════════════════════════════════\n"
            f"📚 CAMILLE BRAIN — CONTEXTE COMPLET DU DOSSIER (v{version})\n"
            "═══════════════════════════════════════════════════════════\n\n"
            "Tu DOIS lire et intégrer TOUT le contexte ci-dessous AVANT de drafter "
            "ta réponse. Ce brief contient les règles spécifiques du dossier, "
            "l'historique, les positions Norvex verrouillées par la direction, et les "
            "réponses types pré-validées. Tu ne peux PAS dévier de ces règles sans "
            "escalade explicite à Yves Barrette. En cas de doute ou de signal qui sort "
            "des scénarios documentés, tu draftes une réponse minimale (accusé de "
            "réception) et tu escalades.\n\n"
            f"{camille_context}\n"
            "\n═══════════════════════════════════════════════════════════\n"
            "FIN DU CAMILLE BRAIN — applique ces directives strictement.\n"
            "═══════════════════════════════════════════════════════════"
        )

    return summary
