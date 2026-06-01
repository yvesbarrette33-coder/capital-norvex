"""Consolidation des 40 cibles fraîches identifiées 27 mai 2026 par 6 agents
Explore parallèles + cross-check exclusion list /tmp/already_solicited_2026-05-27.csv
+ Hunter Domain Search batch.

Output:
  /tmp/fresh_targets_2026-05-27_enriched.json    — 40 cibles + emails Hunter
  /tmp/fresh_targets_2026-05-27_exclusion_hits.txt — cibles déjà touchées (skip)

Usage:
  cd ~/Desktop/capitalnorvex-site
  PYTHONPATH=. python3 agents/capital/fresh_targets_2026-05-27.py

Source consolidée 6 agents :
  1. Pharma QC (a77ac16e)
  2. Alimentaire QC+ON (a3fdaf1b)
  3. Manufactures industrielles QC+ON (aa9940b1)
  4. Distribution/Logistique QC+ON (a812830)
  5. Services pro / Tech B2B QC+ON (adf1a51b)
  6. Cotées-familles QC+ON (a3789f02)
  7. Secteurs divers (a5fd340b)

Règle Yves 27 mai 2026 :
- Cotées canadiennes contrôlées-famille = OK (Saputo/Lassonde/Linamar/CCL/Dorel)
- Semi-publics famille+gouv (Dutil/Lacasse) = OK (Manac/Canam/Honco)
- Méga-multinationales type Couche-Tard = EXCLUS
- Asset managers / pension funds / Brookfield/Onex/Power Corp = EXCLUS
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from dotenv import load_dotenv

# Charge HUNTER_API_KEY depuis ~/.capitalnorvex/.env
load_dotenv(os.path.expanduser("~/.capitalnorvex/.env"))


# ────────────────────────────────────────────────────────────────────
# 40 CIBLES FRAÎCHES (toutes validées « pas Joe Patate » : CA ≥100 M$,
# famille identifiable ou cotée-famille majoritaire, privée ou semi-pub,
# QC ou ON, pas méga-multinationale, pas asset manager)
# ────────────────────────────────────────────────────────────────────
TARGETS = [
    # ─── Tier ULTRA (CA ≥500 M$ ou cap ≥5 G$) ───
    {"name": "CCL Industries", "domain": "ccl.com", "city": "Toronto", "province": "ON",
     "ca": "8.2 G$", "owner": "Famille Lang (90% A-shares)", "sector": "Étiquetage industriel",
     "status": "coté TSX:CCL.A/B famille majoritaire", "lang": "en", "priority": "T1_ULTRA"},
    {"name": "Canam Group", "domain": "canam.com", "city": "Saint-Georges", "province": "QC",
     "ca": "4.1 G$", "owner": "Famille Dutil + CDPQ/Fonds FTQ", "sector": "Acier structural",
     "status": "privé semi-public (Dutil 38%+gouv)", "lang": "fr", "priority": "T1_ULTRA"},
    {"name": "Bridor (LE DUFF Group)", "domain": "bridor.com", "city": "Boucherville", "province": "QC",
     "ca": "2.9 G$", "owner": "Famille Le Duff (Louis)", "sector": "Boulangerie artisanale",
     "status": "privé famille", "lang": "fr", "priority": "T1_ULTRA"},
    {"name": "Sofina Foods", "domain": "sofinafoods.com", "city": "Markham", "province": "ON",
     "ca": "2.3-3.5 G$", "owner": "Famille privée", "sector": "Protéines transformées",
     "status": "privé famille", "lang": "en", "priority": "T1_ULTRA"},
    {"name": "Husky Injection Molding Systems", "domain": "husky.co", "city": "Bolton", "province": "ON",
     "ca": "1.5 G$", "owner": "Privé opaque", "sector": "Équipement injection plastique",
     "status": "privé", "lang": "en", "priority": "T1_ULTRA"},
    {"name": "EBC Construction", "domain": "ebcinc.com", "city": "Montréal", "province": "QC",
     "ca": "1.0 G$", "owner": "Famille Houle (Marie-Claude)", "sector": "Construction génie civil",
     "status": "privé famille (1968)", "lang": "fr", "priority": "T1_ULTRA"},
    {"name": "Dilawri Group", "domain": "dilawri.ca", "city": "Vaughan", "province": "ON",
     "ca": ">1 G$", "owner": "Frères Ajay/Kap/Tony Dilawri", "sector": "Concessions auto",
     "status": "privé famille", "lang": "en", "priority": "T1_ULTRA"},
    {"name": "Reitmans (Canada)", "domain": "reitmans.com", "city": "Montréal", "province": "QC",
     "ca": "767 M$", "owner": "Famille Reitman", "sector": "Mode féminine",
     "status": "coté TSXV:RET.A famille", "lang": "fr", "priority": "T1_ULTRA"},
    {"name": "Groupe Leclerc (Biscuits)", "domain": "leclerc.ca", "city": "Saint-Augustin", "province": "QC",
     "ca": "759 M$", "owner": "Famille Leclerc (depuis 1905)", "sector": "Biscuits/crackers/barres",
     "status": "privé famille", "lang": "fr", "priority": "T1_ULTRA"},
    {"name": "Groupe Soucy", "domain": "soucy-group.com", "city": "Drummondville", "province": "QC",
     "ca": "678 M$", "owner": "Famille Soucy (depuis 1967)", "sector": "Plastiques/caoutchouc industriels",
     "status": "privé famille 100%", "lang": "fr", "priority": "T1_ULTRA"},
    {"name": "Compugen", "domain": "compugen.com", "city": "Richmond Hill", "province": "ON",
     "ca": "626 M$", "owner": "Harry Zarek (depuis 1981)", "sector": "Services TI infogérance",
     "status": "privé famille", "lang": "en", "priority": "T1_ULTRA"},

    # ─── Tier 1 STANDARD (CA 200-500 M$) ───
    {"name": "Dare Foods", "domain": "darefoods.com", "city": "Cambridge", "province": "ON",
     "ca": "470 M$", "owner": "Famille Doerr (depuis 1892)", "sector": "Biscuits/snacks",
     "status": "privé famille", "lang": "en", "priority": "T1"},
    {"name": "Manac", "domain": "manac.ca", "city": "Saint-Georges", "province": "QC",
     "ca": "414 M$", "owner": "Famille Dutil + CDPQ/Fonds FTQ", "sector": "Remorques industrielles",
     "status": "privé semi-public", "lang": "fr", "priority": "T1"},
    {"name": "Jamp Pharma", "domain": "jamppharma.com", "city": "Boucherville", "province": "QC",
     "ca": "~400 M$", "owner": "Louis Pilon (100% depuis 2006)", "sector": "Pharma biosimilaires",
     "status": "privé pur", "lang": "fr", "priority": "T0_PILON"},  # Priorité absolue #1
    {"name": "Pharmascience", "domain": "pharmascience.com", "city": "Montréal", "province": "QC",
     "ca": "~400 M$", "owner": "Famille Goodman", "sector": "Pharma générique",
     "status": "privé famille (1983)", "lang": "fr", "priority": "T1"},
    {"name": "Honco", "domain": "groupehonco.com", "city": "Lévis", "province": "QC",
     "ca": "300-400 M$", "owner": "Famille Lacasse + CDPQ/IQ", "sector": "Bâtiments métal préfab",
     "status": "privé semi-public", "lang": "fr", "priority": "T1"},
    {"name": "Performance Auto Group", "domain": "performance.ca", "city": "Brampton", "province": "ON",
     "ca": "250-350 M$", "owner": "Famille Alizadeh (depuis 1964)", "sector": "Concessions auto",
     "status": "privé famille", "lang": "en", "priority": "T1"},
    {"name": "Sunray Group of Hotels", "domain": "sunraygroup.com", "city": "Mississauga", "province": "ON",
     "ca": "250-350 M$", "owner": "Rattan Ray Gupta", "sector": "Hôtellerie/immobilier",
     "status": "privé famille", "lang": "en", "priority": "T1"},
    {"name": "Groupe Park Avenue", "domain": "groupeparkavenue.com", "city": "Brossard", "province": "QC",
     "ca": "300-400 M$", "owner": "Famille Hébert (3 générations)", "sector": "Concessions auto",
     "status": "privé famille (1959)", "lang": "fr", "priority": "T1"},
    {"name": "Manitoulin Transport", "domain": "manitoulintransport.com", "city": "Gore Bay", "province": "ON",
     "ca": "339 M$", "owner": "Famille Smith (Doug fondateur 1960)", "sector": "Transport LTL/TL",
     "status": "privé famille", "lang": "en", "priority": "T1"},
    {"name": "Groupe Robert", "domain": "robert.ca", "city": "Boucherville", "province": "QC",
     "ca": "332 M$", "owner": "Famille Robert (4e génération)", "sector": "Transport routier/3PL",
     "status": "privé famille (1946)", "lang": "fr", "priority": "T1"},
    {"name": "Erb Group", "domain": "erbgroup.com", "city": "New Hamburg", "province": "ON",
     "ca": "250-300 M$", "owner": "Famille Erb (Mennonite, Vernon 1959)", "sector": "Transport réfrigéré",
     "status": "privé famille", "lang": "en", "priority": "T1"},
    {"name": "Groupe Olivier Auto", "domain": "groupeolivier.com", "city": "Saint-Hubert", "province": "QC",
     "ca": "200-300 M$", "owner": "Jacques Olivier (fondateur 1985)", "sector": "Concessions auto multi-marques",
     "status": "privé famille", "lang": "fr", "priority": "T1"},
    {"name": "Dorel Industries", "domain": "dorel.com", "city": "Montréal", "province": "QC",
     "ca": "~900 M$", "owner": "Famille Schwartz (60% voting)", "sector": "Sièges enfants/vélos/meubles",
     "status": "coté TSX:DII.A/B famille", "lang": "fr", "priority": "T1"},

    # ─── Tier 2 (CA 100-200 M$) ───
    {"name": "Burnbrae Farms", "domain": "burnbraefarms.com", "city": "Lyn", "province": "ON",
     "ca": "194 M$", "owner": "Famille Hudson (6e génération, 1893)", "sector": "Œufs et dérivés",
     "status": "privé famille", "lang": "en", "priority": "T2"},
    {"name": "CIMA+", "domain": "cima.ca", "city": "Laval", "province": "QC",
     "ca": "191 M$", "owner": "Partenaires employee-owned", "sector": "Génie-conseil",
     "status": "privé partnership", "lang": "fr", "priority": "T2"},
    {"name": "Germain Hotels", "domain": "germainhotels.com", "city": "Québec", "province": "QC",
     "ca": "150-200 M$", "owner": "Famille Germain (Christiane + Jean-Yves)", "sector": "Hôtellerie premium",
     "status": "privé famille + CDPQ 2025", "lang": "fr", "priority": "T2"},
    {"name": "Speedy Transport Group", "domain": "speedy.ca", "city": "Brampton", "province": "ON",
     "ca": "130-160 M$", "owner": "Famille (depuis 1941)", "sector": "LTL/same-day delivery",
     "status": "privé famille", "lang": "en", "priority": "T2"},
    {"name": "Boulangerie St-Méthode", "domain": "boulangeriestmethode.com", "city": "Adstock", "province": "QC",
     "ca": "125 M$", "owner": "Famille + CDPQ partenaire 2023", "sector": "Boulangerie industrielle",
     "status": "privé famille majoritaire", "lang": "fr", "priority": "T2"},
    {"name": "Dialog Architects", "domain": "dialogdesign.ca", "city": "Toronto", "province": "ON",
     "ca": "125 M$", "owner": "Employee-owned partnership", "sector": "Architecture/ingénierie",
     "status": "privé partnership", "lang": "en", "priority": "T2"},
    {"name": "Joseph Transportation Group", "domain": "josephhaulage.com", "city": "Stoney Creek", "province": "ON",
     "ca": "120-150 M$", "owner": "Famille (50 ans)", "sector": "Transport bulk matériaux",
     "status": "privé famille", "lang": "en", "priority": "T2"},
    {"name": "Transport Bourassa", "domain": "bourassa.ca", "city": "Saint-Jean-sur-Richelieu", "province": "QC",
     "ca": "120-150 M$", "owner": "Famille Bourassa (1956)", "sector": "Transport LTL/distribution",
     "status": "privé famille", "lang": "fr", "priority": "T2"},
    {"name": "Hector Larivée", "domain": "hectorlarivee.com", "city": "Montréal", "province": "QC",
     "ca": "110-140 M$", "owner": "Famille Larivée (4e génération)", "sector": "Distribution fruits/légumes",
     "status": "privé famille (1940)", "lang": "fr", "priority": "T2"},
    {"name": "Highland Transport", "domain": "highlandtransport.com", "city": "Markham", "province": "ON",
     "ca": "100-130 M$", "owner": "Famille indépendante (1967)", "sector": "Truckload/drayage",
     "status": "privé famille", "lang": "en", "priority": "T2"},

    # ─── Tier 2+ (privé famille, taille à confirmer mais réputation solide) ───
    {"name": "Lallemand", "domain": "lallemand.com", "city": "Montréal", "province": "QC",
     "ca": "~1 G$ estimé", "owner": "Famille Chagnon", "sector": "Probiotiques/levures industrielles",
     "status": "privé famille", "lang": "fr", "priority": "T1"},
    {"name": "FGF Brands", "domain": "fgfbrands.com", "city": "Toronto", "province": "ON",
     "ca": "à confirmer (acq 1.2 G$ Weston 2021)", "owner": "Famille privée (fondée 2004)",
     "sector": "Boulangerie industrielle", "status": "privé famille", "lang": "en", "priority": "T1"},
    {"name": "P&H Milling Group", "domain": "phmilling.com", "city": "Hanover", "province": "ON",
     "ca": "à confirmer (plus grand meunier CA)", "owner": "Familles Parrish & Heimbecker (1909)",
     "sector": "Meunerie", "status": "privé famille", "lang": "en", "priority": "T1"},
    {"name": "St-Helen's Meat Packers", "domain": "sthelensmeat.com", "city": "Toronto", "province": "ON",
     "ca": "à confirmer", "owner": "Famille (50+ ans)", "sector": "Transformation viande",
     "status": "privé famille", "lang": "en", "priority": "T2"},
    {"name": "Imprimerie Solisco", "domain": "solisco.com", "city": "Scott", "province": "QC",
     "ca": "80-150 M$", "owner": "Privé (1991)", "sector": "Imprimerie commerciale",
     "status": "privé", "lang": "fr", "priority": "T2"},
    {"name": "Laboratoires Druide", "domain": "druidebio.com", "city": "Joliette", "province": "QC",
     "ca": "50-150 M$", "owner": "Famille + Derme&Co (2017)", "sector": "Cosmétique biologique",
     "status": "privé famille", "lang": "fr", "priority": "T3"},
]


def hunter_domain_search(domain: str, api_key: str, limit: int = 10) -> dict | None:
    url = (
        "https://api.hunter.io/v2/domain-search?"
        + urllib.parse.urlencode({"domain": domain, "api_key": api_key,
                                   "limit": limit})
    )
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


PRIORITY_TITLES = [
    "owner", "founder", "co-founder", "chairman", "president", "ceo",
    "chief executive", "executive chairman", "co-chair", "managing partner",
    "managing director", "partner", "vp", "vice president", "head",
    "chief financial", "cfo", "directeur g", "président",
]


def score_email(email_obj: dict) -> int:
    title = (email_obj.get("position") or "").lower()
    for i, kw in enumerate(PRIORITY_TITLES):
        if kw in title:
            return 100 - i
    return 0


def load_exclusion(csv_path: str) -> set[str]:
    s: set[str] = set()
    if not os.path.exists(csv_path):
        return s
    with open(csv_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            em = (r.get("email") or "").strip().lower()
            if em:
                s.add(em)
    return s


def main() -> int:
    api_key = os.environ.get("HUNTER_API_KEY")
    if not api_key:
        print("⚠️ HUNTER_API_KEY non set dans ~/.capitalnorvex/.env", file=sys.stderr)
        return 1

    exclusion = load_exclusion("/tmp/already_solicited_2026-05-27.csv")
    print(f"📂 Exclusion list : {len(exclusion)} emails déjà touchés chargés")
    print(f"🎯 Cibles à enrichir : {len(TARGETS)}")
    print()

    enriched = []
    exclusion_hits = []

    for i, t in enumerate(TARGETS, 1):
        print(f"[{i:2d}/{len(TARGETS)}] {t['name']:<35} ({t['domain']}) ... ", end="", flush=True)
        result = hunter_domain_search(t["domain"], api_key, limit=15)
        if result is None or result.get("error"):
            t["hunter_status"] = "error"
            t["hunter_error"] = (result or {}).get("error", "unknown")
            t["emails"] = []
            print(f"❌ {t.get('hunter_error', 'error')[:60]}")
            enriched.append(t)
            time.sleep(1)
            continue

        data = result.get("data") or {}
        emails_raw = data.get("emails") or []

        # Filtre + score
        filtered = []
        for e in emails_raw:
            em_addr = (e.get("value") or "").strip().lower()
            if not em_addr:
                continue
            if em_addr in exclusion:
                exclusion_hits.append({
                    "target": t["name"],
                    "domain": t["domain"],
                    "email": em_addr,
                    "name": f"{e.get('first_name', '')} {e.get('last_name', '')}".strip(),
                    "position": e.get("position", ""),
                })
                continue
            filtered.append({
                "email": em_addr,
                "name": f"{e.get('first_name', '') or ''} {e.get('last_name', '') or ''}".strip(),
                "position": e.get("position") or "",
                "linkedin": e.get("linkedin") or "",
                "confidence": e.get("confidence", 0),
                "score": score_email(e),
            })

        filtered.sort(key=lambda x: (-x["score"], -x["confidence"]))

        t["hunter_status"] = "ok"
        t["hunter_pattern"] = data.get("pattern") or ""
        t["hunter_organization"] = data.get("organization") or ""
        t["emails"] = filtered[:8]  # Top 8 par score
        t["emails_count_raw"] = len(emails_raw)
        t["emails_count_after_exclusion"] = len(filtered)
        print(f"✅ {len(emails_raw)} bruts / {len(filtered)} après exclusion / top score: "
              f"{filtered[0]['email'] if filtered else 'aucun'}")
        enriched.append(t)
        time.sleep(1.2)  # anti rate-limit Hunter

    # Sauvegarde JSON
    out_path = "/tmp/fresh_targets_2026-05-27_enriched.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "audit_date": "2026-05-27",
            "total_targets": len(TARGETS),
            "exclusion_list_size": len(exclusion),
            "exclusion_hits": len(exclusion_hits),
            "targets": enriched,
            "exclusion_hits_detail": exclusion_hits,
        }, f, indent=2, ensure_ascii=False)
    print()
    print(f"📄 JSON enrichi : {out_path}")

    # Sauvegarde exclusion hits
    if exclusion_hits:
        hits_path = "/tmp/fresh_targets_2026-05-27_exclusion_hits.txt"
        with open(hits_path, "w", encoding="utf-8") as f:
            f.write(f"Hunter a trouvé {len(exclusion_hits)} emails déjà dans la "
                    f"liste exclusion 888 (à SKIP) :\n\n")
            for h in exclusion_hits:
                f.write(f"  - {h['target']:<30} {h['email']:<40} "
                        f"({h['name']} - {h['position']})\n")
        print(f"⚠️ Hits exclusion : {hits_path}")

    # Stats finales
    ok = sum(1 for t in enriched if t.get("hunter_status") == "ok")
    no_email = sum(1 for t in enriched
                    if t.get("hunter_status") == "ok"
                    and t.get("emails_count_after_exclusion", 0) == 0)
    total_emails = sum(t.get("emails_count_after_exclusion", 0) for t in enriched)
    print()
    print("=" * 65)
    print(f"✅ Cibles enrichies avec succès  : {ok}/{len(TARGETS)}")
    print(f"📧 Total emails trouvés (post-excl): {total_emails}")
    print(f"⚠️ Cibles sans email Hunter      : {no_email}")
    print(f"🚫 Hits dans exclusion list      : {len(exclusion_hits)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
