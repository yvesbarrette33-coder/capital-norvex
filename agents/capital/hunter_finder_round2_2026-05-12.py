"""Hunter email-finder pour vérifier les emails prédictifs Round 2."""
from __future__ import annotations

import json as _json
import os
import sys
import urllib.parse
import urllib.request

# (first, last, domain, label)
TARGETS = [
    ("Marc", "Dutil", "canam.com", "Marc Dutil — Canam CEO actuel (fils)"),
    ("Marcel", "Dutil", "canam.com", "Marcel Dutil — Canam Chairman fondateur"),
    ("Lawrence", "Zucker", "osmington.com", "Lawrence Zucker — Osmington CEO"),
    ("Michael", "Domb", "dombcapital.com", "Michael Domb — Forest Hill Capital"),
    ("Michael", "Domb", "foresthillcapital.ca", "Michael Domb — alt domain"),
    ("Pierre", "Fitzgibbon", "waltercapital.ca", "Pierre Fitzgibbon — Walter Capital MP"),
]


def find_email(first: str, last: str, domain: str, api_key: str) -> dict | None:
    url = (
        "https://api.hunter.io/v2/email-finder?"
        + urllib.parse.urlencode(
            {
                "domain": domain,
                "first_name": first,
                "last_name": last,
                "api_key": api_key,
            }
        )
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return _json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def main() -> None:
    key = os.environ.get("HUNTER_API_KEY")
    if not key:
        print("⚠️ HUNTER_API_KEY non set")
        sys.exit(1)

    for first, last, domain, label in TARGETS:
        result = find_email(first, last, domain, key)
        print(f"\n=== {label} ({first} {last} @ {domain}) ===")
        if result is None or result.get("error"):
            print(f"  ❌ {result}")
            continue
        data = result.get("data") or {}
        email = data.get("email")
        score = data.get("score")
        verif = (data.get("verification") or {}).get("status")
        sources = data.get("sources") or []
        position = data.get("position")
        print(f"  email: {email}")
        print(f"  confidence_score: {score}")
        print(f"  verification: {verif}")
        print(f"  position: {position}")
        print(f"  sources_count: {len(sources)}")


if __name__ == "__main__":
    main()
