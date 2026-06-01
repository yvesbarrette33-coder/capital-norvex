"""Workflow d'approbation R-APPROVAL.

Aucune communication sortante (email, lettre, appel, vidéo, post LinkedIn)
ne part SANS approbation explicite de Yves dans le pipeline.

Status workflow:
    draft → pending_yves_approval → approved → sent
                                  → rejected (terminal)

API:
    submit_for_approval(collection, doc_id, communication_data) -> id
    notify_yves(collection, doc_id) -> notif envoyée
    mark_approved(collection, doc_id, approver='Yves Barrette')
    mark_rejected(collection, doc_id, reason)
    mark_sent(collection, doc_id)
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from .firestore_client import audit_log, get, update

YVES_EMAIL_DEFAULT = os.getenv("YVES_EMAIL", "yvesbarrette33@gmail.com")
PIPELINE_URL = "https://capitalnorvex.com/capital-norvex-pipeline.html"


def submit_for_approval(
    collection: str,
    doc_id: str,
    communication_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Marque un doc comme en attente d'approbation Yves."""
    payload = {"status": "pending_yves_approval"}
    if communication_data:
        payload.update(communication_data)
    update(collection, doc_id, payload)
    audit_log(
        agent=(communication_data or {}).get("_agent", "unknown"),
        action="submit_for_approval",
        target_type=collection,
        target_id=doc_id,
        result="pending_approval",
    )
    return doc_id


def notify_yves(collection: str, doc_id: str) -> bool:
    """Envoie une notification courriel à Yves pour approbation.

    Format Variation A. Renvoie True si envoyé.
    """
    # Import différé pour éviter cycle
    from .email_sender import send_email
    from .email_template import render_variation_a

    item = get(collection, doc_id)
    if not item:
        return False

    target_label = (
        item.get("name")
        or item.get("organization")
        or item.get("companyName")
        or item.get("firmName")
        or doc_id
    )
    body = (
        f"<p>Une nouvelle communication est en attente de ton approbation.</p>"
        f"<p><strong>Type :</strong> {item.get('touchpointType', 'communication')}<br>"
        f"<strong>Cible :</strong> {target_label}<br>"
        f"<strong>Collection :</strong> {collection}<br>"
        f"<strong>ID :</strong> {doc_id}</p>"
        f"<p>Pour approuver ou modifier, ouvre le pipeline:<br>"
        f"<a href=\"{PIPELINE_URL}\">{PIPELINE_URL}</a></p>"
    )
    html = render_variation_a(
        body_html=body,
        recipient_name="Yves",
        title_line="Approbation requise — Agent Capital Norvex",
    )
    ok = send_email(
        to=YVES_EMAIL_DEFAULT,
        subject=f"[Capital Norvex] Approbation requise — {target_label}",
        html=html,
    )
    audit_log(
        agent="brain",
        action="notify_yves_for_approval",
        target_type=collection,
        target_id=doc_id,
        result="success" if ok else "error",
    )
    return ok


def mark_approved(
    collection: str, doc_id: str, approver: str = "Yves Barrette"
) -> None:
    from datetime import datetime, timezone

    update(
        collection,
        doc_id,
        {
            "status": "approved",
            "yvesApprovedAt": datetime.now(timezone.utc),
            "approvedBy": approver,
        },
    )
    audit_log(
        agent="pipeline",
        action="mark_approved",
        target_type=collection,
        target_id=doc_id,
        details={"approver": approver},
    )


def mark_rejected(collection: str, doc_id: str, reason: str = "") -> None:
    update(
        collection, doc_id, {"status": "rejected", "rejectionReason": reason}
    )
    audit_log(
        agent="pipeline",
        action="mark_rejected",
        target_type=collection,
        target_id=doc_id,
        details={"reason": reason},
    )


def mark_sent(collection: str, doc_id: str, sent_via: str = "graph") -> None:
    from datetime import datetime, timezone

    update(
        collection,
        doc_id,
        {
            "status": "sent",
            "sentDate": datetime.now(timezone.utc),
            "sentVia": sent_via,
        },
    )
    audit_log(
        agent="pipeline",
        action="mark_sent",
        target_type=collection,
        target_id=doc_id,
        details={"sentVia": sent_via},
    )
