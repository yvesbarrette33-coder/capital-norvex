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

EMBLEM_PATH   = r'/Users/yvesbarrette/Desktop/capitalnorvex-site/CapitalNorvex_Scripts/logos/emblem_header.png'
COVER_PATH    = r'/Users/yvesbarrette/Desktop/capitalnorvex-site/CapitalNorvex_Scripts/logos/logo_cover.png'
COVER_SM_PATH = r'/Users/yvesbarrette/Desktop/capitalnorvex-site/CapitalNorvex_Scripts/logos/logo_cover_sm.png'

# ── Custom Flowable: gold line ────────────────────────────────────────────────
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

# ── Header / Footer with logo ─────────────────────────────────────────────────
def make_on_page(product_tag):
    def on_page(canvas, doc):
        canvas.saveState()
        w, h = letter

        # Dark header band
        canvas.setFillColor(DARK)
        canvas.rect(0, h-54, w, 54, fill=1, stroke=0)
        # Gold line below header
        canvas.setFillColor(GOLD)
        canvas.rect(0, h-57, w, 3, fill=1, stroke=0)

        # ── Emblem logo (M+diamond) in header ──
        emb_w, emb_h = 38, 42
        logo_x = MARGIN
        logo_y = h - 47  # uniformisé : top du logo à 5 px du sommet de la page
        canvas.drawImage(EMBLEM_PATH, logo_x, logo_y,
                         width=emb_w, height=emb_h,
                         preserveAspectRatio=True, mask='auto')

        # "CAPITAL NORVEX" text to the right of the emblem
        text_x = logo_x + emb_w + 8
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawString(text_x, h - 30, "CAPITAL NORVEX")
        canvas.setFillColor(GOLD)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(text_x, h - 43, "Institutional Private Lending  |  Quebec & Ontario")

        # Product tag (right side)
        canvas.setFillColor(GOLD)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.drawRightString(w - MARGIN, h - 28, "COMMITMENT LETTER")
        canvas.setFillColor(GREY_LT)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawRightString(w - MARGIN, h - 42, product_tag)

        # Page number
        canvas.setFillColor(GREY_LT)
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(w - MARGIN, h - 52, f"p. {doc.page}")

        # ── Footer (2 lines: brand + address) ──
        canvas.setFillColor(DARK)
        canvas.rect(0, 0, w, 50, fill=1, stroke=0)
        canvas.setFillColor(GOLD)
        canvas.rect(0, 50, w, 1.5, fill=1, stroke=0)
        # Top line — confidentiality centered (gold)
        canvas.setFillColor(GOLD)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.drawCentredString(w/2, 32,
            "CAPITAL NORVEX  ·  Confidential document — Validity as per terms stated")
        # Page number on the right (top line)
        canvas.setFillColor(GREY_LT)
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(w - MARGIN, 32, f"Page {doc.page}")
        # Bottom line — full address centered (light grey)
        canvas.setFillColor(GREY_LT)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(w/2, 14,
            "2705-1000 André-Prévost  ·  Île-des-Sœurs (Verdun)  ·  Montréal, QC H3E 0G2   |   1-(438)-533-PRET (7738)   |   info@capitalnorvex.com   |   capitalnorvex.com")

        canvas.restoreState()
    return on_page

# ── Styles ────────────────────────────────────────────────────────────────────
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

# ── Helpers ───────────────────────────────────────────────────────────────────
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

# ── COVER PAGE with logo ──────────────────────────────────────────────────────
def build_cover(story, product_name, product_desc):
    story.append(Spacer(1, 0.5*inch))

    # Centred logo on cover page
    img = RLImage(COVER_PATH, width=120, height=130)
    img.hAlign = "CENTER"
    story.append(img)
    story.append(Spacer(1, 14))

    # Title band
    tbl = Table([[Paragraph("COMMITMENT LETTER", ST["title"])]],
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

    # Info table
    info = [
        ["FILE NO.",    "___________________________"],
        ["BORROWER",    "___________________________"],
        ["PROJECT",     "___________________________"],
        ["AMOUNT",      "___________________________"],
        ["ISSUE DATE",  "___________________________"],
        ["VALIDITY",    "30 days from date of issuance"],
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
        "Structured Capital.  Controlled Ambition.",
        ParagraphStyle("slogan", fontName="Helvetica-Oblique", fontSize=10,
                       textColor=GOLD2, alignment=TA_CENTER, spaceAfter=8)))

    story.append(Paragraph(
        "CONFIDENTIAL — This document is a conditional financing offer.",
        ST["note"]))
    story.append(Paragraph(
        "The French version shall prevail in Quebec / La version française prévaut au Québec",
        ParagraphStyle("lang_note", fontName="Helvetica-Oblique", fontSize=7,
                       textColor=GREY_MED, alignment=TA_CENTER, spaceAfter=4)))
    story.append(PageBreak())


