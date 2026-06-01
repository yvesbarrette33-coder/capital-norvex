"""Audit Maestro — Firestore writes (dispatch + observations)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agents.shared.firestore_client import (
    audit_log, create, db, query,
)

from .config import (
    AGENT_NAME,
    COLLECTION_DISPATCH,
    COLLECTION_OBSERVATIONS,
)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_message_already_dispatched(internet_message_id: Optional[str]) -> bool:
    """Vrai si Maestro a déjà routé ce Message-ID."""
    if not internet_message_id:
        return False
    safe_id = (internet_message_id.replace("/", "_")
               .replace("#", "_")[:200])
    snap = db().collection(COLLECTION_DISPATCH).document(safe_id).get()
    return snap.exists


def store_dispatch(*, internet_message_id: str, mailbox: str,
                   from_address: str, subject: str,
                   triage_result: Dict[str, Any]) -> str:
    """Enregistre la décision de routing pour ce Message-ID."""
    if not internet_message_id:
        return ""
    safe_id = (internet_message_id.replace("/", "_")
               .replace("#", "_")[:200])

    payload = {
        "messageId": internet_message_id,
        "mailbox": mailbox,
        "from": from_address[:200],
        "subject": (subject or "")[:300],
        "route": triage_result.get("route", "to_yves_directly"),
        "confidence": triage_result.get("confidence", 0),
        "reasoning": (triage_result.get("reasoning") or "")[:500],
        "secondary_relevance": triage_result.get("secondary_relevance", []),
        "alert_yves_now": bool(triage_result.get("alert_yves_now", False)),
        "estimated_priority": triage_result.get("estimated_priority", "medium"),
        "summary": (triage_result.get("summary") or "")[:300],
        "language": triage_result.get("language", "fr"),
        "dispatchedAt": now_utc_iso(),
        "agent": AGENT_NAME,
    }
    db().collection(COLLECTION_DISPATCH).document(safe_id).set(payload)
    return safe_id


def get_dispatch_for_message(internet_message_id: str) -> Optional[Dict[str, Any]]:
    """Permet aux agents spécialistes (Camille/Sophie/Béatrice/Karine) de
    vérifier la décision de Maestro avant de drafter (futur usage)."""
    if not internet_message_id:
        return None
    safe_id = (internet_message_id.replace("/", "_")
               .replace("#", "_")[:200])
    snap = db().collection(COLLECTION_DISPATCH).document(safe_id).get()
    return snap.to_dict() if snap.exists else None


def list_recent_dispatches(*, hours: int = 24,
                            limit: int = 200) -> List[Dict[str, Any]]:
    """Liste les dispatches Maestro des N dernières heures pour le brief."""
    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
    try:
        results = query(
            COLLECTION_DISPATCH,
            filters=[("dispatchedAt", ">=", cutoff_iso)],
            order_by="dispatchedAt",
            limit=limit,
        )
        return results
    except Exception:
        # Fallback : query sans filter si index manquant
        try:
            return query(COLLECTION_DISPATCH, limit=limit)
        except Exception:
            return []


def store_observation(*, kind: str, payload: Dict[str, Any]) -> str:
    """Enregistre une observation Maestro (alerte, opportunité, anomalie)."""
    data = {
        "kind": kind,
        "payload": payload,
        "createdAt": now_utc_iso(),
        "agent": AGENT_NAME,
    }
    return create(COLLECTION_OBSERVATIONS, data)


def log(action: str, *, target_id: str = "", result: str = "ok",
        details: Optional[Dict[str, Any]] = None) -> None:
    audit_log(
        agent=AGENT_NAME,
        action=action,
        target_type="dispatch",
        target_id=target_id or "unknown",
        result=result,
        details=details or {},
    )
