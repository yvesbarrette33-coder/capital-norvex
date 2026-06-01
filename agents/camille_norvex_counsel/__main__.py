"""CLI Camille — pipeline manuel.

Usage :
    python -m agents.camille_norvex_counsel run                  # full pipeline (toutes boîtes)
    python -m agents.camille_norvex_counsel run --mailbox info@capitalnorvex.com
    python -m agents.camille_norvex_counsel run --no-draft       # triage seul (pas de drafts)
    python -m agents.camille_norvex_counsel run --top 5          # 5 derniers messages
    python -m agents.camille_norvex_counsel send <draft_id>      # envoi après approbation
    python -m agents.camille_norvex_counsel approve <draft_id>   # marque approuvé puis envoie
    python -m agents.camille_norvex_counsel reject <draft_id> "raison"
    python -m agents.camille_norvex_counsel list-templates
"""
from __future__ import annotations

import argparse
import json
import sys

from . import audit as camille_audit
from .config import MAILBOXES
from .orchestrator import (
    process_all_mailboxes,
    process_inbox,
    send_approved_draft,
)
from .templates import list_templates


def _cmd_run(args):
    if args.mailbox:
        results = {args.mailbox: process_inbox(
            args.mailbox,
            top=args.top,
            only_unread=not args.all,
            auto_draft=not args.no_draft,
            mark_read_after=args.mark_read,
        )}
    else:
        results = process_all_mailboxes(
            top=args.top,
            only_unread=not args.all,
            auto_draft=not args.no_draft,
            mark_read_after=args.mark_read,
        )
    print(json.dumps(results, indent=2, default=str, ensure_ascii=False))


def _cmd_send(args):
    ok = send_approved_draft(args.draft_id, force=args.force)
    print(f"sent={ok}")
    sys.exit(0 if ok else 1)


def _cmd_approve(args):
    camille_audit.mark_draft_approved(args.draft_id)
    if args.no_send:
        print(f"approved (not sent): {args.draft_id}")
        return
    ok = send_approved_draft(args.draft_id)
    print(f"approved + sent={ok}")
    sys.exit(0 if ok else 1)


def _cmd_reject(args):
    camille_audit.mark_draft_rejected(args.draft_id, reason=args.reason)
    print(f"rejected: {args.draft_id} ({args.reason})")


def _cmd_list_templates(args):
    for tpl in list_templates():
        print(f"  - {tpl}")


def _cmd_list_mailboxes(args):
    for mb, conf in MAILBOXES.items():
        print(f"  - {mb}  → persona={conf['persona']}  ({conf['description']})")


def main():
    parser = argparse.ArgumentParser(prog="camille_norvex_counsel")
    sp = parser.add_subparsers(dest="cmd", required=True)

    p_run = sp.add_parser("run", help="lance le pipeline (triage + drafting)")
    p_run.add_argument("--mailbox", help="boîte spécifique (sinon : toutes)")
    p_run.add_argument("--top", type=int, default=25, help="nb max de messages (def 25)")
    p_run.add_argument("--all", action="store_true", help="lus + non-lus (sinon non-lus)")
    p_run.add_argument("--no-draft", action="store_true", help="triage seul, pas de drafts")
    p_run.add_argument("--mark-read", action="store_true", help="marquer lus après drafting")
    p_run.set_defaults(func=_cmd_run)

    p_send = sp.add_parser("send", help="envoie un draft approuvé")
    p_send.add_argument("draft_id")
    p_send.add_argument("--force", action="store_true", help="bypass check status (urgence)")
    p_send.set_defaults(func=_cmd_send)

    p_app = sp.add_parser("approve", help="marque approuvé + envoie (sauf --no-send)")
    p_app.add_argument("draft_id")
    p_app.add_argument("--no-send", action="store_true")
    p_app.set_defaults(func=_cmd_approve)

    p_rej = sp.add_parser("reject", help="rejette un draft")
    p_rej.add_argument("draft_id")
    p_rej.add_argument("reason", nargs="?", default="")
    p_rej.set_defaults(func=_cmd_reject)

    sp.add_parser("list-templates", help="liste les templates disponibles") \
        .set_defaults(func=_cmd_list_templates)

    sp.add_parser("list-mailboxes", help="liste les boîtes configurées") \
        .set_defaults(func=_cmd_list_mailboxes)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
