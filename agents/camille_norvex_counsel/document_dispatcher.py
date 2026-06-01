"""Document Dispatcher Camille — envoi lettres d'engagement + autres docs juridiques.

Workflow :
1. L'UI Pipeline déclenche un flag Firestore (`engagementLetterRequested = true`)
2. Le cron Camille local exécute `process_pending_documents()`
3. Pour chaque dossier flagué : génère email personnalisé + attache PDF + envoie + audit

⚠️  RÈGLE CRITIQUE (Yves 2026-05-04) :
   Cette fonction NE TOUCHE PAS au workflow existant (Score Norvex / agent_docs.py / Norah).
   Elle s'active SEULEMENT après que Yves clique le bouton "Envoyer lettre d'engagement"
   dans le Pipeline (= GO #2, post-RDV).

Documents disponibles :
   FR : Acquisition / Construction / Terrain / Refinancement
   EN : Acquisition / Construction / Land / Refinancing
"""
from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from agents.shared.auth import get_graph_token
from agents.shared.firestore_client import audit_log, get, query, update

from .audit import _now
from .config import AGENT_NAME

# ── Mapping type Pipeline → fichier PDF ──────────────────────────
DOCS_BASE_PATH = Path(
    "/Users/yvesbarrette/Desktop/capitalnorvex-site/document convention et autres"
)

ENGAGEMENT_LETTER_PDFS = {
    # FR
    ("Construction", "fr"): "CapitalNorvex_LettrEngagement_Construction.pdf",
    ("Terrain", "fr"):       "CapitalNorvex_LettrEngagement_Terrain.pdf",
    ("Acquisition", "fr"):   "CapitalNorvex_LettrEngagement_Acquisition.pdf",
    ("Refinancement", "fr"): "CapitalNorvex_LettrEngagement_Refinancement.pdf",
    # Defaults (Pont/Commercial/Résidentiel → Acquisition)
    ("Pont", "fr"):          "CapitalNorvex_LettrEngagement_Acquisition.pdf",
    ("Commercial", "fr"):    "CapitalNorvex_LettrEngagement_Acquisition.pdf",
    ("Résidentiel", "fr"):   "CapitalNorvex_LettrEngagement_Acquisition.pdf",
    # EN
    ("Construction", "en"):  "CapitalNorvex_CommitmentLetter_Construction_EN.pdf",
    ("Terrain", "en"):       "CapitalNorvex_CommitmentLetter_Land_EN.pdf",
    ("Land", "en"):          "CapitalNorvex_CommitmentLetter_Land_EN.pdf",
    ("Acquisition", "en"):   "CapitalNorvex_CommitmentLetter_Acquisition_EN.pdf",
    ("Refinancement", "en"): "CapitalNorvex_CommitmentLetter_Refinancing_EN.pdf",
    ("Refinancing", "en"):   "CapitalNorvex_CommitmentLetter_Refinancing_EN.pdf",
    ("Pont", "en"):          "CapitalNorvex_CommitmentLetter_Acquisition_EN.pdf",
    ("Commercial", "en"):    "CapitalNorvex_CommitmentLetter_Acquisition_EN.pdf",
    ("Résidentiel", "en"):   "CapitalNorvex_CommitmentLetter_Acquisition_EN.pdf",
    ("Residential", "en"):   "CapitalNorvex_CommitmentLetter_Acquisition_EN.pdf",
}

CAMILLE_MAILBOX = "camille@capitalnorvex.com"
YVES_CC = "yves@capitalnorvex.com"


def get_engagement_letter_pdf(loan_type: str, lang: str = "fr") -> Optional[Path]:
    """Retourne le path du PDF lettre d'engagement adapté au dossier."""
    lang = (lang or "fr").lower()[:2]
    key = (loan_type, lang)
    filename = ENGAGEMENT_LETTER_PDFS.get(key)
    if not filename:
        # Default : Acquisition dans la langue
        filename = ENGAGEMENT_LETTER_PDFS.get(("Acquisition", lang))
    if not filename:
        return None
    full_path = DOCS_BASE_PATH / filename
    return full_path if full_path.exists() else None