# ══════════════════════════════════════════════════════════════════════════════
# CONTENT OF THE 3 COMMITMENT LETTERS
# ══════════════════════════════════════════════════════════════════════════════

def build_construction_en(story):
    story += section_bar("1.  IDENTIFICATION OF PARTIES")
    story += two_col_fields([
        ("Lender:", "Capital Norvex Inc."),
        ("Representative:", "_______________________________"),
        ("Borrower (legal name):", "_______________________________"),
        ("Business No. (BN):", "_______________________________"),
        ("Borrower Address:", "_______________________________"),
        ("Guarantor(s):", "_______________________________"),
    ])
    story += section_bar("2.  PROJECT DESCRIPTION")
    story += two_col_fields([
        ("Project Address:", "_______________________________"),
        ("Municipality / RCM:", "_______________________________"),
        ("Development Type:", "e.g.: Condos, plex, commercial..."),
        ("Number of Units:", "_______________________________"),
        ("Total Area:", "_______________________________"),
        ("Applicable Zoning:", "_______________________________"),
        ("General Contractor:", "_______________________________"),
        ("Architect / Engineer:", "_______________________________"),
        ("Expected Start Date:", "_______________________________"),
        ("Construction Duration:", "_______  months"),
    ])
    story += section_bar("3.  FINANCIAL TERMS")
    story.append(cond_table([
        ["Parameter", "Value", "Notes"],
        ["Maximum Authorized Amount", "$  _____________________ CAD", "Subject to conditions"],
        ["Initial Term", "_______ months", "Extension at Lender's discretion"],
        ["Annual Interest Rate", "_____ % (fixed)", "Calculated daily"],
        ["Origination Fee", "3% to 3.5% of amount", "Payable at first advance"],
        ["Renewal Fee", "_____ %", "If applicable"],
        ["Analysis Fee (term extension)", "1% of principal", "If extension beyond Maturity Date (renegotiable)"],
        ["Prepayment Penalty", "Min. 3 months interest", "At any time"],
        ["Target Maximum LTV", "_____ %", "On approved value — flexibility with collateral"],
        ["Target Maximum LTC", "_____ %", "On total approved cost — flexibility with collateral"],
        ["Construction Holdback", "5% per disbursement", "Released 35 days after substantial completion"],
    ], [2.5*inch, 2.0*inch, 1.5*inch]))
    story.append(Spacer(1,6))
    story += section_bar("4.  DISBURSEMENT TERMS")
    story.append(body("Funds will be advanced progressively on a monthly basis based on construction progress, validated by an inspector mandated by Capital Norvex. Each draw request must include:"))
    for t in ["Approved independent inspection report",
              "Certified cost-to-date statement (CCC)",
              "Partial and final lien waivers from subcontractors",
              "Professional certificate from architect or engineer"]:
        story.append(bullet(t))
    story += section_bar("5.  REQUIRED SECURITY")
    story.append(cond_table([
        ["Security", "Rank / Details"],
        ["Real estate mortgage", "1st rank on property and improvements"],
        ["Assignment of leases", "Total and immediate"],
        ["Personal guarantee", "Joint, irrevocable and unlimited"],
        ["All-risk construction insurance", "Amount = project value + 10%"],
        ["Civil liability insurance", "Minimum $5,000,000"],
    ], [2.8*inch, 3.2*inch]))
    story.append(Spacer(1,6))
    story += section_bar("6.  CONDITIONS PRECEDENT TO FIRST DISBURSEMENT")
    for t in ["Constitutional documents and resolutions authorizing the loan",
              "Proof of injected equity contribution",
              "Detailed final budget and approved construction schedule",
              "Plans and specifications signed and sealed by professionals",
              "General contractor agreement approved by Capital Norvex",
              "Valid and current building permits",
              "Approved independent appraisal report",
              "Phase I environmental report (Phase II if required)",
              "Registration of first-rank mortgage",
              "Complete legal opinion accepted by Capital Norvex"]:
        story.append(bullet(t))
    story.append(Spacer(1,4))
    story += section_bar("7.  ZERO TOLERANCE — TAXES AND LEGAL HYPOTHECS")
    story.append(body("The Borrower undertakes to settle or have any legal hypothec of construction (art. 2724 and 2726 C.C.Q.) discharged immediately, and at the latest within seven (7) days of notice from the Lender. Any delay in payment of property taxes, school taxes, municipal charges, insurance premiums or other current obligations must be remedied within seven (7) days of notice from the Lender. Failing this, an Event of Default shall be automatically declared."))

    story += section_bar("8.  REPRESENTATION OF CAPITAL NORVEX INC.")
    story.append(body("For Capital Norvex Inc., the loan agreement and the mortgage deed shall be signed by a designated representative, duly authorized pursuant to a corporate resolution adopted by the sole shareholder and president, Mrs. Suzanne Breton, a certified true copy of which shall be attached to the file."))

    story += section_bar("9.  INDISSOCIABILITY — LOAN AGREEMENT AND MORTGAGE DEED")
    story.append(body("The loan agreement and the mortgage deed entered into between the Parties form an INDISSOCIABLE contractual whole. Any breach of the terms of the loan agreement automatically constitutes an Event of Default within the meaning of the mortgage deed, and vice versa. In the event of any divergence or ambiguity, the interpretation most favourable to the Lender shall prevail."))

    story += section_bar("10.  VALIDITY AND GENERAL CONDITIONS")
    story += alert_box("This commitment letter is valid for a period of 30 days following the date of issuance. Capital Norvex reserves the right to revise the conditions or withdraw the offer without notice beyond this period.")
    for t in ["Does not constitute an irrevocable commitment prior to the signing of the loan agreement.",
              "Capital Norvex may require any additional document, security or information.",
              "Any modification must be confirmed in writing by Capital Norvex.",
              "LTV/LTC ratios are targets, adjustable on a case-by-case basis with acceptable collateral (up to 95% LTV)."]:
        story.append(bullet(t))


