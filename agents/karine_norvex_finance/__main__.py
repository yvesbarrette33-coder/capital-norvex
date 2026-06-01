"""Entry point Karine — `python -m agents.karine_norvex_finance`.

Utilisé par le launchd cron (com.capitalnorvex.karine).
"""
from __future__ import annotations

import json
import logging
import sys

from .orchestrator import process_all_mailboxes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [karine] %(levelname)s %(message)s",
)


def main() -> int:
    try:
        results = process_all_mailboxes(top=25, only_unread=True,
                                         mark_read_after=False)
    except Exception as e:
        logging.exception("Karine cron failed: %s", e)
        return 1

    total_tx = 0
    total_skipped = 0
    for mailbox, mailbox_results in results.items():
        for r in mailbox_results:
            tx = r.get("transactions_created", []) if isinstance(r, dict) else []
            total_tx += len(tx)
            if isinstance(r, dict) and r.get("skipped"):
                total_skipped += 1

    logging.info(
        "Karine run complete : %d transactions pending créées, %d emails skipped",
        total_tx, total_skipped,
    )
    print(json.dumps({"transactions_created": total_tx,
                      "emails_skipped": total_skipped}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
