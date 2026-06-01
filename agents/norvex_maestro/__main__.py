"""Entry point Norvex Maestro™ — `python -m agents.norvex_maestro`.

Utilisé par le launchd cron (com.capitalnorvex.maestro).
"""
from __future__ import annotations

import json
import logging
import sys

from .orchestrator import process_all_mailboxes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [maestro] %(levelname)s %(message)s",
)


def main() -> int:
    try:
        results = process_all_mailboxes(top=50, only_unread=True)
    except Exception as e:
        logging.exception("Maestro cron failed: %s", e)
        return 1

    total_routed = 0
    total_skipped = 0
    total_alerts = 0
    by_route: dict = {}

    for mailbox, mailbox_results in results.items():
        for r in mailbox_results:
            if not isinstance(r, dict):
                continue
            if r.get("skipped"):
                total_skipped += 1
                continue
            if r.get("route"):
                total_routed += 1
                by_route[r["route"]] = by_route.get(r["route"], 0) + 1
            if r.get("alert"):
                total_alerts += 1

    summary = {
        "routed": total_routed,
        "skipped": total_skipped,
        "alerts": total_alerts,
        "by_route": by_route,
    }
    logging.info("Maestro run : %s", summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
