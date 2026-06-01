from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Flowable, Image as RLImage
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from PIL import Image as PILImage
import os

# ── Palette ──────────────────────────────────────────────────────────────────
DARK     = HexColor("#0a0d13")
GOLD     = HexColor("#C9A84C")
GOLD2    = HexColor("#b8975a")
CREAM    = HexColor("#f5f0e8")
CREAM2   = HexColor("#e8e0ce")
GREY_LT  = HexColor("#d4c9b0")
GREY_MED = HexColor("#8a7d5f")
WHITE    = HexColor("#ffffff")
SILVER   = HexColor("#c0c0c0")

PAGE_W, PAGE_H = letter
MARGIN = 0.75 * inch

EMBLEM_PATH   = "/Users/yvesbarrette/Desktop/capitalnorvex-site/CapitalNorvex_Scripts/logos/emblem_header.png"
COVER_PATH    = "/Users/yvesbarrette/Desktop/capitalnorvex-site/CapitalNorvex_Scripts/logos/logo_cover.png"
COVER_SM_PATH = "/Users/yvesbarrette/Desktop/capitalnorvex-site/CapitalNorvex_Scripts/logos/logo_cover.png"

# ── Custom Flowable : ligne dorée ────────────────────────────────────────────
class GoldLine(Flowable):
    def __init__(self, width=None, thickness=1.2, color=None):
        Flowable.__init__(self)
        self.width     = width
        self.thickness = thickness
        self.color     = color or GOLD
        self.height    = thickness + 2
    def wrap(self, availWidth, availHeight):
        if self.width is None:
            self.width = availWidth
        return (self.width, self.height)
    def draw(self):
        w = self.width or (PAGE_W - 2*MARGIN)
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, w, 0)

# ── Header / Footer avec logo ────────────────────────────────────────────────
def make_on_page(product_tag):
    def on_page(canvas, doc):
        canvas.saveState()
        w, h = letter

        # Bande sombre header
        canvas.setFillColor(DARK)
        canvas.rect(0, h-54, w, 54, fill=1, stroke=0)
        # Ligne dorée sous le header
        canvas.setFillColor(GOLD)
        canvas.rect(0, h-57, w, 3, fill=1, stroke=0)

        # ── Logo emblème (M+diamant) dans le header ──
        emb_w, emb_h = 38, 42
        logo_x = MARGIN
        logo_y = h - 47  # uniformisé : top du logo à 5 px du sommet de la page
        canvas.drawImage(EMBLEM_PATH, logo_x, logo_y,
                         width=emb_w, height=emb_h,
                         preserveAspectRatio=True, mask='auto')

        # Texte "CAPITAL NORVEX" à droite de l'emblème
        text_x = logo_x + emb_w + 8
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawString(text_x, h - 30, "CAPITAL NORVEX")
        canvas.setFillColor(GOLD)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(text_x, h - 43, "Financement Privé Institutionnel  |  Québec & Ontario")

        # Tag produit (droite)
        canvas.setFillColor(GOLD)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.drawRightString(w - MARGIN, h - 28, "LETTRE D'ENGAGEMENT")
        canvas.setFillColor(GREY_LT)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawRightString(w - MARGIN, h - 42, product_tag)

        # Numéro de page
        canvas.setFillColor(GREY_LT)
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(w - MARGIN, h - 52, f"p. {doc.page}")

        # ── Pied de page ──
        canvas.setFillColor(DARK)
        canvas.rect(0, 0, w, 50, fill=1, stroke=0)
        canvas.setFillColor(GOLD)
        canvas.rect(0, 50, w, 1.5, fill=1, stroke=0)
        # Ligne du haut — confidentialité (centrée, gold pour la marque)
        canvas.setFillColor(GOLD)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.drawCentredString(w/2, 32,
            "CAPITAL NORVEX  ·  Document confidentiel — Validité selon les termes indiqués")
        # Numéro de page à droite, aligné sur la 1ère ligne
        canvas.setFillColor(GREY_LT)
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(w - MARGIN, 32, f"Page {doc.page}")
        # Ligne du bas — adresse complète (centrée, gris clair)
        canvas.setFillColor(GREY_LT)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(w/2, 14,
            "2705-1000 André-Prévost  ·  Île-des-Sœurs (Verdun)  ·  Montréal, QC H3E 0G2   |   1-(438)-533-PRET (7738)   |   info@capitalnorvex.com   |   capitalnorvex.com")

        canvas.restoreState()
    return on_page

# ── Styles ───────────────────────────────────────────────────────────────────
def styles():
    def S(name, **kw): return ParagraphStyle(name, **kw)
    return dict(
        title    = S("title",    fontName="Helvetica-Bold",    fontSize=18, textColor=DARK,     alignment=TA_CENTER,  spaceAfter=4,  leading=24),
        subtitle = S("subtitle", fontName="Helvetica",         fontSize=10, textColor=GREY_MED, alignment=TA_CENTER,  spaceAfter=12, leading=16),
        section  = S("section",  fontName="Helvetica-Bold",    fontSize=9.5,textColor=GOLD,     spaceBefore=10, spaceAfter=3,  leading=14),
        body     = S("body",     fontName="Helvetica",         fontSize=9,  textColor=DARK,     alignment=TA_JUSTIFY, spaceAfter=4,  leading=14),
        bullet   = S("bullet",   fontName="Helvetica",         fontSize=8.8,textColor=DARK,     spaceAfter=2,  leading=13,  leftIndent=14),
        flabel   = S("flabel",   fontName="Helvetica-Bold",    fontSize=8,  textColor=GREY_MED, spaceAfter=1),
        fval     = S("fval",     fontName="Helvetica",         fontSize=9.5,textColor=DARK,     spaceAfter=7,  leading=15),
        note     = S("note",     fontName="Helvetica-Oblique", fontSize=8,  textColor=GREY_MED, alignment=TA_CENTER, spaceAfter=4),
        alert    = S("alert",    fontName="Helvetica-Bold",    fontSize=8.5,textColor=DARK,     alignment=TA_JUSTIFY,spaceAfter=3, leading=13),
        sign_head= S("sign_head",fontName="Helvetica-Bold",    fontSize=9,  textColor=WHITE,    alignment=TA_LEFT),
        sign_lbl = S("sign_lbl", fontName="Helvetica-Bold",    fontSize=8,  textColor=GREY_MED, spaceAfter=1),
        sign_val = S("sign_val", fontName="Helvetica",         fontSize=9.5,textColor=DARK,     spaceAfter=7),
    )

