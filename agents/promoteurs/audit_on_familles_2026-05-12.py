"""Audit promoteurTargets — Tridel/Geranium/Mizrahi/Easton's familles."""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/yvesbarrette/Desktop/capitalnorvex-site")

from agents.shared.firestore_client import query


def get_email(doc: dict) -> str | None:
    ci = doc.get("contactInfo") or {}
    pc = doc.get("publicContact") or {}
    return doc.get("email") or ci.get("email") or pc.get("email")


KEYWORDS = [
    "tridel", "della spina", "delcourt",
    "geranium", "cortellucci",
    "mizrahi",
    "easton", "easton's", "silver hotel", "gupta",
]


def main() -> None:
    docs = query("promoteurTargets")
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
                nom = d.get("nom") or d.get("companyName") or "?"
                print(f"[{kw}] {nom} — {get_email(d) or '(no email)'} — status={d.get('status')}, sent={d.get('sentAt') or '-'}, opens={d.get('opens',0) or d.get('openCount',0)} clicks={d.get('clicks',0) or d.get('clickCount',0)}")
                break


if __name__ == "__main__":
    main()
