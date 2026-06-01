"""Configuration Norvex Maestro™.

Maestro = méta-orchestrateur. Il NE drafte pas d'emails. Il NE répond pas.
Il OBSERVE l'écosystème, DÉCIDE qui doit traiter chaque email entrant,
ENREGISTRE les décisions dans Firestore, et ALERTE Yves des conflits ou
opportunités.

Il chapeaute :
  - Camille NORVEX COUNSEL™ (juridique)
  - Sophie NORVEX RELATIONS™ (service client info@)
  - Béatrice (ghostwriter Yves yves@)
  - Hugo NORVEX CHANTIER™ (analyse construction)
  - Karine NORVEX FINANCE™ (CPA/fiscaliste)

Le Score Norvex (porte d'entrée client) est SURVEILLÉ mais JAMAIS modifié
(ZONE INTERDITE).
"""
from __future__ import annotations

import os

AGENT_NAME = "norvex_maestro"

# ── Modèle Claude ─────────────────────────────────────────────────
# Sonnet 4.6 pour méta-triage (rapide, pas de raisonnement long).
# Opus 4.6 pour le brief quotidien synthèse (analyse multi-domaines).
MODEL_TRIAGE = "claude-sonnet-4-6"
MODEL_BRIEF = "claude-opus-4-6"
MAX_TOKENS_TRIAGE = 600
MAX_TOKENS_BRIEF = 4000

# ── Boîtes mail surveillées ───────────────────────────────────────
# Maestro lit TOUTES les boîtes en 1 passe pour avoir la vue globale.
MAILBOXES = (
    "info@capitalnorvex.com",
    "yves@capitalnorvex.com",
    # camille@ (si activée plus tard) :
    # "camille@capitalnorvex.com",
)

# ── Agents spécialistes connus ────────────────────────────────────
# Maestro dispatch un email vers UN ET UN SEUL agent.
SPECIALISTS = {
    "camille": {
        "name": "Camille NORVEX COUNSEL™",
        "domain": "juridique",
        "mailboxes": ("info@capitalnorvex.com", "yves@capitalnorvex.com"),
        "categories": {
            "juridique_contrat", "juridique_litige", "juridique_signature",
            "juridique_loi25", "juridique_general",
        },
    },
    "sophie": {
        "name": "Sophie NORVEX RELATIONS™",
        "domain": "service client général",
        "mailboxes": ("info@capitalnorvex.com",),
        "categories": {
            "client_general", "courtier_inquiry", "promoteur_inquiry",
            "partenaire_inquiry", "presse_pr", "rdv_request_general",
            "info_request",
        },
    },
    "beatrice": {
        "name": "Béatrice (ghostwriter Yves)",
        "domain": "exécutif Yves",
        "mailboxes": ("yves@capitalnorvex.com",),
        "categories": {
            "executive_general", "rdv_with_yves", "investor_relation",
            "personal_business", "operational_yves",
        },
    },
    "hugo": {
        "name": "Hugo NORVEX CHANTIER™",
        "domain": "analyse construction",
        "mailboxes": (),  # Hugo n'écoute PAS des emails — déclenché par Pipeline
        "categories": set(),
    },
    "karine": {
        "name": "Karine NORVEX FINANCE™",
        "domain": "comptabilité fiscale",
        "mailboxes": ("info@capitalnorvex.com", "yves@capitalnorvex.com"),
        "categories": {
            "facture_fournisseur", "paiement_recu",
            "paiement_partenaire", "note_de_frais",
            "fiscal", "releve_bancaire",
        },
    },
}

# ── Catégories Maestro (méta) ─────────────────────────────────────
# Au-dessus des catégories spécialistes : Maestro choisit la VOIE.
MAESTRO_ROUTES = {
    "to_camille": "Délègue à Camille (juridique)",
    "to_sophie": "Délègue à Sophie (service client général)",
    "to_beatrice": "Délègue à Béatrice (exécutif Yves)",
    "to_karine": "Délègue à Karine (comptabilité)",
    "to_yves_directly": "Aucun agent ne devrait drafter — Yves doit lire et répondre lui-même (personnel/sensible/ambigu)",
    "to_hugo_pipeline": "Pas un email à drafter — Hugo doit déclencher analyse via Pipeline (rapports construction)",
    "ignore_no_reply": "No-reply / notification automatique / spam — ignorer",
    "alert_yves_priority": "URGENT : Yves doit voir tout de suite (red flag, urgence opérationnelle, etc.)",
}

# ── Firestore collections ─────────────────────────────────────────
COLLECTION_DISPATCH = "maestroDispatch"      # Décisions de routing par message
COLLECTION_OBSERVATIONS = "maestroObservations"  # État global / métriques
COLLECTION_AUDIT = "norvexAuditLog"          # Audit trail centralisé partagé

# ── Anti-doublon ──────────────────────────────────────────────────
# Maestro évite de re-trier un message déjà dispatché.
# Clé : Message-ID Internet (stable cross-mailboxes).

# ── Anthropic ─────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── Yves ──────────────────────────────────────────────────────────
YVES_EMAIL = "yves@capitalnorvex.com"

# ── Brief quotidien ───────────────────────────────────────────────
# Maestro envoie un brief AU-DELÀ de Brain Daily Brief (qui digest la veille).
# Maestro Brief = vue temps réel des 24h dernières + recommandations actives.
BRIEF_HOUR_LOCAL = 7  # 7h45 EDT (15 min après Brain Daily Brief)
BRIEF_MINUTE_LOCAL = 45

# ── Garde-fous ────────────────────────────────────────────────────
# Maestro NE :
#   - N'envoie JAMAIS d'email externe
#   - Ne MODIFIE JAMAIS un draft d'un autre agent
#   - Ne CONTROLE JAMAIS le Score Norvex (ZONE INTERDITE — porte d'entrée client)
#   - Ne CRÉE JAMAIS de transaction Firestore (c'est Karine)
#   - Ne SUPPRIME JAMAIS rien
#
# Maestro PEUT :
#   - Lire toutes les boîtes
#   - Créer des entrées dans maestroDispatch (recommandation routing)
#   - Créer des observations dans maestroObservations
#   - Envoyer un brief résumé à yves@ (1×/jour + alertes urgentes)
#   - Logger dans norvexAuditLog
ALLOWED_TO_DRAFT_EMAILS = False  # NEVER True
ALLOWED_TO_SEND_EXTERNAL_EMAILS = False  # NEVER True
ALLOWED_TO_MODIFY_OTHER_AGENTS = False  # NEVER True

# ── Cron interval ─────────────────────────────────────────────────
# 5 minutes : plus rapide que Sophie/Camille/Béatrice (10 min) et Karine (30 min)
# pour être le PREMIER à voir et router. Les agents spécialistes lisent ensuite
# maestroDispatch avant de drafter.
CRON_INTERVAL_SECONDS = 300
