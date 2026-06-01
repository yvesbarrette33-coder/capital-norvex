"""Ingest pièces jointes Outlook → Firebase Storage + Firestore dossier.

Fix incident Henri Petit 2026-05-18 : quand un client envoie ses documents
par pièce jointe à yves@capitalnorvex.com (au lieu d'utiliser le PWA),
aucun agent ne téléchargeait automatiquement. Béatrice voyait l'email mais
ne le picksait pas dans le dossier.

Nouveau flux (appelé AVANT le triage Béatrice) :

  1. Email entrant a-t-il des attachments non-inline ? sinon, skip.
  2. L'expéditeur match-t-il un dossier actif (collection `dossiers`
     où `email == sender_address`) ? sinon, skip.
  3. Idempotence : Firestore audit log déjà entry pour ce
     internetMessageId + dossierId ? si oui, skip.
  4. Pour chaque attachment :
     - download_attachment (Graph API)
     - upload Firebase Storage `uploads/{dossier_id}/{ts}_{filename_safe}`
     - append docsList + bump docsReceivedCount + lastDocsReceivedAt
  5. Notif rapide Yves : "📎 Pièces jointes ingérées dans dossier X"
  6. Audit log : action=ingest_outlook_attachments_to_dossier

Le triage Béatrice continue normalement après. Béatrice draftera l'accusé
de réception pour Yves à approuver (workflow standard).
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

log = logging.getLogger("beatrice.attachment_ingester")


def _safe_filename(name: str) -> str:
    """Sanitize filename for Firebase Storage path."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def _get_firebase_app():
    """Lazy init Firebase Admin."""
    try:
        import firebase_admin
        from firebase_admin import credentials
        if not firebase_admin._apps:
            cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            bucket = os.getenv("FIREBASE_STORAGE_BUCKET")
            if not cred_path or not os.path.exists(cred_path):
                return None
            firebase_admin.initialize_app(
                credentials.Certificate(cred_path),
                {"storageBucket": bucket} if bucket else None,
            )
        return firebase_admin.get_app()
    except Exception as e:
        log.warning(f"Firebase Admin init failed: {e}")
        return None


def _find_active_dossier_by_email(db, sender_email: str) -> Optional[Dict[str, Any]]:
    """Cherche un dossier actif dont email == sender (lowercase exact match).

    Retourne le doc Firestore (dict avec id) ou None si pas de match.
    Skip les dossiers `stage = closed` ou `archived`.
    """
    if not sender_email:
        return None
    needle = sender_email.lower().strip()
    # Query simple par email
    try:
        docs = db.collection("dossiers").where("email", "==", needle).limit(5).get()
        for d in docs:
            data = d.to_dict() or {}
            stage = (data.get("stage") or "").lower()
            if stage in ("closed", "archived", "rejected"):
                continue
            data["id"] = d.id
            return data
    except Exception as e:
        log.warning(f"Firestore query dossier by email failed: {e}")
    # Fallback : case-insensitive scan limité (au cas où email stocké avec casse)
    try:
        for d in db.collection("dossiers").limit(500).get():
            data = d.to_dict() or {}
            email_doc = (data.get("email") or "").lower().strip()
            if email_doc == needle:
                stage = (data.get("stage") or "").lower()
                if stage in ("closed", "archived", "rejected"):
                    continue
                data["id"] = d.id
                return data
    except Exception:
        pass
    return None


def _already_ingested(db, internet_message_id: str, dossier_id: str) -> bool:
    """Vérifie via audit log si on a déjà ingéré ce messageId pour ce dossier."""
    if not internet_message_id or not dossier_id:
        return False
    try:
        q = db.collection("auditLogs") \
              .where("action", "==", "ingest_outlook_attachments_to_dossier") \
              .where("targetId", "==", dossier_id) \
              .limit(50)
        for snap in q.get():
            data = snap.to_dict() or {}
            details = data.get("details") or {}
            if details.get("internetMessageId") == internet_message_id:
                return True
    except Exception as e:
        log.warning(f"Idempotence check failed: {e}")
    return False


