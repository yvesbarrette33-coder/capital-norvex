"""Searcher REQ — Registre des entreprises du Québec (V2 Playwright headless).

V2 : utilise une Netlify Function (`/api/diligence-req-scrape`) qui automatise
le formulaire ASP.NET MVC du REQ via Chromium headless (Sparticuz + puppeteer).
La function clique la case CGU, remplit le NEQ/nom, clique Rechercher, et
retourne le HTML rendu. Ce module l'envoie ensuite à Claude pour analyse.

Avantage : automatisation totale (Yves ne fait rien manuellement).
Risque : si le REQ migre encore son frontend, le scraper peut casser → fallback
verdict yellow avec recommandation manuelle.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

import anthropic

from ..config import (
    ANTHROPIC_API_KEY,
    HTTP_TIMEOUT,
    MAX_TOKENS_SCRAPE,
    MODEL_SCRAPE,
    USER_AGENT,
)
from ..system_prompts import REQ_PROMPT


# Endpoint Netlify Function qui automatise le REQ via Chromium headless
SCRAPE_ENDPOINT = os.environ.get(
    "DILIGENCE_REQ_SCRAPE_URL",
    "https://capitalnorvex.com/api/diligence-req-scrape",
)
INTERNAL_SECRET = os.environ.get("INTERNAL_SECRET", "")


def _call_scraper(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Appelle l'endpoint Playwright et retourne {ok, html, finalUrl, ...}."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        SCRAPE_ENDPOINT,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-internal-secret": INTERNAL_SECRET,
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    # Le scraping prend ~10-30 sec (Chromium + REQ render)
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search_by_neq(neq: str) -> Dict[str, Any]:
    """Cherche une entreprise par NEQ (10 chiffres) dans le REQ via Playwright."""
    if not neq or not neq.replace(" ", "").isdigit():
        return _error(f"NEQ invalide : {neq}")
    neq_clean = neq.replace(" ", "").strip()
    try:
        scrape = _call_scraper({"neq": neq_clean})
    except Exception as e:
        return _error(f"REQ scraper HTTP error : {e}")

    if not scrape.get("ok"):
        return _error(
            f"REQ scraper failed : {scrape.get('error', 'inconnu')}"
        )

    return _analyze_html(
        scrape.get("html", ""),
        search_query=f"NEQ {neq_clean}",
        source_url=scrape.get("finalUrl"),
    )


def search_by_name(name: str) -> Dict[str, Any]:
    """Cherche par nom d'entreprise dans le REQ via Playwright."""
    if not name or len(name.strip()) < 3:
        return _error("Nom trop court")
    try:
        scrape = _call_scraper({"name": name.strip()})
    except Exception as e:
        return _error(f"REQ scraper HTTP error : {e}")

    if not scrape.get("ok"):
        return _error(
            f"REQ scraper failed : {scrape.get('error', 'inconnu')}"
        )

    return _analyze_html(
        scrape.get("html", ""),
        search_query=f"Nom : {name}",
        source_url=scrape.get("finalUrl"),
    )


def _analyze_html(
    html: str, search_query: str, source_url: Optional[str] = None
) -> Dict[str, Any]:
    """Passe le HTML brut à Claude Sonnet pour interprétation."""
    if not html or len(html) < 200:
        return _error(f"HTML REQ vide ou trop court ({len(html)} bytes)")
    # Si le HTML est trop gros, on tronque (les fiches REQ font ~50-200 KB)
    html_excerpt = html[:60000] if len(html) > 60000 else html

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    user_msg = f"""Recherche effectuée : {search_query}
URL finale : {source_url or 'n/a'}

HTML brut de la page REQ :
{html_excerpt}

Analyse cette fiche d'entreprise et retourne le JSON structuré demandé. Si \
la page contient une liste de résultats au lieu d'une fiche unique, mets \
verdict='yellow' avec drapeau_jaune 'Plusieurs résultats — désambiguïsation \
requise' et liste les candidats dans un champ 'candidats'."""

    try:
        resp = client.messages.create(
            model=MODEL_SCRAPE,
            max_tokens=MAX_TOKENS_SCRAPE,
            system=REQ_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = resp.content[0].text.strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            return _error("REQ analyse non parsable")
        data = json.loads(raw[start : end + 1])
        data["_source"] = "req"
        data["_search_query"] = search_query
        if source_url:
            data["_source_url"] = source_url
        return data
    except Exception as e:
        return _error(f"REQ analyse échec : {e}")


def _error(msg: str) -> Dict[str, Any]:
    return {
        "_source": "req",
        "verdict": "yellow",
        "drapeaux_jaunes": [msg],
        "drapeaux_rouges": [],
        "verdict_explication": msg,
        "recommandation_yves": "Vérifier manuellement sur registreentreprises.gouv.qc.ca",
    }
