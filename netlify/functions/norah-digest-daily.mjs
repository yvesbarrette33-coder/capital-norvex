/**
 * Scheduled Function — Digest quotidien 18h00 EST
 * Cron: tous les jours à 22:00 UTC (= 18h EDT en été, 17h EST en hiver)
 *
 * Décision Yves 2026-05-09 : éviter de polluer l'inbox avec un email
 * quotidien. Mode A+C :
 *   A) Stockage Firestore quotidien dans `norahDailyDigests/<YYYY-MM-DD>`
 *      (consulté par la tuile Brain "Activité Norah" — UI à ajouter)
 *   C) Email hebdomadaire le DIMANCHE 18h avec récap 7 derniers jours
 *      (zéro email les autres jours, sauf alertes VIP qui restent instant)
 *
 * Pas d'endpoint public — Netlify l'appelle automatiquement via le scheduler.
 * Possibilité de déclenchement manuel via:
 *   curl -H "x-internal-secret: $INTERNAL_SECRET" \
 *     https://capitalnorvex.com/.netlify/functions/norah-digest-daily
 */

import {
  json,
  unauthorized,
  checkInternalSecret,
  firestoreList,
  firestoreCreate,
  sendgridSend,
  YVES_EMAIL,
} from "./_norah-shared.mjs";

