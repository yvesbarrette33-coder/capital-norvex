"""Génération de tokens HMAC signés pour la page RDV Partenaire.

Extrait du défunt letter_generator.py (lettre papier abandonnée 2026-05-04).
Utilisé par capital/email_template.py pour générer des URLs Teams par cible.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

RDV_TOKEN_TTL_DAYS = 30


def sign_rdv_token(target_id: str, lang: str) -> str:
    """Génère un token HMAC signé pour la page RDV Partenaire.

    Le token contient target_id, lang, expiration (30 jours) et kind=partner.
    Validé côté Netlify (rdv-partenaire-availability + rdv-partenaire-book)
    contre le même secret INTERNAL_SECRET.
    """
    secret = os.environ.get("INTERNAL_SECRET") or os.environ.get(
        "CAPITAL_NORVEX_TOKEN_SECRET",
        "fallback-secret-change-me",
    )
    payload = {
        "t": target_id,
        "l": lang,
        "x": int(time.time()) + RDV_TOKEN_TTL_DAYS * 86400,
        "k": "partner",
    }
    data_b64 = (
        base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )
    sig = hmac.new(
        secret.encode("utf-8"),
        data_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")
    return f"{data_b64}.{sig_b64}"
