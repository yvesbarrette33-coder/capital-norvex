"""Audit ON v2 — détails statuts, leads chauds, candidats 2e touch.

Liste:
- Pending yves approval (qui est-ce ?)
- Blacklisted (qui ?)
- Sent : par date + signaux d'intérêt (opens/clicks SendGrid si présents)
- Candidats 2e touch (>14 jours depuis 1er envoi, ouvert/cliqué)
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/Users/yvesbarrette/Desktop/capitalnorvex-site")

from agents.shared.firestore_client import query


def get_email(doc: dict) -> str | None:
    ci = doc.get("contactInfo") or {}
    pc = doc.get("publicContact") or {}
    return doc.get("email") or ci.get("email") or pc.get("email")


def fmt_dt(v) -> str:
    if not v:
        return ""
    try:
        if hasattr(v, "isoformat"):
            return v.isoformat()[:16]
        return str(v)[:16]
    except Exception:
        return str(v)[:16]


def main() -> None:
    docs = query("promoteurTargets")
    on_docs = [d for d in docs if (d.get("region") or "").upper() in ("ON", "ONTARIO")]

    pending = [d for d in on_docs if d.get("status") == "pending_yves_approval"]
    blacklist = [d for d in on_docs if d.get("skipOutreach") or d.get("status") == "blacklist_permanent"]
    sent = [d for d in on_docs if d.get("status") == "sent"]

    print(f"=== PENDING YVES APPROVAL ({len(pending)}) ===")
    for d in pending:
        print(f"  - {d.get('nom') or d.get('companyName')} — {get_email(d)} — tier={d.get('tier','?')}")
        print(f"      created: {fmt_dt(d.get('createdAt'))}")

    print(f"\n=== BLACKLISTED ({len(blacklist)}) ===")
    for d in blacklist:
        print(f"  - {d.get('nom') or d.get('companyName')} — {get_email(d)} — reason: {d.get('blacklistReason','?')}")

    print(f"\n=== TIER 1 — TOUS ({len([d for d in on_docs if d.get('tier')=='Tier 1'])}) ===")
    tier1 = [d for d in on_docs if d.get("tier") == "Tier 1"]
    for d in tier1:
        nom = d.get("nom") or d.get("companyName")
        email = get_email(d)
        status = d.get("status")
        sent_at = fmt_dt(d.get("sentAt") or d.get("lastSentAt"))
        opens = d.get("opens", 0) or d.get("openCount", 0)
        clicks = d.get("clicks", 0) or d.get("clickCount", 0)
        print(f"  - {nom} — {email}")
        print(f"      status={status}, sent={sent_at}, opens={opens}, clicks={clicks}")

    print(f"\n=== CANDIDATS 2e TOUCH (sent >14j, opens>=2 OU clicks>=1) ===")
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    candidates_2e = []
    for d in sent:
        sent_at = d.get("sentAt") or d.get("lastSentAt")
        opens = d.get("opens", 0) or d.get("openCount", 0)
        clicks = d.get("clicks", 0) or d.get("clickCount", 0)
        if not sent_at:
            continue
        try:
            sa = sent_at if hasattr(sent_at, "tzinfo") else datetime.fromisoformat(str(sent_at).replace("Z", "+00:00"))
            if sa.tzinfo is None:
                sa = sa.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if sa < cutoff and (opens >= 2 or clicks >= 1):
            candidates_2e.append((d, sa, opens, clicks))

    candidates_2e.sort(key=lambda t: (t[3], t[2]), reverse=True)
    for d, sa, o, c in candidates_2e[:20]:
        nom = d.get("nom") or d.get("companyName")
        print(f"  - {nom} — {get_email(d)} — sent {sa.date()} — opens={o} clicks={c}")

    if not candidates_2e:
        print("  (aucun lead chaud >14j pour le moment)")

    print(f"\n=== SENT — derniers 7 jours, tous (pas Tier 1) ===")
    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent = []
    for d in sent:
        if d.get("tier") == "Tier 1":
            continue
        sent_at = d.get("sentAt") or d.get("lastSentAt")
        if not sent_at:
            continue
        try:
            sa = sent_at if hasattr(sent_at, "tzinfo") else datetime.fromisoformat(str(sent_at).replace("Z", "+00:00"))
            if sa.tzinfo is None:
                sa = sa.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if sa >= recent_cutoff:
            recent.append((d, sa))
    recent.sort(key=lambda t: t[1], reverse=True)
    print(f"  (total {len(recent)} envoyés derniers 7j)")
    for d, sa in recent[:15]:
        print(f"  - {d.get('nom') or d.get('companyName')} — {sa.date()} — opens={d.get('opens',0) or d.get('openCount',0)} clicks={d.get('clicks',0) or d.get('clickCount',0)}")


if __name__ == "__main__":
    main()
