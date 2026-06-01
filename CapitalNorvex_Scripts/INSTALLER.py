"""
╔══════════════════════════════════════════════════════════════╗
║         CAPITAL NORVEX — INSTALLATEUR DE DOCUMENTS          ║
║         À exécuter avec Claude Code sur le Mac de Yves      ║
╚══════════════════════════════════════════════════════════════╝

Ce script :
1. Crée le dossier CapitalNorvex sur le Bureau
2. Adapte automatiquement tous les chemins
3. Génère les 4 documents PDF directement sur le Bureau
4. Installe les scripts pour régénérer à tout moment

Usage avec Claude Code :
    python INSTALLER.py
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# ── Détection automatique du Bureau Mac ──────────────────────────────────────
HOME = Path.home()
BUREAU = HOME / "Desktop" / "Capital Norvex"
SCRIPTS_DIR = BUREAU / "scripts"
LOGOS_DIR   = BUREAU / "logos"
OUTPUT_DIR  = BUREAU / "Documents PDF"

def banner(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print('='*60)

def etape(msg):
    print(f"  ✦  {msg}")

# ── Étape 1 : Créer la structure de dossiers ─────────────────────────────────
banner("ÉTAPE 1 — Création des dossiers sur le Bureau")
for d in [BUREAU, SCRIPTS_DIR, LOGOS_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
    etape(f"Dossier créé : {d}")

# ── Étape 2 : Installer les dépendances Python ────────────────────────────────
banner("ÉTAPE 2 — Vérification des dépendances Python")
try:
    import reportlab
    etape("reportlab ✅ déjà installé")
except ImportError:
    etape("Installation de reportlab...")
    subprocess.run([sys.executable, "-m", "pip", "install", "reportlab", "Pillow"], check=True)
    etape("reportlab ✅ installé")

try:
    from PIL import Image
    etape("Pillow ✅ déjà installé")
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "Pillow"], check=True)
    etape("Pillow ✅ installé")

# ── Étape 3 : Copier les logos ────────────────────────────────────────────────
banner("ÉTAPE 3 — Copie des logos Capital Norvex")
script_location = Path(__file__).parent
logos_source = script_location / "logos"

if logos_source.exists():
    for logo_file in logos_source.glob("*.png"):
        dest = LOGOS_DIR / logo_file.name
        shutil.copy2(logo_file, dest)
        etape(f"Logo copié : {logo_file.name}")
else:
    print("  ⚠️  Dossier logos non trouvé — placer les PNG dans le même dossier que INSTALLER.py")

# ── Étape 4 : Adapter et copier les scripts ───────────────────────────────────
banner("ÉTAPE 4 — Adaptation des scripts aux chemins Mac")

scripts_source = script_location / "scripts"
EMBLEM = str(LOGOS_DIR / "emblem_header.png")
COVER  = str(LOGOS_DIR / "logo_cover.png")

script_files = {
    "01_lettres_engagement.py":  "Lettres d'engagement (Construction, Terrain, Acquisition)",
    "02_convention_pret.py":     "Convention de prêt de construction",
    "03_sommaire_executif.py":   "Sommaire exécutif partenaire",
}

for filename, description in script_files.items():
    src = scripts_source / filename
    if not src.exists():
        print(f"  ⚠️  {filename} non trouvé")
        continue

    code = src.read_text(encoding="utf-8")

    # Remplacer les chemins des logos
    code = code.replace(
        "EMBLEM_PATH = '/home/claude/emblem_header.png'",
        f"EMBLEM_PATH = r'{EMBLEM}'"
    ).replace(
        "EMBLEM_PATH  = '/home/claude/emblem_header.png'",
        f"EMBLEM_PATH  = r'{EMBLEM}'"
    ).replace(
        "COVER_PATH  = '/home/claude/logo_cover.png'",
        f"COVER_PATH  = r'{COVER}'"
    ).replace(
        "COVER_PATH   = '/home/claude/logo_cover.png'",
        f"COVER_PATH   = r'{COVER}'"
    ).replace(
        "EMBLEM_PATH = \"/home/claude/emblem_header.png\"",
        f"EMBLEM_PATH = r'{EMBLEM}'"
    ).replace(
        "COVER_PATH = \"/home/claude/logo_cover.png\"",
        f"COVER_PATH = r'{COVER}'"
    )

    # Remplacer les chemins de sortie
    code = code.replace(
        '"/mnt/user-data/outputs/',
        f'r"{OUTPUT_DIR}/'
    ).replace(
        "'/mnt/user-data/outputs/",
        f"r'{OUTPUT_DIR}/"
    )

    # Écrire le script adapté
    dest = SCRIPTS_DIR / filename
    dest.write_text(code, encoding="utf-8")
    etape(f"Script adapté : {filename}")
    etape(f"   → {description}")

# ── Étape 5 : Créer le script "GÉNÉRER TOUS LES PDFs" ────────────────────────
banner("ÉTAPE 5 — Création du script de génération rapide")

generer_tout = f'''"""
╔══════════════════════════════════════════════════════════════╗
║        CAPITAL NORVEX — GÉNÉRER TOUS LES DOCUMENTS          ║
║        Double-clic ou : python GENERER_TOUT.py              ║
╚══════════════════════════════════════════════════════════════╝
"""
import subprocess
import sys
from pathlib import Path

scripts = Path(__file__).parent / "scripts"
print("\\n🚀  Capital Norvex — Génération des documents PDF\\n")

for script in sorted(scripts.glob("0*.py")):
    print(f"  📄  Génération : {{script.stem}}...")
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"      ✅  Succès")
    else:
        print(f"      ❌  Erreur : {{result.stderr[-200:]}}")

print(f"\\n✅  Tous les PDFs sont dans :")
print(f"    {OUTPUT_DIR}")
print("\\n")
'''

generer_path = BUREAU / "GENERER_TOUT.py"
generer_path.write_text(generer_tout, encoding="utf-8")
etape(f"Script créé : GENERER_TOUT.py")

# ── Étape 6 : Générer les PDFs immédiatement ─────────────────────────────────
banner("ÉTAPE 6 — Génération initiale de tous les PDFs")

for filename in script_files:
    script_path = SCRIPTS_DIR / filename
    if script_path.exists():
        etape(f"Génération : {filename}...")
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"      ✅  Succès")
        else:
            print(f"      ❌  Erreur :")
            print(result.stderr[-300:])

# ── Résumé final ──────────────────────────────────────────────────────────────
banner("INSTALLATION TERMINÉE ✅")
print(f"""
  📁  Dossier principal  : {BUREAU}
  📁  Scripts            : {SCRIPTS_DIR}
  📁  Logos              : {LOGOS_DIR}
  📁  Documents PDF      : {OUTPUT_DIR}

  Pour régénérer tous les PDFs :
  → Double-clic sur GENERER_TOUT.py
  → Ou demander à Claude Code de modifier un script + le rouler

  Documents générés :
  → 3 × Lettres d'engagement (Construction, Terrain, Acquisition)
  → 1 × Convention de prêt de construction
  → 1 × Sommaire exécutif partenaire

  Capital structuré. Ambition maîtrisée. 🏆
""")
