"""Black-list permanente Capital Norvex — anti-récidive de sollicitation.

⛔ ZONE INTERDITE — Yves a explicitement banni ces destinataires de TOUTE
sollicitation outbound. Litige juridique, conflit personnel, ou décision
stratégique long-terme.

Toute fonction d'envoi outbound DOIT importer `is_blacklisted(email)` et
refuser l'envoi avant de toucher SendGrid.

Mise à jour : ajouter une entrée + raison + date. Ne jamais retirer sans
GO explicite Yves dans la conversation, jamais via auto-merge.
"""

from __future__ import annotations
from typing import Iterable

# Domaines bannis (entiers) — tout email @<domaine> est refusé.
BANNED_DOMAINS: frozenset[str] = frozenset({
    "groupetcj.ca",          # Therrien Couture Joli-Cœur — LITIGE 2026-05-08
    "therriencouture.com",   # ancien domaine TCJ — LITIGE 2026-05-08
    "langlois.ca",           # Langlois Avocats — relations personnelles Yves 2026-05-08
    "gfaa.ca",               # Groupe FAA Construction — historique projet 2026-05-11
    "habra.ca",              # Habitations Raymond Allard — historique projet 2026-05-11
    "groupefaa.ca",          # site web Groupe FAA — historique projet 2026-05-11
    "groupeevoludev.com",    # Groupe Evoludev — décision Yves 2026-05-12
    "groupeevex.com",        # Groupe EVEX — décision Yves 2026-05-12
    "groupemainland.ca",     # Groupe Mainland — décision Yves 2026-05-12
})

# Emails individuels bannis (au cas par cas, indépendamment du domaine).
BANNED_EMAILS: frozenset[str] = frozenset({
    "claude.tessier@couche-tard.com",  # RETRAITE depuis 2023 — boîte désactivée (confirmé Yves 2026-05-12)
    "hwu@pmml.ca",                     # Hao Wu PMML — boîte fermée (mx_connect_refused) — bounces quotidiens à Yves 2026-05-26
})

# Raisons documentaires (pour logs / audits).
BLACKLIST_REASONS = {
    "groupetcj.ca": "LITIGE Yves — TCJ — interdiction permanente 2026-05-08",
    "therriencouture.com": "LITIGE Yves — TCJ ancien domaine — interdiction permanente 2026-05-08",
    "langlois.ca": "Relations personnelles Yves — Langlois Avocats 2026-05-08",
    "gfaa.ca": "Historique projet — Groupe FAA — interdiction permanente 2026-05-11",
    "habra.ca": "Historique projet — Habitations Raymond Allard — interdiction permanente 2026-05-11",
    "groupefaa.ca": "Historique projet — Groupe FAA (site web) — interdiction permanente 2026-05-11",
    "groupeevoludev.com": "Décision Yves — Groupe Evoludev — interdiction permanente 2026-05-12",
    "groupeevex.com": "Décision Yves — Groupe EVEX — interdiction permanente 2026-05-12",
    "groupemainland.ca": "Décision Yves — Groupe Mainland — interdiction permanente 2026-05-12",
    "claude.tessier@couche-tard.com": "RETRAITE depuis 2023 — boîte désactivée (confirmé Yves 2026-05-12). Successor à enrichir : nouveau CFO Couche-Tard.",
    "hwu@pmml.ca": "Boîte fermée PMML (Hao Wu) — mx_connect_refused. Bounces quotidiens à Yves Outlook 2026-05-21 → 2026-05-26. NE JAMAIS retenter.",
}


def is_blacklisted(email: str | None) -> bool:
    """Retourne True si l'email est sur la black-list permanente.

    Comparaison case-insensitive. None / vide → False (pas de blocage,
    laisser le caller décider).
    """
    if not email:
        return False
    e = email.strip().lower()
    if e in BANNED_EMAILS:
        return True
    domain = e.rsplit("@", 1)[-1] if "@" in e else ""
    return domain in BANNED_DOMAINS


def reason_for(email: str | None) -> str:
    """Retourne la raison textuelle du blocage (pour logs)."""
    if not email:
        return ""
    e = email.strip().lower()
    if e in BANNED_EMAILS:
        return f"email_banned_explicit:{e}"
    domain = e.rsplit("@", 1)[-1] if "@" in e else ""
    if domain in BANNED_DOMAINS:
        return BLACKLIST_REASONS.get(domain, f"domain_banned:{domain}")
    return ""


def filter_safe(emails: Iterable[str]) -> list[str]:
    """Filtre une liste d'emails — retourne uniquement ceux NON blacklistés."""
    return [e for e in emails if not is_blacklisted(e)]


def assert_not_blacklisted(email: str) -> None:
    """Lève BlacklistedRecipientError si l'email est banni.

    À appeler en début de toute fonction d'envoi outbound — c'est la
    dernière barrière avant SendGrid.
    """
    if is_blacklisted(email):
        raise BlacklistedRecipientError(
            f"Refus d'envoi à {email} — {reason_for(email)}"
        )


class BlacklistedRecipientError(RuntimeError):
    """Levée quand un envoi outbound est tenté vers un email blacklisté."""
    pass