ST = styles()

# ── Helpers ──────────────────────────────────────────────────────────────────
def section_bar(title):
    tbl = Table([[Paragraph(title, ST["section"])]],
                colWidths=[PAGE_W - 2*MARGIN])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), DARK),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LINEBELOW",     (0,0),(-1,-1), 2, GOLD),
    ]))
    return [Spacer(1,6), tbl, Spacer(1,5)]

def field(label, placeholder):
    return [Paragraph(label, ST["flabel"]),
            Paragraph(f"<u>{placeholder}</u>", ST["fval"])]

def bullet(text):
    return Paragraph(f"• &nbsp; {text}", ST["bullet"])

def body(text):
    return Paragraph(text, ST["body"])

def two_col_fields(pairs):
    items = []
    for i in range(0, len(pairs), 2):
        row_data = []
        for label, ph in pairs[i:i+2]:
            row_data.append(
                Paragraph(f"<b>{label}</b><br/><u>{ph}</u>",
                          ParagraphStyle("tcf", fontName="Helvetica", fontSize=9,
                                         textColor=DARK, spaceAfter=0, leading=15)))
        while len(row_data) < 2:
            row_data.append(Paragraph("", ParagraphStyle("empty", fontSize=9)))
        col_w = (PAGE_W - 2*MARGIN - 16) / 2
        tbl = Table([row_data], colWidths=[col_w, col_w])
        tbl.setStyle(TableStyle([
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 8),
            ("TOPPADDING",    (0,0),(-1,-1), 2),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ]))
        items.append(tbl)
    return items

def cond_table(rows_data, col_widths=None):
    cw = col_widths or [2.4*inch, 1.6*inch, 2.0*inch]
    t = Table(rows_data, colWidths=cw)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), DARK),
        ("TEXTCOLOR",     (0,0),(-1,0), GOLD),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [CREAM, CREAM2]),
        ("GRID",          (0,0),(-1,-1), 0.5, GREY_LT),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("ALIGN",         (1,0),(2,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    return t

def alert_box(text):
    tbl = Table([[Paragraph(text, ST["alert"])]],
                colWidths=[PAGE_W - 2*MARGIN])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), CREAM),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("RIGHTPADDING",  (0,0),(-1,-1), 12),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LINEABOVE",     (0,0),(-1,0), 2, GOLD),
        ("LINEBELOW",     (0,-1),(-1,-1), 2, GOLD2),
    ]))
    return [tbl, Spacer(1,6)]

def sign_block(party_title, fields_list):
    hdr = Table([[Paragraph(party_title, ST["sign_head"])]],
                colWidths=[PAGE_W - 2*MARGIN])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), DARK),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LINEBELOW",     (0,-1),(-1,-1), 2, GOLD),
    ]))
    items = [hdr, Spacer(1,8)]
    for lbl, ph in fields_list:
        items += [Paragraph(lbl, ST["sign_lbl"]),
                  Paragraph(f"<u>{ph}</u>", ST["sign_val"])]
    items.append(Paragraph(
        "Signature : _______________________________________________  Date : ________________",
        ST["body"]))
    items.append(Spacer(1,16))
    return items

