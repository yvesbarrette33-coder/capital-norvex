"""Agent PROMOTEURS — outreach (preview + queue + envoi).

Génère des aperçus HTML personnalisés à partir des vraies cibles Firestore.
Trois modes :
  - preview : aperçu HTML local sur disque (validation Yves)
  - queue   : pré-rend le draft et l'écrit dans Firestore (pendingDraft) — l'UI
              Norvex Agents peut alors afficher l'aperçu et déclencher l'envoi
  - send    : envoi direct depuis le terminal (Graph + SendGrid fallback)

Usage:
    # Aperçus locaux pour validation Yves
    python -m agents.promoteurs.outreach --preview-top 5

    # Met en file d'attente (pendingDraft) les top N — visibles dans UI
    python -m agents.promoteurs.outreach --queue-top 5

    # Met en file d'attente une cible précise
    python -m agents.promoteurs.outreach --queue <doc_id>

    # Envoi de TEST (à yves@) pour valider rendu live
    python -m agents.promoteurs.outreach --send <doc_id> --to yves@capitalnorvex.com

    # Envoi production (à la cible)
    python -m agents.promoteurs.outreach --send <doc_id>

Une cible peut être envoyée 1 SEULE fois (anti-doublon via sentAt).
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
from .email_template import render_project_announcement

AGENT_NAME = "promoteurs_outreach"
PREVIEW_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "previews",
    "promoteurs",
)


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
    """Charge les top N cibles ayant un email, triées par score desc."""
    docs = fs.query("promoteurTargets", limit=400)
    with_email = [d for d in docs if "@" in _resolve_email(d)]
    # Filtre: exclure déjà envoyées + marquées dontSend (doublons, etc.)
    not_sent = [d for d in with_email if not d.get("sentAt") and not d.get("dontSend")]
    not_sent.sort(key=lambda d: d.get("score", 0) or 0, reverse=True)
    return not_sent[:limit]


def _render_for_target(target: Dict[str, Any]) -> Dict[str, Any]:
    """Render le HTML personnalisé pour une cible promoteur."""
    contact_full = target.get("principalContact") or ""
    # Extrait juste le prénom/nom (avant la virgule ou parenthèse)
    contact_name = contact_full.split(",")[0].split("(")[0].strip()
    if not contact_name:
        contact_name = "Direction"

    project_text = target.get("recentProject") or ""
    # Coupe au point ou tiret pour avoir un titre court
    project_short = project_text.split(" - ")[0].split(" — ")[0].split(".")[0][:80]

    # Fallback intelligent par région : ON → EN, QC → FR (si language manquant)
    _lang = target.get("language")
    if not _lang:
        _lang = "en" if (target.get("region") or "").upper() == "ON" else "fr"
    _lang = _lang.lower()
    if _lang not in ("fr", "en"):
        _lang = "en" if (target.get("region") or "").upper() == "ON" else "fr"

    promoter = {
        "name": contact_name,
        "companyName": target.get("companyName", ""),
        "language": _lang,
    }
    project = {"name": project_short or "votre projet récent"}

    lang = promoter["language"]
    html = render_project_announcement(promoter, project, lang=lang)

    subject_fr = f"Capital Norvex — Co-financement structuré pour {promoter['companyName']}"
    subject_en = f"Capital Norvex — Structured Co-Financing for {promoter['companyName']}"
    subject = subject_en if lang == "en" else subject_fr

    return {
        "html": html,
        "subject": subject,
        "to": _resolve_email(target),
        "to_name": contact_name,
        "lang": lang,
        "promoter": promoter,
        "project": project,
    }


def preview_top(n: int = 5) -> None:
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    targets = _load_top_with_email(n)
    if not targets:
        print("❌ Aucune cible avec email à prévisualiser.")
        return

    print(f"📋 Génération aperçus pour {len(targets)} cibles…\n")
    index_rows = []
    for i, t in enumerate(targets, 1):
        rendered = _render_for_target(t)
        slug = (
            (t.get("companyName", "target")
             .lower()
             .replace(" ", "-")
             .replace("/", "-")
             .replace("(", "")
             .replace(")", "")
             .replace("'", "")[:50])
        )
        fname = f"{i:02d}-{slug}.html"
        fpath = os.path.join(PREVIEW_DIR, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(rendered["html"])
        print(f"  ✅ [{t.get('score')}] {t.get('companyName')[:50]:50s} → {fname}")
        print(f"      📧 {rendered['to']}")
        print(f"      📌 Sujet : {rendered['subject']}")
        print(f"      🆔 docId : {t.get('id')}")
        print()
        index_rows.append({
            "i": i,
            "slug": slug,
            "fname": fname,
            "company": t.get("companyName", ""),
            "score": t.get("score"),
            "email": rendered["to"],
            "subject": rendered["subject"],
            "doc_id": t.get("id"),
            "lang": rendered["lang"],
            "city": t.get("city", ""),
        })

    # Index HTML
    rows_html = "".join(
        f'<tr>'
        f'<td style="padding:8px;border-bottom:1px solid #ddd">{r["i"]}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #ddd"><strong>{r["score"]}</strong></td>'
        f'<td style="padding:8px;border-bottom:1px solid #ddd">{r["company"]}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #ddd">{r["city"]}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #ddd">{r["email"]}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #ddd">{r["lang"].upper()}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #ddd"><a href="{r["fname"]}" target="_blank">📨 Aperçu</a></td>'
        f'<td style="padding:8px;border-bottom:1px solid #ddd"><code style="font-size:11px;">{r["doc_id"]}</code></td>'
        f'</tr>'
        for r in index_rows
    )
    index_html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Aperçus envois Promoteurs — Capital Norvex</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:1100px;margin:30px auto;padding:0 20px;}}
table{{border-collapse:collapse;width:100%;margin-top:20px;font-size:14px;}}
th{{background:#1a1a1a;color:#d4af37;padding:10px;text-align:left;}}
.note{{background:#fff8dc;border:1px solid #d4af37;padding:15px;border-radius:6px;margin:20px 0;}}</style></head>
<body>
<h1>📨 Aperçus — Premier batch d'envoi Promoteurs</h1>
<div class="note"><strong>⚠️ Avant d'envoyer :</strong> Vérifie chaque aperçu, le sujet, le ton, le destinataire. Pour envoyer:<br>
<code style="display:block;margin-top:8px;background:#f4f4f4;padding:8px;">python -m agents.promoteurs.outreach --send DOC_ID --to yves@capitalnorvex.com</code>
(remplace <code>--to yves@</code> par rien pour envoyer au vrai destinataire)</div>
<table>
<thead><tr><th>#</th><th>Score</th><th>Promoteur</th><th>Ville</th><th>Courriel</th><th>Lang</th><th>Aperçu</th><th>Doc ID</th></tr></thead>
<tbody>{rows_html}</tbody>
</table>
</body></html>"""
    index_path = os.path.join(PREVIEW_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"📂 Index : {index_path}")
    print(f"   Ouvre avec : open {index_path}")


