"""Norvex Brain v0 — Brief matinal orchestrateur.

Cron quotidien 7h00 EST. Lit Firestore, compose le brief Variation A,
envoie à yves@capitalnorvex.com via Microsoft Graph.

Format brief:
   ─ CAPITAL    : nouvelles cibles, prêtes, pending, réponses
   ─ COURTIERS  : nouveaux warms, deal cards à valider
   ─ PROMOTEURS : actions du jour
   ─ ALERTES    : tentatives TIER ZERO
   ─ À approuver: liste compacte avec lien pipeline

Usage manuel:
    python -m agents.brain.daily_brief [--dry-run] [--to email@x.com]
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from ..shared import firestore_client as fs
from ..shared.email_sender import send_email
from ..shared.email_template import (
    COLOR_GOLD,
    render_variation_a,
)

AGENT_NAME = "brain"
PIPELINE_URL = "https://capitalnorvex.com/capital-norvex-pipeline.html"


def _section_capital() -> Dict[str, Any]:
    new_targets = fs.query("capitalTargets", filters=[("status", "==", "research")], limit=20)
    ready = fs.query("capitalTargets", filters=[("status", "==", "ready")], limit=20)
    pending = fs.query(
        "capitalApproaches", filters=[("status", "==", "pending_yves_approval")], limit=20
    )
    responded = fs.query("capitalApproaches", filters=[("status", "==", "responded")], limit=20)
    return {
        "name": "CAPITAL",
        "counts": {
            "new": len(new_targets),
            "ready": len(ready),
            "pending": len(pending),
            "responded": len(responded),
        },
        "pending_items": pending,
        "ready_items": ready,
    }


def _section_courtiers() -> Dict[str, Any]:
    warms = fs.query("brokers", filters=[("relationshipStatus", "==", "warm")], limit=50)
    pending = fs.query(
        "brokerCommunications", filters=[("status", "==", "pending_yves_approval")], limit=20
    )
    return {
        "name": "COURTIERS",
        "counts": {"warms": len(warms), "pending": len(pending)},
        "pending_items": pending,
    }


def _section_promoteurs() -> Dict[str, Any]:
    pending = fs.query(
        "promoterApproaches", filters=[("status", "==", "pending_yves_approval")], limit=20
    )
    return {
        "name": "PROMOTEURS",
        "counts": {"pending": len(pending)},
        "pending_items": pending,
    }


def _section_alertes() -> Dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(days=1)
    alerts = fs.query(
        "agentAuditLog",
        filters=[("result", "==", "blocked_tier_zero"), ("timestamp", ">=", since)],
        limit=10,
    )
    return {"name": "ALERTES", "counts": {"tier_zero_blocks": len(alerts)}, "items": alerts}


def render_brief_html() -> str:
    cap = _section_capital()
    crt = _section_courtiers()
    pro = _section_promoteurs()
    alr = _section_alertes()

    def line(label: str, txt: str) -> str:
        return (
            f'<p style="margin:0 0 8px 0;">'
            f'<strong style="color:{COLOR_GOLD};letter-spacing:1px;">─ {label}</strong> : {txt}</p>'
        )

    cap_txt = (
        f'{cap["counts"]["new"]} nouvelles cibles, '
        f'{cap["counts"]["ready"]} prêtes, '
        f'{cap["counts"]["pending"]} en attente d\'approbation, '
        f'{cap["counts"]["responded"]} réponses à analyser.'
    )
    crt_txt = (
        f'{crt["counts"]["warms"]} warms actifs, '
        f'{crt["counts"]["pending"]} communications à valider.'
    )
    pro_txt = f'{pro["counts"]["pending"]} actions à valider.'
    alr_txt = (
        f'{alr["counts"]["tier_zero_blocks"]} tentatives TIER ZERO bloquées (24h).'
        if alr["counts"]["tier_zero_blocks"]
        else "aucune."
    )

    total_pending = (
        cap["counts"]["pending"] + crt["counts"]["pending"] + pro["counts"]["pending"]
    )
    approval_block = ""
    if total_pending:
        approval_block = (
            f'<p style="margin:18px 0 6px 0;font-style:italic;">'
            f'<strong>{total_pending}</strong> communication(s) en attente '
            f'd\'approbation aujourd\'hui :</p>'
            f'<p style="margin:0 0 0 0;"><a href="{PIPELINE_URL}" style="color:{COLOR_GOLD};">'
            f'Ouvrir le pipeline →</a></p>'
        )

    today = datetime.now().strftime("%A %d %B %Y").capitalize()
    body = (
        f'<p style="margin:0 0 14px 0;">Bonjour Yves,</p>'
        f'<p style="margin:0 0 18px 0;">Voici le brief Norvex du {today}.</p>'
        f"{line('CAPITAL', cap_txt)}"
        f"{line('COURTIERS', crt_txt)}"
        f"{line('PROMOTEURS', pro_txt)}"
        f"{line('ALERTES', alr_txt)}"
        f"{approval_block}"
        f'<p style="margin:24px 0 0 0;font-style:italic;color:#555;">'
        f'— Norvex Brain v0</p>'
    )
    return render_variation_a(
        body_html=body,
        recipient_name=None,
        title_line="Brief matinal — Capital Norvex",
        show_signature=False,
    )


def send_brief(to: str = None, dry_run: bool = False) -> bool:
    yves_email = to or os.getenv("YVES_EMAIL", "yvesbarrette33@gmail.com")
    html = render_brief_html()

    if dry_run:
        out_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "brief_preview.html")
        )
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"📄 Brief écrit en local: {out_path}")
        return True

    today_str = datetime.now().strftime("%Y-%m-%d")
    ok = send_email(
        to=yves_email,
        subject=f"[Capital Norvex] Brief matinal — {today_str}",
        html=html,
    )
    fs.audit_log(
        agent=AGENT_NAME,
        action="send_daily_brief",
        result="success" if ok else "error",
        details={"to": yves_email},
    )
    return ok


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="Écrit data/brief_preview.html sans envoyer")
    p.add_argument("--to", default=None, help="Adresse destinataire (défaut: YVES_EMAIL)")
    args = p.parse_args()
    ok = send_brief(to=args.to, dry_run=args.dry_run)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
