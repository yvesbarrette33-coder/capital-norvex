#!/usr/bin/env python3
"""
HYPOTHÈQUE MOBILIÈRE SUR CRÉANCE INDIVIDUELLE
Capital Norvex Inc. (Constituant) en faveur du Partenaire (Créancier hypothécaire)

⚠️  FORMAT JURIDIQUE OFFICIEL — SOBRE, SANS BRANDING COMMERCIAL
    Les actes hypothécaires ne portent PAS de logo ou éléments graphiques commerciaux.
    Le notaire utilisera son propre en-tête de cabinet lors de l'authentification.

Cadre légal : Code civil du Québec, art. 2660, 2666, 2696-2701, 2710 et s., 2748 et s.
Publication : RDPRM (Registre des droits personnels et réels mobiliers)

Génère 2 PDFs :
- Hypotheque_Mobiliere_Creance_Individuelle_FR.pdf (français)
- Movable_Hypothec_Individual_Claim_EN.pdf (anglais)
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import black, HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

# ── Format juridique sobre ───────────────────────────────────────────────────
BLACK    = HexColor("#000000")
DARK     = HexColor("#1a1a1a")
GREY_DK  = HexColor("#3a3a3a")
GREY_MED = HexColor("#666666")
GREY_LT  = HexColor("#9a9a9a")
WHITE    = HexColor("#ffffff")

PAGE_W, PAGE_H = letter
MARGIN = 1.0 * inch  # marges juridiques standards

# ── Header / Footer SOBRES ───────────────────────────────────────────────────
def make_on_page(title_top, page_label_fr=True):
    def on_page(canvas, doc):
        canvas.saveState()
        w, h = letter
        # Titre courant minimaliste en haut (texte uniquement, gris foncé)
        canvas.setFillColor(GREY_DK)
        canvas.setFont("Times-Roman", 8.5)
        canvas.drawString(MARGIN, h - 0.5 * inch, title_top)
        # Filet horizontal très fin
        canvas.setStrokeColor(GREY_LT)
        canvas.setLineWidth(0.4)
        canvas.line(MARGIN, h - 0.55 * inch, w - MARGIN, h - 0.55 * inch)
        # Numéro de page en bas centre
        canvas.setFillColor(GREY_DK)
        canvas.setFont("Times-Roman", 9)
        page_text = f"— {doc.page} —"
        canvas.drawCentredString(w / 2, 0.5 * inch, page_text)
        canvas.restoreState()
    return on_page

# ── Styles juridiques ────────────────────────────────────────────────────────
def build_styles():
    def S(name, **kw):
        return ParagraphStyle(name, **kw)
    return dict(
        cover_title  = S("CoverTitle", fontName="Times-Bold", fontSize=18, textColor=BLACK,
                         alignment=TA_CENTER, spaceAfter=12, leading=22),
        cover_sub    = S("CoverSub", fontName="Times-Roman", fontSize=12, textColor=DARK,
                         alignment=TA_CENTER, spaceAfter=8, leading=16),
        cover_meta   = S("CoverMeta", fontName="Times-Roman", fontSize=10, textColor=GREY_DK,
                         alignment=TA_CENTER, spaceAfter=4, leading=14),
        section      = S("Section", fontName="Times-Bold", fontSize=11, textColor=BLACK,
                         alignment=TA_LEFT, spaceBefore=14, spaceAfter=6, leading=14),
        article      = S("Article", fontName="Times-Bold", fontSize=10, textColor=BLACK,
                         alignment=TA_LEFT, spaceBefore=8, spaceAfter=3, leading=13),
        body         = S("Body", fontName="Times-Roman", fontSize=10, textColor=BLACK,
                         alignment=TA_JUSTIFY, spaceAfter=4, leading=14),
        bullet       = S("Bullet", fontName="Times-Roman", fontSize=10, textColor=BLACK,
                         alignment=TA_JUSTIFY, spaceAfter=3, leading=14, leftIndent=18),
        sign_lbl     = S("SignLbl", fontName="Times-Bold", fontSize=10, textColor=BLACK,
                         alignment=TA_LEFT, spaceAfter=4, leading=13),
        confidential = S("Conf", fontName="Times-Italic", fontSize=9, textColor=GREY_DK,
                         alignment=TA_CENTER, spaceAfter=4),
    )

ST = build_styles()

def sec(title):
    return [Spacer(1, 8), Paragraph(title, ST["section"]), Spacer(1, 4)]

def art(num, title):
    return [Paragraph(f"{num}  {title}", ST["article"])]

def bp(text):
    return Paragraph(text, ST["body"])

def sp(h=6):
    return Spacer(1, h)

def blt(items):
    out = []
    for it in items:
        out.append(Paragraph(f"•&nbsp;&nbsp;{it}", ST["bullet"]))
    return out

def num_list(items):
    out = []
    for n, t in items:
        out.append(Paragraph(f"<b>{n}</b>&nbsp;&nbsp;{t}", ST["bullet"]))
    return out

def section_banner(text):
    """Banderole sobre noir-et-blanc pour titres de blocs (signatures, etc.)"""
    t = Table([[Paragraph(f"<b>{text}</b>",
                          ParagraphStyle("b", fontName="Times-Bold", fontSize=10,
                                          alignment=TA_CENTER, textColor=BLACK, leading=14))]],
              colWidths=[PAGE_W - 2*MARGIN])
    t.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.6, BLACK),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    return t

def sign_pair(left, right):
    t = Table([[Paragraph(left, ST["sign_lbl"]), Paragraph(right, ST["sign_lbl"])]],
              colWidths=[(PAGE_W - 2*MARGIN)/2 - 6, (PAGE_W - 2*MARGIN)/2 - 6])
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 16),
        ("LINEBELOW", (0,0), (-1,-1), 0.5, BLACK),
    ]))
    return t


# ═══════════════════════════════════════════════════════════════════════════
# VERSION FRANÇAISE
# ═══════════════════════════════════════════════════════════════════════════
def build_fr():
    story = []

    # ── PAGE DE COUVERTURE SOBRE ───────────────────────────────────────────
    story.append(Spacer(1, 80))
    story.append(Paragraph("HYPOTHÈQUE MOBILIÈRE", ST["cover_title"]))
    story.append(Paragraph("SUR CRÉANCE INDIVIDUELLE", ST["cover_title"]))
    story.append(Spacer(1, 30))
    # Filet décoratif sobre (ligne noire pleine)
    t = Table([[""]], colWidths=[3.0*inch], rowHeights=[0.02*inch])
    t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), BLACK)]))
    story.append(t)
    story.append(Spacer(1, 30))
    story.append(Paragraph("ENTRE", ST["cover_meta"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>CAPITAL NORVEX INC.</b>", ST["cover_sub"]))
    story.append(Paragraph("(Constituant — Débiteur hypothécaire)", ST["cover_meta"]))
    story.append(Spacer(1, 14))
    story.append(Paragraph("ET", ST["cover_meta"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>LE PARTENAIRE</b>", ST["cover_sub"]))
    story.append(Paragraph("(Créancier hypothécaire)", ST["cover_meta"]))
    story.append(Spacer(1, 60))
    story.append(Paragraph(
        "Code civil du Québec — art. 2660, 2696-2701, 2710 et s., 2748 et s.",
        ST["cover_meta"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Publication au RDPRM (Registre des droits personnels et réels mobiliers)",
        ST["cover_meta"]))
    story.append(Spacer(1, 60))
    story.append(Paragraph(
        "Date : ____________________________________",
        ST["cover_meta"]))
    story.append(PageBreak())

    # ── PRÉAMBULE / IDENTIFICATION DES PARTIES ─────────────────────────────
    story += sec("IDENTIFICATION DES PARTIES")
    story += art("A.", "Constituant — Débiteur hypothécaire")
    story.append(bp(
        "<b>CAPITAL NORVEX INC.</b>, personne morale légalement constituée en vertu des lois "
        "du Québec, ayant son siège social au 2705-1000, rue André-Prévost, Île-des-Sœurs "
        "(Verdun), Montréal (Québec) H3E 0G2, ci-après désignée le « <b>Constituant</b> » ou "
        "« <b>Capital Norvex</b> »;"))
    story.append(sp())
    story.append(bp(
        "Représentée aux fins des présentes par : ____________________________________ "
        "(nom complet), agissant à titre de ____________________________________ (mandataire "
        "désigné), dûment autorisé(e) en vertu d'une résolution adoptée par le conseil "
        "d'administration de Capital Norvex Inc. en date du __________________, signée par "
        "Madame Suzanne Breton, présidente et actionnaire unique, dont copie est annexée "
        "aux présentes (Annexe A — Résolution corporative)."))
    story.append(sp())
    story += art("B.", "Créancier hypothécaire — Partenaire")
    story.append(bp(
        "____________________________________ (dénomination sociale ou nom complet), "
        "____________________________________ (forme juridique : société par actions / "
        "personne physique / autre), ayant son siège ou résidant au "
        "____________________________________, ci-après désigné le « <b>Créancier "
        "hypothécaire</b> » ou le « <b>Partenaire</b> »."))
    story.append(sp())
    story.append(bp(
        "Représenté aux fins des présentes par : ____________________________________ "
        "(nom complet), agissant à titre de ____________________________________ (titre)."))
    story.append(sp(10))

    # ── PRÉAMBULE ──────────────────────────────────────────────────────────
    story += sec("PRÉAMBULE")
    story.append(bp(
        "ATTENDU QUE le Partenaire a consenti à Capital Norvex un financement (ci-après le "
        "« <b>Financement Partenaire</b> ») d'un montant de "
        "____________________________________ dollars canadiens "
        "(________________________________ $ CAD), aux termes d'une <b>Convention de "
        "partenariat</b> signée entre les parties (ci-après la « <b>Convention de "
        "partenariat</b> »), en vue du financement par Capital Norvex d'un dossier de prêt "
        "spécifique consenti à un emprunteur tiers (ci-après l'« <b>Actif de Prêt</b> »);"))
    story.append(sp())
    story.append(bp(
        "ATTENDU QUE Capital Norvex prête à son tour les fonds reçus du Partenaire à un "
        "emprunteur tiers (ci-après l'« <b>Emprunteur</b> »), garantis par une hypothèque "
        "immobilière de premier rang détenue par Capital Norvex sur l'immeuble identifié à "
        "l'Annexe B (ci-après la « <b>Créance Hypothécaire</b> » détenue par Capital Norvex);"))
    story.append(sp())
    story.append(bp(
        "ATTENDU QUE Capital Norvex désire consentir au Partenaire, à titre de garantie de "
        "ses obligations envers ce dernier en vertu de la Convention de partenariat, une "
        "<b>hypothèque mobilière sur la Créance Hypothécaire individuelle</b> qu'elle "
        "détient envers l'Emprunteur, conformément aux articles 2696 à 2701 du <i>Code civil "
        "du Québec</i>;"))
    story.append(sp())
    story.append(bp(
        "ATTENDU QUE la présente hypothèque mobilière porte <b>UNIQUEMENT</b> sur la créance "
        "hypothécaire spécifique afférente au présent Actif de Prêt, et <b>NON sur "
        "l'universalité</b> des créances de Capital Norvex envers ses autres clients;"))
    story.append(sp())
    story.append(bp(
        "EN CONSÉQUENCE, les parties conviennent de ce qui suit :"))
    story.append(sp())

    # ── 1 ─────────────────────────────────────────────────────────────────
    story += sec("1. CONSTITUTION DE L'HYPOTHÈQUE MOBILIÈRE")
    story += art("1.1", "Constitution")
    story.append(bp(
        "Le Constituant, par les présentes, <b>HYPOTHÈQUE</b> en faveur du Créancier "
        "hypothécaire, à titre de sûreté pour le paiement et l'exécution des Obligations "
        "Garanties (telles que définies à l'article 2.1), <b>la Créance Hypothécaire "
        "individuelle</b> qu'il détient envers l'Emprunteur, telle que décrite à l'article 3 "
        "et à l'Annexe B des présentes."))
    story.append(sp())
    story += art("1.2", "Nature de l'hypothèque")
    story.append(bp(
        "La présente hypothèque est consentie en vertu des articles 2660, 2696 à 2701, et "
        "2710 et suivants du <i>Code civil du Québec</i>. Il s'agit d'une <b>hypothèque "
        "mobilière conventionnelle sur créance individuelle</b>, dûment publiée au Registre "
        "des droits personnels et réels mobiliers (RDPRM) conformément à l'article 2710 du "
        "<i>Code civil du Québec</i>."))
    story.append(sp())
    story += art("1.3", "Portée limitée à la créance individuelle")
    story.append(bp(
        "Les parties reconnaissent expressément que la présente hypothèque <b>ne porte que "
        "sur la Créance Hypothécaire individuelle</b> détaillée à l'Annexe B, à l'exclusion "
        "expresse de toute autre créance, présente ou future, détenue par Capital Norvex "
        "envers ses autres clients ou emprunteurs. La présente hypothèque <b>n'est pas une "
        "hypothèque sur universalité</b> au sens des articles 2666 à 2674 du <i>Code civil "
        "du Québec</i>."))
    story.append(sp())

    # ── 2 ─────────────────────────────────────────────────────────────────
    story += sec("2. OBLIGATIONS GARANTIES ET MONTANT")
    story += art("2.1", "Obligations garanties")
    story.append(bp(
        "La présente hypothèque garantit l'exécution intégrale par Capital Norvex de "
        "l'ensemble de ses obligations envers le Partenaire en vertu de la Convention de "
        "partenariat et des présentes (ci-après les « <b>Obligations Garanties</b> »), "
        "incluant notamment :"))
    story += blt([
        "Le remboursement intégral du capital du Financement Partenaire, soit la somme de ____________________________________ dollars canadiens (________________________________ $ CAD);",
        "Le paiement des Intérêts (ou Mensualités, selon la Convention de partenariat applicable) calculés au taux de ________ % par année;",
        "Le paiement de tous les frais, accessoires, dommages, intérêts et indemnités prévus aux présentes ou à la Convention de partenariat;",
        "Le respect des engagements de transparence, de bonne foi et de gestion conjointe prévus à la Convention de partenariat;",
        "Le respect des obligations de radiation au RDPRM à l'échéance.",
    ])
    story.append(sp())
    story += art("2.2", "Montant garanti — Article 2689 C.c.Q.")
    story.append(bp(
        "Pour les fins de la publication au RDPRM, le montant total garanti par la présente "
        "hypothèque est fixé à <b>cent vingt pour cent (120 %)</b> du montant du Financement "
        "Partenaire, soit ____________________________________ dollars canadiens "
        "(________________________________ $ CAD), afin de couvrir le capital, les intérêts, "
        "les frais et accessoires."))
    story.append(sp())

    # ── 3 ─────────────────────────────────────────────────────────────────
    story += sec("3. DESCRIPTION DE LA CRÉANCE HYPOTHÉQUÉE")
    story += art("3.1", "Identification précise de la Créance Hypothécaire")
    story.append(bp(
        "La Créance Hypothécaire individuelle hypothéquée par les présentes est celle "
        "détaillée à l'<b>Annexe B</b>, laquelle inclut notamment :"))
    story += blt([
        "<b>Identité de l'Emprunteur :</b> ____________________________________",
        "<b>Numéro de dossier interne :</b> ____________________________________",
        "<b>Montant du prêt principal :</b> ________________________________ $ CAD",
        "<b>Date du prêt :</b> ____________________________________",
        "<b>Date d'échéance :</b> ____________________________________",
        "<b>Taux d'intérêt :</b> ________ % par année",
        "<b>Acte hypothécaire immobilier (numéro de minute, notaire, date de publication) :</b> ____________________________________",
        "<b>Numéro d'inscription au Registre foncier du Québec :</b> ____________________________________",
        "<b>Description de l'immeuble en garantie :</b> ____________________________________",
    ])
    story.append(sp())
    story += art("3.2", "Étendue de la Créance Hypothéquée")
    story.append(bp(
        "L'hypothèque porte sur la Créance Hypothécaire dans son intégralité, incluant :"))
    story += blt([
        "Le capital du prêt consenti à l'Emprunteur;",
        "Tous les intérêts présents et futurs courant sur ce capital;",
        "Tous les frais, accessoires, indemnités et pénalités payables par l'Emprunteur;",
        "Tous les droits, recours, sûretés accessoires et garanties additionnelles consentis par l'Emprunteur (cautionnements, gages d'actions, hypothèques mobilières accessoires, cessions de loyers et de polices d'assurance, etc.);",
        "Tous les produits, indemnités d'assurance, indemnités d'expropriation et autres sommes reçues par Capital Norvex en lien avec cette créance.",
    ])
    story.append(sp())

    # ── 4 ─────────────────────────────────────────────────────────────────
    story += sec("4. PUBLICATION AU RDPRM")
    story += art("4.1", "Publication obligatoire")
    story.append(bp(
        "La présente hypothèque mobilière sera publiée au <b>Registre des droits personnels "
        "et réels mobiliers (RDPRM)</b> conformément aux articles 2710 et suivants du "
        "<i>Code civil du Québec</i>, dans les meilleurs délais et au plus tard concomitamment "
        "au premier déboursement du Financement Partenaire à Capital Norvex."))
    story.append(sp())
    story += art("4.2", "Frais de publication et de radiation")
    story.append(bp(
        "Tous les frais relatifs à la publication initiale au RDPRM, ainsi qu'à toute "
        "modification ou radiation subséquente, sont <b>à la charge exclusive de Capital "
        "Norvex</b>."))
    story.append(sp())
    story += art("4.3", "Renouvellement de la publication")
    story.append(bp(
        "Capital Norvex s'engage à procéder, à ses frais, au renouvellement de la "
        "publication au RDPRM avant son expiration, conformément à l'article 2798 du "
        "<i>Code civil du Québec</i>, tant et aussi longtemps que les Obligations Garanties "
        "ne sont pas intégralement éteintes."))
    story.append(sp())

    # ── 5 ─────────────────────────────────────────────────────────────────
    story += sec("5. ENGAGEMENTS DU CONSTITUANT — TRANSPARENCE ABSOLUE")
    story += art("5.1", "Transparence et reporting")
    story.append(bp(
        "Capital Norvex s'engage envers le Partenaire à une <b>transparence absolue</b> "
        "concernant la Créance Hypothéquée pendant toute la durée de la présente hypothèque, "
        "notamment en :"))
    story += blt([
        "Maintenant un compte bancaire séparé et identifié pour les fonds liés à l'Actif de Prêt visé;",
        "Donnant au Partenaire un accès <b>24 heures sur 24, 7 jours sur 7</b> au <b>Portail Partenaire</b> (PWA — Progressive Web Application) permettant de consulter en temps réel l'ensemble des informations relatives à l'Actif de Prêt et à la Créance Hypothéquée;",
        "Pour les prêts de construction et d'infrastructure, donnant au Partenaire l'accès au module <b>Norvex Track™</b>, par lequel le Partenaire <b>autorise et exécute personnellement chaque Déboursé progressif</b> 24 heures sur 24, 7 jours sur 7, garantissant ainsi sa maîtrise opérationnelle sur les fonds;",
        "Transmettant au Partenaire un rapport mensuel complet sur l'état de l'Actif de Prêt, le solde de la créance, les paiements reçus de l'Emprunteur, et tout événement matériel;",
        "Notifiant le Partenaire <b>par écrit dans les cinq (5) jours ouvrables</b> de tout Événement de Défaut de l'Emprunteur ou de tout événement susceptible d'affecter la valeur de la Créance Hypothéquée;",
        "Mettant à la disposition du Partenaire, sur demande raisonnable, les copies de tout document du dossier de l'Emprunteur (acte hypothécaire, évaluations, polices d'assurance, états de compte, etc.).",
    ])
    story.append(sp())
    story += art("5.2", "Conservation et défense de la Créance Hypothéquée")
    story.append(bp(
        "Capital Norvex s'engage à <b>conserver, défendre et faire valoir</b> la Créance "
        "Hypothéquée avec la diligence d'un administrateur du bien d'autrui, conformément "
        "aux articles 1309 et suivants du <i>Code civil du Québec</i>. Capital Norvex ne "
        "peut, sans le consentement écrit du Partenaire :"))
    story += blt([
        "Renoncer à la Créance Hypothéquée ou à toute partie significative de celle-ci;",
        "Consentir à une remise totale ou partielle de la dette de l'Emprunteur;",
        "Subordonner volontairement son rang hypothécaire au profit d'un autre créancier;",
        "Modifier substantiellement les conditions de la Créance Hypothéquée (échéance, taux, garanties accessoires) au détriment du Partenaire.",
    ])
    story.append(sp())
    story += art("5.3", "Gestion conjointe en cas de défaut de l'Emprunteur")
    story.append(bp(
        "En cas d'Événement de Défaut de l'Emprunteur, Capital Norvex et le Partenaire "
        "<b>travaillent en partenariat actif</b> pour déterminer la meilleure stratégie de "
        "protection et de recouvrement, conformément à la Convention de partenariat. Les "
        "décisions stratégiques importantes (prise en paiement, vente sous contrôle de "
        "justice, choix du courtier immobilier, conclusion d'un règlement) sont prises "
        "<b>conjointement</b> par les parties."))
    story.append(sp())
    story += art("5.4", "Frais juridiques de réalisation")
    story.append(bp(
        "L'ensemble des frais juridiques, honoraires d'avocats, frais notariaux, frais de "
        "Séquestre et autres coûts engagés par Capital Norvex dans le cadre des procédures "
        "de recouvrement ou de Reprise <b>sont à la charge exclusive de Capital Norvex</b>, "
        "et sont prélevés en premier rang sur les Produits de Vente avant toute distribution. "
        "Le Partenaire ne supporte aucun frais additionnel au-delà de sa Contribution "
        "initiale."))
    story.append(sp())
    story += art("5.5", "Information et collaboration continues")
    story.append(bp(
        "Capital Norvex s'engage à informer immédiatement le Partenaire de tout événement, "
        "notification ou procédure susceptible d'affecter la Créance Hypothéquée, incluant "
        "notamment : avis de vente sous contrôle de justice par un autre créancier, "
        "saisie-arrêt, procédure d'insolvabilité visant l'Emprunteur, contestation de "
        "l'hypothèque immobilière, sinistre ou expropriation."))
    story.append(sp())

    # ── 6 ─────────────────────────────────────────────────────────────────
    story += sec("6. ÉVÉNEMENTS DE DÉFAUT DE CAPITAL NORVEX")
    story.append(bp(
        "Constituent des Événements de Défaut de Capital Norvex en vertu des présentes :"))
    story += blt([
        "<b>Non-paiement</b> de toute somme due au Partenaire en vertu de la Convention de partenariat ou des présentes, non remédié dans les trente (30) jours suivant un avis écrit du Partenaire;",
        "<b>Manquement substantiel</b> aux engagements de transparence prévus à l'article 5 (notamment refus persistant de fournir l'accès au portail sécurisé, refus de transmettre les rapports mensuels, ou refus de notifier un défaut de l'Emprunteur), non remédié dans les trente (30) jours suivant un avis écrit;",
        "<b>Fraude documentée</b> ou détournement de fonds par Capital Norvex, ses dirigeants ou employés, en lien avec l'Actif de Prêt;",
        "<b>Insolvabilité</b>, faillite, dépôt de bilan, proposition concordataire ou nomination d'un séquestre visant Capital Norvex;",
        "<b>Aliénation non autorisée</b> de la Créance Hypothéquée ou de l'hypothèque immobilière de premier rang;",
        "<b>Subordination volontaire non autorisée</b> du rang hypothécaire de Capital Norvex au détriment du Partenaire;",
        "<b>Violation matérielle</b> de la Convention de partenariat, non remédiée dans les trente (30) jours suivant un avis écrit, sauf urgence manifeste mettant en péril la Contribution.",
    ])
    story.append(sp())

    # ── 7 ─────────────────────────────────────────────────────────────────
    story += sec("7. RECOURS DU CRÉANCIER HYPOTHÉCAIRE")
    story += art("7.1", "Recours hypothécaires — articles 2748 et s. C.c.Q.")
    story.append(bp(
        "Survenant un Événement de Défaut de Capital Norvex non remédié dans les délais "
        "prévus, le Partenaire peut, après avoir respecté la procédure de médiation prévue "
        "à l'article 9 des présentes (sauf urgence manifeste), exercer tous les recours "
        "hypothécaires prévus aux articles 2748 et suivants du <i>Code civil du Québec</i>, "
        "et notamment :"))
    story += blt([
        "<b>Prise en paiement</b> de la Créance Hypothéquée (art. 2778 et s. C.c.Q.) — le Partenaire devient titulaire de la Créance Hypothécaire détenue par Capital Norvex envers l'Emprunteur;",
        "<b>Cession de la Créance Hypothéquée</b> (art. 2710 et s. C.c.Q.) — le Partenaire peut céder ou recouvrer directement la créance auprès de l'Emprunteur;",
        "<b>Vente par le créancier</b> ou vente sous contrôle de justice de la Créance Hypothéquée;",
        "<b>Recours en perception</b> directe des paiements de l'Emprunteur, conformément à l'article 2743 et s. C.c.Q.;",
        "Tout autre recours prévu par la loi.",
    ])
    story.append(sp())
    story += art("7.2", "Subrogation du Partenaire")
    story.append(bp(
        "Une fois l'un des recours ci-dessus exercé avec succès, le Partenaire est "
        "<b>subrogé</b> dans les droits de Capital Norvex envers l'Emprunteur, incluant le "
        "bénéfice de l'hypothèque immobilière de premier rang sur l'immeuble. Capital Norvex "
        "s'engage à signer tous les documents requis pour parfaire cette subrogation et à "
        "transmettre l'ensemble du dossier au Partenaire."))
    story.append(sp())
    story += art("7.3", "Cumul des recours")
    story.append(bp(
        "Les recours hypothécaires prévus aux présentes sont cumulatifs et non exclusifs. "
        "Le Partenaire peut exercer tout recours, judiciaire ou extrajudiciaire, pour la "
        "réalisation de la Créance Hypothéquée et la réparation du préjudice subi."))
    story.append(sp())

    # ── 8 ─────────────────────────────────────────────────────────────────
    story += sec("8. RADIATION À L'EXTINCTION DES OBLIGATIONS")
    story += art("8.1", "Radiation obligatoire")
    story.append(bp(
        "Dès l'extinction intégrale des Obligations Garanties (remboursement complet du "
        "capital, des intérêts et des frais), le Partenaire s'engage à <b>donner mainlevée</b> "
        "et à autoriser la <b>radiation</b> de la présente hypothèque mobilière au RDPRM, "
        "dans un délai de dix (10) jours ouvrables suivant la réception de la confirmation "
        "écrite de Capital Norvex et de l'ensemble des sommes dues."))
    story.append(sp())
    story += art("8.2", "Frais de radiation")
    story.append(bp(
        "Les frais de radiation au RDPRM sont à la charge exclusive de Capital Norvex."))
    story.append(sp())

    # ── 9 ─────────────────────────────────────────────────────────────────
    story += sec("9. MÉDIATION OBLIGATOIRE AVANT RECOURS JUDICIAIRES")
    story.append(bp(
        "Avant d'introduire tout recours judiciaire en vertu des présentes (à l'exclusion "
        "des recours hypothécaires extrajudiciaires et des mesures conservatoires urgentes), "
        "les parties s'engagent à tenter de résoudre tout différend par voie de "
        "<b>médiation</b>, selon la procédure prévue à la Convention de partenariat. La "
        "présente clause de médiation est <b>indissociable</b> de celle prévue à la "
        "Convention de partenariat et s'applique <i>mutatis mutandis</i> aux différends "
        "découlant de la présente hypothèque."))
    story.append(sp())

    # ── 10 ────────────────────────────────────────────────────────────────
    story += sec("10. INDISSOCIABILITÉ AVEC LA CONVENTION DE PARTENARIAT")
    story.append(bp(
        "La présente hypothèque mobilière et la Convention de partenariat conclue entre les "
        "parties forment <b>un ensemble contractuel indissociable</b>. Les deux documents "
        "doivent être lus, interprétés et exécutés conjointement et de manière complémentaire. "
        "Toute clause, condition ou obligation prévue à la Convention de partenariat "
        "s'applique pleinement aux parties à la présente hypothèque, et tout manquement aux "
        "termes de la Convention de partenariat constitue automatiquement un Événement de "
        "Défaut au sens de l'article 6 des présentes. En cas de divergence ou d'ambiguïté "
        "entre les deux documents, l'<b>interprétation la plus protectrice du Partenaire</b> "
        "(en sa qualité de créancier hypothécaire) prévaudra."))
    story.append(sp())

    # ── 11 ────────────────────────────────────────────────────────────────
    story += sec("11. BONNE FOI ET COLLABORATION")
    story.append(bp(
        "Les parties s'engagent à exécuter la présente hypothèque <b>de bonne foi</b>, "
        "conformément aux articles 6, 7 et 1375 du <i>Code civil du Québec</i>, dans un "
        "esprit de collaboration, de transparence et de respect mutuel. Aucune partie ne "
        "pourra invoquer un manquement de l'autre partie sans avoir préalablement tenté de "
        "résoudre la situation de bonne foi par la communication directe et, le cas échéant, "
        "par la procédure de médiation prévue à l'article 9."))
    story.append(sp())

    # ── 12 ────────────────────────────────────────────────────────────────
    story += sec("12. DISPOSITIONS GÉNÉRALES")
    story += art("12.1", "Droit applicable")
    story.append(bp(
        "La présente hypothèque est régie et interprétée selon les <b>lois de la province "
        "de Québec et les lois fédérales du Canada applicables</b>. Tout différend relève "
        "de la compétence exclusive des tribunaux du district judiciaire de Montréal, sous "
        "réserve de l'article 9 (Médiation obligatoire)."))
    story.append(sp())
    story += art("12.2", "Modifications, avis et cession")
    story += blt([
        "<b>Modifications :</b> Toute modification doit être faite par écrit, signée des deux parties et publiée au RDPRM si requis.",
        "<b>Avis :</b> Tout avis doit être donné par écrit, par courriel avec accusé de réception ou par courrier recommandé.",
        "<b>Cession par le Partenaire :</b> Le Partenaire peut céder ses droits avec l'accord écrit de Capital Norvex, lequel ne peut être déraisonnablement refusé.",
    ])
    story.append(sp())
    story += art("12.3", "Divisibilité, intégralité et renonciation")
    story += blt([
        "<b>Divisibilité :</b> Toute clause invalide n'affecte pas la validité du reste de l'hypothèque.",
        "<b>Intégralité :</b> La présente hypothèque, ensemble avec ses Annexes et la Convention de partenariat, constitue l'entente complète des parties relativement à la Créance Hypothéquée.",
        "<b>Renonciation :</b> Aucune tolérance ou délai dans l'exercice d'un droit ne constitue une renonciation permanente à ce droit.",
    ])
    story.append(sp())
    story += art("12.4", "Langue officielle")
    story.append(bp(
        "Le <b>français est la langue officielle</b> de la présente hypothèque. Toute "
        "traduction anglaise est fournie à titre de courtoisie; en cas de divergence, la "
        "version française prévaut."))
    story.append(sp())

    # ── 13 SIGNATURES ─────────────────────────────────────────────────────
    story += sec("13. SIGNATURES")
    story.append(sp(4))
    story.append(bp(
        "EN FOI DE QUOI, les parties ont signé la présente <b>Hypothèque Mobilière sur "
        "Créance Individuelle</b> à la date indiquée ci-dessous, après en avoir pris "
        "pleinement connaissance et avoir obtenu les conseils juridiques qu'elles ont jugé "
        "appropriés. La présente hypothèque sera publiée au RDPRM dans les meilleurs délais "
        "suivant sa signature."))
    story.append(sp(14))

    story.append(section_banner("CAPITAL NORVEX INC. — CONSTITUANT (DÉBITEUR HYPOTHÉCAIRE)"))
    story.append(sp(8))
    story.append(sign_pair("Représentant autorisé :", "Titre :"))
    story.append(sign_pair("Date :", "Signature :"))
    story.append(sp(8))
    story.append(bp(
        "<i>Représentant désigné en vertu de la résolution corporative annexée (Annexe A), "
        "signée par Madame Suzanne Breton, présidente et actionnaire unique de Capital "
        "Norvex Inc.</i>"))
    story.append(sp(20))

    story.append(section_banner("PARTENAIRE — CRÉANCIER HYPOTHÉCAIRE"))
    story.append(sp(8))
    story.append(sign_pair("Dénomination sociale ou nom :", "Représentant autorisé :"))
    story.append(sign_pair("Titre :", "Date :"))
    story.append(sp(14))
    story.append(Paragraph("Signature :", ST["sign_lbl"]))
    story.append(sp(20))
    story.append(Paragraph(
        "<i>Hypothèque mobilière sur créance individuelle constituée en vertu des articles "
        "2660, 2696-2701 et 2710 et s. du Code civil du Québec. Publication au RDPRM "
        "obligatoire avant le premier déboursement.</i>", ST["confidential"]))

    # ── ANNEXES ───────────────────────────────────────────────────────────
    story.append(PageBreak())
    story += sec("ANNEXE A — RÉSOLUTION CORPORATIVE DE CAPITAL NORVEX INC.")
    story.append(bp(
        "<i>Insérer ici la copie certifiée conforme de la résolution adoptée par le conseil "
        "d'administration de Capital Norvex Inc., signée par Madame Suzanne Breton, "
        "présidente et actionnaire unique, autorisant le mandataire désigné à signer la "
        "présente hypothèque mobilière au nom et pour le compte de Capital Norvex Inc.</i>"))
    story.append(sp(20))

    story += sec("ANNEXE B — DESCRIPTION DÉTAILLÉE DE LA CRÉANCE HYPOTHÉQUÉE")
    story.append(bp("<b>1. Identification de l'Emprunteur</b>"))
    story.append(bp("Nom / Dénomination sociale : ____________________________________"))
    story.append(bp("NEQ ou autre identifiant : ____________________________________"))
    story.append(bp("Adresse : ____________________________________"))
    story.append(sp(6))
    story.append(bp("<b>2. Caractéristiques du prêt</b>"))
    story.append(bp("Numéro de dossier interne : ____________________________________"))
    story.append(bp("Montant principal : ________________________________ $ CAD"))
    story.append(bp("Date du prêt : ____________________________________"))
    story.append(bp("Date d'échéance : ____________________________________"))
    story.append(bp("Taux d'intérêt : ________ % par année"))
    story.append(bp("Type de prêt : ____________________________________"))
    story.append(sp(6))
    story.append(bp("<b>3. Acte hypothécaire immobilier</b>"))
    story.append(bp("Notaire : ____________________________________"))
    story.append(bp("Numéro de minute : ____________________________________"))
    story.append(bp("Date : ____________________________________"))
    story.append(bp("Numéro d'inscription au Registre foncier : ____________________________________"))
    story.append(sp(6))
    story.append(bp("<b>4. Description de l'immeuble en garantie</b>"))
    story.append(bp("Adresse : ____________________________________"))
    story.append(bp("Numéro(s) de lot : ____________________________________"))
    story.append(bp("Cadastre : ____________________________________"))
    story.append(bp("Circonscription foncière : ____________________________________"))

    return story


# ═══════════════════════════════════════════════════════════════════════════
# VERSION ANGLAISE
# ═══════════════════════════════════════════════════════════════════════════
def build_en():
    story = []

    # ── COVER SOBRE ────────────────────────────────────────────────────────
    story.append(Spacer(1, 80))
    story.append(Paragraph("MOVABLE HYPOTHEC", ST["cover_title"]))
    story.append(Paragraph("ON INDIVIDUAL CLAIM", ST["cover_title"]))
    story.append(Spacer(1, 30))
    t = Table([[""]], colWidths=[3.0*inch], rowHeights=[0.02*inch])
    t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), BLACK)]))
    story.append(t)
    story.append(Spacer(1, 30))
    story.append(Paragraph("BETWEEN", ST["cover_meta"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>CAPITAL NORVEX INC.</b>", ST["cover_sub"]))
    story.append(Paragraph("(Grantor — Hypothecary Debtor)", ST["cover_meta"]))
    story.append(Spacer(1, 14))
    story.append(Paragraph("AND", ST["cover_meta"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>THE PARTNER</b>", ST["cover_sub"]))
    story.append(Paragraph("(Hypothecary Creditor)", ST["cover_meta"]))
    story.append(Spacer(1, 60))
    story.append(Paragraph(
        "Civil Code of Quebec — arts. 2660, 2696-2701, 2710 et seq., 2748 et seq.",
        ST["cover_meta"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Registration at RPMR (Register of Personal and Movable Real Rights)",
        ST["cover_meta"]))
    story.append(Spacer(1, 60))
    story.append(Paragraph(
        "Date: ____________________________________",
        ST["cover_meta"]))
    story.append(PageBreak())

    # ── IDENTIFICATION ─────────────────────────────────────────────────────
    story += sec("IDENTIFICATION OF THE PARTIES")
    story += art("A.", "Grantor — Hypothecary Debtor")
    story.append(bp(
        "<b>CAPITAL NORVEX INC.</b>, a legal person duly incorporated under the laws of "
        "Quebec, having its head office at 2705-1000 André-Prévost Street, Île-des-Sœurs "
        "(Verdun), Montreal (Quebec) H3E 0G2, hereinafter the « <b>Grantor</b> » or "
        "« <b>Capital Norvex</b> »;"))
    story.append(sp())
    story.append(bp(
        "Represented for the purposes hereof by: ____________________________________ "
        "(full name), acting as ____________________________________ (designated mandatary), "
        "duly authorized by a resolution adopted by the board of directors of Capital Norvex "
        "Inc. on __________________, signed by Mrs. Suzanne Breton, President and sole "
        "shareholder, a copy of which is attached hereto (Schedule A — Corporate Resolution)."))
    story.append(sp())
    story += art("B.", "Hypothecary Creditor — Partner")
    story.append(bp(
        "____________________________________ (corporate name or full name), "
        "____________________________________ (legal form: corporation / individual / other), "
        "having its registered office or residing at "
        "____________________________________, hereinafter the « <b>Hypothecary Creditor</b> » "
        "or the « <b>Partner</b> »."))
    story.append(sp())
    story.append(bp(
        "Represented for the purposes hereof by: ____________________________________ "
        "(full name), acting as ____________________________________ (title)."))
    story.append(sp(10))

    # Preamble
    story += sec("PREAMBLE")
    story.append(bp(
        "WHEREAS the Partner has granted Capital Norvex financing (hereinafter the "
        "« <b>Partner Financing</b> ») in the amount of "
        "____________________________________ Canadian dollars "
        "(________________________________ CAD), pursuant to a <b>Partnership Agreement</b> "
        "signed between the parties (hereinafter the « <b>Partnership Agreement</b> »), for "
        "the purpose of financing by Capital Norvex of a specific loan file granted to a "
        "third-party borrower (hereinafter the « <b>Loan Asset</b> »);"))
    story.append(sp())
    story.append(bp(
        "WHEREAS Capital Norvex in turn lends the funds received from the Partner to a "
        "third-party borrower (hereinafter the « <b>Borrower</b> »), secured by a first-rank "
        "real estate hypothec held by Capital Norvex on the property identified in Schedule "
        "B (hereinafter the « <b>Hypothecary Claim</b> » held by Capital Norvex);"))
    story.append(sp())
    story.append(bp(
        "WHEREAS Capital Norvex wishes to grant the Partner, as security for its obligations "
        "to the Partner under the Partnership Agreement, a <b>movable hypothec on the "
        "individual Hypothecary Claim</b> it holds against the Borrower, pursuant to "
        "articles 2696 to 2701 of the <i>Civil Code of Quebec</i>;"))
    story.append(sp())
    story.append(bp(
        "WHEREAS this movable hypothec covers <b>ONLY</b> the specific hypothecary claim "
        "relating to this Loan Asset, and <b>NOT the universality</b> of Capital Norvex's "
        "claims against its other clients;"))
    story.append(sp())
    story.append(bp("NOW THEREFORE, the parties agree as follows:"))
    story.append(sp())

    # 1
    story += sec("1. CONSTITUTION OF THE MOVABLE HYPOTHEC")
    story += art("1.1", "Constitution")
    story.append(bp(
        "The Grantor hereby <b>HYPOTHECATES</b> in favour of the Hypothecary Creditor, as "
        "security for the payment and performance of the Secured Obligations (as defined in "
        "Article 2.1), <b>the individual Hypothecary Claim</b> it holds against the Borrower, "
        "as described in Article 3 and Schedule B hereof."))
    story.append(sp())
    story += art("1.2", "Nature of the Hypothec")
    story.append(bp(
        "This hypothec is granted pursuant to articles 2660, 2696 to 2701, and 2710 et seq. "
        "of the <i>Civil Code of Quebec</i>. It is a <b>conventional movable hypothec on an "
        "individual claim</b>, duly published at the Register of Personal and Movable Real "
        "Rights (RPMR) in accordance with article 2710 of the <i>Civil Code of Quebec</i>."))
    story.append(sp())
    story += art("1.3", "Scope Limited to the Individual Claim")
    story.append(bp(
        "The parties expressly acknowledge that this hypothec <b>covers only the individual "
        "Hypothecary Claim</b> detailed in Schedule B, expressly excluding any other claim, "
        "present or future, held by Capital Norvex against its other clients or borrowers. "
        "This hypothec <b>is not a hypothec on a universality</b> within the meaning of "
        "articles 2666 to 2674 of the <i>Civil Code of Quebec</i>."))
    story.append(sp())

    # 2
    story += sec("2. SECURED OBLIGATIONS AND AMOUNT")
    story += art("2.1", "Secured Obligations")
    story.append(bp(
        "This hypothec secures the full performance by Capital Norvex of all its obligations "
        "to the Partner under the Partnership Agreement and hereunder (hereinafter the "
        "« <b>Secured Obligations</b> »), including notably:"))
    story += blt([
        "Full repayment of the principal of the Partner Financing, namely ____________________________________ Canadian dollars (________________________________ CAD);",
        "Payment of Interest (or Monthly Payments, as applicable under the Partnership Agreement) calculated at ________ % per year;",
        "Payment of all fees, accessories, damages, interest and indemnities provided herein or under the Partnership Agreement;",
        "Compliance with the transparency, good-faith and joint-management commitments under the Partnership Agreement;",
        "Compliance with discharge obligations at RPMR upon maturity.",
    ])
    story.append(sp())
    story += art("2.2", "Secured Amount — Article 2689 C.C.Q.")
    story.append(bp(
        "For the purposes of registration at the RPMR, the total amount secured by this "
        "hypothec is set at <b>one hundred twenty percent (120 %)</b> of the Partner "
        "Financing amount, namely ____________________________________ Canadian dollars "
        "(________________________________ CAD), to cover principal, interest, fees and "
        "accessories."))
    story.append(sp())

    # 3
    story += sec("3. DESCRIPTION OF THE HYPOTHECATED CLAIM")
    story += art("3.1", "Precise Identification of the Hypothecary Claim")
    story.append(bp(
        "The individual Hypothecary Claim hypothecated hereby is the one detailed in "
        "<b>Schedule B</b>, which includes notably:"))
    story += blt([
        "<b>Borrower's Identity:</b> ____________________________________",
        "<b>Internal File Number:</b> ____________________________________",
        "<b>Principal Loan Amount:</b> ________________________________ CAD",
        "<b>Date of Loan:</b> ____________________________________",
        "<b>Maturity Date:</b> ____________________________________",
        "<b>Interest Rate:</b> ________ % per year",
        "<b>Real Estate Hypothec Deed (minute number, notary, registration date):</b> ____________________________________",
        "<b>Quebec Land Register Inscription Number:</b> ____________________________________",
        "<b>Description of the Property as Security:</b> ____________________________________",
    ])
    story.append(sp())
    story += art("3.2", "Scope of the Hypothecated Claim")
    story.append(bp(
        "The hypothec covers the Hypothecary Claim in its entirety, including:"))
    story += blt([
        "The principal of the loan granted to the Borrower;",
        "All present and future interest accrued on such principal;",
        "All fees, accessories, indemnities and penalties payable by the Borrower;",
        "All rights, remedies, accessory securities and additional guarantees granted by the Borrower (sureties, share pledges, accessory movable hypothecs, assignments of rents and insurance policies, etc.);",
        "All proceeds, insurance indemnities, expropriation indemnities and other amounts received by Capital Norvex in connection with this claim.",
    ])
    story.append(sp())

    # 4
    story += sec("4. REGISTRATION AT THE RPMR")
    story += art("4.1", "Mandatory Registration")
    story.append(bp(
        "This movable hypothec shall be registered at the <b>Register of Personal and "
        "Movable Real Rights (RPMR)</b> pursuant to articles 2710 et seq. of the <i>Civil "
        "Code of Quebec</i>, as soon as possible and no later than concurrently with the "
        "first disbursement of the Partner Financing to Capital Norvex."))
    story.append(sp())
    story += art("4.2", "Registration and Discharge Fees")
    story.append(bp(
        "All fees relating to the initial registration at the RPMR, as well as any "
        "subsequent modification or discharge, are <b>borne exclusively by Capital Norvex</b>."))
    story.append(sp())
    story += art("4.3", "Renewal of Registration")
    story.append(bp(
        "Capital Norvex undertakes, at its expense, to renew the RPMR registration before "
        "its expiry, in accordance with article 2798 of the <i>Civil Code of Quebec</i>, for "
        "as long as the Secured Obligations are not fully extinguished."))
    story.append(sp())

    # 5
    story += sec("5. GRANTOR'S COMMITMENTS — ABSOLUTE TRANSPARENCY")
    story += art("5.1", "Transparency and Reporting")
    story.append(bp(
        "Capital Norvex undertakes to the Partner to maintain <b>absolute transparency</b> "
        "concerning the Hypothecated Claim throughout the duration of this hypothec, notably by:"))
    story += blt([
        "Maintaining a separate and identified bank account for the funds related to the relevant Loan Asset;",
        "Providing the Partner with <b>24/7 access</b> to the secure <b>Partner Portal</b> (PWA — Progressive Web Application) allowing real-time review of all information relating to the Loan Asset and the Hypothecated Claim;",
        "For construction and infrastructure loans, providing the Partner with access to the <b>Norvex Track™</b> module, through which the Partner <b>personally authorizes and executes each progressive Disbursement</b> 24 hours a day, 7 days a week, thereby ensuring operational control over the funds;",
        "Providing the Partner with a complete monthly report on the status of the Loan Asset, claim balance, payments received from the Borrower and any material event;",
        "Notifying the Partner <b>in writing within five (5) business days</b> of any Borrower Default Event or any event likely to affect the value of the Hypothecated Claim;",
        "Making available to the Partner, upon reasonable request, copies of any document of the Borrower's file (hypothec deed, appraisals, insurance policies, account statements, etc.).",
    ])
    story.append(sp())
    story += art("5.2", "Preservation and Defence of the Hypothecated Claim")
    story.append(bp(
        "Capital Norvex undertakes to <b>preserve, defend and enforce</b> the Hypothecated "
        "Claim with the diligence of an administrator of the property of others, in accordance "
        "with articles 1309 et seq. of the <i>Civil Code of Quebec</i>. Capital Norvex shall "
        "not, without the Partner's written consent:"))
    story += blt([
        "Renounce the Hypothecated Claim or any significant part thereof;",
        "Consent to a total or partial release of the Borrower's debt;",
        "Voluntarily subordinate its hypothecary rank to another creditor;",
        "Substantially amend the conditions of the Hypothecated Claim (maturity, rate, accessory securities) to the detriment of the Partner.",
    ])
    story.append(sp())
    story += art("5.3", "Joint Management in Case of Borrower Default")
    story.append(bp(
        "Upon a Borrower Default Event, Capital Norvex and the Partner <b>work in active "
        "partnership</b> to determine the best protection and recovery strategy, in accordance "
        "with the Partnership Agreement. Major strategic decisions (taking in payment, "
        "court-supervised sale, selection of real estate broker, conclusion of a settlement) "
        "are taken <b>jointly</b> by the parties."))
    story.append(sp())
    story += art("5.4", "Legal Fees of Realization")
    story.append(bp(
        "All legal fees, lawyers' fees, notary fees, Receiver fees and other costs incurred "
        "by Capital Norvex in recovery or Repossession proceedings are <b>borne exclusively "
        "by Capital Norvex</b>, and are collected as first priority from Sale Proceeds before "
        "any distribution. The Partner bears no additional cost beyond its initial Contribution."))
    story.append(sp())
    story += art("5.5", "Continuing Information and Cooperation")
    story.append(bp(
        "Capital Norvex undertakes to immediately inform the Partner of any event, notice or "
        "proceeding likely to affect the Hypothecated Claim, including: notice of "
        "court-supervised sale by another creditor, garnishment, insolvency proceeding "
        "against the Borrower, contestation of the real estate hypothec, loss or expropriation."))
    story.append(sp())

    # 6
    story += sec("6. EVENTS OF DEFAULT OF CAPITAL NORVEX")
    story.append(bp(
        "The following constitute Events of Default of Capital Norvex hereunder:"))
    story += blt([
        "<b>Non-payment</b> of any sum owed to the Partner under the Partnership Agreement or hereunder, not remedied within thirty (30) days of a written notice from the Partner;",
        "<b>Material breach</b> of the transparency commitments under Article 5 (notably persistent refusal to provide secure portal access, refusal to send monthly reports, or refusal to notify a Borrower default), not remedied within thirty (30) days of a written notice;",
        "<b>Documented fraud</b> or misappropriation of funds by Capital Norvex, its directors or employees, in connection with the Loan Asset;",
        "<b>Insolvency</b>, bankruptcy, filing for creditor protection, proposal or appointment of a receiver against Capital Norvex;",
        "<b>Unauthorized alienation</b> of the Hypothecated Claim or the first-rank real estate hypothec;",
        "<b>Unauthorized voluntary subordination</b> of Capital Norvex's hypothecary rank to the Partner's detriment;",
        "<b>Material breach</b> of the Partnership Agreement, not remedied within thirty (30) days of a written notice, save in case of manifest urgency endangering the Contribution.",
    ])
    story.append(sp())

    # 7
    story += sec("7. REMEDIES OF THE HYPOTHECARY CREDITOR")
    story += art("7.1", "Hypothecary Remedies — Articles 2748 et seq. C.C.Q.")
    story.append(bp(
        "Should an Event of Default of Capital Norvex remain unremedied within the periods "
        "provided, the Partner may, after complying with the mediation procedure under "
        "Article 9 hereof (save manifest urgency), exercise all hypothecary remedies provided "
        "by articles 2748 et seq. of the <i>Civil Code of Quebec</i>, notably:"))
    story += blt([
        "<b>Taking in payment</b> of the Hypothecated Claim (arts. 2778 et seq. C.C.Q.) — the Partner becomes the holder of the Hypothecary Claim held by Capital Norvex against the Borrower;",
        "<b>Assignment of the Hypothecated Claim</b> (arts. 2710 et seq. C.C.Q.) — the Partner may assign or directly recover the claim from the Borrower;",
        "<b>Sale by the creditor</b> or court-supervised sale of the Hypothecated Claim;",
        "<b>Direct collection</b> of payments from the Borrower, in accordance with articles 2743 et seq. C.C.Q.;",
        "Any other remedy provided by law.",
    ])
    story.append(sp())
    story += art("7.2", "Subrogation of the Partner")
    story.append(bp(
        "Once one of the above remedies has been successfully exercised, the Partner is "
        "<b>subrogated</b> in the rights of Capital Norvex against the Borrower, including "
        "the benefit of the first-rank real estate hypothec on the property. Capital Norvex "
        "undertakes to sign all documents required to perfect such subrogation and to "
        "transfer the entire file to the Partner."))
    story.append(sp())
    story += art("7.3", "Cumulation of Remedies")
    story.append(bp(
        "The hypothecary remedies provided herein are cumulative and non-exclusive. The "
        "Partner may exercise any remedy, judicial or extrajudicial, for the realization of "
        "the Hypothecated Claim and the reparation of the prejudice suffered."))
    story.append(sp())

    # 8
    story += sec("8. DISCHARGE UPON EXTINCTION OF OBLIGATIONS")
    story += art("8.1", "Mandatory Discharge")
    story.append(bp(
        "Upon full extinction of the Secured Obligations (full repayment of principal, "
        "interest and fees), the Partner undertakes to <b>release</b> and authorize the "
        "<b>discharge</b> of this movable hypothec at the RPMR within ten (10) business days "
        "following receipt of written confirmation from Capital Norvex and all amounts owed."))
    story.append(sp())
    story += art("8.2", "Discharge Fees")
    story.append(bp(
        "RPMR discharge fees are borne exclusively by Capital Norvex."))
    story.append(sp())

    # 9
    story += sec("9. MANDATORY MEDIATION BEFORE JUDICIAL RECOURSE")
    story.append(bp(
        "Before initiating any judicial recourse hereunder (excluding extrajudicial hypothecary "
        "remedies and urgent conservatory measures), the parties undertake to attempt to "
        "resolve any dispute by <b>mediation</b>, in accordance with the procedure provided "
        "in the Partnership Agreement. This mediation clause is <b>indissociable</b> from the "
        "one provided in the Partnership Agreement and applies <i>mutatis mutandis</i> to "
        "disputes arising from this hypothec."))
    story.append(sp())

    # 10
    story += sec("10. INDISSOCIABILITY WITH THE PARTNERSHIP AGREEMENT")
    story.append(bp(
        "This movable hypothec and the Partnership Agreement entered into between the parties "
        "form <b>an indissociable contractual whole</b>. The two documents shall be read, "
        "interpreted and performed jointly and in a complementary manner. Any clause, "
        "condition or obligation set out in the Partnership Agreement applies fully to the "
        "parties hereto, and any breach of the terms of the Partnership Agreement automatically "
        "constitutes an Event of Default within the meaning of Article 6 hereof. In the event "
        "of any divergence or ambiguity between the two documents, the <b>interpretation most "
        "protective of the Partner</b> (as hypothecary creditor) shall prevail."))
    story.append(sp())

    # 11
    story += sec("11. GOOD FAITH AND COLLABORATION")
    story.append(bp(
        "The parties undertake to perform this hypothec <b>in good faith</b>, in accordance "
        "with articles 6, 7 and 1375 of the <i>Civil Code of Quebec</i>, in a spirit of "
        "collaboration, transparency and mutual respect. No party may invoke a breach by the "
        "other without first having attempted to resolve the situation in good faith through "
        "direct communication and, as the case may be, through the mediation procedure under "
        "Article 9."))
    story.append(sp())

    # 12
    story += sec("12. GENERAL PROVISIONS")
    story += art("12.1", "Governing Law")
    story.append(bp(
        "This hypothec is governed by and shall be interpreted in accordance with the <b>laws "
        "of the Province of Quebec and the federal laws of Canada applicable</b>. Any dispute "
        "falls under the exclusive jurisdiction of the courts of the judicial district of "
        "Montreal, subject to Article 9 (Mandatory Mediation)."))
    story.append(sp())
    story += art("12.2", "Amendments, Notices and Assignment")
    story += blt([
        "<b>Amendments:</b> Any modification must be in writing, signed by both parties and registered at the RPMR if required.",
        "<b>Notices:</b> Any notice shall be given in writing, by email with acknowledgment of receipt or by registered mail.",
        "<b>Assignment by the Partner:</b> The Partner may assign its rights with Capital Norvex's written consent, which shall not be unreasonably withheld.",
    ])
    story.append(sp())
    story += art("12.3", "Severability, Entire Agreement and Waiver")
    story += blt([
        "<b>Severability:</b> Any invalid clause does not affect the validity of the remainder of this hypothec.",
        "<b>Entire Agreement:</b> This hypothec, together with its Schedules and the Partnership Agreement, constitutes the entire agreement of the parties relating to the Hypothecated Claim.",
        "<b>Waiver:</b> No tolerance or delay in exercising a right constitutes a permanent waiver of that right.",
    ])
    story.append(sp())
    story += art("12.4", "Official Language")
    story.append(bp(
        "This hypothec is also available in French. <b>In case of divergence, the French "
        "version prevails in Quebec.</b>"))
    story.append(sp())

    # 13 SIGNATURES
    story += sec("13. SIGNATURES")
    story.append(sp(4))
    story.append(bp(
        "IN WITNESS WHEREOF, the parties have signed this <b>Movable Hypothec on Individual "
        "Claim</b> on the date indicated below, having read it in full and obtained such "
        "legal advice as they deemed appropriate. This hypothec shall be registered at the "
        "RPMR as soon as possible following its signature."))
    story.append(sp(14))

    story.append(section_banner("CAPITAL NORVEX INC. — GRANTOR (HYPOTHECARY DEBTOR)"))
    story.append(sp(8))
    story.append(sign_pair("Authorized Representative:", "Title:"))
    story.append(sign_pair("Date:", "Signature:"))
    story.append(sp(8))
    story.append(bp(
        "<i>Designated representative pursuant to the corporate resolution attached hereto "
        "(Schedule A), signed by Mrs. Suzanne Breton, President and sole shareholder of "
        "Capital Norvex Inc.</i>"))
    story.append(sp(20))

    story.append(section_banner("PARTNER — HYPOTHECARY CREDITOR"))
    story.append(sp(8))
    story.append(sign_pair("Corporate name or name:", "Authorized Representative:"))
    story.append(sign_pair("Title:", "Date:"))
    story.append(sp(14))
    story.append(Paragraph("Signature:", ST["sign_lbl"]))
    story.append(sp(20))
    story.append(Paragraph(
        "<i>Movable hypothec on individual claim granted pursuant to articles 2660, 2696-2701 "
        "and 2710 et seq. of the Civil Code of Quebec. Mandatory registration at the RPMR "
        "before the first disbursement.</i>", ST["confidential"]))

    # SCHEDULES
    story.append(PageBreak())
    story += sec("SCHEDULE A — CORPORATE RESOLUTION OF CAPITAL NORVEX INC.")
    story.append(bp(
        "<i>Insert here a certified copy of the resolution adopted by the board of directors "
        "of Capital Norvex Inc., signed by Mrs. Suzanne Breton, President and sole shareholder, "
        "authorizing the designated mandatary to sign this movable hypothec in the name and "
        "on behalf of Capital Norvex Inc.</i>"))
    story.append(sp(20))

    story += sec("SCHEDULE B — DETAILED DESCRIPTION OF THE HYPOTHECATED CLAIM")
    story.append(bp("<b>1. Borrower Identification</b>"))
    story.append(bp("Name / Corporate name: ____________________________________"))
    story.append(bp("NEQ or other identifier: ____________________________________"))
    story.append(bp("Address: ____________________________________"))
    story.append(sp(6))
    story.append(bp("<b>2. Loan Characteristics</b>"))
    story.append(bp("Internal File Number: ____________________________________"))
    story.append(bp("Principal Amount: ________________________________ CAD"))
    story.append(bp("Date of Loan: ____________________________________"))
    story.append(bp("Maturity Date: ____________________________________"))
    story.append(bp("Interest Rate: ________ % per year"))
    story.append(bp("Type of Loan: ____________________________________"))
    story.append(sp(6))
    story.append(bp("<b>3. Real Estate Hypothec Deed</b>"))
    story.append(bp("Notary: ____________________________________"))
    story.append(bp("Minute Number: ____________________________________"))
    story.append(bp("Date: ____________________________________"))
    story.append(bp("Land Register Inscription Number: ____________________________________"))
    story.append(sp(6))
    story.append(bp("<b>4. Description of the Property as Security</b>"))
    story.append(bp("Address: ____________________________________"))
    story.append(bp("Lot Number(s): ____________________________________"))
    story.append(bp("Cadastre: ____________________________________"))
    story.append(bp("Registration Division: ____________________________________"))

    return story


# ═══════════════════════════════════════════════════════════════════════════
# GENERATION
# ═══════════════════════════════════════════════════════════════════════════
OUT_DIR = "/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres"

def generate_fr():
    out = f"{OUT_DIR}/Hypotheque_Mobiliere_Creance_Individuelle_FR.pdf"
    doc = SimpleDocTemplate(
        out, pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )
    on_page = make_on_page(
        title_top="HYPOTHÈQUE MOBILIÈRE SUR CRÉANCE INDIVIDUELLE",
        page_label_fr=True,
    )
    doc.build(build_fr(), onFirstPage=on_page, onLaterPages=on_page)
    print(f"✅  PDF généré : {out}")

def generate_en():
    out = f"{OUT_DIR}/Movable_Hypothec_Individual_Claim_EN.pdf"
    doc = SimpleDocTemplate(
        out, pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )
    on_page = make_on_page(
        title_top="MOVABLE HYPOTHEC ON INDIVIDUAL CLAIM",
        page_label_fr=False,
    )
    doc.build(build_en(), onFirstPage=on_page, onLaterPages=on_page)
    print(f"✅  PDF generated: {out}")

if __name__ == "__main__":
    generate_fr()
    generate_en()
