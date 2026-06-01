"""Agent CAPITAL — script one-shot de chargement initial.

Charge data/seed_targets.json dans Firestore (capitalTargets), en
vérifiant TIER ZERO pour chaque entrée. Programme ensuite les jobs
de recherche.

Usage:
    python -m agents.capital.seed_initial_targets [--dry-run]
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
    is_protected,
)

AGENT_NAME = "capital"
SEED_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "seed_targets.json")
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="N'écrit rien dans Firestore")
    parser.add_argument(
        "--seed-file", default=SEED_PATH, help=f"Chemin vers seed (défaut: {SEED_PATH})"
    )
    args = parser.parse_args()

    if not os.path.exists(args.seed_file):
        print(f"❌ seed introuvable: {args.seed_file}")
        return 1

    with open(args.seed_file, "r", encoding="utf-8") as f:
        seed = json.load(f)

    targets: List[Dict[str, Any]] = seed.get("targets", [])
    print(f"📂 {len(targets)} cibles trouvées dans {args.seed_file}")

    skipped, created, blocked = 0, 0, 0
    for t in targets:
        name = t.get("name", "<sans nom>")
        try:
            check_before_action({**t, "_agent": AGENT_NAME, "_target_type": "capitalTarget"})
        except TierZeroBlocked as e:
            print(f"  🚫 BLOQUÉ TIER ZERO: {name} ({e.matched_name})")
            blocked += 1
            continue

        if t.get("protectedFlag"):
            print(f"  ⏭️  protectedFlag=True, ignoré: {name}")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  • [dry-run] Créerait: {name} (tier {t.get('tier')}, {t.get('region')})")
            created += 1
            continue

        doc_id = fs.create("capitalTargets", t)
        print(f"  ✅ Créé {doc_id}: {name} (tier {t.get('tier')}, {t.get('region')})")
        created += 1

    print(
        f"\nRésumé: créés={created}, ignorés_protected={skipped}, "
        f"bloqués_TIER_ZERO={blocked}"
    )
    if not args.dry_run:
        fs.audit_log(
            agent=AGENT_NAME,
            action="seed_initial_targets",
            details={"created": created, "blocked_tier_zero": blocked, "skipped": skipped},
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
