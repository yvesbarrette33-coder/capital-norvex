"""Seed Vague #5 B+C — 10 cibles familles promoteurs 2026-05-12 PM."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/Users/yvesbarrette/Desktop/capitalnorvex-site")

from agents.shared import firestore_client as fs
from agents.promoteurs.outreach import queue_one

COLLECTION = "promoteurTargets"
AGENT_NAME = "claude_vague5_bc_2026-05-12"

TARGETS = [
    # === B - Pomerleau (QC / FR) ===
    {
        "companyName": "Pomerleau Construction",
        "principalContact": "Philippe Adam",
        "name": "Philippe Adam",
        "title": "Chief Executive Officer",
        "email": "philippe.adam@pomerleau.ca",
        "website": "https://pomerleau.ca",
        "city": "Saint-Georges-de-Beauce",
        "region": "QC", "language": "fr",
        "tier": "Tier 1",
        "evidence": "Pomerleau Construction fondée 1966 par Hervé + Laurette Pomerleau ($25k, 5 employés → 4000 emp, ~2 G$ revenu). Famille Pomerleau actuelle : Pierre (PDG 1997-2023), Francis, Élaine, Gaby. Philippe Adam = CEO depuis 2023.",
        "score": 9,
        "predictive": False,
    },
    {
        "companyName": "Pomerleau Construction (famille)",
        "principalContact": "Pierre Pomerleau",
        "name": "Pierre Pomerleau",
        "title": "Président du conseil, famille fondatrice",
        "email": "pierre.pomerleau@pomerleau.ca",
        "website": "https://pomerleau.ca",
        "city": "Saint-Georges-de-Beauce",
        "region": "QC", "language": "fr",
        "tier": "Tier 1",
        "evidence": "Pierre Pomerleau = fils Hervé, PDG 1997-2023, détient '% très significatif' actions avec Francis. Pattern {first}.{last} confirmé Hunter.",
        "score": 9,
        "predictive": True,
    },
    {
        "companyName": "Pomerleau Construction (famille)",
        "principalContact": "Francis Pomerleau",
        "name": "Francis Pomerleau",
        "title": "Famille fondatrice (frère de Pierre)",
        "email": "francis.pomerleau@pomerleau.ca",
        "website": "https://pomerleau.ca",
        "city": "Saint-Georges-de-Beauce",
        "region": "QC", "language": "fr",
        "tier": "Tier 1",
        "evidence": "Francis Pomerleau = frère Pierre, co-actionnaire majeur. Pattern {first}.{last} confirmé.",
        "score": 8,
        "predictive": True,
    },
    # === C - Greenpark famille Baldassarra (ON / EN) ===
    {
        "companyName": "Greenpark Group",
        "principalContact": "Carlo Baldassarra",
        "name": "Carlo Baldassarra",
        "title": "Founder & CEO (Baldassarra family)",
        "email": "carlo@greenparkgroup.ca",
        "website": "https://greenparkgroup.ca",
        "city": "Vaughan",
        "region": "ON", "language": "en",
        "tier": "Tier 1",
        "evidence": "Carlo Baldassarra = Founder/CEO Greenpark (immigrant italien 1958, founders avec Jack Wine + Phillip Rechtsman). 20,000+ unités résidentielles. Famille = 3 fils Mauro/Armando/Michael (senior execs).",
        "score": 9,
        "predictive": False,
    },
    {
        "companyName": "Greenpark Group (famille)",
        "principalContact": "Mauro Baldassarra",
        "name": "Mauro Baldassarra",
        "title": "Senior Executive (Baldassarra family son)",
        "email": "mauro@greenparkgroup.ca",
        "website": "https://greenparkgroup.ca",
        "city": "Vaughan",
        "region": "ON", "language": "en",
        "tier": "Tier 2",
        "evidence": "Mauro Baldassarra = fils Carlo, senior exec Greenpark. Pattern {first} confirmé Hunter (carlo@greenparkgroup.ca).",
        "score": 8,
        "predictive": True,
    },
    {
        "companyName": "Greenpark Group (famille)",
        "principalContact": "Armando Baldassarra",
        "name": "Armando Baldassarra",
        "title": "Senior Executive (Baldassarra family son)",
        "email": "armando@greenparkgroup.ca",
        "website": "https://greenparkgroup.ca",
        "city": "Vaughan",
        "region": "ON", "language": "en",
        "tier": "Tier 2",
        "evidence": "Armando Baldassarra = fils Carlo, senior exec Greenpark. Pattern {first} confirmé.",
        "score": 8,
        "predictive": True,
    },
    {
        "companyName": "Greenpark Group (famille)",
        "principalContact": "Michael Baldassarra",
        "name": "Michael Baldassarra",
        "title": "Senior Executive (Baldassarra family son)",
        "email": "michael@greenparkgroup.ca",
        "website": "https://greenparkgroup.ca",
        "city": "Vaughan",
        "region": "ON", "language": "en",
        "tier": "Tier 2",
        "evidence": "Michael Baldassarra = fils Carlo, senior exec Greenpark. Pattern {first} confirmé.",
        "score": 8,
        "predictive": True,
    },
    # === C - Empire Communities famille Guizzetti + Golini (ON / EN) ===
    {
        "companyName": "Empire Communities (famille Guizzetti)",
        "principalContact": "Andrew Guizzetti",
        "name": "Andrew Guizzetti",
        "title": "Co-Chief Executive Officer (Guizzetti family)",
        "email": "aguizzetti@empirecommunities.com",
        "website": "https://empirecommunities.com",
        "city": "Vaughan",
        "region": "ON", "language": "en",
        "tier": "Tier 1",
        "evidence": "Andrew Guizzetti = Co-CEO/Co-Founder Empire Communities (1993). Frère Daniel Guizzetti = CEO Emeritus. Famille Guizzetti + Golini, partenariat depuis le père Santo Guizzetti (York Excavating). 35,000+ maisons/condos en 30 ans. Pattern {f}{last} confirmé Hunter.",
        "score": 9,
        "predictive": True,
    },
    {
        "companyName": "Empire Communities (famille Guizzetti)",
        "principalContact": "Daniel Guizzetti",
        "name": "Daniel Guizzetti",
        "title": "Co-Founder & CEO Emeritus (Guizzetti family)",
        "email": "dguizzetti@empirecommunities.com",
        "website": "https://empirecommunities.com",
        "city": "Vaughan",
        "region": "ON", "language": "en",
        "tier": "Tier 1",
        "evidence": "Daniel Guizzetti = frère Andrew, Co-Founder Empire, CEO Emeritus. Pattern {f}{last} confirmé.",
        "score": 9,
        "predictive": True,
    },
    {
        "companyName": "Empire Communities (famille Golini)",
        "principalContact": "Paul Golini Jr.",
        "name": "Paul Golini Jr.",
        "title": "Co-Founder & Executive Chairman (Golini family)",
        "email": "pgolini@empirecommunities.com",
        "website": "https://empirecommunities.com",
        "city": "Vaughan",
        "region": "ON", "language": "en",
        "tier": "Tier 1",
        "evidence": "Paul Golini Jr. = Co-Founder Empire avec Guizzetti, Executive Chairman. Partenariat familial historique avec les Guizzetti. Pattern {f}{last} confirmé.",
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
