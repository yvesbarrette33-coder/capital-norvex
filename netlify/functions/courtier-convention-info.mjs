/**
 * GET /.netlify/functions/courtier-convention-info?token=...
 *
 * Décode + vérifie le token HMAC envoyé dans le courriel d'approbation.
 * Retourne les données du courtier pour pré-remplir la convention.
 *
 * Token = base64url( JSON{ brokerId, exp } ) + "." + base64url( hmacSHA256 )
 *
 * Réponse :
 *   { ok:true, name, agency, brokerNumber, licenseNo, province, alreadySigned:bool }
 *   { ok:false, reason: "invalid"|"expired"|"used"|"not_found" }
 */

const ENC = new TextEncoder();

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

// ── HMAC token helpers ────────────────────────────────────────────────────
function b64urlEncode(bytes) {
  let s = "";
  if (typeof bytes === "string") {
    s = btoa(unescape(encodeURIComponent(bytes)));
  } else {
    s = btoa(String.fromCharCode(...new Uint8Array(bytes)));
  }
  return s.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function b64urlDecode(s) {
  const pad = s.length % 4 === 0 ? "" : "=".repeat(4 - (s.length % 4));
  const base64 = s.replace(/-/g, "+").replace(/_/g, "/") + pad;
  return atob(base64);
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
async function verifyToken(token, secret) {
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
  if (!payload.brokerId || !payload.exp) return { ok: false, reason: "invalid" };
  if (Date.now() > payload.exp) return { ok: false, reason: "expired" };
  return { ok: true, payload };
}

// ── Firestore helpers ─────────────────────────────────────────────────────
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
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");
  const signingInput = `${b64(header)}.${b64(payload)}`;
  const pemBody = sa.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\n/g, "");
  const keyData = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));
  const privateKey = await crypto.subtle.importKey(
    "pkcs8",
    keyData.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    privateKey,
    new TextEncoder().encode(signingInput)
  );
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
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
  return data.access_token;
}

function fromFsValue(v) {
  if (v.nullValue !== undefined) return null;
  if (v.booleanValue !== undefined) return v.booleanValue;
  if (v.integerValue !== undefined) return Number(v.integerValue);
  if (v.stringValue !== undefined) return v.stringValue;
  if (v.timestampValue !== undefined) return v.timestampValue;
  return null;
}
function fsDocToObj(doc) {
  const out = {};
  for (const [k, v] of Object.entries(doc.fields || {})) out[k] = fromFsValue(v);
  return out;
}
let _saCache = null;
async function loadServiceAccount() {
  if (_saCache) return _saCache;
  // 1) Netlify Blobs (norah-config / firebase-sa) — évite limite 4KB AWS Lambda
  try {
    const { getStore } = await import("@netlify/blobs");
    const store = getStore("norah-config");
    const saJson = await store.get("firebase-sa");
    if (saJson) {
      _saCache = JSON.parse(saJson);
      return _saCache;
    }
  } catch (_e) { /* fallback env */ }
  // 2) Fallback: env vars (legacy)
  let saRaw = null;
  if (process.env.FIREBASE_SA_B64) {
    saRaw = atob(process.env.FIREBASE_SA_B64);
  } else if (process.env.FIREBASE_SERVICE_ACCOUNT_KEY) {
    saRaw = process.env.FIREBASE_SERVICE_ACCOUNT_KEY;
  }
  if (!saRaw) throw new Error("Firebase SA not found (no blob, no env var)");
  _saCache = JSON.parse(saRaw);
  return _saCache;
}

// ── Handler ──────────────────────────────────────────────────────────────
export default async function handler(req) {
  if (req.method !== "GET") return json({ ok: false, error: "Method not allowed" }, 405);
  const url = new URL(req.url);
  const token = url.searchParams.get("token") || "";

  const secret = process.env.INTERNAL_SECRET;
  if (!secret) return json({ ok: false, reason: "server_misconfigured" }, 500);

  const verified = await verifyToken(token, secret);
  if (!verified.ok) return json({ ok: false, reason: verified.reason });

  try {
    const sa = await loadServiceAccount();
    const projectId = sa.project_id;
    const fsToken = await getFirestoreToken(sa);

    const brokerId = verified.payload.brokerId;
    const docUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/brokers/${brokerId}`;
    const r = await fetch(docUrl, {
      headers: { Authorization: `Bearer ${fsToken}` },
    });
    if (!r.ok) return json({ ok: false, reason: "not_found" });
    const doc = await r.json();
    const broker = fsDocToObj(doc);

    return json({
      ok: true,
      name: broker.name || broker.fullName || "",
      agency: broker.agency || "",
      brokerNumber: broker.brokerNumber || "",
      licenseNo: broker.licenseNo || "",
      province: broker.province || "",
      alreadySigned: !!broker.contractSignedAt,
    });
  } catch (e) {
    return json({ ok: false, reason: "error", error: e.message }, 500);
  }
}

export const config = {
  path: "/api/courtier-convention-info",
};
