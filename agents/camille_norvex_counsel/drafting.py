"""Pipeline de drafting — Opus 4.6 + adaptive thinking.

Routage automatique selon la persona de la boîte source :
- info@ / camille@  → DRAFTING_INSTITUTIONAL_SYSTEM (signe Camille)
- yves@             → DRAFTING_GHOSTWRITER_SYSTEM   (signe Yves, ghostwriter)
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from .config import (
    MAX_TOKENS_DRAFTING,
    MODEL_DRAFTING,
    get_mailbox_config,
)
from .signatures import build_signature_html
from .system_prompts import get_drafting_system


def draft_reply(
    *,
    source_mailbox: str,
    incoming_email: Dict[str, Any],
    triage_result: Dict[str, Any],
    yves_instructions: Optional[str] = None,
    template_hint: Optional[str] = None,
    dossier_data: Optional[Dict[str, Any]] = None,
    dossier_summary_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Produit un draft de réponse signé selon la persona de la boîte source.

    Retourne :
        {
          "subject", "language", "body_html",
          "internal_note_for_yves", "needs_yves_input_before_send",
          "open_questions",
          "signed_html"  (body_html + signature complète prête à envoyer),
          "persona", "from_user"
        }
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY manquant — Camille ne peut pas drafter")

    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "Librairie 'anthropic' non installée — pip install anthropic"
        )

    mb_config = get_mailbox_config(source_mailbox)
    persona = mb_config["persona"]
    system_prompt = get_drafting_system(persona)

    client = anthropic.Anthropic(api_key=api_key)

    user_blocks = [
        f"Boîte source     : {source_mailbox} (persona : {persona})",
        f"Type suggéré     : {triage_result.get('suggestedDraftType', 'inconnu')}",
        f"Catégorie        : {triage_result.get('category', 'autre')}",
        f"Juridiction      : {triage_result.get('jurisdiction', 'NA')}",
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
        f"Indices dossier  : {', '.join(triage_result.get('dossierHints', []) or []) or 'aucun'}",
        f"Red flags        : {', '.join(triage_result.get('redFlags', []) or []) or 'aucun'}",
    ]

    if dossier_summary_text:
        user_blocks.extend([
            "",
            "─── DOSSIER IDENTIFIÉ — DONNÉES APPROUVÉES ───",
            dossier_summary_text,
            "",
            "⚠️  Tu DOIS utiliser ces données factuelles dans ta réponse.",
            "    Ces éléments sont DÉJÀ APPROUVÉS et signés (lettre d'engagement).",
            "    Tu peux les transmettre, les rappeler, les confirmer.",
            "    Tu ne peux PAS les modifier, les négocier, ni en créer de nouveaux.",
        ])

    if template_hint:
        user_blocks.extend(["", "─── TEMPLATE DE RÉFÉRENCE ───", template_hint])

    if yves_instructions:
        user_blocks.extend(["", "─── INSTRUCTIONS YVES ───", yves_instructions])

    auto_send = bool(triage_result.get("autoSendSafe"))
    mode_block = (
        "MODE AUTO-SEND : ta réponse partira DIRECTEMENT au destinataire (Yves en CC).\n"
        "    → Sois IRRÉPROCHABLE. Aucun engagement nouveau. Aucune décision.\n"
        "    → Limite-toi à transmettre des informations DÉJÀ approuvées dans le dossier."
        if auto_send else
        "MODE ESCALADE : ta réponse sera approuvée par Yves AVANT envoi.\n"
        "    → Tu peux suggérer une réponse ; Yves la validera, modifiera ou rejettera."
    )

    user_blocks.extend(
        [
            "",
            "─── MODE D'ENVOI ───",
            mode_block,
            "",
            "─── DEMANDE ───",
            "Rédige un draft de réponse adapté à la persona de la boîte source,",
            "en respectant les limites fermes (pas d'avis juridique, pas d'engagement",
            "financier sans Yves, etc.). Réponds en JSON strict selon le schéma.",
        ]
    )

    user_msg = "\n".join(user_blocks)

    # Adaptive thinking sur Opus 4.6 (recommandé par doc Anthropic)
    msg = client.messages.create(
        model=MODEL_DRAFTING,
        max_tokens=MAX_TOKENS_DRAFTING,
        thinking={"type": "adaptive"},
        system=system_prompt,
        messages=[{"role": "user", "content": user_msg}],
    )

    # Récupérer uniquement les blocs texte (les blocs thinking sont jetés)
    text = ""
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            text += block.text

    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise RuntimeError(
            f"Drafting : réponse Opus non-JSON. Reçu : {text[:300]!r}"
        )
    json_payload = text[start : end + 1]
    try:
        parsed = json.loads(json_payload)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Drafting : JSON invalide ({e}). Reçu : {json_payload[:300]!r}"
        )

    # Garde-fous champs requis
    parsed.setdefault("subject", "(sans objet)")
    parsed.setdefault("language", triage_result.get("language", "fr"))
    parsed.setdefault("body_html", "<p>(corps vide)</p>")
    parsed.setdefault("internal_note_for_yves", "")
    parsed.setdefault("needs_yves_input_before_send", False)
    parsed.setdefault("open_questions", [])

    # Construction du HTML final avec signature
    signature_html = build_signature_html(
        persona=persona,
        language=parsed["language"],
    )
    parsed["signed_html"] = parsed["body_html"] + signature_html
    parsed["persona"] = persona
    parsed["from_user"] = source_mailbox

    return parsed
