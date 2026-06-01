#!/usr/bin/env python3
"""
Capital Norvex — Agent Analyse Documents
Tourne automatiquement toutes les 10 min via launchd.
mail.capitalnorvex.com IMAP → Classification → Claude AI → Sommaire → Yves
Netlify Blobs uploads → Classification → Claude AI → Sommaire → Yves
"""

import imaplib
import smtplib
import email as email_lib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import decode_header
import os
import json
import logging
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from io import BytesIO
import anthropic
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from pypdf import PdfReader
from dotenv import load_dotenv

# Secrets stockés hors du repo (sécurité — évite tout risque de fuite via Git/Netlify).
# Priorité 1 : ~/.capitalnorvex/.env  (emplacement standard Mac/Linux, perms 600)
# Priorité 2 : ./.env  (legacy local, pour rétrocompatibilité dev)
_env_paths = [
    Path.home() / ".capitalnorvex" / ".env",
    Path(__file__).parent / ".env",
]
for _p in _env_paths:
    if _p.exists():
        load_dotenv(_p, override=True)
        break

# ── Config ────────────────────────────────────────────────────────────────────
MAIL_USER         = os.getenv("MAIL_USER", "yves@capitalnorvex.com")  # mailbox réel (info@ est un alias)
MAIL_PASSWORD     = os.getenv("MAIL_PASSWORD")   # mot de passe yves@capitalnorvex.com
MAIL_HOST         = os.getenv("MAIL_HOST", "mail.capitalnorvex.com")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
YVES_EMAIL        = os.getenv("YVES_EMAIL")       # email personnel de Yves
INTERNAL_SECRET   = os.getenv("INTERNAL_SECRET")  # secret partagé avec Netlify Functions
NETLIFY_SITE_URL  = os.getenv("NETLIFY_SITE_URL", "https://capitalnorvex.com")

BASE_DIR              = Path.home() / "Library" / "Application Support" / "CapitalNorvex" / "Dossiers"
STATE_FILE            = BASE_DIR / "_state.json"
LOG_FILE              = BASE_DIR / "_agent.log"
DESKTOP_DOSSIERS      = Path.home() / "Desktop" / "Capital Norvex"
BASE_DIR.mkdir(parents=True, exist_ok=True)
DESKTOP_DOSSIERS.mkdir(parents=True, exist_ok=True)

PDF_DOCS_DIR          = Path.home() / "Desktop" / "Capital Norvex" / "Documents PDF"
CONVENTION_CONSTRUCTION = PDF_DOCS_DIR / "Convention_Partenariat_Construction_CapitalNorvex.pdf"
CONVENTION_DEFAULT    = PDF_DOCS_DIR / "Convention_Pret_CapitalNorvex.pdf"
SOMMAIRE_PART_FR      = PDF_DOCS_DIR / "CapitalNorvex_SommaireExecutif_Partenaire.pdf"
SOMMAIRE_PART_EN      = PDF_DOCS_DIR / "CapitalNorvex_ExecutiveSummary_Partner_EN.pdf" 

def get_desktop_folder(sender_name: str) -> Path:
    """Retourne (et crée) le dossier Bureau/Capital Norvex/NomClient/."""
    safe_name = "".join(c for c in sender_name if c not in r'\/:*?"<>|').strip() or "Client"
    folder = DESKTOP_DOSSIERS / safe_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("cn_agent")

# ── Checklists documents requis par type de prêt ─────────────────────────────
DOCS_REQUIS_BY_TYPE = {

    "Construction": [
        {"id": "etats_fin_co",       "fr": "États financiers de la compagnie (2 dernières années)",      "en": "Company financial statements (last 2 years)"},
        {"id": "etats_fin_int",      "fr": "États financiers intérimaires récents",                      "en": "Recent interim financial statements"},
        {"id": "decl_fisc",          "fr": "Déclarations fiscales (compagnie et actionnaires)",          "en": "Tax returns (company and shareholders)"},
        {"id": "etats_fin_pers",     "fr": "États financiers personnels des actionnaires",               "en": "Personal financial statements of shareholders"},
        {"id": "liquidites",         "fr": "Preuve de liquidités",                                       "en": "Proof of liquidity"},
        {"id": "actifs_passifs",     "fr": "Liste des actifs et passifs",                                "en": "List of assets and liabilities"},
        {"id": "acte_terrain",       "fr": "Acte d'achat du terrain ou promesse d'achat",               "en": "Land deed or purchase offer"},
        {"id": "cert_localisation",  "fr": "Certificat de localisation",                                 "en": "Certificate of location"},
        {"id": "rapport_titre",      "fr": "Rapport de titre (ou recherche de titres)",                 "en": "Title report or title search"},
        {"id": "taxes",              "fr": "Comptes de taxes municipales et scolaires + preuves de paiement", "en": "Municipal/school tax accounts + payment proofs"},
        {"id": "zonage",             "fr": "Zonage municipal",                                           "en": "Municipal zoning"},
        {"id": "plans_arch",         "fr": "Plans architecturaux",                                       "en": "Architectural plans"},
        {"id": "plans_ing",          "fr": "Plans d'ingénierie (si disponibles)",                       "en": "Engineering plans (if available)"},
        {"id": "permis_construction","fr": "Permis de construction",                                     "en": "Building permit"},
        {"id": "budget_construction","fr": "Budget détaillé de construction",                            "en": "Detailed construction budget"},
        {"id": "echeancier",         "fr": "Échéancier de construction",                                 "en": "Construction schedule"},
        {"id": "contrat_entrepreneur","fr": "Contrat avec l'entrepreneur général",                       "en": "General contractor agreement"},
        {"id": "evaluation",         "fr": "Rapport d'évaluation",                                       "en": "Appraisal report"},
        {"id": "valeur_completion",  "fr": "Valeur projetée à complétion",                              "en": "Projected value at completion"},
        {"id": "geotechnique",       "fr": "Étude géotechnique",                                         "en": "Geotechnical study"},
        {"id": "env_phase1",         "fr": "Étude environnementale Phase I (Phase II si applicable)",   "en": "Phase I Environmental Study (Phase II if applicable)"},
    ],

    "Infrastructure": [
        {"id": "etats_fin_co",       "fr": "États financiers de la compagnie (2 dernières années)",      "en": "Company financial statements (last 2 years)"},
        {"id": "etats_fin_int",      "fr": "États financiers intérimaires récents",                      "en": "Recent interim financial statements"},
        {"id": "decl_fisc",          "fr": "Déclarations fiscales (compagnie et actionnaires)",          "en": "Tax returns (company and shareholders)"},
        {"id": "etats_fin_pers",     "fr": "États financiers personnels des actionnaires",               "en": "Personal financial statements of shareholders"},
        {"id": "liquidites",         "fr": "Preuve de liquidités",                                       "en": "Proof of liquidity"},
        {"id": "acte_terrain",       "fr": "Acte d'achat du terrain ou promesse d'achat",               "en": "Land deed or purchase offer"},
        {"id": "zonage",             "fr": "Zonage municipal",                                           "en": "Municipal zoning"},
        {"id": "plans_arch",         "fr": "Plans architecturaux et d'ingénierie",                       "en": "Architectural and engineering plans"},
        {"id": "permis_construction","fr": "Permis de construction",                                     "en": "Building permit"},
        {"id": "budget_construction","fr": "Budget détaillé du projet",                                  "en": "Detailed project budget"},
        {"id": "echeancier",         "fr": "Échéancier de réalisation",                                  "en": "Project schedule"},
        {"id": "contrat_entrepreneur","fr": "Contrat avec l'entrepreneur général",                       "en": "General contractor agreement"},
        {"id": "evaluation",         "fr": "Rapport d'évaluation",                                       "en": "Appraisal report"},
        {"id": "env_phase1",         "fr": "Étude environnementale Phase I (Phase II si applicable)",   "en": "Phase I Environmental Study (Phase II if applicable)"},
        {"id": "geotechnique",       "fr": "Étude géotechnique",                                         "en": "Geotechnical study"},
    ],

    "Commercial": [
        {"id": "etats_fin_co",       "fr": "États financiers de la compagnie (2 dernières années)",      "en": "Company financial statements (last 2 years)"},
        {"id": "etats_fin_int",      "fr": "États financiers intérimaires récents",                      "en": "Recent interim financial statements"},
        {"id": "decl_fisc",          "fr": "Déclarations fiscales (compagnie et actionnaires)",          "en": "Tax returns (company and shareholders)"},
        {"id": "etats_fin_pers",     "fr": "États financiers personnels des actionnaires",               "en": "Personal financial statements of shareholders"},
        {"id": "liquidites",         "fr": "Preuve de liquidités",                                       "en": "Proof of liquidity"},
        {"id": "actifs_passifs",     "fr": "Liste des actifs et passifs",                                "en": "List of assets and liabilities"},
        {"id": "acte_terrain",       "fr": "Acte d'achat du terrain ou promesse d'achat",               "en": "Land deed or purchase offer"},
        {"id": "cert_localisation",  "fr": "Certificat de localisation",                                 "en": "Certificate of location"},
        {"id": "rapport_titre",      "fr": "Rapport de titre (ou recherche de titres)",                 "en": "Title report or title search"},
        {"id": "taxes",              "fr": "Comptes de taxes municipales et scolaires + preuves de paiement", "en": "Municipal/school tax accounts + payment proofs"},
        {"id": "zonage",             "fr": "Zonage municipal",                                           "en": "Municipal zoning"},
        {"id": "servitudes",         "fr": "Servitudes enregistrées",                                    "en": "Registered easements"},
        {"id": "plan_cadastral",     "fr": "Plan cadastral du terrain",                                  "en": "Cadastral plan of the land"},
        {"id": "evaluation",         "fr": "Rapport d'évaluation",                                       "en": "Appraisal report"},
        {"id": "valeur_actuelle",    "fr": "Valeur actuelle du terrain",                                 "en": "Current land value"},
        {"id": "env_phase1",         "fr": "Étude environnementale Phase I (Phase II si applicable)",   "en": "Phase I Environmental Study (Phase II if applicable)"},
    ],

    "Multilogement": [
        {"id": "etats_fin_co",       "fr": "États financiers de la compagnie (2 dernières années)",      "en": "Company financial statements (last 2 years)"},
        {"id": "etats_fin_int",      "fr": "États financiers intérimaires récents",                      "en": "Recent interim financial statements"},
        {"id": "decl_fisc",          "fr": "Déclarations fiscales (compagnie et actionnaires)",          "en": "Tax returns (company and shareholders)"},
        {"id": "etats_fin_pers",     "fr": "États financiers personnels des actionnaires",               "en": "Personal financial statements of shareholders"},
        {"id": "liquidites",         "fr": "Preuve de liquidités",                                       "en": "Proof of liquidity"},
        {"id": "actifs_passifs",     "fr": "Liste des actifs et passifs",                                "en": "List of assets and liabilities"},
        {"id": "acte_terrain",       "fr": "Acte d'achat du terrain ou promesse d'achat",               "en": "Land deed or purchase offer"},
        {"id": "cert_localisation",  "fr": "Certificat de localisation",                                 "en": "Certificate of location"},
        {"id": "rapport_titre",      "fr": "Rapport de titre (ou recherche de titres)",                 "en": "Title report or title search"},
        {"id": "taxes",              "fr": "Comptes de taxes municipales et scolaires + preuves de paiement", "en": "Municipal/school tax accounts + payment proofs"},
        {"id": "zonage",             "fr": "Zonage municipal",                                           "en": "Municipal zoning"},
        {"id": "servitudes",         "fr": "Servitudes enregistrées",                                    "en": "Registered easements"},
        {"id": "plan_cadastral",     "fr": "Plan cadastral du terrain",                                  "en": "Cadastral plan of the land"},
        {"id": "evaluation",         "fr": "Rapport d'évaluation",                                       "en": "Appraisal report"},
        {"id": "valeur_actuelle",    "fr": "Valeur actuelle du terrain",                                 "en": "Current land value"},
        {"id": "env_phase1",         "fr": "Étude environnementale Phase I (Phase II si applicable)",   "en": "Phase I Environmental Study (Phase II if applicable)"},
    ],

    "Refinancement": [
        {"id": "etats_fin_co",       "fr": "États financiers de la compagnie (2 dernières années)",      "en": "Company financial statements (last 2 years)"},
        {"id": "etats_fin_int",      "fr": "États financiers intérimaires récents",                      "en": "Recent interim financial statements"},
        {"id": "decl_fisc",          "fr": "Déclarations fiscales (compagnie et actionnaires)",          "en": "Tax returns (company and shareholders)"},
        {"id": "etats_fin_pers",     "fr": "États financiers personnels des actionnaires",               "en": "Personal financial statements of shareholders"},
        {"id": "liquidites",         "fr": "Preuve de liquidités",                                       "en": "Proof of liquidity"},
        {"id": "actifs_passifs",     "fr": "Liste des actifs et passifs",                                "en": "List of assets and liabilities"},
        {"id": "acte_terrain",       "fr": "Acte d'achat du terrain ou promesse d'achat",               "en": "Land deed or purchase offer"},
        {"id": "cert_localisation",  "fr": "Certificat de localisation",                                 "en": "Certificate of location"},
        {"id": "rapport_titre",      "fr": "Rapport de titre (ou recherche de titres)",                 "en": "Title report or title search"},
        {"id": "taxes",              "fr": "Comptes de taxes municipales et scolaires + preuves de paiement", "en": "Municipal/school tax accounts + payment proofs"},
        {"id": "zonage",             "fr": "Zonage municipal",                                           "en": "Municipal zoning"},
        {"id": "servitudes",         "fr": "Servitudes enregistrées",                                    "en": "Registered easements"},
        {"id": "plan_cadastral",     "fr": "Plan cadastral du terrain",                                  "en": "Cadastral plan of the land"},
        {"id": "evaluation",         "fr": "Rapport d'évaluation",                                       "en": "Appraisal report"},
        {"id": "valeur_actuelle",    "fr": "Valeur actuelle du terrain",                                 "en": "Current land value"},
        {"id": "env_phase1",         "fr": "Étude environnementale Phase I (Phase II si applicable)",   "en": "Phase I Environmental Study (Phase II if applicable)"},
    ],

    "Bridge": [
        {"id": "etats_fin_co",        "fr": "États financiers de la compagnie (2 dernières années)",      "en": "Company financial statements (last 2 years)"},
        {"id": "etats_fin_int",       "fr": "États financiers intérimaires récents",                      "en": "Recent interim financial statements"},
        {"id": "decl_fisc",           "fr": "Déclarations fiscales (compagnie et actionnaires)",          "en": "Tax returns (company and shareholders)"},
        {"id": "etats_fin_pers",      "fr": "États financiers personnels des actionnaires",               "en": "Personal financial statements of shareholders"},
        {"id": "liquidites",          "fr": "Preuve de liquidités",                                       "en": "Proof of liquidity"},
        {"id": "actifs_passifs",      "fr": "Liste des actifs et passifs",                                "en": "List of assets and liabilities"},
        {"id": "acte_terrain",        "fr": "Acte d'achat du terrain ou promesse d'achat",               "en": "Land deed or purchase offer"},
        {"id": "cert_localisation",   "fr": "Certificat de localisation",                                 "en": "Certificate of location"},
        {"id": "rapport_titre",       "fr": "Rapport de titre (ou recherche de titres)",                 "en": "Title report or title search"},
        {"id": "taxes",               "fr": "Comptes de taxes municipales et scolaires + preuves de paiement", "en": "Municipal/school tax accounts + payment proofs"},
        {"id": "zonage",              "fr": "Zonage municipal",                                           "en": "Municipal zoning"},
        {"id": "plans_arch",          "fr": "Plans architecturaux",                                       "en": "Architectural plans"},
        {"id": "plans_ing",           "fr": "Plans d'ingénierie (si disponibles)",                       "en": "Engineering plans (if available)"},
        {"id": "permis_construction", "fr": "Permis de construction",                                     "en": "Building permit"},
        {"id": "budget_construction", "fr": "Budget détaillé de construction",                            "en": "Detailed construction budget"},
        {"id": "echeancier",          "fr": "Échéancier de construction",                                 "en": "Construction schedule"},
        {"id": "contrat_entrepreneur","fr": "Contrat avec l'entrepreneur général",                        "en": "General contractor agreement"},
        {"id": "evaluation",          "fr": "Rapport d'évaluation",                                       "en": "Appraisal report"},
        {"id": "valeur_completion",   "fr": "Valeur projetée à complétion",                              "en": "Projected value at completion"},
        {"id": "geotechnique",        "fr": "Étude géotechnique",                                         "en": "Geotechnical study"},
        {"id": "env_phase1",          "fr": "Étude environnementale Phase I (Phase II si applicable)",   "en": "Phase I Environmental Study (Phase II if applicable)"},
    ],

    "Terrain": [
        {"id": "etats_fin_co",       "fr": "États financiers de la compagnie (2 dernières années)",      "en": "Company financial statements (last 2 years)"},
        {"id": "etats_fin_int",      "fr": "États financiers intérimaires récents",                      "en": "Recent interim financial statements"},
        {"id": "decl_fisc",          "fr": "Déclarations fiscales (compagnie et actionnaires)",          "en": "Tax returns (company and shareholders)"},
        {"id": "etats_fin_pers",     "fr": "États financiers personnels des actionnaires",               "en": "Personal financial statements of shareholders"},
        {"id": "liquidites",         "fr": "Preuve de liquidités",                                       "en": "Proof of liquidity"},
        {"id": "actifs_passifs",     "fr": "Liste des actifs et passifs",                                "en": "List of assets and liabilities"},
        {"id": "acte_terrain",       "fr": "Acte d'achat du terrain ou promesse d'achat",               "en": "Land deed or purchase offer"},
        {"id": "cert_localisation",  "fr": "Certificat de localisation",                                 "en": "Certificate of location"},
        {"id": "rapport_titre",      "fr": "Rapport de titre (ou recherche de titres)",                 "en": "Title report or title search"},
        {"id": "taxes",              "fr": "Comptes de taxes municipales et scolaires + preuves de paiement", "en": "Municipal/school tax accounts + payment proofs"},
        {"id": "zonage",             "fr": "Zonage municipal",                                           "en": "Municipal zoning"},
        {"id": "servitudes",         "fr": "Servitudes enregistrées (si applicable)",                    "en": "Registered easements (if applicable)"},
        {"id": "plan_terrain",       "fr": "Plan du terrain (cadastre)",                                 "en": "Land survey (cadastral plan)"},
        {"id": "faisabilite",        "fr": "Étude de faisabilité (si disponible)",                       "en": "Feasibility study (if available)"},
        {"id": "plan_developpement", "fr": "Plan de développement projeté (si applicable)",              "en": "Projected development plan (if applicable)"},
        {"id": "evaluation",         "fr": "Rapport d'évaluation",                                       "en": "Appraisal report"},
        {"id": "valeur_actuelle",    "fr": "Valeur actuelle du terrain",                                 "en": "Current land value"},
        {"id": "valeur_projetee",    "fr": "Valeur projetée (si applicable)",                            "en": "Projected value (if applicable)"},
        {"id": "geotechnique",       "fr": "Étude géotechnique (si disponible)",                         "en": "Geotechnical study (if available)"},
        {"id": "env_phase1",         "fr": "Étude environnementale Phase I (Phase II si applicable)",   "en": "Phase I Environmental Study (Phase II if applicable)"},
        {"id": "pro_forma",          "fr": "Pro forma du projet (si développement prévu)",               "en": "Project pro forma (if development planned)"},
        {"id": "previsions_sortie",  "fr": "Prévisions de sortie (vente ou refinancement)",              "en": "Exit strategy projections (sale or refinancing)"},
    ],
}

