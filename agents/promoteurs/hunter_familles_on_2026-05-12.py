"""Hunter enrichment familles promoteurs ON 2026-05-12."""
from __future__ import annotations

import json as _json
import os
import sys
import time
import urllib.parse
import urllib.request

DOMAINS = [
    ("Tridel", "tridel.com"),
    ("Tridel Group", "tridelgroup.com"),
    ("Geranium Corporation", "geraniumcorporation.com"),
    ("Geranium Homes", "geranium.com"),
    ("Mizrahi Developments", "mizrahidevelopments.ca"),
    ("Mizrahi Design Build", "mizrahidesignbuild.ca"),
    ("Easton's Group of Hotels", "eastonsgroup.com"),
    ("Gupta Group", "guptagroup.ca"),
    # Bonus Cortellucci (séparé de Geranium)
    ("Cortel Group", "cortelgroup.com"),
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
        "chief executive", "executive", "managing partner", "managing director",
        "partner", "head", "vice president", "vp",
    ]
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
            # Bonus si nom de famille = celui de la company (DelZotto, Mizrahi, Gupta, Cortellucci)
            last = (e.get("last_name") or "").lower()
            for famille in ("delzotto", "del zotto", "mizrahi", "gupta", "cortellucci", "feiner"):
                if famille in last:
                    score += 5
                    break
            scored.append((score, e))
        scored.sort(key=lambda t: t[0], reverse=True)
        for score, e in scored[:10]:
            print(f"    [{score}] {e.get('value','?')} — {e.get('first_name','')} {e.get('last_name','')} — {e.get('position','?')}")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
