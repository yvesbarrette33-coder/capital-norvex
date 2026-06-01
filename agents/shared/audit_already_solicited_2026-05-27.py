"""Audit Firestore — liste de toutes les cibles DÉJÀ touchées (status=sent
ou pending) dans les 4 collections outreach.

Output : /tmp/already_solicited_2026-05-27.csv
Format : collection,docId,email,name,organization,status,lastSentAt,skipReason

Usage:
    cd ~/Desktop/capitalnorvex-site
    python -m agents.shared.audit_already_solicited_2026-05-27

Source de vérité pour exclure les déjà-touchées de toute nouvelle recherche
de cibles fraîches (méthode 27 mai 2026 verrouillée par Yves).
"""
from __future__ import annotations

import csv
import sys
from datetime import datetime
from typing import Any, Dict, List

from agents.shared.firestore_client import db

COLLECTIONS = [
    "capitalTargets",
    "promoteurTargets",
    "brokers",
    "advisorTargets",
]

OUTPUT_PATH = "/tmp/already_solicited_2026-05-27.csv"


def _email(d: Dict[str, Any]) -> str:
    """Résout email depuis 3 emplacements possibles."""
    for key in ("email",):
        e = d.get(key)
        if e and isinstance(e, str) and "@" in e:
            return e.strip().lower()
    for sub in ("contactInfo", "publicContact"):
        v = d.get(sub)
        if isinstance(v, dict):
            e = v.get("email")
            if e and isinstance(e, str) and "@" in e:
                return e.strip().lower()
    return ""


def _name(d: Dict[str, Any]) -> str:
    return (d.get("name") or d.get("contactName")
            or d.get("fullName") or "").strip()


def _org(d: Dict[str, Any]) -> str:
    return (d.get("organization") or d.get("firmName")
            or d.get("entityName") or d.get("company") or "").strip()


def _iso(v: Any) -> str:
    if not v:
        return ""
    if isinstance(v, str):
        return v[:25]
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()[:25]
        except Exception:
            return ""
    return str(v)[:25]


def _is_solicited(d: Dict[str, Any]) -> bool:
    """True si le doc a déjà été touché ou marqué actif outreach."""
    status = (d.get("status") or "").lower()
    if status in {"sent", "queued", "pending", "drafted",
                  "scheduled", "approved", "active_partner"}:
        return True
    if d.get("sentAt") or d.get("lastSentAt"):
        return True
    if d.get("skipOutreach") is True:
        return True
    return False


def audit_collection(name: str) -> List[Dict[str, Any]]:
    print(f"📂 {name} …", flush=True)
    rows: List[Dict[str, Any]] = []
    skipped_no_email = 0
    total = 0
    for snap in db().collection(name).stream():
        total += 1
        d = snap.to_dict() or {}
        if not _is_solicited(d):
            continue
        em = _email(d)
        if not em:
            skipped_no_email += 1
            continue
        rows.append({
            "collection": name,
            "docId": snap.id,
            "email": em,
            "name": _name(d),
            "organization": _org(d),
            "status": d.get("status") or "",
            "sentAt": _iso(d.get("sentAt") or d.get("lastSentAt")),
            "skipOutreach": "1" if d.get("skipOutreach") else "",
            "skipReason": (d.get("skipReason") or "")[:200],
        })
    print(f"   total={total} solicited={len(rows)} no_email={skipped_no_email}")
    return rows


def main() -> int:
    started = datetime.utcnow()
    all_rows: List[Dict[str, Any]] = []
    for col in COLLECTIONS:
        try:
            all_rows.extend(audit_collection(col))
        except Exception as e:
            print(f"❌ {col}: {e}", file=sys.stderr)

    # Dédupe par email (un email peut être dans plusieurs collections)
    by_email: Dict[str, Dict[str, Any]] = {}
    for r in all_rows:
        em = r["email"]
        if em not in by_email:
            by_email[em] = r
        else:
            # garde le plus récent
            if r["sentAt"] > by_email[em]["sentAt"]:
                by_email[em] = r

    fieldnames = ["collection", "docId", "email", "name", "organization",
                  "status", "sentAt", "skipOutreach", "skipReason"]
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in sorted(by_email.values(),
                        key=lambda x: (x["collection"], x["organization"], x["name"])):
            w.writerow(r)

    by_col: Dict[str, int] = {}
    for r in all_rows:
        by_col[r["collection"]] = by_col.get(r["collection"], 0) + 1

    print()
    print("=" * 60)
    print(f"✅ Audit terminé en {(datetime.utcnow()-started).total_seconds():.1f}s")
    print(f"📄 Sortie : {OUTPUT_PATH}")
    print(f"📊 Total touché brut    : {len(all_rows)}")
    print(f"📊 Total unique (email) : {len(by_email)}")
    for c in COLLECTIONS:
        print(f"   - {c:<20} {by_col.get(c, 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
