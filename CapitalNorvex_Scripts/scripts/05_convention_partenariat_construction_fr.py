"""
05_convention_partenariat_construction_fr.py
CAPITAL NORVEX — Convention de Partenariat — Construction (FR)
Génère : Convention_Partenariat_Construction_CapitalNorvex.pdf
"""
import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image as RLImage
)
from reportlab.platypus.flowables import Flowable

EMBLEM_PATH = r'/Users/yvesbarrette/Desktop/capitalnorvex-site/CapitalNorvex_Scripts/logos/emblem_header.png'
COVER_PATH  = r'/Users/yvesbarrette/Desktop/capitalnorvex-site/CapitalNorvex_Scripts/logos/logo_cover.png'
OUTPUT_FILE = r'/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres/Convention_Partenariat_Construction_CapitalNorvex.pdf'

DARK    = HexColor("#0a0d13")
GOLD    = HexColor("#C9A84C")
GOLD2   = HexColor("#b8975a")
CREAM   = HexColor("#f5f0e8")
CREAM2  = HexColor("#e8e0ce")
GREY_LT = HexColor("#d4c9b0")
GREY_MD = HexColor("#8a7d5f")
WHITE   = HexColor("#ffffff")

PAGE_W, PAGE_H = letter
MARGIN = 0.65 * inch
BW = PAGE_W - 2 * MARGIN  # body width


class GoldLine(Flowable):
    def __init__(self, width=None, thickness=1.2):
        super().__init__()
        self.width = width or BW
        self.thickness = thickness
        self.height = thickness + 2

    def draw(self):
        self.canv.setStrokeColor(GOLD)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self.thickness / 2, self.width, self.thickness / 2)


def on_page(canvas, doc):
    canvas.saveState()
    w, h = letter
    canvas.setFillColor(DARK)
    canvas.rect(0, h - 62, w, 62, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, h - 63.5, w, 1.5, fill=1, stroke=0)
    if os.path.exists(EMBLEM_PATH):
        canvas.drawImage(EMBLEM_PATH, MARGIN, h - 47, width=38, height=42,
                         preserveAspectRatio=True, mask='auto')
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(MARGIN + 44, h - 28, "CAPITAL NORVEX")
    canvas.setFillColor(GREY_LT)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(MARGIN + 44, h - 42, "Financement Privé Institutionnel")
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.drawRightString(w - MARGIN, h - 28, "CONVENTION DE PARTENARIAT — CONSTRUCTION")
    canvas.setFillColor(GREY_LT)
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(w - MARGIN, h - 52, f"p. {doc.page}")
    canvas.setFillColor(DARK)
    canvas.rect(0, 0, w, 50, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, 50, w, 1.5, fill=1, stroke=0)
    # Ligne du haut — confidentialité (centrée, gold pour la marque)
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawCentredString(w/2, 32,
        "CAPITAL NORVEX  ·  Confidentiel – Usage exclusif des parties signataires")
    # Ligne du bas — adresse complète (centrée, gris clair)
    canvas.setFillColor(GREY_LT)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(w/2, 14,
        "2705-1000 André-Prévost  ·  Île-des-Sœurs (Verdun)  ·  Montréal, QC H3E 0G2   |   1-(438)-533-PRET (7738)   |   info@capitalnorvex.com   |   capitalnorvex.com")
    canvas.restoreState()


def S(name, **kw):
    return ParagraphStyle(name, **kw)


ST = dict(
    cov_title  = S("CT",  fontName="Helvetica-Bold",    fontSize=26, textColor=GOLD,  alignment=TA_CENTER, leading=32, spaceAfter=6),
    cov_sub    = S("CS",  fontName="Helvetica-Oblique", fontSize=11, textColor=GOLD2, alignment=TA_CENTER, leading=17, spaceAfter=4),
    cov_name   = S("CN",  fontName="Helvetica-Bold",    fontSize=20, textColor=GOLD,  alignment=TA_CENTER, leading=26, spaceAfter=4),
    cov_name2  = S("CN2", fontName="Helvetica-Bold",    fontSize=13, textColor=WHITE, alignment=TA_CENTER, leading=18, spaceAfter=3),
    cov_name3  = S("CN3", fontName="Helvetica-Bold",    fontSize=9,  textColor=GOLD,  alignment=TA_CENTER, leading=13, spaceAfter=3),
    cov_italic = S("CI",  fontName="Helvetica-Oblique", fontSize=9,  textColor=CREAM, alignment=TA_CENTER, leading=13, spaceAfter=4),
    sec_head   = S("SH",  fontName="Helvetica-Bold",    fontSize=11, textColor=GOLD,  spaceBefore=0, spaceAfter=0, leading=16),
    art_head   = S("AH",  fontName="Helvetica-Bold",    fontSize=9.5,textColor=DARK,  spaceBefore=0, spaceAfter=0, leading=14),
    body       = S("BD",  fontName="Helvetica",         fontSize=9,  textColor=DARK,  alignment=TA_JUSTIFY, spaceAfter=4, leading=14),
    bullet     = S("BL",  fontName="Helvetica",         fontSize=8.8,textColor=DARK,  spaceAfter=2, leading=13, leftIndent=14),
    note       = S("NT",  fontName="Helvetica-Oblique", fontSize=8,  textColor=GREY_MD, alignment=TA_CENTER, spaceAfter=4),
    slogan     = S("SL",  fontName="Helvetica-Oblique", fontSize=10, textColor=GOLD2, alignment=TA_CENTER, spaceAfter=6),
    sign_lbl   = S("SL2", fontName="Helvetica-Bold",    fontSize=9,  textColor=GOLD,  spaceAfter=1),
    tbl_hdr    = S("TH",  fontName="Helvetica-Bold",    fontSize=9,  textColor=GOLD),
    tbl_val    = S("TV",  fontName="Helvetica",         fontSize=9,  textColor=DARK),
    gen_key    = S("GK",  fontName="Helvetica-Bold",    fontSize=9,  textColor=DARK),
    gen_val    = S("GV",  fontName="Helvetica",         fontSize=9,  textColor=DARK,  alignment=TA_JUSTIFY),
    rev_hdr    = S("RH",  fontName="Helvetica-Bold",    fontSize=9,  textColor=GOLD),
    rev_val    = S("RV",  fontName="Helvetica",         fontSize=8.8,textColor=DARK,  alignment=TA_JUSTIFY, leading=13),
)


def sec(title):
    return [
        Spacer(1, 8),
        Table([[Paragraph(title, ST["sec_head"])]],
              colWidths=[BW],
              style=TableStyle([
                  ("BACKGROUND", (0,0),(-1,-1), DARK),
                  ("LEFTPADDING",(0,0),(-1,-1), 10),
                  ("RIGHTPADDING",(0,0),(-1,-1),10),
                  ("TOPPADDING",(0,0),(-1,-1), 6),
                  ("BOTTOMPADDING",(0,0),(-1,-1),6),
                  ("LINEBELOW",(0,0),(-1,-1), 2, GOLD),
              ])),
        Spacer(1, 4),
    ]


def art(num, title):
    return [
        Table([[Paragraph(f"{num}  {title}", ST["art_head"])]],
              colWidths=[BW],
              style=TableStyle([
                  ("BACKGROUND",(0,0),(-1,-1), GREY_LT),
                  ("LEFTPADDING",(0,0),(-1,-1), 8),
                  ("RIGHTPADDING",(0,0),(-1,-1),8),
                  ("TOPPADDING",(0,0),(-1,-1), 4),
                  ("BOTTOMPADDING",(0,0),(-1,-1),4),
              ])),
        Spacer(1, 4),
    ]


def bp(text):
    return Paragraph(text, ST["body"])


def blt(items):
    return [Paragraph(f"• &nbsp; {t}", ST["bullet"]) for t in items]


def sp(n=6):
    return Spacer(1, n)


def params_tbl(rows):
    data = [[Paragraph(r[0], ST["tbl_hdr"]), Paragraph(r[1], ST["tbl_val"])] for r in rows]
    t = Table(data, colWidths=[2.4*inch, BW - 2.4*inch])
    t.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[CREAM, CREAM2]),
        ("TOPPADDING",(0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1), 8),
        ("LINEBELOW",(0,-1),(-1,-1), 1.5, GOLD),
    ]))
    return t


