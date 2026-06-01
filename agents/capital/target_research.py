"""Agent CAPITAL — recherche profonde sur cibles family offices.

Avant TOUTE recherche: vérification TIER ZERO obligatoire.

Sources prioritaires (à étendre):
- SEDAR+ (déclarations publiques)
- LinkedIn public
- Lesaffaires.com, Globe & Mail, Toronto Star
- Communiqués M&A (IPOs, ventes d'entreprise)

Note: la recherche web réelle nécessite un appel à l'API Claude
(web_search tool) OU un service externe. v1 expose la structure;
le moteur de recherche peut être branché plus tard.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from ..shared import firestore_client as fs
from ..shared.tier_zero_guard import (
    TierZeroBlocked,
    check_before_action,
)

AGENT_NAME = "capital"


def research_target(target_id: str, run_web_search: bool = True) -> Dict[str, Any]:
    """Lance la recherche profonde sur une cible.

    1. Charge la cible depuis capitalTargets
    2. Vérifie TIER ZERO (lève TierZeroBlocked si protégé)
    3. (Optionnel) lance la recherche web via Claude API
    4. Sauvegarde le résultat dans capitalResearch
    5. Met à jour capitalTargets.status → 'ready' si suffisamment de signaux

    Retourne le doc de recherche créé.
    """
    target = fs.get("capitalTargets", target_id)
    if not target:
        raise RuntimeError(f"capitalTargets/{target_id} introuvable")

    target["_agent"] = AGENT_NAME
    target["_target_type"] = "capitalTarget"
    check_before_action(target)  # lève si TIER ZERO

    fs.audit_log(
        agent=AGENT_NAME,
        action="research_start",
        target_type="capitalTarget",
        target_id=target_id,
    )

    research_doc: Dict[str, Any] = {
        "targetId": target_id,
        "researchDate": fs.now_utc(),
        "sources": [],
        "facts": [],
        "thesisHypothesis": target.get("investmentThesis", ""),
        "approachStrategy": target.get("approachAngle", ""),
        "generatedDossier": None,
    }

    if run_web_search:
        try:
            web_findings = _run_claude_web_search(target)
            research_doc["sources"] = web_findings.get("sources", [])
            research_doc["facts"] = web_findings.get("facts", [])
            if web_findings.get("thesisHypothesis"):
                research_doc["thesisHypothesis"] = web_findings["thesisHypothesis"]
            if web_findings.get("approachStrategy"):
                research_doc["approachStrategy"] = web_findings["approachStrategy"]
        except Exception as e:
            fs.audit_log(
                agent=AGENT_NAME,
                action="research_websearch_failed",
                target_type="capitalTarget",
                target_id=target_id,
                result="error",
                details={"error": str(e)},
            )

    research_id = fs.create("capitalResearch", research_doc)

    fs.update(
        "capitalTargets",
        target_id,
        {
            "investmentThesis": research_doc["thesisHypothesis"],
            "approachAngle": research_doc["approachStrategy"],
            "status": "ready" if research_doc["facts"] else target.get("status", "research"),
        },
    )

    fs.audit_log(
        agent=AGENT_NAME,
        action="research_complete",
        target_type="capitalTarget",
        target_id=target_id,
        details={"researchId": research_id, "factsCount": len(research_doc["facts"])},
    )
    return {**research_doc, "id": research_id}


def _run_claude_web_search(target: Dict[str, Any]) -> Dict[str, Any]:
    """Appelle l'API Claude avec l'outil web_search pour enrichir une cible.

    Retourne {sources, facts, thesisHypothesis, approachStrategy}.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY manquant")

    try:
        import anthropic
    except ImportError:
        raise RuntimeError("Librairie 'anthropic' non installée — pip install anthropic")

    client = anthropic.Anthropic(api_key=api_key)

    name = target.get("name", "")
    org = target.get("organization", "")
    region = target.get("region", "")
    language = target.get("language", "FR")

    sys_prompt = (
        "Tu es l'agent CAPITAL de Capital Norvex Inc. Ton rôle: produire une "
        "recherche structurée sur un family office canadien, en t'appuyant "
        "uniquement sur des sources publiques (SEDAR+, communiqués, médias "
        "reconnus comme Lesaffaires, Globe & Mail, Toronto Star, LinkedIn "
        "public). Ne jamais inventer de données. Si une donnée n'est pas "
        "trouvée, le dire explicitement. Réponse en JSON strict."
    )
    user_msg = (
        f"Cible:\n- Nom: {name}\n- Organisation: {org}\n- Région: {region}\n"
        f"- Langue: {language}\n\n"
        "Cherche des signaux récents (24 mois): vente d'entreprise, IPO, "
        "succession, déclarations publiques d'investissement, philanthropie. "
        "Réponds en JSON: {sources:[{url,type,snippet,dateAccessed}], "
        "facts:[{category,fact,confidence}], thesisHypothesis, approachStrategy}."
    )

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=sys_prompt,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": user_msg}],
    )

    text = ""
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            text += block.text

    import json as _json
    try:
        start = text.find("{")
        end = text.rfind("}")
        return _json.loads(text[start : end + 1])
    except Exception:
        return {
            "sources": [],
            "facts": [],
            "thesisHypothesis": text[:1000],
            "approachStrategy": "",
        }


def list_ready_targets(region: Optional[str] = None) -> List[Dict[str, Any]]:
    """Liste les cibles prêtes pour une approche."""
    filters: List[tuple] = [("status", "==", "ready")]
    if region:
        filters.append(("region", "==", region))
    return fs.query("capitalTargets", filters=filters, limit=50)
