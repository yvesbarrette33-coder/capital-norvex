/**
 * Émile — NORVEX BRIEFING™ — endpoint
 *
 * POST /api/emile-generate-brief
 *   body: { email: "<recipient>", rdvDateTime?: ISO, source?: "rdv-public" | "rdv-partenaire" | "manual" }
 *
 * Pipeline :
 *   1. pullTargetByEmail (capitalTargets / advisorTargets / promoteurTargets)
 *   2. pullSendGridStats (engagement live)
 *   3. callBoardOfAdvisors (Claude Opus 4.6)
 *   4. renderBriefHTML
 *   5. Email Yves avec brief HTML inline + reply_to du destinataire pour contexte
 *   6. Tracking dans Firestore : `emileBriefs/<id>` pour audit
 *
 * Sécurité : INTERNAL_SECRET requis (header `x-internal-secret`).
 */

import {
  pullTargetByEmail,
  pullSendGridStats,
  callBoardOfAdvisors,
  renderBriefHTML,
} from "./_emile-shared.mjs";

const ENC = new TextEncoder();
const YVES_EMAIL = process.env.YVES_EMAIL || "yves@capitalnorvex.com";
const ORGANIZER_EMAIL = process.env.MAIL_FROM || "info@capitalnorvex.com";
const INTERNAL_SECRET = process.env.INTERNAL_SECRET || "";

// ── Firebase token (réutilise pattern rdv-public-approve) ────────────────
async function getFirestoreToken(sa) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: sa.client_email, sub: sa.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now, exp: now + 3600,
    scope: "https://www.googleapis.com/auth/datastore",
  };
  const b64 = (obj) => btoa(JSON.stringify(obj))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const signingInput = `${b64(header)}.${b64(payload)}`;
  const pemBody = sa.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\n/g, "");
  const keyData = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));
  const privateKey = await crypto.subtle.importKey("pkcs8", keyData.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", privateKey, ENC.encode(signingInput));
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const jwt = `${signingInput}.${sigB64}`;
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: jwt,
    }),
  });
  const data = await r.json();
  if (!data.access_token) throw new Error("Firestore token failed");
  return { token: data.access_token, projectId: sa.project_id };
}

