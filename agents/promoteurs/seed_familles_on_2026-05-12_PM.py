"""Seed 7 cibles promoteurs ON familles 2026-05-12 PM + queue drafts.

Vague #4 du plan séquentiel — familles promoteurs ON.
- Tridel (DelZotto)
- Geranium (Feiner ×2)
- Mizrahi
- Easton's / Gupta Group (×2)
- Cortel Group (Cortellucci)
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/Users/yvesbarrette/Desktop/capitalnorvex-site")

from agents.shared import firestore_client as fs
from agents.promoteurs.outreach import queue_one

COLLECTION = "promoteurTargets"
AGENT_NAME = "claude_pme_on_familles_2026-05-12"

TARGETS = [
    {
        "companyName": "Tridel",
        "principalContact": "Andrew DelZotto",
        "name": "Andrew DelZotto",
        "title": "Vice President of Business Development (DelZotto family)",
        "email": "adelzotto@tridel.com",
        "website": "https://tridel.com",
        "city": "Toronto",
        "tier": "Tier 1",
        "evidence": "Famille DelZotto founders (Jack 1934, fils Angelo/Elvio/Leo = 'Tri'-del). Andrew = fils d'Angelo, VP Business Dev actif. Hunter pattern {f}{last}.",
        "score": 9,
        "predictive": False,
    },
    {
        "companyName": "Geranium Homes",
        "principalContact": "Boaz Feiner",
        "name": "Boaz Feiner",
        "title": "President",
        "email": "boazf@geranium.com",
        "website": "https://geranium.com",
        "city": "Markham",
        "tier": "Tier 1",
        "evidence": "Geranium fondée 1977, 8000+ maisons ON. Boaz Feiner = Président. Barry Feiner = Partner (famille). Pattern {first}{l} confirmé Hunter via 20+ employés.",
        "score": 9,
        "predictive": True,
    },
    {
        "companyName": "Geranium Homes",
        "principalContact": "Barry Feiner",
        "name": "Barry Feiner",
        "title": "Partner (Feiner family)",
        "email": "barryf@geranium.com",
        "website": "https://geranium.com",
        "city": "Markham",
        "tier": "Tier 2",
        "evidence": "Barry Feiner = Partner Geranium, famille Feiner. Confirmé Hunter.",
        "score": 8,
        "predictive": False,
    },
    {
        "companyName": "Mizrahi Developments",
        "principalContact": "Sam Mizrahi",
        "name": "Sam Mizrahi",
        "title": "Founder & President",
        "email": "sam@mizrahidevelopments.ca",
        "website": "https://mizrahidevelopments.ca",
        "city": "Toronto",
        "tier": "Tier 1",
        "evidence": "Sam Mizrahi = founder Mizrahi Developments (2008). Développe The One (85 étages Yonge/Bloor), 133 Hazelton, 181 Davenport, 128 Hazelton, etc. Pattern {first} confirmé Hunter.",
        "score": 9,
        "predictive": True,
    },
    {
        "companyName": "Easton's Group of Hotels (Gupta Group)",
        "principalContact": "Reetu Gupta",
        "name": "Reetu Gupta",
        "title": "President, CEO & Co-Chair (Gupta family)",
        "email": "reetu.gupta@eastonsgroup.com",
        "website": "https://eastonsgroup.com",
        "city": "Toronto",
        "tier": "Tier 1",
        "evidence": "Reetu Gupta = fille Steve Gupta (patriarche), CEO+President+Co-Chair Easton's Group of Hotels (hôtellerie + immobilier mixte usage). Pattern {first}.{last} confirmé Hunter sur 20 employés.",
        "score": 9,
        "predictive": True,
    },
    {
        "companyName": "Easton's Group of Hotels (Gupta Group)",
        "principalContact": "Rashmi Gupta",
        "name": "Rashmi Gupta",
        "title": "Senior Vice President (Gupta family)",
        "email": "rgupta@eastonsgroup.com",
        "website": "https://eastonsgroup.com",
        "city": "Toronto",
        "tier": "Tier 2",
        "evidence": "Rashmi Gupta = famille Gupta, Senior VP Easton's Group. Confirmé Hunter.",
        "score": 8,
        "predictive": False,
    },
    {
        "companyName": "Cortel Group",
        "principalContact": "Mario Cortellucci",
        "name": "Mario Cortellucci",
        "title": "Founder & Principal (Cortellucci family)",
        "email": "mario.cortellucci@cortelgroup.com",
        "website": "https://cortelgroup.com",
        "city": "Vaughan",
        "tier": "Tier 1",
        "evidence": "Mario Cortellucci = founder famille Cortellucci. Cortel Group développe résidentiel/commercial York Region. Pattern {first}.{last} confirmé Hunter via Anthony Cortellucci.",
        "score": 9,
        "predictive": True,
    },
]


def _norm(s: str) -> str:
    return (s or "").strip().lower()


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
        "region": "ON",
        "projectTypes": ["residential", "commercial", "mixed-use"],
        "website": t["website"],
        "email": t["email"],
        "publicContact": {"email": t["email"], "website": t["website"]},
        "contactInfo": {"email": t["email"], "website": t["website"]},
        "language": "en",
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
    print(f"🔎 Lecture {COLLECTION}…")
    existing = fs.query(COLLECTION, limit=2000)
    existing_emails = set()
    for p in existing:
        e = (p.get("email") or
             (p.get("contactInfo") or {}).get("email") or
             (p.get("publicContact") or {}).get("email") or "")
        if e:
            existing_emails.add(e.lower().strip())

    inserted_ids = []
    for t in TARGETS:
        if t["email"].lower() in existing_emails:
            print(f"  [DOUBLON email] {t['name']} — skip")
            continue
        doc = _map_to_firestore(t)
        if dry:
            print(f"  [DRY] {t['name']} ({t['email']})")
            continue
        doc_id = fs.create(COLLECTION, doc)
        inserted_ids.append((doc_id, t))
        print(f"  ✅ {doc_id} — {t['name']} ({t['email']})")

    if dry or not inserted_ids:
        return

    print(f"\n📥 Queue drafts ({len(inserted_ids)})…")
    for doc_id, t in inserted_ids:
        try:
            queue_one(doc_id, force=True)
        except Exception as e:
            print(f"  ❌ queue {t['name']}: {e}")


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
