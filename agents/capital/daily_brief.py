"""Agent CAPITAL — Brief matinal.

Note: l'orchestration globale (tous agents) est dans agents/brain/daily_brief.py.
Ce module fournit la *section Capital* du brief — il peut aussi être
appelé seul pour debug.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..shared import firestore_client as fs


def collect_capital_section() -> Dict[str, Any]:
    """Compile les éléments à présenter dans le brief matinal Capital."""
    new_targets = fs.query(
        "capitalTargets",
        filters=[("status", "==", "research")],
        limit=10,
    )
    ready_targets = fs.query(
        "capitalTargets",
        filters=[("status", "==", "ready")],
        limit=10,
    )
    pending_approvals = fs.query(
        "capitalApproaches",
        filters=[("status", "==", "pending_yves_approval")],
        limit=10,
    )
    responded = fs.query(
        "capitalApproaches",
        filters=[("status", "==", "responded")],
        limit=10,
    )

    return {
        "new_research_24h": new_targets,
        "ready_for_approach": ready_targets,
        "pending_approvals": pending_approvals,
        "responses_to_review": responded,
        "counts": {
            "new": len(new_targets),
            "ready": len(ready_targets),
            "pending": len(pending_approvals),
            "responded": len(responded),
        },
    }


def render_capital_section_html(section: Dict[str, Any]) -> str:
    """Compose la portion HTML 'Capital' du brief Variation A."""
    c = section["counts"]
    lines: List[str] = []
    lines.append(
        f'<p style="margin:0 0 8px 0;"><strong style="color:#C8B070;">'
        f'CAPITAL</strong> — '
        f'{c["new"]} nouvelles cibles à l\'étude, '
        f'{c["ready"]} prêtes pour approche, '
        f'{c["pending"]} en attente d\'approbation, '
        f'{c["responded"]} réponses à analyser.</p>'
    )
    if section["pending_approvals"]:
        lines.append('<ul style="margin:0 0 18px 18px;padding:0;">')
        for app in section["pending_approvals"][:5]:
            tid = app.get("targetId", "?")
            ttype = app.get("touchpointType", "communication")
            lines.append(
                f'<li style="margin-bottom:6px;">{ttype} → cible {tid} '
                f'(approuver dans le pipeline)</li>'
            )
        lines.append("</ul>")
    return "".join(lines)
