"""Configuration Karine NORVEX FINANCE™.

Karine = CPA + Fiscaliste IA spécialisée en immobilier commercial et
comptabilité d'entreprise. Niveau Big Four (KPMG/Deloitte/EY/PwC) +
M.Fisc Sherbrooke / HEC.

Détection automatique :
- Factures fournisseurs reçues → dépenses
- Paiements clients (honoraires Capital Norvex) → revenus
- Paiements partenaires (courtiers/promoteurs) → catégorie partenaire
- Notes de frais Yves (repas, déplacement) → dépenses

Toutes les transactions détectées sont créées avec statut="pending"
dans Firestore et apparaissent dans le dashboard Brain pour validation
par Yves.
"""
from __future__ import annotations

import os

AGENT_NAME = "karine_norvex_finance"

# ── Modèle Claude ────────────────────────────────────────────────
# Sonnet 4.6 pour le triage + Sonnet 4.6 multimodal pour OCR factures.
# (Pas besoin d'Opus : extraction structurée + catégorisation fiscale,
# pas de raisonnement long ; analyze-invoice.mjs déjà rodé sur Sonnet.)
MODEL_TRIAGE = "claude-sonnet-4-6"
MODEL_EXTRACTION = "claude-sonnet-4-6"
MAX_TOKENS_TRIAGE = 800
MAX_TOKENS_EXTRACTION = 1500

# ── Boîtes mail surveillées ──────────────────────────────────────
# Karine lit info@ (factures arrivent souvent là) et yves@ (notes de frais
# personnelles, paiements directs aux comptes Yves, etc.).
MAILBOXES = {
    "info@capitalnorvex.com": True,
    "yves@capitalnorvex.com": True,
    # camille@ : non — c'est juridique, pas comptable
}

def is_mailbox_active(mailbox: str) -> bool:
    return MAILBOXES.get((mailbox or "").lower(), False)

# ── Catégories Brain (enum existant à respecter) ─────────────────
# Source : capital-norvex-brain.html, fonction onTxTypeChange() ligne 1434
CATEGORIES_REVENU = {
    "honoraires_montage",
    "frais_admin",
    "interets",
    "autres_revenus",
}

CATEGORIES_DEPENSE = {
    "salaire",
    "loyer",
    "comptable",
    "marketing",
    "materiel",
    "autres_depenses",
}

CATEGORIES_PARTENAIRE = {
    "paiement_partenaire",
}

# ── Mapping catégories analyze-invoice.mjs → enum Brain ──────────
# analyze-invoice.mjs retourne 12 catégories génériques :
#   loyer_bureau, salaires_contractuels, services_professionnels,
#   marketing_pub, telecom_logiciels, assurances, fournitures_bureau,
#   transport_deplacement, repas_representation, formation,
#   frais_bancaires, autre
INVOICE_CAT_TO_BRAIN_CAT = {
    "loyer_bureau":           "loyer",
    "salaires_contractuels":  "salaire",
    "services_professionnels":"comptable",  # Notaire/avocat/CPA → comptable
    "marketing_pub":          "marketing",
    "telecom_logiciels":      "materiel",
    "assurances":             "autres_depenses",
    "fournitures_bureau":     "materiel",
    "transport_deplacement":  "autres_depenses",
    "repas_representation":   "autres_depenses",  # Karine notera "50% déductible"
    "formation":              "autres_depenses",
    "frais_bancaires":        "autres_depenses",
    "autre":                  "autres_depenses",
}

# ── Détection filtres pré-LLM (économie API) ─────────────────────
# Si l'email matche AUCUN de ces critères, on skip avant Claude.

# Mots-clés sujet/corps qui SUGGÈRENT une transaction financière
FINANCIAL_SUBJECT_KEYWORDS = {
    # FR
    "facture", "reçu", "recu", "paiement", "payment", "montant", "honoraires",
    "tps", "tvq", "taxes", "remboursement", "frais", "abonnement",
    "renouvellement", "transfert", "virement", "interac", "chèque", "cheque",
    "salaire", "paie", "loyer", "invoice", "bill", "statement", "relevé",
    "releve", "facturation", "billing",
    # EN
    "receipt", "amount due", "balance", "wire transfer", "ACH", "EFT",
    "subscription", "renewal", "refund",
}

# Domaines/expéditeurs qui envoient typiquement des factures
FINANCIAL_SENDER_PATTERNS = {
    "billing@", "invoice@", "facturation@", "noreply@stripe", "stripe.com",
    "@quickbooks.com", "@xero.com", "@waveapps.com", "@freshbooks.com",
    "@hellofresh", "@interac", "@desjardins", "@bnc", "@rbc.com", "@td.com",
    "@bmo.com", "@nbc.ca", "@whc.ca", "@netlify.com", "@anthropic.com",
    "@sendgrid.net", "@twilio.com", "@elevenlabs.io", "@firebase.google.com",
    "@google.com", "@apple.com", "@microsoft.com", "@office.com",
    "@adobe.com", "@github.com", "@zoom.us", "@dropbox.com",
    "@vidéotron", "@videotron", "@bell.ca", "@rogers.com", "@telus.com",
    "@whc.com",
    "no-reply@",  # Souvent factures auto
}

# Pièces jointes qui suggèrent une facture
FINANCIAL_ATTACHMENT_KEYWORDS = {
    "facture", "invoice", "receipt", "reçu", "bill", "statement", "relevé",
}

# ── Firestore collections ────────────────────────────────────────
COLLECTION_TRANSACTIONS = "transactions"     # Cible principale (déjà utilisée par Brain UI)
COLLECTION_AUDIT = "norvexAuditLog"          # Audit trail centralisé
COLLECTION_KARINE_DRAFTS = "karineDrafts"    # Optionnel : preview avec PDF original avant approbation

# ── Anthropic ────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── Endpoint OCR existant (analyze-invoice.mjs) ──────────────────
NETLIFY_SITE_URL = os.environ.get("NETLIFY_SITE_URL", "https://capitalnorvex.com")
ANALYZE_INVOICE_ENDPOINT = f"{NETLIFY_SITE_URL}/.netlify/functions/analyze-invoice"

# ── Anti-doublon : on garde les Message-IDs déjà traités ─────────
COLLECTION_PROCESSED = "karineProcessedMessages"

# ── Yves ─────────────────────────────────────────────────────────
YVES_EMAIL = "yves@capitalnorvex.com"

# ── Garde-fous ───────────────────────────────────────────────────
# Karine NE :
# - Ne supprime jamais une transaction
# - Ne modifie jamais une transaction confirmée par Yves
# - Ne dépense JAMAIS d'argent (pas de paiement automatique)
# - N'envoie JAMAIS d'email externe sans approbation Yves
# Tout passe par "pending" → Yves valide dans Brain.
ALLOW_AUTO_CONFIRM = False  # NEVER True. Yves valide toujours.
