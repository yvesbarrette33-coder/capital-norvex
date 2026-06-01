from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Flowable, Image as RLImage
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT

# ── Palette ───────────────────────────────────────────────────────────────────
DARK      = HexColor("#0a0d13")
DARK2     = HexColor("#12182a")
GOLD      = HexColor("#C9A84C")
GOLD2     = HexColor("#b8975a")
GOLD_PALE = HexColor("#e8d5a0")
CREAM     = HexColor("#f5f0e8")
CREAM2    = HexColor("#e8e0ce")
GREY_LT   = HexColor("#d4c9b0")
GREY_MED  = HexColor("#8a7d5f")
SILVER    = HexColor("#c8c8c8")
WHITE     = HexColor("#ffffff")
RED_SOFT  = HexColor("#8B2020")

PAGE_W, PAGE_H = letter
MARGIN  = 0.6 * inch
COL_W   = PAGE_W - 2 * MARGIN

EMBLEM_PATH = "/Users/yvesbarrette/Desktop/capitalnorvex-site/CapitalNorvex_Scripts/logos/emblem_header.png"
COVER_PATH  = "/Users/yvesbarrette/Desktop/capitalnorvex-site/CapitalNorvex_Scripts/logos/logo_cover.png"

# ── Flowables ─────────────────────────────────────────────────────────────────
class GoldLine(Flowable):
    def __init__(self, thickness=1.2, color=None):
        Flowable.__init__(self)
        self.thickness = thickness
        self.color = color or GOLD
        self.height = thickness + 2
        self.width = None
    def wrap(self, aW, aH):
        self.width = aW
        return (aW, self.height)
    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)

class DoubleLine(Flowable):
    def __init__(self):
        Flowable.__init__(self); self.height = 7; self.width = None
    def wrap(self, aW, aH):
        self.width = aW; return (aW, self.height)
    def draw(self):
        self.canv.setStrokeColor(GOLD); self.canv.setLineWidth(2)
        self.canv.line(0, 6, self.width, 6)
        self.canv.setStrokeColor(SILVER); self.canv.setLineWidth(0.6)
        self.canv.line(0, 1, self.width, 1)

# ── Header / Footer ───────────────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    w, h = letter
    canvas.setFillColor(DARK)
    canvas.rect(0, h-54, w, 54, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, h-57, w, 3, fill=1, stroke=0)
    canvas.drawImage(EMBLEM_PATH, MARGIN, h-47,  # uniformisé : top du logo à 5 px du sommet de la page
                     width=38, height=42, preserveAspectRatio=True, mask='auto')
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(MARGIN+46, h-30, "CAPITAL NORVEX")
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(MARGIN+46, h-43, "Financement Privé Institutionnel  |  Québec & Ontario")
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawRightString(w-MARGIN, h-28, "SOMMAIRE EXÉCUTIF PARTENAIRE")
    canvas.setFillColor(GREY_LT)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(w-MARGIN, h-42, "CONFIDENTIEL — USAGE EXCLUSIF")
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(w-MARGIN, h-52, f"p. {doc.page}")
    canvas.setFillColor(DARK)
    canvas.rect(0, 0, w, 50, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, 50, w, 1.5, fill=1, stroke=0)
    # Ligne du haut — confidentialité (centrée, gold pour la marque)
    canvas.setFillColor(GOLD_PALE)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawCentredString(w/2, 32, "CAPITAL NORVEX  ·  Document confidentiel — partenaire financier désigné")
    # Ligne du bas — adresse complète (centrée, gris clair pour les coordonnées)
    canvas.setFillColor(GREY_LT)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(w/2, 14, "2705-1000 André-Prévost  ·  Île-des-Sœurs (Verdun)  ·  Montréal, QC H3E 0G2   |   1-(438)-533-PRET (7738)   |   info@capitalnorvex.com   |   capitalnorvex.com")
    canvas.restoreState()

