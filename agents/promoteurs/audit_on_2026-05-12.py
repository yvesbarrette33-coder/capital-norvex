"""Audit one-shot 2026-05-12 — promoteurTargets région ON.

Liste:
- Total docs Ontario
- Avec email vs sans email
- Statut blacklist / déjà contacté
- Top candidats prêts pour Hunter/WebSearch
"""
from __future__ import annotations

import sys
from collections import Counter

sys.path.insert(0, "/Users/yvesbarrette/Desktop/capitalnorvex-site")

from agents.shared.firestore_client import query


def get_email(doc: dict) -> str | None:
    ci = doc.get("contactInfo") or {}
    pc = doc.get("publicContact") or {}
    return (
        doc.get("email")
        or ci.get("email")
        or pc.get("email")
        or None
    )


def main() -> None:
    docs = query("promoteurTargets")
    on_docs = [d for d in docs if (d.get("region") or "").upper() in ("ON", "ONTARIO")]

    total = len(on_docs)
    with_email = [d for d in on_docs if get_email(d)]
    without_email = [d for d in on_docs if not get_email(d)]

    statuses = Counter((d.get("status") or "?") for d in on_docs)
    tiers = Counter((d.get("tier") if d.get("tier") is not None else "?") for d in on_docs)
    blacklisted = [d for d in on_docs if d.get("skipOutreach") or d.get("status") == "blacklist_permanent"]

    print(f"=== AUDIT promoteurTargets ON — 2026-05-12 ===")
    print(f"Total ON : {total}")
    print(f"  avec email     : {len(with_email)}")
    print(f"  sans email     : {len(without_email)}")
    print(f"  blacklisted    : {len(blacklisted)}")
    print()
    print("Statuts :")
    for k, v in statuses.most_common():
        print(f"  {k}: {v}")
    print()
    print("Tiers :")
    for k, v in tiers.most_common():
        print(f"  {k}: {v}")
    print()
    print("=== SANS EMAIL — top 30 candidats (non-blacklist, tier!=0) ===")
    candidates = [
        d for d in without_email
        if not d.get("skipOutreach")
        and d.get("status") != "blacklist_permanent"
        and (d.get("tier") or 99) != 0
    ]
    candidates.sort(key=lambda d: (d.get("tier") or 99, d.get("nom") or ""))
    for d in candidates[:30]:
        nom = d.get("nom") or d.get("companyName") or "?"
        tier = d.get("tier", "?")
        ville = d.get("ville") or d.get("city") or ""
        website = (d.get("contactInfo") or {}).get("website") or d.get("website") or ""
        notes = d.get("notes") or ""
        print(f"  [tier={tier}] {nom} — {ville} — {website}")
        if notes:
            print(f"      notes: {notes[:120]}")


if __name__ == "__main__":
    main()
