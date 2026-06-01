"""Agent CAPITAL — génération de dossiers d'approche PDF.

Génère un PDF 2-4 pages personnalisé selon le tier de la cible:
- Tier 1A : 4 pages (full dossier + thèse détaillée + cas d'usage)
- Tier 1B : 3 pages
- Tier 2  : 2 pages
- Tier 3  : 1 page (équivalent deal card)

Logo Norvex en haut + filigrane discret. Stockage dans Firebase Storage,
URL signée écrite dans capitalTargets.dossierUrl.

Dépendance: reportlab.
"""
from __future__ import annotations

import io
import os
from typing import Any, Dict, Optional

from ..shared import firestore_client as fs
from ..shared.tier_zero_guard import check_before_action

AGENT_NAME = "capital"

LOGO_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "logo-norvex-officiel.png")
)

PAGE_COUNT_BY_TIER = {"1A": 4, "1B": 3, "2": 2, "3": 1}


def generate_dossier(target_id: str) -> Dict[str, Any]:
    """Génère le dossier PDF et l'upload dans Storage.

    Retourne {dossierUrl, storagePath, pages}.
    """
    target = fs.get("capitalTargets", target_id)
    if not target:
        raise RuntimeError(f"capitalTargets/{target_id} introuvable")
    target["_agent"] = AGENT_NAME
    target["_target_type"] = "capitalTarget"
    check_before_action(target)

    pages = PAGE_COUNT_BY_TIER.get(target.get("tier", "2"), 2)
    pdf_bytes = _build_pdf(target, pages=pages)

    storage_path = f"capital-dossiers/{target_id}.pdf"
    download_url = _upload_to_storage(pdf_bytes, storage_path)

    fs.update("capitalTargets", target_id, {"dossierUrl": download_url})
    fs.audit_log(
        agent=AGENT_NAME,
        action="generate_dossier",
        target_type="capitalTarget",
        target_id=target_id,
        details={"pages": pages, "storagePath": storage_path},
    )

    return {"dossierUrl": download_url, "storagePath": storage_path, "pages": pages}


def _build_pdf(target: Dict[str, Any], pages: int) -> bytes:
    """Compose un PDF simple en reportlab. v1 minimal mais fonctionnel."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Image,
            PageBreak,
        )
    except ImportError:
        raise RuntimeError("reportlab non installé — pip install reportlab")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"Capital Norvex — Dossier {target.get('name', '')}",
        author="Capital Norvex Inc.",
    )

    styles = getSampleStyleSheet()
    h_style = ParagraphStyle(
        "Norvex_H1",
        parent=styles["Heading1"],
        fontName="Times-Roman",
        textColor=colors.HexColor("#0A0A0A"),
        fontSize=22,
        leading=26,
        alignment=1,
        spaceAfter=14,
    )
    sub_style = ParagraphStyle(
        "Norvex_Sub",
        parent=styles["Italic"],
        fontName="Times-Italic",
        textColor=colors.HexColor("#C8B070"),
        fontSize=12,
        alignment=1,
        spaceAfter=24,
    )
    body_style = ParagraphStyle(
        "Norvex_Body",
        parent=styles["BodyText"],
        fontName="Times-Roman",
        fontSize=11,
        leading=17,
        textColor=colors.HexColor("#0A0A0A"),
        spaceAfter=12,
    )

    story = []
    if os.path.exists(LOGO_PATH):
        try:
            story.append(Image(LOGO_PATH, width=1.5 * inch, height=2.25 * inch))
        except Exception:
            pass
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("CAPITAL NORVEX", h_style))
    story.append(Paragraph("Capital structuré. Ambition maîtrisée.", sub_style))

    story.append(
        Paragraph(
            f"<b>Dossier confidentiel préparé pour :</b> {target.get('name', '')}",
            body_style,
        )
    )
    if target.get("organization"):
        story.append(Paragraph(f"<b>Organisation :</b> {target['organization']}", body_style))

    story.append(Spacer(1, 0.3 * inch))
    if target.get("investmentThesis"):
        story.append(Paragraph("<b>Thèse d'investissement</b>", body_style))
        story.append(Paragraph(target["investmentThesis"], body_style))

    if target.get("approachAngle") and pages >= 2:
        story.append(PageBreak())
        story.append(Paragraph("<b>Angle d'approche</b>", body_style))
        story.append(Paragraph(target["approachAngle"], body_style))

    if pages >= 3:
        story.append(PageBreak())
        story.append(Paragraph("<b>Cadre opérationnel</b>", body_style))
        story.append(
            Paragraph(
                "Capital Norvex structure ses engagements autour de garanties "
                "immobilières de premier rang, d'une gouvernance familiale et "
                "d'un suivi mensuel exhaustif. Aucune dilution de contrôle, "
                "rendements stables, transparence intégrale.",
                body_style,
            )
        )

    if pages >= 4:
        story.append(PageBreak())
        story.append(Paragraph("<b>Prochaines étapes</b>", body_style))
        story.append(
            Paragraph(
                "Une discussion confidentielle peut être organisée à votre "
                "convenance. Nous transmettons sur demande des dossiers "
                "représentatifs anonymisés et l'historique du portefeuille "
                "en cours.",
                body_style,
            )
        )

    doc.build(story)
    return buf.getvalue()


def _upload_to_storage(pdf_bytes: bytes, storage_path: str) -> Optional[str]:
    """Upload vers Firebase Storage et retourne URL signée 7 jours."""
    try:
        from datetime import timedelta

        from ..shared.auth import get_storage

        bucket = get_storage()
        blob = bucket.blob(storage_path)
        blob.upload_from_string(pdf_bytes, content_type="application/pdf")
        try:
            return blob.generate_signed_url(expiration=timedelta(days=7))
        except Exception:
            return f"gs://{bucket.name}/{storage_path}"
    except Exception as e:
        print(f"[approach_dossier] upload Storage échoué: {e}")
        return None
