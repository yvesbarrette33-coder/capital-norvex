"""Cleanup one-off (2026-05-10) — rejette les drafts en double.

CONTEXTE :
    Bug systémique sur Béatrice / Sophie / Camille : les crons re-traitaient
    le MÊME Message-ID aux 10 min car personne ne marquait l'email comme
    drafté. Yves a reçu 8 rappels Béatrice en 1h pour 1 seul email entrant.

    Le code a été patché le 2026-05-10 (voir agents/shared/agent_dedup.py +
    audit.py des 3 agents). Au prochain tick, plus de doublons.

    Ce script nettoie les doublons DÉJÀ créés en Firestore :
    - Pour chaque (collection, incomingEmailId), garde le PLUS RÉCENT
    - Marque les autres `rejected` avec reason='auto_cleanup_duplicate_2026-05-10'
    - Met à jour l'email parent avec draftId du draft gardé + status='drafted'

USAGE :
    cd ~/Desktop/capitalnorvex-site
    source ~/.capitalnorvex/.env  # pour ANTHROPIC_API_KEY etc.
    python3 -m agents.shared.cleanup_duplicate_drafts_2026-05-10           # DRY-RUN par défaut
    python3 -m agents.shared.cleanup_duplicate_drafts_2026-05-10 --execute  # vraiment rejeter

SAFETY :
    - DRY-RUN par défaut : affiche ce qu'il ferait sans rien modifier
    - Ne touche QUE les drafts status=pending_yves_approval ou auto_send_pending
    - N'envoie aucun email — purement Firestore
    - Ne supprime rien — change juste le status à `rejected`
"""
from __future__ import annotations

import sys
from collections import defaultdict
from typing import Any, Dict, List

from agents.shared.firestore_client import audit_log, query, update, now_utc


# Collections à nettoyer : (drafts, emails)
TARGETS = [
    ("beatriceDrafts", "beatriceEmails", "beatrice"),
    ("sophieDrafts", "sophieEmails", "sophie"),
    ("camilleDrafts", "camilleEmails", "camille"),
]

PENDING_STATUSES = ("pending_yves_approval", "auto_send_pending")


def _to_iso(ts) -> str:
    """Best-effort ISO-formattage pour log lisible."""
    if ts is None:
        return ""
    try:
        return ts.isoformat()
    except Exception:
        return str(ts)[:30]


def cleanup_collection(drafts_col: str, emails_col: str, agent: str,
                       *, execute: bool) -> Dict[str, int]:
    """Nettoie les doublons d'une collection. Retourne stats."""
    stats = {"groups_examined": 0, "groups_with_duplicates": 0,
             "drafts_kept": 0, "drafts_rejected": 0, "emails_marked": 0}

    print(f"\n=== {drafts_col} (agent={agent}) ===")

    # Récupère tous les drafts pending (status IN PENDING_STATUSES).
    # Firestore n'accepte pas un IN avec query() simple — on fait 2 queries.
    all_pending: List[Dict[str, Any]] = []
    for st in PENDING_STATUSES:
        try:
            res = query(drafts_col, filters=[("status", "==", st)])
            all_pending.extend(res)
        except Exception as e:
            print(f"  WARN query status={st} a échoué: {e}")

    # Groupe par incomingEmailId
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for d in all_pending:
        ie_id = d.get("incomingEmailId")
        if not ie_id:
            continue
        groups[ie_id].append(d)

    stats["groups_examined"] = len(groups)

    for ie_id, drafts in groups.items():
        if len(drafts) <= 1:
            continue

        stats["groups_with_duplicates"] += 1

        # Tri par createdAt DESC (plus récent d'abord). Si pas de createdAt,
        # fallback sur l'id (lexico).
        drafts_sorted = sorted(
            drafts,
            key=lambda d: (d.get("createdAt") or 0, d.get("id", "")),
            reverse=True,
        )
        keeper = drafts_sorted[0]
        rejects = drafts_sorted[1:]

        keeper_id = keeper.get("id", "?")
        print(f"\n  Email {ie_id[:60]}…")
        print(f"    {len(drafts)} drafts pending — garde {keeper_id} "
              f"(createdAt={_to_iso(keeper.get('createdAt'))})")

        for r in rejects:
            r_id = r.get("id", "?")
            print(f"    REJECT {r_id} (createdAt={_to_iso(r.get('createdAt'))})")
            stats["drafts_rejected"] += 1
            if execute:
                try:
                    update(drafts_col, r_id, {
                        "status": "rejected",
                        "rejectedAt": now_utc(),
                        "rejectionReason":
                            "auto_cleanup_duplicate_2026-05-10",
                    })
                    audit_log(
                        agent=agent, action="cleanup_duplicate_draft_rejected",
                        target_type=drafts_col, target_id=r_id,
                        result="success",
                        details={"keeper": keeper_id, "incomingEmailId": ie_id},
                    )
                except Exception as e:
                    print(f"      ERR update reject: {e}")

        stats["drafts_kept"] += 1

        # Met à jour l'email parent pour que dédup self soit cohérent
        if execute:
            try:
                update(emails_col, ie_id, {
                    "draftId": keeper_id,
                    "status": "drafted",
                })
                stats["emails_marked"] += 1
            except Exception as e:
                print(f"    ERR update email parent ({ie_id}): {e}")

    print(f"\n  Stats {drafts_col} : {stats}")
    return stats


def main():
    execute = "--execute" in sys.argv
    if not execute:
        print("="*60)
        print("DRY-RUN par défaut. Pour vraiment rejeter, ajoute --execute")
        print("="*60)

    grand = {"groups_examined": 0, "groups_with_duplicates": 0,
             "drafts_kept": 0, "drafts_rejected": 0, "emails_marked": 0}

    for drafts_col, emails_col, agent in TARGETS:
        s = cleanup_collection(drafts_col, emails_col, agent, execute=execute)
        for k, v in s.items():
            grand[k] += v

    print("\n" + "="*60)
    print(f"TOTAL : {grand}")
    print("="*60)
    if not execute:
        print("\n→ Pour appliquer : "
              "python3 -m agents.shared.cleanup_duplicate_drafts_2026-05-10 --execute")


if __name__ == "__main__":
    main()