# Liste générique (fallback si type inconnu)
DOCS_REQUIS_DEFAUT = [
    {"id": "etats_fin_co",   "fr": "États financiers (2 dernières années)",       "en": "Financial statements (last 2 years)"},
    {"id": "decl_fisc",      "fr": "Déclarations fiscales (2 ans)",               "en": "Tax returns (2 years)"},
    {"id": "etats_fin_pers", "fr": "États financiers personnels",                 "en": "Personal financial statements"},
    {"id": "evaluation",     "fr": "Rapport d'évaluation indépendant",            "en": "Independent appraisal report"},
    {"id": "liquidites",     "fr": "Preuve de liquidités / mise de fonds",        "en": "Proof of liquidity / down payment"},
    {"id": "cv",             "fr": "CV / profil de l'emprunteur",                 "en": "Borrower CV / profile"},
]

# Catalogue UNIFIÉ de tous les types de documents possibles (tous les IDs uniques)
# Utilisé par classify_doc() pour la classification multi-types.
# Construit dynamiquement à partir de DOCS_REQUIS_BY_TYPE + DOCS_REQUIS_DEFAUT.
def _build_docs_requis_unifie():
    seen = {}
    for type_list in DOCS_REQUIS_BY_TYPE.values():
        for d in type_list:
            if d["id"] not in seen:
                seen[d["id"]] = d
    for d in DOCS_REQUIS_DEFAUT:
        if d["id"] not in seen:
            seen[d["id"]] = d
    # Ajouter le CV explicitement (présent dans DEFAUT mais souvent reçu hors checklist standard)
    return list(seen.values())

DOCS_REQUIS = _build_docs_requis_unifie()  # ← NOM utilisé par classify_doc() ; correctif bug 2026-05-05

def get_docs_requis(loan_type: str) -> list:
    """Retourne la liste de documents requis selon le type de prêt."""
    # Normalisation : "construction" → "Construction", etc.
    t = (loan_type or "").strip().lower()
    mapping = {
        "construction": "Construction",
        "infrastructure": "Infrastructure",
        "commercial": "Commercial",
        "multilogement": "Multilogement",
        "multi-logement": "Multilogement",
        "refinancement": "Refinancement",
        "pont": "Bridge",
        "bridge": "Bridge",
        "terrain": "Terrain",
        "land": "Terrain",
    }
    canonical = mapping.get(t, loan_type)
    return DOCS_REQUIS_BY_TYPE.get(canonical, DOCS_REQUIS_DEFAUT)

# ── État local (JSON) ─────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"processed": [], "dossiers": {}}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

# ── Gmail IMAP ────────────────────────────────────────────────────────────────
def fetch_new_emails() -> list:
    """Retourne les nouveaux emails non lus avec pièces jointes PDF."""
    state = load_state()
    results = []

    try:
        imap = imaplib.IMAP4_SSL(MAIL_HOST)
        imap.login(MAIL_USER, MAIL_PASSWORD)
        imap.select("INBOX")

        _, msg_ids = imap.search(None, "UNSEEN")
        if not msg_ids[0]:
            log.info("Aucun nouveau courriel.")
            imap.logout()
            return []

        for mid in msg_ids[0].split():
            mid_str = mid.decode()
            if mid_str in state["processed"]:
                continue

            _, data = imap.fetch(mid, "(RFC822)")
            raw = data[0][1]
            msg = email_lib.message_from_bytes(raw)

            # Décodage du sujet
            subj_parts = decode_header(msg.get("Subject", ""))
            subject = ""
            for part, enc in subj_parts:
                if isinstance(part, bytes):
                    subject += part.decode(enc or "utf-8", errors="replace")
                else:
                    subject += str(part)

            # Expéditeur
            from_raw = msg.get("From", "")
            if "<" in from_raw:
                sender_email = from_raw.split("<")[-1].replace(">", "").strip().lower()
                sender_name  = from_raw.split("<")[0].strip().strip('"')
            else:
                sender_email = from_raw.strip().lower()
                sender_name  = sender_email

            # Ignorer nos propres emails
            if MAIL_USER.lower() in sender_email:
                state["processed"].append(mid_str)
                continue

            # Pièces jointes PDF
            attachments = []
            for part in msg.walk():
                fname = part.get_filename()
                if fname and fname.lower().endswith(".pdf"):
                    payload = part.get_payload(decode=True)
                    if payload:
                        attachments.append({"filename": fname, "data": payload})

            if not attachments:
                log.info(f"Email sans PDF de {sender_email} — ignoré.")
                state["processed"].append(mid_str)
                continue

            # Corps du message
            body = ""
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    except Exception:
                        pass
                    break

            results.append({
                "msg_id":       mid_str,
                "sender_email": sender_email,
                "sender_name":  sender_name,
                "subject":      subject,
                "body":         body[:400],
                "attachments":  attachments,
            })

        imap.logout()

    except Exception as e:
        log.error(f"Erreur IMAP: {e}")

    return results

# ── Lecture PDF ───────────────────────────────────────────────────────────────
def extract_pdf_text(data: bytes, max_chars: int = 3000) -> str:
    try:
        reader = PdfReader(BytesIO(data))
        text = ""
        for page in reader.pages[:5]:
            text += page.extract_text() or ""
            if len(text) >= max_chars:
                break
        return text[:max_chars]
    except Exception as e:
        return f"[Erreur PDF: {e}]"

# ── Détection de langue ───────────────────────────────────────────────────────
def detect_language(subject: str, body: str) -> str:
    """Retourne 'fr' ou 'en' selon la langue du courriel du client."""
    text = (subject + " " + body).lower()
    fr_words = ["bonjour", "merci", "votre", "nous", "notre", "projet", "prêt",
                "demande", "financement", "veuillez", "cordialement", "salut"]
    en_words = ["hello", "please", "thank", "our", "your", "project", "loan",
                "request", "financing", "regards", "dear", "attached"]
    fr_score = sum(1 for w in fr_words if w in text)
    en_score = sum(1 for w in en_words if w in text)
    return "en" if en_score > fr_score else "fr"

# ── Classification document ───────────────────────────────────────────────────
def classify_doc(filename: str, pdf_text: str, ai: anthropic.Anthropic) -> str:
    """Identifie le type de document avec Claude. Retourne l'ID ou 'autre'."""
    ids = [d["id"] for d in DOCS_REQUIS]
    choices = "\n".join(f'- {d["id"]}: {d["fr"]} / {d["en"]}' for d in DOCS_REQUIS)

    prompt = (
        f"Tu analyses un document reçu pour Capital Norvex (prêteur hypothécaire privé).\n\n"
        f"Nom du fichier: {filename}\n"
        f"Contenu (début):\n{pdf_text[:1500]}\n\n"
        f"Identifie le type de document. Réponds UNIQUEMENT avec l'ID exact:\n"
        f"{choices}\n- autre: tout autre document\n\n"
        f"Réponse (un seul mot):"
    )

    try:
        resp = ai.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=15,
            messages=[{"role": "user", "content": prompt}]
        )
        result = resp.content[0].text.strip().lower().split()[0]
        return result if result in ids else "autre"
    except Exception as e:
        log.error(f"Erreur classification: {e}")
        return "autre"

# ── Docs manquants ────────────────────────────────────────────────────────────
def get_missing(docs_recus: list, checklist: list = None) -> list:
    if checklist is None:
        checklist = DOCS_REQUIS_DEFAUT
    return [d for d in checklist if d["id"] not in docs_recus]

def create_upload_token_url(dossier_id: str, client_nom: str, client_email: str, projet: str, lang: str) :
    """Crée un token de dépôt via Netlify et retourne l'URL publique, ou None si indisponible."""
    try:
        payload = json.dumps({
            "dossierID":   dossier_id,
            "clientNom":   client_nom,
            "clientEmail": client_email,
            "projet":      projet,
            "lang":        lang,
        }).encode()
        req = urllib.request.Request(
            f"{NETLIFY_SITE_URL}/.netlify/functions/create-upload-token",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            url = data.get("url")
            if url:
                log.info(f"🔗  Token dépôt créé pour {client_email} → {url}")
            return url
    except Exception as e:
        log.warning(f"Token dépôt indisponible pour {client_email} : {e}")
        return None

# ── Envoi email ───────────────────────────────────────────────────────────────
def _html_to_text(html: str) -> str:
    """Convertit grossièrement HTML→texte pour fournir une alternative text/plain."""
    import re as _re
    text = _re.sub(r"<br\s*/?>", "\n", html, flags=_re.IGNORECASE)
    text = _re.sub(r"</p>", "\n\n", text, flags=_re.IGNORECASE)
    text = _re.sub(r"</tr>", "\n", text, flags=_re.IGNORECASE)
    text = _re.sub(r"<[^>]+>", "", text)
    text = _re.sub(r"\n{3,}", "\n\n", text)
    text = _re.sub(r"[ \t]+", " ", text)
    return text.strip()

def _add_deliverability_headers(msg, to: str):
    """Ajoute les headers transactionnels pour améliorer la deliverability (Gmail/M365)."""
    from email.utils import formatdate, make_msgid
    msg["Date"]    = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="capitalnorvex.com")
    msg["Reply-To"] = f"Capital Norvex <{MAIL_USER}>"
    msg["List-Unsubscribe"] = f"<mailto:{MAIL_USER}?subject=Unsubscribe>"
    msg["X-Auto-Response-Suppress"] = "All"
    msg["X-Capital-Norvex-Type"] = "transactional"
    msg["Precedence"] = "bulk"

# ── Microsoft Graph — token + envoi via API ──────────────────────────────────
_GRAPH_TOKEN_CACHE = {"token": None, "expires_at": 0}

def get_graph_token() -> str:
    """Récupère un access token pour Microsoft Graph (client_credentials).
    Cache en mémoire pendant ~50 min pour éviter de re-demander à chaque envoi.
    Requiert AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET dans .env.
    """
    import time as _time
    import requests as _requests
    now = _time.time()
    if _GRAPH_TOKEN_CACHE["token"] and now < _GRAPH_TOKEN_CACHE["expires_at"]:
        return _GRAPH_TOKEN_CACHE["token"]
    tenant_id    = os.getenv("AZURE_TENANT_ID")
    client_id    = os.getenv("AZURE_CLIENT_ID")
    client_secret= os.getenv("AZURE_CLIENT_SECRET")
    if not (tenant_id and client_id and client_secret):
        raise RuntimeError("AZURE_TENANT_ID / AZURE_CLIENT_ID / AZURE_CLIENT_SECRET manquants dans .env")
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "grant_type":    "client_credentials",
        "client_id":     client_id,
        "client_secret": client_secret,
        "scope":         "https://graph.microsoft.com/.default",
    }
    r = _requests.post(url, data=data, timeout=30)
    r.raise_for_status()
    payload = r.json()
    token   = payload["access_token"]
    expires = int(payload.get("expires_in", 3600))
    _GRAPH_TOKEN_CACHE["token"]      = token
    _GRAPH_TOKEN_CACHE["expires_at"] = now + max(60, expires - 120)
    return token

