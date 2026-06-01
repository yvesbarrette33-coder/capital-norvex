"""Audit Sophie — Firestore + notification Yves (HMAC partagé avec Camille).

Réutilise le même CAMILLE_HMAC_SECRET pour les liens d'approbation cliquables
(pratique : un seul secret pour tous les agents).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from agents.shared.firestore_client import audit_log, create, get, update

from .config import (
    AGENT_NAME,
    COLLECTION_DRAFTS,
    COLLECTION_EMAILS,
    YVES_APPROVAL_INBOX,
)

# ── HMAC partagé avec Camille ────────────────────────────────────
HMAC_TTL_DAYS = 7
SITE_BASE_URL = os.getenv("SITE_URL", "https://capitalnorvex.com")


def _b64url(buf: bytes) -> str:
    return base64.urlsafe_b64encode(buf).rstrip(b"=").decode("ascii")


def _sign_approval_token(draft_id: str, action: str, exp_iso: str) -> str:
    secret = os.getenv("CAMILLE_HMAC_SECRET")
    if not secret or len(secret) < 16:
        raise RuntimeError("CAMILLE_HMAC_SECRET env var manquant")
    payload = f"{draft_id}.{action}.{exp_iso}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
    return _b64url(sig)


def _build_approval_url(draft_id: str, action: str) -> str:
    """URL approve/reject — utilise les endpoints Sophie (pas Camille)."""
    exp_dt = datetime.now(timezone.utc) + timedelta(days=HMAC_TTL_DAYS)
    exp_iso = exp_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    token = _sign_approval_token(draft_id, action, exp_iso)
    return (
        f"{SITE_BASE_URL}/api/sophie-{action}"
        f"?draft={draft_id}&exp={exp_iso}&token={token}"
    )


def _now():
    return datetime.now(timezone.utc)


# ── Email entrant ────────────────────────────────────────────────
def store_incoming_email(*, normalized: Dict[str, Any], triage: Dict[str, Any]) -> str:
    doc_id = None
    imid = normalized.get("internet_message_id")
    if imid:
        doc_id = (imid.replace("<", "").replace(">", "").replace("/", "_").replace(".", "_"))[:1500]
    payload = {
        "graphId": normalized.get("graph_id"),
        "internetMessageId": imid,
        "conversationId": normalized.get("conversation_id"),
        "receivedMailbox": normalized.get("received_mailbox"),
        "receivedAtIso": normalized.get("received_at_iso"),
        "fromAddress": normalized.get("from"),
        "fromName": normalized.get("from_name"),
        "to": normalized.get("to"),
        "cc": normalized.get("cc"),
        "subject": normalized.get("subject"),
        "bodyTextSnippet": (normalized.get("body_text") or "")[:2000],
        "hasAttachments": normalized.get("has_attachments"),
        "triage": triage,
        "status": "triaged",
        "agent": AGENT_NAME,
    }
    existing = get(COLLECTION_EMAILS, doc_id) if doc_id else None
    if existing:
        update(COLLECTION_EMAILS, doc_id, payload)
        action = "update_incoming_email"
    else:
        doc_id = create(COLLECTION_EMAILS, payload, doc_id=doc_id)
        action = "store_incoming_email"

    audit_log(
        agent=AGENT_NAME,
        action=action,
        target_type=COLLECTION_EMAILS,
        target_id=doc_id,
        details={"category": triage.get("category"), "priority": triage.get("priority"),
                 "mailbox": normalized.get("received_mailbox")},
    )
    return doc_id


# ── Draft ────────────────────────────────────────────────────────
def store_draft(*, incoming_email_id: str, source_mailbox: str, draft: Dict[str, Any],
                triage: Dict[str, Any], to_recipient: str,
                cc_recipients: Optional[list] = None,
                initial_status: str = "pending_yves_approval",
                auto_send_reason: str = "") -> str:
    payload = {
        "incomingEmailId": incoming_email_id,
        "sourceMailbox": source_mailbox,
        "persona": draft.get("persona"),
        "fromUser": draft.get("from_user"),
        "toRecipient": to_recipient,
        "ccRecipients": cc_recipients or [],
        "subject": draft.get("subject"),
        "language": draft.get("language"),
        "bodyHtml": draft.get("body_html"),
        "signedHtml": draft.get("signed_html"),
        "internalNoteForYves": draft.get("internal_note_for_yves"),
        "needsYvesInputBeforeSend": draft.get("needs_yves_input_before_send"),
        "openQuestions": draft.get("open_questions", []),
        "triageSnapshot": triage,
        "status": initial_status,
        "autoSendReason": auto_send_reason,
        "agent": AGENT_NAME,
        "createdAt": _now(),
    }
    doc_id = create(COLLECTION_DRAFTS, payload)

    # Bug fix 2026-05-10 (anti-spam dédup self) : voir agent_dedup.py.
    # Marque l'email comme drafté pour que process_one_message skip aux
    # prochains ticks du cron (sinon Sophie re-drafte aux 10 min).
    try:
        update(COLLECTION_EMAILS, incoming_email_id,
               {"draftId": doc_id, "status": "drafted"})
    except Exception as e:
        audit_log(
            agent=AGENT_NAME,
            action="mark_email_drafted_failed",
            target_type=COLLECTION_EMAILS,
            target_id=incoming_email_id,
            result="warning",
            details={"error": str(e)[:300], "draftId": doc_id},
        )

    audit_log(
        agent=AGENT_NAME,
        action="store_draft",
        target_type=COLLECTION_DRAFTS,
        target_id=doc_id,
        details={"persona": draft.get("persona"), "to": to_recipient,
                 "subject": draft.get("subject"), "initialStatus": initial_status},
    )
    return doc_id


def mark_draft_sent(draft_id: str, *, sent_via: str = "graph") -> None:
    update(COLLECTION_DRAFTS, draft_id, {"status": "sent", "sentAt": _now(), "sentVia": sent_via})
    audit_log(agent=AGENT_NAME, action="send_draft", target_type=COLLECTION_DRAFTS,
              target_id=draft_id, details={"sentVia": sent_via})


# ── Notification escalade Yves (3 boutons HMAC) ───────────────────
def notify_yves_for_sophie_draft(
    draft_id: str, *, subject: str, to_recipient: str, summary: str,
    body_html_preview: str = "", cc_recipients: Optional[list] = None,
    source_mailbox: str = "",
    dashboard_url: str = "https://capitalnorvex.com/sophie-admin.html",
) -> bool:
    from agents.shared.email_sender import send_email
    try:
        approve_url = _build_approval_url(draft_id, "approve")
        reject_url = _build_approval_url(draft_id, "reject")
        modify_url = _build_approval_url(draft_id, "modify")
    except RuntimeError:
        approve_url = reject_url = modify_url = dashboard_url

    cc_str = ", ".join(cc_recipients) if cc_recipients else "(aucun)"
    preview_block = f'''<div style="margin:24px 0;border:1px solid #e5e5e7;border-radius:8px;overflow:hidden;">
  <div style="background:#f4f4f6;padding:10px 16px;font-size:12px;color:#555;font-weight:600;text-transform:uppercase;letter-spacing:.5px;">Aperçu de la réponse proposée</div>
  <div style="padding:20px;max-height:480px;overflow:auto;background:white;font-size:14px;line-height:1.55;">{body_html_preview}</div>
</div>''' if body_html_preview else ""

    body = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,sans-serif;max-width:720px;margin:0 auto;padding:24px;color:#1a1a1a;">
<div style="background:linear-gradient(135deg,#1a1a1a 0%,#2a2a2a 100%);color:white;padding:24px;border-radius:12px 12px 0 0;">
  <div style="font-size:12px;letter-spacing:2px;color:#C9A227;font-weight:600;">SOPHIE — NORVEX RELATIONS™</div>
  <div style="font-size:22px;font-family:'Playfair Display',Georgia,serif;margin-top:4px;">Approbation requise</div>
</div>
<div style="background:#fafafa;padding:24px;border:1px solid #e5e5e7;border-top:none;border-radius:0 0 12px 12px;">
<table style="width:100%;border-collapse:collapse;margin-bottom:16px;">
  <tr><td style="padding:6px 0;color:#666;font-size:13px;">Boîte source</td><td style="padding:6px 0;font-family:monospace;">{source_mailbox}</td></tr>
  <tr><td style="padding:6px 0;color:#666;font-size:13px;">Destinataire</td><td style="padding:6px 0;font-family:monospace;">{to_recipient}</td></tr>
  <tr><td style="padding:6px 0;color:#666;font-size:13px;">CC</td><td style="padding:6px 0;font-family:monospace;font-size:13px;">{cc_str}</td></tr>
  <tr><td style="padding:6px 0;color:#666;font-size:13px;">Objet</td><td style="padding:6px 0;font-weight:600;">{subject}</td></tr>
</table>
<div style="background:#f0f4f7;border-left:3px solid #C9A227;padding:12px 16px;margin:16px 0;font-size:14px;">
  <strong>Résumé du courriel reçu :</strong><br>{summary}
</div>
{preview_block}
<div style="margin:28px 0 8px 0;text-align:center;">
  <a href="{approve_url}" style="display:inline-block;background:#2d8a3e;color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:600;margin:4px 6px;font-size:15px;">✅ Approuver et envoyer</a>
  <a href="{modify_url}" style="display:inline-block;background:#1a1a1a;color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:600;margin:4px 6px;font-size:15px;">✏️ Modifier dans dashboard</a>
  <a href="{reject_url}" style="display:inline-block;background:#c33;color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:600;margin:4px 6px;font-size:15px;">❌ Rejeter</a>
</div>
<p style="text-align:center;color:#777;font-size:12px;margin-top:16px;">Liens valides 7 jours · ID draft : <code>{draft_id}</code></p>
<hr style="border:none;border-top:1px solid #e5e5e7;margin:24px 0;">
<p style="font-size:12px;color:#888;text-align:center;">Dashboard : <a href="{dashboard_url}" style="color:#C9A227;">{dashboard_url}</a></p>
</div></body></html>"""

    ok = send_email(to=YVES_APPROVAL_INBOX,
                    subject=f"[Sophie] Approbation requise — {subject}",
                    html=body, from_user=YVES_APPROVAL_INBOX)
    audit_log(agent=AGENT_NAME, action="notify_yves_for_approval",
              target_type=COLLECTION_DRAFTS, target_id=draft_id,
              result="success" if ok else "error")
    return ok


