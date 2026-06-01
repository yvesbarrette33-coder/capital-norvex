"""Audit Norvex Diligence™ — Firestore writes du rapport global."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from agents.shared.firestore_client import (
    audit_log, create, db, get, update,
)

from .config import AGENT_NAME, COLLECTION_REPORTS


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def store_report(*, dossier_id: str, report: Dict[str, Any]) -> str:
    """Stocke un rapport diligence dans Firestore.

    1 dossier = 1 rapport (overwrite si déjà existant — Yves peut relancer).
    Doc ID = dossier_id pour faciliter accès.
    """
    payload = {
        **report,
        "dossierId": dossier_id,
        "agent": AGENT_NAME,
        "generatedAt": now_utc_iso(),
    }
    db().collection(COLLECTION_REPORTS).document(dossier_id).set(payload)
    return dossier_id


def get_report(dossier_id: str) -> Optional[Dict[str, Any]]:
    snap = db().collection(COLLECTION_REPORTS).document(dossier_id).get()
    if not snap.exists:
        return None
    d = snap.to_dict()
    d["id"] = snap.id
    return d


def update_dossier_with_verdict(*, dossier_id: str, verdict: str,
                                 summary: str = "") -> None:
    """Reflète le verdict dans le dossier Pipeline (badge couleur)."""
    try:
        update("dossiers", dossier_id, {
            "diligenceVerdict": verdict,            # green / yellow / red
            "diligenceSummary": summary[:300],
            "diligenceUpdatedAt": now_utc_iso(),
        })
    except Exception:
        # Si le dossier n'existe pas encore, on log mais on n'échoue pas
        audit_log(agent=AGENT_NAME, action="dossier_update_failed",
                  target_type="dossiers", target_id=dossier_id,
                  result="error",
                  details={"verdict": verdict})


def log(action: str, *, target_id: str = "", result: str = "ok",
        details: Optional[Dict[str, Any]] = None) -> None:
    audit_log(
        agent=AGENT_NAME, action=action,
        target_type="diligence", target_id=target_id or "unknown",
        result=result, details=details or {},
    )