def send_email_via_graph(to: str, subject: str, html: str, attachments: list = None) -> bool:
    """Envoie un courriel via Microsoft Graph API (POST /users/{MAIL_USER}/sendMail).
    Contourne le blocage SMTP outbound 5.7.708.
    Retourne True si succès, False si échec.
    """
    import base64 as _b64
    import json as _json
    import urllib.request as _ureq
    import urllib.error as _uerr
    if attachments is None:
        attachments = []
    try:
        token = get_graph_token()
        message = {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html},
            "toRecipients": [{"emailAddress": {"address": to}}],
            "from":         {"emailAddress": {"address": MAIL_USER}},
            "replyTo":      [{"emailAddress": {"address": MAIL_USER}}],
            "internetMessageHeaders": [
                {"name": "X-Capital-Norvex-Type",     "value": "transactional"},
                {"name": "X-Auto-Response-Suppress",  "value": "All"},
            ],
        }
        if attachments:
            graph_atts = []
            for att in attachments:
                content_b64 = _b64.b64encode(att["data"]).decode("ascii")
                graph_atts.append({
                    "@odata.type":  "#microsoft.graph.fileAttachment",
                    "name":         att["filename"],
                    "contentType":  att.get("contentType", "application/pdf"),
                    "contentBytes": content_b64,
                })
            message["attachments"] = graph_atts
        body = _json.dumps({"message": message, "saveToSentItems": True}).encode("utf-8")
        req = _ureq.Request(
            f"https://graph.microsoft.com/v1.0/users/{MAIL_USER}/sendMail",
            data    = body,
            method  = "POST",
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
        )
        with _ureq.urlopen(req, timeout=30) as resp:
            # 202 Accepted = succès
            if resp.status in (200, 202):
                log.info(f"✉  Graph → {to} | {subject} | +{len(attachments)} PJ" if attachments else f"✉  Graph → {to} | {subject}")
                return True
            log.error(f"Graph sendMail status inattendu: {resp.status}")
            return False
    except _uerr.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            err_body = "<no body>"
        log.error(f"Graph sendMail HTTPError {e.code}: {err_body}")
        return False
    except Exception as e:
        log.error(f"Graph sendMail exception: {e}")
        return False

# ── SendGrid — chemin de livraison principal (bypasse M365 outbound) ─────────
def send_email_via_sendgrid(to: str, subject: str, html: str, attachments: list = None) -> bool:
    """Envoie un courriel via SendGrid API (POST /v3/mail/send).
    Bypasse complètement les IPs outbound M365 (qui sont bloquées 5.7.708).
    Retourne True si succès, False si échec.
    """
    import base64 as _b64
    import json as _json
    import requests as _requests
    if attachments is None:
        attachments = []
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        log.error("SENDGRID_API_KEY manquant dans .env")
        return False
    payload = {
        "personalizations": [{"to": [{"email": to}]}],
        "from":    {"email": MAIL_USER, "name": "Capital Norvex"},
        "reply_to":{"email": MAIL_USER, "name": "Capital Norvex"},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": _html_to_text(html)},
            {"type": "text/html",  "value": html},
        ],
        "headers": {
            "X-Capital-Norvex-Type":    "transactional",
            "X-Auto-Response-Suppress": "All",
        },
        "tracking_settings": {
            "click_tracking": {"enable": False, "enable_text": False},
            "open_tracking":  {"enable": False},
        },
    }
    if attachments:
        sg_atts = []
        for att in attachments:
            sg_atts.append({
                "content":     _b64.b64encode(att["data"]).decode("ascii"),
                "type":        att.get("contentType", "application/pdf"),
                "filename":    att["filename"],
                "disposition": "attachment",
            })
        payload["attachments"] = sg_atts
    try:
        r = _requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            data=_json.dumps(payload),
            timeout=30,
        )
        if r.status_code in (200, 202):
            log.info(f"✉  SendGrid → {to} | {subject}" + (f" | +{len(attachments)} PJ" if attachments else ""))
            return True
        log.error(f"SendGrid status {r.status_code}: {r.text[:300]}")
        return False
    except Exception as e:
        log.error(f"SendGrid exception: {e}")
        return False

# ── Wrappers publics : appelés partout dans le code ───────────────────────────
# Stratégie : SendGrid en priorité (réputation IP propre), Graph en fallback.
def send_email_with_attachments(to: str, subject: str, html: str, attachments: list = None):
    """Envoie un email HTML avec pièces jointes PDF — SendGrid d'abord, Graph en fallback."""
    if send_email_via_sendgrid(to, subject, html, attachments):
        return
    log.warning(f"SendGrid a échoué pour {to}, fallback sur Microsoft Graph")
    send_email_via_graph(to, subject, html, attachments)

def send_email(to: str, subject: str, html: str):
    """Envoie un email HTML simple — SendGrid d'abord, Graph en fallback."""
    if send_email_via_sendgrid(to, subject, html, None):
        return
    log.warning(f"SendGrid a échoué pour {to}, fallback sur Microsoft Graph")
    send_email_via_graph(to, subject, html, None)

# ── ANCIENNES fonctions SMTP — gardées pour rollback rapide en cas de besoin ──
def send_email_with_attachments_LEGACY_smtp(to: str, subject: str, html: str, attachments: list = None):
    """[LEGACY] Ancienne version SMTP via smtp.office365.com:587. Bloquée par 5.7.708."""
    if attachments is None:
        attachments = []
    try:
        msg = MIMEMultipart("mixed")
        msg["From"]    = f"Capital Norvex <{MAIL_USER}>"
        msg["To"]      = to
        msg["Subject"] = subject
        _add_deliverability_headers(msg, to)
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(_html_to_text(html), "plain", "utf-8"))
        alt.attach(MIMEText(html, "html", "utf-8"))
        msg.attach(alt)
        for att in attachments:
            part = MIMEApplication(att["data"], Name=att["filename"])
            part["Content-Disposition"] = f'attachment; filename="{att["filename"]}"'
            msg.attach(part)
        with smtplib.SMTP("smtp.office365.com", 587) as srv:
            srv.ehlo()
            srv.starttls()
            srv.login(MAIL_USER, MAIL_PASSWORD)
            srv.sendmail(MAIL_USER, [to], msg.as_string())
        log.info(f"✉  [SMTP-LEGACY] (+{len(attachments)} PJ) → {to} | {subject}")
    except Exception as e:
        log.error(f"[SMTP-LEGACY] Erreur envoi email avec PJ: {e}")

def send_email_LEGACY_smtp(to: str, subject: str, html: str):
    """[LEGACY] Ancienne version SMTP via smtp.office365.com:587. Bloquée par 5.7.708."""
    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = f"Capital Norvex <{MAIL_USER}>"
        msg["To"]      = to
        msg["Subject"] = subject
        _add_deliverability_headers(msg, to)
        msg.attach(MIMEText(_html_to_text(html), "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP("smtp.office365.com", 587) as srv:
            srv.ehlo()
            srv.starttls()
            srv.login(MAIL_USER, MAIL_PASSWORD)
            srv.sendmail(MAIL_USER, [to], msg.as_string())

        log.info(f"✉  [SMTP-LEGACY] → {to} | {subject}")
    except Exception as e:
        log.error(f"[SMTP-LEGACY] Erreur envoi email: {e}")

# ── Email client — docs manquants (template officiel Capital Norvex) ──────────
def _doc_rows(docs: list, lang: str) -> str:
    """Génère les lignes HTML de la liste de documents pour le template."""
    rows = []
    for i, d in enumerate(docs):
        border = "" if i == len(docs) - 1 else "border-bottom:1px solid #f2ede5;"
        name = d["fr"] if lang == "fr" else d["en"]
        rows.append(
            f'<tr><td style="padding:5px 0;font-size:13px;color:#1a1a1a;{border}">'
            f'<span style="display:inline-block;width:6px;height:6px;border-radius:50%;'
            f'background:#C9A84C;margin-right:10px;vertical-align:middle;"></span>'
            f'{name}</td></tr>'
        )
    return "\n".join(rows)

def email_docs_manquants(sender_email: str, sender_name: str, missing: list, lang: str = "fr", upload_url = None):
    prenom = sender_name.split()[0] if sender_name else sender_name
    rows   = _doc_rows(missing, lang)

    if lang == "fr":
        subject      = "Capital Norvex — Bienvenue, voici les prochaines étapes"
        logo_sub     = "Financement Privé Institutionnel &nbsp;·&nbsp; Québec &amp; Ontario"
        greeting     = f"Bienvenue chez Capital Norvex, <strong style=\"color:#C9A84C;\">{prenom}</strong>,"
        intro        = ("Nous avons bien reçu votre demande de financement et nous vous remercions "
                        "de l'intérêt que vous portez à Capital Norvex. Notre équipe a pris connaissance "
                        "de votre dossier. Pour procéder à son analyse complète, nous avons besoin "
                        "des documents suivants :")
        if upload_url:
            cta       = ("Utilisez le bouton ci-dessous pour déposer vos documents de façon sécurisée. "
                         "Le lien est personnel et réservé exclusivement à votre dossier.")
            btn_label = "Déposer mes documents"
        else:
            cta       = ("Veuillez nous transmettre ces documents par retour de courriel à "
                         "<strong style=\"color:#0a0d13;\">info@capitalnorvex.com</strong>.")
            btn_label = None
        sig_name     = "Équipe Capital Norvex"
        footer_right = "Capital structuré. Ambition maîtrisée."
    else:
        subject      = "Capital Norvex — Welcome, here are your next steps"
        logo_sub     = "Institutional Private Lending &nbsp;·&nbsp; Quebec &amp; Ontario"
        greeting     = f"Welcome to Capital Norvex, <strong style=\"color:#C9A84C;\">{prenom}</strong>,"
        intro        = ("Thank you for submitting your financing request to Capital Norvex. "
                        "Our team has received your file. To proceed with a complete analysis, "
                        "we require the following documents:")
        if upload_url:
            cta       = ("Use the button below to securely upload your documents. "
                         "This link is personal and reserved exclusively for your file.")
            btn_label = "Upload my documents"
        else:
            cta       = ("Please send these documents by reply email to "
                         "<strong style=\"color:#0a0d13;\">info@capitalnorvex.com</strong>.")
            btn_label = None
        sig_name     = "Capital Norvex Team"
        footer_right = "Structured Capital. Controlled Ambition."

    upload_btn_html = f"""
              <!-- BOUTON DÉPÔT -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin:24px 0;">
                <tr>
                  <td align="center">
                    <a href="{upload_url}"
                       style="display:inline-block;background-color:#C9A84C;color:#0a0d13;
                              font-family:Arial,sans-serif;font-size:14px;font-weight:700;
                              letter-spacing:1px;text-decoration:none;padding:14px 36px;
                              border-radius:2px;text-transform:uppercase;">
                      {btn_label}
                    </a>
                  </td>
                </tr>
              </table>""" if upload_url else ""

    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background-color:#f0ece4;font-family:Arial,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0ece4;padding:24px 0;">
    <tr>
      <td align="center">
        <table width="620" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:4px;overflow:hidden;border:1px solid #e0d9cc;">

          <!-- HEADER -->
          <tr>
            <td style="background-color:#0a0d13;padding:24px 40px;">
              <table cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding-right:18px;vertical-align:middle;">
                    <img src="https://capitalnorvex.com/norvex-v2/assets/logo.png"
                         alt="Capital Norvex" width="72" height="90"
                         style="display:block;border:0;">
                  </td>
                  <td style="vertical-align:middle;">
                    <p style="margin:0 0 4px 0;font-family:Georgia,serif;font-size:20px;font-weight:700;letter-spacing:3px;color:#C9A84C;text-transform:uppercase;">Capital Norvex</p>
                    <p style="margin:0;font-size:10px;letter-spacing:2px;color:#888888;text-transform:uppercase;">{logo_sub}</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- GOLD BAR -->
          <tr>
            <td style="background:linear-gradient(90deg,#7a5c10 0%,#C9A84C 35%,#e8c97a 50%,#C9A84C 65%,#7a5c10 100%);height:2px;font-size:0;line-height:0;">&nbsp;</td>
          </tr>

          <!-- BODY -->
          <tr>
            <td style="background-color:#fafaf8;padding:32px 40px;">

              <p style="margin:0 0 14px 0;font-family:Georgia,serif;font-size:17px;color:#0a0d13;">{greeting}</p>

              <p style="margin:0 0 18px 0;font-size:13.5px;line-height:1.8;color:#3a3a3a;">{intro}</p>

              <!-- DOC LIST -->
              <table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #e4ddd0;border-left:3px solid #C9A84C;border-radius:0 2px 2px 0;margin-bottom:18px;">
                <tr><td style="padding:16px 20px;">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    {rows}
                  </table>
                </td></tr>
              </table>

              <p style="margin:0 0 24px 0;font-size:13.5px;line-height:1.8;color:#3a3a3a;">{cta}</p>
{upload_btn_html}
              <!-- SIGNATURE -->
              <table width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #e4ddd0;">
                <tr><td style="padding-top:16px;font-size:13.5px;font-weight:600;color:#0a0d13;">{sig_name}</td></tr>
                <tr><td style="font-size:12px;color:#888888;">info@capitalnorvex.com &nbsp;·&nbsp; capitalnorvex.com</td></tr>
              </table>

            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="background-color:#0a0d13;padding:16px 40px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <a href="mailto:info@capitalnorvex.com" style="font-size:11px;color:#C9A84C;text-decoration:none;margin-right:18px;">info@capitalnorvex.com</a>
                    <a href="https://capitalnorvex.com" style="font-size:11px;color:#C9A84C;text-decoration:none;">capitalnorvex.com</a>
                  </td>
                  <td align="right" style="font-size:10px;color:#555555;font-style:italic;letter-spacing:1px;">{footer_right}</td>
                </tr>
              </table>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""

    send_email(sender_email, subject, html)

# ── Norvex Intel™ — Extraction données propriété ─────────────────────────────
def extract_property_data(corpus: str, ai: anthropic.Anthropic) -> dict:
    """Extrait les données clés de la propriété depuis le corpus de PDFs."""
    prompt = f"""Tu analyses des documents de financement immobilier pour Capital Norvex.

Extrait les données suivantes en JSON strict. Utilise null si non disponible.

DOCUMENTS:
{corpus[:8000]}

JSON requis (respecte exactement ces clés):
{{
  "adresse": "adresse complète de la propriété ou null",
  "type_actif": "Multilogement|Commercial|Industriel|Bureau|Terrain|Autre",
  "marche": "nom de la ville/marché",
  "superficie_terrain": null,
  "superficie_batiment": null,
  "annee_construction": null,
  "eval_muni": null,
  "nb_unites": null,
  "revenu_brut_annuel": null,
  "taux_vacance_pct": null,
  "depenses_annuelles": null,
  "cap_rate_marche": null,
  "valeur_demandee": null,
  "req_nom": null,
  "req_statut": null,
  "foncier_date": null,
  "foncier_montant": null
}}

Réponds UNIQUEMENT avec le JSON, aucun texte autour."""
    try:
        resp = ai.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        text = resp.content[0].text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        log.warning(f"   ⚠️  Extraction propriété partielle : {e}")
        return {}


def call_norvex_intel(corpus: str, ai: anthropic.Anthropic) -> str | None:
    """Extrait les données de la propriété et appelle Norvex Intel™ automatiquement."""
    log.info("   🏠  Norvex Intel™ — extraction données propriété...")
    prop = extract_property_data(corpus, ai)

    adresse = prop.get("adresse")
    if not adresse:
        log.info("   ⚠️  Adresse propriété introuvable — Intel ignoré.")
        return None

    # ── Calculs financiers ────────────────────────────────────────────────────
    revenu_brut  = prop.get("revenu_brut_annuel") or 0
    vacance_pct  = prop.get("taux_vacance_pct") or 5.0
    depenses     = prop.get("depenses_annuelles") or 0
    cap_rate     = prop.get("cap_rate_marche") or 6.5
    eval_muni    = prop.get("eval_muni") or 0

    revenu_net    = revenu_brut * (1 - vacance_pct / 100) - depenses
    valeur_revenu = (revenu_net / (cap_rate / 100)) if cap_rate and revenu_net > 0 else 0

    # Approche coût — estimation basique
    superficie_bat = prop.get("superficie_batiment") or 0
    valeur_cout    = superficie_bat * 250 + (eval_muni * 0.25 if eval_muni else 0)

    # Comparables — proxy éval municipale
    valeur_comp = eval_muni * 1.15 if eval_muni else (valeur_revenu * 1.05 if valeur_revenu else 0)

    # Poids de réconciliation selon type d'actif
    type_actif = (prop.get("type_actif") or "Multilogement").lower()
    if "commercial" in type_actif or "bureau" in type_actif or "industriel" in type_actif:
        poids = (55, 25, 20)
    elif "terrain" in type_actif:
        poids = (20, 55, 25)
    else:
        poids = (60, 25, 15)

    vals_dispo    = [v for v in [valeur_revenu, valeur_cout, valeur_comp] if v > 0]
    total_poids   = sum(p for p, v in zip(poids, [valeur_revenu, valeur_cout, valeur_comp]) if v > 0)
    valeur_mid    = (valeur_revenu * poids[0] + valeur_cout * poids[1] + valeur_comp * poids[2]) / 100 if vals_dispo else 0
    valeur_low    = valeur_mid * 0.95
    valeur_high   = valeur_mid * 1.05
    valeur_preteur = valeur_mid * 0.75
    divergence    = ((max(vals_dispo) - min(vals_dispo)) / min(vals_dispo) * 100) if len(vals_dispo) >= 2 else 0

    stress_loyers = ((revenu_brut * 0.9 * (1 - vacance_pct / 100) - depenses) / (cap_rate / 100)) if revenu_brut and cap_rate else 0
    stress_cap    = (revenu_net / ((cap_rate + 1) / 100)) if revenu_net and cap_rate else 0

    # ── Appel Netlify Intel ───────────────────────────────────────────────────
    payload = {
        "sujet": {
            "adresse":             adresse,
            "type_actif":          prop.get("type_actif", "Multilogement"),
            "marche":              prop.get("marche", "Québec"),
            "superficie_terrain":  prop.get("superficie_terrain") or 0,
            "superficie_batiment": superficie_bat,
            "annee_construction":  prop.get("annee_construction") or 0,
            "eval_muni":           eval_muni,
            "req_nom":             prop.get("req_nom") or "N/D",
            "req_statut":          prop.get("req_statut") or "N/D",
            "rbq_numero":          "N/D",
            "rbq_categorie":       "N/D",
            "rbq_statut":          "N/D",
            "foncier_date":        prop.get("foncier_date") or "N/D",
            "foncier_montant":     prop.get("foncier_montant") or 0,
            "judiciaire_notes":    "Analyse automatique agent — vérification manuelle recommandée",
        },
        "revenu":      {},
        "cout":        {},
        "preteur":     {},
        "comparables": [],
        "resultats": {
            "revenu_valeur":   valeur_revenu,
            "noi":             revenu_net,
            "cap_rate":        cap_rate,
            "cout_valeur":     valeur_cout,
            "comp_valeur":     valeur_comp,
            "poids_revenu":    poids[0],
            "poids_cout":      poids[1],
            "poids_comp":      poids[2],
            "valeur_mid":      valeur_mid,
            "valeur_low":      valeur_low,
            "valeur_high":     valeur_high,
            "valeur_preteur":  valeur_preteur,
            "divergence_pct":  round(divergence, 1),
            "flag_divergence": divergence > 10,
            "stress_loyers":   stress_loyers,
            "stress_cap":      stress_cap,
        }
    }

    try:
        req_data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{NETLIFY_SITE_URL}/.netlify/functions/norvex-intel",
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            analysis = data.get("analysis", "")
            if analysis:
                log.info("   ✅  Norvex Intel™ — analyse reçue")
                return analysis
            log.warning(f"   ⚠️  Intel sans résultat : {data}")
            return None
    except Exception as e:
        log.error(f"   ❌  Erreur appel Intel : {e}")
        return None


# ── Analyse complète avec Claude ──────────────────────────────────────────────
def analyze_dossier(dossier_path: Path, dossier: dict, ai: anthropic.Anthropic) -> tuple[str, str | None]:
    """Lit tous les PDFs du dossier et génère un sommaire + analyse Intel pour Yves.

    Sortie en FR ou EN selon dossier['lang'] (défaut: fr).
    """
    corpus = ""
    for pdf_file in sorted(dossier_path.glob("*.pdf")):
        text = extract_pdf_text(pdf_file.read_bytes(), max_chars=4000)
        corpus += f"\n\n{'='*60}\n📄 {pdf_file.name}\n{'='*60}\n{text}"

    _is_en = (dossier.get("lang") or "fr").lower().startswith("en")

    if _is_en:
        prompt = f"""You are the analysis agent for Capital Norvex, an institutional private mortgage lender (Quebec & Ontario).

FILE RECEIVED
Borrower  : {dossier.get('sender_name')} ({dossier.get('sender_email')})
Subject   : {dossier.get('subject')}
Documents : {', '.join(dossier.get('docs_recus', []))}

DOCUMENT CONTENT:
{corpus[:14000]}

---
Produce a complete EXECUTIVE SUMMARY for Yves Barrette (founder of Capital Norvex).

Mandatory structure:

## 📋 FILE SUMMARY
Borrower, project type, location, estimated amount requested.

## 💰 FINANCIAL STRUCTURE
Amount, term, loan type, estimated LTV, debt service coverage ratio if applicable.

## 👤 BORROWER PROFILE
Experience, track record, financial capacity, strengths.

## ⚠️ IDENTIFIED RISKS
Points of attention, inconsistencies, gaps in the file.

## ✅ PRELIMINARY RECOMMENDATION
**GO** / **CONDITIONAL GO** / **NO-GO** — with 2-3 sentence justification.

## 📝 NEXT STEPS
Recommended actions before the Zoom call with the borrower.

Be direct, precise and professional. Use real data from the documents."""
    else:
        prompt = f"""Tu es l'agent d'analyse de Capital Norvex, prêteur hypothécaire privé institutionnel (Québec & Ontario).

DOSSIER REÇU
Emprunteur : {dossier.get('sender_name')} ({dossier.get('sender_email')})
Sujet      : {dossier.get('subject')}
Documents  : {', '.join(dossier.get('docs_recus', []))}

CONTENU DES DOCUMENTS :
{corpus[:14000]}

---
Produis un SOMMAIRE EXÉCUTIF complet pour Yves Barrette (fondateur de Capital Norvex).

Structure obligatoire :

## 📋 RÉSUMÉ DU DOSSIER
Emprunteur, type de projet, localisation, montant demandé estimé.

## 💰 STRUCTURE FINANCIÈRE
Montant, durée, type de prêt, LTV estimé, ratio couverture dette si applicable.

## 👤 PROFIL EMPRUNTEUR
Expérience, réalisations, capacité financière, points forts.

## ⚠️ RISQUES IDENTIFIÉS
Points d'attention, incohérences, manques dans le dossier.

## ✅ RECOMMANDATION PRÉLIMINAIRE
**GO** / **GO CONDITIONNEL** / **NO-GO** — avec justification en 2-3 phrases.

## 📝 PROCHAINES ÉTAPES
Actions recommandées avant le Zoom avec l'emprunteur.

Sois direct, précis et professionnel. Utilise les données réelles des documents."""

    try:
        resp = ai.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}]
        )
        analysis = resp.content[0].text
    except Exception as e:
        log.error(f"Erreur analyse Claude: {e}")
        err_msg = f"⚠️ Error during automated analysis: {e}" if _is_en else f"⚠️ Erreur lors de l'analyse automatique : {e}"
        analysis = err_msg

    # Appel automatique Norvex Intel™
    intel = call_norvex_intel(corpus, ai)

    return analysis, intel

