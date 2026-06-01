"""Méta-triage Maestro : décide l'agent qui doit traiter chaque email."""
from __future__ import annotations

import json
from typing import Any, Dict

import anthropic

from .config import (
    ANTHROPIC_API_KEY,
    MAX_TOKENS_TRIAGE,
    MODEL_TRIAGE,
)
from .system_prompts import META_TRIAGE_PROMPT


def meta_triage(*, mailbox: str, from_address: str, subject: str,
                 body_text: str, has_attachments: bool,
                 received_at_iso: str) -> Dict[str, Any]:
    """Décide quel agent doit traiter cet email.

    Retour :
        {
          route, confidence, reasoning, secondary_relevance,
          alert_yves_now, estimated_priority, summary, language
        }
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    user_message = f"""Email à router :

REÇU SUR : {mailbox}
EXPÉDITEUR : {from_address}
SUJET : {subject}
REÇU LE : {received_at_iso}
PIÈCES JOINTES : {"oui" if has_attachments else "non"}

CORPS (extrait) :
{(body_text or "")[:2500]}

Décide la route. Réponds avec le JSON demandé."""

    try:
        resp = client.messages.create(
            model=MODEL_TRIAGE,
            max_tokens=MAX_TOKENS_TRIAGE,
            system=META_TRIAGE_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = resp.content[0].text.strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            return _fallback_route("Triage parse error")
        data = json.loads(raw[start : end + 1])
        return _validate_route(data)
    except Exception as e:
        return _fallback_route(f"Triage exception: {e}"[:200])


def _validate_route(data: Dict[str, Any]) -> Dict[str, Any]:
    valid_routes = {
        "to_camille", "to_sophie", "to_beatrice", "to_karine",
        "to_hugo_pipeline", "to_yves_directly", "alert_yves_priority",
        "ignore_no_reply",
    }
    route = data.get("route", "to_yves_directly")
    if route not in valid_routes:
        route = "to_yves_directly"
    data["route"] = route

    try:
        c = int(data.get("confidence", 0))
        data["confidence"] = max(0, min(100, c))
    except (ValueError, TypeError):
        data["confidence"] = 0

    valid_priorities = {"low", "medium", "high", "critical"}
    if data.get("estimated_priority") not in valid_priorities:
        data["estimated_priority"] = "medium"

    if not isinstance(data.get("alert_yves_now"), bool):
        data["alert_yves_now"] = False

    if not isinstance(data.get("secondary_relevance"), list):
        data["secondary_relevance"] = []

    return data


def _fallback_route(reason: str) -> Dict[str, Any]:
    """Si triage échoue : route vers Yves directement (safe default)."""
    return {
        "route": "to_yves_directly",
        "confidence": 0,
        "reasoning": f"Maestro fallback : {reason}",
        "secondary_relevance": [],
        "alert_yves_now": False,
        "estimated_priority": "medium",
        "summary": "Triage failed — Yves to review manually",
        "language": "fr",
    }
