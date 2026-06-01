/**
 * POST /.netlify/functions/norah-log-call
 * Header: X-Internal-Secret
 * Body: {
 *   caller_phone, caller_role?, caller_identified?,
 *   dossier_id?, scenario, summary,
 *   action_taken, qualified, transcript_url?,
 *   started_at?, ended_at?, duration_sec?
 * }
 *
 * Tool ElevenLabs #8 — log_call_summary
 *
 * Loggue chaque appel dans Firestore `appels` à la fin de la conversation.
 * Si qualified=true → email résumé à Yves (sauf VIP où l'alert_yves a déjà tout fait).
 *
 * Pas de session 2FA requise (appelé en fin d'appel pour TOUS les appels,
 * incluant spams, raccrochés, etc.)
 */

import {
  json,
  unauthorized,
  badRequest,
  serverError,
  checkInternalSecret,
  firestoreCreate,
  sendgridSend,
  normalizePhone,
  YVES_EMAIL,
} from "./_norah-shared.mjs";

const VALID_SCENARIOS = [
  "promoteur_premiere_fois",
  "courtier_nouveau_dossier",
  "courtier_verifie_statut",
  "client_avancement",
  "info_generale",
  "co_preteur",
  "notaire_closing",
  "avocat_partenaire",
  "urgence_closing",
  "client_insiste_yves",
  "appelant_hostile",
  "journaliste_media",
  "courtier_non_accredite",
  "hors_territoire",
  "hors_fourchette",
  "spam_ou_raccroche",
  "autre",
];

export default async (req) => {
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });
  if (!checkInternalSecret(req)) return unauthorized();

  let body;
  try { body = await req.json(); } catch { return badRequest("Invalid JSON body"); }

  const phone = normalizePhone(body.caller_phone) || body.caller_phone || "unknown";
  const scenario = String(body.scenario || "autre").trim();
  if (!VALID_SCENARIOS.includes(scenario)) {
    return badRequest(`scenario invalide: ${scenario}`);
  }

  const summary = String(body.summary || "").trim().slice(0, 4000);
  const actionTaken = String(body.action_taken || "").trim().slice(0, 500);
  const qualified = body.qualified === true || body.qualified === "true";

  const log = {
    caller_phone: phone,
    caller_role: body.caller_role || null,
    caller_identified: body.caller_identified === true,
    dossier_id: body.dossier_id || null,
    scenario,
    summary,
    action_taken: actionTaken,
    qualified,
    transcript_url: body.transcript_url || null,
    started_at: body.started_at || null,
    ended_at: body.ended_at || new Date().toISOString(),
    duration_sec: typeof body.duration_sec === "number" ? body.duration_sec : null,
    created_at: new Date(),
  };

  let doc;
  try {
    doc = await firestoreCreate("appels", log);
  } catch (e) {
    return serverError("Firestore create failed: " + e.message);
  }

  // Si appel qualifié et NON-VIP (les VIP ont déjà reçu une alerte via alert_yves),
  // on envoie un email résumé à Yves
  const isVipScenario = ["co_preteur", "notaire_closing", "avocat_partenaire", "urgence_closing", "journaliste_media"].includes(scenario);

  let emailSent = false;
  if (qualified && !isVipScenario) {
    try {
      await sendgridSend({
        to: YVES_EMAIL,
        subject: `📞 Appel ${scenario.replaceAll("_", " ")} — ${phone}`,
        html: buildSummaryEmailHTML(log),
      });
      emailSent = true;
    } catch (e) {
      console.error("[norah-log-call] email failed:", e.message);
    }
  }

  return json({
    ok: true,
    appel_id: doc?.id || null,
    email_sent: emailSent,
    scenario,
    qualified,
  });
};

function buildSummaryEmailHTML(log) {
  return `
    <div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:#0f172a;color:#fff;padding:16px;">
        <h2 style="margin:0;">📞 Résumé d'appel — Norah</h2>
        <div style="font-size:13px;opacity:.8;margin-top:4px;">
          ${new Date(log.ended_at).toLocaleString("fr-CA", { timeZone: "America/Toronto" })}
        </div>
      </div>
      <div style="padding:20px;background:#f9fafb;">
        <table style="width:100%;border-collapse:collapse;">
          <tr><td style="padding:6px 0;color:#6b7280;width:140px;">Appelant</td><td><a href="tel:${log.caller_phone}">${log.caller_phone}</a> ${log.caller_identified ? "✅" : "⚠️ non identifié"}</td></tr>
          <tr><td style="padding:6px 0;color:#6b7280;">Rôle</td><td>${log.caller_role || "—"}</td></tr>
          ${log.dossier_id ? `<tr><td style="padding:6px 0;color:#6b7280;">Dossier</td><td>${log.dossier_id}</td></tr>` : ""}
          <tr><td style="padding:6px 0;color:#6b7280;">Scénario</td><td>${log.scenario.replaceAll("_", " ")}</td></tr>
          <tr><td style="padding:6px 0;color:#6b7280;">Action prise</td><td>${escapeHTML(log.action_taken) || "—"}</td></tr>
          ${log.duration_sec ? `<tr><td style="padding:6px 0;color:#6b7280;">Durée</td><td>${Math.round(log.duration_sec)} sec</td></tr>` : ""}
        </table>
        <h3 style="color:#111827;margin-top:20px;">Résumé</h3>
        <div style="white-space:pre-wrap;color:#374151;">${escapeHTML(log.summary)}</div>
        ${log.transcript_url ? `<p><a href="${log.transcript_url}">📄 Transcript complet</a></p>` : ""}
      </div>
    </div>
  `;
}

function escapeHTML(s) {
  return String(s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
