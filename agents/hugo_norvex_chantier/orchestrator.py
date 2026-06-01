"""Hugo — Orchestrateur principal.

Workflow :
1. analyze_dossier(dossier_id, intel_documents=None)
   → appelle en parallèle les 3 endpoints orchestrateurs
   → collecte les 3 rapports
2. synthesize(rapports)
   → Claude Opus produit le verdict business consolidé
3. push_to_brain(rapport_consolidé)
   → écrit dans Norvex Brain (audit + alertes + factures)
4. notify_yves(rapport_consolidé)
   → envoie email résumé à Yves si action requise

CLI :
    python -m agents.hugo_norvex_chantier --dossier <dossier_id>
    python -m agents.hugo_norvex_chantier --dossier <id> --skip-brain --skip-notify
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from .config import (
    AGENT_NAME,
    DISBURSEMENT_BLOCK_VERDICTS,
    ENDPOINT_BRAIN_PUSH,
    ENDPOINT_COST,
    ENDPOINT_INTEL,
    ENDPOINT_TRACK,
    ESCALATION_TRIGGERS,
    INTERNAL_SECRET,
    MODEL_SYNTHESIS,
    SITE_URL,
    SYNTHESIS_MAX_TOKENS,
    YVES_EMAIL,
)
from .system_prompts import SYNTHESIS_SYSTEM


# ─── Appels endpoints orchestrateurs ─────────────────────────────────────


def _call_endpoint(name: str, url: str, body: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    """Appel HTTP générique avec auth INTERNAL_SECRET."""
    if not INTERNAL_SECRET:
        return {"error": "INTERNAL_SECRET not set", "module": name}
    try:
        r = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "x-internal-secret": INTERNAL_SECRET,
            },
            json=body,
            timeout=timeout,
        )
        if r.status_code >= 400:
            return {
                "error": f"HTTP {r.status_code}",
                "detail": r.text[:300],
                "module": name,
            }
        return r.json()
    except requests.Timeout:
        return {"error": "Timeout", "module": name, "timeout_seconds": timeout}
    except Exception as e:
        return {"error": str(e), "module": name}


def call_intel(dossier_id: str, documents: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Appelle Norvex Intel orchestrateur. Documents = liste optionnelle de PDFs."""
    body = {"dossierId": dossier_id}
    if documents:
        body["documents"] = documents
    return _call_endpoint("intel", ENDPOINT_INTEL, body, timeout=90)


def call_track(
    dossier_id: str,
    documents: Optional[List[Dict]] = None,
    force_opus_validation: bool = False,
) -> Dict[str, Any]:
    """Appelle Norvex Track orchestrateur. Documents = liste optionnelle (rapports avancement, photos, factures)."""
    body: Dict[str, Any] = {"dossierId": dossier_id}
    if documents:
        body["documents"] = documents
    if force_opus_validation:
        body["force_opus_validation"] = True
    return _call_endpoint("track", ENDPOINT_TRACK, body, timeout=90)


def call_cost(
    dossier_id: str,
    documents: Optional[List[Dict]] = None,
    force_opus_validation: bool = False,
) -> Dict[str, Any]:
    """Appelle Cost Analyzer orchestrateur. Documents = liste optionnelle (factures, devis, soumissions)."""
    body: Dict[str, Any] = {"dossierId": dossier_id}
    if documents:
        body["documents"] = documents
    if force_opus_validation:
        body["force_opus_validation"] = True
    return _call_endpoint("cost", ENDPOINT_COST, body, timeout=90)


def gather_module_reports(
    dossier_id: str,
    intel_documents: Optional[List[Dict]] = None,
    track_documents: Optional[List[Dict]] = None,
    cost_documents: Optional[List[Dict]] = None,
    force_opus_validation: bool = False,
    parallel: bool = True,
) -> Dict[str, Any]:
    """Lance les 3 appels orchestrateurs (parallèle par défaut)."""
    if parallel:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            f_intel = pool.submit(call_intel, dossier_id, intel_documents)
            f_track = pool.submit(call_track, dossier_id, track_documents, force_opus_validation)
            f_cost = pool.submit(call_cost, dossier_id, cost_documents, force_opus_validation)
            return {
                "intel": f_intel.result(),
                "track": f_track.result(),
                "cost": f_cost.result(),
            }
    return {
        "intel": call_intel(dossier_id, intel_documents),
        "track": call_track(dossier_id, track_documents, force_opus_validation),
        "cost": call_cost(dossier_id, cost_documents, force_opus_validation),
    }


