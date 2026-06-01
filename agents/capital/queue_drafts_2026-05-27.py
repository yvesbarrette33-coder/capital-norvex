"""Batch queue_one sur les 41 cibles capitalTargets seedées ce matin
27 mai 2026 (source = fresh_targets_2026-05-27_*).

Génère drafts V9 capital + upload Storage + patch Firestore pendingDraft
+ status=pending_yves_approval pour validation Yves dashboard.

ZÉRO envoi (queue_one ne fait que pré-rendre, pas envoyer).

Usage:
  cd ~/Desktop/capitalnorvex-site
  PYTHONPATH=. python3 agents/capital/queue_drafts_2026-05-27.py --dry-run
  PYTHONPATH=. python3 agents/capital/queue_drafts_2026-05-27.py
"""
from __future__ import annotations

import sys
from agents.shared.firestore_client import db
from agents.capital.outreach import queue_one

SOURCE_TAG_PREFIX = "fresh_targets_2026-05-27"


def main() -> int:
    dry = "--dry-run" in sys.argv
    # Lister tous les docs créés ce matin via seed
    docs = []
    for snap in db().collection("capitalTargets").stream():
        d = snap.to_dict() or {}
        src = d.get("source") or ""
        if src.startswith(SOURCE_TAG_PREFIX):
            docs.append((snap.id, d))
    print(f"📂 Docs seedés ce matin trouvés : {len(docs)}")
    print(f"{'🧪 DRY RUN' if dry else '💾 GENERATION drafts active'}")
    print()

    queued = 0
    skipped = 0
    errors = 0
    for i, (doc_id, d) in enumerate(sorted(docs, key=lambda x: x[1].get("organization", "")), 1):
        org = d.get("organization", "?")
        tier = d.get("tier", "")
        email = d.get("email") or (d.get("contactInfo") or {}).get("email") or ""
        if dry:
            print(f"[{i:2d}/{len(docs)}] {org:<35} [{tier:<9}] {email:<45} → would queue")
            queued += 1
            continue
        try:
            ok = queue_one(doc_id, force=True)
            if ok:
                queued += 1
            else:
                skipped += 1
        except Exception as e:
            errors += 1
            print(f"   ❌ {org} erreur : {str(e)[:100]}")

    print()
    print("=" * 70)
    print(f"✅ Drafts queue       : {queued}")
    print(f"⏭️ Skip                : {skipped}")
    print(f"❌ Erreurs             : {errors}")
    print(f"📊 Total processés     : {len(docs)}")
    print()
    print("📋 Yves : ouvrir dashboard capital-norvex-agents.html (onglet Capital)")
    print("   pour valider/envoyer chaque draft un par un.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
