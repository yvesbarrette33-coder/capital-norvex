"""CLI Norvex Diligence™ — pour usage manuel et tests.

Usage :
  python -m agents.norvex_diligence --dossier CNV-2026-0001 \\
      --emprunteur-neq 1234567890 \\
      --rbq-nom "Construction Untel inc." --type-projet commercial \\
      --courtier-immo-nom "Jean Dupont"
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from .orchestrator import run_diligence

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [diligence] %(levelname)s %(message)s",
)


def main() -> int:
    p = argparse.ArgumentParser(prog="norvex_diligence")
    p.add_argument("--dossier", required=True, help="ID dossier Firestore")
    p.add_argument("--emprunteur-neq", default=None)
    p.add_argument("--emprunteur-nom", default=None)
    p.add_argument("--rbq-licence", default=None)
    p.add_argument("--rbq-nom", default=None)
    p.add_argument("--type-projet", default=None,
                   choices=[None, "residentiel", "commercial", "industriel"])
    p.add_argument("--courtier-immo-nom", default=None)
    p.add_argument("--courtier-immo-permis", default=None)
    p.add_argument("--courtier-hypo-nom", default=None)
    p.add_argument("--courtier-hypo-inscription", default=None)
    p.add_argument("--rfq-pdf", default=None,
                   help="Chemin vers PDF index RFQ (optionnel)")
    p.add_argument("--rfq-loan-amount", type=float, default=None)
    p.add_argument("--rfq-property-value", type=float, default=None)
    p.add_argument("--rfq-property-address", default=None)
    args = p.parse_args()

    rfq_bytes = None
    if args.rfq_pdf:
        with open(args.rfq_pdf, "rb") as f:
            rfq_bytes = f.read()

    result = run_diligence(
        dossier_id=args.dossier,
        emprunteur_neq=args.emprunteur_neq,
        emprunteur_nom=args.emprunteur_nom,
        entrepreneur_licence_rbq=args.rbq_licence,
        entrepreneur_nom=args.rbq_nom,
        type_projet=args.type_projet,
        courtier_immo_nom=args.courtier_immo_nom,
        courtier_immo_permis=args.courtier_immo_permis,
        courtier_hypo_nom=args.courtier_hypo_nom,
        courtier_hypo_inscription=args.courtier_hypo_inscription,
        rfq_pdf_bytes=rfq_bytes,
        rfq_loan_amount=args.rfq_loan_amount,
        rfq_property_value=args.rfq_property_value,
        rfq_property_address=args.rfq_property_address,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
