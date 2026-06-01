"""Import des courtiers HYPOTHÉCAIRES commerciaux 2026-05-06 dans Firestore.

Source : data/research-2026-05-06/seed_mortgage_brokers_2026-05-06.json
Cible  : collection brokers (dashboard Norvex Agents)
Dédup  : par (name + firmName) case-insensitive contre l'existant
Filtre : EXCLUT tout courtier immobilier de vente (RE/MAX, Sotheby's, Royal LePage,
         Engel & Völkers, Coldwell, Century 21, Berkshire Hathaway HomeServices)

Status à l'insertion : cold (jamais contacté).

Usage :
    cd ~/Desktop/capitalnorvex-site
    set -a && source ~/.capitalnorvex/.env && set +a
    python3 -m agents.courtiers.import_research_2026-05-06 --dry
    python3 -m agents.courtiers.import_research_2026-05-06
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..shared import firestore_client as fs

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JSON_FILE = os.path.join(
    ROOT, "data", "research-2026-05-06", "seed_mortgage_brokers_2026-05-06.json"
)
COLLECTION = "brokers"
AGENT_NAME = "claude_cowork_research_2026-05-06"

# Garde-fou : firmes de courtage IMMOBILIER (vente) — à exclure
SALES_BROKERAGE_KEYWORDS = (
    "re/max", "remax", "sotheby's", "sotheby", "royal lepage", "engel & völkers",
    "engel volkers", "coldwell", "century 21", "century21", "berkshire hathaway",
    "via capitale", "keller williams", "la capitale immobilier",
)


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _is_sales_broker(b: Dict[str, Any]) -> bool:
    """Heuristique : exclut les courtiers immobiliers de vente."""
    firm = _norm(b.get("firmName"))
    if not firm:
        return False
    for kw in SALES_BROKERAGE_KEYWORDS:
        if kw in firm:
            return True
    return False


def _map_to_firestore(b: Dict[str, Any]) -> Dict[str, Any]:
    """Mappe une entrée recherche JSON → schéma brokers."""
    pc = b.get("publicContact") or {}
    deal = b.get("typicalDealSize") or {}
    now = datetime.now(timezone.utc).isoformat()
    return {
        "name": b.get("name"),
        "firmName": b.get("firmName"),
        "title": b.get("title") or "",
        "licenseNumber": b.get("licenseNumber") or "",
        "region": b.get("region") or "QC",
        "city": b.get("city") or "",
        "specialty": b.get("specialty") or [],
        "typicalDealSize": deal,
        "relationshipStatus": b.get("relationshipStatus") or "cold",
        "dealsReceived": b.get("dealsReceived") or 0,
        "dealsClosed": b.get("dealsClosed") or 0,
        "preferredChannel": b.get("preferredChannel") or "email",
        "email": pc.get("email") or "",
        "phone": pc.get("phone") or "",
        "linkedin": pc.get("linkedin") or "",
        "profileUrl": pc.get("profile_url") or "",
        "sourceUrl": b.get("sourceUrl") or "",
        "notes": b.get("notes") or "",
        "language": "fr",
        "status": "pending_review",
        "discoveredAt": now,
        "discoveredBy": AGENT_NAME,
        "protectedFlag": False,
    }


def main(dry_run: bool = False) -> Dict[str, Any]:
    print(f"📂 Lecture {JSON_FILE}")
    with open(JSON_FILE, encoding="utf-8") as f:
        data = json.load(f)
    candidates: List[Dict[str, Any]] = data.get("brokers") or []
    print(f"📥 Candidats à importer : {len(candidates)}")

    # Filtre garde-fou : exclut les courtiers de vente immobilière
    sales_excluded = [c for c in candidates if _is_sales_broker(c)]
    candidates = [c for c in candidates if not _is_sales_broker(c)]
    if sales_excluded:
        print(f"🚫 Courtiers de VENTE écartés (garde-fou) : {len(sales_excluded)}")
        for c in sales_excluded:
            print(f"     - {c.get('name')} / {c.get('firmName')}")

    print(f"🔎 Lecture des existants ({COLLECTION})…")
    existing = fs.query(COLLECTION, limit=2000)
    existing_keys = {
        (_norm(p.get("name")), _norm(p.get("firmName")))
        for p in existing
    }
    print(f"   ↳ {len(existing)} entrées déjà en base")

    duplicates: List[str] = []
    new_entries: List[Dict[str, Any]] = []
    for b in candidates:
        key = (_norm(b.get("name")), _norm(b.get("firmName")))
        if key in existing_keys:
            duplicates.append(f"{b.get('name')} ({b.get('firmName')})")
        else:
            new_entries.append(b)

    print()
    print(f"♻️  Doublons écartés : {len(duplicates)}")
    for d in duplicates:
        print(f"     - {d}")
    print()
    print(f"🆕 Nouveaux à insérer : {len(new_entries)}")

    inserted: List[Dict[str, Any]] = []
    if not dry_run:
        print()
        print(f"💾 Insertion dans Firestore ({COLLECTION})…")
        for b in new_entries:
            doc = _map_to_firestore(b)
            doc_id = fs.create(COLLECTION, doc)
            inserted.append({"id": doc_id, "name": doc["name"], "firm": doc["firmName"]})
            print(f"   ✅ {doc_id} — {doc['name']} ({doc['firmName']})")

        fs.audit_log(
            agent=AGENT_NAME,
            action="bulk_import_research_brokers",
            target_id=None,
            details={
                "source_file": "data/research-2026-05-06/seed_mortgage_brokers_2026-05-06.json",
                "candidates_count": len(candidates) + len(sales_excluded),
                "sales_excluded_count": len(sales_excluded),
                "duplicates_count": len(duplicates),
                "inserted_count": len(inserted),
            },
        )

    print()
    print("─" * 60)
    print(
        f"✅ TERMINÉ — {len(inserted)} insérés / {len(duplicates)} doublons / "
        f"{len(sales_excluded)} courtiers vente écartés"
    )
    print("─" * 60)
    return {
        "candidates": len(candidates) + len(sales_excluded),
        "sales_excluded": len(sales_excluded),
        "duplicates": len(duplicates),
        "inserted": len(inserted),
    }


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    main(dry_run=dry)
