"""Orchestrateur Karine NORVEX FINANCE™ — flow principal."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

# Réutilise les utilitaires inbox de Camille (Microsoft Graph)
from agents.camille_norvex_counsel.inbox_reader import (
    get_message_full,
    list_inbox_messages,
    mark_as_read,
    normalize_for_triage,
)
# Module partagé pour télécharger les attachments
from agents.shared.graph_attachments import (
    download_attachment,
    list_attachments,
)
# Coordination Maestro V2
from agents.shared.maestro_check import should_skip_per_maestro

from . import audit as karine_audit
from .config import (
    AGENT_NAME,
    MAILBOXES,
    is_mailbox_active,
)
from .extractor import extract_with_karine
from .triage import is_likely_financial, triage_email

log = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Traitement d'un message
# ────────────────────────────────────────────────────────────────────
def process_one_message(*, mailbox: str, raw_graph_message: Dict[str, Any]
                        ) -> Dict[str, Any]:
    full = get_message_full(mailbox, raw_graph_message["id"])
    normalized = normalize_for_triage(mailbox, full)
    # Charge les métadonnées des attachments (sans télécharger le contenu)
    try:
        attachments = list_attachments(mailbox, raw_graph_message["id"])
    except Exception:
        attachments = []

    summary: Dict[str, Any] = {
        "mailbox": mailbox,
        "from": normalized.get("from"),
        "subject": normalized.get("subject"),
        "category_triage": None,
        "transactions_created": [],
        "skipped": None,
    }

    msg_id = normalized.get("internet_message_id")

    # ── Maestro V2 : skip si routé ailleurs ─────────────────────────
    if should_skip_per_maestro(msg_id, my_route="to_karine"):
        summary["skipped"] = "maestro_routed_elsewhere"
        karine_audit.mark_email_as_processed(
            internet_message_id=msg_id, mailbox=mailbox,
            category="maestro_routed_elsewhere",
            summary="Skipped per Maestro routing",
        )
        return summary

    # ── Anti-doublon ────────────────────────────────────────────────
    if karine_audit.is_email_already_processed(msg_id):
        summary["skipped"] = "already_processed"
        return summary

    # ── Pré-filtre rapide (économie API) ────────────────────────────
    if not is_likely_financial(
        from_address=normalized.get("from", ""),
        subject=normalized.get("subject", ""),
        body_text=normalized.get("body_text", ""),
        attachments=[
            {"name": a.get("name", ""), "contentType": a.get("contentType", "")}
            for a in attachments
        ],
    ):
        summary["skipped"] = "pre_filter_not_financial"
        karine_audit.mark_email_as_processed(
            internet_message_id=msg_id, mailbox=mailbox,
            category="non_financier_pre_filter",
            summary="Skipped by pre-filter",
        )
        return summary

    # ── Triage Sonnet 4.6 ───────────────────────────────────────────
    triage = triage_email(
        from_address=normalized.get("from", ""),
        subject=normalized.get("subject", ""),
        body_text=normalized.get("body_text", ""),
        attachments=[
            {"name": a.get("name", ""), "contentType": a.get("contentType", "")}
            for a in attachments
        ],
        received_at_iso=normalized.get("received_at_iso", ""),
    )
    summary["category_triage"] = triage.get("category")

    karine_audit.log("triage_done", target_id=msg_id or "unknown",
                     details={"category": triage.get("category"),
                              "confidence": triage.get("confidence"),
                              "mailbox": mailbox})

    # ── Si non-financier ou releve_bancaire ou fiscal : skip création tx
    if triage.get("category") in {"non_financier", "releve_bancaire", "fiscal"}:
        summary["skipped"] = f"category={triage.get('category')}"
        karine_audit.mark_email_as_processed(
            internet_message_id=msg_id, mailbox=mailbox,
            category=triage.get("category"),
            summary=triage.get("summary", ""),
        )
        return summary

    # ── Extraire chaque PDF/image attaché ───────────────────────────
    extractable_attachments = [
        a for a in attachments
        if (a.get("contentType") or "").lower() in {
            "application/pdf", "image/jpeg", "image/png", "image/webp"
        } or (a.get("name") or "").lower().endswith(
            (".pdf", ".jpg", ".jpeg", ".png", ".webp")
        )
    ]

    if not extractable_attachments:
        summary["skipped"] = "no_extractable_attachment"
        karine_audit.mark_email_as_processed(
            internet_message_id=msg_id, mailbox=mailbox,
            category=triage.get("category"),
            summary="No PDF/image to extract",
        )
        return summary

    email_context = {
        "from": normalized.get("from", ""),
        "subject": normalized.get("subject", ""),
        "body_text": normalized.get("body_text", ""),
        "received_at_iso": normalized.get("received_at_iso", ""),
        "category_triage": triage.get("category"),
    }

    for att in extractable_attachments:
        try:
            pdf_bytes = download_attachment(mailbox, raw_graph_message["id"],
                                            att["id"])
        except Exception as e:
            karine_audit.log("attachment_download_failed",
                             target_id=msg_id or "unknown",
                             result="error",
                             details={"error": str(e)[:300],
                                      "attachment": att.get("name")})
            continue

        media_type = att.get("contentType") or "application/pdf"

        extracted = extract_with_karine(
            pdf_bytes=pdf_bytes,
            media_type=media_type,
            email_context=email_context,
        )
        if not extracted:
            continue

        # ── Détection doublon ────────────────────────────────────────
        dup = karine_audit.is_duplicate_invoice(
            fournisseur=extracted.get("fournisseur_ou_payeur") or "",
            numero=extracted.get("numero_facture") or "",
            montant_total=float(extracted.get("montant_total", 0)),
            date=extracted.get("date") or "",
        )
        if dup:
            karine_audit.log("duplicate_invoice_detected",
                             target_id=dup,
                             result="skipped",
                             details={"fournisseur":
                                      extracted.get("fournisseur_ou_payeur"),
                                      "numero":
                                      extracted.get("numero_facture")})
            continue

        # ── Lien dossier client ──────────────────────────────────────
        dossier_link = karine_audit.try_link_to_dossier(extracted)
        if dossier_link:
            extracted["dossier_link_suggestion"] = dossier_link.get("dossierId", "")

        # ── Création transaction pending ─────────────────────────────
        try:
            tx_id = karine_audit.create_pending_transaction(
                extracted=extracted,
                source_email=email_context,
                pdf_blob_key=None,  # V2 : upload du PDF pour preview UI
            )
            if dossier_link:
                # Compléter dossierNom après création
                from agents.shared.firestore_client import update
                update("transactions", tx_id, {"dossierNom":
                                                dossier_link.get("dossierNom",
                                                                  "")})
            summary["transactions_created"].append({
                "id": tx_id,
                "type": extracted.get("type"),
                "categorie": extracted.get("categorie"),
                "montant": extracted.get("montant_total"),
                "fournisseur": extracted.get("fournisseur_ou_payeur"),
                "requires_yves_review": extracted.get("requires_yves_review"),
            })
            karine_audit.log("transaction_created",
                             target_id=tx_id, result="ok",
                             details={"type": extracted.get("type"),
                                      "categorie": extracted.get("categorie"),
                                      "montant": extracted.get("montant_total"),
                                      "confidence":
                                      extracted.get("confidence")})
        except Exception as e:
            karine_audit.log("transaction_create_failed",
                             target_id=msg_id or "unknown",
                             result="error",
                             details={"error": str(e)[:300]})

    karine_audit.mark_email_as_processed(
        internet_message_id=msg_id, mailbox=mailbox,
        category=triage.get("category"),
        summary=triage.get("summary", ""),
    )

    return summary


def process_inbox(mailbox: str, *, top: int = 25,
                  only_unread: bool = True,
                  mark_read_after: bool = False) -> List[Dict[str, Any]]:
    if not is_mailbox_active(mailbox):
        raise RuntimeError(f"Boîte non configurée pour Karine : {mailbox}")
    messages = list_inbox_messages(mailbox, top=top, only_unread=only_unread)
    results: List[Dict[str, Any]] = []
    for raw in messages:
        try:
            res = process_one_message(mailbox=mailbox, raw_graph_message=raw)
            results.append(res)
            # Karine NE marque PAS l'email comme lu (laissé pour Béatrice/Sophie)
            # sauf si l'opérateur le demande explicitement
            if mark_read_after and res.get("transactions_created"):
                mark_as_read(mailbox, raw["id"])
        except Exception as e:
            karine_audit.log("process_message_error",
                             target_id=raw.get("id", "unknown"),
                             result="error",
                             details={"error": str(e)[:300],
                                      "mailbox": mailbox})
            results.append({"graph_id": raw.get("id"),
                            "mailbox": mailbox,
                            "error": str(e)[:300]})
    return results


def process_all_mailboxes(*, top: int = 25, only_unread: bool = True,
                          mark_read_after: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for mailbox in MAILBOXES.keys():
        if not is_mailbox_active(mailbox):
            continue
        try:
            out[mailbox] = process_inbox(mailbox, top=top,
                                          only_unread=only_unread,
                                          mark_read_after=mark_read_after)
        except Exception as e:
            out[mailbox] = [{"error": str(e)[:300]}]
    return out
