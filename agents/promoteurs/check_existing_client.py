"""Agent PROMOTEURS v0 — vérification anti-doublon avant envoi.

Avant tout envoi à un promoteur, vérifie qu'il n'est pas déjà:
1. Client actif Capital Norvex (collection `dossiers` ou `dossiers_clients`)
2. Récemment refusé (cool-down 6 mois — R-CADENCE)
3. Sur la liste TIER ZERO

Si oui → STOP + log.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from ..shared import firestore_client as fs
from ..shared.tier_zero_guard import is_protected

AGENT_NAME = "promoteurs"
COOLDOWN_MONTHS = 6


class PromoterBlocked(Exception):
    """Levée si un envoi est bloqué."""

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        self.reason = reason
        self.details = details or {}
        super().__init__(reason)


def check(promoter: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Retourne (ok_to_send, reason_if_blocked)."""
    name = promoter.get("name") or ""
    company = promoter.get("companyName") or ""
    email = (promoter.get("contactInfo") or {}).get("email") or ""

    # 1. TIER ZERO
    for v in (name, company, email):
        if is_protected(v):
            fs.audit_log(
                agent=AGENT_NAME,
                action="check_blocked_tier_zero",
                target_type="promoter",
                target_id=promoter.get("id"),
                result="blocked_tier_zero",
            )
            return False, "TIER_ZERO"

    # 2. Client actif (dossiers / dossiers_clients)
    if email:
        active_clients = fs.query(
            "dossiers_clients", filters=[("email", "==", email)], limit=1
        )
        if active_clients:
            fs.audit_log(
                agent=AGENT_NAME,
                action="check_blocked_existing_client",
                target_type="promoter",
                target_id=promoter.get("id"),
                result="blocked_existing_client",
            )
            return False, "EXISTING_CLIENT"

    # 3. Cool-down 6 mois si refusé
    threshold = datetime.now(timezone.utc) - timedelta(days=30 * COOLDOWN_MONTHS)
    if promoter.get("id"):
        recents = fs.query(
            "promoterApproaches",
            filters=[
                ("promoterId", "==", promoter["id"]),
                ("status", "==", "responded"),
            ],
            limit=5,
        )
        for r in recents:
            sent = r.get("sentDate")
            if r.get("response", "").lower().startswith(("refus", "non", "pas inter")) and (
                sent is None or (hasattr(sent, "timestamp") and sent > threshold)
            ):
                fs.audit_log(
                    agent=AGENT_NAME,
                    action="check_blocked_cooldown",
                    target_type="promoter",
                    target_id=promoter.get("id"),
                    result="blocked_cooldown",
                )
                return False, "COOLDOWN_6M"

    return True, None


def assert_can_send(promoter: Dict[str, Any]) -> None:
    """Lève PromoterBlocked si l'envoi est interdit."""
    ok, reason = check(promoter)
    if not ok:
        raise PromoterBlocked(reason or "BLOCKED", {"promoterId": promoter.get("id")})
