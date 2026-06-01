"""Agent PROMOTEURS — prospector automatique.

Découvre automatiquement des promoteurs immobiliers privés au Québec via
recherche web Claude API, puis filtre strictement selon les critères
Capital Norvex.

CIBLES (✅) :
- Construction immeubles à revenus (multi-locatif 6+ unités)
- Construction commerciale (bureaux, hôtels, centres commerciaux)
- Construction industrielle (entrepôts, usines)
- Développement de terrain
- Acquisition-reconversion immobilière

EXCLUSIONS (❌) :
- Gestionnaires d'immeubles (BOMA-style)
- Routes, ponts, infrastructures publiques, voirie, aqueducs
- Construction résidentielle unifamiliale ou < 6 unités
- Génie civil lourd
- Courtiers immobiliers (différent de promoteurs)

Usage:
    python -m agents.promoteurs.prospector --region grand-mtl --max 20
    python -m agents.promoteurs.prospector --region rive-sud --max 10 --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..shared import firestore_client as fs

AGENT_NAME = "promoteurs_prospector"


# ─── Config ─────────────────────────────────────────────────────────────────

REGIONS = {
    "ile-mtl": "île de Montréal",
    "laval": "Laval",
    "rive-nord": "Rive-Nord de Montréal (Terrebonne, Mascouche, Boisbriand, Mirabel, Blainville, Sainte-Thérèse)",
    "rive-sud": "Rive-Sud de Montréal (Longueuil, Brossard, Boucherville, Saint-Bruno, Chambly, Saint-Jean-sur-Richelieu)",
    "lanaudiere": "Lanaudière (Repentigny, L'Assomption, Joliette)",
    "monteregie": "Montérégie (Saint-Hyacinthe, Vaudreuil-Dorion, Granby)",
    "laurentides": "Laurentides (Saint-Jérôme, Sainte-Adèle, Saint-Sauveur, Mont-Tremblant)",
}

# Mots-clés d'exclusion (rejet immédiat dans le nom/description)
EXCLUSION_KEYWORDS = [
    # Infrastructures publiques
    "ingénierie civile", "génie civil", "infrastructure publique",
    "routes", "route", "ponts", "pont", "autoroute", "voirie",
    "aqueduc", "égout", "réseau pluvial", "trottoirs",
    "transport en commun", "métro", "rail",
    # Gestionnaires (pas promoteurs)
    "gestion immobilière", "gestionnaire d'immeubles", "property management",
    "syndic de copropriété", "gérance",
    # Résidentiel petit
    "maisons unifamiliales", "résidentiel unifamilial",
    "constructeur de maisons", "maisons modèles",
    "rénovation résidentielle",
    # Hors scope
    "courtier immobilier", "agent immobilier", "real estate broker",
    "evaluation immobilière", "évaluateur agréé",
    # Petits entrepreneurs
    "rénovation", "entrepreneur général résidentiel",
    "menuiserie", "plomberie", "électricien",
]

# Mots-clés positifs (boost score)
POSITIVE_KEYWORDS = [
    "promoteur immobilier", "développeur immobilier", "developer",
    "immeuble à revenus", "immeuble locatif", "multilogement", "multi-rés",
    "tour résidentielle", "tour à condos", "complexe résidentiel",
    "centre commercial", "tour de bureaux", "complexe commercial",
    "entrepôt", "industriel", "centre de distribution",
    "développement de terrain", "subdivision",
    "construction commerciale", "construction industrielle",
    "construction multi-résidentielle", "multi-residential construction",
]


# ─── Recherche Claude API ───────────────────────────────────────────────────

def _claude_search_promoters(region_label: str, max_results: int = 20) -> Dict[str, Any]:
    """Cherche des promoteurs via Claude API web_search.

    Retourne {promoters: [{name, companyName, city, type, website, recentProject, source, evidence}]}.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY manquant")

    try:
        import anthropic
    except ImportError:
        raise RuntimeError("pip install anthropic")

    client = anthropic.Anthropic(api_key=api_key)

    sys_prompt = (
        "Tu es l'agent PROSPECTOR de Capital Norvex Inc., qui finance des projets "
        "immobiliers commerciaux et multi-résidentiels privés au Québec.\n\n"
        "Ta mission : trouver des PROMOTEURS IMMOBILIERS PRIVÉS actifs, qui développent :\n"
        "- Immeubles à revenus locatifs (6+ unités)\n"
        "- Construction commerciale (bureaux, hôtels, centres commerciaux)\n"
        "- Construction industrielle (entrepôts, usines)\n"
        "- Développement de terrain pour construction\n\n"
        "TU DOIS REJETER ABSOLUMENT :\n"
        "- Firmes d'ingénierie civile (routes, ponts, infrastructures)\n"
        "- Gestionnaires d'immeubles (sans promotion)\n"
        "- Constructeurs résidentiels unifamiliaux\n"
        "- Petits entrepreneurs (rénovation, menuiserie, plomberie)\n"
        "- Courtiers/agents immobiliers\n\n"
        "Sources prioritaires : IDU Québec membres, Constructo.ca, Les Affaires, "
        "communiqués de presse de projets immobiliers récents (24 mois), permis "
        "de construction municipaux.\n\n"
        "Réponds en JSON STRICT, aucun texte avant/après. Si tu ne trouves rien "
        "de qualifié, retourne {\"promoters\": []}."
    )

    user_msg = (
        f"Trouve jusqu'à {max_results} promoteurs immobiliers privés ACTIFS dans la région : "
        f"**{region_label}**.\n\n"
        "Chaque promoteur doit avoir un projet RÉCENT (24 derniers mois) de "
        "minimum 2,5 M$ en construction commerciale, multi-résidentielle (6+ unités), "
        "industrielle ou en développement de terrain.\n\n"
        "Format JSON requis :\n"
        "{\n"
        '  "promoters": [\n'
        "    {\n"
        '      "companyName": "Nom légal de l\'entreprise",\n'
        '      "principalContact": "Nom du président/fondateur si connu",\n'
        '      "city": "Ville principale",\n'
        '      "region": "ile-mtl|laval|rive-nord|rive-sud|lanaudiere|monteregie|laurentides",\n'
        '      "projectTypes": ["multi-rés"|"commercial"|"industriel"|"terrain"|"acquisition"],\n'
        '      "website": "https://...",\n'
        '      "recentProject": "Nom du projet récent et description courte",\n'
        '      "estimatedProjectValue": "ex: 25 M$",\n'
        '      "source": "URL de la source",\n'
        '      "evidence": "Citation directe de la source qui confirme l\'activité",\n'
        '      "language": "fr"|"en"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Ne JAMAIS inventer. Si une info manque, mets null. "
        "Inclus uniquement des entreprises avec preuves publiques vérifiables."
    )

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=sys_prompt,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": user_msg}],
    )

    text = ""
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            text += block.text

    try:
        start = text.find("{")
        end = text.rfind("}")
        return json.loads(text[start:end + 1])
    except Exception as e:
        print(f"⚠️  JSON parse failed: {e}")
        print(f"Raw text: {text[:500]}")
        return {"promoters": []}