# ── Email sommaire à Yves ─────────────────────────────────────────────────────
def email_sommaire_yves(dossier: dict, analysis: str, intel: str | None = None):
    name     = dossier.get("sender_name", "Emprunteur")
    email_cl = dossier.get("sender_email", "")
    did      = dossier.get("id", "")
    now      = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Markdown simple → HTML
    def md_to_html(text):
        lines = text.split("\n")
        html_lines = []
        for line in lines:
            if line.startswith("## "):
                html_lines.append(f'<h3 style="color:#C9A84C;margin:16px 0 4px">{line[3:]}</h3>')
            elif line.startswith("**") and line.endswith("**"):
                html_lines.append(f'<p><strong>{line[2:-2]}</strong></p>')
            elif line.startswith("- "):
                html_lines.append(f'<li style="margin:3px 0">{line[2:]}</li>')
            elif line.strip():
                html_lines.append(f'<p style="margin:4px 0">{line}</p>')
        return "\n".join(html_lines)

    analysis_html = md_to_html(analysis)
    docs_list = ", ".join(dossier.get("docs_recus", []))

    if intel:
        intel_html = f"""
  <div style="background:#0d1420;border-left:3px solid #C9A84C;margin:0;padding:20px 24px">
    <div style="color:#C9A84C;font-size:11px;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px">
      🏠 Norvex Intel™ — Évaluation immobilière automatique
    </div>
    <div style="color:#d4c9b0;font-size:13px;line-height:1.8;white-space:pre-wrap">{intel}</div>
    <div style="margin-top:12px;font-size:11px;color:#6a7a8a;font-style:italic">
      ⚠️ Évaluation préliminaire basée sur les documents reçus. Données manquantes estimées. Vérification manuelle recommandée.
    </div>
  </div>"""
    else:
        intel_html = ""

    html = f"""
<div style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;border:1px solid #e8e0ce">

  <div style="background:#0a0d13;padding:18px 24px">
    <div style="color:#C9A84C;font-size:20px;font-weight:bold">CAPITAL NORVEX</div>
    <div style="color:#d4c9b0;font-size:11px">Agent Analyse — Nouveau dossier</div>
  </div>

  <div style="background:#C9A84C;padding:10px 24px">
    <span style="color:#0a0d13;font-weight:bold;font-size:13px">
      ✅ DOSSIER REÇU ET ANALYSÉ — {name.upper()}
    </span>
  </div>

  <div style="background:#f5f0e8;padding:14px 24px">
    <table style="font-size:12px;width:100%">
      <tr><td style="color:#8a7d5f;width:130px;padding:3px 0"><b>Emprunteur</b></td><td>{name}</td></tr>
      <tr><td style="color:#8a7d5f;padding:3px 0"><b>Courriel</b></td><td><a href="mailto:{email_cl}" style="color:#C9A84C">{email_cl}</a></td></tr>
      <tr><td style="color:#8a7d5f;padding:3px 0"><b>Dossier No.</b></td><td>{did}</td></tr>
      <tr><td style="color:#8a7d5f;padding:3px 0"><b>Documents reçus</b></td><td>{docs_list}</td></tr>
      <tr><td style="color:#8a7d5f;padding:3px 0"><b>Analysé le</b></td><td>{now}</td></tr>
    </table>
  </div>

  <div style="padding:24px;color:#0a0d13;font-size:13px;line-height:1.6">
    {analysis_html}
  </div>

  {intel_html}

  <div style="background:#f5f0e8;padding:12px 24px;border-top:2px solid #C9A84C">
    <p style="margin:0;font-size:12px;color:#8a7d5f">
      ⚡ <b>Prochaine action :</b> Si tu donnes le GO, l'agent peut réserver automatiquement un Zoom avec l'emprunteur.
      Réponds à ce courriel avec <b>GO</b> pour déclencher la prise de rendez-vous.
    </p>
  </div>

  <div style="background:#0a0d13;padding:12px 24px;text-align:center">
    <div style="color:#d4c9b0;font-size:11px">Capital Norvex — Système automatisé  |  capitalnorvex.com</div>
  </div>
</div>"""

    # Générer le PDF Intel et l'attacher si disponible
    attachments = []
    if intel:
        try:
            intel_pdf_bytes = generate_intel_pdf(dossier, intel)
            attachments.append({"filename": f"NI-Intel-{did}.pdf", "data": intel_pdf_bytes})
            # Stocker le chemin dans le dossier pour le GO
            dossier["intel_text"]    = intel
            dossier["intel_pdf_key"] = did
        except Exception as e:
            log.warning(f"Génération PDF Intel échouée : {e}")

    subj = f"🏦 CN — Dossier analysé : {name} [ID:{did}]"
    if attachments:
        send_email_with_attachments(YVES_EMAIL, subj, html, attachments)
    else:
        send_email(YVES_EMAIL, subj, html)

# ── Traitement principal ──────────────────────────────────────────────────────
def process_new_emails():
    state  = load_state()
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY or ""
    ai     = anthropic.Anthropic()
    emails = fetch_new_emails()

    if not emails:
        return

    for em in emails:
        sender = em["sender_email"]
        log.info(f"📩  {sender} | {em['subject'][:60]}")

        # Créer ou récupérer le dossier
        if sender not in state["dossiers"]:
            dossier_id = f"{datetime.now().strftime('%Y%m')}-{sender.split('@')[0][:14]}"
            state["dossiers"][sender] = {
                "id":           dossier_id,
                "sender_name":  em["sender_name"],
                "sender_email": sender,
                "subject":      em["subject"],
                "docs_recus":   [],
                "status":       "en_attente",
                "created":      datetime.now().isoformat(),
            }

        dossier    = state["dossiers"][sender]
        dossier_id = dossier["id"]
        dos_path   = BASE_DIR / dossier_id
        dos_path.mkdir(parents=True, exist_ok=True)

        # Créer le dossier Bureau dès le premier contact
        desktop_folder = get_desktop_folder(dossier["sender_name"])

        # Sauvegarder et classifier les PDFs
        for att in em["attachments"]:
            fpath = dos_path / att["filename"]
            fpath.write_bytes(att["data"])
            # Copie immédiate sur le Bureau
            (desktop_folder / att["filename"]).write_bytes(att["data"])

            pdf_text = extract_pdf_text(att["data"])
            doc_type = classify_doc(att["filename"], pdf_text, ai)
            log.info(f"   📄  {att['filename']} → {doc_type}")

            if doc_type != "autre" and doc_type not in dossier["docs_recus"]:
                dossier["docs_recus"].append(doc_type)

        # Marquer comme traité
        state["processed"].append(em["msg_id"])

        # Détecter la langue si pas encore fait
        if "lang" not in dossier:
            dossier["lang"] = detect_language(em["subject"], em["body"])
            log.info(f"   🌐  Langue détectée : {dossier['lang'].upper()}")

        # Vérifier la complétude
        checklist = get_docs_requis(dossier.get("type", ""))
        missing = get_missing(dossier["docs_recus"], checklist)

        if missing:
            log.info(f"   ⏳  Manquants : {[d['id'] for d in missing]}")
            upload_url = create_upload_token_url(
                dossier_id   = sender,
                client_nom   = dossier["sender_name"],
                client_email = sender,
                projet       = dossier.get("subject", ""),
                lang         = dossier["lang"],
            )
            email_docs_manquants(sender, dossier["sender_name"], missing, dossier["lang"], upload_url=upload_url)
            dossier["status"] = "en_attente_docs"
        else:
            log.info(f"   ✅  Dossier complet → analyse Claude")
            dossier["status"] = "analyse_en_cours"
            save_state(state)

            analysis, intel = analyze_dossier(dos_path, dossier, ai)

            dossier["status"]   = "analyse_complete"
            dossier["analysed"] = datetime.now().isoformat()

            # Sauvegarder le résumé dans le dossier Bureau
            resume_path = desktop_folder / f"RÉSUMÉ - {dossier['sender_name']}.txt"
            resume_path.write_text(analysis, encoding="utf-8")
            log.info(f"   📁  Résumé sauvegardé → {resume_path}")

            email_sommaire_yves(dossier, analysis, intel)
            log.info(f"   📧  Sommaire envoyé à {YVES_EMAIL}")

        save_state(state)

    log.info(f"Cycle terminé — {len(emails)} courriel(s) traité(s).")

