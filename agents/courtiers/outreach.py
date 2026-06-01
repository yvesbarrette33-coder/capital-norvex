"""Agent COURTIERS — outreach (queue + envoi).

Pré-rend les courriels d'approche pour les courtiers identifiés et stocke
les drafts dans Firestore (`brokers/{docId}.pendingDraft`) + Storage.

L'UI Norvex Agents (onglet Courtiers) lit ces drafts pour aperçu/test/envoi
en un clic.

Usage:
    # Met en file d'attente les top N courtiers (cold, jamais contactés)
    python -m agents.courtiers.outreach --queue-top 10

    # Met en file un courtier précis
    python -m agents.courtiers.outreach --queue <doc_id>

    # Envoi de TEST
    python -m agents.courtiers.outreach --send <doc_id> --to yves@capitalnorvex.com

    # Envoi production
    python -m agents.courtiers.outreach --send <doc_id>
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..shared import firestore_client as fs
from ..shared.blacklist import is_blacklisted, reason_for
from ..shared.email_sender import send_email
from .email_template import render_cold_outreach, render_warm_followup

AGENT_NAME = "courtiers_outreach"
COLLECTION = "brokers"


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


def _load_top_cold(limit: int) -> List[Dict[str, Any]]:
    """Charge les top N courtiers cold (avec email, jamais contactés)."""
    docs = fs.query(COLLECTION, limit=500)
    eligible = [
        d for d in docs
        if "@" in _resolve_email(d)
        and not d.get("sentAt")
        and not d.get("dontSend")
        and (d.get("relationshipStatus") or "cold") == "cold"
    ]
    # Tri optionnel par firme (pour grouper)
    eligible.sort(key=lambda d: (d.get("firmName", ""), d.get("name", "")))
    return eligible[:limit]


def _render_for_broker(broker: Dict[str, Any]) -> Dict[str, Any]:
    """Render le HTML personnalisé pour un courtier."""
    name = (broker.get("name") or "").strip()
    firm = (broker.get("firmName") or "").strip()
    # Fallback intelligent par région : ON → EN, QC → FR (si language manquant)
    lang = broker.get("language")
    if not lang:
        lang = "en" if (broker.get("region") or "").upper() == "ON" else "fr"
    lang = lang.lower()
    if lang not in ("fr", "en"):
        lang = "en" if (broker.get("region") or "").upper() == "ON" else "fr"
    deal_count = broker.get("dealsReceived") or 0
    relationship = broker.get("relationshipStatus") or "cold"

    if relationship in ("warm", "active", "champion"):
        html = render_warm_followup({"name": name, "agency": firm}, deal_count=deal_count, lang=lang)
        if lang == "en":
            subject = f"Capital Norvex — Recent platform updates ({firm or name})"
        else:
            subject = f"Capital Norvex — Mises à jour récentes de la plateforme ({firm or name})"
    else:
        html = render_cold_outreach({"name": name, "agency": firm}, lang=lang)
        if lang == "en":
            subject = "Capital Norvex — Partner broker program (technology platform for private real estate financing)"
        else:
            subject = "Capital Norvex — Programme courtier partenaire (plateforme techno de financement privé)"

    return {
        "html": html,
        "subject": subject,
        "to": _resolve_email(broker),
        "to_name": name,
        "lang": lang,
    }


def _upload_html_to_storage(doc_id: str, html: str) -> str:
    """Upload HTML rendu dans Firebase Storage. Retourne le storagePath."""
    from firebase_admin import storage as fb_storage
    bucket = fb_storage.bucket()
    storage_path = f"outreach-drafts/brokers/{doc_id}.html"
    blob = bucket.blob(storage_path)
    blob.upload_from_string(html, content_type="text/html; charset=utf-8")
    return storage_path


def queue_one(doc_id: str, force: bool = False) -> bool:
    """Pré-rend le draft pour un courtier."""
    broker = fs.get(COLLECTION, doc_id)
    if not broker:
        print(f"❌ {COLLECTION}/{doc_id} introuvable")
        return False

    if broker.get("sentAt") and not force:
        print(f"⚠️  Déjà envoyé le {broker.get('sentAt')}. --force pour réécrire un draft.")
        return False

    if broker.get("dontSend"):
        print(f"⚠️  Marqué dontSend=true. Skip.")
        return False

    if broker.get("skipOutreach"):
        print(f"⚠️  Marqué skipOutreach=true ({broker.get('skipReason','?')}). Skip.")
        return False

    rendered = _render_for_broker(broker)
    if not rendered.get("to") or "@" not in rendered.get("to", ""):
        print(f"❌ Email manquant pour {broker.get('name')}")
        return False

    if is_blacklisted(rendered["to"]):
        print(f"⛔ BLACKLIST: {rendered['to']} — {reason_for(rendered['to'])}. Refus de queue.")
        return False

    storage_path = _upload_html_to_storage(doc_id, rendered["html"])

    now = datetime.now(timezone.utc).isoformat()
    fs.update(COLLECTION, doc_id, {
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
    })
    fs.audit_log(
        agent=AGENT_NAME,
        action="outreach_queued",
        target_type="broker",
        target_id=doc_id,
        details={"to": rendered["to"], "subject": rendered["subject"], "storagePath": storage_path},
    )
    print(f"📥 Draft → {broker.get('name')} ({broker.get('firmName')}) — {rendered['to']}")
    return True


def queue_top(n: int) -> int:
    """Pré-rend top N courtiers cold."""
    targets = _load_top_cold(n)
    if not targets:
        print("❌ Aucun courtier cold à mettre en file.")
        return 0
    print(f"📥 Mise en file de {len(targets)} courtiers…\n")
    count = 0
    for t in targets:
        if queue_one(t["id"]):
            count += 1
    print(f"\n✅ {count}/{len(targets)} drafts créés. Visibles dans Norvex Agents → Courtiers.")
    return count


def send_one(doc_id: str, to_override: Optional[str] = None, force: bool = False) -> bool:
    """Envoie pour un courtier. Update sentAt en Firestore (sauf si test)."""
    broker = fs.get(COLLECTION, doc_id)
    if not broker:
        print(f"❌ {COLLECTION}/{doc_id} introuvable")
        return False

    if broker.get("sentAt") and not force:
        print(f"⚠️  Déjà envoyé le {broker.get('sentAt')}. --force pour outrepasser.")
        return False

    rendered = _render_for_broker(broker)
    to = to_override or rendered["to"]
    if not to or "@" not in to:
        print(f"❌ Email manquant pour {broker.get('name')}")
        return False

    is_test = bool(to_override)
    label = " [TEST → " + to + "]" if is_test else ""
    print(f"📤 Envoi à {to}{label}")
    print(f"   Sujet : {rendered['subject']}")

    # Décision Yves 2026-05-04 : outreach courtiers partent de info@ (pas yves@)
    # car signés « L'équipe Capital Norvex ». Les replies arrivent à info@ où
    # Sophie peut les trier (autonomie + escalade selon catégorie).
    ok = send_email(
        to=to,
        subject=rendered["subject"],
        html=rendered["html"],
        from_user="info@capitalnorvex.com",
    )

    now = datetime.now(timezone.utc).isoformat()
    if ok:
        print(f"   ✅ Envoyé")
        fs.audit_log(
            agent=AGENT_NAME,
            action="outreach_sent",
            target_type="broker",
            target_id=doc_id,
            details={"to": to, "subject": rendered["subject"], "isTest": is_test},
        )
        if not is_test:
            fs.update(COLLECTION, doc_id, {
                "sentAt": now,
                "sentTo": to,
                "sentSubject": rendered["subject"],
                "sentBy": AGENT_NAME,
                "relationshipStatus": "warm",  # cold → warm après contact
                "pendingDraft": None,
            })
        else:
            fs.update(COLLECTION, doc_id, {
                "lastTestAt": now,
                "lastTestTo": to,
            })
        return True
    else:
        print(f"   ❌ Échec d'envoi")
        fs.audit_log(
            agent=AGENT_NAME,
            action="outreach_failed",
            target_type="broker",
            target_id=doc_id,
            result="failure",
            details={"to": to, "subject": rendered["subject"], "isTest": is_test},
        )
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue-top", type=int, help="Pré-rend top N courtiers cold")
    parser.add_argument("--queue", type=str, help="Doc ID à mettre en file")
    parser.add_argument("--send", type=str, help="Doc ID à envoyer")
    parser.add_argument("--to", type=str, help="Override destinataire (test)")
    parser.add_argument("--force", action="store_true", help="Réenvoyer/réécrire draft")
    args = parser.parse_args()

    if args.queue_top:
        queue_top(args.queue_top)
        return 0
    if args.queue:
        return 0 if queue_one(args.queue, force=args.force) else 1
    if args.send:
        return 0 if send_one(args.send, to_override=args.to, force=args.force) else 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
