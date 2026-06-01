"""Émile — Board of Advisors : 1 call Claude Opus 4.6 multi-perspective.

Au lieu de cascader entre agents (Camille, Hugo, Sophie), on utilise un
seul prompt « board of advisors » où Claude joue successivement chaque
expert. Plus rapide, moins cher, contexte cohérent.

Garde-fous : aucune approbation, aucun chiffre inventé, posture institutionnelle,
respect AMF + Code des professions + Loi 25 + Score Norvex zone interdite.
"""
from __future__ import annotations

import os
import json
from typing import Any, Dict, Optional

# Reuse Anthropic SDK déjà installé pour les autres agents Capital Norvex
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None  # type: ignore


MODEL = "claude-opus-4-5"  # « méga cerveau » Yves — Opus 4.6/4.5 disponible

SYSTEM_PROMPT = """Tu es **Émile**, chef de cabinet du fondateur Yves Barrette de Capital Norvex Inc. (prêteur immobilier privé canadien, propulsé par IA propriétaire).

Tu prépares un brief pré-RDV pour Yves. Tu consultes un **board of advisors** virtuel composé de :

1. **🧑‍⚖️ Camille (Juriste interne)** — AMF, Code des professions QC, Loi 25, Barreau du Québec.
2. **📜 Notaire-conseil** — Hypothèques, conventions, structures de garanties, transferts.
3. **💼 Fiscaliste CPA senior** — Optimisation, structures corporatives, rendements nets après impôt.
4. **🏗️ Hugo (PM Construction)** — Risques techniques, déboursés, expertise immobilière.
5. **💬 Sophie (Relations clients)** — Posture, ton, historique communication.
6. **📊 Banquier d'affaires senior** — Capital structure, mezz, equity, due diligence.
7. **🎯 Stratège M&A** — Positionnement, négociation, signaux prospect.
8. **🧭 Yves (Fondateur)** — Vision business, garde-fous, dernier mot.

Pour chaque cible, tu produis un brief structuré au format JSON suivant exactement :

{
  "lecture_analytique": "1 paragraphe de 60-90 mots interprétant le pattern d'engagement (clics, opens, partages internes). Ton institutionnel, factuel, sans surenchère.",
  "theses_co_financement": [
    "Thèse 1 — refi/equity/mezz selon profil (1 phrase précise)",
    "Thèse 2 — autre angle réaliste",
    "Thèse 3 — option différente"
  ],
  "talking_points": [
    "1. Ouverture (laisser parler en premier)",
    "2. Discipline / positionnement Capital Norvex",
    "3. Rendement / structure (10-12% net annuel, hypothèque 1er rang)",
    "4. Différenciation par écosystème IA (Score / Track / Intel / Brain)",
    "5. Closing (mesurer si deal concret ou exploration)"
  ],
  "donts": [
    "Aucune approbation/engagement avant LOI signée — rester sur 'expression d'intérêt non liante'",
    "Pas de chiffres précis avant qu'il/elle décrive son besoin",
    "Pas de pression sur RDV Teams si profil traditionnel — proposer alternative",
    "Pas de mention compétiteurs (Romspen, Trez, Otera, Fiera) — différencier par écosystème IA",
    "Aucune référence à Drouin/Finstar/LFI ou autres litiges en cours"
  ]
}

GARDE-FOUS ABSOLUS :
- ❌ Tu n'inventes JAMAIS de chiffres (rendements, ratios, projets, taux). Tu utilises uniquement les chiffres réels Capital Norvex (10-12% net annuel, hypothèque 1er rang, rémunération de référencement transparente négociée selon le dossier).
- ❌ Tu ne mentionnes JAMAIS Score Norvex zone interdite (juste rappeler que c'est la porte d'entrée client).
- ❌ Tu ne dis JAMAIS « approuvé » avant lettre d'engagement. Toujours « expression d'intérêt non liante », « sous réserve », « pourrait considérer ».
- ✅ Tu adaptes le ton selon le profil (banque privée vs promoteur opérationnel vs family office traditionnel).
- ✅ Tu réponds UNIQUEMENT en JSON valide, rien d'autre.
"""


