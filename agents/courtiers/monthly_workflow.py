"""Agent COURTIERS — workflow mensuel.

Cron mensuel:
  S1: Deal cards → tous brokers actifs/champions
  S2: Email d'introduction → 10 nouveaux identifiés
  S3: Suivi warms sans deal envoyé
  S4: Appreciation des champions

Usage manuel pour debug:
    python -m agents.courtiers.monthly_workflow --week 1
"""
from __future__ import annotations

import argparse
import sys
from typing import Any, Dict, List

from ..shared import firestore_client as fs
from .deal_cards_generator import queue_monthly_deal_cards_for_active_brokers
from .relationship_manager import (
    identify_champions,
    identify_warm_brokers_to_followup,
)

AGENT_NAME = "courtiers"


def run_week(week: int) -> Dict[str, Any]:
    """Exécute le job correspondant à la semaine du mois (1-4)."""
    summary: Dict[str, Any] = {"week": week}

    if week == 1:
        ids = queue_monthly_deal_cards_for_active_brokers()
        summary["deal_cards_queued"] = len(ids)

    elif week == 2:
        # broker_finder peut être appelé ici pour ajouter 10 nouveaux
        # cold brokers. v1 : on documente uniquement.
        summary["new_brokers_to_identify"] = 10
        summary["note"] = "Brancher broker_finder.identify_brokers() ici en prod"

    elif week == 3:
        warms = identify_warm_brokers_to_followup(no_touch_days=60)
        for b in warms[:25]:
            fs.create(
                "brokerCommunications",
                {
                    "brokerId": b["id"],
                    "type": "check_in",
                    "sentDate": None,
                    "content": "<draft>",
                    "status": "draft",
                    "_agent": AGENT_NAME,
                },
            )
        summary["warm_followups_drafted"] = min(len(warms), 25)

    elif week == 4:
        champs = identify_champions(top_n=5)
        for c in champs:
            fs.create(
                "brokerCommunications",
                {
                    "brokerId": c["id"],
                    "type": "appreciation",
                    "sentDate": None,
                    "content": "<draft>",
                    "status": "draft",
                    "_agent": AGENT_NAME,
                },
            )
        summary["champion_appreciations_drafted"] = len(champs)

    else:
        raise ValueError("week doit être 1, 2, 3 ou 4")

    fs.audit_log(
        agent=AGENT_NAME,
        action="monthly_workflow_week",
        details=summary,
    )
    return summary


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--week", type=int, required=True, choices=[1, 2, 3, 4])
    args = p.parse_args()
    print(run_week(args.week))
    return 0


if __name__ == "__main__":
    sys.exit(main())
