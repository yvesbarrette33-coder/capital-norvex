/**
 * Scheduled Function — Brief matinal Norvex Brain v1
 * Cron: tous les jours à 11:00 UTC (= 7h00 EDT en été, 6h00 EST en hiver)
 *
 * Pas d'endpoint public — Netlify l'appelle automatiquement via le scheduler.
 * Possibilité de déclenchement manuel via:
 *   curl -H "x-internal-secret: $INTERNAL_SECRET" \
 *     https://capitalnorvex.com/.netlify/functions/brain-daily-brief
 *
 * Génère un email récapitulatif à yves@capitalnorvex.com:
 *   ─ CAPITAL    : nouvelles cibles, prêtes, pending, réponses
 *   ─ COURTIERS  : warms actifs, deal cards à valider
 *   ─ PROMOTEURS : actions à valider
 *   ─ ALERTES    : tentatives TIER ZERO (24h)
 *   + Bloc « À approuver » avec lien direct vers le pipeline
 *
 * Réécrit du Python original `agents/brain/daily_brief.py` en .mjs Netlify
 * pour activation cron native (Python ne peut pas tourner en Scheduled Function).
 */

import {
  json,
  unauthorized,
  checkInternalSecret,
  sendgridSend,
  YVES_EMAIL,
  CAPITAL_NORVEX_SIGNATURE_HTML,
  getFirestoreToken,
  firestoreDocToObject,
} from "./_norah-shared.mjs";

const PIPELINE_URL = "https://capitalnorvex.com/capital-norvex-pipeline.html";

// ─── Brand colors (Variation A) ──────────────────────────────────────────
const COLOR_GOLD = "#B8860B";
const COLOR_INK = "#080808";
const COLOR_CREAM = "#FAF8F4";
const COLOR_MUTED = "#5b5b5b";

// ─────────────────────────────────────────────────────────────────────────
// Firestore helpers — query par filtre `status == X` (un seul filtre,
// pas d'index composite requis)
// ─────────────────────────────────────────────────────────────────────────

async function queryByEquality(collection, fieldPath, value, limit = 50) {
  const { accessToken, projectId } = await getFirestoreToken();
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;

  const structuredQuery = {
    from: [{ collectionId: collection }],
    where: {
      fieldFilter: {
        field: { fieldPath },
        op: "EQUAL",
        value: { stringValue: String(value) },
      },
    },
    limit,
  };

  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ structuredQuery }),
  });

  const results = await resp.json();
  if (!Array.isArray(results)) return [];
  return results.filter((r) => r.document).map((r) => firestoreDocToObject(r.document));
}

async function queryRecentSince(collection, sinceField, sinceDate, limit = 100) {
  const { accessToken, projectId } = await getFirestoreToken();
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;

  const structuredQuery = {
    from: [{ collectionId: collection }],
    where: {
      fieldFilter: {
        field: { fieldPath: sinceField },
        op: "GREATER_THAN_OR_EQUAL",
        value: { timestampValue: new Date(sinceDate).toISOString() },
      },
    },
    limit,
  };

  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ structuredQuery }),
  });

  const results = await resp.json();
  if (!Array.isArray(results)) return [];
  return results.filter((r) => r.document).map((r) => firestoreDocToObject(r.document));
}

// ─────────────────────────────────────────────────────────────────────────
// Sections
// ─────────────────────────────────────────────────────────────────────────

async function sectionCapital() {
  const [newTargets, ready, pending, responded] = await Promise.all([
    queryByEquality("capitalTargets", "status", "research", 100),
    queryByEquality("capitalTargets", "status", "ready", 100),
    queryByEquality("capitalApproaches", "status", "pending_yves_approval", 100),
    queryByEquality("capitalApproaches", "status", "responded", 100),
  ]);
  return {
    newCount: newTargets.length,
    readyCount: ready.length,
    pendingCount: pending.length,
    respondedCount: responded.length,
  };
}

async function sectionCourtiers() {
  const [warms, pending] = await Promise.all([
    queryByEquality("brokers", "relationshipStatus", "warm", 200),
    queryByEquality("brokerCommunications", "status", "pending_yves_approval", 100),
  ]);
  return {
    warmsCount: warms.length,
    pendingCount: pending.length,
  };
}

async function sectionPromoteurs() {
  const pending = await queryByEquality(
    "promoterApproaches",
    "status",
    "pending_yves_approval",
    100,
  );
  return { pendingCount: pending.length };
}

async function sectionAlertes() {
  const since = new Date(Date.now() - 24 * 60 * 60 * 1000);
  const recent = await queryRecentSince("agentAuditLog", "timestamp", since, 200);
  // Filtre en JS pour éviter index composite Firestore
  const tierZeroBlocks = recent.filter((r) => r.result === "blocked_tier_zero");
  return { tierZeroCount: tierZeroBlocks.length };
}

// ─────────────────────────────────────────────────────────────────────────
// HTML render — style Variation A (crème / encre / or, Georgia 13.5px)
// ─────────────────────────────────────────────────────────────────────────

