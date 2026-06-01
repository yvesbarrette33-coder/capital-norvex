"""Agent PROMOTEURS v2 — templates d'approche FR/EN.

3 angles d'approche selon le signal détecté:
- Projet annoncé (permis, communiqué, presse)
- Croissance (volume estimé en hausse)
- Permis récent (dépôt municipal)

v2 (2026-05-01) :
- Bilingue FR/EN
- Mise en valeur de l'écosystème Norvex (Score, Intel, Track, Cost Analyzer, Brain)
- LOI 30 minutes mise en avant
- Norvex Intel (économie d'éval externe) en argument principal
"""
from __future__ import annotations

import os
from typing import Any, Dict

from ..shared.email_template import (
    COLOR_GOLD_DARK,
    cta_button,
    feature_list,
    gold_rule,
    info_box,
    render_variation_a,
    video_block,
)

SITE_URL = os.environ.get("SITE_URL", "https://capitalnorvex.com")


# ─── Helpers communs ────────────────────────────────────────────────────────

def _ecosystem_block_fr() -> str:
    return info_box(
        title="CE QUI NOUS DISTINGUE — PLATEFORME PROPULSÉE PAR IA, UNIQUE AU CANADA",
        content_html=(
            "<p style=\"margin:0 0 12px 0;\">Capital Norvex n'est pas un "
            "prêteur traditionnel. Nous opérons une <strong>plateforme "
            "propriétaire propulsée par intelligence artificielle</strong> "
            "qui transforme la façon dont un promoteur obtient son "
            "financement&nbsp;:</p>"
            + feature_list([
                "<strong>Score Norvex&trade;</strong> — IA propriétaire qui "
                "analyse votre dossier et produit une <strong>LOI "
                "préliminaire en 30 minutes</strong> (pas un comité humain "
                "qui prend des semaines)",
                "<strong>Norvex Intel&trade;</strong> — analyse IA "
                "propriétaire qui valide, complète et réconcilie votre "
                "évaluation initiale en 3 approches (revenu, comparables, "
                "coût) et calcule la valeur prêteur conservative. Une "
                "évaluation immobilière de base reste requise (frais "
                "standard du marché à votre charge)&nbsp;; <strong>aucune "
                "deuxième évaluation, aucun délai supplémentaire de 3 à "
                "6 semaines de notre côté pour valider votre dossier</strong>",
                "<strong>Norvex Cost Analyzer&trade;</strong> — analyse "
                "automatisée et ventilation complète des coûts de "
                "construction (équité, honoraires, coût/porte, holdback, "
                "soft costs)",
                "<strong>Norvex Track&trade;</strong> — suivi de chantier "
                "en temps réel (photos de site, déboursés, retenues, "
                "certificats d'avancement) — <strong>aucun prêteur privé "
                "canadien n'offre cela</strong>",
                "<strong>Norvex Brain&trade;</strong> — système central de "
                "gestion intégrée&nbsp;: traçabilité, comptabilité et "
                "auditabilité totales de votre dossier",
                "<strong>Norvex Counsel&trade;</strong> — coordination "
                "juridique IA pour notaires, avocats, RDPRM&nbsp;: "
                "<strong>closing fluide et rapide</strong>, sans accrochage",
                "<strong>Norvex Relations&trade;</strong> et <strong>Norvex "
                "Talk&trade;</strong> — service à la clientèle IA (info@) "
                "et assistante téléphonique 24/7&nbsp;: vous joignez "
                "Capital Norvex à toute heure, votre dossier est accessible "
                "immédiatement",
                "<strong>Portails Client et Partenaire (PWA "
                "installables)</strong> — communication, documents, "
                "déboursés, états d'avancement, accessibles 24/7 sur "
                "ordinateur, tablette ou téléphone",
                "<strong>Décision finale en 5 jours ouvrables</strong> — "
                "standardisée, traçable, mesurable",
            ])
        ),
    )


def _ecosystem_block_en() -> str:
    return info_box(
        title="WHAT SETS US APART — TECHNOLOGY INFRASTRUCTURE",
        content_html=feature_list([
            "<strong>Score Norvex&trade;</strong> — proprietary AI that "
            "analyzes your file and produces an <strong>LOI in 30 "
            "minutes</strong> (not a human committee that takes weeks)",
            "<strong>Norvex Intel&trade;</strong> — proprietary AI "
            "analysis that validates, completes and reconciles your "
            "initial appraisal across 3 approaches (income, comparables, "
            "cost) and computes the conservative lender value. A baseline "
            "real estate appraisal is still required (standard market fee, "
            "borne by you); <strong>no second appraisal, no additional "
            "3-to-6 week delay on our side to validate your file</strong>",
            "<strong>Norvex Cost Analyzer&trade;</strong> — complete and "
            "automatic breakdown of all project costs",
            "<strong>Norvex Track&trade;</strong> — real-time construction "
            "monitoring (no Canadian private lender offers this)",
            "<strong>Norvex Brain&trade;</strong> — central integrated "
            "management system: full traceability, accounting and "
            "auditability of your file",
            "<strong>Final decision in 5 business days</strong> — fully "
            "standardized, fully traceable",
            "<strong>Developer Portal (PWA)</strong> — communication, "
            "documents, disbursements, progress status, accessible 24/7",
        ]),
    )


