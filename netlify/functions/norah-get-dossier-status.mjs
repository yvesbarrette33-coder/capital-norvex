/**
 * POST /.netlify/functions/norah-get-dossier-status
 * Header: X-Internal-Secret
 * Body: { caller_phone, dossier_id }
 *
 * Tool ElevenLabs #3 — get_dossier_status
 *
 * Retourne les FAITS d'un dossier (étape, statut, dernière mise à jour) selon
 * le rôle de l'appelant. JAMAIS de décisions (taux, montant approuvé, oui/non).
 *
 * Vérifications:
 *   1. INTERNAL_SECRET valide
 *   2. Session Norah valide pour caller_phone (2FA passé < 30 min)
 *   3. L'appelant a-t-il le DROIT de voir ce dossier ?
 *      - client    → dossier.tel == caller_phone OU dossier.client_phone == caller_phone
 *      - courtier  → dossier.courtier_phone == caller_phone (dossier apporté)
 *      - partenaire → dossier.partenaires_coprêteurs contient son ID
 *      - yves      → toujours OK
 */

import {
  json,
  unauthorized,
  badRequest,
  serverError,
  checkInternalSecret,
  requireValidSession,
  firestoreGet,
  normalizePhone,
} from "./_norah-shared.mjs";

// Champs explicitement INTERDITS de retourner (décisions/internes)
const FORBIDDEN_FIELDS = new Set([
  "decision",
  "taux",
  "montant_approuve",
  "montantApprouve",
  "approbation",
  "commentaires_internes",
  "internal_notes",
  "score_internal",
  "rating_internal",
]);

// Whitelist des champs publics par rôle
const FIELDS_BY_ROLE = {
  client: ["stage", "etape_actuelle", "statut", "documents_manquants", "last_update", "agent_attitre", "agent_email"],
  courtier: ["stage", "etape_actuelle", "statut", "documents_manquants", "last_update", "agent_attitre", "agent_email", "prenom", "nom"],
  partenaire: ["stage", "etape_actuelle", "statut", "documents_manquants", "last_update", "agent_attitre", "type", "montant"],
  yves: null, // null = retourner tout (sauf forbidden)
};

function filterFields(dossier, role) {
  const allowed = FIELDS_BY_ROLE[role];
  const out = { id: dossier.id };

  for (const [key, val] of Object.entries(dossier)) {
    if (FORBIDDEN_FIELDS.has(key)) continue;
    if (allowed === null || allowed.includes(key)) {
      out[key] = val;
    }
  }
  return out;
}

function canAccessDossier(session, dossier) {
  if (session.role === "yves") return true;
  const phone = session.phone;

  if (session.role === "client") {
    return dossier.tel === phone || dossier.client_phone === phone || dossier.email_phone === phone;
  }
  if (session.role === "courtier") {
    return dossier.courtier_phone === phone || dossier.broker_phone === phone;
  }
  if (session.role === "partenaire") {
    const partners = dossier.partenaires_coprêteurs || dossier.partners || [];
    if (Array.isArray(partners)) {
      return partners.some((p) => p === phone || (p && p.phone === phone));
    }
  }
  return false;
}

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
  if (!phone) return badRequest("caller_phone manquant ou invalide");
  if (!dossierId) return badRequest("dossier_id manquant");

  let sessionCheck;
  try {
    sessionCheck = await requireValidSession(phone);
  } catch (e) {
    return serverError("Session check failed: " + e.message);
  }
  if (!sessionCheck.valid) {
    return json({ ok: false, reason: sessionCheck.reason }, 403);
  }
  const session = sessionCheck.session;

  let dossier;
  try {
    dossier = await firestoreGet("dossiers", dossierId);
  } catch (e) {
    return serverError("Firestore get failed: " + e.message);
  }
  if (!dossier) return json({ ok: false, reason: "dossier_introuvable" }, 404);

  if (!canAccessDossier(session, dossier)) {
    return json({ ok: false, reason: "acces_refuse" }, 403);
  }

  const filtered = filterFields(dossier, session.role);

  return json({
    ok: true,
    dossier: filtered,
    role: session.role,
  });
};
