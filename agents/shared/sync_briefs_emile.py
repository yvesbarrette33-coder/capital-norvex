"""Sync briefs Émile : Firestore (emileBriefs) → ~/Desktop/Briefs Émile/

Pull tous les briefs Émile avec champ `html` non vide et écrit chacun
dans le dossier Desktop sous le nom :
    BRIEF_<orgClean>_<nameClean>_<YYYY-MM-DD>.html

Idempotent : ne ré-écrit pas un fichier existant identique.

Usage :
    python -m agents.shared.sync_briefs_emile
    python -m agents.shared.sync_briefs_emile --force   # re-écrit tout
"""
import os
import re
import argparse
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/.capitalnorvex/.env'))

from agents.shared.firestore_client import db

DEST = Path.home() / "Desktop" / "Briefs Émile"
DEST.mkdir(parents=True, exist_ok=True)


def slugify(s: str) -> str:
    if not s:
        return "inconnu"
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s-]+", "_", s).strip("_")
    return s[:60] or "inconnu"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Ré-écrit même les fichiers existants")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    fs = db()
    docs = list(fs.collection("emileBriefs").stream())
    if not args.quiet:
        print(f"📥 {len(docs)} briefs en Firestore — destination : {DEST}")

    written = skipped = empty = 0
    for d in docs:
        data = d.to_dict() or {}
        html = data.get("html", "")
        if not html or not html.strip():
            empty += 1
            continue
        org = slugify(data.get("targetOrg", "?"))
        name = slugify(data.get("targetName", data.get("email", d.id)))
        # generatedAt → YYYY-MM-DD (sinon fallback brief id)
        gen = data.get("generatedAt", "")[:10] if data.get("generatedAt") else d.id[:10]
        filename = f"BRIEF_{org}_{name}_{gen}.html"
        path = DEST / filename
        if path.exists() and not args.force:
            # Compare longueur pour détecter régénération
            if path.stat().st_size == len(html.encode("utf-8")):
                skipped += 1
                continue
        path.write_text(html, encoding="utf-8")
        written += 1
        if not args.quiet:
            print(f"  ✅ {filename}")

    if not args.quiet:
        print(f"\n📊 Résumé : {written} écrit(s), {skipped} déjà à jour, {empty} sans HTML")


if __name__ == "__main__":
    main()
