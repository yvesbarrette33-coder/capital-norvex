"""Régénère TOUS les drafts pending dans Firestore + Firebase Storage.

Utile après une modification de template (changement de numéro de tél, etc.)
pour mettre à jour les drafts existants qui contiennent encore l'ancienne version.

Usage:
    python -m agents.regenerate_drafts
    python -m agents.regenerate_drafts --collection brokers   # courtiers seulement
    python -m agents.regenerate_drafts --collection promoters # promoteurs seulement
"""
from __future__ import annotations

import argparse
import sys

from .shared import firestore_client as fs


def regenerate_brokers() -> int:
    """Regenerate tous les drafts courtiers existants."""
    from .courtiers.outreach import queue_one as queue_broker

    docs = fs.query("brokers", limit=500)
    targets = [d for d in docs if d.get("pendingDraft") and not d.get("sentAt")]

    if not targets:
        print("✓ Aucun draft pending pour les courtiers.")
        return 0

    print(f"📋 {len(targets)} draft(s) courtier à regenerate…")
    ok = 0
    for broker in targets:
        doc_id = broker.get("id") or broker.get("docId")
        if not doc_id:
            continue
        if queue_broker(doc_id, force=True):
            ok += 1
    print(f"✅ {ok}/{len(targets)} drafts courtiers régénérés.")
    return ok


def regenerate_promoters() -> int:
    """Regenerate tous les drafts promoteurs existants."""
    from .promoteurs.outreach import queue_one as queue_promoter

    docs = fs.query("promoters", limit=500)
    targets = [d for d in docs if d.get("pendingDraft") and not d.get("sentAt")]

    if not targets:
        print("✓ Aucun draft pending pour les promoteurs.")
        return 0

    print(f"📋 {len(targets)} draft(s) promoteur à regenerate…")
    ok = 0
    for promoter in targets:
        doc_id = promoter.get("id") or promoter.get("docId")
        if not doc_id:
            continue
        if queue_promoter(doc_id, force=True):
            ok += 1
    print(f"✅ {ok}/{len(targets)} drafts promoteurs régénérés.")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--collection",
        choices=["all", "brokers", "promoters"],
        default="all",
        help="Quelle collection regenerate (défaut: tout)",
    )
    args = parser.parse_args()

    total = 0
    if args.collection in ("all", "brokers"):
        total += regenerate_brokers()
    if args.collection in ("all", "promoters"):
        total += regenerate_promoters()

    print(f"\n🎯 Total: {total} drafts régénérés.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