def gen_tbl(rows):
    data = [[Paragraph(r[0], ST["gen_key"]), Paragraph(r[1], ST["gen_val"])] for r in rows]
    t = Table(data, colWidths=[2.0*inch, BW - 2.0*inch])
    t.setStyle(TableStyle([
        ("TOPPADDING",(0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1), 0),
        ("LINEBELOW",(0,0),(-1,-2), 0.5, GREY_LT),
        ("LINEBELOW",(0,-1),(-1,-1), 1.5, GOLD),
    ]))
    return t


def rev_tbl(rows):
    """2-column revenue allocation table with dark header row."""
    data = []
    for i, r in enumerate(rows):
        if i == 0:
            data.append([Paragraph(r[0], ST["rev_hdr"]), Paragraph(r[1], ST["rev_hdr"])])
        else:
            data.append([Paragraph(r[0], ST["rev_val"]), Paragraph(r[1], ST["rev_val"])])
    col1 = 2.6 * inch
    col2 = BW - col1
    t = Table(data, colWidths=[col1, col2])
    style = [
        ("BACKGROUND",(0,0),(-1,0), DARK),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[CREAM, CREAM2]),
        ("TOPPADDING",(0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1), 8),
        ("RIGHTPADDING",(0,0),(-1,-1),8),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LINEBELOW",(0,-1),(-1,-1), 1.5, GOLD),
        ("LINEAFTER",(0,0),(0,-1), 0.5, GREY_LT),
    ]
    t.setStyle(TableStyle(style))
    return t


def num_list(items):
    result = []
    for num, text in items:
        row = [[Paragraph(num, ST["body"]), Paragraph(text, ST["body"])]]
        t = Table(row, colWidths=[0.3*inch, BW - 0.3*inch])
        t.setStyle(TableStyle([
            ("TOPPADDING",(0,0),(-1,-1), 2),
            ("BOTTOMPADDING",(0,0),(-1,-1),2),
            ("LEFTPADDING",(0,0),(-1,-1), 0),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
        ]))
        result.append(t)
    return result


def sign_pair(lbl1, lbl2):
    t = Table([
        [Paragraph(lbl1, ST["sign_lbl"]), Paragraph(lbl2, ST["sign_lbl"])],
        [GoldLine(width=BW*0.44, thickness=0.8), GoldLine(width=BW*0.44, thickness=0.8)],
    ], colWidths=[BW*0.5, BW*0.5])
    t.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"BOTTOM"),
        ("TOPPADDING",(0,0),(-1,-1), 14),
        ("BOTTOMPADDING",(0,0),(-1,-1),2),
        ("LEFTPADDING",(0,0),(-1,-1), 0),
    ]))
    return t


def dark_banner(text, color=WHITE):
    style = S("DBN", fontName="Helvetica-Bold", fontSize=10,
              textColor=color, alignment=TA_CENTER)
    t = Table([[Paragraph(text, style)]], colWidths=[BW])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), DARK),
        ("TOPPADDING",(0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1),8),
    ]))
    return t


def build_cover(story):
    story.append(sp(12))
    if os.path.exists(COVER_PATH):
        img = RLImage(COVER_PATH, width=120, height=130)
        img.hAlign = "CENTER"
        story.append(img)
    story.append(sp(8))
    story.append(Paragraph("CAPITAL NORVEX", ST["cov_title"]))
    story.append(Paragraph("<i>Financement Privé Institutionnel  |  Québec &amp; Ontario</i>", ST["cov_sub"]))
    story.append(GoldLine())
    story.append(sp(8))

    block = Table([
        [Paragraph("CONVENTION DE PARTENARIAT", ST["cov_name"])],
        [Paragraph("CO-FINANCEMENT IMMOBILIER PRIVÉ", ST["cov_name2"])],
        [Paragraph("PRÊTS CONSTRUCTION &amp; INFRASTRUCTURE", ST["cov_name3"])],
        [Paragraph("<i>Capital Norvex Inc. — Version Institutionnelle — Québec &amp; Ontario</i>", ST["cov_italic"])],
    ], colWidths=[BW])
    block.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), DARK),
        ("TOPPADDING",(0,0),(0,0), 18),
        ("TOPPADDING",(0,1),(-1,-1), 5),
        ("BOTTOMPADDING",(0,-1),(-1,-1), 18),
        ("BOTTOMPADDING",(0,0),(0,-2), 5),
        ("LEFTPADDING",(0,0),(-1,-1), 12),
        ("RIGHTPADDING",(0,0),(-1,-1),12),
        ("LINEABOVE",(0,0),(-1,0), 3, GOLD),
        ("LINEBELOW",(0,-1),(-1,-1), 3, GOLD),
    ]))
    story.append(block)
    story.append(sp(14))

    cov_tbl = Table([
        [Paragraph("PARTENAIRE", ST["tbl_hdr"]),               Paragraph("___________________________________", ST["tbl_val"])],
        [Paragraph("TYPE DE FINANCEMENT", ST["tbl_hdr"]),      Paragraph("Construction commerciale / Infrastructure", ST["tbl_val"])],
        [Paragraph("MONTANT DE PARTICIPATION", ST["tbl_hdr"]), Paragraph("$___________________________________ CAD", ST["tbl_val"])],
        [Paragraph("TAUX DE RENDEMENT", ST["tbl_hdr"]),        Paragraph("_____ % par année", ST["tbl_val"])],
        [Paragraph("DATE", ST["tbl_hdr"]),                     Paragraph("___________________________________", ST["tbl_val"])],
        [Paragraph("DOSSIER No.", ST["tbl_hdr"]),              Paragraph("___________________________________", ST["tbl_val"])],
    ], colWidths=[2.0*inch, BW - 2.0*inch])
    cov_tbl.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[CREAM, CREAM2]),
        ("TOPPADDING",(0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1), 10),
        ("LINEBELOW",(0,-1),(-1,-1), 1.5, GOLD),
    ]))
    story.append(cov_tbl)
    story.append(sp(18))
    story.append(Paragraph("Capital structuré.  Ambition maîtrisée.", ST["slogan"]))
    story.append(Paragraph(
        "CONFIDENTIEL — Réservé aux parties signataires et à leurs conseillers juridiques",
        ST["note"]))
    story.append(PageBreak())


