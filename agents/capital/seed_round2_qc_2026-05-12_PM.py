#!/usr/bin/env python3
"""Seed 7 cibles Round 2 capital QC PM 2026-05-12 + queue drafts.

Vague #3 du plan séquentiel.
- 3 vertes Hunter (Walter Group + Walter Capital × 2)
- 4 prédictives (Dutil ×2, Zucker, Fitzgibbon) — patterns confirmés par d'autres employés
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


TARGETS: List[Dict[str, Any]] = [
    # === VERTS Hunter ===
    {
        "name": "Pierre Somers",
        "organization": "Walter Group",
        "title": "Président du conseil et chef de la direction (famille fondatrice)",
        "region": "QC",
        "language": "fr",
        "email": "psomers@waltergroup.ca",
        "tier": "2_round2_qc_2026-05-12_verified",
    },
    {
        "name": "Eric Phaneuf",
        "organization": "Walter Capital Partners",
        "title": "Associé directeur",
        "region": "QC",
        "language": "fr",
        "email": "ephaneuf@waltercapital.ca",
        "tier": "2_round2_qc_2026-05-12_verified",
    },
    {
        "name": "Eric Doyon",
        "organization": "Walter Capital Partners",
        "title": "Associé directeur",
        "region": "QC",
        "language": "fr",
        "email": "edoyon@waltercapital.ca",
        "tier": "2_round2_qc_2026-05-12_verified",
    },
    # === PRÉDICTIFS — patterns Hunter confirmés par autres employés ===
    {
        "name": "Marc Dutil",
        "organization": "Groupe Canam",
        "title": "Président et chef de la direction (famille fondatrice)",
        "region": "QC",
        "language": "fr",
        "email": "marc.dutil@canam.com",
        "tier": "2_round2_qc_2026-05-12_predictive",
    },
    {
        "name": "Marcel Dutil",
        "organization": "Groupe Canam",
        "title": "Président du conseil, fondateur",
        "region": "QC",
        "language": "fr",
        "email": "marcel.dutil@canam.com",
        "tier": "2_round2_qc_2026-05-12_predictive",
    },
    {
        "name": "Lawrence Zucker",
        "organization": "Osmington Inc.",
        "title": "Chief Executive Officer",
        "region": "ON",
        "language": "en",
        "email": "lzucker@osmington.com",
        "tier": "2_round2_qc_2026-05-12_predictive",
    },
    {
        "name": "Pierre Fitzgibbon",
        "organization": "Walter Capital Partners",
        "title": "Associé directeur",
        "region": "QC",
        "language": "fr",
        "email": "pfitzgibbon@waltercapital.ca",
        "tier": "2_round2_qc_2026-05-12_predictive",
    },
]


def _find_existing(name: str, organization: str) -> Optional[str]:
    name_l = (name or "").lower().strip()
    docs = fs.query("capitalTargets", limit=500)
    for d in docs:
        dn = (d.get("name") or "").lower().strip()
        if dn == name_l:
            return d.get("id")
    return None


def upsert_target(target: Dict[str, Any], dry_run: bool = False) -> Optional[str]:
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
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--no-queue", action="store_true")
    args = parser.parse_args()

    print(f"=== Seed Round 2 QC PM 2026-05-12 — {len(TARGETS)} cibles ===\n")
    results = []
    for i, t in enumerate(TARGETS, 1):
        print(f"[{i}/{len(TARGETS)}] {t['name']} ({t['organization']})")
        doc_id = upsert_target(t, dry_run=args.dry)
        if doc_id and not args.dry and not args.no_queue:
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
