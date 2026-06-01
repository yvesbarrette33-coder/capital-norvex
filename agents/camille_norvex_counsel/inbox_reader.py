"""Lecture des boîtes Inbox via Microsoft Graph (info@ + yves@ + camille@ futur).

Utilise la même auth Graph que `agents/shared/auth.py` (Azure App "Norvex-Agent 2026").

Permission requise sur Azure App :
    - Mail.Read (Application) — pour lire la Inbox des utilisateurs
    - Mail.ReadWrite (Application) — pour marquer comme lu (optionnel)
"""
from __future__ import annotations

import urllib.parse
import urllib.request
import urllib.error
import json as _json
from typing import Any, Dict, List, Optional

from agents.shared.auth import get_graph_token

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _get(url: str, token: str) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return _json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Graph GET {url} → {e.code} {err}") from e


def list_inbox_messages(
    mailbox: str,
    *,
    top: int = 25,
    only_unread: bool = True,
    since_iso: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Liste les messages de la Inbox d'une boîte.

    Args:
        mailbox: ex "info@capitalnorvex.com"
        top: max messages (défaut 25, max Graph 1000)
        only_unread: filtre isRead eq false
        since_iso: filtre receivedDateTime ge {since_iso} (UTC, format ISO)

    Returns:
        Liste de messages bruts Graph (id, subject, from, receivedDateTime,
        bodyPreview, isRead, conversationId, etc.)
    """
    token = get_graph_token()
    filters = []
    if only_unread:
        filters.append("isRead eq false")
    if since_iso:
        filters.append(f"receivedDateTime ge {since_iso}")
    filter_str = " and ".join(filters)

    params = {
        "$top": str(top),
        "$orderby": "receivedDateTime desc",
        "$select": (
            "id,subject,from,toRecipients,ccRecipients,receivedDateTime,"
            "bodyPreview,isRead,conversationId,internetMessageId,hasAttachments"
        ),
    }
    if filter_str:
        params["$filter"] = filter_str

    qs = urllib.parse.urlencode(params)
    url = f"{GRAPH_BASE}/users/{urllib.parse.quote(mailbox)}/mailFolders/Inbox/messages?{qs}"

    payload = _get(url, token)
    return payload.get("value", [])


def get_message_full(mailbox: str, message_id: str) -> Dict[str, Any]:
    """Récupère un message complet avec le body texte + HTML."""
    token = get_graph_token()
    url = (
        f"{GRAPH_BASE}/users/{urllib.parse.quote(mailbox)}"
        f"/messages/{urllib.parse.quote(message_id)}"
    )
    return _get(url, token)


def extract_plain_text(message: Dict[str, Any]) -> str:
    """Extrait le corps texte d'un message Graph (préfère text/plain)."""
    body = message.get("body", {}) or {}
    content_type = body.get("contentType", "").lower()
    content = body.get("content", "") or ""
    if content_type == "html":
        # Très basique HTML → text. Pas de bs4 pour rester sans dépendance.
        import re as _re

        text = _re.sub(r"<br\s*/?>", "\n", content, flags=_re.IGNORECASE)
        text = _re.sub(r"</p>", "\n\n", text, flags=_re.IGNORECASE)
        text = _re.sub(r"<[^>]+>", "", text)
        # Décoder entités HTML basiques
        for entity, char in (
            ("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
            ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'"),
        ):
            text = text.replace(entity, char)
        return text.strip()
    return content.strip()


def normalize_for_triage(mailbox: str, message: Dict[str, Any]) -> Dict[str, Any]:
    """Convertit un message Graph en dict prêt pour triage_email()."""
    sender = (message.get("from") or {}).get("emailAddress") or {}
    to_list = [
        (r.get("emailAddress") or {}).get("address", "")
        for r in (message.get("toRecipients") or [])
    ]
    cc_list = [
        (r.get("emailAddress") or {}).get("address", "")
        for r in (message.get("ccRecipients") or [])
    ]
    return {
        "graph_id": message.get("id"),
        "internet_message_id": message.get("internetMessageId"),
        "conversation_id": message.get("conversationId"),
        "received_mailbox": mailbox,
        "received_at_iso": message.get("receivedDateTime"),
        "from": sender.get("address", ""),
        "from_name": sender.get("name", ""),
        "to": ", ".join(to_list),
        "cc": ", ".join(cc_list),
        "subject": message.get("subject", "(sans objet)"),
        "body_text": extract_plain_text(message),
        "has_attachments": bool(message.get("hasAttachments")),
    }


def mark_as_read(mailbox: str, message_id: str) -> bool:
    """Marque un message comme lu (optionnel, requiert Mail.ReadWrite)."""
    token = get_graph_token()
    url = (
        f"{GRAPH_BASE}/users/{urllib.parse.quote(mailbox)}"
        f"/messages/{urllib.parse.quote(message_id)}"
    )
    body = _json.dumps({"isRead": True}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        print(f"[inbox_reader] mark_as_read failed: {e.code}")
        return False