def build_body(story):
    # ── 1 ──────────────────────────────────────────────────────────────────
    story += sec("1. INTERPRÉTATION ET DÉFINITIONS")
    story += art("1.1", "Interprétation")
    story.append(bp(
        "Sauf indication contraire du contexte, les titres de sections sont insérés pour la seule "
        "commodité des parties et ne limitent en rien la portée des dispositions. Le singulier inclut "
        "le pluriel et vice versa. Toute référence à une loi vise également ses modifications, refonte "
        "ou succession. Les termes non définis ont leur sens usuel dans l'industrie du financement "
        "immobilier commercial au Québec."))
    story.append(sp())
    story += art("1.2", "Définitions")
    defs = [
        ("<b>« Accord »</b> : La présente Convention de partenariat, incluant toutes ses annexes, "
         "avenants et documents accessoires incorporés par référence."),
        ("<b>« Actif de Prêt »</b> : Le dossier de financement immobilier de type construction ou "
         "infrastructure consenti par Capital Norvex à un Emprunteur tiers, dans lequel le Partenaire "
         "participe financièrement aux termes des présentes."),
        ("<b>« Capital Norvex »</b> : CAPITAL NORVEX INC., société constituée sous les lois de la province "
         "de Québec, gestionnaire exclusif et administrateur de l'ensemble du Partenariat."),
        ("<b>« Contribution »</b> : Le montant en capital que le Partenaire s'engage à déposer et à "
         "maintenir en faveur de Capital Norvex afin de co-financer l'Actif de Prêt identifié à l'Annexe A."),
        ("<b>« Déboursé »</b> : Toute avance de fonds versée à l'Emprunteur en vertu de l'Actif de Prêt, "
         "incluant le premier déboursé chez le notaire et tout déboursé progressif subséquent."),
        ("<b>« Emprunteur »</b> : Toute société ou entité commerciale à qui Capital Norvex consent un "
         "financement immobilier privé de type construction ou infrastructure, dans lequel la Contribution "
         "du Partenaire est déployée."),
        ("<b>« Événement de Défaut de l'Emprunteur »</b> : Tout défaut de paiement ou manquement de "
         "l'Emprunteur en vertu de la convention de prêt le liant à Capital Norvex, incluant le "
         "non-paiement des intérêts ou du capital à l'échéance."),
        ("<b>« Événement de Défaut du Partenaire »</b> : Tout manquement du Partenaire à ses obligations "
         "en vertu des présentes, tel que défini à la Section 10."),
        ("<b>« Frais de Dossier Capital Norvex »</b> : Les frais d'analyse, de montage et d'administration "
         "représentant de 3 % à 3,5 % du montant total de l'Actif de Prêt, appartenant exclusivement à "
         "Capital Norvex, prélevés lors du premier Déboursé chez le notaire."),
        ("<b>« Hypothèque Mobilière »</b> : La sûreté publiée par le Partenaire au Registre des droits "
         "personnels et réels mobiliers (RDPRM) sur l'Actif de Prêt détenu par Capital Norvex, "
         "conformément aux articles 2660 et suivants du Code civil du Québec (art. 2660 CCQ)."),
        ("<b>« Intérêts »</b> : Les intérêts annuels générés par l'Actif de Prêt, calculés quotidiennement "
         "et capitalisés mensuellement sur le solde de la Contribution déboursée, appartenant "
         "exclusivement au Partenaire."),
        ("<b>« Partenaire »</b> : La personne physique ou morale identifiée à la Section 2.2, "
         "partenaire financier de l'Actif de Prêt."),
        ("<b>« Produits de Vente »</b> : L'ensemble des sommes nettes perçues lors de la vente d'un "
         "immeuble repris en paiement ou vendu sous contrôle de justice, après acquittement des frais "
         "de vente, des charges prioritaires et des frais juridiques de Capital Norvex."),
        ("<b>« Profit de Vente »</b> : L'excédent des Produits de Vente après remboursement intégral de "
         "la Contribution du Partenaire, des Intérêts capitalisés et des Frais de Dossier Capital Norvex."),
        ("<b>« RDPRM »</b> : Le Registre des droits personnels et réels mobiliers tenu par le "
         "ministère de la Justice du Québec."),
        ("<b>« Reprise »</b> : L'exercice par Capital Norvex de son droit de prise en paiement de "
         "l'immeuble ou de vente forcée sous contrôle de justice, à la suite d'un Événement de Défaut "
         "de l'Emprunteur."),
        ("<b>« Score Norvex™ »</b> : Le système d'analyse et de cotation propriétaire de Capital Norvex "
         "servant à l'évaluation initiale, au suivi continu et à la gestion du risque de chaque Actif de Prêt."),
    ]
    for d in defs:
        story.append(bp(d))
    story.append(sp())

    # ── 2 ──────────────────────────────────────────────────────────────────
    story += sec("2. PARTIES")
    story += art("2.1", "Capital Norvex Inc. — Gestionnaire Exclusif")
    story.append(bp("<b>Dénomination sociale : CAPITAL NORVEX INC.</b>"))
    story.append(bp("Adresse : ___________________________________________________________"))
    story.append(bp("Représentant autorisé : Yves Barrette"))
    story.append(bp("Titre : Fondateur &amp; Directeur, Financement Privé"))
    story.append(sp())
    story += art("2.2", "Partenaire")
    story.append(bp("Dénomination sociale ou nom complet : _______________________________________"))
    story.append(bp("Numéro d'entreprise (NEQ) ou NAS (personne physique) : _____________________"))
    story.append(bp("Adresse du siège social : ________________________________________________"))
    story.append(bp("Représentant autorisé : __________________________________________________"))
    story.append(bp("Titre : _________________________________________________________________"))
    story.append(bp("Courriel : ______________________________________________________________"))
    story.append(bp("Téléphone : _____________________________________________________________"))
    story.append(sp())

    # ── 3 ──────────────────────────────────────────────────────────────────
    story += sec("3. NATURE ET OBJET DU PARTENARIAT")
    story += art("3.1", "Esprit du partenariat")
    story.append(bp(
        "La présente Convention repose sur une relation de partenariat véritable, fondée sur la "
        "confiance mutuelle, la transparence totale et le respect des intérêts de chacune des parties. "
        "Capital Norvex s'engage à traiter le Partenaire comme un associé stratégique à part entière, "
        "en lui fournissant toute l'information nécessaire pour suivre sa Contribution en toute "
        "sécurité et en temps réel. Le Partenaire, de son côté, s'engage à appuyer Capital Norvex "
        "dans la réalisation de ses objectifs de financement avec diligence et bonne foi."))
    story.append(sp())
    story += art("3.2", "Structure générale")
    story.append(bp(
        "Le Partenaire avance une Contribution financière à Capital Norvex, laquelle est intégralement "
        "déployée par Capital Norvex à titre de financement immobilier privé de type construction ou "
        "infrastructure en faveur d'un Emprunteur tiers identifié à l'Annexe A. Capital Norvex agit "
        "comme gestionnaire exclusif, prêteur inscrit et seul administrateur de l'Actif de Prêt, "
        "assurant ainsi la protection des droits du Partenaire à chaque étape."))
    story.append(sp())
    story += art("3.3", "Champ d'application — Prêts construction et infrastructure uniquement")
    story.append(bp(
        "La présente Convention s'applique exclusivement aux Actifs de Prêt de type financement de "
        "construction commerciale et d'infrastructure, caractérisés par des déboursements progressifs "
        "mensuels en fonction de l'avancement des travaux. Elle ne s'applique pas aux prêts à "
        "mensualités fixes (terrain, acquisition d'immeuble locatif), lesquels font l'objet d'une "
        "convention distincte."))
    story.append(sp())
    story += art("3.4", "Indépendance des parties")
    story.append(bp(
        "La présente Convention ne crée aucune relation de société, de fiducie, de coentreprise, "
        "d'emploi ou de mandat implicite entre Capital Norvex et le Partenaire, au-delà de ce qui "
        "est expressément prévu aux présentes. Chaque partie demeure une entité juridique distincte "
        "et indépendante."))
    story.append(sp())
    story += art("3.5", "Reconnaissance du Score Norvex™")
    story.append(bp(
        "Le Partenaire reconnaît et accepte que Capital Norvex utilise son système propriétaire "
        "Score Norvex™ pour analyser, approuver, surveiller et coter chaque Actif de Prêt tout au "
        "long de son terme. Le Partenaire accepte les décisions prises par Capital Norvex sur la "
        "base de ce système, sous réserve du respect des présentes."))
    story.append(sp())

    # ── 4 ──────────────────────────────────────────────────────────────────
    story += sec("4. STRUCTURE FINANCIÈRE — REVENUS ET PARTAGE")
    story += art("4.1", "Tableau de répartition des revenus")
    story.append(rev_tbl([
        ["Élément de revenu", "Bénéficiaire"],
        ["Frais de dossier (3 % à 3,5 %)", "Capital Norvex Inc. — exclusivement"],
        ["Intérêts annuels (10 % à 12 %)", "Partenaire — exclusivement"],
        ["Profit net à la vente — En cas de reprise seulement",
         "50 % Capital Norvex / 50 % Partenaire (après remboursement prioritaire du Partenaire)"],
        ["Vente sans profit net — En cas de reprise",
         "Partenaire récupère 100 % de sa Contribution + intérêts capitalisés. Aucune perte pour le Partenaire."],
        ["Frais juridiques (en cas de reprise)", "Capital Norvex Inc. — à sa charge"],
    ]))
    story.append(sp(8))
    story += art("4.2", "Frais de dossier — Appartiennent exclusivement à Capital Norvex")
    story.append(bp(
        "Les Frais de Dossier Capital Norvex, représentant de <b>3 % à 3,5 % du montant total de "
        "l'Actif de Prêt</b>, sont prélevés lors du premier Déboursé effectué chez le notaire et "
        "appartiennent <b>exclusivement et intégralement à Capital Norvex Inc.</b> Le Partenaire "
        "n'a aucun droit sur ces frais. Ils constituent la rémunération de Capital Norvex pour "
        "l'analyse, le montage et l'administration de l'Actif de Prêt."))
    story.append(sp())
    story += art("4.3", "Intérêts — Appartiennent exclusivement au Partenaire")
    story.append(bp(
        "Les intérêts annuels générés par l'Actif de Prêt, au taux convenu de <b>10 % à 12 % par "
        "année</b>, calculés quotidiennement et capitalisés mensuellement sur le solde de la "
        "Contribution réellement déboursée, appartiennent <b>exclusivement et intégralement au "
        "Partenaire.</b> Capital Norvex ne conserve aucune portion des intérêts. "
        "Les intérêts courent sans interruption du premier au dernier jour de l'Actif de Prêt, "
        "incluant durant toute la période de construction, la période post-construction et la période "
        "de stabilisation précédant la sortie bancaire. Il n'existe aucune période de suspension des "
        "intérêts. Les intérêts sont capitalisés mensuellement et remboursés intégralement au Partenaire "
        "lors de la clôture du dossier."))
    story.append(sp())
    story += art("4.4", "Partage du Profit de Vente — En cas de Reprise uniquement")
    story.append(bp(
        "Le mécanisme de partage du profit à 50/50 entre Capital Norvex et le Partenaire s'applique "
        "exclusivement en cas de Reprise suivie d'une vente générant un Profit de Vente. "
        "<b>Ordre de priorité de distribution des Produits de Vente :</b>"))
    story += num_list([
        ("1.", "Frais juridiques, frais de Séquestre, honoraires d'experts et tous frais directs de réalisation — à la charge de Capital Norvex, prélevés en premier rang sur les Produits de Vente."),
        ("2.", "Remboursement intégral de la Contribution du Partenaire."),
        ("3.", "Remboursement de tous les Intérêts capitalisés non perçus dus au Partenaire."),
        ("4.", "Remboursement à Capital Norvex de tout montant avancé en lien avec la Reprise."),
        ("5.", "Distribution du Profit de Vente résiduel : 50 % à Capital Norvex / 50 % au Partenaire."),
    ])
    story.append(sp())
    story += art("4.5", "Structure de remboursement — Prêt construction 18 mois")
    story.append(bp(
        "Pour les Actifs de Prêt de type construction commerciale d'une durée standard de dix-huit "
        "(18) mois, le remboursement est structuré comme suit, tel que détaillé à l'Annexe A :"))
    story += num_list([
        ("1.", "<b>Phase construction (mois 1 à 18) :</b> Déboursements progressifs en fonction de l'avancement des travaux. Intérêts capitalisés mensuellement. Aucune mensualité exigible de l'Emprunteur durant cette phase."),
        ("2.", "<b>Phase post-construction — Stabilisation (mois 19 à 20 environ) :</b> Période suivant la fin substantielle des travaux permettant à l'Emprunteur de louer les espaces et de préparer la sortie bancaire. Les intérêts continuent de courir et de se capitaliser."),
        ("3.", "<b>Phase mensualités (à compter du 20e mois environ) :</b> L'Emprunteur débute le versement de mensualités couvrant les intérêts courants dans l'attente du financement bancaire permanent."),
        ("4.", "<b>Sortie bancaire — Clôture :</b> L'Emprunteur obtient son financement institutionnel permanent et rembourse Capital Norvex intégralement : capital, tous les intérêts capitalisés impayés et tous les frais accessoires. Capital Norvex procède alors au remboursement complet du Partenaire."),
    ])
    story.append(sp())
    story += art("4.6", "Absence de profit — Protection du capital du Partenaire")
    story.append(bp(
        "Si les Produits de Vente, après règlement des éléments 1 et 4 ci-dessus, ne génèrent aucun "
        "Profit de Vente net, le Partenaire récupère intégralement sa Contribution et l'ensemble des "
        "Intérêts capitalisés, et ne subit aucune perte en lien avec la vente. Capital Norvex n'assume "
        "aucune obligation de garantir un rendement ou un capital au-delà des droits conférés par "
        "l'Hypothèque Mobilière et la structure de la présente Convention."))
    story.append(sp())

    # ── 5 ──────────────────────────────────────────────────────────────────
    story += sec("5. GARANTIES DU PARTENAIRE — HYPOTHÈQUE MOBILIÈRE AU RDPRM")
    story += art("5.1", "Publication obligatoire avant tout déboursé")
    story.append(bp(
        "En garantie du remboursement de sa Contribution, des Intérêts et de la quote-part du "
        "Profit de Vente (le cas échéant), Capital Norvex consent en faveur du Partenaire une "
        "hypothèque mobilière sans dépossession sur l'Actif de Prêt identifié à l'Annexe A, "
        "conformément aux articles 2660 et suivants du Code civil du Québec. Cette sûreté doit "
        "être publiée par le Partenaire au RDPRM dans les cinq (5) jours ouvrables suivant la "
        "signature des présentes et, dans tous les cas, avant le premier Déboursé."))
    story.append(sp())
    story += art("5.2", "Portée et limites de la sûreté")
    story.append(bp(
        "L'Hypothèque Mobilière porte sur les droits de créance de Capital Norvex à l'encontre de "
        "l'Emprunteur en vertu de l'Actif de Prêt. Elle ne confère au Partenaire aucun droit réel "
        "immobilier direct sur l'immeuble hypothéqué par l'Emprunteur, aucun droit d'intervenir "
        "dans la gestion du dossier, ni aucun recours direct contre l'Emprunteur. La sûreté garantit "
        "uniquement le paiement par Capital Norvex des sommes dues au Partenaire en vertu des présentes."))
    story.append(sp())
    story += art("5.3", "Radiation à l'échéance")
    story.append(bp(
        "Le Partenaire s'engage irrévocablement à radier l'inscription au RDPRM dans les dix (10) "
        "jours ouvrables suivant la réception du remboursement intégral de sa Contribution, des "
        "Intérêts et de sa quote-part du Profit de Vente. Tout défaut de radiation dans ce délai "
        "permet à Capital Norvex de procéder à la radiation aux frais exclusifs du Partenaire."))
    story.append(sp())

    # ── 6 ──────────────────────────────────────────────────────────────────
    story += sec("6. GESTION EXCLUSIVE PAR CAPITAL NORVEX — DANS UN ESPRIT DE BONNE FOI")
    story += art("6.1", "Principe de la gestion exclusive et de la bonne foi")
    story.append(bp(
        "Capital Norvex assume la gestion exclusive de l'Actif de Prêt, incluant la relation "
        "opérationnelle avec l'Emprunteur, la documentation juridique, les inspections de chantier "
        "et toutes les décisions de crédit. Cette gestion s'exerce <b>en tout temps dans un esprit "
        "de bonne foi</b> et de transparence absolue envers le Partenaire, conformément aux articles "
        "6 et 1375 du <i>Code civil du Québec</i>. Le Partenaire ne s'adresse pas directement à "
        "l'Emprunteur ni à ses représentants, mais conserve en tout temps son droit à l'information "
        "complète et à la consultation pour toute décision matérielle, tel que prévu aux Sections 6.3, "
        "6.4 et 8.3 des présentes."))
    story.append(sp())
    story += art("6.2", "Pouvoirs exclusifs")
    story.append(bp("Sans limiter ce qui précède, les pouvoirs suivants appartiennent exclusivement à Capital Norvex :"))
    story += blt([
        "Approuver, refuser ou modifier les conditions de l'Actif de Prêt",
        "Gérer les montants et le calendrier de chaque Déboursé",
        "Ordonner des inspections de chantier, des expertises et des évaluations",
        "Déclarer un Événement de Défaut et exercer tous les recours disponibles",
        "Décider de procéder à une Reprise ou une vente sous contrôle de justice",
        "Nommer un Séquestre ou tout autre mandataire spécialisé",
        "Engager et diriger toutes procédures judiciaires et notariales",
        "Négocier et conclure tout règlement ou arrangement avec l'Emprunteur",
        "Remplacer l'entrepreneur général ou tout autre intervenant sur le chantier",
        "Gérer directement ou indirectement les travaux de construction en cas de Reprise",
    ])
    story.append(sp())
    story += art("6.3", "Rapports mensuels automatiques au Partenaire")
    story.append(bp(
        "Simultanément à chaque demande d'autorisation de Déboursé mensuel, Capital Norvex transmet "
        "automatiquement au Partenaire un rapport complet sur l'état de l'Actif de Prêt, incluant : "
        "l'avancement des travaux, le montant du Déboursé demandé, le solde cumulatif déboursé, les "
        "Intérêts capitalisés courus, et tout événement matériel susceptible d'affecter la valeur de "
        "la Contribution. Le Partenaire est ainsi pleinement informé à chaque étape du financement. "
        "En cas d'Événement de Défaut de l'Emprunteur, Capital Norvex avise le Partenaire par écrit "
        "dans les cinq (5) jours ouvrables."))
    story.append(sp())
    story += art("6.4", "Portail Partenaire (PWA) — Transparence 24 h/7 jours sur tous ses prêts")
    story.append(bp(
        "Capital Norvex met à la disposition du Partenaire un <b>Portail Partenaire</b> "
        "numérique sécurisé (PWA — Progressive Web Application), accessible <b>24 heures sur "
        "24, 7 jours sur 7</b>, depuis tout appareil (téléphone intelligent, tablette, "
        "ordinateur). Ce portail constitue un <b>droit contractuel</b> du Partenaire et un "
        "engagement de transparence absolue de Capital Norvex. Le Partenaire y a accès en "
        "temps réel aux informations suivantes pour <b>tous ses Actifs de Prêt</b> en cours :"))
    story += blt([
        "Solde de la Contribution déboursée et Intérêts capitalisés courus en temps réel",
        "Historique complet de tous les Déboursés effectués",
        "Rapports d'inspection et d'avancement des travaux",
        "Statut de chaque demande d'autorisation de Déboursé en attente",
        "Documents du dossier : évaluations, permis, assurances, états de compte, polices",
        "Alertes automatiques pour tout événement matériel affectant le dossier",
        "Communications directes et messagerie sécurisée avec Capital Norvex",
    ])
    story.append(sp())
    story += art("6.5", "Norvex Track™ — Module de déboursement et autorisation 24 h/7 jours")
    story.append(bp(
        "Pour les prêts de construction et d'infrastructure, Capital Norvex met également "
        "à la disposition du Partenaire le module <b>Norvex Track™</b>, un outil "
        "technologique propriétaire qui permet au Partenaire, <b>24 heures sur 24, 7 jours "
        "sur 7</b>, de :"))
    story += blt([
        "<b>Recevoir</b> en temps réel chaque demande de Déboursé progressif accompagnée des rapports d'inspection, certificats d'avancement et quittances partielles;",
        "<b>Examiner</b> en ligne l'ensemble des documents justificatifs depuis tout appareil;",
        "<b>Autoriser</b> chaque Déboursé d'un simple bouton, conformément à la Section 7;",
        "<b>Exécuter</b> directement le Déboursé : c'est le Partenaire qui, sur son autorisation, déclenche le virement des fonds — Capital Norvex n'effectue aucun déboursé sans cette autorisation explicite;",
        "<b>Suivre</b> en temps réel le statut de chaque transaction, l'avancement budgétaire, le calendrier de réalisation et toute alerte sur le chantier.",
    ])
    story.append(bp(
        "L'utilisation de <b>Norvex Track™</b> par le Partenaire constitue une garantie "
        "supplémentaire de sa maîtrise opérationnelle des fonds : aucun montant ne quitte "
        "le compte séparé sans son autorisation expresse, donnée et exécutée par lui via "
        "le module."))
    story.append(sp())

    # ── 7 ──────────────────────────────────────────────────────────────────
    story += sec("7. MÉCANISME DE DÉBOURSEMENT — AUTORISATION ET CONTRÔLE DU PARTENAIRE")
    story += art("7.0", "Principe — Déboursements MENSUELS uniquement et suivi serré")
    story.append(bp(
        "Les Déboursés progressifs en faveur de l'Emprunteur sont effectués selon une "
        "<b>cadence strictement mensuelle</b>, à raison d'un (1) Déboursé par mois civil "
        "maximum, en fonction de l'avancement réel des travaux. Cette cadence mensuelle "
        "est :"))
    story += blt([
        "<b>Régulière et prévisible</b> : un Déboursé par mois, sur la base d'un rapport d'inspection professionnelle indépendant et d'un Certificat d'Avancement des Coûts (CAC) signé par l'architecte ou l'ingénieur responsable;",
        "<b>Non cumulable</b> : aucun Déboursé multiple dans le même mois, sauf accord écrit conjoint des parties pour des circonstances exceptionnelles dûment documentées (ex. retard d'inspection causé par cas de force majeure);",
        "<b>Soumise à un suivi serré</b> : chaque Déboursé est précédé d'une vérification rigoureuse de l'avancement des travaux, du respect du budget approuvé, du respect de l'échéancier, des assurances en vigueur, des permis valides et de toute autre condition matérielle;",
        "<b>Tracée intégralement</b> : chaque Déboursé est enregistré dans le module Norvex Track™ et accessible au Partenaire en temps réel via le Portail Partenaire (PWA) 24 h/7 jours.",
    ])
    story.append(bp(
        "Capital Norvex et le Partenaire reconnaissent que cette cadence mensuelle, "
        "rigoureuse et strictement encadrée, constitue une <b>protection essentielle</b> "
        "pour la valeur de la Contribution du Partenaire et pour la bonne réalisation du "
        "projet. Aucune dérogation ne peut être accordée unilatéralement par Capital Norvex."))
    story.append(sp())
    story += art("7.1", "Premier déboursé — Obligatoirement chez le notaire")
    story.append(bp(
        "Le premier Déboursé de tout Actif de Prêt est effectué, sans exception, en présence d'un "
        "notaire désigné par Capital Norvex. Cette exigence est absolue et ne peut être renoncée par "
        "aucune des parties. Le notaire vérifie toutes les conditions préalables, procède à "
        "l'inscription de l'hypothèque immobilière de premier rang en faveur de Capital Norvex, "
        "confirme l'inscription de l'Hypothèque Mobilière du Partenaire au RDPRM, et libère les "
        "fonds conformément aux instructions écrites de Capital Norvex. Cette procédure constitue "
        "la protection juridique primaire du Partenaire."))
    story.append(sp())
    story += art("7.2", "Déboursés progressifs — Autorisation et exécution par le Partenaire via Norvex Track™")
    story.append(bp(
        "Pour chaque Déboursé progressif mensuel subséquent, Capital Norvex transmet au Partenaire "
        "une demande d'autorisation de Déboursé au moins cinq (5) jours ouvrables avant la date "
        "prévue. Cette demande comprend obligatoirement :"))
    story += blt([
        "Le montant exact du Déboursé demandé et le solde cumulatif déboursé",
        "Un rapport d'inspection indépendant certifiant l'avancement des travaux",
        "Un Certificat d'Avancement des Coûts (CAC) certifié par l'architecte ou l'ingénieur responsable",
        "Une confirmation de la conformité au budget approuvé et à l'échéancier des travaux",
        "Les quittances partielles des sous-traitants concernés",
        "Tout élément additionnel que Capital Norvex juge pertinent",
    ])
    story.append(sp())
    story += art("7.3", "Obligation d'autoriser — Actif de Prêt performant")
    story.append(bp(
        "Lorsque l'Actif de Prêt est en bonne santé — c'est-à-dire qu'aucun Événement de Défaut "
        "de l'Emprunteur n'existe, que le budget approuvé et l'échéancier sont respectés et que "
        "les rapports professionnels sont satisfaisants — le Partenaire s'engage, agissant de bonne "
        "foi, à autoriser le Déboursé dans les soixante-douze (72) heures suivant la réception de la "
        "demande de Capital Norvex. À défaut de réponse écrite du Partenaire dans ce délai, "
        "<b>une présomption d'approbation s'applique</b> et Capital Norvex peut procéder au "
        "Déboursé, sous réserve du droit du Partenaire de soulever par écrit, dans les vingt-quatre "
        "(24) heures suivantes, toute objection sérieuse fondée sur l'un des motifs prévus ci-dessous. "
        "Le Partenaire peut légitimement refuser ou suspendre son autorisation dans les circonstances "
        "suivantes :"))
    story += blt([
        "Existence documentée d'un Événement de Défaut de l'Emprunteur non divulgué par Capital Norvex",
        "Dépassement manifeste du budget approuvé sans autorisation écrite de Capital Norvex",
        "Fraude prouvée et documentée imputable à Capital Norvex",
    ])
    story.append(sp())
    story += art("7.4", "Compte séparé par Actif de Prêt")
    story.append(bp(
        "L'ensemble des fonds de la Contribution sont détenus dans un compte bancaire séparé, "
        "identifié et désigné exclusivement à l'Actif de Prêt prévu à l'Annexe A. Aucun retrait, "
        "transfert ou compensation n'est permis sauf tel que prévu aux présentes. Capital Norvex "
        "tient une comptabilité distincte par Actif de Prêt et la met à la disposition du Partenaire "
        "sur demande écrite."))
    story.append(sp())

    # ── 8 ──────────────────────────────────────────────────────────────────
    story += sec("8. DÉFAUT DE L'EMPRUNTEUR — GESTION CONJOINTE EN PARTENARIAT")
    story += art("8.1", "Capital Norvex n'assume pas les mensualités impayées de l'Emprunteur")
    story.append(bp(
        "En cas d'Événement de Défaut de l'Emprunteur, incluant le non-paiement des intérêts ou "
        "le non-respect des conditions de l'Actif de Prêt, <b>Capital Norvex n'assume aucune "
        "obligation de substitution et n'effectue pas de paiements au nom de l'Emprunteur "
        "défaillant.</b> Capital Norvex n'est ni garant ni caution des obligations de l'Emprunteur "
        "envers le Partenaire. La Contribution du Partenaire constitue un engagement de partenariat comportant "
        "des risques, protégé par l'Hypothèque Mobilière et l'hypothèque immobilière de premier "
        "rang détenue par Capital Norvex."))
    story.append(sp())
    story += art("8.2", "Capitalisation des intérêts impayés")
    story.append(bp(
        "Les Intérêts dus au Partenaire qui ne sont pas perçus en raison du défaut de l'Emprunteur "
        "<b>sont automatiquement capitalisés</b> et s'ajoutent au solde dû au Partenaire. Ces "
        "Intérêts capitalisés portent eux-mêmes intérêt au taux contractuel. L'intégralité des "
        "Intérêts capitalisés est remboursée au Partenaire à même les Produits de Vente lors de la "
        "Reprise, en priorité et avant tout partage du Profit de Vente."))
    story.append(sp())
    story += art("8.3", "Le défaut de l'Emprunteur ne constitue pas un défaut de Capital Norvex")
    story.append(bp(
        "Les parties reconnaissent expressément qu'un Événement de Défaut de l'Emprunteur "
        "<b>ne constitue en aucun cas un Événement de Défaut de Capital Norvex</b> envers le "
        "Partenaire. Capital Norvex demeure pleinement engagée à gérer le dossier avec diligence "
        "et de bonne foi, et à mener à terme la procédure de protection des intérêts conjoints "
        "des parties, jusqu'à la récupération complète des sommes dues."))
    story.append(sp())
    story += art("8.4", "Gestion conjointe et décisions stratégiques en partenariat")
    story.append(bp(
        "Dès la constatation d'un Événement de Défaut de l'Emprunteur, Capital Norvex et le "
        "Partenaire <b>travaillent en partenariat actif</b> pour déterminer la meilleure stratégie "
        "de protection et de recouvrement. Capital Norvex assume la gestion opérationnelle quotidienne, "
        "mais les décisions stratégiques importantes sont prises <b>conjointement</b> par les deux "
        "parties, selon le processus suivant :"))
    story += num_list([
        ("1.", "<b>Avis et consultation immédiats :</b> Dans les cinq (5) jours ouvrables suivant le constat du défaut, Capital Norvex avise simultanément l'Emprunteur et le Partenaire par écrit, et convoque le Partenaire à une réunion de consultation (en personne ou par vidéoconférence) dans les sept (7) jours suivants afin de convenir conjointement d'une stratégie d'intervention."),
        ("2.", "<b>Avis de 60 jours à l'Emprunteur :</b> Capital Norvex transmet à l'Emprunteur un avis de défaut formel lui accordant soixante (60) jours pour remédier à sa situation, conformément aux articles 2757 et suivants du <i>Code civil du Québec</i>. Durant ce délai, Capital Norvex tient le Partenaire informé en temps réel via le portail PWA et par communication directe."),
        ("3.", "<b>Décision conjointe à l'expiration du 60 jours :</b> À défaut de remédiation, Capital Norvex et le Partenaire prennent <b>conjointement</b> la décision quant à la suite à donner, en choisissant entre les options suivantes : (a) <b>prise en paiement</b> par Capital Norvex (avec indemnisation appropriée du Partenaire); (b) <b>vente sous contrôle de justice</b>; (c) toute autre solution conforme à la loi. À défaut d'entente entre les parties dans les quinze (15) jours, la procédure de médiation prévue à la Section 14.5 s'applique."),
        ("4.", "<b>Choix du courtier immobilier :</b> Si l'option retenue est la vente, le choix du courtier immobilier (et de son cabinet) est fait <b>conjointement</b> par Capital Norvex et le Partenaire, sur la base de la compétence, du réseau, du plan de mise en marché et des honoraires proposés. Le mandat de vente est signé conjointement."),
        ("5.", "<b>Gestion du chantier en cours :</b> Si l'Actif de Prêt est en phase de construction au moment du défaut, Capital Norvex assume la gestion technique du chantier (entrepreneurs, sous-traitants, inspections), en consultant le Partenaire pour toute décision financière matérielle (>5 % du budget restant)."),
        ("6.", "<b>Distribution des produits de vente :</b> Capital Norvex procède à la distribution des Produits de Vente selon l'ordre de priorité prévu à la Section 4.4, en toute transparence avec le Partenaire."),
    ])
    story.append(sp())
    story += art("8.5", "Frais juridiques de reprise — À la charge de Capital Norvex")
    story.append(bp(
        "L'ensemble des frais juridiques, honoraires d'avocats, frais notariaux, frais de Séquestre "
        "et autres coûts engagés par Capital Norvex dans le cadre des procédures de Reprise sont "
        "prélevés en premier rang sur les Produits de Vente. Le Partenaire ne supporte aucun frais "
        "additionnel au-delà de sa Contribution initiale. Capital Norvex assume la responsabilité "
        "de mener ces procédures avec diligence et compétence."))
    story.append(sp())

    # ── 9 ──────────────────────────────────────────────────────────────────
    story += sec("9. ENGAGEMENT DU PARTENAIRE POUR LA DURÉE DE L'ACTIF DE PRÊT")
    story += art("9.1", "Engagement ferme jusqu'au terme de l'Actif de Prêt")
    story.append(bp(
        "Le Partenaire s'engage à maintenir sa Contribution en place pour toute la durée de l'Actif "
        "de Prêt, jusqu'au remboursement intégral par l'Emprunteur de l'ensemble du capital, des "
        "intérêts, des frais et accessoires — ou jusqu'à la distribution complète des Produits de "
        "Vente en cas de Reprise. Une fois le dossier mené à terme, le Partenaire est libre de ne "
        "pas reconduire son partenariat et peut récupérer la totalité de sa Contribution avec les Intérêts dus. "
        "Aucun retrait anticipé total ou partiel n'est autorisé pendant la durée de l'Actif de Prêt, "
        "sauf dans les cas expressément prévus à la Section 9.3 ci-dessous."))
    story.append(sp())
    story += art("9.2", "Cession et nantissement — Accord raisonnable")
    story.append(bp(
        "Le Partenaire peut céder, transférer, nantir ou grever ses droits en vertu des présentes "
        "avec le consentement écrit préalable de Capital Norvex, lequel consentement <b>ne peut être "
        "déraisonnablement refusé</b>. Capital Norvex examine toute demande de cession ou de "
        "nantissement de bonne foi et dans un délai raisonnable, en tenant compte de la solvabilité "
        "et de la légitimité du cessionnaire ou créancier proposé."))
    story.append(sp())
    story += art("9.3", "Exceptions — Sortie anticipée autorisée")
    story.append(bp(
        "Une sortie anticipée du Partenaire est permise dans les seules circonstances suivantes :"))
    story += blt([
        "Capital Norvex y consent expressément par écrit et prend les dispositions nécessaires pour remplacer intégralement la Contribution par un autre autre partenaire ou ses propres fonds, sans interruption du financement de l'Actif de Prêt ;",
        "Capital Norvex décide de rembourser le Partenaire et de le remplacer, conformément à la Section 9.4 ;",
        "<b>Manquement grave de Capital Norvex</b> à ses obligations en vertu des présentes, non remédié dans les trente (30) jours suivant un avis écrit du Partenaire (par exemple : fraude documentée, défaut de transparence persistant, violation matérielle des engagements de bonne foi).",
    ])
    story.append(sp())
    story += art("9.4", "Droit de remplacement de Capital Norvex — Encadrement")
    story.append(bp(
        "Capital Norvex peut, en cas de motif sérieux et objectif (notamment réorganisation "
        "stratégique, refinancement institutionnel, ou intérêt légitime de l'Actif de Prêt), "
        "remplacer le Partenaire par un autre autre partenaire ou ses propres fonds, en respectant "
        "les conditions cumulatives suivantes :"))
    story += blt([
        "Préavis écrit minimum de <b>trente (30) jours</b> au Partenaire, exposant les motifs du remplacement ;",
        "Remise au Partenaire, en un seul versement : (i) l'intégralité de la Contribution ; (ii) tous les Intérêts capitalisés courus à la date du remboursement ;",
        "Aucune pénalité ou retenue ne peut être imposée au Partenaire dans le cadre de ce remplacement ;",
        "Le Partenaire procède à la radiation de l'Hypothèque Mobilière dans les dix (10) jours ouvrables suivant la réception complète des sommes dues.",
    ])
    story.append(bp(
        "Ce remboursement complet libère les deux parties de toutes obligations mutuelles relatives "
        "à l'Actif de Prêt concerné."))
    story.append(sp())
    story += art("9.5", "Conséquences d'un retrait non conforme — Aucune pénalité financière")
    story.append(bp(
        "Si le Partenaire procédait à un retrait non conforme aux Sections 9.1 à 9.4, "
        "<b>aucune pénalité financière</b> ne lui serait imposée. Toutefois, les parties "
        "reconnaissent que la stabilité du financement est essentielle au bon déroulement de "
        "l'Actif de Prêt. Dans un tel cas :"))
    story += blt([
        "Les parties s'engagent à se rencontrer de bonne foi dans les plus brefs délais afin de trouver une solution conjointe permettant la continuité du financement ;",
        "Capital Norvex pourra, à sa discrétion, remplacer la Contribution par un autre autre partenaire ou ses propres fonds, sans interruption pour l'Emprunteur ;",
        "À défaut de solution amiable, le différend sera soumis à la procédure de médiation prévue à la Section 14.5 des présentes ;",
        "Les recours judiciaires demeurent disponibles en dernier ressort, mais sont limités à la réparation du préjudice réel et documenté subi par Capital Norvex (à l'exclusion de toute pénalité contractuelle).",
    ])
    story.append(sp())

    # ── 10 ──────────────────────────────────────────────────────────────────
    story += sec("10. ÉVÉNEMENTS DE DÉFAUT DU PARTENAIRE — RÉCIPROCITÉ ET BONNE FOI")
    story.append(sp(4))
    story.append(bp(
        "Constituent des Événements de Défaut du Partenaire, notamment :"))
    story.append(sp(4))
    story.append(bp("<b>Financiers :</b>"))
    story += blt([
        "Non-versement de la Contribution dans le délai convenu à l'Annexe A, malgré un avis écrit de quinze (15) jours",
        "Insolvabilité, faillite ou dépôt de bilan du Partenaire",
        "Proposition concordataire ou arrangement avec les créanciers du Partenaire affectant sa capacité à honorer ses engagements",
    ])
    story.append(sp(4))
    story.append(bp("<b>Contractuels :</b>"))
    story += blt([
        "Refus injustifié et de mauvaise foi d'autoriser un Déboursé dans les délais prévus à la Section 7.3",
        "Cession ou nantissement effectué sans avoir préalablement requis le consentement de Capital Norvex en vertu de la Section 9.2",
        "Violation matérielle des présentes non remédiée dans les vingt (20) jours suivant un avis écrit",
        "Fausse déclaration substantielle ayant induit Capital Norvex en erreur",
    ])
    story.append(sp(4))
    story.append(bp("<b>Juridiques :</b>"))
    story += blt([
        "Saisie de la Contribution par un créancier tiers, non levée dans les trente (30) jours",
        "<b>Sous réserve de l'article 10.1 ci-dessous</b> — Procédure judiciaire intentée directement par le Partenaire contre l'Emprunteur sans avoir préalablement notifié Capital Norvex et tenté la médiation prévue à la Section 14.5",
    ])
    story.append(sp(4))
    story += art("10.1", "Droit du Partenaire de protéger ses droits en cas de manquement grave de Capital Norvex")
    story.append(bp(
        "Nonobstant ce qui précède, le Partenaire conserve en tout temps le droit de protéger "
        "ses droits hypothécaires et contractuels par toute mesure légale appropriée si Capital "
        "Norvex commet un <b>manquement grave</b> à ses obligations (notamment : fraude, "
        "détournement de fonds, défaut persistant de transparence, refus de respecter les engagements "
        "de bonne foi prévus aux Sections 6, 8 et 14). Le Partenaire doit dans ce cas notifier "
        "Capital Norvex par écrit et accorder un délai de remédiation de trente (30) jours, sauf "
        "urgence manifeste mettant en péril la Contribution."))
    story.append(sp(4))
    story += art("10.2", "Recours de Capital Norvex — Bonne foi et proportionnalité")
    story.append(bp(
        "En cas d'Événement de Défaut du Partenaire, Capital Norvex peut, après avoir respecté la "
        "procédure de médiation prévue à la Section 14.5 (sauf urgence) : réclamer les sommes "
        "effectivement dues, exiger réparation du préjudice réel et documenté, et exercer tout "
        "recours prévu par la loi. <b>Aucune pénalité contractuelle forfaitaire</b> n'est applicable; "
        "seul le préjudice réel subi peut faire l'objet d'une demande de réparation."))
    story.append(sp())

    # ── 11 ──────────────────────────────────────────────────────────────────
    story += sec("11. DÉCLARATIONS ET GARANTIES DES PARTIES")
    story += art("11.1", "Déclarations du Partenaire")
    story.append(bp(
        "Le Partenaire déclare et garantit à Capital Norvex que, à la date de signature des présentes "
        "ET à toute date de Déboursé :"))
    story += blt([
        "Il est dûment constitué, autorisé et en règle selon les lois applicables",
        "Il possède la pleine capacité légale et financière pour contracter les présentes",
        "La Contribution provient de fonds légaux, déclarés et conformes aux exigences réglementaires, incluant les règles relatives à la lutte contre le blanchiment d'argent",
        "Il n'existe aucun litige, réclamation ou charge susceptible d'affecter ses droits en vertu des présentes",
        "La signature des présentes ne contrevient à aucun engagement ou obligation antérieur",
        "Il a obtenu tous les avis juridiques et fiscaux nécessaires avant de signer",
    ])
    story.append(sp())
    story += art("11.2", "Déclarations de Capital Norvex")
    story.append(bp(
        "Capital Norvex déclare et garantit au Partenaire que, à la date de signature des présentes :"))
    story += blt([
        "Elle est dûment constituée et autorisée à exercer ses activités au Québec et en Ontario",
        "L'Actif de Prêt a été analysé et approuvé conformément à ses politiques internes de crédit",
        "Le Score Norvex™ applicable a été calculé de bonne foi",
        "Elle gérera l'Actif de Prêt avec diligence, compétence et professionnalisme",
    ])
    story.append(sp())

    # ── 12 ──────────────────────────────────────────────────────────────────
    story += sec("12. CONFIDENTIALITÉ")
    story.append(sp(4))
    story.append(bp(
        "Toute information reçue dans le cadre des présentes, incluant les renseignements sur les "
        "Emprunteurs, les Actifs de Prêt, les conditions financières, les politiques internes et les "
        "systèmes propriétaires de Capital Norvex (dont le Score Norvex™), est strictement confidentielle. "
        "Cette obligation survit à la résiliation ou à l'expiration des présentes pour une période de "
        "cinq (5) ans. Aucune information ne peut être divulguée à un tiers sans le consentement écrit "
        "préalable de l'autre partie, sauf si requis par la loi, une ordonnance judiciaire ou un "
        "organisme de réglementation compétent."))
    story.append(sp())

    # ── 13 ──────────────────────────────────────────────────────────────────
    story += sec("13. DURÉE ET RÉSILIATION")
    story.append(sp(4))
    story.append(bp(
        "La présente Convention entre en vigueur dès sa signature par les deux parties et demeure "
        "en vigueur jusqu'au remboursement intégral de l'Actif de Prêt ou, en cas de Reprise, "
        "jusqu'à la distribution complète des Produits de Vente. Elle ne peut être résiliée "
        "prématurément que dans les cas expressément prévus aux présentes ou par accord mutuel "
        "écrit des parties. La résiliation ou l'expiration des présentes n'affecte pas les droits "
        "et obligations qui, par leur nature, survivent à la fin de la Convention, notamment : "
        "la confidentialité, la reddition de compte, et les obligations de radiation de l'Hypothèque Mobilière."))
    story.append(sp())

    # ── 14 ──────────────────────────────────────────────────────────────────
    story += sec("14. DISPOSITIONS GÉNÉRALES")
    story += art("14.1", "Droit applicable et compétence")
    story.append(bp(
        "La présente Convention est régie et interprétée selon les <b>lois de la province de "
        "Québec et les lois fédérales du Canada applicables</b>. Tout différend découlant de la "
        "présente Convention ou s'y rapportant relève de la compétence exclusive des tribunaux "
        "du district judiciaire de Montréal, sous réserve des Sections 14.5 (Médiation) et "
        "14.6 (Bonne foi)."))
    story.append(sp())
    story += art("14.2", "Amendements, avis et cession")
    story += blt([
        "<b>Amendements :</b> Toute modification doit être écrite et signée par les deux parties.",
        "<b>Avis :</b> Tout avis doit être donné par écrit, par courriel avec accusé de réception ou par courrier recommandé, aux adresses indiquées à l'Annexe A.",
        "<b>Cession :</b> Conformément à la Section 9.2, la cession des droits du Partenaire est permise avec consentement écrit préalable de Capital Norvex, lequel ne peut être déraisonnablement refusé.",
    ])
    story.append(sp())
    story += art("14.3", "Divisibilité, intégralité et renonciation")
    story += blt([
        "<b>Divisibilité :</b> Toute clause déclarée invalide ou inapplicable n'affecte pas la validité du reste de la Convention.",
        "<b>Intégralité :</b> La présente Convention, ensemble avec ses Annexes et l'Hypothèque Mobilière s'y rattachant, constitue l'entente complète des parties relativement à l'Actif de Prêt visé.",
        "<b>Renonciation :</b> Aucune tolérance ou délai dans l'exercice d'un droit ne constitue une renonciation permanente à ce droit.",
    ])
    story.append(sp())
    story += art("14.4", "Langue et interprétation")
    story.append(bp(
        "Le <b>français est la langue officielle</b> de la présente Convention. Toute traduction "
        "anglaise est fournie à titre de courtoisie; en cas de divergence, la version française "
        "prévaut. Les parties reconnaissent avoir négocié les présentes en français et avoir "
        "expressément renoncé à l'application de l'article 1432 du <i>Code civil du Québec</i> "
        "concernant l'interprétation contre le rédacteur, étant entendu que la Convention a été "
        "rédigée dans l'intérêt mutuel des parties."))
    story.append(sp())
    story += art("14.5", "Médiation obligatoire avant tout recours judiciaire")
    story.append(bp(
        "Les parties s'engagent à <b>tenter de résoudre à l'amiable, par voie de médiation</b>, "
        "tout différend, désaccord ou interprétation divergente découlant de la présente Convention "
        "<b>avant d'introduire toute procédure judiciaire</b>. La procédure de médiation est la "
        "suivante :"))
    story += num_list([
        ("1.", "La partie qui souhaite soulever un différend transmet un avis écrit à l'autre partie décrivant la nature du différend et la solution proposée."),
        ("2.", "Les parties disposent de quinze (15) jours pour tenter de résoudre le différend par discussion directe et de bonne foi."),
        ("3.", "À défaut de résolution, les parties désignent conjointement un médiateur indépendant et qualifié dans les dix (10) jours suivants. À défaut d'entente sur le choix du médiateur, chaque partie en désigne un et les deux médiateurs en désignent un troisième qui agira seul."),
        ("4.", "Les parties participent de bonne foi à au moins une (1) séance de médiation, dont les frais sont partagés à parts égales."),
        ("5.", "À défaut de règlement dans les soixante (60) jours suivant la nomination du médiateur, l'une ou l'autre des parties peut introduire un recours judiciaire."),
        ("6.", "<b>Exception — Mesures urgentes :</b> Cette obligation de médiation ne s'applique pas aux mesures conservatoires ou injonctions urgentes nécessaires pour préserver les droits hypothécaires d'une partie ou prévenir un préjudice irréparable."),
    ])
    story.append(sp())
    story += art("14.6", "Bonne foi et collaboration")
    story.append(bp(
        "Les parties s'engagent à exécuter la présente Convention <b>de bonne foi</b>, conformément "
        "aux articles 6, 7 et 1375 du <i>Code civil du Québec</i>, dans un esprit de collaboration, "
        "de transparence et de respect mutuel. Aucune partie ne pourra invoquer un manquement de "
        "l'autre partie sans avoir préalablement tenté de résoudre la situation de bonne foi par la "
        "communication directe et, le cas échéant, par la procédure de médiation prévue à la "
        "Section 14.5."))
    story.append(sp())
    story += art("14.7", "Indissociabilité avec l'Hypothèque Mobilière")
    story.append(bp(
        "La présente Convention de partenariat et l'Hypothèque Mobilière sur Créance Individuelle "
        "consentie par Capital Norvex en faveur du Partenaire en lien avec le présent Actif de Prêt "
        "forment <b>un ensemble contractuel indissociable</b>. Les deux documents doivent être lus, "
        "interprétés et exécutés conjointement et de manière complémentaire. Toute violation des "
        "termes de la présente Convention constitue automatiquement un Événement de Défaut au sens "
        "de l'Hypothèque Mobilière, et inversement. En cas de divergence ou d'ambiguïté entre les "
        "deux documents, l'interprétation la plus protectrice du Partenaire (créancier hypothécaire) "
        "prévaudra."))
    story.append(sp())

    # ── 15 SIGNATURES ───────────────────────────────────────────────────────
    story += sec("15. SIGNATURES")
    story.append(sp(4))
    story.append(bp(
        "EN FOI DE QUOI, les parties ont signé la présente Convention de partenariat à la date "
        "indiquée ci-dessous, après en avoir pris pleinement connaissance et avoir obtenu les "
        "conseils juridiques et fiscaux qu'elles ont jugé appropriés. Les parties reconnaissent "
        "que la présente Convention constitue un engagement ferme et légalement contraignant."))
    story.append(sp(10))

    story.append(dark_banner("CAPITAL NORVEX INC. — GESTIONNAIRE EXCLUSIF", GOLD))
    story.append(sign_pair("Représentant autorisé :", "Titre :"))
    story.append(sign_pair("Date :", "Signature :"))
    story.append(sp(18))

    story.append(dark_banner("PARTENAIRE", WHITE))
    story.append(sign_pair("Dénomination sociale :", "Représentant autorisé :"))
    story.append(sign_pair("Titre :", "Date :"))
    story.append(sp(14))
    story.append(Paragraph("Signature :", ST["sign_lbl"]))
    story.append(sp(16))
    story.append(GoldLine(thickness=0.8))

    # ── ANNEXE A ──────────────────────────────────────────────────────────
    story.append(PageBreak())
    story += sec("ANNEXE A — DESCRIPTION DE L'ACTIF DE PRÊT")
    story.append(sp(4))
    story.append(params_tbl([
        ["Nom du dossier / Emprunteur",          "___________________________________________"],
        ["Adresse de l'immeuble ou du projet",   "___________________________________________"],
        ["Type de financement",                   "Construction commerciale / Infrastructure"],
        ["Montant total du prêt accordé",         "$_________________________________________ CAD"],
        ["Contribution du Partenaire",            "$_________________________________________ CAD"],
        ["Frais de dossier CN (3 % à 3,5 %)",    "$_________________________________________ CAD — Capital Norvex"],
        ["Taux d'intérêt annuel au Partenaire",   "_____ % (calculé quotidiennement, capitalisé mensuellement)"],
        ["Score Norvex™",                         "_____ / 100"],
        ["Terme du prêt",                         "_____ mois"],
        ["Modalité de remboursement des intérêts","Intérêts capitalisés — remboursés à l'échéance"],
        ["Date de premier déboursé (notaire)",    "_______________"],
        ["Date d'échéance prévue",                "_______________"],
        ["Rang hypothécaire immobilier (Emprunteur)", "1er rang — Capital Norvex Inc."],
        ["Hypothèque mobilière RDPRM (Partenaire)",   "En faveur du Partenaire sur l'Actif de Prêt"],
        ["Notaire désigné",                       "___________________________________________"],
        ["Partage du profit en cas de reprise",   "50 % Capital Norvex / 50 % Partenaire (si profit)"],
    ]))
    story.append(sp(16))
    paraph = Table([[
        Paragraph("Paraphé — Capital Norvex : ___________________________", ST["sign_lbl"]),
        Paragraph("Paraphé — Partenaire : ___________________________", ST["sign_lbl"]),
    ]], colWidths=[BW*0.5, BW*0.5])
    story.append(paraph)
    story.append(sp(24))
    story.append(Paragraph(
        "<i>Cette convention est rédigée conformément aux lois de la province de Québec (Canada).</i>",
        ST["note"]))
    story.append(Paragraph(
        "Confidentiel — Usage exclusif des parties signataires © 2026 Capital Norvex Inc. — capitalnorvex.ca",
        ST["note"]))


def main():
    doc = SimpleDocTemplate(
        OUTPUT_FILE,
        pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=0.9*inch, bottomMargin=0.95*inch,
    )
    story = []
    build_cover(story)
    build_body(story)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"✅  Convention_Partenariat_Construction_CapitalNorvex.pdf généré.")


if __name__ == "__main__":
    main()
