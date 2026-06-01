"""Sender Camille — Microsoft Graph natif avec support CC + BCC.

Le sender partagé `agents/shared/email_sender.py` ne supporte pas CC.
Ce module l'étend pour Camille (Yves toujours en CC sur info@/camille@).

Fallback SendGrid si Graph KO.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from typing import List, Optional

from agents.shared.auth import get_graph_token


def send_via_graph_with_cc(
    *,
    to: str,
    subject: str,
    html: str,
    from_user: str,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[dict]] = None,
    save_to_sent_items: bool = True,
) -> bool:
    """Envoie via Microsoft Graph avec CC/BCC. Retourne True/False.

    `attachments`: liste de dicts {name, contentType, contentBytes (b64 ou bytes)}
    """
    try:
        token = get_graph_token()
    except Exception as e:
        print(f"[camille.sender] Graph token failed: {e}")
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

    def _recip(addr: str) -> dict:
        return {"emailAddress": {"address": addr}}

    message = {
        "subject": subject,
        "body": {"contentType": "HTML", "content": html},
        "toRecipients": [_recip(to)],
        "from": {"emailAddress": {"address": from_user}},
        "replyTo": [_recip(from_user)],
        "internetMessageHeaders": [
            {"name": "X-Capital-Norvex-Type", "value": "transactional"},
            {"name": "X-Capital-Norvex-Agent", "value": "camille_norvex_counsel"},
            {"name": "X-Auto-Response-Suppress", "value": "All"},
        ],
    }
    if cc:
        message["ccRecipients"] = [_recip(c) for c in cc if c]
    if bcc:
        message["bccRecipients"] = [_recip(b) for b in bcc if b]
    if msg_attachments:
        message["attachments"] = msg_attachments

    payload = {"message": message, "saveToSentItems": save_to_sent_items}
    body = json.dumps(payload).encode("utf-8")
    url = f"https://graph.microsoft.com/v1.0/users/{from_user}/sendMail"
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
        print(f"[camille.sender] Graph sendMail HTTPError: {e.code} {err}")
        return False
    except Exception as e:
        print(f"[camille.sender] Graph sendMail failed: {e}")
        return False


def send_via_sendgrid_with_cc(
    *,
    to: str,
    subject: str,
    html: str,
    from_user: str,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    from_name: str = "Capital Norvex",
) -> bool:
    """Fallback SendGrid avec CC/BCC."""
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        print("[camille.sender] SENDGRID_API_KEY manquant — fallback impossible")
        return False
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Bcc, Cc, Mail
    except ImportError:
        print("[camille.sender] librairie sendgrid non installée")
        return False

    msg = Mail(
        from_email=(from_user, from_name),
        to_emails=to,
        subject=subject,
        html_content=html,
    )
    for c in cc or []:
        if c:
            msg.add_cc(Cc(c))
    for b in bcc or []:
        if b:
            msg.add_bcc(Bcc(b))
    try:
        sg = SendGridAPIClient(api_key)
        resp = sg.send(msg)
        return 200 <= resp.status_code < 300
    except Exception as e:
        print(f"[camille.sender] SendGrid failed: {e}")
        return False


def send_email_with_cc(
    *,
    to: str,
    subject: str,
    html: str,
    from_user: str,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[dict]] = None,
) -> bool:
    """Envoi Camille/Sophie avec CC.

    🚨 BYPASS M365 HRDP (bounce 5.7.708) — Yves 2026-05-04
    M365 sortant via Graph se fait régulièrement blacklister par Gmail/Yahoo
    (HRDP = High Risk Delivery Pool). Solution : SendGrid en priorité
    (Domain Auth verified depuis 2026-05-01).

    Stratégie :
    - Recipient externe (gmail/yahoo/hotmail/etc.) → SendGrid d'abord
    - Recipient interne (@capitalnorvex.com) → Graph d'abord (intra-tenant OK)
    - Fallback systématique sur l'autre si premier échoue
    - Override possible : FORCE_SENDGRID=true dans .env → toujours SendGrid

    NOTE : SendGrid ne supporte pas les attachments via cette fonction (à
    enrichir si besoin). Pour les emails AVEC pièces jointes (lettres
    engagement Camille), Graph reste le path car attachements >>> bounce risk.
    """
    force_sendgrid = os.getenv("FORCE_SENDGRID", "").strip().lower() in ("true", "1", "yes")
    is_internal = (to or "").strip().lower().endswith("@capitalnorvex.com")
    has_attachments = bool(attachments)

    # Path 1 : envois avec pièces jointes → Graph d'abord (SendGrid attachment pas géré ici)
    if has_attachments:
        if send_via_graph_with_cc(
            to=to, subject=subject, html=html, from_user=from_user,
            cc=cc, bcc=bcc, attachments=attachments,
        ):
            return True
        print("[sender] Graph KO avec attachments → SendGrid (sans attachments — DEGRADED)")
        return send_via_sendgrid_with_cc(
            to=to, subject=subject, html=html, from_user=from_user, cc=cc, bcc=bcc
        )

    # Path 2 : envoi externe (Gmail/Yahoo/etc.) → SendGrid d'abord (évite HRDP)
    if force_sendgrid or not is_internal:
        if send_via_sendgrid_with_cc(
            to=to, subject=subject, html=html, from_user=from_user, cc=cc, bcc=bcc,
        ):
            return True
        print("[sender] SendGrid KO → fallback Graph M365…")
        return send_via_graph_with_cc(
            to=to, subject=subject, html=html, from_user=from_user, cc=cc, bcc=bcc,
        )

    # Path 3 : envoi interne capitalnorvex.com → Graph (intra-tenant pas de HRDP)
    if send_via_graph_with_cc(
        to=to, subject=subject, html=html, from_user=from_user, cc=cc, bcc=bcc,
    ):
        return True
    print("[sender] Graph interne KO → fallback SendGrid…")
    return send_via_sendgrid_with_cc(
        to=to, subject=subject, html=html, from_user=from_user, cc=cc, bcc=bcc
    )
