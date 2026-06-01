"""Importe une liste de courtiers fournie par Yves dans Firestore (`brokers`).

Format JSON attendu (voir data/yves_initial_brokers.json) :
  {"groups": [{"firmName": "...", "specialty": [...], "brokers": [{"name", "email", ...}]}]}

Anti-doublon : on cherche un broker existant par email (lowercase). Si trouvé,
on met à jour les champs vides ; on ne touche pas aux statuts ni aux deals.
Si introuvable, on crée un nouveau document.

Usage:
    python -m agents.courtiers.import_list agents/courtiers/data/yves_initial_brokers.json
    python -m agents.courtiers.import_list agents/courtiers/data/yves_initial_brokers.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..shared import firestore_client as fs

AGENT_NAME = "courtiers_import_list"
COLLECTION = "brokers"


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _find_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Cherche un courtier par email (lowercase)."""
    if not email:
        return None
    rows = fs.query(COLLECTION, filters=[("email", "==", email)], limit=1)
    return rows[0] if rows else None


def _build_broker_doc(
    name: str,
    email: str,
    firm_name: str,
    specialty: List[str],
    region: str,
    language: str,
    notes: str,
) -> Dict[str, Any]:
    return {
        "name": name,
        "email": email,
        "firmName": firm_name,
        "specialty": specialty,
        "region": region,
        "language": language,
        "relationshipStatus": "cold",
        "dealsReceived": 0,
        "dealsClosed": 0,
        "source": "yves_initial_list",
        "notes": notes,
        "importedAt": datetime.now(timezone.utc).isoformat(),
        "importedBy": AGENT_NAME,
    }


def import_file(path: str, dry_run: bool = False) -> Dict[str, int]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("_meta", {})
    default_lang = meta.get("language_default", "fr")
    default_region = meta.get("region_default", "QC")

    counts = {"created": 0, "updated": 0, "skipped": 0}

    for group in data.get("groups", []):
        group_firm = group.get("firmName", "")
        group_specialty = group.get("specialty", [])
        group_note = group.get("firmNote", "")

        for b in group.get("brokers", []):
            email = _normalize_email(b.get("email", ""))
            name = (b.get("name") or "").strip()
            firm = b.get("firmName") or group_firm
            specialty = b.get("specialty") or group_specialty
            region = b.get("region") or default_region
            language = b.get("language") or default_lang
            notes = b.get("notes") or group_note

            if not email or "@" not in email or not name:
                print(f"  ⚠️  Skip (email/nom manquant) : {b}")
                counts["skipped"] += 1
                continue

            existing = _find_by_email(email)
            doc = _build_broker_doc(name, email, firm, specialty, region, language, notes)

            if existing:
                if dry_run:
                    print(f"  ↻ [dry-run] UPDATE {email} → {firm}")
                else:
                    # On garde relationshipStatus / dealsReceived / dealsClosed existants
                    safe_update = {
                        k: v for k, v in doc.items()
                        if k not in {"relationshipStatus", "dealsReceived", "dealsClosed"}
                    }
                    fs.update(COLLECTION, existing["id"], safe_update)
                    print(f"  ↻ UPDATE {email} → {firm}")
                counts["updated"] += 1
            else:
                if dry_run:
                    print(f"  + [dry-run] CREATE {email} ({name}, {firm})")
                else:
                    new_id = fs.create(COLLECTION, doc)
                    print(f"  + CREATE {email} ({name}, {firm}) → {new_id}")
                counts["created"] += 1

    if not dry_run:
        fs.audit_log(
            agent=AGENT_NAME,
            action="import_brokers",
            target_type="brokers",
            target_id=os.path.basename(path),
            details={"counts": counts, "source_file": path},
        )

    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", help="Chemin vers le JSON à importer")
    parser.add_argument("--dry-run", action="store_true", help="N'écrit rien, affiche seulement")
    args = parser.parse_args()

    if not os.path.exists(args.json_path):
        print(f"❌ Fichier introuvable : {args.json_path}")
        return 1

    print(f"📥 Import courtiers depuis : {args.json_path}")
    if args.dry_run:
        print("🔍 MODE DRY-RUN — aucune écriture Firestore\n")
    else:
        print()

    counts = import_file(args.json_path, dry_run=args.dry_run)
    print(f"\n✅ Terminé : {counts['created']} créés · {counts['updated']} mis à jour · {counts['skipped']} ignorés")
    return 0


if __name__ == "__main__":
    sys.exit(main())