def maybe_ingest_attachments_for_active_dossier(
    *,
    mailbox: str,
    message_id: str,
    internet_message_id: str,
    sender_email: str,
    sender_name: str = "",
    notify_yves_email: Optional[str] = None,
) -> Dict[str, Any]:
    """Pipeline d'ingestion. Idempotent. Safe à appeler à chaque tick.

    Retourne un summary dict (toujours, même si skip) :
        { "matched": bool, "dossier_id": str|None, "ingested_count": int,
          "skipped_reason": str|None, "files": list[dict] }

    Ne lève jamais d'exception — log seulement (pas casser flow Béatrice).
    """
    summary = {
        "matched": False,
        "dossier_id": None,
        "ingested_count": 0,
        "skipped_reason": None,
        "files": [],
    }

    if not message_id or not sender_email:
        summary["skipped_reason"] = "missing message_id or sender_email"
        return summary

    # Lazy import pour ne pas charger Graph/Firebase si pas besoin
    try:
        from agents.shared.graph_attachments import (
            list_attachments,
            download_attachment,
        )
    except Exception as e:
        summary["skipped_reason"] = f"graph_attachments import failed: {e}"
        return summary

    app = _get_firebase_app()
    if app is None:
        summary["skipped_reason"] = "firebase_admin unavailable"
        return summary

    try:
        from firebase_admin import firestore, storage
    except Exception as e:
        summary["skipped_reason"] = f"firebase_admin modules import failed: {e}"
        return summary

    # 1. List attachments
    try:
        atts = list_attachments(mailbox, message_id)
    except Exception as e:
        summary["skipped_reason"] = f"list_attachments failed: {e}"
        return summary

    non_inline = [a for a in atts if not a.get("isInline")]
    if not non_inline:
        summary["skipped_reason"] = "no_attachments"
        return summary

    # 2. Match dossier
    db = firestore.client()
    dossier = _find_active_dossier_by_email(db, sender_email)
    if not dossier:
        summary["skipped_reason"] = f"no active dossier for {sender_email}"
        return summary

    dossier_id = dossier["id"]
    summary["matched"] = True
    summary["dossier_id"] = dossier_id

    # 3. Idempotence : déjà ingéré ?
    if _already_ingested(db, internet_message_id, dossier_id):
        summary["skipped_reason"] = "already_ingested_for_this_message"
        return summary

    # 4. Download + upload chaque attachment
    bucket = storage.bucket()
    new_docs: List[Dict[str, Any]] = []
    for a in non_inline:
        try:
            data = download_attachment(mailbox, message_id, a["id"])
            if not data:
                continue
            ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            fn_safe = _safe_filename(a["name"])
            storage_path = f"uploads/{dossier_id}/{ts_ms}_{fn_safe}"
            blob = bucket.blob(storage_path)
            blob.upload_from_string(
                data,
                content_type=a.get("contentType", "application/octet-stream"),
            )
            new_docs.append({
                "uploadedAt": datetime.now(timezone.utc).isoformat(),
                "storagePath": storage_path,
                "size": len(data),
                "name": a["name"],
                "contentType": a.get("contentType", "application/octet-stream"),
                "source": "beatrice_outlook_ingest_2026-05-18",
                "messageId": message_id,
                "internetMessageId": internet_message_id,
                "originalAttachmentId": a["id"],
            })
            log.info(f"   📎 Upload Storage : {storage_path} ({len(data)} bytes)")
        except Exception as e:
            log.warning(f"   ⚠ Skip attachment {a.get('name')}: {e}")
            continue

    if not new_docs:
        summary["skipped_reason"] = "no attachment successfully uploaded"
        return summary

    # 5. Update dossier Firestore
    try:
        doc_ref = db.collection("dossiers").document(dossier_id)
        snap = doc_ref.get()
        d = snap.to_dict() or {}
        current_list = d.get("docsList", []) or []
        doc_ref.update({
            "docsList": current_list + new_docs,
            "docsReceivedCount": (d.get("docsReceivedCount", 0) or 0) + len(new_docs),
            "lastDocsReceivedAt": datetime.now(timezone.utc),
            "lastUpdated": datetime.now(timezone.utc),
            "_lastOutlookIngestAt": datetime.now(timezone.utc),
        })
        log.info(f"   📈 Firestore bump : docsReceivedCount +{len(new_docs)} (dossier {dossier_id})")
    except Exception as e:
        log.error(f"   ⚠ Firestore update failed: {e}")

    # 6. Audit log (sert d'idempotence pour les prochains ticks)
    try:
        db.collection("auditLogs").add({
            "agent": "beatrice",
            "action": "ingest_outlook_attachments_to_dossier",
            "targetType": "dossiers",
            "targetId": dossier_id,
            "result": "success",
            "createdAt": datetime.now(timezone.utc),
            "details": {
                "mailbox": mailbox,
                "messageId": message_id,
                "internetMessageId": internet_message_id,
                "senderEmail": sender_email,
                "attachmentsCount": len(new_docs),
                "totalSizeBytes": sum(x["size"] for x in new_docs),
                "fileNames": [x["name"] for x in new_docs],
            },
        })
    except Exception as e:
        log.warning(f"   ⚠ Audit log failed (ingestion already done in Firestore): {e}")

    # 7. Notif rapide Yves
    if notify_yves_email and new_docs:
        try:
            from agents.shared.email_sender import send_email_smart
            files_html = "".join(
                f"<li><b>{x['name']}</b> — {x['size']:,} bytes</li>"
                for x in new_docs
            )
            client_label = sender_name or sender_email
            html = f"""
<div style="font-family:Aptos,Arial,sans-serif;font-size:13pt;color:#212121;line-height:1.5;">
  <p>📎 <b>Pièces jointes ingérées dans le dossier {dossier_id}</b></p>
  <p>De : {client_label} &lt;{sender_email}&gt;</p>
  <p>Fichiers déposés ({len(new_docs)}) :</p>
  <ul>{files_html}</ul>
  <p>Storage path : <code>uploads/{dossier_id}/</code></p>
  <p>L'analyse Norvex Final sera relancée automatiquement au prochain cycle (≤ 10 min).</p>
  <p style="color:#888;font-size:11pt;font-style:italic;">Béatrice — ingestion automatique pièces jointes Outlook (fix 2026-05-18)</p>
</div>
"""
            subj = f"📎 Pièces jointes ingérées — {client_label} — dossier {dossier_id}"
            send_email_smart(
                to=notify_yves_email,
                subject=subj,
                html=html,
                from_name="Béatrice (Capital Norvex)",
            )
            log.info(f"   ✉ Notif Yves envoyée pour ingestion dossier {dossier_id}")
        except Exception as e:
            log.warning(f"   ⚠ Notif Yves échouée : {e}")

    summary["ingested_count"] = len(new_docs)
    summary["files"] = new_docs
    return summary