def _build_email_html(client_name: str, loan_type: str, dossier_id: str,
                      lang: str = "fr") -> tuple[str, str]:
    """Construit (subject, body_html) personnalisé pour l'envoi."""
    is_en = (lang or "fr").lower().startswith("en")

    if is_en:
        subject = f"Capital Norvex — Commitment Letter for your file {dossier_id}"
        body = f"""<!DOCTYPE html><html lang="en"><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1a1a1a;line-height:1.6;max-width:680px;margin:0 auto;padding:24px">
<p>Dear {client_name},</p>
<p>Following our recent discussions, please find attached the <strong>Commitment Letter</strong> for your <strong>{loan_type}</strong> financing file (reference <code>{dossier_id}</code>).</p>
<p>This letter sets out the principal terms and conditions under which Capital Norvex Inc. is prepared to extend the requested financing. We invite you to:</p>
<ol>
<li>Review the document carefully (5–10 minutes).</li>
<li>Sign the last page (digital signature accepted).</li>
<li>Return the signed copy to this email address.</li>
</ol>
<p>Once received, our legal team will prepare the loan agreement and coordinate the closing with the notary or solicitor at your file.</p>
<p>Should you have any questions about the terms, please do not hesitate to reply directly. <strong>Mr. Yves Barrette, our President, is in copy</strong> of this email and will be happy to clarify any aspect.</p>
<p>Best regards,</p>
<p style="margin-top:24px;font-size:13px;line-height:1.6;color:#333">
<strong style="color:#C9A227;letter-spacing:1px">CAMILLE — NORVEX COUNSEL™</strong><br>
Legal Coordination<br>
<strong>Capital Norvex Inc.</strong><br>
2705-1000 André-Prévost, Île-des-Sœurs, Montréal, QC&nbsp;H3E&nbsp;0G2<br>
<a href="tel:+14385337738" style="color:#444;text-decoration:none">1-(438)-533-PRET (7738)</a> ·
<a href="mailto:camille@capitalnorvex.com" style="color:#444;text-decoration:none">camille@capitalnorvex.com</a>
</p>
<p style="margin-top:8px;font-size:11px;color:#888;font-style:italic">
Camille is an AI legal coordinator. All financial and legal decisions binding Capital Norvex Inc. are made and validated by Mr. Yves Barrette, President, who is in copy of this exchange.
</p>
</body></html>"""
    else:
        subject = f"Capital Norvex — Lettre d'engagement pour votre dossier {dossier_id}"
        body = f"""<!DOCTYPE html><html lang="fr"><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1a1a1a;line-height:1.6;max-width:680px;margin:0 auto;padding:24px">
<p>Bonjour {client_name},</p>
<p>Suite à nos récents échanges, vous trouverez ci-joint la <strong>Lettre d'engagement</strong> pour votre dossier de financement <strong>{loan_type}</strong> (référence <code>{dossier_id}</code>).</p>
<p>Cette lettre énonce les principales modalités selon lesquelles Capital Norvex Inc. est disposée à octroyer le financement demandé. Nous vous invitons à :</p>
<ol>
<li>Relire attentivement le document (5–10 minutes).</li>
<li>Signer à la dernière page (signature numérique acceptée).</li>
<li>Nous retourner la copie signée à cette adresse courriel.</li>
</ol>
<p>Dès réception, notre équipe juridique préparera la convention de prêt et coordonnera le closing avec le notaire au dossier.</p>
<p>Pour toute question sur les modalités, n'hésitez pas à répondre directement à ce courriel. <strong>M. Yves Barrette, notre Président, est en copie</strong> de cet envoi et se fera un plaisir de clarifier tout aspect.</p>
<p>Avec considération,</p>
<p style="margin-top:24px;font-size:13px;line-height:1.6;color:#333">
<strong style="color:#C9A227;letter-spacing:1px">CAMILLE — NORVEX COUNSEL™</strong><br>
Coordination juridique<br>
<strong>Capital Norvex Inc.</strong><br>
2705-1000 André-Prévost, Île-des-Sœurs (Verdun), Montréal, QC&nbsp;H3E&nbsp;0G2<br>
<a href="tel:+14385337738" style="color:#444;text-decoration:none">1-(438)-533-PRET (7738)</a> ·
<a href="mailto:camille@capitalnorvex.com" style="color:#444;text-decoration:none">camille@capitalnorvex.com</a>
</p>
<p style="margin-top:8px;font-size:11px;color:#888;font-style:italic">
Camille est une coordonnatrice juridique IA. Toutes les décisions financières et juridiques engageant Capital Norvex Inc. sont prises et validées par M. Yves Barrette, Président, en copie de cet échange.
</p>
</body></html>"""
    return subject, body