def _scope_fr() -> str:
    return (
        '<p style="margin:0 0 18px 0;">Capital Norvex finance par '
        'convention privée toute la gamme du marché immobilier : '
        '<strong>construction commerciale, multi-résidentielle, '
        'industrielle, projets de développement, acquisition d\'immeubles '
        'locatifs et financement de terrain</strong> — au Québec et en '
        'Ontario, sur des montants de <strong>2,5 M$ à 100 M$</strong>, '
        'taux 10-12 %, frais 3-3,5 %, garanties immobilières standard, '
        'sans dilution de contrôle.</p>'
    )


def _scope_en() -> str:
    return (
        '<p style="margin:0 0 18px 0;">Capital Norvex finances under '
        'private agreement the full range of the real estate market: '
        '<strong>commercial, multi-residential, industrial construction, '
        'development projects, acquisition of revenue properties and '
        'land financing</strong> — in Quebec and Ontario, on amounts '
        'from <strong>CA$2.5M to CA$100M</strong>, rates 10-12%, fees '
        '3-3.5%, standard real estate guarantees, no dilution of control.</p>'
    )


def _track_record_fr() -> str:
    # ⚠️ Cette section ne re-liste PAS les modules (déjà détaillés dans
    # _ecosystem_block_fr juste au-dessus). Elle ajoute UNIQUEMENT le crédit
    # track record + tagline résultat. Évite la redondance signalée par Yves
    # 2026-05-05.
    return (
        '<p style="margin:18px 0;">Notre direction cumule plus de '
        '<strong>200 M$ de financements immobiliers structurés '
        'annuellement</strong> dans le marché privé québécois. Cette '
        'discipline opérationnelle, doublée de l\'infrastructure '
        'technologique décrite ci-dessus, permet à Capital Norvex de faire '
        '<strong>en jours ce que les autres font en semaines</strong>.</p>'
    )


def _track_record_en() -> str:
    return (
        '<p style="margin:18px 0;">Our leadership has structured '
        '<strong>over CA$200M of real estate financing annually</strong> '
        'in the Quebec private market. This operational discipline, '
        'combined with a technology infrastructure unmatched in Canada, '
        'lets Capital Norvex do <strong>in days what others do in '
        'weeks</strong> — without imposing a second appraisal or the '
        'usual 3-to-6 week delay on our side.</p>'
    )


def _cta_fr() -> str:
    return (
        '<div style="margin:24px 0 8px 0;text-align:center;">'
        f'<div style="font-size:10px;letter-spacing:2.5px;'
        f'color:{COLOR_GOLD_DARK};margin-bottom:10px;">'
        'POUR DÉMARRER — LOI EN 30 MINUTES, SANS ENGAGEMENT</div>'
        '<p style="margin:0 0 6px 0;font-size:13px;color:#555;">'
        'Une LOI préliminaire incluant la valeur prêteur peut être '
        'produite <strong>aujourd\'hui même</strong>, sans impact sur '
        'votre cote de crédit.</p>'
        '</div>'
        + cta_button(
            label="Analyser mon dossier en 30 minutes",
            url=f"{SITE_URL}/capital-norvex-score.html",
            sublabel="Score Norvex — capitalnorvex.com",
        )
        + '<p style="margin:18px 0 0 0;text-align:center;font-size:12.5px;'
        'color:#666;">Toute l\'information sur '
        f'<a href="{SITE_URL}" style="color:#9A8554;text-decoration:none;">'
        '<strong>capitalnorvex.com</strong></a></p>'
    )


def _cta_en() -> str:
    return (
        '<div style="margin:24px 0 8px 0;text-align:center;">'
        f'<div style="font-size:10px;letter-spacing:2.5px;'
        f'color:{COLOR_GOLD_DARK};margin-bottom:10px;">'
        'GET STARTED — LOI IN 30 MINUTES, NO COMMITMENT</div>'
        '<p style="margin:0 0 6px 0;font-size:13px;color:#555;">'
        'A preliminary LOI including lender value can be produced '
        '<strong>today</strong>, with no impact on your credit score.</p>'
        '</div>'
        + cta_button(
            label="Analyze my file in 30 minutes",
            url=f"{SITE_URL}/capital-norvex-score.html?lang=en",
            sublabel="Score Norvex — capitalnorvex.com",
        )
        + '<p style="margin:18px 0 0 0;text-align:center;font-size:12.5px;'
        'color:#666;">Full details on '
        f'<a href="{SITE_URL}" style="color:#9A8554;text-decoration:none;">'
        '<strong>capitalnorvex.com</strong></a></p>'
    )


