/**
 * POST /api/rdv-public-request
 *
 * Endpoint public — pas d'auth (formulaire ouvert au monde).
 * Anti-spam basique : taille/format des champs.
 *
 * Body : { name, email, phone?, company?, subject, availability, message?, language }
 *
 * 1. Stocke la demande dans Firestore `rdvPublicRequests`.
 * 2. Génère 2 tokens HMAC (approve, reject).
 * 3. Envoie un email à yves@capitalnorvex.com avec 2 boutons.
 * 4. Yves clique → endpoint approve/reject prend le relais.
 *
 * SLA : Yves a configuré responseSlaHours via /api/rdv-public-config (défaut 24h).
 */

const ENC = new TextEncoder();
const ORGANIZER_EMAIL = process.env.MAIL_FROM || "info@capitalnorvex.com";
const ORGANIZER_NAME = "Capital Norvex Inc.";
const YVES_EMAIL = process.env.YVES_EMAIL || "yves@capitalnorvex.com";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

function isValidEmail(s) {
  return typeof s === "string" && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s);
}

function escapeHtml(s) {
  if (!s) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// ── HMAC helpers ──────────────────────────────────────────────────────────
function b64urlEncode(bytes) {
  let s = "";
  if (typeof bytes === "string") {
    s = btoa(unescape(encodeURIComponent(bytes)));
  } else {
    s = btoa(String.fromCharCode(...new Uint8Array(bytes)));
  }
  return s.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function hmacSign(secret, message) {
  const key = await crypto.subtle.importKey(
    "raw",
    ENC.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, ENC.encode(message));
  return b64urlEncode(sig);
}

async function buildToken(secret, payload) {
  const payloadB64 = b64urlEncode(JSON.stringify(payload));
  const sig = await hmacSign(secret, payloadB64);
  return `${payloadB64}.${sig}`;
}

// ── Firestore ─────────────────────────────────────────────────────────────
async function getFirestoreToken(sa) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: sa.client_email,
    sub: sa.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
    scope: "https://www.googleapis.com/auth/datastore",
  };
  const b64 = (obj) =>
    btoa(JSON.stringify(obj))
      .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const signingInput = `${b64(header)}.${b64(payload)}`;
  const pemBody = sa.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\n/g, "");
  const keyData = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));
  const privateKey = await crypto.subtle.importKey(
    "pkcs8", keyData.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5", privateKey, ENC.encode(signingInput)
  );
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

function fromFsValue(v) {
  if (!v) return null;
  if (v.nullValue !== undefined) return null;
  if (v.booleanValue !== undefined) return v.booleanValue;
  if (v.integerValue !== undefined) return Number(v.integerValue);
  if (v.doubleValue !== undefined) return v.doubleValue;
  if (v.stringValue !== undefined) return v.stringValue;
  if (v.timestampValue !== undefined) return v.timestampValue;
  return null;
}

function toFsValue(v) {
  if (v === null || v === undefined) return { nullValue: null };
  if (typeof v === "boolean") return { booleanValue: v };
  if (typeof v === "number") {
    return Number.isInteger(v) ? { integerValue: String(v) } : { doubleValue: v };
  }
  if (typeof v === "string") return { stringValue: v };
  if (v instanceof Date) return { timestampValue: v.toISOString() };
  return { stringValue: String(v) };
}

async function getSlaHours(projectId, token) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/settings/rdvPublic`;
  try {
    const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    if (r.status === 404) return 24;
    if (!r.ok) return 24;
    const data = await r.json();
    const sla = fromFsValue(data.fields?.responseSlaHours);
    return Number(sla) > 0 ? Number(sla) : 24;
  } catch {
    return 24;
  }
}

async function createDoc(projectId, token, collectionId, fields) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collectionId}`;
  const fsFields = {};
  for (const [k, v] of Object.entries(fields)) fsFields[k] = toFsValue(v);
  const r = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ fields: fsFields }),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`Firestore createDoc ${r.status}: ${t.slice(0, 200)}`);
  }
  const data = await r.json();
  const id = data.name.split("/").pop();
  return id;
}

