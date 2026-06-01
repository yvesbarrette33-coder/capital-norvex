"""Hunter domain-search pour récupérer les courriels NOMINATIFS des 3 firmes fraîches."""
from __future__ import annotations

import json as _json
import os
import urllib.parse
import urllib.request

DOMAINS = [
    ("massmortgagegroup.com", "MASS Mortgage Group"),
    ("matrixmortgageglobal.ca", "Matrix Mortgage Global"),
    ("cirrius.ca", "Cirrius Commercial Financing"),
]


def _load_key() -> str | None:
    k = os.environ.get("HUNTER_API_KEY")
    if k:
        return k
    path = os.path.expanduser("~/.capitalnorvex/.env")
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("HUNTER_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return None


def domain_search(domain: str, api_key: str) -> dict:
    url = "https://api.hunter.io/v2/domain-search?" + urllib.parse.urlencode(
        {"domain": domain, "api_key": api_key, "limit": 100}
    )
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return _json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def main() -> None:
    key = _load_key()
    if not key:
        print("HUNTER_API_KEY introuvable")
        return
    for domain, label in DOMAINS:
        res = domain_search(domain, key)
        print(f"\n=== {label} ({domain}) ===")
        if res.get("error"):
            print(f"  ERROR {res['error']}")
            continue
        data = res.get("data") or {}
        emails = data.get("emails") or []
        print(f"  org: {data.get('organization')}  total_emails: {len(emails)}")
        for e in emails:
            name = f"{e.get('first_name') or ''} {e.get('last_name') or ''}".strip()
            print(
                f"  - {e.get('value')} | {name or '(no name)'} | "
                f"pos={e.get('position')} | conf={e.get('confidence')} | "
                f"dept={e.get('department')} | type={e.get('type')}"
            )


if __name__ == "__main__":
    main()
