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

EMBLEM_PATH = r'/Users/yvesbarrette/Desktop/capitalnorvex-site/CapitalNorvex_Scripts/logos/emblem_header.png'
COVER_PATH  = r'/Users/yvesbarrette/Desktop/capitalnorvex-site/CapitalNorvex_Scripts/logos/logo_cover.png'

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
    canvas.drawString(MARGIN+46, h-43, "Institutional Private Lending  |  Quebec & Ontario")
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawRightString(w-MARGIN, h-28, "PARTNER EXECUTIVE SUMMARY")
    canvas.setFillColor(GREY_LT)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(w-MARGIN, h-42, "CONFIDENTIAL — EXCLUSIVE USE")
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(w-MARGIN, h-52, f"p. {doc.page}")
    canvas.setFillColor(DARK)
    canvas.rect(0, 0, w, 50, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, 50, w, 1.5, fill=1, stroke=0)
    # Top line — confidentiality (centered, gold for branding)
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawCentredString(w/2, 32, "CAPITAL NORVEX  \u00b7  Confidential document — designated financial partner")
    # Bottom line — full address (centered, light grey)
    canvas.setFillColor(GREY_LT)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(w/2, 14, "2705-1000 André-Prévost  \u00b7  Île-des-Sœurs (Verdun)  \u00b7  Montréal, QC H3E 0G2   |   1-(438)-533-PRET (7738)   |   info@capitalnorvex.com   |   capitalnorvex.com")
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

# ── AI zone (reserved area for automatically generated content) ───────────────
def ai_zone(title, lines, height_pt=None):
    """Premium visual zone indicating content generated by the AI agent."""
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

# ── Data table ────────────────────────────────────────────────────────────────
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
# PAGE 1 — COVER
# ══════════════════════════════════════════════════════════════════════════════
def page_cover(story):
    story.append(Spacer(1, 0.15*inch))
    img = RLImage(COVER_PATH, width=120, height=130)
    img.hAlign = "CENTER"
    story.append(img)
    story.append(Spacer(1, 3))
    tbl = Table([[Paragraph("EXECUTIVE SUMMARY", ST["cover_t"])]], colWidths=[COL_W])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), DARK),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LINEABOVE",     (0,0),(-1,0), 3, GOLD),
        ("LINEBELOW",     (0,-1),(-1,-1), 3, GOLD),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 3))
    story.append(Paragraph("PARTNER FINANCING OPPORTUNITY", ST["cover_s"]))
    story.append(Spacer(1, 2))
    info = [
        ["PROJECT",        "_______________________________________________"],
        ["LOCATION",       "_______________________________________________"],
        ["LOAN TYPE",      "Construction  /  Land  /  Acquisition"],
        ["AMOUNT",         "_______________________________________________"],
        ["TARGET YIELD",   "_______________________________________________"],
        ["TERM",           "_______________________________________________"],
        ["DATE",           "_______________________________________________"],
        ["RECIPIENT",      "_______________________________________________"],
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
    story.append(Paragraph("Structured Capital.  Controlled Ambition.", ST["slogan"]))
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        "CONFIDENTIAL — Document prepared exclusively for the designated financial partner. "
        "Do not reproduce or distribute without written authorization from Capital Norvex.",
        ST["conf"]))
    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — KEY HIGHLIGHTS + PROJECT OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
