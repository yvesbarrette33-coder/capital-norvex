"""Agent CAPITAL — outreach (queue + envoi) pour family offices / wealth managers.

Calqué sur agents/promoteurs/outreach.py. Génère des drafts emails
personnalisés pour les capitalTargets, stocke dans Firestore +
Firebase Storage. UI Norvex Agents affiche les boutons Aperçu / Test /
Envoyer.

Usage :
    # Génère drafts pour TOUTES les cibles avec email
    python -m agents.capital.outreach --queue-top 100

    # Génère draft pour une cible précise
    python -m agents.capital.outreach --queue <doc_id>

    # Envoi de TEST à yves@
    python -m agents.capital.outreach --send <doc_id> --to yves@capitalnorvex.com

    # Envoi production
    python -m agents.capital.outreach --send <doc_id>

⚠️  Capital = EMAIL UNIQUEMENT (cf. feedback_capital_email_only.md).
    Les cibles SANS email seront ignorées par queue_top — Yves doit
    enrichir manuellement avant d'envoyer.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..shared import firestore_client as fs
from ..shared.blacklist import is_blacklisted, reason_for
from .email_template import render_partnership_intro

AGENT_NAME = "capital_outreach"


# ─── Loader ─────────────────────────────────────────────────────────────────

def _resolve_email(d: Dict[str, Any]) -> str:
    """Email peut être dans email / contactInfo.email / publicContact.email."""
    e = d.get("email")
    if e and "@" in e:
        return e
    ci = d.get("contactInfo") or {}
    if isinstance(ci, dict):
        e = ci.get("email")
        if e and "@" in e:
            return e
    pc = d.get("publicContact") or {}
    if isinstance(pc, dict):
        e = pc.get("email")
        if e and "@" in e:
            return e
    return ""


def _load_top_with_email(limit: int) -> List[Dict[str, Any]]:
    """Charge les top N cibles avec email, triées par tier puis readinessScore."""
    docs = fs.query("capitalTargets", limit=200)
    with_email = [
        d for d in docs
        if "@" in _resolve_email(d)
    ]
    not_sent = [
        d for d in with_email
        if not d.get("sentAt") and not d.get("protectedFlag")
    ]
    # Tri : tier (1A > 1B > 2 > 3) puis readinessScore desc
    tier_order = {"1A": 0, "1B": 1, "2": 2, "3": 3, "ZERO": 99}
    not_sent.sort(
        key=lambda d: (
            tier_order.get(d.get("tier", "3"), 9),
            -(d.get("readinessScore", 0) or 0),
        )
    )
    return not_sent[:limit]


# ─── Renderer ───────────────────────────────────────────────────────────────

def _render_for_target(target: Dict[str, Any], target_id: str | None = None) -> Dict[str, Any]:
    """Render le HTML personnalisé pour une cible Capital."""
    name = target.get("name") or ""
    org = target.get("organization") or ""
    # Fallback intelligent par région : ON → EN, QC → FR (si language manquant)
    raw_lang = target.get("language")
    if not raw_lang:
        lang = "en" if (target.get("region") or "").upper() == "ON" else "fr"
    else:
        lang = raw_lang.lower()
    if lang == "both":
        lang = "en" if (target.get("region") or "").upper() == "ON" else "fr"
    if lang not in ("fr", "en"):
        lang = "en" if (target.get("region") or "").upper() == "ON" else "fr"

    html = render_partnership_intro(target, lang=lang, target_id=target_id)

    if lang == "en":
        subject = (
            f"Capital Norvex — Structured private real estate "
            f"partnership ({org or name})"
        )
    else:
        subject = (
            f"Capital Norvex — Partenariat structuré en prêt privé "
            f"immobilier ({org or name})"
        )

    return {
        "html": html,
        "subject": subject,
        "to": _resolve_email(target),
        "to_name": name or org or "",
        "lang": lang,
    }


# ─── Storage upload ─────────────────────────────────────────────────────────

def _upload_html_to_storage(doc_id: str, html: str) -> str:
    """Upload le HTML rendu dans Firebase Storage. Retourne le storagePath."""
    from firebase_admin import storage as fb_storage
    bucket = fb_storage.bucket()
    storage_path = f"outreach-drafts/capitalTargets/{doc_id}.html"
    blob = bucket.blob(storage_path)
    blob.upload_from_string(html, content_type="text/html; charset=utf-8")
    return storage_path


# ─── Queue ──────────────────────────────────────────────────────────────────

def queue_one(doc_id: str, force: bool = False) -> bool:
    """Pré-rend le draft pour une cible Capital."""
    target = fs.get("capitalTargets", doc_id)
    if not target:
        print(f"❌ capitalTargets/{doc_id} introuvable")
        return False

    if target.get("sentAt") and not force:
        print(f"⚠️  Déjà envoyé le {target.get('sentAt')}. --force pour réécrire un draft.")
        return False

    if target.get("protectedFlag"):
        print(f"⚠️  Cible protectedFlag=true (TIER ZERO). Skip.")
        return False

    if target.get("skipOutreach"):
        print(f"⚠️  Cible marquée skipOutreach=true ({target.get('skipReason','?')}). Skip.")
        return False

    rendered = _render_for_target(target, target_id=doc_id)
    has_email = bool(rendered.get("to")) and "@" in (rendered.get("to") or "")
    if has_email and is_blacklisted(rendered["to"]):
        print(f"⛔ BLACKLIST: {rendered['to']} — {reason_for(rendered['to'])}. Refus de queue.")
        return False
    if not has_email:
        # Mode aperçu seulement : on génère le draft pour qu'Yves puisse voir
        # le contenu dans Norvex Agents, mais l'envoi sera bloqué tant que
        # l'email n'est pas enrichi. Yves voit l'aperçu et peut décider
        # d'enrichir manuellement après.
        print(f"ℹ️  Email manquant pour {target.get('name')} — draft généré en mode aperçu seulement.")

    storage_path = _upload_html_to_storage(doc_id, rendered["html"])

    now = datetime.now(timezone.utc).isoformat()
    fs.update("capitalTargets", doc_id, {
        "pendingDraft": {
            "storagePath": storage_path,
            "htmlBytes": len(rendered["html"].encode("utf-8")),
            "subject": rendered["subject"],
            "to": rendered["to"],
            "toName": rendered["to_name"],
            "lang": rendered["lang"],
            "renderedAt": now,
            "renderedBy": AGENT_NAME,
        },
        "status": "pending_yves_approval",
    })
    fs.audit_log(
        agent=AGENT_NAME,
        action="outreach_queued",
        target_type="capitalTarget",
        target_id=doc_id,
        details={
            "to": rendered["to"],
            "subject": rendered["subject"],
            "storagePath": storage_path,
        },
    )
    print(f"📥 Draft en file → {target.get('name')} / {target.get('organization')} ({rendered['to']})")
    return True


def queue_top(n: int = 100) -> int:
    """Pré-rend les top N cibles Capital (avec email, non envoyées) dans Firestore."""
    targets = _load_top_with_email(n)
    if not targets:
        print("❌ Aucune cible Capital avec email à mettre en file.")
        print("   (Les capitalTargets sont des family offices/HNW — emails à enrichir manuellement)")
        return 0
    print(f"📥 Mise en file de {len(targets)} cibles Capital…\n")
    count = 0
    for t in targets:
        if queue_one(t["id"]):
            count += 1
    print(f"\n✅ {count}/{len(targets)} drafts Capital créés. Visibles dans Norvex Agents → Capital.")
    return count


# ─── CLI ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Agent Capital — outreach")
    parser.add_argument("--queue-top", type=int, help="Pré-rend les top N cibles Capital avec email")
    parser.add_argument("--queue", type=str, help="Doc ID à mettre en file")
    parser.add_argument("--force", action="store_true", help="Réécrit le draft même si déjà envoyé")
    args = parser.parse_args()

    if args.queue:
        ok = queue_one(args.queue, force=args.force)
        return 0 if ok else 1

    if args.queue_top:
        queue_top(args.queue_top)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