# ── Netlify API helpers ───────────────────────────────────────────────────────

def _netlify_request(path: str, method: str = "GET", data: dict = None) -> dict:
    """Appelle une Netlify Function interne sécurisée."""
    if not INTERNAL_SECRET:
        raise RuntimeError("INTERNAL_SECRET absent du .env")
    url     = f"{NETLIFY_SITE_URL}{path}"
    headers = {"X-Internal-Secret": INTERNAL_SECRET}
    body    = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _download_blob(blob_key: str) -> bytes:
    """Télécharge un fichier depuis Netlify Blobs via get-upload-doc."""
    if not INTERNAL_SECRET:
        raise RuntimeError("INTERNAL_SECRET absent du .env")
    url = f"{NETLIFY_SITE_URL}/.netlify/functions/get-upload-doc?key={urllib.parse.quote(blob_key)}"
    req = urllib.request.Request(url, headers={"X-Internal-Secret": INTERNAL_SECRET})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def _download_score_pdf(key: str, pdf_type: str) -> bytes:
    """Télécharge un PDF déposé lors de l'analyse Score Norvex (blob analysis-results)."""
    if not INTERNAL_SECRET:
        raise RuntimeError("INTERNAL_SECRET absent du .env")
    url = (f"{NETLIFY_SITE_URL}/.netlify/functions/get-score-pdf"
           f"?key={urllib.parse.quote(key)}&type={urllib.parse.quote(pdf_type)}")
    req = urllib.request.Request(url, headers={"X-Internal-Secret": INTERNAL_SECRET})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


# ── Traitement des uploads portail (100 % Netlify Blobs — zéro Firebase) ─────
def process_storage_uploads():
    """Lit la queue Netlify Blobs (pending), télécharge et analyse chaque fichier."""
    if not INTERNAL_SECRET:
        log.warning("INTERNAL_SECRET absent — uploads portail ignorés.")
        return

    ai = anthropic.Anthropic()

    try:
        result = _netlify_request("/.netlify/functions/list-pending")
    except Exception as e:
        log.error(f"Erreur lecture queue: {e}")
        return

    pending = result.get("pending", [])
    state   = load_state()
    processed_count = 0

    for item in pending:
        queue_key    = item.get("queueKey", "")
        dossier_id   = item.get("dossierID", "")
        client_nom   = item.get("clientNom", "")
        client_email = item.get("clientEmail", "")
        item_lang    = item.get("lang", "fr")
        filename     = item.get("filename", "")
        blob_key     = item.get("blobKey", "")

        if not blob_key:
            continue

        log.info(f"📦  Upload portail: {filename} ({client_nom}) → dossier {dossier_id}")

        try:
            # Marquer en_traitement pour éviter double traitement
            _netlify_request("/.netlify/functions/mark-processed", "POST",
                             {"queueKey": queue_key, "status": "en_traitement"})

            # Télécharger le fichier
            file_data = _download_blob(blob_key)

            # Sauvegarder localement
            dos_path = BASE_DIR / dossier_id
            dos_path.mkdir(parents=True, exist_ok=True)
            (dos_path / filename).write_bytes(file_data)

            # Copie immédiate sur le Bureau
            desktop_folder = get_desktop_folder(client_nom or dossier_id)
            (desktop_folder / filename).write_bytes(file_data)

            # Créer ou récupérer le dossier dans l'état local
            key = client_email or dossier_id
            if key not in state["dossiers"]:
                state["dossiers"][key] = {
                    "id":           dossier_id,
                    "sender_name":  client_nom,
                    "sender_email": client_email,
                    "subject":      f"Upload portail — {filename}",
                    "docs_recus":   [],
                    "status":       "en_attente",
                    "created":      datetime.now().isoformat(),
                    "source":       "upload_portail",
                    "lang":         item_lang,
                }
            elif "lang" not in state["dossiers"][key]:
                state["dossiers"][key]["lang"] = item_lang

            dossier = state["dossiers"][key]

            # Classifier le fichier si PDF
            if filename.lower().endswith(".pdf"):
                pdf_text = extract_pdf_text(file_data)
                doc_type = classify_doc(filename, pdf_text, ai)
                log.info(f"   📄  {filename} → {doc_type}")
                if doc_type != "autre" and doc_type not in dossier["docs_recus"]:
                    dossier["docs_recus"].append(doc_type)
            else:
                log.info(f"   📎  {filename} — non-PDF ajouté au dossier")

            # Vérifier la complétude
            checklist = get_docs_requis(dossier.get("type", ""))
            missing = get_missing(dossier["docs_recus"], checklist)

            if missing:
                log.info(f"   ⏳  Manquants : {[d['id'] for d in missing]}")
                upload_url = create_upload_token_url(
                    dossier_id   = dossier_id,
                    client_nom   = client_nom,
                    client_email = client_email,
                    projet       = dossier.get("subject", ""),
                    lang         = dossier.get("lang", "fr"),
                )
                email_docs_manquants(client_email, client_nom, missing,
                                     dossier.get("lang", "fr"), upload_url=upload_url)
                dossier["status"] = "en_attente_docs"
            else:
                log.info(f"   ✅  Dossier complet → analyse Claude")
                dossier["status"] = "analyse_en_cours"
                save_state(state)

                analysis, intel = analyze_dossier(dos_path, dossier, ai)
                dossier["status"]   = "analyse_complete"
                dossier["analysed"] = datetime.now().isoformat()

                # Sauvegarder le résumé dans le dossier Bureau
                resume_path = desktop_folder / f"RÉSUMÉ - {client_nom}.txt"
                resume_path.write_text(analysis, encoding="utf-8")
                log.info(f"   📁  Résumé sauvegardé → {resume_path}")

                email_sommaire_yves(dossier, analysis, intel)
                log.info(f"   📧  Sommaire envoyé à {YVES_EMAIL}")

            # Marquer traité dans la queue
            _netlify_request("/.netlify/functions/mark-processed", "POST",
                             {"queueKey": queue_key, "status": "processed"})

            save_state(state)
            processed_count += 1

        except Exception as e:
            log.error(f"Erreur traitement {filename}: {e}")
            try:
                _netlify_request("/.netlify/functions/mark-processed", "POST",
                                 {"queueKey": queue_key, "status": "error", "error": str(e)})
            except Exception:
                pass

    if processed_count:
        log.info(f"Portail: {processed_count} upload(s) traité(s).")
    else:
        log.info("Portail: aucun nouvel upload.")


def _render_analysis_summary_html(analysis: dict, client_nom: str, dossier_id: str) -> str:
    """Rend un résumé HTML de l'analyse Score Norvex telle que vue par le client."""
    import html as _html
    esc = _html.escape

    decision = analysis.get("decision", "") or ""
    if "APPROUV" in decision.upper() or "APPROVED" in decision.upper():
        col, bg = "#1f7a4d", "#e6f5ee"
    elif "REFUS" in decision.upper() or "DECLINED" in decision.upper():
        col, bg = "#a8323c", "#f9e9eb"
    else:
        col, bg = "#b8860b", "#fdf4dd"

    sn = analysis.get("score_norvex") or {}
    total = sn.get("total")
    taux = sn.get("taux_recommande", "")
    cr = sn.get("criteres") or {}

    crit_labels = [
        ("ltv_garantie", "LTV & Garantie", 25),
        ("capacite_remboursement", "Capacité remboursement", 20),
        ("profil_emprunteur", "Profil emprunteur", 20),
        ("viabilite_projet", "Viabilité du projet", 15),
        ("qualite_propriete", "Qualité & marché", 15),
        ("relation_norvex", "Relation Norvex", 5),
    ]
    crit_rows = ""
    for key, lbl, mx in crit_labels:
        ci = cr.get(key) or {}
        # Clamp défensif : protège les anciens dossiers stockés en Firestore
        # avant la normalisation côté front (capital-norvex-score.html).
        # Garantit qu'on n'affiche jamais un sous-score qui dépasse son maximum
        # (ex. ancien bug "16/15" vu par le client).
        try:
            pts_raw = int(round(float(ci.get("score", 0) or 0)))
        except (TypeError, ValueError):
            pts_raw = 0
        pts = max(0, min(pts_raw, mx))
        comm = ci.get("commentaire", "") or ""
        crit_rows += (
            f'<tr><td style="padding:6px 10px;border-bottom:1px solid #eee">{esc(lbl)}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:right;font-weight:600">{pts} / {mx}</td></tr>'
            + (f'<tr><td colspan="2" style="padding:0 10px 8px;border-bottom:1px solid #eee;color:#555;font-size:12px">{esc(comm)}</td></tr>' if comm else "")
        )

    ratios = analysis.get("ratios") or {}
    ratio_rows = ""
    for lbl, val in [("LTV", ratios.get("ltv")), ("DSCR", ratios.get("dscr")), ("Taux d'endettement", ratios.get("taux_endettement"))]:
        ratio_rows += f'<tr><td style="padding:6px 10px">{esc(lbl)}</td><td style="padding:6px 10px;text-align:right;font-weight:600">{esc(val or "—")}</td></tr>'

    montant_rec = analysis.get("montant_recommande") or 0
    try:
        montant_str = f"{int(montant_rec):,} $".replace(",", " ")
    except Exception:
        montant_str = str(montant_rec)

    def _list_block(title, items, color):
        if not items:
            return ""
        lis = "".join(f"<li style='margin:4px 0'>{esc(str(x))}</li>" for x in items)
        return (
            f'<div style="margin-top:18px"><div style="font-weight:600;color:{color};margin-bottom:6px">{esc(title)}</div>'
            f'<ul style="margin:0;padding-left:20px;color:#333">{lis}</ul></div>'
        )

    forts = _list_block("Points forts", analysis.get("points_forts") or [], "#1f7a4d")
    risques = _list_block("Risques", analysis.get("risques") or [], "#b8860b")
    conds = _list_block("Conditions", analysis.get("conditions") or [], "#7a5c00")

    resume = analysis.get("resume_analyse") or ""
    note = analysis.get("note_analyste") or ""
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    montant_block = (
        f'<div style="margin-top:6px;color:#333">Montant recommandé : <strong>{esc(montant_str)}</strong></div>'
        if montant_rec else ''
    )
    taux_suffix = f" — Taux recommandé : {esc(taux)}" if taux and taux != "N/A" else ""
    # Clamp défensif du total à [0, 100] (anciens dossiers non normalisés)
    if total is not None:
        try:
            _t = int(round(float(total)))
            _t = max(0, min(_t, 100))
            score_str = f"{_t}/100"
        except (TypeError, ValueError):
            score_str = "N/A/100"
    else:
        score_str = "N/A/100"
    resume_block = (
        f'<h2 style="font-size:16px;margin:24px 0 8px">Résumé de l&#39;analyse</h2>'
        f'<p style="background:#fafafa;border:1px solid #eee;padding:12px 14px;font-size:13px;white-space:pre-wrap">{esc(resume)}</p>'
        if resume else ''
    )
    note_block = (
        f'<p style="color:#555;font-size:12px;font-style:italic">Note analyste : {esc(note)}</p>'
        if note else ''
    )
    decision_str = esc(decision) or "—"

    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<title>Analyse Score Norvex — {esc(client_nom)}</title></head>
<body style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;max-width:780px;margin:30px auto;padding:0 20px;color:#222;line-height:1.5">
  <div style="border-bottom:2px solid #b8975a;padding-bottom:14px;margin-bottom:20px">
    <div style="font-size:12px;letter-spacing:.25em;text-transform:uppercase;color:#b8975a">Capital Norvex — Analyse Score Norvex™</div>
    <h1 style="margin:6px 0 0;font-size:22px">{esc(client_nom)} — {esc(dossier_id)}</h1>
    <div style="color:#777;font-size:12px;margin-top:4px">Généré le {generated_at}</div>
  </div>

  <div style="background:{bg};border-left:4px solid {col};padding:14px 18px;margin-bottom:20px">
    <div style="font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:{col}">Décision</div>
    <div style="font-size:18px;font-weight:700;color:{col};margin-top:4px">{decision_str}</div>
    {montant_block}
  </div>

  <h2 style="font-size:16px;margin:20px 0 8px">Score Norvex™ : {score_str}{taux_suffix}</h2>
  <table style="width:100%;border-collapse:collapse;font-size:13px;background:#fafafa;border:1px solid #eee">{crit_rows}</table>

  <h2 style="font-size:16px;margin:24px 0 8px">Ratios financiers</h2>
  <table style="width:100%;border-collapse:collapse;font-size:13px;background:#fafafa;border:1px solid #eee">{ratio_rows}</table>

  {resume_block}
  {note_block}

  {forts}
  {risques}
  {conds}

  <div style="margin-top:30px;padding-top:14px;border-top:1px solid #ddd;color:#888;font-size:11px">
    Document généré automatiquement par l'agent Capital Norvex à partir de l'analyse présentée au client.
  </div>
