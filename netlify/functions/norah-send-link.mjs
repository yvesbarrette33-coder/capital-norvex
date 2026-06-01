/**
 * POST /.netlify/functions/norah-send-link
 * Header: X-Internal-Secret
 * Body: { caller_phone, type: "promoteur"|"courtier"|"upload" }
 *
 * Tool ElevenLabs #9 — send_application_link
 *
 * Envoie un SMS à l'appelant avec le bon lien selon le type:
 *   - promoteur → formulaire Score Norvex
 *   - courtier  → formulaire d'accréditation
 *   - upload    → portail d'upload de documents
 *
 * Pas de session 2FA requise (envoi de lien public).
 */

import {
  json,
  unauthorized,
  badRequest,
  serverError,
  checkInternalSecret,
  twilioSendSMS,
  normalizePhone,
} from "./_norah-shared.mjs";

const LINKS = {
  promoteur: {
    url: "https://capitalnorvex.com/#formulaire",
    label: "Formulaire de demande Capital Norvex",
  },
  courtier: {
    url: "https://capitalnorvex.com/courtier-candidature.html",
    label: "Candidature courtier accrédité",
  },
  upload: {
    url: "https://capitalnorvex.com/upload.html",
    label: "Téléversement de documents",
  },
};

export default async (req) => {
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });
  if (!checkInternalSecret(req)) return unauthorized();

  let body;
  try { body = await req.json(); } catch { return badRequest("Invalid JSON body"); }

  const phone = normalizePhone(body.caller_phone);
  const type = String(body.type || "").toLowerCase().trim();
  if (!phone) return badRequest("caller_phone manquant");
  if (!LINKS[type]) return badRequest(`type invalide: ${type} (attendu: promoteur|courtier|upload)`);

  const link = LINKS[type];
  const smsBody = `Bonjour, voici le lien demandé : ${link.url}\n\n— Capital Norvex`;

  let result;
  try {
    result = await twilioSendSMS(phone, smsBody);
  } catch (e) {
    return serverError("Twilio SMS error: " + e.message);
  }

  if (!result.success) {
    return json({ ok: false, sms_sent: false, error: result.error });
  }

  return json({
    ok: true,
    sms_sent: true,
    type,
    link: link.url,
    sid: result.sid,
  });
};
