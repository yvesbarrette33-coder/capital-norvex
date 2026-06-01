"""
06_partnership_agreement_monthly_en.py
CAPITAL NORVEX — Partnership Agreement — Monthly Payments (EN)
Generates: Monthly_Payment_Partnership_Agreement_CapitalNorvex.pdf
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
OUTPUT_FILE = r'/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres/Monthly_Payment_Partnership_Agreement_CapitalNorvex.pdf'

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
    canvas.drawString(MARGIN + 44, h - 42, "Institutional Private Lending")
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.drawRightString(w - MARGIN, h - 28, "PARTNERSHIP AGREEMENT — MONTHLY PAYMENTS")
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
        "CAPITAL NORVEX  ·  Confidential – For the exclusive use of the signing parties")
    # Bottom line — full address (centered, light grey)
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
    story.append(Paragraph("<i>Institutional Private Lending  |  Quebec &amp; Ontario</i>", ST["cov_sub"]))
    story.append(GoldLine())
    story.append(sp(8))

    block = Table([
        [Paragraph("PARTNERSHIP AGREEMENT", ST["cov_name"])],
        [Paragraph("PRIVATE REAL ESTATE CO-FINANCING", ST["cov_name2"])],
        [Paragraph("MONTHLY PAYMENT LOANS — LAND / ACQUISITION / INCOME PROPERTY", ST["cov_name3"])],
        [Paragraph("<i>Capital Norvex Inc. — Institutional Version — Quebec &amp; Ontario</i>", ST["cov_italic"])],
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
        [Paragraph("PARTNER", ST["tbl_hdr"]),              Paragraph("___________________________________", ST["tbl_val"])],
        [Paragraph("TYPE OF FINANCING", ST["tbl_hdr"]),    Paragraph("Land / Acquisition / Income Property", ST["tbl_val"])],
        [Paragraph("CONTRIBUTION AMOUNT", ST["tbl_hdr"]), Paragraph("$___________________________________ CAD", ST["tbl_val"])],
        [Paragraph("MONTHLY PAYMENT TO PARTNER", ST["tbl_hdr"]), Paragraph("$___________________________________ / month", ST["tbl_val"])],
        [Paragraph("DATE", ST["tbl_hdr"]),                 Paragraph("___________________________________", ST["tbl_val"])],
        [Paragraph("FILE No.", ST["tbl_hdr"]),             Paragraph("___________________________________", ST["tbl_val"])],
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
    story.append(Paragraph("Structured Capital.  Controlled Ambition.", ST["slogan"]))
    story.append(Paragraph(
        "CONFIDENTIAL — For the exclusive use of the signing parties and their legal advisors",
        ST["note"]))
    story.append(PageBreak())


def build_body(story):
    # ── 1 ──────────────────────────────────────────────────────────────────
    story += sec("1. INTERPRETATION AND DEFINITIONS")
    story += art("1.1", "Interpretation")
    story.append(bp(
        "Unless the context otherwise requires, section headings are inserted for convenience only "
        "and do not limit the scope of the provisions. The singular includes the plural and vice versa. "
        "Any reference to a statute includes its amendments, restatements or successors."))
    story.append(sp())
    story += art("1.2", "Definitions")
    defs = [
        ("<b>“Agreement”</b>: This Monthly Payment Partnership Agreement, including all its schedules, "
         "amendments and ancillary documents incorporated by reference."),
        ("<b>“Loan Asset”</b>: The private real-estate financing file (land, acquisition or income "
         "property) granted by Capital Norvex to a third-party Borrower, in which the Partner "
         "participates financially under the terms hereof."),
        ("<b>“Capital Norvex”</b>: CAPITAL NORVEX INC., a corporation incorporated under the laws of "
         "the Province of Quebec, exclusive manager and administrator of the entire Partnership."),
        ("<b>“Contribution”</b>: The capital amount the Partner undertakes to deposit and maintain "
         "in favour of Capital Norvex in order to co-finance the Loan Asset identified in Schedule A."),
        ("<b>“Borrower”</b>: Any company or commercial entity to which Capital Norvex grants private "
         "real-estate financing of the land, acquisition or income-property type, in which the "
         "Partner's Contribution is deployed."),
        ("<b>“Borrower Default Event”</b>: Any payment default or breach by the Borrower under the "
         "loan agreement, including non-payment of a Monthly Payment within the prescribed timeframes."),
        ("<b>“Capital Norvex File Management Fees”</b>: The analysis, structuring and administration "
         "fees representing 3% to 3.5% of the total amount of the Loan Asset, belonging exclusively "
         "to Capital Norvex, deducted at the time of disbursement at the notary's office."),
        ("<b>“Movable Hypothec”</b>: The security published by the Partner in the Register of Personal "
         "and Movable Real Rights (RPMR) on the Loan Asset held by Capital Norvex, pursuant to "
         "articles 2660 et seq. of the Civil Code of Quebec."),
        ("<b>“Monthly Payment”</b>: The monthly interest payment due to the Partner, calculated on "
         "the disbursed Contribution balance at the agreed rate, payable on the first business day "
         "of each month."),
        ("<b>“Standard Mode”</b>: The default payment mechanism whereby the Borrower remits its "
         "monthly payment to Capital Norvex, which redistributes it to the Partner within two (2) "
         "business days thereafter."),
        ("<b>“Direct Mode”</b>: The exceptional and temporary payment mechanism whereby the Borrower "
         "remits its monthly payment directly to the Partner, with a mandatory copy of confirmation "
         "to Capital Norvex."),
        ("<b>“Partner”</b>: The natural or legal person identified in Section 2.2, financial partner "
         "of the Loan Asset, beneficiary of the Monthly Payments."),
        ("<b>“Sale Proceeds”</b>: All net amounts received upon the sale of a property taken in "
         "payment or sold under court supervision, after payment of sale costs, priority charges "
         "and Capital Norvex's legal fees."),
        ("<b>“RPMR”</b>: The Register of Personal and Movable Real Rights kept by the Quebec "
         "Ministry of Justice."),
        ("<b>“Repossession”</b>: The exercise by Capital Norvex of its right of taking in payment "
         "of the property or forced sale under court supervision, following a Borrower Default Event."),
        ("<b>“Norvex Score™”</b>: Capital Norvex's proprietary analysis and rating system used to "
         "evaluate and monitor each Loan Asset."),
    ]
    for d in defs:
        story.append(bp(d))
    story.append(sp())

    # ── 2 ──────────────────────────────────────────────────────────────────
    story += sec("2. PARTIES")
    story += art("2.1", "Capital Norvex Inc. — Exclusive Manager")
    story.append(bp("<b>Corporate Name: CAPITAL NORVEX INC.</b>"))
    story.append(bp("Address: ___________________________________________________________"))
    story.append(bp("Authorized Representative: Yves Barrette"))
    story.append(bp("Title: Founder &amp; Director, Private Lending"))
    story.append(sp())
    story += art("2.2", "Partner")
    story.append(bp("Corporate Name or Full Legal Name: _______________________________________"))
    story.append(bp("Business Number (BN) or SIN (individual): ________________________________"))
    story.append(bp("Registered Address: ___________________________________________________"))
    story.append(bp("Authorized Representative: ____________________________________________"))
    story.append(bp("Title: _______________________________________________________________"))
    story.append(bp("Email: ______________________________________________________________"))
    story.append(bp("Banking Coordinates for Receipt of Monthly Payments:"))
    story.append(bp("Financial Institution: __________________ &nbsp;&nbsp; Transit: __________________"))
    story.append(bp("Account Number: _____________________________________________________"))
    story.append(sp())

    # ── 3 ──────────────────────────────────────────────────────────────────
    story += sec("3. NATURE AND PURPOSE OF THE PARTNERSHIP")
    story += art("3.1", "Spirit of the Partnership")
    story.append(bp(
        "This Agreement is based on a genuine partnership relationship, founded on mutual trust, "
        "complete transparency and respect for the interests of each Party. Capital Norvex undertakes "
        "to treat the Partner as a fully-fledged strategic associate, by paying its Monthly Payments "
        "punctually and by providing all information necessary to monitor its Contribution in real "
        "time via the secure Partner Portal (PWA)."))
    story.append(sp())
    story += art("3.2", "General Structure")
    story.append(bp(
        "The Partner advances a financial Contribution to Capital Norvex, which is deployed as private "
        "real-estate financing of the land, acquisition or income-property type in favour of a third-"
        "party Borrower identified in Schedule A. In consideration, the Partner receives Monthly "
        "Payments corresponding to the interest generated by its Contribution, paid monthly for the "
        "entire term of the Loan Asset."))
    story.append(sp())
    story += art("3.3", "Scope — Monthly Payment Loans Only")
    story.append(bp(
        "This Agreement applies exclusively to Loan Assets of the land, acquisition and income-"
        "property type, characterized by monthly interest payments by the Borrower. It does not "
        "apply to construction or infrastructure loans with progressive disbursements, which are "
        "the subject of a separate agreement."))
    story.append(sp())

    # ── 4 ──────────────────────────────────────────────────────────────────
    story += sec("4. FINANCIAL STRUCTURE — MONTHLY PAYMENTS AND RETURN")
    story += art("4.1", "Loan Asset Parameters")
    story.append(params_tbl([
        ["Borrower",                                "___________________________________________"],
        ["Financing Type",                          "Land / Acquisition / Income Property"],
        ["Contribution Amount",                     "$_________________________________________ CAD"],
        ["Annual Interest Rate to Partner",         "_____ % per year"],
        ["Monthly Payment to Partner",              "$_________________________________________ / month"],
        ["Date of First Payment",                   "_______________"],
        ["Loan Term",                               "_____ months"],
        ["Real Estate Mortgage Ranking",            "1st ranking — Capital Norvex Inc."],
        ["Movable Hypothec RPMR",                   "In favour of Partner on the Loan Asset"],
        ["Payment Method (default)",                "Capital Norvex → Partner (designated CN account)"],
        ["Payment Method (exception)",              "Direct payment Borrower → Partner (if authorized in writing)"],
        ["Norvex Score™",                           "_____ / 100"],
        ["Designated Notary",                       "___________________________________________"],
    ]))
    story.append(sp(8))
    story += art("4.2", "File Management Fees — Belonging Exclusively to Capital Norvex")
    story.append(bp(
        "The Capital Norvex File Management Fees, representing <b>3% to 3.5% of the total amount of "
        "the Loan Asset</b>, are deducted at the time of disbursement made at the notary's office "
        "and belong <b>exclusively and entirely to Capital Norvex Inc.</b> The Partner has no right "
        "to these fees."))
    story.append(sp())
    story += art("4.3", "Monthly Payments — Belonging Exclusively to the Partner")
    story.append(bp(
        "The annual interest generated by the Loan Asset, at the agreed rate of <b>10% to 12% per "
        "year</b>, calculated on the disbursed Contribution balance and paid monthly, belongs "
        "<b>exclusively and entirely to the Partner.</b> Capital Norvex retains no portion of the "
        "interest. Monthly Payments are due on the first business day of each month and remitted to "
        "the Partner within the timeframes set out in Section 5."))
    story.append(sp())
    story += art("4.4", "Capital — Repayment at Maturity")
    story.append(bp(
        "The capital of the Contribution is fully repayable at the maturity of the Loan Asset, "
        "simultaneously with the Borrower's repayment of the loan. No partial repayment of capital "
        "shall be made during the term, except in the cases expressly provided herein."))
    story.append(sp())

    # ── 5 ──────────────────────────────────────────────────────────────────
    story += sec("5. MONTHLY PAYMENT MECHANISM")
    story += art("5.1", "Standard Mode — Capital Norvex to Partner (Rule)")
    story.append(bp(
        "By default and at all times, the applicable payment mechanism is the <b>Standard Mode</b>: "
        "the Borrower deposits its monthly payment into Capital Norvex's designated account, and "
        "Capital Norvex redistributes the Monthly Payment to the Partner within <b>two (2) business "
        "days</b> following receipt. This mechanism ensures complete traceability, rigorous "
        "accounting and optimal protection for both Parties. Capital Norvex maintains a monthly "
        "register of all payments made, accessible to the Partner via the PWA portal."))
    story.append(sp())
    story += art("5.2", "Direct Mode — Payment by the Borrower Directly to the Partner (Exception)")
    story.append(bp(
        "On an exceptional and temporary basis, Capital Norvex may authorize the Direct Mode in "
        "writing, whereby the Borrower remits its Monthly Payment directly to the Partner. This "
        "mode is subject to the following strict conditions:"))
    story += blt([
        "The authorization must be granted in writing by Capital Norvex, for a determined period not exceeding twelve (12) consecutive months;",
        "The Borrower must transmit to Capital Norvex, simultaneously with the payment, a written confirmation (email or notice) indicating the date, amount and details of the transfer made to the Partner;",
        "The Partner must confirm in writing to Capital Norvex the receipt of each Monthly Payment within two (2) business days following its receipt;",
        "Capital Norvex retains at all times the right to revoke the Direct Mode authorization, with five (5) business days' notice, and to return to the Standard Mode without justification;",
        "Failing confirmation of receipt by the Partner, Capital Norvex may presume non-payment and trigger the applicable procedures.",
    ])
    story.append(sp())
    story += art("5.3", "Capital Norvex's Institutional Preference")
    story.append(bp(
        "Capital Norvex favours the Standard Mode at all times, which ensures centralized management, "
        "precise accounting and maximum legal protection for all Parties. The Direct Mode is a "
        "temporary accommodation offered in the early phases of the file's life or in exceptional "
        "justified circumstances. It does not constitute an acquired right of the Partner or the "
        "Borrower."))
    story.append(sp())
    story += art("5.4", "Partner Portal (PWA) — 24/7 Transparency on All the Partner's Loans")
    story.append(bp(
        "Simultaneously with each Monthly Payment made, Capital Norvex sends the Partner a "
        "monthly statement confirming: payment date, amount paid, Contribution balance, "
        "accrued interest and any other relevant information. The Partner also has access "
        "<b>24 hours a day, 7 days a week</b>, to its secure <b>Partner Portal</b> (PWA — "
        "Progressive Web Application), accessible from any device. This portal constitutes "
        "a <b>contractual right</b> of the Partner and provides real-time access, for <b>all "
        "of its active Loan Assets</b>, to:"))
    story += blt([
        "Contribution balance and complete history of Monthly Payments received",
        "Schedule of upcoming payments and alerts on any Borrower delay",
        "File documents (hypothec deed, appraisals, insurance policies, account statements)",
        "Direct communications and secure messaging with Capital Norvex",
        "Automatic alerts for any material event affecting the file",
    ])
    story.append(sp())
    story += art("5.5", "Norvex Track™ — Monitoring and Audit Module 24/7")
    story.append(bp(
        "Capital Norvex also provides the Partner with the <b>Norvex Track™</b> module, a "
        "proprietary technological tool integrated into the Partner Portal that allows the "
        "Partner, <b>24 hours a day, 7 days a week</b>, to:"))
    story += blt([
        "<b>Receive</b> in real time each Monthly Payment confirmation, accompanied by the detailed statement and supporting documentation;",
        "<b>Review</b> online all file documents (hypothec deed, insurance policies, appraisals, releases) from any device;",
        "<b>Consult</b> in real time the Contribution balance, accrued interest, payment schedule and any material event affecting the file;",
        "<b>Receive</b> automatically any alert in the event of delay, default or material change — including written notice within five (5) business days pursuant to Section 7.3;",
        "<b>Audit</b> at any time the complete operations history on the Loan Asset, ensuring absolute traceability.",
    ])
    story.append(bp(
        "The Partner's use of <b>Norvex Track™</b> constitutes an <b>additional transparency "
        "guarantee</b>: the Partner retains at all times complete and independent visibility "
        "over its Loan Asset, without having to wait for a periodic report. This module is "
        "complementary to the monthly report sent by Capital Norvex (Section 7.3) and to the "
        "Partner Portal (Section 5.4)."))
    story.append(sp())

    # ── 6 ──────────────────────────────────────────────────────────────────
    story += sec("6. PARTNER SECURITY — MOVABLE HYPOTHEC AT THE RPMR")
    story += art("6.1", "Mandatory Publication Before Disbursement")
    story.append(bp(
        "As security for the repayment of its Contribution and the payment of the Monthly Payments, "
        "Capital Norvex grants in favour of the Partner a movable hypothec without delivery on the "
        "Loan Asset identified in Schedule A, pursuant to articles 2660 et seq. of the Civil Code of "
        "Quebec. This security must be published by the Partner in the RPMR within five (5) business "
        "days following the signature hereof and, in any event, prior to any disbursement at the "
        "notary's office."))
    story.append(sp())
    story += art("6.2", "Scope of the Security")
    story.append(bp(
        "The Movable Hypothec bears on Capital Norvex's claim rights against the Borrower under the "
        "Loan Asset. It confers upon the Partner no direct real right in the immovable hypothecated "
        "by the Borrower. The security guarantees the repayment of the Contribution and the payment "
        "of all Monthly Payments owed."))
    story.append(sp())
    story += art("6.3", "Discharge at Maturity")
    story.append(bp(
        "The Partner irrevocably undertakes to discharge the registration at the RPMR within ten (10) "
        "business days following receipt of the full repayment of its Contribution and of all Monthly "
        "Payments owed. Any failure to discharge within this period entitles Capital Norvex to "
        "proceed with the discharge at the Partner's exclusive expense."))
    story.append(sp())

    # ── 7 ──────────────────────────────────────────────────────────────────
    story += sec("7. EXCLUSIVE MANAGEMENT BY CAPITAL NORVEX — IN A SPIRIT OF GOOD FAITH")
    story += art("7.1", "Principle of Exclusive Management and Good Faith")
    story.append(bp(
        "Capital Norvex assumes exclusive management of the Loan Asset and the operational "
        "relationship with the Borrower. This management is exercised <b>at all times in a spirit "
        "of good faith</b> and absolute transparency toward the Partner, in accordance with Articles "
        "6 and 1375 of the <i>Civil Code of Quebec</i>. The Partner does not communicate directly "
        "with the Borrower or its representatives, but retains at all times its right to complete "
        "information and consultation for any material decision, as set out in Sections 7.3 and 8.4."))
    story.append(sp())
    story += art("7.2", "Capital Norvex's Powers")
    story += blt([
        "Manage the entire contractual relationship with the Borrower",
        "Declare a Default Event and exercise all remedies",
        "Decide to proceed with Repossession or court-supervised sale (in consultation with the Partner pursuant to Section 8.4)",
        "Appoint a Receiver or any other mandatary",
        "Negotiate and conclude any settlement with the Borrower (in consultation with the Partner for material matters)",
        "Authorize or revoke the Direct Payment Mode",
        "Manage the property in the event of Repossession",
    ])
    story.append(sp())
    story += art("7.3", "Transparency and Monthly Reports")
    story.append(bp(
        "Capital Norvex provides the Partner with a complete monthly report simultaneously with each "
        "Monthly Payment, including the file status, the Contribution balance and any material event. "
        "In the event of a Borrower Default Event, Capital Norvex notifies the Partner in writing "
        "within five (5) business days and consults the Partner to determine the best protection strategy."))
    story.append(sp())

    # ── 8 ──────────────────────────────────────────────────────────────────
    story += sec("8. BORROWER DEFAULT — JOINT MANAGEMENT IN PARTNERSHIP")
    story += art("8.1", "Capital Norvex Does Not Assume the Borrower's Unpaid Monthly Payments")
    story.append(bp(
        "In the event of non-payment of a Monthly Payment by the Borrower, <b>Capital Norvex assumes "
        "no substitution obligation and does not pay the Monthly Payment to the Partner in lieu of "
        "the defaulting Borrower.</b> Capital Norvex is neither a guarantor nor surety for the "
        "Borrower's payment obligations to the Partner."))
    story.append(sp())
    story += art("8.2", "Capitalization of Unpaid Monthly Payments")
    story.append(bp(
        "Monthly Payments not collected due to Borrower default <b>are automatically capitalized</b> "
        "and added to the balance owed to the Partner. Such capitalized amounts themselves bear "
        "interest at the contractual rate. All capitalized Monthly Payments are repaid to the Partner "
        "from Sale Proceeds upon Repossession, as a priority and before any other distribution."))
    story.append(sp())
    story += art("8.3", "Borrower's Default Does Not Constitute Capital Norvex's Default")
    story.append(bp(
        "The Parties expressly acknowledge that a Borrower Default Event <b>does not in any way "
        "constitute a Default Event of Capital Norvex</b> toward the Partner. Capital Norvex remains "
        "fully committed to managing the file diligently and in good faith until full recovery of "
        "amounts owed."))
    story.append(sp())
    story += art("8.4", "Joint Management and Strategic Decisions in Partnership")
    story.append(bp(
        "Upon a Borrower Default Event, Capital Norvex and the Partner <b>work in active "
        "partnership</b>. Capital Norvex assumes day-to-day operational management, but major "
        "strategic decisions are taken <b>jointly</b> by both Parties, according to the following process:"))
    story += num_list([
        ("1.", "<b>Immediate Notice and Consultation:</b> Within five (5) business days of identifying the default, Capital Norvex simultaneously notifies the Borrower and the Partner in writing, and convenes the Partner to a consultation meeting (in person or by videoconference) within the following seven (7) days."),
        ("2.", "<b>60-Day Notice to Borrower:</b> Capital Norvex issues a formal default notice to the Borrower granting sixty (60) days to remedy, pursuant to Articles 2757 et seq. of the <i>Civil Code of Quebec</i>. During this period, Capital Norvex keeps the Partner fully informed."),
        ("3.", "<b>Joint Decision at Expiry of 60 Days:</b> Failing remediation, Capital Norvex and the Partner take <b>jointly</b> the decision on the next step: (a) <b>taking in payment</b> by Capital Norvex (with appropriate compensation to the Partner); (b) <b>court-supervised sale</b>; (c) any other lawful solution. Failing agreement within fifteen (15) days, the mediation procedure under Section 12.5 applies."),
        ("4.", "<b>Selection of Real Estate Broker:</b> If sale is the chosen option, the broker is selected <b>jointly</b> by the Parties. The listing mandate is signed jointly."),
        ("5.", "<b>Distribution of Sale Proceeds:</b> Capital Norvex distributes Sale Proceeds according to the priority order in Section 8.6, in full transparency with the Partner."),
    ])
    story.append(sp())
    story += art("8.5", "Legal Fees of Repossession — Borne by Capital Norvex")
    story.append(bp(
        "All legal fees, lawyers' fees, notary fees and other costs incurred in Repossession "
        "proceedings are collected as first priority from Sale Proceeds. The Partner bears no "
        "additional costs beyond its initial Contribution. Capital Norvex assumes responsibility "
        "for conducting these proceedings diligently and competently."))
    story.append(sp())
    story += art("8.6", "Distribution of Sale Proceeds in the Event of Repossession")
    story.append(bp("Sale Proceeds are distributed in the following priority order:"))
    story += num_list([
        ("1.", "Legal fees and direct realization costs — Capital Norvex."),
        ("2.", "Full repayment of the Partner's Contribution."),
        ("3.", "Repayment of all capitalized Monthly Payments owed to the Partner."),
        ("4.", "Repayment to Capital Norvex of any amount advanced in connection with the Repossession."),
        ("5.", "Any residual balance belongs to Capital Norvex."),
    ])
    story.append(sp())

    # ── 9 ──────────────────────────────────────────────────────────────────
    story += sec("9. PARTNER'S COMMITMENT FOR THE TERM OF THE LOAN ASSET")
    story += art("9.1", "Firm Commitment Until the End of the Loan Asset")
    story.append(bp(
        "The Partner commits to maintain its Contribution in place for the full term of the Loan "
        "Asset, until full repayment by the Borrower. Once the file is brought to term, the Partner "
        "is free not to renew its partnership and may recover its full Contribution with all Monthly Payments owed. "
        "No early withdrawal is permitted during the term of the Loan Asset, except as expressly "
        "provided in Section 9.3."))
    story.append(sp())
    story += art("9.2", "Assignment and Encumbrance — Reasonable Consent")
    story.append(bp(
        "The Partner may assign, transfer, pledge or otherwise encumber its rights under this "
        "Agreement with the prior written consent of Capital Norvex, which consent <b>shall not be "
        "unreasonably withheld</b>. Capital Norvex shall examine any such request in good faith and "
        "within a reasonable timeframe."))
    story.append(sp())
    story += art("9.3", "Exceptions — Authorized Early Exit")
    story += blt([
        "Capital Norvex expressly agrees in writing and makes necessary arrangements to fully replace the Contribution without interrupting the financing;",
        "Capital Norvex decides to repay the Partner and replace it, pursuant to Section 9.4;",
        "<b>Material Breach by Capital Norvex</b> of its obligations under this Agreement (notably documented fraud, persistent failure of transparency, material breach of good faith commitments), not remedied within thirty (30) days of a written notice from the Partner.",
    ])
    story.append(sp())
    story += art("9.4", "Capital Norvex's Right to Replace the Partner — Framework")
    story.append(bp(
        "Capital Norvex may, in case of a serious and objective reason, replace the Partner with "
        "another partner or its own funds, subject to the following cumulative conditions:"))
    story += blt([
        "Minimum written notice of <b>thirty (30) days</b> to the Partner, setting out the reasons;",
        "Remittance to the Partner, in a single payment: (i) the full Contribution; (ii) all Monthly Payments owed and not yet paid as of the repayment date;",
        "<b>No penalty or retention</b> may be imposed on the Partner under this replacement;",
        "The Partner shall discharge the Movable Hypothec within ten (10) business days of full receipt of amounts owed.",
    ])
    story.append(sp())
    story += art("9.5", "No Financial Penalty in Case of Non-Compliant Withdrawal")
    story.append(bp(
        "Should the Partner proceed with a withdrawal not in compliance with Sections 9.1 through 9.4, "
        "<b>no financial penalty</b> shall be imposed on it. The Parties commit to meet in good faith "
        "to find a joint solution allowing financing continuity. Failing an amicable solution, the "
        "dispute shall be submitted to the mediation procedure under Section 12.5. Judicial recourse "
        "is limited to the reparation of actual and documented prejudice (excluding any contractual "
        "lump-sum penalty)."))
    story.append(sp())

    # ── 10 ──────────────────────────────────────────────────────────────────
    story += sec("10. REPRESENTATIONS AND WARRANTIES OF THE PARTIES")
    story += art("10.1", "Partner's Representations")
    story += blt([
        "It is duly incorporated, authorized and in good standing under applicable laws",
        "It has full legal and financial capacity to contract under this Agreement",
        "The Contribution comes from lawful, declared funds compliant with regulatory requirements",
        "There is no litigation or encumbrance that may affect its rights",
        "It has obtained all necessary legal and tax advice",
    ])
    story.append(sp())
    story += art("10.2", "Capital Norvex's Representations")
    story += blt([
        "It is duly incorporated and authorized to carry on its activities in Quebec and Ontario",
        "The Loan Asset has been analyzed and approved in accordance with its internal policies",
        "The applicable Norvex Score™ was calculated in good faith",
        "It will pay the Monthly Payments to the Partner punctually in accordance with the terms hereof",
    ])
    story.append(sp())

    # ── 11 ──────────────────────────────────────────────────────────────────
    story += sec("11. CONFIDENTIALITY")
    story.append(sp(4))
    story.append(bp(
        "Each Party undertakes to treat as strictly confidential any information received from the "
        "other Party under this Agreement. This obligation survives the termination or expiration "
        "of this Agreement for a period of five (5) years."))
    story.append(sp())

    # ── 12 ──────────────────────────────────────────────────────────────────
    story += sec("12. GENERAL PROVISIONS")
    story += art("12.1", "Governing Law and Jurisdiction")
    story.append(bp(
        "This Agreement is governed by the <b>laws of the Province of Quebec and the federal laws "
        "of Canada applicable therein</b>. Any dispute falls under the exclusive jurisdiction of "
        "the courts of the judicial district of Montreal, subject to Sections 12.5 and 12.6."))
    story.append(sp())
    story += art("12.2", "Amendments, Notices and Assignment")
    story += blt([
        "<b>Amendments:</b> Any modification must be in writing and signed by both Parties.",
        "<b>Notices:</b> Any notice shall be given in writing, by email with acknowledgment of receipt or by registered mail.",
        "<b>Assignment:</b> Pursuant to Section 9.2, assignment of the Partner's rights is permitted with prior written consent of Capital Norvex, which shall not be unreasonably withheld.",
    ])
    story.append(sp())
    story += art("12.3", "Severability, Entire Agreement and Waiver")
    story += blt([
        "<b>Severability:</b> Any invalid clause does not affect the remainder of this Agreement.",
        "<b>Entire Agreement:</b> This Agreement, together with its Schedules and the Movable Hypothec, constitutes the entire agreement between the Parties.",
        "<b>Waiver:</b> No tolerance shall constitute a permanent waiver.",
    ])
    story.append(sp())
    story += art("12.4", "Language and Interpretation")
    story.append(bp(
        "This Agreement is also available in French. <b>In case of divergence, the French version "
        "prevails in Quebec.</b> The Parties acknowledge having expressly waived the application of "
        "Article 1432 of the <i>Civil Code of Quebec</i> regarding interpretation against the drafter."))
    story.append(sp())
    story += art("12.5", "Mandatory Mediation Before Any Judicial Recourse")
    story.append(bp(
        "The Parties commit to <b>attempting to resolve amicably, by mediation</b>, any dispute "
        "arising out of this Agreement <b>before initiating any judicial proceeding</b>. The procedure is:"))
    story += num_list([
        ("1.", "Written notice describing the dispute, sent to the other Party."),
        ("2.", "Fifteen (15) days to attempt to resolve through direct, good-faith discussion."),
        ("3.", "Failing resolution, joint designation of an independent mediator within ten (10) days."),
        ("4.", "At least one (1) mediation session, costs shared equally."),
        ("5.", "Failing settlement within sixty (60) days following the mediator's appointment, judicial recourse is permitted."),
        ("6.", "<b>Exception:</b> Conservatory measures or urgent injunctions to preserve hypothecary rights or prevent irreparable harm."),
    ])
    story.append(sp())
    story += art("12.6", "Good Faith and Collaboration")
    story.append(bp(
        "The Parties commit to perform this Agreement <b>in good faith</b>, in accordance with "
        "Articles 6, 7 and 1375 of the <i>Civil Code of Quebec</i>, in a spirit of collaboration, "
        "transparency and mutual respect."))
    story.append(sp())
    story += art("12.7", "Indissociability with the Movable Hypothec")
    story.append(bp(
        "This Partnership Agreement and the Movable Hypothec on Individual Claim granted by Capital "
        "Norvex in favour of the Partner form <b>an indissociable contractual whole</b>. The two "
        "documents shall be read, interpreted and performed jointly. Any breach of this Agreement "
        "automatically constitutes a Default Event under the Movable Hypothec, and vice versa. In "
        "case of divergence, the interpretation most protective of the Partner (as hypothecary "
        "creditor) shall prevail."))
    story.append(sp())

    # ── 13 SIGNATURES ───────────────────────────────────────────────────────
    story += sec("13. SIGNATURES")
    story.append(sp(4))
    story.append(bp(
        "IN WITNESS WHEREOF, the parties have signed this Monthly Payment Partnership Agreement "
        "on the date indicated below, having read it in full and obtained such legal and tax advice "
        "as they deemed appropriate."))
    story.append(sp(10))

    story.append(dark_banner("CAPITAL NORVEX INC. — EXCLUSIVE MANAGER", GOLD))
    story.append(sign_pair("Authorized Representative:", "Title:"))
    story.append(sign_pair("Date:", "Signature:"))
    story.append(sp(18))

    story.append(dark_banner("PARTNER", WHITE))
    story.append(sign_pair("Corporate Name:", "Authorized Representative:"))
    story.append(sign_pair("Title:", "Date:"))
    story.append(sp(14))
    story.append(Paragraph("Signature:", ST["sign_lbl"]))
    story.append(sp(16))
    story.append(GoldLine(thickness=0.8))

    # ── SCHEDULE A ──────────────────────────────────────────────────────────
    story.append(PageBreak())
    story += sec("SCHEDULE A — LOAN ASSET DESCRIPTION")
    story.append(sp(4))
    story.append(params_tbl([
        ["Borrower",                            "___________________________________________"],
        ["Financing Type",                      "Land / Acquisition / Income Property"],
        ["Contribution Amount",                 "$_________________________________________ CAD"],
        ["Annual Interest Rate to Partner",     "_____ % per year"],
        ["Monthly Payment to Partner",          "$_________________________________________ / month"],
        ["Date of First Payment",               "_______________"],
        ["Loan Term",                           "_____ months"],
        ["Real Estate Mortgage Ranking",        "1st ranking — Capital Norvex Inc."],
        ["Movable Hypothec RPMR",               "In favour of Partner on the Loan Asset"],
        ["Payment Method (default)",            "Capital Norvex → Partner (designated CN account)"],
        ["Payment Method (exception)",          "Direct payment Borrower → Partner (if authorized in writing)"],
        ["Norvex Score™",                       "_____ / 100"],
        ["Designated Notary",                   "___________________________________________"],
    ]))
    story.append(sp(16))
    paraph = Table([[
        Paragraph("Initialled — Capital Norvex: ___________________________", ST["sign_lbl"]),
        Paragraph("Initialled — Partner: ___________________________", ST["sign_lbl"]),
    ]], colWidths=[BW*0.5, BW*0.5])
    story.append(paraph)
    story.append(sp(24))
    story.append(Paragraph(
        "<i>This Agreement is governed by the laws of the Province of Quebec (Canada). "
        "The French version shall prevail in Quebec.</i>",
        ST["note"]))
    story.append(Paragraph(
        "Confidential — For the exclusive use of the signing parties © 2026 Capital Norvex Inc. — capitalnorvex.ca",
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
    print(f"✅  Monthly_Payment_Partnership_Agreement_CapitalNorvex.pdf generated.")


if __name__ == "__main__":
    main()
