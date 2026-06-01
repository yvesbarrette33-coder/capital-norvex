/**
 * Helpers partagés pour les endpoints "espace-courtier-*".
 *
 * - HMAC tokens (magic links + session tokens)
 * - Firestore (lecture/écriture brokers + dossiers)
 * - SendGrid (envoi du magic link)
 *
 * 2026-05-21 : créé pour la PWA Espace Courtier (Phase 2 courtiers).
 */

import { getServiceAccount } from "./_firebase-sa.mjs";

const ENC = new TextEncoder();

export function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

// ── HMAC token helpers ────────────────────────────────────────────────────
export function b64urlEncode(bytes) {
  let s = "";
  if (typeof bytes === "string") {
    s = btoa(unescape(encodeURIComponent(bytes)));
  } else {
    s = btoa(String.fromCharCode(...new Uint8Array(bytes)));
  }
  return s.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
export function b64urlDecode(s) {
  const pad = s.length % 4 === 0 ? "" : "=".repeat(4 - (s.length % 4));
  const base64 = s.replace(/-/g, "+").replace(/_/g, "/") + pad;
  return atob(base64);
}
export async function hmacSign(secret, message) {
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

export async function makeToken(secret, payloadObj) {
  const payloadB64 = b64urlEncode(JSON.stringify(payloadObj));
  const sig = await hmacSign(secret, payloadB64);
  return payloadB64 + "." + sig;
}

export async function verifyToken(token, secret) {
  if (!token || typeof token !== "string" || !token.includes(".")) {
    return { ok: false, reason: "invalid" };
  }
  const [payloadB64, sigB64] = token.split(".");
  const expected = await hmacSign(secret, payloadB64);
  if (expected !== sigB64) return { ok: false, reason: "invalid" };
  let payload;
  try {
    payload = JSON.parse(b64urlDecode(payloadB64));
  } catch {
    return { ok: false, reason: "invalid" };
  }
  if (!payload.exp || Date.now() > payload.exp) {
    return { ok: false, reason: "expired" };
  }
  return { ok: true, payload };
}

// ── Firestore (Google REST) ───────────────────────────────────────────────
let _fsTokenCache = { token: null, expiresAt: 0 };
async function getFirestoreToken(sa) {
  if (_fsTokenCache.token && Date.now() < _fsTokenCache.expiresAt - 60_000) {
    return _fsTokenCache.token;
  }
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
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");
  const unsigned = b64(header) + "." + b64(payload);

  // Import RSA private key
  const pem = sa.private_key.replace(/-----[^-]+-----/g, "").replace(/\s/g, "");
  const der = Uint8Array.from(atob(pem), (c) => c.charCodeAt(0));
  const key = await crypto.subtle.importKey(
    "pkcs8",
    der.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    key,
    ENC.encode(unsigned)
  );
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  const jwt = unsigned + "." + sigB64;

  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body:
      "grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=" + jwt,
  });
  const data = await res.json();
  if (!data.access_token) throw new Error("FS token failed: " + JSON.stringify(data));
  _fsTokenCache = {
    token: data.access_token,
    expiresAt: Date.now() + data.expires_in * 1000,
  };
  return data.access_token;
}

export function fsValueFromAny(v) {
  if (v === null || v === undefined) return { nullValue: null };
  if (typeof v === "string") return { stringValue: v };
  if (typeof v === "boolean") return { booleanValue: v };
  if (typeof v === "number") {
    return Number.isInteger(v)
      ? { integerValue: String(v) }
      : { doubleValue: v };
  }
  if (Array.isArray(v)) {
    return { arrayValue: { values: v.map(fsValueFromAny) } };
  }
  if (typeof v === "object") {
    const fields = {};
    for (const k of Object.keys(v)) fields[k] = fsValueFromAny(v[k]);
    return { mapValue: { fields } };
  }
  return { stringValue: String(v) };
}

export function fsValueToAny(v) {
  if (!v || typeof v !== "object") return null;
  if ("stringValue" in v) return v.stringValue;
  if ("booleanValue" in v) return v.booleanValue;
  if ("integerValue" in v) return Number(v.integerValue);
  if ("doubleValue" in v) return Number(v.doubleValue);
  if ("nullValue" in v) return null;
  if ("timestampValue" in v) return v.timestampValue;
  if ("arrayValue" in v) {
    return (v.arrayValue.values || []).map(fsValueToAny);
  }
  if ("mapValue" in v) {
    const out = {};
    for (const k of Object.keys(v.mapValue.fields || {})) {
      out[k] = fsValueToAny(v.mapValue.fields[k]);
    }
    return out;
  }
  return null;
}

