"""Drafting Sophie — Opus 4.6 + adaptive thinking."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from .config import MAX_TOKENS_DRAFTING, MODEL_DRAFTING, get_mailbox_config
from .system_prompts import get_drafting_system


def _build_signature_html(language: str = "fr") -> str:
    """Signature HTML Sophie — design système unifié 2026-05-04.

    Délègue à `agents.shared.signature_block.signature_sophie()` qui retourne :
    - Bandeau or sur fond clair (style « LIGHT » pour agents IA)
    - Mention IA + phrase « validées par la direction » + disclaimer
    - Adresse + email + site (pas de tél = agent IA)
    - Cohérent avec design unifié Yves/Suzanne (DARK) / Sophie/Camille (LIGHT)
    """
    from agents.shared.signature_block import signature_sophie
    return signature_sophie(language=language)


def draft_reply(
    *,
    source_mailbox: str,
    incoming_email: Dict[str, Any],
    triage_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Produit un draft Sophie signé."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY manquant — Sophie ne peut pas drafter")

    try:
        import anthropic
    except ImportError:
        raise RuntimeError("Librairie 'anthropic' non installée")

    mb_config = get_mailbox_config(source_mailbox)
    persona = mb_config["persona"]
    system_prompt = get_drafting_system(persona)
    client = anthropic.Anthropic(api_key=api_key)

    auto_send = bool(triage_result.get("autoSendSafe"))
    mode_block = (
        "MODE AUTO-SEND : ta réponse partira DIRECTEMENT au destinataire (Yves CC).\n"
        "    → Sois IRRÉPROCHABLE. Aucun engagement spécifique. Donne fourchettes générales."
        if auto_send else
        "MODE ESCALADE : ta réponse sera approuvée par Yves AVANT envoi.\n"
        "    → Tu peux suggérer ; Yves validera, modifiera ou rejettera."
    )

    user_blocks = [
        f"Boîte source     : {source_mailbox}",
        f"Type suggéré     : {triage_result.get('suggestedDraftType', 'inconnu')}",
        f"Catégorie        : {triage_result.get('category', 'autre')}",
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
        "Rédige un draft de réponse cohérent avec ta persona Sophie — NORVEX RELATIONS™.",
        "Donne les fourchettes générales (pas de chiffres exacts d'engagement).",
        "Invite à passer par Score Norvex / formulaire courtier / suivi Yves selon contexte.",
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
        raise RuntimeError(f"Drafting Sophie : JSON manquant. Reçu : {text[:300]!r}")

    parsed = json.loads(text[start: end + 1])
    parsed.setdefault("subject", "Re: Votre demande")
    parsed.setdefault("language", triage_result.get("language", "fr"))
    parsed.setdefault("body_html", "<p>(corps vide)</p>")
    parsed.setdefault("internal_note_for_yves", "")
    parsed.setdefault("needs_yves_input_before_send", False)
    parsed.setdefault("open_questions", [])

    parsed["signed_html"] = parsed["body_html"] + _build_signature_html()
    parsed["persona"] = persona
    parsed["from_user"] = source_mailbox
    return parsed