# ── PAGE DE COUVERTURE avec logo ─────────────────────────────────────────────
def build_cover(story, product_name, product_desc):
    story.append(Spacer(1, 0.5*inch))

    # Logo centré sur la couverture
    img = RLImage(COVER_PATH, width=120, height=130)
    img.hAlign = "CENTER"
    story.append(img)
    story.append(Spacer(1, 14))

    # Bande titre
    tbl = Table([[Paragraph("LETTRE D'ENGAGEMENT", ST["title"])]],
                colWidths=[PAGE_W - 2*MARGIN])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), DARK),
        ("TOPPADDING",    (0,0),(-1,-1), 14),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LINEABOVE",     (0,0),(-1,0), 3, GOLD),
        ("LINEBELOW",     (0,-1),(-1,-1), 3, GOLD),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 6))
    story.append(Paragraph(product_name, ParagraphStyle(
        "pname", fontName="Helvetica-Bold", fontSize=15,
        textColor=DARK, alignment=TA_CENTER, spaceAfter=4)))
    story.append(Paragraph(product_desc, ST["subtitle"]))
    story.append(Spacer(1, 16))

    # Tableau infos
    info = [
        ["NO. DOSSIER",    "___________________________"],
        ["EMPRUNTEUR",     "___________________________"],
        ["PROJET",         "___________________________"],
        ["MONTANT",        "___________________________"],
        ["DATE D'ÉMISSION","___________________________"],
        ["VALIDITÉ",       "30 jours suivant la date d'émission"],
    ]
    t = Table(info, colWidths=[1.8*inch, 3.8*inch], hAlign="CENTER")
    t.setStyle(TableStyle([
        ("FONTNAME",     (0,0),(0,-1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0),(-1,-1), 9),
        ("TEXTCOLOR",    (0,0),(0,-1), GOLD),
        ("TEXTCOLOR",    (1,0),(1,-1), DARK),
        ("ROWBACKGROUNDS",(0,0),(-1,-1), [CREAM, CREAM2]),
        ("TOPPADDING",   (0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING",  (0,0),(0,-1), 12),
        ("LEFTPADDING",  (1,0),(1,-1), 12),
        ("LINEBELOW",    (0,-1),(-1,-1), 1.5, GOLD),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.3*inch))

    # Slogan
    story.append(Paragraph(
        "Capital structuré.  Ambition maîtrisée.",
        ParagraphStyle("slogan", fontName="Helvetica-Oblique", fontSize=10,
                       textColor=GOLD2, alignment=TA_CENTER, spaceAfter=8)))

    story.append(Paragraph(
        "CONFIDENTIEL — Ce document est une offre de financement conditionnelle.",
        ST["note"]))
    story.append(PageBreak())


# ══════════════════════════════════════════════════════════════════════════════
# CONTENU DES 3 LETTRES (identique à la version précédente)
# ══════════════════════════════════════════════════════════════════════════════

def build_construction(story):
    story += section_bar("1.  IDENTIFICATION DES PARTIES")
    story += two_col_fields([
        ("Prêteur :", "Capital Norvex Inc."),
        ("Adresse du Prêteur :", "2705-1000 André-Prévost, Île-des-Sœurs (Verdun), Montréal, QC H3E 0G2"),
        ("Téléphone :", "1-(438)-533-PRET (7738)"),
        ("Courriel :", "info@capitalnorvex.com"),
        ("Représentant :", "_______________________________"),
        ("Emprunteur (dénomination légale) :", "_______________________________"),
        ("NEQ :", "_______________________________"),
        ("Adresse de l'Emprunteur :", "_______________________________"),
        ("Garant(s) :", "_______________________________"),
    ])
    story += section_bar("2.  DESCRIPTION DU PROJET DE CONSTRUCTION")
    story += two_col_fields([
        ("Adresse du projet :", "_______________________________"),
        ("Municipalité / MRC :", "_______________________________"),
        ("Type de développement :", "Ex. : Condos, plex, commercial…"),
        ("Nombre d'unités :", "_______________________________"),
        ("Superficie totale :", "_______________________________"),
        ("Zonage applicable :", "_______________________________"),
        ("Entrepreneur général :", "_______________________________"),
        ("Architecte / Ingénieur :", "_______________________________"),
        ("Date de début prévue :", "_______________________________"),
        ("Durée des travaux :", "_______  mois"),
    ])
    story += section_bar("3.  CONDITIONS FINANCIÈRES")
    story.append(cond_table([
        ["Paramètre", "Valeur", "Remarques"],
        ["Montant autorisé (max.)", "$  _____________________ CAD", "Sous réserve des conditions"],
        ["Durée initiale", "_______ mois", "Prorogation à la discrétion du Prêteur"],
        ["Taux d'intérêt annuel", "_____ % (fixe)", "Calculé quotidiennement"],
        ["Frais d'ouverture (dossier)", "3 % à 3,5 % du montant", "Payables à la première avance"],
        ["Frais de renouvellement", "_____ %", "Le cas échéant"],
        ["Frais d'analyse (terme dépassé)", "1 % du capital", "Si prolongation au-delà de l'échéance (renégociable au cas par cas)"],
        ["Pénalité de remboursement", "Min. 3 mois d'intérêts", "En tout temps"],
        ["LTV maximum (cible)", "_____ %", "Sur valeur approuvée — flexibilité avec collatéraux"],
        ["LTC maximum (cible)", "_____ %", "Sur coût total approuvé — flexibilité avec collatéraux"],
        ["Retenue de chantier (holdback)", "5 % par déboursé", "Libérée 35 jours après achèvement substantiel"],
    ], [2.5*inch, 2.0*inch, 1.5*inch]))
    story.append(Spacer(1,6))
    story += section_bar("4.  MODALITÉS DE DÉBOURSÉS")
    story.append(body("Les fonds seront avancés progressivement sur base mensuelle selon l'avancement des Travaux, validé par l'inspecteur mandaté par Capital Norvex. Chaque demande doit comprendre :"))
    for t in ["Rapport d'inspection indépendant approuvé","État des coûts à date (CAC) certifié","Quittances partielles et finales des sous-traitants","Certificat professionnel de l'architecte ou ingénieur"]:
        story.append(bullet(t))
    story += section_bar("5.  GARANTIES REQUISES")
    story.append(cond_table([
        ["Garantie", "Rang / Détails"],
        ["Hypothèque immobilière", "1er rang sur l'immeuble et améliorations"],
        ["Cession de loyers", "Totale et immédiate"],
        ["Cautionnement personnel", "Solidaire, irrévocable et illimité"],
        ["Assurance chantier (tous risques)", "Montant = valeur du projet + 10 %"],
        ["Assurance responsabilité civile", "Minimum 5 000 000 $"],
    ], [2.8*inch, 3.2*inch]))
    story.append(Spacer(1,6))
    story += section_bar("6.  CONDITIONS PRÉALABLES AU PREMIER DÉBOURSÉ")
    for t in ["Documents constitutifs et résolutions autorisant l'emprunt",
              "Preuve de mise de fonds propres injectée",
              "Budget final détaillé et calendrier des Travaux approuvés",
              "Plans et devis signés et scellés par les professionnels",
              "Contrat d'entrepreneur général approuvé par Capital Norvex",
              "Permis de construction valides et en vigueur",
              "Rapport d'évaluation indépendant approuvé",
              "Rapport environnemental Phase I (Phase II si requis)",
              "Publication de l'hypothèque de premier rang",
              "Opinion juridique complète acceptée par Capital Norvex"]:
        story.append(bullet(t))
    story.append(Spacer(1,4))
    story += section_bar("7.  TOLÉRANCE ZÉRO — TAXES ET HYPOTHÈQUES LÉGALES")
    story.append(body("L'Emprunteur s'engage à régler ou faire radier toute hypothèque légale de la construction (art. 2724 et 2726 C.c.Q.) immédiatement, et au plus tard dans les sept (7) jours d'un avis du Prêteur. Tout retard de paiement de taxes foncières, taxes scolaires, charges municipales, primes d'assurance ou autres obligations courantes doit être régularisé dans les sept (7) jours d'un avis du Prêteur. À défaut, un Événement de Défaut sera automatiquement déclaré."))

    story += section_bar("8.  REPRÉSENTATION DE CAPITAL NORVEX INC.")
    story.append(body("Pour Capital Norvex Inc., la convention de prêt et l'acte d'hypothèque seront signés par un mandataire désigné, dûment autorisé en vertu d'une résolution corporative adoptée par l'actionnaire unique et présidente, Madame Suzanne Breton, dont copie certifiée conforme sera annexée au dossier."))

    story += section_bar("9.  INDISSOCIABILITÉ — CONVENTION DE PRÊT ET HYPOTHÈQUE")
    story.append(body("La convention de prêt et l'acte d'hypothèque conclu entre les Parties forment un ensemble contractuel INDISSOCIABLE. Tout manquement aux termes de la convention de prêt constitue automatiquement un Événement de Défaut au sens de l'acte d'hypothèque, et inversement. En cas de divergence ou d'ambiguïté, l'interprétation la plus favorable au Prêteur prévaudra."))

    story += section_bar("10.  VALIDITÉ ET CONDITIONS GÉNÉRALES")
    story += alert_box("La présente lettre d'engagement est valide pour une période de 30 jours suivant la date d'émission. Capital Norvex se réserve le droit de réviser les conditions ou de retirer l'offre sans préavis au-delà de ce délai.")
    for t in ["Ne constitue pas un engagement irrévocable avant la signature de la convention de prêt.",
              "Capital Norvex peut exiger tout document, garantie ou information additionnelle.",
              "Toute modification doit être confirmée par écrit par Capital Norvex.",
              "Les ratios LTV/LTC sont des cibles, ajustables au cas par cas avec collatéraux acceptables (jusqu'à 95 % LTV)."]:
        story.append(bullet(t))

def build_terrain(story):
    story += section_bar("1.  IDENTIFICATION DES PARTIES")
    story += two_col_fields([
        ("Prêteur :", "Capital Norvex Inc."),
        ("Adresse du Prêteur :", "2705-1000 André-Prévost, Île-des-Sœurs (Verdun), Montréal, QC H3E 0G2"),
        ("Téléphone :", "1-(438)-533-PRET (7738)"),
        ("Courriel :", "info@capitalnorvex.com"),
        ("Représentant :", "_______________________________"),
        ("Emprunteur (dénomination légale) :", "_______________________________"),
        ("NEQ :", "_______________________________"),
        ("Adresse de l'Emprunteur :", "_______________________________"),
        ("Garant(s) :", "_______________________________"),
    ])
    story += section_bar("2.  DESCRIPTION DU TERRAIN")
    story += two_col_fields([
        ("Adresse / localisation :", "_______________________________"),
        ("Municipalité / MRC :", "_______________________________"),
        ("Superficie :", "_______________________________"),
        ("Zonage actuel :", "_______________________________"),
        ("Numéro de lot cadastral :", "_______________________________"),
        ("Usage projeté :", "_______________________________"),
        ("Valeur d'évaluation indépendante :", "$  ______________________ CAD"),
        ("Prix d'acquisition / valeur marchande :", "$  ______________________ CAD"),
        ("Statut du terrain :", "_______________________________"),
        ("Stratégie de sortie prévue :", "_______________________________"),
    ])
    story += section_bar("3.  CONDITIONS FINANCIÈRES")
    story.append(cond_table([
        ["Paramètre", "Valeur", "Remarques"],
        ["Montant autorisé (max.)", "$  _____________________ CAD", "Sous réserve des conditions"],
        ["Durée initiale", "_______ mois", "Prorogation à la discrétion du Prêteur"],
        ["Taux d'intérêt annuel", "_____ % (fixe)", "Calculé mensuellement"],
        ["Frais d'ouverture (dossier)", "3 % à 3,5 % du montant", "Payables à la signature"],
        ["Frais d'analyse (terme dépassé)", "1 % du capital", "Si prolongation au-delà de l'échéance (renégociable)"],
        ["Pénalité de remboursement", "Min. 3 mois d'intérêts", "En tout temps"],
        ["LTV maximum (cible — sur valeur terrain)", "_____ %", "Flexibilité avec collatéraux"],
        ["Mise de fonds minimale (cible)", "_____ %", "Fonds propres vérifiés"],
    ], [2.5*inch, 2.0*inch, 1.5*inch]))
    story.append(Spacer(1,4))
    story += section_bar("4.  GARANTIES REQUISES")
    story.append(cond_table([
        ["Garantie", "Rang / Détails"],
        ["Hypothèque immobilière sur le terrain", "1er rang exclusif"],
        ["Cautionnement personnel", "Solidaire, irrévocable et illimité"],
        ["Cession de toute promesse de vente", "En faveur de Capital Norvex"],
        ["Rapport environnemental Phase I", "Obligatoire avant tout déboursé"],
    ], [2.8*inch, 3.2*inch]))
    story.append(Spacer(1,6))
    story += section_bar("5.  STRATÉGIE DE SORTIE")
    story.append(body("L'Emprunteur doit démontrer un plan de remboursement crédible :"))
    for t in ["Construction avec transition vers un prêt construction",
              "Vente du terrain à un développeur identifié",
              "Refinancement avec institution financière",
              "Autre stratégie approuvée par Capital Norvex"]:
        story.append(bullet(t))
    story.append(Spacer(1,4))
    story += section_bar("6.  CONDITIONS PRÉALABLES AU DÉBOURSÉ")
    for t in ["Documents constitutifs et résolutions autorisant l'emprunt",
              "Rapport d'évaluation indépendant approuvé par Capital Norvex",
              "Rapport environnemental Phase I (Phase II si requis)",
              "Preuve de mise de fonds propres injectée",
              "Confirmation de zonage de la municipalité",
              "Publication de l'hypothèque de premier rang",
              "Cautionnements personnels signés",
              "Opinion juridique complète acceptée par Capital Norvex"]:
        story.append(bullet(t))
    story.append(Spacer(1,4))
    story += section_bar("7.  TOLÉRANCE ZÉRO — TAXES ET CHARGES")
    story.append(body("L'Emprunteur s'engage à payer ponctuellement toutes les taxes foncières, taxes scolaires, charges municipales, primes d'assurance et autres obligations courantes affectant le Terrain. Tout retard doit être régularisé dans les sept (7) jours d'un avis du Prêteur. À défaut, un Événement de Défaut sera automatiquement déclaré."))

    story += section_bar("8.  REPRÉSENTATION DE CAPITAL NORVEX INC.")
    story.append(body("Pour Capital Norvex Inc., la convention de prêt et l'acte d'hypothèque seront signés par un mandataire désigné, dûment autorisé en vertu d'une résolution corporative adoptée par l'actionnaire unique et présidente, Madame Suzanne Breton, dont copie certifiée conforme sera annexée au dossier."))

    story += section_bar("9.  INDISSOCIABILITÉ — CONVENTION DE PRÊT ET HYPOTHÈQUE")
    story.append(body("La convention de prêt et l'acte d'hypothèque conclu entre les Parties forment un ensemble contractuel INDISSOCIABLE. Tout manquement aux termes de la convention de prêt constitue automatiquement un Événement de Défaut au sens de l'acte d'hypothèque, et inversement. En cas de divergence ou d'ambiguïté, l'interprétation la plus favorable au Prêteur prévaudra."))

    story += section_bar("10.  VALIDITÉ ET CONDITIONS GÉNÉRALES")
    story += alert_box("La présente lettre d'engagement est valide pour une période de 30 jours suivant la date d'émission. Capital Norvex se réserve le droit de réviser les conditions ou de retirer l'offre sans préavis.")
    for t in ["Ne constitue pas un engagement irrévocable avant la signature de la convention de prêt.",
              "Le financement terrain est accordé exclusivement à des fins commerciales.",
              "Toute modification doit être confirmée par écrit par Capital Norvex.",
              "Les ratios LTV sont des cibles, ajustables au cas par cas avec collatéraux acceptables."]:
        story.append(bullet(t))

def build_acquisition(story):
    story += section_bar("1.  IDENTIFICATION DES PARTIES")
    story += two_col_fields([
        ("Prêteur :", "Capital Norvex Inc."),
        ("Adresse du Prêteur :", "2705-1000 André-Prévost, Île-des-Sœurs (Verdun), Montréal, QC H3E 0G2"),
        ("Téléphone :", "1-(438)-533-PRET (7738)"),
        ("Courriel :", "info@capitalnorvex.com"),
        ("Représentant :", "_______________________________"),
        ("Emprunteur (dénomination légale) :", "_______________________________"),
        ("NEQ :", "_______________________________"),
        ("Adresse de l'Emprunteur :", "_______________________________"),
        ("Garant(s) :", "_______________________________"),
    ])
    story += section_bar("2.  DESCRIPTION DE L'IMMEUBLE")
    story += two_col_fields([
        ("Adresse de l'immeuble :", "_______________________________"),
        ("Municipalité / MRC :", "_______________________________"),
        ("Type de propriété :", "_______________________________"),
        ("Année de construction :", "_______________________________"),
        ("Nombre d'unités / locaux :", "_______________________________"),
        ("Taux d'occupation actuel :", "_____ %"),
        ("Revenus bruts annuels :", "$  ______________________ CAD"),
        ("Prix d'achat / Valeur marchande :", "$  ______________________ CAD"),
        ("Valeur d'évaluation indépendante :", "$  ______________________ CAD"),
        ("Mise de fonds prévue :", "$  ______________________ CAD"),
    ])
    story += section_bar("3.  CONDITIONS FINANCIÈRES")
    story.append(cond_table([
        ["Paramètre", "Valeur", "Remarques"],
        ["Montant autorisé (max.)", "$  _____________________ CAD", "Sous réserve des conditions"],
        ["Durée initiale", "_______ mois", "Prorogation à la discrétion du Prêteur"],
        ["Taux d'intérêt annuel", "_____ % (fixe)", "Calculé mensuellement"],
        ["Frais d'ouverture (dossier)", "3 % à 3,5 % du montant", "Payables à la signature"],
        ["Frais d'analyse (terme dépassé)", "1 % du capital", "Si prolongation au-delà de l'échéance (renégociable)"],
        ["Pénalité de remboursement", "Min. 3 mois d'intérêts", "En tout temps"],
        ["LTV maximum (cible)", "_____ %", "Sur valeur AACI — flexibilité avec collatéraux"],
        ["DSCR minimum (cible)", "_____ x", "Ratio de couverture de la dette"],
        ["Mise de fonds minimale (cible)", "_____ %", "Fonds propres vérifiés"],
    ], [2.6*inch, 2.0*inch, 1.4*inch]))
    story.append(Spacer(1,6))
    story += section_bar("4.  GARANTIES REQUISES")
    story.append(cond_table([
        ["Garantie", "Rang / Détails"],
        ["Hypothèque immobilière sur l'immeuble", "1er rang exclusif"],
        ["Cession de loyers (totale et immédiate)", "En faveur de Capital Norvex"],
        ["Cautionnement personnel", "Solidaire, irrévocable et illimité"],
        ["Cession des baux existants", "Tous les baux en vigueur"],
        ["Assurance bien immeuble", "Valeur de remplacement"],
        ["Assurance responsabilité civile", "Minimum 2 000 000 $"],
    ], [2.8*inch, 3.2*inch]))
    story.append(Spacer(1,6))
    story += section_bar("5.  ANALYSE DE REVENUS ET STRATÉGIE DE SORTIE")
    story.append(body("Capital Norvex analysera la viabilité sur la base des revenus réels documentés. L'Emprunteur fournit :"))
    for t in ["Rôles de baux en vigueur, signés et à jour",
              "Historique de revenus des 24 derniers mois",
              "Liste des dépenses d'exploitation détaillées",
              "Rapport de dépenses en capital (capex) — 3 dernières années"]:
        story.append(bullet(t))
    story.append(Spacer(1,4))
    story += section_bar("6.  CONDITIONS PRÉALABLES AU DÉBOURSÉ")
    for t in ["Documents constitutifs et résolutions autorisant l'emprunt",
              "Rapport d'évaluation indépendant approuvé par Capital Norvex",
              "Rapport d'inspection du bâtiment — ingénieur certifié",
              "Rapport environnemental Phase I (Phase II si requis)",
              "Rôles de baux certifiés et historique de revenus",
              "États financiers vérifiés des 2 dernières années",
              "Preuve de mise de fonds propres injectée",
              "Publication de l'hypothèque de premier rang",
              "Cautionnements personnels signés",
              "Opinion juridique complète acceptée par Capital Norvex"]:
        story.append(bullet(t))
    story.append(Spacer(1,4))
    story += section_bar("7.  TOLÉRANCE ZÉRO — TAXES ET CHARGES")
    story.append(body("L'Emprunteur s'engage à payer ponctuellement toutes les taxes foncières, taxes scolaires, charges municipales, primes d'assurance et autres obligations courantes affectant l'Immeuble. Tout retard doit être régularisé dans les sept (7) jours d'un avis du Prêteur. À défaut, un Événement de Défaut sera automatiquement déclaré."))

    story += section_bar("8.  REPRÉSENTATION DE CAPITAL NORVEX INC.")
    story.append(body("Pour Capital Norvex Inc., la convention de prêt et l'acte d'hypothèque seront signés par un mandataire désigné, dûment autorisé en vertu d'une résolution corporative adoptée par l'actionnaire unique et présidente, Madame Suzanne Breton, dont copie certifiée conforme sera annexée au dossier."))

    story += section_bar("9.  INDISSOCIABILITÉ — CONVENTION DE PRÊT ET HYPOTHÈQUE")
    story.append(body("La convention de prêt et l'acte d'hypothèque conclu entre les Parties forment un ensemble contractuel INDISSOCIABLE. Tout manquement aux termes de la convention de prêt constitue automatiquement un Événement de Défaut au sens de l'acte d'hypothèque, et inversement. En cas de divergence ou d'ambiguïté, l'interprétation la plus favorable au Prêteur prévaudra."))

    story += section_bar("10.  VALIDITÉ ET CONDITIONS GÉNÉRALES")
    story += alert_box("La présente lettre d'engagement est valide pour une période de 30 jours suivant la date d'émission. Capital Norvex se réserve le droit de réviser les conditions ou de retirer l'offre sans préavis.")
    for t in ["Ne constitue pas un engagement irrévocable avant la signature de la convention de prêt.",
              "Les revenus retenus sont ceux vérifiés par Capital Norvex, non les projections.",
              "Toute modification doit être confirmée par écrit par Capital Norvex.",
              "Les ratios LTV sont des cibles, ajustables au cas par cas avec collatéraux acceptables."]:
        story.append(bullet(t))

# ── SIGNATURES ───────────────────────────────────────────────────────────────
def build_refinancement(story):
    story += section_bar("1.  IDENTIFICATION DES PARTIES")
    story += two_col_fields([
        ("Prêteur :", "Capital Norvex Inc."),
        ("Adresse du Prêteur :", "2705-1000 André-Prévost, Île-des-Sœurs (Verdun), Montréal, QC H3E 0G2"),
        ("Téléphone :", "1-(438)-533-PRET (7738)"),
        ("Courriel :", "info@capitalnorvex.com"),
        ("Emprunteur :", "_______________________________________________________"),
        ("Représenté par :", "_______________________________________________________"),
        ("Adresse de l'Emprunteur :", "_______________________________________________________"),
        ("Numéro d'entreprise (NEQ) :", "________________________________"),
    ])

    story += section_bar("2.  DESCRIPTION DE L'IMMEUBLE À REFINANCER")
    story += two_col_fields([
        ("Adresse de l'Immeuble :", "_______________________________________________________"),
        ("Type d'immeuble :", "Multilogements / Commercial / Mixte / Autre : ___________"),
        ("Année de construction :", "________________________________"),
        ("Lot(s) cadastraux :", "_______________________________________________________"),
        ("Valeur marchande (AACI) :", "________________________________"),
        ("Revenus locatifs bruts annuels :", "________________________________"),
        ("Revenus nets stabilisés :", "________________________________"),
        ("Taux d'occupation actuel :", "________________________________"),
    ])

    story += section_bar("3.  STRATÉGIE DE SORTIE — OBLIGATOIRE")
    story += alert_box("Le refinancement n'est consenti qu'avec une stratégie de sortie claire et documentée. Aucun cash-out pur sans plan de remboursement n'est autorisé.")
    story.append(body("L'Emprunteur s'engage à fournir l'une des stratégies suivantes :"))
    for t in ["Vente de l'Immeuble — promesse d'achat ou mandat de vente",
              "Refinancement bancaire confirmé — lettre d'engagement ou confirmation préliminaire",
              "Autre stratégie documentée acceptable au Prêteur"]:
        story.append(bullet(t))

    story += section_bar("4.  CONDITIONS FINANCIÈRES")
    story.append(cond_table([
        ["Élément", "Condition", "Notes"],
        ["Montant maximum approuvé", "____________ $ CAD", "Sujet aux conditions"],
        ["Durée du Prêt", "12 mois renouvelable", "Sous réserve d'approbation"],
        ["Taux d'intérêt", "_____ % (fixe)", "Calculé mensuellement"],
        ["Frais d'ouverture (dossier)", "3 % à 3,5 % du montant", "À la signature"],
        ["Frais d'analyse (terme dépassé)", "1 % du capital", "Si prolongation au-delà de l'échéance (renégociable)"],
        ["Pénalité de remboursement", "Min. 3 mois d'intérêts", "En tout temps"],
        ["LTV maximum (cible)", "70 %", "Sur valeur AACI — flexibilité avec collatéraux"],
        ["DCR minimum (cible)", "1,20x", "Sur revenus nets stabilisés"],
        ["Équité cash minimum (cible)", "30 %", "De la valeur de l'Immeuble"],
    ], [2.5*inch, 2.0*inch, 1.5*inch]))
    story.append(Spacer(1,6))

    story += section_bar("5.  AFFECTATION DES FONDS")
    story += alert_box("AUCUN cash-out pur sans plan de remboursement documenté n'est autorisé. Toute affectation des fonds doit faire l'objet d'une justification écrite acceptable au Prêteur.")
    story.append(body("Les fonds du Prêt sont affectés exclusivement à :"))
    for t in ["Remboursement intégral de l'hypothèque existante (Ancien Prêteur)",
              "Frais de dossier, frais notariaux, taxes et frais de publication",
              "Liquidités additionnelles à usage spécifique documenté (amélioration locative, capex, etc.)"]:
        story.append(bullet(t))

    story += section_bar("6.  GARANTIES REQUISES")
    story.append(cond_table([
        ["Garantie", "Rang / Détails"],
        ["Hypothèque immobilière", "1er rang sur l'Immeuble (après radiation Ancien Prêteur)"],
        ["Cession de loyers", "Totale et immédiate"],
        ["Cautionnement personnel", "Solidaire, irrévocable et illimité"],
        ["Quittance Ancien Prêteur", "OBLIGATOIRE — avant ou simultanément au déboursement"],
        ["Mainlevée hypothèque ancienne", "OBLIGATOIRE — dûment publiée"],
    ], [2.8*inch, 3.2*inch]))
    story.append(Spacer(1,6))

    story += section_bar("7.  CONDITIONS PRÉALABLES AU DÉBOURSEMENT")
    for t in ["Documents constitutifs et résolutions autorisant l'emprunt",
              "Évaluation agréée AACI datée de moins de 6 mois",
              "Lettre de quittance / décharge de l'Ancien Prêteur indiquant le solde exact",
              "Stratégie de sortie documentée acceptable au Prêteur",
              "États financiers et rapport d'exploitation de l'Immeuble",
              "Rôles de baux certifiés et historique de revenus",
              "Étude environnementale Phase I (le cas échéant)",
              "Polices d'assurance avec Capital Norvex désigné bénéficiaire",
              "Publication de l'hypothèque de premier rang (après radiation)",
              "Cautionnements personnels signés"]:
        story.append(bullet(t))
    story.append(Spacer(1,4))

    story += section_bar("8.  TOLÉRANCE ZÉRO — TAXES ET CHARGES")
    story.append(body("L'Emprunteur s'engage à payer ponctuellement toutes les taxes foncières, taxes scolaires, charges municipales, primes d'assurance et autres obligations courantes affectant l'Immeuble. Tout retard doit être régularisé dans les sept (7) jours d'un avis du Prêteur. À défaut, un Événement de Défaut sera automatiquement déclaré."))

    story += section_bar("9.  REPRÉSENTATION DE CAPITAL NORVEX INC.")
    story.append(body("Pour Capital Norvex Inc., la convention de prêt et l'acte d'hypothèque seront signés par un mandataire désigné, dûment autorisé en vertu d'une résolution corporative adoptée par l'actionnaire unique et présidente, Madame Suzanne Breton, dont copie certifiée conforme sera annexée au dossier."))

    story += section_bar("10.  INDISSOCIABILITÉ — CONVENTION DE PRÊT ET HYPOTHÈQUE")
    story.append(body("La convention de prêt et l'acte d'hypothèque conclu entre les Parties forment un ensemble contractuel INDISSOCIABLE. Tout manquement aux termes de la convention de prêt constitue automatiquement un Événement de Défaut au sens de l'acte d'hypothèque, et inversement. En cas de divergence ou d'ambiguïté, l'interprétation la plus favorable au Prêteur prévaudra."))

    story += section_bar("11.  VALIDITÉ ET CONDITIONS GÉNÉRALES")
    story += alert_box("La présente lettre d'engagement est valide pour une période de 30 jours suivant la date d'émission. Capital Norvex se réserve le droit de réviser les conditions ou de retirer l'offre sans préavis.")
    for t in ["Ne constitue pas un engagement irrévocable avant la signature de la convention de prêt.",
              "Le refinancement est subordonné à la radiation préalable de l'hypothèque de l'Ancien Prêteur.",
              "Les ratios LTV/DCR sont des cibles, ajustables au cas par cas avec collatéraux acceptables (jusqu'à 95 % LTV).",
              "Toute modification doit être confirmée par écrit par Capital Norvex."]:
        story.append(bullet(t))


def build_norvex_tools(story, has_track):
    story.append(Spacer(1, 8))
    story += section_bar("OUTILS NUMÉRIQUES CAPITAL NORVEX")
    story.append(Spacer(1, 4))
    story.append(body(
        "Dès l'autorisation du financement, l'Emprunteur bénéficie des outils technologiques "
        "propriétaires de Capital Norvex :"))
    story.append(bullet(
        "<b>Portail Emprunteur (PWA — Progressive Web Application)</b> : application Web sécurisée "
        "accessible <b>24 h/24, 7 jours/7</b> depuis tout appareil. Permet de consulter en temps réel "
        "le solde du Prêt, l'échéancier des paiements, l'historique des transactions, le statut "
        "des déboursés et tout document pertinent au dossier."))
    if has_track:
        story.append(bullet(
            "<b>Norvex Track™</b> : module de gestion et de traçabilité des déboursés progressifs, "
            "accessible <b>24 h/24, 7 jours/7</b>. Toute demande de déboursé est soumise et "
            "documentée via Norvex Track™ (rapports d'inspection, factures, photos d'avancement, "
            "certificats professionnels, quittances). Capital Norvex conserve le contrôle absolu, "
            "exclusif et discrétionnaire de l'autorisation des déboursés."))
    story.append(body(
        "Ces outils constituent un engagement de transparence de Capital Norvex envers l'Emprunteur "
        "et ne se substituent pas aux communications officielles écrites prévues à la Convention "
        "de prêt définitive."))
    story.append(Spacer(1, 6))


def build_signatures(story):
    story.append(PageBreak())
    tbl = Table([[Paragraph("ACCEPTATION ET SIGNATURES", ST["section"])]],
                colWidths=[PAGE_W - 2*MARGIN])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), DARK),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LINEBELOW",     (0,0),(-1,-1), 2, GOLD),
    ]))
    story.append(Spacer(1,6))
    story.append(tbl)
    story.append(Spacer(1,8))
    story.append(body(
        "Les soussignés déclarent avoir lu, compris et accepté l'ensemble des conditions "
        "de la présente lettre d'engagement et s'engagent à fournir tous les documents "
        "requis en vue de la conclusion de la convention de prêt définitive avec Capital Norvex Inc."))
    story.append(Spacer(1,12))
    story += sign_block("PRÊTEUR — CAPITAL NORVEX INC.", [
        ("Représentant autorisé :", "________________________________"),
        ("Titre :", "________________________________"),
    ])
    story += sign_block("EMPRUNTEUR", [
        ("Dénomination sociale :", "________________________________"),
        ("Représentant autorisé :", "________________________________"),
        ("Titre :", "________________________________"),
    ])
    story += sign_block("GARANT 1", [("Nom complet :", "________________________________")])
    story += sign_block("GARANT 2 (le cas échéant)", [("Nom complet :", "________________________________")])

