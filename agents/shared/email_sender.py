"""Envoi de courriels — Microsoft Graph d'abord, SendGrid en fallback.

Réutilise la même logique que agent_docs.py:
- Graph: POST /users/{MAIL_USER}/sendMail
- SendGrid: API v3 (Single Sender vérifié)

Variables d'env requises:
- MAIL_USER (ex: info@capitalnorvex.com)
- AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET (Graph)
- SENDGRID_API_KEY (fallback)
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request
import urllib.error
from typing import List, Optional

from .auth import get_graph_token

MAIL_USER = os.getenv("MAIL_USER", "info@capitalnorvex.com")


def send_via_graph(
    to: str,
    subject: str,
    html: str,
    attachments: Optional[List[dict]] = None,
    from_user: Optional[str] = None,
) -> bool:
    """Envoie via Microsoft Graph. Retourne True/False.

    `attachments`: liste de dicts {name, contentType, contentBytes (b64 ou bytes)}
    """
    sender = from_user or MAIL_USER
    try:
        token = get_graph_token()
    except Exception as e:
        print(f"[email_sender] Graph token failed: {e}")
        return False

    msg_attachments = []
    for att in attachments or []:
        content = att.get("contentBytes")
        if isinstance(content, bytes):
            content = base64.b64encode(content).decode("ascii")
        msg_attachments.append(
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": att.get("name", "fichier"),
                "contentType": att.get("contentType", "application/octet-stream"),
                "contentBytes": content,
            }
        )

    message = {
        "subject": subject,
        "body": {"contentType": "HTML", "content": html},
        "toRecipients": [{"emailAddress": {"address": to}}],
        "from": {"emailAddress": {"address": sender}},
        "replyTo": [{"emailAddress": {"address": sender}}],
        "internetMessageHeaders": [
            {"name": "X-Capital-Norvex-Type", "value": "transactional"},
            {"name": "X-Auto-Response-Suppress", "value": "All"},
        ],
    }
    if msg_attachments:
        message["attachments"] = msg_attachments

    payload = {"message": message, "saveToSentItems": True}
    body = json.dumps(payload).encode("utf-8")
    url = f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail"
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"[email_sender] Graph sendMail HTTPError: {e.code} {err}")
        return False
    except Exception as e:
        print(f"[email_sender] Graph sendMail failed: {e}")
        return False


def send_via_sendgrid(
    to: str,
    subject: str,
    html: str,
    from_user: Optional[str] = None,
    from_name: str = "Capital Norvex",
) -> bool:
    """Fallback SendGrid (Single Sender vérifié)."""
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        print("[email_sender] SENDGRID_API_KEY manquant — fallback impossible")
        return False
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
    except ImportError:
        print("[email_sender] librairie sendgrid non installée")
        return False

    sender = from_user or MAIL_USER
    msg = Mail(
        from_email=(sender, from_name),
        to_emails=to,
        subject=subject,
        html_content=html,
    )
    try:
        sg = SendGridAPIClient(api_key)
        resp = sg.send(msg)
        return 200 <= resp.status_code < 300
    except Exception as e:
        print(f"[email_sender] SendGrid failed: {e}")
        return False


# Domaines internes (envois Graph OK car même tenant M365)
_INTERNAL_DOMAINS = ("capitalnorvex.com",)


def _is_internal_recipient(addr: Optional[str]) -> bool:
    """True si le destinataire est sur un domaine interne (Graph OK)."""
    if not addr or "@" not in addr:
        return False
    domain = addr.rsplit("@", 1)[-1].lower().strip()
    return any(domain == d or domain.endswith("." + d) for d in _INTERNAL_DOMAINS)


def send_email(
    to: str,
    subject: str,
    html: str,
    attachments: Optional[List[dict]] = None,
    from_user: Optional[str] = None,
) -> bool:
    """Routage intelligent Graph/SendGrid.

    🐛 Bug fix 2026-05-05 PM : avant ce patch, on tentait TOUJOURS Graph en
    premier. Problème : Graph répond 200 OK (mail accepté), puis le MTA distant
    bounce avec « 550 5.7.708 Service unavailable » (HRDP de M365 envoie depuis
    une IP blocklistée par Gmail/etc.) — `send_via_graph` ne voit pas le bounce
    et `send_email` retourne True alors que l'email N'EST PAS LIVRÉ.

    Maintenant :
    - Destinataire INTERNE (capitalnorvex.com) → Graph (rapide, même tenant).
    - Destinataire EXTERNE → SendGrid d'abord (bypass HRDP 5.7.708),
      Graph en fallback si SendGrid down.

    Identique à la logique `sendEmailSmart()` côté Netlify (Camille).

    🛡️ Garde-fou blacklist Yves 2026-05-08 : refus immédiat si l'email est sur
    la blacklist permanente (litige TCJ, Langlois, etc.). Anti-récidive : un
    `excluded=true` Firestore peut être contourné par bug ou agent autonome,
    mais ce check hardcodé est le dernier rempart avant SendGrid/Graph.
    """
    # Garde-fou blacklist permanente — REFUS HARDCODÉ
    try:
        from agents.shared.blacklist import is_blacklisted, reason_for
    except ImportError:
        from .blacklist import is_blacklisted, reason_for  # type: ignore
    if is_blacklisted(to):
        print(f"[email_sender] ⛔ BLACKLIST refusé : {to} — {reason_for(to)}")
        return False

    if _is_internal_recipient(to):
        if send_via_graph(to, subject, html, attachments=attachments, from_user=from_user):
            return True
        print("[email_sender] Graph KO (interne) → fallback SendGrid…")
        return send_via_sendgrid(to, subject, html, from_user=from_user)

    # Destinataire externe : SendGrid d'abord (évite bounce 5.7.708)
    if send_via_sendgrid(to, subject, html, from_user=from_user):
        return True
    print("[email_sender] SendGrid KO (externe) → fallback Graph (risque bounce 5.7.708)…")
    return send_via_graph(to, subject, html, attachments=attachments, from_user=from_user)
