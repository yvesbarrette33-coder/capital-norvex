"""Norvex Diligence™ — agent de due diligence pré-engagement.

Vérifie qu'un dossier est en règle AVANT d'envoyer la lettre d'engagement :
  - REQ (Registre des entreprises QC) — entreprise emprunteuse
  - RBQ (Régie du bâtiment) — entrepreneur (si construction)
  - OACIQ — courtier immobilier référent
  - AMF — courtier hypothécaire référent

Position dans le pipeline (verrouillé Yves 2026-05-05) :
  ... → RDV Teams → Diligence → GO #2 Yves → Camille (lettre engagement)
"""
