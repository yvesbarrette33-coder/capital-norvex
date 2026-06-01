/**
 * GET /.netlify/functions/admin-broker-applications
 * Header: X-Admin-Password
 * Query: ?status=pending_review|approved|declined  (optionnel)
 *        ?limit=50  (max 200, défaut 100)
 *
 * Retourne la liste des candidatures courtiers triées par submittedAt desc.
 */

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
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

// Décodage Firestore → JS
function fromFsValue(v) {
  if (v.nullValue !== undefined) return null;
  if (v.booleanValue !== undefined) return v.booleanValue;
  if (v.integerValue !== undefined) return Number(v.integerValue);
  if (v.doubleValue !== undefined) return v.doubleValue;
  if (v.stringValue !== undefined) return v.stringValue;
  if (v.timestampValue !== undefined) return v.timestampValue;
  if (v.arrayValue !== undefined) {
    return (v.arrayValue.values || []).map(fromFsValue);
  }
  if (v.mapValue !== undefined) {
    const out = {};
    const fields = v.mapValue.fields || {};
    for (const [k, val] of Object.entries(fields)) out[k] = fromFsValue(val);
    return out;
  }
  return null;
}

function fsDocToObj(doc) {
  const out = { id: doc.name.split("/").pop() };
  const fields = doc.fields || {};
  for (const [k, v] of Object.entries(fields)) out[k] = fromFsValue(v);
  return out;
}

let _saCache = null;
async function loadServiceAccount() {
  if (_saCache) return _saCache;
  try {
    const { getStore } = await import("@netlify/blobs");
    const store = getStore("norah-config");
    const saJson = await store.get("firebase-sa");
    if (saJson) {
      _saCache = JSON.parse(saJson);
      return _saCache;
    }
  } catch (_e) { /* fallback env */ }
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

export default async function handler(req) {
  if (req.method !== "GET") return json({ error: "Method not allowed" }, 405);

  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return json({ error: "Unauthorized" }, 401);
  }

  const url = new URL(req.url);
  const statusFilter = url.searchParams.get("status");
  const limit = Math.min(Number(url.searchParams.get("limit") || 100), 200);

  try {
    const sa = await loadServiceAccount();
    const projectId = sa.project_id;
    const fsToken = await getFirestoreToken(sa);

    // RunQuery pour pouvoir trier
    const queryUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;
    const where = statusFilter
      ? {
          fieldFilter: {
            field: { fieldPath: "status" },
            op: "EQUAL",
            value: { stringValue: statusFilter },
          },
        }
      : null;

    const structuredQuery = {
      from: [{ collectionId: "brokerApplications" }],
      orderBy: [
        {
          field: { fieldPath: "submittedAt" },
          direction: "DESCENDING",
        },
      ],
      limit,
    };
    if (where) structuredQuery.where = where;

    const qResp = await fetch(queryUrl, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${fsToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ structuredQuery }),
    });
    if (!qResp.ok) {
      const txt = await qResp.text();
      return json({ error: "Firestore query failed: " + txt.slice(0, 300) }, 500);
    }
    const rows = await qResp.json();
    const applications = (rows || [])
      .filter((r) => r.document)
      .map((r) => fsDocToObj(r.document));

    // Compteurs par statut (utile pour le dashboard)
    const counts = { pending_review: 0, approved: 0, declined: 0 };
    for (const app of applications) {
      if (counts[app.status] !== undefined) counts[app.status]++;
    }

    return json({
      ok: true,
      count: applications.length,
      counts,
      applications,
    });
  } catch (e) {
    return json({ error: e.message }, 500);
  }
}

export const config = {
  path: "/api/admin-broker-applications",
};
