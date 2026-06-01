"""Searcher AMF — Autorité des marchés financiers (courtiers hypothécaires)."""
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
from ..system_prompts import AMF_PROMPT

AMF_SEARCH_URL = (
    "https://lautorite.qc.ca/grand-public/registres/"
    "registre-des-entreprises-et-des-individus-autorises-a-exercer"
)


def _http_get(url: str) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def search_amf(nom: str = "", numero_inscription: str = "") -> Dict[str, Any]:
    if not nom and not numero_inscription:
        return _error("Nom ou numéro d'inscription requis")
    params = {}
    if nom: params["q"] = nom.strip()
    if numero_inscription: params["no"] = numero_inscription.strip()
    qs = urllib.parse.urlencode(params)
    url = f"{AMF_SEARCH_URL}?{qs}"
    try:
        html = _http_get(url)
    except Exception as e:
        return _error(f"AMF HTTP error : {e}")
    return _analyze_html(html, search_query=nom or numero_inscription)


def _analyze_html(html: str, search_query: str) -> Dict[str, Any]:
    html_excerpt = html[:50000] if len(html) > 50000 else html
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    user_msg = f"""Recherche AMF : {search_query}

HTML brut :
{html_excerpt}

Analyse cette fiche AMF et retourne le JSON structuré demandé."""
    try:
        resp = client.messages.create(
            model=MODEL_SCRAPE,
            max_tokens=MAX_TOKENS_SCRAPE,
            system=AMF_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = resp.content[0].text.strip()
        start = raw.find("{"); end = raw.rfind("}")
        if start == -1 or end == -1:
            return _error("AMF analyse non parsable")
        data = json.loads(raw[start : end + 1])
        data["_source"] = "amf"
        data["_search_query"] = search_query
        return data
    except Exception as e:
        return _error(f"AMF analyse échec : {e}")


def _error(msg: str) -> Dict[str, Any]:
    return {
        "_source": "amf",
        "verdict": "yellow",
        "drapeaux_jaunes": [msg],
        "drapeaux_rouges": [],
        "verdict_explication": msg,
        "recommandation_yves": "Vérifier manuellement sur lautorite.qc.ca",
    }
