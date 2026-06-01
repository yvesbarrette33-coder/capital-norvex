from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import Flowable, Image as RLImage
from reportlab.lib import colors

EMBLEM_PATH = '/Users/yvesbarrette/Desktop/capitalnorvex-site/CapitalNorvex_Scripts/logos/emblem_header.png'
COVER_PATH  = '/Users/yvesbarrette/Desktop/capitalnorvex-site/CapitalNorvex_Scripts/logos/logo_cover.png'


# ── Palette Capital Norvex ──────────────────────────────────────────────────
DARK     = HexColor("#0a0d13")   # fond sombre
GOLD     = HexColor("#C9A84C")   # or principal
GOLD2    = HexColor("#b8975a")   # or secondaire
CREAM    = HexColor("#f5f0e8")   # crème
GREY_LT  = HexColor("#d4c9b0")   # gris doré léger
GREY_MED = HexColor("#8a7d5f")   # gris doré moyen
WHITE    = HexColor("#ffffff")
DARK_MED = HexColor("#1a2030")   # fond section légère

# ── Page setup ──────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = letter
MARGIN = 0.75 * inch

# ── Ligne dorée décorative ───────────────────────────────────────────────────
class GoldLine(Flowable):
    def __init__(self, width=None, thickness=1.5, color=None):
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

# ── En-tête / pied de page ───────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    w, h = letter

    # Bande dorée en haut
    canvas.setFillColor(DARK)
    canvas.rect(0, h - 52, w, 52, fill=1, stroke=0)

    canvas.setFillColor(GOLD)
    canvas.rect(0, h - 55, w, 3, fill=1, stroke=0)

    # Logo emblème dans le header
    emb_w, emb_h = 38, 42
    logo_x = MARGIN
    logo_y = h - 47  # uniformisé : top du logo à 5 px du sommet de la page
    canvas.drawImage(EMBLEM_PATH, logo_x, logo_y,
                     width=emb_w, height=emb_h,
                     preserveAspectRatio=True, mask="auto")
    # Texte à droite du logo
    text_x = logo_x + emb_w + 8
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(text_x, h - 30, "CAPITAL NORVEX")
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(text_x, h - 43, "Financement Privé Institutionnel  |  Québec & Ontario")
    # Tag convention (droite)
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawRightString(w - MARGIN, h - 28, "CONVENTION DE PRÊT")
    canvas.setFillColor(GREY_LT)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(w - MARGIN, h - 42, "DE CONSTRUCTION")
    # Page
    canvas.setFillColor(GREY_LT)
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(w - MARGIN, h - 52, f"p. {doc.page}")

    # Pied de page
    canvas.setFillColor(DARK)
    canvas.rect(0, 0, w, 50, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, 50, w, 1.5, fill=1, stroke=0)

    # Ligne du haut — confidentialité (centrée, gold pour la marque)
    canvas.setFillColor(GOLD2)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawCentredString(w/2, 32,
        "CAPITAL NORVEX  ·  Confidentiel – Usage exclusif des parties signataires")
    # Ligne du bas — adresse complète (centrée, gris clair)
    canvas.setFillColor(GREY_LT)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(w/2, 14,
        "2705-1000 André-Prévost  ·  Île-des-Sœurs (Verdun)  ·  Montréal, QC H3E 0G2   |   1-(438)-533-PRET (7738)   |   info@capitalnorvex.com   |   capitalnorvex.com")

    canvas.restoreState()

# ── Styles ───────────────────────────────────────────────────────────────────
def build_styles():
    styles = getSampleStyleSheet()

    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    cover_title = S("CoverTitle",
        fontName="Helvetica-Bold", fontSize=26, textColor=GOLD,
        alignment=TA_CENTER, spaceAfter=6, leading=32)

    cover_sub = S("CoverSub",
        fontName="Helvetica", fontSize=12, textColor=CREAM,
        alignment=TA_CENTER, spaceAfter=4, leading=18)

    cover_label = S("CoverLabel",
        fontName="Helvetica-Bold", fontSize=9, textColor=GOLD,
        alignment=TA_CENTER, spaceAfter=2)

    cover_value = S("CoverValue",
        fontName="Helvetica", fontSize=10, textColor=CREAM,
        alignment=TA_CENTER, spaceAfter=10)

    section_head = S("SectionHead",
        fontName="Helvetica-Bold", fontSize=11, textColor=GOLD,
        spaceBefore=14, spaceAfter=4, leading=16,
        borderPadding=(4, 0, 4, 8))

    article_num = S("ArticleNum",
        fontName="Helvetica-Bold", fontSize=9.5, textColor=DARK,
        spaceBefore=8, spaceAfter=2, leading=14,
        backColor=GREY_LT, borderPadding=(3, 6, 3, 6))

    body = S("Body",
        fontName="Helvetica", fontSize=9, textColor=DARK,
        alignment=TA_JUSTIFY, spaceAfter=4, leading=14,
        leftIndent=0)

    bullet_item = S("BulletItem",
        fontName="Helvetica", fontSize=8.8, textColor=DARK,
        spaceAfter=2, leading=13, leftIndent=14, bulletIndent=4,
        bulletFontName="Helvetica", bulletFontSize=9)

    field_label = S("FieldLabel",
        fontName="Helvetica-Bold", fontSize=8.5, textColor=GREY_MED,
        spaceAfter=1)

    field_line = S("FieldLine",
        fontName="Helvetica", fontSize=9.5, textColor=DARK,
        spaceAfter=8, leading=16, borderWidth=0,
        borderPadding=(0, 0, 2, 0))

    note = S("Note",
        fontName="Helvetica-Oblique", fontSize=8, textColor=GREY_MED,
        alignment=TA_CENTER, spaceAfter=4)

    sign_label = S("SignLabel",
        fontName="Helvetica-Bold", fontSize=9, textColor=DARK,
        spaceAfter=2)

    sign_val = S("SignVal",
        fontName="Helvetica", fontSize=9, textColor=DARK,
        spaceAfter=6, leading=14)

    return dict(
        cover_title=cover_title, cover_sub=cover_sub,
        cover_label=cover_label, cover_value=cover_value,
        section_head=section_head, article_num=article_num,
        body=body, bullet_item=bullet_item,
        field_label=field_label, field_line=field_line,
        note=note, sign_label=sign_label, sign_val=sign_val,
    )