</body></html>"""


# ── Nouveaux dossiers pipeline (Score Norvex) ─────────────────────────────────
def process_new_pipeline_dossiers():
    """Détecte les nouveaux dossiers créés via Score Norvex et envoie l'email de bienvenue."""
    if not INTERNAL_SECRET:
        log.warning("INTERNAL_SECRET absent — pipeline dossiers ignorés.")
        return

    try:
        data = _netlify_request("/.netlify/functions/get-new-dossiers")
    except Exception as e:
        log.warning(f"get-new-dossiers indisponible : {e}")
        return

    dossiers_list = data.get("dossiers", [])
    if not dossiers_list:
        log.info("Pipeline: aucun nouveau dossier.")
        return

    log.info(f"Pipeline: {len(dossiers_list)} nouveau(x) dossier(s) détecté(s).")

    ai = anthropic.Anthropic()

    for d in dossiers_list:
        dossier_id   = d.get("id", "")
        prenom       = d.get("prenom", "")
        nom          = d.get("nom", "")
        client_nom   = f"{prenom} {nom}".strip()
        client_email = d.get("email", "")
        projet       = d.get("adresse") or d.get("type") or ""
        lang         = d.get("lang", "fr")
        montant      = d.get("montant", "")
        score        = d.get("score")
        decision     = d.get("decision", "")
        loan_type    = d.get("type", "")

        if not client_email:
            log.warning(f"Dossier {dossier_id} sans email — ignoré.")
            continue

        log.info(f"📋  Nouveau dossier pipeline: {client_nom} ({client_email}) — {projet}")

        # Créer le dossier Bureau
        desktop_folder = get_desktop_folder(client_nom or dossier_id)

        # Télécharger et classifier les PDFs déposés lors de l'analyse Score Norvex
        pdf_blobs = d.get("pdfBlobs", [])
        docs_score_norvex = []   # noms de fichiers
        docs_recus_ids    = []   # IDs classifiés (pour soustraire de la checklist)
        for blob in pdf_blobs:
            b_key  = blob.get("key", "")
            b_type = blob.get("type", "blob_ref")
            b_name = blob.get("name", "document.pdf")
            if not b_key:
                continue
            try:
                pdf_data = _download_score_pdf(b_key, b_type)
                # Éviter d'écraser un fichier existant
                dest = desktop_folder / b_name
                if dest.exists():
                    base, ext = b_name.rsplit(".", 1) if "." in b_name else (b_name, "pdf")
                    dest = desktop_folder / f"{base}_score.{ext}"
                dest.write_bytes(pdf_data)
                docs_score_norvex.append(b_name)
                log.info(f"   📄  Score Norvex PDF sauvegardé → {dest.name}")
                # Classifier le document pour savoir ce qu'on a déjà
                pdf_text = extract_pdf_text(pdf_data)
                doc_type = classify_doc(b_name, pdf_text, ai)
                if doc_type != "autre" and doc_type not in docs_recus_ids:
                    docs_recus_ids.append(doc_type)
                    log.info(f"       → classifié : {doc_type}")
            except Exception as e:
                log.warning(f"   ⚠️  Impossible de télécharger {b_name} : {e}")

        # Déterminer les documents manquants selon le type de prêt
        checklist = get_docs_requis(loan_type)
        missing   = get_missing(docs_recus_ids, checklist)
        log.info(f"   📋  Type: {loan_type} — {len(docs_recus_ids)} reçu(s), {len(missing)} manquant(s)")

        # Sauvegarder le résumé INFO dans le dossier Bureau
        info_lines = [
            f"DOSSIER CAPITAL NORVEX — {client_nom}",
            f"{'='*50}",
            f"ID          : {dossier_id}",
            f"Courriel    : {client_email}",
            f"Téléphone   : {d.get('tel','')}",
            f"Projet      : {projet}",
            f"Type        : {loan_type}",
            f"Montant     : {montant}",
            f"Score Norvex: {score}/100" if score else f"Score Norvex: N/A",
            f"Décision    : {decision}",
            f"Créé le     : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"{'='*50}",
        ]
        _is_en = (lang or "fr").lower().startswith("en")
        if docs_score_norvex:
            info_lines.append("Documents received during Score Norvex analysis:" if _is_en
                              else "Documents reçus lors de l'analyse Score Norvex :")
            for doc_name in docs_score_norvex:
                info_lines.append(f"  • {doc_name}")
        else:
            info_lines.append("No document submitted during Score Norvex analysis." if _is_en
                              else "Aucun document déposé lors de l'analyse Score Norvex.")
        info_lines.append("")
        if missing:
            info_lines.append(f"Documents still required ({len(missing)}):" if _is_en
                              else f"Documents encore requis ({len(missing)}) :")
            for m in missing:
                info_lines.append(f"  • {m['en'] if _is_en else m['fr']}")
        else:
            info_lines.append("All documents were received during Score Norvex analysis." if _is_en
                              else "Tous les documents ont été reçus lors de l'analyse Score Norvex.")
        (desktop_folder / "INFO - Score Norvex.txt").write_text(
            "\n".join(info_lines), encoding="utf-8"
        )

        # Sauvegarder le résumé de l'analyse vue par le client + une copie de la LOI
        analysis_raw = d.get("analysisJson") or ""
        if analysis_raw:
            try:
                analysis_obj = json.loads(analysis_raw)
            except Exception as e:
                log.warning(f"   ⚠️  analysisJson illisible pour {dossier_id} : {e}")
                analysis_obj = None
            if analysis_obj:
                try:
                    summary_html = _render_analysis_summary_html(analysis_obj, client_nom, dossier_id)
                    (desktop_folder / "Analyse Score Norvex.html").write_text(summary_html, encoding="utf-8")
                    log.info("   📊  Résumé de l'analyse sauvegardé → Analyse Score Norvex.html")
                except Exception as e:
                    log.warning(f"   ⚠️  Impossible de générer le résumé d'analyse : {e}")
                loi_html = analysis_obj.get("lettre_intention_html") or ""
                if loi_html:
                    try:
                        (desktop_folder / "LOI - Lettre d'intention.html").write_text(loi_html, encoding="utf-8")
                        log.info("   📄  LOI sauvegardée → LOI - Lettre d'intention.html")
                    except Exception as e:
                        log.warning(f"   ⚠️  Impossible de sauvegarder la LOI : {e}")
        else:
            log.info(f"   ℹ️  Aucune analysisJson pour {dossier_id} (dossier antérieur à l'ajout).")

        # Générer le lien de dépôt
        upload_url = create_upload_token_url(
            dossier_id   = dossier_id,
            client_nom   = client_nom,
            client_email = client_email,
            projet       = projet,
            lang         = lang,
        )

        # Envoyer l'email de bienvenue — uniquement les documents manquants
        email_docs_manquants(client_email, client_nom, missing, lang, upload_url=upload_url)
        log.info(f"   ✉  Email de bienvenue envoyé → {client_email}")

        # Marquer dans Firestore : welcomeEmailSent=true, stage='docs'
        try:
            _netlify_request("/.netlify/functions/mark-welcome-sent", "POST",
                             {"dossierId": dossier_id})
            log.info(f"   ✅  Dossier {dossier_id} marqué welcomeEmailSent=true")
        except Exception as e:
            log.error(f"   ⚠️  Impossible de marquer le dossier {dossier_id} : {e}")


# ── Dossiers approuvés → génération automatique des documents ─────────────────
def process_approved_dossiers():
    """Détecte les dossiers approuvés et génère lettre d'engagement + convention."""
    if not INTERNAL_SECRET:
        log.warning("INTERNAL_SECRET absent — dossiers approuvés ignorés.")
        return

    try:
        data = _netlify_request("/.netlify/functions/get-approved-dossiers")
    except Exception as e:
        log.warning(f"get-approved-dossiers indisponible : {e}")
        return

    dossiers_list = data.get("dossiers", [])
    if not dossiers_list:
        log.info("Approuvés: aucun nouveau dossier à traiter.")
        return

    log.info(f"Approuvés: {len(dossiers_list)} dossier(s) à générer.")

    # Import des générateurs de documents
    agent_dir = str(Path(__file__).parent)
    if agent_dir not in __import__("sys").path:
        __import__("sys").path.insert(0, agent_dir)
    try:
        from generate_docs import generate_all_docs
    except ImportError as e:
        log.error(f"Impossible d'importer generate_docs: {e}")
        return
    try:
        from generate_sommaire_partenaire import generate_sommaire_partenaire
        _has_sommaire = True
    except ImportError as e:
        log.warning(f"generate_sommaire_partenaire non disponible : {e}")
        _has_sommaire = False

    for d in dossiers_list:
        dossier_id    = d.get("id", "")
        prenom        = d.get("prenom", "")
        nom           = d.get("nom", "")
        client_nom    = f"{prenom} {nom}".strip()
        client_email  = d.get("email", "")
        lang          = d.get("lang", "fr")
        loan_type     = d.get("type", "")
        partner_email = d.get("partnerEmail", "")
        partner_name  = d.get("partnerName", "")
        partner_lang  = d.get("partnerLang", "fr")

        if not client_email:
            log.warning(f"Dossier {dossier_id} sans email — ignoré.")
            continue

        log.info(f"📄  Génération docs : {client_nom} ({dossier_id}) — {loan_type}")

        try:
            # Générer les PDFs
            docs = generate_all_docs(d)
            if not docs:
                log.error(f"   ⚠️  Aucun PDF généré pour {dossier_id}")
                continue

            # Sauvegarder dans le dossier Bureau
            desktop_folder = get_desktop_folder(client_nom or dossier_id)
            saved = []
            for filename, pdf_bytes in docs.items():
                if pdf_bytes:
                    out_path = desktop_folder / filename
                    out_path.write_bytes(pdf_bytes)
                    saved.append(out_path)
                    log.info(f"   📁  {filename} → sauvegardé")

            if not saved:
                log.error(f"   ⚠️  Aucun fichier sauvegardé pour {dossier_id}")
                continue

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            attachments = [{"filename": p.name, "data": p.read_bytes()} for p in saved]

            # ── Email à Yves avec tous les docs en pièces jointes ─────────────
            docs_list_html = "".join(f"<li>{p.name}</li>" for p in saved)
            html_yves = f"""
<div style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;border:1px solid #e8e0ce">
  <div style="background:#0a0d13;padding:18px 24px">
    <div style="color:#C9A84C;font-size:20px;font-weight:bold">CAPITAL NORVEX</div>
    <div style="color:#d4c9b0;font-size:11px">Agent — Documents générés automatiquement</div>
  </div>
  <div style="background:#C9A84C;padding:10px 24px">
    <span style="color:#0a0d13;font-weight:bold;font-size:13px">
      📄 DOCUMENTS GÉNÉRÉS — {client_nom.upper()}
    </span>
  </div>
  <div style="background:#f5f0e8;padding:14px 24px">
    <table style="font-size:12px;width:100%">
      <tr><td style="color:#8a7d5f;width:140px;padding:3px 0"><b>Client</b></td><td>{client_nom}</td></tr>
      <tr><td style="color:#8a7d5f;padding:3px 0"><b>Courriel</b></td><td><a href="mailto:{client_email}" style="color:#C9A84C">{client_email}</a></td></tr>
      <tr><td style="color:#8a7d5f;padding:3px 0"><b>Type de prêt</b></td><td>{loan_type}</td></tr>
      <tr><td style="color:#8a7d5f;padding:3px 0"><b>Dossier No.</b></td><td>{dossier_id}</td></tr>
      <tr><td style="color:#8a7d5f;padding:3px 0"><b>Généré le</b></td><td>{now_str}</td></tr>
    </table>
  </div>
  <div style="padding:16px 24px;color:#0a0d13;font-size:13px;">
    <p><b>Documents ci-joints :</b></p>
    <ul style="margin:4px 0;padding-left:20px">{docs_list_html}</ul>
    <p style="margin-top:14px;color:#555">
      La lettre d'engagement a été envoyée au client à {client_email}.<br>
      La convention est en pièce jointe pour ta révision avant envoi final.
    </p>
  </div>
  <div style="background:#0a0d13;padding:12px 24px;text-align:center">
    <div style="color:#d4c9b0;font-size:11px">Capital Norvex — Agent automatisé | capitalnorvex.com</div>
  </div>
</div>"""
            send_email_with_attachments(
                YVES_EMAIL,
                f"📄 CN — Documents générés : {client_nom}",
                html_yves,
                attachments
            )
            log.info(f"   📧  Docs envoyés à Yves ({len(saved)} PJ)")

            # ── Email au client avec la lettre d'engagement seulement ─────────
            lettre_path = next((p for p in saved if "Engagement" in p.name or "Lettre" in p.name), None)
            if lettre_path:
                if lang == "fr":
                    subj_cl  = "Capital Norvex — Votre lettre d'engagement"
                    prenom_c = prenom or client_nom
                    html_cl  = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0ece4;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0ece4;padding:24px 0;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:4px;border:1px solid #e0d9cc;">
  <tr><td style="background:#0a0d13;padding:24px 40px;">
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="padding-right:18px;vertical-align:middle;">
        <img src="https://capitalnorvex.com/norvex-v2/assets/logo.png" width="52" height="65" style="display:block;border:0;">
      </td>
      <td style="vertical-align:middle;">
        <p style="margin:0 0 4px;font-family:Georgia,serif;font-size:20px;font-weight:700;letter-spacing:3px;color:#C9A84C;text-transform:uppercase;">Capital Norvex</p>
        <p style="margin:0;font-size:10px;letter-spacing:2px;color:#888;text-transform:uppercase;">Financement Privé Institutionnel · Québec &amp; Ontario</p>
      </td>
    </tr></table>
  </td></tr>
  <tr><td style="background:linear-gradient(90deg,#7a5c10,#C9A84C 35%,#e8c97a 50%,#C9A84C 65%,#7a5c10);height:2px;font-size:0;">&nbsp;</td></tr>
  <tr><td style="background:#fafaf8;padding:32px 40px;">
    <p style="margin:0 0 14px;font-family:Georgia,serif;font-size:17px;color:#0a0d13;">Félicitations, <strong style="color:#C9A84C;">{prenom_c}</strong>,</p>
    <p style="margin:0 0 18px;font-size:13.5px;line-height:1.8;color:#3a3a3a;">
      Capital Norvex est heureux de vous transmettre votre <strong>lettre d'engagement préliminaire</strong>
      concernant votre demande de financement. Ce document confirme notre décision préliminaire
      favorable et détaille les prochaines étapes.
    </p>
    <p style="margin:0 0 18px;font-size:13.5px;line-height:1.8;color:#3a3a3a;">
      Veuillez prendre connaissance de la lettre ci-jointe et nous confirmer votre acceptation
      par retour de courriel.
    </p>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin:24px 0;">
      <tr><td align="center">
        <a href="mailto:info@capitalnorvex.com"
           style="display:inline-block;background:#C9A84C;color:#0a0d13;font-family:Arial,sans-serif;font-size:14px;font-weight:700;letter-spacing:1px;text-decoration:none;padding:14px 36px;border-radius:2px;text-transform:uppercase;">
          Confirmer mon acceptation
        </a>
      </td></tr>
    </table>
    <table width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #e4ddd0;">
      <tr><td style="padding-top:16px;font-size:13.5px;font-weight:600;color:#0a0d13;">Équipe Capital Norvex</td></tr>
      <tr><td style="font-size:12px;color:#888;">info@capitalnorvex.com &nbsp;·&nbsp; capitalnorvex.com</td></tr>
    </table>
  </td></tr>
  <tr><td style="background:#0a0d13;padding:16px 40px;">
    <table width="100%"><tr>
      <td><a href="mailto:info@capitalnorvex.com" style="font-size:11px;color:#C9A84C;text-decoration:none;">info@capitalnorvex.com</a></td>
      <td align="right" style="font-size:10px;color:#555;font-style:italic;letter-spacing:1px;">Capital structuré. Ambition maîtrisée.</td>
    </tr></table>
  </td></tr>
