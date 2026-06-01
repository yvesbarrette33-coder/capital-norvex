"""Triage Karine — détecte les emails financiers (et économise sur l'API LLM)."""
from __future__ import annotations

import json
from typing import Dict, Any

import anthropic

from .config import (
    ANTHROPIC_API_KEY,
    FINANCIAL_ATTACHMENT_KEYWORDS,
    FINANCIAL_SENDER_PATTERNS,
    FINANCIAL_SUBJECT_KEYWORDS,
    MAX_TOKENS_TRIAGE,
    MODEL_TRIAGE,
)
from .system_prompts import TRIAGE_PROMPT


def is_likely_financial(*, from_address: str, subject: str, body_text: str,
                        attachments: list[dict]) -> bool:
    """Pré-filtre rapide AVANT appel Claude (économie API)."""
    fa = (from_address or "").lower()
    sj = (subject or "").lower()
    bd = (body_text or "")[:600].lower()

    # 1. Sender pattern
    for pattern in FINANCIAL_SENDER_PATTERNS:
        if pattern in fa:
            return True

    # 2. Subject keyword
    for kw in FINANCIAL_SUBJECT_KEYWORDS:
        if kw in sj or kw in bd:
            return True

    # 3. Pièce jointe avec mot-clé financier dans le nom
    for att in attachments or []:
        name = (att.get("name") or "").lower()
        for kw in FINANCIAL_ATTACHMENT_KEYWORDS:
            if kw in name:
                return True

    # 4. Pièce jointe PDF + sujet contenant un montant ($)
    has_pdf = any(
        (att.get("contentType") or "").lower() == "application/pdf"
        or (att.get("name") or "").lower().endswith(".pdf")
        for att in attachments or []
    )
    if has_pdf and ("$" in subject or "$" in body_text[:300]):
        return True

    return False


def triage_email(*, from_address: str, subject: str, body_text: str,
                 attachments: list[dict], received_at_iso: str) -> Dict[str, Any]:
    """Triage Sonnet 4.6 : retourne {category, confidence, has_extractable_pdf, ...}."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    has_pdf = any(
        (att.get("contentType") or "").lower() == "application/pdf"
        or (att.get("name") or "").lower().endswith(".pdf")
        for att in attachments or []
    )
    attachment_summary = (
        ", ".join(att.get("name", "") for att in attachments[:5])
        if attachments else "aucune"
    )

    user_message = f"""Courriel à analyser :

EXPÉDITEUR : {from_address}
SUJET : {subject}
REÇU LE : {received_at_iso}
PIÈCES JOINTES : {attachment_summary}
PDF présent : {has_pdf}

CORPS (extrait) :
{(body_text or "")[:2000]}

Réponds avec le JSON demandé."""

    try:
        resp = client.messages.create(
            model=MODEL_TRIAGE,
            max_tokens=MAX_TOKENS_TRIAGE,
            system=TRIAGE_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = resp.content[0].text.strip()
        # Extraire JSON
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            return _fallback_triage(has_pdf)
        return json.loads(raw[start : end + 1])
    except Exception:
        return _fallback_triage(has_pdf)


def _fallback_triage(has_pdf: bool) -> Dict[str, Any]:
    return {
        "category": "non_financier",
        "confidence": 0,
        "has_extractable_pdf": has_pdf,
        "preliminary_supplier_or_payer": None,
        "language": "fr",
        "summary": "Triage failed — fallback",
        "notes": "fallback after exception",
    }