function fsDocToObject(doc) {
  if (!doc || !doc.fields) return null;
  const out = {};
  for (const k of Object.keys(doc.fields)) out[k] = fsValueToAny(doc.fields[k]);
  // Extract Firestore document ID from name
  if (doc.name) {
    const parts = doc.name.split("/");
    out.id = parts[parts.length - 1];
  }
  return out;
}

// ── Firestore queries pour Espace Courtier ────────────────────────────────
// Note (2026-05-21) : on filtre par email seul puis on valide
// `relationshipStatus === "active_partner"` côté Node, car le workflow
// admin-broker-decision met à jour `relationshipStatus`, pas `status`.
// Permet d'éviter un index composite Firestore.
export async function findBrokerByEmail(email) {
  const sa = await getServiceAccount();
  const token = await getFirestoreToken(sa);
  const projectId = sa.project_id;
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;
  const body = {
    structuredQuery: {
      from: [{ collectionId: "brokers" }],
      where: {
        fieldFilter: {
          field: { fieldPath: "email" },
          op: "EQUAL",
          value: { stringValue: String(email).trim().toLowerCase() },
        },
      },
      limit: 10,
    },
  };
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: "Bearer " + token,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  const arr = await res.json();
  if (!Array.isArray(arr)) return null;
  const docs = arr.filter((r) => r.document).map((r) => fsDocToObject(r.document));
  // Filtre côté Node : accepter status OU relationshipStatus = active_partner
  const accredited = docs.find((b) => {
    const s = (b.status || "").toLowerCase();
    const rs = (b.relationshipStatus || "").toLowerCase();
    return s === "active_partner" || rs === "active_partner" || rs === "active" || rs === "cold";
  });
  return accredited || null;
}

export async function getBrokerById(brokerId) {
  const sa = await getServiceAccount();
  const token = await getFirestoreToken(sa);
  const projectId = sa.project_id;
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/brokers/${encodeURIComponent(brokerId)}`;
  const res = await fetch(url, { headers: { Authorization: "Bearer " + token } });
  if (!res.ok) return null;
  const doc = await res.json();
  return fsDocToObject(doc);
}

export async function findDossiersByBrokerId(brokerId) {
  // Note: orderBy retiré car nécessiterait un index composite Firestore
  // (referrerBrokerId + created_at). Tri fait côté client après fetch.
  const sa = await getServiceAccount();
  const token = await getFirestoreToken(sa);
  const projectId = sa.project_id;
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;
  const body = {
    structuredQuery: {
      from: [{ collectionId: "dossiers" }],
      where: {
        fieldFilter: {
          field: { fieldPath: "referrerBrokerId" },
          op: "EQUAL",
          value: { stringValue: brokerId },
        },
      },
      limit: 100,
    },
  };
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: "Bearer " + token,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  const arr = await res.json();
  if (!Array.isArray(arr)) return [];
  const docs = arr.filter((r) => r.document).map((r) => fsDocToObject(r.document));
  // Tri côté serveur Node (created_at DESC)
  docs.sort((a, b) => {
    const da = a.created_at || a.submittedAt || "";
    const db = b.created_at || b.submittedAt || "";
    if (da > db) return -1;
    if (da < db) return 1;
    return 0;
  });
  return docs;
}

export async function createDossier(dossierData) {
  const sa = await getServiceAccount();
  const token = await getFirestoreToken(sa);
  const projectId = sa.project_id;
  // ID custom : CNV-COURTIER-{timestamp}
  const dossierId = `CNV-COURTIER-${Date.now()}`;
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/dossiers?documentId=${dossierId}`;
  const fields = {};
  for (const k of Object.keys(dossierData)) {
    if (dossierData[k] !== undefined && dossierData[k] !== null) {
      fields[k] = fsValueFromAny(dossierData[k]);
    }
  }
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: "Bearer " + token,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ fields }),
  });
  if (!res.ok) {
    const errTxt = await res.text();
    throw new Error("Firestore createDossier failed: " + errTxt);
  }
  return dossierId;
}