# ── Styles ────────────────────────────────────────────────────────────────────
def S(name, **kw): return ParagraphStyle(name, **kw)
ST = dict(
    cover_t  = S("ct",  fontName="Helvetica-Bold",   fontSize=26, textColor=WHITE,    alignment=TA_CENTER, spaceAfter=3,  leading=32),
    cover_s  = S("cs",  fontName="Helvetica",         fontSize=11, textColor=GOLD_PALE,alignment=TA_CENTER, spaceAfter=4,  leading=16),
    slogan   = S("sl",  fontName="Helvetica-Oblique", fontSize=10, textColor=GOLD2,    alignment=TA_CENTER, spaceAfter=3),
    conf     = S("cf",  fontName="Helvetica-Oblique", fontSize=7.5,textColor=RED_SOFT, alignment=TA_CENTER, spaceAfter=4),
    sec_t    = S("st",  fontName="Helvetica-Bold",    fontSize=10, textColor=GOLD,     spaceAfter=2, spaceBefore=2),
    h3       = S("h3",  fontName="Helvetica-Bold",    fontSize=9.5,textColor=DARK,     spaceAfter=3, spaceBefore=3),
    body     = S("bd",  fontName="Helvetica",         fontSize=8.5,textColor=DARK,     alignment=TA_JUSTIFY, spaceAfter=3, leading=13),
    bullet   = S("bl",  fontName="Helvetica",         fontSize=8.5,textColor=DARK,     spaceAfter=3, leading=13, leftIndent=14),
    note     = S("nt",  fontName="Helvetica-Oblique", fontSize=7.5,textColor=GREY_MED, alignment=TA_CENTER, spaceAfter=4),
    kpi_num  = S("kn",  fontName="Helvetica-Bold",    fontSize=17, textColor=GOLD,     alignment=TA_CENTER, spaceAfter=1, leading=24),
    kpi_lbl  = S("kl",  fontName="Helvetica",         fontSize=7.5,textColor=GREY_MED, alignment=TA_CENTER, spaceAfter=0),
    ai_title = S("ait", fontName="Helvetica-Bold",    fontSize=8.5,textColor=GOLD,     spaceAfter=3, alignment=TA_LEFT),
    ai_body  = S("aib", fontName="Helvetica-Oblique", fontSize=8.5,textColor=GREY_MED, alignment=TA_JUSTIFY, leading=13, spaceAfter=0),
    tbl_hdr  = S("th2", fontName="Helvetica-Bold",    fontSize=8.5,textColor=GOLD,     spaceAfter=0),
    tbl_lbl  = S("tl",  fontName="Helvetica-Bold",    fontSize=8.5,textColor=GREY_MED, spaceAfter=0),
    tbl_val  = S("tv",  fontName="Helvetica",         fontSize=8.5,textColor=DARK,     spaceAfter=0, leading=12),
    white_b  = S("wb",  fontName="Helvetica-Bold",    fontSize=12, textColor=GOLD,     alignment=TA_CENTER, spaceAfter=4),
    white_sm = S("wsm", fontName="Helvetica",         fontSize=8.5,textColor=GREY_LT,  alignment=TA_CENTER, spaceAfter=3),
    white_em = S("wem", fontName="Helvetica-Bold",    fontSize=9,  textColor=WHITE,    alignment=TA_CENTER, spaceAfter=0),
    step_num = S("sn",  fontName="Helvetica-Bold",    fontSize=14, textColor=GOLD,     alignment=TA_CENTER, spaceAfter=0, leading=16),
    step_t   = S("stt", fontName="Helvetica-Bold",    fontSize=8.5,textColor=DARK,     spaceAfter=2),
    step_b   = S("stb", fontName="Helvetica",         fontSize=8,  textColor=GREY_MED, leading=12, spaceAfter=0),
)

def bul(t): return Paragraph(f"•  {t}", ST["bullet"])
def body(t): return Paragraph(t, ST["body"])

# ── Section bar ───────────────────────────────────────────────────────────────
def sec(title):
    tbl = Table([[Paragraph(title, ST["sec_t"])]], colWidths=[COL_W])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), DARK),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LINEABOVE",     (0,0),(-1,0), 0.5, GOLD2),
        ("LINEBELOW",     (0,-1),(-1,-1), 2.5, GOLD),
    ]))
    return [Spacer(1,4), tbl, Spacer(1,4)]

