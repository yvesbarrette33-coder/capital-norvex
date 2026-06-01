"""Fix language field on existing Firestore docs based on region.

Règle :
  - region == "ON" → language = "en"
  - region == "QC" → language = "fr"
  - autre → laisser tel quel

Usage :
    python -m agents.shared.fix_language_by_region [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from typing import Any, Dict

from . import firestore_client as fs


def expected_lang(region: str | None) -> str | None:
    if not region:
        return None
    r = region.upper().strip()
    if r == "ON":
        return "en"
    if r == "QC":
        return "fr"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    collections = ["brokers", "promoters", "family_offices"]
    total_fixed = 0
    total_already_ok = 0
    total_skipped = 0

    for coll in collections:
        print(f"\n=== {coll} ===")
        docs = fs.query(coll)
        for doc in docs:
            doc_id = doc.get("id")
            region = doc.get("region")
            current = (doc.get("language") or "").lower() or None
            expected = expected_lang(region)

            display = (
                doc.get("name")
                or doc.get("companyName")
                or doc.get("organization")
                or doc_id
            )

            if expected is None:
                total_skipped += 1
                continue

            if current == expected:
                total_already_ok += 1
                continue

            # Fix needed
            if args.dry_run:
                print(
                    f"  [dry-run] {display} ({region}): "
                    f"language '{current}' → '{expected}'"
                )
            else:
                fs.update(coll, doc_id, {"language": expected})
                print(
                    f"  ✅ {display} ({region}): "
                    f"language '{current}' → '{expected}'"
                )
            total_fixed += 1

    if not args.dry_run:
        fs.audit_log(
            agent="shared",
            action="fix_language_by_region",
            details={
                "fixed": total_fixed,
                "already_ok": total_already_ok,
                "skipped_no_region": total_skipped,
            },
        )

    print(
        f"\n📊 Résumé: fixés={total_fixed}, "
        f"déjà OK={total_already_ok}, "
        f"skip (region inconnue)={total_skipped}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
