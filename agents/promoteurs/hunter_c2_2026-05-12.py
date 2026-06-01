"""Hunter C2 — Pearl/Liberty/Camrost/Marlin Spring/Baz."""
from __future__ import annotations

import json as _json
import os
import sys
import time
import urllib.parse
import urllib.request

DOMAINS = [
    ("Pearl Group", "pearlgroup.ca"),
    ("Liberty Development", "libertydevelopment.ca"),
    ("Camrost Felcorp", "camrost.com"),
    ("Marlin Spring", "marlinspring.com"),
    ("Baz Group", "bazgroup.ca"),
]


def hunter(domain: str, api_key: str) -> dict | None:
    url = (
        "https://api.hunter.io/v2/domain-search?"
        + urllib.parse.urlencode({"domain": domain, "api_key": api_key, "limit": 20})
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return _json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def main() -> None:
    key = os.environ.get("HUNTER_API_KEY")
    if not key:
        sys.exit("⚠️ HUNTER_API_KEY non set")

    priority = [
        "owner", "founder", "co-founder", "chairman", "president", "ceo",
        "chief executive", "executive chairman", "co-chair", "managing partner",
        "executive", "partner", "head", "vice president", "vp",
    ]
    famille = ("pearl", "feldman", "fazel", "darvish", "bakst", "kazarnovsky", "mandelbaum")

    for name, domain in DOMAINS:
        r = hunter(domain, key)
        print(f"\n=== {name} ({domain}) ===")
        if not r or r.get("error"):
            print(f"  ❌ {r}")
            continue
        data = r.get("data") or {}
        org = data.get("organization") or "?"
        pattern = data.get("pattern") or "?"
        emails = data.get("emails") or []
        print(f"  org={org}  pattern={pattern}  count={len(emails)}")
        scored = []
        for e in emails:
            pos = (e.get("position") or "").lower()
            score = 0
            for i, kw in enumerate(priority):
                if kw in pos:
                    score = len(priority) - i
                    break
            last = (e.get("last_name") or "").lower()
            first = (e.get("first_name") or "").lower()
            for f in famille:
                if f in last or f in first:
                    score += 10
                    break
            scored.append((score, e))
        scored.sort(key=lambda t: t[0], reverse=True)
        for score, e in scored[:8]:
            print(f"    [{score:2d}] {e.get('value','?')} — {e.get('first_name','')} {e.get('last_name','')} — {e.get('position','?')}")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
