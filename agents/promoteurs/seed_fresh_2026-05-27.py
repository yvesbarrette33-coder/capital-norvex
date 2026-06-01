"""Seed Firestore promoteurTargets avec les cibles fraîches 27 mai 2026 PM
identifiées par 4 agents Explore + enrichies Hunter.

Source : /tmp/fresh_promoteurs_2026-05-27_enriched.json
Status : `to_validate` (ZÉRO envoi)

Cross-check duplicates par email contre la base existante promoteurTargets.

Usage:
  cd ~/Desktop/capitalnorvex-site
  PYTHONPATH=. python3 agents/promoteurs/seed_fresh_2026-05-27.py --dry-run
  PYTHONPATH=. python3 agents/promoteurs/seed_fresh_2026-05-27.py
"""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone
from agents.shared.firestore_client import db, create, audit_log

JSON_PATH = "/tmp/fresh_promoteurs_2026-05-27_enriched.json"
COLLECTION = "promoteurTargets"
SOURCE_TAG = "fresh_promoteurs_2026-05-27_4axes_explore_pm"


def _index_existing() -> set[str]:
    seen = set()
    for snap in db().collection(COLLECTION).stream():
        d = snap.to_dict() or {}
        for k in ("email",):
            v = d.get(k)
            if v and "@" in str(v):
                seen.add(str(v).strip().lower())
        for sub in ("contactInfo", "publicContact"):
            v = d.get(sub)
            if isinstance(v, dict) and v.get("email"):
                seen.add(v["email"].strip().lower())
    return seen


def main() -> int:
    dry = "--dry-run" in sys.argv
    data = json.load(open(JSON_PATH, encoding="utf-8"))
    targets = data.get("targets", [])
    print(f"📂 Source : {JSON_PATH} ({len(targets)} cibles)")
    print(f"{'🧪 DRY RUN' if dry else '💾 ÉCRITURE Firestore active'}")

    existing = _index_existing()
    print(f"📊 Emails déjà dans {COLLECTION} : {len(existing)}")
    print()

    created = 0
    skip_dup = 0
    skip_no_email = 0
    created_no_email = 0  # seed quand même pour enrichissement manuel
    rows = []

    for i, t in enumerate(targets, 1):
        name = t.get("name", "?")
        emails = t.get("emails") or []
        primary_email = emails[0]["email"] if emails else ""
        primary_contact = emails[0].get("name", "") if emails else t.get("contact", "Direction")
        primary_title = emails[0].get("position", "") if emails else t.get("title", "")

        # Fallback contact si Hunter rien
        if not primary_contact and t.get("contact") and t["contact"] != "Direction":
            primary_contact = t["contact"]
        if not primary_title and t.get("title"):
            primary_title = t["title"]

        if primary_email and primary_email in existing:
            print(f"[{i:2d}/{len(targets)}] {name:<35} ⚠️ {primary_email} déjà → SKIP")
            skip_dup += 1
            continue

        doc = {
            "companyName": name,
            "principalContact": primary_contact or t.get("contact", "Direction"),
            "title": primary_title or "",
            "email": primary_email or "",  # peut être vide — Yves enrichit dashboard
            "contactInfo": {"email": primary_email or ""} if primary_email else {},
            "region": t.get("province") or "",
            "province": t.get("province") or "",
            "city": t.get("city") or "",
            "language": t.get("lang") or "fr",
            "recentProject": "",  # template fallback à "votre récent projet"
            "sector_descriptor": t.get("sector") or "",
            "tier": t.get("tier") or "",
            "axis": t.get("axis") or "",
            "domain": t.get("domain") or "",
            "hunterEnriched": True,
            "hunterDate": "2026-05-27",
            "hunterPattern": t.get("hunter_pattern") or "",
            "hunterTopEmails": [e["email"] for e in emails[:5]],
            "primaryTargetEmail": primary_email or "",
            "notes_internal": t.get("flag") or "",
            "source": SOURCE_TAG,
            "status": "to_validate" if primary_email else "to_enrich_email",
            "skipOutreach": False,
            "dontSend": False,
            "createdBy": "claude_session_2026-05-27_pm_promoteurs",
        }

        if not primary_email:
            print(f"[{i:2d}/{len(targets)}] {name:<35} ℹ️ pas d'email Hunter → seed pour enrichissement")
            if not dry:
                try:
                    doc_id = create(COLLECTION, doc)
                    created_no_email += 1
                    rows.append({"name": name, "email": "", "tier": doc["tier"], "id": doc_id, "status": "to_enrich_email"})
                except Exception as e:
                    print(f"   ❌ {e}")
            continue

        if dry:
            print(f"[{i:2d}/{len(targets)}] {name:<35} ✓ would create | {primary_email} | tier={doc['tier']}")
            created += 1
            rows.append({"name": name, "email": primary_email, "tier": doc["tier"], "id": "(dry)"})
        else:
            try:
                doc_id = create(COLLECTION, doc)
                print(f"[{i:2d}/{len(targets)}] {name:<35} ✅ {doc_id} | {primary_email} | tier={doc['tier']}")
                created += 1
                rows.append({"name": name, "email": primary_email, "tier": doc["tier"], "id": doc_id, "status": "to_validate"})
            except Exception as e:
                print(f"[{i:2d}/{len(targets)}] {name:<35} ❌ {str(e)[:100]}")

    print()
    print("=" * 70)
    print(f"✅ Créés avec email (to_validate)       : {created}")
    print(f"📭 Créés sans email (to_enrich_email)   : {created_no_email}")
    print(f"⏭️ Skip doublons                         : {skip_dup}")
    print(f"📊 Total processés                       : {len(targets)}")

    if not dry:
        try:
            audit_log(
                agent="claude_session_2026-05-27_pm_promoteurs",
                action="seed_fresh_promoteur_targets",
                target_type="promoteurTargets",
                target_id=f"batch_{created+created_no_email}_targets",
                result="ok",
                details={"created_with_email": created, "created_no_email": created_no_email,
                         "skipped_duplicate": skip_dup, "source": SOURCE_TAG,
                         "rows_sample": rows[:5]},
            )
            print("📝 Audit log écrit")
        except Exception as e:
            print(f"⚠️ Audit log : {e}")

    out = f"/tmp/seed_promoteurs_results_2026-05-27{'_dry' if dry else ''}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"timestamp": datetime.now(timezone.utc).isoformat(),
                   "dry_run": dry,
                   "created_with_email": created,
                   "created_no_email": created_no_email,
                   "skipped_duplicate": skip_dup,
                   "rows": rows}, f, indent=2, ensure_ascii=False)
    print(f"📄 Résultats : {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
