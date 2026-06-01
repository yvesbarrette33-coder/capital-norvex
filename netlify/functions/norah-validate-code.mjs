/**
 * POST /.netlify/functions/norah-validate-code
 * Header: X-Internal-Secret
 * Body JSON: {
 *   caller_phone: "+15145551234",
 *   code: "123456",
 *   role: "client|courtier|partenaire|yves",
 *   display_name: "Optional — pour personnalisation"
 * }
 *
 * Tool ElevenLabs #2 — validate_code
 *
 * Valide le code 2FA reçu par SMS via Twilio Verify, et si OK crée une
 * session Norah valide 30 min. Les autres tools vérifient cette session.
 *
 * Réponses:
 *   200 { approved: true, status: "approved", session_ttl_minutes }
 *   200 { approved: false, status: "pending"|"denied"|"expired_or_exhausted", reason }
 *   400 { error: "..." }
 *   401 { error: "Unauthorized" }
 *   500 { error: "..." }
 */

import {
  json,
  unauthorized,
  badRequest,
  serverError,
  checkInternalSecret,
  twilioCheckVerification,
  normalizePhone,
  createNorahSession,
  SESSION_TTL_MINUTES,
} from "./_norah-shared.mjs";

export default async (req) => {
  if (req.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405 });
  }

  if (!checkInternalSecret(req)) return unauthorized();

  let body;
  try {
    body = await req.json();
  } catch {
    return badRequest("Invalid JSON body");
  }

  const phone = normalizePhone(body.caller_phone);
  const code = String(body.code || "").trim();
  const role = (body.role || "").toLowerCase().trim();
  const displayName = body.display_name || null;

  if (!phone) return badRequest("caller_phone manquant ou invalide");
  if (!/^\d{4,8}$/.test(code)) return badRequest("code invalide (4-8 chiffres attendus)");
  if (!["client", "courtier", "partenaire", "yves"].includes(role)) {
    return badRequest(`role invalide: ${role}`);
  }

  let result;
  try {
    result = await twilioCheckVerification(phone, code);
  } catch (e) {
    return serverError("Twilio check error: " + e.message);
  }

  if (result.error) {
    return json({
      approved: false,
      status: "expired_or_exhausted",
      reason: result.error,
    });
  }

  if (result.approved !== true) {
    return json({
      approved: false,
      status: result.status,
      reason: "code_incorrect",
    });
  }

  // Code validé — création de la session Norah (30 min)
  try {
    await createNorahSession({ phone, role, displayName });
  } catch (e) {
    // Session non créée mais code validé — on retourne quand même OK
    // mais on log l'erreur côté serveur (pas dans la réponse)
    console.error("[norah-validate-code] session creation failed:", e.message);
  }

  return json({
    approved: true,
    status: "approved",
    session_ttl_minutes: SESSION_TTL_MINUTES,
  });
};