def _signature_phone_fr() -> str:
    # Police Arial + tabular-nums : alignement parfait des chiffres
    # (Georgia rend en old-style, le 8 dépasse — bug fixé 2026-05-05).
    return (
        '<p style="margin:18px 0;font-size:13px;color:#555;">'
        'Ou ligne directe : <strong style="font-family:Arial,Helvetica,sans-serif;'
        'font-variant-numeric:tabular-nums lining-nums;">438-533-PRÊT (7738)</strong></p>'
    )


def _signature_phone_en() -> str:
    return (
        '<p style="margin:18px 0;font-size:13px;color:#555;">'
        'Direct line: <strong style="font-family:Arial,Helvetica,sans-serif;'
        'font-variant-numeric:tabular-nums lining-nums;">+1 (438) 533-PRÊT (7738)</strong></p>'
    )


# ─── Render functions (FR + EN, 3 angles) ───────────────────────────────────

def render_project_announcement(
    promoter: Dict[str, Any],
    project: Dict[str, Any],
    lang: str = "fr",
) -> str:
    """Approche basée sur un projet annoncé publiquement."""
    is_en = lang == "en"
    name = promoter.get("name", "")
    company = promoter.get("companyName", "")
    project_name = project.get("name", "")

    if is_en:
        opener = (
            f'<p style="margin:0 0 18px 0;">I came across '
            f'<strong>{project_name or "your recent project"}</strong> '
            f'and wanted to commend the quality of the operation.</p>'
        )
        positioning = (
            '<p style="margin:0 0 18px 0;">I\'m writing because '
            '<strong>Capital Norvex is different from anything you\'ve '
            'seen</strong> in the private real estate lending market: we '
            'are not a traditional lender, <strong>we are a technology '
            'platform for structured financing</strong>.</p>'
        )
        body = (
            opener
            + positioning
            + video_block("KRmp0JA1JYU", "Letter of intent in 30 minutes", "55s", lang="en")
            + _scope_en()
            + _ecosystem_block_en()
            + _track_record_en()
            + gold_rule()
            + _cta_en()
            + _signature_phone_en()
            + '<p style="margin:18px 0 0 0;">Sincerely,</p>'
        )
    else:
        opener = (
            f'<p style="margin:0 0 18px 0;">J\'ai pris connaissance de '
            f'<strong>{project_name or "votre récent projet"}</strong> et '
            f'je voulais saluer la qualité de l\'opération.</p>'
        )
        positioning = (
            '<p style="margin:0 0 18px 0;">Je vous écris parce que '
            '<strong>Capital Norvex est différent de tout ce que vous '
            'avez vu</strong> sur le marché du prêt privé immobilier : '
            'nous ne sommes pas un prêteur traditionnel, <strong>nous '
            'sommes une plateforme technologique de financement '
            'structuré</strong>.</p>'
        )
        body = (
            opener
            + positioning
            + video_block("ydAnJRY_xa4", "Lettre d'intention en 30 minutes", "55s")
            + _scope_fr()
            + _ecosystem_block_fr()
            + _track_record_fr()
            + gold_rule()
            + _cta_fr()
            + _signature_phone_fr()
            + '<p style="margin:18px 0 0 0;">Avec considération,</p>'
        )

    # Décision Yves 2026-05-04 : outreach promoteurs signé « L'équipe Capital
    # Norvex » (PAS Yves perso). Mass outbound = pas honnête de signer perso.
    return render_variation_a(
        body_html=body,
        recipient_name=name or None,
        title_line=None,
        signature_name="L'équipe Capital Norvex" if lang == "fr" else "The Capital Norvex Team",
        signature_title="Programme financement promoteurs" if lang == "fr" else "Developer financing program",
        use_image_signature=False,
        lang=lang,
    )


