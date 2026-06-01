"""Agent COURTIERS — génération de Deal Cards mensuelles.

Lit les dossiers fermés du mois précédent, anonymise (pas de noms
d'emprunteurs), et compose une Deal Card HTML en style Variation A.

Critères Norvex actuels mis en avant. Témoignages courtiers si dispo.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ..shared import firestore_client as fs
from ..shared.email_template import (
    COLOR_GOLD,
    COLOR_INK,
    render_variation_a,
)

AGENT_NAME = "courtiers"


def fetch_recent_deals(months: int = 1) -> List[Dict[str, Any]]:
    """Récupère les dossiers fermés des N derniers mois."""
    since = datetime.now(timezone.utc) - timedelta(days=30 * months)
    deals = fs.query(
        "dossiers",
        filters=[("status", "==", "closed"), ("closedAt", ">=", since)],
        limit=20,
    )
    return deals


def _anonymize(deal: Dict[str, Any]) -> Dict[str, Any]:
    """Retire toute info nominative emprunteur."""
    return {
        "amount": deal.get("amount") or deal.get("loanAmount"),
        "type": deal.get("projectType") or deal.get("type"),
        "region": deal.get("region") or deal.get("city"),
        "term": deal.get("termMonths") or deal.get("term"),
        "ltv": deal.get("ltv"),
        "highlights": deal.get("highlights") or [],
    }


def generate_monthly_deal_card(deals: Optional[List[Dict[str, Any]]] = None) -> str:
    """Compose le HTML d'une Deal Card mensuelle. Retourne le HTML complet."""
    if deals is None:
        deals = fetch_recent_deals(months=1)

    deals_html_parts: List[str] = []
    for d in deals[:6]:
        a = _anonymize(d)
        amount = a.get("amount")
        amount_str = f"{int(amount):,} $".replace(",", " ") if amount else "—"
        deals_html_parts.append(
            f'<tr>'
            f'<td style="padding:10px 6px;border-bottom:1px solid #ddd;'
            f'font-family:Georgia,serif;font-size:13px;">{a.get("type") or "Multilogement"}</td>'
            f'<td style="padding:10px 6px;border-bottom:1px solid #ddd;'
            f'font-family:Georgia,serif;font-size:13px;">{a.get("region") or "QC"}</td>'
            f'<td style="padding:10px 6px;border-bottom:1px solid #ddd;'
            f'font-family:Georgia,serif;font-size:13px;text-align:right;">'
            f'<strong>{amount_str}</strong></td>'
            f'</tr>'
        )

    deals_table = (
        f'<table role="presentation" width="100%" cellpadding="0" '
        f'cellspacing="0" style="margin:18px 0;border-collapse:collapse;">'
        f'<thead><tr>'
        f'<th align="left" style="padding:8px 6px;border-bottom:2px solid '
        f'{COLOR_INK};font-family:Georgia,serif;font-size:12px;'
        f'color:{COLOR_GOLD};letter-spacing:1px;">TYPE</th>'
        f'<th align="left" style="padding:8px 6px;border-bottom:2px solid '
        f'{COLOR_INK};font-family:Georgia,serif;font-size:12px;'
        f'color:{COLOR_GOLD};letter-spacing:1px;">RÉGION</th>'
        f'<th align="right" style="padding:8px 6px;border-bottom:2px solid '
        f'{COLOR_INK};font-family:Georgia,serif;font-size:12px;'
        f'color:{COLOR_GOLD};letter-spacing:1px;">MONTANT</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(deals_html_parts) or "<tr><td colspan=3 style=\\"padding:12px;color:#888;\\">Aucune transaction fermée ce mois-ci.</td></tr>"}</tbody>'
        f'</table>'
    )

    body = (
        '<p style="margin:0 0 12px 0;">Bonjour,</p>'
        '<p style="margin:0 0 12px 0;">Voici un aperçu anonymisé des '
        'dossiers récemment financés par Capital Norvex. Ces transactions '
        'reflètent nos critères actuels — n\'hésitez pas à nous soumettre '
        'tout dossier qui s\'en approche.</p>'
        f"{deals_table}"
        '<p style="margin:12px 0 0 0;font-style:italic;color:#444;">'
        "Critères Norvex actuels — multilogement et commercial, "
        "ticket 2,5–25 M$ CAD, garanties immobilières de 1<sup>er</sup> rang, "
        "structure mensualité fixe.</p>"
    )

    title = f"Deal Card — {datetime.now().strftime('%B %Y').capitalize()}"
    return render_variation_a(
        body_html=body,
        recipient_name=None,
        title_line=title,
        show_signature=True,
    )


def queue_monthly_deal_cards_for_active_brokers() -> List[str]:
    """Crée des entrées brokerCommunications status=draft pour chaque
    broker actif/champion. Yves approuve dans le pipeline.
    """
    brokers = fs.query(
        "brokers",
        filters=[("relationshipStatus", "in", ["active", "champion"])],
        limit=200,
    )
    deals = fetch_recent_deals(months=1)
    html = generate_monthly_deal_card(deals)

    created_ids = []
    for b in brokers:
        cid = fs.create(
            "brokerCommunications",
            {
                "brokerId": b["id"],
                "type": "deal_card",
                "sentDate": None,
                "content": html,
                "status": "pending_yves_approval",
                "_agent": AGENT_NAME,
            },
        )
        created_ids.append(cid)

    fs.audit_log(
        agent=AGENT_NAME,
        action="queue_monthly_deal_cards",
        details={"count": len(created_ids), "deals_in_card": len(deals)},
    )
    return created_ids