def build_land_en(story):
    story += section_bar("1.  IDENTIFICATION OF PARTIES")
    story += two_col_fields([
        ("Lender:", "Capital Norvex Inc."),
        ("Representative:", "_______________________________"),
        ("Borrower (legal name):", "_______________________________"),
        ("Business No. (BN):", "_______________________________"),
        ("Borrower Address:", "_______________________________"),
        ("Guarantor(s):", "_______________________________"),
    ])
    story += section_bar("2.  LAND DESCRIPTION")
    story += two_col_fields([
        ("Address / Location:", "_______________________________"),
        ("Municipality / RCM:", "_______________________________"),
        ("Area:", "_______________________________"),
        ("Current Zoning:", "_______________________________"),
        ("Cadastral Lot Number:", "_______________________________"),
        ("Intended Use:", "_______________________________"),
        ("Independent Appraisal Value:", "$  ______________________ CAD"),
        ("Acquisition Price / Market Value:", "$  ______________________ CAD"),
        ("Land Status:", "_______________________________"),
        ("Intended Exit Strategy:", "_______________________________"),
    ])
    story += section_bar("3.  FINANCIAL TERMS")
    story.append(cond_table([
        ["Parameter", "Value", "Notes"],
        ["Maximum Authorized Amount", "$  _____________________ CAD", "Subject to conditions"],
        ["Initial Term", "_______ months", "Extension at Lender's discretion"],
        ["Annual Interest Rate", "_____ % (fixed)", "Calculated monthly"],
        ["Origination Fee", "3% to 3.5% of amount", "Payable at signing"],
        ["Analysis Fee (term extension)", "1% of principal", "If extension beyond Maturity (renegotiable)"],
        ["Prepayment Penalty", "Min. 3 months interest", "At any time"],
        ["Target Maximum LTV (on land value)", "_____ %", "Flexibility with collateral"],
        ["Target Minimum Down Payment", "_____ %", "Verified equity funds"],
    ], [2.5*inch, 2.0*inch, 1.5*inch]))
    story.append(Spacer(1,4))
    story += section_bar("4.  REQUIRED SECURITY")
    story.append(cond_table([
        ["Security", "Rank / Details"],
        ["Real estate mortgage on land", "Exclusive 1st rank"],
        ["Personal guarantee", "Joint, irrevocable and unlimited"],
        ["Assignment of any purchase agreement", "In favour of Capital Norvex"],
        ["Phase I Environmental Report", "Required prior to any disbursement"],
    ], [2.8*inch, 3.2*inch]))
    story.append(Spacer(1,6))
    story += section_bar("5.  EXIT STRATEGY")
    story.append(body("The Borrower must demonstrate a credible repayment plan:"))
    for t in ["Construction with transition to a construction loan",
              "Sale of land to an identified developer",
              "Refinancing with financial institution",
              "Other strategy approved by Capital Norvex"]:
        story.append(bullet(t))
    story.append(Spacer(1,4))
    story += section_bar("6.  CONDITIONS PRECEDENT TO DISBURSEMENT")
    for t in ["Constitutional documents and resolutions authorizing the loan",
              "Approved independent appraisal report accepted by Capital Norvex",
              "Phase I environmental report (Phase II if required)",
              "Proof of injected equity contribution",
              "Zoning confirmation from municipality",
              "Registration of first-rank mortgage",
              "Signed personal guarantees",
              "Complete legal opinion accepted by Capital Norvex"]:
        story.append(bullet(t))
    story.append(Spacer(1,4))
    story += section_bar("7.  ZERO TOLERANCE — TAXES AND CHARGES")
    story.append(body("The Borrower undertakes to pay punctually all property taxes, school taxes, municipal charges, insurance premiums and other current obligations affecting the Land. Any delay must be remedied within seven (7) days of notice from the Lender. Failing this, an Event of Default shall be automatically declared."))

    story += section_bar("8.  REPRESENTATION OF CAPITAL NORVEX INC.")
    story.append(body("For Capital Norvex Inc., the loan agreement and the mortgage deed shall be signed by a designated representative, duly authorized pursuant to a corporate resolution adopted by the sole shareholder and president, Mrs. Suzanne Breton, a certified true copy of which shall be attached to the file."))

    story += section_bar("9.  INDISSOCIABILITY — LOAN AGREEMENT AND MORTGAGE DEED")
    story.append(body("The loan agreement and the mortgage deed entered into between the Parties form an INDISSOCIABLE contractual whole. Any breach of the terms of the loan agreement automatically constitutes an Event of Default within the meaning of the mortgage deed, and vice versa. In the event of any divergence or ambiguity, the interpretation most favourable to the Lender shall prevail."))

    story += section_bar("10.  VALIDITY AND GENERAL CONDITIONS")
    story += alert_box("This commitment letter is valid for a period of 30 days following the date of issuance. Capital Norvex reserves the right to revise the conditions or withdraw the offer without notice beyond this period.")
    for t in ["Does not constitute an irrevocable commitment prior to the signing of the loan agreement.",
              "Land financing is granted exclusively for commercial purposes.",
              "Any modification must be confirmed in writing by Capital Norvex.",
              "LTV ratios are targets, adjustable on a case-by-case basis with acceptable collateral."]:
        story.append(bullet(t))


