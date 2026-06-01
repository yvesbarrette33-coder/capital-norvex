"""Hugo NORVEX CHANTIER™ — Orchestrateur IA des modules construction.

Hugo gère les 3 modules construction de Capital Norvex :
- Norvex Intel (évaluation immobilière 3 approches)
- Norvex Track (suivi de chantier)
- Norvex Cost Analyzer (analyse des coûts)

Il s'enclenche après réception complète de la documentation post-LOI :
1. Reçoit un dossierId
2. Appelle en parallèle les 3 endpoints orchestrateurs
3. Synthétise les verdicts en UN verdict global construction
4. Décide de l'action (déboursé OK / info requise / escalade Yves)
5. Pousse les résultats dans Norvex Brain (comptabilité)
6. Notifie Yves si nécessaire

Verrouillé à l'usage interne (clé INTERNAL_SECRET) — pas exposé client.
"""
__version__ = "1.0.0"
__agent_name__ = "hugo_norvex_chantier"
