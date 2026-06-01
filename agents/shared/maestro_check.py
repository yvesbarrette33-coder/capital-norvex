"""Helper partagé : vérifie la décision Maestro avant qu'un agent drafte.

Usage typique dans Camille / Sophie / Béatrice / Karine orchestrators :

    from agents.shared.maestro_check import should_skip_per_maestro

    if should_skip_per_maestro(internet_message_id, my_route="to_camille"):
        return {"skipped": "maestro_routed_elsewhere"}

Rétro-compatibilité totale : si Maestro n'a pas encore traité ce Message-ID
(pas d'entrée dans `maestroDispatch`), la fonction retourne False et l'agent
continue comme avant. Pas de blocage.
"""
from __future__ import annotations

from typing import Optional

from agents.shared.firestore_client import db


def get_maestro_route(internet_message_id: Optional[str]) -> Optional[str]:
    """Retourne la route Maestro pour ce Message-ID, ou None si pas dispatché."""
    if not internet_message_id:
        return None
    safe_id = (internet_message_id.replace("/", "_")
               .replace("#", "_")[:200])
    try:
        snap = db().collection("maestroDispatch").document(safe_id).get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        return data.get("route")
    except Exception:
        return None


def should_skip_per_maestro(internet_message_id: Optional[str],
                             my_route: str) -> bool:
    """Vrai si Maestro a routé l'email vers un AUTRE agent que moi.

    Args:
        internet_message_id: Message-ID Internet du courriel
        my_route: ma route Maestro ("to_camille", "to_sophie",
                  "to_beatrice", "to_karine")

    Returns:
        True : SKIP (Maestro a explicitement routé ailleurs)
        False : continue (pas dispatché OU dispatché vers moi OU vers Yves
                directement OU urgence)

    Note rétro-compatibilité :
        - Si Maestro pas encore traité → False (l'agent continue son flow)
        - Si Maestro a routé `to_yves_directly` ou `alert_yves_priority` →
          False (les agents peuvent quand même décider de drafter ; c'est
          une suggestion forte mais pas un veto)
        - Si Maestro a routé `ignore_no_reply` → True (skip strict)
    """
    route = get_maestro_route(internet_message_id)
    if route is None:
        return False  # Pas encore dispatché par Maestro
    if route == my_route:
        return False  # C'est bien pour moi
    if route == "ignore_no_reply":
        return True   # Skip strict
    # Autres routes (vers un AUTRE spécialiste) → skip
    other_specialist_routes = {
        "to_camille", "to_sophie", "to_beatrice", "to_karine",
        "to_hugo_pipeline",
    }
    if route in other_specialist_routes:
        return True
    # to_yves_directly / alert_yves_priority → l'agent peut quand même drafter
    # (Yves verra le draft + l'alerte ; il choisit)
    return False