def build_acquisition_en(story):
    story += section_bar("1.  IDENTIFICATION OF PARTIES")
    story += two_col_fields([
        ("Lender:", "Capital Norvex Inc."),
        ("Representative:", "_______________________________"),
        ("Borrower (legal name):", "_______________________________"),
        ("Business No. (BN):", "_______________________________"),
        ("Borrower Address:", "_______________________________"),
        ("Guarantor(s):", "_______________________________"),
    ])
    story += section_bar("2.  PROPERTY DESCRIPTION")
    story += two_col_fields([
        ("Property Address:", "_______________________________"),
        ("Municipality / RCM:", "_______________________________"),
        ("Property Type:", "_______________________________"),
        ("Year Built:", "_______________________________"),
        ("Number of Units / Premises:", "_______________________________"),
        ("Current Occupancy Rate:", "_____ %"),
        ("Annual Gross Revenue:", "$  ______________________ CAD"),
        ("Purchase Price / Market Value:", "$  ______________________ CAD"),
        ("Independent Appraisal Value:", "$  ______________________ CAD"),
        ("Planned Down Payment:", "$  ______________________ CAD"),
    ])
    story += section_bar("3.  FINANCIAL TERMS")
    story.append(cond_table([
        ["Parameter", "Value", "Notes"],
        ["Maximum Authorized Amount", "$  _____________________ CAD", "Subject to conditions"],
        ["Initial Term", "_______ months", "Extension at Lender's discretion"],
        ["Annual Interest Rate", "_____ % (fixed)", "Calculated monthly"],
        ["Origination Fee", "3% to 3.5% of amount", "Payable at signing"],
        ["Analysis Fee (term extension)", "1% of principal", "If extension beyond Maturity (renegotiable)"],
        ["Prepayment Penalty", "Min. 3 months interest", "At any time"],
        ["Target Maximum LTV", "_____ %", "On approved AACI value — flexibility with collateral"],
        ["Target DSCR Minimum", "_____ x", "Debt service coverage ratio"],
        ["Target Minimum Down Payment", "_____ %", "Verified equity funds"],
    ], [2.6*inch, 2.0*inch, 1.4*inch]))
    story.append(Spacer(1,6))
    story += section_bar("4.  REQUIRED SECURITY")
    story.append(cond_table([
        ["Security", "Rank / Details"],
        ["Real estate mortgage on property", "Exclusive 1st rank"],
        ["Assignment of leases (total and immediate)", "In favour of Capital Norvex"],
        ["Personal guarantee", "Joint, irrevocable and unlimited"],
        ["Assignment of existing leases", "All leases in force"],
        ["Property insurance", "Replacement value"],
        ["Civil liability insurance", "Minimum $2,000,000"],
    ], [2.8*inch, 3.2*inch]))
    story.append(Spacer(1,6))
    story += section_bar("5.  REVENUE ANALYSIS AND EXIT STRATEGY")
    story.append(body("Capital Norvex will analyze viability based on documented actual revenues. The Borrower provides:"))
    for t in ["Current, signed and up-to-date rent rolls",
              "Revenue history for the last 24 months",
              "Detailed operating expense list",
              "Capital expenditure report (capex) — last 3 years"]:
        story.append(bullet(t))
    story.append(Spacer(1,4))
    story += section_bar("6.  CONDITIONS PRECEDENT TO DISBURSEMENT")
    for t in ["Constitutional documents and resolutions authorizing the loan",
              "Approved independent appraisal report",
              "Building inspection report — certified engineer",
              "Phase I environmental report (Phase II if required)",
              "Certified rent rolls and revenue history",
              "Audited financial statements for the last 2 years",
              "Proof of injected equity contribution",
              "Registration of first-rank mortgage",
              "Signed personal guarantees",
              "Complete legal opinion accepted by Capital Norvex"]:
        story.append(bullet(t))
    story.append(Spacer(1,4))
    story += section_bar("7.  ZERO TOLERANCE — TAXES AND CHARGES")
    story.append(body("The Borrower undertakes to pay punctually all property taxes, school taxes, municipal charges, insurance premiums and other current obligations affecting the Property. Any delay must be remedied within seven (7) days of notice from the Lender. Failing this, an Event of Default shall be automatically declared."))

    story += section_bar("8.  REPRESENTATION OF CAPITAL NORVEX INC.")
    story.append(body("For Capital Norvex Inc., the loan agreement and the mortgage deed shall be signed by a designated representative, duly authorized pursuant to a corporate resolution adopted by the sole shareholder and president, Mrs. Suzanne Breton, a certified true copy of which shall be attached to the file."))

    story += section_bar("9.  INDISSOCIABILITY — LOAN AGREEMENT AND MORTGAGE DEED")
    story.append(body("The loan agreement and the mortgage deed entered into between the Parties form an INDISSOCIABLE contractual whole. Any breach of the terms of the loan agreement automatically constitutes an Event of Default within the meaning of the mortgage deed, and vice versa. In the event of any divergence or ambiguity, the interpretation most favourable to the Lender shall prevail."))

    story += section_bar("10.  VALIDITY AND GENERAL CONDITIONS")
    story += alert_box("This commitment letter is valid for a period of 30 days following the date of issuance. Capital Norvex reserves the right to revise the conditions or withdraw the offer without notice beyond this period.")
    for t in ["Does not constitute an irrevocable commitment prior to the signing of the loan agreement.",
              "Revenues retained are those verified by Capital Norvex, not projections.",
              "Any modification must be confirmed in writing by Capital Norvex.",
              "LTV ratios are targets, adjustable on a case-by-case basis with acceptable collateral."]:
        story.append(bullet(t))