# ── Helpers ──────────────────────────────────────────────────────────────────
def section(title, st):
    items = [
        Spacer(1, 6),
        Table([[Paragraph(title, st["section_head"])]],
              colWidths=[PAGE_W - 2*MARGIN],
              style=TableStyle([
                  ("BACKGROUND", (0,0), (-1,-1), DARK),
                  ("LEFTPADDING", (0,0), (-1,-1), 10),
                  ("RIGHTPADDING", (0,0), (-1,-1), 10),
                  ("TOPPADDING", (0,0), (-1,-1), 5),
                  ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                  ("LINEBELOW", (0,0), (-1,-1), 2, GOLD),
              ])),
        Spacer(1, 4),
    ]
    return items

def art(num, title, st):
    return Paragraph(f"{num}  {title}", st["article_num"])

def body(text, st):
    return Paragraph(text, st["body"])

def bullets(items_list, st):
    return [Paragraph(f"• &nbsp; {t}", st["bullet_item"]) for t in items_list]

def field(label, placeholder, st):
    return [
        Paragraph(label, st["field_label"]),
        Paragraph(f"<u>{placeholder}</u>", st["field_line"]),
    ]

def gold_hr(w=None):
    return GoldLine(width=w, thickness=1.2)

# ── COUVERTURE ────────────────────────────────────────────────────────────────
def build_cover(story, st):
    story.append(Spacer(1, 0.7*inch))

    # Logo Capital Norvex centré sur la couverture
    img = RLImage(COVER_PATH, width=120, height=130)
    img.hAlign = "CENTER"
    story.append(img)
    story.append(Spacer(1, 16))

    # Bloc central sombre
    cover_data = [[
        Paragraph("CONVENTION DE PRÊT", st["cover_title"]),
    ]]
    tbl = Table(cover_data, colWidths=[PAGE_W - 2*MARGIN])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), DARK),
        ("TOPPADDING", (0,0), (-1,-1), 24),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LINEABOVE", (0,0), (-1,0), 3, GOLD),
        ("LINEBELOW", (0,-1), (-1,-1), 3, GOLD),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 10))

    story.append(Paragraph("DE CONSTRUCTION", ParagraphStyle(
        "CT2", fontName="Helvetica-Bold", fontSize=20,
        textColor=DARK, alignment=TA_CENTER, spaceAfter=4)))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Capital Norvex Inc.  —  Version Institutionnelle  —  Québec",
        st["cover_sub"]))
    story.append(Spacer(1, 24))

    # Tableau infos
    info = [
        ["EMPRUNTEUR",  "_________________________________"],
        ["PROJET",       "_________________________________"],
        ["MONTANT",      "_________________________________"],
        ["DURÉE",        "_________________________________"],
        ["DATE",         "_________________________________"],
        ["DOSSIER No.",  "_________________________________"],
    ]
    t = Table(info, colWidths=[1.6*inch, 3.8*inch], hAlign="CENTER")
    t.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME", (1,0), (1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("TEXTCOLOR", (0,0), (0,-1), GOLD),
        ("TEXTCOLOR", (1,0), (1,-1), DARK),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [CREAM, HexColor("#e8e0ce")]),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING", (0,0), (0,-1), 10),
        ("LEFTPADDING", (1,0), (1,-1), 10),
        ("LINEBELOW", (0,-1), (-1,-1), 1.5, GOLD),
    ]))
    story.append(t)

    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(
        "Capital structuré.  Ambition maîtrisée.",
        ParagraphStyle("slogan", fontName="Helvetica-Oblique", fontSize=10,
                       textColor=HexColor("#b8975a"), alignment=TA_CENTER, spaceAfter=8)))
    story.append(Paragraph(
        "CONFIDENTIEL — Réservé aux parties signataires et à leurs conseillers juridiques",
        st["note"]))
    story.append(PageBreak())

