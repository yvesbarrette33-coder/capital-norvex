"""Agent CAPITAL — templates d'approche FR/EN pour family offices / wealth managers.

⚠️  Capital Norvex utilise EXCLUSIVEMENT le courriel pour ses outreach.
    Aucune lettre papier (cf. feedback_capital_email_only.md).

Audience cible :
- Family offices (multi-générationnels)
- Wealth managers / Private banking
- High Net Worth individuals
- Investisseurs accrédités

Ton :
- Très institutionnel (Stikeman / Brookfield / Apollo)
- Focus rendement structuré + sécurité hypothécaire + transparence (Norvex Track)
- Zéro hype, zéro emoji, langue soignée
- Court (≤ 250 mots) — ces gens lisent vite

v1 (2026-05-04) : version basique pour démarrer. Yves enrichira avec
créativité (vidéos, dossiers personnalisés, intros) au fil du temps.
"""
from __future__ import annotations

import os
import re
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


# ─── Bloc valeur partenaire (ce que Capital Norvex offre aux investisseurs) ──

def _value_block_fr() -> str:
    return info_box(
        title="OPPORTUNITÉ DE PARTENARIAT — PRÊT PRIVÉ IMMOBILIER STRUCTURÉ",
        content_html=feature_list([
            "<strong>Rendement cible 10 % à 12 %</strong> nets, "
            "garantis par hypothèque immobilière de premier rang",
            "<strong>Sécurité collatérale rigoureuse</strong> — ratio "
            "prêt-valeur calibré au type d'actif et renforcé par garanties "
            "complémentaires&nbsp;: nous ne finançons aucun dossier qui ne "
            "soit solidement protégé",
            "<strong>Norvex Track&trade;</strong> — accès en temps réel "
            "à votre dossier (déboursés, photos chantier, statut) — "
            "transparence totale, aucun prêteur privé canadien n'offre cela",
            "<strong>Norvex Intel&trade;</strong> — évaluation interne en "
            "3 approches (revenu, comparables, coût) intégrée à chaque "
            "dossier, réconciliée à l'interne par notre intelligence "
            "artificielle dédiée au prêt privé immobilier",
            "<strong>Décision de financement en 5 jours ouvrables</strong> — "
            "vélocité de capital, capital toujours en service",
            "<strong>Structure flexible</strong> : co-investissement par "
            "dossier OU pool de capital (selon votre préférence fiscale)",
        ]),
    )


