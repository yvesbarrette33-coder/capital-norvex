"""
Discover law firm advisors via Hunter Domain Search — 2026-05-07.

Phase 1 « Trusted Advisors » : 30 cabinets QC/ON (Langlois EXCLU).
Pour chaque cabinet :
  1. Hunter Domain Search → tous les emails publics
  2. Filtre titres : Tax / Estate / M&A privé / Family Office / Patrimoine
  3. Skip ceux déjà dans capitalTargets (par email)
  4. Crée doc capitalTargets avec relationshipStatus='pending_review'
     (Yves valide UN À UN avant tout envoi)

USAGE :
  python -m agents.capital.discover_law_firms --dry              # simulation, pas d'écriture
  python -m agents.capital.discover_law_firms --dry --limit 2    # test sur 2 cabinets seulement
  python -m agents.capital.discover_law_firms                    # exécute pour de vrai
  python -m agents.capital.discover_law_firms --firm stikeman    # 1 cabinet précis

⚠️ JAMAIS d'envoi automatique. Tous les contacts créés sont en pending_review.
"""
from __future__ import annotations

import csv
import os
import sys
import time
import argparse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from agents.shared.firestore_client import db, audit_log, query as fs_query
from agents.capital._law_firms_qc_on import LAW_FIRMS, EXCLUDED

# Charge ~/.capitalnorvex/.env
load_dotenv(os.path.expanduser("~/.capitalnorvex/.env"))

HUNTER_API_KEY = os.environ.get("HUNTER_API_KEY")
if not HUNTER_API_KEY:
    print("❌ HUNTER_API_KEY introuvable dans ~/.capitalnorvex/.env")
    sys.exit(1)

HUNTER_BASE = "https://api.hunter.io/v2"
COLLECTION = "capitalTargets"

# MODE STRICT : on ne garde QUE les titres explicites (fiscalité/successoral/M&A/Family Office/Trusts/Wealth)
# « partner » seul = REJETÉ (trop générique)
# « famille » seul = REJETÉ (= droit de la famille / divorce, pas patrimoine)
TARGET_TITLE_KEYWORDS = [
    # Fiscalité
    "tax", "fiscal", "fiscalité", "fiscaliste", "fiscale", "fiscaux",
    # Successoral / Estate
    "estate", "estates", "succession", "successoral", "successorale", "successions",
    # Trusts / Fiducies
    "trust", "trusts", "fiducie", "fiduciaire", "fiduciaires",
    # Patrimoine / Wealth
    "patrimoine", "patrimonial", "patrimoniale",
    "wealth", "private wealth", "private client", "private clients",
    # Family Office / Family Business / Family Enterprise (PAS juste "famille")
    "family office", "family enterprise", "family business",
    "family wealth", "family advisory",
    # Private Capital / Private Equity / M&A
    "private capital", "private equity", "private m&a",
    "m&a", "mergers", "mergers and acquisitions",
    "fusions et acquisitions", "fusions-acquisitions",
    # UHNW
    "uhnw", "high net worth", "high-net-worth", "ultra high",
]

# Mots-clés DISQUALIFIANTS (pas le bon profil pour notre pitch)
EXCLUDE_TITLE_KEYWORDS = [
    "marketing", "communication", "communications",
    "ressources humaines", "human resources", "hr",
    "recruteur", "recruiter", "recruitment", "talent",
    "stagiaire", "student", "stagiaires", "summer associate",
    "comptable", "accounting", "comptabilité",
    "réceptionniste", "receptionist",
    "litigation", "litige",  # contentieux pur peu pertinent
    "criminal", "criminel", "criminelle",
    "immigration", "labour", "labor", "employment",
    "famille", "family law",  # droit de la famille = divorce, PAS patrimoine
    "real estate broker", "courtier immobilier",
    "real estate agent", "agent immobilier",
    "real estate paralegal", "real estate assistant",
    "paralegal", "parajuriste", "parajuristes",
    "law clerk", "law clerks", "legal assistant", "legal assistants",
    "adjoint", "adjointe", "adjoints", "adjointes",  # adjoint juridique
    "secretary", "secrétaire",
    "articling", "articling student", "stagiaire en droit",
    "summer student", "étudiant",
    "intellectual property", "propriété intellectuelle", "ip ",
    "construction law", "droit de la construction",
]


