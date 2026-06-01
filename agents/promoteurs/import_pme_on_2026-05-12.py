"""Import des 9 PME promoteurs ON 2026-05-12 dans Firestore.

Source : audit + WebSearch + Hunter (2026-05-12 PM)
Cible  : collection promoteurTargets
Dédup  : par companyName (case-insensitive)
Status : pending_review (Yves valide via dashboard avant envoi)
Language : en (ON par défaut)
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/Users/yvesbarrette/Desktop/capitalnorvex-site")

from agents.shared import firestore_client as fs

COLLECTION = "promoteurTargets"
AGENT_NAME = "claude_pme_on_research_2026-05-12"

# Cibles confirmées Hunter, contacts owner/president/VP prioritaires
TARGETS = [
    # TOP 4 — Owners/Presidents directs
    {
        "companyName": "Elite Developments",
        "principalContact": "Pankaj Chopra",
        "name": "Pankaj Chopra",
        "title": "Owner",
        "email": "pchopra@elitedevelopments.ca",
        "website": "https://elitedevelopments.ca",
        "city": "Hamilton",
        "tier": "Tier 2",
        "evidence": "Famille Chopra propriétaires; Sahaj Chopra VP, Surinder Mahajan Managing Partner. PME mid-market Hamilton. Hunter pattern {f}{last}.",
        "score": 8,
    },
    {
        "companyName": "Coletara Development",
        "principalContact": "Paul Kemper",
        "name": "Paul Kemper",
        "title": "President",
        "email": "pkemper@coletara.com",
        "website": "https://coletara.com",
        "city": "Hamilton",
        "tier": "Tier 2",
        "evidence": "Boutique developer Hamilton, mid-rise/townhouse. Michael Krasic VP Development. Hunter pattern {f}{last}.",
        "score": 8,
    },
    {
        "companyName": "Antilia Homes",
        "principalContact": "Ravi Shanghavi",
        "name": "Ravi Shanghavi",
        "title": "President",
        "email": "ravi@antiliahomes.com",
        "website": "https://antiliahomes.com",
        "city": "Ottawa",
        "tier": "Tier 2",
        "evidence": "Boutique luxury Ottawa, custom homes. Purvang Sheth project coord. Hunter pattern {first}.",
        "score": 8,
    },
    {
        "companyName": "TCU Development Corporation",
        "principalContact": "Gabriel Gauthier",
        "name": "Gabriel Gauthier",
        "title": "Vice President Finance",
        "email": "g.gauthier@tcudevcorp.com",
        "website": "https://tcudevcorp.com",
        "city": "Ottawa",
        "tier": "Tier 2",
        "evidence": "Privé depuis 2010, fondateurs Mike Corneau + Billy Triantafilos. Équipe finance francophone (Tessier, Gauthier, Mhimzat, Martinez). Strategic development + investment management.",
        "score": 9,
    },
    # Mid-tier (Yves veut visibilité même si trop gros)
    {
        "companyName": "Pinemount Developments",
        "principalContact": "Eli Turk",
        "name": "Eli Turk",
        "title": "CPA",
        "email": "eliturk@pinemount.ca",
        "website": "https://pinemount.ca",
        "city": "Hamilton",
        "tier": "Tier 3",
        "evidence": "Boutique Hamilton. Petit team. Hunter pattern {first}{last}.",
        "score": 7,
    },
    {
        "companyName": "Losani Homes",
        "principalContact": "Dean Campbell",
        "name": "Dean Campbell",
        "title": "Vice President Residential Operations",
        "email": "dcampbell@losanihomes.com",
        "website": "https://losanihomes.com",
        "city": "Hamilton",
        "tier": "Tier 2",
        "evidence": "Grand builder Hamilton/Niagara. Possiblement trop gros pour fourchette 2,5-25 M$, mais visibilité valable selon stratégie 12 mai. Équipe finance identifiée.",
        "score": 7,
    },
    {
        "companyName": "Regional Group",
        "principalContact": "Sachin Anand",
        "name": "Sachin Anand",
        "title": "Vice President of Acquisitions",
        "email": "sanand@regionalgroup.com",
        "website": "https://regionalgroup.com",
        "city": "Ottawa",
        "tier": "Tier 2",
        "evidence": "Depuis 1958, 2M sf commercial + résidentiel Ottawa. Probablement trop gros / bancaire, mais visibilité + possibilité référencement projets plus petits.",
        "score": 7,
    },
    {
        "companyName": "CLV Group",
        "principalContact": "Chris Clarke",
        "name": "Chris Clarke",
        "title": "Chief Financial Officer",
        "email": "chris.clarke@clvgroup.com",
        "website": "https://clvgroup.com",
        "city": "Ottawa",
        "tier": "Tier 2",
        "evidence": "7,6M sf résidentiel Ottawa. Fonds institutionnel. Trop gros direct mais visibilité + référencements possibles.",
        "score": 6,
    },
    {
        "companyName": "York Developments",
        "principalContact": "Said Meddaoui",
        "name": "Said Meddaoui",
        "title": "Vice President of Finance",
        "email": "said.meddaoui@yorkdev.ca",
        "website": "https://yorkdev.ca",
        "city": "London",
        "tier": "Tier 2",
        "evidence": "Depuis 1996, 1M sf commercial + résidentiel Ontario, basé London. Famille. Frontière entre PME et méga, bon candidat visibilité.",
        "score": 7,
    },
]


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _map_to_firestore(t: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "companyName": t["companyName"],
        "nom": t["companyName"],  # alias utilisé par certains dashboards
        "principalContact": t["principalContact"],
        "name": t["name"],
        "title": t["title"],
        "city": t["city"],
        "ville": t["city"],  # alias
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
    }


def main(dry_run: bool = False) -> None:
    print(f"🔎 Lecture {COLLECTION} existants…")
    existing = fs.query(COLLECTION, limit=2000)
    existing_names = {_norm(p.get("companyName") or p.get("nom")) for p in existing}
    existing_emails = set()
    for p in existing:
        e = p.get("email") or (p.get("contactInfo") or {}).get("email") or (p.get("publicContact") or {}).get("email")
        if e:
            existing_emails.add(e.lower().strip())

    duplicates = []
    new_entries = []
    for t in TARGETS:
        if _norm(t["companyName"]) in existing_names or t["email"].lower() in existing_emails:
            duplicates.append(t["companyName"])
        else:
            new_entries.append(t)

    print(f"♻️  Doublons écartés : {len(duplicates)}")
    for d in duplicates:
        print(f"     - {d}")
    print(f"🆕 Nouveaux à insérer : {len(new_entries)}")

    if dry_run:
        print("(dry-run, pas d'insertion)")
        return

    print(f"\n💾 Insertion dans Firestore ({COLLECTION})…")
    for t in new_entries:
        doc = _map_to_firestore(t)
        doc_id = fs.create(COLLECTION, doc)
        print(f"   ✅ {doc_id} — {t['companyName']} ({t['name']}, {t['title']})")

    print(f"\n✅ Import terminé : {len(new_entries)} cibles ajoutées avec status=pending_review.")


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    main(dry_run=dry)
