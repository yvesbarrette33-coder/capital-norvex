"""Orchestrateur Béatrice — pipeline complet (lit yves@, drafte, notifie).

Coordination Camille ↔ Béatrice sur yves@ :
- Camille traite le juridique sur yves@ (legal_only_filter=True)
- Béatrice traite le NON-juridique non-personnel
- Dédup via Message-ID : si Camille a déjà traité, Béatrice skip

Mode : escalade systématique (autoSendSafe forcé à False).
Yves approuve chaque envoi via dashboard.
"""
from __future__ import annotations

from typing import Any, Dict, List

from agents.shared.agent_dedup import has_existing_draft_for_email
from agents.shared.firestore_client import audit_log
from agents.shared.maestro_check import should_skip_per_maestro
from agents.shared.no_reply_filter import is_auto_reply

# Réutilise les utilitaires Camille pour lire la boîte (Graph API)
from agents.camille_norvex_counsel.inbox_reader import (
    get_message_full,
    list_inbox_messages,
    mark_as_read,
    normalize_for_triage,
)

from . import audit as beatrice_audit
from .attachment_ingester import maybe_ingest_attachments_for_active_dossier
from .config import (
    AGENT_NAME,
    BEATRICE_DRAFTABLE_CATEGORIES,
    COLLECTION_DRAFTS,
    COLLECTION_EMAILS,
    MAILBOXES,
    YVES_APPROVAL_INBOX,
    is_legal_reserved_for_camille,
    is_mailbox_active,
    is_no_reply_sender,
    is_personal_yves,
)
from .drafting import draft_reply
from .triage import triage_email


