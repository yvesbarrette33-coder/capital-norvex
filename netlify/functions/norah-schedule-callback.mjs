/**
 * POST /.netlify/functions/norah-schedule-callback
 * Header: X-Internal-Secret
 * Body: {
 *   caller_phone, caller_name?, reason,
 *   urgency: "normal"|"vip"|"urgent",
 *   preferred_time?: "ISO timestamp",
 *   notes?
 * }
 *
 * Tool ElevenLabs #7 — schedule_callback
 *
 * Crée une tâche de rappel pour Yves (jamais transfert direct).
 * Selon urgency:
 *   - normal  → email à Yves (digest)
 *   - vip     → SMS Yves immédiat + email résumé
 *   - urgent  → SMS Yves IMMÉDIAT (closing péril, journaliste, etc.)
 *
 * Pas besoin de session 2FA (un appelant non identifié peut demander un rappel).
 */

import {
  json,
  unauthorized,
  badRequest,
  serverError,
  checkInternalSecret,
  firestoreCreate,
  twilioSendSMS,
  sendgridSend,
  normalizePhone,
  YVES_VIP_PHONE,
  YVES_EMAIL,
} from "./_norah-shared.mjs";

export default async (req) => {
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });
  if (!checkInternalSecret(req)) return unauthorized();

  let body;
  try { body = await req.json(); } catch { return badRequest("Invalid JSON body"); }

  const phone = normalizePhone(body.caller_phone);
  if (!phone) return badRequest("caller_phone manquant");

  const callerName = String(body.caller_name || "Inconnu").trim();
  const reason = String(body.reason || "Demande de rappel").trim();
  const urgency = ["normal", "vip", "urgent"].includes(body.urgency) ? body.urgency : "normal";
  const notes = String(body.notes || "").trim();
  const preferredTime = body.preferred_time || null;

  // 1. Enregistrer le rappel dans Firestore (collection `appels_rappels`)
  let callbackDoc;
  try {
    callbackDoc = await firestoreCreate("appels_rappels", {
      caller_phone: phone,
      caller_name: callerName,
      reason,
      urgency,
      preferred_time: preferredTime,
      notes,
      status: "pending",
      created_at: new Date(),
    });
  } catch (e) {
    return serverError("Firestore create failed: " + e.message);
  }

  // 2. Notifier Yves selon urgence
  let smsSent = false;
  let emailSent = false;
  const errors = [];

  if (urgency === "urgent" || urgency === "vip") {
    const smsBody =
      urgency === "urgent"
        ? `🚨 URGENT — ${callerName} (${phone}) — ${reason}`
        : `VIP appel: ${callerName} (${phone}) — ${reason} — email envoyé`;
    try {
      const r = await twilioSendSMS(YVES_VIP_PHONE, smsBody);
      smsSent = r.success;
      if (!r.success) errors.push("sms: " + r.error);
    } catch (e) {
      errors.push("sms_exception: " + e.message);
    }
  }

  // Email à Yves dans tous les cas (sauf normal qui passe par le digest 18h)
  if (urgency !== "normal") {
    try {
      await sendgridSend({
        to: YVES_EMAIL,
        subject:
          urgency === "urgent"
            ? `🚨 URGENT — Rappel demandé par ${callerName}`
            : `VIP — Rappel demandé par ${callerName}`,
        html: buildCallbackEmailHTML({ callerName, phone, reason, urgency, notes, preferredTime }),
      });
      emailSent = true;
    } catch (e) {
      errors.push("email: " + e.message);
    }
  }

  return json({
    ok: true,
    callback_id: callbackDoc?.id || null,
    sms_sent: smsSent,
    email_sent: emailSent,
    urgency,
    errors: errors.length ? errors : undefined,
  });
};

function buildCallbackEmailHTML({ callerName, phone, reason, urgency, notes, preferredTime }) {
  const banner =
    urgency === "urgent"
      ? `<div style="background:#dc2626;color:#fff;padding:12px;font-weight:bold;">🚨 URGENT — Action immédiate requise</div>`
      : `<div style="background:#f59e0b;color:#fff;padding:12px;font-weight:bold;">VIP — Rappel prioritaire</div>`;

  return `
    <div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;">
      ${banner}
      <div style="padding:20px;background:#f9fafb;">
        <h2 style="margin:0 0 16px;color:#111827;">Demande de rappel</h2>
        <table style="width:100%;border-collapse:collapse;">
          <tr><td style="padding:6px 0;color:#6b7280;">Appelant</td><td><strong>${escapeHTML(callerName)}</strong></td></tr>
          <tr><td style="padding:6px 0;color:#6b7280;">Téléphone</td><td><a href="tel:${phone}">${phone}</a></td></tr>
          <tr><td style="padding:6px 0;color:#6b7280;">Raison</td><td>${escapeHTML(reason)}</td></tr>
          ${preferredTime ? `<tr><td style="padding:6px 0;color:#6b7280;">Heure préférée</td><td>${escapeHTML(preferredTime)}</td></tr>` : ""}
          ${notes ? `<tr><td style="padding:6px 0;color:#6b7280;vertical-align:top;">Notes</td><td>${escapeHTML(notes)}</td></tr>` : ""}
        </table>
      </div>
      <div style="padding:12px;text-align:center;color:#6b7280;font-size:12px;">
        Norah · Capital Norvex · ${new Date().toLocaleString("fr-CA", { timeZone: "America/Toronto" })}
      </div>
    </div>
  `;
}

function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
