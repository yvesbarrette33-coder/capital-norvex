"""
Migration urgente 2026-05-07 : déplacer les avocats hors de capitalTargets.

Yves a vu Stikeman/etc. apparaître dans son dashboard "Capital" → mélange à éviter.
Solution : nouvelle collection `advisorTargets` séparée pour avocats/comptables/PWM.

USAGE :
  python -m agents.shared.move_lawyers_to_advisorTargets --dry  # simule
  python -m agents.shared.move_lawyers_to_advisorTargets        # exécute
"""
from __future__ import annotations
import sys
from datetime import datetime, timezone
from agents.shared.firestore_client import db, audit_log

SOURCE = "capitalTargets"
DEST = "advisorTargets"

def main(dry: bool):
    fs = db()
    # Critère : tous les docs créés par discover_law_firms_2026-05-07
    docs = list(
        fs.collection(SOURCE)
          .where("createdBy", "==", "discover_law_firms_2026-05-07")
          .stream()
    )
    print(f"\n{'🟡 DRY-RUN' if dry else '🚀 MIGRATION'} — {len(docs)} avocats à déplacer\n")

    moved, errors = 0, []
    for snap in docs:
        data = snap.to_dict()
        old_id = snap.id
        firm = data.get("organization", "?")
        name = data.get("name", "?")
        try:
            if not dry:
                # 1. Crée doc dans advisorTargets (preserve toutes les données)
                new_data = {**data, "_migratedFrom": f"capitalTargets/{old_id}",
                            "_migratedAt": datetime.now(timezone.utc).isoformat()}
                new_data.pop("id", None)  # pas un champ Firestore
                new_ref = fs.collection(DEST).document(old_id)  # même ID = simple
                new_ref.set(new_data)
                # 2. Supprime de capitalTargets
                fs.collection(SOURCE).document(old_id).delete()
                # 3. Audit
                audit_log(
                    agent="migrate_lawyers_2026-05-07",
                    action="move_to_advisorTargets",
                    target_type=DEST,
                    target_id=old_id,
                    result="success",
                    details={"firm": firm, "name": name},
                )
            print(f"  {'🔍' if dry else '✅'} {firm[:30]:30s} | {name[:30]:30s} | {old_id}")
            moved += 1
        except Exception as e:
            errors.append((old_id, name, str(e)))
            print(f"  ❌ {firm} / {name} → {e}")

    print(f"\n— Résumé —")
    print(f"  {'Simulés' if dry else 'Déplacés'} : {moved}/{len(docs)}")
    print(f"  Erreurs  : {len(errors)}")
    if errors:
        for eid, en, ee in errors:
            print(f"     {eid} ({en}) → {ee}")
    if not dry and moved > 0:
        print(f"\n  ✅ Section CAPITAL de ton dashboard ne montrera plus d'avocats.")
        print(f"  📂 Nouvelle collection : advisorTargets ({moved} docs)")

if __name__ == "__main__":
    main("--dry" in sys.argv)
