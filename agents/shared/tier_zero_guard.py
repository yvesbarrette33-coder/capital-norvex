"""TIER ZERO Guard — Règle d'or R-TIER-ZERO.

Personnes invisibles aux 3 agents (Capital, Courtiers, Promoteurs).
Aucune communication, aucune cartographie, aucune recherche, aucune mention.

Si un agent tente de toucher quelqu'un de cette liste:
  → STOP immédiat
  → Audit log avec result='blocked_tier_zero'
  → Notification Yves

API:
    is_protected(name_or_email_or_org) -> bool
    check_before_action(target_data)   -> raises TierZeroBlocked si protégé
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

_CACHE: Dict[str, Any] = {"data": None, "loaded_at": 0}
_CACHE_TTL_SEC = 3600  # 1 heure

# Mots-vides à exclure du matching par "last_name" — ce sont des suffixes
# d'entreprises trop génériques qui créeraient des false positives
# (ex: "Saputo Inc." matcherait "Metro Inc.", "Jolina Capital" matcherait
# "Walter Capital Partners", etc.)
_STOP_WORDS = {
    "inc", "inc.", "ltd", "ltd.", "llc", "llp", "lp", "lp.",
    "corp", "corp.", "corporation", "co", "co.", "company",
    "group", "groupe", "capital", "capitaux", "capitals",
    "family", "famille", "families", "familles",
    "holding", "holdings", "holdco",
    "partners", "partenaires", "partner",
    "ventures", "venture",
    "fund", "funds", "fonds",
    "trust", "trusts",
    "enterprises", "enterprise",
    "investments", "investment", "placements", "placement",
    "foundation", "fondation",
    "office", "offices", "bureau",
    "limited", "limitee", "ltee",
    "international", "global", "worldwide",
    "industries", "industrie",
    "advisors", "advisor", "conseil", "conseils",
    "services", "service",
    "asset", "assets",
    "management", "gestion",
    "real", "estate",
    # Géographie — termes trop génériques
    "canada", "canadien", "canadienne", "canadiens", "canadiennes",
    "quebec", "quebecois", "quebecoise",
    "ontario", "alberta", "manitoba", "saskatchewan",
    "montreal", "toronto", "ottawa", "calgary", "vancouver", "edmonton",
    "america", "american", "americain", "americaine",
    "north", "south", "east", "west", "nord", "sud", "est", "ouest",
    "city", "ville", "town",
    "street", "rue", "avenue",
    "republic",
}


class TierZeroBlocked(Exception):
    """Levée quand un agent essaie de toucher une personne TIER ZERO."""

    def __init__(self, matched_name: str, target: Dict[str, Any]):
        self.matched_name = matched_name
        self.target = target
        super().__init__(
            f"🚫 TIER ZERO BLOCK — Tentative de toucher '{matched_name}'. "
            f"Cible: {target}"
        )


def _tier_zero_path() -> str:
    return os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "tier_zero.json"
    )


def _load() -> Dict[str, Any]:
    """Charge data/tier_zero.json avec cache 1h."""
    now = time.time()
    if _CACHE["data"] and (now - _CACHE["loaded_at"]) < _CACHE_TTL_SEC:
        return _CACHE["data"]
    path = _tier_zero_path()
    if not os.path.exists(path):
        raise RuntimeError(f"tier_zero.json introuvable à {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    _CACHE["data"] = data
    _CACHE["loaded_at"] = now
    return data


def _normalize(s: str) -> str:
    """Normalise pour comparaison: lowercase, accents retirés, espaces simples."""
    if not s:
        return ""
    import unicodedata

    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s.strip().lower())
    return s


def list_protected() -> List[Dict[str, Any]]:
    """Retourne la liste complète des personnes TIER ZERO."""
    return _load().get("protected_individuals", [])


def is_protected(value: Optional[str]) -> Optional[str]:
    """Vérifie si la valeur correspond à une personne TIER ZERO.
    Retourne le nom matché si oui, None sinon.

    Matche sur:
    - Substring exacte (dans un sens ou l'autre)
    - Nom de famille (dernier token ≥ 4 caractères) présent dans la
      valeur testée (ex: "Robitaille" dans "Famille Robitaille Holdings").
    """
    if not value:
        return None
    needle = _normalize(value)
    if not needle:
        return None
    needle_tokens = set(needle.split())
    for entry in list_protected():
        candidates = (
            [entry.get("name", "")]
            + entry.get("aliases", [])
            + entry.get("known_emails", [])
            + entry.get("known_organizations", [])
        )
        for c in candidates:
            cn = _normalize(c)
            if not cn:
                continue
            if cn in needle or needle in cn:
                return entry["name"]
            # Token-based "last name" match — filtre les mots-vides
            # génériques (Inc., Capital, Group, etc.) pour éviter les
            # false positives.
            tokens = [
                t for t in cn.split()
                if len(t) >= 4
                and t not in _STOP_WORDS
                and not t.isdigit()  # exclure tokens purement numériques
            ]
            if tokens:
                last_name = tokens[-1]
                # Word boundary match : on exige le token comme MOT
                # complet dans la cible, pas juste comme sous-chaîne.
                if last_name in needle_tokens:
                    return entry["name"]
    return None


def check_before_action(target: Dict[str, Any]) -> None:
    """Vérifie les champs sensibles d'une cible avant toute action.

    Lève TierZeroBlocked si match. Sinon retourne None silencieusement.
    """
    fields_to_check = [
        target.get("name"),
        target.get("organization"),
        target.get("companyName"),
        target.get("firmName"),
        (target.get("contactInfo") or {}).get("email"),
        (target.get("contactInfo") or {}).get("linkedin"),
    ]
    introducers = target.get("introducers") or []
    for intro in introducers:
        if isinstance(intro, dict):
            fields_to_check.append(intro.get("name"))
        elif isinstance(intro, str):
            fields_to_check.append(intro)

    for field in fields_to_check:
        matched = is_protected(field)
        if matched:
            # Log audit (import différé pour éviter cycle)
            try:
                from .firestore_client import audit_log

                audit_log(
                    agent=target.get("_agent", "unknown"),
                    action="tier_zero_block",
                    target_type=target.get("_target_type"),
                    target_id=target.get("id"),
                    result="blocked_tier_zero",
                    details={"matched_name": matched, "field_value": field},
                )
            except Exception:
                pass  # ne jamais empêcher le block à cause d'un log
            raise TierZeroBlocked(matched, target)


def invalidate_cache() -> None:
    """Force le rechargement au prochain appel."""
    _CACHE["data"] = None
    _CACHE["loaded_at"] = 0
