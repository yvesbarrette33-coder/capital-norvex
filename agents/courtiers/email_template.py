"""Agent COURTIERS — templates d'approche FR/EN pour courtiers hypothécaires.

2 angles d'approche:
- Cold outreach : courtier identifié, jamais contacté
- Warm follow-up : courtier déjà en relation, relance avec deal cards

v1 (2026-05-01):
- Bilingue FR/EN selon broker.language
- Mise en valeur de l'écosystème Norvex (Score, Intel, Track, Cost Analyzer, Brain)
- LOI 30 minutes + commissions compétitives
- Lien direct vers section Courtiers du site (modal)
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

def _client_block_fr() -> str:
    # Aligné sur _ecosystem_block_fr Promoteurs (Yves 2026-05-05) — chaque
    # lettre doit présenter TOUS les modules de l'écosystème.
    return info_box(
        title="CE QUE VOS CLIENTS REÇOIVENT — PLATEFORME PROPULSÉE PAR IA, UNIQUE AU CANADA",
        content_html=(
            "<p style=\"margin:0 0 12px 0;\">Capital Norvex n'est pas un "
            "prêteur traditionnel. Vos clients accèdent à une "
            "<strong>plateforme propriétaire propulsée par intelligence "
            "artificielle</strong> qui transforme l'expérience de "
            "financement&nbsp;:</p>"
            + feature_list([
                "<strong>Score Norvex&trade;</strong> — IA propriétaire, "
                "<strong>LOI en 30 minutes</strong> prête à présenter",
                "<strong>Norvex Intel&trade;</strong> — analyse IA "
                "propriétaire en 3 approches (revenu, comparables, coût) "
                "qui valide et complète l'évaluation initiale à l'interne. "
                "Votre client fournit une évaluation de base au tarif "
                "standard du marché&nbsp;; <strong>aucune deuxième "
                "évaluation à payer chez nous, aucun délai supplémentaire "
                "de 3 à 6 semaines pour notre validation</strong>",
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
                "auditabilité totales du dossier",
                "<strong>Norvex Counsel&trade;</strong> — coordination "
                "juridique IA pour notaires, avocats, RDPRM&nbsp;: "
                "<strong>closing fluide et rapide</strong>, sans accrochage",
                "<strong>Norvex Relations&trade;</strong> et <strong>Norvex "
                "Talk&trade;</strong> — service à la clientèle IA (info@) "
                "et assistante téléphonique 24/7&nbsp;: votre client "
                "joint Capital Norvex à toute heure, dossier accessible "
                "immédiatement",
                "<strong>Portails Client et Partenaire (PWA "
                "installables)</strong> — communication, documents, "
                "déboursés, états d'avancement, accessibles 24/7 sur "
                "ordinateur, tablette ou téléphone",
                "<strong>Décision finale en 5 jours ouvrables</strong> "
                "(vs 4 à 8 semaines en institution)",
            ])
        ),
    )


def _client_block_en() -> str:
    return info_box(
        title="WHAT YOUR CLIENTS RECEIVE",
        content_html=feature_list([
            "<strong>Score Norvex&trade;</strong> — proprietary AI, "
            "<strong>LOI in 30 minutes</strong> ready to present",
            "<strong>Norvex Intel&trade;</strong> — proprietary AI "
            "analysis in 3 approaches (income, comparables, cost) that "
            "validates and completes the initial appraisal internally. "
            "Your client provides a baseline appraisal at standard market "
            "rates; <strong>no second appraisal billed by us, no "
            "additional 3-to-6 week delay for our validation</strong>",
            "<strong>Norvex Cost Analyzer&trade;</strong> — complete and "
            "automated cost breakdown",
            "<strong>Norvex Track&trade;</strong> — real-time construction "
            "monitoring for construction files",
            "<strong>Norvex Brain&trade;</strong> — central management "
            "system: full traceability, auditability, integrated accounting",
            "<strong>Client Portal (PWA)</strong> — your client tracks "
            "their file 24/7 on their phone",
            "<strong>Final decision in 5 business days</strong> "
            "(vs 4-8 weeks at an institution)",
        ]),
    )


def _engagement_block_fr() -> str:
    """Bloc d'engagement V10 (2026-05-21) : '100% contrôle relation client'.

    Ajouté après que Yves a constaté que les courtiers s'inscrivaient pas
    parce qu'ils craignaient de perdre leur client. Ce bloc est placé EN TÊTE
    (juste après l'opener + vidéo) pour rassurer immédiatement.
    """
    return (
        '<div style="background:#FCF8EE;border-left:3px solid #C8B070;'
        'padding:18px 22px;margin:18px 0 22px;">'
        '<div style="font-size:10px;letter-spacing:2.5px;color:#9A8554;'
        'text-transform:uppercase;margin-bottom:10px;">'
        'Notre engagement envers vous'
        '</div>'
        '<div style="font-family:Georgia,serif;font-size:19px;color:#0A0A0A;'
        'line-height:1.4;margin-bottom:14px;">'
        'Vous gardez 100 % le contrôle de votre relation client.'
        '</div>'
        '<div style="font-size:13.5px;color:#3a3a3a;line-height:1.7;">'
        'Vous restez <strong>au centre</strong> de chaque communication avec '
        'votre client. La LOI est envoyée à votre client avec vous en copie. '
        'À chaque rencontre &mdash; typiquement avant signature finale &mdash; '
        '<strong>vous êtes présent</strong>. C\'est votre client, votre '
        'relation, votre commission. Nous, on est le moteur de financement '
        'qui exécute pour vous, en partenariat.'
        '</div>'
        '</div>'
    )


def _broker_block_fr() -> str:
    return info_box(
        title="CE QUE VOUS RECEVEZ EN TANT QUE COURTIER PARTENAIRE",
        content_html=feature_list([
            "<strong>Inscription rapide</strong> &mdash; 5 champs, "
            "30 secondes. Examen institutionnel sous "
            "<strong>24 h ouvrables</strong>",
            "<strong>Rémunération transparente et compétitive</strong>, "
            "payée à la clôture chez le notaire, sans délai. Modalités "
            "confirmées dès l'acceptation de votre candidature",
            "<strong>Agent de suivi dédié</strong> &mdash; pour chaque "
            "dossier que vous nous référez, vous recevez automatiquement "
            "les mises à jour clés (réception, statut, questions, décision "
            "finale). <strong>Toutes les communications passent par vous</strong>",
            "<strong>Ligne directe à la direction</strong> &mdash; "
            "interlocuteur humain prioritaire, disponibilité accélérée",
            "<strong>Outils pro inclus</strong> : générateur de LOI, "
            "sommaires investisseur, fiches deal cards prêtes à présenter "
            "à vos clients",
            "<strong>Dossiers complexes bienvenus</strong> : crédit "
            "difficile, travailleurs autonomes, délais serrés, construction "
            "commerciale/multi-résidentielle/industrielle, développement, "
            "acquisition d'immeubles locatifs, financement de terrain, "
            "refinancement, prêts-ponts, propositions concordataires libérées",
            "Financements de <strong>2,5 M$ à 100 M$</strong> &mdash; "
            "Québec &amp; Ontario, conditions calibrées au Score Norvex de "
            "chaque dossier",
        ]),
    )


def _engagement_block_en() -> str:
    """Engagement block V10 (2026-05-21): '100% control over your client'.

    Added after Yves identified that brokers weren't signing up because they
    feared losing their client. Placed at the top of the letter to reassure
    immediately.
    """
    return (
        '<div style="background:#FCF8EE;border-left:3px solid #C8B070;'
        'padding:18px 22px;margin:18px 0 22px;">'
        '<div style="font-size:10px;letter-spacing:2.5px;color:#9A8554;'
        'text-transform:uppercase;margin-bottom:10px;">'
        'Our commitment to you'
        '</div>'
        '<div style="font-family:Georgia,serif;font-size:19px;color:#0A0A0A;'
        'line-height:1.4;margin-bottom:14px;">'
        'You keep 100 % control over your client relationship.'
        '</div>'
        '<div style="font-size:13.5px;color:#3a3a3a;line-height:1.7;">'
        'You remain <strong>at the center</strong> of every communication with '
        'your client. The LOI is sent to your client with you in copy. At '
        'every meeting &mdash; typically before final signing &mdash; '
        '<strong>you are present</strong>. It\'s your client, your '
        'relationship, your commission. We are the financing engine '
        'that executes for you, in partnership.'
        '</div>'
        '</div>'
    )


def _broker_block_en() -> str:
    return info_box(
        title="WHAT YOU RECEIVE AS A PARTNER BROKER",
        content_html=feature_list([
            "<strong>Quick registration</strong> &mdash; 5 fields, "
            "30 seconds. Institutional review within "
            "<strong>24 business hours</strong>",
            "<strong>Transparent and competitive compensation</strong>, "
            "paid at closing through the notary/lawyer, without delay. "
            "Terms confirmed upon acceptance of your application",
            "<strong>Dedicated follow-up agent</strong> &mdash; for every "
            "file you refer to us, you automatically receive key updates "
            "(receipt, status, questions, final decision). "
            "<strong>All communications go through you</strong>",
            "<strong>Direct line to leadership</strong> &mdash; priority "
            "human point of contact, fast availability",
            "<strong>Pro tools included</strong>: LOI generator, investor "
            "summaries, deal cards ready to present to your clients",
            "<strong>Complex files welcome</strong>: difficult credit, "
            "self-employed, tight timelines, commercial/multi-residential/"
            "industrial construction, development, acquisition of revenue "
            "properties, land financing, refinancing, bridge loans, "
            "discharged consumer proposals",
            "Financings from <strong>CA$2.5M to CA$100M</strong> &mdash; "
            "Quebec &amp; Ontario, terms calibrated to each file's Score "
            "Norvex",
        ]),
    )


def _track_record_fr() -> str:
    # ⚠️ Pas de re-listing des modules ici (déjà détaillés dans _broker_block_fr).
    # Évite la redondance signalée par Yves 2026-05-05.
    return (
        '<p style="margin:18px 0;">Notre direction cumule plus de '
        '<strong>200 M$ de financements annuels</strong> en privé. '
        'Doublé de notre infrastructure technologique décrite ci-dessus, '
        'cela permet à Capital Norvex d\'être <strong>en jours ce que '
        'les autres font en semaines</strong>.</p>'
        '<p style="margin:0 0 18px 0;">Quand vous référez un client à '
        'Capital Norvex, vous ne lui vendez pas un prêt — vous lui '
        'donnez accès à <strong>un standard institutionnel international</strong>. '
        'Votre client en sort gagnant&nbsp;; votre réputation aussi.</p>'
    )


def _track_record_en() -> str:
    return (
        '<p style="margin:18px 0;">Our leadership has structured '
        '<strong>over CA$200M of private financing annually</strong>. '
        'But it\'s our <strong>technology infrastructure</strong> that '
        'makes the difference: no lender — private or institutional — '
        'offers <em>LOI in 30 min + internal appraisal included + '
        'real-time construction monitoring + PWA portals</em>.</p>'
        '<p style="margin:0 0 18px 0;">When you refer a client to '
        'Capital Norvex, you\'re not selling a loan. You\'re offering '
        '<strong>the full Norvex ecosystem</strong>.</p>'
    )


def _cta_fr() -> str:
    return (
        '<div style="margin:24px 0 8px 0;text-align:center;">'
        f'<div style="font-size:10px;letter-spacing:2.5px;'
        f'color:{COLOR_GOLD_DARK};margin-bottom:10px;">'
        'DEVENIR COURTIER PARTENAIRE &middot; INSCRIPTION RAPIDE</div>'
        '<p style="margin:0 0 6px 0;font-size:13px;color:#555;">'
        'L\'inscription prend <strong>30 secondes</strong> (5 champs). '
        'La direction de Capital Norvex examine votre profil sous '
        '<strong>24 h ouvrables</strong>. Sur acceptation, vous recevez '
        'votre code courtier unique ainsi que l\'accès à votre Espace '
        'Courtier.</p>'
        '</div>'
        + cta_button(
            label="M'inscrire au programme",
            url=f"{SITE_URL}/courtier-candidature.html",
            sublabel="5 champs · 30 secondes · réponse en 24 h",
        )
        + '<p style="margin:18px 0 0 0;text-align:center;font-size:12.5px;'
        'color:#666;">'
        'Découvrez l\'écosystème complet sur '
        f'<a href="{SITE_URL}" style="color:#9A8554;text-decoration:none;">'
        '<strong>capitalnorvex.com</strong></a></p>'
    )


def _cta_en() -> str:
    return (
        '<div style="margin:24px 0 8px 0;text-align:center;">'
        f'<div style="font-size:10px;letter-spacing:2.5px;'
        f'color:{COLOR_GOLD_DARK};margin-bottom:10px;">'
        'BECOME A PARTNER BROKER &middot; QUICK REGISTRATION</div>'
        '<p style="margin:0 0 6px 0;font-size:13px;color:#555;">'
        'Registration takes <strong>30 seconds</strong> (5 fields). '
        'Capital Norvex management reviews your profile within '
        '<strong>24 business hours</strong>. Upon acceptance, you '
        'receive your unique broker code and access to your Broker '
        'Workspace.</p>'
        '</div>'
        + cta_button(
            label="Sign me up",
            url=f"{SITE_URL}/courtier-candidature-en.html",
            sublabel="5 fields · 30 seconds · 24 h response",
        )
        + '<p style="margin:18px 0 0 0;text-align:center;font-size:12.5px;'
        'color:#666;">'
        'Discover the full ecosystem at '
        f'<a href="{SITE_URL}" style="color:#9A8554;text-decoration:none;">'
        '<strong>capitalnorvex.com</strong></a></p>'
    )


def _signature_phone_fr() -> str:
    # Arial + tabular-nums : alignement chiffres (fix 2026-05-05)
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


# ─── Render functions ───────────────────────────────────────────────────────

def _v11_body_fr() -> str:
    """Lettre courtier V11 — PUNCH + écosystème + bonnes mains (FR)."""
    return (
        # Hook punch
        '<p style="margin:0 0 18px 0;font-size:15px;line-height:1.7;">'
        'Vous le savez aussi bien que nous : en hypothèque commerciale, '
        '<strong>votre crédibilité tient à votre vitesse</strong>. Quand le '
        'prêteur prend 3 mois pour répondre, c\'est vous qui perdez votre client.</p>'
        # Promesse vitesse
        '<div style="background:#FCF8EE;border-left:3px solid #C8B070;padding:18px 22px;margin:0 0 22px 0;">'
        '<div style="font-size:10.5px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">'
        'Chez Capital Norvex, on a fait simple</div>'
        '<div style="font-family:\'Playfair Display\',Georgia,serif;font-size:21px;line-height:1.35;color:#0A0A0A;margin-bottom:14px;">'
        'LOI en 30 minutes.<br>Décision finale en moins de 5 jours.</div>'
        '<div style="font-size:13.5px;color:#3a3a3a;line-height:1.7;">'
        '(LOI institutionnelle en 30 minutes · Décision finale en moins de 5 jours '
        'après documents complets et RDV Teams)<br>'
        '<strong>Plus rapides. Plus efficaces. Sans la lenteur de la banque.</strong>'
        '</div></div>'
        # Comment on fait ça
        '<div style="margin:0 0 22px 0;">'
        '<div style="font-size:10.5px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">'
        'Comment on fait ça</div>'
        '<p style="margin:0 0 12px 0;font-size:14px;line-height:1.7;color:#3a3a3a;">'
        'Notre infrastructure d\'intelligence artificielle propriétaire nous permet '
        'd\'aller <strong>dix fois plus vite qu\'une banque traditionnelle</strong>, '
        'sans compromettre la rigueur. Notre <strong>Comité de crédit interne</strong> '
        '— analystes, juriste, direction — examine chaque dossier. '
        '<strong>L\'humain reste toujours au centre de la décision.</strong></p>'
        '<p style="margin:0;font-size:15px;font-style:italic;color:#0A0A0A;line-height:1.7;">'
        'Rapide comme une machine. Rigoureux comme une banque.</p>'
        '</div>'
    )


def _v11_body_en() -> str:
    """Broker letter V11 — PUNCH + ecosystem + good hands (EN)."""
    return (
        # Hook punch
        '<p style="margin:0 0 18px 0;font-size:15px;line-height:1.7;">'
        'You know it as well as we do: in commercial mortgage brokering, '
        '<strong>your credibility hinges on your speed</strong>. When the lender '
        'takes 3 months to respond, YOU are the one losing the client.</p>'
        # Speed promise
        '<div style="background:#FCF8EE;border-left:3px solid #C8B070;padding:18px 22px;margin:0 0 22px 0;">'
        '<div style="font-size:10.5px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">'
        'At Capital Norvex, we kept it simple</div>'
        '<div style="font-family:\'Playfair Display\',Georgia,serif;font-size:21px;line-height:1.35;color:#0A0A0A;margin-bottom:14px;">'
        'LOI in 30 minutes.<br>Final decision in under 5 days.</div>'
        '<div style="font-size:13.5px;color:#3a3a3a;line-height:1.7;">'
        '(Institutional LOI in 30 minutes · Final decision in under 5 days '
        'after complete documents and Teams call)<br>'
        '<strong>Faster. More efficient. Without the bank\'s slowness.</strong>'
        '</div></div>'
        # How we do it
        '<div style="margin:0 0 22px 0;">'
        '<div style="font-size:10.5px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">'
        'How we do it</div>'
        '<p style="margin:0 0 12px 0;font-size:14px;line-height:1.7;color:#3a3a3a;">'
        'Our proprietary AI infrastructure allows us to move <strong>ten times '
        'faster than a traditional bank</strong>, without compromising rigor. '
        'Our <strong>in-house Credit Committee</strong> — analysts, counsel, '
        'leadership — reviews every file. <strong>Humans remain at the center '
        'of every decision.</strong></p>'
        '<p style="margin:0;font-size:15px;font-style:italic;color:#0A0A0A;line-height:1.7;">'
        'As fast as a machine. As rigorous as a bank.</p>'
        '</div>'
    )


def _v11_ecosystem_fr() -> str:
    """Encart écosystème 6 modules — vos clients en bonnes mains."""
    rows = [
        ('Score Norvex™', 'Analyse complète du dossier en 30 minutes'),
        ('Hugo Norvex Chantier™', 'Suivi construction en temps réel (avances, déboursés, conformité)'),
        ('Émile Briefing™', 'Brief pré-RDV institutionnel généré automatiquement'),
        ('Norvex Track™', 'Suivi des déboursés et conformité bancaire'),
        ('Norvex Intel™', 'Évaluation interne de l\'actif (sans attendre l\'évaluateur externe)'),
        ('Espace Courtier™', 'Votre app installable 24/7 sur téléphone et ordinateur'),
    ]
    rows_html = "".join(
        f'<tr><td style="padding:8px 12px 8px 0;color:#0A0A0A;font-weight:600;width:200px;font-size:13.5px;vertical-align:top;">{name}</td>'
        f'<td style="padding:8px 0;color:#3a3a3a;font-size:13.5px;line-height:1.6;">{desc}</td></tr>'
        for name, desc in rows
    )
    return (
        '<div style="margin:0 0 22px 0;">'
        '<div style="font-size:10.5px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">'
        'Notre écosystème · Vos clients en bonnes mains</div>'
        '<table style="width:100%;border-collapse:collapse;">'
        + rows_html +
        '</table>'
        '<p style="margin:14px 0 0 0;font-size:13.5px;color:#3a3a3a;font-style:italic;">'
        'Une vraie machine institutionnelle. Pas un consultant solo.</p>'
        '</div>'
    )


def _v11_ecosystem_en() -> str:
    """Ecosystem block 6 modules — your clients in good hands."""
    rows = [
        ('Score Norvex™', 'Complete file analysis in 30 minutes'),
        ('Hugo Norvex Chantier™', 'Real-time construction tracking (advances, draws, compliance)'),
        ('Émile Briefing™', 'Institutional pre-meeting brief, automatically generated'),
        ('Norvex Track™', 'Disbursement and banking compliance tracking'),
        ('Norvex Intel™', 'In-house asset valuation (no waiting for external appraisal)'),
        ('Broker Workspace™', 'Your installable app, 24/7, phone + desktop'),
    ]
    rows_html = "".join(
        f'<tr><td style="padding:8px 12px 8px 0;color:#0A0A0A;font-weight:600;width:200px;font-size:13.5px;vertical-align:top;">{name}</td>'
        f'<td style="padding:8px 0;color:#3a3a3a;font-size:13.5px;line-height:1.6;">{desc}</td></tr>'
        for name, desc in rows
    )
    return (
        '<div style="margin:0 0 22px 0;">'
        '<div style="font-size:10.5px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">'
        'Our ecosystem · Your clients in good hands</div>'
        '<table style="width:100%;border-collapse:collapse;">'
        + rows_html +
        '</table>'
        '<p style="margin:14px 0 0 0;font-size:13.5px;color:#3a3a3a;font-style:italic;">'
        'A real institutional machine. Not a solo consultant.</p>'
        '</div>'
    )


def _v11_au_centre_fr() -> str:
    """Vous restez au centre de votre relation client."""
    items = [
        'Nous ne contactons <strong>jamais</strong> votre client sans que vous soyez en copie',
        'Pour chaque rencontre Teams — typiquement avant signature finale — <strong>vous êtes présent</strong>',
        'C\'est <strong>votre client, votre commission, votre rôle de conseiller</strong>',
        'Nous travaillons en partenariat avec vous, en coulisse',
    ]
    items_html = "".join(
        f'<li style="padding:5px 0;font-size:13.5px;color:#3a3a3a;line-height:1.6;">{it}</li>'
        for it in items
    )
    return (
        '<div style="background:#FCF8EE;border-left:3px solid #C8B070;padding:18px 22px;margin:0 0 22px 0;">'
        '<div style="font-size:10.5px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">'
        'Vous restez au centre de votre relation client</div>'
        '<ul style="margin:0;padding:0 0 0 18px;list-style:none;">'
        + items_html +
        '</ul></div>'
    )


def _v11_au_centre_en() -> str:
    """You remain at the center of your client relationship."""
    items = [
        'We <strong>never</strong> contact your client without you in copy',
        'For every Teams meeting — typically before final signing — <strong>you are present</strong>',
        'It\'s <strong>your client, your commission, your advisor role</strong>',
        'We work in partnership with you, behind the scenes',
    ]
    items_html = "".join(
        f'<li style="padding:5px 0;font-size:13.5px;color:#3a3a3a;line-height:1.6;">{it}</li>'
        for it in items
    )
    return (
        '<div style="background:#FCF8EE;border-left:3px solid #C8B070;padding:18px 22px;margin:0 0 22px 0;">'
        '<div style="font-size:10.5px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">'
        'You remain at the center of your client relationship</div>'
        '<ul style="margin:0;padding:0 0 0 18px;list-style:none;">'
        + items_html +
        '</ul></div>'
    )


def _v11_espace_courtier_fr() -> str:
    """Section Espace Courtier 24/7."""
    items = [
        '<strong>Suivi temps réel</strong> de chaque dossier référé, 24 h sur 24, 7 jours sur 7',
        '<strong>Soumission de dossier en quelques clics</strong> (vous avez déjà les documents de votre client)',
        '<strong>LOI téléchargeable</strong> dès qu\'elle est prête',
        '<strong>Plus besoin de nous appeler</strong> pour savoir où c\'est rendu',
    ]
    items_html = "".join(
        f'<li style="padding:5px 0;font-size:13.5px;color:#3a3a3a;line-height:1.6;">{it}</li>'
        for it in items
    )
    return (
        '<div style="margin:0 0 22px 0;">'
        '<div style="font-size:10.5px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">'
        'Votre nouvel outil · L\'Espace Courtier</div>'
        '<p style="margin:0 0 12px 0;font-size:14px;line-height:1.7;color:#3a3a3a;">'
        'Une fois accrédité, vous recevez votre <strong>code courtier personnel</strong> '
        'et l\'accès à l\'<strong>Espace Courtier Capital Norvex</strong> — installable '
        'sur votre téléphone et votre ordinateur comme une vraie application :</p>'
        '<ul style="margin:0;padding:0 0 0 18px;list-style:none;">'
        + items_html +
        '</ul></div>'
    )


def _v11_espace_courtier_en() -> str:
    """Broker Workspace 24/7 section."""
    items = [
        '<strong>Real-time tracking</strong> of every referred file, 24/7',
        '<strong>File submission in a few clicks</strong> (you already have your client\'s documents)',
        '<strong>LOI download</strong> as soon as it\'s ready',
        '<strong>No more calling us</strong> to check where things stand',
    ]
    items_html = "".join(
        f'<li style="padding:5px 0;font-size:13.5px;color:#3a3a3a;line-height:1.6;">{it}</li>'
        for it in items
    )
    return (
        '<div style="margin:0 0 22px 0;">'
        '<div style="font-size:10.5px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">'
        'Your new tool · The Broker Workspace</div>'
        '<p style="margin:0 0 12px 0;font-size:14px;line-height:1.7;color:#3a3a3a;">'
        'Once accredited, you receive your <strong>personal broker code</strong> and '
        'access to the <strong>Capital Norvex Broker Workspace</strong> — installable '
        'on your phone and desktop as a real application:</p>'
        '<ul style="margin:0;padding:0 0 0 18px;list-style:none;">'
        + items_html +
        '</ul></div>'
    )


def _v11_creneau_fr() -> str:
    return (
        '<div style="margin:0 0 22px 0;">'
        '<div style="font-size:10.5px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">'
        'Notre créneau</div>'
        '<p style="margin:0 0 8px 0;font-size:14px;line-height:1.7;color:#3a3a3a;">'
        'Financements de <strong>2,5 M$ à 100 M$</strong>, <strong>Québec &amp; Ontario</strong> : '
        'acquisition, construction, refinancement, terrain, multi-résidentiel, commercial.</p>'
        '<p style="margin:0;font-size:14px;line-height:1.7;color:#3a3a3a;">'
        'Crédit difficile, délais serrés, propositions concordataires, immeubles à revenus '
        'complexes — <strong>on prend les dossiers que la banque refuse</strong>.</p>'
        '</div>'
    )


def _v11_creneau_en() -> str:
    return (
        '<div style="margin:0 0 22px 0;">'
        '<div style="font-size:10.5px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">'
        'Our niche</div>'
        '<p style="margin:0 0 8px 0;font-size:14px;line-height:1.7;color:#3a3a3a;">'
        'Financings from <strong>CA$2.5M to CA$100M</strong>, <strong>Quebec &amp; Ontario</strong>: '
        'acquisition, construction, refinancing, land, multi-residential, commercial.</p>'
        '<p style="margin:0;font-size:14px;line-height:1.7;color:#3a3a3a;">'
        'Difficult credit, tight deadlines, restructuring proposals, complex income '
        'properties — <strong>we take the files banks turn down</strong>.</p>'
        '</div>'
    )


def _v11_cta_fr() -> str:
    site_url = SITE_URL
    return (
        '<div style="background:#FCF8EE;border-left:3px solid #C8B070;padding:22px;margin:0 0 22px 0;text-align:center;">'
        '<div style="font-size:10.5px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">'
        'Inscription en 30 secondes</div>'
        '<p style="margin:0 0 18px 0;font-size:14px;line-height:1.6;color:#3a3a3a;">'
        '5 champs. Examen sous <strong>24-48 h ouvrables</strong>. Sur acceptation, votre '
        'code courtier vous est transmis avec l\'accès à votre Espace Courtier.</p>'
        + cta_button(
            label='Soumettre ma demande d\'accréditation',
            url=f'{site_url}/courtier-candidature.html',
            sublabel='Programme courtier partenaire',
        )
        + '</div>'
    )


def _v11_cta_en() -> str:
    site_url = SITE_URL
    return (
        '<div style="background:#FCF8EE;border-left:3px solid #C8B070;padding:22px;margin:0 0 22px 0;text-align:center;">'
        '<div style="font-size:10.5px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">'
        'Registration in 30 seconds</div>'
        '<p style="margin:0 0 18px 0;font-size:14px;line-height:1.6;color:#3a3a3a;">'
        '5 fields. Review within <strong>24-48 business hours</strong>. Upon acceptance, '
        'your broker code is sent along with access to your Broker Workspace.</p>'
        + cta_button(
            label='Submit my accreditation request',
            url=f'{site_url}/courtier-candidature-en.html',
            sublabel='Partner broker program',
        )
        + '</div>'
    )


def render_cold_outreach(
    broker: Dict[str, Any],
    lang: str = "fr",
) -> str:
    """Cold outreach V11 (2026-05-21) : courtier identifié, jamais contacté.
    Angle PUNCH : LOI 30 min + décision < 5 jours, Comité de crédit interne
    (pas Yves perso), écosystème complet, Espace Courtier installable 24/7.
    Décideur = Comité de crédit (scalabilité 150+ dossiers/an)."""
    is_en = lang == "en"
    name = broker.get("name", "")

    if is_en:
        body = (
            _v11_body_en()
            + video_block("c8w5joFPMTY", "Broker Partner Program", "1 min 15", lang="en")
            + _v11_ecosystem_en()
            + _v11_au_centre_en()
            + _v11_espace_courtier_en()
            + _v11_creneau_en()
            + gold_rule()
            + _v11_cta_en()
            + '<p style="margin:18px 0 0 0;">Looking forward to working with you,</p>'
        )
    else:
        body = (
            _v11_body_fr()
            + video_block("aJJuOUBIunc", "Programme Courtier Partenaire", "1 min 15")
            + _v11_ecosystem_fr()
            + _v11_au_centre_fr()
            + _v11_espace_courtier_fr()
            + _v11_creneau_fr()
            + gold_rule()
            + _v11_cta_fr()
            + '<p style="margin:18px 0 0 0;">Au plaisir de travailler avec vous,</p>'
        )

    # Décision Yves 2026-05-21 : Comité de crédit interne (pas Yves perso) =
    # scalabilité institutionnelle. Signature en bandeau noir = Yves OK.
    return render_variation_a(
        body_html=body,
        recipient_name=name or None,
        signature_name="L'équipe Capital Norvex" if lang == "fr" else "The Capital Norvex Team",
        signature_title="Programme courtier partenaire" if lang == "fr" else "Partner broker program",
        use_image_signature=False,
        lang=lang,
    )


def render_warm_followup(
    broker: Dict[str, Any],
    deal_count: int = 0,
    lang: str = "fr",
) -> str:
    """Relance d'un courtier déjà en relation."""
    is_en = lang == "en"
    name = broker.get("name", "")

    deal_intro_fr = (
        f"Vous avez déjà référé {deal_count} dossier(s) à Capital Norvex — "
        f"merci pour votre confiance. "
        if deal_count > 0
        else "Suite à notre dernier échange, "
    )
    deal_intro_en = (
        f"You've already referred {deal_count} file(s) to Capital Norvex — "
        f"thank you for your trust. "
        if deal_count > 0
        else "Following our last exchange, "
    )

    if is_en:
        opener = (
            f'<p style="margin:0 0 18px 0;">{deal_intro_en}'
            'I wanted to share some recent improvements to our platform '
            'that may interest your clients with active or upcoming files.</p>'
        )
        body = (
            opener
            + _client_block_en()
            + _track_record_en()
            + gold_rule()
            + _signature_phone_en()
            + '<p style="margin:18px 0 0 0;">Sincerely,</p>'
        )
    else:
        opener = (
            f'<p style="margin:0 0 18px 0;">{deal_intro_fr}'
            'je voulais vous partager quelques améliorations récentes de '
            'notre plateforme susceptibles d\'intéresser vos clients ayant '
            'des dossiers actifs ou à venir.</p>'
        )
        body = (
            opener
            + _client_block_fr()
            + _track_record_fr()
            + gold_rule()
            + _signature_phone_fr()
            + '<p style="margin:18px 0 0 0;">Avec considération,</p>'
        )

    # Décision Yves 2026-05-04 : warm follow-up courtier aussi signé équipe.
    return render_variation_a(
        body_html=body,
        recipient_name=name or None,
        signature_name="L'équipe Capital Norvex" if lang == "fr" else "The Capital Norvex Team",
        signature_title="Programme partenaires courtiers" if lang == "fr" else "Partner brokers program",
        use_image_signature=False,
        lang=lang,
    )
