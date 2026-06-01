/**
 * POST /api/beatrice-sms-notify
 * Header: X-Internal-Secret
 * Body: {
 *   draftId: string,
 *   subject: string,
 *   fromName: string,           // ex. "Marc Tremblay (Groupe Montoni)"
 *   summary: string,            // résumé du triage en 1-2 phrases
 *   approveUrl: string,         // URL HMAC déjà signée
 *   rejectUrl: string,
 *   modifyUrl: string,
 * }
 *
 * Envoie un SMS à Yves via Twilio quand le Mode Mobile est activé. Le SMS
 * contient les 3 liens HMAC tap-to-approve (les mêmes URLs que l'email).
 *
 * Env vars requises :
 * - TWILIO_ACCOUNT_SID
 * - TWILIO_AUTH_TOKEN
 * - TWILIO_PHONE_NUMBER (E.164, ex. +14385337738)
 * - YVES_MOBILE_PHONE   (E.164, ex. +15145312705)
 */

import { jsonResponse } from "./_camille-shared.mjs";

const SMS_MAX_LENGTH = 1600; // Twilio limite par segment, mais accepte les longs

function buildSmsBody({ subject, fromName, summary, approveUrl, rejectUrl, modifyUrl }) {
  // Subject + summary doivent être courts pour rester dans 1 SMS si possible
  const subj = (subject || "(sans objet)").slice(0, 80);
  const from = (fromName || "(sans nom)").slice(0, 60);
  const sum = (summary || "").slice(0, 200);
  const lines = [
    `📧 Béatrice — nouveau draft`,
    ``,
    `De : ${from}`,
    `Sujet : ${subj}`,
    ``,
    `${sum}`,
    ``,
    `✅ Approuver : ${approveUrl}`,
    `❌ Rejeter : ${rejectUrl}`,
    `✏️ Modifier : ${modifyUrl}`,
  ];
  let body = lines.join("\n");
  if (body.length > SMS_MAX_LENGTH) {
    body = body.slice(0, SMS_MAX_LENGTH - 3) + "...";
  }
  return body;
}

export default async function handler(req) {
  if (req.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405);
  }
  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return jsonResponse({ error: "Unauthorized" }, 401);
  }

  const sid = process.env.TWILIO_ACCOUNT_SID;
  const token = process.env.TWILIO_AUTH_TOKEN;
  const fromNumber = process.env.TWILIO_PHONE_NUMBER;
  const toNumber = process.env.YVES_MOBILE_PHONE;

  if (!sid || !token || !fromNumber || !toNumber) {
    return jsonResponse(
      {
        error:
          "Twilio non configuré (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, YVES_MOBILE_PHONE manquants)",
      },
      503
    );
  }

  let body;
  try {
    body = await req.json();
  } catch {
    return jsonResponse({ error: "Invalid JSON" }, 400);
  }

  const { draftId, subject, fromName, summary, approveUrl, rejectUrl, modifyUrl } = body;
  if (!draftId || !approveUrl || !rejectUrl || !modifyUrl) {
    return jsonResponse(
      { error: "draftId, approveUrl, rejectUrl, modifyUrl requis" },
      400
    );
  }

  const smsBody = buildSmsBody({ subject, fromName, summary, approveUrl, rejectUrl, modifyUrl });

  // Twilio API : POST https://api.twilio.com/2010-04-01/Accounts/{SID}/Messages.json
  const url = `https://api.twilio.com/2010-04-01/Accounts/${encodeURIComponent(sid)}/Messages.json`;
  const auth = Buffer.from(`${sid}:${token}`).toString("base64");

  const params = new URLSearchParams();
  params.set("From", fromNumber);
  params.set("To", toNumber);
  params.set("Body", smsBody);

  try {
    const r = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Basic ${auth}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params.toString(),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      return jsonResponse(
        {
          error: "Twilio send failed",
          twilio: data.message || data.error_message || `HTTP ${r.status}`,
        },
        502
      );
    }
    return jsonResponse({
      ok: true,
      draftId,
      sid: data.sid || null,
      to: toNumber,
      length: smsBody.length,
    });
  } catch (e) {
    return jsonResponse({ error: e.message }, 500);
  }
}

export const config = {
  path: "/api/beatrice-sms-notify",
};
