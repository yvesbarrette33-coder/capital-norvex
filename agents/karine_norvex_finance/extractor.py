"""Extraction OCR + analyse fiscale Karine.

Combine 2 niveaux :
  1. /api/analyze-invoice (Sonnet multimodal) — extraction des champs OCR
  2. Karine system prompt fiscal — confirme/corrige + ajoute note fiscale
"""
from __future__ import annotations

import base64
import json
from typing import Dict, Any, Optional

import anthropic

from .config import (
    ANTHROPIC_API_KEY,
    INVOICE_CAT_TO_BRAIN_CAT,
    MAX_TOKENS_EXTRACTION,
    MODEL_EXTRACTION,
)
from .system_prompts import EXTRACTION_PROMPT


def extract_with_karine(*,
                         pdf_bytes: bytes,
                         media_type: str,
                         email_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extrait + catégorise fiscalement une facture/reçu PDF.

    email_context : {
        "from": str, "subject": str, "body_text": str, "received_at_iso": str,
        "category_triage": str (de triage_email)
    }

    Retourne le dict structuré (cf. EXTRACTION_PROMPT) ou None si échec.
    """
    if not pdf_bytes:
        return None

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    b64 = base64.b64encode(pdf_bytes).decode("ascii")

    is_pdf = media_type == "application/pdf"
    is_image = media_type and media_type.startswith("image/")
    if not (is_pdf or is_image):
        return None

    if is_pdf:
        document_block = {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": b64},
        }
    else:
        document_block = {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": b64},
        }

    user_text = f"""Contexte du courriel :

EXPÉDITEUR : {email_context.get('from', '?')}
SUJET : {email_context.get('subject', '?')}
REÇU LE : {email_context.get('received_at_iso', '?')}
TRIAGE PRÉLIMINAIRE : {email_context.get('category_triage', '?')}

CORPS (extrait) :
{(email_context.get('body_text') or '')[:1500]}

Analyse le document ci-joint et retourne le JSON structuré demandé. \
Applique TON expertise CPA fiscaliste immobilier commercial : choisis la \
catégorie Brain optimale, identifie les enjeux fiscaux (déductibilité, \
capitalisation, 50 % repas, etc.), et propose un lien vers un dossier client \
si pertinent."""

    content_blocks = [document_block, {"type": "text", "text": user_text}]

    try:
        resp = client.messages.create(
            model=MODEL_EXTRACTION,
            max_tokens=MAX_TOKENS_EXTRACTION,
            system=EXTRACTION_PROMPT,
            messages=[{"role": "user", "content": content_blocks}],
            extra_headers={"anthropic-beta": "pdfs-2024-09-25"} if is_pdf else None,
        )
        raw = resp.content[0].text.strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            return None
        data = json.loads(raw[start : end + 1])

        # Validation & coercition légère
        data = _validate_and_coerce(data)
        return data
    except Exception as e:
        return {
            "_error": str(e)[:500],
            "type": "depense",
            "categorie": "autres_depenses",
            "requires_yves_review": True,
            "yves_review_reason": f"Extraction error: {e}"[:200],
            "confidence": 0,
        }


def _validate_and_coerce(data: Dict[str, Any]) -> Dict[str, Any]:
    """Garde-fous pour ne JAMAIS écrire un champ invalide dans Firestore."""
    # type
    t = (data.get("type") or "depense").lower()
    if t not in {"revenu", "depense", "partenaire"}:
        t = "depense"
    data["type"] = t

    # categorie (si Karine a inventé une catégorie hors enum, mapper / fallback)
    cat = (data.get("categorie") or "").lower()
    valid_categories_by_type = {
        "revenu": {"honoraires_montage", "frais_admin", "interets", "autres_revenus"},
        "depense": {"salaire", "loyer", "comptable", "marketing", "materiel",
                    "autres_depenses"},
        "partenaire": {"paiement_partenaire"},
    }
    if cat not in valid_categories_by_type[t]:
        # tenter mapping via INVOICE_CAT_TO_BRAIN_CAT
        cat = INVOICE_CAT_TO_BRAIN_CAT.get(cat, "")
        if cat not in valid_categories_by_type[t]:
            # fallback safe
            if t == "revenu":
                cat = "autres_revenus"
            elif t == "partenaire":
                cat = "paiement_partenaire"
            else:
                cat = "autres_depenses"
    data["categorie"] = cat

    # montants → float
    for k in ("montant_ht", "tps", "tvq", "montant_total"):
        v = data.get(k)
        try:
            data[k] = float(v) if v is not None else 0.0
        except (ValueError, TypeError):
            data[k] = 0.0

    # confidence
    try:
        c = int(data.get("confidence", 0))
        data["confidence"] = max(0, min(100, c))
    except (ValueError, TypeError):
        data["confidence"] = 0

    # devise
    if not data.get("devise"):
        data["devise"] = "CAD"

    # requires_yves_review : forcer True si confidence < 50
    if data["confidence"] < 50:
        data["requires_yves_review"] = True

    return data