# ── GÉNÉRATION ────────────────────────────────────────────────────────────────
configs = [
    {
        "filename": "/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres/CapitalNorvex_LettrEngagement_Construction.pdf",
        "product_name": "PRÊT DE CONSTRUCTION",
        "product_desc": "Financement privé institutionnel — Travaux neufs et rénovations majeures — Québec & Ontario",
        "product_tag": "PRÊT CONSTRUCTION",
        "builder": build_construction,
        "has_track": True,
    },
    {
        "filename": "/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres/CapitalNorvex_LettrEngagement_Terrain.pdf",
        "product_name": "PRÊT TERRAIN",
        "product_desc": "Financement privé institutionnel — Acquisition et portage de terrain — Québec & Ontario",
        "product_tag": "PRÊT TERRAIN",
        "builder": build_terrain,
        "has_track": False,
    },
    {
        "filename": "/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres/CapitalNorvex_LettrEngagement_Acquisition.pdf",
        "product_name": "PRÊT ACQUISITION D'IMMEUBLE",
        "product_desc": "Financement privé institutionnel — Acquisition d'immeubles à revenus — Québec & Ontario",
        "product_tag": "PRÊT ACQUISITION",
        "builder": build_acquisition,
        "has_track": False,
    },
    {
        "filename": "/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres/CapitalNorvex_LettrEngagement_Refinancement.pdf",
        "product_name": "PRÊT REFINANCEMENT",
        "product_desc": "Financement privé institutionnel — Refinancement immobilier — Québec & Ontario",
        "product_tag": "PRÊT REFINANCEMENT",
        "builder": build_refinancement,
        "has_track": False,
    },
]

for cfg in configs:
    doc = SimpleDocTemplate(
        cfg["filename"], pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 40, bottomMargin=MARGIN + 24,
        title=f"Lettre d'engagement — {cfg['product_name']} — Capital Norvex",
        author="Capital Norvex Inc.",
    )
    on_page = make_on_page(cfg["product_tag"])
    story = []
    build_cover(story, cfg["product_name"], cfg["product_desc"])
    cfg["builder"](story)
    build_norvex_tools(story, cfg["has_track"])
    build_signatures(story)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"✅  {cfg['filename']}")

print("\n🎉 4 lettres d'engagement avec logo générées (Construction, Terrain, Acquisition, Refinancement) !")
