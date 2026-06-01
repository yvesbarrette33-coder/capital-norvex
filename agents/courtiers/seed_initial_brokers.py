"""Agent COURTIERS — chargement initial depuis data/seed_brokers.json.

Usage:
    python -m agents.courtiers.seed_initial_brokers [--dry-run]
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

AGENT_NAME = "courtiers"
SEED_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "seed_brokers.json")
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--seed-file", default=SEED_PATH)
    args = parser.parse_args()

    if not os.path.exists(args.seed_file):
        print(f"❌ seed introuvable: {args.seed_file}")
        return 1

    with open(args.seed_file, "r", encoding="utf-8") as f:
        seed = json.load(f)
    brokers: List[Dict[str, Any]] = seed.get("brokers", [])
    print(f"📂 {len(brokers)} courtiers dans {args.seed_file}")

    created, blocked = 0, 0
    for b in brokers:
        try:
            check_before_action({**b, "_agent": AGENT_NAME, "_target_type": "broker"})
        except TierZeroBlocked as e:
            print(f"🚫 BLOQUÉ TIER ZERO: {b.get('name')} ({e.matched_name})")
            blocked += 1
            continue

        if args.dry_run:
            print(f"  • [dry-run] Créerait: {b.get('name')} ({b.get('region')})")
            created += 1
            continue
        doc_id = fs.create("brokers", b)
        print(f"  ✅ {doc_id}: {b.get('name')}")
        created += 1

    if not args.dry_run:
        fs.audit_log(
            agent=AGENT_NAME,
            action="seed_initial_brokers",
            details={"created": created, "blocked_tier_zero": blocked},
        )
    print(f"\nRésumé: créés={created}, bloqués_TIER_ZERO={blocked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