# ── Zone AI (zone réservée au contenu généré automatiquement) ─────────────────
def ai_zone(title, lines, height_pt=None):
    """Zone visuelle premium pour indiquer le contenu généré par l'agent AI."""
    h = height_pt or (len(lines) * 13 + 32)
    content_rows = []
    content_rows.append([Paragraph(f"[ AI ]  {title}", ST["ai_title"])])
    for line in lines:
        content_rows.append([Paragraph(line, ST["ai_body"])])
    tbl = Table(content_rows, colWidths=[COL_W - 24])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), DARK2),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 12),
        ("TOPPADDING",    (0,0),(0,0), 10),
        ("BOTTOMPADDING", (0,-1),(-1,-1), 10),
        ("TOPPADDING",    (0,1),(-1,-1), 2),
        ("BOTTOMPADDING", (0,0),(-1,-2), 2),
        ("LINEABOVE",     (0,0),(-1,0), 1.5, GOLD),
        ("LINEBELOW",     (0,-1),(-1,-1), 1, GOLD2),
        ("LINEBEFORE",    (0,0),(0,-1), 1.5, GOLD),
        ("LINEAFTER",     (-1,0),(-1,-1), 0.5, GOLD2),
    ]))
    outer = Table([[tbl]], colWidths=[COL_W])
    outer.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(-1,-1), 0),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ]))
    return outer

# ── Photo placeholder ─────────────────────────────────────────────────────────
def photo_box(label, w, h_pt):
    t = Table([[Paragraph(label, ParagraphStyle(
        "pp", fontName="Helvetica-Bold", fontSize=8.5,
        textColor=GREY_MED, alignment=TA_CENTER))]],
        colWidths=[w])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), DARK2),
        ("TOPPADDING",    (0,0),(-1,-1), h_pt * 0.38),
        ("BOTTOMPADDING", (0,0),(-1,-1), h_pt * 0.38),
        ("LINEABOVE",     (0,0),(-1,0), 1, GOLD2),
        ("LINEBELOW",     (0,-1),(-1,-1), 1, GOLD2),
        ("LINEBEFORE",    (0,0),(0,-1), 1, GOLD2),
        ("LINEAFTER",     (-1,0),(-1,-1), 1, GOLD2),
    ]))
    return t

# ── Tableau données ───────────────────────────────────────────────────────────
def dtable(rows, widths):
    p_rows = []
    for i, row in enumerate(rows):
        p_row = []
        for j, cell in enumerate(row):
            if i == 0:
                style = ST["tbl_hdr"]
            elif j == 0:
                style = ST["tbl_lbl"]
            else:
                style = ST["tbl_val"]
            p_row.append(Paragraph(str(cell), style))
        p_rows.append(p_row)
    t = Table(p_rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), DARK),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [CREAM, CREAM2]),
        ("GRID",          (0,0),(-1,-1), 0.4, GREY_LT),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("LINEABOVE",     (0,0),(-1,0), 0.5, GOLD2),
        ("LINEBELOW",     (0,-1),(-1,-1), 1.5, GOLD2),
    ]))
    return t

