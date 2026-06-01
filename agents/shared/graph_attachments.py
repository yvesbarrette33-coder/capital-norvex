"""Lecture des pièces jointes via Microsoft Graph.

Module partagé : utilisé par Karine (extraction factures), pourra l'être par
Maestro futur (analyse de documents reçus).

Permission Azure App requise :
    - Mail.Read (Application) — déjà accordée
"""
from __future__ import annotations

import base64
import json as _json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from agents.shared.auth import get_graph_token

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _get_json(url: str, token: str) -> Dict[str, Any]:
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


def list_attachments(mailbox: str, message_id: str) -> List[Dict[str, Any]]:
    """Retourne la liste des attachments du message (métadonnées only).

    Chaque attachment a : id, name, contentType, size, isInline.
    Le contenu binaire (contentBytes) doit être récupéré via download_attachment.
    """
    token = get_graph_token()
    url = (
        f"{GRAPH_BASE}/users/{urllib.parse.quote(mailbox)}"
        f"/messages/{urllib.parse.quote(message_id)}/attachments"
        f"?$select=id,name,contentType,size,isInline"
    )
    payload = _get_json(url, token)
    return payload.get("value", [])


def download_attachment(mailbox: str, message_id: str,
                         attachment_id: str) -> bytes:
    """Télécharge le contenu binaire d'un attachment.

    Retourne les bytes décodés (peut être un PDF, image, etc.).
    """
    token = get_graph_token()
    url = (
        f"{GRAPH_BASE}/users/{urllib.parse.quote(mailbox)}"
        f"/messages/{urllib.parse.quote(message_id)}"
        f"/attachments/{urllib.parse.quote(attachment_id)}"
    )
    payload = _get_json(url, token)
    # Pour fileAttachment, le contenu est dans `contentBytes` (base64).
    content_b64 = payload.get("contentBytes", "")
    if not content_b64:
        return b""
    try:
        return base64.b64decode(content_b64)
    except Exception:
        return b""


def list_attachments_with_content(mailbox: str,
                                    message_id: str) -> List[Dict[str, Any]]:
    """Liste + télécharge tous les attachments d'un coup (utile pour petits emails)."""
    metas = list_attachments(mailbox, message_id)
    out = []
    for m in metas:
        if m.get("isInline"):
            continue  # skip images inline (signatures, etc.)
        try:
            data = download_attachment(mailbox, message_id, m["id"])
            out.append({**m, "data": data})
        except Exception:
            continue
    return out
