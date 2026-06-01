"""Hunter Vague #5 B+C — familles QC + promoteurs ON familles supp."""
from __future__ import annotations

import json as _json
import os
import sys
import time
import urllib.parse
import urllib.request

DOMAINS = [
    # B - QC familles
    ("Pomerleau", "pomerleau.ca"),
    ("Telesystem (Sirois)", "telesystem.ca"),
    ("Jean Coutu Group", "jeancoutu.com"),
    ("Jean Coutu (alt)", "jc-pjc.com"),
    # C - ON promoteurs familles
    ("Greenpark Group", "greenparkgroup.ca"),
    ("Greenpark Homes", "greenparkhomes.com"),
    ("Empire Communities", "empirecommunities.com"),
    ("Empire Homes (alt)", "empirehomes.com"),
    ("Tribute Communities", "tributecommunities.com"),
    # Bonus famille Wynn (Wynn Group of Companies)
    ("Wynn Group of Companies", "wynngroupofcompanies.com"),
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
        "managing director", "partner", "executive", "head", "vice president", "vp",
    ]
    # Familles dont le nom de famille devrait booster le score
    famille_keywords = (
        "pomerleau", "sirois", "coutu", "baldassarra", "guizzetti", "golini",
        "wynn", "weinzweig", "lassonde", "rechtsman", "wine",
    )

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
            for famille in famille_keywords:
                if famille in last or famille in first:
                    score += 8
                    break
            scored.append((score, e))
        scored.sort(key=lambda t: t[0], reverse=True)
        for score, e in scored[:10]:
            print(f"    [{score:2d}] {e.get('value','?')} — {e.get('first_name','')} {e.get('last_name','')} — {e.get('position','?')}")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
