"""Orchestrateur Norvex Maestro™ — boucle principale de méta-triage."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from agents.camille_norvex_counsel.inbox_reader import (
    get_message_full,
    list_inbox_messages,
    normalize_for_triage,
)
from agents.shared.outreach_targets_lookup import lookup_outreach_target

from . import audit as maestro_audit
from .config import AGENT_NAME, MAILBOXES
from .triage import meta_triage


# Règle verrouillée 26 mai 2026 PM : tout email d'une cible outreach active
# DOIT être routé à Béatrice/Sophie/Camille pour réponse courtoise. JAMAIS
# `ignore_no_reply`. Mapping (collection, mailbox) -> route :
#   - capitalTargets    → Béatrice si yves@, sinon Sophie
#   - promoteurTargets  → Béatrice si yves@, sinon Sophie
#   - brokers           → Sophie (operationnel)
#   - advisorTargets    → Camille (avocat-à-avocat, comptable, PWM)
def _force_route_for_outreach_target(collection: str, mailbox: str) -> str:
    mb = (mailbox or "").lower()
    is_yves = mb.startswith("yves@")
    if collection == "advisorTargets":
        return "to_camille"
    if collection == "brokers":
        return "to_sophie"
    # capitalTargets / promoteurTargets
    return "to_beatrice" if is_yves else "to_sophie"

log = logging.getLogger(__name__)


def process_one_message(*, mailbox: str,
                         raw_graph_message: Dict[str, Any]) -> Dict[str, Any]:
    """Méta-triage d'un message : décide qui doit le traiter.

    Maestro NE drafte PAS. Il enregistre seulement la décision dans
    Firestore (`maestroDispatch`) pour que les agents spécialistes
    puissent la consulter (futur).
    """
    summary: Dict[str, Any] = {
        "mailbox": mailbox,
        "graph_id": raw_graph_message.get("id"),
        "skipped": None,
        "route": None,
        "alert": False,
    }

    # Charge le message complet (corps + headers)
    try:
        full = get_message_full(mailbox, raw_graph_message["id"])
    except Exception as e:
        maestro_audit.log("get_message_full_failed",
                          target_id=raw_graph_message.get("id", "unknown"),
                          result="error", details={"error": str(e)[:200],
                                                   "mailbox": mailbox})
        summary["skipped"] = "get_message_full_failed"
        return summary

    normalized = normalize_for_triage(mailbox, full)
    msg_id = normalized.get("internet_message_id")
    summary["from"] = normalized.get("from")
    summary["subject"] = normalized.get("subject")

    # Anti-doublon : Maestro a-t-il déjà routé ce Message-ID ?
    if maestro_audit.is_message_already_dispatched(msg_id):
        summary["skipped"] = "already_dispatched"
        return summary

    # Anti self-send (bug fix 2026-05-08) : si Yves/info@ s'auto-envoie (BCC
    # sur ses propres outbound, ou copie carbone des 588 envois d'hier), on ne
    # route PAS vers un agent. Ces emails sont OUTBOUND déjà envoyés, pas des
    # messages entrants à drafter. Sans ça, Maestro envoie 588 dispatches vers
    # Béatrice qui essaie de drafter des réponses fantômes.
    from_addr = (normalized.get("from") or "").strip().lower()
    mailbox_addr = (mailbox or "").strip().lower()
    if from_addr and mailbox_addr and from_addr == mailbox_addr:
        maestro_audit.log("self_send_skipped",
                          target_id=msg_id or "unknown",
                          details={"mailbox": mailbox,
                                   "subject": (normalized.get("subject") or "")[:200]})
        summary["skipped"] = "self_send"
        return summary

    # ── Override outreach targets (règle verrouillée 26 mai 2026 PM) ──
    # Si l'expéditeur est une cible outreach active dans Firestore, on bypass
    # le LLM triage et on force la route vers l'agent qui rédigera la réponse
    # courtoise. Évite la classification accidentelle en `ignore_no_reply`
    # sur du boilerplate institutionnel (cas Prime Quadrant 26 mai 2026).
    outreach_hit = lookup_outreach_target(from_addr) if from_addr else None
    if outreach_hit:
        forced_route = _force_route_for_outreach_target(
            outreach_hit["collection"], mailbox)
        triage = {
            "route": forced_route,
            "alert_yves_now": True,
            "summary": (f"Réponse d'une cible outreach active "
                        f"({outreach_hit['collection']} / "
                        f"{outreach_hit.get('organization') or '?'} / "
                        f"{outreach_hit.get('name') or '?'}). "
                        f"Réponse courtoise obligatoire — JAMAIS ignorer."),
            "reasoning": ("Override Maestro : expéditeur trouvé dans Firestore "
                          f"outreach targets ({outreach_hit['collection']} "
                          f"doc={outreach_hit['docId']}, lastSentAt="
                          f"{outreach_hit.get('lastSentAt') or 'n/a'}). "
                          "Règle 26 mai 2026 PM : pas d'ignore_no_reply sur "
                          "cibles outreach actives."),
            "confidence": 1.0,
            "estimated_priority": "high",
            "outreach_target_override": True,
            "outreach_collection": outreach_hit["collection"],
            "outreach_doc_id": outreach_hit["docId"],
        }
        maestro_audit.log("outreach_target_force_route",
                          target_id=msg_id or "unknown",
                          details={"mailbox": mailbox,
                                   "from": from_addr,
                                   "collection": outreach_hit["collection"],
                                   "docId": outreach_hit["docId"],
                                   "forced_route": forced_route,
                                   "organization": outreach_hit.get("organization", ""),
                                   "subject": (normalized.get("subject") or "")[:200]})
    else:
        # Méta-triage Sonnet 4.6 (chemin normal)
        triage = meta_triage(
            mailbox=mailbox,
            from_address=normalized.get("from", ""),
            subject=normalized.get("subject", ""),
            body_text=normalized.get("body_text", ""),
            has_attachments=bool(normalized.get("has_attachments")),
            received_at_iso=normalized.get("received_at_iso", ""),
        )
    summary["route"] = triage.get("route")
    summary["alert"] = bool(triage.get("alert_yves_now"))
    summary["priority"] = triage.get("estimated_priority")

    # Enregistre la décision
    maestro_audit.store_dispatch(
        internet_message_id=msg_id or "unknown",
        mailbox=mailbox,
        from_address=normalized.get("from", ""),
        subject=normalized.get("subject", ""),
        triage_result=triage,
    )

    # Audit log
    maestro_audit.log("dispatch_done",
                      target_id=msg_id or "unknown",
                      details={"route": triage.get("route"),
                               "priority": triage.get("estimated_priority"),
                               "confidence": triage.get("confidence"),
                               "mailbox": mailbox})

    # Si alert_yves_now → observation enregistrée (UI Brain pourra l'afficher)
    if triage.get("alert_yves_now"):
        maestro_audit.store_observation(
            kind="urgent_email",
            payload={
                "messageId": msg_id,
                "mailbox": mailbox,
                "from": normalized.get("from", ""),
                "subject": normalized.get("subject", ""),
                "summary": triage.get("summary", ""),
                "reasoning": triage.get("reasoning", ""),
                "priority": triage.get("estimated_priority"),
            },
        )

    return summary


def process_inbox(mailbox: str, *, top: int = 50,
                   only_unread: bool = True) -> List[Dict[str, Any]]:
    """Lit la boîte et méta-trie chaque message."""
    messages = list_inbox_messages(mailbox, top=top, only_unread=only_unread)
    results: List[Dict[str, Any]] = []
    for raw in messages:
        try:
            res = process_one_message(mailbox=mailbox, raw_graph_message=raw)
            results.append(res)
        except Exception as e:
            maestro_audit.log("process_message_error",
                              target_id=raw.get("id", "unknown"),
                              result="error",
                              details={"error": str(e)[:300],
                                       "mailbox": mailbox})
            results.append({"graph_id": raw.get("id"),
                            "mailbox": mailbox,
                            "error": str(e)[:300]})
    return results


def process_all_mailboxes(*, top: int = 50,
                           only_unread: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for mailbox in MAILBOXES:
        try:
            out[mailbox] = process_inbox(mailbox, top=top,
                                          only_unread=only_unread)
        except Exception as e:
            out[mailbox] = [{"error": str(e)[:300]}]
    return out
