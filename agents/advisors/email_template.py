"""Agent ADVISORS — template email FR/EN pour avocats fiscaux/successoraux/M&A.

Audience : associés et seniors en cabinets d'avocats QC/ON.
Pratiques cibles : fiscalité, succession, trusts, family office, M&A privé,
patrimoine, real estate transactionnel.

Ton :
- Conseil-pair (avocat parle à avocat — Yves a Barreau? non, mais respecte protocole)
- Court (≤ 200 mots)
- Pas de pitch emprunteur — programme de RÉFÉRENCEMENT
- Mention 10-12% rendement = ce que TES clients obtiennent
- Modalités de partenariat « à discuter » (pas inventer commission)
- AMF safe : prêt commercial, pas valeur mobilière

v1 — 2026-05-07
"""
from __future__ import annotations

import os
from typing import Any, Dict

from ..shared.email_template import (
    cta_button,
    feature_list,
    gold_rule,
    info_box,
    render_variation_a,
    video_block,
)
from ..shared.rdv_token import sign_rdv_token

SITE_URL = os.environ.get("SITE_URL", "https://capitalnorvex.com")

# ─── Vidéos HeyGen Advisor — IDs YouTube à remplir après upload ──────────────
# Format : juste l'ID YouTube court (ex: "dQw4w9WgXcQ"), PAS l'URL complète.
# Si vide, aucune vidéo n'est intégrée dans la lettre (no-op safe).
ADVISOR_VIDEO_ID_FR = "4Tm1uEvLzPo"  # https://youtube.com/shorts/4Tm1uEvLzPo
ADVISOR_VIDEO_ID_EN = "9L6Pu0kxmlM"  # https://youtube.com/shorts/9L6Pu0kxmlM


# ─── Salutation protocole avocat ────────────────────────────────────────────

def _greet_fr(first: str, last: str, advisor_type: str = "") -> str:
    """Salutation FR selon profession :
    - Avocat → « Maître X » (protocole Barreau)
    - Notaire → « Maître X » (protocole Chambre des notaires)
    - Comptable / autre → « Monsieur X » / « Madame X »
    """
    last = (last or "").strip()
    t = (advisor_type or "").lower()
    if t in ("lawyer", "notary", "notaire", "avocat") and last:
        return f"Maître {last}"
    if last:
        return f"Monsieur {last}"
    return "Madame, Monsieur"


def _greet_en(first: str, last: str, advisor_type: str = "") -> str:
    """EN : « Mr./Ms. <Lastname> » — pas de « Maître »."""
    last = (last or "").strip()
    if last:
        return f"Dear Mr./Ms. {last}"
    first = (first or "").strip()
    if first:
        return f"Dear {first}"
    return "Dear Sir or Madam"


# ─── Bloc valeur — programme référencement ──────────────────────────────────

def _value_block_fr() -> str:
    return info_box(
        title="POUR VOS CLIENTS FORTUNÉS QUI CHERCHENT À DÉPLOYER DU CAPITAL",
        content_html=feature_list([
            "<strong>Rendement cible 10 % à 12 % net</strong>, garanti par "
            "<strong>hypothèque de premier rang</strong> sur immobilier "
            "canadien — protection institutionnelle du capital",
            "<strong>Loan-to-Value plafonné à 65 %</strong> — marge de "
            "sécurité jamais en deçà de 35 %, supérieure à la majorité "
            "des fonds privés canadiens",
            "<strong>Norvex Track&trade;</strong> — votre client (Partenaire) "
            "suit son investissement 24/7 (déboursés, photos chantier, "
            "soldes) depuis son portail PWA — transparence absolue, aucun "
            "autre prêteur privé canadien n'offre cela",
            "<strong>Structures flexibles</strong> — co-investissement par "
            "dossier OU pool de capital, selon la préférence fiscale et "
            "stratégique de votre client",
            "<strong>Prêt commercial</strong> (hors AMF) — structure "
            "hypothécaire, pas un placement de valeurs mobilières "
            "réglementé",
            "<strong>Prime de référencement</strong> — rémunération "
            "transparente, négociée selon le dossier mis en place suite à "
            "votre référence, payable à la signature de la lettre "
            "d'engagement, dans le respect de votre cadre déontologique",
        ]),
    )


