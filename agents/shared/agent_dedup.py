"""Dédup self pour agents email (Béatrice / Sophie / Camille).

Bug fix 2026-05-10 (dimanche après-midi) : Yves a reçu 8 rappels Béatrice
en 1h pour le MÊME email. Cause : les crons Béatrice/Sophie/Camille tournent
aux 10 min, lisent `only_unread=True`, MAIS personne ne marque l'email
comme lu. Donc à chaque tick, ils re-triagent (Sonnet $), re-draftent
(Opus $$), re-notifient Yves (spam).

Ce helper offre 2 fonctions :
  - compute_email_doc_id(internet_message_id) : doc_id Firestore stable
  - has_existing_draft_for_email(...) : True si déjà drafté, skip silencieux

Pattern d'usage dans process_one_message() :

    from agents.shared.agent_dedup import has_existing_draft_for_email

    if has_existing_draft_for_email(
        internet_message_id=msg_id_internet,
        emails_collection=COLLECTION_EMAILS,
    ):
        summary["skip_reason"] = "already_drafted_by_self"
        return summary

Pour que ça marche, l'audit.py de l'agent DOIT appeler
update(COLLECTION_EMAILS, incoming_email_id, {"draftId": <id>,
"status": "drafted"}) après avoir créé le draft.

Hugo Watcher utilise un pattern différent (cooldown 6h via
`hugoLastAnalyzedAt`) — pas concerné par ce helper.
"""
from __future__ import annotations

from typing import Optional

from agents.shared.firestore_client import get


def compute_email_doc_id(internet_message_id: Optional[str]) -> Optional[str]:
    """Calcule le doc_id Firestore stable depuis un Message-ID Internet.

    Doit MATCH la logique de store_incoming_email() de chaque agent
    (Béatrice/Sophie/Camille utilisent tous la même normalisation).
    """
    if not internet_message_id:
        return None
    return (
        internet_message_id.replace("<", "").replace(">", "")
        .replace("/", "_").replace(".", "_")
    )[:1500]


_DRAFTED_STATUSES = frozenset({
    "drafted",
    "sent",
    "approved",
    "pending_yves_approval",
    "auto_send_pending",
})


def has_existing_draft_for_email(
    *,
    internet_message_id: Optional[str],
    emails_collection: str,
) -> bool:
    """True si l'email a déjà un draft (ou a été marqué drafté).

    Lit `<emails_collection>/<email_doc_id>`. Retourne True si :
      - le doc a un champ `draftId` ou `draft_id` non-vide
      - OU le status est dans {drafted, sent, approved,
        pending_yves_approval, auto_send_pending}

    Si pas d'internet_message_id (cas rare/edge), retourne False
    (l'agent continue son flow normal — fail-open pour éviter de
    bloquer du légitime).
    """
    doc_id = compute_email_doc_id(internet_message_id)
    if not doc_id:
        return False
    try:
        rec = get(emails_collection, doc_id)
    except Exception:
        # Fail-open : si Firestore indisponible, l'agent continue.
        # Mieux re-process une fois que de bloquer pour de vrai.
        return False
    if not rec:
        return False
    if rec.get("draftId") or rec.get("draft_id"):
        return True
    status = (rec.get("status") or "").lower().strip()
    return status in _DRAFTED_STATUSES
