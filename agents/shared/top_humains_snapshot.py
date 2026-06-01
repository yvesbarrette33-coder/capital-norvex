#!/usr/bin/env python3
"""Top leads chauds — snapshot SendGrid (filtre humain).

Filtre les scanners de sécurité corporate (Mimecast, Proofpoint, etc.)
pour ne garder que les opens/clicks d'humains réels.

Usage:
    python -m agents.shared.top_humains_snapshot [--top 25]
"""
import os
import sys
import json
import time
import argparse
from collections import defaultdict
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.capitalnorvex/.env"))
SG_KEY = os.environ.get("SENDGRID_API_KEY", "")
if not SG_KEY:
    print("❌ SENDGRID_API_KEY manquant", file=sys.stderr)
    sys.exit(1)

# User-agents identifiés comme scanners/bots — à exclure
BOT_UA_PATTERNS = [
    "GoogleImageProxy", "YahooMailProxy", "Mimecast", "Proofpoint",
    "Microsoft Defender", "Office365 Connectivity", "MicrosoftOutlook",
    "Python", "aiohttp", "curl", "wget", "Go-http-client", "Java/",
    "okhttp", "PostmanRuntime", "Apache-HttpClient", "node-fetch",
    "BarracudaCentral", "Cisco", "Forcepoint", "Symantec", "FireEye",
    "TrendMicro", "Sophos", "McAfee",
]


def is_bot(ua: str) -> bool:
    if not ua:
        return True  # pas de UA = suspect
    for pattern in BOT_UA_PATTERNS:
        if pattern.lower() in ua.lower():
            return True
    return False


def fetch_messages(query: str, limit: int = 1000) -> list:
    """Query SendGrid messages API."""
    msgs = []
    url = "https://api.sendgrid.com/v3/messages"
    r = requests.get(
        url,
        params={"query": query, "limit": min(limit, 1000)},
        headers={"Authorization": f"Bearer {SG_KEY}"},
        timeout=30,
    )
    if r.status_code != 200:
        print(f"⚠️ SendGrid {r.status_code}: {r.text[:200]}", file=sys.stderr)
        return []
    data = r.json()
    return data.get("messages", [])