// ── SendGrid ──────────────────────────────────────────────────────────────
async function sendGridEmail({ to, subject, html, replyTo }) {
  const sgKey = process.env.SENDGRID_API_KEY;
  if (!sgKey) return { ok: false, error: "SENDGRID_API_KEY not set" };
  const r = await fetch("https://api.sendgrid.com/v3/mail/send", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${sgKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      personalizations: [{ to: [{ email: to }] }],
      from: { email: ORGANIZER_EMAIL, name: ORGANIZER_NAME },
      reply_to: { email: replyTo || ORGANIZER_EMAIL, name: ORGANIZER_NAME },
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

// ── Handler ──────────────────────────────────────────────────────────────
export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  }
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  let body;
  try { body = await req.json(); }
  catch { return json({ error: "Invalid JSON" }, 400); }

  const name = (body.name || "").toString().trim().slice(0, 200);
  const email = (body.email || "").toString().trim().slice(0, 200).toLowerCase();
  const phone = (body.phone || "").toString().trim().slice(0, 60);
  const company = (body.company || "").toString().trim().slice(0, 200);
  const subject = (body.subject || "").toString().trim().slice(0, 300);
  const availability = (body.availability || "").toString().trim().slice(0, 1000);
  const message = (body.message || "").toString().trim().slice(0, 2000);
  const language = body.language === "en" ? "en" : "fr";

  if (!name || !isValidEmail(email) || !subject || !availability) {
    return json({ error: "Champs obligatoires manquants" }, 400);
  }

  const hmacSecret = process.env.CAMILLE_HMAC_SECRET || process.env.INTERNAL_SECRET;
  if (!hmacSecret) return json({ error: "HMAC secret not configured" }, 500);

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let sa;


  try { sa = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  try {
    const { token, projectId } = await getFirestoreToken(sa);
    const slaHours = await getSlaHours(projectId, token);
    const slaMs = slaHours * 3600 * 1000;
    const expMs = Date.now() + slaMs + 7 * 24 * 3600 * 1000; // tokens valides SLA + 7j

    const requestId = await createDoc(projectId, token, "rdvPublicRequests", {
      name, email, phone, company, subject, availability, message,
      language, status: "pending", createdAt: new Date(),
      slaHours, slaDeadline: new Date(Date.now() + slaMs),
    });

    const approveToken = await buildToken(hmacSecret, {
      requestId, action: "approve", exp: expMs,
    });
    const rejectToken = await buildToken(hmacSecret, {
      requestId, action: "reject", exp: expMs,
    });
    const approveUrl = `https://capitalnorvex.com/api/rdv-public-approve?token=${encodeURIComponent(approveToken)}`;
    const rejectUrl = `https://capitalnorvex.com/api/rdv-public-reject?token=${encodeURIComponent(rejectToken)}`;

    // Email à Yves
    const yvesHtml = `
<div style="font-family:Georgia,serif;color:#222;max-width:640px;margin:0 auto;padding:24px;background:#fbf9f2;">
  <div style="background:#0A0A0A;color:#C9A227;padding:20px 24px;text-align:center;">
    <div style="font-family:'Playfair Display',Georgia,serif;font-size:22px;letter-spacing:0.18em;">CAPITAL NORVEX</div>
    <div style="font-style:italic;font-size:12.5px;color:#d6cca0;margin-top:6px;">Demande de RDV à valider</div>
  </div>
  <div style="background:#fff;padding:28px 24px;border:1px solid #e8e2cc;border-top:none;">
    <h2 style="margin:0 0 14px 0;font-family:'Playfair Display',Georgia,serif;font-weight:400;color:#0A0A0A;">Nouvelle demande de rendez-vous</h2>
    <p style="font-size:13px;color:#666;margin:0 0 18px 0;">Reçue le ${new Date().toLocaleString("fr-CA")} · SLA de réponse : <strong>${slaHours}h</strong></p>

    <table style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:20px;">
      <tr><td style="padding:8px 0;color:#6b6354;width:140px;font-size:12px;letter-spacing:0.1em;text-transform:uppercase;">Nom</td><td style="padding:8px 0;"><strong>${escapeHtml(name)}</strong></td></tr>
      <tr><td style="padding:8px 0;color:#6b6354;font-size:12px;letter-spacing:0.1em;text-transform:uppercase;">Courriel</td><td style="padding:8px 0;"><a href="mailto:${escapeHtml(email)}" style="color:#0A0A0A;">${escapeHtml(email)}</a></td></tr>
      ${phone ? `<tr><td style="padding:8px 0;color:#6b6354;font-size:12px;letter-spacing:0.1em;text-transform:uppercase;">Téléphone</td><td style="padding:8px 0;">${escapeHtml(phone)}</td></tr>` : ""}
      ${company ? `<tr><td style="padding:8px 0;color:#6b6354;font-size:12px;letter-spacing:0.1em;text-transform:uppercase;">Entreprise</td><td style="padding:8px 0;">${escapeHtml(company)}</td></tr>` : ""}
      <tr><td style="padding:8px 0;color:#6b6354;font-size:12px;letter-spacing:0.1em;text-transform:uppercase;">Langue</td><td style="padding:8px 0;">${language.toUpperCase()}</td></tr>
    </table>

    <div style="background:#fefcf3;border-left:3px solid #C9A227;padding:14px 18px;margin-bottom:14px;">
      <div style="font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:#6b6354;margin-bottom:6px;">Motif</div>
      <div style="font-size:15px;line-height:1.5;">${escapeHtml(subject)}</div>
    </div>

    <div style="background:#fefcf3;border-left:3px solid #C9A227;padding:14px 18px;margin-bottom:14px;">
      <div style="font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:#6b6354;margin-bottom:6px;">Disponibilités demandées</div>
      <div style="font-size:14px;line-height:1.6;white-space:pre-wrap;">${escapeHtml(availability)}</div>
    </div>

    ${message ? `<div style="background:#fefcf3;border-left:3px solid #C9A227;padding:14px 18px;margin-bottom:14px;"><div style="font-size:12px;letter-spacing:0.1em;text-transform:uppercase;color:#6b6354;margin-bottom:6px;">Message</div><div style="font-size:14px;line-height:1.6;white-space:pre-wrap;">${escapeHtml(message)}</div></div>` : ""}

    <div style="margin:32px 0 12px 0;text-align:center;">
      <a href="${approveUrl}" style="display:inline-block;background:#2d8a3e;color:#fff;padding:14px 28px;text-decoration:none;border-radius:4px;font-family:-apple-system,sans-serif;font-size:13px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;margin:0 6px 8px 0;">✓ Approuver &amp; envoyer Teams</a>
      <a href="${rejectUrl}" style="display:inline-block;background:#fff;color:#c0392b;border:1px solid #c0392b;padding:14px 28px;text-decoration:none;border-radius:4px;font-family:-apple-system,sans-serif;font-size:13px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;margin:0 6px 8px 0;">✗ Refuser poliment</a>
    </div>

    <p style="font-size:12px;color:#6b6354;text-align:center;margin:18px 0 0 0;">
      ID demande : ${requestId}<br>
      Liens valides ${slaHours + 168}h. Tu peux aussi répondre à cet email pour discuter avant de décider.
    </p>
  </div>
</div>`;

    await sendGridEmail({
      to: YVES_EMAIL,
      subject: `[RDV] ${name} — ${subject.slice(0, 80)}`,
      html: yvesHtml,
      replyTo: email,
    });

    return json({ ok: true, requestId, slaHours });
  } catch (e) {
    return json({ error: e.message }, 500);
  }
};

export const config = {
  path: "/api/rdv-public-request",
};
