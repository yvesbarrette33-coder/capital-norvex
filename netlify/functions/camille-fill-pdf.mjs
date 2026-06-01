/**
 * POST /api/camille-fill-pdf
 * Header: X-Internal-Secret
 *
 * Body:
 * {
 *   templateName: "commitment_letter_construction_en",  // see TEMPLATE_MAP below
 *   fieldValues: { "field_0001": "Acme Inc.", "sig_0001": "John Smith", ... },
 *   dossierId:   "CNV-2026-59109",   // optional — used for storage path + audit trail
 *   sendEmail:   false,              // optional — auto-send via Camille SendGrid path
 *   sendTo:      "client@example.com",       // required if sendEmail=true
 *   ccYves:      true,               // optional — Yves on CC of outgoing email
 *   subject:     "Norvex Counsel — Document for review",  // optional override
 *   emailIntroHtml: "<p>Bonjour ...</p>"          // optional intro paragraph
 * }
 *
 * Steps:
 *  1. Download the FILLABLE template PDF from Firebase Storage.
 *  2. Programmatically set AcroForm field values via pdf-lib.
 *  3. Upload the filled PDF to Storage under `dossiers/{dossierId}/filled/`.
 *  4. (Optional) Email the client a download link via SendGrid + Camille persona.
 *  5. Write a `legal_documents_sent` audit log in Firestore.
 *
 * IMPORTANT — pattern Camille (memory 2026-05-18):
 *   Fields are filled by Camille (the AI agent), NOT by a human. The visual
 *   design keeps the original black underline + the field value overlays
 *   on top so the document looks signed.
 */

import { PDFDocument } from "pdf-lib";

import {
  createAuditLog,
  downloadStorageAsBase64,
  getDoc,
  getFirestoreToken,
  getStorageToken,
  jsonResponse,
  loadServiceAccount,
  patchDoc,
  sendEmailSmart,
} from "./_camille-shared.mjs";

// Local helper : Storage RW token (the shared getStorageToken is read-only).
async function getStorageTokenRW(sa) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: sa.client_email,
    sub: sa.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
    scope: "https://www.googleapis.com/auth/devstorage.read_write",
  };
  const b64 = (obj) =>
    Buffer.from(JSON.stringify(obj))
      .toString("base64")
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");
  const signingInput = `${b64(header)}.${b64(payload)}`;
  const crypto = await import("node:crypto");
  const sig = crypto
    .createSign("RSA-SHA256")
    .update(signingInput)
    .sign(sa.private_key);
  const sigB64 = sig
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  const jwt = `${signingInput}.${sigB64}`;
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: jwt,
    }),
  });
  const data = await r.json();
  if (!data.access_token)
    throw new Error("Storage RW token failed: " + JSON.stringify(data));
  return data.access_token;
}

// ── Template registry (templateName → Storage path) ─────────────────────────
// Storage layout : templates/legal/{folder}/{filename}
const TEMPLATE_BUCKET_DEFAULT = "capital-norvex-uploads";
const TEMPLATE_PREFIX = "templates/legal";

