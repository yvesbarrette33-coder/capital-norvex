"""
Patch Hunter.io emails — 2026-05-07
Source : ~/Downloads/capital-norvex-2026-05-07-759576-all.csv

Patche UNIQUEMENT le champ email (dot-notation), aucun autre champ touché.
- capitalTargets → publicContact.email
- promoteurTargets → contactInfo.email

USAGE:
  python -m agents.shared.patch_hunter_emails_2026-05-07 --dry    # simulation
  python -m agents.shared.patch_hunter_emails_2026-05-07          # exécute
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

from agents.shared.firestore_client import db, audit_log

# 18 patches validés (16 valid + 2 accept-all crédibles)
# JUNK exclus : aidentifier@espaceslokalia.ca, aidentifier@habitationsplus.com,
#               cde-depot-et-placement-du-quebec@cdpq.com (format inventé)
PATCHES = [
    # capitalTargets (10)
    ("capitalTargets", "1ipsywi6rinY6a7k609b", "john.bitove@obelysk.com",                "Obelysk",                    "valid",      97),
    ("capitalTargets", "7MsKFCEplXsjpWsdCJI5", "mgrondin@samara.ca",                     "Samara",                     "valid",      98),
    ("capitalTargets", "WfM26wVTjIQ9pjtuOu1x", "tgaglardi@northland.ca",                 "Northland Properties",       "valid",      97),
    ("capitalTargets", "YLfXLDCDm7omrrE7s5HN", "mpathy@mavrik.com",                      "MAVRIK Corp.",               "valid",      96),
    ("capitalTargets", "Zyvb6WrZHN3oQmfRS9ot", "frochon@givernycapital.com",             "Giverny Capital",            "valid",      96),
    ("capitalTargets", "kH1GsHwQvnhw8Zp4R5zW", "csirois@telesystem.ca",                  "Telesystem (Charles Sirois)","valid",      97),
    ("capitalTargets", "mf8ysETSwwYF9c0OssoB", "jmccain@iriecapital.com",                "Irie Capital",               "valid",      98),
    ("capitalTargets", "u9hvQwomGo4ApQOkRxzY", "jmccain@woodwardcapital.ca",             "Woodward Capital",           "valid",      95),
    ("capitalTargets", "xApumCdiArbCj5XjlcGx", "dhenry@patrimonica.com",                 "Patrimonica",                "valid",      95),
    ("capitalTargets", "IDy8Sjf1Rjo1tbw8ooak", "mike.lazaridis@quantumvalleyinvestments.com", "Quantum Valley",        "accept_all", 79),
    # promoteurTargets (8)
    ("promoteurTargets","BOI99HId6mj3PuBSr22M", "tommy@constructom.ca",                   "ConstrucTom",               "valid",      98),
    ("promoteurTargets","YvzLR2AWPSRgNiBpRUIL", "matthieu@lionnare.com",                  "Lionnare",                  "valid",      95),
    ("promoteurTargets","l20HchUhQgB4qIZMHRyM", "rmalbeuf@structuresrp3.com",             "Structures RP3",            "valid",      96),
    ("promoteurTargets","uAj0Z2SlIunq3bIrZBTJ", "marco@parisienconstruction.com",         "Parisien Construction",     "valid",      98),
    ("promoteurTargets","OASBsfrRtqMMT9TmMHQm", "vincent@biophiliadeveloppementdurable.com","Biophilia",               "valid",      95),
    ("promoteurTargets","Xl8V26YamoVEAU0s13Yp", "emonticciolo@groupemonsap.com",          "Groupe Monsap",             "valid",      99),
    ("promoteurTargets","rTAGyWvc3rT5IIYO6ywK", "philippedusseault@immeublesmusturbain.com","Immeubles Must Urbain",   "valid",      96),
    ("promoteurTargets","tpqYC4Y0vIYyKJ7HuEuH", "ylemonde@habitationsurbania.com",        "Habitations Urbania",       "accept_all", 81),
]

FIELD_BY_COLLECTION = {
    "capitalTargets":   "publicContact",
    "promoteurTargets": "contactInfo",
}

def main(dry: bool):
    fs = db()
    now_iso = datetime.now(timezone.utc).isoformat()
    skipped, patched, errors = [], [], []

    print(f"\n{'🟡 DRY-RUN' if dry else '🚀 EXÉCUTION'} — {len(PATCHES)} patches\n")

    for col, doc_id, email, label, status, score in PATCHES:
        field = FIELD_BY_COLLECTION[col]
        ref = fs.collection(col).document(doc_id)
        snap = ref.get()
        if not snap.exists:
            errors.append((col, doc_id, label, "DOC INTROUVABLE"))
            print(f"  ❌ {col}/{doc_id} ({label}) — DOC INTROUVABLE")
            continue
        data = snap.to_dict()
        existing = ((data.get(field) or {}).get("email") or "").strip()
        if existing:
            skipped.append((col, doc_id, label, existing))
            print(f"  ⏭️  {col}/{doc_id:25s} ({label[:30]:30s}) — DÉJÀ : {existing}")
            continue

        # Patch dot-notation : touche QUE les sous-champs ciblés
        update_payload = {
            f"{field}.email":             email,
            f"{field}._enrichedBy":       "hunter.io",
            f"{field}._enrichedAt":       now_iso,
            f"{field}._hunterStatus":     status,
            f"{field}._hunterScore":      score,
        }

        if not dry:
            try:
                ref.update(update_payload)
                audit_log(
                    agent="hunter-patch-2026-05-07",
                    action="email_enrichment",
                    target_type=col,
                    target_id=doc_id,
                    result="success",
                    details={"email": email, "status": status, "score": score, "label": label},
                )
            except Exception as e:
                errors.append((col, doc_id, label, str(e)))
                print(f"  ❌ {col}/{doc_id} ({label}) — {e}")
                continue

        patched.append((col, doc_id, label, email))
        print(f"  {'🔍' if dry else '✅'} {col}/{doc_id:25s} ({label[:30]:30s}) → {email}  [{status} {score}]")

    print(f"\n— Résumé —")
    print(f"  Patchés    : {len(patched)}")
    print(f"  Sautés     : {len(skipped)} (email déjà présent)")
    print(f"  Erreurs    : {len(errors)}")
    if skipped:
        print(f"\n  ⏭️  Détails sautés :")
        for col, doc_id, label, existing in skipped:
            print(f"     {col}/{doc_id} ({label}) → {existing}")
    if errors:
        print(f"\n  ❌ Erreurs :")
        for col, doc_id, label, err in errors:
            print(f"     {col}/{doc_id} ({label}) → {err}")

if __name__ == "__main__":
    dry = "--dry" in sys.argv
    main(dry)