def _value_block_en() -> str:
    return info_box(
        title="FOR YOUR HIGH NET WORTH CLIENTS LOOKING TO DEPLOY CAPITAL",
        content_html=feature_list([
            "<strong>Target net returns of 10% to 12%</strong>, secured by "
            "<strong>first-rank mortgages</strong> on Canadian real estate "
            "— institutional capital protection",
            "<strong>Loan-to-Value capped at 65%</strong> — safety margin "
            "never below 35%, ahead of most Canadian private funds",
            "<strong>Norvex Track&trade;</strong> — your client (Partner) "
            "follows their investment 24/7 (disbursements, site photos, "
            "balances) from their PWA portal — full transparency, no other "
            "Canadian private lender offers this",
            "<strong>Flexible structures</strong> — per-deal co-investment "
            "OR capital pool, depending on your client's tax and strategic "
            "preference",
            "<strong>Commercial loan</strong> (outside AMF/OSC scope) — "
            "mortgage structure, not a regulated securities offering",
            "<strong>Referral premium</strong> — transparent compensation, "
            "negotiated per file funded following your introduction, "
            "payable upon execution of the Commitment Letter, within your "
            "professional "
            "framework",
        ]),
    )


# ─── Bloc écosystème — INFRASTRUCTURE TECHNOLOGIQUE (aligné Capital/Promoteurs/Courtiers) ──

def _ecosystem_block_fr() -> str:
    """Liste complète 8 modules + 2 portails — alignée avec les autres templates."""
    return info_box(
        title="INFRASTRUCTURE TECHNOLOGIQUE PROPRIÉTAIRE — UNIQUE AU CANADA",
        content_html=(
            "<p style=\"margin:0 0 12px 0;\">Notre plateforme est <strong>"
            "propulsée par intelligence artificielle</strong> et conçue "
            "spécifiquement pour le prêt privé immobilier institutionnel. "
            "Aucun autre prêteur — privé ou institutionnel — n'offre la "
            "stack technologique que Capital Norvex met à la disposition "
            "de vos clients&nbsp;:</p>"
            + feature_list([
                "<strong>Score Norvex&trade;</strong> — moteur d'IA "
                "propriétaire de cotation et de suivi de risque continu sur "
                "chaque dossier (analyse complète documentation, garants, "
                "structure, marché, risques, recommandation finale)",
                "<strong>Norvex Intel&trade;</strong> — analyse IA "
                "propriétaire d'évaluation immobilière <strong>en 3 "
                "approches</strong> (revenu, comparables, coût) avec "
                "réconciliation, sensibilité, stress tests et valeur "
                "prêteur conservative",
                "<strong>Norvex Track&trade;</strong> — <strong>suivi de "
                "chantier en temps réel</strong>&nbsp;: progression, "
                "photos de site, ventilation des déboursés, retenues, "
                "certificats d'avancement, accessible 24/7 par votre "
                "client depuis son portail",
                "<strong>Norvex Cost Analyzer&trade;</strong> — "
                "analyse automatisée des coûts de construction (équité, "
                "honoraires, coût/porte, holdback, soft costs) avec "
                "validation des budgets et écarts en temps réel",
                "<strong>Norvex Brain&trade;</strong> — système central "
                "de gestion et de comptabilité intégrée — traçabilité et "
                "auditabilité totales sur chaque transaction",
                "<strong>Norvex Counsel&trade;</strong> — coordination "
                "juridique IA pour notaires, avocats et RDPRM&nbsp;; "
                "vélocité documentaire institutionnelle",
                "<strong>Norvex Relations&trade;</strong> — service à la "
                "clientèle IA de niveau premium pour toute coordination",
                "<strong>Norvex Talk&trade;</strong> — assistante "
                "téléphonique IA disponible 24/7 avec authentification "
                "2FA",
                "<strong>Portails Client et Partenaire (PWA "
                "installables)</strong> — vue 24/7 sur le solde, intérêts "
                "capitalisés, historique des déboursés, photos chantier, "
                "alertes automatiques&nbsp;: <strong>tout l'écosystème "
                "est digital de bout en bout</strong>",
            ])
            + "<p style=\"margin:12px 0 0 0;font-size:12.5px;color:#666;\">"
            "Vous gardez votre rôle de conseiller sans avoir à courir "
            "après l'information&nbsp;: votre client a tout en main, "
            "vous pouvez être informé en parallèle si vous le souhaitez.</p>"
        ),
    )