const TEMPLATE_MAP = {
  // ── ON Emprunteur — Commitment letters ────────────────────────────────
  commitment_letter_acquisition_en: "01_Commitment_letters_EN/CN_COMMITMENT_LETTER_Acquisition_ON_FILLABLE.pdf",
  commitment_letter_construction_en: "01_Commitment_letters_EN/CN_COMMITMENT_LETTER_Construction_ON_FILLABLE.pdf",
  commitment_letter_land_en: "01_Commitment_letters_EN/CN_COMMITMENT_LETTER_Land_ON_FILLABLE.pdf",
  commitment_letter_refinancing_en: "01_Commitment_letters_EN/CN_COMMITMENT_LETTER_Refinancing_ON_FILLABLE.pdf",
  lettre_engagement_acquisition_fr: "01_Lettres_engagement_FR/CN_LETTRE_ENGAGEMENT_Acquisition_ON_FR_FILLABLE.pdf",
  lettre_engagement_construction_fr: "01_Lettres_engagement_FR/CN_LETTRE_ENGAGEMENT_Construction_ON_FR_FILLABLE.pdf",
  lettre_engagement_refinancement_fr: "01_Lettres_engagement_FR/CN_LETTRE_ENGAGEMENT_Refinancement_ON_FR_FILLABLE.pdf",
  lettre_engagement_terrain_fr: "01_Lettres_engagement_FR/CN_LETTRE_ENGAGEMENT_Terrain_ON_FR_FILLABLE.pdf",
  // ── ON Emprunteur — Loan agreements ───────────────────────────────────
  loan_agreement_construction_en: "02_Loan_agreements_EN/CN_LOAN_AGREEMENT_Construction_ON_FILLABLE.pdf",
  loan_agreement_refinancing_en: "02_Loan_agreements_EN/CN_LOAN_AGREEMENT_Refinancing_ON_FILLABLE.pdf",
  convention_pret_construction_fr: "02_Conventions_de_pret_FR/CN_CONVENTION_DE_PRET_Construction_ON_FR_FILLABLE.pdf",
  convention_pret_refinancement_fr: "02_Conventions_de_pret_FR/CN_CONVENTION_DE_PRET_Refinancement_ON_FR_FILLABLE.pdf",
  // ── ON Emprunteur — Charges (LRRA Form 2) ─────────────────────────────
  // 2026-05-19: switched to _LEGAL_STRICT.pdf versions (cover page + header/footer
  // marketing branding stripped — required for documents inscribed at Teraview).
  charge_construction_en: "03_Charge_Mortgage_of_Land_Form2/CN_CHARGE_Construction_ON_LEGAL_STRICT.pdf",
  charge_multiresidential_en: "03_Charge_Mortgage_of_Land_Form2/CN_CHARGE_MultiResidential_ON_LEGAL_STRICT.pdf",
  charge_refinancing_en: "03_Charge_Mortgage_of_Land_Form2/CN_CHARGE_Refinancing_ON_LEGAL_STRICT.pdf",
  charge_vacantland_en: "03_Charge_Mortgage_of_Land_Form2/CN_CHARGE_VacantLand_ON_LEGAL_STRICT.pdf",
  charge_acquisition_fr: "03_Charge_Mortgage_of_Land_Form2_FR/CN_CHARGE_acquisition_ON_FR_LEGAL_STRICT.pdf",
  charge_construction_fr: "03_Charge_Mortgage_of_Land_Form2_FR/CN_CHARGE_construction_ON_FR_LEGAL_STRICT.pdf",
  charge_refinancing_fr: "03_Charge_Mortgage_of_Land_Form2_FR/CN_CHARGE_refinancing_ON_FR_LEGAL_STRICT.pdf",
  charge_vacant_land_fr: "03_Charge_Mortgage_of_Land_Form2_FR/CN_CHARGE_vacant_land_ON_FR_LEGAL_STRICT.pdf",
  // ── ON Emprunteur — Standard Charge Terms (LEGAL_STRICT, filed at LRRA) ─
  standard_charge_terms_en: "04_Standard_Charge_Terms/CN_STANDARD_CHARGE_TERMS_ON_LEGAL_STRICT.pdf",
  conditions_standard_charge_fr: "04_Standard_Charge_Terms_FR/CN_CONDITIONS_STANDARD_CHARGE_ON_FR_LEGAL_STRICT.pdf",
  // ── ON Emprunteur — PPSA / GSA ────────────────────────────────────────
  gsa_ppsa_en: "05_PPSA_Security_GSA/CN_GENERAL_SECURITY_AGREEMENT_PPSA_ON_FILLABLE.pdf",
  gsa_ppsa_fr: "05_PPSA_Security_GSA_FR/CN_GENERAL_SECURITY_AGREEMENT_PPSA_ON_FR_FILLABLE.pdf",
  // ── ON Emprunteur — Assignment of rents ───────────────────────────────
  assignment_of_rents_en: "06_Assignment_of_Rents/CN_ASSIGNMENT_OF_RENTS_AND_LEASES_ON_FILLABLE.pdf",
  cession_loyers_baux_fr: "06_Assignment_of_Rents_FR/CN_CESSION_DE_LOYERS_ET_BAUX_ON_FR_FILLABLE.pdf",
  // ── ON Emprunteur — Guarantees ────────────────────────────────────────
  guarantee_en: "07_Guarantees/CN_GUARANTEE_ON_FILLABLE.pdf",
  cautionnement_fr: "07_Guarantees_FR/CN_CAUTIONNEMENT_ON_FR_FILLABLE.pdf",
  // ── ON Emprunteur — Corporate resolutions ─────────────────────────────
  corporate_resolution_en: "08_Corporate_Resolutions/CN_CORPORATE_RESOLUTION_ON_FILLABLE.pdf",
  resolution_corporative_fr: "08_Corporate_Resolutions_FR/CN_RESOLUTION_CORPORATIVE_ON_FR_FILLABLE.pdf",
  // ── Partnership ───────────────────────────────────────────────────────
  partner_executive_summary_en: "Partnership/01_Executive_Summaries_EN/CN_PARTNER_EXECUTIVE_SUMMARY_ON_FILLABLE.pdf",
  sommaire_executif_partenaire_fr: "Partnership/01_Sommaires_Executifs_FR/CN_SOMMAIRE_EXECUTIF_PARTENAIRE_ON_FR_FILLABLE.pdf",
  partnership_agreement_construction_en: "Partnership/02_Partnership_Agreements_EN/CN_PARTNERSHIP_AGREEMENT_Construction_ON_FILLABLE.pdf",
  partnership_agreement_monthly_en: "Partnership/02_Partnership_Agreements_EN/CN_PARTNERSHIP_AGREEMENT_MonthlyPayments_ON_FILLABLE.pdf",
  convention_partenariat_construction_fr: "Partnership/02_Conventions_Partenariat_FR/CN_CONVENTION_PARTENARIAT_Construction_ON_FR_FILLABLE.pdf",
  convention_partenariat_mensualites_fr: "Partnership/02_Conventions_Partenariat_FR/CN_CONVENTION_PARTENARIAT_Mensualites_ON_FR_FILLABLE.pdf",
};