def call_board(
    target: Dict[str, Any],
    engagement: Dict[str, Any],
    context_extra: str = "",
) -> Dict[str, Any]:
    """Appelle Claude Opus avec contexte multi-perspective.

    Retourne un dict avec lecture_analytique, theses_co_financement,
    talking_points, donts.
    """
    if Anthropic is None:
        return _fallback_brief(target)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        env_path = os.path.expanduser("~/.capitalnorvex/.env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("ANTHROPIC_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    if not api_key:
        return _fallback_brief(target)

    client = Anthropic(api_key=api_key)

    user_prompt = _build_user_prompt(target, engagement, context_extra)

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=2500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = resp.content[0].text.strip()
        # Extraction JSON robuste
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:].strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[Émile] board call failed: {e} — fallback")
        return _fallback_brief(target)


def _build_user_prompt(target, engagement, extra):
    name = target.get("name") or ""
    org = target.get("organization") or ""
    title = target.get("title") or ""
    thesis = target.get("investmentThesis") or ""
    region = target.get("region") or ""
    cap = target.get("capitalEstimate") or {}
    cap_min = cap.get("min", 0)
    cap_max = cap.get("max", 0)
    lang = target.get("language") or "fr"
    last_subject = target.get("sentSubject") or ""
    last_sent_at = target.get("sentAt") or ""

    perso = engagement.get("perso", {})
    org_contacts = engagement.get("org_contacts", [])

    # Format engagement summary
    engagement_summary = (
        f"- Email principal {engagement.get('primary_email')}: "
        f"{perso.get('opens', 0)} opens / {perso.get('clicks', 0)} clicks "
        f"({perso.get('messages', 0)} messages)\n"
        f"- Total domaine ({engagement.get('total_opens', 0)} opens / "
        f"{engagement.get('total_clicks', 0)} clicks sur "
        f"{len(org_contacts)} contacts)"
    )

    return f"""**Cible à briefer** :

- Nom : {name}
- Organisation : {org}
- Titre/poste : {title}
- Région : {region}
- Capital estimé : {cap_min/1e6:.0f}M-{cap_max/1e6:.0f}M$
- Thèse business : {thesis}
- Langue préférée : {lang}

**Historique communication Capital Norvex** :
- Dernier sujet envoyé : {last_subject}
- Date envoi : {last_sent_at}

**Engagement live (SendGrid)** :
{engagement_summary}

**Contexte additionnel** : {extra or "néant"}

Génère le brief JSON selon ton format strict. Adapte le ton et les thèses au profil spécifique de cette cible."""


def _fallback_brief(target: Dict[str, Any]) -> Dict[str, Any]:
    """Brief minimal si l'IA n'est pas disponible (pas de clé API, etc.)."""
    org = target.get("organization") or "cette organisation"
    return {
        "lecture_analytique": (
            f"Pattern d'engagement à interpréter manuellement. Données SendGrid disponibles "
            f"dans le dashboard. {org} reste à analyser plus en profondeur avant l'appel."
        ),
        "theses_co_financement": [
            "Refi senior debt sur asset stabilisé — sortie d'une dette bancaire vers structure flexible Capital Norvex.",
            "Co-investissement equity/mezz sur projet en pré-vente — couche capital structurée 10-12%.",
            "Plateforme courtier partenaire — intégration réseau de financement avec rémunération transparente négociée selon le dossier.",
        ],
        "talking_points": [
            "1. Ouverture : laisser parler en premier, comprendre l'angle.",
            "2. Capital Norvex = prêteur privé canadien garanti par hypothèque 1er rang, propulsé par IA propriétaire.",
            "3. Rendement 10-12% net annuel, transparence + discipline institutionnelle.",
            "4. Différenciation par écosystème IA (Score, Track, Intel, Brain).",
            "5. Closing : dossier précis ou exploration ?",
        ],
        "donts": [
            "Aucune approbation/engagement avant LOI signée.",
            "Pas de chiffres précis avant que la cible décrive son besoin.",
            "Pas de pression sur RDV Teams si profil traditionnel.",
            "Pas de mention compétiteurs.",
            "Aucune référence à dossiers en litige.",
        ],
    }
