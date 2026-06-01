"""Agent ADVISORS — outreach pour avocats fiscaux/successoraux/M&A.

Queue + send pour la collection `advisorTargets` (créée 2026-05-07).
Pattern aligné avec agents/promoteurs/outreach.py.

Usage:
    # Aperçus locaux
    python -m agents.advisors.outreach --preview-top 3

    # Met en file d'attente (drafts pendingDraft visibles dans UI)
    python -m agents.advisors.outreach --queue-top 5
    python -m agents.advisors.outreach --queue <doc_id>

    # Envoi de TEST à yves@
    python -m agents.advisors.outreach --send <doc_id> --to yves@capitalnorvex.com

    # Envoi production
    python -m agents.advisors.outreach --send <doc_id>
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
from .email_template import render_advisor_intro

AGENT_NAME = "advisors_outreach"
COLLECTION = "advisorTargets"
PREVIEW_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "previews",
    "advisors",
)


def _resolve_email(d: Dict[str, Any]) -> str:
    """Email peut être dans publicContact.email ou contactInfo.email."""
    pc = d.get("publicContact") or {}
    if isinstance(pc, dict):
        e = pc.get("email")
        if e and "@" in e:
            return e
    ci = d.get("contactInfo") or {}
    if isinstance(ci, dict):
        e = ci.get("email")
        if e and "@" in e:
            return e
    return ""


def _resolve_lang(d: Dict[str, Any]) -> str:
    """Fallback intelligent par region : ON → EN, QC → FR."""
    lang = (d.get("language") or "").lower()
    if lang in ("fr", "en"):
        return lang
    region = (d.get("region") or "").upper()
    return "en" if region == "ON" else "fr"


def _load_top_with_email(limit: int) -> List[Dict[str, Any]]:
    """Charge top N cibles advisorTargets avec email, non envoyées."""
    docs = fs.query(COLLECTION, limit=200)
    with_email = [d for d in docs if "@" in _resolve_email(d)]
    not_sent = [d for d in with_email if not d.get("sentAt") and not d.get("dontSend")]
    # Tri par confidence Hunter desc (qualité email)
    def _conf(d):
        return (d.get("publicContact") or {}).get("_hunterConfidence", 0) or 0
    not_sent.sort(key=_conf, reverse=True)
    return not_sent[:limit]


def _render_for_target(target: Dict[str, Any]) -> Dict[str, Any]:
    """Render le HTML pour un avocat."""
    lang = _resolve_lang(target)
    org = target.get("organization", "")
    name = target.get("name", "")

    html = render_advisor_intro(target, lang=lang, target_id=target.get("id"))

    if lang == "en":
        subject = f"Capital Norvex — Referral program for {org}"
    else:
        subject = f"Capital Norvex — Programme de référencement ({org})"

    return {
        "html": html,
        "subject": subject,
        "to": _resolve_email(target),
        "to_name": name,
        "lang": lang,
    }


def preview_top(n: int = 3) -> int:
    """Génère N aperçus HTML locaux pour validation Yves."""
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    targets = _load_top_with_email(n)
    if not targets:
        print("❌ Aucune cible avec email.")
        return 0
    print(f"📄 Génération de {len(targets)} aperçus dans {PREVIEW_DIR}\n")
    for t in targets:
        rendered = _render_for_target(t)
        slug = (t.get("organization", "advisor")[:40] + "_" + (t.get("name", "")[:30]))
        slug = "".join(c if c.isalnum() else "_" for c in slug)
        path = os.path.join(PREVIEW_DIR, f"{slug}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(rendered["html"])
        print(f"  ✓ {t.get('organization', '?')[:40]:40s} | {t.get('name', '?')[:25]:25s} → {path}")
    return len(targets)


def _upload_html_to_storage(doc_id: str, html: str) -> str:
    from firebase_admin import storage as fb_storage
    bucket = fb_storage.bucket()
    storage_path = f"outreach-drafts/{COLLECTION}/{doc_id}.html"
    blob = bucket.blob(storage_path)
    blob.upload_from_string(html, content_type="text/html; charset=utf-8")
    return storage_path


def queue_one(doc_id: str, force: bool = False) -> bool:
    """Pré-rend le draft pour un avocat. Status → pending_yves_approval."""
    target = fs.get(COLLECTION, doc_id)
    if not target:
        print(f"❌ {COLLECTION}/{doc_id} introuvable")
        return False

    if target.get("sentAt") and not force:
        print(f"⚠️  Déjà envoyé le {target.get('sentAt')}. --force pour réécrire.")
        return False

    if target.get("dontSend"):
        print(f"⚠️  Cible marquée dontSend=true. Skip.")
        return False

    if target.get("skipOutreach"):
        print(f"⚠️  Cible marquée skipOutreach=true ({target.get('skipReason','?')}). Skip.")
        return False

    rendered = _render_for_target(target)
    if not rendered.get("to") or "@" not in rendered.get("to", ""):
        print(f"❌ Email manquant pour {target.get('organization')}")
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
        "status": "pending_yves_approval",
    })
    fs.audit_log(
        agent=AGENT_NAME,
        action="outreach_queued",
        target_type=COLLECTION,
        target_id=doc_id,
        details={"to": rendered["to"], "subject": rendered["subject"]},
    )
    print(f"📥 Draft → {target.get('organization')} / {target.get('name')} ({rendered['to']})")
    return True


def queue_top(n: int = 5) -> int:
    targets = _load_top_with_email(n)
    if not targets:
        print("❌ Aucune cible avec email.")
        return 0
    print(f"📥 Mise en file de {len(targets)} avocats…\n")
    count = 0
    for t in targets:
        if queue_one(t["id"]):
            count += 1
    print(f"\n✅ {count}/{len(targets)} drafts créés. Visibles dans Norvex Agents → Conseillers.")
    return count


def send_one(doc_id: str, to_override: Optional[str] = None, force: bool = False) -> bool:
    target = fs.get(COLLECTION, doc_id)
    if not target:
        print(f"❌ {COLLECTION}/{doc_id} introuvable")
        return False

    if target.get("sentAt") and not force:
        print(f"⚠️  Déjà envoyé le {target.get('sentAt')}.")
        return False

    rendered = _render_for_target(target)
    to = to_override or rendered["to"]
    if not to or "@" not in to:
        print(f"❌ Email manquant pour {target.get('organization')}")
        return False

    is_test = bool(to_override)
    label = " [TEST → " + to + "]" if is_test else ""
    print(f"📤 Envoi à {to}{label}")
    print(f"   Sujet : {rendered['subject']}")

    # Avocats = ton conseiller-pair → envoi depuis yves@ (signé Yves Barrette personnellement)
    ok = send_email(
        to=to,
        subject=rendered["subject"],
        html=rendered["html"],
        from_user="yves@capitalnorvex.com",
    )
    now = datetime.now(timezone.utc).isoformat()
    if ok:
        print("   ✅ Envoyé")
        fs.audit_log(
            agent=AGENT_NAME,
            action="outreach_sent",
            target_type=COLLECTION,
            target_id=doc_id,
            details={"to": to, "subject": rendered["subject"], "isTest": is_test},
        )
        if not is_test:
            fs.update(COLLECTION, doc_id, {
                "sentAt": now,
                "sentTo": to,
                "sentSubject": rendered["subject"],
                "sentBy": AGENT_NAME,
                "status": "sent",
                "pendingDraft": None,
            })
        else:
            fs.update(COLLECTION, doc_id, {"lastTestAt": now, "lastTestTo": to})
        return True
    else:
        print("   ❌ Échec d'envoi")
        fs.audit_log(
            agent=AGENT_NAME,
            action="outreach_failed",
            target_type=COLLECTION,
            target_id=doc_id,
            result="failure",
            details={"to": to, "subject": rendered["subject"], "isTest": is_test},
        )
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--preview-top", type=int)
    p.add_argument("--queue-top", type=int)
    p.add_argument("--queue", type=str)
    p.add_argument("--send", type=str)
    p.add_argument("--to", type=str)
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    if args.preview_top:
        preview_top(args.preview_top)
    elif args.queue_top:
        queue_top(args.queue_top)
    elif args.queue:
        queue_one(args.queue, force=args.force)
    elif args.send:
        send_one(args.send, to_override=args.to, force=args.force)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
