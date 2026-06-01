#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
12_convention_pret_refinancement.py
Convention de prêt — REFINANCEMENT — Capital Norvex Inc.
Génère 2 PDFs : Convention_Pret_Refinancement_CapitalNorvex.pdf (FR)
              Loan_Agreement_Refinancing_CapitalNorvex_EN.pdf (EN)

Indissociable avec l'acte d'hypothèque Refinancement (clause fondamentale).
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.units import inch
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                                 Table, TableStyle, Image as RLImage)
import os

DARK   = HexColor("#0F1419")
GOLD   = HexColor("#C9A961")
GOLD2  = HexColor("#b8975a")
CREAM  = HexColor("#F4ECD8")
GREY_LT = HexColor("#A6A6A6")
GREY_MED= HexColor("#808080")
WHITE  = white

PAGE_W, PAGE_H = letter
MARGIN = 0.75 * inch

EMBLEM_PATH = "/Users/yvesbarrette/Desktop/capitalnorvex-site/CapitalNorvex_Scripts/scripts/emblem_header.png"
COVER_PATH  = "/Users/yvesbarrette/Desktop/capitalnorvex-site/CapitalNorvex_Scripts/scripts/logo_cover.png"


def make_on_page(product_tag):
    def on_page(canvas, doc):
        canvas.saveState()
        w, h = letter
        canvas.setFillColor(DARK)
        canvas.rect(0, h - 54, w, 54, fill=1, stroke=0)
        canvas.setFillColor(GOLD)
        canvas.rect(0, h - 56, w, 1.5, fill=1, stroke=0)
        if os.path.exists(EMBLEM_PATH):
            canvas.drawImage(EMBLEM_PATH, MARGIN, h - 47, width=38, height=42,
                             preserveAspectRatio=True, mask='auto')
        canvas.setFillColor(GOLD)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(MARGIN + 50, h - 30, "CAPITAL NORVEX")
        canvas.setFillColor(GREY_LT)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(MARGIN + 50, h - 43, "Financement Privé Institutionnel  |  Québec & Ontario")
        canvas.setFillColor(GOLD)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.drawRightString(w - MARGIN, h - 28, "CONVENTION DE PRÊT")
        canvas.setFillColor(GREY_LT)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawRightString(w - MARGIN, h - 42, product_tag)
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(w - MARGIN, h - 52, f"p. {doc.page}")

        # Footer
        canvas.setFillColor(DARK)
        canvas.rect(0, 0, w, 50, fill=1, stroke=0)
        canvas.setFillColor(GOLD)
        canvas.rect(0, 50, w, 1.5, fill=1, stroke=0)
        canvas.setFillColor(GOLD2)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.drawCentredString(w/2, 32, "CAPITAL NORVEX  ·  Confidentiel – Usage exclusif des parties signataires")
        canvas.setFillColor(GREY_LT)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(w/2, 14, "2705-1000 André-Prévost  ·  Île-des-Sœurs (Verdun)  ·  Montréal, QC H3E 0G2   |   1-(438)-533-PRET (7738)   |   info@capitalnorvex.com   |   capitalnorvex.com")
        canvas.restoreState()
    return on_page


def build_styles():
    return {
        "title":   ParagraphStyle("title",   fontName="Helvetica-Bold", fontSize=18, textColor=DARK,    alignment=TA_CENTER, spaceAfter=6, leading=24),
        "section": ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=11, textColor=GOLD,    spaceBefore=14, spaceAfter=6, leading=15),
        "art":     ParagraphStyle("art",     fontName="Helvetica-Bold", fontSize=9.5, textColor=DARK,    spaceBefore=8, spaceAfter=3, leading=13),
        "body":    ParagraphStyle("body",    fontName="Helvetica",      fontSize=9,   textColor=DARK,    alignment=TA_JUSTIFY, spaceAfter=4, leading=12.5),
        "bullet":  ParagraphStyle("bullet",  fontName="Helvetica",      fontSize=9,   textColor=DARK,    leftIndent=14, spaceAfter=3, leading=12.5),
        "field_label": ParagraphStyle("fl",  fontName="Helvetica",      fontSize=9,   textColor=DARK),
        "field_line":  ParagraphStyle("fln", fontName="Helvetica",      fontSize=9,   textColor=GREY_MED, leading=14),
    }


def section(title, st):
    rows = [[Paragraph(title, ParagraphStyle("ST", fontName="Helvetica-Bold", fontSize=10,
                                              textColor=WHITE, alignment=TA_LEFT))]]
    tbl = Table(rows, colWidths=[PAGE_W - 2*MARGIN])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), DARK),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LINEBELOW", (0,-1), (-1,-1), 2, GOLD),
    ]))
    return [tbl, Spacer(1, 6)]


def art(num, title, st):
    return Paragraph(f"<b>{num}  {title}</b>", st["art"])


def body(text, st):
    return Paragraph(text, st["body"])


def bullets(items, st):
    return [Paragraph(f"•  {it}", st["bullet"]) for it in items]