# ── KPI row ───────────────────────────────────────────────────────────────────
def kpi_row(items):
    n = len(items)
    cw = COL_W / n
    nums = [Paragraph(v, ST["kpi_num"]) for v, l in items]
    lbls = [Paragraph(l, ST["kpi_lbl"]) for v, l in items]
    t = Table([nums, lbls], colWidths=[cw]*n)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), CREAM),
        ("TOPPADDING",    (0,0),(-1,0), 8),
        ("BOTTOMPADDING", (0,1),(-1,-1), 7),
        ("TOPPADDING",    (0,1),(-1,-1), 2),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ("RIGHTPADDING",  (0,0),(-1,-1), 4),
        ("LINEABOVE",     (0,0),(-1,0), 2, GOLD),
        ("LINEBELOW",     (0,-1),(-1,-1), 1.5, GOLD2),
        ("LINEBEFORE",    (1,0),(n-1,-1), 0.4, GREY_LT),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    return t

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — COUVERTURE
# ══════════════════════════════════════════════════════════════════════════════
def page_couverture(story):
    story.append(Spacer(1, 0.15*inch))
    img = RLImage(COVER_PATH, width=120, height=130)
    img.hAlign = "CENTER"
    story.append(img)
    story.append(Spacer(1, 3))
    tbl = Table([[Paragraph("SOMMAIRE EXÉCUTIF", ST["cover_t"])]], colWidths=[COL_W])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), DARK),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LINEABOVE",     (0,0),(-1,0), 3, GOLD),
        ("LINEBELOW",     (0,-1),(-1,-1), 3, GOLD),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 3))
    story.append(Paragraph("OPPORTUNITÉ DE FINANCEMENT PARTENAIRE", ST["cover_s"]))
    story.append(Spacer(1, 2))
    info = [
        ["PROJET",          "_______________________________________________"],
        ["LOCALISATION",    "_______________________________________________"],
        ["TYPE DE PRÊT",    "Construction  /  Terrain  /  Acquisition"],
        ["MONTANT",         "_______________________________________________"],
        ["RENDEMENT CIBLE", "_______________________________________________"],
        ["DURÉE",           "_______________________________________________"],
        ["DATE",            "_______________________________________________"],
        ["DESTINATAIRE",    "_______________________________________________"],
    ]
    t = Table(info, colWidths=[1.7*inch, 4.0*inch], hAlign="CENTER")
    t.setStyle(TableStyle([
        ("FONTNAME",      (0,0),(0,-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 9),
        ("TEXTCOLOR",     (0,0),(0,-1), GOLD),
        ("TEXTCOLOR",     (1,0),(1,-1), DARK),
        ("ROWBACKGROUNDS",(0,0),(-1,-1), [CREAM, CREAM2]),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(0,-1), 12),
        ("LEFTPADDING",   (1,0),(1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("LINEBELOW",     (0,-1),(-1,-1), 2, GOLD),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(Spacer(1, 3))
    story.append(DoubleLine())
    story.append(Spacer(1, 3))
    story.append(Paragraph("Capital structuré.  Ambition maîtrisée.", ST["slogan"]))
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        "CONFIDENTIEL — Document préparé exclusivement à l'intention du partenaire financier désigné. "
        "Ne pas reproduire ni distribuer sans autorisation écrite de Capital Norvex.",
        ST["conf"]))
    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — FAITS SAILLANTS + APERÇU
# ══════════════════════════════════════════════════════════════════════════════
def page_faits_saillants(story):
    story += sec("FAITS SAILLANTS DE L'OPPORTUNITÉ")
    story.append(kpi_row([
        ("$  __________", "Montant du prêt"),
        ("_____ %",       "Taux d'intérêt annuel"),
        ("_____ mois",    "Durée initiale"),
        ("_____ %",       "LTV"),
    ]))
    story.append(Spacer(1, 3))
    story.append(kpi_row([
        ("$  __________", "Votre participation"),
        ("_____ %",       "Rendement annuel cible"),
        ("1er rang",      "Rang hypothécaire"),
        ("$  __________", "Intérêts mensuels estimés"),
    ]))
    story.append(Spacer(1, 3))

    story += sec("APERÇU DU PROJET")
    # Photo + infos rapides côte à côte
    photo = photo_box("PHOTO PRINCIPALE DU PROJET\n— insérer ici —", w=COL_W * 0.47, h_pt=1.1*inch)
    infos = dtable([
        ["Paramètre",           "Détail"],
        ["Adresse",             "________________________________"],
        ["Municipalité / MRC",  "________________________________"],
        ["Type de développement","________________________________"],
        ["Nombre d'unités",     "________________________________"],
        ["Valeur à l'achèvement","$  ________________________ CAD"],
        ["Coût total du projet", "$  ________________________ CAD"],
        ["Mise de fonds",       "$  ____________  ( ______ %)"],
    ], [1.5*inch, 1.93*inch])
    row = Table([[photo, infos]], colWidths=[COL_W*0.48, COL_W*0.50])
    row.setStyle(TableStyle([
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(0,-1), 10),
        ("RIGHTPADDING", (1,0),(1,-1), 0),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ]))
    story.append(row)
    story.append(Spacer(1, 2))

    # Zone AI — résumé exécutif du projet (1 paragraphe)
    story.append(ai_zone(
        "Résumé exécutif généré par l'agent Capital Norvex",
        [
            "Description complète du projet rédigée automatiquement à partir du dossier complet de l'emprunteur.",
            "Localisation, type de développement, positionnement de marché, avantages concurrentiels du projet.",
            "Points forts identifiés par Capital Norvex : expérience de l'équipe, solidité financière, qualité de l'actif.",
            "Conclusion préliminaire et recommandation de Capital Norvex pour présentation au partenaire.",
        ]
    ))
    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — ANALYSE DÉTAILLÉE DU PROJET ET DE L'EMPRUNTEUR
# ══════════════════════════════════════════════════════════════════════════════
def page_analyse(story):
    story += sec("ANALYSE DU PROJET — RAPPORT CAPITAL NORVEX")

    # Intro AI badge
    badge = Table([[Paragraph(
        "[ CONTENU GÉNÉRÉ PAR L'AGENT AI CAPITAL NORVEX ]  "
        "Le texte suivant est produit automatiquement à partir de la documentation complète "
        "du dossier, de l'entretien de qualification et de l'analyse Score Norvex™.",
        ParagraphStyle("badge", fontName="Helvetica-Oblique", fontSize=8,
                       textColor=GREY_MED, alignment=TA_JUSTIFY, spaceAfter=0))
    ]], colWidths=[COL_W])
    badge.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), DARK2),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 12),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LINEABOVE",     (0,0),(-1,0), 1.5, GOLD),
        ("LINEBELOW",     (0,-1),(-1,-1), 1, GOLD2),
    ]))
    story.append(badge)
    story.append(Spacer(1, 2))

    # Section 1 : Description générale
    story.append(Paragraph("1.  Description générale du projet", ST["h3"]))
    story.append(ai_zone(
        "Description narrative — générée automatiquement",
        [
            "Présentation complète du projet : nature des travaux, type d'actif, envergure du développement,",
            "nombre d'unités ou superficie, usage prévu, clientèle cible et positionnement dans le marché local.",
            "Historique du site, statut des permis, état d'avancement au moment de la demande de financement.",
            "Calendrier prévu des travaux, jalons principaux, date d'achèvement substantiel et de livraison.",
        ]
    ))
    story.append(Spacer(1, 3))

    # Section 2 : Marché et localisation
    story.append(Paragraph("2.  Contexte de marché et localisation", ST["h3"]))
    story.append(ai_zone(
        "Analyse du marché — générée automatiquement",
        [
            "Portrait du secteur géographique : croissance démographique, taux d'inoccupation local, tendances de prix.",
            "Infrastructure municipale, accès aux transports, services de proximité, dynamique de développement.",
            "Validation de la valeur marchande par le rapport d'évaluation indépendant — ratio LTV confirmé.",
            "Comparables de marché retenus par l'évaluateur agréé et leur incidence sur le dossier.",
        ]
    ))
    story.append(Spacer(1, 3))

    # Section 3 : Emprunteur
    story.append(Paragraph("3.  Profil et capacité de l'emprunteur", ST["h3"]))
    # Deux colonnes : infos tabulaires + zone AI
    emp_tbl = dtable([
        ["Paramètre",              "Détail"],
        ["Dénomination légale",    "________________________________"],
        ["NEQ",                    "________________________________"],
        ["Garant principal",       "________________________________"],
        ["Années d'expérience",    "________________________________"],
        ["Projets réalisés",       "________________________________"],
        ["Valeur nette déclarée",  "$  ________________________ CAD"],
    ], [1.7*inch, 1.9*inch])

    emp_ai = ai_zone(
        "Évaluation de l'emprunteur",
        [
            "Analyse de l'expérience,",
            "des réalisations passées",
            "et de la capacité financière",
            "vérifiée par Capital Norvex.",
            "Points forts et facteurs",
            "de risque identifiés.",
        ]
    )
    row2 = Table([[emp_tbl, emp_ai]], colWidths=[COL_W*0.51, COL_W*0.47])
    row2.setStyle(TableStyle([
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(0,-1), 10),
        ("RIGHTPADDING", (1,0),(1,-1), 0),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ]))
    story.append(row2)
    story.append(Spacer(1, 3))

    # Section 4 : Stratégie de sortie
    story.append(Paragraph("4.  Stratégie de sortie et recommandation finale", ST["h3"]))
    story.append(ai_zone(
        "Stratégie de sortie + recommandation — générées automatiquement",
        [
            "Description détaillée du plan de remboursement : refinancement institutionnel, vente, ou combinaison.",
            "Évaluation de la crédibilité et du réalisme de la stratégie selon les conditions actuelles du marché.",
            "Délai estimé de sortie, marge de manœuvre et scénarios alternatifs en cas d'écart au plan initial.",
            "RECOMMANDATION CAPITALE NORVEX : analyse synthèse et verdict final sur la présentation au partenaire.",
        ]
    ))

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — STRUCTURE FINANCIÈRE + PARTICIPATION PARTENAIRE
# ══════════════════════════════════════════════════════════════════════════════
def page_financiere(story):
    story += sec("STRUCTURE FINANCIÈRE DU PRÊT")
    story.append(dtable([
        ["Paramètre financier",              "Valeur",                    "Notes"],
        ["Montant total du prêt",            "$  ______________ CAD",     "Capital Norvex + Partenaires"],
        ["Durée initiale",                   "_______ mois",              "Prorogation à la discrétion du Prêteur"],
        ["Taux d'intérêt annuel",            "_______ %",                 "Calculé quotidiennement, cap. mensuel"],
        ["LTV (Loan-to-Value)",              "_______ %",                 "Sur évaluation indépendante approuvée"],
        ["LTC (Loan-to-Cost)",               "_______ %",                 "Sur coût total approuvé"],
        ["Retenue de chantier",              "10 %",                      "Libérée à l'achèvement substantiel"],
        ["Frais d'ouverture",                "_______ %",                 "Inclus dans la structure"],
        ["Pénalité remboursement anticipé",  "Min. 3 mois d'intérêts",   "En tout temps"],
        ["Fréquence des déboursés",          "Mensuelle",                 "Sur rapport d'inspection approuvé"],
        ["Rang hypothécaire",                "1er rang exclusif",         "Publié avant tout déboursé"],
    ], [2.4*inch, 1.9*inch, 1.81*inch]))
    story.append(Spacer(1, 3))

    story += sec("VOTRE PARTICIPATION — DÉTAIL PARTENAIRE")
    story.append(kpi_row([
        ("$  __________", "Votre participation"),
        ("_____ %",       "Part de l'ensemble"),
        ("_____ %",       "Rendement annuel"),
        ("$  __________", "Intérêts mensuels"),
    ]))
    story.append(Spacer(1, 2))

    # Tableau participation + zone AI côte à côte
    part_tbl = dtable([
        ["Détail",                       "Valeur"],
        ["Montant de votre participation","$  _________________ CAD"],
        ["Pourcentage du prêt total",    "_______ %"],
        ["Taux de rendement annuel",     "_______ %"],
        ["Intérêts mensuels estimés",    "$  _________________ CAD"],
        ["Durée prévue",                 "_______ mois"],
        ["Remboursement du capital",     "Terme / vente / refinancement"],
        ["Mode de versement",            "Mensuel — virement bancaire"],
        ["Sûreté mobilière RDPRM",       "Enregistrée pour votre compte"],
    ], [2.0*inch, 1.85*inch])

    part_ai = ai_zone(
        "Projection des rendements",
        [
            "Tableau de rendement",
            "personnalisé selon votre",
            "montant de participation,",
            "la durée du prêt et les",
            "conditions du dossier.",
            "Généré automatiquement",
            "par l'agent Capital Norvex.",
        ]
    )
    row3 = Table([[part_tbl, part_ai]], colWidths=[COL_W*0.52, COL_W*0.46])
    row3.setStyle(TableStyle([
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(0,-1), 10),
        ("RIGHTPADDING", (1,0),(1,-1), 0),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ]))
    story.append(row3)
    story.append(Spacer(1, 3))
    story.append(body(
        "Capital Norvex agit à titre d'administrateur exclusif du prêt. Votre participation "
        "est sécurisée par une sûreté mobilière enregistrée au RDPRM. Aucune relation directe "
        "avec l'emprunteur n'est créée. Votre capital et vos rendements sont gérés entièrement "
        "par Capital Norvex selon les termes de la convention partenaire."))
    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — GARANTIES + SCORE NORVEX™