# ── Notification AUTO-SEND Yves (info, sans boutons) ──────────────
def notify_yves_sophie_auto_sent(
    draft_id: str, *, subject: str, to_recipient: str, summary: str,
    body_html_preview: str = "", cc_recipients: Optional[list] = None,
    source_mailbox: str = "", auto_send_reason: str = "",
    dashboard_url: str = "https://capitalnorvex.com/sophie-admin.html",
) -> bool:
    from agents.shared.email_sender import send_email

    cc_str = ", ".join(cc_recipients) if cc_recipients else "(aucun)"
    preview_block = f'''<div style="margin:24px 0;border:1px solid #e5e5e7;border-radius:8px;overflow:hidden;">
  <div style="background:#f4f4f6;padding:10px 16px;font-size:12px;color:#555;font-weight:600;text-transform:uppercase;letter-spacing:.5px;">Réponse envoyée par Sophie</div>
  <div style="padding:20px;max-height:480px;overflow:auto;background:white;font-size:14px;line-height:1.55;">{body_html_preview}</div>
</div>''' if body_html_preview else ""

    body = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,sans-serif;max-width:720px;margin:0 auto;padding:24px;color:#1a1a1a;">
<div style="background:linear-gradient(135deg,#1c5d2c 0%,#2d8a3e 100%);color:white;padding:24px;border-radius:12px 12px 0 0;">
  <div style="font-size:12px;letter-spacing:2px;color:#C9A227;font-weight:600;">SOPHIE — NORVEX RELATIONS™</div>
  <div style="font-size:22px;font-family:'Playfair Display',Georgia,serif;margin-top:4px;">📤 Réponse envoyée pour information</div>
  <div style="font-size:13px;opacity:.85;margin-top:6px;">Sophie a répondu en autonomie. Tu es en CC. Aucune action requise.</div>