def fetch_events(msg_id: str) -> dict:
    """Récupère détails events pour un message."""
    url = f"https://api.sendgrid.com/v3/messages/{msg_id}"
    r = requests.get(url, headers={"Authorization": f"Bearer {SG_KEY}"}, timeout=30)
    if r.status_code != 200:
        return {}
    return r.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=25)
    parser.add_argument("--date", default="2026-05-07", help="Date d'envoi cohorte (YYYY-MM-DD)")
    parser.add_argument("--window-days", type=int, default=7,
                        help="Nb de jours d'activité post-envoi à scanner (default 7)")
    parser.add_argument("--no-cohort-filter", action="store_true",
                        help="Ne pas filtrer par date d'envoi côté client — voir TOUTE l'activité du range")
    args = parser.parse_args()

    snapshot_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Range last_event_time : du jour d'envoi + window_days
    from datetime import datetime as dt, timedelta
    cohort_start = dt.strptime(args.date, "%Y-%m-%d")
    range_end = cohort_start + timedelta(days=args.window_days)
    # Borne max = aujourd'hui (jamais futur)
    today = dt.utcnow()
    if range_end > today:
        range_end = today

    print(f"🔍 Snapshot SendGrid — {snapshot_time}")
    print(f"   Cohorte d'envoi  : {args.date}")
    print(f"   Fenêtre activité : {args.date} → {range_end.strftime('%Y-%m-%d')} "
          f"({(range_end - cohort_start).days} jours)")
    print(f"   Filtre cohorte   : {'OFF (toute activité)' if args.no_cohort_filter else 'ON (envoyé le ' + args.date + ')'}")
    print()

    # Query SendGrid : tous messages avec last_event_time dans la fenêtre élargie
    query = (
        f'last_event_time > TIMESTAMP "{args.date}T00:00:00Z" '
        f'AND last_event_time < TIMESTAMP "{range_end.strftime("%Y-%m-%d")}T23:59:59Z"'
    )
    all_msgs = fetch_messages(query, limit=1000)
    msgs_engaged = [m for m in all_msgs if (m.get("opens_count", 0) > 0 or m.get("clicks_count", 0) > 0)]
    print(f"📬 {len(msgs_engaged)} messages avec engagement (sur {len(all_msgs)} dans la fenêtre)")
    if len(all_msgs) >= 1000:
        print(f"   ⚠️  Limite SendGrid 1000 atteinte — résultats potentiellement tronqués")
    msgs = msgs_engaged

    # Aggregate par to_email
    per_email = defaultdict(lambda: {
        "human_opens": 0,
        "human_clicks": 0,
        "raw_opens": 0,
        "raw_clicks": 0,
        "unique_human_uas": set(),
        "subject": "",
        "from_email": "",
    })

    skipped_out_of_cohort = 0
    for i, m in enumerate(msgs):
        if i % 25 == 0:
            print(f"   {i}/{len(msgs)} messages traités…", end="\r")
        msg_id = m.get("msg_id")
        to_email = m.get("to_email", "").lower()
        if not to_email or not msg_id:
            continue

        # Fetch details d'abord pour pouvoir filtrer par date d'envoi
        details = fetch_events(msg_id)
        events = details.get("events", [])

        # Trouver la date d'envoi (1er event "processed" ou "delivered")
        sent_date = None
        for ev in events:
            if ev.get("event_name") in ("processed", "delivered"):
                ts = ev.get("processed") or ev.get("delivered") or ""
                if ts:
                    sent_date = ts[:10]  # YYYY-MM-DD
                    break

        # Filtre cohorte
        if not args.no_cohort_filter and sent_date and sent_date != args.date:
            skipped_out_of_cohort += 1
            continue

        per_email[to_email]["raw_opens"] += m.get("opens_count", 0)
        per_email[to_email]["raw_clicks"] += m.get("clicks_count", 0)
        per_email[to_email]["subject"] = m.get("subject", "")
        per_email[to_email]["from_email"] = m.get("from_email", "")
        per_email[to_email]["sent_date"] = sent_date or "?"

        for ev in events:
            ev_type = ev.get("event_name", "")
            ua = ev.get("http_user_agent", "") or ev.get("user_agent", "")
            if ev_type not in ("open", "click"):
                continue
            if is_bot(ua):
                continue
            if ev_type == "open":
                per_email[to_email]["human_opens"] += 1
            else:
                per_email[to_email]["human_clicks"] += 1
            per_email[to_email]["unique_human_uas"].add(ua[:80])
        time.sleep(0.05)  # rate limit

    if skipped_out_of_cohort:
        print(f"   ↪ {skipped_out_of_cohort} messages ignorés (hors cohorte {args.date})")
    print(f"\n✅ {len(per_email)} destinataires uniques avec engagement dans la cohorte\n")

    # Tri par human_clicks puis human_opens
    ranked = sorted(
        per_email.items(),
        key=lambda kv: (kv[1]["human_clicks"], kv[1]["human_opens"]),
        reverse=True,
    )

    print(f"━━━ TOP {args.top} LEADS CHAUDS HUMAINS — {snapshot_time} ━━━\n")
    print(f"{'Rang':<5}{'Destinataire':<45}{'H-Cl':<6}{'H-Op':<6}{'#UA':<5}{'Raw-Cl':<7}{'Raw-Op':<7}")
    print("─" * 95)
    for i, (email, stats) in enumerate(ranked[:args.top], 1):
        nb_ua = len(stats["unique_human_uas"])
        print(
            f"{i:<5}{email[:43]:<45}"
            f"{stats['human_clicks']:<6}{stats['human_opens']:<6}"
            f"{nb_ua:<5}{stats['raw_clicks']:<7}{stats['raw_opens']:<7}"
        )

    # Sauvegarde JSON pour comparaison snapshots futurs
    out_path = f"/tmp/top_humains_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    serializable = {
        "snapshot_time": snapshot_time,
        "cohort_date": args.date,
        "total_destinataires": len(per_email),
        "top": [
            {
                "rank": i,
                "email": email,
                "human_clicks": s["human_clicks"],
                "human_opens": s["human_opens"],
                "unique_uas": len(s["unique_human_uas"]),
                "raw_clicks": s["raw_clicks"],
                "raw_opens": s["raw_opens"],
                "subject": s["subject"],
                "from": s["from_email"],
            }
            for i, (email, s) in enumerate(ranked[:args.top], 1)
        ],
    }
    with open(out_path, "w") as f:
        json.dump(serializable, f, indent=2)
    print(f"\n💾 Snapshot sauvegardé : {out_path}")


if __name__ == "__main__":
    main()