# ══════════════════════════════════════════════════════════════════════════════
def page_garanties(story):
    story += sec("STRUCTURE DE SÉCURITÉ ET GARANTIES")
    story.append(dtable([
        ["Garantie",                        "Détail",                             "Bénéficiaire"],
        ["Hypothèque immobilière",           "1er rang exclusif sur l'immeuble",   "Capital Norvex / Partenaires"],
        ["Valeur garantie",                  "$  ______________________ CAD",      "Évaluation indépendante"],
        ["Cession de loyers",                "Totale et immédiate",                "Capital Norvex"],
        ["Cautionnement personnel",          "Solidaire, irrévocable, illimité",   "Capital Norvex"],
        ["Assurance chantier tous risques",  "Valeur projet + 10 %",               "Capital Norvex 1er bénéficiaire"],
        ["Assurance responsabilité civile",  "Minimum 5 000 000 $",               "Capital Norvex désigné"],
        ["Sûreté mobilière RDPRM",           "Au bénéfice de Capital Norvex",      "Partenaires financiers"],
        ["Retenue de chantier",              "10 % à chaque déboursé",             "Réserve qualité / protection"],
        ["Droit de prise de contrôle",       "Step-in en cas de défaut",           "Capital Norvex — protection totale"],
    ], [2.1*inch, 2.35*inch, 1.66*inch]))
    story.append(Spacer(1, 3))

    story += sec("ANALYSE SCORE NORVEX™ — GRILLE DE NOTATION PONDÉRÉE")

    # Score table + zone AI côte à côte
    score_tbl = dtable([
        ["Critère",                    "Poids", "Note",       "Verdict"],
        ["Expérience emprunteur",      "25 %",  "_____ / 25", "________"],
        ["Ratio LTV",                  "20 %",  "_____ / 20", "________"],
        ["Stratégie de sortie",        "20 %",  "_____ / 20", "________"],
        ["Localisation du projet",     "15 %",  "_____ / 15", "________"],
        ["Force financière",           "15 %",  "_____ / 15", "________"],
        ["Structure du projet",        "5 %",   "_____ / 5",  "________"],
        ["SCORE GLOBAL",               "100 %", "_____ / 100","________"],
    ], [1.7*inch, 0.6*inch, 0.85*inch, 0.8*inch])

    score_ai = ai_zone(
        "Commentaires Score Norvex™",
        [
            "Analyse détaillée de",
            "chaque critère générée",
            "automatiquement par",
            "l'agent AI Capital Norvex.",
            "Points forts, points de",
            "vigilance et conditions",
            "imposées au dossier.",
        ]
    )
    row4 = Table([[score_tbl, score_ai]], colWidths=[COL_W*0.56, COL_W*0.42])
    row4.setStyle(TableStyle([
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(0,-1), 10),
        ("RIGHTPADDING", (1,0),(1,-1), 0),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ]))
    story.append(row4)
    story.append(Spacer(1, 2))

    story += sec("CONDITIONS PARTICULIÈRES IMPOSÉES PAR CAPITAL NORVEX")
    for t in [
        "Premier déboursé conditionnel à la publication de l'hypothèque de 1er rang et à la réception de l'opinion juridique",
        "Inspection mensuelle obligatoire par un professionnel indépendant approuvé avant chaque déboursé",
        "Rapport d'avancement mensuel disponible au partenaire via son portail PWA Capital Norvex",
        "Tout changement majeur aux plans, au budget ou à l'équipe requiert l'approbation écrite de Capital Norvex",
        "Droit de prise de contrôle (step-in) activable en tout temps en cas de défaut — protection totale du capital investi",
    ]:
        story.append(bul(t))
    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — POURQUOI CAPITAL NORVEX + PROCHAINES ÉTAPES
