"""Lookup rapide : cet email est-il une cible outreach active ?

Construit un index en mémoire (cache 10 min) à partir des 4 collections
Firestore (capitalTargets / promoteurTargets / brokers / advisorTargets)
pour permettre à Maestro de cross-checker l'expéditeur AVANT de router
vers `ignore_no_reply`.

Règle verrouillée 26 mai 2026 PM :
« Tout email arrivant d'une cible outreach active DOIT être routé à
Béatrice/Sophie/Camille pour réponse courtoise. JAMAIS classer
`ignore_no_reply` ni skip, même si contenu = boilerplate institutionnel. »

Usage typique (depuis Maestro orchestrator) :

    from agents.shared.outreach_targets_lookup import lookup_outreach_target

    hit = lookup_outreach_target("info@primequadrant.com")
    if hit:
        # hit = {"collection": "capitalTargets",
        #        "docId": "abc123",
        #        "name": "...",
        #        "organization": "Prime Quadrant",
        #        "lastSentAt": "2026-05-25T..."}
        # → forcer route vers Béatrice/Sophie/Camille
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from agents.shared.firestore_client import db

# Cache mémoire singleton
_CACHE: Dict[str, Any] = {
    "index": None,        # dict[email_lower] -> match metadata
    "built_at": 0.0,
    "ttl_seconds": 600,   # 10 min
}

COLLECTIONS = [
    "capitalTargets",
    "promoteurTargets",
    "brokers",
    "advisorTargets",
]


def _resolve_email(d: Dict[str, Any]) -> str:
    e = d.get("email")
    if e and isinstance(e, str) and "@" in e:
        return e.strip().lower()
    for sub in ("contactInfo", "publicContact"):
        v = d.get(sub)
        if isinstance(v, dict):
            e = v.get("email")
            if e and isinstance(e, str) and "@" in e:
                return e.strip().lower()
    return ""


def _is_active_target(d: Dict[str, Any]) -> bool:
    """Cible considérée active si elle a été sollicitée OU est en queue.

    Inclut volontairement les `skipOutreach=true` car même une cible
    skip peut envoyer une réponse à laquelle il faut répondre poliment
    (ex: un courtier blacklisté qui écrit pour autre chose).
    """
    status = (d.get("status") or "").lower()
    if status in {"sent", "queued", "pending", "drafted", "scheduled",
                  "approved", "active_partner"}:
        return True
    if d.get("sentAt") or d.get("lastSentAt"):
        return True
    if d.get("skipOutreach") is True:
        return True
    return False


def _iso(v: Any) -> str:
    if not v:
        return ""
    if isinstance(v, str):
        return v[:25]
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()[:25]
        except Exception:
            return ""
    return str(v)[:25]


def _build_index() -> Dict[str, Dict[str, Any]]:
    """Scanne les 4 collections et bâtit dict[email] -> metadata."""
    index: Dict[str, Dict[str, Any]] = {}
    for col in COLLECTIONS:
        try:
            for snap in db().collection(col).stream():
                d = snap.to_dict() or {}
                if not _is_active_target(d):
                    continue
                em = _resolve_email(d)
                if not em:
                    continue
                entry = {
                    "collection": col,
                    "docId": snap.id,
                    "name": (d.get("name") or d.get("contactName")
                             or "").strip(),
                    "organization": (d.get("organization") or d.get("firmName")
                                     or d.get("entityName") or "").strip(),
                    "status": d.get("status") or "",
                    "lastSentAt": _iso(d.get("sentAt") or d.get("lastSentAt")),
                    "skipOutreach": bool(d.get("skipOutreach")),
                }
                # Si l'email existe déjà, garde le plus récent
                prev = index.get(em)
                if prev is None or entry["lastSentAt"] > prev["lastSentAt"]:
                    index[em] = entry
        except Exception:
            # Une collection en erreur ne doit pas bloquer les autres
            continue
    return index


def _get_index() -> Dict[str, Dict[str, Any]]:
    now = time.time()
    if (_CACHE["index"] is None
            or (now - _CACHE["built_at"]) > _CACHE["ttl_seconds"]):
        _CACHE["index"] = _build_index()
        _CACHE["built_at"] = now
    return _CACHE["index"]


def lookup_outreach_target(email: Optional[str]) -> Optional[Dict[str, Any]]:
    """Retourne metadata si l'email est une cible outreach active, sinon None."""
    if not email:
        return None
    em = email.strip().lower()
    if "@" not in em:
        return None
    return _get_index().get(em)


def invalidate_cache() -> None:
    """Force rebuild au prochain lookup (utile après bulk patch Firestore)."""
    _CACHE["index"] = None
    _CACHE["built_at"] = 0.0


def cache_stats() -> Dict[str, Any]:
    idx = _CACHE.get("index")
    return {
        "built": idx is not None,
        "size": len(idx) if idx else 0,
        "age_seconds": (time.time() - _CACHE["built_at"]) if idx else None,
        "ttl_seconds": _CACHE["ttl_seconds"],
    }


if __name__ == "__main__":
    # Smoke test CLI
    import sys
    idx = _get_index()
    print(f"Index bâti : {len(idx)} cibles outreach actives")
    print(f"Stats: {cache_stats()}")
    if len(sys.argv) > 1:
        for e in sys.argv[1:]:
            hit = lookup_outreach_target(e)
            if hit:
                print(f"✅ {e} → {hit['collection']}/{hit['docId']} "
                      f"({hit['organization']} - {hit['name']})")
            else:
                print(f"❌ {e} → pas trouvé dans outreach targets")
