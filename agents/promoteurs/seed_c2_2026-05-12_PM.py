"""Seed mini-vague C2 — 5 cibles promoteurs ON 2026-05-12 PM."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/Users/yvesbarrette/Desktop/capitalnorvex-site")

from agents.shared import firestore_client as fs
from agents.promoteurs.outreach import queue_one

COLLECTION = "promoteurTargets"
AGENT_NAME = "claude_vague5_c2_2026-05-12"

TARGETS = [
    {
        "companyName": "The Pearl Group",
        "principalContact": "Jordan Pearl",
        "name": "Jordan Pearl",
        "title": "President (Pearl family, 3rd generation)",
        "email": "jordan@pearlgroup.ca",
        "website": "https://pearlgroup.ca",
        "city": "Toronto",
        "region": "ON", "language": "en",
        "tier": "Tier 1",
        "evidence": "Jordan Pearl = 3e génération président Pearl Group (founded 1973 by grandfather Martin Pearl, immigrant 1950s). Real estate commercial high-street Toronto, $400M+ transactions. Pattern {first} confirmé Hunter.",
        "score": 9,
        "predictive": True,
    },
    {
        "companyName": "Camrost Felcorp",
        "principalContact": "David Feldman",
        "name": "David Feldman",
        "title": "Founder, Chairman & CEO (Feldman family)",
        "email": "dfeldman@camrost.com",
        "website": "https://camrost.com",
        "city": "Toronto",
        "region": "ON", "language": "en",
        "tier": "Tier 1",
        "evidence": "David Feldman = founder Camrost Felcorp (1976), CEO/Chairman. Famille active : Angela Feldman EVP (épouse) + Joseph Feldman President COO (fils). 80+ buildings, 20,000+ résidences, 2M sf retail/office, 4 G$ projets actuels. Hunter ✅.",
        "score": 9,
        "predictive": False,
    },
    {
        "companyName": "Camrost Felcorp (famille)",
        "principalContact": "Joseph Feldman",
        "name": "Joseph Feldman",
        "title": "President & COO (Feldman family son)",
        "email": "jfeldman@camrost.com",
        "website": "https://camrost.com",
        "city": "Toronto",
        "region": "ON", "language": "en",
        "tier": "Tier 1",
        "evidence": "Joseph Feldman = fils David, President/COO Camrost Felcorp. Hunter ✅.",
        "score": 9,
        "predictive": False,
    },
    {
        "companyName": "Baz Group of Companies (ex-Marlin Spring)",
        "principalContact": "Benjamin Bakst",
        "name": "Benjamin Bakst",
        "title": "Chief Executive Officer & Co-Founder",
        "email": "bbakst@bazgroup.ca",
        "website": "https://bazgroup.ca",
        "city": "Toronto",
        "region": "ON", "language": "en",
        "tier": "Tier 1",
        "evidence": "Benjamin Bakst = CEO/Co-Founder Baz Group (ex-Marlin Spring, rebrand 2024 = 'BA' + 'Z' = BAkst + kAZarnovsky). Marlin Spring #1 2020 Growth List. Hunter ✅.",
        "score": 9,
        "predictive": False,
    },
    {
        "companyName": "Baz Group of Companies (ex-Marlin Spring)",
        "principalContact": "Elliot Kazarnovsky",
        "name": "Elliot Kazarnovsky",
        "title": "Chief Financial Officer & Co-Founder",
        "email": "ekazarnovsky@bazgroup.ca",
        "website": "https://bazgroup.ca",
        "city": "Toronto",
        "region": "ON", "language": "en",
        "tier": "Tier 1",
        "evidence": "Elliot Kazarnovsky = CFO/Co-Founder Baz Group (ex-Marlin Spring). Pattern {f}{last} confirmé Hunter via Benjamin Bakst.",
        "score": 9,
        "predictive": True,
    },
]


def _map_to_firestore(t: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "companyName": t["companyName"],
        "nom": t["companyName"],
        "principalContact": t["principalContact"],
        "name": t["name"],
        "title": t["title"],
        "city": t["city"],
        "ville": t["city"],
        "region": t["region"],
        "projectTypes": ["residential", "commercial", "mixed-use"],
        "website": t["website"],
        "email": t["email"],
        "publicContact": {"email": t["email"], "website": t["website"]},
        "contactInfo": {"email": t["email"], "website": t["website"]},
        "language": t["language"],
        "score": t["score"],
        "status": "pending_review",
        "tier": t["tier"],
        "evidence": t["evidence"],
        "discoveredAt": now,
        "discoveredBy": AGENT_NAME,
        "protectedFlag": False,
        "predictiveEmail": t.get("predictive", False),
    }


def main(dry: bool = False) -> None:
    existing = fs.query(COLLECTION, limit=2000)
    existing_emails = set()
    for p in existing:
        e = (p.get("email") or
             (p.get("contactInfo") or {}).get("email") or
             (p.get("publicContact") or {}).get("email") or "")
        if e:
            existing_emails.add(e.lower().strip())

    inserted = []
    for t in TARGETS:
        if t["email"].lower() in existing_emails:
            print(f"  [DOUBLON] {t['name']} — skip")
            continue
        if dry:
            print(f"  [DRY] {t['name']} ({t['email']})")
            continue
        doc = _map_to_firestore(t)
        doc_id = fs.create(COLLECTION, doc)
        inserted.append((doc_id, t))
        print(f"  ✅ {doc_id} — {t['name']} ({t['email']})")

    if dry or not inserted:
        return

    print(f"\n📥 Queue drafts ({len(inserted)})…")
    for doc_id, t in inserted:
        try:
            queue_one(doc_id, force=True)
        except Exception as e:
            print(f"  ❌ {t['name']}: {e}")


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
