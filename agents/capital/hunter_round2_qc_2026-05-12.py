"""Hunter enrichment Round 2 capital QC — 2026-05-12.

Focus : Marcel/Marc Dutil (Canam/CMI), Pierre Somers (Walter), Lawrence Zucker (Osmington CEO),
Michael Domb (Forest Hill Capital), Jim Balsillie (Wealhouse founder).
"""
from __future__ import annotations

import json as _json
import os
import sys
import time
import urllib.parse
import urllib.request

DOMAINS = [
    ("Canam Group", "canam.com", "QC", "fr"),
    ("Walter Group", "waltergroup.ca", "QC", "fr"),
    ("Walter Capital Partners", "waltercapital.ca", "QC", "fr"),
    ("Walter Capital Management", "waltercapitalmanagement.ca", "QC", "fr"),
    ("Forest Hill Capital (foresthillcapital.ca)", "foresthillcapital.ca", "ON", "en"),
    ("Domb Capital", "dombcapital.com", "ON", "en"),
    ("Forest Hill Advisory", "foresthilladvisory.com", "ON", "en"),
    ("Osmington Capital Partners", "osmingtoncp.com", "ON", "en"),
    ("Wealhouse", "wealhouse.com", "ON", "en"),  # vérifier si Balsillie présent
]


def hunter_domain_search(domain: str, api_key: str) -> dict | None:
    url = (
        "https://api.hunter.io/v2/domain-search?"
        + urllib.parse.urlencode({"domain": domain, "api_key": api_key, "limit": 15})
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

    priority = [
        "owner", "founder", "co-founder", "chairman", "president", "ceo",
        "chief executive", "executive chairman", "co-chair", "managing partner",
        "managing director", "partner", "head", "vice president", "vp",
    ]
    for name, domain, region, lang in DOMAINS:
        result = hunter_domain_search(domain, key)
        print(f"\n=== {name} ({domain}) — région {region}, langue {lang} ===")
        if result is None or result.get("error"):
            print(f"  ❌ {result}")
            continue
        data = result.get("data") or {}
        org = data.get("organization") or "?"
        pattern = data.get("pattern") or "?"
        emails = data.get("emails") or []
        print(f"  org={org}  pattern={pattern}  emails_count={len(emails)}")
        scored = []
        for e in emails:
            pos = (e.get("position") or "").lower()
            score = 0
            for i, kw in enumerate(priority):
                if kw in pos:
                    score = len(priority) - i
                    break
            scored.append((score, e))
        scored.sort(key=lambda t: t[0], reverse=True)
        for score, e in scored[:10]:
            print(f"    [{score}] {e.get('value','?')} — {e.get('first_name','')} {e.get('last_name','')} — {e.get('position','?')}")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
