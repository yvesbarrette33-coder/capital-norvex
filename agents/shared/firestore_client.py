"""Helpers Firestore pour les 3 agents.

Wrappers simples au-dessus de l'Admin SDK pour rester cohérent et
journaliser dans agentAuditLog.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from .auth import get_firestore


def db():
    """Raccourci pour le client Firestore."""
    return get_firestore()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create(collection: str, data: Dict[str, Any], doc_id: Optional[str] = None) -> str:
    """Crée un document. Retourne l'ID."""
    data = {**data, "createdAt": now_utc(), "lastUpdated": now_utc()}
    col = db().collection(collection)
    if doc_id:
        col.document(doc_id).set(data)
        return doc_id
    ref = col.add(data)[1]
    return ref.id


def update(collection: str, doc_id: str, data: Dict[str, Any]) -> None:
    """Met à jour un document existant. Met lastUpdated à now."""
    data = {**data, "lastUpdated": now_utc()}
    db().collection(collection).document(doc_id).update(data)


def get(collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
    snap = db().collection(collection).document(doc_id).get()
    if not snap.exists:
        return None
    d = snap.to_dict()
    d["id"] = snap.id
    return d


def query(
    collection: str,
    filters: Optional[List[tuple]] = None,
    order_by: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Requête simple. filters = [('field', 'op', value), ...]."""
    q = db().collection(collection)
    for field, op, value in filters or []:
        q = q.where(field, op, value)
    if order_by:
        q = q.order_by(order_by)
    if limit:
        q = q.limit(limit)
    out = []
    for snap in q.stream():
        d = snap.to_dict()
        d["id"] = snap.id
        out.append(d)
    return out


def delete(collection: str, doc_id: str) -> None:
    db().collection(collection).document(doc_id).delete()


def audit_log(
    agent: str,
    action: str,
    *,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    result: str = "success",
    details: Optional[Dict[str, Any]] = None,
) -> str:
    """Journalise une action dans agentAuditLog. Retourne l'ID du log."""
    return create(
        "agentAuditLog",
        {
            "timestamp": now_utc(),
            "agent": agent,
            "action": action,
            "targetType": target_type,
            "targetId": target_id,
            "result": result,
            "details": details or {},
        },
    )