# ─── Synthèse via Claude Opus ────────────────────────────────────────────


def synthesize(dossier_id: str, reports: Dict[str, Any]) -> Dict[str, Any]:
    """Appelle Claude Opus pour produire le verdict business consolidé."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    user_message = (
        f"DOSSIER ID : {dossier_id}\n\n"
        f"═══════════════════════════════════════════════════════════════════\n"
        f"RAPPORT NORVEX INTEL (évaluation immobilière)\n"
        f"═══════════════════════════════════════════════════════════════════\n"
        f"{json.dumps(reports.get('intel', {}), indent=2, ensure_ascii=False)}\n\n"
        f"═══════════════════════════════════════════════════════════════════\n"
        f"RAPPORT NORVEX TRACK (suivi chantier)\n"
        f"═══════════════════════════════════════════════════════════════════\n"
        f"{json.dumps(reports.get('track', {}), indent=2, ensure_ascii=False)}\n\n"
        f"═══════════════════════════════════════════════════════════════════\n"
        f"RAPPORT NORVEX COST ANALYZER (ventilation coûts)\n"
        f"═══════════════════════════════════════════════════════════════════\n"
        f"{json.dumps(reports.get('cost', {}), indent=2, ensure_ascii=False)}\n\n"
        f"Synthétise les 3 rapports en UN verdict business consolidé pour Capital Norvex.\n"
        f"Format de sortie : JSON strict selon ton system prompt."
    )

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL_SYNTHESIS,
            "max_tokens": SYNTHESIS_MAX_TOKENS,
            "system": SYNTHESIS_SYSTEM,
            "messages": [{"role": "user", "content": user_message}],
        },
        timeout=120,
    )
    if not r.ok:
        raise RuntimeError(f"Claude synthesis error {r.status_code}: {r.text[:300]}")
    data = r.json()
    text = data["content"][0]["text"].strip()
    # Nettoyer ```json fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0] if "```" in text else text
    # Extraire le premier objet JSON
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Synthèse JSON invalide : {e}\nText (300c): {text[:300]}"
        )


# ─── Push vers Brain ─────────────────────────────────────────────────────


def push_to_brain(dossier_id: str, synthesis: Dict[str, Any], reports: Dict[str, Any]) -> Dict[str, Any]:
    """Pousse le rapport Hugo dans Norvex Brain (audit + alertes)."""
    payload = {
        "dossierId": dossier_id,
        "agent": AGENT_NAME,
        "verdictGlobal": synthesis.get("verdict_global"),
        "actionRecommandee": synthesis.get("action_recommandee"),
        "synthesis": synthesis.get("synthesis"),
        "modulesSummary": synthesis.get("modules_summary", {}),
        "alertesConsolidees": synthesis.get("alertes_consolidees", []),
        "deboursementAutorise": synthesis.get("deboursement_autorise"),
        "valeurPreteeRecommandee": synthesis.get("valeur_pretee_recommandee"),
        "confianceGlobale": synthesis.get("confiance_globale"),
        "rawReports": {
            "intel_status": "ok" if "evaluation" in reports.get("intel", {}) else "error",
            "track_status": "ok" if "verdict_global" in reports.get("track", {}) else "error",
            "cost_status": "ok" if "verdict_global" in reports.get("cost", {}) else "error",
        },
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    return _call_endpoint("brain_push", ENDPOINT_BRAIN_PUSH, payload, timeout=30)


# ─── Workflow complet ────────────────────────────────────────────────────


def analyze_dossier(
    dossier_id: str,
    intel_documents: Optional[List[Dict]] = None,
    track_documents: Optional[List[Dict]] = None,
    cost_documents: Optional[List[Dict]] = None,
    force_opus_validation: bool = False,
    push_brain: bool = True,
) -> Dict[str, Any]:
    """Workflow Hugo complet pour un dossier.

    Args:
        dossier_id: ID Firestore du dossier (collection `dossiers`).
        intel_documents: PDFs optionnels pour Intel (titres, baux, états fin.).
        track_documents: PDFs/photos optionnels pour Track (rapports, photos chantier, factures).
        cost_documents: PDFs optionnels pour Cost (factures, devis, soumissions).
        force_opus_validation: Force la validation Opus 4.6 sur Track + Cost
            même si verdict initial pas Critique.
        push_brain: Si True, pousse les résultats dans Norvex Brain.

    Returns:
        {
            "dossier_id": str,
            "synthesis": {...},
            "raw_reports": {intel, track, cost},
            "brain_push_status": "ok" | "error" | "skipped",
            "should_escalate_yves": bool,
            "should_block_disbursement": bool,
            "completed_at": ISO timestamp,
        }
    """
    print(f"🤖 Hugo NORVEX CHANTIER™ — analyse dossier {dossier_id}")
    print(f"   Étape 1/3 : appels parallèles aux 3 modules construction…")

    reports = gather_module_reports(
        dossier_id,
        intel_documents=intel_documents,
        track_documents=track_documents,
        cost_documents=cost_documents,
        force_opus_validation=force_opus_validation,
    )

    # Diagnostic rapide
    for mod, rep in reports.items():
        if rep.get("error"):
            print(f"   ⚠️  Module {mod} : ERREUR — {rep['error']}")
        else:
            print(f"   ✅ Module {mod} : OK")

    print(f"   Étape 2/3 : synthèse Claude Opus 4.6…")
    try:
        synthesis = synthesize(dossier_id, reports)
    except Exception as e:
        return {
            "dossier_id": dossier_id,
            "error": f"Synthèse échouée : {e}",
            "raw_reports": reports,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    verdict = synthesis.get("verdict_global", "UNKNOWN")
    action = synthesis.get("action_recommandee", "UNKNOWN")
    print(f"   ✅ Verdict global : {verdict} | Action : {action}")

    should_escalate = any(
        synthesis.get("modules_summary", {}).get(m, {}).get("verdict") in ESCALATION_TRIGGERS
        for m in ("intel", "track", "cost")
    ) or verdict in ESCALATION_TRIGGERS
    should_block = verdict in DISBURSEMENT_BLOCK_VERDICTS

    brain_status = "skipped"
    if push_brain:
        print(f"   Étape 3/3 : push vers Norvex Brain…")
        brain_resp = push_to_brain(dossier_id, synthesis, reports)
        if brain_resp.get("error"):
            print(f"   ⚠️  Brain push erreur : {brain_resp['error']}")
            brain_status = f"error: {brain_resp['error']}"
        else:
            print(f"   ✅ Brain push OK (reportId: {brain_resp.get('reportId', 'N/A')})")
            brain_status = "ok"

    return {
        "dossier_id": dossier_id,
        "synthesis": synthesis,
        "raw_reports": reports,
        "brain_push_status": brain_status,
        "should_escalate_yves": should_escalate,
        "should_block_disbursement": should_block,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


# ─── CLI ─────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hugo NORVEX CHANTIER™ — orchestrateur modules construction"
    )
    parser.add_argument(
        "--dossier", required=True, help="ID Firestore du dossier à analyser"
    )
    parser.add_argument(
        "--skip-brain", action="store_true", help="N'envoie PAS le push Brain"
    )
    parser.add_argument(
        "--force-opus",
        action="store_true",
        help="Force la validation Opus 4.6 sur Track + Cost même si verdict pas Critique",
    )
    parser.add_argument(
        "--output",
        choices=["json", "summary"],
        default="summary",
        help="Format de sortie",
    )
    args = parser.parse_args()

    if not INTERNAL_SECRET:
        print("❌ INTERNAL_SECRET non défini dans l'environnement.", file=sys.stderr)
        return 1

    result = analyze_dossier(
        dossier_id=args.dossier,
        force_opus_validation=args.force_opus,
        push_brain=not args.skip_brain,
    )

    if args.output == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        synth = result.get("synthesis", {})
        print()
        print(f"═══ Hugo NORVEX CHANTIER™ — Rapport dossier {args.dossier} ═══")
        print()
        print(f"Verdict global         : {synth.get('verdict_global', 'N/D')}")
        print(f"Action recommandée     : {synth.get('action_recommandee', 'N/D')}")
        print(f"Confiance              : {synth.get('confiance_globale', 'N/D')}")
        print(f"Déboursement autorisé  : {synth.get('deboursement_autorise', 'N/D')}")
        print(f"Valeur prêtée recom.   : {synth.get('valeur_pretee_recommandee', 'N/D')}")
        print()
        print("Synthèse :")
        print(f"  {synth.get('synthesis', '(aucune)')}")
        print()
        print("Recommandation Yves :")
        print(f"  {synth.get('recommandation_yves', '(aucune)')}")
        print()
        print(f"Brain push : {result.get('brain_push_status')}")
        print(f"Escalade Yves : {result.get('should_escalate_yves')}")
        print(f"Bloquer déboursé : {result.get('should_block_disbursement')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