# ══════════════════════════════════════════════════════════════════════════════
def page_pourquoi(story):
    story += sec("POURQUOI CAPITAL NORVEX")

    vals_data = [
        ["Contrôle absolu des déboursés",
         "Chaque avance est conditionnelle à l'inspection indépendante approuvée. Aucun dollar ne sort sans validation complète."],
        ["Sélection rigoureuse — moins de 20 %",
         "Moins de 20 % des dossiers soumis atteignent la présentation partenaire. Chaque dossier passe par Score Norvex™."],
        ["Transparence et accès temps réel",
         "Votre portail partenaire PWA vous donne accès en tout temps aux déboursés, rapports et statuts de votre prêt."],
        ["Structure juridique institutionnelle",
         "Hypothèque 1er rang, cession de loyers, cautionnements illimités, sûreté RDPRM — protection à chaque niveau."],
    ]
    rows = [[
        Paragraph(v[0], ParagraphStyle("vt", fontName="Helvetica-Bold",
            fontSize=9, textColor=GOLD, spaceAfter=3)),
        Paragraph(v[1], ParagraphStyle("vb", fontName="Helvetica",
            fontSize=8.5, textColor=DARK, leading=13, spaceAfter=0, alignment=TA_JUSTIFY)),
    ] for v in vals_data]
    val_tbl = Table(rows, colWidths=[1.9*inch, COL_W - 1.9*inch])
    val_tbl.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0),(-1,-1), [CREAM, CREAM2]),
        ("LEFTPADDING",    (0,0),(-1,-1), 10),
        ("RIGHTPADDING",   (0,0),(-1,-1), 10),
        ("TOPPADDING",     (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 5),
        ("VALIGN",         (0,0),(-1,-1), "TOP"),
        ("GRID",           (0,0),(-1,-1), 0.3, GREY_LT),
        ("LINEABOVE",      (0,0),(-1,0), 2, GOLD),
        ("LINEBELOW",      (0,-1),(-1,-1), 1.5, GOLD2),
    ]))
    story.append(val_tbl)
    story.append(Spacer(1, 2))

    story.append(kpi_row([
        ("$2.5M – $100M", "Fourchette de prêts"),
        ("10 – 12 %",     "Taux annuel"),
        ("Qc & On",       "Marchés actifs"),
        ("> $1 Md",       "Volume annuel cible"),
    ]))
    story.append(Spacer(1, 3))

    story += sec("PROCHAINES ÉTAPES POUR CONFIRMER VOTRE PARTICIPATION")

    # 5 étapes visuelles
    steps = [
        ("1", "Confirmer votre intérêt",         "Répondre par courriel ou téléphone à Capital Norvex"),
        ("2", "Signer la convention partenaire",  "Document transmis dès réception de votre confirmation"),
        ("3", "Effectuer votre virement",         "Coordonnées bancaires fournies à la signature de la convention"),
        ("4", "Accéder à votre portail PWA",      "Suivi en temps réel — mobile et web — dès l'activation"),
        ("5", "Recevoir votre 1er versement",     "Dès le premier déboursé effectué — virement mensuel garanti"),
    ]
    step_rows = [
        [Paragraph(n, ST["step_num"]),
         Paragraph(t, ST["step_t"]),
         Paragraph(d, ST["step_b"])]
        for n, t, d in steps
    ]
    step_tbl = Table(step_rows, colWidths=[0.4*inch, 2.1*inch, COL_W - 2.5*inch])
    step_tbl.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0),(-1,-1), [CREAM, CREAM2]),
        ("GRID",           (0,0),(-1,-1), 0.3, GREY_LT),
        ("TOPPADDING",     (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 5),
        ("LEFTPADDING",    (0,0),(-1,-1), 8),
        ("RIGHTPADDING",   (0,0),(-1,-1), 8),
        ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
        ("ALIGN",          (0,0),(0,-1), "CENTER"),
        ("LINEABOVE",      (0,0),(-1,0), 2, GOLD),
        ("LINEBELOW",      (0,-1),(-1,-1), 1.5, GOLD2),
    ]))
    story.append(step_tbl)
    story.append(Spacer(1, 3))

    # Bloc contact (adresse complète déjà au pied de page → on garde juste l'appel à l'action)
    contact_tbl = Table([
        [Paragraph("CAPITAL NORVEX INC.", ST["white_b"])],
        [Paragraph("Pour confirmer votre participation ou obtenir de l'information additionnelle :", ST["white_sm"])],
        [Paragraph("1-(438)-533-PRET (7738)  ·  info@capitalnorvex.com", ST["white_em"])],
    ], colWidths=[COL_W])
    contact_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), DARK),
        ("LEFTPADDING",   (0,0),(-1,-1), 16),
        ("RIGHTPADDING",  (0,0),(-1,-1), 16),
        ("TOPPADDING",    (0,0),(0,0), 14),
        ("BOTTOMPADDING", (0,-1),(-1,-1), 14),
        ("TOPPADDING",    (0,1),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-2), 3),
        ("LINEABOVE",     (0,0),(-1,0), 3, GOLD),
        ("LINEBELOW",     (0,-1),(-1,-1), 3, GOLD2),
    ]))
    story.append(contact_tbl)
    story.append(Spacer(1, 3))
    story.append(GoldLine())
    story.append(Spacer(1, 3))
    story.append(Paragraph("Capital structuré.  Ambition maîtrisée.", ST["slogan"]))
    story.append(Paragraph(
        "Ce document est préparé par Capital Norvex Inc. à partir des informations fournies par l'emprunteur. "
        "Il ne constitue pas une garantie de rendement. Les performances passées ne garantissent pas les résultats futurs.",
        ST["note"]))

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    out = "/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres/CapitalNorvex_SommaireExecutif_Partenaire.pdf"
    doc = SimpleDocTemplate(
        out, pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 38, bottomMargin=MARGIN + 34,
        title="Sommaire Exécutif Partenaire — Capital Norvex",
        author="Capital Norvex Inc.",
        subject="Opportunité de financement partenaire — Confidentiel",
    )
    story = []
    page_couverture(story)
    page_faits_saillants(story)
    page_analyse(story)
    page_financiere(story)
    page_garanties(story)
    page_pourquoi(story)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

    from pypdf import PdfReader
    r = PdfReader(out)
    print(f"✅  PDF généré : {out}")
    print(f"📄  Nombre de pages : {len(r.pages)}")

if __name__ == "__main__":
    main()
