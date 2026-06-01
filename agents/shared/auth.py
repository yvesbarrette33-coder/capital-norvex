"""Authentification partagée pour les 3 agents Capital Norvex.

Fournit:
- get_graph_token()    : token Microsoft Graph (client_credentials)
- get_firebase_admin() : client Firebase Admin SDK (singleton)
- get_firestore()      : client Firestore (singleton)
- get_storage()        : client Firebase Storage (singleton)

Réutilise les mêmes variables d'environnement que agent_docs.py
(AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, MAIL_USER,
GOOGLE_APPLICATION_CREDENTIALS).
"""
from __future__ import annotations

import os
import time
from typing import Optional

import requests
from dotenv import load_dotenv

# Secrets stockés hors du repo (~/.capitalnorvex/.env, perms 600 — sécurité).
# Fallbacks pour rétrocompatibilité dev / migration progressive.
_ENV_PATHS = [
    os.path.join(os.path.expanduser("~"), ".capitalnorvex", ".env"),
    os.path.join(os.path.dirname(__file__), "..", "..", "Capital Norvex", "agent", ".env"),
    os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
]
for p in _ENV_PATHS:
    if os.path.exists(p):
        # override=True : si une variable existe en shell mais avec valeur vide
        # (cas Yves), on remplace par celle du .env (source de vérité).
        load_dotenv(p, override=True)
        break

# ── Microsoft Graph ──────────────────────────────────────────────
_GRAPH_TOKEN_CACHE = {"token": None, "expires_at": 0}


def get_graph_token() -> str:
    """Token Microsoft Graph via client_credentials. Cache ~50 min."""
    now = time.time()
    if _GRAPH_TOKEN_CACHE["token"] and now < _GRAPH_TOKEN_CACHE["expires_at"]:
        return _GRAPH_TOKEN_CACHE["token"]

    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    if not (tenant_id and client_id and client_secret):
        raise RuntimeError(
            "AZURE_TENANT_ID / AZURE_CLIENT_ID / AZURE_CLIENT_SECRET "
            "manquants dans .env"
        )

    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
    }
    r = requests.post(url, data=data, timeout=30)
    r.raise_for_status()
    payload = r.json()
    token = payload["access_token"]
    expires = int(payload.get("expires_in", 3600))
    _GRAPH_TOKEN_CACHE["token"] = token
    _GRAPH_TOKEN_CACHE["expires_at"] = now + max(60, expires - 120)
    return token


# ── Firebase Admin SDK ───────────────────────────────────────────
_FIREBASE_APP = None


def get_firebase_admin():
    """Initialise (une seule fois) et retourne l'app Firebase Admin."""
    global _FIREBASE_APP
    if _FIREBASE_APP is not None:
        return _FIREBASE_APP

    import firebase_admin
    from firebase_admin import credentials

    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv(
        "FIREBASE_SERVICE_ACCOUNT_KEY_PATH"
    )
    if not cred_path or not os.path.exists(cred_path):
        raise RuntimeError(
            "GOOGLE_APPLICATION_CREDENTIALS (chemin clé JSON service account) "
            "manquant ou introuvable"
        )

    cred = credentials.Certificate(cred_path)
    project_id = os.getenv("FIREBASE_PROJECT_ID", "capital-norvex")
    storage_bucket = os.getenv(
        "FIREBASE_STORAGE_BUCKET", f"{project_id}.appspot.com"
    )

    if firebase_admin._apps:
        _FIREBASE_APP = firebase_admin.get_app()
    else:
        _FIREBASE_APP = firebase_admin.initialize_app(
            cred,
            {"projectId": project_id, "storageBucket": storage_bucket},
        )
    return _FIREBASE_APP


def get_firestore():
    """Client Firestore (Admin SDK — bypass les règles)."""
    from firebase_admin import firestore

    get_firebase_admin()
    return firestore.client()


def get_storage():
    """Bucket Firebase Storage (Admin SDK)."""
    from firebase_admin import storage

    get_firebase_admin()
    return storage.bucket()
