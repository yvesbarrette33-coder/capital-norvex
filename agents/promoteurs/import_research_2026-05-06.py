"""Import de la recherche promoteurs 2026-05-06 (60 promoteurs) dans Firestore.

Source : data/promoters_research_2026-05-06.json
Cible  : collection promoteurTargets (dashboard Norvex Agents)
Dédup  : par companyName (case-insensitive)

Status à l'insertion : pending_review (Yves valide avant envoi).

Usage :
    cd ~/Desktop/capitalnorvex-site
    set -a && source ~/.capitalnorvex/.env && set +a
    python3 -m agents.promoteurs.import_research_2026-05-06
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..shared import firestore_client as fs

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JSON_FILE = os.path.join(ROOT, "data", "promoters_research_2026-05-06.json")
COLLECTION = "promoteurTargets"
AGENT_NAME = "claude_cowork_research_2026-05-06"


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _map_to_firestore(p: Dict[str, Any]) -> Dict[str, Any]:
    """Mappe une entrée recherche JSON → schéma promoteurTargets."""
    contact = p.get("contactInfo") or {}
    now = datetime.now(timezone.utc).isoformat()
    return {
        "companyName": p.get("companyName"),
        "principalContact": contact.get("contact_person") or p.get("name") or "",
        "name": p.get("name") or "",
        "city": p.get("city"),
        "region": p.get("region") or "QC",
        "subregion": p.get("subregion"),
        "projectTypes": p.get("projectTypes") or [],
        "projectTypesDetail": p.get("projectTypesDetail") or [],
        "website": contact.get("website") or "",
        "email": contact.get("email") or "",
        "phone": contact.get("phone") or "",
        "linkedin": contact.get("linkedin") or "",
        "recentProject": p.get("recentProjects") or "",
        "estimatedProjectValue": p.get("estimatedAnnualVolume"),
        "source": p.get("sourceUrl") or "",
        "evidence": p.get("notes") or "",
        "language": "fr",
        "score": p.get("score") or 5,
        "status": "pending_review",
        "tier": "auto",
        "discoveredAt": now,
        "discoveredBy": AGENT_NAME,
        "protectedFlag": False,
    }


def main(dry_run: bool = False) -> Dict[str, Any]:
    print(f"📂 Lecture {JSON_FILE}")
    with open(JSON_FILE, encoding="utf-8") as f:
        data = json.load(f)
    candidates: List[Dict[str, Any]] = data.get("promoters") or []
    print(f"📥 Candidats à importer : {len(candidates)}")

    print(f"🔎 Lecture des existants ({COLLECTION})…")
    existing = fs.query(COLLECTION, limit=2000)
    existing_names = {_norm(p.get("companyName")) for p in existing}
    print(f"   ↳ {len(existing)} entrées déjà en base")

    duplicates: List[str] = []
    new_entries: List[Dict[str, Any]] = []
    for p in candidates:
        if _norm(p.get("companyName")) in existing_names:
            duplicates.append(p.get("companyName"))
        else:
            new_entries.append(p)

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
        for p in new_entries:
            doc = _map_to_firestore(p)
            doc_id = fs.create(COLLECTION, doc)
            inserted.append({"id": doc_id, "companyName": doc["companyName"]})
            print(f"   ✅ {doc_id} — {doc['companyName']} (score {doc['score']})")

        # Audit log
        fs.audit_log(
            agent=AGENT_NAME,
            action="bulk_import_research",
            target_id=None,
            details={
                "source_file": "data/promoters_research_2026-05-06.json",
                "candidates_count": len(candidates),
                "duplicates_count": len(duplicates),
                "inserted_count": len(inserted),
            },
        )

    print()
    print("─" * 60)
    print(f"✅ TERMINÉ — {len(inserted)} insérés / {len(duplicates)} doublons / {len(candidates)} candidats")
    print("─" * 60)
    return {
        "candidates": len(candidates),
        "duplicates": len(duplicates),
        "inserted": len(inserted),
    }


if __name__ == "__main__":
    import sys
    dry = "--dry" in sys.argv
    main(dry_run=dry)