</div>
<div style="background:#fafafa;padding:24px;border:1px solid #e5e5e7;border-top:none;border-radius:0 0 12px 12px;">
<table style="width:100%;border-collapse:collapse;margin-bottom:16px;">
  <tr><td style="padding:6px 0;color:#666;font-size:13px;">Boîte source</td><td style="padding:6px 0;font-family:monospace;">{source_mailbox}</td></tr>
  <tr><td style="padding:6px 0;color:#666;font-size:13px;">Destinataire</td><td style="padding:6px 0;font-family:monospace;">{to_recipient}</td></tr>
  <tr><td style="padding:6px 0;color:#666;font-size:13px;">CC</td><td style="padding:6px 0;font-family:monospace;font-size:13px;">{cc_str}</td></tr>
  <tr><td style="padding:6px 0;color:#666;font-size:13px;">Objet</td><td style="padding:6px 0;font-weight:600;">{subject}</td></tr>
</table>
{f'<div style="background:#e8f5e9;border-left:3px solid #2d8a3e;padding:10px 16px;font-size:13px;margin:12px 0;"><strong>Pourquoi Sophie a pu envoyer :</strong> {auto_send_reason}</div>' if auto_send_reason else ''}
<div style="background:#f0f4f7;border-left:3px solid #C9A227;padding:12px 16px;margin:16px 0;font-size:14px;">
  <strong>Résumé du courriel reçu :</strong><br>{summary}
</div>
{preview_block}
<hr style="border:none;border-top:1px solid #e5e5e7;margin:24px 0;">
<p style="font-size:12px;color:#888;text-align:center;">Historique complet : <a href="{dashboard_url}" style="color:#C9A227;">{dashboard_url}</a></p>
</div></body></html>"""

    ok = send_email(to=YVES_APPROVAL_INBOX,
                    subject=f"[Sophie — pour info] Envoyé : {subject}",
                    html=body, from_user=YVES_APPROVAL_INBOX)
    audit_log(agent=AGENT_NAME, action="notify_yves_auto_sent",
              target_type=COLLECTION_DRAFTS, target_id=draft_id,
              result="success" if ok else "error")
    return ok
