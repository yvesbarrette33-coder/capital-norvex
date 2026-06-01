"""Agent COURTIERS — gestion des relations courtiers.

Met à jour `relationshipStatus` selon l'activité, identifie les warms
sans deal récent, et signale les champions (top 5 producteurs).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from ..shared import firestore_client as fs

AGENT_NAME = "courtiers"

THRESHOLD_CHAMPION_DEALS_RECEIVED = 5


def update_status_after_deal_received(broker_id: str) -> None:
    """À appeler quand un nouveau deal arrive d'un courtier."""
    b = fs.get("brokers", broker_id)
    if not b:
        return

    received = (b.get("dealsReceived") or 0) + 1
    new_status = b.get("relationshipStatus") or "cold"

    if received >= THRESHOLD_CHAMPION_DEALS_RECEIVED:
        new_status = "champion"
    elif (b.get("dealsClosed") or 0) > 0:
        new_status = "active"
    elif received >= 1:
        new_status = "warm"

    fs.update(
        "brokers",
        broker_id,
        {
            "dealsReceived": received,
            "relationshipStatus": new_status,
            "lastTouchpoint": fs.now_utc(),
        },
    )
    fs.audit_log(
        agent=AGENT_NAME,
        action="update_status_after_deal_received",
        target_type="broker",
        target_id=broker_id,
        details={"newStatus": new_status, "dealsReceived": received},
    )


def identify_warm_brokers_to_followup(no_touch_days: int = 60) -> List[Dict[str, Any]]:
    """Liste les warms sans touchpoint depuis N jours."""
    threshold = datetime.now(timezone.utc) - timedelta(days=no_touch_days)
    brokers = fs.query(
        "brokers",
        filters=[("relationshipStatus", "==", "warm")],
        limit=200,
    )
    candidates: List[Dict[str, Any]] = []
    for b in brokers:
        last = b.get("lastTouchpoint")
        if last is None or (hasattr(last, "timestamp") and last < threshold):
            candidates.append(b)
    return candidates


def identify_champions(top_n: int = 5) -> List[Dict[str, Any]]:
    """Top N courtiers par nombre de deals reçus."""
    brokers = fs.query("brokers", filters=None, limit=500)
    sorted_brokers = sorted(
        brokers, key=lambda b: (b.get("dealsClosed") or 0, b.get("dealsReceived") or 0), reverse=True
    )
    return sorted_brokers[:top_n]
