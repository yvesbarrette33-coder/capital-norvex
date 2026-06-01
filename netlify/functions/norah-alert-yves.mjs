/**
 * POST /.netlify/functions/norah-alert-yves
 * Header: X-Internal-Secret
 * Body: {
 *   level: "vip"|"urgent"|"critical",
 *   summary: "Court résumé",
 *   caller_phone, caller_name?, caller_role?,
 *   detail?: "HTML/texte plus long pour l'email"
 * }
 *
 * Tool ElevenLabs #10 — alert_yves
 *
 * Déclenche le PROTOCOLE VIP — SMS instantané + email détaillé.
 * Utilisé pour: co-prêteur, notaire closing, avocat partenaire, urgence
 * closing, journaliste, escalade client.
 *
 * Différence avec schedule_callback:
 *   - alert_yves     → notification PUSH immédiate (SMS+email simultanés)
 *   - schedule_callback → demande de rappel asynchrone
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

const VALID_LEVELS = ["vip", "urgent", "critical"];

export default async (req) => {
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });
  if (!checkInternalSecret(req)) return unauthorized();

  let body;
  try { body = await req.json(); } catch { return badRequest("Invalid JSON body"); }

  const level = String(body.level || "vip").toLowerCase().trim();
  if (!VALID_LEVELS.includes(level)) return badRequest(`level invalide: ${level}`);

  const summary = String(body.summary || "").trim().slice(0, 200);
  if (!summary) return badRequest("summary manquant");

  const phone = normalizePhone(body.caller_phone) || body.caller_phone || "inconnu";
  const callerName = String(body.caller_name || "Inconnu").trim();
  const callerRole = String(body.caller_role || "").trim();
  const detail = String(body.detail || "").trim();

  // 1. Log dans Firestore (collection notifications)
  try {
    await firestoreCreate("notifications", {
      type: "vip_alert",
      level,
      summary,
      caller_phone: phone,
      caller_name: callerName,
      caller_role: callerRole,
      detail,
      created_at: new Date(),
      sms_sent: false,
      email_sent: false,
    });
  } catch (e) {
    console.error("[norah-alert-yves] notification log failed:", e.message);
  }

  // 2. SMS instantané
  const prefix = { vip: "VIP", urgent: "🚨 URGENT", critical: "🔴 CRITIQUE" }[level];
  const smsBody = `${prefix} — ${callerName} (${phone}) — ${summary}`.slice(0, 320);

  let smsResult = { success: false };
  try {
    smsResult = await twilioSendSMS(YVES_VIP_PHONE, smsBody);
  } catch (e) {
    console.error("[norah-alert-yves] SMS failed:", e.message);
  }

  // 3. Email détaillé
  let emailSent = false;
  try {
    await sendgridSend({
      to: YVES_EMAIL,
      subject: `${prefix} — ${callerName} — ${summary}`,
      html: buildAlertEmailHTML({ level, summary, callerName, phone, callerRole, detail }),
    });
    emailSent = true;
  } catch (e) {
    console.error("[norah-alert-yves] email failed:", e.message);
  }

  return json({
    ok: true,
    level,
    sms_sent: smsResult.success,
    email_sent: emailSent,
  });
};

function buildAlertEmailHTML({ level, summary, callerName, phone, callerRole, detail }) {
  const colors = {
    vip: { bg: "#f59e0b", label: "VIP" },
    urgent: { bg: "#dc2626", label: "🚨 URGENT" },
    critical: { bg: "#7f1d1d", label: "🔴 CRITIQUE" },
  }[level];

  return `
    <div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:${colors.bg};color:#fff;padding:16px;font-weight:bold;font-size:18px;">
        ${colors.label} — Action requise
      </div>
      <div style="padding:20px;background:#f9fafb;">
        <h2 style="margin:0 0 12px;color:#111827;">${escapeHTML(summary)}</h2>
        <table style="width:100%;border-collapse:collapse;">
          <tr><td style="padding:6px 0;color:#6b7280;width:140px;">Appelant</td><td><strong>${escapeHTML(callerName)}</strong></td></tr>
          <tr><td style="padding:6px 0;color:#6b7280;">Téléphone</td><td><a href="tel:${phone}">${phone}</a></td></tr>
          ${callerRole ? `<tr><td style="padding:6px 0;color:#6b7280;">Rôle</td><td>${escapeHTML(callerRole)}</td></tr>` : ""}
        </table>
        ${detail ? `<div style="margin-top:16px;padding:12px;background:#fff;border-left:4px solid ${colors.bg};white-space:pre-wrap;">${escapeHTML(detail)}</div>` : ""}
        <p style="margin-top:20px;color:#6b7280;font-size:13px;">
          📞 Norah lui a confirmé que vous le rappelez dans l'heure.
        </p>
      </div>
      <div style="padding:12px;text-align:center;color:#6b7280;font-size:12px;">
        Norah · Capital Norvex · ${new Date().toLocaleString("fr-CA", { timeZone: "America/Toronto" })}
      </div>
    </div>
  `;
}

function escapeHTML(s) {
  return String(s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