def _ecosystem_block_fr() -> str:
    """V8 — Infrastructure technologique Norvex, 9 modules + portails PWA.

    Porté tel quel depuis letter_generator.py (V8 verrouillée).
    """
    return info_box(
        title="INFRASTRUCTURE TECHNOLOGIQUE INTERNE — UNIQUE AU CANADA",
        content_html=(
            "<p style=\"margin:0 0 12px 0;\">Notre plateforme est <strong>"
            "propulsée par une intelligence artificielle développée à "
            "l'interne</strong> et conçue spécifiquement pour le prêt "
            "privé immobilier institutionnel. Aucun autre prêteur — privé "
            "ou institutionnel — n'offre l'ensemble technologique que "
            "Capital Norvex met à votre disposition&nbsp;:</p>"
            + feature_list([
                "<strong>Score Norvex&trade;</strong> — moteur "
                "d'intelligence artificielle interne de cotation et de "
                "suivi de risque continu sur chaque dossier (analyse "
                "complète documentation, garants, structure, marché, "
                "risques, recommandation finale)",
                "<strong>Norvex Intel&trade;</strong> — analyse "
                "d'évaluation immobilière <strong>en 3 approches</strong> "
                "(revenu, comparables, coût) avec réconciliation, "
                "sensibilité, stress tests et valeur prêteur "
                "conservative. Sur chaque dossier, l'évaluation initiale "
                "fournie par l'emprunteur est validée et réconciliée à "
                "l'interne par notre intelligence artificielle — "
                "protection supplémentaire du capital du Partenaire",
                "<strong>Norvex Track&trade;</strong> — <strong>suivi de "
                "chantier en temps réel</strong> par dossier de "
                "construction&nbsp;: progression des travaux, photos de "
                "site, ventilation des déboursés, retenues, certificats "
                "d'avancement, le tout <strong>accessible 24/7 au "
                "Partenaire depuis son portail</strong>",
                "<strong>Norvex Cost Analyzer&trade;</strong> — "
                "<strong>analyse automatisée des coûts de construction</strong> "
                "(équité, honoraires, coût par porte, retenues, coûts "
                "indirects) avec validation des budgets et des écarts en "
                "temps réel",
                "<strong>Norvex Brain&trade;</strong> — système central de "
                "gestion et de comptabilité intégrée — traçabilité et "
                "auditabilité totales sur chaque transaction, chaque "
                "déboursé, chaque revenu",
                "<strong>Norvex Counsel&trade;</strong> — coordination "
                "juridique IA pour notaires, avocats et RDPRM&nbsp;; "
                "vélocité documentaire institutionnelle",
                "<strong>Norvex Relations&trade;</strong> — service à la "
                "clientèle IA de niveau premium pour toute coordination "
                "administrative et suivi général",
                "<strong>Norvex Talk&trade;</strong> — assistante "
                "téléphonique IA disponible 24/7 avec authentification à "
                "deux facteurs et alertes prioritaires Partenaires&nbsp;: "
                "vous appelez à toute heure, votre identité est validée, "
                "votre dossier est accessible immédiatement",
                "<strong>Portails Partenaire et Client (PWA "
                "installables)</strong> — vue 24/7 sur votre solde de "
                "Contribution, intérêts capitalisés, historique des "
                "déboursés, photos chantier, alertes automatiques en temps "
                "réel — accessible sur ordinateur, tablette ou téléphone, "
                "tant pour le Partenaire que pour l'emprunteur final&nbsp;: "
                "<strong>tout l'écosystème est digital de bout en bout</strong>",
            ])
            + "<p style=\"margin:12px 0 0 0;font-size:12.5px;color:#666;\">"
            "Vous recevez par ailleurs un rapport mensuel automatique "
            "complet, en plus d'une notification simultanée à chaque "
            "demande de déboursé sur vos dossiers — vous savez tout, "
            "en temps réel, sans avoir à demander.</p>"
        ),
    )


def _ecosystem_block_en() -> str:
    """V8 — Technology infrastructure (EN, condensed)."""
    return info_box(
        title="TECHNOLOGY INFRASTRUCTURE — UNIQUE IN CANADA",
        content_html=(
            "<p style=\"margin:0 0 12px 0;\">No lender — private or "
            "institutional — offers the technology platform Capital "
            "Norvex puts at your disposal:</p>"
            + feature_list([
                "<strong>Score Norvex&trade;</strong> — internal "
                "artificial intelligence for file scoring and continuous "
                "risk monitoring",
                "<strong>Norvex Intel&trade;</strong> — internal real "
                "estate appraisal in 3 approaches (income, comparables, "
                "cost) with conservative lender value",
                "<strong>Norvex Track&trade;</strong> — real-time "
                "construction monitoring <strong>accessible 24/7 to "
                "Partners</strong>",
                "<strong>Norvex Cost Analyzer&trade;</strong> — full "
                "and automated cost breakdown and analysis",
                "<strong>Norvex Brain&trade;</strong> — central "
                "management and integrated accounting system, total "
                "traceability and auditability",
                "<strong>Partner Portal (PWA)</strong> — Contribution "
                "balance, capitalized interest, disbursement history, "
                "automatic alerts, accessible 24/7",
            ])
            + "<p style=\"margin:12px 0 0 0;font-size:12.5px;color:#666;\">"
            "You also receive a complete monthly report simultaneously "
            "with every disbursement request.</p>"
        ),
    )