function renderBriefHTML({ cap, crt, pro, alr, dateLabel }) {
  const totalPending = cap.pendingCount + crt.pendingCount + pro.pendingCount;

  const line = (label, txt) => `
    <p style="margin:0 0 10px 0;font-family:Georgia,serif;font-size:13.5px;line-height:1.6;color:${COLOR_INK};">
      <strong style="color:${COLOR_GOLD};letter-spacing:1.5px;font-size:12px;">─ ${label}</strong>
      &nbsp;: ${txt}
    </p>`;

  const capTxt =
    `${cap.newCount} nouvelle(s) cible(s), ` +
    `${cap.readyCount} prête(s), ` +
    `${cap.pendingCount} en attente d'approbation, ` +
    `${cap.respondedCount} réponse(s) à analyser.`;

  const crtTxt =
    `${crt.warmsCount} courtier(s) warm actif(s), ` +
    `${crt.pendingCount} communication(s) à valider.`;

  const proTxt = `${pro.pendingCount} action(s) à valider.`;

  const alrTxt =
    alr.tierZeroCount > 0
      ? `<strong style="color:#B22222;">${alr.tierZeroCount} tentative(s) TIER ZERO bloquée(s)</strong> (24h).`
      : `aucune.`;

  const approvalBlock = totalPending
    ? `
      <div style="margin:24px 0 0 0;padding:16px 18px;background:#FFFCF5;border-left:3px solid ${COLOR_GOLD};border-radius:2px;">
        <p style="margin:0 0 8px 0;font-family:Georgia,serif;font-size:13.5px;color:${COLOR_INK};">
          <strong>${totalPending}</strong> communication(s) en attente d'approbation aujourd'hui.
        </p>
        <p style="margin:0;font-family:Georgia,serif;font-size:13.5px;">
          <a href="${PIPELINE_URL}" style="color:${COLOR_GOLD};text-decoration:none;border-bottom:1px solid ${COLOR_GOLD};">
            Ouvrir le pipeline →
          </a>
        </p>
      </div>`
    : "";

  return `<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Brief matinal — Capital Norvex</title>
</head>
<body style="margin:0;padding:0;background:${COLOR_CREAM};font-family:Georgia,serif;color:${COLOR_INK};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:${COLOR_CREAM};">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;background:#FFFFFF;border:1px solid #EAE4D6;border-radius:4px;">
          <tr>
            <td style="padding:36px 44px 28px;border-bottom:1px solid #EAE4D6;">
              <p style="margin:0;font-family:Georgia,serif;font-size:11px;letter-spacing:3px;color:${COLOR_GOLD};text-transform:uppercase;">
                Capital Norvex Inc.
              </p>
              <h1 style="margin:6px 0 0 0;font-family:Georgia,serif;font-size:22px;font-weight:400;color:${COLOR_INK};letter-spacing:.5px;">
                Brief matinal
              </h1>
              <p style="margin:4px 0 0 0;font-family:Georgia,serif;font-size:12px;color:${COLOR_MUTED};font-style:italic;">
                ${dateLabel}
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:32px 44px;">
              <p style="margin:0 0 14px 0;font-family:Georgia,serif;font-size:14px;color:${COLOR_INK};">
                Bonjour Yves,
              </p>
              <p style="margin:0 0 24px 0;font-family:Georgia,serif;font-size:13.5px;color:${COLOR_INK};">
                Voici le brief Norvex de ce matin.
              </p>
              ${line("CAPITAL", capTxt)}
              ${line("COURTIERS", crtTxt)}
              ${line("PROMOTEURS", proTxt)}
              ${line("ALERTES", alrTxt)}
              ${approvalBlock}
              <p style="margin:32px 0 0 0;font-family:Georgia,serif;font-size:11.5px;color:${COLOR_MUTED};font-style:italic;">
                — Norvex Brain v1 (cron 7h00 EDT)
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:0 44px 28px;">
              ${CAPITAL_NORVEX_SIGNATURE_HTML}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;
}

// ─────────────────────────────────────────────────────────────────────────
// Handler
// ─────────────────────────────────────────────────────────────────────────

export default async (req, context) => {
  // Si appelé en HTTP manuel (pas par le scheduler), exiger le secret interne
  const isScheduled = Boolean(context?.scheduledTime);
  if (!isScheduled && !checkInternalSecret(req)) {
    return unauthorized();
  }

  // Mode test : ?dry=1 retourne le HTML sans envoi
  const url = new URL(req.url);
  const isDry = url.searchParams.get("dry") === "1";

  const errors = [];
  let cap = { newCount: 0, readyCount: 0, pendingCount: 0, respondedCount: 0 };
  let crt = { warmsCount: 0, pendingCount: 0 };
  let pro = { pendingCount: 0 };
  let alr = { tierZeroCount: 0 };

  try { cap = await sectionCapital(); }
  catch (e) { errors.push("capital: " + e.message); }

  try { crt = await sectionCourtiers(); }
  catch (e) { errors.push("courtiers: " + e.message); }

  try { pro = await sectionPromoteurs(); }
  catch (e) { errors.push("promoteurs: " + e.message); }

  try { alr = await sectionAlertes(); }
  catch (e) { errors.push("alertes: " + e.message); }

  const dateLabel = new Date().toLocaleDateString("fr-CA", {
    timeZone: "America/Toronto",
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const html = renderBriefHTML({ cap, crt, pro, alr, dateLabel });

  if (isDry) {
    return new Response(html, {
      status: 200,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  }

  const subject = `[Capital Norvex] Brief matinal — ${dateLabel}`;

  try {
    await sendgridSend({
      to: YVES_EMAIL,
      subject,
      html,
    });
  } catch (e) {
    errors.push("sendgrid: " + e.message);
    return json({ ok: false, errors }, 500);
  }

  return json({
    ok: true,
    scheduled: isScheduled,
    counts: {
      capital: cap,
      courtiers: crt,
      promoteurs: pro,
      alertes: alr,
    },
    errors: errors.length ? errors : undefined,
  });
};

// Cron Netlify: tous les jours à 11:00 UTC
// = 07h00 EDT (heure d'été, mai-novembre)
// = 06h00 EST (heure d'hiver, novembre-mars)
export const config = {
  schedule: "0 11 * * *",
};
