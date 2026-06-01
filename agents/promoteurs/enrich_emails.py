"""Agent ENRICH-EMAILS — trouve les courriels professionnels des promoteurs.

Pour chaque promoteur en base SANS email, lance Sonnet 4-6 + web_search pour
trouver l'email du contact principal (ou à défaut un email corporate plausible).

Coût estimé : ~$0.05-0.15 USD par cible.

Usage:
    python -m agents.promoteurs.enrich_emails --max 10
    python -m agents.promoteurs.enrich_emails --max 5 --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

from ..shared import firestore_client as fs

AGENT_NAME = "promoteurs_enrich_emails"


def _search_email(target: Dict[str, Any]) -> Dict[str, Any]:
    """Cherche l'email professionnel pour une cible promoteur."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY manquant")

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    company = target.get("companyName") or "?"
    contact = target.get("principalContact") or ""
    city = target.get("city") or ""
    website = target.get("website") or ""

    sys_prompt = (
        "Tu es un agent de recherche d'emails professionnels pour Capital Norvex. "
        "Ta mission: trouver l'email professionnel d'un contact ou de l'entreprise.\n\n"
        "Stratégie:\n"
        "1. Cherche l'email DIRECT du contact nommé (LinkedIn, site corporate, communiqués)\n"
        "2. À défaut, trouve un email corporate (info@, contact@, direction@)\n"
        "3. NE JAMAIS inventer ou deviner. Si rien trouvé, retourne null.\n\n"
        "Réponds en JSON STRICT, aucun texte avant/après."
    )

    user_msg = (
        f"Trouve l'email professionnel pour:\n"
        f"- Entreprise: {company}\n"
        f"- Contact principal: {contact}\n"
        f"- Ville: {city}\n"
        f"- Site web: {website}\n\n"
        "Format JSON requis:\n"
        "{\n"
        '  "email": "email@domain.com" ou null,\n'
        '  "type": "personal" | "corporate" | null,\n'
        '  "confidence": "high" | "medium" | "low",\n'
        '  "source": "URL où l\'email a été trouvé",\n'
        '  "notes": "Courte explication"\n'
        "}\n\n"
        "Si plusieurs emails trouvés, retourne le PLUS PERTINENT (contact direct > "
        "service direction > info général)."
    )

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
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
        print(f"   ⚠️  JSON parse failed: {e}")
        return {"email": None, "type": None, "confidence": "low", "notes": "parse_error"}


def run(max_targets: int = 10, dry_run: bool = False) -> None:
    print(f"🔍 Enrichissement emails — top {max_targets} cibles sans email")
    print()

    # Charger toutes les cibles sans email (status=pending_review prioritaire)
    all_docs = fs.query("promoteurTargets", limit=200)
    no_email = [d for d in all_docs if not d.get("email")]
    no_email.sort(key=lambda d: d.get("score", 0) or 0, reverse=True)
    targets = no_email[:max_targets]

    print(f"   📊 Total en base    : {len(all_docs)}")
    print(f"   📭 Sans email       : {len(no_email)}")
    print(f"   🎯 À traiter (top)  : {len(targets)}")
    print()

    found = 0
    for i, t in enumerate(targets, 1):
        company = t.get("companyName", "?")
        score = t.get("score", "?")
        print(f"  [{i}/{len(targets)}] [{score}] {company[:50]}")
        try:
            result = _search_email(t)
            email = result.get("email")
            if email and "@" in email:
                conf = result.get("confidence", "?")
                etype = result.get("type", "?")
                source = (result.get("source") or "")[:50]
                print(f"      ✅ {email} ({etype}, {conf}) — {source}")
                if not dry_run:
                    fs.update("promoteurTargets", t["id"], {
                        "email": email,
                        "emailType": etype,
                        "emailConfidence": conf,
                        "emailSource": result.get("source"),
                        "emailNotes": result.get("notes"),
                        "emailEnrichedBy": AGENT_NAME,
                    })
                found += 1
            else:
                print(f"      ❌ Pas trouvé — {result.get('notes', '')[:60]}")
        except Exception as e:
            print(f"      ⚠️  Erreur : {e}")

    print()
    print(f"📊 Résultat : {found}/{len(targets)} emails trouvés")

    if not dry_run:
        fs.audit_log(
            agent=AGENT_NAME,
            action="enrich_emails_run",
            details={"processed": len(targets), "found": found},
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        run(max_targets=args.max, dry_run=args.dry_run)
        return 0
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
