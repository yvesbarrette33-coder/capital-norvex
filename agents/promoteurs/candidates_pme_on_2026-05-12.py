"""Vérification doublons + check Hunter pour PME promoteurs ON 2026-05-12.

Liste candidate compilée via WebSearch (2e vague PME mid-market).
"""
from __future__ import annotations

import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, "/Users/yvesbarrette/Desktop/capitalnorvex-site")

from agents.shared.firestore_client import query

# Source: WebSearch 2026-05-12 PM (Hamilton/Ottawa/London/KW/Niagara/York Region/Mississauga)
CANDIDATES = [
    # Hamilton
    ("Losani Homes", "losanihomes.com", "Hamilton", "ON"),
    ("Hue Developments", "huedev.ca", "Hamilton", "ON"),
    ("Elite Developments", "elitedevelopments.ca", "Hamilton", "ON"),
    ("Coletara Development", "coletara.com", "Hamilton", "ON"),
    ("Pinemount Developments", "pinemount.ca", "Hamilton", "ON"),
    ("Royal Living", "royallivinghomes.com", "Hamilton", "ON"),
    ("Emblem Developments", "emblemdevelopments.com", "Hamilton", "ON"),
    # Ottawa
    ("TCU Development Corporation", "tcudevcorp.com", "Ottawa", "ON"),
    ("Antilia Homes", "antiliahomes.com", "Ottawa", "ON"),
    ("MB Groupe Canada (Mahi-Beaudry)", "mbgroupcanada.com", "Ottawa-Gatineau", "ON"),
    ("Regional Group", "regionalgroup.com", "Ottawa", "ON"),
    ("CLV Group", "clvgroup.com", "Ottawa", "ON"),
    # London / SW Ontario
    ("York Developments", "yorkdev.ca", "London", "ON"),
    ("CSM Dev Corp", "csmdevcorp.ca", "London", "ON"),
    # Kitchener-Waterloo
    ("Whitney & Company Residential", "whitneyres.com", "Waterloo", "ON"),
    # Niagara
    ("Mountainview Construction Inc.", "mountainviewbuildinggroup.com", "Niagara", "ON"),
    # York Region
    ("Markham Development Company", "markhamdevelopmentcompany.com", "Markham", "ON"),
]


def get_email(doc: dict) -> str | None:
    ci = doc.get("contactInfo") or {}
    pc = doc.get("publicContact") or {}
    return doc.get("email") or ci.get("email") or pc.get("email")


def existing_names_domains():
    docs = query("promoteurTargets")
    names = set()
    domains = set()
    for d in docs:
        nom = (d.get("nom") or d.get("companyName") or "").lower().strip()
        if nom:
            names.add(nom)
        email = (get_email(d) or "").lower()
        if "@" in email:
            domains.add(email.split("@", 1)[1])
        ws = (d.get("contactInfo") or {}).get("website") or d.get("website") or ""
        if ws:
            host = ws.replace("https://", "").replace("http://", "").split("/")[0].lower()
            if host.startswith("www."):
                host = host[4:]
            domains.add(host)
    return names, domains


def hunter_domain_search(domain: str, api_key: str) -> dict | None:
    url = (
        "https://api.hunter.io/v2/domain-search?"
        + urllib.parse.urlencode({"domain": domain, "api_key": api_key, "limit": 5})
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            import json as _json
            return _json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def main() -> None:
    names, domains = existing_names_domains()

    print(f"Base actuelle : {len(names)} noms, {len(domains)} domaines\n")
    print("=== Cross-check candidats vs Firestore ===")
    new_candidates = []
    for name, domain, city, region in CANDIDATES:
        in_base = (name.lower() in names) or (domain.lower() in domains)
        if in_base:
            print(f"  [DOUBLON] {name} ({domain}) — déjà en base, skip")
        else:
            new_candidates.append((name, domain, city, region))
            print(f"  [NEW]     {name} ({domain}) — {city}")

    print(f"\n{len(new_candidates)} nouveaux candidats à enrichir.\n")

    # Hunter
    hunter_key = os.environ.get("HUNTER_API_KEY")
    if not hunter_key:
        print("⚠️ HUNTER_API_KEY non set — skip enrichissement emails")
        return

    print("=== Hunter enrichment ===")
    for name, domain, city, region in new_candidates:
        result = hunter_domain_search(domain, hunter_key)
        if result is None or result.get("error"):
            print(f"  {name}: ❌ {result}")
            continue
        data = result.get("data") or {}
        org = data.get("organization") or "?"
        pattern = data.get("pattern") or "?"
        emails = data.get("emails") or []
        print(f"  {name} ({domain})")
        print(f"      org={org}  pattern={pattern}")
        for e in emails[:5]:
            roles = ",".join(e.get("position") or [] if isinstance(e.get("position"), list) else [str(e.get("position") or "")])
            print(f"      → {e.get('value','?')}  ({e.get('first_name','')} {e.get('last_name','')} — {e.get('position','?')})")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
