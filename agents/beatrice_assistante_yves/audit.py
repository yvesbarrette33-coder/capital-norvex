"""Audit Béatrice — Firestore + notification Yves (HMAC partagé Camille/Sophie).

Réutilise le même CAMILLE_HMAC_SECRET pour les liens d'approbation cliquables
(un seul secret pour tous les agents). Endpoints visés : /api/beatrice-approve,
/api/beatrice-reject, /api/beatrice-modify (à créer côté Netlify).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

# ── Limite Firestore (1 MiB par valeur de champ) ─────────────────
# On garde une marge de sécurité pour les autres champs du document.
_FIRESTORE_FIELD_MAX_BYTES = 1_048_487
_HTML_SAFE_LIMIT_BYTES = 900_000  # ~860 KB de HTML max → laisse de l'air pour métadonnées


def _compact_html_for_firestore(html: Optional[str]) -> Optional[str]:
    """Compacte un HTML de draft si > limite Firestore.

    Stratégie :
      1. Si HTML ≤ 900 KB → retourne tel quel.
      2. Strip les `<img src="data:image/...;base64,...">` (souvent ce qui pèse).
      3. Si encore > 900 KB → tronque + note explicative en clair.

    Le draft est conservé : le user verra le contenu Yves avait écrit, juste sans
    les images embarquées (qui sont rarement utiles dans un draft de réponse).
    """
    if not html:
        return html
    if not isinstance(html, str):
        return html

    encoded = html.encode("utf-8", errors="replace")
    if len(encoded) <= _HTML_SAFE_LIMIT_BYTES:
        return html

    # Étape 1 — strip les data: URIs (images base64 inline).
    stripped = re.sub(
        r'src=["\']data:[^"\']*["\']',
        'src="" alt="[image lourde retirée]"',
        html,
        flags=re.IGNORECASE,
    )
    encoded2 = stripped.encode("utf-8", errors="replace")
    if len(encoded2) <= _HTML_SAFE_LIMIT_BYTES:
        return stripped

    # Étape 2 — tronque proprement (caractère par caractère pour éviter de
    # couper au milieu d'une séquence multibyte UTF-8).
    note = (
        '<p style="color:#a00;font-size:12px;'
        'border-top:1px solid #eee;margin-top:16px;padding-top:8px;">'
        '[⚠️ Contenu original lourd tronqué pour respecter la limite Firestore. '
        'Yves : voir l\'email entrant directement dans Outlook si besoin.]'
        '</p>'
    )
    note_bytes = note.encode("utf-8")
    budget = _HTML_SAFE_LIMIT_BYTES - len(note_bytes)
    if budget <= 0:
        return note  # cas extrême, ne devrait jamais arriver

    truncated_bytes = encoded2[:budget]
    # Décode en remplaçant les caractères incomplets en fin de chaîne.
    truncated = truncated_bytes.decode("utf-8", errors="ignore")
    return truncated + note

from agents.shared.firestore_client import audit_log, create, get, update

from .config import (
    AGENT_NAME,
    COLLECTION_DRAFTS,
    COLLECTION_EMAILS,
    YVES_APPROVAL_INBOX,
)

# ── HMAC partagé avec Camille/Sophie ─────────────────────────────
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
    """URL approve/reject/modify — endpoints Béatrice (à créer côté Netlify)."""
    exp_dt = datetime.now(timezone.utc) + timedelta(days=HMAC_TTL_DAYS)
    exp_iso = exp_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    token = _sign_approval_token(draft_id, action, exp_iso)
    return (
        f"{SITE_BASE_URL}/api/beatrice-{action}"
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


# ── Dédup avec Camille (et Sophie) ───────────────────────────────
def is_already_processed_elsewhere(internet_message_id: Optional[str]) -> Optional[str]:
    """Vérifie si ce Message-ID a déjà été DRAFTÉ par Camille ou Sophie.

    Retourne le nom de l'agent qui l'a draftée, ou None.

    🐛 Bug fix 2026-05-05 PM : avant ce patch, on retournait "camille" dès que
    le doc `camilleEmails/{id}` existait, MÊME SI Camille avait juste triagé +
    skippé (filtre legal_only sur yves@ → tout ce qui n'est pas juridique va
    « hors scope, réservé futur agent »). Résultat : Béatrice voyait le marker
    et skippait à son tour → l'email tombait entre les craques.

    Maintenant : on retourne le nom de l'agent SEULEMENT s'il a effectivement
    drafté. Si Camille a juste triagé + skippé hors scope, Béatrice prend le
    relais (puisque Béatrice EST le « futur agent général » sur yves@).
    """
    if not internet_message_id:
        return None
    doc_id = (
        internet_message_id.replace("<", "").replace(">", "")
        .replace("/", "_").replace(".", "_")
    )[:1500]

    def _was_actually_drafted(record) -> bool:
        if not record:
            return False
        if record.get("drafted") is True:
            return True
        if record.get("draftId") or record.get("draft_id"):
            return True
        status = (record.get("status") or "").lower().strip()
        if status in {
            "sent", "auto_sent", "drafted",
            "pending_yves_approval", "auto_send_pending",
        }:
            return True
        return False

    # Camille traite le juridique sur yves@ (et info@) — collection 'camilleEmails'
    try:
        camille_record = get("camilleEmails", doc_id)
        if _was_actually_drafted(camille_record):
            return "camille"
    except Exception:
        pass
    # Sophie polle info@ — collection 'sophieEmails' (théoriquement pas yves@,
    # mais on sécurise en cas de doublon de routage)
    try:
        sophie_record = get("sophieEmails", doc_id)
        if _was_actually_drafted(sophie_record):
            return "sophie"
    except Exception:
        pass
    return None


# ── Draft ────────────────────────────────────────────────────────
def store_draft(*, incoming_email_id: str, source_mailbox: str, draft: Dict[str, Any],
                triage: Dict[str, Any], to_recipient: str,
                cc_recipients: Optional[list] = None,
                initial_status: str = "pending_yves_approval",
                auto_send_reason: str = "") -> str:
    # Bug fix 2026-05-05 : Firestore limite chaque field à 1,048,487 bytes.
    # Les emails entrants avec images base64 inline pouvaient faire exploser
    # cette limite et causer une erreur 400 sur tout le draft (« The value of
    # property "signedHtml" is longer than 1048487 bytes »).
    body_html_safe = _compact_html_for_firestore(draft.get("body_html"))
    signed_html_safe = _compact_html_for_firestore(draft.get("signed_html"))

    payload = {
        "incomingEmailId": incoming_email_id,
        "sourceMailbox": source_mailbox,
        "persona": draft.get("persona"),
        "fromUser": draft.get("from_user"),
        "toRecipient": to_recipient,
        "ccRecipients": cc_recipients or [],
        "subject": draft.get("subject"),
        "language": draft.get("language"),
        "bodyHtml": body_html_safe,
        "signedHtml": signed_html_safe,
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

    # Bug fix 2026-05-10 (anti-spam dédup self) : marquer l'email comme
    # drafté pour que process_one_message skip aux prochains ticks du cron
    # (sinon Béatrice re-drafte le même email aux 10 min → 8 rappels/h vers
    # la boîte d'Yves). Voir agents/shared/agent_dedup.py.
    try:
        update(COLLECTION_EMAILS, incoming_email_id,
               {"draftId": doc_id, "status": "drafted"})
    except Exception as e:
        # Best-effort : si update échoue, le draft est quand même créé.
        # Le cron re-tentera mais c'est moins grave que de bloquer.
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


def mark_draft_rejected(draft_id: str, *, reason: str = "") -> None:
    update(COLLECTION_DRAFTS, draft_id,
           {"status": "rejected", "rejectedAt": _now(), "rejectionReason": reason})
    audit_log(agent=AGENT_NAME, action="reject_draft", target_type=COLLECTION_DRAFTS,
              target_id=draft_id, details={"reason": reason})


# ── Notification escalade Yves (3 boutons HMAC) ───────────────────
def send_escalation_notification_to_yves(
    draft_id: str, *, subject: str, to_recipient: str, summary: str,
    body_html_preview: str = "", cc_recipients: Optional[list] = None,
    source_mailbox: str = "",
    dashboard_url: str = "https://capitalnorvex.com/beatrice-admin.html",
) -> bool:
    """Notification d'approbation requise — Yves clique pour envoyer le draft."""
    from agents.shared.email_sender import send_email
    try:
        approve_url = _build_approval_url(draft_id, "approve")
        reject_url = _build_approval_url(draft_id, "reject")
        modify_url = _build_approval_url(draft_id, "modify")
    except RuntimeError:
        approve_url = reject_url = modify_url = dashboard_url

    cc_str = ", ".join(cc_recipients) if cc_recipients else "(aucun)"
    preview_block = f'''<div style="margin:24px 0;border:1px solid #e5e5e7;border-radius:8px;overflow:hidden;">
  <div style="background:#f4f4f6;padding:10px 16px;font-size:12px;color:#555;font-weight:600;text-transform:uppercase;letter-spacing:.5px;">Aperçu de la réponse proposée (signée Yves Barrette)</div>
  <div style="padding:20px;max-height:480px;overflow:auto;background:white;font-size:14px;line-height:1.55;">{body_html_preview}</div>
</div>''' if body_html_preview else ""

    body = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,sans-serif;max-width:720px;margin:0 auto;padding:24px;color:#1a1a1a;">
