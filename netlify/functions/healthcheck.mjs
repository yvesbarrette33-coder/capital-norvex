/**
 * Norvex Healthcheck™ — surveillance automatique du site en production.
 *
 * Cron : toutes les 6h (00:00, 06:00, 12:00, 18:00 UTC)
 *
 * Vérifie les endpoints et pages critiques. Si TOUT OK → silencieux.
 * Si UN truc plante → email à yves@capitalnorvex.com via SendGrid.
 *
 * Pur read-only : aucune écriture, aucun side-effect business.
 *
 * Manuel :
 *   curl -H "x-internal-secret: $SECRET" https://capitalnorvex.com/.netlify/functions/healthcheck
 *   curl https://capitalnorvex.com/.netlify/functions/healthcheck?dry=1  (pas d'email même si fail)
 */

const BASE_URL = process.env.URL || "https://capitalnorvex.com";

// Liste des checks. Chaque check : { name, url, method, expectStatus, expectContains? }
const CHECKS = [
  // --- Pages publiques FR ---
  {
    name: "Home FR",
    url: "/",
    method: "GET",
    expectStatus: 200,
    expectContains: "Capital Norvex",
  },
  {
    name: "Capsules vidéos",
    url: "/capsules.html",
    method: "GET",
    expectStatus: 200,
    expectContains: "video-wrap",
  },
  {
    name: "Score Norvex (page)",
    url: "/capital-norvex-score.html",
    method: "GET",
    expectStatus: 200,
    expectContains: "Score Norvex",
  },
  {
    name: "Candidature courtier (page)",
    url: "/courtier-candidature.html",
    method: "GET",
    expectStatus: 200,
    expectContains: "courtier",
  },

  // --- Endpoints Netlify Functions critiques (smoke tests) ---
  // submit-analysis : GET → 405 Method Not Allowed (signe que la fonction est déployée).
  {
    name: "submit-analysis (déployé)",
    url: "/.netlify/functions/submit-analysis",
    method: "GET",
    expectStatus: 405,
  },
  // upload-doc : GET → 405 attendu (uniquement POST accepté).
  {
    name: "upload-doc (déployé)",
    url: "/.netlify/functions/upload-doc",
    method: "GET",
    expectStatus: 405,
  },
  // get-result : GET sans jobId → 400 attendu (preuve que la fonction tourne).
  {
    name: "get-result (déployé)",
    url: "/.netlify/functions/get-result",
    method: "GET",
    expectStatus: 400,
  },
];

async function runCheck(check) {
  const fullUrl = check.url.startsWith("http") ? check.url : BASE_URL + check.url;
  const started = Date.now();
  try {
    const r = await fetch(fullUrl, {
      method: check.method || "GET",
      redirect: "follow",
      headers: { "User-Agent": "Norvex-Healthcheck/1.0" },
    });
    const elapsed = Date.now() - started;
    const statusOk = r.status === check.expectStatus;
    let bodyOk = true;
    let bodySnippet = "";
    if (check.expectContains) {
      const text = await r.text();
      bodySnippet = text.slice(0, 200);
      bodyOk = text.toLowerCase().includes(check.expectContains.toLowerCase());
    }
    const ok = statusOk && bodyOk;
    return {
      name: check.name,
      url: check.url,
      ok,
      status: r.status,
      expectStatus: check.expectStatus,
      bodyOk,
      expectContains: check.expectContains || null,
      elapsedMs: elapsed,
      reason: ok
        ? null
        : !statusOk
        ? `status ${r.status} (attendu ${check.expectStatus})`
        : `body ne contient pas "${check.expectContains}"`,
    };
  } catch (err) {
    return {
      name: check.name,
      url: check.url,
      ok: false,
      status: 0,
      elapsedMs: Date.now() - started,
      reason: `fetch failed: ${err.message}`,
    };
  }
}