def _value_block_en() -> str:
    return info_box(
        title="PARTNERSHIP OPPORTUNITY — STRUCTURED PRIVATE REAL ESTATE LENDING",
        content_html=feature_list([
            "<strong>Target net returns of 10% to 12%</strong>, secured "
            "by first-rank mortgages on Canadian real estate",
            "<strong>Rigorous collateral coverage</strong> — "
            "loan-to-value calibrated by asset type and reinforced by "
            "complementary guarantees: we do not finance any file that "
            "is not solidly protected",
            "<strong>Norvex Track&trade;</strong> — real-time access to "
            "your file (disbursements, construction photos, status) — "
            "full transparency, no Canadian private lender offers this",
            "<strong>Norvex Intel&trade;</strong> — internal appraisal "
            "across 3 approaches (income, comparables, cost) embedded in "
            "every file, reconciled internally by our artificial "
            "intelligence dedicated to private real estate lending",
            "<strong>Funding decision in 5 business days</strong> — "
            "capital velocity, always-deployed capital",
            "<strong>Flexible structure</strong>: per-deal co-investment "
            "OR capital pool (your fiscal preference)",
        ]),
    )


# ─── CTA ────────────────────────────────────────────────────────────────────

def _rdv_url(target_id: str | None, lang: str) -> str:
    """Génère l'URL RDV — token HMAC signé si target_id fourni (page Teams),
    sinon fallback sur /rdv-public (formulaire générique)."""
    if target_id:
        token = sign_rdv_token(target_id, lang)
        return f"{SITE_URL}/rdv-partenaire?token={token}"
    lang_param = "&lang=en" if lang == "en" else ""
    return f"{SITE_URL}/rdv-public?utm=capital_outreach{lang_param}"