def _ecosystem_block_en() -> str:
    """Full 8-modules ecosystem block (EN) — aligned with other templates."""
    return info_box(
        title="PROPRIETARY TECHNOLOGY INFRASTRUCTURE — UNIQUE IN CANADA",
        content_html=(
            "<p style=\"margin:0 0 12px 0;\">Our platform is <strong>"
            "AI-powered</strong> and built specifically for institutional "
            "private real estate lending. No other lender — private or "
            "institutional — offers the technology stack that Capital "
            "Norvex puts at your clients' disposal:</p>"
            + feature_list([
                "<strong>Score Norvex&trade;</strong> — proprietary AI "
                "scoring and continuous risk monitoring engine",
                "<strong>Norvex Intel&trade;</strong> — proprietary AI "
                "real estate appraisal <strong>across 3 approaches</strong> "
                "(income, comparables, cost) with reconciliation, "
                "sensitivity, stress tests and conservative lender value",
                "<strong>Norvex Track&trade;</strong> — <strong>real-time "
                "construction monitoring</strong>: progress, site photos, "
                "disbursement breakdowns, holdbacks, completion "
                "certificates, accessible 24/7 by your client from their "
                "portal",
                "<strong>Norvex Cost Analyzer&trade;</strong> — automated "
                "construction cost analysis with real-time budget "
                "validation and variance tracking",
                "<strong>Norvex Brain&trade;</strong> — central management "
                "and integrated accounting system — total traceability and "
                "auditability on every transaction",
                "<strong>Norvex Counsel&trade;</strong> — AI legal "
                "coordination for notaries, lawyers and registrations; "
                "institutional documentation velocity",
                "<strong>Norvex Relations&trade;</strong> — premium AI "
                "client service for all administrative coordination",
                "<strong>Norvex Talk&trade;</strong> — AI phone assistant "
                "available 24/7 with 2FA authentication",
                "<strong>Client and Partner Portals (installable "
                "PWA)</strong> — 24/7 view on balance, capitalized "
                "interest, disbursement history, site photos, automatic "
                "alerts: <strong>the entire ecosystem is fully "
                "digital</strong>",
            ])
            + "<p style=\"margin:12px 0 0 0;font-size:12.5px;color:#666;\">"
            "You preserve your advisory role without chasing information: "
            "your client has everything in hand, and you can be kept in "
            "the loop in parallel as you wish.</p>"
        ),
    )


# ─── CTA ────────────────────────────────────────────────────────────────────

def _rdv_url(target_id: str | None, lang: str) -> str:
    if target_id:
        token = sign_rdv_token(target_id, lang)
        return f"{SITE_URL}/rdv-partenaire?token={token}"
    lang_param = "&lang=en" if lang == "en" else ""
    return f"{SITE_URL}/rdv-public?utm=advisor_outreach{lang_param}"