def title_matches(position: Optional[str]) -> Optional[str]:
    """Retourne le mot-clé matché si position pertinent, sinon None."""
    if not position:
        return None
    p = position.lower()
    # Disqualification
    for bad in EXCLUDE_TITLE_KEYWORDS:
        if bad in p:
            return None
    # Match positif
    for kw in TARGET_TITLE_KEYWORDS:
        if kw in p:
            return kw
    return None


def hunter_domain_search(domain: str, limit: int = 100) -> Dict[str, Any]:
    """Appel Hunter Domain Search. 1 crédit par appel (pas par email retourné)."""
    url = f"{HUNTER_BASE}/domain-search"
    params = {"domain": domain, "api_key": HUNTER_API_KEY, "limit": limit}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def existing_emails_in_firestore() -> set:
    """Récupère tous les emails déjà dans capitalTargets pour dédup."""
    emails = set()
    docs = fs_query(COLLECTION, limit=2000)
    for d in docs:
        pc = d.get("publicContact") or {}
        e = (pc.get("email") or "").strip().lower()
        if e:
            emails.add(e)
        # Aussi le champ "email" top-level si présent
        e2 = (d.get("email") or "").strip().lower()
        if e2:
            emails.add(e2)
    return emails


def build_target_doc(
    firm_slug: str,
    firm_name: str,
    domain: str,
    province: str,
    person: Dict[str, Any],
    matched_kw: str,
) -> Dict[str, Any]:
    """Construit un doc capitalTargets prêt pour Firestore."""
    first = (person.get("first_name") or "").strip()
    last = (person.get("last_name") or "").strip()
    full_name = f"{first} {last}".strip() or "(à identifier)"
    position = (person.get("position") or "").strip()
    email = (person.get("value") or "").strip().lower()
    confidence = person.get("confidence") or 0
    linkedin = person.get("linkedin") or ""
    twitter = person.get("twitter") or ""
    phone = person.get("phone_number") or ""

    # Région : QC ou ON (multi = on prend QC par défaut, ajustable)
    region = "QC" if "QC" in province else "ON"
    # Langue par règle 2026-05-06 : ON → EN, QC → FR
    language = "fr" if region == "QC" else "en"

    return {
        "name": full_name,
        "organization": firm_name,
        "category": "advisor_law_firm",  # nouvelle catégorie
        "advisorType": "lawyer",
        "tier": "tier_one_advisor",
        "region": region,
        "language": language,
        "title": position,
        "investmentThesis": (
            "Cabinet d'avocats — relais vers UHNW / family offices "
            "(fiscalité, planification successorale, M&A privé, patrimoine)."
        ),
        "approachAngle": (
            "Programme de référencement Capital Norvex : prêts construction/refi "
            "10-12% pour leurs clients fortunés. Partenariat conseiller, pas pitch direct."
        ),
        "publicContact": {
            "email": email,
            "phone": phone,
            "linkedin": linkedin,
            "twitter": twitter,
            "website": f"https://{domain}",
            "_enrichedBy": "hunter.io/domain-search",
            "_enrichedAt": datetime.now(timezone.utc).isoformat(),
            "_hunterConfidence": confidence,
            "_matchedKeyword": matched_kw,
        },
        "relationshipStatus": "pending_review",  # ⚠️ Yves valide AVANT envoi
        "createdBy": "discover_law_firms_2026-05-07",
        "sourceUrl": f"https://{domain}",
        "_firmSlug": firm_slug,
        "_firmDomain": domain,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true", help="Simulation, aucune écriture")
    parser.add_argument("--limit", type=int, default=None, help="Limite de cabinets traités")
    parser.add_argument("--firm", type=str, default=None, help="Slug d'un cabinet précis")
    parser.add_argument("--max-per-firm", type=int, default=15, help="Max contacts par cabinet")
    args = parser.parse_args()

    # Garde-fou Langlois
    for slug, name, domain, *_ in LAW_FIRMS:
        if domain in EXCLUDED or "langlois" in slug.lower():
            print(f"❌ Cabinet exclu détecté dans la liste : {slug}/{domain}")
            sys.exit(1)

    firms = LAW_FIRMS
    if args.firm:
        firms = [f for f in firms if f[0] == args.firm]
        if not firms:
            print(f"❌ Cabinet '{args.firm}' introuvable")
            sys.exit(1)
    if args.limit:
        firms = firms[: args.limit]

    print(f"\n{'🟡 DRY-RUN' if args.dry else '🚀 EXÉCUTION'} — {len(firms)} cabinets\n")
    print("📥 Chargement emails existants Firestore (dédup)…")
    existing = existing_emails_in_firestore()
    print(f"   {len(existing)} emails déjà connus\n")

    fs = db()
    total_created = 0
    total_skipped_dedup = 0
    total_filtered_out = 0
    total_credits = 0
    summary_per_firm = []
    csv_rows = []  # Preview CSV — toujours rempli (dry ou pas)

    for i, (slug, firm_name, domain, province, size, practices) in enumerate(firms, 1):
        print(f"[{i}/{len(firms)}] {firm_name} ({domain}) — {province}")
        try:
            payload = hunter_domain_search(domain)
        except Exception as e:
            print(f"   ❌ Hunter erreur : {e}")
            summary_per_firm.append((firm_name, 0, 0, 0, "ERROR"))
            continue
        total_credits += 1

        data = payload.get("data") or {}
        emails = data.get("emails") or []
        kept = []
        skipped_dedup = 0
        filtered_out = 0

        for person in emails:
            email = (person.get("value") or "").strip().lower()
            if not email:
                continue
            matched = title_matches(person.get("position"))
            if not matched:
                filtered_out += 1
                continue
            if email in existing:
                skipped_dedup += 1
                continue
            kept.append((person, matched))
            existing.add(email)  # évite doublons intra-batch

        # Cap par cabinet
        kept = kept[: args.max_per_firm]

        for person, matched in kept:
            doc = build_target_doc(slug, firm_name, domain, province, person, matched)
            csv_rows.append({
                "firm": firm_name,
                "domain": domain,
                "province": province,
                "name": doc["name"],
                "title": doc["title"],
                "email": doc["publicContact"]["email"],
                "matched_keyword": matched,
                "confidence": doc["publicContact"]["_hunterConfidence"],
                "linkedin": doc["publicContact"]["linkedin"],
            })
            if args.dry:
                print(f"   🔍 {doc['name']:35s} | {doc['title'][:40]:40s} | {doc['publicContact']['email']}")
            else:
                try:
                    doc_id = fs.collection(COLLECTION).add({
                        **doc,
                        "createdAt": datetime.now(timezone.utc),
                        "lastUpdated": datetime.now(timezone.utc),
                    })[1].id
                    audit_log(
                        agent="discover_law_firms",
                        action="create_advisor_target",
                        target_type=COLLECTION,
                        target_id=doc_id,
                        result="success",
                        details={
                            "firm": firm_name,
                            "name": doc["name"],
                            "email": doc["publicContact"]["email"],
                            "title": doc["title"],
                            "matched_keyword": matched,
                        },
                    )
                    print(f"   ✅ {doc['name']:35s} | {doc['title'][:40]:40s} | {doc['publicContact']['email']}")
                except Exception as e:
                    print(f"   ❌ Erreur écriture {doc['name']} : {e}")

        total_created += len(kept)
        total_skipped_dedup += skipped_dedup
        total_filtered_out += filtered_out
        summary_per_firm.append((firm_name, len(kept), skipped_dedup, filtered_out, "OK"))
        print(f"   → {len(kept)} retenus | {skipped_dedup} déjà connus | {filtered_out} hors-cible")
        time.sleep(0.5)  # politesse API

    print(f"\n— Résumé global —")
    print(f"  Cabinets traités       : {len(firms)}")
    print(f"  Crédits Hunter utilisés: {total_credits}")
    print(f"  {'Drafts simulés' if args.dry else 'Drafts créés'}        : {total_created}")
    print(f"  Sautés (dédup)         : {total_skipped_dedup}")
    print(f"  Filtrés (hors-cible)   : {total_filtered_out}")
    print(f"\n  Statut : {'pending_review' if not args.dry else '(dry-run, rien écrit)'}")
    print(f"  ⚠️  Aucun envoi — Yves valide manuellement avant que les drafts partent.\n")

    print("— Détails par cabinet —")
    for name, kept, skipped, filt, status in summary_per_firm:
        print(f"  [{status}] {name[:35]:35s}  retenus={kept:3d}  dédup={skipped:3d}  hors-cible={filt:3d}")

    # CSV preview pour validation Yves
    if csv_rows:
        csv_path = os.path.expanduser(
            f"~/Downloads/discover_law_firms_preview_{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M')}.csv"
        )
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"\n📄 CSV preview écrit : {csv_path}")
        print(f"   ({len(csv_rows)} lignes — ouvre dans Numbers pour valider)")


if __name__ == "__main__":
    main()
