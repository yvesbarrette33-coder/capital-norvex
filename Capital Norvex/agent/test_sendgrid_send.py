#!/usr/bin/env python3
"""Test SendGrid sendMail — Capital Norvex 2026-04-30."""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from agent_docs import send_email_via_sendgrid, MAIL_USER

DESTINATAIRE = "info@capitalnorvex.com"

def main():
    print("="*70)
    print("TEST SENDGRID — Capital Norvex")
    print("="*70)
    print(f"Expéditeur: {MAIL_USER}")
    print(f"Destinataire: {DESTINATAIRE}")
    print()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject   = f"Test SendGrid - {timestamp}"
    html      = f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;padding:20px;">
  <h2 style="color:#C9A84C;">Test SendGrid ✅</h2>
  <p>Si tu reçois ce courriel <strong>dans la boîte de réception</strong>,
     ça veut dire que SendGrid bypasse bien le blocage M365 outbound. 🎯</p>
  <p>Détails:</p>
  <ul>
    <li><strong>Date:</strong> {timestamp}</li>
    <li><strong>Expéditeur:</strong> {MAIL_USER}</li>
    <li><strong>Destinataire:</strong> {DESTINATAIRE}</li>
    <li><strong>Méthode:</strong> SendGrid API v3 (IPs SendGrid, pas M365)</li>
  </ul>
  <p style="color:#888;font-size:12px;margin-top:30px;">
    — Capital Norvex / Norvex-Agent 2026
  </p>
</body></html>"""

    print("→ Envoi via SendGrid…")
    success = send_email_via_sendgrid(DESTINATAIRE, subject, html)
    print()
    if success:
        print("✅ SUCCÈS — SendGrid a accepté le courriel")
        print(f"   Va vérifier {DESTINATAIRE} (boîte de réception ET spam)")
        return 0
    else:
        print("❌ ÉCHEC — voir logs ci-dessus")
        return 1

if __name__ == "__main__":
    sys.exit(main())