def build_refinancement_en(story):
    story += section_bar("1.  IDENTIFICATION OF PARTIES")
    story += two_col_fields([
        ("Lender:", "Capital Norvex Inc."),
        ("Lender's Address:", "2705-1000 André-Prévost, Île-des-Sœurs (Verdun), Montréal, QC H3E 0G2"),
        ("Phone:", "1-(438)-533-PRET (7738)"),
        ("Email:", "info@capitalnorvex.com"),
        ("Borrower:", "_______________________________________________________"),
        ("Represented by:", "_______________________________________________________"),
        ("Borrower's Address:", "_______________________________________________________"),
        ("Business Number (NEQ):", "________________________________"),
    ])

    story += section_bar("2.  DESCRIPTION OF PROPERTY TO BE REFINANCED")
    story += two_col_fields([
        ("Property Address:", "_______________________________________________________"),
        ("Property Type:", "Multi-residential / Commercial / Mixed-use / Other: ________"),
        ("Year of Construction:", "________________________________"),
        ("Cadastral lot(s):", "_______________________________________________________"),
        ("Market Value (AACI):", "________________________________"),
        ("Annual Gross Rental Income:", "________________________________"),
        ("Stabilized Net Income:", "________________________________"),
        ("Current Occupancy Rate:", "________________________________"),
    ])

    story += section_bar("3.  EXIT STRATEGY \u2014 MANDATORY")
    story += alert_box("Refinancing is granted only with a clear and documented exit strategy. NO pure cash-out without a repayment plan is authorized.")
    story.append(body("The Borrower undertakes to provide one of the following strategies:"))
    for t in ["Sale of the Property — promise to purchase or listing mandate",
              "Confirmed bank refinancing — commitment letter or preliminary confirmation",
              "Other documented strategy acceptable to the Lender"]:
        story.append(bullet(t))

    story += section_bar("4.  FINANCIAL TERMS")
    story.append(cond_table([
        ["Item", "Condition", "Notes"],
        ["Maximum Approved Amount", "____________ CAD", "Subject to conditions"],
        ["Loan Term", "12 months renewable", "Subject to approval"],
        ["Interest Rate", "_____ % (fixed)", "Calculated monthly"],
        ["Origination Fee", "3% to 3.5% of amount", "At signing"],
        ["Analysis Fee (term extension)", "1% of principal", "If extension beyond Maturity (renegotiable)"],
        ["Prepayment Penalty", "Min. 3 months interest", "At any time"],
        ["Target Maximum LTV", "70%", "On AACI value — flexibility with collateral"],
        ["Target Minimum DCR", "1.20x", "On stabilized net income"],
        ["Target Cash Equity Minimum", "30%", "Of property value"],
    ], [2.5*inch, 2.0*inch, 1.5*inch]))
    story.append(Spacer(1,6))

    story += section_bar("5.  USE OF FUNDS")
    story += alert_box("NO pure cash-out without a documented repayment plan is authorized. Any allocation of funds must be the subject of written justification acceptable to the Lender.")
    story.append(body("The Loan proceeds are exclusively allocated to:"))
    for t in ["Full repayment of the existing mortgage (Former Lender)",
              "File fees, notarial fees, taxes and registration fees",
              "Additional liquidity for documented specific use (tenant improvements, capex, etc.)"]:
        story.append(bullet(t))

    story += section_bar("6.  REQUIRED SECURITY")
    story.append(cond_table([
        ["Security", "Rank / Details"],
        ["Real Estate Mortgage", "1st rank on the Property (after Former Lender discharge)"],
        ["Assignment of Rents", "Total and immediate"],
        ["Personal Suretyship", "Joint, irrevocable and unlimited"],
        ["Former Lender Discharge", "MANDATORY — prior to or simultaneous with disbursement"],
        ["Mortgage Discharge Registration", "MANDATORY — duly registered"],
    ], [2.8*inch, 3.2*inch]))
    story.append(Spacer(1,6))

    story += section_bar("7.  CONDITIONS PRECEDENT TO DISBURSEMENT")
    for t in ["Constitutional documents and resolutions authorizing the loan",
              "Accredited AACI appraisal dated less than 6 months",
              "Discharge / payoff letter from Former Lender stating the exact balance",
              "Documented exit strategy acceptable to the Lender",
              "Financial statements and operating report of the Property",
              "Certified rent rolls and revenue history",
              "Phase I environmental study (if applicable)",
              "Insurance policies with Capital Norvex designated as beneficiary",
              "Registration of first-rank mortgage (after discharge)",
              "Signed personal guarantees"]:
        story.append(bullet(t))
    story.append(Spacer(1,4))

    story += section_bar("8.  ZERO TOLERANCE \u2014 TAXES AND CHARGES")
    story.append(body("The Borrower undertakes to pay punctually all property taxes, school taxes, municipal charges, insurance premiums and other current obligations affecting the Property. Any delay must be remedied within seven (7) days of notice from the Lender. Failing this, an Event of Default shall be automatically declared."))

    story += section_bar("9.  REPRESENTATION OF CAPITAL NORVEX INC.")
    story.append(body("For Capital Norvex Inc., the loan agreement and the mortgage deed shall be signed by a designated representative, duly authorized pursuant to a corporate resolution adopted by the sole shareholder and president, Mrs. Suzanne Breton, a certified true copy of which shall be attached to the file."))

    story += section_bar("10.  INDISSOCIABILITY \u2014 LOAN AGREEMENT AND MORTGAGE DEED")
    story.append(body("The loan agreement and the mortgage deed entered into between the Parties form an INDISSOCIABLE contractual whole. Any breach of the terms of the loan agreement automatically constitutes an Event of Default within the meaning of the mortgage deed, and vice versa. In the event of any divergence or ambiguity, the interpretation most favourable to the Lender shall prevail."))

    story += section_bar("11.  VALIDITY AND GENERAL CONDITIONS")
    story += alert_box("This commitment letter is valid for a period of 30 days following the date of issuance. Capital Norvex reserves the right to revise the conditions or withdraw the offer without notice.")
    for t in ["Does not constitute an irrevocable commitment prior to the signing of the loan agreement.",
              "Refinancing is subject to prior discharge of the Former Lender's mortgage.",
              "LTV/DCR ratios are targets, adjustable on a case-by-case basis with acceptable collateral (up to 95% LTV).",
              "Any modification must be confirmed in writing by Capital Norvex."]:
        story.append(bullet(t))