<div style="background:linear-gradient(135deg,#1a1a1a 0%,#2a2a2a 100%);color:white;padding:24px;border-radius:12px 12px 0 0;">
  <div style="font-size:12px;letter-spacing:2px;color:#C9A227;font-weight:600;">BÉATRICE — ASSISTANTE EXÉCUTIVE (interne)</div>
  <div style="font-size:22px;font-family:'Playfair Display',Georgia,serif;margin-top:4px;">Approbation requise</div>
  <div style="font-size:13px;opacity:.85;margin-top:6px;">Draft signé "Yves Barrette" prêt à partir.</div>
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
  <a href="{approve_url}" style="display:inline-block;background:#2d8a3e;color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:600;margin:4px 6px;font-size:15px;">Approuver et envoyer</a>
  <a href="{modify_url}" style="display:inline-block;background:#1a1a1a;color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:600;margin:4px 6px;font-size:15px;">Modifier dans dashboard</a>
  <a href="{reject_url}" style="display:inline-block;background:#c33;color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:600;margin:4px 6px;font-size:15px;">Rejeter</a>
</div>
<p style="text-align:center;color:#777;font-size:12px;margin-top:16px;">Liens valides 7 jours · ID draft : <code>{draft_id}</code></p>
<hr style="border:none;border-top:1px solid #e5e5e7;margin:24px 0;">
<p style="font-size:12px;color:#888;text-align:center;">Dashboard : <a href="{dashboard_url}" style="color:#C9A227;">{dashboard_url}</a></p>
</div></body></html>"""

    ok = send_email(to=YVES_APPROVAL_INBOX,
                    subject=f"[Béatrice] Approbation requise — {subject}",
                    html=body, from_user=YVES_APPROVAL_INBOX)
    audit_log(agent=AGENT_NAME, action="notify_yves_for_approval",
              target_type=COLLECTION_DRAFTS, target_id=draft_id,
              result="success" if ok else "error")

    # ── MODE MOBILE : envoyer aussi un SMS si Yves est sur la route ──
    # Lecture Firestore system/beatrice_settings.mobile_mode (bool).
    # Si actif → call /api/beatrice-sms-notify avec mêmes liens HMAC.
    try:
        _send_sms_if_mobile_mode_active(
            draft_id=draft_id,
            subject=subject,
            from_name=to_recipient,
            summary=summary,
            approve_url=approve_url,
            reject_url=reject_url,
            modify_url=modify_url,
        )
    except Exception as e:
        # Mode Mobile = best-effort, ne JAMAIS bloquer l'email d'approbation
        audit_log(agent=AGENT_NAME, action="sms_notify_failed",
                  target_type=COLLECTION_DRAFTS, target_id=draft_id,
                  result="error", details={"error": str(e)[:300]})

    return ok


def _send_sms_if_mobile_mode_active(*, draft_id: str, subject: str,
                                     from_name: str, summary: str,
                                     approve_url: str, reject_url: str,
                                     modify_url: str) -> None:
    """Si Firestore system/beatrice_settings.mobile_mode == True, envoie un
    SMS via /api/beatrice-sms-notify (Twilio).

    Tout best-effort : aucune exception ne doit casser le flow d'email
    d'approbation principal.
    """
    from agents.shared.firestore_client import get as fs_get

    settings = fs_get("system", "beatrice_settings") or {}
    if not settings.get("mobile_mode"):
        return  # Mode Bureau, on ne fait rien

    import urllib.request
    import urllib.error
    import json as _json

    internal_secret = os.getenv("INTERNAL_SECRET")
    if not internal_secret:
        audit_log(agent=AGENT_NAME, action="sms_notify_skipped",
                  target_type=COLLECTION_DRAFTS, target_id=draft_id,
                  result="skipped", details={"reason": "INTERNAL_SECRET manquant"})
        return

    base_url = os.getenv("PUBLIC_SITE_URL", "https://capitalnorvex.com")
    url = f"{base_url}/api/beatrice-sms-notify"
    payload = {
        "draftId": draft_id, "subject": subject, "fromName": from_name,
        "summary": summary, "approveUrl": approve_url,
        "rejectUrl": reject_url, "modifyUrl": modify_url,
    }
    req = urllib.request.Request(
        url, data=_json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "X-Internal-Secret": internal_secret},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
        audit_log(agent=AGENT_NAME, action="sms_notify_sent",
                  target_type=COLLECTION_DRAFTS, target_id=draft_id,
                  result="success",
                  details={"sid": data.get("sid"), "to": data.get("to")})
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        audit_log(agent=AGENT_NAME, action="sms_notify_http_error",
                  target_type=COLLECTION_DRAFTS, target_id=draft_id,
                  result="error", details={"status": e.code, "body": body})


# ── Notification AUTO-SEND Yves (info, sans boutons) ──────────────
# Conservé pour symétrie d'API même si autoSendSafe est forcé à False
# côté triage Béatrice (le path auto-send ne devrait JAMAIS s'activer).
def send_auto_send_notification_to_yves(
    draft_id: str, *, subject: str, to_recipient: str, summary: str,
    body_html_preview: str = "", cc_recipients: Optional[list] = None,
    source_mailbox: str = "", auto_send_reason: str = "",
    dashboard_url: str = "https://capitalnorvex.com/beatrice-admin.html",
) -> bool:
    from agents.shared.email_sender import send_email

    cc_str = ", ".join(cc_recipients) if cc_recipients else "(aucun)"
    preview_block = f'''<div style="margin:24px 0;border:1px solid #e5e5e7;border-radius:8px;overflow:hidden;">
  <div style="background:#f4f4f6;padding:10px 16px;font-size:12px;color:#555;font-weight:600;text-transform:uppercase;letter-spacing:.5px;">Réponse envoyée (signée Yves Barrette)</div>
  <div style="padding:20px;max-height:480px;overflow:auto;background:white;font-size:14px;line-height:1.55;">{body_html_preview}</div>
</div>''' if body_html_preview else ""

    body = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,sans-serif;max-width:720px;margin:0 auto;padding:24px;color:#1a1a1a;">
<div style="background:linear-gradient(135deg,#1c5d2c 0%,#2d8a3e 100%);color:white;padding:24px;border-radius:12px 12px 0 0;">
  <div style="font-size:12px;letter-spacing:2px;color:#C9A227;font-weight:600;">BÉATRICE — ASSISTANTE EXÉCUTIVE (interne)</div>
  <div style="font-size:22px;font-family:'Playfair Display',Georgia,serif;margin-top:4px;">Réponse envoyée pour information</div>
</div>
<div style="background:#fafafa;padding:24px;border:1px solid #e5e5e7;border-top:none;border-radius:0 0 12px 12px;">
<table style="width:100%;border-collapse:collapse;margin-bottom:16px;">
  <tr><td style="padding:6px 0;color:#666;font-size:13px;">Boîte source</td><td style="padding:6px 0;font-family:monospace;">{source_mailbox}</td></tr>
  <tr><td style="padding:6px 0;color:#666;font-size:13px;">Destinataire</td><td style="padding:6px 0;font-family:monospace;">{to_recipient}</td></tr>
  <tr><td style="padding:6px 0;color:#666;font-size:13px;">CC</td><td style="padding:6px 0;font-family:monospace;font-size:13px;">{cc_str}</td></tr>
  <tr><td style="padding:6px 0;color:#666;font-size:13px;">Objet</td><td style="padding:6px 0;font-weight:600;">{subject}</td></tr>
</table>
{f'<div style="background:#e8f5e9;border-left:3px solid #2d8a3e;padding:10px 16px;font-size:13px;margin:12px 0;"><strong>Pourquoi auto-send :</strong> {auto_send_reason}</div>' if auto_send_reason else ''}
<div style="background:#f0f4f7;border-left:3px solid #C9A227;padding:12px 16px;margin:16px 0;font-size:14px;">
  <strong>Résumé du courriel reçu :</strong><br>{summary}
</div>
{preview_block}
<hr style="border:none;border-top:1px solid #e5e5e7;margin:24px 0;">
<p style="font-size:12px;color:#888;text-align:center;">Historique complet : <a href="{dashboard_url}" style="color:#C9A227;">{dashboard_url}</a></p>
</div></body></html>"""

    ok = send_email(to=YVES_APPROVAL_INBOX,
                    subject=f"[Béatrice — pour info] Envoyé : {subject}",
                    html=body, from_user=YVES_APPROVAL_INBOX)
    audit_log(agent=AGENT_NAME, action="notify_yves_auto_sent",
              target_type=COLLECTION_DRAFTS, target_id=draft_id,
              result="success" if ok else "error")
    return ok
