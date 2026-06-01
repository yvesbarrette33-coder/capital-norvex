"""Orchestrateur Norvex Diligence™ — coordonne les 5 searchers et synthèse."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import anthropic

from . import audit as diligence_audit
from .config import (
    ANTHROPIC_API_KEY,
    MAX_TOKENS_SYNTHESIS,
    MODEL_SYNTHESIS,
    VERDICT_GRAY,
    VERDICT_GREEN,
    VERDICT_RED,
    VERDICT_YELLOW,
)
from .searchers import amf as amf_searcher
from .searchers import oaciq as oaciq_searcher
from .searchers import rbq as rbq_searcher
from .searchers import req as req_searcher
from .searchers import rfq as rfq_searcher
from .system_prompts import SYNTHESIS_PROMPT


def _worst_verdict(verdicts: List[str]) -> str:
    """Combine plusieurs verdicts : pire l'emporte (red > yellow > green > gray)."""
    rank = {VERDICT_RED: 3, VERDICT_YELLOW: 2, VERDICT_GREEN: 1, VERDICT_GRAY: 0}
    if not verdicts:
        return VERDICT_GRAY
    return max(verdicts, key=lambda v: rank.get(v, 0))


def run_diligence(
    *,
    dossier_id: str,
    # REQ
    emprunteur_neq: Optional[str] = None,
    emprunteur_nom: Optional[str] = None,
    # RBQ
    entrepreneur_licence_rbq: Optional[str] = None,
    entrepreneur_nom: Optional[str] = None,
    type_projet: Optional[str] = None,
    # OACIQ
    courtier_immo_nom: Optional[str] = None,
    courtier_immo_permis: Optional[str] = None,
    # AMF
    courtier_hypo_nom: Optional[str] = None,
    courtier_hypo_inscription: Optional[str] = None,
    # RFQ
    rfq_pdf_bytes: Optional[bytes] = None,
    rfq_loan_amount: Optional[float] = None,
    rfq_property_value: Optional[float] = None,
    rfq_property_address: Optional[str] = None,
) -> Dict[str, Any]:
    """Lance tous les searchers applicables et produit la synthèse globale.

    Tous les paramètres sont optionnels. L'orchestrateur exécute uniquement
    les searchers pour lesquels les paramètres sont fournis.
    """
    results: Dict[str, Any] = {
        "dossierId": dossier_id,
        "searchers": {},
        "verdict_global": VERDICT_GRAY,
        "synthese": "",
    }

    diligence_audit.log("diligence_started", target_id=dossier_id,
                         details={"has_neq": bool(emprunteur_neq),
                                  "has_rbq": bool(entrepreneur_licence_rbq or entrepreneur_nom),
                                  "has_oaciq": bool(courtier_immo_nom or courtier_immo_permis),
                                  "has_amf": bool(courtier_hypo_nom or courtier_hypo_inscription),
                                  "has_rfq": bool(rfq_pdf_bytes)})

    # ── REQ : entreprise emprunteuse ────────────────────────────────
    if emprunteur_neq:
        results["searchers"]["req"] = req_searcher.search_by_neq(emprunteur_neq)
    elif emprunteur_nom:
        results["searchers"]["req"] = req_searcher.search_by_name(emprunteur_nom)

    # ── RBQ : entrepreneur (si construction) ────────────────────────
    if entrepreneur_licence_rbq or entrepreneur_nom:
        results["searchers"]["rbq"] = rbq_searcher.search_licence(
            numero_licence=entrepreneur_licence_rbq or "",
            nom_entreprise=entrepreneur_nom or "",
            type_projet=type_projet or "",
        )

    # ── OACIQ : courtier immobilier ─────────────────────────────────
    if courtier_immo_nom or courtier_immo_permis:
        results["searchers"]["oaciq"] = oaciq_searcher.search_courtier(
            nom=courtier_immo_nom or "",
            numero_permis=courtier_immo_permis or "",
        )

    # ── AMF : courtier hypothécaire ─────────────────────────────────
    if courtier_hypo_nom or courtier_hypo_inscription:
        results["searchers"]["amf"] = amf_searcher.search_amf(
            nom=courtier_hypo_nom or "",
            numero_inscription=courtier_hypo_inscription or "",
        )

    # ── RFQ : analyse PDF index ────────────────────────────────────
    if rfq_pdf_bytes:
        results["searchers"]["rfq"] = rfq_searcher.analyze_rfq_pdf(
            pdf_bytes=rfq_pdf_bytes,
            loan_amount_requested=rfq_loan_amount,
            property_estimated_value=rfq_property_value,
            borrower_name=emprunteur_nom,
            property_address=rfq_property_address,
        )

    # ── Synthèse Opus 4.6 ───────────────────────────────────────────
    if results["searchers"]:
        synthesis = _synthesize(results["searchers"])
        results.update(synthesis)
        results["verdict_global"] = synthesis.get("verdict_global", VERDICT_GRAY)
    else:
        results["synthese"] = "Aucune source disponible — diligence non exécutée."

    # ── Persistence ─────────────────────────────────────────────────
    diligence_audit.store_report(dossier_id=dossier_id, report=results)
    diligence_audit.update_dossier_with_verdict(
        dossier_id=dossier_id,
        verdict=results["verdict_global"],
        summary=results.get("synthese", "")[:300],
    )
    diligence_audit.log("diligence_completed", target_id=dossier_id,
                        details={"verdict_global": results["verdict_global"]})

    return results


def _synthesize(searcher_results: Dict[str, Any]) -> Dict[str, Any]:
    """Combine les résultats des searchers via Opus 4.6."""
    # Calcul rapide des verdicts
    verdicts = [r.get("verdict", VERDICT_GRAY) for r in searcher_results.values()]
    worst = _worst_verdict(verdicts)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    user_msg = f"""Résultats de chaque searcher (en JSON) :

{json.dumps(searcher_results, indent=2, ensure_ascii=False, default=str)}

Verdicts individuels : {verdicts}
Pire verdict (calcul mécanique) : {worst}

Produis la synthèse globale demandée."""

    try:
        resp = client.messages.create(
            model=MODEL_SYNTHESIS,
            max_tokens=MAX_TOKENS_SYNTHESIS,
            system=SYNTHESIS_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = resp.content[0].text.strip()
        start = raw.find("{"); end = raw.rfind("}")
        if start == -1 or end == -1:
            return {"verdict_global": worst,
                    "synthese": "Synthèse non parsable. Pire verdict mécanique : "
                                + worst}
        data = json.loads(raw[start : end + 1])
        # Force le pire verdict si Claude est trop optimiste
        if data.get("verdict_global") not in {VERDICT_GREEN, VERDICT_YELLOW, VERDICT_RED}:
            data["verdict_global"] = worst
        return data
    except Exception as e:
        return {
            "verdict_global": worst,
            "synthese": f"Synthèse échec : {e}. Pire verdict mécanique : {worst}",
        }
