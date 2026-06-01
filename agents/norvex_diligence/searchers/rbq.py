"""Searcher RBQ — Régie du bâtiment du Québec.

Recherche par numéro de licence ou nom d'entreprise. La RBQ a un formulaire
public à `rbq.gouv.qc.ca/grand-public/services-en-ligne/recherche-detenteur-licence-rbq`.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Dict

import anthropic

from ..config import (
    ANTHROPIC_API_KEY,
    HTTP_TIMEOUT,
    MAX_TOKENS_SCRAPE,
    MODEL_SCRAPE,
    USER_AGENT,
)
from ..system_prompts import RBQ_PROMPT

# RBQ search backend (formulaire avec POST). Le service public utilise une
# query string simple sur la page de résultats.
RBQ_SEARCH_URL = (
    "https://www.rbq.gouv.qc.ca/grand-public/services-en-ligne/"
    "recherche-detenteur-licence-rbq.html"
)


def _http_get(url: str) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def search_licence(numero_licence: str = "", nom_entreprise: str = "",
                    type_projet: str = "") -> Dict[str, Any]:
    """Cherche une licence RBQ par numéro OU nom.

    type_projet : 'residentiel' | 'commercial' | 'industriel' (optionnel)
    """
    if not numero_licence and not nom_entreprise:
        return _error("Numéro de licence ou nom d'entreprise requis")

    params = {}
    if numero_licence:
        params["numero_licence"] = numero_licence.strip()
    if nom_entreprise:
        params["nom"] = nom_entreprise.strip()
    qs = urllib.parse.urlencode(params)
    url = f"{RBQ_SEARCH_URL}?{qs}"

    try:
        html = _http_get(url)
    except Exception as e:
        return _error(f"RBQ HTTP error : {e}")

    return _analyze_html(html, search_query=f"Licence {numero_licence or nom_entreprise}",
                          type_projet=type_projet)


def _analyze_html(html: str, search_query: str,
                   type_projet: str = "") -> Dict[str, Any]:
    html_excerpt = html[:50000] if len(html) > 50000 else html
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    type_hint = (
        f"\n\nLe projet Capital Norvex concerné est de type : {type_projet}. "
        f"Vérifie que les catégories couvrent ce type."
        if type_projet else ""
    )

    user_msg = f"""Recherche RBQ : {search_query}{type_hint}

HTML brut de la page RBQ :
{html_excerpt}

Analyse cette fiche RBQ et retourne le JSON structuré demandé."""

    try:
        resp = client.messages.create(
            model=MODEL_SCRAPE,
            max_tokens=MAX_TOKENS_SCRAPE,
            system=RBQ_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = resp.content[0].text.strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            return _error("RBQ analyse non parsable")
        data = json.loads(raw[start : end + 1])
        data["_source"] = "rbq"
        data["_search_query"] = search_query
        return data
    except Exception as e:
        return _error(f"RBQ analyse échec : {e}")


def _error(msg: str) -> Dict[str, Any]:
    return {
        "_source": "rbq",
        "verdict": "yellow",
        "drapeaux_jaunes": [msg],
        "drapeaux_rouges": [],
        "verdict_explication": msg,
        "recommandation_yves": "Vérifier manuellement sur rbq.gouv.qc.ca",
    }