</table></td></tr></table>
</body></html>"""
                else:
                    subj_cl  = "Capital Norvex — Your Engagement Letter"
                    prenom_c = prenom or client_nom
                    html_cl  = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0ece4;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0ece4;padding:24px 0;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:4px;border:1px solid #e0d9cc;">
  <tr><td style="background:#0a0d13;padding:24px 40px;">
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="padding-right:18px;vertical-align:middle;">
        <img src="https://capitalnorvex.com/norvex-v2/assets/logo.png" width="52" height="65" style="display:block;border:0;">
      </td>
      <td style="vertical-align:middle;">
        <p style="margin:0 0 4px;font-family:Georgia,serif;font-size:20px;font-weight:700;letter-spacing:3px;color:#C9A84C;text-transform:uppercase;">Capital Norvex</p>
        <p style="margin:0;font-size:10px;letter-spacing:2px;color:#888;text-transform:uppercase;">Institutional Private Lending · Quebec &amp; Ontario</p>
      </td>
    </tr></table>
  </td></tr>
  <tr><td style="background:linear-gradient(90deg,#7a5c10,#C9A84C 35%,#e8c97a 50%,#C9A84C 65%,#7a5c10);height:2px;font-size:0;">&nbsp;</td></tr>
  <tr><td style="background:#fafaf8;padding:32px 40px;">
    <p style="margin:0 0 14px;font-family:Georgia,serif;font-size:17px;color:#0a0d13;">Congratulations, <strong style="color:#C9A84C;">{prenom_c}</strong>,</p>
    <p style="margin:0 0 18px;font-size:13.5px;line-height:1.8;color:#3a3a3a;">
      Capital Norvex is pleased to send you your <strong>preliminary engagement letter</strong>
      regarding your financing application. This document confirms our preliminary
      favourable decision and outlines the next steps.
    </p>
    <p style="margin:0 0 18px;font-size:13.5px;line-height:1.8;color:#3a3a3a;">
      Please review the attached letter and confirm your acceptance by reply email.
    </p>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin:24px 0;">
      <tr><td align="center">
        <a href="mailto:info@capitalnorvex.com"
           style="display:inline-block;background:#C9A84C;color:#0a0d13;font-family:Arial,sans-serif;font-size:14px;font-weight:700;letter-spacing:1px;text-decoration:none;padding:14px 36px;border-radius:2px;text-transform:uppercase;">
          Confirm My Acceptance
        </a>
      </td></tr>
    </table>
    <table width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #e4ddd0;">
      <tr><td style="padding-top:16px;font-size:13.5px;font-weight:600;color:#0a0d13;">Capital Norvex Team</td></tr>
      <tr><td style="font-size:12px;color:#888;">info@capitalnorvex.com &nbsp;·&nbsp; capitalnorvex.com</td></tr>
    </table>
  </td></tr>
  <tr><td style="background:#0a0d13;padding:16px 40px;">
    <table width="100%"><tr>
      <td><a href="mailto:info@capitalnorvex.com" style="font-size:11px;color:#C9A84C;text-decoration:none;">info@capitalnorvex.com</a></td>
      <td align="right" style="font-size:10px;color:#555;font-style:italic;letter-spacing:1px;">Structured Capital. Controlled Ambition.</td>
    </tr></table>
  </td></tr>
</table></td></tr></table>
</body></html>"""

                send_email_with_attachments(
                    client_email, subj_cl, html_cl,
                    [{"filename": lettre_path.name, "data": lettre_path.read_bytes()}]
                )
                log.info(f"   📧  Lettre d'engagement → {client_email}")

            # ── Sommaire exécutif partenaire ──────────────────────────────────
            if partner_email and _has_sommaire:
                try:
                    sommaire_bytes = generate_sommaire_partenaire(d, lang=partner_lang,
                                                                   partner_name=partner_name or partner_email)
                    today_str  = datetime.now().strftime("%Y%m%d")
                    client_key = (prenom + "_" + nom).replace(" ", "_").strip("_")
                    sommaire_fn = f"SommaireExecutif_{client_key}_{today_str}.pdf"

                    # Sauvegarder localement
                    sommaire_path = get_desktop_folder(client_nom or dossier_id) / sommaire_fn
                    sommaire_path.write_bytes(sommaire_bytes)
                    log.info(f"   📁  {sommaire_fn} → sauvegardé")

                    # Email au partenaire
                    if partner_lang == "en":
                        subj_p = f"Capital Norvex — Investment Opportunity: {client_nom}"
                        intro_p = (f"Please find enclosed the executive summary for the financing opportunity "
                                   f"<b>{client_nom}</b> — <b>{loan_type}</b>.<br><br>"
                                   f"We invite you to review this document and confirm your interest.")
                        btn_p = "Confirm My Interest"
                    else:
                        subj_p = f"Capital Norvex — Opportunité d'investissement : {client_nom}"
                        intro_p = (f"Veuillez trouver ci-joint le sommaire exécutif pour l'opportunité de "
                                   f"financement <b>{client_nom}</b> — <b>{loan_type}</b>.<br><br>"
                                   f"Nous vous invitons à prendre connaissance de ce document et à confirmer votre intérêt.")
                        btn_p = "Confirmer Mon Intérêt"

                    html_partner = f"""
<div style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;border:1px solid #e8e0ce">
  <div style="background:#0a0d13;padding:18px 24px">
    <div style="color:#C9A84C;font-size:20px;font-weight:bold">CAPITAL NORVEX</div>
    <div style="color:#d4c9b0;font-size:11px">Financement Privé Institutionnel | Québec &amp; Ontario</div>
  </div>
  <div style="background:#C9A84C;padding:10px 24px">
    <span style="color:#0a0d13;font-weight:bold;font-size:13px">SOMMAIRE EXÉCUTIF — {client_nom.upper()}</span>
  </div>
  <div style="background:#f5f0e8;padding:20px 24px;font-size:13px;line-height:1.8;color:#3a3a3a;">
    <p>{intro_p}</p>
    <table style="margin:20px 0;font-size:12px;width:100%">
      <tr><td style="color:#8a7d5f;width:140px;padding:3px 0"><b>Dossier No.</b></td><td>CN-{dossier_id}</td></tr>
      <tr><td style="color:#8a7d5f;padding:3px 0"><b>Type</b></td><td>{loan_type}</td></tr>
      <tr><td style="color:#8a7d5f;padding:3px 0"><b>Localisation</b></td><td>{d.get("adresse","")}</td></tr>
    </table>
    <div style="text-align:center;margin:20px 0">
      <a href="mailto:info@capitalnorvex.com" style="display:inline-block;background:#C9A84C;color:#0a0d13;font-weight:bold;font-size:13px;text-decoration:none;padding:12px 32px;border-radius:2px">{btn_p}</a>
    </div>
  </div>
  <div style="background:#0a0d13;padding:12px 24px;text-align:center">
    <div style="color:#d4c9b0;font-size:11px">Capital Norvex | capitalnorvex.com | info@capitalnorvex.com</div>
  </div>
</div>"""
                    send_email_with_attachments(
                        partner_email, subj_p, html_partner,
                        [{"filename": sommaire_fn, "data": sommaire_bytes}]
                    )
                    log.info(f"   📧  Sommaire exécutif → {partner_email}")
                except Exception as e:
                    log.error(f"   ⚠️  Erreur sommaire partenaire {dossier_id} : {e}")
            elif partner_email and not _has_sommaire:
                log.warning(f"   ⚠️  partnerEmail présent mais generate_sommaire_partenaire non importé")

            # ── Marquer dans Firestore ────────────────────────────────────────
            try:
                _netlify_request("/.netlify/functions/mark-docs-generated", "POST",
                                 {"dossierId": dossier_id})
                log.info(f"   ✅  Dossier {dossier_id} → stage=engagement, documentsGenerated=true")
            except Exception as e:
                log.error(f"   ⚠️  Impossible de marquer {dossier_id} : {e}")

        except Exception as e:
            log.error(f"Erreur génération docs {dossier_id} : {e}")


# ── Notifications Norvex Track™ ───────────────────────────────────────────────
def process_track_alerts():
    """
    Lit les trackAlerts Firestore (status='pending'), envoie les emails
    appropriés à Yves, puis marque chaque alerte comme 'processed'.
    """
    if not INTERNAL_SECRET:
        log.warning("INTERNAL_SECRET absent — trackAlerts ignorés.")
        return
    if not YVES_EMAIL:
        log.warning("YVES_EMAIL absent — trackAlerts ignorés.")
        return

    try:
        result = _netlify_request("/.netlify/functions/get-track-alerts")
    except Exception as e:
        log.error(f"Erreur lecture trackAlerts : {e}")
        return

    alerts = result.get("alerts", [])
    if not alerts:
        return

    log.info(f"📬  {len(alerts)} alerte(s) Track à traiter")

    for alert in alerts:
        alert_id   = alert.get("_id", "")
        alert_type = alert.get("type", "")
        dossier_name = alert.get("dossierName", alert.get("dossierId", "—"))
        dossier_id   = alert.get("dossierId", "")
        montant      = float(alert.get("montant", 0))
        montant_fmt  = f"{montant:,.0f} $".replace(",", " ")

        try:
            if alert_type == "nouvelle_demande":
                nb_postes = alert.get("nbPostes", 0)
                subject = f"🔔 Norvex Track™ — Nouvelle demande de débourse | {dossier_name}"
                html = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#faf8f4;border:1px solid #e8e3da">
  <div style="background:#0a0d13;padding:20px 24px">
    <div style="font-family:Georgia,serif;font-size:20px;color:#b8975a">Capital <em>Norvex</em></div>
    <div style="font-size:10px;letter-spacing:3px;color:#7a8294;text-transform:uppercase;margin-top:4px">Norvex Track™ — Notification automatique</div>
  </div>
  <div style="padding:28px 24px">
    <div style="font-size:14px;font-weight:600;color:#0a0d13;margin-bottom:8px">🔔 Nouvelle demande de débourse soumise</div>
    <p style="font-size:13px;color:#3d4455;line-height:1.6">Un client vient de soumettre une demande de débourse pour le dossier <strong>{dossier_name}</strong> ({dossier_id}).</p>
    <div style="background:#fff;border:1px solid #e8e3da;padding:16px;margin:16px 0">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
        <div><div style="font-size:10px;letter-spacing:2px;color:#7a8294;text-transform:uppercase">Dossier</div><div style="font-size:16px;font-weight:600;color:#0a0d13">{dossier_name}</div></div>
        <div><div style="font-size:10px;letter-spacing:2px;color:#7a8294;text-transform:uppercase">Montant demandé</div><div style="font-size:16px;font-weight:600;color:#b8975a">{montant_fmt}</div></div>
      </div>
      <div style="margin-top:8px;font-size:11px;color:#7a8294">{nb_postes} poste(s) de construction inclus</div>
    </div>
    <p style="font-size:13px;color:#3d4455">Connectez-vous à <strong>capitalnorvex.com/capital-norvex-track.html</strong> pour approuver ou refuser la demande.</p>
  </div>
  <div style="background:#0a0d13;padding:12px 24px;text-align:center">
    <div style="color:#d4c9b0;font-size:11px">Capital Norvex | capitalnorvex.com | info@capitalnorvex.com</div>
  </div>
</div>"""
                send_email(YVES_EMAIL, subject, html)

            elif alert_type == "approuve_yves":
                subject = f"✅ Norvex Track™ — Demande approuvée — En attente partenaire | {dossier_name}"
                html = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#faf8f4;border:1px solid #e8e3da">
  <div style="background:#0a0d13;padding:20px 24px">
    <div style="font-family:Georgia,serif;font-size:20px;color:#b8975a">Capital <em>Norvex</em></div>
    <div style="font-size:10px;letter-spacing:3px;color:#7a8294;text-transform:uppercase;margin-top:4px">Norvex Track™ — Notification automatique</div>
  </div>
  <div style="padding:28px 24px">
    <div style="font-size:14px;font-weight:600;color:#2e86c1;margin-bottom:8px">✅ Demande approuvée par Capital Norvex — Transfert au partenaire requis</div>
    <p style="font-size:13px;color:#3d4455;line-height:1.6">La demande de débourse de <strong>{montant_fmt}</strong> pour le dossier <strong>{dossier_name}</strong> a été approuvée. Le partenaire financier doit maintenant autoriser le transfert.</p>
    <p style="font-size:13px;color:#3d4455">Transmettez le lien partenaire pour qu'il puisse autoriser le transfert via Norvex Track™.</p>
  </div>
  <div style="background:#0a0d13;padding:12px 24px;text-align:center">
    <div style="color:#d4c9b0;font-size:11px">Capital Norvex | capitalnorvex.com | info@capitalnorvex.com</div>
  </div>
</div>"""
                send_email(YVES_EMAIL, subject, html)

            elif alert_type == "approuve_final":
                subject = f"🚀 Norvex Track™ — PRÊT POUR TRANSFERT | {dossier_name}"
                html = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#faf8f4;border:1px solid #e8e3da">
  <div style="background:#0a0d13;padding:20px 24px">
    <div style="font-family:Georgia,serif;font-size:20px;color:#b8975a">Capital <em>Norvex</em></div>
    <div style="font-size:10px;letter-spacing:3px;color:#7a8294;text-transform:uppercase;margin-top:4px">Norvex Track™ — Notification automatique</div>
  </div>
  <div style="padding:28px 24px">
    <div style="font-size:14px;font-weight:600;color:#2d6a4f;margin-bottom:8px">🚀 TRANSFERT AUTORISÉ — Action requise</div>
    <p style="font-size:13px;color:#3d4455;line-height:1.6">La demande de débourse de <strong>{montant_fmt}</strong> pour le dossier <strong>{dossier_name}</strong> a été approuvée par le partenaire financier.</p>
    <div style="background:#f0fdf4;border:1px solid #a7f3d0;padding:16px;margin:16px 0;border-left:4px solid #2d6a4f">
      <strong style="color:#2d6a4f">Action requise :</strong><span style="color:#3d4455"> Effectuez le virement de <strong>{montant_fmt}</strong> et marquez la demande comme "Transférée" dans Norvex Track™.</span>
    </div>
    <p style="font-size:13px;color:#3d4455">N'oubliez pas d'exiger la quittance après le transfert pour débloquer les postes concernés.</p>
  </div>
  <div style="background:#0a0d13;padding:12px 24px;text-align:center">
    <div style="color:#d4c9b0;font-size:11px">Capital Norvex | capitalnorvex.com | info@capitalnorvex.com</div>
  </div>