// ── SendGrid (envoi magic link) ───────────────────────────────────────────
export async function sendMagicLinkEmail({ to, name, magicUrl, expiresInMinutes }) {
  const apiKey = process.env.SENDGRID_API_KEY;
  if (!apiKey) throw new Error("SENDGRID_API_KEY not set");
  const firstName = (name || "").trim().split(/\s+/)[0] || "";
  const subject = "🔐 Votre lien de connexion — Espace Courtier Capital Norvex";
  const html = `<!DOCTYPE html><html><body style="margin:0;padding:0;background:#FBF7EB;font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#0A0A0A;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#FBF7EB;padding:24px 12px;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="max-width:620px;width:100%;background:#FFFFFF;border-radius:2px;box-shadow:0 2px 18px rgba(0,0,0,0.05);">
<tr><td style="background:#0A0A0A;padding:32px 24px;text-align:center;">
<div style="color:#C8B070;font-family:'Playfair Display',Georgia,serif;font-size:26px;letter-spacing:4px;font-weight:400;">CAPITAL NORVEX</div>
<div style="color:#C8B070;font-style:italic;font-size:11.5px;letter-spacing:2px;margin-top:10px;opacity:0.78;">Espace Courtier</div>
</td></tr>
<tr><td style="height:3px;background:linear-gradient(90deg,transparent 0%,#C8B070 50%,transparent 100%);"></td></tr>
<tr><td style="padding:36px 40px;">
<div style="font-size:10.5px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">Connexion sécurisée</div>
<h1 style="font-family:'Playfair Display',Georgia,serif;font-size:26px;line-height:1.25;font-weight:400;color:#0A0A0A;margin:0 0 14px;">Bonjour ${firstName},</h1>
<p style="font-family:Georgia,serif;font-size:15px;color:#3a3a3a;line-height:1.7;margin:14px 0;">Voici votre lien de connexion sécurisé à votre <strong>Espace Courtier Capital Norvex</strong>. Cliquez sur le bouton ci-dessous pour ouvrir votre tableau de bord.</p>
<div style="text-align:center;margin:30px 0;">
<a href="${magicUrl}" style="display:inline-block;background:#0A0A0A;color:#C8B070;border:1px solid #C8B070;padding:16px 38px;font-size:13.5px;letter-spacing:1.5px;text-transform:uppercase;text-decoration:none;font-weight:500;">Ouvrir mon espace courtier</a>
</div>
<div style="background:#FCF8EE;border-left:3px solid #C8B070;padding:14px 18px;font-size:12.5px;color:#3a3a3a;line-height:1.6;">
🔒 Ce lien est <strong>personnel et confidentiel</strong>. Il expire dans <strong>${expiresInMinutes} minutes</strong>. Si vous n'avez pas demandé cette connexion, ignorez ce courriel — votre compte reste sécurisé.
</div>
<p style="margin:24px 0 0;font-size:12.5px;color:#888;">Vous pouvez aussi copier-coller ce lien dans votre navigateur :<br>
<a href="${magicUrl}" style="color:#9A8554;word-break:break-all;font-size:11.5px;">${magicUrl}</a></p>
</td></tr>
<tr><td style="background:#0A0A0A;padding:18px;text-align:center;color:#C8B070;font-size:11px;letter-spacing:1.2px;">
<a href="https://capitalnorvex.com" style="color:#C8B070;text-decoration:none;">capitalnorvex.com</a>
</td></tr>
</table>
</td></tr></table>
</body></html>`;
  const res = await fetch("https://api.sendgrid.com/v3/mail/send", {
    method: "POST",
    headers: {
      Authorization: "Bearer " + apiKey,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      personalizations: [{ to: [{ email: to, name: name || to }] }],
      from: { email: "info@capitalnorvex.com", name: "Capital Norvex" },
      reply_to: { email: "info@capitalnorvex.com", name: "Capital Norvex" },
      subject,
      content: [{ type: "text/html", value: html }],
    }),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error("SendGrid failed: " + res.status + " " + txt);
  }
}

// ── Helper auth header ───────────────────────────────────────────────────
export async function requireSession(req, secret) {
  const auth = req.headers.get("authorization") || "";
  if (!auth.startsWith("Bearer ")) return { ok: false, reason: "missing_token" };
  const token = auth.slice(7);
  const result = await verifyToken(token, secret);
  if (!result.ok) return result;
  if (result.payload.type !== "session") return { ok: false, reason: "wrong_type" };
  if (!result.payload.brokerId) return { ok: false, reason: "no_broker" };
  return { ok: true, brokerId: result.payload.brokerId, email: result.payload.email };
}
