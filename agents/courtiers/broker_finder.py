"""Agent COURTIERS — identification de nouveaux courtiers commerciaux.

Sources:
- CMBA-Québec et CMBA-ON (Canadian Mortgage Brokers Association)
- LinkedIn courtiers commerciaux
- Filtres: tickets historiques 2,5M$+, spécialité construction/terrain/commercial

v1 expose la structure et utilise Claude API web search.
Le moteur peut être branché plus tard. Aucune donnée fictive injectée.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from ..shared import firestore_client as fs
from ..shared.tier_zero_guard import TierZeroBlocked, check_before_action

AGENT_NAME = "courtiers"


def identify_brokers(
    region: str = "QC",
    specialty: Optional[str] = None,
    max_count: int = 10,
    run_web_search: bool = True,
) -> List[Dict[str, Any]]:
    """Identifie de nouveaux courtiers commerciaux et les crée dans `brokers`.

    Retourne la liste des brokers créés.
    """
    candidates: List[Dict[str, Any]] = []
    if run_web_search:
        try:
            candidates = _claude_search_brokers(region=region, specialty=specialty, max_count=max_count)
        except Exception as e:
            fs.audit_log(
                agent=AGENT_NAME,
                action="identify_brokers_search_failed",
                result="error",
                details={"error": str(e)},
            )
            candidates = []

    created: List[Dict[str, Any]] = []
    for c in candidates:
        try:
            check_before_action({**c, "_agent": AGENT_NAME, "_target_type": "broker"})
        except TierZeroBlocked as e:
            print(f"🚫 broker bloqué TIER ZERO: {e.matched_name}")
            continue

        c.setdefault("relationshipStatus", "cold")
        c.setdefault("dealsReceived", 0)
        c.setdefault("dealsClosed", 0)
        c.setdefault("region", region)

        broker_id = fs.create("brokers", c)
        c["id"] = broker_id
        created.append(c)

    fs.audit_log(
        agent=AGENT_NAME,
        action="identify_brokers",
        details={"region": region, "specialty": specialty, "created": len(created)},
    )
    return created


def _claude_search_brokers(
    region: str,
    specialty: Optional[str],
    max_count: int,
) -> List[Dict[str, Any]]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY manquant")
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic non installé")

    client = anthropic.Anthropic(api_key=api_key)
    spec_str = specialty or "multilogement, construction ou commercial"
    user_msg = (
        f"Identifie {max_count} courtiers commerciaux actifs en {region} "
        f"(Canada) spécialisés en {spec_str}. Critères: tickets historiques "
        f"d'au moins 2,5M$ CAD. Sources: CMBA, LinkedIn public. Réponds en "
        f"JSON: [{{name, firmName, licenseNumber, region, specialty:[], "
        f"typicalDealSize:{{min,max}}, preferredChannel, notes}}]. Ne pas "
        f"inventer de licence; mettre null si inconnue."
    )
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": user_msg}],
    )
    text = ""
    for b in msg.content:
        if getattr(b, "type", None) == "text":
            text += b.text

    import json as _json

    try:
        start = text.find("[")
        end = text.rfind("]")
        return _json.loads(text[start : end + 1])
    except Exception:
        return []