const FROM_EMAIL = "camille@capitalnorvex.com";
const YVES_NOTIF = "yves@capitalnorvex.com";

export default async function handler(req) {
  if (req.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405);
  }
  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return jsonResponse({ error: "Unauthorized" }, 401);
  }

  let body;
  try {
    body = await req.json();
  } catch {
    return jsonResponse({ error: "Invalid JSON body" }, 400);
  }

  const {
    templateName,
    fieldValues = {},
    dossierId = null,
    sendEmail = false,
    sendTo = null,
    ccYves = true,
    subject: customSubject = null,
    emailIntroHtml = null,
  } = body || {};

  if (!templateName || !TEMPLATE_MAP[templateName]) {
    return jsonResponse(
      {
        error: `Unknown templateName. Known: ${Object.keys(TEMPLATE_MAP).join(", ")}`,
      },
      400
    );
  }
  if (sendEmail && !sendTo) {
    return jsonResponse({ error: "sendTo required when sendEmail=true" }, 400);
  }
  if (!fieldValues || typeof fieldValues !== "object") {
    return jsonResponse({ error: "fieldValues must be an object" }, 400);
  }

  try {
    const sa = await loadServiceAccount();
    const projectId = sa.project_id;
    const bucketName = process.env.FIREBASE_STORAGE_BUCKET || TEMPLATE_BUCKET_DEFAULT;
    const fsToken = await getFirestoreToken(sa);
    // RW token : we need both download (template) AND upload (filled result).
    const stToken = await getStorageTokenRW(sa);

    // ── 1. Download template ─────────────────────────────────────────────
    const templatePath = `${TEMPLATE_PREFIX}/${TEMPLATE_MAP[templateName]}`;
    const templateB64 = await downloadStorageAsBase64({
      bucketName,
      storagePath: templatePath,
      storageToken: stToken,
    });
    const templateBuf = Buffer.from(templateB64, "base64");

    // ── 2. Fill form fields ──────────────────────────────────────────────
    const pdf = await PDFDocument.load(templateBuf);
    const form = pdf.getForm();
    const availableFields = form.getFields().map((f) => f.getName());
    let filledCount = 0;
    const skipped = [];

    for (const [name, raw] of Object.entries(fieldValues)) {
      if (!availableFields.includes(name)) {
        skipped.push(name);
        continue;
      }
      try {
        const field = form.getTextField(name);
        const value = raw == null ? "" : String(raw);
        field.setText(value);
        filledCount++;
      } catch (e) {
        // Not a text field (rare since all our fields are text), skip safely
        skipped.push(`${name} (${e.message})`);
      }
    }

    // Flatten so the values are baked-in (cannot be edited downstream)
    try {
      form.flatten();
    } catch (_) {
      // Some fields may not flatten cleanly — non-fatal, continue
    }

    const filledBytes = await pdf.save();
    const filledB64 = Buffer.from(filledBytes).toString("base64");

    // ── 3. Upload filled PDF to Storage ──────────────────────────────────
    const ts = Date.now();
    const dossierFolder = dossierId || "ad-hoc";
    const filename = `${templateName}_${ts}.pdf`;
    const filledPath = `dossiers/${dossierFolder}/filled/${filename}`;
    const uploadUrl =
      `https://storage.googleapis.com/upload/storage/v1/b/${bucketName}/o?` +
      `uploadType=media&name=${encodeURIComponent(filledPath)}`;
    const uploadResp = await fetch(uploadUrl, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${stToken}`,
        "Content-Type": "application/pdf",
      },
      body: Buffer.from(filledBytes),
    });
    if (!uploadResp.ok) {
      const errText = await uploadResp.text();
      throw new Error(
        `Storage upload failed (${uploadResp.status}): ${errText.slice(0, 200)}`
      );
    }

    // ── 4. (Optional) Send via SendGrid + Camille persona ────────────────
    let emailResult = null;
    if (sendEmail && sendTo) {
      const intro =
        emailIntroHtml ||
        `<p>Hello,</p><p>Please find attached your document prepared by Camille, NORVEX COUNSEL™ (AI legal assistant of Capital Norvex Inc.).</p>`;
      const subject = customSubject || `Capital Norvex — Document for review (${templateName})`;
      const html = `<!DOCTYPE html><html><body style="font-family:-apple-system,sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#1a1a1a">
${intro}
<p>This document is provided for review and signature. All financial and legal decisions are taken and validated by the management of Capital Norvex Inc.</p>
<p>If you have any questions, please reply to this email.</p>
<p style="margin-top:24px;color:#555;font-size:12px;font-style:italic">Camille NORVEX COUNSEL™ — Independent legal advice (ILA) recommended before signing. This email is sent on behalf of Capital Norvex Inc.</p>
</body></html>`;

      const ccList = ccYves ? [YVES_NOTIF] : [];
      emailResult = await sendEmailSmart({
        from: FROM_EMAIL,
        to: [sendTo],
        cc: ccList,
        subject,
        html,
        attachments: [
          {
            filename: `${templateName}.pdf`,
            content: filledB64,
            contentType: "application/pdf",
          },
        ],
      });
    }

    // ── 5. Audit log ─────────────────────────────────────────────────────
    await createAuditLog(projectId, fsToken, {
      agent: "camille-fill-pdf",
      action: "fill_pdf",
      targetType: dossierId ? "dossier" : "ad-hoc",
      targetId: dossierId || "n/a",
      result: emailResult && emailResult.error ? "partial" : "success",
      details: {
        templateName,
        filledPath,
        fieldsFilled: filledCount,
        fieldsSkipped: skipped.length,
        emailSent: !!(sendEmail && emailResult && !emailResult.error),
        emailRecipient: sendTo,
      },
    });

    if (dossierId) {
      await patchDoc(projectId, fsToken, "dossiers", dossierId, {
        lastFilledTemplate: templateName,
        lastFilledPath: filledPath,
        lastFilledAt: new Date(),
      });
    }

    return jsonResponse({
      ok: true,
      templateName,
      dossierId,
      filledPath,
      bucket: bucketName,
      fieldsFilled: filledCount,
      fieldsSkipped: skipped,
      availableFieldsCount: availableFields.length,
      emailSent: !!(sendEmail && emailResult && !emailResult.error),
      emailResult,
    });
  } catch (e) {
    return jsonResponse({ error: e.message, stack: e.stack }, 500);
  }
}

export const config = {
  path: "/api/camille-fill-pdf",
};
