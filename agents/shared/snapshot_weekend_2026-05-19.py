"""Snapshot weekend Victoria Day — vendredi 15 mai 0h EDT → mardi 19 mai 9h33 EDT.

Source de vérité : Firestore (opens/clicks aggregés par les agents).
Fenêtre = long weekend de congé Victoria Day (lundi 18 mai férié).
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/Users/yvesbarrette/Desktop/capitalnorvex-site")

from agents.shared.firestore_client import query


# Fenêtre EDT (UTC-4) → UTC
# Vendredi 15 mai 00:00 EDT  = 15 mai 04:00 UTC
# Mardi 19 mai 09:33 EDT     = 19 mai 13:33 UTC
WINDOW_START = datetime(2026, 5, 15, 4, 0, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 5, 19, 13, 33, tzinfo=timezone.utc)


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


def get_last_event_at(d: dict):
    """Dernier open/click connu (si l'agent l'a stocké)."""
    for key in ("lastOpenAt", "lastClickAt", "lastEngagementAt", "updatedAt"):
        v = d.get(key)
        if not v:
            continue
        try:
            if hasattr(v, "tzinfo"):
                return v
            s = str(v).replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None


def fmt_edt(dt: datetime) -> str:
    if dt is None:
        return "?"
    edt = dt.astimezone(timezone(timedelta(hours=-4)))
    return edt.strftime("%a %d %b %H:%M EDT")


def main() -> None:
    sections = [
        ("capitalTargets", "CAPITAL"),
        ("promoteurTargets", "PROMOTEURS"),
        ("brokers", "COURTIERS"),
    ]

    overall_sent_window = 0
    overall_opens = 0
    overall_clicks = 0
    leads_chauds = []
    leads_overnight = []  # activité dans la fenêtre (engagement récent)

    for col, label in sections:
        docs = query(col, limit=3000)
        sent_in_window = []
        opens_total = 0
        clicks_total = 0

        for d in docs:
            sa = get_sent_at(d)
            opens = int(d.get("opens", 0) or d.get("openCount", 0) or 0)
            clicks = int(d.get("clicks", 0) or d.get("clickCount", 0) or 0)
            last_evt = get_last_event_at(d)

            # Envois pendant le weekend
            if sa is not None and WINDOW_START <= sa <= WINDOW_END:
                sent_in_window.append(d)

            # Leads chauds cumulés
            if clicks >= 1 or opens >= 3:
                name = d.get("nom") or d.get("name") or d.get("companyName") or "?"
                org = d.get("organization") or d.get("companyName") or ""
                leads_chauds.append({
                    "section": label, "name": name, "org": org,
                    "email": get_email(d), "opens": opens, "clicks": clicks,
                    "sent_at": sa, "last_evt": last_evt,
                })

            # Activité dans la fenêtre (engagement récent)
            if last_evt is not None and WINDOW_START <= last_evt <= WINDOW_END and (opens >= 1 or clicks >= 1):
                name = d.get("nom") or d.get("name") or d.get("companyName") or "?"
                org = d.get("organization") or d.get("companyName") or ""
                leads_overnight.append({
                    "section": label, "name": name, "org": org,
                    "email": get_email(d), "opens": opens, "clicks": clicks,
                    "sent_at": sa, "last_evt": last_evt,
                })

            opens_total += opens
            clicks_total += clicks

        print(f"\n=== {label} ===")
        print(f"  Envoyés pendant le weekend (15-19 mai) : {len(sent_in_window)}")
        print(f"  Opens cumulés (total all-time) : {opens_total}")
        print(f"  Clicks cumulés (total all-time): {clicks_total}")
        overall_sent_window += len(sent_in_window)
        overall_opens += opens_total
        overall_clicks += clicks_total

    print(f"\n=== TOTAUX WEEKEND VICTORIA DAY ===")
    print(f"  Fenêtre : ven 15 mai 0h00 EDT → mar 19 mai 9h33 EDT")
    print(f"  Envois pendant le weekend : {overall_sent_window}")
    print(f"  Opens all-time cumulés    : {overall_opens}")
    print(f"  Clicks all-time cumulés   : {overall_clicks}")

    # Activité weekend (engagement dans la fenêtre)
    leads_overnight.sort(key=lambda x: (x["clicks"], x["opens"]), reverse=True)
    print(f"\n=== ACTIVITÉ ENGAGEMENT PENDANT LE WEEKEND ({len(leads_overnight)} cibles) ===")
    if not leads_overnight:
        print("  (aucune activité détectée dans la fenêtre — possible si lastOpenAt/lastClickAt pas stocké)")
    for lead in leads_overnight[:30]:
        print(f"  [{lead['section']}] {lead['name']} / {lead['org']}")
        print(f"      {lead['email']}  —  opens={lead['opens']} clicks={lead['clicks']}")
        print(f"      sent {fmt_edt(lead['sent_at'])} · dernier évt {fmt_edt(lead['last_evt'])}")

    # Top leads chauds all-time
    leads_chauds.sort(key=lambda x: (x["clicks"], x["opens"]), reverse=True)
    print(f"\n=== TOP 25 LEADS CHAUDS ALL-TIME (clicks≥1 ou opens≥3) ===")
    for lead in leads_chauds[:25]:
        d_sent = fmt_edt(lead["sent_at"]) if lead["sent_at"] else "?"
        d_evt = fmt_edt(lead["last_evt"]) if lead["last_evt"] else "?"
        print(f"  [{lead['section']}] {lead['name']} / {lead['org']}")
        print(f"      {lead['email']}  —  opens={lead['opens']} clicks={lead['clicks']}")
        print(f"      sent {d_sent} · dernier évt {d_evt}")


if __name__ == "__main__":
    main()
