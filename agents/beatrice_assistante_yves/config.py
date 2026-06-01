"""Configuration Béatrice — assistante exécutive d'Yves Barrette.

Béatrice = ghostwriter pur sur yves@capitalnorvex.com. Tous drafts produits
sont signés "Yves Barrette" (signature_yves). Aucune mention publique de
Béatrice. Usage interne uniquement (Brain dashboard).

Coordination Camille ↔ Béatrice sur yves@ :
- Camille a `legal_only_filter: True` sur yves@ et traite UNIQUEMENT le juridique
  (notaires QC, avocats QC, solicitors ON, RDPRM)
- Béatrice traite TOUT LE RESTE non-juridique sur yves@
- Mutex sémantique : Béatrice SKIP les catégories juridiques

Autonomie : MOYENNE — autoSendSafe = False par défaut. Yves approuve
chaque envoi via le dashboard avant que ça parte.
"""
from __future__ import annotations

import os
import re
from typing import Dict, Literal

# ── Modèles Anthropic ────────────────────────────────────────────
MODEL_TRIAGE = "claude-sonnet-4-6"
MODEL_DRAFTING = "claude-opus-4-6"
MAX_TOKENS_TRIAGE = 1024
MAX_TOKENS_DRAFTING = 4096

# ── Identité Capital Norvex ──────────────────────────────────────
COMPANY_NAME = "Capital Norvex Inc."
COMPANY_ADDRESS = "2705-1000 André-Prévost, Île-des-Sœurs (Verdun), Montréal, QC H3E 0G2"
COMPANY_NEQ = "1182097890"
COMPANY_PHONE = "1-(438)-533-PRET (7738)"
COMPANY_WEBSITE = "capitalnorvex.com"

YVES_FULL_NAME = "Yves Barrette"
YVES_TITLE = "Directeur-Fondateur"

# ── Boîte d'approbation Yves (sa propre boîte) ───────────────────
YVES_APPROVAL_INBOX = os.getenv("CAMILLE_APPROVAL_INBOX", "yves@capitalnorvex.com")

# ── Persona ──────────────────────────────────────────────────────
PersonaMode = Literal["beatrice_executive"]

# ── Catégories JURIDIQUES = réservées à Camille (Béatrice SKIP) ───
LEGAL_CATEGORIES_RESERVED_FOR_CAMILLE = {
    "notaire_qc",
    "avocat_qc",
    "solicitor_on",
    "rdprm",
}

# ── Catégories que Béatrice traite (NON-juridique sur yves@) ──────
BEATRICE_DRAFTABLE_CATEGORIES = {
    "partenariat_capital",       # Capital, partenariats stratégiques majeurs
    "courtier_dossier",          # Courtier sur dossier en cours
    "promoteur_dossier",         # Promoteur sur dossier en cours
    "client_emprunteur",         # Client emprunteur (suivi dossier, questions)
    "prospect_referencement",    # Prospect adressé/référé directement à Yves
    "rdv_administratif",         # Demande de RDV / coordination agenda
    "fournisseur",               # Fournisseur / vendeur professionnel
    "autre_general",             # Autres sujets non-juridiques
}

# ── CC sur les envois ────────────────────────────────────────────
# Vide : c'est SA boîte, il voit son propre Sent. Pas besoin de se CC.
CC_YVES_CATEGORIES: set = set()

# ── Configuration boîtes surveillées par Béatrice ────────────────
# Béatrice ne polle QUE yves@ (Camille a déjà legal_only_filter=True sur yves@)
MAILBOXES: Dict[str, dict] = {
    "yves@capitalnorvex.com": {
        "persona": "beatrice_executive",
        "ghostwriter": True,                  # Tous drafts signés "Yves Barrette"
        "skip_legal_for_camille": True,       # Filtre : juridique → SKIP
        "skip_personal": True,                # Skip emails perso (famille/amis)
        "auto_send_default": False,           # Yves approuve chaque envoi
        "cc_email": None,                     # Pas de CC : c'est sa boîte
        "description": (
            "Boîte yves@ — Béatrice ghostwriter, autonomie MOYENNE. "
            "Camille gère le juridique en parallèle (legal_only_filter=True). "
            "Béatrice drafte le non-juridique non-personnel et notifie Yves "
            "pour approbation via dashboard."
        ),
    },
}