def process_one_message(*, mailbox: str, raw_graph_message: Dict[str, Any],
                        auto_draft: bool = True) -> Dict[str, Any]:
    """Traite un message Graph : dédup → triage → drafte → notif Yves."""
    full = get_message_full(mailbox, raw_graph_message["id"])
    normalized = normalize_for_triage(mailbox, full)

    summary = {
        "email_doc_id": None,
        "mailbox": mailbox,
        "from": normalized["from"],
        "subject": normalized["subject"],
        "category": None,
        "priority": None,
        "draft_id": None,
        "drafted": False,
        "sent": False,
        "notified": False,
        "skip_reason": None,
        "mode": None,
    }

    # ── Maestro V2 : vérifie si Norvex Maestro™ a routé ailleurs ──
    # Rétro-compatible : si Maestro pas tourné, retourne False (continue).
    msg_id_internet = normalized.get("internet_message_id")
    if should_skip_per_maestro(msg_id_internet, my_route="to_beatrice"):
        summary["skip_reason"] = "maestro_routed_elsewhere"
        audit_log(agent=AGENT_NAME, action="skip_per_maestro",
                  target_type="incoming_email",
                  target_id=msg_id_internet or "unknown",
                  result="skipped", details={"mailbox": mailbox})
        return summary

    # ── Dédup pré-triage : déjà traité par Camille ou Sophie ? ────
    other_agent = beatrice_audit.is_already_processed_elsewhere(
        normalized.get("internet_message_id")
    )
    if other_agent:
        summary["skip_reason"] = f"already_processed_by_{other_agent}"
        audit_log(agent=AGENT_NAME, action="skip_dedup",
                  target_type="incoming_email",
                  target_id=normalized.get("internet_message_id") or "unknown",
                  result="skipped",
                  details={"other_agent": other_agent, "mailbox": mailbox})
        return summary

    # ── Dédup SELF (bug fix 2026-05-10) : Béatrice elle-même a-t-elle ──
    # déjà drafté CE Message-ID ? Si oui, skip silencieux pour éviter le
    # spam de rappels (cause des 8 rappels/h reçus par Yves le matin du
    # 2026-05-10). Voir agents/shared/agent_dedup.py.
    if has_existing_draft_for_email(
        internet_message_id=msg_id_internet,
        emails_collection=COLLECTION_EMAILS,
    ):
        summary["skip_reason"] = "already_drafted_by_self"
        audit_log(agent=AGENT_NAME, action="skip_dedup_self",
                  target_type="incoming_email",
                  target_id=msg_id_internet or "unknown",
                  result="skipped", details={"mailbox": mailbox})
        return summary

    # ── Pré-filtre no-reply / notifications / factures auto ───────
    # Yves : « il faut pas qu'on réponde à Microsoft, factures, pubs,
    # notifications. » → skip avant LLM (économie API + pas de bruit dashboard)
    if is_no_reply_sender(
        from_address=normalized.get("from", ""),
        subject=normalized.get("subject", ""),
    ):
        summary["skip_reason"] = "no_reply_sender_pre_filter"
        audit_log(agent=AGENT_NAME, action="skip_no_reply_pre_filter",
                  target_type="incoming_email",
                  target_id=normalized.get("internet_message_id") or "unknown",
                  result="skipped",
                  details={"mailbox": mailbox,
                           "from": normalized.get("from", "")[:200],
                           "subject": normalized.get("subject", "")[:200]})
        return summary

    # ── Pré-filtre auto-reply / out-of-office (FR + EN) ───────────
    # Yves 2026-05-07 : « ça vaut pas la peine de répondre à un robot
    # d'absence, on passe pour des amateurs ». Détection par sujet :
    # « Réponse automatique », « Automatic reply », « Out of office »...
    if is_auto_reply(subject=normalized.get("subject", "")):
        summary["skip_reason"] = "auto_reply_no_action"
        audit_log(agent=AGENT_NAME, action="skip_auto_reply",
                  target_type="incoming_email",
                  target_id=normalized.get("internet_message_id") or "unknown",
                  result="skipped",
                  details={"mailbox": mailbox,
                           "from": normalized.get("from", "")[:200],
                           "subject": normalized.get("subject", "")[:200]})
        return summary

    # ── Pré-filtre personnel (heuristique avant LLM) ──────────────
    if is_personal_yves(
        from_address=normalized.get("from", ""),
        subject=normalized.get("subject", ""),
        body_text=normalized.get("body_text", ""),
    ):
        summary["skip_reason"] = "personal_email_pre_filter"
        audit_log(agent=AGENT_NAME, action="skip_personal_pre_filter",
                  target_type="incoming_email",
                  target_id=normalized.get("internet_message_id") or "unknown",
                  result="skipped", details={"mailbox": mailbox})
        return summary

    # ── Ingest pièces jointes vers dossier actif (fix 2026-05-18) ───
    # Si l'email vient d'un client avec un dossier ACTIF ET contient des
    # pièces jointes, on télécharge automatiquement vers Firebase Storage
    # + on bump docsReceivedCount Firestore + notif Yves. Idempotent par
    # internet_message_id. Le triage continue normalement après pour que
    # Béatrice drafte l'accusé de réception à approuver par Yves.
    try:
        ingest_result = maybe_ingest_attachments_for_active_dossier(
            mailbox=mailbox,
            message_id=raw_graph_message["id"],
            internet_message_id=msg_id_internet or "",
            sender_email=normalized.get("from", ""),
            sender_name=normalized.get("from_name", "") or "",
            notify_yves_email=YVES_APPROVAL_INBOX,
        )
        summary["attachments_ingested"] = ingest_result.get("ingested_count", 0)
        summary["dossier_matched"] = ingest_result.get("dossier_id")
        if ingest_result.get("ingested_count"):
            audit_log(agent=AGENT_NAME, action="attachments_auto_ingested",
                      target_type="dossiers",
                      target_id=ingest_result.get("dossier_id") or "unknown",
                      result="success",
                      details={
                          "count": ingest_result["ingested_count"],
                          "messageId": msg_id_internet,
                          "files": [f["name"] for f in ingest_result.get("files", [])],
                      })
    except Exception as _e:
        # Ne casse pas le flow Béatrice même si l'ingestion échoue
        audit_log(agent=AGENT_NAME, action="attachments_ingest_error",
                  target_type="incoming_email",
                  target_id=msg_id_internet or "unknown",
                  result="error", details={"error": str(_e)[:500]})

    # ── Triage Sonnet 4.6 ────────────────────────────────────────
    triage = triage_email(
        from_address=normalized["from"],
        subject=normalized["subject"],
        body_text=normalized["body_text"],
        received_mailbox=mailbox,
        received_at_iso=normalized["received_at_iso"],
    )

    email_doc_id = beatrice_audit.store_incoming_email(
        normalized=normalized, triage=triage,
    )
    summary["email_doc_id"] = email_doc_id
    summary["category"] = triage["category"]
    summary["priority"] = triage["priority"]

    if not auto_draft:
        summary["skip_reason"] = "auto_draft=False"
        return summary

    # ── isPersonal détecté par le LLM ─────────────────────────────
    if triage.get("isPersonal") is True:
        summary["skip_reason"] = "personal_email_llm"
        audit_log(agent=AGENT_NAME, action="skip_personal_llm",
                  target_type=COLLECTION_DRAFTS, target_id=email_doc_id,
                  result="skipped")
        return summary

    # ── Coordination Camille : skip le juridique ──────────────────
    if is_legal_reserved_for_camille(triage["category"]):
        summary["skip_reason"] = (
            f"category={triage['category']} reserved for Camille"
        )
        audit_log(agent=AGENT_NAME, action="skip_for_camille",
                  target_type=COLLECTION_DRAFTS, target_id=email_doc_id,
                  result="skipped",
                  details={"category": triage["category"]})
        return summary

    # ── Catégories techniques non-draftables ──────────────────────
    if triage["category"] in {"interne", "spam"}:
        summary["skip_reason"] = f"category={triage['category']} not draftable"
        return summary

    # ── Catégories Béatrice valides ───────────────────────────────
    if triage["category"] not in BEATRICE_DRAFTABLE_CATEGORIES:
        summary["skip_reason"] = (
            f"category={triage['category']} not in BEATRICE_DRAFTABLE_CATEGORIES"
        )
        return summary

    # ── Sécurité : prompt injection ───────────────────────────────
    if "prompt_injection_attempt" in (triage.get("redFlags") or []):
        summary["skip_reason"] = "prompt_injection_detected"
        audit_log(agent=AGENT_NAME, action="skip_drafting_security",
                  target_type=COLLECTION_DRAFTS, target_id=email_doc_id,
                  result="blocked")
        return summary

    # ── Drafting Opus 4.6 (ghostwriter Yves) ──────────────────────
    incoming_payload = {
        "from": normalized["from"], "to": normalized["to"], "cc": normalized["cc"],
        "subject": normalized["subject"], "body_text": normalized["body_text"],
    }
    try:
        draft = draft_reply(source_mailbox=mailbox, incoming_email=incoming_payload,
                            triage_result=triage)
    except Exception as e:
        summary["skip_reason"] = f"drafting_error: {e}"
        audit_log(agent=AGENT_NAME, action="drafting_failed",
                  target_type=COLLECTION_DRAFTS, target_id=email_doc_id,
                  result="error", details={"error": str(e)[:500]})
        return summary

    # ── Stockage draft ────────────────────────────────────────────
    # Béatrice : autoSendSafe TOUJOURS False → toujours pending_yves_approval
    cc_list: List[str] = []  # Pas de CC : c'est la boîte d'Yves lui-même
    initial_status = "pending_yves_approval"

    draft_id = beatrice_audit.store_draft(
        incoming_email_id=email_doc_id, source_mailbox=mailbox,
        draft=draft, triage=triage, to_recipient=normalized["from"],
        cc_recipients=cc_list, initial_status=initial_status,
        auto_send_reason="",
    )
    summary["drafted"] = True
    summary["draft_id"] = draft_id

    # ── ESCALADE : notif approbation Yves (3 boutons) ─────────────
    beatrice_audit.send_escalation_notification_to_yves(
        draft_id=draft_id, subject=draft["subject"],
        to_recipient=normalized["from"], summary=triage.get("summary", ""),
        body_html_preview=draft.get("signed_html") or draft.get("body_html") or "",
        cc_recipients=cc_list, source_mailbox=mailbox,
    )
    summary["notified"] = True
    summary["mode"] = "escalation"
    return summary


