"""
JOUR 1 OFFICIEL CAPITAL NORVEX — 2026-05-04
============================================
SCRIPT 01 : BACKUP COMPLET FIRESTORE

Exporte TOUTES les collections Firestore vers un fichier JSON local.
Filet de sécurité absolu AVANT tout nettoyage.

Sortie : ~/Desktop/capitalnorvex-site-BACKUP-JOUR1-OFFICIEL-2026-05-04.json

Usage :
    cd ~/Desktop/capitalnorvex-site
    python -m scripts.jour1_officiel.01_backup_firestore_complet
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Ajout du repo au path pour importer agents/shared
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from agents.shared.auth import get_firestore  # noqa: E402


def serialize_value(v):
    """Convertit les types Firestore non-JSON-sérialisables."""
    if hasattr(v, "isoformat"):  # datetime / Timestamp
        return v.isoformat()
    if hasattr(v, "path"):  # DocumentReference
        return f"REF:{v.path}"
    if isinstance(v, dict):
        return {k: serialize_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [serialize_value(x) for x in v]
    return v


def export_collection_recursive(db, coll_ref, depth=0):
    """Exporte une collection + ses sous-collections récursivement."""
    docs = {}
    indent = "  " * depth
    for doc in coll_ref.stream():
        data = serialize_value(doc.to_dict() or {})
        sub = {}
        # Sous-collections
        for sub_coll in doc.reference.collections():
            sub[sub_coll.id] = export_collection_recursive(db, sub_coll, depth + 1)
        docs[doc.id] = {"_data": data}
        if sub:
            docs[doc.id]["_subcollections"] = sub
        print(f"{indent}  📄 {doc.id}")
    return docs


def main():
    db = get_firestore()
    print("🔐 Connexion Firestore OK")

    backup = {
        "metadata": {
            "backup_date": datetime.utcnow().isoformat() + "Z",
            "purpose": "JOUR 1 OFFICIEL Capital Norvex — backup AVANT nettoyage",
            "project_id": os.getenv("FIREBASE_PROJECT_ID", "capital-norvex"),
        },
        "collections": {},
    }

    # Liste TOUTES les collections racines
    print("\n📂 Énumération des collections racines...")
    root_collections = list(db.collections())
    print(f"   → {len(root_collections)} collections trouvées\n")

    for coll in root_collections:
        print(f"📦 Export collection : {coll.id}")
        backup["collections"][coll.id] = export_collection_recursive(db, coll)
        print(f"   ✅ {len(backup['collections'][coll.id])} documents\n")

    # Sauvegarde
    out_path = Path.home() / "Desktop" / f"capitalnorvex-site-BACKUP-JOUR1-OFFICIEL-2026-05-04.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2, default=str)

    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"\n✅ BACKUP COMPLET → {out_path}")
    print(f"   Taille : {size_mb:.2f} MB")
    print(f"   Collections : {len(backup['collections'])}")
    total_docs = sum(len(v) for v in backup["collections"].values())
    print(f"   Documents racine total : {total_docs}")


if __name__ == "__main__":
    main()
