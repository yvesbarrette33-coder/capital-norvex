"""Seed Firestore `capitalTargets` avec les 42 cibles fraîches identifiées
27 mai 2026 (6 axes Explore + Mirage + Olymbec).

Status = `to_validate` (Yves valide chaque draft un par un dashboard ENSUITE,
ce script ne génère AUCUN draft et n'envoie AUCUN courriel).

Cross-check par email (top Hunter / primary_target_email) pour éviter doublons
contre la base existante `capitalTargets` Firestore.

Usage:
  cd ~/Desktop/capitalnorvex-site
  PYTHONPATH=. python3 agents/capital/seed_fresh_targets_2026-05-27.py --dry-run  # simule
  PYTHONPATH=. python3 agents/capital/seed_fresh_targets_2026-05-27.py            # exécute

Conservation totale du JSON source : `/tmp/fresh_targets_2026-05-27_with_hooks.json`
Audit log via `audit_logs` Firestore + sortie console.
"""
from __future__ import annotations

import json
import sys
import os
from datetime import datetime, timezone

from agents.shared.firestore_client import db, create, audit_log

JSON_PATH = "/tmp/fresh_targets_2026-05-27_with_hooks.json"
COLLECTION = "capitalTargets"
SOURCE_TAG = "fresh_targets_2026-05-27_6axes_explore_+_yves_additions"


def _primary_email(t: dict) -> str | None:
    """Retourne l'email cible primaire : override `primary_target_email` ou top Hunter."""
    if t.get("primary_target_email"):
        return t["primary_target_email"].strip().lower()
    emails = t.get("emails") or []
    if emails:
        return emails[0]["email"].strip().lower()
    return None


def _primary_contact(t: dict) -> dict:
    """Retourne {name, position} du contact primaire correspondant à l'email primaire."""
    em = _primary_email(t)
    if not em:
        return {"name": "", "position": ""}
    for e in t.get("emails") or []:
        if e["email"].strip().lower() == em:
            return {"name": e.get("name", ""), "position": e.get("position", "")}
    # Si primary_target_email a été overridé (ex: rstern, lpilon) et n'est pas dans top Hunter
    return {"name": "", "position": ""}


def _index_existing_emails() -> set[str]:
    """Index tous les emails déjà présents dans capitalTargets pour éviter doublons."""
    seen: set[str] = set()
    for snap in db().collection(COLLECTION).stream():
        d = snap.to_dict() or {}
        for key in ("email",):
            v = d.get(key)
            if v and "@" in str(v):
                seen.add(str(v).strip().lower())
        for sub in ("contactInfo", "publicContact"):
            v = d.get(sub)
            if isinstance(v, dict) and v.get("email") and "@" in v["email"]:
                seen.add(v["email"].strip().lower())
    return seen


def main() -> int:
    dry = "--dry-run" in sys.argv

    if not os.path.exists(JSON_PATH):
        print(f"❌ Fichier introuvable : {JSON_PATH}", file=sys.stderr)
        return 1

    data = json.load(open(JSON_PATH, encoding="utf-8"))
    targets = data.get("targets", [])
    print(f"📂 Source : {JSON_PATH}")
    print(f"🎯 Cibles à seeder : {len(targets)}")
    print(f"{'🧪 DRY RUN (aucune écriture Firestore)' if dry else '💾 ÉCRITURE Firestore active'}")
    print()

    existing = _index_existing_emails()
    print(f"📊 Emails déjà dans capitalTargets : {len(existing)}")
    print()

    created = 0
    skipped_duplicate = 0
    skipped_no_email = 0
    rows: list[dict] = []

    for i, t in enumerate(targets, 1):
        name = t.get("name") or "?"
        em = _primary_email(t)
        if not em:
            print(f"[{i:2d}/{len(targets)}] {name:<35} ⚠️ pas d'email → SKIP")
            skipped_no_email += 1
            continue

        if em in existing:
            print(f"[{i:2d}/{len(targets)}] {name:<35} ⚠️ {em} déjà dans capitalTargets → SKIP")
            skipped_duplicate += 1
            continue

        contact = _primary_contact(t)
        doc = {
            "organization": name,
            "name": contact.get("name") or name,  # contact name (top Hunter) ou fallback org name
            "contactName": contact.get("name") or "",
            "title": contact.get("position") or "",
            "email": em,
            "contactInfo": {"email": em},
            "region": t.get("province") or "",
            "province": t.get("province") or "",
            "city": t.get("city") or "",
            "lang": t.get("lang") or "fr",
            "letterPersonalizedHook": t.get("letterPersonalizedHook") or "",
            "tier": t.get("priority") or "",
            "ca_estimated_descriptor": t.get("ca") or "",
            "owner_descriptor": t.get("owner") or "",
            "sector_descriptor": t.get("sector") or "",
            "status_descriptor": t.get("status") or "",
            "domain": t.get("domain") or "",
            "hunterEnriched": True,
            "hunterDate": "2026-05-27",
            "hunterPattern": t.get("hunter_pattern") or "",
            "hunterTopEmails": [e["email"] for e in (t.get("emails") or [])[:5]],
            "primaryTargetEmail": em,
            "notes_internal": t.get("notes_yves") or "",
            "source": SOURCE_TAG,
            "status": "to_validate",  # Yves valide → puis génère draft via pipeline
            "skipOutreach": False,
            "createdBy": "claude_session_2026-05-27_matin",
        }

        if dry:
            print(f"[{i:2d}/{len(targets)}] {name:<35} ✓ would create | {em} | tier={doc['tier']} | hook={len(doc['letterPersonalizedHook'].split())}w")
            created += 1
            rows.append({"name": name, "email": em, "tier": doc['tier'], "id": "(dry)"})
        else:
            try:
                doc_id = create(COLLECTION, doc)
                print(f"[{i:2d}/{len(targets)}] {name:<35} ✅ created {doc_id} | {em} | tier={doc['tier']}")
                created += 1
                rows.append({"name": name, "email": em, "tier": doc['tier'], "id": doc_id})
            except Exception as e:
                print(f"[{i:2d}/{len(targets)}] {name:<35} ❌ erreur : {str(e)[:100]}")

    print()
    print("=" * 70)
    print(f"✅ Créés                 : {created}")
    print(f"⏭️ Skip (doublon email)  : {skipped_duplicate}")
    print(f"⏭️ Skip (pas d'email)    : {skipped_no_email}")
    print(f"📊 Total processés       : {len(targets)}")

    if not dry and created > 0:
        # Audit log global
        try:
            audit_log(
                agent="claude_session_2026-05-27_matin",
                action="seed_fresh_capital_targets",
                target_type="capitalTargets",
                target_id=f"batch_{created}_targets",
                result="ok",
                details={
                    "created": created,
                    "skipped_duplicate": skipped_duplicate,
                    "skipped_no_email": skipped_no_email,
                    "source": SOURCE_TAG,
                    "json_path": JSON_PATH,
                    "rows_sample": rows[:5],
                },
            )
            print(f"📝 Audit log écrit")
        except Exception as e:
            print(f"⚠️ Audit log échec : {e}")

    # Sauvegarde résultats locaux
    out = f"/tmp/seed_results_2026-05-27{'_dry' if dry else ''}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": dry,
            "created": created,
            "skipped_duplicate": skipped_duplicate,
            "skipped_no_email": skipped_no_email,
            "rows": rows,
        }, f, indent=2, ensure_ascii=False)
    print(f"📄 Résultats : {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
