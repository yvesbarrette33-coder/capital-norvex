"""CLI Sophie — pipeline manuel.

Usage :
    python -m agents.sophie_norvex_relations run                     # full pipeline
    python -m agents.sophie_norvex_relations run --top 50            # 50 derniers
    python -m agents.sophie_norvex_relations run --no-draft          # triage seul
    python -m agents.sophie_norvex_relations run --all               # inclure déjà-lus
"""
from __future__ import annotations

import argparse
import json
import sys

from .orchestrator import process_all_mailboxes


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["run"], help="Commande à exécuter")
    p.add_argument("--top", type=int, default=25, help="N derniers messages")
    p.add_argument("--all", action="store_true", help="Inclure déjà-lus")
    p.add_argument("--no-draft", action="store_true", help="Triage seul, pas de drafting")
    p.add_argument("--mark-read", action="store_true", help="Marquer lus après drafting")
    args = p.parse_args()

    if args.cmd == "run":
        results = process_all_mailboxes(
            top=args.top, only_unread=not args.all,
            auto_draft=not args.no_draft, mark_read_after=args.mark_read,
        )
        print(json.dumps(results, indent=2, default=str, ensure_ascii=False))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