def build_norvex_tools(story, has_track):
    story.append(Spacer(1, 8))
    story += section_bar("CAPITAL NORVEX DIGITAL TOOLS")
    story.append(Spacer(1, 4))
    story.append(body(
        "Upon authorization of the financing, the Borrower benefits from Capital Norvex\u2019s "
        "proprietary technology tools:"))
    story.append(bullet(
        "<b>Borrower Portal (PWA — Progressive Web Application)</b>: secure web application "
        "accessible <b>24/7</b> from any device. Allows real-time consultation of the Loan "
        "balance, payment schedule, transaction history, disbursement status and any document "
        "relevant to the file."))
    if has_track:
        story.append(bullet(
            "<b>Norvex Track\u2122</b>: progressive disbursement management and traceability "
            "module, accessible <b>24/7</b>. Every disbursement request is submitted and "
            "documented through Norvex Track\u2122 (inspection reports, invoices, progress photos, "
            "professional certificates, lien waivers). Capital Norvex retains absolute, "
            "exclusive and discretionary control over disbursement authorizations."))
    story.append(body(
        "These tools constitute a transparency commitment from Capital Norvex toward the "
        "Borrower and do not replace the official written communications provided for in the "
        "definitive Loan Agreement."))
    story.append(Spacer(1, 6))