# ─── CONTENU FR ──────────────────────────────────────────────────────────────
def build_fr(story, st):
    # Cover
    if os.path.exists(COVER_PATH):
        story.append(Spacer(1, 24))
        story.append(RLImage(COVER_PATH, width=120, height=130))
        story.append(Spacer(1, 8))
    story.append(Paragraph("CAPITAL NORVEX", st["title"]))
    story.append(Paragraph("Financement Privé Institutionnel  |  Québec & Ontario",
                            ParagraphStyle("sub", fontName="Helvetica", fontSize=10, textColor=GOLD2, alignment=TA_CENTER, spaceAfter=8)))
    story.append(Spacer(1, 12))
    cover_tbl = Table([[Paragraph("CONVENTION DE PRÊT — REFINANCEMENT IMMOBILIER<br/>Co-financement avec hypothèque immobilière de premier rang",
                                  ParagraphStyle("ct", fontName="Helvetica-Bold", fontSize=14, textColor=GOLD, alignment=TA_CENTER, leading=18))]],
                     colWidths=[PAGE_W - 2*MARGIN - 20])
    cover_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), DARK),
        ("TOPPADDING", (0,0), (-1,-1), 18),
        ("BOTTOMPADDING", (0,0), (-1,-1), 18),
        ("LINEBELOW", (0,-1), (-1,-1), 3, GOLD),
    ]))
    story.append(cover_tbl)
    story.append(Spacer(1, 18))
    story.append(Paragraph("<i>Capital structuré. Ambition maîtrisée.</i>",
                            ParagraphStyle("slogan", fontName="Helvetica-Oblique", fontSize=10, textColor=GOLD2, alignment=TA_CENTER, spaceAfter=4)))
    story.append(Paragraph("CONFIDENTIEL — Réservé aux parties signataires et à leurs conseillers juridiques",
                            ParagraphStyle("conf", fontName="Helvetica", fontSize=8, textColor=HexColor("#7a3a3a"), alignment=TA_CENTER)))
    story.append(PageBreak())

    # Article 1
    story += section("1.  PARTIES", st)
    story.append(art("1.1", "Prêteur", st))
    story.append(body(
        "<b>CAPITAL NORVEX INC.</b>, personne morale légalement constituée en vertu des lois du Québec, "
        "ayant son siège social au 2705-1000, rue André-Prévost, Île-des-Sœurs (Verdun), Montréal (Québec) "
        "H3E 0G2 (« Capital Norvex » ou le « Prêteur »).", st))
    story.append(body(
        "Pour les fins des présentes, Capital Norvex Inc. est représentée par un mandataire désigné, "
        "dûment autorisé en vertu d'une <b>résolution corporative</b> adoptée par l'actionnaire unique "
        "et présidente, <b>Madame Suzanne Breton</b>, dont copie certifiée conforme est jointe au "
        "dossier.", st))
    story.append(art("1.2", "Emprunteur", st))
    story.append(body("________________________________________________________________________________ "
                       "(l'« Emprunteur »).", st))
    story.append(art("1.3", "Garants", st))
    story.append(body("________________________________________________________________________________ "
                       "(les « Garants », solidaires de l'Emprunteur).", st))

    # Article 2
    story += section("2.  OBJET DU PRÊT — REFINANCEMENT", st)
    story.append(body(
        "Le Prêt a pour objet exclusif le <b>refinancement</b> d'une hypothèque existante sur "
        "l'Immeuble identifié à l'Annexe A, en faveur d'un ancien prêteur (l'« Ancien Prêteur »), "
        "ainsi que, le cas échéant, le déblocage d'une liquidité additionnelle pour un usage "
        "spécifique documenté.", st))
    story.append(art("2.1", "Affectation des fonds", st))
    story += bullets([
        "Remboursement intégral de l'hypothèque existante (Ancien Prêteur)",
        "Frais de dossier, frais notariaux, taxes et frais de publication",
        "Liquidités additionnelles à usage spécifique documenté (capex, amélioration locative, etc.)",
    ], st)
    story.append(body(
        "<b>AUCUN cash-out pur sans plan de remboursement documenté n'est autorisé.</b> Toute "
        "affectation des fonds doit faire l'objet d'une justification écrite acceptable au Prêteur.", st))

    # Article 3
    story += section("3.  CONDITIONS FINANCIÈRES", st)
    fin_data = [
        ["Élément", "Condition"],
        ["Montant du Prêt", "_____________ $ CAD"],
        ["Durée", "12 mois renouvelable"],
        ["Taux d'intérêt fixe", "_____ % par année (calculé et capitalisé mensuellement)"],
        ["Frais de dossier", "3 % à 3,5 % du montant — payables à la signature"],
        ["Frais d'analyse (terme dépassé)", "1 % du capital — si prolongation au-delà de l'échéance (renégociable)"],
        ["Pénalité de remboursement anticipé", "Min. 3 mois d'intérêts"],
        ["Taux de défaut", "_____ % par année"],
    ]
    tbl = Table(fin_data, colWidths=[2.6*inch, 4.0*inch])
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
    ]))
    story.append(tbl)
    story.append(Spacer(1, 6))

    # Article 4
    story += section("4.  RATIOS DE QUALIFICATION (CIBLES — FLEXIBILITÉ AU CAS PAR CAS)", st)
    story.append(body(
        "À titre de critères de base, le Prêt vise les ratios suivants :"
        "<br/>•  Ratio prêt-valeur (LTV) cible de <b>70 %</b> de la valeur AACI"
        "<br/>•  Ratio de couverture de la dette (DCR) cible de <b>1,20x</b>"
        "<br/>•  Équité cash de l'Emprunteur cible d'au moins <b>30 %</b>", st))
    story.append(body(
        "<b>FLEXIBILITÉ ADAPTÉE AU DOSSIER :</b> Ces ratios constituent des critères de base et peuvent "
        "être ajustés au cas par cas, jusqu'à un LTV maximal de <b>quatre-vingt-quinze pour cent (95 %)</b>, "
        "si l'Emprunteur fournit des garanties supplémentaires acceptables au Prêteur (hypothèque "
        "additionnelle, hypothèque de 2e rang sur autre immeuble, caution personnelle solide, dépôt "
        "en fiducie, etc.). L'évaluation et l'acceptation des collatéraux relèvent de la discrétion "
        "exclusive du Prêteur.", st))

    # Article 5
    story += section("5.  STRATÉGIE DE SORTIE — OBLIGATOIRE", st)
    story.append(body(
        "<b>Le refinancement n'est consenti qu'avec une stratégie de sortie claire et documentée.</b> "
        "L'Emprunteur déclare et garantit que sa stratégie de sortie pour le remboursement intégral du "
        "Prêt à la Date d'Échéance est l'une des suivantes :", st))
    story += bullets([
        "Vente de l'Immeuble — promesse d'achat ou mandat de vente confirmé",
        "Refinancement bancaire confirmé — lettre d'engagement ou confirmation préliminaire",
        "Autre stratégie documentée acceptable au Prêteur",
    ], st)
    story.append(body(
        "<b>Le défaut de fournir une stratégie de sortie acceptable et documentée constitue un Événement "
        "de Défaut.</b> L'Emprunteur s'engage à informer immédiatement le Prêteur de toute évolution "
        "affectant la stratégie de sortie et à proposer une stratégie de remplacement acceptable au Prêteur.", st))

    # Article 6
    story += section("6.  CONDITIONS PRÉALABLES AU DÉBOURSEMENT", st)
    story += bullets([
        "Confirmation du premier rang hypothécaire après radiation de l'hypothèque de l'Ancien Prêteur",
        "Lettre de quittance / décharge de l'Ancien Prêteur indiquant le solde exact à rembourser",
        "Évaluation agréée AACI de l'Immeuble, datée de moins de 6 mois",
        "Stratégie de sortie documentée acceptable au Prêteur",
        "Étude environnementale Phase I (le cas échéant) acceptable au Prêteur",
        "Polices d'assurance avec Capital Norvex désigné comme bénéficiaire / assuré additionnel",
        "Résolution corporative de Capital Norvex Inc. désignant le mandataire signataire",
        "Signature de l'acte d'hypothèque et de tout document accessoire requis par le Prêteur",
    ], st)

    # Article 7
    story += section("7.  GARANTIES", st)
    story += bullets([
        "Hypothèque immobilière de 1er rang sur l'Immeuble (après radiation Ancien Prêteur)",
        "Cession totale et immédiate de loyers (art. 2695 C.c.Q.)",
        "Cautionnement personnel solidaire, irrévocable et illimité des Garants",
        "Quittance et mainlevée d'hypothèque de l'Ancien Prêteur (OBLIGATOIRE)",
        "Toute garantie supplémentaire acceptable au Prêteur le cas échéant (collatéraux pour LTV > 70 %)",
    ], st)

    # Article 8
    story += section("8.  CESSION DES CONTRATS, PLANS, PERMIS — LE CAS ÉCHÉANT", st)
    story.append(body(
        "Pour tout dossier comportant une composante de construction ou de rénovation majeure, "
        "l'Emprunteur cède au Prêteur tous les contrats avec l'entrepreneur général et les sous-traitants "
        "principaux, les plans, devis et autres documents techniques, les permis municipaux, les "
        "soumissions, certificats et garanties, ainsi que toutes les polices d'assurance liées au Projet. "
        "Ces cessions deviennent exécutoires de plein droit lors d'un Événement de Défaut.", st))

    # Article 9
    story += section("9.  TOLÉRANCE ZÉRO — TAXES ET HYPOTHÈQUES LÉGALES", st)
    story.append(art("9.1", "Hypothèques légales de la construction", st))
    story.append(body(
        "<b>AUCUNE</b> hypothèque légale de la construction (art. 2724 et 2726 C.c.Q.) n'est tolérée. "
        "L'Emprunteur s'engage à régler ou à faire radier toute hypothèque légale enregistrée "
        "<b>immédiatement</b>, et au plus tard dans les <b>sept (7) jours</b> d'un avis écrit du Prêteur. "
        "À défaut, un Événement de Défaut sera <b>automatiquement déclaré</b>.", st))
    story.append(art("9.2", "Taxes, charges et obligations courantes", st))
    story.append(body(
        "L'Emprunteur s'engage à payer ponctuellement à leur échéance toutes les taxes foncières, "
        "taxes scolaires, charges municipales, primes d'assurance et autres obligations courantes affectant "
        "l'Immeuble. <b>AUCUN</b> retard n'est toléré. En cas de retard, l'Emprunteur s'engage à "
        "régulariser la situation <b>immédiatement</b>, et au plus tard dans les <b>sept (7) jours</b> "
        "d'un avis écrit du Prêteur. À défaut, un Événement de Défaut sera "
        "<b>automatiquement déclaré</b>.", st))

    # Article 10
    story += section("10.  ÉVÉNEMENTS DE DÉFAUT", st)
    story.append(body("Constituent des Événements de Défaut, sans préavis ni mise en demeure préalable autre que ceux prévus par la loi :", st))
    story += bullets([
        "Tout défaut de paiement à son échéance",
        "Le défaut de fournir ou de maintenir une stratégie de sortie acceptable et documentée",
        "Toute fausse déclaration substantielle de l'Emprunteur, notamment quant à l'affectation des fonds",
        "L'usage des fonds à des fins autres que celles déclarées (cash-out non autorisé)",
        "La détérioration matérielle des ratios LTV ou DCR sous les seuils convenus",
        "L'enregistrement de toute hypothèque légale de la construction non radiée dans les 7 jours d'un avis du Prêteur (tolérance zéro — art. 9.1)",
        "Tout retard de paiement de taxes, charges, assurances ou autres obligations courantes non régularisé dans les 7 jours d'un avis du Prêteur (tolérance zéro — art. 9.2)",
        "L'aliénation ou modification substantielle de l'Immeuble sans autorisation écrite préalable",
        "L'insolvabilité, la faillite ou la mise sous séquestre de l'Emprunteur",
        "Le manquement aux termes de l'acte d'hypothèque (clause d'indissociabilité — art. 13)",
    ], st)

    # Article 11
    story += section("11.  RECOURS DU PRÊTEUR", st)
    story.append(body(
        "Lors d'un Événement de Défaut, le Prêteur peut, à son entière discrétion : "
        "(i) déclarer le Prêt immédiatement exigible; "
        "(ii) faire valoir tous les recours hypothécaires (art. 2748 et s. C.c.Q.), incluant la prise en "
        "paiement, la vente sous contrôle de justice et la vente par le créancier; "
        "(iii) percevoir directement les loyers en vertu de la cession; "
        "(iv) faire exécuter les cautionnements; "
        "(v) cumuler les recours.", st))

    # Article 12
    story += section("12.  REMBOURSEMENT", st)
    story.append(art("12.1", "Échéance", st))
    story.append(body(
        "L'intégralité du solde en capital, des intérêts capitalisés et des frais sera remboursée au plus "
        "tard à la Date d'Échéance, soit le ____________________________.", st))
    story.append(art("12.2", "Remboursement anticipé", st))
    story.append(body(
        "L'Emprunteur peut rembourser le Prêt en tout ou en partie sans pénalité, moyennant cinq (5) "
        "jours ouvrables de préavis écrit, sous réserve des frais de sortie applicables (min. 3 mois "
        "d'intérêts).", st))
    story.append(art("12.3", "Renouvellement", st))
    story.append(body(
        "Le Prêteur peut, à sa seule discrétion, accepter de renouveler le Prêt aux conditions "
        "financières alors en vigueur, sous réserve d'une nouvelle évaluation de l'Immeuble, du respect "
        "continu des ratios de l'article 4 et du paiement des frais d'analyse (article 3) si applicables.", st))

    # Article 12.bis — PORTAIL EMPRUNTEUR (PWA)
    story += section("12.bis  PORTAIL EMPRUNTEUR (PWA) — TRANSPARENCE 24 H/7 JOURS", st)
    story.append(body(
        "Capital Norvex met à la disposition de l'Emprunteur un <b>Portail Emprunteur</b> "
        "numérique sécurisé (<b>PWA — Progressive Web Application</b>), accessible "
        "<b>24 heures sur 24, 7 jours sur 7</b>, depuis tout appareil (téléphone intelligent, "
        "tablette, ordinateur). L'Emprunteur peut y consulter en temps réel :", st))
    story += bullets([
        "Le solde du Prêt, le capital remboursé et les intérêts capitalisés;",
        "L'échéancier des paiements et l'historique des paiements effectués;",
        "Le statut du remboursement de l'Ancien Prêteur et de la radiation hypothécaire;",
        "Les avis et communications officiels transmis par Capital Norvex;",
        "Les documents pertinents au dossier (évaluation, polices d'assurance, quittances).",
    ], st)
    story.append(body(
        "Le Portail Emprunteur (PWA) constitue un outil de <b>transparence</b> mis à la "
        "disposition de l'Emprunteur. Il ne se substitue pas aux communications officielles "
        "écrites prévues à la présente Convention et n'altère en rien les obligations de "
        "l'Emprunteur ni les droits du Prêteur. <b>Lorsque</b> le refinancement comporte un volet "
        "construction ou rénovation majeure au sens de l'article 8, les déboursés progressifs "
        "afférents sont gérés via le module <b>Norvex Track\u2122</b> selon les conditions usuelles "
        "de Capital Norvex.", st))

    # Article 13 — INDISSOCIABILITÉ
    story += section("13.  INDISSOCIABILITÉ — ACTE D'HYPOTHÈQUE — CLAUSE FONDAMENTALE", st)
    story.append(body(
        "<b>La présente Convention de prêt et l'acte d'hypothèque immobilière conclu entre les Parties "
        "forment un ensemble contractuel INDISSOCIABLE et complémentaire.</b> Les Parties reconnaissent "
        "expressément et conviennent irrévocablement que ces deux documents doivent être lus, "
        "interprétés et exécutés conjointement, comme s'ils ne formaient qu'un seul et même contrat. "
        "Tout manquement aux termes de la présente Convention constitue automatiquement un Événement de "
        "Défaut au sens de l'article 10 et permet l'exercice de tous les recours hypothécaires. "
        "En cas de divergence ou d'ambiguïté entre les deux documents, "
        "<b>l'interprétation la plus favorable au Prêteur prévaudra</b>.", st))

    # Article 14
    story += section("14.  DISPOSITIONS GÉNÉRALES", st)
    gen_data = [
        ["Droit applicable", "Lois de la province de Québec (Canada)"],
        ["Compétence judiciaire", "District de Montréal, Québec"],
        ["Cession", "Interdite sans consentement écrit préalable du Prêteur"],
        ["Amendements", "Par écrit, signés des parties"],
        ["LRPCFAT / CANAFE", "Vérifications d'identité et source des fonds effectuées"],
        ["Avis", "Par écrit, courriel certifié ou recommandé"],
        ["Intégralité", "La présente Convention et l'acte d'hypothèque constituent l'entente complète"],
    ]
    tbl = Table(gen_data, colWidths=[2.0*inch, 4.6*inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), DARK),
        ("TEXTCOLOR", (0,0), (0,-1), GOLD),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [CREAM, HexColor("#e8e0ce")]),
        ("GRID", (0,0), (-1,-1), 0.5, GREY_LT),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(tbl)

    # Article 15 — Signatures
    story.append(PageBreak())
    story += section("15.  SIGNATURES", st)
    story.append(body(
        "EN FOI DE QUOI, les parties ont signé la présente Convention à la date indiquée ci-dessous, "
        "après en avoir pris connaissance.", st))
    story.append(body(
        "<i>Pour Capital Norvex Inc., la présente Convention est signée par le mandataire désigné "
        "ci-dessous, dûment autorisé en vertu d'une résolution corporative adoptée par l'actionnaire "
        "unique et présidente, Madame Suzanne Breton, dont copie certifiée conforme est jointe au "
        "dossier.</i>", st))
    story.append(Spacer(1, 12))

    for label, fields in [
        ("PRÊTEUR — CAPITAL NORVEX INC.", [
            "Mandataire désigné (nom complet) : ___________________________________",
            "Titre / Qualité : ___________________________________________________",
            "Résolution corporative datée du : __________________________________",
            "Signée par : Madame Suzanne Breton, présidente et actionnaire unique",
            "Date de signature : _________________________________________________",
            "Signature : _________________________________________________________",
        ]),
        ("EMPRUNTEUR", [
            "Dénomination sociale : ______________________________________________",
            "Représentant autorisé : _____________________________________________",
            "Titre : _____________________________________________________________",
            "Date : ______________________________________________________________",
            "Signature : _________________________________________________________",
        ]),
        ("GARANT(S)", [
            "Nom complet : _______________________________________________________",
            "Date : ______________________________________________________________",
            "Signature : _________________________________________________________",
        ]),
    ]:
        rows = [[Paragraph(label, ParagraphStyle("ST", fontName="Helvetica-Bold", fontSize=10,
                                                  textColor=WHITE, alignment=TA_LEFT))]]
        tbl = Table(rows, colWidths=[PAGE_W - 2*MARGIN])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), DARK),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LINEBELOW", (0,-1), (-1,-1), 2, GOLD),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 8))
        for f in fields:
            story.append(Paragraph(f, st["field_line"]))
        story.append(Spacer(1, 14))


