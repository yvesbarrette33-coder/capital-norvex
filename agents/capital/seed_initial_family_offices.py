"""Agent CAPITAL — chargement initial family offices (QC + ON).

Usage:
    python -m agents.capital.seed_initial_family_offices [--dry-run]
    python -m agents.capital.seed_initial_family_offices \\
        --seed-file data/MASTER/seed_family_offices_ALL_2026-05-07.json --dry-run

Note : la clé JSON attendue est `familyOffices` (camelCase, master format).
Fallback sur `family_offices` (snake_case) si présent.
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

AGENT_NAME = "capital"
SEED_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "data",
        "seed_family_offices.json",
    )
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--seed-file", default=SEED_PATH)
    parser.add_argument("--input", dest="seed_file_alias", default=None,
                        help="Alias de --seed-file (compat README MASTER)")
    args = parser.parse_args()

    seed_file = args.seed_file_alias or args.seed_file

    if not os.path.exists(seed_file):
        print(f"❌ seed introuvable: {seed_file}")
        return 1

    with open(seed_file, "r", encoding="utf-8") as f:
        seed = json.load(f)

    # Master format = "familyOffices" (camelCase). Fallback "family_offices".
    family_offices: List[Dict[str, Any]] = (
        seed.get("familyOffices")
        or seed.get("family_offices")
        or []
    )
    print(f"📂 {len(family_offices)} family offices dans {seed_file}")

    created, blocked = 0, 0
    for fo in family_offices:
        # `name` peut être "à identifier" ; on garde organization comme identifiant principal.
        display = fo.get("organization") or fo.get("name") or "?"
        try:
            check_before_action(
                {**fo, "_agent": AGENT_NAME, "_target_type": "family_office"}
            )
        except TierZeroBlocked as e:
            print(f"🚫 BLOQUÉ TIER ZERO: {display} ({e.matched_name})")
            blocked += 1
            continue

        if args.dry_run:
            print(
                f"  • [dry-run] Créerait: {display} "
                f"({fo.get('region', '?')}/{fo.get('city', '?')})"
            )
            created += 1
            continue
        doc_id = fs.create("family_offices", fo)
        print(f"  ✅ {doc_id}: {display}")
        created += 1

    if not args.dry_run:
        fs.audit_log(
            agent=AGENT_NAME,
            action="seed_initial_family_offices",
            details={"created": created, "blocked_tier_zero": blocked},
        )
    print(f"\nRésumé: créés={created}, bloqués_TIER_ZERO={blocked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
