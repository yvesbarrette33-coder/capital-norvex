"""Orchestrateur Sophie — pipeline complet (lit info@, drafte, envoie ou escalade).

Coordination Camille ↔ Sophie sur info@ :
- Sophie lit info@
- Si triage = "juridique_pour_camille" → Sophie SKIP (Camille gérera)
- Sinon → Sophie drafte + envoie (auto-send par défaut, Yves CC)
"""
from __future__ import annotations

from typing import Any, Dict, List

from agents.shared.agent_dedup import has_existing_draft_for_email
from agents.shared.firestore_client import audit_log
from agents.shared.maestro_check import should_skip_per_maestro
from agents.shared.no_reply_filter import is_no_reply_sender, is_auto_reply

# Réutilise les utilitaires Camille pour lire la boîte (Graph API)
from agents.camille_norvex_counsel.inbox_reader import (
    get_message_full,
    list_inbox_messages,
    mark_as_read,
    normalize_for_triage,
)
# Réutilise sender Camille (envoi via Graph + CC)
from agents.camille_norvex_counsel.sender import send_email_with_cc

from . import audit as sophie_audit
from .config import (
    AGENT_NAME,
    COLLECTION_DRAFTS,
    COLLECTION_EMAILS,
    MAILBOXES,
    SOPHIE_DRAFTABLE_CATEGORIES,
    get_cc_list,
    is_legal_reserved_for_camille,
    is_mailbox_active,
)
from .drafting import draft_reply
from .triage import triage_email