# ─── Filtrage ───────────────────────────────────────────────────────────────

def _is_excluded(promoter: Dict[str, Any]) -> Optional[str]:
    """Retourne la raison d'exclusion ou None si la cible passe le filtre."""
    text = " ".join([
        str(promoter.get("companyName", "")),
        str(promoter.get("recentProject", "")),
        str(promoter.get("evidence", "")),
        " ".join(promoter.get("projectTypes", []) or []),
    ]).lower()

    for kw in EXCLUSION_KEYWORDS:
        if kw.lower() in text:
            return f"exclusion_keyword:{kw}"

    project_types = [t.lower() for t in (promoter.get("projectTypes") or [])]
    if not project_types:
        return "no_project_types"

    valid_types = {"multi-rés", "multi-res", "multilogement", "commercial",
                   "industriel", "industrial", "terrain", "land", "acquisition"}
    if not any(t in valid_types for t in project_types):
        return f"no_valid_project_type:{project_types}"

    return None


def _score_promoter(promoter: Dict[str, Any]) -> int:
    """Score 0-100. + pour signaux positifs, indicateurs de taille."""
    score = 50
    text = " ".join([
        str(promoter.get("companyName", "")),
        str(promoter.get("recentProject", "")),
        str(promoter.get("evidence", "")),
    ]).lower()

    for kw in POSITIVE_KEYWORDS:
        if kw.lower() in text:
            score += 5

    value = str(promoter.get("estimatedProjectValue", "")).lower()
    if "100 m" in value or "100m" in value or "milliard" in value:
        score += 20
    elif "50 m" in value or "50m" in value:
        score += 15
    elif "25 m" in value or "25m" in value or "20 m" in value:
        score += 10
    elif "10 m" in value or "10m" in value:
        score += 5

    if promoter.get("website"):
        score += 3
    if promoter.get("principalContact"):
        score += 5

    return min(100, max(0, score))


