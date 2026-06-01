"""Snapshot journée 12 mai 2026 — bilan envois + opens/clicks via Firestore.

Source de vérité : Firestore (opens/clicks aggregés par les agents).
Plus rapide et fiable que SendGrid API directe.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone, date

sys.path.insert(0, "/Users/yvesbarrette/Desktop/capitalnorvex-site")

from agents.shared.firestore_client import query


def get_email(d: dict) -> str:
    ci = d.get("contactInfo") or {}
    pc = d.get("publicContact") or {}
    return d.get("email") or ci.get("email") or pc.get("email") or ""


def get_sent_at(d: dict):
    v = d.get("sentAt") or d.get("lastSentAt")
    if not v:
        return None
    try:
        if hasattr(v, "tzinfo"):
            return v
        s = str(v).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def main() -> None:
    today = date(2026, 5, 12)

    sections = [
        ("capitalTargets", "CAPITAL"),
        ("promoteurTargets", "PROMOTEURS"),
        ("brokers", "COURTIERS"),
    ]
    overall_sent_today = 0
    overall_opens = 0
    overall_clicks = 0
    leads_chauds = []

    for col, label in sections:
        docs = query(col, limit=2000)
        sent_today = []
        opens_total = 0
        clicks_total = 0
        for d in docs:
            sa = get_sent_at(d)
            if sa is None:
                continue
            opens = int(d.get("opens", 0) or d.get("openCount", 0) or 0)
            clicks = int(d.get("clicks", 0) or d.get("clickCount", 0) or 0)
            if sa.date() == today:
                sent_today.append(d)
                opens_total += opens
                clicks_total += clicks
            # Leads chauds = clicks >= 1 OR opens >= 3, peu importe la date
            if clicks >= 1 or opens >= 3:
                name = d.get("nom") or d.get("name") or d.get("companyName") or "?"
                org = d.get("organization") or d.get("companyName") or ""
                leads_chauds.append({
                    "section": label, "name": name, "org": org,
                    "email": get_email(d), "opens": opens, "clicks": clicks,
                    "sent_at": sa,
                })

        print(f"\n=== {label} ===")
        print(f"  Envoyés AUJOURD'HUI ({today}) : {len(sent_today)}")
        print(f"  Opens cumulés     : {opens_total}")
        print(f"  Clicks cumulés    : {clicks_total}")
        overall_sent_today += len(sent_today)
        overall_opens += opens_total
        overall_clicks += clicks_total

    print(f"\n=== TOTAL JOURNÉE {today} ===")
    print(f"  Envois aujourd'hui : {overall_sent_today}")
    print(f"  Opens cumulés (aujourd'hui)  : {overall_opens}")
    print(f"  Clicks cumulés (aujourd'hui) : {overall_clicks}")

    leads_chauds.sort(key=lambda x: (x["clicks"], x["opens"]), reverse=True)
    print(f"\n=== TOP 20 LEADS CHAUDS (toutes dates, clicks≥1 ou opens≥3) ===")
    for lead in leads_chauds[:20]:
        d = lead["sent_at"].date()
        print(f"  [{lead['section']}] {lead['name']} / {lead['org']}")
        print(f"      {lead['email']}  —  sent {d}  —  opens={lead['opens']} clicks={lead['clicks']}")


if __name__ == "__main__":
    main()