export default async (req, context) => {
  // Si appelé en HTTP manuel (pas par le scheduler), exiger le secret
  // context?.scheduledTime est défini quand Netlify appelle via cron
  const isScheduled = Boolean(context?.scheduledTime);
  if (!isScheduled && !checkInternalSecret(req)) {
    return unauthorized();
  }

  const now = new Date();
  const startOfDay = new Date(now);
  startOfDay.setHours(0, 0, 0, 0);

  let appels = [];
  let rappels = [];
  let alertes = [];
  const errors = [];

  try {
    appels = await firestoreList("appels", {
      sinceField: "created_at",
      sinceDate: startOfDay,
      limit: 500,
    });
  } catch (e) {
    errors.push("appels: " + e.message);
  }

  try {
    rappels = await firestoreList("appels_rappels", {
      sinceField: "created_at",
      sinceDate: startOfDay,
      limit: 200,
    });
  } catch (e) {
    errors.push("rappels: " + e.message);
  }

  try {
    alertes = await firestoreList("notifications", {
      sinceField: "created_at",
      sinceDate: startOfDay,
      limit: 100,
    });
  } catch (e) {
    errors.push("notifications: " + e.message);
  }

  // Stats
  const total = appels.length;
  const qualified = appels.filter((a) => a.qualified).length;
  const vip = alertes.length;
  const rappelsPending = rappels.filter((r) => r.status === "pending").length;

  const byScenario = {};
  for (const a of appels) {
    const s = a.scenario || "autre";
    byScenario[s] = (byScenario[s] || 0) + 1;
  }
  const topScenarios = Object.entries(byScenario)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  const dateLabel = now.toLocaleDateString("fr-CA", {
    timeZone: "America/Toronto",
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  const html = buildDigestHTML({
    dateLabel,
    total,
    qualified,
    vip,
    rappelsPending,
    topScenarios,
    appels: appels.slice(0, 20),
    alertes,
    rappels: rappels.filter((r) => r.status === "pending").slice(0, 10),
    errors,
  });

  // ═══════════════════════════════════════════════════════════════════════
  // A) Stockage Firestore (toujours, pour la tuile Brain "Activité Norah")
  // ═══════════════════════════════════════════════════════════════════════
  // docId = YYYY-MM-DD pour navigation chronologique facile
  const yyyy = now.toLocaleDateString("en-CA", { timeZone: "America/Toronto", year: "numeric" });
  const mm = now.toLocaleDateString("en-CA", { timeZone: "America/Toronto", month: "2-digit" });
  const dd = now.toLocaleDateString("en-CA", { timeZone: "America/Toronto", day: "2-digit" });
  const docId = `${yyyy}-${mm}-${dd}`;

  try {
    await firestoreCreate("norahDailyDigests", {
      date: docId,
      dateLabel,
      total,
      qualified,
      vip,
      rappelsPending,
      topScenarios: Object.fromEntries(topScenarios),
      appelsCount: appels.length,
      alertesCount: alertes.length,
      rappelsCount: rappels.length,
      html,                                 // pour affichage direct dans la tuile Brain
      generatedAt: new Date().toISOString(),
      cronType: isScheduled ? "scheduled" : "manual",
    }, docId);
  } catch (e) {
    errors.push("firestore_digest: " + e.message);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // C) Email hebdomadaire — DIMANCHE seulement
  // ═══════════════════════════════════════════════════════════════════════
  // Day 0 = Sunday en time zone America/Toronto
  const torontoDay = new Date(now.toLocaleString("en-US", { timeZone: "America/Toronto" })).getDay();
  const isSunday = torontoDay === 0;

  let emailSent = false;
  if (isSunday) {
    // Compile les 7 derniers jours depuis Firestore
    try {
      const recentDigests = await firestoreList("norahDailyDigests", {
        sinceField: "generatedAt",
        sinceDate: new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000),
        limit: 7,
      });

      // Stats hebdo
      let weekTotal = 0, weekQualified = 0, weekVip = 0, weekRappels = 0;
      const weekScenarios = {};
      for (const d of recentDigests) {
        weekTotal += d.total || 0;
        weekQualified += d.qualified || 0;
        weekVip += d.vip || 0;
        weekRappels += d.rappelsPending || 0;
        if (d.topScenarios) {
          for (const [s, n] of Object.entries(d.topScenarios)) {
            weekScenarios[s] = (weekScenarios[s] || 0) + Number(n);
          }
        }
      }
      const weekTopScenarios = Object.entries(weekScenarios)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5);

      const weekHtml = buildWeeklyDigestHTML({
        weekTotal,
        weekQualified,
        weekVip,
        weekRappels,
        weekTopScenarios,
        recentDigests: recentDigests.sort((a, b) => (b.date || "").localeCompare(a.date || "")),
      });

      await sendgridSend({
        to: YVES_EMAIL,
        subject: `📊 Récap hebdo Norah — ${dateLabel} — ${weekTotal} appels`,
        html: weekHtml,
      });
      emailSent = true;
    } catch (e) {
      errors.push("sendgrid_weekly: " + e.message);
    }
  }

  return json({
    ok: true,
    total,
    qualified,
    vip,
    scheduled: isScheduled,
    storedInFirestore: true,
    weeklyEmailSent: emailSent,
    isSunday,
    errors: errors.length ? errors : undefined,
  });
};

// Cron Netlify: tous les jours à 22:00 UTC (≈ 18h EDT / 17h EST America/Toronto)
export const config = {
  schedule: "0 22 * * *",
};

function buildDigestHTML({ dateLabel, total, qualified, vip, rappelsPending, topScenarios, appels, alertes, rappels, errors }) {
  const stat = (label, val, color = "#0f172a") => `
    <div style="flex:1;background:#fff;border-radius:8px;padding:14px;margin:4px;border:1px solid #e5e7eb;">
      <div style="color:#6b7280;font-size:12px;text-transform:uppercase;">${label}</div>
      <div style="font-size:28px;font-weight:bold;color:${color};margin-top:4px;">${val}</div>
    </div>
  `;

  return `
    <div style="font-family:Inter,Arial,sans-serif;max-width:680px;margin:0 auto;background:#f9fafb;">
      <div style="background:#0f172a;color:#fff;padding:20px;">
        <h1 style="margin:0;font-size:22px;">📊 Digest Norah — ${dateLabel}</h1>
        <div style="opacity:.7;margin-top:4px;font-size:13px;">Capital Norvex · résumé quotidien 18h00</div>
      </div>

      <div style="display:flex;flex-wrap:wrap;padding:12px;">
        ${stat("Appels totaux", total)}
        ${stat("Qualifiés", qualified, "#10b981")}
        ${stat("VIP / Urgents", vip, vip > 0 ? "#dc2626" : "#0f172a")}
        ${stat("Rappels en attente", rappelsPending, rappelsPending > 0 ? "#f59e0b" : "#0f172a")}
      </div>

      ${topScenarios.length ? `
        <div style="padding:0 16px 16px;">
          <h3 style="color:#111827;margin-bottom:8px;">Top scénarios</h3>
          <table style="width:100%;background:#fff;border-radius:8px;border:1px solid #e5e7eb;border-collapse:separate;border-spacing:0;">
            ${topScenarios.map(([s, n]) => `
              <tr><td style="padding:10px 14px;border-bottom:1px solid #f3f4f6;">${escapeHTML(s.replaceAll("_", " "))}</td><td style="text-align:right;padding:10px 14px;border-bottom:1px solid #f3f4f6;font-weight:bold;">${n}</td></tr>
            `).join("")}
          </table>
        </div>
      ` : ""}

      ${alertes.length ? `
        <div style="padding:0 16px 16px;">
          <h3 style="color:#dc2626;margin-bottom:8px;">⚠️ Alertes VIP du jour</h3>
          <div style="background:#fff;border-radius:8px;border:1px solid #fecaca;">
            ${alertes.map((a) => `
              <div style="padding:12px 14px;border-bottom:1px solid #fef2f2;">
                <div style="font-weight:bold;color:#7f1d1d;">${escapeHTML(a.summary || "—")}</div>
                <div style="color:#6b7280;font-size:13px;margin-top:2px;">${escapeHTML(a.caller_name || "Inconnu")} · ${escapeHTML(a.caller_phone || "")}</div>
              </div>
            `).join("")}
          </div>
        </div>
      ` : ""}

      ${rappels.length ? `
        <div style="padding:0 16px 16px;">
          <h3 style="color:#f59e0b;margin-bottom:8px;">📞 Rappels en attente</h3>
          <div style="background:#fff;border-radius:8px;border:1px solid #fde68a;">
            ${rappels.map((r) => `
              <div style="padding:12px 14px;border-bottom:1px solid #fffbeb;">
                <div style="font-weight:bold;">${escapeHTML(r.caller_name || "Inconnu")}</div>
                <div style="color:#6b7280;font-size:13px;">${escapeHTML(r.caller_phone || "")} — ${escapeHTML(r.reason || "")}</div>
              </div>
            `).join("")}
          </div>
        </div>
      ` : ""}

      ${appels.length ? `
        <div style="padding:0 16px 16px;">
          <h3 style="color:#111827;margin-bottom:8px;">Derniers appels (max 20)</h3>
          <table style="width:100%;background:#fff;border-radius:8px;border:1px solid #e5e7eb;font-size:13px;border-collapse:separate;border-spacing:0;">
            <tr style="background:#f3f4f6;">
              <th style="text-align:left;padding:8px 12px;">Heure</th>
              <th style="text-align:left;padding:8px 12px;">Téléphone</th>
              <th style="text-align:left;padding:8px 12px;">Scénario</th>
              <th style="text-align:left;padding:8px 12px;">Action</th>
            </tr>
            ${appels.map((a) => {
              const t = a.ended_at ? new Date(a.ended_at).toLocaleTimeString("fr-CA", { timeZone: "America/Toronto", hour: "2-digit", minute: "2-digit" }) : "—";
              return `
                <tr>
                  <td style="padding:8px 12px;border-top:1px solid #f3f4f6;">${t}</td>
                  <td style="padding:8px 12px;border-top:1px solid #f3f4f6;">${escapeHTML(a.caller_phone || "—")}</td>
                  <td style="padding:8px 12px;border-top:1px solid #f3f4f6;">${escapeHTML((a.scenario || "").replaceAll("_", " "))}</td>
                  <td style="padding:8px 12px;border-top:1px solid #f3f4f6;color:#6b7280;">${escapeHTML((a.action_taken || "").slice(0, 60))}</td>
                </tr>
              `;
            }).join("")}
          </table>
        </div>
      ` : `
        <div style="padding:20px;text-align:center;color:#6b7280;">Aucun appel aujourd'hui.</div>
      `}

      ${errors.length ? `
        <div style="margin:12px 16px;padding:12px;background:#fef2f2;border-left:4px solid #dc2626;color:#7f1d1d;">
          <strong>Erreurs:</strong><br>
          ${errors.map(escapeHTML).join("<br>")}
        </div>
      ` : ""}

      <div style="padding:16px;text-align:center;color:#6b7280;font-size:12px;border-top:1px solid #e5e7eb;background:#fff;">
        Généré automatiquement par Norah · Capital Norvex Inc.
      </div>
      <div style="padding:14px 16px;text-align:center;color:#64748b;font-size:11px;background:#f8fafc;border-top:1px solid #e5e7eb;line-height:1.5;letter-spacing:.3px">
        <strong style="color:#0f172a">CAPITAL NORVEX INC.</strong> · 2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
        Téléphone : 1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
      </div>
    </div>
  `;
}

function escapeHTML(s) {
  return String(s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ─── Récap hebdo dimanche soir (Yves le lit lundi matin avec son café) ───
function buildWeeklyDigestHTML({ weekTotal, weekQualified, weekVip, weekRappels, weekTopScenarios, recentDigests }) {
  const stat = (label, val, color = "#0f172a") => `
    <div style="flex:1;background:#fff;border-radius:8px;padding:14px;margin:4px;border:1px solid #e5e7eb;">
      <div style="color:#6b7280;font-size:12px;text-transform:uppercase;">${label}</div>
      <div style="font-size:28px;font-weight:bold;color:${color};margin-top:4px;">${val}</div>
    </div>
  `;

  const dailyRow = (d) => {
    const dayLabel = d.dateLabel || d.date || "—";
    return `<tr>
      <td style="padding:10px 14px;border-bottom:1px solid #f3f4f6;">${escapeHTML(dayLabel)}</td>
      <td style="text-align:right;padding:10px 14px;border-bottom:1px solid #f3f4f6;font-weight:bold;">${d.total || 0}</td>
      <td style="text-align:right;padding:10px 14px;border-bottom:1px solid #f3f4f6;color:#10b981;">${d.qualified || 0}</td>
      <td style="text-align:right;padding:10px 14px;border-bottom:1px solid #f3f4f6;color:${(d.vip || 0) > 0 ? "#dc2626" : "#6b7280"};">${d.vip || 0}</td>
    </tr>`;
  };

  return `
    <div style="font-family:Inter,Arial,sans-serif;max-width:680px;margin:0 auto;background:#f9fafb;">
      <div style="background:#0f172a;color:#fff;padding:20px;">
        <h1 style="margin:0;font-size:22px;">📊 Récap hebdomadaire Norah</h1>
        <div style="opacity:.7;margin-top:4px;font-size:13px;">Capital Norvex · 7 derniers jours · dimanche 18h</div>
      </div>

      <div style="display:flex;flex-wrap:wrap;padding:12px;">
        ${stat("Appels semaine", weekTotal)}
        ${stat("Qualifiés", weekQualified, "#10b981")}
        ${stat("VIP / Urgents", weekVip, weekVip > 0 ? "#dc2626" : "#0f172a")}
        ${stat("Rappels en attente", weekRappels, weekRappels > 0 ? "#f59e0b" : "#0f172a")}
      </div>

      ${weekTopScenarios.length ? `
        <div style="padding:0 16px 16px;">
          <h3 style="color:#111827;margin-bottom:8px;">Top scénarios de la semaine</h3>
          <table style="width:100%;background:#fff;border-radius:8px;border:1px solid #e5e7eb;border-collapse:separate;border-spacing:0;">
            ${weekTopScenarios.map(([s, n]) => `
              <tr><td style="padding:10px 14px;border-bottom:1px solid #f3f4f6;">${escapeHTML(s.replaceAll("_", " "))}</td><td style="text-align:right;padding:10px 14px;border-bottom:1px solid #f3f4f6;font-weight:bold;">${n}</td></tr>
            `).join("")}
          </table>
        </div>
      ` : ""}

      ${recentDigests.length ? `
        <div style="padding:0 16px 16px;">
          <h3 style="color:#111827;margin-bottom:8px;">Détail jour par jour</h3>
          <table style="width:100%;background:#fff;border-radius:8px;border:1px solid #e5e7eb;font-size:13px;border-collapse:separate;border-spacing:0;">
            <tr style="background:#f3f4f6;">
              <th style="text-align:left;padding:8px 12px;">Jour</th>
              <th style="text-align:right;padding:8px 12px;">Total</th>
              <th style="text-align:right;padding:8px 12px;">Qualifiés</th>
              <th style="text-align:right;padding:8px 12px;">VIP</th>
            </tr>
            ${recentDigests.map(dailyRow).join("")}
          </table>
        </div>
      ` : ""}

      <div style="padding:14px 16px;text-align:center;color:#64748b;font-size:11px;background:#f8fafc;border-top:1px solid #e5e7eb;line-height:1.5;letter-spacing:.3px">
        <strong style="color:#0f172a">CAPITAL NORVEX INC.</strong> · 2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
        Téléphone : 1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
      </div>
    </div>
  `;
}
