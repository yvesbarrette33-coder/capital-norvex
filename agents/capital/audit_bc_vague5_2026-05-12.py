"""Audit Firestore — cibles candidates Vague #5 B+C 2026-05-12 PM."""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/yvesbarrette/Desktop/capitalnorvex-site")

from agents.shared.firestore_client import query


def get_email(doc: dict) -> str | None:
    ci = doc.get("contactInfo") or {}
    pc = doc.get("publicContact") or {}
    return doc.get("email") or ci.get("email") or pc.get("email")


# B = familles QC discrètes / C = promoteurs ON familles supplémentaires
KEYWORDS = [
    # B - QC familles discrètes
    "coutu", "lassonde", "sirois", "aubut", "lamarre", "tisseyre",
    "pomerleau", "boivin", "industrielle alliance", "catania",
    "ebc", "lessard construction", "cossette", "dansereau",
    # C - ON familles promoteurs
    "pearl group", "liberty development", "filice",
    "greenpark", "baldassarra",
    "tribute communities", "wynn",
    "camrost", "felcorp", "feldman",
    "plaza partners", "cresci",
    "marlin spring", "bakst", "kazarnovsky",
    "empire communities", "guizzetti", "golini",
]


def main() -> None:
    cap = query("capitalTargets")
    prom = query("promoteurTargets")
    print(f"capitalTargets : {len(cap)}  |  promoteurTargets : {len(prom)}\n")

    for collection_name, docs in (("capitalTargets", cap), ("promoteurTargets", prom)):
        for d in docs:
            haystack = " ".join(
                str(v).lower() for v in [
                    d.get("nom"), d.get("companyName"), d.get("organization"),
                    d.get("name"), d.get("principalContact"), d.get("evidence"),
                    (d.get("contactInfo") or {}).get("website"), d.get("website"),
                    get_email(d),
                ] if v
            )
            for kw in KEYWORDS:
                if kw in haystack:
                    nom = d.get("nom") or d.get("name") or d.get("companyName") or "?"
                    print(f"[{collection_name}/{kw}] {nom} — {get_email(d) or '(no email)'} — status={d.get('status')}, sent={d.get('sentAt') or '-'}")
                    break


if __name__ == "__main__":
    main()
