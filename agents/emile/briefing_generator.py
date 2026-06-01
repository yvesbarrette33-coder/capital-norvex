"""Émile — orchestrateur principal.

Pipeline :
  1. Pull target Firestore + engagement SendGrid
  2. Call Board of Advisors (Claude Opus 4.6 multi-perspective)
  3. Render HTML template Norvex
  4. Dépôt fichier sur Desktop + retour path
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .enrichment import fetch_target, build_engagement_summary
from .board_of_advisors import call_board
from .template import render_html_brief


def generate_brief(
    target_collection: str,
    target_doc_id: str,
    output_dir: Optional[str] = None,
    open_after: bool = True,
) -> str:
    """Génère un brief pré-call complet.

    Args:
        target_collection: ex 'capitalTargets'
        target_doc_id: ID Firestore
        output_dir: dossier de sortie (défaut : ~/Desktop)
        open_after: ouvrir le fichier dans Safari après génération

    Returns:
        Path absolu du fichier HTML généré.
    """
    print(f"[Émile] Génération brief pour {target_collection}/{target_doc_id}…")

    # 1. Pull profil
    target = fetch_target(target_collection, target_doc_id)
    name = target.get("name") or "Inconnu"
    org = target.get("organization") or ""
    print(f"[Émile] Profil : {name} ({org})")

    # 2. Engagement live
    engagement = build_engagement_summary(target)
    print(
        f"[Émile] Engagement : {engagement['perso'].get('opens', 0)} opens / "
        f"{engagement['perso'].get('clicks', 0)} clicks (perso)"
    )

    # 3. Call Board of Advisors
    print(f"[Émile] Consultation board (Claude Opus 4.6)…")
    advisor_output = call_board(target, engagement)

    # 4. Render
    html = render_html_brief(target, engagement, advisor_output)

    # 5. Dépôt
    out_dir = Path(output_dir) if output_dir else Path.home() / "Desktop"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = name.replace(" ", "_").replace("/", "_")
    today = datetime.now().strftime("%Y-%m-%d")
    fname = f"BRIEF_EMILE_{safe_name}_{today}.html"
    fpath = out_dir / fname
    fpath.write_text(html, encoding="utf-8")
    print(f"[Émile] ✅ Brief déposé : {fpath}")

    if open_after:
        try:
            os.system(f"open {fpath!s}")
        except Exception:
            pass

    return str(fpath)
