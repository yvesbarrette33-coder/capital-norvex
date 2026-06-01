/**
 * POST /.netlify/functions/norah-list-documents
 * Header: X-Internal-Secret
 * Body: { caller_phone, dossier_id }
 *
 * Tool ElevenLabs #4 — list_documents
 *
 * Liste les documents reçus et manquants pour un dossier.
 * Vérifie session 2FA + autorisation d'accès.
 */

import {
  json,
  unauthorized,
  badRequest,
  serverError,
  checkInternalSecret,
  requireValidSession,
  firestoreGet,
  canCallerAccessDossier,
  normalizePhone,
} from "./_norah-shared.mjs";

export default async (req) => {
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });
  if (!checkInternalSecret(req)) return unauthorized();

  let body;
  try {
    body = await req.json();
  } catch {
    return badRequest("Invalid JSON body");
  }

  const phone = normalizePhone(body.caller_phone);
  const dossierId = String(body.dossier_id || "").trim();
  if (!phone) return badRequest("caller_phone manquant");
  if (!dossierId) return badRequest("dossier_id manquant");

  let sessionCheck;
  try {
    sessionCheck = await requireValidSession(phone);
  } catch (e) {
    return serverError("Session check failed: " + e.message);
  }
  if (!sessionCheck.valid) return json({ ok: false, reason: sessionCheck.reason }, 403);

  let dossier;
  try {
    dossier = await firestoreGet("dossiers", dossierId);
  } catch (e) {
    return serverError("Firestore get failed: " + e.message);
  }
  if (!dossier) return json({ ok: false, reason: "dossier_introuvable" }, 404);
  if (!canCallerAccessDossier(sessionCheck.session, dossier)) {
    return json({ ok: false, reason: "acces_refuse" }, 403);
  }

  // Documents reçus = pdfBlobs (existant) + documents_recus (nouveau)
  const recus = [];
  if (Array.isArray(dossier.pdfBlobs)) {
    for (const blob of dossier.pdfBlobs) {
      recus.push({ type: blob.type || "document", name: blob.name || "", date: blob.uploadedAt || null });
    }
  }
  if (Array.isArray(dossier.documents_recus)) {
    for (const d of dossier.documents_recus) recus.push(d);
  }

  const manquants = Array.isArray(dossier.documents_manquants)
    ? dossier.documents_manquants
    : [];

  return json({
    ok: true,
    documents_recus: recus,
    documents_manquants: manquants,
    nb_recus: recus.length,
    nb_manquants: manquants.length,
  });
};