# ── CORPS DU DOCUMENT ─────────────────────────────────────────────────────────
def build_body(story, st):

    # ── 1. INTERPRÉTATION ────────────────────────────────────────────────────
    story += section("1.  INTERPRÉTATION ET DÉFINITIONS", st)
    story.append(art("1.1", "Interprétation", st))
    story.append(body(
        "Sauf indication contraire, les titres sont insérés pour la commodité des parties "
        "seulement et ne limitent pas la portée des dispositions. Le singulier inclut le pluriel "
        "et vice versa. Toute référence à une loi inclut ses modifications ultérieures. Les termes "
        "non définis ont leur sens usuel dans l'industrie du financement immobilier commercial.", st))
    story.append(Spacer(1,4))

    story.append(art("1.2", "Définitions", st))
    defs = [
        ("<b>« Accord »</b>", "La présente convention, ses annexes, amendements et tous documents accessoires."),
        ("<b>« Achèvement Substantiel »</b>", "Stade où au moins 97 % des coûts du Projet sont engagés, permettant l'utilisation normale de l'immeuble."),
        ("<b>« Budget »</b>", "Budget détaillé approuvé par Capital Norvex, incluant coûts directs, indirects, contingences, frais financiers et réserves."),
        ("<b>« Calendrier »</b>", "Échéancier des Travaux approuvé par Capital Norvex."),
        ("<b>« Déboursé »</b>", "Toute avance de fonds effectuée par le Prêteur."),
        ("<b>« Emprunteur »</b>", "La société emprunteuse identifiée aux présentes."),
        ("<b>« Garant »</b>", "Toute personne physique ou morale fournissant une garantie au Prêteur."),
        ("<b>« Hypothèque »</b>", "Hypothèque immobilière de premier rang publiée en faveur de Capital Norvex."),
        ("<b>« LTC »</b>", "Ratio prêt-coût (Loan-to-Cost)."),
        ("<b>« LTV »</b>", "Ratio prêt-valeur (Loan-to-Value)."),
        ("<b>« Norvex Track™ »</b>", "Module technologique propriétaire de Capital Norvex utilisé pour la soumission, la vérification, l'autorisation et la traçabilité des Déboursés progressifs, accessible 24 h/24, 7 jours/7."),
        ("<b>« Portail Emprunteur (PWA) »</b>", "Application Web progressive sécurisée mise à la disposition de l'Emprunteur par Capital Norvex, accessible 24 h/24, 7 jours/7, permettant la consultation en temps réel du dossier de l'Emprunteur (solde, échéancier, déboursés, documents)."),
        ("<b>« Prêteur »</b>", "CAPITAL NORVEX INC., agissant pour son compte et/ou pour celui de partenaires financiers."),
        ("<b>« Projet »</b>", "Développement immobilier décrit à l'Annexe A."),
        ("<b>« Score Norvex™ »</b>", "Système d'analyse propriétaire de Capital Norvex servant à l'évaluation et au suivi du dossier."),
        ("<b>« SPV »</b>", "Entité juridique dédiée à la détention du Projet."),
        ("<b>« Travaux »</b>", "Ensemble des travaux de construction visés par le Projet."),
    ]
    for term, defn in defs:
        story.append(Paragraph(
            f"{term} : {defn}", st["bullet_item"]))
    story.append(Spacer(1, 6))

    # ── 2. PARTIES ──────────────────────────────────────────────────────────
    story += section("2.  PARTIES", st)
    story.append(art("2.1", "Prêteur", st))
    story += field("Dénomination sociale :", "CAPITAL NORVEX INC.", st)
    story += field("Adresse :", "2705-1000 André-Prévost, Île-des-Sœurs (Verdun), Montréal, QC H3E 0G2", st)
    story += field("Téléphone :", "1-(438)-533-PRET (7738)", st)
    story += field("Courriel :", "info@capitalnorvex.com", st)
    story += field("Représentant autorisé :", "_________________________________________________", st)

    story.append(art("2.2", "Emprunteur", st))
    story += field("Dénomination sociale :", "_________________________________________________", st)
    story += field("Numéro d'entreprise (NEQ) :", "_________________", st)
    story += field("Adresse du siège social :", "_________________________________________________", st)
    story += field("Représentant autorisé :", "_________________________________________________", st)
    story += field("Titre :", "_________________________________________________", st)

    story.append(art("2.3", "Garants", st))
    story.append(body(
        "Les Garants ci-dessous sont tenus solidairement et indivisiblement "
        "avec l'Emprunteur pour toutes les obligations découlant de la présente Convention.", st))
    story += field("Garant 1 – Nom :", "_________________________________________________", st)
    story += field("Garant 2 – Nom (le cas échéant) :", "_________________________________________________", st)
    story.append(Spacer(1,6))

    # ── 3. OBJET ────────────────────────────────────────────────────────────
    story += section("3.  OBJET DU PRÊT", st)
    story.append(body(
        "Capital Norvex consent à l'Emprunteur un financement de construction destiné "
        "<b>exclusivement</b> à la réalisation du Projet décrit à l'Annexe A. "
        "Les fonds ne peuvent être utilisés à d'autres fins sans le consentement écrit "
        "préalable du Prêteur. Sont expressément interdits, sans autorisation écrite :", st))
    story += bullets([
        "Tout refinancement non autorisé d'obligations existantes",
        "Toute distribution aux actionnaires, associés ou membres",
        "Tout transfert vers d'autres projets ou entités",
    ], st)
    story.append(Spacer(1,6))

    # ── 4. MONTANT / DURÉE / INTÉRÊTS ───────────────────────────────────────
    story += section("4.  MONTANT, DURÉE ET CONDITIONS FINANCIÈRES", st)

    story.append(art("4.1", "Montant du prêt", st))
    story += field("Montant maximal autorisé :", "$  _____________________________ CAD", st)
    story.append(body(
        "Le Prêteur n'est pas tenu d'avancer la totalité du montant autorisé. "
        "Les déboursés sont effectués de manière discrétionnaire selon l'avancement "
        "des Travaux et la satisfaction de toutes les conditions prévues aux présentes.", st))

    story.append(art("4.2", "Durée", st))
    story += field("Durée initiale :", "_______  mois à compter de la date du premier déboursé", st)
    story.append(body(
        "Toute prolongation est à la discrétion exclusive du Prêteur et peut être "
        "assujettie à des frais additionnels.", st))

    story.append(art("4.3", "Taux d'intérêt", st))
    story += field("Taux annuel :", "_____ % par année  (calculé quotidiennement, capitalisé mensuellement)", st)
    story.append(body(
        "Les intérêts courent sur les seuls montants réellement déboursés. "
        "Les paiements d'intérêts sont exigibles le premier jour ouvrable de chaque mois.", st))

    story.append(art("4.4", "Frais", st))
    frais_data = [
        ["Type de frais", "Taux / Montant", "Exigibilité"],
        ["Frais d'ouverture de dossier", "3 % à 3,5 %", "À la signature"],
        ["Frais de renouvellement", "_____ %", "À chaque renouvellement"],
        ["Frais d'analyse (terme dépassé)", "1 % du capital", "Si prolongation au-delà de l'échéance"],
        ["Frais de sortie", "Min. 3 mois d'intérêts", "Au remboursement"],
        ["Frais juridiques (Prêteur)", "Au coût réel", "Sur demande"],
        ["Frais d'inspection / expertise", "Au coût réel", "À chaque déboursé"],
    ]
    tbl = Table(frais_data, colWidths=[2.5*inch, 1.9*inch, 1.5*inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), DARK),
        ("TEXTCOLOR", (0,0), (-1,0), GOLD),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [CREAM, HexColor("#e8e0ce")]),
        ("GRID", (0,0), (-1,-1), 0.5, GREY_LT),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("ALIGN", (1,0), (2,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(tbl)
    story.append(Spacer(1,8))

    # ── 5. STRUCTURE NORVEX ──────────────────────────────────────────────────
    story += section("5.  STRUCTURE DU FINANCEMENT — CLAUSE NORVEX", st)
    story.append(art("5.1", "Participation de partenaires", st))
    story.append(body(
        "Capital Norvex peut, à sa seule discrétion et sans avis à l'Emprunteur : "
        "financer le Prêt en tout ou en partie par l'intermédiaire de partenaires financiers, "
        "céder ou syndiquer tout ou partie du financement, et structurer des participations "
        "économiques de toute nature.", st))

    story.append(art("5.2", "Administration exclusive", st))
    story.append(body(
        "Capital Norvex agit à titre unique de gestionnaire du financement, "
        "d'administrateur des déboursés et de représentant des partenaires financiers. "
        "Seul Capital Norvex détient les pouvoirs décisionnels à l'égard de l'Emprunteur. "
        "Les partenaires financiers n'assument aucune responsabilité directe "
        "envers l'Emprunteur, qui renonce expressément à tout recours direct contre eux.", st))

    story.append(art("5.3", "Score Norvex™", st))
    story.append(body(
        "L'Emprunteur reconnaît que Capital Norvex utilise le système propriétaire "
        "<b>Score Norvex™</b> pour évaluer, surveiller et noter le dossier tout au long "
        "de la durée du Prêt. Les résultats de cette analyse peuvent influencer les conditions, "
        "les montants des déboursés et les décisions du Prêteur.", st))
    story.append(Spacer(1,6))

    # ── 6. CONDITIONS PRÉALABLES ─────────────────────────────────────────────
    story += section("6.  CONDITIONS PRÉALABLES AUX DÉBOURSÉS", st)
    story.append(art("6.1", "Conditions au premier déboursé", st))
    story.append(body(
        "Aucun déboursé initial ne sera effectué tant que Capital Norvex n'aura pas reçu, "
        "jugé satisfaisants et approuvés, à sa seule discrétion, tous les éléments suivants :", st))
    story += bullets([
        "Documents constitutifs et résolutions autorisant l'emprunt",
        "Preuve de mise de fonds propres injectée (fonds réels, non conditionnels)",
        "Budget final détaillé et calendrier des Travaux approuvés",
        "Plans et devis signés et scellés par les professionnels compétents",
        "Contrat d'entrepreneur général (forme et contenu approuvés par le Prêteur)",
        "Permis de construction valides et en vigueur",
        "Rapport d'évaluation indépendant (évaluateur agréé accepté par le Prêteur)",
        "Rapport environnemental Phase I (Phase II si requis par le Prêteur)",
        "Police d'assurance chantier (tous risques) et assurance responsabilité civile (5 M$ min.)",
        "Publication de l'Hypothèque de premier rang",
        "Cession de loyers signée (le cas échéant)",
        "Cautionnements personnels des Garants identifiés aux présentes",
        "Opinion juridique complète acceptée par le Prêteur",
    ], st)

    story.append(art("6.2", "Conditions continues", st))
    story.append(body("Chaque déboursé subséquent est conditionnel à :", st))
    story += bullets([
        "Absence de tout Événement de Défaut",
        "Respect du Budget et du Calendrier approuvés",
        "Maintien des assurances requises",
        "Validité de tous les permis nécessaires",
        "Conformité aux lois et règlements applicables",
        "Rapport d'inspection favorable de l'Inspecteur mandaté par Capital Norvex",
    ], st)
    story.append(Spacer(1,6))

    story.append(PageBreak())

    # ── 7. DÉBOURSÉS ─────────────────────────────────────────────────────────
    story += section("7.  DÉBOURSÉS — CONTRÔLE CAPITAL NORVEX", st)
    story.append(art("7.1", "Contrôle discrétionnaire absolu", st))
    story.append(body(
        "Capital Norvex conserve un contrôle absolu, exclusif et discrétionnaire "
        "sur tous les déboursés. Aucun montant n'est dû tant que l'ensemble des conditions "
        "prévues aux présentes ne sont pas entièrement satisfaites.", st))

    story.append(art("7.2", "Fréquence et documents requis", st))
    story.append(body("Les déboursés sont effectués mensuellement. Chaque demande doit comprendre :", st))
    story += bullets([
        "Demande formelle de déboursé signée",
        "Rapport d'inspection indépendant (Inspecteur agréé par Capital Norvex)",
        "État des coûts à date (CAC) certifié",
        "Ventilation détaillée des coûts engagés et des paiements effectués",
        "Quittances partielles et finales de tous les sous-traitants concernés",
        "Certificat professionnel de l'architecte ou de l'ingénieur responsable",
    ], st)

    story.append(art("7.3", "Retenue (holdback) et pouvoir de refus", st))
    story.append(body(
        "Une retenue de <b>cinq pour cent (5 %)</b> est maintenue sur chaque déboursé à titre "
        "de <b>holdback de construction</b> conforme à la pratique standard au Québec. Cette "
        "retenue sera libérée trente-cinq (35) jours après l'Achèvement Substantiel des travaux, "
        "sous réserve de l'absence de tout enregistrement d'hypothèque légale de la construction "
        "(art. 2724 et 2726 C.c.Q.) et après remise des quittances finales de tous les fournisseurs "
        "et sous-traitants. Capital Norvex peut, sans obligation de justification :", st))
    story += bullets([
        "Refuser ou réduire tout déboursé",
        "Exiger des garanties supplémentaires ou une injection de capital additionnel",
        "Retarder tout paiement en cas de doute sur l'avancement ou la conformité",
    ], st)
    story.append(Spacer(1,6))

    story.append(art("7.4", "Norvex Track\u2122 — Module de gestion des déboursés 24 h/7 jours", st))
    story.append(body(
        "Capital Norvex met en œuvre, pour la gestion des déboursés progressifs du Prêt, "
        "son module technologique propriétaire <b>Norvex Track\u2122</b>. "
        "L'Emprunteur reconnaît et accepte que :", st))
    story += bullets([
        "Toute demande de déboursé doit être soumise et documentée par l'Emprunteur via le module <b>Norvex Track\u2122</b>;",
        "Chaque déboursé est subordonné à la vérification documentaire complète (rapport d'inspection, factures, photos d'avancement, certificats professionnels, quittances) enregistrée dans le module;",
        "L'historique complet des déboursés (montants, dates, justificatifs) est tracé intégralement et accessible <b>24 heures sur 24, 7 jours sur 7</b>;",
        "Capital Norvex conserve, conformément à l'article 7.1, son <b>contrôle absolu, exclusif et discrétionnaire</b> sur l'autorisation ou le refus de tout déboursé via Norvex Track\u2122.",
    ], st)
    story.append(body(
        "Le module Norvex Track\u2122 ne crée aucun droit autonome de l'Emprunteur sur les fonds "
        "du Prêt et ne diminue en rien les pouvoirs de Capital Norvex prévus à la présente "
        "Convention.", st))

    story.append(art("7.5", "Portail Emprunteur (PWA) — Transparence 24 h/7 jours", st))
    story.append(body(
        "Capital Norvex met à la disposition de l'Emprunteur un <b>Portail Emprunteur</b> "
        "numérique sécurisé (<b>PWA — Progressive Web Application</b>), accessible "
        "<b>24 heures sur 24, 7 jours sur 7</b>, depuis tout appareil (téléphone intelligent, "
        "tablette, ordinateur). L'Emprunteur peut y consulter en temps réel :", st))
    story += bullets([
        "Le solde de son Prêt, le capital déboursé et le capital encore disponible;",
        "L'échéancier des paiements, les intérêts courus et l'historique des paiements effectués;",
        "Le statut des demandes de déboursé soumises via Norvex Track\u2122 (en attente, autorisée, exécutée, refusée);",
        "Les rapports d'inspection, photos d'avancement et documents pertinents au dossier;",
        "Les avis et communications officiels transmis par Capital Norvex.",
    ], st)
    story.append(body(
        "Le Portail Emprunteur (PWA) constitue un outil de <b>transparence</b> mis à la "
        "disposition de l'Emprunteur. Il ne se substitue pas aux communications officielles "
        "écrites prévues à la présente Convention et n'altère en rien les obligations de "
        "l'Emprunteur ni les droits du Prêteur.", st))
    story.append(Spacer(1,6))

    # ── 8. GARANTIES ─────────────────────────────────────────────────────────
    story += section("8.  GARANTIES", st)
    story.append(art("8.1", "Hypothèque immobilière", st))
    story.append(body(
        "L'Emprunteur consent en faveur de Capital Norvex une hypothèque immobilière "
        "de <b>premier rang</b> grevant l'immeuble, ses améliorations présentes et futures, "
        "les loyers, les indemnités d'assurance et les produits de vente.", st))

    story.append(art("8.2", "Cession de loyers et cautionnements", st))
    story.append(body(
        "L'Emprunteur cède la totalité de ses loyers présents et futurs. "
        "Les Garants fournissent un cautionnement <b>solidaire, irrévocable et illimité</b> "
        "couvrant le capital, les intérêts, les frais et tous coûts engagés.", st))

    story.append(art("8.3", "Garanties additionnelles", st))
    story.append(body("Capital Norvex peut exiger, à tout moment :", st))
    story += bullets([
        "Cautionnement de construction et cautionnement de main-d'œuvre/matériaux",
        "Lettre de crédit irrévocable",
        "Garantie corporative d'une entité approuvée par le Prêteur",
    ], st)
    story.append(Spacer(1,6))

    # ── 9. CONTRÔLE FINANCIER ────────────────────────────────────────────────
    story += section("9.  CONTRÔLE FINANCIER ET FLUX DE TRÉSORERIE", st)
    story.append(body(
        "Tous les fonds transitent par un compte contrôlé par Capital Norvex. "
        "Aucun retrait, transfert ou distribution n'est autorisé sans autorisation écrite préalable. "
        "Capital Norvex peut appliquer les sommes reçues dans l'ordre suivant : frais, "
        "intérêts, capital, réserves. L'Emprunteur fournit un accès complet et immédiat "
        "à ses comptes, livres et transactions.", st))
    story.append(Spacer(1,6))

    # ── 10. ENGAGEMENTS ──────────────────────────────────────────────────────
    story += section("10.  ENGAGEMENTS ET COVENANTS", st)
    story.append(art("10.1", "Engagements positifs", st))
    story += bullets([
        "Réaliser le Projet selon les plans approuvés par Capital Norvex",
        "Respecter le Budget et le Calendrier en tout temps",
        "Payer tous les intervenants, entrepreneurs et fournisseurs",
        "Maintenir toutes les assurances requises",
        "Fournir des rapports mensuels d'avancement au Prêteur",
        "Aviser immédiatement Capital Norvex de tout problème, litige ou retard",
    ], st)

    story.append(art("10.2", "Engagements négatifs (sans consentement écrit)", st))
    story += bullets([
        "Aucune dette additionnelle ou charge sur l'immeuble",
        "Aucun changement d'entrepreneur général",
        "Aucune modification majeure aux plans ou au budget",
        "Aucune vente, transfert ou cession du Projet",
        "Aucune distribution aux actionnaires ou associés",
    ], st)

    story.append(art("10.3", "Covenants financiers", st))
    cov_data = [
        ["Covenant", "Seuil", "Fréquence de vérification"],
        ["LTV maximal", "75 %", "À chaque déboursé"],
        ["LTC maximal", "80 %", "À chaque déboursé"],
        ["Réserve d'intérêts", "Obligatoire", "Continue"],
        ["Rapports financiers", "Trimestriels", "Continue"],
    ]
    tbl = Table(cov_data, colWidths=[2.5*inch, 1.5*inch, 2.0*inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), DARK),
        ("TEXTCOLOR", (0,0), (-1,0), GOLD),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [CREAM, HexColor("#e8e0ce")]),
        ("GRID", (0,0), (-1,-1), 0.5, GREY_LT),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("ALIGN", (1,0), (2,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(tbl)
    story.append(Spacer(1,8))

    # ── 11. DÉCLARATIONS ─────────────────────────────────────────────────────
    story += section("11.  DÉCLARATIONS ET GARANTIES", st)
    story.append(body(
        "L'Emprunteur et les Garants déclarent et garantissent à Capital Norvex que, "
        "à la date de signature et à chaque déboursé :", st))
    story += bullets([
        "Ils sont dûment constitués et en règle selon les lois applicables",
        "Ils ont la pleine capacité légale de contracter les présentes obligations",
        "Toutes les autorisations requises ont été dûment obtenues",
        "Les informations fournies sont complètes, exactes et non trompeuses",
        "Le Projet respecte toutes les lois, normes et règlements applicables",
        "Aucun litige, réclamation ou hypothèque légale n'est en cours",
        "Aucun événement de défaut n'existe ou n'est sur le point de survenir",
    ], st)
    story.append(Spacer(1,6))

    story.append(PageBreak())

    # ── 12. ÉVÉNEMENTS DE DÉFAUT ─────────────────────────────────────────────
    story += section("12.  ÉVÉNEMENTS DE DÉFAUT", st)
    story.append(body(
        "Constituent des Événements de Défaut, notamment :", st))

    defauts = [
        ("Financiers", ["Défaut de paiement d'intérêts ou de capital", "Non-respect d'un covenant financier", "Insuffisance de liquidités pour compléter le Projet"]),
        ("Opérationnels", ["Arrêt de chantier de plus de 5 jours ouvrables", "Retard significatif non approuvé", "Dépassement de budget sans autorisation", "Abandon du Projet"]),
        ("Juridiques", ["Hypothèque légale publiée contre l'immeuble non radiée dans les 7 jours d'un avis du Prêteur (tolérance zéro — voir art. 14.bis.1)", "Tout retard de paiement de taxes, charges municipales, assurances ou autres obligations courantes non régularisé dans les 7 jours d'un avis du Prêteur (tolérance zéro — voir art. 14.bis.2)", "Saisie ou procédure judiciaire significative", "Perte ou invalidité d'une garantie"]),
        ("Administratifs", ["Retrait ou suspension de permis de construction", "Non-maintien des assurances requises", "Fausse déclaration ou information inexacte", "Manquement aux termes de l'acte d'hypothèque conclu en lien avec la présente Convention (clause d'indissociabilité — art. 16.bis)"]),
        ("Emprunteur/Garant", ["Insolvabilité, faillite ou proposition concordataire", "Changement de contrôle non autorisé de l'Emprunteur"]),
        ("Discrétionnaires", ["Tout événement jugé par Capital Norvex comme compromettant la réalisation du Projet ou augmentant le risque"]),
    ]
    for cat, items in defauts:
        story.append(Paragraph(f"<b>{cat} :</b>", st["body"]))
        story += bullets(items, st)
    story.append(Spacer(1,6))

    # ── 13. RECOURS ──────────────────────────────────────────────────────────
    story += section("13.  RECOURS DU PRÊTEUR", st)
    story.append(body(
        "En cas d'Événement de Défaut, Capital Norvex peut, sans préavis ni délai :", st))
    story += bullets([
        "Suspendre immédiatement tous les déboursés",
        "Déclarer le Prêt exigible dans sa totalité",
        "Réaliser toutes les garanties consenties",
        "Percevoir directement les loyers et revenus",
        "Nommer un séquestre avec pouvoirs complets",
        "Exercer tout autre recours prévu par la loi",
    ], st)
    story.append(Spacer(1,6))

    # ── 14. DROIT DE PRISE DE CONTRÔLE ──────────────────────────────────────
    story += section("14.  DROIT DE PRISE DE CONTRÔLE (STEP-IN)", st)
    story.append(body(
        "En cas d'Événement de Défaut, Capital Norvex peut, à sa seule discrétion :", st))
    story += bullets([
        "Prendre possession du Projet et accéder au chantier sans restriction",
        "Remplacer l'entrepreneur général ou tout autre intervenant",
        "Résilier tout contrat lié au Projet",
        "Gérer directement ou indirectement les Travaux",
        "Compléter le Projet via toute entité affiliée ou mandataire",
    ], st)
    story.append(body(
        "Tous les coûts engagés dans ce cadre deviennent immédiatement exigibles "
        "et portent intérêt au taux majoré prévu aux présentes. "
        "L'Emprunteur renonce irrévocablement à contester toute intervention "
        "effectuée de bonne foi par Capital Norvex.", st))
    story.append(Spacer(1,6))

    # ── 14.bis  TOLÉRANCE ZÉRO — TAXES ET HYPOTHÈQUES LÉGALES ──────────────────
    story += section("14.bis  TOLÉRANCE ZÉRO — TAXES ET HYPOTHÈQUES LÉGALES", st)
    story.append(art("14.bis.1", "Hypothèques légales de la construction", st))
    story.append(body(
        "<b>AUCUNE</b> hypothèque légale de la construction (art. 2724 et 2726 C.c.Q.) n'est tolérée. "
        "L'Emprunteur s'engage à régler ou à faire radier toute hypothèque légale enregistrée "
        "<b>immédiatement</b> dès qu'il en est avisé, et au plus tard dans les "
        "<b>sept (7) jours</b> d'un avis écrit du Prêteur (ou plus tôt si la situation l'exige selon "
        "l'appréciation exclusive du Prêteur). À défaut, un Événement de Défaut sera "
        "<b>automatiquement déclaré</b>, et le Prêteur pourra : (i) payer la créance et porter le "
        "montant au capital du Prêt avec intérêts au taux de défaut; (ii) suspendre tout déboursé "
        "futur; (iii) déclarer le Prêt immédiatement exigible et exercer tous ses recours.", st))

    story.append(art("14.bis.2", "Taxes, charges et obligations courantes", st))
    story.append(body(
        "L'Emprunteur s'engage à payer ponctuellement à leur échéance toutes les taxes foncières, "
        "taxes scolaires, taxes d'amélioration locale, charges municipales, primes d'assurance et "
        "toutes autres obligations courantes affectant l'Immeuble. <b>AUCUN</b> retard n'est toléré. "
        "En cas de retard ou de défaut de paiement, l'Emprunteur s'engage à régulariser la situation "
        "<b>immédiatement</b> dès qu'il en est avisé, et au plus tard dans les "
        "<b>sept (7) jours</b> d'un avis écrit du Prêteur. À défaut, un Événement de Défaut sera "
        "<b>automatiquement déclaré</b>, et le Prêteur pourra : (i) payer directement la créance et "
        "porter le montant au capital du Prêt avec intérêts au taux de défaut; (ii) suspendre tout "
        "déboursé futur; (iii) déclarer le Prêt immédiatement exigible et exercer tous ses recours.", st))
    story.append(Spacer(1,6))

    # ── 14.ter  CESSION DES CONTRATS, PLANS, PERMIS — CONSTRUCTION ─────────────
    story += section("14.ter  CESSION DES CONTRATS, PLANS, PERMIS ET DROITS — CONSTRUCTION", st)
    story.append(body(
        "À titre de garantie additionnelle au présent Prêt, et pour les fins de tout dossier de "
        "construction, l'Emprunteur cède au Prêteur :", st))
    story += bullets([
        "Tous les contrats avec l'entrepreneur général et les sous-traitants principaux du Projet",
        "Tous les plans, devis et autres documents techniques du Projet",
        "Tous les permis de construction, d'occupation et autres autorisations municipales",
        "Toutes les soumissions, certificats et garanties (incluant la GCR et toute garantie d'entrepreneur)",
        "Toutes les polices d'assurance liées au Projet, avec Capital Norvex désigné comme bénéficiaire",
    ], st)
    story.append(body(
        "Ces cessions deviennent exécutoires de plein droit lors d'un Événement de Défaut. "
        "Le Projet est de plus assujetti aux exigences de la Régie du bâtiment du Québec (RBQ) "
        "et, le cas échéant (construction résidentielle), à la Garantie de construction "
        "résidentielle (GCR) ou tout autre programme de garantie applicable. La preuve "
        "d'inscription doit être remise au Prêteur avant tout déboursement.", st))
    story.append(Spacer(1,6))

    # ── 15. REMBOURSEMENT ────────────────────────────────────────────────────
    story += section("15.  REMBOURSEMENT", st)
    story.append(art("15.1", "Échéance et modalités", st))
    story.append(body(
        "Le capital est remboursable intégralement à l'échéance, lors de la vente, "
        "du refinancement ou de la stabilisation du Projet, selon la première occurrence. "
        "Les paiements sont appliqués dans l'ordre suivant : frais, intérêts, capital.", st))

    story.append(art("15.2", "Remboursement anticipé", st))
    story.append(body(
        "Autorisé, sous réserve d'une pénalité minimale équivalant à "
        "<b>trois (3) mois d'intérêts</b> calculés au taux contractuel.", st))
    story.append(Spacer(1,6))

    # ── 16. DISPOSITIONS GÉNÉRALES ───────────────────────────────────────────
    story += section("16.  DISPOSITIONS GÉNÉRALES", st)
    gen_data = [
        ["Droit applicable", "Lois de la province de Québec (Canada)"],
        ["Compétence judiciaire", "District de Montréal, Québec"],
        ["Cession", "Interdite sans consentement écrit préalable du Prêteur"],
        ["Amendements", "Par écrit, signés des parties"],
        ["Divisibilité", "Toute clause invalide n'affecte pas le reste de la Convention"],
        ["Avis", "Par écrit, incluant courriel certifié ou recommandé"],
        ["Intégralité", "Le présent Accord constitue l'entente complète des parties"],
        ["Renonciation", "Aucune tolérance ne constitue une renonciation permanente"],
        ["LRPCFAT / CANAFE", "Vérifications d'identité et source des fonds effectuées"],
    ]
    tbl = Table(gen_data, colWidths=[2.2*inch, 3.8*inch])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("TEXTCOLOR", (0,0), (0,-1), DARK),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [CREAM, HexColor("#e8e0ce")]),
        ("GRID", (0,0), (-1,-1), 0.5, GREY_LT),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(tbl)
    story.append(Spacer(1,8))

    # ── 16.bis  CLAUSE D'INDISSOCIABILITÉ — FONDAMENTALE ─────────────────────
    story += section("16.bis  INDISSOCIABILITÉ AVEC L'ACTE D'HYPOTHÈQUE — CLAUSE FONDAMENTALE", st)
    story.append(body(
        "<b>La présente Convention de prêt et l'acte d'hypothèque immobilière conclu entre "
        "les Parties forment un ensemble contractuel INDISSOCIABLE et complémentaire.</b> "
        "Les Parties reconnaissent expressément et conviennent irrévocablement que ces deux "
        "documents doivent être lus, interprétés et exécutés conjointement, comme s'ils ne "
        "formaient qu'un seul et même contrat. Toute clause, condition, déclaration, garantie, "
        "engagement ou obligation prévu(e) dans la présente Convention s'applique pleinement et "
        "de plein droit aux Parties à l'acte d'hypothèque, et tout manquement aux termes de la "
        "présente Convention constitue automatiquement un Événement de Défaut au sens de l'article "
        "12 et permet l'exercice de tous les recours hypothécaires. Aucune des Parties ne peut "
        "invoquer l'absence d'une clause dans l'un des deux documents pour échapper à une obligation "
        "prévue dans l'autre. En cas de divergence ou d'ambiguïté entre les deux documents, "
        "<b>l'interprétation la plus favorable au Prêteur prévaudra</b>.", st))
    story.append(Spacer(1, 8))

    # ── 17. SIGNATURES ───────────────────────────────────────────────────────
    story.append(PageBreak())
    story += section("17.  SIGNATURES", st)
    story.append(body(
        "EN FOI DE QUOI, les parties ont signé la présente Convention à la date "
        "indiquée ci-dessous, après en avoir pris connaissance.", st))
    story.append(Spacer(1, 6))
    story.append(body(
        "<i>Pour Capital Norvex Inc., le présent acte est signé par le mandataire désigné "
        "ci-dessous, dûment autorisé en vertu d'une résolution corporative adoptée par "
        "l'actionnaire unique et présidente, Madame Suzanne Breton, dont copie certifiée "
        "conforme est jointe au dossier.</i>", st))
    story.append(Spacer(1, 10))

    def sign_block(title, fields):
        rows = [[Paragraph(title, ParagraphStyle(
            "ST", fontName="Helvetica-Bold", fontSize=10,
            textColor=WHITE, alignment=TA_LEFT))]]
        tbl_h = Table(rows, colWidths=[PAGE_W - 2*MARGIN])
        tbl_h.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), DARK),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LINEBELOW", (0,-1), (-1,-1), 2, GOLD),
        ]))
        items = [tbl_h, Spacer(1,8)]
        for lbl, placeholder in fields:
            items.append(Paragraph(lbl, st["field_label"]))
            items.append(Paragraph(f"<u>{placeholder}</u>", st["field_line"]))
        items.append(Spacer(1,6))
        items.append(Paragraph("Signature : _______________________________________________", st["body"]))
        items.append(Spacer(1,16))
        return items

    story += sign_block("PRÊTEUR — CAPITAL NORVEX INC.", [
        ("Mandataire désigné (nom complet) :", "________________________________"),
        ("Titre / Qualité :", "________________________________"),
        ("Résolution corporative datée du :", "________________________________"),
        ("Signée par : Madame Suzanne Breton, présidente et actionnaire unique", ""),
        ("Date de signature :", "________________________________"),
    ])

    story += sign_block("EMPRUNTEUR", [
        ("Dénomination sociale :", "________________________________"),
        ("Représentant autorisé :", "________________________________"),
        ("Titre :", "________________________________"),
        ("Date :", "________________________________"),
    ])

    story += sign_block("GARANT 1", [
        ("Nom complet :", "________________________________"),
        ("Date :", "________________________________"),
    ])

    story += sign_block("GARANT 2 (le cas échéant)", [
        ("Nom complet :", "________________________________"),
        ("Date :", "________________________________"),
    ])

    # ── ANNEXE A ─────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story += section("ANNEXE A  —  DESCRIPTION DU PROJET", st)
    annexe_fields = [
        ("Nom du projet :", "_________________________________________________"),
        ("Adresse municipale :", "_________________________________________________"),
        ("Municipalité / MRC :", "_________________________________________________"),
        ("Type de développement :", "_________________________________________________"),
        ("Nombre d'unités / superficie :", "_________________________________________________"),
        ("Valeur estimée à l'achèvement :", "$  ___________________________ CAD"),
        ("Coût total du projet :", "$  ___________________________ CAD"),
        ("Mise de fonds de l'Emprunteur :", "$  ___________________________ CAD  ( ______ % du coût)"),
        ("Entrepreneur général :", "_________________________________________________"),
        ("Architecte / ingénieur :", "_________________________________________________"),
        ("Date de début des Travaux :", "_________________"),
        ("Date d'achèvement prévue :", "_________________"),
    ]
    for lbl, ph in annexe_fields:
        story += field(lbl, ph, st)

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Les plans, devis, budget détaillé et calendrier des Travaux constituent "
        "des pièces intégrantes de la présente Annexe A et sont réputés y être joints.",
        st["note"]))
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "Paraphé et approuvé par : _______________________ (Prêteur)  "
        "   _______________________ (Emprunteur)",
        st["body"]))

# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    out = "/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres/Convention_Pret_CapitalNorvex.pdf"
    doc = SimpleDocTemplate(
        out,
        pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 36, bottomMargin=MARGIN + 38,
        title="Convention de Prêt de Construction — Capital Norvex",
        author="Capital Norvex Inc.",
        subject="Financement Privé Institutionnel",
    )

    styles = build_styles()
    story = []
    build_cover(story, styles)
    build_body(story, styles)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"✅ PDF généré : {out}")

if __name__ == "__main__":
    main()