def _cta_fr(target_id: str | None) -> str:
    # Décision Yves 2026-05-08 : même fix que Capital partner — option soft
    # téléphone direct + reply email sous le bouton Teams. Profil advisor =
    # institutionnel, peut intimider sur cold outreach.
    return (
        '<p style="margin:0 0 14px 0;">Si le programme s\'inscrit dans '
        'votre pratique, je vous propose un <strong>échange Teams de '
        '20 minutes</strong> pour explorer si une mise en relation '
        'mutuelle aurait du sens — sans engagement.</p>'
        + cta_button("RÉSERVER UN ÉCHANGE TEAMS — 20 MIN", _rdv_url(target_id, "fr"))
        + '<p style="margin:18px 0 6px 0;font-size:.85em;color:#888;text-align:center;'
          'letter-spacing:.15em;text-transform:uppercase;">— ou plus simplement —</p>'
        '<p style="margin:0;font-size:.95em;color:#333;text-align:center;line-height:1.6;">'
        'Joignez-moi directement&nbsp;: '
        # Bug fix Yves 2026-05-08 : forcer Arial + tabular/lining nums sur le
        # numéro de téléphone — sinon Georgia rend les chiffres "old-style"
        # (8 et PRÊT plus hauts que 4-3-3). Même fix que la signature dark.
        '<a href="tel:+14385337738" style="color:#0a0d13;font-weight:500;'
        'text-decoration:none;border-bottom:1px solid #b8975a;'
        'font-family:Arial,Helvetica,sans-serif;'
        'font-variant-numeric:tabular-nums lining-nums;'
        'font-feature-settings:\'lnum\' 1, \'tnum\' 1;">'
        '438-533-PRÊT (7738)</a><br>'
        '<span style="color:#666;font-size:.92em;">ou répondez simplement à ce '
        'courriel — une phrase suffit.</span>'
        '</p>'
    )


def _cta_en(target_id: str | None) -> str:
    # Yves decision 2026-05-08 — see _cta_fr() rationale.
    return (
        '<p style="margin:0 0 14px 0;">If the program fits your '
        'practice, I would welcome a <strong>20-minute Teams meeting</strong> '
        'to explore whether a mutual introduction would make sense — '
        'no commitment.</p>'
        + cta_button("BOOK A TEAMS MEETING — 20 MIN", _rdv_url(target_id, "en"))
        + '<p style="margin:18px 0 6px 0;font-size:.85em;color:#888;text-align:center;'
          'letter-spacing:.15em;text-transform:uppercase;">— or more simply —</p>'
        '<p style="margin:0;font-size:.95em;color:#333;text-align:center;line-height:1.6;">'
        'Reach me directly: '
        # Bug fix Yves 2026-05-08 : forcer Arial + tabular/lining nums sur le
        # numéro de téléphone — sinon Georgia rend les chiffres "old-style"
        # (8 et PRÊT plus hauts que 4-3-3). Même fix que la signature dark.
        '<a href="tel:+14385337738" style="color:#0a0d13;font-weight:500;'
        'text-decoration:none;border-bottom:1px solid #b8975a;'
        'font-family:Arial,Helvetica,sans-serif;'
        'font-variant-numeric:tabular-nums lining-nums;'
        'font-feature-settings:\'lnum\' 1, \'tnum\' 1;">'
        '+1 (438) 533-PRÊT (7738)</a><br>'
        '<span style="color:#666;font-size:.92em;">or simply reply to this email '
        '— one sentence is enough.</span>'
        '</p>'
    )


# ─── Signature (alignée capital/email_template) ─────────────────────────────

def _signature_fr() -> str:
    # Téléphone + email + adresse retirés (déjà présents dans la photo
    # carte de visite + bandeau noir bas). Yves 2026-05-07.
    return (
        '<p style="margin:0 0 4px 0;font-size:.95em;color:#444;">'
        'Yves Barrette — Fondateur, Capital Norvex Inc.'
        '</p>'
    )


def _signature_en() -> str:
    # Phone + email + address removed (already shown in the business
    # card image + black footer banner). Yves 2026-05-07.
    return (
        '<p style="margin:0 0 4px 0;font-size:.95em;color:#444;">'
        'Yves Barrette — Founder, Capital Norvex Inc.'
        '</p>'
    )


# ─── Renderer principal ─────────────────────────────────────────────────────

