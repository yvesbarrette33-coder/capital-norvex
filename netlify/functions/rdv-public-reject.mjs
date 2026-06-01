/**
 * GET /api/rdv-public-reject?token=...
 *
 * Yves clique le bouton REFUSER dans son email.
 * - Vérifie le token HMAC
 * - Marque la demande comme "rejected"
 * - Envoie email poli au visiteur (téléphone direct + invitation à reformuler)
 */

const ENC = new TextEncoder();
const ORGANIZER_EMAIL = process.env.MAIL_FROM || "info@capitalnorvex.com";
const ORGANIZER_NAME = "Capital Norvex Inc.";
const YVES_EMAIL = process.env.YVES_EMAIL || "yves@capitalnorvex.com";

function escapeHtml(s) {
  if (!s) return "";
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function htmlPage(title, body) {
  return new Response(`<!doctype html><html><head><meta charset="utf-8"><title>${title}</title>
<style>body{font-family:Georgia,serif;max-width:560px;margin:80px auto;padding:24px;background:#fbf9f2;color:#222;text-align:center}
h1{font-family:'Playfair Display',Georgia,serif;font-weight:400;color:#0A0A0A}
.box{background:#fff;border:1px solid #e8e2cc;padding:32px 24px;border-radius:6px}
.ok{color:#1a5d28} .err{color:#8c1f1f}</style></head>
<body><div class="box">${body}</div></body></html>`,
    { status: 200, headers: { "Content-Type": "text/html; charset=utf-8" } });
}

function b64urlDecode(s) {
  const pad = s.length % 4 === 0 ? "" : "=".repeat(4 - (s.length % 4));
  const base64 = s.replace(/-/g, "+").replace(/_/g, "/") + pad;
  return atob(base64);
}
async function hmacSign(secret, message) {
  const key = await crypto.subtle.importKey("raw", ENC.encode(secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, ENC.encode(message));
  return btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
async function verifyToken(token, secret) {
  if (!token || !token.includes(".")) return { ok: false };
  const [payloadB64, sigB64] = token.split(".");
  const expected = await hmacSign(secret, payloadB64);
  if (expected !== sigB64) return { ok: false };
  let payload;
  try { payload = JSON.parse(b64urlDecode(payloadB64)); } catch { return { ok: false }; }
  if (Date.now() > payload.exp) return { ok: false, reason: "expired" };
  return { ok: true, payload };
}

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

function fromFsValue(v) {
  if (!v) return null;
  if (v.nullValue !== undefined) return null;
  if (v.booleanValue !== undefined) return v.booleanValue;
  if (v.stringValue !== undefined) return v.stringValue;
  if (v.timestampValue !== undefined) return v.timestampValue;
  if (v.integerValue !== undefined) return Number(v.integerValue);
  return null;
}
function toFsValue(v) {
  if (v === null || v === undefined) return { nullValue: null };
  if (typeof v === "boolean") return { booleanValue: v };
  if (typeof v === "string") return { stringValue: v };
  if (v instanceof Date) return { timestampValue: v.toISOString() };
  return { stringValue: String(v) };
}
async function getDoc(projectId, token, path) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${path}`;
  const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (r.status === 404 || !r.ok) return null;
  const data = await r.json();
  if (!data.fields) return null;
  const out = {};
  for (const [k, v] of Object.entries(data.fields)) out[k] = fromFsValue(v);
  return out;
}
async function patchDoc(projectId, token, path, updates) {
  const fieldNames = Object.keys(updates);
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${path}?` +
    fieldNames.map(f => `updateMask.fieldPaths=${encodeURIComponent(f)}`).join("&");
  const fields = {};
  for (const [k, v] of Object.entries(updates)) fields[k] = toFsValue(v);
  const r = await fetch(url, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });
  if (!r.ok) throw new Error(`Firestore patch ${r.status}`);
}

async function sendGridEmail({ to, subject, html, replyTo }) {
  const sgKey = process.env.SENDGRID_API_KEY;
  if (!sgKey) return { ok: false, error: "SENDGRID_API_KEY not set" };
  const r = await fetch("https://api.sendgrid.com/v3/mail/send", {
    method: "POST",
    headers: { Authorization: `Bearer ${sgKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      personalizations: [{ to: [{ email: to }] }],
      from: { email: ORGANIZER_EMAIL, name: ORGANIZER_NAME },
      reply_to: { email: replyTo || YVES_EMAIL, name: ORGANIZER_NAME },
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

export default async (req) => {
  const url = new URL(req.url);
  const token = url.searchParams.get("token");
  if (!token) return htmlPage("Lien invalide", `<h1 class="err">✗ Lien invalide</h1>`);

  const hmacSecret = process.env.CAMILLE_HMAC_SECRET || process.env.INTERNAL_SECRET;
  if (!hmacSecret) return htmlPage("Erreur", `<h1 class="err">Erreur configuration</h1>`);

  const v = await verifyToken(token, hmacSecret);
  if (!v.ok) return htmlPage("Lien invalide", `<h1 class="err">✗ Lien invalide ou expiré</h1>`);
  if (v.payload.action !== "reject") return htmlPage("Action incorrecte", `<h1 class="err">Action incorrecte</h1>`);

  const { getServiceAccount } = await import("./_firebase-sa.mjs");
  let sa;
  try { sa = await getServiceAccount(); }
  catch { return htmlPage("Erreur", `<h1 class="err">Erreur Firebase</h1>`); }

  try {
    const { token: fsToken, projectId } = await getFirestoreToken(sa);
    const reqDoc = await getDoc(projectId, fsToken, `rdvPublicRequests/${v.payload.requestId}`);
    if (!reqDoc) return htmlPage("Introuvable", `<h1 class="err">Demande introuvable</h1>`);
    if (reqDoc.status === "approved" || reqDoc.status === "rejected") {
      return htmlPage("Déjà traité", `<h1>Demande déjà traitée</h1><p>Statut actuel : <strong>${reqDoc.status}</strong>.</p>`);
    }

    const isEn = reqDoc.language === "en";

    const visitorHtml = `
<div style="font-family:Georgia,serif;color:#222;max-width:640px;margin:0 auto;padding:24px;background:#fbf9f2;">
  <div style="background:#0A0A0A;color:#C9A227;padding:20px 24px;text-align:center;">
    <div style="font-family:'Playfair Display',Georgia,serif;font-size:22px;letter-spacing:0.18em;">CAPITAL NORVEX</div>
  </div>
  <div style="background:#fff;padding:28px 24px;border:1px solid #e8e2cc;border-top:none;">
    <p style="font-size:15px;line-height:1.7;">${isEn ? `Hello ${escapeHtml(reqDoc.name)},` : `Bonjour ${escapeHtml(reqDoc.name)},`}</p>

    <p style="font-size:15px;line-height:1.7;">${isEn
      ? "Thank you for your meeting request. Unfortunately, the time slots you indicated do not work on my end this week."
      : "Je vous remercie pour votre demande de rendez-vous. Malheureusement, les créneaux que vous avez indiqués ne sont pas disponibles de mon côté cette semaine."}</p>

    <p style="font-size:15px;line-height:1.7;">${isEn
      ? "The fastest way to connect remains by phone — feel free to call me directly at <strong>+1 (438) 533-PRÊT (7738)</strong> during business hours, and we'll find a time that works for both of us."
      : "Le moyen le plus rapide de se joindre demeure le téléphone — n'hésitez pas à m'appeler directement au <strong>438-533-PRÊT (7738)</strong> aux heures ouvrables et nous conviendrons ensemble d'un créneau qui fonctionne pour nous deux."}</p>

    <p style="font-size:15px;line-height:1.7;">${isEn
      ? "Alternatively, you may resubmit the form with different time options at <a href=\"https://capitalnorvex.com/rdv-public.html\">capitalnorvex.com/rdv-public.html</a>."
      : "Vous pouvez aussi soumettre à nouveau le formulaire avec d'autres options à l'adresse <a href=\"https://capitalnorvex.com/rdv-public.html\">capitalnorvex.com/rdv-public.html</a>."}</p>

    <p style="font-size:15px;line-height:1.7;">${isEn ? "Looking forward to connecting." : "Au plaisir d'échanger avec vous."}</p>

    <p style="font-size:15px;margin-top:28px;">${isEn ? "Best regards," : "Cordialement,"}<br>
    <strong>Yves Barrette</strong><br>
    <span style="font-style:italic;font-size:13px;color:#6b6354;">${isEn ? "Founder &amp; Director" : "Directeur-Fondateur"} · Capital Norvex Inc.</span></p>
  </div>
</div>`;

    const sendResult = await sendGridEmail({
      to: reqDoc.email,
      subject: isEn
        ? `Re: ${reqDoc.subject.slice(0, 80)}`
        : `Re : ${reqDoc.subject.slice(0, 80)}`,
      html: visitorHtml,
      replyTo: YVES_EMAIL,
    });

    await patchDoc(projectId, fsToken, `rdvPublicRequests/${v.payload.requestId}`, {
      status: "rejected",
      decidedAt: new Date(),
      emailSent: !!sendResult.ok,
      emailError: sendResult.ok ? "" : (sendResult.error || "unknown"),
    });

    return htmlPage("Refusé", `
      <h1>✗ Demande refusée poliment</h1>
      <p>Un courriel poli a été envoyé à <strong>${escapeHtml(reqDoc.email)}</strong> avec ton numéro de téléphone direct comme alternative.</p>
      <p style="color:#666;font-size:13px;margin-top:24px;">${sendResult.ok ? "Email envoyé avec succès." : "⚠️ " + (sendResult.error || "Erreur d'envoi")}</p>`);
  } catch (e) {
    return htmlPage("Erreur", `<h1 class="err">Erreur : ${escapeHtml(e.message)}</h1>`);
  }
};

export const config = {
  path: "/api/rdv-public-reject",
};
