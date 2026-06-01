"""
09_loan_agreement_en.py
CAPITAL NORVEX — Construction Loan Agreement (EN)
Generates: Loan_Agreement_Construction_CapitalNorvex_EN.pdf
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
OUTPUT_FILE = r'/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres/Loan_Agreement_Construction_CapitalNorvex_EN.pdf'

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
    canvas.drawString(MARGIN + 44, h - 42, "Institutional Private Lending  |  Quebec & Ontario")
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.drawRightString(w - MARGIN, h - 28, "LOAN AGREEMENT")
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawRightString(w - MARGIN, h - 42, "CONSTRUCTION")
    canvas.setFillColor(GREY_LT)
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(w - MARGIN, h - 52, f"p. {doc.page}")
    canvas.setFillColor(DARK)
    canvas.rect(0, 0, w, 50, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, 50, w, 1.5, fill=1, stroke=0)
    # Top line — confidentiality (centered, gold for branding)
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawCentredString(w/2, 32,
        "CAPITAL NORVEX  \u00b7  Confidential \u2014 For exclusive use of the signatory parties")
    # Bottom line — full address (centered, light grey)
    canvas.setFillColor(GREY_LT)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(w/2, 14,
        "2705-1000 André-Prévost  \u00b7  Île-des-Sœurs (Verdun)  \u00b7  Montréal, QC H3E 0G2   |   1-(438)-533-PRET (7738)   |   info@capitalnorvex.com   |   capitalnorvex.com")
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
    fee_hdr    = S("FH",  fontName="Helvetica-Bold",    fontSize=9,  textColor=GOLD),
    fee_val    = S("FV",  fontName="Helvetica",         fontSize=8.8,textColor=DARK,  alignment=TA_JUSTIFY, leading=13),
)


def sec(title):
    return [
        Spacer(1, 8),
        Table([[Paragraph(title, ST["sec_head"])]],
              colWidths=[BW],
              style=TableStyle([
                  ("BACKGROUND", (0, 0), (-1, -1), DARK),
                  ("LEFTPADDING", (0, 0), (-1, -1), 10),
                  ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                  ("TOPPADDING", (0, 0), (-1, -1), 6),
                  ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                  ("LINEBELOW", (0, 0), (-1, -1), 2, GOLD),
              ])),
        Spacer(1, 4),
    ]


def art(num, title):
    return [
        Table([[Paragraph(f"{num}  {title}", ST["art_head"])]],
              colWidths=[BW],
              style=TableStyle([
                  ("BACKGROUND", (0, 0), (-1, -1), GREY_LT),
                  ("LEFTPADDING", (0, 0), (-1, -1), 8),
                  ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                  ("TOPPADDING", (0, 0), (-1, -1), 4),
                  ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
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
    t = Table(data, colWidths=[2.4 * inch, BW - 2.4 * inch])
    t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [CREAM, CREAM2]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, -1), (-1, -1), 1.5, GOLD),
    ]))
    return t


def gen_tbl(rows):
    data = [[Paragraph(r[0], ST["gen_key"]), Paragraph(r[1], ST["gen_val"])] for r in rows]
    t = Table(data, colWidths=[2.0 * inch, BW - 2.0 * inch])
    t.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, GREY_LT),
        ("LINEBELOW", (0, -1), (-1, -1), 1.5, GOLD),
    ]))
    return t


def fee_tbl(rows):
    """3-column fee table with dark header row."""
    data = []
    for i, r in enumerate(rows):
        if i == 0:
            data.append([Paragraph(r[0], ST["fee_hdr"]),
                         Paragraph(r[1], ST["fee_hdr"]),
                         Paragraph(r[2], ST["fee_hdr"])])
        else:
            data.append([Paragraph(r[0], ST["fee_val"]),
                         Paragraph(r[1], ST["fee_val"]),
                         Paragraph(r[2], ST["fee_val"])])
    col1 = 2.2 * inch
    col2 = 1.6 * inch
    col3 = BW - col1 - col2
    t = Table(data, colWidths=[col1, col2, col3])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [CREAM, CREAM2]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, -1), (-1, -1), 1.5, GOLD),
        ("LINEAFTER", (0, 0), (1, -1), 0.5, GREY_LT),
    ]))
    return t


def cov_tbl_widget(rows):
    data = [[Paragraph(r[0], ST["tbl_hdr"]), Paragraph(r[1], ST["tbl_val"])] for r in rows]
    t = Table(data, colWidths=[2.0 * inch, BW - 2.0 * inch])
    t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [CREAM, CREAM2]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, -1), (-1, -1), 1.5, GOLD),
    ]))
    return t


def covenant_tbl(rows):
    """3-column financial covenant table with dark header."""
    data = []
    for i, r in enumerate(rows):
        if i == 0:
            data.append([Paragraph(r[0], ST["fee_hdr"]),
                         Paragraph(r[1], ST["fee_hdr"]),
                         Paragraph(r[2], ST["fee_hdr"])])
        else:
            data.append([Paragraph(r[0], ST["fee_val"]),
                         Paragraph(r[1], ST["fee_val"]),
                         Paragraph(r[2], ST["fee_val"])])
    col1 = 2.4 * inch
    col2 = 1.4 * inch
    col3 = BW - col1 - col2
    t = Table(data, colWidths=[col1, col2, col3])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [CREAM, CREAM2]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, -1), (-1, -1), 1.5, GOLD),
        ("LINEAFTER", (0, 0), (1, -1), 0.5, GREY_LT),
    ]))
    return t


def dark_banner(text, color=WHITE):
    style = S("DBN", fontName="Helvetica-Bold", fontSize=10,
              textColor=color, alignment=TA_CENTER)
    t = Table([[Paragraph(text, style)]], colWidths=[BW])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def sign_block(label, fields):
    """Single signature block with label and field lines."""
    items = [Paragraph(label, ST["sign_lbl"]), GoldLine(width=BW * 0.9, thickness=0.8)]
    for f in fields:
        items.append(bp(f))
    items.append(bp("Signature : _______________________________________________"))
    return items


def build_cover(story):
    story.append(sp(12))
    if os.path.exists(COVER_PATH):
        img = RLImage(COVER_PATH, width=120, height=130)
        img.hAlign = "CENTER"
        story.append(img)
    story.append(sp(8))
    story.append(Paragraph("CAPITAL NORVEX", ST["cov_title"]))
    story.append(Paragraph(
        "<i>Institutional Private Lending  |  Quebec &amp; Ontario</i>", ST["cov_sub"]))
    story.append(GoldLine())
    story.append(sp(8))

    block = Table([
        [Paragraph("LOAN AGREEMENT", ST["cov_name"])],
        [Paragraph("CONSTRUCTION", ST["cov_name2"])],
        [Paragraph(
            "<i>Capital Norvex Inc.  \u2014  Institutional Version  \u2014  Quebec</i>",
            ST["cov_italic"])],
    ], colWidths=[BW])
    block.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK),
        ("TOPPADDING", (0, 0), (0, 0), 18),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (0, -2), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("LINEABOVE", (0, 0), (-1, 0), 3, GOLD),
        ("LINEBELOW", (0, -1), (-1, -1), 3, GOLD),
    ]))
    story.append(block)
    story.append(sp(14))

    cov_tbl = cov_tbl_widget([
        ["BORROWER",  "___________________________________"],
        ["PROJECT",   "___________________________________"],
        ["AMOUNT",    "$___________________________________ CAD"],
        ["TERM",      "_______ months"],
        ["DATE",      "___________________________________"],
        ["FILE No.",  "___________________________________"],
    ])
    story.append(cov_tbl)
    story.append(sp(18))
    story.append(Paragraph("Structured Capital.  Controlled Ambition.", ST["slogan"]))
    story.append(Paragraph(
        "CONFIDENTIAL \u2014 Reserved for signatory parties and their legal counsel",
        ST["note"]))
    story.append(PageBreak())


def build_body(story):
    # ── 1 ──────────────────────────────────────────────────────────────────
    story += sec("1. INTERPRETATION AND DEFINITIONS")
    story += art("1.1", "Interpretation")
    story.append(bp(
        "Unless otherwise indicated, headings are inserted for the convenience of the parties only "
        "and do not limit the scope of the provisions. The singular includes the plural and vice versa. "
        "Any reference to a statute includes subsequent amendments thereto. Undefined terms have their "
        "customary meaning in the commercial real estate financing industry."))
    story.append(sp())
    story += art("1.2", "Definitions")
    defs = [
        ('<b>"Agreement"</b>: This convention, its schedules, amendments and all ancillary documents.'),
        ('<b>"Substantial Completion"</b>: Stage where at least 97% of Project costs are committed, '
         'allowing normal use of the property.'),
        ('<b>"Budget"</b>: Detailed budget approved by Capital Norvex, including direct costs, indirect '
         'costs, contingencies, financing costs and reserves.'),
        ('<b>"Schedule"</b>: Construction timeline approved by Capital Norvex.'),
        ('<b>"Disbursement"</b>: Any advance of funds made by the Lender.'),
        ('<b>"Borrower"</b>: The borrowing entity identified herein.'),
        ('<b>"Guarantor"</b>: Any natural or legal person providing security to the Lender.'),
        ('<b>"Mortgage"</b>: First-rank real estate mortgage registered in favour of Capital Norvex.'),
        ('<b>"LTC"</b>: Loan-to-Cost ratio.'),
        ('<b>"LTV"</b>: Loan-to-Value ratio.'),
        ('<b>"Norvex Track\u2122"</b>: Capital Norvex\u2019s proprietary technology module used for '
         'submission, verification, authorization and traceability of progressive Disbursements, '
         'accessible 24/7.'),
        ('<b>"Borrower Portal (PWA)"</b>: Secure Progressive Web Application made available by '
         'Capital Norvex to the Borrower, accessible 24/7, allowing real-time consultation of the '
         'Borrower\u2019s file (balance, schedule, disbursements, documents).'),
        ('<b>"Lender"</b>: CAPITAL NORVEX INC., acting on its own behalf and/or on behalf of financial '
         'partners.'),
        ('<b>"Project"</b>: Real estate development described in Schedule A.'),
        ('<b>"Score Norvex\u2122"</b>: Capital Norvex\u2019s proprietary analysis system used for '
         'evaluation and ongoing monitoring of the file.'),
        ('<b>"SPV"</b>: Legal entity dedicated to holding the Project.'),
        ('<b>"Works"</b>: All construction work covered by the Project.'),
    ]
    for d in defs:
        story.append(bp(d))
    story.append(sp())

    # ── 2 ──────────────────────────────────────────────────────────────────
    story += sec("2. PARTIES")
    story += art("2.1", "Lender")
    story.append(bp("<b>Corporate Name: CAPITAL NORVEX INC.</b>"))
    story.append(bp("Address: ___________________________________________________________"))
    story.append(bp("Authorized Representative: ___________________________________________"))
    story.append(sp())
    story += art("2.2", "Borrower")
    story.append(bp("Corporate Name: _____________________________________________________"))
    story.append(bp("Business Number (BN): _______________________________________________"))
    story.append(bp("Registered Office Address: __________________________________________"))
    story.append(bp("Authorized Representative: ___________________________________________"))
    story.append(bp("Title: ______________________________________________________________"))
    story.append(sp())
    story += art("2.3", "Guarantors")
    story.append(bp(
        "The Guarantors below are jointly and indivisibly bound with the Borrower for all obligations "
        "arising from this Agreement."))
    story.append(bp("Guarantor 1 \u2013 Name: ___________________________________________________"))
    story.append(bp("Guarantor 2 \u2013 Name (if applicable): ____________________________________"))
    story.append(sp())

    # ── 3 ──────────────────────────────────────────────────────────────────
    story += sec("3. PURPOSE OF THE LOAN")
    story.append(bp(
        "Capital Norvex grants the Borrower construction financing intended exclusively for the "
        "completion of the Project described in Schedule A. Funds may not be used for any other "
        "purpose without the prior written consent of the Lender. The following are expressly "
        "prohibited without written authorization:"))
    story += blt([
        "Any unauthorized refinancing of existing obligations",
        "Any distribution to shareholders, partners or members",
        "Any transfer to other projects or entities",
    ])
    story.append(sp())

    # ── 4 ──────────────────────────────────────────────────────────────────
    story += sec("4. AMOUNT, TERM AND FINANCIAL CONDITIONS")
    story += art("4.1", "Loan Amount")
    story.append(bp("<b>Maximum Authorized Amount: $_____ CAD</b>"))
    story.append(bp(
        "The Lender is not obligated to advance the full authorized amount. Disbursements are made "
        "on a discretionary basis based on construction progress and satisfaction of all conditions "
        "set forth herein."))
    story.append(sp())
    story += art("4.2", "Term")
    story.append(bp(
        "<b>Initial Term: _______ months from the date of the first disbursement</b>"))
    story.append(bp(
        "Any extension is at the exclusive discretion of the Lender and may be subject to "
        "additional fees."))
    story.append(sp())
    story += art("4.3", "Interest Rate")
    story.append(bp(
        "<b>Annual Rate: _____ % per year (calculated daily, compounded monthly)</b>"))
    story.append(bp(
        "Interest accrues only on amounts actually disbursed. Interest payments are due on the "
        "first business day of each month."))
    story.append(sp())
    story += art("4.4", "Fees")
    story.append(fee_tbl([
        ["Fee Type", "Rate / Amount", "Due Date"],
        ["Origination Fee", "3% to 3.5%", "At signing"],
        ["Renewal Fee", "_____ %", "At each renewal"],
        ["Analysis Fee (term extension)", "1% of principal", "If extension beyond Maturity Date"],
        ["Exit Fee", "Min. 3 months interest", "Upon repayment"],
        ["Legal Fees (Lender)", "At actual cost", "Upon request"],
        ["Inspection / Appraisal Fees", "At actual cost", "At each disbursement"],
    ]))
    story.append(sp(8))

    # ── 5 ──────────────────────────────────────────────────────────────────
    story += sec("5. FINANCING STRUCTURE \u2014 NORVEX CLAUSE")
    story += art("5.1", "Partner Participation")
    story.append(bp(
        "Capital Norvex may, at its sole discretion and without notice to the Borrower: finance "
        "the Loan in whole or in part through financial partners, assign or syndicate all or part "
        "of the financing, and structure economic participations of any nature."))
    story.append(sp())
    story += art("5.2", "Exclusive Administration")
    story.append(bp(
        "Capital Norvex acts as the sole manager of the financing, disbursement administrator and "
        "representative of financial partners. Only Capital Norvex holds decision-making powers "
        "with respect to the Borrower. Financial partners assume no direct liability to the "
        "Borrower, who expressly waives any direct recourse against them."))
    story.append(sp())
    story += art("5.3", "Score Norvex\u2122")
    story.append(bp(
        "The Borrower acknowledges that Capital Norvex uses the proprietary Score Norvex\u2122 "
        "system to evaluate, monitor and rate the file throughout the term of the Loan. The "
        "results of this analysis may influence conditions, disbursement amounts and Lender "
        "decisions."))
    story.append(sp())

    # ── 6 ──────────────────────────────────────────────────────────────────
    story += sec("6. CONDITIONS PRECEDENT TO DISBURSEMENTS")
    story += art("6.1", "Conditions to First Disbursement")
    story.append(bp(
        "No initial disbursement will be made until Capital Norvex has received, reviewed and "
        "approved, in its sole discretion, all of the following:"))
    story += blt([
        "Constitutional documents and resolutions authorizing the loan",
        "Proof of injected equity (real, non-conditional funds)",
        "Detailed final budget and approved construction schedule",
        "Plans and specifications signed and sealed by qualified professionals",
        "General contractor agreement (form and content approved by Lender)",
        "Valid and current building permits",
        "Independent appraisal report (certified appraiser accepted by Lender)",
        "Phase I environmental report (Phase II if required by Lender)",
        "All-risk construction insurance and civil liability insurance ($5M min.)",
        "Registration of first-rank Mortgage",
        "Signed assignment of leases (if applicable)",
        "Personal guarantees from Guarantors identified herein",
        "Complete legal opinion accepted by Lender",
    ])
    story.append(sp())
    story += art("6.2", "Ongoing Conditions")
    story.append(bp("Each subsequent disbursement is conditional upon:"))
    story += blt([
        "Absence of any Event of Default",
        "Compliance with approved Budget and Schedule",
        "Maintenance of required insurance",
        "Validity of all necessary permits",
        "Compliance with applicable laws and regulations",
        "Favourable inspection report from Capital Norvex\u2019s designated Inspector",
    ])
    story.append(sp())

    # ── 7 ──────────────────────────────────────────────────────────────────
    story += sec("7. DISBURSEMENTS \u2014 CAPITAL NORVEX CONTROL")
    story += art("7.1", "Absolute Discretionary Control")
    story.append(bp(
        "Capital Norvex retains absolute, exclusive and discretionary control over all "
        "disbursements. No amount is owed as long as all conditions set forth herein are not "
        "fully satisfied."))
    story.append(sp())
    story += art("7.2", "Frequency and Required Documents")
    story.append(bp("Disbursements are made monthly. Each request must include:"))
    story += blt([
        "Formal signed disbursement request",
        "Independent inspection report (Inspector approved by Capital Norvex)",
        "Certified cost-to-date statement (CCC)",
        "Detailed breakdown of costs incurred and payments made",
        "Partial and final lien waivers from all relevant subcontractors",
        "Professional certificate from responsible architect or engineer",
    ])
    story.append(sp())
    story += art("7.3", "Construction Holdback and Right of Refusal")
    story.append(bp(
        "A holdback of <b>five percent (5%)</b> is maintained on each disbursement as a "
        "<b>construction holdback</b> in accordance with standard practice in Quebec. This "
        "holdback shall be released thirty-five (35) days after Substantial Completion of the "
        "works, subject to the absence of any registered legal hypothec for construction "
        "(art. 2724 and 2726 C.C.Q.) and upon delivery of final waivers from all suppliers and "
        "subcontractors. Capital Norvex may, without obligation to justify:"))
    story += blt([
        "Refuse or reduce any disbursement",
        "Require additional security or additional capital injection",
        "Delay any payment in the event of doubt regarding progress or compliance",
    ])
    story.append(sp())

    story += art("7.4", "Norvex Track\u2122 — 24/7 Disbursement Management Module")
    story.append(bp(
        "Capital Norvex deploys, for the management of progressive Disbursements under the "
        "Loan, its proprietary technology module <b>Norvex Track\u2122</b>. "
        "The Borrower acknowledges and accepts that:"))
    story += blt([
        "Every Disbursement request shall be submitted and documented by the Borrower through the <b>Norvex Track\u2122</b> module;",
        "Each Disbursement is subject to complete documentary verification (inspection report, invoices, progress photos, professional certificates, lien waivers) recorded in the module;",
        "The complete Disbursement history (amounts, dates, supporting documents) is fully traced and accessible <b>24 hours a day, 7 days a week</b>;",
        "Capital Norvex retains, in accordance with Article 7.1, its <b>absolute, exclusive and discretionary control</b> over the authorization or refusal of any Disbursement through Norvex Track\u2122.",
    ])
    story.append(bp(
        "The Norvex Track\u2122 module creates no autonomous right of the Borrower over the "
        "Loan funds and in no way diminishes the powers of Capital Norvex provided for in this "
        "Agreement."))
    story.append(sp())

    story += art("7.5", "Borrower Portal (PWA) — 24/7 Transparency")
    story.append(bp(
        "Capital Norvex makes available to the Borrower a secure digital "
        "<b>Borrower Portal</b> (<b>PWA — Progressive Web Application</b>), accessible "
        "<b>24 hours a day, 7 days a week</b>, from any device (smartphone, tablet, computer). "
        "The Borrower may consult in real time:"))
    story += blt([
        "The Loan balance, the principal disbursed and the principal still available;",
        "The payment schedule, accrued interest and history of payments made;",
        "The status of Disbursement requests submitted via Norvex Track\u2122 (pending, authorized, executed, refused);",
        "Inspection reports, progress photos and documents relevant to the file;",
        "Official notices and communications transmitted by Capital Norvex.",
    ])
    story.append(bp(
        "The Borrower Portal (PWA) is a <b>transparency</b> tool made available to the "
        "Borrower. It does not replace the official written communications provided for in this "
        "Agreement and in no way alters the Borrower's obligations or the Lender's rights."))
    story.append(sp())

    # ── 8 ──────────────────────────────────────────────────────────────────
    story += sec("8. SECURITY")
    story += art("8.1", "Real Estate Mortgage")
    story.append(bp(
        "The Borrower grants Capital Norvex a first-rank real estate mortgage encumbering the "
        "property, its present and future improvements, rents, insurance indemnities and sale "
        "proceeds."))
    story.append(sp())
    story += art("8.2", "Assignment of Leases and Guarantees")
    story.append(bp(
        "The Borrower assigns all present and future rents. Guarantors provide a joint, "
        "irrevocable and unlimited guarantee covering principal, interest, fees and all costs "
        "incurred."))
    story.append(sp())
    story += art("8.3", "Additional Security")
    story.append(bp("Capital Norvex may require, at any time:"))
    story += blt([
        "Construction bond and labour/material payment bond",
        "Irrevocable letter of credit",
        "Corporate guarantee from an entity approved by the Lender",
    ])
    story.append(sp())

    # ── 9 ──────────────────────────────────────────────────────────────────
    story += sec("9. FINANCIAL CONTROL AND CASH FLOW")
    story.append(bp(
        "All funds flow through an account controlled by Capital Norvex. No withdrawal, transfer "
        "or distribution is authorized without prior written authorization. Capital Norvex may "
        "apply amounts received in the following order: fees, interest, principal, reserves. "
        "The Borrower provides full and immediate access to its accounts, books and transactions."))
    story.append(sp())

    # ── 10 ─────────────────────────────────────────────────────────────────
    story += sec("10. COVENANTS")
    story += art("10.1", "Positive Covenants")
    story += blt([
        "Complete the Project in accordance with plans approved by Capital Norvex",
        "Comply with the Budget and Schedule at all times",
        "Pay all contractors, subcontractors and suppliers",
        "Maintain all required insurance",
        "Provide monthly progress reports to the Lender",
        "Immediately notify Capital Norvex of any issue, dispute or delay",
    ])
    story.append(sp())
    story += art("10.2", "Negative Covenants (without written consent)")
    story += blt([
        "No additional debt or charge on the property",
        "No change of general contractor",
        "No material modification to plans or budget",
        "No sale, transfer or assignment of the Project",
        "No distribution to shareholders or partners",
    ])
    story.append(sp())
    story += art("10.3", "Financial Covenants")
    story.append(covenant_tbl([
        ["Covenant", "Threshold", "Verification Frequency"],
        ["Maximum LTV", "75%", "At each disbursement"],
        ["Maximum LTC", "80%", "At each disbursement"],
        ["Interest Reserve", "Required", "Ongoing"],
        ["Financial Reports", "Quarterly", "Ongoing"],
    ]))
    story.append(sp(8))

    # ── 11 ─────────────────────────────────────────────────────────────────
    story += sec("11. REPRESENTATIONS AND WARRANTIES")
    story.append(bp(
        "The Borrower and Guarantors represent and warrant to Capital Norvex that, as of the "
        "signing date and at each disbursement:"))
    story += blt([
        "They are duly incorporated and in good standing under applicable laws",
        "They have full legal capacity to enter into these obligations",
        "All required authorizations have been duly obtained",
        "All information provided is complete, accurate and not misleading",
        "The Project complies with all applicable laws, standards and regulations",
        "No litigation, claim or legal mortgage is pending",
        "No Event of Default exists or is about to occur",
    ])
    story.append(sp())

    # ── 12 ─────────────────────────────────────────────────────────────────
    story += sec("12. EVENTS OF DEFAULT")
    story.append(bp("The following constitute Events of Default, including:"))
    story.append(sp(4))
    story += art("", "Financial")
    story += blt([
        "Default on interest or principal payment",
        "Breach of a financial covenant",
        "Insufficient liquidity to complete the Project",
    ])
    story.append(sp(4))
    story += art("", "Operational")
    story += blt([
        "Work stoppage of more than 5 business days",
        "Significant unapproved delay",
        "Budget overrun without authorization",
        "Abandonment of the Project",
    ])
    story.append(sp(4))
    story += art("", "Legal")
    story += blt([
        "Legal mortgage registered against the property not discharged within 7 days of notice from the Lender (zero tolerance \u2014 see Article 14.bis.1)",
        "Any delay in payment of property taxes, municipal charges, insurance premiums or other current obligations not remedied within 7 days of notice from the Lender (zero tolerance \u2014 see Article 14.bis.2)",
        "Significant seizure or legal proceedings",
        "Loss or invalidity of a security",
    ])
    story.append(sp(4))
    story += art("", "Administrative")
    story += blt([
        "Revocation or suspension of building permits",
        "Failure to maintain required insurance",
        "Misrepresentation or inaccurate information",
        "Breach of the terms of the mortgage deed entered into in connection with this Agreement (indissociability clause \u2014 Article 16.bis)",
    ])
    story.append(sp(4))
    story += art("", "Borrower / Guarantor")
    story += blt([
        "Insolvency, bankruptcy or creditor arrangement",
        "Unauthorized change of control of Borrower",
    ])
    story.append(sp(4))
    story += art("", "Discretionary")
    story += blt([
        "Any event deemed by Capital Norvex to compromise project completion or increase risk",
    ])
    story.append(sp())

    # ── 13 ─────────────────────────────────────────────────────────────────
    story += sec("13. LENDER\u2019S REMEDIES")
    story.append(bp(
        "Upon an Event of Default, Capital Norvex may, without notice or delay:"))
    story += blt([
        "Immediately suspend all disbursements",
        "Declare the Loan immediately due and payable in full",
        "Enforce all security granted",
        "Collect rents and revenues directly",
        "Appoint a receiver with full powers",
        "Exercise any other remedy available at law",
    ])
    story.append(sp())

    # ── 14 ─────────────────────────────────────────────────────────────────
    story += sec("14. STEP-IN RIGHT")
    story.append(bp(
        "Upon an Event of Default, Capital Norvex may, at its sole discretion:"))
    story += blt([
        "Take possession of the Project and access the site without restriction",
        "Replace the general contractor or any other party",
        "Terminate any contract related to the Project",
        "Manage the Works directly or indirectly",
        "Complete the Project through any affiliated entity or agent",
    ])
    story.append(bp(
        "All costs incurred in this context become immediately due and bear interest at the "
        "increased rate provided herein. The Borrower irrevocably waives any challenge to any "
        "intervention made in good faith by Capital Norvex."))
    story.append(sp())

    # ── 14.bis  ZERO TOLERANCE — TAXES AND LEGAL HYPOTHECS ─────────────────
    story += sec("14.bis  ZERO TOLERANCE — TAXES AND LEGAL HYPOTHECS")
    story += art("14.bis.1", "Legal Hypothecs of Construction")
    story.append(bp(
        "<b>NO</b> legal hypothec of construction (art. 2724 and 2726 C.C.Q.) is tolerated. The "
        "Borrower undertakes to settle or have any registered legal hypothec discharged "
        "<b>immediately</b> upon being notified, and at the latest within <b>seven (7) days</b> of "
        "a written notice from the Lender (or sooner if the situation requires, in the Lender's sole "
        "judgment). Failing this, an Event of Default shall be <b>automatically declared</b>, and "
        "the Lender may: (i) directly pay the claim and add the amount to the principal of the Loan "
        "with interest at the default rate; (ii) suspend any future disbursement; (iii) declare the "
        "Loan immediately due and payable and exercise all remedies."))
    story += art("14.bis.2", "Taxes, Charges and Current Obligations")
    story.append(bp(
        "The Borrower undertakes to pay punctually when due all property taxes, school taxes, "
        "local improvement taxes, municipal charges, insurance premiums, and any other current "
        "obligations affecting the Property. <b>NO</b> delay is tolerated. In the event of any "
        "delay or default in payment, the Borrower undertakes to remedy the situation "
        "<b>immediately</b> upon being notified, and at the latest within <b>seven (7) days</b> of "
        "a written notice from the Lender. Failing this, an Event of Default shall be "
        "<b>automatically declared</b>."))
    story.append(sp())

    # ── 14.ter  ASSIGNMENT OF CONTRACTS, PLANS, PERMITS — CONSTRUCTION ─────
    story += sec("14.ter  ASSIGNMENT OF CONTRACTS, PLANS, PERMITS AND RIGHTS — CONSTRUCTION")
    story.append(bp(
        "As additional security to this Loan, and for the purposes of any construction file, the "
        "Borrower assigns to the Lender:"))
    story += blt([
        "All contracts with the general contractor and major subcontractors of the Project",
        "All plans, specifications, and other technical documents of the Project",
        "All building permits, occupancy permits, and other municipal authorizations",
        "All bids, certificates, and warranties (including GCR and any contractor's warranty)",
        "All insurance policies relating to the Project, with Capital Norvex designated as beneficiary",
    ])
    story.append(bp(
        "These assignments become enforceable by operation of law upon an Event of Default. The "
        "Project is further subject to the requirements of the Régie du bâtiment du Québec (RBQ) "
        "and, where applicable (residential construction), to the Garantie de construction "
        "résidentielle (GCR) or any other applicable warranty program. Proof of registration must "
        "be delivered to the Lender prior to any disbursement."))
    story.append(sp())

    # ── 15 ─────────────────────────────────────────────────────────────────
    story += sec("15. REPAYMENT")
    story += art("15.1", "Maturity and Terms")
    story.append(bp(
        "Principal is repayable in full at maturity, upon sale, refinancing or stabilization of "
        "the Project, whichever occurs first. Payments are applied in the following order: fees, "
        "interest, principal."))
    story.append(sp())
    story += art("15.2", "Prepayment")
    story.append(bp(
        "Permitted, subject to a minimum penalty equivalent to three (3) months of interest "
        "calculated at the contractual rate."))
    story.append(sp())

    # ── 16 ─────────────────────────────────────────────────────────────────
    story += sec("16. GENERAL PROVISIONS")
    story.append(gen_tbl([
        ["Governing Law",    "Laws of the Province of Quebec (Canada)"],
        ["Jurisdiction",     "District of Montreal, Quebec"],
        ["Assignment",       "Prohibited without prior written consent of Lender"],
        ["Amendments",       "In writing, signed by the parties"],
        ["Severability",     "Any invalid clause does not affect the remainder of the Agreement"],
        ["Notices",          "In writing, including certified email or registered mail"],
        ["Entire Agreement", "This Agreement constitutes the entire agreement of the parties"],
        ["Waiver",           "No tolerance constitutes a permanent waiver"],
        ["PCMLTFA / FINTRAC","Identity and source-of-funds verifications carried out"],
    ]))
    story.append(sp(8))

    # ── 16.bis  INDISSOCIABILITY WITH MORTGAGE DEED — FUNDAMENTAL CLAUSE ────
    story += sec("16.bis  INDISSOCIABILITY WITH THE MORTGAGE DEED — FUNDAMENTAL CLAUSE")
    story.append(bp(
        "<b>This Loan Agreement and the real estate mortgage deed entered into between the Parties "
        "form an INDISSOCIABLE and complementary contractual whole.</b> The Parties expressly "
        "acknowledge and irrevocably agree that these two documents must be read, interpreted, and "
        "performed jointly, as if they constituted one and the same contract. Any clause, condition, "
        "representation, warranty, covenant, or obligation set forth in this Agreement applies fully "
        "and by operation of law to the Parties to the mortgage deed, and any breach of the terms of "
        "this Agreement automatically constitutes an Event of Default within the meaning of Article "
        "12 and allows the exercise of all hypothecary remedies. Neither Party may invoke the "
        "absence of a clause in one of the two documents to escape an obligation set forth in the "
        "other. In the event of any divergence or ambiguity between the two documents, "
        "<b>the interpretation most favourable to the Lender shall prevail</b>."))
    story.append(sp(8))

    # ── 17 ─────────────────────────────────────────────────────────────────
    story += sec("17. SIGNATURES")
    story.append(bp(
        "IN WITNESS WHEREOF, the parties have signed this Agreement on the date indicated below, "
        "having read it."))
    story.append(bp(
        "<i>For Capital Norvex Inc., this Agreement is signed by the designated representative "
        "below, duly authorized pursuant to a corporate resolution adopted by the sole shareholder "
        "and president, Mrs. Suzanne Breton, a certified true copy of which is attached to the "
        "file.</i>"))
    story.append(sp(10))

    # Lender block
    story += sign_block("LENDER \u2014 CAPITAL NORVEX INC.", [
        "Designated Representative (full name): ___________________________________",
        "Title / Capacity: _________________________________________________________",
        "Pursuant to Corporate Resolution dated: __________________________________",
        "Signed by: Mrs. Suzanne Breton, sole shareholder and president",
        "Date of signature: ________________________________________________________",
    ])
    story.append(sp(10))

    # Borrower block
    story += sign_block("BORROWER", [
        "Corporate Name: __________________________________________________________",
        "Authorized Representative: _______________________________________________",
        "Title: ___________________________________________________________________",
        "Date: ____________________________________________________________________",
    ])
    story.append(sp(10))

    # Guarantor 1
    story += sign_block("GUARANTOR 1", [
        "Full Name: _______________________________________________________________",
        "Date: ____________________________________________________________________",
    ])
    story.append(sp(10))

    # Guarantor 2
    story += sign_block("GUARANTOR 2 (if applicable)", [
        "Full Name: _______________________________________________________________",
        "Date: ____________________________________________________________________",
    ])
    story.append(sp())


def build_schedule_a(story):
    story.append(PageBreak())
    story += sec("SCHEDULE A \u2014 PROJECT DESCRIPTION")
    story.append(params_tbl([
        ["Project Name",                "___________________________________________"],
        ["Municipal Address",           "___________________________________________"],
        ["Municipality / RCM",          "___________________________________________"],
        ["Development Type",            "___________________________________________"],
        ["Number of Units / Area",      "___________________________________________"],
        ["Estimated Value at Completion", "$___________________________________________ CAD"],
        ["Total Project Cost",          "$___________________________________________ CAD"],
        ["Borrower's Equity",           "$___________________________________________ CAD (___%)"],
        ["General Contractor",          "___________________________________________"],
        ["Architect / Engineer",        "___________________________________________"],
        ["Work Start Date",             "___________________________________________"],
        ["Expected Completion Date",    "___________________________________________"],
    ]))
    story.append(sp(10))
    story.append(bp(
        "Plans, specifications, detailed budget and construction schedule constitute integral "
        "parts of this Schedule A and are deemed attached hereto."))
    story.append(sp(8))
    story.append(bp(
        "<i>The French version shall prevail in Quebec.</i>"))
    story.append(sp(12))
    story.append(bp(
        "Initialled and approved by:"))
    story.append(sp(6))
    story.append(bp(
        "_______________________ (Lender)     _______________________ (Borrower)"))


def main():
    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        OUTPUT_FILE,
        pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=0.9 * inch, bottomMargin=0.95 * inch,
        title="Construction Loan Agreement \u2014 Capital Norvex",
        author="Capital Norvex Inc.",
    )
    story = []
    build_cover(story)
    build_body(story)
    build_schedule_a(story)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF generated: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