def render_advisor_intro(
    target: Dict[str, Any],
    lang: str = "fr",
    target_id: str | None = None,
) -> str:
    """Approche initiale avocat fiscal/successoral/M&A — ton conseil-pair."""
    is_en = lang == "en"
    full_name = (target.get("name") or "").strip()
    parts = full_name.split()
    first = parts[0] if parts else ""
    last = parts[-1] if len(parts) > 1 else ""
    org = target.get("organization") or ""
    title = target.get("title") or ""
    # Bug fix Yves 2026-05-08 : 38 advisors ont un title EN avec lang=fr.
    # On traduit à la volée pour éviter d'afficher « Tax Partner » dans un
    # courriel français destiné à un avocat québécois.
    from ..shared.title_translator import translate_title_for_lang
    title = translate_title_for_lang(title, lang)
    tid = target_id or target.get("_doc_id") or target.get("id")

    advisor_type = target.get("advisorType", "")
    if is_en:
        greeting = _greet_en(first, last, advisor_type)
        opener = (
            f'<p style="margin:0 0 18px 0;">{greeting},</p>'
            f'<p style="margin:0 0 18px 0;">I am reaching out because '
            f'<strong>{org}</strong> serves a clientele where capital '
            f'allocation is a recurring topic — and we believe several '
            f'of your clients would benefit from a private real estate '
            f'opportunity that is rare in Canada.</p>'
        )
        positioning = (
            '<p style="margin:0 0 18px 0;"><strong>Capital Norvex</strong> '
            'is a Canadian private commercial real estate lender, fully '
            'collateralized by first-rank mortgages. We are <strong>actively '
            'seeking Capital Partners</strong> — high-net-worth individuals '
            'and family offices — wishing to deploy capital at <strong>10% '
            'to 12% net annual returns</strong>, with full transparency '
            'and institutional discipline.</p>'
            '<p style="margin:0 0 18px 0;">If your practice serves clients '
            'who hold liquidity and seek a yield-driven, asset-backed '
            'allocation, your introduction would be of mutual interest. '
            'A <strong>referral premium — transparent and negotiated '
            'per file</strong> is recognized at the execution of the '
            'Commitment Letter.</p>'
        )
        video_html = (
            video_block(ADVISOR_VIDEO_ID_EN, label="Watch a short introduction", duration="35 s", lang="en")
            if ADVISOR_VIDEO_ID_EN else ""
        )
        body = (
            opener
            + video_html
            + positioning
            + _value_block_en()
            + _ecosystem_block_en()
            + gold_rule()
            + _cta_en(tid)
            + _signature_en()
            + '<p style="margin:18px 0 0 0;">With consideration,</p>'
        )
    else:
        greeting = _greet_fr(first, last, advisor_type)
        opener = (
            f'<p style="margin:0 0 18px 0;">{greeting},</p>'
            f'<p style="margin:0 0 18px 0;">Je vous écris parce que '
            f'<strong>{org}</strong> dessert une clientèle où l\'allocation '
            f'de capital est un sujet récurrent — et nous croyons que '
            f'plusieurs de vos clients bénéficieraient d\'une opportunité '
            f'de prêt privé immobilier qui demeure rare au Canada.</p>'
        )
        positioning = (
            '<p style="margin:0 0 18px 0;"><strong>Capital Norvex</strong> '
            'est un prêteur immobilier commercial privé canadien, '
            'entièrement garanti par hypothèques de premier rang. Nous '
            'recherchons <strong>activement des Partenaires de capital</strong> '
            '— personnes fortunées et family offices — qui souhaitent '
            'déployer du capital à <strong>10 % à 12 % de rendement net '
            'annuel</strong>, avec une transparence totale et une discipline '
            'institutionnelle.</p>'
            '<p style="margin:0 0 18px 0;">Si votre pratique compte des '
            'clients disposant de liquidités à allouer dans des produits '
            'générateurs de rendement adossés à des actifs réels, votre '
            'mise en relation serait d\'intérêt mutuel. Une <strong>prime '
            'de référencement — transparente et négociée selon le '
            'dossier mis en place</strong> est reconnue à la signature de '
            'la lettre d\'engagement.</p>'
        )
        video_html = (
            video_block(ADVISOR_VIDEO_ID_FR, label="Voir une présentation", duration="35 s")
            if ADVISOR_VIDEO_ID_FR else ""
        )
        body = (
            opener
            + video_html
            + positioning
            + _value_block_fr()
            + _ecosystem_block_fr()
            + gold_rule()
            + _cta_fr(tid)
            + _signature_fr()
            + '<p style="margin:18px 0 0 0;">Avec considération,</p>'
        )

    title_line = title if title else None
    return render_variation_a(
        body_html=body,
        recipient_name=full_name or None,
        title_line=title_line,
        lang=lang,
    )
