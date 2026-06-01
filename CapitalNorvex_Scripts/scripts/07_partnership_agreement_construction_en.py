"""
07_partnership_agreement_construction_en.py
CAPITAL NORVEX — Partnership Agreement — Construction (EN)
Generates: Partnership_Agreement_Construction_CapitalNorvex.pdf
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
OUTPUT_FILE = r'/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres/Partnership_Agreement_Construction_CapitalNorvex.pdf'

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
    canvas.drawRightString(w - MARGIN, h - 28, "PARTNERSHIP AGREEMENT — CONSTRUCTION")
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
    story.append(Paragraph("<i>Institutional Private Lending  |  Quebec &amp; Ontario</i>", ST["cov_sub"]))
    story.append(GoldLine())
    story.append(sp(8))

    block = Table([
        [Paragraph("PARTNERSHIP AGREEMENT", ST["cov_name"])],
        [Paragraph("PRIVATE REAL ESTATE CO-FINANCING", ST["cov_name2"])],
        [Paragraph("CONSTRUCTION &amp; INFRASTRUCTURE LOANS", ST["cov_name3"])],
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
        [Paragraph("PARTNER", ST["tbl_hdr"]),               Paragraph("___________________________________", ST["tbl_val"])],
        [Paragraph("TYPE OF FINANCING", ST["tbl_hdr"]),     Paragraph("Commercial Construction / Infrastructure", ST["tbl_val"])],
        [Paragraph("CONTRIBUTION AMOUNT", ST["tbl_hdr"]),   Paragraph("$___________________________________ CAD", ST["tbl_val"])],
        [Paragraph("ANNUAL RETURN RATE", ST["tbl_hdr"]),    Paragraph("_____ % per year", ST["tbl_val"])],
        [Paragraph("DATE", ST["tbl_hdr"]),                  Paragraph("___________________________________", ST["tbl_val"])],
        [Paragraph("FILE No.", ST["tbl_hdr"]),              Paragraph("___________________________________", ST["tbl_val"])],
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
        "Any reference to a statute includes its amendments, restatements or successors. Terms not "
        "defined herein have their customary meaning in the commercial real estate lending industry "
        "in Quebec."))
    story.append(sp())
    story += art("1.2", "Definitions")
    defs = [
        ('<b>"Agreement"</b>: This Partnership Agreement, all schedules, amendments and ancillary '
         'documents incorporated by reference.'),
        ('<b>"Loan Asset"</b>: construction or infrastructure real estate financing file granted by '
         'Capital Norvex to third-party Borrower in which Partner participates.'),
        ('<b>"Capital Norvex"</b>: CAPITAL NORVEX INC., corporation constituted under laws of Province '
         'of Quebec, acting as exclusive manager and sole administrator.'),
        ('<b>"Contribution"</b>: capital amount Partner commits to deposit and maintain in favour of '
         'Capital Norvex to co-finance Loan Asset in Schedule A.'),
        ('<b>"Disbursement"</b>: any advance of funds to Borrower under Loan Asset, including first '
         'disbursement before notary and any subsequent progressive disbursement.'),
        ('<b>"Borrower"</b>: any corporation or commercial entity to whom Capital Norvex grants private '
         'real estate financing of construction or infrastructure type.'),
        ('<b>"Borrower Default Event"</b>: any payment default or breach by Borrower under loan '
         'agreement binding it to Capital Norvex, including non-payment of interest or principal at maturity.'),
        ('<b>"Partner Default Event"</b>: any breach by Partner of its obligations under this Agreement, '
         'as defined in Section 10.'),
        ('<b>"Capital Norvex File Fees"</b>: analysis, arrangement and administration fees representing '
         '3% to 3.5% of total Loan Asset amount, collected at first notarial disbursement and belonging '
         'exclusively to Capital Norvex.'),
        ('<b>"Movable Hypothec"</b>: security published by Partner at Register of Personal and Movable '
         'Real Rights (RPMR) on Loan Asset held by Capital Norvex, pursuant to articles 2660 et seq. '
         'of Civil Code of Quebec.'),
        ('<b>"Interest"</b>: annual interest generated by Loan Asset, calculated daily and compounded '
         'monthly on disbursed Contribution balance, belonging exclusively to Partner.'),
        ('<b>"Partner"</b>: individual or legal entity identified in Section 2.2, acting as financial '
         'financial partner of the Loan Asset.'),
        ('<b>"Sale Proceeds"</b>: all net amounts received upon sale of repossessed property or property '
         'sold under judicial authority, after payment of selling costs, priority charges and Capital '
         "Norvex's legal fees."),
        ('<b>"Net Sale Profit"</b>: surplus of Sale Proceeds after full repayment of Partner\'s '
         "Contribution, capitalized Interest and Capital Norvex's File Fees."),
        ('<b>"RPMR"</b>: Register of Personal and Movable Real Rights maintained by Quebec Ministry of Justice.'),
        ('<b>"Repossession"</b>: Capital Norvex\'s exercise of its right to take mortgaged property in '
         'payment or to force its sale under judicial authority, following a Borrower Default Event.'),
        ('<b>"Norvex Score™"</b>: Capital Norvex\'s proprietary analysis and rating system used for '
         'initial assessment, ongoing monitoring and risk management of each Loan Asset.'),
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
    story.append(bp("Phone: ______________________________________________________________"))
    story.append(sp())

    # ── 3 ──────────────────────────────────────────────────────────────────
    story += sec("3. NATURE AND PURPOSE OF THE PARTNERSHIP")
    story += art("3.1", "Partnership Spirit — A Relationship of Trust and Transparency")
    story.append(bp(
        "This Agreement is grounded in a genuine partnership relationship built on mutual trust, "
        "full transparency and respect for each party's interests. Capital Norvex commits to treating "
        "the Partner as a full strategic partner, providing all information needed to monitor their "
        "Contribution safely and in real time. The Partner, in turn, commits to supporting Capital Norvex "
        "in achieving its financing objectives with diligence and good faith."))
    story.append(sp())
    story += art("3.2", "General Structure")
    story.append(bp(
        "The Partner advances a financial Contribution to Capital Norvex, which is fully deployed by "
        "Capital Norvex as private real estate financing of the construction or infrastructure type to "
        "a third-party Borrower identified in Schedule A. Capital Norvex acts as exclusive manager, "
        "lender of record and sole administrator of the Loan Asset, thereby ensuring the protection "
        "of the Partner's rights at every stage."))
    story.append(sp())
    story += art("3.3", "Scope — Construction and Infrastructure Loans Only")
    story.append(bp(
        "This Agreement applies exclusively to Loan Assets of the commercial construction and "
        "infrastructure financing type, characterized by progressive monthly disbursements based on "
        "construction progress. It does not apply to fixed-payment loans (land financing, income "
        "property acquisition), which are governed by a separate agreement."))
    story.append(sp())
    story += art("3.4", "Independence of the Parties")
    story.append(bp(
        "This Agreement does not create any partnership, trust, joint venture, employment or implied "
        "agency relationship between Capital Norvex and the Partner beyond what is expressly provided "
        "herein. Each party remains a distinct and independent legal entity."))
    story.append(sp())
    story += art("3.5", "Acknowledgment of Norvex Score™")
    story.append(bp(
        "The Partner acknowledges and agrees that Capital Norvex uses its proprietary Norvex Score™ "
        "system to analyze, approve, monitor and rate each Loan Asset throughout its term. The Partner "
        "accepts decisions made by Capital Norvex based on this system, subject to compliance with "
        "this Agreement."))
    story.append(sp())

    # ── 4 ──────────────────────────────────────────────────────────────────
    story += sec("4. FINANCIAL STRUCTURE — REVENUE AND PROFIT SHARING")
    story += art("4.1", "Revenue Allocation Table")
    story.append(rev_tbl([
        ["Revenue Item", "Beneficiary"],
        ["File Fees (3% to 3.5%)", "Capital Norvex Inc. — exclusively"],
        ["Annual Interest (10% to 12%)", "Partner — exclusively"],
        ["Net profit on sale — Repossession only",
         "50% Capital Norvex / 50% Partner (after priority repayment of Partner)"],
        ["Sale with no net profit — Repossession",
         "Partner recovers 100% of Contribution + capitalized interest. No loss to Partner."],
        ["Legal fees (repossession proceedings)", "Capital Norvex Inc. — at its own expense"],
    ]))
    story.append(sp(8))
    story += art("4.2", "File Fees — Belong Exclusively to Capital Norvex")
    story.append(bp(
        "The Capital Norvex File Fees, representing <b>3% to 3.5% of the total Loan Asset amount</b>, "
        "are collected at the first notarial disbursement and belong <b>exclusively and entirely to "
        "Capital Norvex Inc.</b> The Partner has no entitlement to these fees. They constitute Capital "
        "Norvex's compensation for analysis, structuring and administration of the Loan Asset."))
    story.append(sp())
    story += art("4.3", "Interest — Belongs Exclusively to the Partner")
    story.append(bp(
        "The annual interest generated by the Loan Asset, at the agreed rate of <b>10% to 12% per "
        "year</b>, calculated daily and compounded monthly on the disbursed Contribution balance, "
        "belongs <b>exclusively and entirely to the Partner.</b> Capital Norvex retains no portion "
        "of the interest. Interest accrues without interruption from the first to the last day of "
        "the Loan Asset, including throughout the entire construction period, the post-construction "
        "stabilization period and the period leading up to the banking exit. There is no interest "
        "suspension period. Interest is compounded monthly and repaid in full to the Partner upon "
        "file closure."))
    story.append(sp())
    story += art("4.4", "Repayment Structure — 18-Month Construction Loan")
    story.append(bp(
        "For Loan Assets of the commercial construction type with a standard term of eighteen (18) "
        "months, repayment is structured as follows, as set out in Schedule A:"))
    story += num_list([
        ("1.", "<b>Construction Phase (Months 1 to 18):</b> Funds disbursed progressively based on construction progress. Interest compounded monthly. No monthly payments required from Borrower during this phase."),
        ("2.", "<b>Post-Construction Phase — Stabilization (approx. Months 19 to 20):</b> Period following substantial completion allows Borrower to lease up and prepare for banking exit. Interest continues to accrue and compound."),
        ("3.", "<b>Monthly Payment Phase (from approx. Month 20 onward):</b> Borrower begins making monthly payments covering current interest while awaiting permanent bank financing."),
        ("4.", "<b>Banking Exit — File Closure:</b> Borrower secures permanent institutional financing and repays Capital Norvex in full: principal, all capitalized unpaid interest and all ancillary fees. Capital Norvex then proceeds with full repayment of Partner."),
    ])
    story.append(sp())
    story += art("4.5", "Net Sale Profit Sharing — Repossession Only")
    story.append(bp(
        "The 50/50 profit-sharing mechanism between Capital Norvex and the Partner applies exclusively "
        "in the event of a Repossession followed by a sale generating a Net Sale Profit. "
        "<b>Priority Order of Distribution of Sale Proceeds:</b>"))
    story += num_list([
        ("1.", "Legal fees, receiver fees, expert fees and all direct realization costs — borne by Capital Norvex, first priority from Sale Proceeds."),
        ("2.", "Full repayment of Partner's Contribution."),
        ("3.", "Repayment of all capitalized unpaid Interest owed to Partner."),
        ("4.", "Repayment to Capital Norvex of amounts advanced in connection with Repossession."),
        ("5.", "Distribution of residual Net Sale Profit: 50% to Capital Norvex / 50% to Partner."),
    ])
    story.append(sp())
    story += art("4.6", "No Net Profit — Partner Capital Protection")
    story.append(bp(
        "If Sale Proceeds, after settlement of items 1 and 4 above, generate no Net Sale Profit, "
        "the Partner recovers its Contribution and all capitalized Interest in full, and suffers no "
        "loss in connection with the sale. Capital Norvex assumes no obligation to guarantee return "
        "or capital beyond the rights conferred by the Movable Hypothec and the structure of this Agreement."))
    story.append(sp())

    # ── 5 ──────────────────────────────────────────────────────────────────
    story += sec("5. PARTNER SECURITY — MOVABLE HYPOTHEC AT THE RPMR")
    story += art("5.1", "Mandatory Registration Before Any Disbursement")
    story.append(bp(
        "As security for repayment of the Contribution, Interest and share of Net Sale Profit (if "
        "applicable), Capital Norvex grants in favour of the Partner a movable hypothec without "
        "delivery on the Loan Asset identified in Schedule A, pursuant to articles 2660 et seq. of "
        "the Civil Code of Quebec. This security must be registered by the Partner at the RPMR within "
        "five (5) business days of signing this Agreement and, in all cases, before the first Disbursement."))
    story.append(sp())
    story += art("5.2", "Scope and Limits of the Security")
    story.append(bp(
        "The Movable Hypothec covers Capital Norvex's receivable rights against the Borrower under "
        "the Loan Asset. It does not confer upon the Partner any direct real property right over the "
        "Borrower's mortgaged property, any right to intervene in file management, or any direct "
        "recourse against the Borrower. The security guarantees only Capital Norvex's payment of "
        "amounts owed to the Partner under this Agreement."))
    story.append(sp())
    story += art("5.3", "Discharge at Maturity")
    story.append(bp(
        "The Partner irrevocably commits to discharge the RPMR registration within ten (10) business "
        "days of receiving full repayment of its Contribution, Interest and share of Net Sale Profit. "
        "Any failure to discharge within this period entitles Capital Norvex to proceed with the "
        "discharge at the Partner's sole expense."))
    story.append(sp())

    # ── 6 ──────────────────────────────────────────────────────────────────
    story += sec("6. EXCLUSIVE MANAGEMENT BY CAPITAL NORVEX — IN A SPIRIT OF GOOD FAITH")
    story += art("6.1", "Principle of Exclusive Management and Good Faith")
    story.append(bp(
        "Capital Norvex assumes exclusive management of the Loan Asset, including the operational "
        "relationship with the Borrower, legal documentation, site inspections and all credit "
        "decisions. This management is exercised <b>at all times in a spirit of good faith</b> and "
        "absolute transparency toward the Partner, in accordance with Articles 6 and 1375 of the "
        "<i>Civil Code of Quebec</i>. The Partner does not communicate directly with the Borrower "
        "or its representatives, but retains at all times its right to complete information and "
        "consultation for any material decision, as set out in Sections 6.3, 6.4 and 8.4."))
    story.append(sp())
    story += art("6.2", "Exclusive Powers of Capital Norvex")
    story.append(bp("Without limiting the foregoing, the following powers belong exclusively to Capital Norvex:"))
    story += blt([
        "Approve, decline or modify the terms and conditions of the Loan Asset",
        "Manage the amounts and schedule of each Disbursement",
        "Order site inspections, appraisals and expert assessments",
        "Declare a Default Event and exercise all available remedies",
        "Decide to proceed with Repossession or a court-supervised sale",
        "Appoint a Receiver or any other specialized mandatary",
        "Initiate and direct all judicial and notarial proceedings",
        "Negotiate and conclude any settlement or arrangement with the Borrower",
        "Replace the general contractor or any other site participant",
        "Directly or indirectly manage construction works in the event of Repossession",
    ])
    story.append(sp())
    story += art("6.3", "Automatic Monthly Reports to the Partner")
    story.append(bp(
        "Simultaneously with each monthly Disbursement authorization request, Capital Norvex "
        "automatically provides the Partner with a complete monthly report on the status of the Loan "
        "Asset, including: construction progress, the amount of the Disbursement requested, the "
        "cumulative disbursed balance, accrued capitalized Interest, and any material information "
        "that may affect the value of the Contribution. The Partner is thus fully informed at every "
        "stage of the financing. In the event of a Borrower Default Event, Capital Norvex notifies "
        "the Partner in writing within five (5) business days."))
    story.append(sp())
    story += art("6.4", "Partner Portal (PWA) — 24/7 Transparency on All the Partner's Loans")
    story.append(bp(
        "Capital Norvex provides the Partner with a <b>secure Partner Portal</b> (PWA — "
        "Progressive Web Application), accessible <b>24 hours a day, 7 days a week</b>, from "
        "any device (smartphone, tablet, computer). This portal constitutes a <b>contractual "
        "right</b> of the Partner and a commitment of absolute transparency by Capital Norvex. "
        "The Partner has real-time access to the following information for <b>all of its "
        "active Loan Assets</b>:"))
    story += blt([
        "Disbursed Contribution balance and accrued capitalized Interest in real time",
        "Complete history of all Disbursements made",
        "Inspection reports and construction progress updates",
        "Status of each pending Disbursement authorization request",
        "File documents: appraisals, permits, insurance, account statements, policies",
        "Automatic alerts for any material event affecting the file",
        "Direct communications and secure messaging with Capital Norvex",
    ])
    story.append(sp())
    story += art("6.5", "Norvex Track™ — Disbursement and Authorization Module 24/7")
    story.append(bp(
        "For construction and infrastructure loans, Capital Norvex also makes available to "
        "the Partner the <b>Norvex Track™</b> module, a proprietary technology tool that "
        "enables the Partner, <b>24 hours a day, 7 days a week</b>, to:"))
    story += blt([
        "<b>Receive</b> in real time each progressive Disbursement request together with inspection reports, progress certificates and partial lien waivers;",
        "<b>Review</b> online all supporting documents from any device;",
        "<b>Authorize</b> each Disbursement at the click of a button, in accordance with Section 7;",
        "<b>Execute</b> the Disbursement directly: it is the Partner who, upon its authorization, triggers the funds transfer — Capital Norvex makes no disbursement without this express authorization;",
        "<b>Track</b> in real time the status of each transaction, budget progress, completion schedule and any site alert.",
    ])
    story.append(bp(
        "The Partner's use of <b>Norvex Track™</b> constitutes an additional guarantee of "
        "its operational control over the funds: no amount leaves the separate account "
        "without its express authorization, given and executed by the Partner through the "
        "module."))
    story.append(sp())

    # ── 7 ──────────────────────────────────────────────────────────────────
    story += sec("7. DISBURSEMENT MECHANISM — PARTNER AUTHORIZATION AND CONTROL")
    story += art("7.0", "Principle — MONTHLY Disbursements Only and Close Monitoring")
    story.append(bp(
        "Progressive Disbursements to the Borrower are made on a <b>strictly monthly "
        "basis</b>, at a rate of one (1) Disbursement per calendar month maximum, based on "
        "actual construction progress. This monthly cadence is:"))
    story += blt([
        "<b>Regular and predictable</b>: one Disbursement per month, based on an independent professional inspection report and a Cost Report to Date (CRT) signed by the responsible architect or engineer;",
        "<b>Non-cumulative</b>: no multiple Disbursements within the same month, unless joint written agreement of the Parties for duly documented exceptional circumstances (e.g., inspection delay caused by force majeure);",
        "<b>Subject to close monitoring</b>: each Disbursement is preceded by a rigorous verification of construction progress, compliance with the approved budget, compliance with the schedule, insurance in force, valid permits and any other material condition;",
        "<b>Fully tracked</b>: each Disbursement is recorded in the Norvex Track™ module and accessible to the Partner in real time via the Partner Portal (PWA) 24/7.",
    ])
    story.append(bp(
        "Capital Norvex and the Partner acknowledge that this monthly cadence, rigorous "
        "and strictly framed, constitutes an <b>essential protection</b> for the value of "
        "the Partner's Contribution and the proper completion of the project. No exemption "
        "may be granted unilaterally by Capital Norvex."))
    story.append(sp())
    story += art("7.1", "First Disbursement — Mandatory Before the Notary")
    story.append(bp(
        "The first Disbursement of any Loan Asset is made, without exception, in the presence of a "
        "notary designated by Capital Norvex. This requirement is absolute and may not be waived by "
        "either party. The notary verifies all conditions precedent, proceeds with registration of "
        "the first-ranking real estate mortgage in favour of Capital Norvex, confirms the Partner's "
        "Movable Hypothec registration at the RPMR, and releases funds in accordance with Capital "
        "Norvex's written instructions. This procedure constitutes the Partner's primary legal protection."))
    story.append(sp())
    story += art("7.2", "Progressive Monthly Disbursements — Partner Authorization and Execution via Norvex Track™")
    story.append(bp(
        "For each subsequent monthly progressive Disbursement, Capital Norvex sends the Partner a "
        "Disbursement authorization request at least five (5) business days before the intended date. "
        "This request must include:"))
    story += blt([
        "Exact amount of the Disbursement requested and the cumulative disbursed balance",
        "Independent inspection report certifying construction progress",
        "Certified Cost Report to Date (CRT) signed by architect or responsible engineer",
        "Confirmation of compliance with approved budget and schedule",
        "Partial lien waivers from relevant subcontractors",
        "Any additional element Capital Norvex deems relevant",
    ])
    story.append(sp())
    story += art("7.3", "Obligation to Authorize — Performing Loan Asset")
    story.append(bp(
        "When the Loan Asset is in good standing — meaning no Borrower Default Event exists, the "
        "approved budget and schedule are being respected, and professional reports are satisfactory "
        "— the Partner agrees, acting in good faith, to authorize the Disbursement within seventy-two "
        "(72) hours of receiving Capital Norvex's request. Failing a written response from the Partner "
        "within this period, <b>a presumption of approval applies</b> and Capital Norvex may proceed "
        "with the Disbursement, subject to the Partner's right to raise in writing, within twenty-four "
        "(24) hours thereafter, any serious objection based on one of the grounds set out below. "
        "The Partner may legitimately withhold or suspend authorization in the following circumstances:"))
    story += blt([
        "Documented existence of a Borrower Default Event not disclosed by Capital Norvex",
        "Manifest budget overrun without written authorization from Capital Norvex",
        "Proven and documented fraud or material misrepresentation attributable to Capital Norvex",
    ])
    story.append(sp())
    story += art("7.4", "Separate Account per Loan Asset")
    story.append(bp(
        "All Contribution funds are held in a separate, identified bank account designated exclusively "
        "to the Loan Asset set out in Schedule A. No withdrawal, transfer or set-off is permitted "
        "except as provided in this Agreement. Capital Norvex maintains separate accounting per Loan "
        "Asset and makes it available to the Partner upon written request."))
    story.append(sp())

    # ── 8 ──────────────────────────────────────────────────────────────────
    story += sec("8. BORROWER DEFAULT — JOINT MANAGEMENT IN PARTNERSHIP")
    story += art("8.1", "Capital Norvex Does Not Assume the Borrower's Unpaid Monthly Payments")
    story.append(bp(
        "In the event of a Borrower Default Event, including non-payment of interest or failure to "
        "comply with Loan Asset conditions, <b>Capital Norvex assumes no substitution obligation and "
        "does not make payments on behalf of the defaulting Borrower.</b> Capital Norvex is neither "
        "a guarantor nor surety for the Borrower's obligations to the Partner. The Partner's "
        "Contribution is a partnership engagement carrying risk, protected by the Movable Hypothec and the "
        "first-ranking real estate mortgage held by Capital Norvex."))
    story.append(sp())
    story += art("8.2", "Capitalization of Unpaid Interest")
    story.append(bp(
        "Interest owed to the Partner that is not collected due to Borrower default is "
        "<b>automatically capitalized</b> and added to the balance owed to the Partner. Such "
        "capitalized Interest itself accrues interest at the contractual rate. All capitalized "
        "Interest is repaid to the Partner from Sale Proceeds upon Repossession, as a priority "
        "and before any Net Sale Profit sharing."))
    story.append(sp())
    story += art("8.3", "Borrower's Default Does Not Constitute Capital Norvex's Default")
    story.append(bp(
        "The Parties expressly acknowledge that a Borrower Default Event <b>does not in any way "
        "constitute a Default Event of Capital Norvex</b> toward the Partner. Capital Norvex remains "
        "fully committed to managing the file diligently and in good faith, and to carrying through "
        "the protection process for the Parties' joint interests until full recovery of amounts owed."))
    story.append(sp())
    story += art("8.4", "Joint Management and Strategic Decisions in Partnership")
    story.append(bp(
        "Upon a Borrower Default Event, Capital Norvex and the Partner <b>work in active "
        "partnership</b> to determine the best protection and recovery strategy. Capital Norvex "
        "assumes day-to-day operational management, but major strategic decisions are taken "
        "<b>jointly</b> by both Parties, according to the following process:"))
    story += num_list([
        ("1.", "<b>Immediate Notice and Consultation:</b> Within five (5) business days of identifying the default, Capital Norvex simultaneously notifies the Borrower and the Partner in writing, and convenes the Partner to a consultation meeting (in person or by videoconference) within the following seven (7) days to jointly agree on the intervention strategy."),
        ("2.", "<b>60-Day Notice to Borrower:</b> Capital Norvex issues a formal default notice to the Borrower granting sixty (60) days to remedy, pursuant to Articles 2757 et seq. of the <i>Civil Code of Quebec</i>. During this period, Capital Norvex keeps the Partner fully informed in real time via the PWA portal and direct communication."),
        ("3.", "<b>Joint Decision at Expiry of 60 Days:</b> Failing remediation, Capital Norvex and the Partner take <b>jointly</b> the decision on the next step: (a) <b>taking in payment</b> by Capital Norvex (with appropriate compensation to the Partner); (b) <b>court-supervised sale</b>; (c) any other lawful solution. Failing agreement between the Parties within fifteen (15) days, the mediation procedure under Section 14.5 applies."),
        ("4.", "<b>Selection of Real Estate Broker:</b> If sale is the chosen option, the selection of the real estate broker (and its firm) is made <b>jointly</b> by Capital Norvex and the Partner, based on competence, network, marketing plan and proposed fees. The listing mandate is signed jointly."),
        ("5.", "<b>Construction Site Management:</b> If the Loan Asset is in the construction phase at the time of default, Capital Norvex assumes technical site management (contractors, subcontractors, inspections), consulting the Partner on any material financial decision (>5% of remaining budget)."),
        ("6.", "<b>Distribution of Sale Proceeds:</b> Capital Norvex distributes Sale Proceeds according to the priority order in Section 4.4, in full transparency with the Partner."),
    ])
    story.append(sp())
    story += art("8.5", "Legal Fees of Repossession — Borne by Capital Norvex")
    story.append(bp(
        "All legal fees, lawyers' fees, notary fees, Receiver fees and other costs incurred by "
        "Capital Norvex in Repossession proceedings are collected as first priority from Sale "
        "Proceeds. The Partner bears no additional costs beyond its initial Contribution. Capital "
        "Norvex assumes responsibility for conducting these proceedings diligently and competently."))
    story.append(sp())

    # ── 9 ──────────────────────────────────────────────────────────────────
    story += sec("9. PARTNER'S COMMITMENT FOR THE TERM OF THE LOAN ASSET")
    story += art("9.1", "Firm Commitment Until the End of the Loan Asset")
    story.append(bp(
        "The Partner commits to maintain its Contribution in place for the full term of the Loan "
        "Asset, until the Borrower has repaid in full all principal, interest, fees and ancillary "
        "amounts — or until Sale Proceeds have been fully distributed in the event of Repossession. "
        "Once the file is brought to term, the Partner is free not to renew its partnership and may recover its "
        "full Contribution with all Interest owed. No early total or partial withdrawal is permitted "
        "during the term of the Loan Asset, except as expressly provided in Section 9.3 below."))
    story.append(sp())
    story += art("9.2", "Assignment and Encumbrance — Reasonable Consent")
    story.append(bp(
        "The Partner may assign, transfer, pledge or otherwise encumber its rights under this "
        "Agreement with the prior written consent of Capital Norvex, which consent <b>shall not be "
        "unreasonably withheld</b>. Capital Norvex shall examine any assignment or pledge request "
        "in good faith and within a reasonable timeframe, taking into account the solvency and "
        "legitimacy of the proposed assignee or pledgee."))
    story.append(sp())
    story += art("9.3", "Exceptions — Authorized Early Exit")
    story.append(bp("An early exit by the Partner is permitted only in the following circumstances:"))
    story += blt([
        "Capital Norvex expressly agrees in writing and makes necessary arrangements to fully replace the Contribution with another other partner or its own funds, without interrupting the Loan Asset financing;",
        "Capital Norvex decides to repay the Partner and replace it, pursuant to Section 9.4;",
        "<b>Material Breach by Capital Norvex</b> of its obligations under this Agreement, not remedied within thirty (30) days of a written notice from the Partner (e.g., documented fraud, persistent failure of transparency, material breach of good faith commitments).",
    ])
    story.append(sp())
    story += art("9.4", "Capital Norvex's Right to Replace the Partner — Framework")
    story.append(bp(
        "Capital Norvex may, in case of a serious and objective reason (notably strategic "
        "reorganization, institutional refinancing, or legitimate interest of the Loan Asset), "
        "replace the Partner with another other partner or its own funds, subject to the following "
        "cumulative conditions:"))
    story += blt([
        "Minimum written notice of <b>thirty (30) days</b> to the Partner, setting out the reasons for replacement;",
        "Remittance to the Partner, in a single payment: (i) the full Contribution; (ii) all capitalized Interest accrued to the repayment date;",
        "<b>No penalty or retention</b> may be imposed on the Partner under this replacement;",
        "The Partner shall discharge the Movable Hypothec within ten (10) business days of full receipt of amounts owed.",
    ])
    story.append(bp(
        "This full repayment releases both parties from all mutual obligations relating to the "
        "concerned Loan Asset."))
    story.append(sp())
    story += art("9.5", "Consequences of Non-Compliant Withdrawal — No Financial Penalty")
    story.append(bp(
        "Should the Partner proceed with a withdrawal not in compliance with Sections 9.1 through 9.4, "
        "<b>no financial penalty</b> shall be imposed on it. However, the Parties acknowledge that "
        "financing stability is essential to the proper conduct of the Loan Asset. In such case:"))
    story += blt([
        "The Parties commit to meet in good faith as soon as possible to find a joint solution allowing financing continuity;",
        "Capital Norvex may, at its discretion, replace the Contribution with another other partner or its own funds, without interruption for the Borrower;",
        "Failing an amicable solution, the dispute shall be submitted to the mediation procedure provided for in Section 14.5;",
        "Judicial recourse remains available as a last resort, but is limited to the reparation of actual and documented prejudice suffered by Capital Norvex (excluding any contractual lump-sum penalty).",
    ])
    story.append(sp())

    # ── 10 ──────────────────────────────────────────────────────────────────
    story += sec("10. PARTNER DEFAULT EVENTS — RECIPROCITY AND GOOD FAITH")
    story.append(sp(4))
    story.append(bp(
        "The following constitute Partner Default Events, including:"))
    story.append(sp(4))
    story.append(bp("<b>Financial:</b>"))
    story += blt([
        "Failure to advance Contribution within agreed timeframe in Schedule A, despite a fifteen (15) days written notice",
        "Insolvency, bankruptcy or filing for creditor protection by Partner",
        "Proposal or arrangement with Partner's creditors affecting its ability to honour its commitments",
    ])
    story.append(sp(4))
    story.append(bp("<b>Contractual:</b>"))
    story += blt([
        "Unjustified and bad-faith refusal to authorize Disbursement within timeframe set out in Section 7.3",
        "Assignment or pledge made without having previously sought Capital Norvex's consent under Section 9.2",
        "Material breach not remedied within twenty (20) days of written notice",
        "Substantial false representation that misled Capital Norvex",
    ])
    story.append(sp(4))
    story.append(bp("<b>Legal:</b>"))
    story += blt([
        "Seizure of the Contribution by a third-party creditor, not lifted within thirty (30) days",
        "<b>Subject to Section 10.1 below</b> — Judicial proceedings initiated directly by the Partner against the Borrower without first notifying Capital Norvex and attempting the mediation provided for in Section 14.5",
    ])
    story.append(sp(4))
    story += art("10.1", "Partner's Right to Protect Its Rights in Case of Material Breach by Capital Norvex")
    story.append(bp(
        "Notwithstanding the foregoing, the Partner retains at all times the right to protect its "
        "hypothecary and contractual rights through any appropriate legal action if Capital Norvex "
        "commits a <b>material breach</b> of its obligations (notably: fraud, misappropriation of "
        "funds, persistent failure of transparency, refusal to honour the good-faith commitments set "
        "out in Sections 6, 8 and 14). The Partner shall in such case notify Capital Norvex in "
        "writing and grant a thirty (30) day cure period, save in case of manifest urgency endangering "
        "the Contribution."))
    story.append(sp(4))
    story += art("10.2", "Capital Norvex's Remedies — Good Faith and Proportionality")
    story.append(bp(
        "Upon a Partner Default Event, Capital Norvex may, after having complied with the mediation "
        "procedure under Section 14.5 (save in case of urgency): claim amounts actually owed, demand "
        "reparation of actual and documented prejudice, and exercise any remedy available at law. "
        "<b>No lump-sum contractual penalty</b> applies; only actual prejudice suffered may be "
        "subject to a claim for reparation."))
    story.append(sp())

    # ── 11 ──────────────────────────────────────────────────────────────────
    story += sec("11. REPRESENTATIONS AND WARRANTIES OF THE PARTIES")
    story += art("11.1", "Partner's Representations")
    story.append(bp(
        "The Partner represents and warrants to Capital Norvex that, as of the date of signing and "
        "at each Disbursement date:"))
    story += blt([
        "It is duly incorporated, authorized and in good standing under applicable laws",
        "It has full legal and financial capacity to enter into this Agreement",
        "The Contribution comes from lawful, declared funds compliant with applicable regulatory requirements, including anti-money laundering rules",
        "There is no litigation, claim or encumbrance that could affect its rights hereunder",
        "Signing this Agreement does not contravene any prior commitment or obligation",
        "It has obtained all necessary legal and tax advice before signing",
    ])
    story.append(sp())
    story += art("11.2", "Capital Norvex's Representations")
    story.append(bp(
        "Capital Norvex represents and warrants to the Partner that, as of the date of signing:"))
    story += blt([
        "It is duly incorporated and authorized to carry on business in Quebec and Ontario",
        "The Loan Asset has been analyzed and approved in accordance with its internal credit policies",
        "The applicable Norvex Score™ has been calculated in good faith",
        "It will manage the Loan Asset with diligence, competence and professionalism",
    ])
    story.append(sp())

    # ── 12 ──────────────────────────────────────────────────────────────────
    story += sec("12. CONFIDENTIALITY")
    story.append(sp(4))
    story.append(bp(
        "Each party undertakes to treat as strictly confidential all information received from the "
        "other party in connection with this Agreement, including information about Borrowers, Loan "
        "Assets, financial terms, internal policies and Capital Norvex's proprietary systems "
        "(including Norvex Score™). This confidentiality obligation survives termination or expiry "
        "of this Agreement for a period of five (5) years. No information may be disclosed to any "
        "third party without the prior written consent of the other party, except as required by "
        "law, court order or a competent regulatory authority."))
    story.append(sp())

    # ── 13 ──────────────────────────────────────────────────────────────────
    story += sec("13. TERM AND TERMINATION")
    story.append(sp(4))
    story.append(bp(
        "This Agreement comes into force upon signature by both parties and remains in force until "
        "full repayment of the Loan Asset or, in the event of Repossession, until Sale Proceeds have "
        "been fully distributed. It may not be terminated early except as expressly provided herein "
        "or by mutual written agreement. Termination or expiry does not affect rights and obligations "
        "that, by their nature, survive the end of the agreement, including confidentiality, "
        "accounting obligations and Movable Hypothec discharge obligations."))
    story.append(sp())

    # ── 14 ──────────────────────────────────────────────────────────────────
    story += sec("14. GENERAL PROVISIONS")
    story += art("14.1", "Governing Law and Jurisdiction")
    story.append(bp(
        "This Agreement is governed by and shall be interpreted in accordance with the <b>laws of "
        "the Province of Quebec and the federal laws of Canada applicable therein</b>. Any dispute "
        "arising out of or in connection with this Agreement falls under the exclusive jurisdiction "
        "of the courts of the judicial district of Montreal, subject to Sections 14.5 (Mediation) "
        "and 14.6 (Good Faith)."))
    story.append(sp())
    story += art("14.2", "Amendments, Notices and Assignment")
    story += blt([
        "<b>Amendments:</b> Any modification must be in writing and signed by both Parties.",
        "<b>Notices:</b> Any notice shall be given in writing, by email with acknowledgment of receipt or by registered mail, at the addresses set out in Schedule A.",
        "<b>Assignment:</b> Pursuant to Section 9.2, assignment of the Partner's rights is permitted with prior written consent of Capital Norvex, which consent shall not be unreasonably withheld.",
    ])
    story.append(sp())
    story += art("14.3", "Severability, Entire Agreement and Waiver")
    story += blt([
        "<b>Severability:</b> Any clause declared invalid or unenforceable does not affect the validity of the remainder of this Agreement.",
        "<b>Entire Agreement:</b> This Agreement, together with its Schedules and the Movable Hypothec attached thereto, constitutes the entire agreement between the Parties relating to the relevant Loan Asset.",
        "<b>Waiver:</b> No tolerance or delay in exercising a right constitutes a permanent waiver of that right.",
    ])
    story.append(sp())
    story += art("14.4", "Language and Interpretation")
    story.append(bp(
        "This Agreement is also available in French. <b>In case of divergence, the French version "
        "prevails in Quebec.</b> The Parties acknowledge having negotiated this Agreement in French "
        "and having expressly waived the application of Article 1432 of the <i>Civil Code of Quebec</i> "
        "regarding interpretation against the drafter, it being understood that the Agreement was "
        "drafted in the mutual interest of the Parties."))
    story.append(sp())
    story += art("14.5", "Mandatory Mediation Before Any Judicial Recourse")
    story.append(bp(
        "The Parties commit to <b>attempting to resolve amicably, by mediation</b>, any dispute, "
        "disagreement or divergent interpretation arising out of this Agreement <b>before initiating "
        "any judicial proceeding</b>. The mediation procedure is as follows:"))
    story += num_list([
        ("1.", "The Party wishing to raise a dispute sends a written notice to the other Party describing the nature of the dispute and the proposed solution."),
        ("2.", "The Parties have fifteen (15) days to attempt to resolve the dispute through direct, good-faith discussion."),
        ("3.", "Failing resolution, the Parties jointly designate an independent and qualified mediator within ten (10) days. Failing agreement on the mediator, each Party designates one and the two mediators designate a third who shall act alone."),
        ("4.", "The Parties participate in good faith in at least one (1) mediation session, the costs of which are shared equally."),
        ("5.", "Failing settlement within sixty (60) days following the mediator's appointment, either Party may initiate judicial recourse."),
        ("6.", "<b>Exception — Urgent Measures:</b> This mediation obligation does not apply to conservatory measures or urgent injunctions necessary to preserve a Party's hypothecary rights or prevent irreparable harm."),
    ])
    story.append(sp())
    story += art("14.6", "Good Faith and Collaboration")
    story.append(bp(
        "The Parties commit to perform this Agreement <b>in good faith</b>, in accordance with "
        "Articles 6, 7 and 1375 of the <i>Civil Code of Quebec</i>, in a spirit of collaboration, "
        "transparency and mutual respect. No Party may invoke a breach by the other without first "
        "having attempted to resolve the situation in good faith through direct communication and, "
        "as the case may be, through the mediation procedure under Section 14.5."))
    story.append(sp())
    story += art("14.7", "Indissociability with the Movable Hypothec")
    story.append(bp(
        "This Partnership Agreement and the Movable Hypothec on Individual Claim granted by Capital "
        "Norvex in favour of the Partner in connection with this Loan Asset form <b>an indissociable "
        "contractual whole</b>. The two documents shall be read, interpreted and performed jointly "
        "and in a complementary manner. Any breach of the terms of this Agreement automatically "
        "constitutes a Default Event under the Movable Hypothec, and vice versa. In the event of "
        "any divergence or ambiguity between the two documents, the interpretation most protective "
        "of the Partner (as hypothecary creditor) shall prevail."))
    story.append(sp())

    # ── 15 SIGNATURES ───────────────────────────────────────────────────────
    story += sec("15. SIGNATURES")
    story.append(sp(4))
    story.append(bp(
        "IN WITNESS WHEREOF, the parties have signed this Partnership Agreement on the date "
        "indicated below, having read it in full and obtained such legal and tax advice as they "
        "deemed appropriate. The parties acknowledge that this Agreement constitutes a firm and "
        "legally binding commitment."))
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
        ["File Name / Borrower",                  "___________________________________________"],
        ["Property / Project Address",            "___________________________________________"],
        ["Type of Financing",                     "Commercial Construction / Infrastructure"],
        ["Total Loan Amount",                     "$_________________________________________ CAD"],
        ["Partner Contribution",                  "$_________________________________________ CAD"],
        ["CN File Fees (3% to 3.5%)",             "$_________________________________________ CAD — Capital Norvex"],
        ["Annual Interest Rate to Partner",       "_____ % (calculated daily, compounded monthly)"],
        ["Norvex Score™",                         "_____ / 100"],
        ["Loan Term",                             "_____ months"],
        ["Interest Payment Structure",            "Capitalized — repaid in full at maturity"],
        ["Date of First Disbursement (Notary)",   "_______________"],
        ["Expected Maturity Date",                "_______________"],
        ["Real Estate Mortgage Ranking (Borrower)", "1st ranking — Capital Norvex Inc."],
        ["Movable Hypothec RPMR (Partner)",       "In favour of Partner on the Loan Asset"],
        ["Designated Notary",                     "___________________________________________"],
        ["Profit Sharing on Repossession Sale",   "50% Capital Norvex / 50% Partner (if net profit)"],
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
    print(f"✅  Partnership_Agreement_Construction_CapitalNorvex.pdf generated.")


if __name__ == "__main__":
    main()