# ─── Pipeline principal ─────────────────────────────────────────────────────

def run_prospector(
    region: str,
    max_results: int = 20,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Lance le prospector pour une région."""
    if region not in REGIONS:
        raise ValueError(f"Région inconnue : {region}. Options : {list(REGIONS.keys())}")

    region_label = REGIONS[region]
    print(f"🔍 Prospection : {region_label}")
    print(f"   Max résultats demandés : {max_results}")
    print()

    # 1. Recherche Claude
    raw = _claude_search_promoters(region_label, max_results)
    promoters = raw.get("promoters") or []
    print(f"📥 Trouvés (brut) : {len(promoters)}")

    # 2. Dédoublonnage contre Firestore existant
    existing = fs.query("promoteurTargets", limit=1000)
    existing_names = {(p.get("companyName") or "").strip().lower() for p in existing}
    deduped = [p for p in promoters
               if (p.get("companyName") or "").strip().lower() not in existing_names]
    skipped_dup = len(promoters) - len(deduped)
    if skipped_dup:
        print(f"   ↳ {skipped_dup} doublons écartés (déjà en base)")

    # 3. Filtrage
    accepted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for p in deduped:
        reason = _is_excluded(p)
        if reason:
            rejected.append({**p, "_rejection_reason": reason})
        else:
            p["_score"] = _score_promoter(p)
            accepted.append(p)

    accepted.sort(key=lambda x: x.get("_score", 0), reverse=True)

    print(f"✅ Acceptés : {len(accepted)}")
    print(f"❌ Rejetés : {len(rejected)}")
    if rejected:
        print("   Raisons :")
        from collections import Counter
        reasons = Counter(r["_rejection_reason"] for r in rejected)
        for reason, count in reasons.most_common(5):
            print(f"     - {reason}: {count}")

    # 4. Affichage
    print()
    print("📋 ACCEPTÉS (triés par score) :")
    for i, p in enumerate(accepted, 1):
        print(f"  {i}. [{p.get('_score', 0):3d}] {p.get('companyName', '?')} "
              f"({p.get('city', '?')}) — {', '.join(p.get('projectTypes', []) or [])}")
        if p.get("recentProject"):
            print(f"      📌 {p['recentProject'][:120]}")

    # 5. Sauvegarde Firestore
    if not dry_run and accepted:
        print()
        print("💾 Sauvegarde Firestore (promoteurTargets)…")
        now = datetime.now(timezone.utc).isoformat()
        for p in accepted:
            doc = {
                "companyName": p.get("companyName"),
                "principalContact": p.get("principalContact"),
                "city": p.get("city"),
                "region": p.get("region") or region,
                "projectTypes": p.get("projectTypes"),
                "website": p.get("website"),
                "recentProject": p.get("recentProject"),
                "estimatedProjectValue": p.get("estimatedProjectValue"),
                "source": p.get("source"),
                "evidence": p.get("evidence"),
                "language": p.get("language") or "fr",
                "score": p.get("_score"),
                "status": "pending_review",
                "tier": "auto",
                "discoveredAt": now,
                "discoveredBy": AGENT_NAME,
                "protectedFlag": False,
            }
            doc_id = fs.create("promoteurTargets", doc)
            print(f"   ✅ {doc_id} — {p.get('companyName')}")

    # 6. Audit
    fs.audit_log(
        agent=AGENT_NAME,
        action="prospector_run",
        target_id=None,
        details={
            "region": region,
            "raw_count": len(promoters),
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "dry_run": dry_run,
        },
    )

    return {
        "region": region,
        "raw": len(promoters),
        "accepted": accepted,
        "rejected": rejected,
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", required=True, choices=list(REGIONS.keys()))
    parser.add_argument("--max", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true",
                        help="N'écrit pas en Firestore, affiche seulement")
    args = parser.parse_args()

    try:
        run_prospector(args.region, max_results=args.max, dry_run=args.dry_run)
        return 0
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
