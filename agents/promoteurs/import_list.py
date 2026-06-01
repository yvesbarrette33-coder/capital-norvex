"""Importe une liste de promoteurs/entrepreneurs fournie par Yves dans
Firestore (`promoteurTargets`).

Format JSON attendu (voir data/yves_initial_promoteurs.json) :
  {"groups": [{"category": "...", "promoteurs": [{"companyName", "principalContact", "email", ...}]}]}

Anti-doublon : on cherche par email (lowercase). Si trouvé, on met à jour les
champs vides ; on ne touche pas à sentAt/pendingDraft/dontSend.
Si introuvable, on crée un nouveau document avec source=yves_initial_list.

Usage:
    python -m agents.promoteurs.import_list agents/promoteurs/data/yves_initial_promoteurs.json
    python -m agents.promoteurs.import_list ... --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..shared import firestore_client as fs

AGENT_NAME = "promoteurs_import_list"
COLLECTION = "promoteurTargets"


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _find_by_email(email: str) -> Optional[Dict[str, Any]]:
    if not email:
        return None
    rows = fs.query(COLLECTION, filters=[("email", "==", email)], limit=1)
    return rows[0] if rows else None


def _build_doc(p: Dict[str, Any], category: str, default_lang: str, default_region: str) -> Dict[str, Any]:
    return {
        "companyName": (p.get("companyName") or "").strip(),
        "principalContact": (p.get("principalContact") or "Direction").strip(),
        "email": _normalize_email(p.get("email", "")),
        "region": p.get("region") or default_region,
        "city": p.get("city") or "",
        "language": p.get("language") or default_lang,
        "category": category,
        "recentProject": p.get("recentProject") or "",
        "score": p.get("score") or 0,
        "source": "yves_initial_list",
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
        category = group.get("category", "")
        for p in group.get("promoteurs", []):
            email = _normalize_email(p.get("email", ""))
            company = (p.get("companyName") or "").strip()

            if not email or "@" not in email or not company:
                print(f"  ⚠️  Skip (email/companyName manquant) : {p}")
                counts["skipped"] += 1
                continue

            existing = _find_by_email(email)
            doc = _build_doc(p, category, default_lang, default_region)

            if existing:
                if dry_run:
                    print(f"  ↻ [dry-run] UPDATE {email} → {company}")
                else:
                    safe_update = {
                        k: v for k, v in doc.items()
                        if k not in {"score"}  # ne pas écraser un score Norvex existant
                    }
                    fs.update(COLLECTION, existing["id"], safe_update)
                    print(f"  ↻ UPDATE {email} → {company}")
                counts["updated"] += 1
            else:
                if dry_run:
                    print(f"  + [dry-run] CREATE {email} ({company})")
                else:
                    new_id = fs.create(COLLECTION, doc)
                    print(f"  + CREATE {email} ({company}) → {new_id}")
                counts["created"] += 1

    if not dry_run:
        fs.audit_log(
            agent=AGENT_NAME,
            action="import_promoteurs",
            target_type="promoteurTargets",
            target_id=os.path.basename(path),
            details={"counts": counts, "source_file": path},
        )

    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", help="Chemin vers le JSON à importer")
    parser.add_argument("--dry-run", action="store_true", help="N'écrit rien")
    args = parser.parse_args()

    if not os.path.exists(args.json_path):
        print(f"❌ Fichier introuvable : {args.json_path}")
        return 1

    print(f"📥 Import promoteurs depuis : {args.json_path}")
    if args.dry_run:
        print("🔍 MODE DRY-RUN — aucune écriture\n")
    else:
        print()

    counts = import_file(args.json_path, dry_run=args.dry_run)
    print(f"\n✅ Terminé : {counts['created']} créés · {counts['updated']} mis à jour · {counts['skipped']} ignorés")
    return 0


if __name__ == "__main__":
    sys.exit(main())