# ── SIGNATURES ────────────────────────────────────────────────────────────────
def build_signatures(story):
    story.append(PageBreak())
    tbl = Table([[Paragraph("ACCEPTANCE AND SIGNATURES", ST["section"])]],
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
        "The undersigned declare having read, understood and accepted all conditions of this "
        "commitment letter and undertake to provide all required documents in connection with "
        "the conclusion of the definitive loan agreement with Capital Norvex Inc."))
    story.append(Spacer(1,12))
    story += sign_block("LENDER — CAPITAL NORVEX INC.", [
        ("Authorized Representative :", "________________________________"),
        ("Title :", "________________________________"),
    ])
    story += sign_block("BORROWER", [
        ("Corporate Name :", "________________________________"),
        ("Authorized Representative :", "________________________________"),
        ("Title :", "________________________________"),
    ])
    story += sign_block("GUARANTOR 1", [("Full Name :", "________________________________")])
    story += sign_block("GUARANTOR 2 (if applicable)", [("Full Name :", "________________________________")])
    story.append(Spacer(1,20))
    story.append(GoldLine())
    story.append(Spacer(1,6))
    story.append(Paragraph(
        "Capital Norvex Inc.  |  capitalnorvex.com  |  info@capitalnorvex.com  |  Quebec & Ontario, Canada",
        ST["note"]))
    story.append(Paragraph(
        "The French version shall prevail in Quebec / La version française prévaut au Québec",
        ParagraphStyle("lang_footer", fontName="Helvetica-Oblique", fontSize=7,
                       textColor=GREY_MED, alignment=TA_CENTER, spaceAfter=4)))


