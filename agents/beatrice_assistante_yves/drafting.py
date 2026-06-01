"""Drafting Béatrice — Opus 4.6 + adaptive thinking, ghostwriter Yves."""
from __future__ import annotations

import json
import os
from typing import Any, Dict

from .config import MAX_TOKENS_DRAFTING, MODEL_DRAFTING, get_mailbox_config
from .system_prompts import get_drafting_system


def _build_signature_html(language: str = "fr") -> str:
    """Signature HTML Béatrice — GHOSTWRITER PUR.

    Délègue à `agents.shared.signature_block.signature_yves()` qui retourne
    la signature DARK officielle d'Yves Barrette (Directeur-Fondateur).

    ⚠️ Aucune mention de Béatrice / IA / assistante. Le destinataire reçoit
    une signature 100% identique à celle qu'Yves utilise lui-même.
    """
    from agents.shared.signature_block import signature_yves
    return signature_yves(language=language)


def draft_reply(
    *,
    source_mailbox: str,
    incoming_email: Dict[str, Any],
    triage_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Produit un draft Béatrice signé "Yves Barrette" (ghostwriter pur)."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY manquant — Béatrice ne peut pas drafter")

    try:
        import anthropic
    except ImportError:
        raise RuntimeError("Librairie 'anthropic' non installée")

    mb_config = get_mailbox_config(source_mailbox)
    persona = mb_config["persona"]
    system_prompt = get_drafting_system(persona)
    client = anthropic.Anthropic(api_key=api_key)

    # Béatrice = TOUJOURS escalade Yves (autoSendSafe forcé à False côté triage)
    mode_block = (
        "MODE ESCALADE : ta réponse sera approuvée par Yves AVANT envoi.\n"
        "    → Tu rédiges au nom d'Yves comme un GHOSTWRITER. Yves validera,\n"
        "      modifiera ou rejettera depuis le dashboard."
    )

    user_blocks = [
        f"Boîte source     : {source_mailbox} (yves@)",
        f"Catégorie triage : {triage_result.get('category', 'autre')}",
        f"Langue cible     : {triage_result.get('language', 'fr')}",
        f"Priorité         : {triage_result.get('priority', 'normale')}",
        "",
        "─── COURRIEL REÇU ───",
        f"De     : {incoming_email.get('from', '?')}",
        f"À      : {incoming_email.get('to', '?')}",
        f"Cc     : {incoming_email.get('cc', '')}",
        f"Objet  : {incoming_email.get('subject', '?')}",
        "",
        incoming_email.get("body_text", "")[:12000],
        "",
        "─── CONTEXTE TRIAGE ───",
        f"Résumé           : {triage_result.get('summary', '')}",
        f"Action attendue  : {triage_result.get('actionRequested', '')}",
        f"Échéance         : {triage_result.get('deadlineMentioned') or 'aucune'}",
        f"Red flags        : {', '.join(triage_result.get('redFlags', []) or []) or 'aucun'}",
        "",
        "─── MODE D'ENVOI ───",
        mode_block,
        "",
        "─── DEMANDE ───",
        "Rédige le draft EN TANT QU'YVES BARRETTE (ghostwriter pur).",
        "Voix Yves : ultra-pro mais humain, niveau Stikeman / BlackRock.",
        "Aucune mention de Béatrice, IA, assistante, automatisation.",
        "N'INCLUS PAS la signature — elle est ajoutée automatiquement.",
        "Réponds en JSON strict.",
    ]

    user_msg = "\n".join(user_blocks)

    msg = client.messages.create(
        model=MODEL_DRAFTING,
        max_tokens=MAX_TOKENS_DRAFTING,
        thinking={"type": "adaptive"},
        system=system_prompt,
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
        raise RuntimeError(f"Drafting Béatrice : JSON manquant. Reçu : {text[:300]!r}")

    parsed = json.loads(text[start: end + 1])
    parsed.setdefault("subject", "Re: Votre courriel")
    parsed.setdefault("language", triage_result.get("language", "fr"))
    parsed.setdefault("body_html", "<p>(corps vide)</p>")
    parsed.setdefault("internal_note_for_yves", "")
    parsed.setdefault("needs_yves_input_before_send", False)
    parsed.setdefault("open_questions", [])

    # Concatène le body avec la signature Yves (ghostwriter pur)
    lang = parsed.get("language", "fr")
    parsed["signed_html"] = parsed["body_html"] + _build_signature_html(language=lang)
    parsed["persona"] = persona
    parsed["from_user"] = source_mailbox
    return parsed