</div>"""
                send_email(YVES_EMAIL, subject, html)

            else:
                log.info(f"   ℹ️  Type d'alerte inconnu : {alert_type} — ignoré")
                _netlify_request("/.netlify/functions/mark-track-alert", "POST",
                                 {"alertId": alert_id, "status": "processed"})
                continue

            # Marquer comme traité
            _netlify_request("/.netlify/functions/mark-track-alert", "POST",
                             {"alertId": alert_id, "status": "processed"})
            log.info(f"   ✅  Alerte {alert_type} traitée — {dossier_name} {montant_fmt}")

        except Exception as e:
            log.error(f"   ⚠️  Erreur traitement alerte {alert_id} ({alert_type}) : {e}")



# ── Génération PDF Intel (reportlab) ─────────────────────────────────────────
def generate_intel_pdf(dossier: dict, intel_text: str) -> bytes:
    """Génère le rapport Norvex Intel™ en PDF professionnel."""
    from io import BytesIO as _BIO
    buf = _BIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            topMargin=0.55*inch, bottomMargin=0.55*inch,
                            leftMargin=0.8*inch, rightMargin=0.8*inch)

    GOLD = colors.HexColor("#C9A84C")
    INK  = colors.HexColor("#0a0d13")
    CREAM= colors.HexColor("#faf8f4")
    MUTED= colors.HexColor("#7a8294")

    s_title  = ParagraphStyle("ct", fontName="Helvetica-Bold", fontSize=18, textColor=GOLD,
                               spaceAfter=2, alignment=TA_CENTER)
    s_sub    = ParagraphStyle("cs", fontName="Helvetica", fontSize=7.5, textColor=MUTED,
                               spaceAfter=2, alignment=TA_CENTER, charSpace=2)
    s_sect   = ParagraphStyle("cc", fontName="Helvetica-Bold", fontSize=9.5, textColor=GOLD,
                               spaceBefore=14, spaceAfter=4, charSpace=1)
    s_body   = ParagraphStyle("cb", fontName="Helvetica", fontSize=9, textColor=INK,
                               leading=14, spaceAfter=4)
    s_bold   = ParagraphStyle("cbold", fontName="Helvetica-Bold", fontSize=9, textColor=INK,
                               leading=14, spaceAfter=4)
    s_note   = ParagraphStyle("cn", fontName="Helvetica-Oblique", fontSize=7.5, textColor=MUTED,
                               spaceBefore=8, alignment=TA_CENTER)

    name     = dossier.get("sender_name", "N/D")
    did      = dossier.get("id", "")
    now      = datetime.now().strftime("%Y-%m-%d")

    story = []
    story.append(Paragraph("CAPITAL NORVEX", s_title))
    story.append(Paragraph("NORVEX INTEL™  ·  RAPPORT D'ÉVALUATION IMMOBILIÈRE", s_sub))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=10))

    # Info dossier
    story.append(Paragraph("INFORMATIONS DU DOSSIER", s_sect))
    tbl_data = [
        ["Emprunteur",    name],
        ["Dossier No.",   did],
        ["Date rapport",  now],
        ["Confidentiel",  "Usage interne Capital Norvex & partenaires autorisés"],
    ]
    tbl = Table(tbl_data, colWidths=[1.5*inch, 5.2*inch])
    tbl.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",  (1,0), (1,-1), "Helvetica"),
        ("FONTSIZE",  (0,0), (-1,-1), 9),
        ("TEXTCOLOR", (0,0), (0,-1), GOLD),
        ("TEXTCOLOR", (1,0), (1,-1), INK),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [CREAM, colors.white]),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e8e3da")))

    # Analyse Intel
    story.append(Paragraph("ANALYSE IA — NORVEX INTEL™", s_sect))
    for line in intel_text.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 4))
            continue
        # Détecter les titres en gras (**Titre**)
        if line.startswith("**") and line.endswith("**"):
            story.append(Paragraph(line[2:-2], s_bold))
        else:
            # Remplacer **bold** inline
            import re as _re
            line = _re.sub(r"\*\*(.+?)\*\*", lambda m: f"<b>{m.group(1)}</b>", line)
            story.append(Paragraph(line, s_body))

    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e8e3da")))
    story.append(Paragraph(
        "⚠️  Évaluation préliminaire générée automatiquement par Norvex Intel™. "
        "Certaines données ont été estimées à partir des documents reçus. "
        "Vérification manuelle recommandée avant toute décision finale.",
        s_note))

    doc.build(story)
    return buf.getvalue()


# ── Convention partenaire selon type de prêt ─────────────────────────────────
def get_convention_pdf(loan_type: str) -> bytes | None:
    """Retourne les bytes de la convention partenaire selon le type de prêt."""
    t = (loan_type or "").lower()
    if any(k in t for k in ["construction", "bridge", "pont", "infrastructure"]):
        path = CONVENTION_CONSTRUCTION
    else:
        path = CONVENTION_DEFAULT
    if path.exists():
        return path.read_bytes()
    # Fallback sur l'autre
    fallback = CONVENTION_DEFAULT if path != CONVENTION_DEFAULT else CONVENTION_CONSTRUCTION
    if fallback.exists():
        return fallback.read_bytes()
    log.warning(f"Convention PDF introuvable : {path}")
    return None


def get_sommaire_part_pdf(lang: str = "fr") -> bytes | None:
    """Retourne le PDF sommaire partenaire template."""
    path = SOMMAIRE_PART_FR if lang != "en" else SOMMAIRE_PART_EN
    if path.exists():
        return path.read_bytes()
    log.warning(f"Sommaire partenaire PDF introuvable : {path}")
    return None


# ── Email partenaire : Intel PDF + Convention + Sommaire ──────────────────────
def email_intel_partenaire(partenaire_email: str, partenaire_nom: str,
                           dossier: dict, intel_text: str, lang: str = "fr"):
    """Envoie le rapport Intel + Convention + Sommaire au partenaire."""
    name       = dossier.get("sender_name", "Dossier")
    did        = dossier.get("id", "")
    loan_type  = dossier.get("type", "")
    prenom_part = partenaire_nom.split()[0] if partenaire_nom else partenaire_nom

    attachments = []

    # 1) PDF Intel
    try:
        intel_pdf = generate_intel_pdf(dossier, intel_text)
        attachments.append({"filename": f"NI-Intel-{did}.pdf", "data": intel_pdf})
    except Exception as e:
        log.warning(f"PDF Intel non généré : {e}")

    # 2) Convention partenaire
    conv_pdf = get_convention_pdf(loan_type)
    if conv_pdf:
        attachments.append({"filename": "Convention_Partenariat_CapitalNorvex.pdf", "data": conv_pdf})

    # 3) Sommaire exécutif template
    somm_pdf = get_sommaire_part_pdf(lang)
    if somm_pdf:
        attachments.append({"filename": "SommaireExecutif_CapitalNorvex.pdf", "data": somm_pdf})

    if lang == "fr":
        subject = f"Capital Norvex — Opportunité d'investissement | Dossier {did}"
        greeting = f"Bonjour <strong>{prenom_part}</strong>,"
        intro = (f"Suite à notre analyse du dossier <strong>{name}</strong>, "
                 f"nous vous faisons parvenir l'évaluation immobilière Norvex Intel™ ainsi que les documents "
                 f"d'entente partenaire pour votre examen.")
        docs_label = "Documents inclus :"
        docs_list  = ["Rapport Norvex Intel™ — Évaluation immobilière IA",
                      "Convention de partenariat Capital Norvex",
                      "Sommaire exécutif partenaire"]
        closing    = "N'hésitez pas à nous contacter pour discuter de cette opportunité."
        sig        = "Yves Barrette<br/>Capital Norvex — Prêteur Privé<br/>info@capitalnorvex.com"
        footer_r   = "Capital structuré. Ambition maîtrisée."
    else:
        subject = f"Capital Norvex — Investment Opportunity | File {did}"
        greeting = f"Hello <strong>{prenom_part}</strong>,"
        intro = (f"Further to our analysis of the <strong>{name}</strong> file, "
                 f"please find enclosed the Norvex Intel™ real estate evaluation and partner agreement documents for your review.")
        docs_label = "Documents included:"
        docs_list  = ["Norvex Intel™ Report — AI Real Estate Evaluation",
                      "Capital Norvex Partnership Agreement",
                      "Executive Summary for Partners"]
        closing    = "Please don't hesitate to contact us to discuss this opportunity."
        sig        = "Yves Barrette<br/>Capital Norvex — Private Lender<br/>info@capitalnorvex.com"
        footer_r   = "Structured Capital. Controlled Ambition."

    doc_rows = "".join(f'<li style="margin:4px 0;font-size:13px;color:#1a1a1a">{d}</li>' for d in docs_list)

    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0ece4;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0ece4;padding:24px 0;">
  <tr><td align="center">
    <table width="620" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:4px;border:1px solid #e0d9cc;overflow:hidden;">
      <tr><td style="background:#0a0d13;padding:24px 40px;">
        <p style="margin:0;font-family:Georgia,serif;font-size:20px;font-weight:700;letter-spacing:3px;color:#C9A84C;text-transform:uppercase;">Capital Norvex</p>
        <p style="margin:4px 0 0;font-size:10px;letter-spacing:2px;color:#888;text-transform:uppercase;">Prêteur Privé Institutionnel · Québec &amp; Ontario</p>
      </td></tr>
      <tr><td style="background:linear-gradient(90deg,#7a5c10,#C9A84C 35%,#e8c97a 50%,#C9A84C 65%,#7a5c10);height:2px;font-size:0;">&nbsp;</td></tr>
      <tr><td style="padding:32px 40px;">
        <p style="font-family:Georgia,serif;font-size:17px;color:#0a0d13;margin:0 0 14px">{greeting}</p>
        <p style="font-size:13.5px;line-height:1.8;color:#3a3a3a;margin:0 0 18px">{intro}</p>
        <p style="font-size:13px;font-weight:700;color:#0a0d13;margin:0 0 6px">{docs_label}</p>
        <ul style="margin:0 0 18px;padding-left:22px">{doc_rows}</ul>
        <p style="font-size:13.5px;line-height:1.8;color:#3a3a3a;margin:0 0 24px">{closing}</p>
        <table width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #e4ddd0;">
          <tr><td style="padding-top:16px;font-size:13px;line-height:1.7;color:#0a0d13">{sig}</td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#0a0d13;padding:16px 40px;">
        <table width="100%" cellpadding="0" cellspacing="0"><tr>
          <td><a href="mailto:info@capitalnorvex.com" style="font-size:11px;color:#C9A84C;text-decoration:none;margin-right:18px">info@capitalnorvex.com</a>
              <a href="https://capitalnorvex.com" style="font-size:11px;color:#C9A84C;text-decoration:none">capitalnorvex.com</a></td>
          <td align="right" style="font-size:10px;color:#555;font-style:italic;letter-spacing:1px">{footer_r}</td>
        </tr></table>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""

    send_email_with_attachments(partenaire_email, subject, html, attachments)
    log.info(f"   📧  Intel + Convention → partenaire {partenaire_email}")


# ── Détection réponses GO de Yves ────────────────────────────────────────────
def fetch_go_replies() -> list:
    """Scanne l'IMAP pour les réponses GO de Yves (format: GO email@partenaire.com [Nom])."""
    if not YVES_EMAIL:
        return []
    results = []
    try:
        imap = imaplib.IMAP4_SSL(MAIL_HOST)
        imap.login(MAIL_USER, MAIL_PASSWORD)
        imap.select("INBOX")

        _, msg_ids = imap.search(None, f'UNSEEN FROM "{YVES_EMAIL}"')
        if not msg_ids[0]:
            imap.logout()
            return []

        state = load_state()
        for mid in msg_ids[0].split():
            mid_str = mid.decode()
            _, data = imap.fetch(mid, "(RFC822)")
            raw     = data[0][1]
            msg     = email_lib.message_from_bytes(raw)

            # Sujet — chercher l'ID dossier
            subj_parts = decode_header(msg.get("Subject", ""))
            subject = ""
            for part, enc in subj_parts:
                subject += part.decode(enc or "utf-8", errors="replace") if isinstance(part, bytes) else str(part)

            import re as _re
            id_match = _re.search(r"\[ID:([^\]]+)\]", subject)
            dossier_id = id_match.group(1) if id_match else None

            # Corps du message
            body = ""
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    except Exception:
                        pass
                    break

            # Première ligne significative du corps (avant le quoted reply)
            first_line = ""
            for line in body.split("\n"):
                line = line.strip()
                if line and not line.startswith(">") and not line.startswith("On ") and not line.startswith("Le "):
                    first_line = line
                    break

            if not first_line.upper().startswith("GO"):
                # Marquer tout de même comme lu pour ne pas reprocesser
                imap.store(mid, "+FLAGS", "\Seen")
                continue

            # Parser: GO email@... [Nom optionnel]
            parts     = first_line.split()
            part_email = ""
            part_nom   = ""
            for p in parts[1:]:
                if "@" in p:
                    part_email = p.strip("<>,.;")
                else:
                    part_nom += (" " if part_nom else "") + p

            # Si pas d'email de partenaire → chercher dans le dossier
            if not part_email and dossier_id:
                for d in state.get("dossiers", {}).values():
                    if d.get("id") == dossier_id:
                        part_email = d.get("partenaire_email", "")
                        part_nom   = d.get("partenaire_nom", "")
                        break

            if part_email:
                results.append({
                    "dossier_id":      dossier_id,
                    "partenaire_email": part_email,
                    "partenaire_nom":   part_nom or part_email.split("@")[0],
                    "msg_id":           mid_str,
                })
                log.info(f"✅  GO reçu → dossier={dossier_id} partenaire={part_email}")
            else:
                log.info(f"⚡  GO reçu sans email partenaire — dossier={dossier_id}")

            imap.store(mid, "+FLAGS", "\Seen")

        imap.logout()
    except Exception as e:
        log.error(f"Erreur scan GO replies : {e}")
    return results


def process_go_replies():
    """Traite les GO replies de Yves : envoie Intel + Convention + Sommaire au partenaire."""
    goes = fetch_go_replies()
    if not goes:
        log.info("GO replies : aucun.")
        return

    state = load_state()

    for go in goes:
        dossier_id    = go["dossier_id"]
        part_email    = go["partenaire_email"]
        part_nom      = go["partenaire_nom"]

        # Trouver le dossier
        dossier = None
        for d in state.get("dossiers", {}).values():
            if d.get("id") == dossier_id:
                dossier = d
                break

        if not dossier:
            log.warning(f"GO : dossier {dossier_id} introuvable dans l'état")
            continue

        intel_text = dossier.get("intel_text", "")
        if not intel_text:
            log.warning(f"GO : aucun Intel stocké pour {dossier_id} — envoi sans Intel")

        lang = dossier.get("lang", "fr")
        email_intel_partenaire(part_email, part_nom, dossier, intel_text, lang)

        # Sauvegarder l'email partenaire dans le dossier
        dossier["partenaire_email"] = part_email
        dossier["partenaire_nom"]   = part_nom
        dossier["go_sent"]          = datetime.now().isoformat()
        save_state(state)

        log.info(f"📦  Intel + docs → {part_email} (dossier {dossier_id})")


# ── Point d'entrée ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("══════════════════════════════════════════")
    log.info("  Capital Norvex — Agent Docs — Démarrage")
    log.info("══════════════════════════════════════════")
    process_go_replies()
    process_track_alerts()
    # ⚠️ DÉSACTIVÉ 2026-05-04 (Yves) : Camille (NORVEX COUNSEL™) prend
    # le relais pour l'envoi des lettres d'engagement. Le déclenchement se
    # fait via le bouton « 📧 Envoyer lettre d'engagement (Camille) » dans
    # le Pipeline → /api/camille-trigger-engagement → flag Firestore →
    # cron Camille (process_pending_engagement_letters) envoie le PDF.
    # Voir : agents/camille_norvex_counsel/document_dispatcher.py
    # Voir mémoire : camille_phase1_lettres_engagement.md
    log.info("⏭  process_approved_dossiers() désactivé (remplacé par Camille NORVEX COUNSEL)")
    # process_approved_dossiers()  # ← DÉSACTIVÉ - voir Camille document_dispatcher
    process_new_pipeline_dossiers()
    process_new_emails()
    process_storage_uploads()
    log.info("══ Cycle terminé ══")
