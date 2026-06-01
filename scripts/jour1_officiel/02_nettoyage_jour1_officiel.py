"""
JOUR 1 OFFICIEL CAPITAL NORVEX — 2026-05-04
============================================
SCRIPT 02 : NETTOYAGE CIBLÉ FIRESTORE

Vide les collections de TEST avant le lancement officiel.

✅ COLLECTIONS PRÉSERVÉES (vraies données) :
   - utilisateurs
   - brokers (64 courtiers réels)
   - promoters / promoteurTargets (136 promoteurs réels)
   - capitalTargets (cibles capital outreach)
   - agentAuditLog (historique d'audit)
   - camilleAuditLog (audit Camille)
   - phone_sessions (uniquement Yves +15145312705 et Suzanne +14506311688)

🗑️  COLLECTIONS VIDÉES :
   - dossiers (+ sous-collections track / costAnalyzer / trackUploads)
   - transactions
   - factures
   - trackAlerts
   - phone_sessions (sauf Yves et Suzanne)

⚠️  PRÉ-REQUIS : avoir lancé 01_backup_firestore_complet.py AVANT.

Usage :
    cd ~/Desktop/capitalnorvex-site
    python -m scripts.jour1_officiel.02_nettoyage_jour1_officiel
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from agents.shared.auth import get_firestore  # noqa: E402

# Numéros à PRÉSERVER dans phone_sessions (Yves + Suzanne)
PRESERVED_PHONES = {"+15145312705", "+14506311688"}

# Collections à VIDER complètement (validées par Yves 2026-05-04)
COLLECTIONS_TO_PURGE = [
    "transactions",
    "factures",
    "trackAlerts",
    "dossiers_clients",      # Legacy (validé Yves)
    "appels",                # Tests Norah (validé Yves)
    "norahSessions",         # Tests Norah (validé Yves)
    "brokerApplications",    # Tests candidatures (validé Yves)
]

# Sous-collections sous chaque dossier à supprimer en cascade
DOSSIER_SUBCOLLECTIONS = ["track", "costAnalyzer", "trackUploads"]


def delete_subcollections(doc_ref):
    """Supprime toutes les sous-collections d'un document."""
    for sub_coll in doc_ref.collections():
        for sub_doc in sub_coll.stream():
            sub_doc.reference.delete()


def purge_dossiers(db):
    """Supprime TOUS les dossiers + leurs sous-collections."""
    print("🗑️  Suppression de TOUS les dossiers (et sous-collections)...")
    count = 0
    sub_count = 0
    for doc in db.collection("dossiers").stream():
        # Compter sous-collections avant
        for sub_coll in doc.reference.collections():
            for _ in sub_coll.stream():
                sub_count += 1
        delete_subcollections(doc.reference)
        doc.reference.delete()
        count += 1
        print(f"   ❌ Dossier supprimé : {doc.id}")
    print(f"   ✅ Total : {count} dossiers + {sub_count} sous-documents supprimés\n")
    return count


def purge_collection(db, coll_name):
    """Supprime tous les documents d'une collection."""
    print(f"🗑️  Vidage collection : {coll_name}")
    count = 0
    for doc in db.collection(coll_name).stream():
        doc.reference.delete()
        count += 1
    print(f"   ✅ {count} documents supprimés\n")
    return count


def purge_phone_sessions(db):
    """Supprime les phone_sessions SAUF Yves et Suzanne."""
    print("🗑️  Nettoyage phone_sessions (préserve Yves + Suzanne)...")
    deleted = 0
    preserved = 0
    for doc in db.collection("phone_sessions").stream():
        data = doc.to_dict() or {}
        phone = data.get("phone") or doc.id
        # Normalise (parfois doc.id = phone)
        phone_clean = phone.replace(" ", "").replace("-", "")
        if any(p in phone_clean for p in PRESERVED_PHONES):
            print(f"   ✅ Préservé : {phone}")
            preserved += 1
        else:
            doc.reference.delete()
            print(f"   ❌ Supprimé : {phone or doc.id}")
            deleted += 1
    print(f"   ✅ {deleted} sessions supprimées, {preserved} préservées\n")


def main():
    db = get_firestore()
    print("🔐 Connexion Firestore OK\n")
    print("=" * 60)
    print("  NETTOYAGE JOUR 1 OFFICIEL — Capital Norvex")
    print("  Date : 2026-05-04")
    print("=" * 60 + "\n")

    # 1. Dossiers (avec sous-collections en cascade)
    purge_dossiers(db)

    # 2. Collections à vider complètement
    for coll in COLLECTIONS_TO_PURGE:
        purge_collection(db, coll)

    # 3. Phone sessions (sauf Yves/Suzanne)
    purge_phone_sessions(db)

    print("=" * 60)
    print("✅ NETTOYAGE TERMINÉ")
    print("   Capital Norvex est prêt pour le JOUR 1 OFFICIEL")
    print("=" * 60)


if __name__ == "__main__":
    main()