def page_highlights(story):
    story += sec("OPPORTUNITY HIGHLIGHTS")
    story.append(kpi_row([
        ("$  __________", "Loan Amount"),
        ("_____ %",       "Annual Interest Rate"),
        ("_____ months",  "Initial Term"),
        ("_____ %",       "LTV"),
    ]))
    story.append(Spacer(1, 3))
    story.append(kpi_row([
        ("$  __________", "Your Participation"),
        ("_____ %",       "Target Annual Yield"),
        ("1st Rank",      "Mortgage Rank"),
        ("$  __________", "Est. Monthly Interest"),
    ]))
    story.append(Spacer(1, 3))

    story += sec("PROJECT OVERVIEW")
    # Photo + quick info side by side
    photo = photo_box("MAIN PROJECT PHOTO\n— insert here —", w=COL_W * 0.47, h_pt=1.1*inch)
    infos = dtable([
        ["Parameter",            "Detail"],
        ["Address",              "________________________________"],
        ["Municipality / RCM",   "________________________________"],
        ["Development Type",     "________________________________"],
        ["Number of Units",      "________________________________"],
        ["Value at Completion",  "$  ________________________ CAD"],
        ["Total Project Cost",   "$  ________________________ CAD"],
        ["Down Payment",         "$  ____________  ( ______ %)"],
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

    # AI zone — executive summary of project
    story.append(ai_zone(
        "Executive summary generated by the Capital Norvex AI agent",
        [
            "Complete project description automatically drafted from the borrower's full file.",
            "Location, development type, market positioning, competitive advantages of the project.",
            "Key strengths identified by Capital Norvex: team experience, financial strength, asset quality.",
            "Preliminary conclusion and Capital Norvex recommendation for partner presentation.",
        ]
    ))
    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — DETAILED PROJECT AND BORROWER ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
def page_analysis(story):
    story += sec("PROJECT ANALYSIS — CAPITAL NORVEX REPORT")

    # Intro AI badge
    badge = Table([[Paragraph(
        "[ CONTENT GENERATED BY CAPITAL NORVEX AI AGENT ]  "
        "The following text is automatically produced from the complete file documentation, "
        "qualification interview and Score Norvex™ analysis.",
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

    # Section 1: General description
    story.append(Paragraph("1.  General project description", ST["h3"]))
    story.append(ai_zone(
        "Narrative description — automatically generated",
        [
            "Complete project presentation: nature of work, asset type, development scope,",
            "number of units or area, intended use, target clientele and positioning in the local market.",
            "Site history, permit status, progress at time of financing application.",
            "Planned work schedule, key milestones, substantial completion and delivery date.",
        ]
    ))
    story.append(Spacer(1, 3))

    # Section 2: Market and location
    story.append(Paragraph("2.  Market context and location", ST["h3"]))
    story.append(ai_zone(
        "Market analysis — automatically generated",
        [
            "Portrait of the geographic area: population growth, local vacancy rates, price trends.",
            "Municipal infrastructure, transportation access, nearby services, development dynamics.",
            "Validation of market value by independent appraisal report — confirmed LTV ratio.",
            "Market comparables retained by the certified appraiser and their impact on the file.",
        ]
    ))
    story.append(Spacer(1, 3))

    # Section 3: Borrower
    story.append(Paragraph("3.  Borrower profile and capacity", ST["h3"]))
    # Two columns: tabular info + AI zone
    emp_tbl = dtable([
        ["Parameter",            "Detail"],
        ["Legal Name",           "________________________________"],
        ["BN",                   "________________________________"],
        ["Principal Guarantor",  "________________________________"],
        ["Years of Experience",  "________________________________"],
        ["Projects Completed",   "________________________________"],
        ["Declared Net Worth",   "$  ________________________ CAD"],
    ], [1.7*inch, 1.9*inch])

    emp_ai = ai_zone(
        "Borrower assessment",
        [
            "Analysis of experience,",
            "past achievements",
            "and financial capacity",
            "verified by Capital Norvex.",
            "Key strengths and risk",
            "factors identified.",
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

    # Section 4: Exit strategy
    story.append(Paragraph("4.  Exit strategy and final recommendation", ST["h3"]))
    story.append(ai_zone(
        "Exit strategy + recommendation — automatically generated",
        [
            "Detailed description of the repayment plan: institutional refinancing, sale, or combination.",
            "Assessment of the credibility and realism of the strategy under current market conditions.",
            "Estimated exit timeline, margin of safety and alternative scenarios if plan deviates.",
            "CAPITAL NORVEX RECOMMENDATION: synthesis analysis and final verdict on partner presentation.",
        ]
    ))

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — LOAN FINANCIAL STRUCTURE + PARTNER PARTICIPATION
# ══════════════════════════════════════════════════════════════════════════════
def page_financial(story):
    story += sec("LOAN FINANCIAL STRUCTURE")
    story.append(dtable([
        ["Financial Parameter",              "Value",                         "Notes"],
        ["Total Loan Amount",                "$  ______________ CAD",         "Capital Norvex + Partners"],
        ["Initial Term",                     "_______ months",                "Extension at Lender's discretion"],
        ["Annual Interest Rate",             "_______ %",                     "Calculated daily, comp. monthly"],
        ["LTV (Loan-to-Value)",              "_______ %",                     "On approved independent appraisal"],
        ["LTC (Loan-to-Cost)",               "_______ %",                     "On total approved cost"],
        ["Construction Holdback",            "10%",                           "Released at substantial completion"],
        ["Origination Fee",                  "_______ %",                     "Included in structure"],
        ["Prepayment Penalty",               "Min. 3 months interest",        "At any time"],
        ["Disbursement Frequency",           "Monthly",                       "On approved inspection report"],
        ["Mortgage Rank",                    "Exclusive 1st rank",            "Registered before any disbursement"],
    ], [2.4*inch, 1.9*inch, 1.81*inch]))
    story.append(Spacer(1, 3))

    story += sec("YOUR PARTICIPATION — PARTNER DETAILS")
    story.append(kpi_row([
        ("$  __________", "Your Participation"),
        ("_____ %",       "Share of Total"),
        ("_____ %",       "Annual Yield"),
        ("$  __________", "Monthly Interest"),
    ]))
    story.append(Spacer(1, 2))

    # Participation table + AI zone side by side
    part_tbl = dtable([
        ["Detail",                         "Value"],
        ["Amount of your participation",   "$  _________________ CAD"],
        ["Percentage of total loan",       "_______ %"],
        ["Annual return rate",             "_______ %"],
        ["Estimated monthly interest",     "$  _________________ CAD"],
        ["Expected term",                  "_______ months"],
        ["Principal repayment",            "Maturity / sale / refinancing"],
        ["Payment method",                 "Monthly — bank wire transfer"],
        ["PPSA / RDPRM Security",          "Registered on your behalf"],
    ], [2.0*inch, 1.85*inch])

    part_ai = ai_zone(
        "Yield Projection",
        [
            "Customized return schedule",
            "based on your participation",
            "amount, loan term and",
            "file conditions.",
            "Automatically generated",
            "by the Capital Norvex",
            "AI agent.",
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
        "Capital Norvex acts as exclusive loan administrator. Your participation is secured by a "
        "registered personal property security. No direct relationship with the borrower is created. "
        "Your capital and returns are managed entirely by Capital Norvex in accordance with the terms "
        "of the partner agreement."))
    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — SECURITY + SCORE NORVEX™
# ══════════════════════════════════════════════════════════════════════════════
def page_security(story):
    story += sec("SECURITY STRUCTURE AND GUARANTEES")
    story.append(dtable([
        ["Security",                          "Detail",                              "Beneficiary"],
        ["Real estate mortgage",              "Exclusive 1st rank on property",      "Capital Norvex / Partners"],
        ["Secured value",                     "$  ______________________ CAD",       "Independent appraisal"],
        ["Assignment of leases",              "Total and immediate",                 "Capital Norvex"],
        ["Personal guarantee",               "Joint, irrevocable, unlimited",        "Capital Norvex"],
        ["All-risk construction insurance",   "Project value + 10%",                 "Capital Norvex — 1st beneficiary"],
        ["Civil liability insurance",         "Minimum $5,000,000",                  "Capital Norvex designated"],
        ["PPSA / RDPRM Security",             "In favour of Capital Norvex",         "Financial partners"],
        ["Construction holdback",             "10% at each disbursement",            "Quality reserve / protection"],
        ["Step-in right",                     "Exercisable upon default",            "Capital Norvex — full protection"],
    ], [2.1*inch, 2.35*inch, 1.66*inch]))
    story.append(Spacer(1, 3))

    story += sec("SCORE NORVEX™ ANALYSIS — WEIGHTED RATING GRID")

    # Score table + AI zone side by side
    score_tbl = dtable([
        ["Criterion",              "Weight", "Score",       "Verdict"],
        ["Borrower Experience",    "25%",    "_____ / 25",  "________"],
        ["LTV Ratio",              "20%",    "_____ / 20",  "________"],
        ["Exit Strategy",          "20%",    "_____ / 20",  "________"],
        ["Project Location",       "15%",    "_____ / 15",  "________"],
        ["Financial Strength",     "15%",    "_____ / 15",  "________"],
        ["Project Structure",      "5%",     "_____ / 5",   "________"],
        ["OVERALL SCORE",          "100%",   "_____ / 100", "________"],
    ], [1.7*inch, 0.6*inch, 0.85*inch, 0.8*inch])

    score_ai = ai_zone(
        "Score Norvex™ Comments",
        [
            "Detailed analysis of",
            "each criterion generated",
            "automatically by the",
            "Capital Norvex AI agent.",
            "Key strengths, areas of",
            "vigilance and conditions",
            "imposed on the file.",
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

    story += sec("SPECIFIC CONDITIONS IMPOSED BY CAPITAL NORVEX")
    for t in [
        "First disbursement conditional on registration of 1st-rank mortgage and receipt of legal opinion",
        "Mandatory monthly inspection by an approved independent professional before each disbursement",
        "Monthly progress report available to partner via their Capital Norvex PWA portal",
        "Any material change to plans, budget or team requires written approval from Capital Norvex",
        "Step-in right exercisable at any time upon default — full protection of invested capital",
    ]:
        story.append(bul(t))
    story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — WHY CAPITAL NORVEX + NEXT STEPS
# ══════════════════════════════════════════════════════════════════════════════
def page_why(story):
    story += sec("WHY CAPITAL NORVEX")

    vals_data = [
        ["Absolute Disbursement Control",
         "Each advance is conditional on an approved independent inspection. No dollar disbursed without full validation."],
        ["Rigorous Selection — Less than 20%",
         "Fewer than 20% of submitted files reach partner presentation. Every file goes through Score Norvex™."],
        ["Transparency and Real-Time Access",
         "Your partner PWA portal gives you real-time access to disbursements, reports and loan status at any time."],
        ["Institutional Legal Structure",
         "1st-rank mortgage, assignment of leases, unlimited guarantees, PPSA/RDPRM security — protection at every level."],
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
        ("$2.5M – $100M", "Loan Range"),
        ("10 – 12%",      "Annual Rate"),
        ("QC & ON",       "Active Markets"),
        ("> $1B",         "Annual Volume Target"),
    ]))
    story.append(Spacer(1, 3))

    story += sec("NEXT STEPS TO CONFIRM YOUR PARTICIPATION")

    # 5 visual steps
    steps = [
        ("1", "Confirm your interest",        "Reply by email or phone to Capital Norvex"),
        ("2", "Sign the partner agreement",   "Document transmitted upon receipt of your confirmation"),
        ("3", "Wire your funds",              "Banking coordinates provided upon signing the agreement"),
        ("4", "Access your PWA portal",       "Real-time tracking — mobile and web — from activation"),
        ("5", "Receive your 1st payment",     "From first disbursement made — guaranteed monthly wire transfer"),
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

    # Contact block (full address already in footer → just keep call to action)
    contact_tbl = Table([
        [Paragraph("CAPITAL NORVEX INC.", ST["white_b"])],
        [Paragraph("To confirm your participation or obtain additional information:", ST["white_sm"])],
        [Paragraph("1-(438)-533-PRET (7738)  \u00b7  info@capitalnorvex.com", ST["white_em"])],
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
    story.append(Paragraph("Structured Capital.  Controlled Ambition.", ST["slogan"]))
    story.append(Paragraph(
        "This document is prepared by Capital Norvex Inc. from information provided by the borrower. "
        "It does not constitute a guarantee of return. Past performance does not guarantee future results.",
        ST["note"]))
    story.append(Paragraph(
        "The French version shall prevail in Quebec.",
        ST["note"]))

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    out = r"/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres/CapitalNorvex_ExecutiveSummary_Partner_EN.pdf"
    doc = SimpleDocTemplate(
        out, pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 38, bottomMargin=MARGIN + 38,
        title="Partner Executive Summary — Capital Norvex",
        author="Capital Norvex Inc.",
        subject="Partner Financing Opportunity — Confidential",
    )
    story = []
    page_cover(story)
    page_highlights(story)
    page_analysis(story)
    page_financial(story)
    page_security(story)
    page_why(story)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

    from pypdf import PdfReader
    r = PdfReader(out)
    print(f"PDF generated: {out}")
    print(f"Page count: {len(r.pages)}")

if __name__ == "__main__":
    main()
