"""Audit capitalTargets — recherche cibles Round 2 QC manquants."""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/yvesbarrette/Desktop/capitalnorvex-site")

from agents.shared.firestore_client import query


def get_email(doc: dict) -> str | None:
    ci = doc.get("contactInfo") or {}
    pc = doc.get("publicContact") or {}
    return doc.get("email") or ci.get("email") or pc.get("email")


KEYWORDS = [
    "dutil", "canam",
    "walter",
    "reichmann",
    "balsillie", "wealhouse",
    "domb", "forest hill",
    "zucker", "osmington",
    "beattie",  # rappel
]


def main() -> None:
    docs = query("capitalTargets")
    print(f"Total capitalTargets : {len(docs)}\n")

    matches = []
    for d in docs:
        haystack = " ".join(
            str(v).lower() for v in [
                d.get("nom"),
                d.get("companyName"),
                d.get("organization"),
                d.get("name"),
                d.get("principalContact"),
                d.get("evidence"),
                d.get("ville"),
                d.get("city"),
                (d.get("contactInfo") or {}).get("website"),
                d.get("website"),
                get_email(d),
            ] if v
        )
        for kw in KEYWORDS:
            if kw in haystack:
                matches.append((kw, d))
                break

    print(f"=== Correspondances trouvées ({len(matches)}) ===\n")
    for kw, d in matches:
        nom = d.get("nom") or d.get("name") or d.get("companyName") or "?"
        org = d.get("organization") or d.get("companyName") or ""
        email = get_email(d) or "(pas d'email)"
        status = d.get("status") or "?"
        sent_at = d.get("sentAt") or d.get("lastSentAt") or "-"
        opens = d.get("opens", 0) or d.get("openCount", 0)
        clicks = d.get("clicks", 0) or d.get("clickCount", 0)
        print(f"  [{kw}] {nom} / {org}")
        print(f"      email: {email}")
        print(f"      status={status}, sent={sent_at}, opens={opens}, clicks={clicks}")
        print()


if __name__ == "__main__":
    main()