def get_mailbox_config(email: str) -> dict:
    key = (email or "").lower().strip()
    if key not in MAILBOXES:
        raise KeyError(f"Boîte non configurée pour Béatrice : {email}")
    return MAILBOXES[key]


def is_mailbox_active(email: str) -> bool:
    return (email or "").lower().strip() in MAILBOXES


def is_legal_reserved_for_camille(category: str) -> bool:
    """True si cette catégorie est juridique → Béatrice SKIP, Camille gère."""
    return (category or "").lower().strip() in LEGAL_CATEGORIES_RESERVED_FOR_CAMILLE


# ── Détection emails personnels (famille, amis) ──────────────────
# Heuristique conservative : si l'email vient d'un domaine perso connu d'Yves
# OU contient un marqueur perso explicite, on SKIP (jamais de ghostwriting
# sur sa correspondance privée).
_PERSONAL_DOMAINS = {
    # Domaines généralistes que Yves utilise potentiellement pour des contacts
    # personnels — on ne skip PAS uniquement sur le domaine, mais on combine
    # avec d'autres signaux pour réduire les faux positifs.
}

# Adresses perso explicites (à enrichir au fil du temps si Yves les signale).
# Format : email exact (lowercase) → SKIP automatique.
_PERSONAL_EMAIL_ALLOWLIST: set = {
    # Exemples (à compléter par Yves) :
    # "yvesbarrette33@gmail.com",   # Yves → Yves (auto-mail)
}

# Mots-clés explicitement personnels dans l'objet ou le corps : SKIP
#
# RÈGLE : phrases sans ambiguïté UNIQUEMENT. Un mot isolé comme "personnel"
# matche du vocabulaire dossier financier ("bilan personnel", "compte personnel",
# "revenus personnels", "déclaration personnelle") = faux positifs critiques.
# Incident 2026-05-18 : email Henri Petit (CNV-2026-59109, 27,5 M$, ami perso)
# skippé à tort à cause de "Bilan personnel" dans liste de PDFs. Fix : remplacer
# le mot brut "personnel" par 3 phrases sans ambiguïté.
_PERSONAL_KEYWORDS = (
    "famille",
    "anniversaire",
    "joyeux noël",
    "bonne année",
    "vacances",
    "souper",
    "brunch",
    "happy birthday",
    "courriel personnel",
    "message personnel",
    "affaire personnelle",
)


def is_personal_yves(*, from_address: str = "", subject: str = "",
                      body_text: str = "") -> bool:
    """Détecte si un email est PERSONNEL (famille, amis) → Béatrice SKIP.

    Heuristique conservative :
    - Allowlist explicite d'adresses persos → SKIP
    - Mots-clés persos clairs dans subject/body → SKIP

    En cas de doute, on retourne False (Béatrice traite, Yves peut toujours
    rejeter le draft). Le risque inverse — répondre par erreur à un email
    perso — est plus dommageable.
    """
    addr = (from_address or "").lower().strip()
    if addr and addr in _PERSONAL_EMAIL_ALLOWLIST:
        return True

    blob = f"{subject or ''} {body_text or ''}".lower()
    for kw in _PERSONAL_KEYWORDS:
        # Match mot entier pour limiter les faux positifs
        if re.search(rf"\b{re.escape(kw)}\b", blob):
            return True

    return False