def _upload_html_to_storage(doc_id: str, html: str) -> str:
    """Upload le HTML rendu dans Firebase Storage. Retourne le storagePath.

    Le HTML peut faire plusieurs MB (logo + signature embarqués en base64),
    ce qui dépasse la limite 1 MiB des documents Firestore. On stocke le
    HTML dans Storage, et seulement le path dans Firestore.
    """
    from firebase_admin import storage as fb_storage
    bucket = fb_storage.bucket()
    storage_path = f"outreach-drafts/promoteurTargets/{doc_id}.html"
    blob = bucket.blob(storage_path)
    blob.upload_from_string(html, content_type="text/html; charset=utf-8")
    return storage_path


def queue_one(doc_id: str, force: bool = False) -> bool:
    """Pré-rend le draft pour une cible.

    Le HTML est uploadé dans Firebase Storage (`outreach-drafts/.../{docId}.html`)
    et seulement la métadata + storagePath sont écrits dans Firestore
    (`promoteurTargets/{docId}.pendingDraft`).

    L'UI Norvex Agents lit cette métadata pour afficher l'état "draft prêt"
    et permettre à Yves d'approuver/envoyer d'un clic. La Netlify function
    `agent-send-outreach` télécharge le HTML depuis Storage avant l'envoi.
    """
    target = fs.get("promoteurTargets", doc_id)
    if not target:
        print(f"❌ promoteurTargets/{doc_id} introuvable")
        return False

    if target.get("sentAt") and not force:
        print(f"⚠️  Déjà envoyé le {target.get('sentAt')}. --force pour réécrire un draft.")
        return False

    if target.get("dontSend"):
        print(f"⚠️  Cible marquée dontSend=true. Skip.")
        return False

    if target.get("skipOutreach"):
        print(f"⚠️  Cible marquée skipOutreach=true ({target.get('skipReason','?')}). Skip.")
        return False

    rendered = _render_for_target(target)
    if not rendered.get("to") or "@" not in rendered.get("to", ""):
        print(f"❌ Email manquant pour {target.get('companyName')}")
        return False

    if is_blacklisted(rendered["to"]):
        print(f"⛔ BLACKLIST: {rendered['to']} — {reason_for(rendered['to'])}. Refus de queue.")
        return False

    storage_path = _upload_html_to_storage(doc_id, rendered["html"])

    now = datetime.now(timezone.utc).isoformat()
    fs.update("promoteurTargets", doc_id, {
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
        target_type="promoteurTarget",
        target_id=doc_id,
        details={"to": rendered["to"], "subject": rendered["subject"], "storagePath": storage_path},
    )
    print(f"📥 Draft en file → {target.get('companyName')} ({rendered['to']})")
    return True


def queue_top(n: int = 5) -> int:
    """Pré-rend les top N cibles (avec email, non envoyées) dans Firestore."""
    targets = _load_top_with_email(n)
    if not targets:
        print("❌ Aucune cible avec email à mettre en file.")
        return 0
    print(f"📥 Mise en file de {len(targets)} cibles…\n")
    count = 0
    for t in targets:
        if queue_one(t["id"]):
            count += 1
    print(f"\n✅ {count}/{len(targets)} drafts créés. Visibles dans Norvex Agents → Promoteurs.")
    return count


def send_one(doc_id: str, to_override: Optional[str] = None, force: bool = False) -> bool:
    """Envoie le courriel pour une cible. Update sentAt en Firestore.

    Note: les tests (--to override) sont aussi loggés avec isTest=true,
    pour que Yves puisse les voir dans l'UI sans qu'ils marquent la cible
    comme contactée.
    """
    target = fs.get("promoteurTargets", doc_id)
    if not target:
        print(f"❌ promoteurTargets/{doc_id} introuvable")
        return False

    if target.get("sentAt") and not force:
        print(f"⚠️  Déjà envoyé le {target.get('sentAt')}. --force pour outrepasser.")
        return False

    rendered = _render_for_target(target)
    to = to_override or rendered["to"]
    if not to or "@" not in to:
        print(f"❌ Email manquant pour {target.get('companyName')}")
        return False

    is_test = bool(to_override)
    label = " [TEST → " + to + "]" if is_test else ""
    print(f"📤 Envoi à {to}{label}")
    print(f"   Sujet : {rendered['subject']}")

    # Décision Yves 2026-05-04 : outreach promoteurs partent de info@ (pas yves@)
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
        # Log toujours dans audit (test inclus, avec flag)
        fs.audit_log(
            agent=AGENT_NAME,
            action="outreach_sent",
            target_type="promoteurTarget",
            target_id=doc_id,
            details={"to": to, "subject": rendered["subject"], "isTest": is_test},
        )
        if not is_test:
            fs.update("promoteurTargets", doc_id, {
                "sentAt": now,
                "sentTo": to,
                "sentSubject": rendered["subject"],
                "sentBy": AGENT_NAME,
                "status": "sent",
                "pendingDraft": None,  # nettoie le draft après envoi réel
            })
        else:
            # En mode test, on enregistre dans lastTestAt pour visibilité UI
            fs.update("promoteurTargets", doc_id, {
                "lastTestAt": now,
                "lastTestTo": to,
            })
        return True
    else:
        print(f"   ❌ Échec d'envoi")
        fs.audit_log(
            agent=AGENT_NAME,
            action="outreach_failed",
            target_type="promoteurTarget",
            target_id=doc_id,
            result="failure",
            details={"to": to, "subject": rendered["subject"], "isTest": is_test},
        )
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview-top", type=int,
                        help="Génère N aperçus HTML locaux pour validation")
    parser.add_argument("--queue-top", type=int,
                        help="Pré-rend les top N drafts dans Firestore (visibles dans Norvex Agents)")
    parser.add_argument("--queue", type=str,
                        help="Doc ID Firestore à mettre en file (pré-rend draft)")
    parser.add_argument("--send", type=str,
                        help="Doc ID Firestore à envoyer")
    parser.add_argument("--to", type=str,
                        help="Override destinataire (pour test)")
    parser.add_argument("--force", action="store_true",
                        help="Réenvoyer/réécrire draft même si sentAt existe")
    args = parser.parse_args()

    if args.preview_top:
        preview_top(args.preview_top)
        return 0
    if args.queue_top:
        queue_top(args.queue_top)
        return 0
    if args.queue:
        ok = queue_one(args.queue, force=args.force)
        return 0 if ok else 1
    if args.send:
        ok = send_one(args.send, to_override=args.to, force=args.force)
        return 0 if ok else 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
