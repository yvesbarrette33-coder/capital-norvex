"""Filtre partagé : détection des senders no-reply / notifications / factures.

Yves 2026-05-04 : « il faut pas qu'on réponde à Microsoft, factures, pubs,
notifications. » Cette logique est partagée entre Béatrice (yves@), Sophie
(info@) et Camille (yves@ + info@) pour éviter :
  - les drafts gênants (« Bonjour Microsoft, je vous remercie de votre... »)
  - les coûts API inutiles (un appel LLM par notification automatisée)
  - le bruit dans les dashboards d'approbation

Stratégie : skip AVANT l'appel LLM si match sur :
  1. Préfixe local de l'adresse (noreply@, billing@, mailer-daemon@, ...)
  2. Domaine notification systématique (@notifications.github.com, @stripe.com, ...)
  3. Sujet typique notification combiné avec sender suspect
"""
from __future__ import annotations

# ── Préfixes locaux typiques no-reply ────────────────────────────
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
    "billing@",
    "invoicing@",
    "invoices@",
    "no.reply@",
)

# ── Domaines à skip systématiquement ─────────────────────────────
_NO_REPLY_DOMAIN_PATTERNS = (
    "@email.microsoft.com",
    "@microsoftonline.com",
    "@e.linkedin.com",
    "@e.linkedinmail.com",
    "@linkedin.com",
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

# ── Sujets typiques notifications/factures/pubs ──────────────────
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


# ── Patterns auto-reply / out-of-office (FR + EN multi-langues) ──
# Bug fix 2026-05-07 : Béatrice a drafté un suivi à un OOO de Mayrand David
# (RCGT) qui a été envoyé. Yves : « ça vaut pas la peine de répondre à un
# robot, on passe pour des amateurs ».
_AUTO_REPLY_SUBJECT_PATTERNS = (
    "automatic reply",
    "automatic reply:",
    "auto-reply",
    "auto reply:",
    "réponse automatique",
    "reponse automatique",
    "out of office",
    "out-of-office",
    "ooto",
    "out of the office",
    "absence du bureau",
    "hors du bureau",
    "hors-bureau",
    "vacation reply",
    "vacation auto-reply",
    "automated response",
    "réponse auto",
    "réponse d'absence",
    "réponse d absence",
    "absence reply",
    "[ooto]",
    "[ooo]",
    "i am out",
    "je suis absent",
    "je serai absent",
    "i will be out",
    "currently out of",
    "currently away",
    "on holiday",
    "on vacation",
    "en congé",
    "en vacances",
    "bureau fermé",
)


def is_auto_reply(*, subject: str = "") -> bool:
    """True si le SUJET indique un out-of-office / auto-reply humain.

    Différent de is_no_reply_sender (qui cible noreply@/notifications@).
    Ici on détecte les humains qui ont activé leur réponse automatique
    d'absence — ne PAS leur drafter une réponse de suivi (on passerait
    pour des amateurs qui répondent à un robot d'absence).
    """
    subj = (subject or "").lower().strip()
    if not subj:
        return False
    for pat in _AUTO_REPLY_SUBJECT_PATTERNS:
        if pat in subj:
            return True
    return False


def is_no_reply_sender(*, from_address: str = "", subject: str = "") -> bool:
    """True si l'email vient d'un sender automatique / no-reply → SKIP.

    Yves veut LIRE ces emails dans sa inbox mais JAMAIS qu'on y réponde
    automatiquement. Cas typiques : notifications Microsoft/LinkedIn/GitHub,
    factures Stripe, mailer-daemon, newsletters, codes de vérification.

    Stratégie :
    1. Match adresse exacte (préfixe noreply@/notifications@/etc.)
    2. Match domaine (linkedin.com, microsoft.com newsletters, etc.)
    3. Match sujet typique (invoice, undeliverable, verification code) +
       sender ne contenant pas un nom humain plausible

    En cas de doute → False (l'agent traite, Yves peut rejeter le draft).
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

    # 3) Sujet typique notification + sender suspect
    subj = (subject or "").lower()
    if any(pat in subj for pat in _NO_REPLY_SUBJECT_PATTERNS):
        local = addr.split("@", 1)[0]
        suspect_locals = (
            "auto", "system", "support", "billing", "noreply", "no-reply",
            "notifications", "alerts", "service", "team", "do-not-reply",
            "mailer", "postmaster",
        )
        if any(s in local for s in suspect_locals):
            return True

    return False
