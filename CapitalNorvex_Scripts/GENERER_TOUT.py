"""
╔══════════════════════════════════════════════════════════════╗
║        CAPITAL NORVEX — GÉNÉRER TOUS LES DOCUMENTS          ║
║        Double-clic ou : python GENERER_TOUT.py              ║
╚══════════════════════════════════════════════════════════════╝
"""
import subprocess
import sys
from pathlib import Path

scripts = Path(__file__).parent / "scripts"
print("\n🚀  Capital Norvex — Génération des documents PDF\n")

for script in sorted(scripts.glob("[0-9]*.py")):
    print(f"  📄  Génération : {script.stem}...")
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"      ✅  Succès")
    else:
        print(f"      ❌  Erreur : {result.stderr[-200:]}")

print(f"\n✅  Tous les PDFs sont dans :")
print(f"    /Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres/")
print("\n")