# ── Détection senders « ne PAS répondre » ───────────────────────
# Yves 2026-05-04 : « il faut pas qu'on réponde à toutes sortes de courriels
# qu'il faut pas qu'on réponde — Microsoft, factures, pubs, notifications. »
# Ces emails sont à LIRE seulement (Yves les voit dans sa inbox), pas à drafter.
#
# Pattern : les expéditeurs no-reply, notifications systèmes, mailer-daemon,
# newsletters automatisées sont skippés AVANT l'appel LLM (économie API +
# pas de pollution dashboard).
_NO_REPLY_SENDER_PATTERNS = (
    "noreply@",
    "no-reply@",
    "no_reply@",
    "donotreply@",
    "do-not-reply@",
    "do_not_reply@",
    "mailer-daemon@",
    "postmaster@",
    "notifications@",
    "notification@",
    "alerts@",
    "alert@",
    "automated@",
    "system@",
    "bounces@",
    "bounce@",
    "newsletter@",
    "marketing@",
    "info-noreply@",
    "support-noreply@",
    "billing@",  # Stripe, factures auto — Yves voit, pas de réponse auto
    "invoicing@",
    "invoices@",
    "no.reply@",
)

# Domaines à skip systématiquement (notifications systèmes connues)
_NO_REPLY_DOMAIN_PATTERNS = (
    "@email.microsoft.com",
    "@microsoftonline.com",
    "@e.linkedin.com",
    "@e.linkedinmail.com",
    "@linkedin.com",  # invitations, notifications
    "@notifications.github.com",
    "@notifications.slack.com",
    "@stripe.com",
    "@noreply.netlify.com",
    "@email.facebook.com",
    "@facebookmail.com",
    "@accounts.google.com",
    "@googlegroups.com",
    "@email.apple.com",
    "@updates.linkedin.com",
    "@mailchimp.com",
    "@sendgrid.net",
    "@sendgridmail.com",
    "@auth.docusign.com",
    "@dse.docusign.net",
)

# Mots-clés sujet typiques notifications/factures/pubs (skip à la marge —
# uniquement si combiné avec sender suspect ou seul si TRÈS clair)
_NO_REPLY_SUBJECT_PATTERNS = (
    "invoice",
    "facture",
    "receipt",
    "reçu",
    "your order",
    "votre commande",
    "newsletter",
    "weekly digest",
    "monthly digest",
    "delivery failure",
    "undeliverable",
    "non remis",
    "verification code",
    "code de vérification",
    "password reset",
    "réinitialisation",
    "your subscription",
    "votre abonnement",
    "shipping notification",
)


def is_no_reply_sender(*, from_address: str = "", subject: str = "") -> bool:
    """True si l'email vient d'un sender automatique / no-reply → Béatrice SKIP.

    Yves veut LIRE ces emails dans sa inbox mais JAMAIS qu'on y réponde
    automatiquement. Cas typiques : notifications Microsoft/LinkedIn/GitHub,
    factures Stripe, mailer-daemon, newsletters, codes de vérification.

    Stratégie :
    1. Match adresse exacte (préfixe noreply@/notifications@/etc.)
    2. Match domaine (linkedin.com, microsoft.com newsletters, etc.)
    3. Match sujet typique (invoice, undeliverable, verification code) +
       sender ne contenant pas un nom humain plausible

    En cas de doute → False (Béatrice traite, Yves peut rejeter le draft).
    """
    addr = (from_address or "").lower().strip()
    if not addr:
        return False

    # 1) Préfixe local typique no-reply
    for pat in _NO_REPLY_SENDER_PATTERNS:
        if pat in addr:
            return True

    # 2) Domaine notifié systématique
    for pat in _NO_REPLY_DOMAIN_PATTERNS:
        if addr.endswith(pat):
            return True

    # 3) Sujet typique notification + sender suspect (= sans prénom humain
    #    avant le @, ex. "billing-team", "auto", "support" combiné avec sujet)
    subj = (subject or "").lower()
    if any(pat in subj for pat in _NO_REPLY_SUBJECT_PATTERNS):
        # Si le sender contient déjà un mot suspect (auto, system, support,
        # billing, no-reply variant) → SKIP
        local = addr.split("@", 1)[0]
        suspect_locals = (
            "auto", "system", "support", "billing", "noreply", "no-reply",
            "notifications", "alerts", "service", "team", "do-not-reply",
            "mailer", "postmaster",
        )
        if any(s in local for s in suspect_locals):
            return True

    return False


# ── Firestore collections ────────────────────────────────────────
COLLECTION_EMAILS = "beatriceEmails"
COLLECTION_DRAFTS = "beatriceDrafts"
AGENT_NAME = "beatrice"
