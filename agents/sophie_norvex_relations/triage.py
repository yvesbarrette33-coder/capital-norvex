"""Triage Sophie — Sonnet 4.6 sur emails entrants info@."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from .config import MAX_TOKENS_TRIAGE, MODEL_TRIAGE
from .system_prompts import TRIAGE_SYSTEM


def triage_email(
    *,
    from_address: str,
    subject: str,
    body_text: str,
    received_mailbox: str,
    received_at_iso: Optional[str] = None,
) -> Dict[str, Any]:
    """Trie un email et retourne dict structuré (idem Camille pattern)."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY manquant — Sophie ne peut pas trier")

    try:
        import anthropic
    except ImportError:
        raise RuntimeError("Librairie 'anthropic' non installée")

    client = anthropic.Anthropic(api_key=api_key)
    body_truncated = body_text[:8000]
    truncation_note = (
        f"\n\n[…corps tronqué — {len(body_text)} caractères au total]"
        if len(body_text) > 8000 else ""
    )
    user_msg = "\n".join([
        f"Boîte de réception : {received_mailbox}",
        f"Date reçue        : {received_at_iso or 'inconnue'}",
        f"Expéditeur        : {from_address}",
        f"Objet             : {subject}",
        "",
        "─── Corps du courriel ───",
        body_truncated + truncation_note,
    ])

    msg = client.messages.create(
        model=MODEL_TRIAGE,
        max_tokens=MAX_TOKENS_TRIAGE,
        system=TRIAGE_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )

    text = ""
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            text += block.text

    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise RuntimeError(f"Triage Sophie : JSON manquant. Reçu : {text[:200]!r}")

    parsed = json.loads(text[start: end + 1])
    parsed.setdefault("category", "autre_general")
    parsed.setdefault("priority", "normale")
    parsed.setdefault("language", "fr")
    parsed.setdefault("summary", "")
    parsed.setdefault("actionRequested", "")
    parsed.setdefault("deadlineMentioned", None)
    parsed.setdefault("suggestedDraftType", "accuse_reception")
    parsed.setdefault("autoSendSafe", True)  # défaut autonomie (règle Yves)
    parsed.setdefault("autoSendReason", "")
    parsed.setdefault("redFlags", [])
    return parsed
