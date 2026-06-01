"""Agent PROMOTEURS v0 — chargement initial.

10 promoteurs test (data manuelle Yves dans data/seed_promoters.json).
Crée la structure pour v1 (mercredi 7 mai).

Usage:
    python -m agents.promoteurs.seed_initial_promoters [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List

from ..shared import firestore_client as fs
from ..shared.tier_zero_guard import (
    TierZeroBlocked,
    check_before_action,
)

AGENT_NAME = "promoteurs"
SEED_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "seed_promoters.json")
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--seed-file", default=SEED_PATH)
    args = parser.parse_args()

    if not os.path.exists(args.seed_file):
        print(
            f"⚠️  seed introuvable: {args.seed_file}\n"
            "   Crée data/seed_promoters.json avec un objet "
            '{"promoters":[...]} pour démarrer.'
        )
        return 1

    with open(args.seed_file, "r", encoding="utf-8") as f:
        seed = json.load(f)
    promoters: List[Dict[str, Any]] = seed.get("promoters", [])
    print(f"📂 {len(promoters)} promoteurs dans {args.seed_file}")

    created, blocked = 0, 0
    for p in promoters:
        try:
            check_before_action({**p, "_agent": AGENT_NAME, "_target_type": "promoter"})
        except TierZeroBlocked as e:
            print(f"🚫 BLOQUÉ: {p.get('name')} ({e.matched_name})")
            blocked += 1
            continue
        if args.dry_run:
            print(f"  • [dry-run] Créerait: {p.get('name')}")
            created += 1
            continue
        doc_id = fs.create("promoters", p)
        print(f"  ✅ {doc_id}: {p.get('name')}")
        created += 1

    if not args.dry_run:
        fs.audit_log(
            agent=AGENT_NAME,
            action="seed_initial_promoters",
            details={"created": created, "blocked_tier_zero": blocked},
        )
    print(f"\nRésumé: créés={created}, bloqués_TIER_ZERO={blocked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