# ── GENERATION ────────────────────────────────────────────────────────────────
configs = [
    {
        "filename": r"/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres/CapitalNorvex_CommitmentLetter_Construction_EN.pdf",
        "product_name": "CONSTRUCTION LOAN",
        "product_desc": "Institutional Private Lending — New Construction & Major Renovations — Quebec & Ontario",
        "product_tag": "CONSTRUCTION LOAN",
        "builder": build_construction_en,
        "has_track": True,
    },
    {
        "filename": r"/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres/CapitalNorvex_CommitmentLetter_Land_EN.pdf",
        "product_name": "LAND LOAN",
        "product_desc": "Institutional Private Lending — Land Acquisition & Carry — Quebec & Ontario",
        "product_tag": "LAND LOAN",
        "builder": build_land_en,
        "has_track": False,
    },
    {
        "filename": r"/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres/CapitalNorvex_CommitmentLetter_Acquisition_EN.pdf",
        "product_name": "PROPERTY ACQUISITION LOAN",
        "product_desc": "Institutional Private Lending — Income-Producing Property Acquisition — Quebec & Ontario",
        "product_tag": "PROPERTY ACQUISITION",
        "builder": build_acquisition_en,
        "has_track": False,
    },
    {
        "filename": r"/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres/CapitalNorvex_CommitmentLetter_Refinancing_EN.pdf",
        "product_name": "REFINANCING LOAN",
        "product_desc": "Institutional Private Lending — Real Estate Refinancing — Quebec & Ontario",
        "product_tag": "REFINANCING LOAN",
        "builder": build_refinancement_en,
        "has_track": False,
    },
]

for cfg in configs:
    doc = SimpleDocTemplate(
        cfg["filename"], pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 40, bottomMargin=MARGIN + 38,
        title=f"Commitment Letter — {cfg['product_name']} — Capital Norvex",
        author="Capital Norvex Inc.",
    )
    on_page = make_on_page(cfg["product_tag"])
    story = []
    build_cover(story, cfg["product_name"], cfg["product_desc"])
    cfg["builder"](story)
    build_norvex_tools(story, cfg["has_track"])
    build_signatures(story)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"OK  {cfg['filename']}")

print("\n4 English commitment letters generated successfully (Construction, Land, Acquisition, Refinancing)!")
