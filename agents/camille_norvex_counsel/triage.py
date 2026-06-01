"""Pipeline de triage des courriels entrants — Sonnet 4.6.

Entrée : un email brut (de/sujet/corps texte)
Sortie : dict structuré {category, priority, dossierHints, summary, ...}
"""
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
    thread_history: Optional[str] = None,
) -> Dict[str, Any]:
    """Trie un courriel reçu et retourne un dict structuré.

    Lève RuntimeError si ANTHROPIC_API_KEY manquante ou si réponse non-JSON.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY manquant — Camille ne peut pas trier")

    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "Librairie 'anthropic' non installée — pip install anthropic"
        )

    client = anthropic.Anthropic(api_key=api_key)

    # Tronquer le corps si extrêmement long pour rester sous budget triage
    body_truncated = body_text[:8000]
    truncation_note = (
        f"\n\n[…corps tronqué — {len(body_text)} caractères au total]"
        if len(body_text) > 8000
        else ""
    )

    user_msg_parts = [
        f"Boîte de réception : {received_mailbox}",
        f"Date reçue        : {received_at_iso or 'inconnue'}",
        f"Expéditeur        : {from_address}",
        f"Objet             : {subject}",
        "",
        "─── Corps du courriel ───",
        body_truncated + truncation_note,
    ]
    if thread_history:
        user_msg_parts.extend(
            ["", "─── Historique du fil (résumé) ───", thread_history[:4000]]
        )
    user_msg = "\n".join(user_msg_parts)

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
    # Extraire le JSON même si le modèle a ajouté du préfixe/suffixe
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise RuntimeError(
            f"Triage : réponse Sonnet non-JSON. Reçu : {text[:200]!r}"
        )
    json_payload = text[start : end + 1]
    try:
        parsed = json.loads(json_payload)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Triage : JSON invalide ({e}). Reçu : {json_payload[:300]!r}")

    # Garde-fous : champs requis
    parsed.setdefault("category", "autre")
    parsed.setdefault("priority", "normale")
    parsed.setdefault("language", "fr")
    parsed.setdefault("jurisdiction", "NA")
    parsed.setdefault("dossierHints", [])
    parsed.setdefault("dossierIdGuess", None)
    parsed.setdefault("summary", "")
    parsed.setdefault("actionRequested", "")
    parsed.setdefault("deadlineMentioned", None)
    parsed.setdefault("requiresHumanLawyer", False)
    parsed.setdefault("requiresYvesDecision", False)
    parsed.setdefault("suggestedDraftType", "no_reply_needed")
    parsed.setdefault("autoSendSafe", True)  # défaut Yves 2026-05-04 : autonomie day-to-day
    parsed.setdefault("autoSendReason", "")
    parsed.setdefault("redFlags", [])

    return parsed
