"""Configuration Hugo NORVEX CHANTIER™."""
from __future__ import annotations

import os

# ─── Identité ────────────────────────────────────────────────────────────
AGENT_NAME = "hugo_norvex_chantier"
AGENT_DISPLAY_NAME = "Hugo — NORVEX CHANTIER™"
AGENT_TITLE_FR = "Coordonnateur technique chantier IA"
AGENT_TITLE_EN = "Construction Technical Coordinator (AI)"

# ─── URL & Auth ──────────────────────────────────────────────────────────
SITE_URL = os.environ.get("SITE_URL", "https://capitalnorvex.com")
INTERNAL_SECRET = os.environ.get("INTERNAL_SECRET")

# ─── Endpoints orchestrateurs (déployés 2026-05-05) ──────────────────────
ENDPOINT_INTEL = f"{SITE_URL}/api/intel-analyze-dossier"
ENDPOINT_TRACK = f"{SITE_URL}/api/track-analyze-dossier"
ENDPOINT_COST = f"{SITE_URL}/api/cost-analyze-dossier"
ENDPOINT_BRAIN_PUSH = f"{SITE_URL}/api/brain-push-from-hugo"

# ─── Modèles Anthropic ───────────────────────────────────────────────────
# Hugo lui-même utilise Opus pour la synthèse finale (décision business)
# Les 3 endpoints orchestrateurs utilisent Sonnet/Opus selon leur tâche.
MODEL_SYNTHESIS = "claude-opus-4-6"
SYNTHESIS_MAX_TOKENS = 2000

# ─── Seuils business ─────────────────────────────────────────────────────
# Si l'un des 3 modules est CRITIQUE → Hugo escalade Yves automatiquement
ESCALATION_TRIGGERS = ["Critique", "refus_recommande"]

# Si verdict global Hugo = critique, on bloque le déboursé
DISBURSEMENT_BLOCK_VERDICTS = ["Critique", "refus_recommande"]

# ─── Notifications Yves ──────────────────────────────────────────────────
YVES_EMAIL = "yves@capitalnorvex.com"
YVES_CC_ON_REPORTS = True  # Yves CC sur tous les rapports Hugo

# ─── Firestore ───────────────────────────────────────────────────────────
COLLECTION_HUGO_REPORTS = "hugoReports"
COLLECTION_AUDIT_LOG = "agentAuditLog"
