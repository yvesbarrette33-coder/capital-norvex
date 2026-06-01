"""
04_convention_partenariat_mensualites_fr.py
CAPITAL NORVEX — Convention de Partenariat — Mensualités (FR)
Génère : Convention_Partenariat_Mensualites_CapitalNorvex.pdf
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
OUTPUT_FILE = r'/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres/Convention_Partenariat_Mensualites_CapitalNorvex.pdf'

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
    canvas.drawRightString(w - MARGIN, h - 28, "CONVENTION DE PARTENARIAT — MENSUALITÉS")
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
        [Paragraph("PRÊTS À MENSUALITÉS — TERRAIN / ACQUISITION / LOCATIF", ST["cov_name3"])],
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
        [Paragraph("PARTENAIRE", ST["tbl_hdr"]),              Paragraph("___________________________________", ST["tbl_val"])],
        [Paragraph("TYPE DE FINANCEMENT", ST["tbl_hdr"]),     Paragraph("Terrain / Acquisition / Immeuble locatif", ST["tbl_val"])],
        [Paragraph("MONTANT DE PARTICIPATION", ST["tbl_hdr"]),Paragraph("$___________________________________ CAD", ST["tbl_val"])],
        [Paragraph("MENSUALITÉ AU PARTENAIRE", ST["tbl_hdr"]),Paragraph("$___________________________________ / mois", ST["tbl_val"])],
        [Paragraph("DATE", ST["tbl_hdr"]),                    Paragraph("___________________________________", ST["tbl_val"])],
        [Paragraph("DOSSIER No.", ST["tbl_hdr"]),             Paragraph("___________________________________", ST["tbl_val"])],
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
        "ou succession."))
    story.append(sp())
    story += art("1.2", "Définitions")
    defs = [
        ("<b>« Accord »</b> : La présente Convention de partenariat à mensualités, incluant toutes ses "
         "annexes, avenants et documents accessoires incorporés par référence."),
        ("<b>« Actif de Prêt »</b> : Le dossier de financement immobilier de type terrain, acquisition "
         "ou immeuble locatif consenti par Capital Norvex à un Emprunteur tiers, dans lequel le Partenaire "
         "participe financièrement aux termes des présentes."),
        ("<b>« Capital Norvex »</b> : CAPITAL NORVEX INC., société constituée sous les lois de la province "
         "de Québec, gestionnaire exclusif et administrateur de l'ensemble du Partenariat."),
        ("<b>« Contribution »</b> : Le montant en capital que le Partenaire s'engage à déposer et à "
         "maintenir en faveur de Capital Norvex afin de co-financer l'Actif de Prêt identifié à l'Annexe A."),
        ("<b>« Emprunteur »</b> : Toute société ou entité commerciale à qui Capital Norvex consent un "
         "financement immobilier privé de type terrain, acquisition ou immeuble locatif, dans lequel la "
         "Contribution du Partenaire est déployée."),
        ("<b>« Événement de Défaut de l'Emprunteur »</b> : Tout défaut de paiement ou manquement de "
         "l'Emprunteur en vertu de la convention de prêt, incluant le non-paiement d'une mensualité "
         "dans les délais prévus."),
        ("<b>« Frais de Dossier Capital Norvex »</b> : Les frais d'analyse, de montage et d'administration "
         "représentant de 3 % à 3,5 % du montant total de l'Actif de Prêt, appartenant exclusivement à "
         "Capital Norvex, prélevés lors du déboursé chez le notaire."),
        ("<b>« Hypothèque Mobilière »</b> : La sûreté publiée par le Partenaire au Registre des droits "
         "personnels et réels mobiliers (RDPRM) sur l'Actif de Prêt détenu par Capital Norvex, "
         "conformément aux articles 2660 et suivants du Code civil du Québec."),
        ("<b>« Mensualité »</b> : Le versement mensuel d'intérêts dû au Partenaire, calculé sur le solde "
         "de la Contribution déboursée au taux convenu, payable le premier jour ouvrable de chaque mois."),
        ("<b>« Mode Standard »</b> : Le mécanisme de paiement par défaut dans lequel l'Emprunteur verse "
         "sa mensualité à Capital Norvex, qui la redistribue au Partenaire dans les deux (2) jours ouvrables suivants."),
        ("<b>« Mode Direct »</b> : Le mécanisme de paiement exceptionnel et temporaire dans lequel "
         "l'Emprunteur verse sa mensualité directement au Partenaire, avec copie de confirmation "
         "obligatoire à Capital Norvex."),
        ("<b>« Partenaire »</b> : La personne physique ou morale identifiée à la Section 2.2, "
         "partenaire financier de l'Actif de Prêt, bénéficiaire des Mensualités."),
        ("<b>« Produits de Vente »</b> : L'ensemble des sommes nettes perçues lors de la vente d'un "
         "immeuble repris en paiement ou vendu sous contrôle de justice, après acquittement des frais "
         "de vente, des charges prioritaires et des frais juridiques de Capital Norvex."),
        ("<b>« RDPRM »</b> : Le Registre des droits personnels et réels mobiliers tenu par le "
         "ministère de la Justice du Québec."),
        ("<b>« Reprise »</b> : L'exercice par Capital Norvex de son droit de prise en paiement de "
         "l'immeuble ou de vente forcée sous contrôle de justice, à la suite d'un Événement de Défaut "
         "de l'Emprunteur."),
        ("<b>« Score Norvex™ »</b> : Le système d'analyse et de cotation propriétaire de Capital Norvex "
         "servant à l'évaluation et au suivi de chaque Actif de Prêt."),
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
    story.append(bp("Coordonnées bancaires pour réception des Mensualités :"))
    story.append(bp("Institution financière : __________________ &nbsp;&nbsp; Transit : __________________"))
    story.append(bp("Numéro de compte : ______________________________________________________"))
    story.append(sp())

    # ── 3 ──────────────────────────────────────────────────────────────────
    story += sec("3. NATURE ET OBJET DU PARTENARIAT")
    story += art("3.1", "Esprit du partenariat")
    story.append(bp(
        "La présente Convention repose sur une relation de partenariat véritable, fondée sur la "
        "confiance mutuelle, la transparence totale et le respect des intérêts de chacune des parties. "
        "Capital Norvex s'engage à traiter le Partenaire comme un associé stratégique à part entière, "
        "en lui versant ses Mensualités avec ponctualité et en lui fournissant toute l'information "
        "nécessaire pour suivre sa Contribution en temps réel via le portail partenaire PWA."))
    story.append(sp())
    story += art("3.2", "Structure générale")
    story.append(bp(
        "Le Partenaire avance une Contribution financière à Capital Norvex, laquelle est déployée à "
        "titre de financement immobilier privé de type terrain, acquisition ou immeuble locatif en "
        "faveur d'un Emprunteur tiers identifié à l'Annexe A. En contrepartie, le Partenaire reçoit "
        "des Mensualités correspondant aux intérêts générés par sa Contribution, versées mensuellement "
        "pour toute la durée de l'Actif de Prêt."))
    story.append(sp())
    story += art("3.3", "Champ d'application — Prêts à mensualités uniquement")
    story.append(bp(
        "La présente Convention s'applique exclusivement aux Actifs de Prêt de type terrain, acquisition "
        "et immeuble locatif, caractérisés par un remboursement mensuel des intérêts à l'Emprunteur. "
        "Elle ne s'applique pas aux prêts construction ou infrastructure à déboursements progressifs, "
        "lesquels font l'objet d'une convention distincte."))
    story.append(sp())

    # ── 4 ──────────────────────────────────────────────────────────────────
    story += sec("4. STRUCTURE FINANCIÈRE — MENSUALITÉS ET RENDEMENT")
    story += art("4.1", "Paramètres de l'Actif de Prêt")
    story.append(params_tbl([
        ["Emprunteur",                         "___________________________________________"],
        ["Type de financement",                "Terrain / Acquisition / Immeuble locatif"],
        ["Montant de la Contribution",         "$_________________________________________ CAD"],
        ["Taux d'intérêt annuel au Partenaire","_____ % par année"],
        ["Mensualité au Partenaire",           "$_________________________________________ / mois"],
        ["Date de premier versement",          "_______________"],
        ["Terme du prêt",                      "_____ mois"],
        ["Rang hypothécaire immobilier",       "1er rang — Capital Norvex Inc."],
        ["Hypothèque mobilière RDPRM",         "En faveur du Partenaire sur l'Actif de Prêt"],
        ["Mode de paiement (défaut)",          "Capital Norvex → Partenaire (compte CN désigné)"],
        ["Mode de paiement (exception)",       "Paiement direct Emprunteur → Partenaire (si autorisé par écrit)"],
        ["Score Norvex™",                      "_____ / 100"],
        ["Notaire désigné",                    "___________________________________________"],
    ]))
    story.append(sp(8))
    story += art("4.2", "Frais de dossier — Appartiennent exclusivement à Capital Norvex")
    story.append(bp(
        "Les Frais de Dossier Capital Norvex, représentant de <b>3 % à 3,5 % du montant total de "
        "l'Actif de Prêt</b>, sont prélevés lors du déboursé effectué chez le notaire et appartiennent "
        "<b>exclusivement et intégralement à Capital Norvex Inc.</b> Le Partenaire n'a aucun droit sur ces frais."))
    story.append(sp())
    story += art("4.3", "Mensualités — Appartiennent exclusivement au Partenaire")
    story.append(bp(
        "Les intérêts annuels générés par l'Actif de Prêt, au taux convenu de <b>10 % à 12 % par "
        "année</b>, calculés sur le solde de la Contribution déboursée et versés mensuellement, "
        "appartiennent <b>exclusivement et intégralement au Partenaire.</b> Capital Norvex ne conserve "
        "aucune portion des intérêts. Les Mensualités sont exigibles le premier jour ouvrable de chaque "
        "mois et versées au Partenaire dans les délais prévus à la Section 5."))
    story.append(sp())
    story += art("4.4", "Capital — Remboursement à l'échéance")
    story.append(bp(
        "Le capital de la Contribution est remboursable intégralement à l'échéance de l'Actif de Prêt, "
        "simultanément au remboursement du prêt par l'Emprunteur. Aucun remboursement partiel du capital "
        "n'est effectué en cours de terme, sauf dans les cas expressément prévus aux présentes."))
    story.append(sp())

    # ── 5 ──────────────────────────────────────────────────────────────────
    story += sec("5. MÉCANISME DE PAIEMENT DES MENSUALITÉS")
    story += art("5.1", "Mode Standard — Capital Norvex vers Partenaire (Règle)")
    story.append(bp(
        "Par défaut et en tout temps, le mécanisme de paiement applicable est le <b>Mode Standard</b> : "
        "l'Emprunteur verse sa mensualité dans le compte désigné de Capital Norvex, et Capital Norvex "
        "redistribue la Mensualité au Partenaire dans les <b>deux (2) jours ouvrables</b> suivant la "
        "réception. Ce mécanisme assure une traçabilité complète, une comptabilité rigoureuse et une "
        "protection optimale pour les deux parties. Capital Norvex tient un registre mensuel de tous "
        "les paiements effectués, accessible au Partenaire via le portail PWA."))
    story.append(sp())
    story += art("5.2", "Mode Direct — Paiement de l'Emprunteur directement au Partenaire (Exception)")
    story.append(bp(
        "À titre exceptionnel et temporaire, Capital Norvex peut autoriser par écrit le Mode Direct, "
        "dans lequel l'Emprunteur verse sa Mensualité directement au Partenaire. Ce mode est soumis "
        "aux conditions strictes suivantes :"))
    story += blt([
        "L'autorisation doit être accordée par écrit par Capital Norvex, pour une durée déterminée ne pouvant excéder douze (12) mois consécutifs ;",
        "L'Emprunteur doit transmettre à Capital Norvex, simultanément au paiement, une confirmation écrite (courriel ou avis) indiquant la date, le montant et les coordonnées du virement effectué au Partenaire ;",
        "Le Partenaire doit confirmer par écrit à Capital Norvex la réception de chaque Mensualité dans les deux (2) jours ouvrables suivant sa réception ;",
        "Capital Norvex conserve en tout temps le droit de révoquer l'autorisation de Mode Direct, avec un préavis de cinq (5) jours ouvrables, et de revenir au Mode Standard sans justification ;",
        "En l'absence de confirmation de réception par le Partenaire, Capital Norvex peut présumer le non-paiement et déclencher les procédures applicables.",
    ])
    story.append(sp())
    story += art("5.3", "Préférence institutionnelle de Capital Norvex")
    story.append(bp(
        "Capital Norvex favorise le Mode Standard en tout temps, lequel assure une gestion centralisée, "
        "une comptabilité précise et une protection juridique maximale pour l'ensemble des parties. "
        "Le Mode Direct est une accommodation temporaire offerte dans les premières phases d'exploitation "
        "du dossier ou dans des circonstances exceptionnelles justifiées. Il ne constitue pas un droit "
        "acquis du Partenaire ou de l'Emprunteur."))
    story.append(sp())
    story += art("5.4", "Portail Partenaire (PWA) — Transparence 24 h/7 jours sur tous ses prêts")
    story.append(bp(
        "Simultanément à chaque Mensualité versée, Capital Norvex transmet au Partenaire un "
        "relevé mensuel confirmant : la date du versement, le montant versé, le solde de la "
        "Contribution, les intérêts courus et tout autre renseignement pertinent. Le Partenaire "
        "a également accès <b>24 heures sur 24, 7 jours sur 7</b>, à son <b>Portail Partenaire</b> "
        "numérique sécurisé (PWA — Progressive Web Application), accessible depuis tout appareil "
        "(téléphone intelligent, tablette, ordinateur). Ce portail constitue un <b>droit "
        "contractuel</b> du Partenaire et lui donne accès en temps réel, pour <b>tous ses Actifs "
        "de Prêt</b> en cours, à :"))
    story += blt([
        "Solde de la Contribution et historique complet des Mensualités reçues",
        "Calendrier des prochains paiements et alertes sur tout retard de l'Emprunteur",
        "Documents du dossier (acte hypothécaire, évaluations, polices d'assurance, états de compte)",
        "Communications directes et messagerie sécurisée avec Capital Norvex",
        "Alertes automatiques pour tout événement matériel affectant le dossier",
    ])
    story.append(sp())
    story += art("5.5", "Norvex Track™ — Module de suivi et d'audit 24 h/7 jours")
    story.append(bp(
        "Capital Norvex met également à la disposition du Partenaire le module "
        "<b>Norvex Track™</b>, un outil technologique propriétaire intégré au Portail "
        "Partenaire qui permet au Partenaire, <b>24 heures sur 24, 7 jours sur 7</b>, de :"))
    story += blt([
        "<b>Recevoir</b> en temps réel chaque confirmation de Mensualité, accompagnée du relevé détaillé et de la pièce justificative;",
        "<b>Examiner</b> en ligne l'ensemble des documents du dossier (acte hypothécaire, polices d'assurance, évaluations, quittances) depuis tout appareil;",
        "<b>Consulter</b> en temps réel le solde de la Contribution, les intérêts courus, le calendrier des paiements et tout événement matériel affectant le dossier;",
        "<b>Recevoir</b> automatiquement toute alerte en cas de retard, défaut ou changement matériel — incluant un avis écrit dans les cinq (5) jours ouvrables conformément à la Section 7.3;",
        "<b>Auditer</b> à tout moment l'historique complet des opérations sur l'Actif de Prêt, garantissant une traçabilité absolue.",
    ])
    story.append(bp(
        "L'utilisation de <b>Norvex Track™</b> par le Partenaire constitue une "
        "<b>garantie supplémentaire de transparence</b> : le Partenaire conserve en tout "
        "temps une visibilité complète et indépendante sur son Actif de Prêt, sans avoir "
        "à attendre un rapport périodique. Ce module est complémentaire au rapport mensuel "
        "transmis par Capital Norvex (Section 7.3) et au Portail Partenaire (Section 5.4)."))
    story.append(sp())

    # ── 6 ──────────────────────────────────────────────────────────────────
    story += sec("6. GARANTIES DU PARTENAIRE — HYPOTHÈQUE MOBILIÈRE AU RDPRM")
    story += art("6.1", "Publication obligatoire avant le déboursé")
    story.append(bp(
        "En garantie du remboursement de sa Contribution et du versement des Mensualités, Capital Norvex "
        "consent en faveur du Partenaire une hypothèque mobilière sans dépossession sur l'Actif de Prêt "
        "identifié à l'Annexe A, conformément aux articles 2660 et suivants du Code civil du Québec. "
        "Cette sûreté doit être publiée par le Partenaire au RDPRM dans les cinq (5) jours ouvrables "
        "suivant la signature des présentes et, dans tous les cas, avant tout déboursé chez le notaire."))
    story.append(sp())
    story += art("6.2", "Portée de la sûreté")
    story.append(bp(
        "L'Hypothèque Mobilière porte sur les droits de créance de Capital Norvex à l'encontre de "
        "l'Emprunteur en vertu de l'Actif de Prêt. Elle ne confère au Partenaire aucun droit réel "
        "immobilier direct sur l'immeuble hypothéqué par l'Emprunteur. La sûreté garantit le "
        "remboursement de la Contribution et le versement de toutes les Mensualités dues."))
    story.append(sp())
    story += art("6.3", "Radiation à l'échéance")
    story.append(bp(
        "Le Partenaire s'engage irrévocablement à radier l'inscription au RDPRM dans les dix (10) "
        "jours ouvrables suivant la réception du remboursement intégral de sa Contribution et de toutes "
        "les Mensualités dues. Tout défaut de radiation dans ce délai permet à Capital Norvex de procéder "
        "à la radiation aux frais exclusifs du Partenaire."))
    story.append(sp())

    # ── 7 ──────────────────────────────────────────────────────────────────
    story += sec("7. GESTION EXCLUSIVE PAR CAPITAL NORVEX — DANS UN ESPRIT DE BONNE FOI")
    story += art("7.1", "Principe de la gestion exclusive et de la bonne foi")
    story.append(bp(
        "Capital Norvex assume la gestion exclusive de l'Actif de Prêt et de la relation "
        "opérationnelle avec l'Emprunteur. Cette gestion s'exerce <b>en tout temps dans un esprit "
        "de bonne foi</b> et de transparence absolue envers le Partenaire, conformément aux articles "
        "6 et 1375 du <i>Code civil du Québec</i>. Le Partenaire ne s'adresse pas directement à "
        "l'Emprunteur ni à ses représentants, mais conserve en tout temps son droit à l'information "
        "complète et à la consultation pour toute décision matérielle, tel que prévu aux Sections 7.3 "
        "et 8.4 des présentes."))
    story.append(sp())
    story += art("7.2", "Pouvoirs exclusifs de Capital Norvex")
    story += blt([
        "Gérer l'ensemble de la relation contractuelle avec l'Emprunteur",
        "Déclarer un Événement de Défaut et exercer tous les recours",
        "Décider de procéder à une Reprise ou une vente sous contrôle de justice",
        "Nommer un séquestre ou tout autre mandataire",
        "Négocier et conclure tout règlement avec l'Emprunteur",
        "Autoriser ou révoquer le Mode Direct de paiement",
        "Gérer l'immeuble en cas de Reprise",
    ])
    story.append(sp())
    story += art("7.3", "Transparence et rapports mensuels")
    story.append(bp(
        "Capital Norvex transmet au Partenaire un rapport mensuel complet simultanément à chaque "
        "Mensualité, incluant l'état du dossier, le solde de la Contribution, et tout événement matériel. "
        "En cas d'Événement de Défaut de l'Emprunteur, Capital Norvex avise le Partenaire par écrit "
        "dans les cinq (5) jours ouvrables et le consulte pour déterminer la meilleure stratégie de protection."))
    story.append(sp())

    # ── 8 ──────────────────────────────────────────────────────────────────
    story += sec("8. DÉFAUT DE L'EMPRUNTEUR — GESTION CONJOINTE EN PARTENARIAT")
    story += art("8.1", "Capital Norvex n'assume pas les Mensualités impayées de l'Emprunteur")
    story.append(bp(
        "En cas de non-paiement d'une Mensualité par l'Emprunteur, <b>Capital Norvex n'assume aucune "
        "obligation de substitution et ne verse pas la Mensualité au Partenaire à la place de l'Emprunteur "
        "défaillant.</b> Capital Norvex n'est ni garant ni caution des obligations de paiement de "
        "l'Emprunteur envers le Partenaire."))
    story.append(sp())
    story += art("8.2", "Capitalisation des Mensualités impayées")
    story.append(bp(
        "Les Mensualités non perçues en raison du défaut de l'Emprunteur <b>sont automatiquement "
        "capitalisées</b> et s'ajoutent au solde dû au Partenaire. Ces montants capitalisés portent "
        "eux-mêmes intérêt au taux contractuel. L'intégralité des Mensualités capitalisées est remboursée "
        "au Partenaire à même les Produits de Vente lors de la Reprise, en priorité et avant toute autre distribution."))
    story.append(sp())
    story += art("8.3", "Le défaut de l'Emprunteur ne constitue pas un défaut de Capital Norvex")
    story.append(bp(
        "Les parties reconnaissent expressément qu'un Événement de Défaut de l'Emprunteur "
        "<b>ne constitue en aucun cas un Événement de Défaut de Capital Norvex</b> envers le "
        "Partenaire. Capital Norvex demeure pleinement engagée à gérer le dossier avec diligence "
        "et de bonne foi jusqu'à la récupération complète des sommes dues."))
    story.append(sp())
    story += art("8.4", "Gestion conjointe et décisions stratégiques en partenariat")
    story.append(bp(
        "Dès la constatation d'un Événement de Défaut de l'Emprunteur, Capital Norvex et le "
        "Partenaire <b>travaillent en partenariat actif</b>. Capital Norvex assume la gestion "
        "opérationnelle, mais les décisions stratégiques importantes sont prises <b>conjointement</b> "
        "par les deux parties, selon le processus suivant :"))
    story += num_list([
        ("1.", "<b>Avis et consultation immédiats :</b> Dans les cinq (5) jours ouvrables suivant le constat du défaut, Capital Norvex avise simultanément l'Emprunteur et le Partenaire par écrit, et convoque le Partenaire à une réunion de consultation (en personne ou par vidéoconférence) dans les sept (7) jours suivants."),
        ("2.", "<b>Avis de 60 jours à l'Emprunteur :</b> Capital Norvex transmet à l'Emprunteur un avis de défaut formel lui accordant soixante (60) jours pour remédier à sa situation, conformément aux articles 2757 et suivants du <i>Code civil du Québec</i>. Durant ce délai, Capital Norvex tient le Partenaire pleinement informé."),
        ("3.", "<b>Décision conjointe à l'expiration du 60 jours :</b> À défaut de remédiation, Capital Norvex et le Partenaire prennent <b>conjointement</b> la décision quant à la suite à donner : (a) <b>prise en paiement</b> par Capital Norvex (avec indemnisation appropriée du Partenaire); (b) <b>vente sous contrôle de justice</b>; (c) toute autre solution conforme à la loi. À défaut d'entente entre les parties dans les quinze (15) jours, la procédure de médiation prévue à la Section 12.5 s'applique."),
        ("4.", "<b>Choix du courtier immobilier :</b> Si l'option retenue est la vente, le choix du courtier immobilier est fait <b>conjointement</b> par les parties. Le mandat de vente est signé conjointement."),
        ("5.", "<b>Distribution des produits de vente :</b> Capital Norvex procède à la distribution des Produits de Vente selon l'ordre de priorité prévu à la Section 8.6, en toute transparence avec le Partenaire."),
    ])
    story.append(sp())
    story += art("8.5", "Frais juridiques de Reprise — À la charge de Capital Norvex")
    story.append(bp(
        "L'ensemble des frais juridiques, honoraires d'avocats, frais notariaux et autres coûts "
        "engagés dans le cadre d'une Reprise sont prélevés en premier rang sur les Produits de Vente. "
        "Le Partenaire ne supporte aucun frais additionnel au-delà de sa Contribution initiale. "
        "Capital Norvex assume la responsabilité de mener ces procédures avec diligence et compétence."))
    story.append(sp())
    story += art("8.6", "Distribution des Produits de Vente en cas de Reprise")
    story.append(bp("Les Produits de Vente sont distribués dans l'ordre de priorité suivant :"))
    story += num_list([
        ("1.", "Frais juridiques et frais directs de réalisation — Capital Norvex."),
        ("2.", "Remboursement intégral de la Contribution du Partenaire."),
        ("3.", "Remboursement de toutes les Mensualités capitalisées non perçues dues au Partenaire."),
        ("4.", "Remboursement à Capital Norvex de tout montant avancé en lien avec la Reprise."),
        ("5.", "Tout solde résiduel appartient à Capital Norvex."),
    ])
    story.append(sp())

    # ── 9 ──────────────────────────────────────────────────────────────────
    story += sec("9. ENGAGEMENT DU PARTENAIRE POUR LA DURÉE DE L'ACTIF DE PRÊT")
    story += art("9.1", "Engagement ferme jusqu'au terme de l'Actif de Prêt")
    story.append(bp(
        "Le Partenaire s'engage à maintenir sa Contribution en place pour toute la durée de l'Actif "
        "de Prêt, jusqu'au remboursement intégral par l'Emprunteur. Une fois le dossier mené à terme, "
        "le Partenaire est libre de ne pas reconduire son partenariat et peut récupérer la totalité de sa Contribution "
        "avec les Mensualités dues. Aucun retrait anticipé n'est autorisé pendant la durée de l'Actif "
        "de Prêt, sauf dans les cas expressément prévus à la Section 9.3."))
    story.append(sp())
    story += art("9.2", "Cession et nantissement — Accord raisonnable")
    story.append(bp(
        "Le Partenaire peut céder, transférer, nantir ou grever ses droits en vertu des présentes "
        "avec le consentement écrit préalable de Capital Norvex, lequel <b>ne peut être "
        "déraisonnablement refusé</b>. Capital Norvex examine toute demande de bonne foi et dans "
        "un délai raisonnable."))
    story.append(sp())
    story += art("9.3", "Exceptions — Sortie anticipée autorisée")
    story += blt([
        "Capital Norvex y consent expressément par écrit et prend les dispositions nécessaires pour remplacer intégralement la Contribution sans interruption du financement ;",
        "Capital Norvex décide de rembourser le Partenaire et de le remplacer, conformément à la Section 9.4 ;",
        "<b>Manquement grave de Capital Norvex</b> à ses obligations en vertu des présentes (notamment fraude documentée, défaut de transparence persistant, violation matérielle des engagements de bonne foi), non remédié dans les trente (30) jours suivant un avis écrit du Partenaire.",
    ])
    story.append(sp())
    story += art("9.4", "Droit de remplacement de Capital Norvex — Encadrement")
    story.append(bp(
        "Capital Norvex peut, en cas de motif sérieux et objectif, remplacer le Partenaire par un "
        "autre partenaire ou ses propres fonds, en respectant les conditions cumulatives suivantes :"))
    story += blt([
        "Préavis écrit minimum de <b>trente (30) jours</b> au Partenaire, exposant les motifs;",
        "Remise au Partenaire, en un seul versement : (i) l'intégralité de la Contribution; (ii) toutes les Mensualités dues et non encore versées à la date du remboursement;",
        "<b>Aucune pénalité ou retenue</b> ne peut être imposée au Partenaire dans le cadre de ce remplacement;",
        "Le Partenaire procède à la radiation de l'Hypothèque Mobilière dans les dix (10) jours ouvrables suivant la réception complète des sommes dues.",
    ])
    story.append(sp())
    story += art("9.5", "Aucune pénalité financière en cas de retrait non conforme")
    story.append(bp(
        "Si le Partenaire procédait à un retrait non conforme aux Sections 9.1 à 9.4, "
        "<b>aucune pénalité financière</b> ne lui serait imposée. Les parties s'engagent à se "
        "rencontrer de bonne foi pour trouver une solution conjointe permettant la continuité du "
        "financement. À défaut de solution amiable, le différend sera soumis à la procédure de "
        "médiation prévue à la Section 12.5. Les recours judiciaires sont limités à la réparation "
        "du préjudice réel et documenté (à l'exclusion de toute pénalité contractuelle forfaitaire)."))
    story.append(sp())

    # ── 10 ──────────────────────────────────────────────────────────────────
    story += sec("10. DÉCLARATIONS ET GARANTIES DES PARTIES")
    story += art("10.1", "Déclarations du Partenaire")
    story += blt([
        "Il est dûment constitué, autorisé et en règle selon les lois applicables",
        "Il possède la pleine capacité légale et financière pour contracter les présentes",
        "La Contribution provient de fonds légaux, déclarés et conformes aux exigences réglementaires",
        "Il n'existe aucun litige ou charge susceptible d'affecter ses droits",
        "Il a obtenu tous les avis juridiques et fiscaux nécessaires",
    ])
    story.append(sp())
    story += art("10.2", "Déclarations de Capital Norvex")
    story += blt([
        "Elle est dûment constituée et autorisée à exercer ses activités au Québec et en Ontario",
        "L'Actif de Prêt a été analysé et approuvé conformément à ses politiques internes",
        "Le Score Norvex™ applicable a été calculé de bonne foi",
        "Elle versera les Mensualités au Partenaire avec ponctualité selon les termes des présentes",
    ])
    story.append(sp())

    # ── 11 ──────────────────────────────────────────────────────────────────
    story += sec("11. CONFIDENTIALITÉ")
    story.append(sp(4))
    story.append(bp(
        "Chacune des parties s'engage à traiter comme strictement confidentielle toute information "
        "reçue de l'autre partie dans le cadre des présentes. Cette obligation survit à la résiliation "
        "ou à l'expiration des présentes pour une période de cinq (5) ans."))
    story.append(sp())

    # ── 12 ──────────────────────────────────────────────────────────────────
    story += sec("12. DISPOSITIONS GÉNÉRALES")
    story += art("12.1", "Droit applicable et compétence")
    story.append(bp(
        "La présente Convention est régie et interprétée selon les <b>lois de la province de "
        "Québec et les lois fédérales du Canada applicables</b>. Tout différend relève de la "
        "compétence exclusive des tribunaux du district judiciaire de Montréal, sous réserve des "
        "Sections 12.5 et 12.6."))
    story.append(sp())
    story += art("12.2", "Amendements, avis et cession")
    story += blt([
        "<b>Amendements :</b> Toute modification doit être écrite et signée par les deux parties.",
        "<b>Avis :</b> Tout avis doit être donné par écrit, par courriel avec accusé de réception ou par courrier recommandé.",
        "<b>Cession :</b> Conformément à la Section 9.2, la cession des droits du Partenaire est permise avec consentement écrit préalable de Capital Norvex, lequel ne peut être déraisonnablement refusé.",
    ])
    story.append(sp())
    story += art("12.3", "Divisibilité, intégralité et renonciation")
    story += blt([
        "<b>Divisibilité :</b> Toute clause invalide n'affecte pas la validité du reste de la Convention.",
        "<b>Intégralité :</b> La présente Convention, ensemble avec ses Annexes et l'Hypothèque Mobilière s'y rattachant, constitue l'entente complète des parties.",
        "<b>Renonciation :</b> Aucune tolérance ne constitue une renonciation permanente.",
    ])
    story.append(sp())
    story += art("12.4", "Langue et interprétation")
    story.append(bp(
        "Le <b>français est la langue officielle</b> de la présente Convention. Toute traduction "
        "anglaise est fournie à titre de courtoisie; en cas de divergence, la version française "
        "prévaut. Les parties reconnaissent avoir négocié les présentes en français et avoir "
        "expressément renoncé à l'application de l'article 1432 du <i>Code civil du Québec</i> "
        "concernant l'interprétation contre le rédacteur."))
    story.append(sp())
    story += art("12.5", "Médiation obligatoire avant tout recours judiciaire")
    story.append(bp(
        "Les parties s'engagent à <b>tenter de résoudre à l'amiable, par voie de médiation</b>, "
        "tout différend découlant des présentes <b>avant d'introduire toute procédure judiciaire</b>. "
        "La procédure est la suivante :"))
    story += num_list([
        ("1.", "Avis écrit décrivant le différend, transmis à l'autre partie."),
        ("2.", "Quinze (15) jours pour tenter de résoudre par discussion directe et de bonne foi."),
        ("3.", "À défaut, désignation conjointe d'un médiateur indépendant dans les dix (10) jours."),
        ("4.", "Au moins une (1) séance de médiation, frais partagés à parts égales."),
        ("5.", "À défaut de règlement dans les soixante (60) jours suivant la nomination du médiateur, recours judiciaire possible."),
        ("6.", "<b>Exception :</b> Mesures conservatoires ou injonctions urgentes pour préserver les droits hypothécaires ou prévenir un préjudice irréparable."),
    ])
    story.append(sp())
    story += art("12.6", "Bonne foi et collaboration")
    story.append(bp(
        "Les parties s'engagent à exécuter la présente Convention <b>de bonne foi</b>, conformément "
        "aux articles 6, 7 et 1375 du <i>Code civil du Québec</i>, dans un esprit de collaboration, "
        "de transparence et de respect mutuel."))
    story.append(sp())
    story += art("12.7", "Indissociabilité avec l'Hypothèque Mobilière")
    story.append(bp(
        "La présente Convention de partenariat et l'Hypothèque Mobilière sur Créance Individuelle "
        "consentie par Capital Norvex en faveur du Partenaire forment <b>un ensemble contractuel "
        "indissociable</b>. Les deux documents doivent être lus, interprétés et exécutés conjointement. "
        "Toute violation des termes de la présente Convention constitue automatiquement un Événement "
        "de Défaut au sens de l'Hypothèque Mobilière, et inversement. En cas de divergence, "
        "l'interprétation la plus protectrice du Partenaire (créancier hypothécaire) prévaudra."))
    story.append(sp())

    # ── 13 SIGNATURES ───────────────────────────────────────────────────────
    story += sec("13. SIGNATURES")
    story.append(sp(4))
    story.append(bp(
        "EN FOI DE QUOI, les parties ont signé la présente Convention de partenariat à mensualités "
        "à la date indiquée ci-dessous, après en avoir pris pleinement connaissance et avoir obtenu "
        "les conseils juridiques et fiscaux qu'elles ont jugé appropriés."))
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
        ["Emprunteur",                         "___________________________________________"],
        ["Type de financement",                "Terrain / Acquisition / Immeuble locatif"],
        ["Montant de la Contribution",         "$_________________________________________ CAD"],
        ["Taux d'intérêt annuel au Partenaire","_____ % par année"],
        ["Mensualité au Partenaire",           "$_________________________________________ / mois"],
        ["Date de premier versement",          "_______________"],
        ["Terme du prêt",                      "_____ mois"],
        ["Rang hypothécaire immobilier",       "1er rang — Capital Norvex Inc."],
        ["Hypothèque mobilière RDPRM",         "En faveur du Partenaire sur l'Actif de Prêt"],
        ["Mode de paiement (défaut)",          "Capital Norvex → Partenaire (compte CN désigné)"],
        ["Mode de paiement (exception)",       "Paiement direct Emprunteur → Partenaire (si autorisé par écrit)"],
        ["Score Norvex™",                      "_____ / 100"],
        ["Notaire désigné",                    "___________________________________________"],
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
    print(f"✅  Convention_Partenariat_Mensualites_CapitalNorvex.pdf généré.")


if __name__ == "__main__":
    main()
