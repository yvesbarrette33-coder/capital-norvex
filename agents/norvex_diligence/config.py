"""Configuration Norvex Diligence™."""
from __future__ import annotations

import os

AGENT_NAME = "norvex_diligence"

# ── Modèles Claude ─────────────────────────────────────────────────
# Sonnet 4.6 pour interprétation HTML scraping.
# Opus 4.6 pour synthèse finale multi-sources (verdict global).
MODEL_SCRAPE = "claude-sonnet-4-6"
MODEL_SYNTHESIS = "claude-opus-4-6"
MAX_TOKENS_SCRAPE = 1500
MAX_TOKENS_SYNTHESIS = 2500

# ── Anthropic ──────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── User-Agent (être courtois envers les registres publics) ────────
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 "
    "(Capital-Norvex-Diligence/1.0; +https://capitalnorvex.com)"
)

# ── Timeouts HTTP ──────────────────────────────────────────────────
HTTP_TIMEOUT = 25  # secondes

# ── URLs des registres (publics, sans auth) ────────────────────────
URLS = {
    "req_search": "https://www.registreentreprises.gouv.qc.ca/RQEntreprises/GR/GR03/GR03A2_19A_PIU_RechEnt_PC/PageRechSimple.aspx",
    "rbq_search": "https://www.rbq.gouv.qc.ca/grand-public/services-en-ligne/recherche-detenteur-licence-rbq.html",
    "oaciq_search": "https://www.oaciq.com/fr/grand-public/registre-titulaires-permis",
    "amf_search": "https://lautorite.qc.ca/grand-public/registres/registre-des-entreprises-et-des-individus-autorises-a-exercer",
}

# ── Firestore collections ──────────────────────────────────────────
COLLECTION_REPORTS = "diligenceReports"   # 1 rapport par dossier
COLLECTION_AUDIT = "norvexAuditLog"

# ── Verdicts ───────────────────────────────────────────────────────
VERDICT_GREEN = "green"      # 🟢 Tout en règle
VERDICT_YELLOW = "yellow"    # 🟡 À vérifier (info manquante, doute mineur)
VERDICT_RED = "red"          # 🔴 Problème confirmé — BLOQUE Camille
VERDICT_GRAY = "gray"        # ⚪ Source non applicable / non vérifiable

# ── Garde-fous ─────────────────────────────────────────────────────
# Diligence NE :
#   - Ne BLOQUE jamais physiquement Camille (pas d'enforcement automatique)
#   - Ne contacte JAMAIS l'emprunteur, courtier ou entrepreneur directement
#   - N'écrit RIEN dans les registres officiels (lecture seule)
#   - Ne stocke PAS d'infos personnelles au-delà de ce que les registres
#     publics affichent déjà
# Diligence PEUT :
#   - Lire les registres publics
#   - Stocker un rapport JSON dans Firestore
#   - Notifier Yves dans Pipeline (badge couleur)
#   - Recommander GO/STOP — décision finale = Yves
