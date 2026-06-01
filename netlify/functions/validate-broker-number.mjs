/**
 * GET /.netlify/functions/validate-broker-number?n=CN-2026-001
 *
 * Vérifie qu'un numéro courtier est :
 *   1. Bien formé (CN-YYYY-NNN)
 *   2. Existant dans Firestore brokers/
 *   3. Avec relationshipStatus différent de "applicant" (= approuvé)
 *      et différent de "declined" (= refusé)
 *
 * Retourne :
 *   { ok: true, valid: true, brokerName, agency, status } si OK
 *   { ok: true, valid: false, reason } sinon
 *
 * Endpoint PUBLIC : utilisé par le formulaire de soumission de dossier sur le
 * site capitalnorvex.com pour bloquer les soumissions de courtiers non
 * approuvés (avant qu'ils paient les frais d'analyse Score Norvex).
 *
 * Pas d'auth — mais réponse minimale (nom du courtier + statut), aucune
 * donnée sensible exposée.
 */

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
    },
  });
}

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
  if (v.arrayValue !== undefined)
    return (v.arrayValue.values || []).map(fromFsValue);
  return null;
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

const FORMAT = /^CN-\d{4}-\d{3}$/;

export default async function handler(req) {
  if (req.method !== "GET") return json({ error: "Method not allowed" }, 405);

  const url = new URL(req.url);
  const number = (url.searchParams.get("n") || "").trim().toUpperCase();
  if (!number) {
    return json({ ok: true, valid: false, reason: "missing" });
  }
  if (!FORMAT.test(number)) {
    return json({ ok: true, valid: false, reason: "format" });
  }

  try {
    const sa = await loadServiceAccount();
    const projectId = sa.project_id;
    const fsToken = await getFirestoreToken(sa);

    // Query brokers où brokerNumber == number
    const queryUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;
    const structuredQuery = {
      from: [{ collectionId: "brokers" }],
      where: {
        fieldFilter: {
          field: { fieldPath: "brokerNumber" },
          op: "EQUAL",
          value: { stringValue: number },
        },
      },
      limit: 1,
    };
    const r = await fetch(queryUrl, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${fsToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ structuredQuery }),
    });
    if (!r.ok) {
      return json({ ok: false, error: "lookup failed" }, 500);
    }
    const rows = await r.json();
    const docs = (rows || []).filter((row) => row.document);
    if (docs.length === 0) {
      return json({ ok: true, valid: false, reason: "not_found" });
    }
    const fields = docs[0].document.fields || {};
    const status = fromFsValue(fields.relationshipStatus || {}) || "";
    const name = fromFsValue(fields.name || {}) || "";
    const agency = fromFsValue(fields.agency || {}) || "";

    // Statuts acceptés : tout SAUF applicant et declined
    if (status === "applicant") {
      return json({ ok: true, valid: false, reason: "pending_review" });
    }
    if (status === "declined") {
      return json({ ok: true, valid: false, reason: "declined" });
    }

    return json({
      ok: true,
      valid: true,
      brokerName: name,
      agency,
      status,
    });
  } catch (e) {
    return json({ ok: false, error: e.message }, 500);
  }
}

export const config = {
  path: "/api/validate-broker-number",
};
