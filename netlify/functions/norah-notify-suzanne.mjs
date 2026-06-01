/**
 * POST /api/norah-notify-suzanne
 *
 * Tool ElevenLabs : Norah envoie un SMS à Suzanne Breton (+14506311688)
 * quand un appelant demande à lui parler. Le SMS contient les coordonnées
 * de l'appelant pour que Suzanne le rappelle dans l'heure.
 *
 * Sécurité : header X-Norah-Tool-Secret (configuré côté ElevenLabs Tool).
 *
 * Body :
 * {
 *   "callerName": "Jean Tremblay",
 *   "callerPhone": "514-555-1234",
 *   "callerReason": "Question facturation février",
 *   "language": "fr"  // optionnel
 * }
 *
 * Env vars requises :
 * - TWILIO_ACCOUNT_SID
 * - TWILIO_AUTH_TOKEN
 * - TWILIO_PHONE_NUMBER  (le 438-533-PRÊT)
 * - SUZANNE_MOBILE_PHONE (E.164, ex. +14506311688)
 * - NORAH_TOOL_SECRET    (token partagé avec ElevenLabs)
 *
 * Trace : Firestore norahCallNotes pour audit.
 */

import {
  createAuditLog,
  getFirestoreToken,
  jsonResponse,
  loadServiceAccount,
} from "./_camille-shared.mjs";

const SUZANNE_DEFAULT = "+14506311688";

function buildSmsBody({ callerName, callerPhone, callerReason, language }) {
  const now = new Date();
  const tz = "America/Toronto";
  const time = new Intl.DateTimeFormat("fr-CA", {
    timeZone: tz, hour: "2-digit", minute: "2-digit",
  }).format(now);
  const date = new Intl.DateTimeFormat("fr-CA", {
    timeZone: tz, day: "2-digit", month: "short",
  }).format(now);

  const isEN = (language || "").toLowerCase().startsWith("en");
  if (isEN) {
    return [
      "📞 Capital Norvex — call for you",
      "",
      `From: ${callerName || "(name not provided)"}`,
      `Phone: ${callerPhone || "(no number)"}`,
      `Reason: ${callerReason || "(no details)"}`,
      `Received: ${date} at ${time} — please call back within the hour`,
    ].join("\n");
  }
  return [
    "📞 Capital Norvex — appel pour vous",
    "",
    `De : ${callerName || "(nom non fourni)"}`,
    `Tél : ${callerPhone || "(pas de numéro)"}`,
    `Motif : ${callerReason || "(non précisé)"}`,
    `Reçu : ${date} à ${time} — à rappeler dans l'heure`,
  ].join("\n");
}

export default async function handler(req) {
  if (req.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405);
  }

  // Auth : token dédié pour ce tool ElevenLabs
  const toolSecret = req.headers.get("x-norah-tool-secret");
  if (
    !process.env.NORAH_TOOL_SECRET ||
    toolSecret !== process.env.NORAH_TOOL_SECRET
  ) {
    return jsonResponse({ error: "Unauthorized" }, 401);
  }

  const sid = process.env.TWILIO_ACCOUNT_SID;
  const token = process.env.TWILIO_AUTH_TOKEN;
  const fromNumber = process.env.TWILIO_PHONE_NUMBER;
  const toNumber = process.env.SUZANNE_MOBILE_PHONE || SUZANNE_DEFAULT;

  if (!sid || !token || !fromNumber || !toNumber) {
    return jsonResponse(
      { error: "Twilio non configuré (TWILIO_*, SUZANNE_MOBILE_PHONE)" },
      503
    );
  }

  let body;
  try {
    body = await req.json();
  } catch {
    return jsonResponse({ error: "Invalid JSON" }, 400);
  }

  const { callerName, callerPhone, callerReason, language } = body;
  if (!callerName && !callerPhone) {
    return jsonResponse(
      { error: "callerName ou callerPhone requis" },
      400
    );
  }

  const smsBody = buildSmsBody({
    callerName, callerPhone, callerReason, language,
  });

  // Twilio API
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

    // Audit Firestore (best-effort)
    try {
      const sa = await loadServiceAccount();
      const projectId = sa.project_id;
      const fsToken = await getFirestoreToken(sa);
      await createAuditLog(projectId, fsToken, {
        agent: "norah",
        action: "notify_suzanne_sms",
        targetType: "suzanne_callback",
        targetId: data.sid || "unknown",
        result: r.ok ? "success" : "error",
        details: {
          callerName: callerName || "",
          callerPhone: callerPhone || "",
          callerReason: callerReason || "",
          twilio_status: r.status,
        },
      });
    } catch (auditErr) {
      // Audit fail = pas bloquant
    }

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
      message: "SMS envoyé à Madame Breton — elle rappellera dans l'heure.",
      sid: data.sid || null,
    });
  } catch (e) {
    return jsonResponse({ error: e.message }, 500);
  }
}

export const config = {
  path: "/api/norah-notify-suzanne",
};