def process_one_message(*, mailbox: str, raw_graph_message: Dict[str, Any],
                        auto_draft: bool = True) -> Dict[str, Any]:
    """Traite un message Graph : triage → store → drafte ou skip."""
    full = get_message_full(mailbox, raw_graph_message["id"])
    normalized = normalize_for_triage(mailbox, full)

    msg_id_internet = normalized.get("internet_message_id")

    # ── Dédup SELF (bug fix 2026-05-10) : Sophie a-t-elle déjà drafté ──
    # CE Message-ID ? Si oui, skip silencieux (évite re-triage / re-draft /
    # re-notif aux 10 min). Voir agents/shared/agent_dedup.py.
    if has_existing_draft_for_email(
        internet_message_id=msg_id_internet,
        emails_collection=COLLECTION_EMAILS,
    ):
        audit_log(agent=AGENT_NAME, action="skip_dedup_self",
                  target_type="incoming_email",
                  target_id=msg_id_internet or "unknown",
                  result="skipped", details={"mailbox": mailbox})
        return {
            "email_doc_id": None, "mailbox": mailbox,
            "from": normalized["from"], "subject": normalized["subject"],
            "category": None, "priority": None,
            "draft_id": None, "drafted": False, "sent": False,
            "notified": False, "skip_reason": "already_drafted_by_self",
            "mode": None,
        }

    # ── Maestro V2 : skip si routé ailleurs ───────────────────────
    if should_skip_per_maestro(msg_id_internet, my_route="to_sophie"):
        audit_log(agent=AGENT_NAME, action="skip_per_maestro",
                  target_type="incoming_email",
                  target_id=msg_id_internet or "unknown",
                  result="skipped", details={"mailbox": mailbox})
        return {
            "email_doc_id": None, "mailbox": mailbox,
            "from": normalized["from"], "subject": normalized["subject"],
            "category": None, "priority": None,
            "draft_id": None, "drafted": False, "sent": False,
            "notified": False, "skip_reason": "maestro_routed_elsewhere",
            "mode": None,
        }

    # ── Pré-filtre no-reply / notifications / factures auto ───────
    # Yves 2026-05-04 : « pas de réponse à Microsoft, factures, pubs,
    # notifications. » → skip avant LLM (économie API + dashboard propre)
    if is_no_reply_sender(
        from_address=normalized.get("from", ""),
        subject=normalized.get("subject", ""),
    ) or is_auto_reply(subject=normalized.get("subject", "")):
        action_name = (
            "skip_auto_reply"
            if is_auto_reply(subject=normalized.get("subject", ""))
            else "skip_no_reply_pre_filter"
        )
        audit_log(agent=AGENT_NAME, action=action_name,
                  target_type="incoming_email",
                  target_id=normalized.get("internet_message_id") or "unknown",
                  result="skipped",
                  details={"mailbox": mailbox,
                           "from": normalized.get("from", "")[:200],
                           "subject": normalized.get("subject", "")[:200]})
        return {
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
            "skip_reason": "no_reply_sender_pre_filter",
            "mode": None,
        }

    triage = triage_email(
        from_address=normalized["from"],
        subject=normalized["subject"],
        body_text=normalized["body_text"],
        received_mailbox=mailbox,
        received_at_iso=normalized["received_at_iso"],
    )

    email_doc_id = sophie_audit.store_incoming_email(normalized=normalized, triage=triage)

    summary = {
        "email_doc_id": email_doc_id,
        "mailbox": mailbox,
        "from": normalized["from"],
        "subject": normalized["subject"],
        "category": triage["category"],
        "priority": triage["priority"],
        "draft_id": None,
        "drafted": False,
        "sent": False,
        "notified": False,
        "skip_reason": None,
        "mode": None,
    }

    if not auto_draft:
        summary["skip_reason"] = "auto_draft=False"
        return summary

    # ── Coordination Camille : skip le juridique ─────────────────
    if is_legal_reserved_for_camille(triage["category"]) or triage["category"] == "juridique_pour_camille":
        summary["skip_reason"] = f"category={triage['category']} reserved for Camille"
        audit_log(agent=AGENT_NAME, action="skip_for_camille",
                  target_type=COLLECTION_DRAFTS, target_id=email_doc_id,
                  result="skipped")
        return summary

    # ── Catégories qui méritent un draft ─────────────────────────
    if triage["category"] not in SOPHIE_DRAFTABLE_CATEGORIES and triage["category"] != "autre_general":
        summary["skip_reason"] = f"category={triage['category']} not draftable for Sophie"
        return summary

    # ── Sécurité : prompt injection ──────────────────────────────
    if "prompt_injection_attempt" in (triage.get("redFlags") or []):
        summary["skip_reason"] = "prompt_injection_detected"
        audit_log(agent=AGENT_NAME, action="skip_drafting_security",
                  target_type=COLLECTION_DRAFTS, target_id=email_doc_id, result="blocked")
        return summary

    # ── Drafting Opus 4.6 ────────────────────────────────────────
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

    # ── Stockage draft + branche envoi ───────────────────────────
    auto_send_effective = bool(triage.get("autoSendSafe"))
    # Architecture scalable Yves 2026-05-04 : Yves CC SEULEMENT sur catégories
    # sensibles (media/litige/strategique/etc.). Le routine = pas de CC.
    cc_list = get_cc_list(mailbox, category=triage.get("category"))
    initial_status = "auto_send_pending" if auto_send_effective else "pending_yves_approval"
    auto_send_reason = triage.get("autoSendReason") or "Sophie autonomie day-to-day"

    draft_id = sophie_audit.store_draft(
        incoming_email_id=email_doc_id, source_mailbox=mailbox,
        draft=draft, triage=triage, to_recipient=normalized["from"],
        cc_recipients=cc_list, initial_status=initial_status,
        auto_send_reason=auto_send_reason,
    )
    summary["drafted"] = True
    summary["draft_id"] = draft_id

    if auto_send_effective:
        send_ok = send_email_with_cc(
            to=normalized["from"], subject=draft["subject"],
            html=draft["signed_html"], from_user=mailbox, cc=cc_list,
        )
        if send_ok:
            sophie_audit.mark_draft_sent(draft_id, sent_via="auto_send_sophie")
            sophie_audit.notify_yves_sophie_auto_sent(
                draft_id=draft_id, subject=draft["subject"],
                to_recipient=normalized["from"], summary=triage.get("summary", ""),
                body_html_preview=draft.get("signed_html") or draft.get("body_html") or "",
                cc_recipients=cc_list, source_mailbox=mailbox,
                auto_send_reason=auto_send_reason,
            )
            summary["sent"] = True
            summary["notified"] = True
            summary["mode"] = "auto_send"
        else:
            # Fallback escalade si envoi échoue
            sophie_audit.notify_yves_for_sophie_draft(
                draft_id=draft_id, subject=draft["subject"],
                to_recipient=normalized["from"],
                summary=triage.get("summary", "(échec auto-send → approbation requise)"),
                body_html_preview=draft.get("signed_html") or draft.get("body_html") or "",
                cc_recipients=cc_list, source_mailbox=mailbox,
            )
            summary["mode"] = "auto_send_failed_to_escalation"
        return summary

    # ── ESCALADE : notif approbation Yves (3 boutons) ────────────
    sophie_audit.notify_yves_for_sophie_draft(
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
        raise RuntimeError(f"Boîte non configurée pour Sophie : {mailbox}")
    messages = list_inbox_messages(mailbox, top=top, only_unread=only_unread)
    results = []
    for raw in messages:
        try:
            res = process_one_message(mailbox=mailbox, raw_graph_message=raw, auto_draft=auto_draft)
            results.append(res)
            if mark_read_after and res.get("drafted"):
                mark_as_read(mailbox, raw["id"])
        except Exception as e:
            audit_log(agent=AGENT_NAME, action="process_message_error",
                      target_type="graph_message", target_id=raw.get("id", "unknown"),
                      result="error", details={"error": str(e)[:500], "mailbox": mailbox})
            results.append({"graph_id": raw.get("id"), "mailbox": mailbox, "error": str(e)[:500]})
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
