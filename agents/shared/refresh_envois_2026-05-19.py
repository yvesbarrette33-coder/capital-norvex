"""Refresh complet des envois — qui a été envoyé quand, par section.

Source : Firestore (capitalTargets / promoteurTargets / brokers) → sentAt.
Sortie : breakdown par date + listes nominatives + non-envoyés (cibles disponibles).
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta

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


def fmt_edt(dt: datetime) -> str:
    if dt is None:
        return "?"
    edt = dt.astimezone(timezone(timedelta(hours=-4)))
    return edt.strftime("%Y-%m-%d %a")


def main() -> None:
    sections = [
        ("capitalTargets", "CAPITAL PARTNERS"),
        ("promoteurTargets", "PROMOTEURS"),
        ("brokers", "COURTIERS"),
    ]

    grand_total_sent = 0
    grand_total_unsent = 0

    for col, label in sections:
        docs = query(col, limit=5000)
        sent_docs = []
        unsent_docs = []
        for d in docs:
            sa = get_sent_at(d)
            if sa:
                sent_docs.append((sa, d))
            else:
                unsent_docs.append(d)

        # Group by EDT date
        by_date = defaultdict(list)
        for sa, d in sent_docs:
            date_key = fmt_edt(sa)
            by_date[date_key].append(d)

        print(f"\n{'='*80}")
        print(f"=== {label}  —  {len(sent_docs)} envoyés / {len(unsent_docs)} jamais touchés")
        print(f"{'='*80}")

        for date_key in sorted(by_date.keys()):
            items = by_date[date_key]
            print(f"\n  📅 {date_key}  →  {len(items)} envois")
            for d in items[:50]:  # limit display
                name = d.get("nom") or d.get("name") or d.get("companyName") or "?"
                org = d.get("organization") or d.get("companyName") or d.get("firmName") or ""
                email = get_email(d)
                tier = d.get("tier", "")
                tier_str = f" [T{tier}]" if tier else ""
                lang = d.get("language", "")
                print(f"     · {name:<35} {org[:35]:<35} {email:<40} {lang}{tier_str}")
            if len(items) > 50:
                print(f"     … ({len(items) - 50} de plus)")

        # Non envoyés — cibles disponibles
        if unsent_docs:
            print(f"\n  💎 NON ENVOYÉS — {len(unsent_docs)} cibles disponibles")
            # Sort by tier then name
            def sort_key(d):
                t = d.get("tier")
                try:
                    t_val = int(t) if t else 99
                except (ValueError, TypeError):
                    t_val = 99
                return (t_val, d.get("name") or d.get("nom") or "")
            unsent_sorted = sorted(unsent_docs, key=sort_key)
            for d in unsent_sorted[:40]:
                name = d.get("nom") or d.get("name") or d.get("companyName") or "?"
                org = d.get("organization") or d.get("companyName") or d.get("firmName") or ""
                email = get_email(d)
                tier = d.get("tier", "")
                tier_str = f" [T{tier}]" if tier else ""
                lang = d.get("language", "")
                status = d.get("status", "")
                skip = d.get("skipOutreach", False)
                flag = " 🚫" if (status in ("blacklist_permanent", "blacklist") or skip) else ""
                print(f"     · {name:<35} {org[:35]:<35} {email:<40} {lang}{tier_str}{flag}")
            if len(unsent_docs) > 40:
                print(f"     … ({len(unsent_docs) - 40} de plus)")

        grand_total_sent += len(sent_docs)
        grand_total_unsent += len(unsent_docs)

    print(f"\n{'='*80}")
    print(f"=== GRAND TOTAL ===")
    print(f"   Envoyés cumul : {grand_total_sent}")
    print(f"   Disponibles   : {grand_total_unsent}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