def render_growth_signal(
    promoter: Dict[str, Any],
    lang: str = "fr",
) -> str:
    """Approche basée sur un signal de croissance."""
    is_en = lang == "en"
    company = promoter.get("companyName", "")
    name = promoter.get("name", "")

    if is_en:
        opener = (
            f'<p style="margin:0 0 18px 0;">The recent activity of '
            f'<strong>{company or "your firm"}</strong> caught my attention. '
            f'Capital Norvex discreetly supports developers whose growth '
            f'demands more flexible financing structures than traditional '
            f'banking.</p>'
        )
        positioning = (
            '<p style="margin:0 0 18px 0;">We are not a traditional '
            'lender — <strong>we are a technology platform for structured '
            'private real estate financing</strong>, with an infrastructure '
            'unmatched in Canada.</p>'
        )
        body = (
            opener
            + positioning
            + video_block("KRmp0JA1JYU", "Letter of intent in 30 minutes", "55s", lang="en")
            + _scope_en()
            + _ecosystem_block_en()
            + _track_record_en()
            + gold_rule()
            + _cta_en()
            + _signature_phone_en()
            + '<p style="margin:18px 0 0 0;">Sincerely,</p>'
        )
    else:
        opener = (
            f'<p style="margin:0 0 18px 0;">L\'activité récente de '
            f'<strong>{company or "votre firme"}</strong> retient l\'attention. '
            f'Capital Norvex accompagne discrètement des promoteurs dont la '
            f'croissance impose des structures de financement plus souples '
            f'que le bancaire traditionnel.</p>'
        )
        positioning = (
            '<p style="margin:0 0 18px 0;">Nous ne sommes pas un prêteur '
            'traditionnel — <strong>nous sommes une plateforme technologique '
            'de financement privé immobilier structuré</strong>, avec une '
            'infrastructure unique au Canada.</p>'
        )
        body = (
            opener
            + positioning
            + video_block("ydAnJRY_xa4", "Lettre d'intention en 30 minutes", "55s")
            + _scope_fr()
            + _ecosystem_block_fr()
            + _track_record_fr()
            + gold_rule()
            + _cta_fr()
            + _signature_phone_fr()
            + '<p style="margin:18px 0 0 0;">Avec considération,</p>'
        )

    # Décision Yves 2026-05-04 : signé équipe (pas Yves perso) pour mass outreach.
    return render_variation_a(
        body_html=body,
        recipient_name=name or None,
        signature_name="L'équipe Capital Norvex" if lang == "fr" else "The Capital Norvex Team",
        signature_title="Programme financement promoteurs" if lang == "fr" else "Developer financing program",
        use_image_signature=False,
        lang=lang,
    )


def render_permit_signal(
    promoter: Dict[str, Any],
    permit: Dict[str, Any],
    lang: str = "fr",
) -> str:
    """Approche basée sur un permis récemment déposé."""
    is_en = lang == "en"
    addr = permit.get("address", "")
    name = promoter.get("name", "")
    company = promoter.get("companyName", "")

    if is_en:
        opener = (
            f'<p style="margin:0 0 18px 0;">I noted your recent permit '
            f'filing at <strong>{addr or "this location"}</strong>. '
            f'Capital Norvex finances this type of project under private '
            f'agreement, without dilution of control, with fixed '
            f'monthly payments and standard guarantees.</p>'
        )
        positioning = (
            '<p style="margin:0 0 18px 0;">If the structure is helpful '
            'to your assembly, here is what makes us <strong>different '
            'from any private lender you\'ve worked with</strong>:</p>'
        )
        body = (
            opener
            + positioning
            + video_block("KRmp0JA1JYU", "Letter of intent in 30 minutes", "55s", lang="en")
            + _scope_en()
            + _ecosystem_block_en()
            + _track_record_en()
            + gold_rule()
            + _cta_en()
            + _signature_phone_en()
            + '<p style="margin:18px 0 0 0;">Sincerely,</p>'
        )
    else:
        opener = (
            f'<p style="margin:0 0 18px 0;">J\'ai noté votre récent dépôt '
            f'de permis à <strong>{addr or "cette adresse"}</strong>. '
            f'Capital Norvex finance ce type de projet par convention '
            f'privée, sans dilution de contrôle, avec mensualités fixes '
            f'et garanties standard.</p>'
        )
        positioning = (
            '<p style="margin:0 0 18px 0;">Si la structure peut être utile '
            'à votre montage, voici ce qui nous rend <strong>différents '
            'de tout prêteur privé avec lequel vous avez déjà travaillé'
            '</strong> :</p>'
        )
        body = (
            opener
            + positioning
            + video_block("ydAnJRY_xa4", "Lettre d'intention en 30 minutes", "55s")
            + _scope_fr()
            + _ecosystem_block_fr()
            + _track_record_fr()
            + gold_rule()
            + _cta_fr()
            + _signature_phone_fr()
            + '<p style="margin:18px 0 0 0;">Avec considération,</p>'
        )

    # Décision Yves 2026-05-04 : signé équipe (pas Yves perso) pour mass outreach.
    return render_variation_a(
        body_html=body,
        recipient_name=name or None,
        signature_name="L'équipe Capital Norvex" if lang == "fr" else "The Capital Norvex Team",
        signature_title="Programme financement promoteurs" if lang == "fr" else "Developer financing program",
        use_image_signature=False,
        lang=lang,
    )