async function sendFailureEmail(failures, total) {
  const apiKey = process.env.SENDGRID_API_KEY;
  if (!apiKey) {
    console.warn("[healthcheck] SENDGRID_API_KEY manquant — pas d'email envoyé");
    return false;
  }

  const rows = failures
    .map(
      (f) => `
    <tr>
      <td style="padding:8px;border-bottom:1px solid #eee;font-weight:600;">${f.name}</td>
      <td style="padding:8px;border-bottom:1px solid #eee;font-family:monospace;font-size:12px;">${f.url}</td>
      <td style="padding:8px;border-bottom:1px solid #eee;color:#c0392b;">${f.reason || "?"}</td>
    </tr>`
    )
    .join("");

  const html = `
  <div style="font-family:Arial,sans-serif;max-width:700px;margin:auto;color:#222;">
    <h2 style="color:#c0392b;margin-bottom:6px;">⚠️ Norvex Healthcheck — ${failures.length}/${total} test(s) échoué(s)</h2>
    <p style="color:#555;margin-top:0;">Détecté le ${new Date().toLocaleString("fr-CA", { timeZone: "America/Montreal" })} (heure Montréal).</p>
    <table style="border-collapse:collapse;width:100%;margin-top:16px;">
      <thead>
        <tr style="background:#f5f5f5;">
          <th style="text-align:left;padding:8px;border-bottom:2px solid #ddd;">Check</th>
          <th style="text-align:left;padding:8px;border-bottom:2px solid #ddd;">URL</th>
          <th style="text-align:left;padding:8px;border-bottom:2px solid #ddd;">Raison</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
    <p style="font-size:12px;color:#888;margin-top:24px;">
      Norvex Healthcheck™ tourne automatiquement toutes les 6h. Tu reçois cet email
      uniquement quand au moins un check plante.
    </p>
  </div>`;

  const r = await fetch("https://api.sendgrid.com/v3/mail/send", {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      personalizations: [
        {
          to: [{ email: "yves@capitalnorvex.com" }],
          subject: `⚠️ Norvex Healthcheck — ${failures.length}/${total} échec(s) sur le site`,
        },
      ],
      from: { email: "info@capitalnorvex.com", name: "Norvex Healthcheck" },
      reply_to: { email: "yves@capitalnorvex.com" },
      content: [{ type: "text/html", value: html }],
      headers: {
        "X-Capital-Norvex-Type": "healthcheck-alert",
        "X-Auto-Response-Suppress": "All",
      },
    }),
  });
  if (!r.ok) {
    const txt = await r.text();
    console.error(`[healthcheck] SendGrid ${r.status}: ${txt}`);
    return false;
  }
  return true;
}

export default async (req, context) => {
  const url = new URL(req.url);
  const isDry = url.searchParams.get("dry") === "1";
  const isScheduled = Boolean(context?.scheduledTime);

  // Auth pour appels manuels (cron Netlify n'a pas besoin de secret)
  if (!isScheduled) {
    const provided = req.headers.get("x-internal-secret");
    const expected = process.env.INTERNAL_SECRET;
    // Si pas de secret expected, on laisse passer pour /dry (debugging local)
    if (expected && provided !== expected && !isDry) {
      return new Response(JSON.stringify({ error: "unauthorized" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }
  }

  // Run all checks in parallel
  const results = await Promise.all(CHECKS.map(runCheck));
  const failures = results.filter((r) => !r.ok);
  const allOk = failures.length === 0;

  let emailSent = false;
  if (!allOk && !isDry) {
    try {
      emailSent = await sendFailureEmail(failures, results.length);
    } catch (e) {
      console.error("[healthcheck] sendFailureEmail error:", e.message);
    }
  }

  const body = {
    ok: allOk,
    total: results.length,
    failures: failures.length,
    emailSent,
    scheduled: isScheduled,
    dry: isDry,
    timestamp: new Date().toISOString(),
    results,
  };

  return new Response(JSON.stringify(body, null, 2), {
    status: allOk ? 200 : 503,
    headers: { "Content-Type": "application/json" },
  });
};

// Cron Netlify : toutes les 6 heures (00:00, 06:00, 12:00, 18:00 UTC)
export const config = {
  schedule: "0 */6 * * *",
};
