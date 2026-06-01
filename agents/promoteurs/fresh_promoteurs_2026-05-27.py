"""Consolidation 67 cibles promoteurs brutes identifiées 27 mai 2026 PM
par 4 agents Explore parallèles. Filtre doublons + Hunter batch + seed.

Pipeline complet:
  1. Liste consolidée des 67 cibles avec metadata
  2. Cross-check exclusion list (888 emails) + capital matin (43) + connus déjà touchés mémoire
  3. Hunter Domain Search sur domaines fresh
  4. Output JSON enrichi + résumé filtrage

Usage:
  cd ~/Desktop/capitalnorvex-site
  PYTHONPATH=. python3 agents/promoteurs/fresh_promoteurs_2026-05-27.py
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

load_dotenv(os.path.expanduser("~/.capitalnorvex/.env"))


# ────────────────────────────────────────────────────────────────────
# 67 CIBLES PROMOTEURS BRUTES (4 agents Explore 27 mai PM)
# ────────────────────────────────────────────────────────────────────

TARGETS = [
    # ─── Agent 1/4 : Promoteurs résidentiels QC régional (18) ───
    {"name": "Services Immobiliers First", "domain": "servicesimmobiliersfirst.ca", "city": "Sherbrooke", "province": "QC",
     "contact": "Christian St-James", "title": "CEO", "sector": "Résidentiel — condos, multilogements (340+ logements Estrie)",
     "lang": "fr", "tier": "T1", "axis": "res_qc"},
    {"name": "Groupe Desainay", "domain": "desainay.com", "city": "Chicoutimi", "province": "QC",
     "contact": "Cajetan Bouchard", "title": "Fondateur", "sector": "RPA + multilogement (600+ apts retraite, 8 résidences, Place Desainay 45M$)",
     "lang": "fr", "tier": "T1", "axis": "res_qc"},
    {"name": "Habitations Urbania", "domain": "habitationsurbania.com", "city": "Bécancour", "province": "QC",
     "contact": "Yannick Lemonde", "title": "Président", "sector": "Maisons neuves Bécancour+Trois-Rivières (100+ projets, grade A GCR)",
     "lang": "fr", "tier": "T2", "axis": "res_qc"},
    {"name": "Constructions Éric Gélinas", "domain": "constructionericgelinas.com", "city": "Trois-Rivières", "province": "QC",
     "contact": "Éric Gélinas", "title": "Propriétaire", "sector": "Développements résidentiels Trois-Rivières",
     "lang": "fr", "tier": "T2", "axis": "res_qc"},
    {"name": "Domaine de la famille", "domain": "domainedelafamille.com", "city": "Trois-Rivières", "province": "QC",
     "contact": "Direction", "title": "", "sector": "Lots résidentiels boisés (20 min TR)",
     "lang": "fr", "tier": "T2", "axis": "res_qc"},
    {"name": "Habitations Moderno", "domain": "moderno.immo", "city": "Lanaudière", "province": "QC",
     "contact": "Charles Morneau", "title": "Co-fondateur", "sector": "Condos locatifs (340+ logements, Aqua Roca 230 condos 2025-2028)",
     "lang": "fr", "tier": "T1", "axis": "res_qc", "flag": "déjà touché 12 mai — à vérifier CSV"},
    {"name": "Le Norden / Domicil", "domain": "lenorden.com", "city": "Saint-Jérôme", "province": "QC",
     "contact": "Direction", "title": "", "sector": "Condo+locatif (Le Boisé Terrebonne 188 unités, Boisé Rivière-du-Nord 200 unités, 35 ans expérience)",
     "lang": "fr", "tier": "T1", "axis": "res_qc"},
    {"name": "Domaine des 4 Collines", "domain": "4collines.com", "city": "Ste-Marguerite", "province": "QC",
     "contact": "Direction", "title": "", "sector": "Domaine privé résidentiel Laurentides (depuis 2001)",
     "lang": "fr", "tier": "T2", "axis": "res_qc"},
    {"name": "Habita Nord-Est", "domain": "habitanordest.com", "city": "Boisbriand", "province": "QC",
     "contact": "Direction", "title": "", "sector": "Townhouses (3 générations, 50+ ans — Cité du Boisé Dion, NORCITÉ 2 Mirabel 29 townhouses)",
     "lang": "fr", "tier": "T1", "axis": "res_qc"},
    {"name": "San Leon", "domain": "sanleon.ca", "city": "Boisbriand", "province": "QC",
     "contact": "Direction", "title": "", "sector": "Condos locatifs esthétique européenne (Faubourg Boisbriand)",
     "lang": "fr", "tier": "T2", "axis": "res_qc"},
    {"name": "Groupe Alta-Socam", "domain": "altasocam.com", "city": "Boisbriand", "province": "QC",
     "contact": "Direction", "title": "", "sector": "Loggias sur le Parc (Faubourg Boisbriand)",
     "lang": "fr", "tier": "T2", "axis": "res_qc"},
    {"name": "Gestion Fauvel", "domain": "gestionfauvel.com", "city": "Drummondville", "province": "QC",
     "contact": "Direction", "title": "", "sector": "Terrains+commerces (30+ ans, Le QG complexe 30M$ 5-étages 70k sq ft)",
     "lang": "fr", "tier": "T1", "axis": "res_qc"},
    {"name": "Les Entreprises Lachance", "domain": "lachance.qc.ca", "city": "Drummondville", "province": "QC",
     "contact": "Direction", "title": "", "sector": "Maisons neuves Drummondville (Lachance famille depuis 1962, 60+ ans)",
     "lang": "fr", "tier": "T2", "axis": "res_qc"},
    {"name": "Exo Construction", "domain": "constructionexo.com", "city": "Gatineau", "province": "QC",
     "contact": "Direction", "title": "", "sector": "Promoteur résidentiel Gatineau-Ottawa",
     "lang": "fr", "tier": "T2", "axis": "res_qc"},
    {"name": "Habitations Unik", "domain": "habitationunik.com", "city": "Gatineau", "province": "QC",
     "contact": "Direction", "title": "", "sector": "Maison neuve Outaouais",
     "lang": "fr", "tier": "T2", "axis": "res_qc"},

    # ─── Agent 2/4 : Promoteurs résidentiels ON régional (22, on prend top 15) ───
    {"name": "Fusion Homes", "domain": "fusionhomes.com", "city": "Guelph", "province": "ON",
     "contact": "Lee Piccoli", "title": "Founder & CEO", "sector": "Residential — 3,300+ homes built + 329 acres Guelph Innovation District (titanic 2026-2030)",
     "lang": "en", "tier": "T1_ULTRA", "axis": "res_on"},
    {"name": "Rinaldi Homes", "domain": "rinaldihomes.com", "city": "St. Catharines", "province": "ON",
     "contact": "Jerry Rinaldi", "title": "Co-Owner (with Frank Rinaldi)", "sector": "Niagara residential (~50 homes/year × 30+ years = 1,500+ total, family since 1955)",
     "lang": "en", "tier": "T1", "axis": "res_on"},
    {"name": "Blythwood Homes", "domain": "blythwoodhomes.ca", "city": "Niagara Falls", "province": "ON",
     "contact": "Rob Mills", "title": "Founder & CEO", "sector": "Niagara residential 40+ years, multi-communities adult retirement focus",
     "lang": "en", "tier": "T1", "axis": "res_on"},
    {"name": "Ironstone Building Company", "domain": "ironstonebuilt.com", "city": "London", "province": "ON",
     "contact": "David Stimac", "title": "Co-Founder (with Allan Drewlo)", "sector": "London/Kitchener residential (1,500+ homes via Stoneridge+Drewlo, 15+ years Ironstone)",
     "lang": "en", "tier": "T1", "axis": "res_on"},
    {"name": "Geertsma Homes", "domain": "geertsma.com", "city": "Belleville", "province": "ON",
     "contact": "Andy Geertsma", "title": "Owner", "sector": "Eastern ON (Belleville/Kingston/Peterborough) — 40+ years, multi-units + retirement",
     "lang": "en", "tier": "T1", "axis": "res_on"},
    {"name": "Sider Bros Builders", "domain": "siderbros.com", "city": "Fort Erie", "province": "ON",
     "contact": "Shawn Sider", "title": "Co-Owner (with Wayne Sider)", "sector": "Niagara residential (since 1972, custom estates)",
     "lang": "en", "tier": "T2", "axis": "res_on"},
    {"name": "Gilbert + Burke Associates", "domain": "gilbertburke.ca", "city": "Peterborough", "province": "ON",
     "contact": "Brian Gilbert", "title": "Owner (since 2022)", "sector": "Peterborough/Muskoka/Kawartha cottages+homes custom, 20+ years",
     "lang": "en", "tier": "T2", "axis": "res_on"},
    {"name": "Berardi Custom Homes", "domain": "berardicustomhomes.ca", "city": "Brantford", "province": "ON",
     "contact": "Robert Berardi", "title": "Master Builder/Proprietor", "sector": "Custom homes Brantford/Hamilton/Kitchener/Guelph (Royal West Estates major)",
     "lang": "en", "tier": "T2", "axis": "res_on"},
    {"name": "Timberland Homes", "domain": "timberlandhomes.ca", "city": "Windsor", "province": "ON",
     "contact": "Gino Piccioni", "title": "Owner", "sector": "Windsor/Essex/Chatham-Kent residential — since 1996, ~25 projects/year",
     "lang": "en", "tier": "T2", "axis": "res_on"},
    {"name": "Pinevest Homes", "domain": "pinevesthomes.com", "city": "Brantford", "province": "ON",
     "contact": "Henry Stolp", "title": "Owner", "sector": "Brant County (Cedar Lane Condos, Oak Avenue, Cedar Street) — green/efficient focus",
     "lang": "en", "tier": "T2", "axis": "res_on"},
    {"name": "AT Developments", "domain": "atdevelopments.ca", "city": "Barrie", "province": "ON",
     "contact": "Joseph Santos", "title": "Founder (1998)", "sector": "Barrie rezoning specialist (Five Points Downtown 208+ units)",
     "lang": "en", "tier": "T2", "axis": "res_on"},
    {"name": "Cusinato Developments", "domain": "cusinatodevelopments.com", "city": "Sudbury", "province": "ON",
     "contact": "Paolo Cusinato", "title": "Owner", "sector": "Sudbury custom homes + subdivisions + commercial (25+ years)",
     "lang": "en", "tier": "T2", "axis": "res_on"},
    {"name": "Kaven Homes", "domain": "kaven.ca", "city": "Georgetown", "province": "ON",
     "contact": "Kyle Venne", "title": "Owner/GC", "sector": "Halton Hills/Erin/Acton design-build (ADUs/estate homes)",
     "lang": "en", "tier": "T2", "axis": "res_on"},
    {"name": "Spring Valley Homes", "domain": "springvalleyhomes.ca", "city": "Brockville", "province": "ON",
     "contact": "Direction", "title": "", "sector": "Brockville (since 1984, 200+ homes, energy-efficient features innovation)",
     "lang": "en", "tier": "T2", "axis": "res_on"},
    {"name": "Di Gregorio Developments", "domain": "digregoriodevelopments.com", "city": "Thunder Bay", "province": "ON",
     "contact": "Silvio Di Gregorio", "title": "President", "sector": "Thunder Bay 40+ years (109 units Country Club, seniors/resort/mixed-use)",
     "lang": "en", "tier": "T2", "axis": "res_on"},

    # ─── Agent 3/4 : Promoteurs commerciaux/industriels (15, on filtre les déjà touchés capital matin) ───
    {"name": "Westcliff Group", "domain": "westcliff.ca", "city": "Montréal", "province": "QC",
     "contact": "Direction", "title": "", "sector": "Centres commerciaux régionaux, mixed-use (40+ projets, 10M+ sq ft, 500+ employés)",
     "lang": "fr", "tier": "T1_ULTRA", "axis": "comm_ind"},
    {"name": "Sorbara Group of Companies", "domain": "sorbara.com", "city": "Toronto", "province": "ON",
     "contact": "Edward Sorbara", "title": "CEO (with Greg Sorbara advisory chair)", "sector": "Offices, industrial, commercial, retail — famille depuis 1942, 500+ employés",
     "lang": "en", "tier": "T1_ULTRA", "axis": "comm_ind"},
    {"name": "Skyline Group of Companies", "domain": "skylinegroupofcompanies.ca", "city": "Guelph", "province": "ON",
     "contact": "Jason Castellan", "title": "Co-founder (with Martin Castellan + Jason Ashdown)", "sector": "Apartments, commercial, retail, clean energy — $8,95 G$ AUM, 500+ employés (1999)",
     "lang": "en", "tier": "T1", "axis": "comm_ind"},
    {"name": "Effort Trust", "domain": "efforttrust.com", "city": "Hamilton", "province": "ON",
     "contact": "Direction", "title": "", "sector": "Multifamily, commercial mgmt — 11,000+ unités (150+ bâtiments), depuis 1978",
     "lang": "en", "tier": "T1", "axis": "comm_ind"},
    {"name": "Quintcap", "domain": "quintcap.com", "city": "Brossard", "province": "QC",
     "contact": "Ted Quint", "title": "Leader", "sector": "Industrial parks, retail, commercial, hôtels (4,000+ unités résidentielles, 1M+ sq ft industriel)",
     "lang": "fr", "tier": "T1", "axis": "comm_ind"},
    {"name": "Realstar Group", "domain": "realstargroup.com", "city": "Toronto", "province": "ON",
     "contact": "Jonas Prince", "title": "Co-founder (with Wayne Squibb)", "sector": "Rental residential, hospitality, alternative assets — 25,000+ unités locatives, $8 G$+ assets",
     "lang": "en", "tier": "T1_ULTRA", "axis": "comm_ind"},
    {"name": "Neudorfer Corporation", "domain": "neudorfer.com", "city": "Toronto", "province": "ON",
     "contact": "Direction", "title": "", "sector": "Residential condos + commercial mixed-use (famille 40 ans)",
     "lang": "en", "tier": "T2", "axis": "comm_ind"},
    {"name": "Europro", "domain": "europro.ca", "city": "Kitchener", "province": "ON",
     "contact": "Direction", "title": "", "sector": "Class A offices + regional shopping centres + service retail (Kitchener/Windsor/Barrie, family-run 2003)",
     "lang": "en", "tier": "T2", "axis": "comm_ind"},
    {"name": "Asgaard Inc.", "domain": "asgaard.ca", "city": "Montréal", "province": "QC",
     "contact": "Max Francischiello", "title": "Président", "sector": "Office, commercial, industrial portfolio diversifié + dev",
     "lang": "fr", "tier": "T2", "axis": "comm_ind"},
    {"name": "Entreprise EGB", "domain": "entrepriseegb.com", "city": "Lévis", "province": "QC",
     "contact": "Gyno Boivin", "title": "Président", "sector": "Industrial, commercial, retail South Shore Québec",
     "lang": "fr", "tier": "T2", "axis": "comm_ind"},
    {"name": "Park Property Management", "domain": "parkproperty.ca", "city": "Toronto", "province": "ON",
     "contact": "Direction", "title": "", "sector": "Residential + commercial mgmt SW Ontario (12,000+ unités / 95 bâtiments, 50 ans)",
     "lang": "en", "tier": "T1", "axis": "comm_ind"},

    # ─── Agent 4/4 : Promoteurs spécialisés / sortie financement (12, on filtre Germain/Concert déjà capital matin) ───
    {"name": "Schlegel Villages", "domain": "schlegelvillages.com", "city": "Kitchener", "province": "ON",
     "contact": "Direction (famille Schlegel)", "title": "", "sector": "Retirement communities + LTC (8+ villages, 2,500+ seniors, 3 générations depuis 1991)",
     "lang": "en", "tier": "T1", "axis": "specialise"},
    {"name": "Symphony Senior Living", "domain": "symphonyseniorliving.com", "city": "Ottawa", "province": "ON",
     "contact": "Lisa Brush", "title": "Founder (2008)", "sector": "Retirement communities (4 Ottawa, 11 total Canada)",
     "lang": "en", "tier": "T2", "axis": "specialise"},
    {"name": "Verve Senior Living", "domain": "verveseniorliving.com", "city": "Toronto", "province": "ON",
     "contact": "Direction", "title": "", "sector": "Retirement residences (30+ communities, ~4,000 unités)",
     "lang": "en", "tier": "T2", "axis": "specialise"},
    {"name": "Self Stor Storage", "domain": "selfstor.ca", "city": "Toronto", "province": "ON",
     "contact": "Direction", "title": "", "sector": "Self-storage 5 facilities GTA + Guelph (famille canadienne 30 ans, depuis 1996)",
     "lang": "en", "tier": "T2", "axis": "specialise"},
    {"name": "Vaultra Storage", "domain": "vaultrastorage.ca", "city": "Toronto", "province": "ON",
     "contact": "Direction", "title": "", "sector": "Self-storage 100% canadien (ON+AB expansion rapide, 5-7 facilities)",
     "lang": "en", "tier": "T2", "axis": "specialise"},
    {"name": "Dymon Storage Corp.", "domain": "dymon.ca", "city": "Ottawa", "province": "ON",
     "contact": "Direction", "title": "", "sector": "Self-storage Ottawa (7 facilities + 80 TGA en pipeline développement)",
     "lang": "en", "tier": "T1", "axis": "specialise"},
    {"name": "Duka Property Management", "domain": "dukamanagement.com", "city": "Toronto", "province": "ON",
     "contact": "Direction", "title": "", "sector": "Development PM + condo mgmt boutique (Toronto/Mississauga/Ottawa, +1000 projets)",
     "lang": "en", "tier": "T2", "axis": "specialise"},
]


def hunter_domain_search(domain: str, api_key: str, limit: int = 10) -> dict | None:
    url = (
        "https://api.hunter.io/v2/domain-search?"
        + urllib.parse.urlencode({"domain": domain, "api_key": api_key, "limit": limit})
    )
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


PRIORITY_TITLES = ["owner","founder","co-founder","chairman","president","ceo","chief executive",
                   "executive chairman","co-chair","managing partner","managing director","partner",
                   "vp","vice president","head","chief financial","cfo","directeur g","président"]


def score_email(e: dict) -> int:
    t = (e.get("position") or "").lower()
    for i, kw in enumerate(PRIORITY_TITLES):
        if kw in t:
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
        print("⚠️ HUNTER_API_KEY manquant", file=sys.stderr)
        return 1

    exclusion = load_exclusion("/tmp/already_solicited_2026-05-27.csv")
    print(f"📂 Exclusion list : {len(exclusion)} emails déjà touchés")
    print(f"🎯 Cibles brutes : {len(TARGETS)}")
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
            print(f"❌ {t.get('hunter_error', '?')[:50]}")
            enriched.append(t)
            time.sleep(1)
            continue

        data = result.get("data") or {}
        emails_raw = data.get("emails") or []
        filtered = []
        for e in emails_raw:
            em = (e.get("value") or "").strip().lower()
            if not em:
                continue
            if em in exclusion:
                exclusion_hits.append({"target": t["name"], "email": em,
                                       "name": f"{e.get('first_name','')} {e.get('last_name','')}".strip(),
                                       "position": e.get("position","")})
                continue
            filtered.append({
                "email": em,
                "name": f"{e.get('first_name','') or ''} {e.get('last_name','') or ''}".strip(),
                "position": e.get("position") or "",
                "linkedin": e.get("linkedin") or "",
                "confidence": e.get("confidence", 0),
                "score": score_email(e),
            })
        filtered.sort(key=lambda x: (-x["score"], -x["confidence"]))

        t["hunter_status"] = "ok"
        t["hunter_pattern"] = data.get("pattern") or ""
        t["emails"] = filtered[:6]
        t["emails_count_raw"] = len(emails_raw)
        t["emails_count_after_exclusion"] = len(filtered)
        top = filtered[0]["email"] if filtered else "aucun"
        print(f"✅ {len(emails_raw)} bruts / {len(filtered)} après-excl / top: {top}")
        enriched.append(t)
        time.sleep(1.1)

    out = "/tmp/fresh_promoteurs_2026-05-27_enriched.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"audit_date": "2026-05-27_pm",
                   "total_targets": len(TARGETS),
                   "exclusion_list_size": len(exclusion),
                   "exclusion_hits": len(exclusion_hits),
                   "targets": enriched,
                   "exclusion_hits_detail": exclusion_hits}, f, indent=2, ensure_ascii=False)

    ok = sum(1 for t in enriched if t.get("hunter_status") == "ok")
    no_email = sum(1 for t in enriched if t.get("hunter_status") == "ok"
                    and t.get("emails_count_after_exclusion", 0) == 0)
    total_emails = sum(t.get("emails_count_after_exclusion", 0) for t in enriched)
    print()
    print("=" * 70)
    print(f"📄 JSON enrichi : {out}")
    print(f"✅ Cibles OK            : {ok}/{len(TARGETS)}")
    print(f"📧 Total emails (post-excl): {total_emails}")
    print(f"⚠️ Cibles sans email     : {no_email}")
    print(f"🚫 Hits exclusion         : {len(exclusion_hits)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
