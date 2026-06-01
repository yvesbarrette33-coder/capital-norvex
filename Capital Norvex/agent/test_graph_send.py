#!/usr/bin/env python3
"""Test Microsoft Graph sendMail — Capital Norvex 2026-04-30."""
import sys
from datetime import datetime
from pathlib import Path

# Importer depuis agent_docs.py qui est dans le même dossier
sys.path.insert(0, str(Path(__file__).parent))
from agent_docs import send_email_via_graph, get_graph_token, MAIL_USER

DESTINATAIRE = "yvesbarrette21@gmail.com"

def main():
    print("="*70)
    print("TEST MICROSOFT GRAPH — Capital Norvex")
    print("="*70)
    print(f"Expéditeur (MAIL_USER): {MAIL_USER}")
    print(f"Destinataire:           {DESTINATAIRE}")
    print()

    # Étape 1 — récupérer un token
    print("→ Étape 1: récupération du token Microsoft Graph…")
    try:
        token = get_graph_token()
        print(f"   ✅ Token reçu (longueur: {len(token)} caractères)")
    except Exception as e:
        print(f"   ❌ ÉCHEC token: {e}")
        return 1

    # Étape 2 — envoyer le courriel test
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject   = f"Test Microsoft Graph - {timestamp}"
    html      = f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;padding:20px;">
  <h2 style="color:#C9A84C;">Test Microsoft Graph API ✅</h2>
  <p>Si tu reçois ce courriel dans ta boîte de réception (et <strong>pas dans le spam</strong>),
     ça veut dire que la migration Microsoft Graph fonctionne. 🎯</p>
  <p>Détails du test:</p>
  <ul>
    <li><strong>Date:</strong> {timestamp}</li>
    <li><strong>Expéditeur:</strong> {MAIL_USER}</li>
    <li><strong>Destinataire:</strong> {DESTINATAIRE}</li>
    <li><strong>Méthode:</strong> POST https://graph.microsoft.com/v1.0/users/{{user}}/sendMail</li>
  </ul>
  <p style="color:#888;font-size:12px;margin-top:30px;">
    — Capital Norvex / Norvex-Agent 2026
  </p>
</body></html>"""

    print()
    print("→ Étape 2: envoi via Graph API…")
    success = send_email_via_graph(DESTINATAIRE, subject, html)

    print()
    if success:
        print("="*70)
        print("✅ SUCCÈS — Courriel accepté par Microsoft Graph")
        print("="*70)
        print(f"   Va vérifier {DESTINATAIRE} (boîte de réception ET spam)")
        return 0
    else:
        print("="*70)
        print("❌ ÉCHEC — Voir les logs ci-dessus pour le détail")
        print("="*70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