def process_inbox(mailbox: str, *, top: int = 25, only_unread: bool = True,
                  auto_draft: bool = True, mark_read_after: bool = False) -> List[Dict[str, Any]]:
    if not is_mailbox_active(mailbox):
        raise RuntimeError(f"Boîte non configurée pour Béatrice : {mailbox}")
    messages = list_inbox_messages(mailbox, top=top, only_unread=only_unread)
    results = []
    for raw in messages:
        try:
            res = process_one_message(mailbox=mailbox, raw_graph_message=raw,
                                       auto_draft=auto_draft)
            results.append(res)
            if mark_read_after and res.get("drafted"):
                mark_as_read(mailbox, raw["id"])
        except Exception as e:
            audit_log(agent=AGENT_NAME, action="process_message_error",
                      target_type="graph_message", target_id=raw.get("id", "unknown"),
                      result="error", details={"error": str(e)[:500], "mailbox": mailbox})
            results.append({"graph_id": raw.get("id"), "mailbox": mailbox,
                            "error": str(e)[:500]})
    return results


def process_all_mailboxes(*, top: int = 25, only_unread: bool = True,
                          auto_draft: bool = True, mark_read_after: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    out = {}
    for mailbox in MAILBOXES.keys():
        try:
            out[mailbox] = process_inbox(mailbox, top=top, only_unread=only_unread,
                                          auto_draft=auto_draft, mark_read_after=mark_read_after)
        except Exception as e:
            out[mailbox] = [{"error": str(e)[:500]}]
    return out
