"""Émile — module enrichment : pull data Firestore + SendGrid + Web."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from agents.shared import firestore_client as fc


def fetch_target(collection: str, doc_id: str) -> Dict[str, Any]:
    """Pull document Firestore complet."""
    doc = fc.get(collection, doc_id)
    if not doc:
        raise ValueError(f"{collection}/{doc_id} introuvable Firestore")
    doc["_collection"] = collection
    doc["_doc_id"] = doc_id
    return doc


def fetch_sendgrid_engagement(email: str) -> Dict[str, Any]:
    """Pull stats engagement SendGrid pour un email donné (7 derniers jours)."""
    api_key = _load_sendgrid_key()
    if not api_key:
        return {"opens": 0, "clicks": 0, "messages": 0, "subjects": [], "error": "no_api_key"}

    import requests

    headers = {"Authorization": f"Bearer {api_key}"}
    query = (
        f'to_email = "{email}" AND '
        f'last_event_time > TIMESTAMP "2026-04-30T00:00:00Z"'
    )
    try:
        r = requests.get(
            "https://api.sendgrid.com/v3/messages",
            headers=headers,
            params={"query": query, "limit": 50},
            timeout=15,
        )
        msgs = r.json().get("messages", [])
        total_opens = sum(m.get("opens_count", 0) or 0 for m in msgs)
        total_clicks = sum(m.get("clicks_count", 0) or 0 for m in msgs)
        subjects = list({m.get("subject") for m in msgs if m.get("subject")})
        return {
            "opens": total_opens,
            "clicks": total_clicks,
            "messages": len(msgs),
            "subjects": subjects,
            "last_event": msgs[0].get("last_event_time") if msgs else None,
        }
    except Exception as e:
        return {"opens": 0, "clicks": 0, "messages": 0, "subjects": [], "error": str(e)}


def fetch_org_engagement(org_email_pattern: str) -> Dict[str, Any]:
    """Pull engagement aggregate pour tous les emails d'un domaine.

    Ex: 'saputo.com' → tous les emails @saputo.com des 7 derniers jours.
    """
    api_key = _load_sendgrid_key()
    if not api_key:
        return {"contacts": []}

    import requests

    headers = {"Authorization": f"Bearer {api_key}"}
    query = (
        f'to_email LIKE "%@{org_email_pattern}" AND '
        f'last_event_time > TIMESTAMP "2026-04-30T00:00:00Z"'
    )
    try:
        r = requests.get(
            "https://api.sendgrid.com/v3/messages",
            headers=headers,
            params={"query": query, "limit": 100},
            timeout=15,
        )
        msgs = r.json().get("messages", [])
        from collections import defaultdict
        agg = defaultdict(lambda: {"opens": 0, "clicks": 0})
        for m in msgs:
            em = m.get("to_email", "")
            agg[em]["opens"] += m.get("opens_count", 0) or 0
            agg[em]["clicks"] += m.get("clicks_count", 0) or 0
        contacts = sorted(
            [{"email": k, **v} for k, v in agg.items()],
            key=lambda x: (x["clicks"], x["opens"]),
            reverse=True,
        )
        return {"contacts": contacts}
    except Exception:
        return {"contacts": []}


def _load_sendgrid_key() -> Optional[str]:
    """Charge SENDGRID_API_KEY depuis env ou ~/.capitalnorvex/.env."""
    key = os.getenv("SENDGRID_API_KEY")
    if key:
        return key
    env_path = os.path.expanduser("~/.capitalnorvex/.env")
    if not os.path.exists(env_path):
        return None
    with open(env_path) as f:
        for line in f:
            if line.startswith("SENDGRID_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def build_engagement_summary(target: Dict[str, Any]) -> Dict[str, Any]:
    """Synthèse d'engagement pour un target.

    Combine email perso + email org (info@) si disponibles.
    """
    pc = target.get("publicContact") or {}
    primary_email = pc.get("email") or target.get("sentTo") or ""
    org = target.get("organization") or ""

    perso_stats = fetch_sendgrid_engagement(primary_email) if primary_email else {}

    # Tente de pull stats org via domaine
    org_stats = {"contacts": []}
    if "@" in primary_email:
        domain = primary_email.split("@", 1)[-1]
        org_stats = fetch_org_engagement(domain)

    return {
        "primary_email": primary_email,
        "org": org,
        "perso": perso_stats,
        "org_contacts": org_stats.get("contacts", []),
        "total_opens": sum(c.get("opens", 0) for c in org_stats.get("contacts", [])),
        "total_clicks": sum(c.get("clicks", 0) for c in org_stats.get("contacts", [])),
    }