def _cta_fr(target_id: str | None = None) -> str:
    # Décision Yves 2026-05-08 : pour les capital partners institutionnels
    # (CFO, fondateurs, family offices), un bouton Teams 30 min seul est trop
    # engageant en cold outreach. On ajoute une option « soft » sous le bouton :
    # téléphone direct + reply email. Le secrétariat d'un fondateur transmet
    # plus facilement un numéro qu'un lien Teams. Promoteurs/Courtiers/Advisors
    # gardent leur CTA Teams seul (profil plus tech, déjà proven).
    return (
        '<p style="margin:0 0 14px 0;">Si Capital Norvex correspond à '
        'votre intérêt, je serais honoré de vous présenter notre '
        '<strong>livre de prêts en cours</strong> et nos '
        '<strong>structures partenariales</strong> lors d\'un échange '
        'Teams de 15 minutes.</p>'
        + cta_button(
            "RÉSERVER UN ÉCHANGE TEAMS — 15 MIN",
            _rdv_url(target_id, "fr"),
        )
        + '<p style="margin:18px 0 6px 0;font-size:.85em;color:#888;text-align:center;'
          'letter-spacing:.15em;text-transform:uppercase;">— ou plus simplement —</p>'
        '<p style="margin:0;font-size:.95em;color:#333;text-align:center;line-height:1.6;">'
        'Joignez-moi directement&nbsp;: '
        # Bug fix Yves 2026-05-08 : forcer Arial + tabular/lining nums sur le
        # numéro de téléphone — sinon Georgia (hérité du parent) rend les
        # chiffres en "old-style" (8 et PRÊT plus hauts que 4-3-3). Même fix
        # que la signature dark.
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


def _cta_en(target_id: str | None = None) -> str:
    # Yves decision 2026-05-08 — see _cta_fr() for rationale.
    return (
        '<p style="margin:0 0 14px 0;">If Norvex Capital aligns with '
        'your interests, I would be honoured to walk you through our '
        '<strong>active loan book</strong> and our '
        '<strong>partnership structures</strong> on a 15-minute Teams '
        'meeting.</p>'
        + cta_button(
            "BOOK A TEAMS MEETING — 15 MIN",
            _rdv_url(target_id, "en"),
        )
        + '<p style="margin:18px 0 6px 0;font-size:.85em;color:#888;text-align:center;'
          'letter-spacing:.15em;text-transform:uppercase;">— or more simply —</p>'
        '<p style="margin:0;font-size:.95em;color:#333;text-align:center;line-height:1.6;">'
        'Reach me directly: '
        # Bug fix Yves 2026-05-08 : forcer Arial + tabular/lining nums sur le
        # numéro de téléphone — sinon Georgia (hérité du parent) rend les
        # chiffres en "old-style" (8 et PRÊT plus hauts que 4-3-3). Même fix
        # que la signature dark.
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


# ─── Signature ──────────────────────────────────────────────────────────────

def _signature_fr() -> str:
    # Téléphone + email + adresse retirés (déjà dans la photo carte de
    # visite + bandeau noir bas). Yves 2026-05-07 — cohérence avec advisors.
    return (
        '<p style="margin:0 0 4px 0;font-size:.95em;color:#444;">'
        'Yves Barrette — Fondateur, Capital Norvex Inc.'
        '</p>'
    )


def _signature_en() -> str:
    # Phone + email + address removed (already in business card image
    # + black footer banner). Yves 2026-05-07 — consistency with advisors.
    return (
        '<p style="margin:0 0 4px 0;font-size:.95em;color:#444;">'
        'Yves Barrette — Founder, Capital Norvex Inc.'
        '</p>'
    )


# ─── Renderers ──────────────────────────────────────────────────────────────

# ─── Filtre défensif anti-contamination notes internes ──────────────────────
# Incident 2026-05-14 : certaines fiches Firestore/JSON contiennent des notes
# internes dans `investmentThesis` (« per insight Yves », « post-échec ... »,
# « rebuff ... », « TODO ... »). Ces marqueurs ne doivent JAMAIS apparaître
# dans le corps d'une lettre destinée au destinataire externe.
# Ce filtre est appliqué AVANT toute injection dans le template, peu importe
# la source (JSON seed, Firestore, agent LLM, etc.).
_INTERNAL_MARKER_PATTERNS = [
    r'\s*\(per insight[^)]*\)',          # (per insight Yves), (per insight ...)
    r'\s*\(insight[^)]*\)',              # (insight ...)
    r'\bTODO\b[^.]*\.?',                 # TODO ... .
    r'\bnote interne\b[^.;]*[.;]?',      # note interne ...
    r'\binternal note\b[^.;]*[.;]?',     # internal note ...
    r'\bpost-échec\s+[\w\-& ]+',         # post-échec 7-Eleven, post-échec ...
    r'\bpost-rebuff\s+[\w\-& ]+',        # post-rebuff Seven & i
    r'\brebuff\s+[\w\-& ]+',             # rebuff Seven & i Holdings
    r'\baprès le rebuff\b[^.;]*[.;]?',   # après le rebuff ...
    r'\bafter the rebuff\b[^.;]*[.;]?',  # after the rebuff ...
    r'\bechec[_ ]\w+_\d+\b',             # echec_7_eleven_2024 (signal tag)
]


def _strip_internal_markers(text: str) -> str:
    """Retire toute trace de note interne d'un texte avant injection lettre."""
    if not text:
        return ""
    cleaned = text
    for pat in _INTERNAL_MARKER_PATTERNS:
        cleaned = re.sub(pat, '', cleaned, flags=re.IGNORECASE)
    # Normalise espaces doublés et ponctuation flottante laissée par les retraits
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r'\s+([,.;:])', r'\1', cleaned)
    cleaned = re.sub(r'([,.;:]){2,}', r'\1', cleaned)
    return cleaned.strip(' ;,.')


def render_partnership_intro(
    target: Dict[str, Any],
    lang: str = "fr",
    target_id: str | None = None,
) -> str:
    """Approche initiale family office / wealth manager."""
    is_en = lang == "en"
    name = target.get("name", "")
    org = target.get("organization", "")
    title = target.get("title", "")
    # Bug fix Yves 2026-05-08 : 52 capitalTargets ont un title EN avec lang=fr.
    # On traduit à la volée pour éviter d'afficher « Vice President » ou
    # « Tax Partner » dans un courriel français destiné à un cadre québécois.
    from ..shared.title_translator import translate_title_for_lang
    title = translate_title_for_lang(title, lang)
    # Fix anti-contamination v2 (2026-05-14, après audit Henri Petit) :
    # UNIQUEMENT le champ `letterPersonalizedHook` (texte propre rédigé par Yves
    # ou par Camille en mode ghost-writer) déclenche un paragraphe personnalisé.
    # Les champs `investmentThesis` et `approachAngle` sont des notes INTERNES
    # de pilotage stratégique — jamais destinées au destinataire externe.
    # Aucun fallback automatique : si pas de hook propre, pas de paragraphe perso.
    raw_thesis = target.get("letterPersonalizedHook") or ""
    thesis = _strip_internal_markers(raw_thesis)
    if len(thesis) < 25:
        thesis = ""
    # Récupère target_id pour génération du token RDV (sinon fallback /rdv-public)
    tid = target_id or target.get("_doc_id") or target.get("id")

    # Override capsule vidéo perso (HeyGen Tier 1) — patch 2026-05-12
    # Si target a un customCapsuleId, on l'utilise au lieu de la générique « Mot du fondateur »/« Partner Letter »
    custom_capsule = target.get("customCapsuleId")
    if custom_capsule:
        if is_en:
            capsule_block = video_block(
                custom_capsule,
                "A personal video message from Yves Barrette",
                target.get("customCapsuleDuration", "35s"),
                lang="en",
            )
        else:
            capsule_block = video_block(
                custom_capsule,
                "Un mot vidéo personnel d'Yves Barrette",
                target.get("customCapsuleDuration", "35s"),
            )
    else:
        if lang == "en":
            capsule_block = video_block(
                "E1LMl-keATM", "Capital Norvex — 50 seconds, no pitch", "50s", lang="en"
            )
        else:
            capsule_block = video_block(
                "IBiCQCezivs", "Capital Norvex — 50 secondes, sans pitch", "50s"
            )

    if is_en:
        opener = (
            f'<p style="margin:0 0 18px 0;">I am writing because an '
            f'introduction between <strong>{org or name}</strong> and '
            f'<strong>Capital Norvex</strong> could, I believe, prove '
            f'mutually beneficial.</p>'
        )
        if thesis:
            personalized = (
                f'<p style="margin:0 0 18px 0;">{thesis}</p>'
            )
        else:
            personalized = ""
        positioning = (
            '<p style="margin:0 0 18px 0;"><strong>Capital Norvex</strong> '
            'is a Canadian private real estate lender built on a '
            'technology platform developed internally — not a traditional '
            'fund. We seek capital partners with a <strong>structured, '
            'conservative profile</strong>, for whom asset solidity and '
            'transparency take precedence over volume.</p>'
        )
        body = (
            opener
            + personalized
            + positioning
            + capsule_block
            + _value_block_en()
            + _ecosystem_block_en()
            + gold_rule()
            + _cta_en(tid)
            + _signature_en()
            + '<p style="margin:18px 0 0 0;">With consideration,</p>'
        )
    else:
        opener = (
            f'<p style="margin:0 0 18px 0;">Je vous écris parce qu\'une '
            f'mise en relation entre <strong>{org or name}</strong> et '
            f'<strong>Capital Norvex</strong> pourrait, je crois, être '
            f'bénéfique aux deux parties.</p>'
        )
        if thesis:
            personalized = (
                f'<p style="margin:0 0 18px 0;">{thesis}</p>'
            )
        else:
            personalized = ""
        positioning = (
            '<p style="margin:0 0 18px 0;"><strong>Capital Norvex</strong> '
            'est un prêteur immobilier privé canadien bâti sur une '
            'infrastructure technologique développée à l\'interne — pas '
            'un fonds traditionnel. Nous recherchons des partenaires de '
            'capital <strong>au profil structuré et conservateur</strong>, '
            'pour qui la solidité des actifs et la transparence priment '
            'sur le volume.</p>'
        )
        body = (
            opener
            + personalized
            + positioning
            + capsule_block
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
        recipient_name=name or None,
        title_line=title_line,
        lang=lang,
        show_signature=False,  # Yves 2026-05-12 matin : retirer la carte de visite image (numéro perso). _signature_fr/en() est déjà dans body (texte sobre). Footer noir entreprise (bandeau du bas) reste.
    )