def send_engagement_letter(dossier_id: str, *, force: bool = False) -> Dict[str, Any]:
    """Envoie la lettre d'engagement pour un dossier donné.

    Args:
        dossier_id: ID Firestore du dossier
        force: si True, renvoie même si déjà envoyé (utilité : correctifs)

    Returns:
        {ok, dossier_id, sent_to, pdf_filename, mode, error?}
    """
    dossier = get("dossiers", dossier_id)
    if not dossier:
        return {"ok": False, "dossier_id": dossier_id, "error": "Dossier introuvable"}

    # Anti-doublon : si déjà envoyé et force=False, skip
    if dossier.get("engagementSentAt") and not force:
        return {
            "ok": False, "dossier_id": dossier_id,
            "error": f"Déjà envoyé le {dossier['engagementSentAt']}. Utilise force=True pour renvoyer.",
        }

    client_email = (dossier.get("email") or dossier.get("client_email") or "").strip()
    if not client_email or "@" not in client_email:
        return {"ok": False, "dossier_id": dossier_id, "error": "Email client manquant"}

    client_first = dossier.get("prenom") or dossier.get("client_prenom") or ""
    client_last = dossier.get("nom") or dossier.get("client_nom") or ""
    client_name = f"{client_first} {client_last}".strip() or "Client"

    loan_type = (dossier.get("type") or dossier.get("loanType") or "Acquisition").strip()
    lang = (dossier.get("lang") or dossier.get("language") or "fr").lower()[:2]

    # Termes négociés (priorité aux champs `negotiatedTerms` saisis par Yves dans Pipeline)
    negotiated = dossier.get("negotiatedTerms") or {}

    # Génération PDF DYNAMIQUE personnalisé (Phase B Yves 2026-05-04)
    # Le PDF contient les termes négociés réels (taux/montant/durée/conditions
    # spécifiques) — pas un template statique.
    try:
        from .engagement_letter_pdf import generate_engagement_letter_pdf
        pdf_bytes = generate_engagement_letter_pdf(
            dossier={**dossier, "_id": dossier_id},
            terms=negotiated,
            lang=lang,
            dossier_id=dossier_id,
        )
        pdf_filename = f"CapitalNorvex_LettrEngagement_{dossier_id}.pdf"
    except Exception as e:
        # Fallback : template statique si génération dynamique échoue
        # (anti-régression : on n'arrête pas un envoi pour un bug PDF)
        pdf_path = get_engagement_letter_pdf(loan_type, lang)
        if not pdf_path:
            return {
                "ok": False, "dossier_id": dossier_id,
                "error": f"PDF dynamique en erreur ({e}) ET aucun template fallback pour type={loan_type} lang={lang}",
            }
        pdf_bytes = pdf_path.read_bytes()
        pdf_filename = pdf_path.name
        audit_log(
            agent=AGENT_NAME, action="engagement_letter_dynamic_fallback",
            target_type="dossiers", target_id=dossier_id, result="warning",
            details={"error": str(e)[:300]},
        )

    # Email personnalisé
    subject, html = _build_email_html(client_name, loan_type, dossier_id, lang)

    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    # Envoi via Microsoft Graph (depuis camille@) avec attachment + Yves CC
    token = get_graph_token()
    message = {
        "subject": subject,
        "body": {"contentType": "HTML", "content": html},
        "toRecipients": [{"emailAddress": {"address": client_email}}],
        "ccRecipients": [{"emailAddress": {"address": YVES_CC}}],
        "from": {"emailAddress": {"address": CAMILLE_MAILBOX}},
        "replyTo": [{"emailAddress": {"address": CAMILLE_MAILBOX}}],
        "attachments": [
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": pdf_filename,
                "contentType": "application/pdf",
                "contentBytes": pdf_b64,
            }
        ],
        "internetMessageHeaders": [
            {"name": "X-Capital-Norvex-Type", "value": "engagement-letter"},
            {"name": "X-Capital-Norvex-Dossier", "value": dossier_id},
            {"name": "X-Auto-Response-Suppress", "value": "All"},
        ],
    }

    import requests
    url = f"https://graph.microsoft.com/v1.0/users/{CAMILLE_MAILBOX}/sendMail"
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"message": message, "saveToSentItems": True},
        timeout=60,
    )

    if r.status_code >= 200 and r.status_code < 300:
        # MAJ Firestore : marque envoyé + reset flag de demande
        update("dossiers", dossier_id, {
            "engagementSentAt": _now().isoformat(),
            "engagementSentTo": client_email,
            "engagementPdfFilename": pdf_path.name,
            "engagementSentBy": "camille",
            "engagementLetterRequested": False,  # consomme la demande
            "stage": "engagement_envoye",
        })
        audit_log(
            agent=AGENT_NAME,
            action="engagement_letter_sent",
            target_type="dossiers",
            target_id=dossier_id,
            result="success",
            details={
                "to": client_email, "cc": YVES_CC,
                "pdfFilename": pdf_path.name,
                "loanType": loan_type, "lang": lang,
            },
        )
        return {
            "ok": True, "dossier_id": dossier_id,
            "sent_to": client_email, "cc": YVES_CC,
            "pdf_filename": pdf_path.name,
            "mode": "auto_send",
        }
    else:
        err_text = r.text[:500]
        update("dossiers", dossier_id, {
            "engagementSentError": err_text,
            "engagementLetterRequested": False,  # ne pas re-tenter en boucle
        })
        audit_log(
            agent=AGENT_NAME,
            action="engagement_letter_failed",
            target_type="dossiers",
            target_id=dossier_id,
            result="error",
            details={"http_status": r.status_code, "error": err_text},
        )
        return {
            "ok": False, "dossier_id": dossier_id,
            "error": f"Graph {r.status_code}: {err_text}",
        }


def process_pending_engagement_letters() -> list[Dict[str, Any]]:
    """Scanne Firestore pour les dossiers avec `engagementLetterRequested=true`
    et envoie pour chacun. Appelé par le cron Camille (10 min)."""
    pending = query("dossiers",
                    filters=[("engagementLetterRequested", "==", True)],
                    limit=50)
    results = []
    for d in pending:
        if d.get("engagementSentAt"):
            continue  # déjà envoyé → skip
        try:
            res = send_engagement_letter(d["id"])
            results.append(res)
        except Exception as e:
            results.append({"ok": False, "dossier_id": d.get("id"), "error": str(e)[:300]})
            audit_log(
                agent=AGENT_NAME,
                action="engagement_letter_exception",
                target_type="dossiers",
                target_id=d.get("id", "unknown"),
                result="error",
                details={"error": str(e)[:500]},
            )
    return results
