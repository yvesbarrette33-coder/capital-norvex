"""Émile — NORVEX BRIEFING™

Agent de préparation pré-RDV. Génère un brief premium 1 page (HTML) pour
chaque RDV Teams confirmé, à partir du profil Firestore + stats SendGrid +
analyse Claude Opus.

Usage CLI :
    python -m agents.emile <target_collection> <target_doc_id>
    python -m agents.emile capitalTargets ie7YRDszJQh8OlxDH4U3

Usage import :
    from agents.emile import generate_brief
    path = generate_brief("capitalTargets", "ie7YRDszJQh8OlxDH4U3")
"""

from .briefing_generator import generate_brief

__all__ = ["generate_brief"]
