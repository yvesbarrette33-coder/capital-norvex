"""Searcher RFQ — Registre foncier du Québec.

V1 : analyse hybride. Yves télécharge l'index manuellement depuis le RFQ
(via son compte clicSÉQUR Entreprise) et l'uploade. L'agent analyse le PDF
avec Claude Opus 4.6 multimodal — niveau avocat senior en droit immobilier.

V2 (futur) : scraping authentifié automatique avec credentials env :
  RFQ_CLICSEQUR_USER, RFQ_CLICSEQUR_PASS, RFQ_API_KEY
"""
from __future__ import annotations

import base64
import json
from typing import Any, Dict, Optional

import anthropic

from ..config import (
    ANTHROPIC_API_KEY,
    MAX_TOKENS_SCRAPE,
    MODEL_SYNTHESIS,  # On utilise Opus pour le RFQ (analyse complexe)
)
from ..system_prompts import RFQ_PROMPT


def analyze_rfq_pdf(pdf_bytes: bytes,
                     loan_amount_requested: Optional[float] = None,
                     property_estimated_value: Optional[float] = None,
                     borrower_name: Optional[str] = None,
                     property_address: Optional[str] = None,
                     ) -> Dict[str, Any]:
    """Analyse un index RFQ uploadé (PDF) avec Opus 4.6 multimodal.

    Yves doit téléverser :
      - L'INDEX d'un lot (page « État du registre foncier »)
      - OU un extrait d'acte spécifique (vente, hypothèque, mainlevée, etc.)

    Le PDF est encodé en base64 et passé en `document` block à Claude.

    Le contexte (montant demandé, valeur immeuble, emprunteur, adresse) aide
    Claude à calculer la marge libre et à vérifier la cohérence avec
    l'emprunteur.
    """
    if not pdf_bytes:
        return _error("PDF RFQ vide")

    b64 = base64.b64encode(pdf_bytes).decode("ascii")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    contexte = []
    if borrower_name:
        contexte.append(f"Emprunteur déclaré : {borrower_name}")
    if property_address:
        contexte.append(f"Adresse de l'immeuble : {property_address}")
    if loan_amount_requested:
        contexte.append(
            f"Montant de prêt demandé à Capital Norvex : "
            f"{loan_amount_requested:,.0f} $"
        )
    if property_estimated_value:
        contexte.append(
            f"Valeur estimée de l'immeuble (Score Norvex / évaluation) : "
            f"{property_estimated_value:,.0f} $"
        )
    contexte_str = "\n".join(contexte) if contexte else "Aucun contexte fourni."

    user_text = f"""Tu reçois ci-dessous un document du Registre foncier du Québec \
(RFQ) en PDF.

Contexte du dossier Capital Norvex :
{contexte_str}

Analyse ce document avec ton expertise d'avocat senior en droit immobilier. \
Identifie tous les éléments pertinents (titres, hypothèques actives/radiées, \
saisies, préavis, servitudes, ordonnances). Calcule la marge libre disponible \
si tu peux, détermine si Capital Norvex serait en 1er rang en cas \
d'engagement, signale tous les drapeaux rouges et jaunes, et produis le \
JSON structuré demandé."""

    content = [
        {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": b64,
            },
        },
        {"type": "text", "text": user_text},
    ]

    try:
        resp = client.messages.create(
            model=MODEL_SYNTHESIS,
            max_tokens=4500,
            system=RFQ_PROMPT,
            messages=[{"role": "user", "content": content}],
            extra_headers={"anthropic-beta": "pdfs-2024-09-25"},
        )
        raw = resp.content[0].text.strip()
        start = raw.find("{"); end = raw.rfind("}")
        if start == -1 or end == -1:
            return _error("RFQ analyse non parsable")
        data = json.loads(raw[start : end + 1])
        data["_source"] = "rfq"
        return data
    except Exception as e:
        return _error(f"RFQ analyse échec : {e}")


def _error(msg: str) -> Dict[str, Any]:
    return {
        "_source": "rfq",
        "verdict": "yellow",
        "drapeaux_jaunes": [msg],
        "drapeaux_rouges": [],
        "analyse_avocat": msg,
        "verdict_explication": msg,
        "recommandation_yves": "Yves doit téléverser un index RFQ valide.",
    }
