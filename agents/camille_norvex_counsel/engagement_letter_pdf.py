"""Générateur PDF dynamique de lettres d'engagement Capital Norvex.

Usage :
    from .engagement_letter_pdf import generate_engagement_letter_pdf
    pdf_bytes = generate_engagement_letter_pdf(dossier, terms, lang="fr")

Le PDF généré reflète les termes spécifiques au dossier (taux, montant, durée,
frais, conditions particulières) au lieu d'utiliser un template statique.

Style : reproduit l'identité visuelle du script existant
`CapitalNorvex_Scripts/scripts/01_lettres_engagement.py` (palette dorée,
GoldLine, structure de sections).

⚠️  Ce module est AUTONOME — il ne touche pas au script existant
    (anti-régression : le script existant continue de générer les 4 PDFs
    statiques de référence dans `document convention et autres/`).
"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Dict, Optional

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Palette (alignée sur 01_lettres_engagement.py) ────────────────
DARK = HexColor("#0a0d13")
GOLD = HexColor("#C9A84C")
GOLD2 = HexColor("#b8975a")
CREAM = HexColor("#f5f0e8")
CREAM2 = HexColor("#e8e0ce")
GREY_LT = HexColor("#d4c9b0")
GREY_MED = HexColor("#8a7d5f")
WHITE = HexColor("#ffffff")

PAGE_W, PAGE_H = letter
MARGIN = 0.75 * inch

# ── Styles ────────────────────────────────────────────────────────
_TITLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=18,
                       textColor=WHITE, alignment=TA_CENTER, spaceAfter=4,
                       leading=22, letterSpacing=2)
_SUBTITLE = ParagraphStyle("subtitle", fontName="Helvetica-Oblique", fontSize=10,
                          textColor=GREY_MED, alignment=TA_CENTER, spaceAfter=4)
_SECTION = ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=11,
                         textColor=GOLD, alignment=TA_LEFT, spaceAfter=8,
                         leading=14, letterSpacing=1)
_BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=9.5,
                      textColor=DARK, alignment=TA_LEFT, leading=14, spaceAfter=4)
_BODY_SM = ParagraphStyle("body_sm", fontName="Helvetica", fontSize=8.5,
                         textColor=DARK, alignment=TA_LEFT, leading=12, spaceAfter=3)
_NOTE = ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=8,
                      textColor=GREY_MED, alignment=TA_CENTER, spaceAfter=4)
_FIELD_LABEL = ParagraphStyle("flabel", fontName="Helvetica-Bold", fontSize=8.5,
                             textColor=GOLD, alignment=TA_LEFT, leading=11)
_FIELD_VAL = ParagraphStyle("fval", fontName="Helvetica", fontSize=9,
                           textColor=DARK, alignment=TA_LEFT, leading=12)


# ── Custom flowable : ligne dorée ────────────────────────────────
class GoldLine(Flowable):
    def __init__(self, width=None, thickness=1.2, color=None):
        Flowable.__init__(self)
        self.width = width
        self.thickness = thickness
        self.color = color or GOLD
        self.height = thickness + 2

    def wrap(self, availWidth, availHeight):
        if self.width is None:
            self.width = availWidth
        return (self.width, self.height)

    def draw(self):
        w = self.width or (PAGE_W - 2 * MARGIN)
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, w, 0)


# ── Header / Footer dorés ────────────────────────────────────────
def _make_on_page(product_tag: str, dossier_id: str):
    def on_page(canvas, doc):
        canvas.saveState()
        w, h = letter
        # Header bande sombre
        canvas.setFillColor(DARK)
        canvas.rect(0, h - 54, w, 54, fill=1, stroke=0)
        canvas.setFillColor(GOLD)
        canvas.rect(0, h - 57, w, 3, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(MARGIN, h - 32, "CAPITAL NORVEX INC.")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GOLD)
        canvas.drawRightString(w - MARGIN, h - 30, product_tag)
        canvas.setFillColor(GREY_LT)
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(w - MARGIN, h - 42, f"Dossier : {dossier_id}")

        # Footer
        canvas.setFillColor(GOLD)
        canvas.rect(0, 30, w, 1, fill=1, stroke=0)
        canvas.setFillColor(GREY_MED)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(MARGIN, 18,
                          "Capital Norvex Inc. · 2705-1000 André-Prévost, Île-des-Sœurs, Montréal QC H3E 0G2")
        canvas.drawRightString(w - MARGIN, 18, f"Page {doc.page}")
        canvas.restoreState()

    return on_page


# ── Helpers de structure ─────────────────────────────────────────
def _section_bar(title: str) -> list:
    """Retourne une barre de section dorée."""
    out = []
    out.append(Spacer(1, 8))
    tbl = Table([[Paragraph(title, _SECTION)]],
                colWidths=[PAGE_W - 2 * MARGIN])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CREAM),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBEFORE", (0, 0), (0, 0), 3, GOLD),
    ]))
    out.append(tbl)
    out.append(Spacer(1, 6))
    return out


def _two_col_fields(rows: list[tuple[str, str]]) -> list:
    """Tableau 2 colonnes (label en or / valeur)."""
    data = []
    for label, value in rows:
        data.append([
            Paragraph(label, _FIELD_LABEL),
            Paragraph(value or "—", _FIELD_VAL),
        ])
    t = Table(data, colWidths=[2.0 * inch, 4.6 * inch])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, GREY_LT),
    ]))
    return [t, Spacer(1, 8)]


def _modalites_financieres_table(terms: Dict[str, Any]) -> list:
    """Tableau premium des modalités financières — chiffres mis en valeur."""
    rows = [
        ["Montant du prêt approuvé",
         f"{terms.get('montantApprouve', '—')} {terms.get('devise', 'CAD $')}".strip()],
        ["Taux annuel (intérêts)",
         f"{terms.get('taux', '—')} %"],
        ["Frais d'origination",
         f"{terms.get('frais', '—')} %"],
        ["Durée du prêt",
         f"{terms.get('termeMois', '—')} mois"],
        ["Type d'intérêts",
         terms.get('typeInterets', 'Mensuels')],
        ["LTV (Loan-to-Value)",
         f"{terms.get('ltv', '—')} %"],
        ["Garantie principale",
         terms.get('garanties', 'Hypothèque immobilière de premier rang')],
        ["Date d'émission",
         terms.get('dateEmission', datetime.now().strftime('%Y-%m-%d'))],
        ["Validité de l'offre",
         f"{terms.get('validiteJours', 30)} jours"],
    ]
    t = Table(rows, colWidths=[2.5 * inch, 4.1 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), GOLD),
        ("TEXTCOLOR", (1, 0), (1, -1), DARK),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [CREAM, CREAM2]),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEABOVE", (0, 0), (-1, 0), 2, GOLD),
        ("LINEBELOW", (0, -1), (-1, -1), 2, GOLD),
    ]))
    return [t, Spacer(1, 12)]


# ── PRODUIT/TYPE → label affiché ─────────────────────────────────
PRODUCT_LABELS = {
    "Construction":   ("PRÊT DE CONSTRUCTION",
                       "Financement privé institutionnel — Travaux neufs et rénovations majeures"),
    "Terrain":        ("PRÊT TERRAIN",
                       "Financement privé institutionnel — Acquisition et portage de terrain"),
    "Acquisition":    ("PRÊT ACQUISITION D'IMMEUBLE",
                       "Financement privé institutionnel — Acquisition d'immeubles à revenus"),
    "Refinancement":  ("PRÊT REFINANCEMENT",
                       "Financement privé institutionnel — Refinancement immobilier"),
    "Pont":           ("PRÊT-PONT",
                       "Financement privé institutionnel — Solution de transition court terme"),
    "Commercial":     ("PRÊT COMMERCIAL",
                       "Financement privé institutionnel — Immeuble commercial"),
    "Résidentiel":    ("PRÊT RÉSIDENTIEL",
                       "Financement privé institutionnel — Immeuble résidentiel"),
}


# ── Builder principal ─────────────────────────────────────────────
def _build_cover(story: list, product_name: str, product_desc: str,
                 dossier_id: str, dossier: Dict[str, Any], terms: Dict[str, Any]):
    """Couverture personnalisée."""
    story.append(Spacer(1, 0.6 * inch))

    # Bande titre dorée
    tbl = Table([[Paragraph("LETTRE D'ENGAGEMENT", _TITLE)]],
                colWidths=[PAGE_W - 2 * MARGIN])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEABOVE", (0, 0), (-1, 0), 3, GOLD),
        ("LINEBELOW", (0, -1), (-1, -1), 3, GOLD),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 6))
    story.append(Paragraph(product_name, ParagraphStyle(
        "pname", fontName="Helvetica-Bold", fontSize=15,
        textColor=DARK, alignment=TA_CENTER, spaceAfter=4)))
    story.append(Paragraph(product_desc, _SUBTITLE))
    story.append(Spacer(1, 24))

    # Tableau d'identification (DOSSIER + EMPRUNTEUR + PROJET + MONTANT — REMPLIS)
    client_name = f"{dossier.get('prenom', '')} {dossier.get('nom', '')}".strip() or "—"
    info = [
        ["NO. DOSSIER", dossier_id],
        ["EMPRUNTEUR", client_name],
        ["PROJET", dossier.get('adresse', '—')],
        ["MONTANT APPROUVÉ", f"{terms.get('montantApprouve', '—')} {terms.get('devise', 'CAD $')}".strip()],
        ["DATE D'ÉMISSION", terms.get('dateEmission', datetime.now().strftime('%Y-%m-%d'))],
        ["VALIDITÉ", f"{terms.get('validiteJours', 30)} jours suivant l'émission"],
    ]
    t = Table(info, colWidths=[1.9 * inch, 4.0 * inch], hAlign="CENTER")
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (0, -1), GOLD),
        ("TEXTCOLOR", (1, 0), (1, -1), DARK),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [CREAM, CREAM2]),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("LINEBELOW", (0, -1), (-1, -1), 1.5, GOLD),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4 * inch))

    story.append(Paragraph(
        "Capital structuré.  Ambition maîtrisée.",
        ParagraphStyle("slogan", fontName="Helvetica-Oblique", fontSize=10,
                       textColor=GOLD2, alignment=TA_CENTER, spaceAfter=8)))

    story.append(Paragraph(
        "CONFIDENTIEL — Offre de financement conditionnelle, sous réserve "
        "des conditions énoncées dans la présente lettre.", _NOTE))
    story.append(PageBreak())


def _build_identification(story: list, dossier: Dict[str, Any]):
    """Section 1 : identification des parties."""
    story.extend(_section_bar("1.  IDENTIFICATION DES PARTIES"))
    client_name = f"{dossier.get('prenom', '')} {dossier.get('nom', '')}".strip() or "—"
    rows = [
        ("Prêteur :", "Capital Norvex Inc."),
        ("Adresse du Prêteur :", "2705-1000 André-Prévost, Île-des-Sœurs (Verdun), Montréal, QC H3E 0G2"),
        ("Téléphone :", "1-(438)-533-PRET (7738)"),
        ("Courriel :", "info@capitalnorvex.com"),
        ("Représentant :", "Yves Barrette, Président"),
        ("NEQ Capital Norvex :", "1182097890"),
        ("Emprunteur :", client_name),
        ("Courriel emprunteur :", dossier.get('email', '—')),
        ("Téléphone emprunteur :", dossier.get('tel', '—')),
        ("Adresse du projet :", dossier.get('adresse', '—')),
    ]
    story.extend(_two_col_fields(rows))


def _build_modalites(story: list, terms: Dict[str, Any]):
    """Section 2 : modalités financières (le cœur des termes négociés)."""
    story.extend(_section_bar("2.  MODALITÉS FINANCIÈRES — TERMES CONVENUS"))
    story.extend(_modalites_financieres_table(terms))

    if terms.get('echeancierType'):
        story.append(Paragraph(
            f"<b>Échéancier :</b> {terms['echeancierType']}", _BODY))
        story.append(Spacer(1, 6))


def _build_conditions_particulieres(story: list, terms: Dict[str, Any]):
    """Section 3 : conditions particulières au dossier."""
    cond = terms.get('conditionsParticulieres') or terms.get('conditions')
    if not cond:
        return
    story.extend(_section_bar("3.  CONDITIONS PARTICULIÈRES AU DOSSIER"))
    if isinstance(cond, str):
        story.append(Paragraph(cond.replace("\n", "<br/>"), _BODY))
    elif isinstance(cond, list):
        for c in cond:
            story.append(Paragraph(f"• {c}", _BODY))
            story.append(Spacer(1, 3))
    story.append(Spacer(1, 8))


def _build_conditions_standards(story: list):
    """Section 4 : conditions standards (template)."""
    story.extend(_section_bar("4.  CONDITIONS STANDARDS"))
    items = [
        "<b>Vérification diligente complète</b> (titres, RDPRM, conformité réglementaire, états financiers, "
        "évaluation immobilière, taxation municipale et scolaire) à la satisfaction du Prêteur avant tout déboursé.",
        "<b>Hypothèque immobilière de premier rang</b> sur l'immeuble visé, publiée au RDPRM (QC) ou au LRO (ON).",
        "<b>Assurance incendie et responsabilité civile</b> avec Capital Norvex Inc. désigné bénéficiaire et "
        "créancier hypothécaire (montant minimum : valeur de remplacement).",
        "<b>Audit annuel</b> du dossier par le Prêteur (état du projet, conformité aux conditions, suivi Norvex Track™).",
        "<b>Convention de prêt définitive</b> à être signée chez le notaire désigné par le Prêteur, "
        "avec tous les actes et documents accessoires requis.",
        "<b>Honoraires juridiques et professionnels</b> (notaire, évaluateur, arpenteur, etc.) à la charge "
        "de l'Emprunteur, sauf entente contraire écrite.",
        "<b>Aucune clause pénale forfaitaire</b> en cas de défaut — la philosophie Capital Norvex est de privilégier "
        "la résolution amiable et la médiation institutionnelle (voir Convention de prêt à venir).",
    ]
    for item in items:
        story.append(Paragraph(f"• {item}", _BODY))
        story.append(Spacer(1, 4))
    story.append(Spacer(1, 8))


def _build_norvex_tools(story: list, has_track: bool = True):
    """Section 5 : outils Norvex inclus."""
    story.extend(_section_bar("5.  INFRASTRUCTURE TECHNOLOGIQUE NORVEX"))
    story.append(Paragraph(
        "L'Emprunteur bénéficie de l'écosystème technologique propriétaire Capital Norvex — "
        "transparence totale sur l'évolution de son dossier :", _BODY))
    story.append(Spacer(1, 6))
    items = [
        "<b>Score Norvex™</b> — analyse IA de votre dossier en 30 minutes (déjà émise)",
        "<b>Norvex Intel™</b> — évaluation immobilière interne en 3 approches (revenu, comparables, coût)",
        "<b>Norvex Cost Analyzer™</b> — ventilation détaillée des coûts du projet",
    ]
    if has_track:
        items.append(
            "<b>Norvex Track™</b> — suivi en temps réel des déboursés, photos chantier, "
            "statuts (aucun prêteur privé canadien n'offre ce niveau de transparence)"
        )
    items.append(
        "<b>Portail client (PWA)</b> — accès 24/7 à votre dossier, communications, documents, "
        "états d'avancement"
    )
    items.append(
        "<b>NORVEX COUNSEL™ (Camille)</b> — coordination juridique IA pour les échanges "
        "avec votre notaire, en copie de toute communication officielle"
    )
    for item in items:
        story.append(Paragraph(f"• {item}", _BODY))
        story.append(Spacer(1, 3))
    story.append(Spacer(1, 8))


def _build_signatures(story: list, dossier: Dict[str, Any]):
    """Section 6 : signatures."""
    story.append(PageBreak())
    story.extend(_section_bar("6.  SIGNATURES — ACCEPTATION DE L'OFFRE"))
    story.append(Paragraph(
        "L'acceptation de la présente lettre d'engagement par l'Emprunteur (signature ci-dessous "
        "et retour par courriel à <b>camille@capitalnorvex.com</b>, en copie de "
        "<b>yves@capitalnorvex.com</b>) déclenche la phase de vérification diligente et la "
        "préparation de la convention de prêt définitive chez le notaire désigné.",
        _BODY))
    story.append(Spacer(1, 24))

    sig_data = [
        ["POUR CAPITAL NORVEX INC.", "POUR L'EMPRUNTEUR"],
        ["", ""],
        ["", ""],
        ["_______________________________", "_______________________________"],
        ["Yves Barrette, Président", f"{dossier.get('prenom', '')} {dossier.get('nom', '')}".strip()],
        ["Date : __________________", "Date : __________________"],
    ]
    t = Table(sig_data, colWidths=[3.3 * inch, 3.3 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("TEXTCOLOR", (0, 0), (-1, 0), GOLD),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEABOVE", (0, 0), (-1, 0), 1.2, GOLD),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, GOLD),
    ]))
    story.append(t)
    story.append(Spacer(1, 24))
    story.append(GoldLine())
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "<b>Camille — NORVEX COUNSEL™</b> · coordination juridique IA · "
        "M. Yves Barrette, Président, en copie de toute communication officielle.",
        _NOTE))


# ── Fonction publique ────────────────────────────────────────────
def generate_engagement_letter_pdf(
    dossier: Dict[str, Any],
    terms: Dict[str, Any],
    *,
    lang: str = "fr",
    dossier_id: Optional[str] = None,
) -> bytes:
    """Génère un PDF lettre d'engagement personnalisée. Retourne les bytes du PDF.

    Args:
        dossier: doc Firestore du dossier (contient prenom, nom, email, tel, adresse, type)
        terms: termes négociés (montantApprouve, taux, frais, termeMois, ltv,
               garanties, conditionsParticulieres, dateEmission, validiteJours)
        lang: 'fr' ou 'en' (FR par défaut, EN à venir Phase 2)
        dossier_id: si fourni, override l'id du dossier
    """
    # Type de prêt et label
    loan_type = (dossier.get("type") or "Acquisition").strip()
    product_name, product_desc = PRODUCT_LABELS.get(
        loan_type, PRODUCT_LABELS["Acquisition"]
    )
    has_track = loan_type in ("Construction",)
    did = dossier_id or dossier.get("_id") or dossier.get("id") or "DOSSIER"

    # Defaults pour les termes manquants (sécuritaire)
    terms = {
        "montantApprouve": dossier.get("montant", "—"),
        "taux": "11",
        "frais": "3.0",
        "termeMois": "12",
        "ltv": "65",
        "garanties": "Hypothèque immobilière de premier rang",
        "typeInterets": "Mensuels capitalisés",
        "dateEmission": datetime.now().strftime("%Y-%m-%d"),
        "validiteJours": 30,
        "devise": "CAD $",
        **(terms or {}),  # override avec les termes négociés
    }

    # Build PDF
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 40, bottomMargin=MARGIN + 24,
        title=f"Lettre d'engagement — {product_name} — Capital Norvex",
        author="Capital Norvex Inc.",
    )
    on_page = _make_on_page(product_name, did)
    story: list = []
    _build_cover(story, product_name, product_desc, did, dossier, terms)
    _build_identification(story, dossier)
    _build_modalites(story, terms)
    _build_conditions_particulieres(story, terms)
    _build_conditions_standards(story)
    _build_norvex_tools(story, has_track=has_track)
    _build_signatures(story, dossier)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()