# ─── CONTENU EN ──────────────────────────────────────────────────────────────
def build_en(story, st):
    if os.path.exists(COVER_PATH):
        story.append(Spacer(1, 24))
        story.append(RLImage(COVER_PATH, width=120, height=130))
        story.append(Spacer(1, 8))
    story.append(Paragraph("CAPITAL NORVEX", st["title"]))
    story.append(Paragraph("Institutional Private Lending  |  Quebec & Ontario",
                            ParagraphStyle("sub", fontName="Helvetica", fontSize=10, textColor=GOLD2, alignment=TA_CENTER, spaceAfter=8)))
    story.append(Spacer(1, 12))
    cover_tbl = Table([[Paragraph("LOAN AGREEMENT — REAL ESTATE REFINANCING<br/>Co-financing with first-rank real estate mortgage",
                                  ParagraphStyle("ct", fontName="Helvetica-Bold", fontSize=14, textColor=GOLD, alignment=TA_CENTER, leading=18))]],
                     colWidths=[PAGE_W - 2*MARGIN - 20])
    cover_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), DARK),
        ("TOPPADDING", (0,0), (-1,-1), 18),
        ("BOTTOMPADDING", (0,0), (-1,-1), 18),
        ("LINEBELOW", (0,-1), (-1,-1), 3, GOLD),
    ]))
    story.append(cover_tbl)
    story.append(Spacer(1, 18))
    story.append(Paragraph("<i>Structured Capital. Controlled Ambition.</i>",
                            ParagraphStyle("slogan", fontName="Helvetica-Oblique", fontSize=10, textColor=GOLD2, alignment=TA_CENTER, spaceAfter=4)))
    story.append(Paragraph("CONFIDENTIAL — Reserved for signing parties and their legal advisors",
                            ParagraphStyle("conf", fontName="Helvetica", fontSize=8, textColor=HexColor("#7a3a3a"), alignment=TA_CENTER)))
    story.append(PageBreak())

    story += section("1. PARTIES", st)
    story.append(art("1.1", "Lender", st))
    story.append(body(
        "<b>CAPITAL NORVEX INC.</b>, a legal person duly constituted under the laws of Quebec, having "
        "its head office at 2705-1000 André-Prévost Street, Île-des-Sœurs (Verdun), Montreal, Quebec "
        "H3E 0G2 (\"Capital Norvex\" or the \"Lender\").", st))
    story.append(body(
        "For the purposes hereof, Capital Norvex Inc. is represented by a designated representative, "
        "duly authorized pursuant to a <b>corporate resolution</b> adopted by the sole shareholder and "
        "president, <b>Mrs. Suzanne Breton</b>, a certified true copy of which is attached to the file.", st))
    story.append(art("1.2", "Borrower", st))
    story.append(body("________________________________________________________________________________ "
                       "(the \"Borrower\").", st))
    story.append(art("1.3", "Guarantors", st))
    story.append(body("________________________________________________________________________________ "
                       "(the \"Guarantors\", jointly and severally with the Borrower).", st))

    story += section("2. PURPOSE OF THE LOAN — REFINANCING", st)
    story.append(body(
        "The Loan's exclusive purpose is the <b>refinancing</b> of an existing mortgage on the Property "
        "identified in Schedule A, in favour of a former lender (the \"Former Lender\"), and where "
        "applicable, the disbursement of additional liquidity for a documented specific use.", st))
    story.append(art("2.1", "Use of Funds", st))
    story += bullets([
        "Full repayment of the existing mortgage (Former Lender)",
        "File fees, notarial fees, taxes and registration fees",
        "Additional liquidity for documented specific use (capex, tenant improvements, etc.)",
    ], st)
    story.append(body(
        "<b>NO pure cash-out without a documented repayment plan is authorized.</b> Any allocation of "
        "funds must be the subject of written justification acceptable to the Lender.", st))

    story += section("3. FINANCIAL CONDITIONS", st)
    fin_data = [
        ["Item", "Condition"],
        ["Loan Amount", "_____________ CAD"],
        ["Term", "12 months renewable"],
        ["Fixed Interest Rate", "_____% per year (calculated and capitalized monthly)"],
        ["Origination Fee", "3% to 3.5% of amount — payable at signing"],
        ["Analysis Fee (term extension)", "1% of principal — if extension beyond Maturity (renegotiable)"],
        ["Prepayment Penalty", "Min. 3 months interest"],
        ["Default Rate", "_____% per year"],
    ]
    tbl = Table(fin_data, colWidths=[2.6*inch, 4.0*inch])
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
    ]))
    story.append(tbl)
    story.append(Spacer(1, 6))

    story += section("4. QUALIFICATION RATIOS (TARGETS — CASE-BY-CASE FLEXIBILITY)", st)
    story.append(body(
        "As base criteria, the Loan aims for the following ratios:"
        "<br/>•  Target loan-to-value (LTV) ratio of <b>70%</b> of the AACI value"
        "<br/>•  Target debt service coverage ratio (DCR) of <b>1.20x</b>"
        "<br/>•  Target Borrower's cash equity of at least <b>30%</b>", st))
    story.append(body(
        "<b>FILE-BY-FILE FLEXIBILITY:</b> These ratios constitute base criteria and may be adjusted on "
        "a case-by-case basis, up to a maximum LTV of <b>ninety-five percent (95%)</b>, if the Borrower "
        "provides additional collateral acceptable to the Lender (additional mortgage, second-rank "
        "mortgage on another property, solid personal suretyship, deposit in trust, etc.). The "
        "evaluation and acceptance of collateral are at the sole discretion of the Lender.", st))

    story += section("5. EXIT STRATEGY — MANDATORY", st)
    story.append(body(
        "<b>Refinancing is granted only with a clear and documented exit strategy.</b> The Borrower "
        "represents and warrants that its exit strategy for the full repayment of the Loan at the "
        "Maturity Date is one of the following:", st))
    story += bullets([
        "Sale of the Property — confirmed promise to purchase or listing mandate",
        "Confirmed bank refinancing — commitment letter or preliminary confirmation",
        "Other documented strategy acceptable to the Lender",
    ], st)
    story.append(body(
        "<b>Failure to provide an acceptable and documented exit strategy constitutes an Event of Default.</b> "
        "The Borrower undertakes to immediately inform the Lender of any development affecting the exit "
        "strategy and to propose a replacement strategy acceptable to the Lender.", st))

    story += section("6. CONDITIONS PRECEDENT TO DISBURSEMENT", st)
    story += bullets([
        "Confirmation of first-rank mortgage status after discharge of the Former Lender's mortgage",
        "Discharge / payoff letter from Former Lender stating the exact balance due",
        "Accredited AACI appraisal of the Property, dated less than 6 months",
        "Documented exit strategy acceptable to the Lender",
        "Phase I environmental study (if applicable) acceptable to the Lender",
        "Insurance policies with Capital Norvex designated as beneficiary / additional insured",
        "Corporate resolution of Capital Norvex Inc. designating the signing representative",
        "Execution of the mortgage deed and any ancillary document required by the Lender",
    ], st)

    story += section("7. SECURITY", st)
    story += bullets([
        "First-rank real estate mortgage on the Property (after Former Lender discharge)",
        "Total and immediate assignment of rents (art. 2695 C.C.Q.)",
        "Joint, irrevocable and unlimited personal suretyship of the Guarantors",
        "Discharge and registered mortgage discharge from the Former Lender (MANDATORY)",
        "Any additional collateral acceptable to the Lender where applicable (for LTV > 70%)",
    ], st)

    story += section("8. ASSIGNMENT OF CONTRACTS, PLANS, PERMITS — WHERE APPLICABLE", st)
    story.append(body(
        "For any file involving a construction or major renovation component, the Borrower assigns to "
        "the Lender all contracts with the general contractor and major subcontractors, plans, "
        "specifications and other technical documents, municipal permits, bids, certificates and "
        "warranties, as well as all insurance policies relating to the Project. These assignments "
        "become enforceable by operation of law upon an Event of Default.", st))

    story += section("9. ZERO TOLERANCE — TAXES AND LEGAL HYPOTHECS", st)
    story.append(art("9.1", "Legal Hypothecs of Construction", st))
    story.append(body(
        "<b>NO</b> legal hypothec of construction (art. 2724 and 2726 C.C.Q.) is tolerated. The "
        "Borrower undertakes to settle or have any registered legal hypothec discharged "
        "<b>immediately</b>, and at the latest within <b>seven (7) days</b> of a written notice from "
        "the Lender. Failing this, an Event of Default shall be <b>automatically declared</b>.", st))
    story.append(art("9.2", "Taxes, Charges and Current Obligations", st))
    story.append(body(
        "The Borrower undertakes to pay punctually when due all property taxes, school taxes, municipal "
        "charges, insurance premiums, and any other current obligations affecting the Property. "
        "<b>NO</b> delay is tolerated. In the event of any delay, the Borrower undertakes to remedy the "
        "situation <b>immediately</b>, and at the latest within <b>seven (7) days</b> of a written "
        "notice from the Lender. Failing this, an Event of Default shall be "
        "<b>automatically declared</b>.", st))

    story += section("10. EVENTS OF DEFAULT", st)
    story.append(body("The following constitute Events of Default, without prior notice or formal demand other than as provided by law:", st))
    story += bullets([
        "Any payment default at maturity",
        "Failure to provide or maintain an acceptable and documented exit strategy",
        "Any material misrepresentation by the Borrower, particularly as to the use of funds",
        "Use of funds for purposes other than those declared (unauthorized cash-out)",
        "Material deterioration of the LTV or DCR ratios below the agreed thresholds",
        "Registration of any legal hypothec of construction not discharged within 7 days of notice from the Lender (zero tolerance — art. 9.1)",
        "Any delay in payment of taxes, charges, insurance or other current obligations not remedied within 7 days of notice from the Lender (zero tolerance — art. 9.2)",
        "Alienation or substantial modification of the Property without prior written authorization",
        "Insolvency, bankruptcy, or receivership of the Borrower",
        "Breach of the terms of the mortgage deed (indissociability clause — art. 13)",
    ], st)

    story += section("11. LENDER'S REMEDIES", st)
    story.append(body(
        "Upon an Event of Default, the Lender may, at its sole discretion: "
        "(i) declare the Loan immediately due and payable; "
        "(ii) exercise all hypothecary remedies (art. 2748 et seq. C.C.Q.), including taking in payment, "
        "sale by judicial authority, and sale by the creditor; "
        "(iii) directly collect rents under the assignment; "
        "(iv) enforce the suretyships; "
        "(v) cumulate remedies.", st))

    story += section("12. REPAYMENT", st)
    story.append(art("12.1", "Maturity", st))
    story.append(body(
        "The full balance of principal, capitalized interest, and fees shall be repaid no later than "
        "the Maturity Date, namely ____________________________.", st))
    story.append(art("12.2", "Prepayment", st))
    story.append(body(
        "The Borrower may repay the Loan in whole or in part without penalty, upon five (5) business "
        "days' prior written notice, subject to applicable exit fees (min. 3 months interest).", st))
    story.append(art("12.3", "Renewal", st))
    story.append(body(
        "The Lender may, at its sole discretion, agree to renew the Loan on the financial conditions "
        "then in effect, subject to a new appraisal of the Property, continued compliance with the "
        "ratios of Article 4, and payment of the analysis fees (Article 3) if applicable.", st))

    story += section("12.bis  BORROWER PORTAL (PWA) — 24/7 TRANSPARENCY", st)
    story.append(body(
        "Capital Norvex makes available to the Borrower a secure digital "
        "<b>Borrower Portal</b> (<b>PWA — Progressive Web Application</b>), accessible "
        "<b>24 hours a day, 7 days a week</b>, from any device (smartphone, tablet, computer). "
        "The Borrower may consult in real time:", st))
    story += bullets([
        "The Loan balance, the principal repaid, and the capitalized interest;",
        "The payment schedule and the history of payments made;",
        "The status of the repayment to the Former Lender and the discharge of the prior mortgage;",
        "Official notices and communications transmitted by Capital Norvex;",
        "Documents relevant to the file (appraisal, insurance policies, releases).",
    ], st)
    story.append(body(
        "The Borrower Portal (PWA) is a <b>transparency</b> tool made available to the "
        "Borrower. It does not replace the official written communications provided for in this "
        "Agreement and in no way alters the Borrower's obligations or the Lender's rights. "
        "<b>Where</b> the refinancing includes a construction or major renovation component within the "
        "meaning of Article 8, the related progressive disbursements are managed through the "
        "<b>Norvex Track\u2122</b> module under Capital Norvex's standard conditions.", st))

    story += section("13. INDISSOCIABILITY — MORTGAGE DEED — FUNDAMENTAL CLAUSE", st)
    story.append(body(
        "<b>This Loan Agreement and the real estate mortgage deed entered into between the Parties form "
        "an INDISSOCIABLE and complementary contractual whole.</b> The Parties expressly acknowledge "
        "and irrevocably agree that these two documents must be read, interpreted, and performed "
        "jointly, as if they constituted one and the same contract. Any breach of the terms of this "
        "Agreement automatically constitutes an Event of Default within the meaning of Article 10 and "
        "allows the exercise of all hypothecary remedies. In the event of any divergence or ambiguity "
        "between the two documents, "
        "<b>the interpretation most favourable to the Lender shall prevail</b>.", st))

    story += section("14. GENERAL PROVISIONS", st)
    gen_data = [
        ["Governing Law", "Laws of the Province of Quebec (Canada)"],
        ["Jurisdiction", "District of Montreal, Quebec"],
        ["Assignment", "Prohibited without prior written consent of the Lender"],
        ["Amendments", "In writing, signed by the parties"],
        ["PCMLTFA / FINTRAC", "Identity and source-of-funds verifications carried out"],
        ["Notices", "In writing, certified email or registered mail"],
        ["Entire Agreement", "This Agreement and the mortgage deed constitute the entire agreement"],
    ]
    tbl = Table(gen_data, colWidths=[2.0*inch, 4.6*inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), DARK),
        ("TEXTCOLOR", (0,0), (0,-1), GOLD),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [CREAM, HexColor("#e8e0ce")]),
        ("GRID", (0,0), (-1,-1), 0.5, GREY_LT),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(tbl)

    story.append(PageBreak())
    story += section("15. SIGNATURES", st)
    story.append(body(
        "IN WITNESS WHEREOF, the parties have signed this Agreement on the date indicated below, "
        "having read it.", st))
    story.append(body(
        "<i>For Capital Norvex Inc., this Agreement is signed by the designated representative below, "
        "duly authorized pursuant to a corporate resolution adopted by the sole shareholder and "
        "president, Mrs. Suzanne Breton, a certified true copy of which is attached to the file.</i>", st))
    story.append(Spacer(1, 12))

    for label, fields in [
        ("LENDER — CAPITAL NORVEX INC.", [
            "Designated Representative (full name): ___________________________________",
            "Title / Capacity: _________________________________________________________",
            "Pursuant to Corporate Resolution dated: __________________________________",
            "Signed by: Mrs. Suzanne Breton, sole shareholder and president",
            "Date of signature: ________________________________________________________",
            "Signature: ________________________________________________________________",
        ]),
        ("BORROWER", [
            "Corporate Name: ___________________________________________________________",
            "Authorized Representative: _______________________________________________",
            "Title: _____________________________________________________________________",
            "Date: ______________________________________________________________________",
            "Signature: _________________________________________________________________",
        ]),
        ("GUARANTOR(S)", [
            "Full Name: _________________________________________________________________",
            "Date: ______________________________________________________________________",
            "Signature: _________________________________________________________________",
        ]),
    ]:
        rows = [[Paragraph(label, ParagraphStyle("ST", fontName="Helvetica-Bold", fontSize=10,
                                                  textColor=WHITE, alignment=TA_LEFT))]]
        tbl = Table(rows, colWidths=[PAGE_W - 2*MARGIN])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), DARK),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LINEBELOW", (0,-1), (-1,-1), 2, GOLD),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 8))
        for f in fields:
            story.append(Paragraph(f, st["field_line"]))
        story.append(Spacer(1, 14))


# ─── GÉNÉRATION ──────────────────────────────────────────────────────────────
def generate(filename, builder, product_tag, title, st):
    doc = SimpleDocTemplate(
        filename, pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 36, bottomMargin=MARGIN + 38,
        title=title, author="Capital Norvex Inc.",
    )
    on_page = make_on_page(product_tag)
    story = []
    builder(story, st)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"✅ {filename}")


if __name__ == "__main__":
    st = build_styles()
    OUT_DIR = "/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres"

    generate(f"{OUT_DIR}/Convention_Pret_Refinancement_CapitalNorvex.pdf", build_fr,
             "REFINANCEMENT", "Convention de prêt — Refinancement — Capital Norvex", st)
    generate(f"{OUT_DIR}/Loan_Agreement_Refinancing_CapitalNorvex_EN.pdf", build_en,
             "REFINANCING", "Loan Agreement — Refinancing — Capital Norvex", st)

    print("\n🎉 2 conventions Refinancement (FR + EN) générées avec clause d'indissociabilité !")