// ── Email Yves via SendGrid ──────────────────────────────────────────────
async function sendBriefToYves({ recipientEmail, recipientName, html, rdvDateTime }) {
  const sgKey = process.env.SENDGRID_API_KEY;
  if (!sgKey) return { ok: false, error: "SENDGRID_API_KEY not set" };

  const subjectDate = rdvDateTime
    ? new Date(rdvDateTime).toLocaleDateString("fr-CA", { day: "2-digit", month: "short", year: "numeric" })
    : new Date().toLocaleDateString("fr-CA", { day: "2-digit", month: "short", year: "numeric" });
  const subject = `📋 Brief Émile — ${recipientName || recipientEmail} — RDV ${subjectDate}`;

  const r = await fetch("https://api.sendgrid.com/v3/mail/send", {
    method: "POST",
    headers: { Authorization: `Bearer ${sgKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      personalizations: [{ to: [{ email: YVES_EMAIL }] }],
      from: { email: ORGANIZER_EMAIL, name: "Émile · Capital Norvex" },
      reply_to: { email: YVES_EMAIL, name: "Yves Barrette" },
      subject,
      content: [{ type: "text/html", value: html }],
      tracking_settings: {
        click_tracking: { enable: false, enable_text: false },
        open_tracking: { enable: false },
      },
    }),
  });
  if (r.ok || r.status === 202) return { ok: true };
  const txt = await r.text();
  return { ok: false, error: `SendGrid ${r.status}: ${txt.slice(0, 200)}` };
}

// ── Save audit Firestore ─────────────────────────────────────────────────
async function saveBriefAudit(projectId, fsToken, briefData) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/emileBriefs`;
  const fields = {};
  for (const [k, v] of Object.entries(briefData)) {
    if (v === null || v === undefined) continue;
    if (typeof v === "string") fields[k] = { stringValue: v };
    else if (typeof v === "boolean") fields[k] = { booleanValue: v };
    else if (typeof v === "number") fields[k] = { integerValue: String(v) };
    else fields[k] = { stringValue: JSON.stringify(v) };
  }
  try {
    await fetch(url, {
      method: "POST",
      headers: { Authorization: `Bearer ${fsToken}`, "Content-Type": "application/json" },
      body: JSON.stringify({ fields }),
    });
  } catch (e) {
    console.warn("[Émile] audit save failed:", e.message);
  }
}

// ── Handler ──────────────────────────────────────────────────────────────
export default async (req) => {
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ ok: false, error: "POST only" }), {
      status: 405, headers: { "Content-Type": "application/json" },
    });
  }

  // Sécurité interne
  const secret = req.headers.get("x-internal-secret") || "";
  if (INTERNAL_SECRET && secret !== INTERNAL_SECRET) {
    return new Response(JSON.stringify({ ok: false, error: "Unauthorized" }), {
      status: 401, headers: { "Content-Type": "application/json" },
    });
  }

  let body;
  try { body = await req.json(); } catch {
    return new Response(JSON.stringify({ ok: false, error: "Invalid JSON" }), {
      status: 400, headers: { "Content-Type": "application/json" },
    });
  }

  const { email, rdvDateTime, source = "manual" } = body;
  if (!email) {
    return new Response(JSON.stringify({ ok: false, error: "email required" }), {
      status: 400, headers: { "Content-Type": "application/json" },
    });
  }

  try {
    // Firestore auth (pattern identique à rdv-public-approve.mjs)
    const { getServiceAccount } = await import("./_firebase-sa.mjs");

    const sa = await getServiceAccount();
    const { token: fsToken, projectId } = await getFirestoreToken(sa);

    // 1. Pull target
    const targetMatch = await pullTargetByEmail(projectId, fsToken, email);
    if (!targetMatch) {
      return new Response(JSON.stringify({
        ok: false,
        error: `Aucun target trouvé pour ${email} dans Firestore (capitalTargets/advisorTargets/promoteurTargets/courtierTargets)`,
      }), { status: 404, headers: { "Content-Type": "application/json" } });
    }
    const target = targetMatch.data;

    // 2. SendGrid stats
    const engagement = await pullSendGridStats(email);

    // 3. Board of advisors
    const advisor = await callBoardOfAdvisors(target, engagement);

    // 4. Render HTML
    const html = renderBriefHTML(target, engagement, advisor);

    // 5. Email Yves
    const sendResult = await sendBriefToYves({
      recipientEmail: email,
      recipientName: target.name || email,
      html,
      rdvDateTime,
    });

    // 6. Audit Firestore (HTML inclus pour sync local sur Desktop Yves)
    await saveBriefAudit(projectId, fsToken, {
      email,
      targetName: target.name || "",
      targetOrg: target.organization || "",
      collection: targetMatch.collection,
      docId: targetMatch.docId,
      source,
      rdvDateTime: rdvDateTime || "",
      generatedAt: new Date().toISOString(),
      emailSent: sendResult.ok,
      emailError: sendResult.error || "",
      html: html,
      subject: `📋 Brief Émile — ${target.name || email}`,
    });

    return new Response(JSON.stringify({
      ok: true,
      target: {
        name: target.name,
        organization: target.organization,
        collection: targetMatch.collection,
        docId: targetMatch.docId,
      },
      emailSent: sendResult.ok,
      source,
    }), { status: 200, headers: { "Content-Type": "application/json" } });

  } catch (e) {
    console.error("[Émile] error:", e);
    return new Response(JSON.stringify({ ok: false, error: e.message }), {
      status: 500, headers: { "Content-Type": "application/json" },
    });
  }
};

export const config = {
  path: "/api/emile-generate-brief",
};
