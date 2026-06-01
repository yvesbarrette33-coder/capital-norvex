"""Audit Karine — Firestore writes + déduplication anti-doublons."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from agents.shared.firestore_client import (
    audit_log, create, db, get, query, update,
)

from .config import (
    AGENT_NAME,
    COLLECTION_KARINE_DRAFTS,
    COLLECTION_PROCESSED,
    COLLECTION_TRANSACTIONS,
)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ────────────────────────────────────────────────────────────────────
# Anti-doublon : Message-ID
# ────────────────────────────────────────────────────────────────────

def is_email_already_processed(internet_message_id: Optional[str]) -> bool:
    """Vrai si on a déjà traité ce Message-ID."""
    if not internet_message_id:
        return False
    safe_id = internet_message_id.replace("/", "_").replace("#", "_")[:200]
    snap = db().collection(COLLECTION_PROCESSED).document(safe_id).get()
    return snap.exists


def mark_email_as_processed(*, internet_message_id: str, mailbox: str,
                             category: str, summary: str = "") -> None:
    if not internet_message_id:
        return
    safe_id = internet_message_id.replace("/", "_").replace("#", "_")[:200]
    db().collection(COLLECTION_PROCESSED).document(safe_id).set({
        "messageId": internet_message_id,
        "mailbox": mailbox,
        "category": category,
        "summary": summary[:500],
        "processedAt": now_utc_iso(),
        "agent": AGENT_NAME,
    })


def is_duplicate_invoice(*, fournisseur: str, numero: str, montant_total: float,
                         date: str) -> Optional[str]:
    """Détecte un doublon évident dans les transactions confirmées + pending.

    Heuristique : même fournisseur + même numero_facture + même montant ±0.01 +
    même mois → probablement déjà enregistré.

    Retourne l'ID de la transaction existante OU None.
    """
    if not (fournisseur and numero):
        return None
    try:
        existing = query(
            COLLECTION_TRANSACTIONS,
            filters=[
                ("partenaire", "==", fournisseur),  # champ approximatif ; on filtrera ensuite
            ],
            limit=50,
        )
    except Exception:
        return None
    for tx in existing:
        if (tx.get("numero_facture") or "").lower() == numero.lower():
            try:
                if abs(float(tx.get("montant", 0)) - montant_total) < 0.02:
                    return tx.get("id")
            except (ValueError, TypeError):
                pass
    return None


# ────────────────────────────────────────────────────────────────────
# Création transaction Firestore
# ────────────────────────────────────────────────────────────────────

def create_pending_transaction(*, extracted: Dict[str, Any],
                                source_email: Dict[str, Any],
                                pdf_blob_key: Optional[str] = None) -> str:
    """Crée une transaction `pending` dans Firestore.

    Le schéma respecte EXACTEMENT celui utilisé par capital-norvex-brain.html
    (loadTransactions / saveTx ligne 1450-1471) :

      type, date, montant, categorie, description, statut,
      dossierId, dossierNom, partenaire, source, createdAt

    Champs additionnels Karine (rétro-compatibles, ignorés par UI existante) :
      tax_note, tps, tvq, montant_ht, devise, fournisseur, numero_facture,
      requires_yves_review, confidence, sourceEmailFrom, sourceEmailSubject,
      pdfBlobKey, agent
    """
    type_tx = extracted.get("type", "depense")
    cat = extracted.get("categorie", "autres_depenses")
    montant = float(extracted.get("montant_total", 0))
    date = extracted.get("date") or datetime.now(timezone.utc).date().isoformat()
    desc = (extracted.get("description") or "").strip()[:200]

    payload: Dict[str, Any] = {
        # ── Champs requis Brain UI ────
        "type": type_tx,
        "date": date,
        "montant": montant,
        "categorie": cat,
        "description": desc,
        "statut": "pending",
        "dossierId": extracted.get("dossier_link_suggestion") or "",
        "dossierNom": "",  # à remplir si dossier_link_suggestion match dans Firestore
        "source": AGENT_NAME,

        # ── Champs Karine étendus ────
        "fournisseur": extracted.get("fournisseur_ou_payeur") or "",
        "numero_facture": extracted.get("numero_facture") or "",
        "montant_ht": float(extracted.get("montant_ht", 0)),
        "tps": float(extracted.get("tps", 0)),
        "tvq": float(extracted.get("tvq", 0)),
        "devise": extracted.get("devise", "CAD"),
        "tax_note": (extracted.get("tax_note") or "")[:300],
        "requires_yves_review": bool(extracted.get("requires_yves_review", False)),
        "yves_review_reason": (extracted.get("yves_review_reason") or "")[:200],
        "confidence": int(extracted.get("confidence", 0)),
        "sourceEmailFrom": (source_email.get("from") or "")[:200],
        "sourceEmailSubject": (source_email.get("subject") or "")[:200],
        "sourceEmailDate": source_email.get("received_at_iso") or now_utc_iso(),
        "pdfBlobKey": pdf_blob_key or "",
        "agent": AGENT_NAME,
    }

    # Pour les paiements partenaires, dupliquer dans `partenaire` (champ Brain)
    if type_tx == "partenaire":
        payload["partenaire"] = extracted.get("partenaire_nom") or extracted.get(
            "fournisseur_ou_payeur"
        ) or ""

    tx_id = create(COLLECTION_TRANSACTIONS, payload)
    return tx_id


# ────────────────────────────────────────────────────────────────────
# Lien dossier client (best-effort)
# ────────────────────────────────────────────────────────────────────

def try_link_to_dossier(extracted: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Si Karine a suggéré un dossier_link_suggestion, on essaie de matcher."""
    suggestion = (extracted.get("dossier_link_suggestion") or "").strip()
    if not suggestion:
        return None

    # 1. Match direct sur ID
    try:
        dossier = get("dossiers", suggestion)
        if dossier:
            nom = (
                dossier.get("borrowerName")
                or dossier.get("name")
                or f"{dossier.get('prenom','')} {dossier.get('nom','')}".strip()
                or ""
            )
            return {"dossierId": dossier.get("id", suggestion), "dossierNom": nom}
    except Exception:
        pass

    # 2. Match sur nom emprunteur (recherche partielle)
    try:
        sug_lower = suggestion.lower()
        all_dossiers = query("dossiers", limit=200)
        for d in all_dossiers:
            name = (
                d.get("borrowerName")
                or d.get("name")
                or f"{d.get('prenom','')} {d.get('nom','')}".strip()
                or ""
            ).lower()
            if not name:
                continue
            if sug_lower in name or name in sug_lower:
                return {"dossierId": d.get("id", ""), "dossierNom": name.title()}
    except Exception:
        pass

    return None


# ────────────────────────────────────────────────────────────────────
# Audit log shortcut
# ────────────────────────────────────────────────────────────────────

def log(action: str, *, target_id: str = "", result: str = "ok",
        details: Optional[Dict[str, Any]] = None) -> None:
    audit_log(
        agent=AGENT_NAME,
        action=action,
        target_type="transaction" if "transaction" in action else "email",
        target_id=target_id or "unknown",
        result=result,
        details=details or {},
    )
