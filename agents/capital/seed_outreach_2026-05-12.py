#!/usr/bin/env python3
"""Seed/update 13 cibles Capital pour outreach 2026-05-12 + lancement drafts.

Pour chaque cible :
1. Trouve ou crée le doc dans capitalTargets
2. Met à jour l'email (Hunter) + customCapsuleId si Tier 1 + reset status
3. Appelle queue_one(doc_id, force=True) → upload draft Storage + Firestore pendingDraft
"""
from __future__ import annotations

import os
import sys
import argparse
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.capitalnorvex/.env"))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.shared import firestore_client as fs  # type: ignore
from agents.capital.outreach import queue_one  # type: ignore


# ─── 13 cibles d'aujourd'hui ────────────────────────────────────────────────

TARGETS: List[Dict[str, Any]] = [
    # === Tier 1 — vidéo perso HeyGen ===
    {
        "name": "Alain Bouchard",
        "organization": "Alimentation Couche-Tard",
        "title": "Co-fondateur, Executive Chairman",
        "region": "QC", "language": "fr",
        "email": "alain.bouchard@couche-tard.com",
        "customCapsuleId": "gQB8o0nwdmY",
        "tier": "1A_resend_2026-05-12",
    },
    {
        "name": "Claude Tessier",
        "organization": "Alimentation Couche-Tard",
        "title": "Chef de la direction financière",
        "region": "QC", "language": "fr",
        "email": "claude.tessier@couche-tard.com",
        "customCapsuleId": "mcSfynPrsLA",
        "tier": "1A_resend_2026-05-12",
    },
    {
        "name": "Vincent Chiara",
        "organization": "Groupe MACH",
        "title": "Fondateur & Président",
        "region": "QC", "language": "fr",
        "email": "vchiara@groupemach.com",
        "customCapsuleId": "8mDiRHr36XE",
        "tier": "1A_resend_2026-05-12",
    },
    {
        "name": "David Thomson",
        "organization": "Thomson Reuters / The Globe and Mail",
        "title": "Chairman",
        "region": "ON", "language": "en",
        "email": "dthomson@globeandmail.com",
        "customCapsuleId": "KqYRcLQ1ESU",
        "tier": "1A_new_2026-05-12",
    },
    {
        "name": "Galen Weston",
        "organization": "Loblaw Companies / Wittington Investments",
        "title": "Executive Chairman",
        "region": "ON", "language": "en",
        "email": "galen@loblaw.ca",
        "customCapsuleId": "K0XryVReehU",
        "tier": "1A_new_2026-05-12",
    },
    # === Tier 2 — vidéo générique « Lettre partenaire FR / EN » ===
    {
        "name": "Louis Audet",
        "organization": "Gestion Audem Inc. / Cogeco Family Holdings",
        "title": "Chairman / Family Office",
        "region": "QC", "language": "fr",
        "email": "louis.audet@cogeco.com",
        "tier": "2_new_2026-05-12",
    },
    {
        "name": "Pierre Beaudoin",
        "organization": "Bombardier / Famille Beaudoin",
        "title": "Chairman",
        "region": "QC", "language": "fr",
        "email": "pierre.beaudoin@bombardier.com",
        "tier": "2_new_2026-05-12",
    },
    {
        "name": "Larry Rossy",
        "organization": "Dollarama / Famille Rossy",
        "title": "Founder, Executive Chairman",
        "region": "QC", "language": "fr",
        "email": "larry.rossy@dollarama.com",
        "tier": "2_new_2026-05-12",
    },
    {
        "name": "Neil Rossy",
        "organization": "Dollarama",
        "title": "President & CEO",
        "region": "QC", "language": "fr",
        "email": "neil.rossy@dollarama.com",
        "tier": "2_new_2026-05-12",
    },
    {
        "name": "Lino Saputo Jr.",
        "organization": "Saputo Inc.",
        "title": "Chairman & CEO",
        "region": "QC", "language": "fr",
        "email": "linos@saputo.com",  # Hunter score 45 — à risque
        "tier": "2_new_2026-05-12",
    },
    {
        "name": "Alain Lemaire",
        "organization": "Cascades Inc.",
        "title": "Co-fondateur",
        "region": "QC", "language": "fr",
        "email": "alain_lemaire@cascades.com",
        "tier": "2_new_2026-05-12",
    },
    {
        "name": "Michael McCain",
        "organization": "Maple Leaf Foods / Famille McCain",
        "title": "Executive Chairman",
        "region": "ON", "language": "en",
        "email": "michael.mccain@mapleleaf.com",
        "tier": "2_new_2026-05-12",
    },
    {
        "name": "Jim Pattison",
        "organization": "Jim Pattison Group",
        "title": "Chairman, CEO & Founder",
        "region": "BC", "language": "en",
        "email": "jpattison@pattisonsign.com",
        "tier": "2_new_2026-05-12",
    },
]


def _find_existing(name: str, organization: str) -> Optional[str]:
    """Retourne doc_id existant si trouvé (match par name OU organization)."""
    db = fs.db()
    col = db.collection("capitalTargets")
    docs = list(col.limit(500).stream())
    name_l = name.lower().strip()
    for snap in docs:
        d = snap.to_dict() or {}
        dn = (d.get("name") or "").lower().strip()
        if dn == name_l:
            return snap.id
    return None


def upsert_target(target: Dict[str, Any], dry_run: bool = False) -> Optional[str]:
    """Crée ou update le doc capitalTargets. Retourne doc_id."""
    doc_id = _find_existing(target["name"], target["organization"])
    update_data = {
        "name": target["name"],
        "organization": target["organization"],
        "title": target.get("title", ""),
        "region": target["region"],
        "language": target["language"],
        "email": target["email"],
        "publicContact": {"email": target["email"]},
        "tier": target.get("tier", "2"),
        "status": "approved_pending_render",
    }
    if target.get("customCapsuleId"):
        update_data["customCapsuleId"] = target["customCapsuleId"]
        update_data["customCapsuleDuration"] = "35s"
    if dry_run:
        print(f"   [DRY] upsert {target['name']} → {update_data}")
        return doc_id or "DRY_NEW_ID"
    if doc_id:
        fs.update("capitalTargets", doc_id, update_data)
        print(f"   ✅ UPDATE {doc_id} → {target['name']}")
    else:
        doc_id = fs.create("capitalTargets", update_data)
        print(f"   🆕 CREATE {doc_id} → {target['name']}")
    return doc_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true", help="Dry-run (pas d'écriture Firestore)")
    parser.add_argument("--no-queue", action="store_true", help="Upsert seulement, pas de queue_one")
    args = parser.parse_args()

    print(f"=== Seed outreach 2026-05-12 — {len(TARGETS)} cibles ===\n")
    results = []
    for i, t in enumerate(TARGETS, 1):
        print(f"[{i:2d}/{len(TARGETS)}] {t['name']} ({t['organization']})")
        doc_id = upsert_target(t, dry_run=args.dry)
        if doc_id and not args.dry and not args.no_queue:
            print(f"   → queue_one({doc_id}, force=True)")
            try:
                ok = queue_one(doc_id, force=True)
                results.append((t["name"], doc_id, ok))
            except Exception as e:
                print(f"   ❌ queue_one ERROR: {e}")
                results.append((t["name"], doc_id, False))
        else:
            results.append((t["name"], doc_id, None))
        print()

    print(f"\n=== Bilan ===")
    for name, doc_id, ok in results:
        status = "✅" if ok else ("❌" if ok is False else "—")
        print(f"  {status}  {name:30s}  doc={doc_id}")


if __name__ == "__main__":
    main()
