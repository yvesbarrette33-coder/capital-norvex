/**
 * GET /.netlify/functions/diligence-report?dossierId=CNV-2026-XXXX
 * Header: x-internal-secret
 *
 * Retourne le rapport diligence stocké dans Firestore pour un dossier donné.
 */

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status, headers: { "Content-Type": "application/json", "Cache-Control": "private, max-age=10" },
  });
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
  const b64 = (obj) => btoa(JSON.stringify(obj)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const signingInput = `${b64(header)}.${b64(payload)}`;
  const pemBody = sa.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\n/g, "");
  const keyData = Uint8Array.from(atob(pemBody), c => c.charCodeAt(0));
  const privateKey = await crypto.subtle.importKey(
    "pkcs8", keyData.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5", privateKey, new TextEncoder().encode(signingInput)
  );
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: `${signingInput}.${sigB64}`,
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
  if (v.arrayValue !== undefined) return (v.arrayValue.values || []).map(fromFsValue);
  if (v.mapValue !== undefined) {
    const out = {};
    for (const [k, val] of Object.entries(v.mapValue.fields || {})) out[k] = fromFsValue(val);
    return out;
  }
  return null;
}

function docToObj(doc) {
  if (!doc?.fields) return {};
  const out = {};
  for (const [k, v] of Object.entries(doc.fields)) out[k] = fromFsValue(v);
  return out;
}

export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-internal-secret",
      },
    });
  }
  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET)
    return json({ error: "Unauthorized" }, 401);

  const url = new URL(req.url);
  const dossierId = url.searchParams.get("dossierId");
  if (!dossierId) return json({ error: "dossierId requis" }, 400);

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let sa;


  try { sa = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  try {
    const { token, projectId } = await getFirestoreToken(sa);
    const fsUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/diligenceReports/${encodeURIComponent(dossierId)}`;
    const r = await fetch(fsUrl, { headers: { Authorization: `Bearer ${token}` } });
    if (r.status === 404) return json({ ok: false, error: "Aucun rapport pour ce dossier" }, 404);
    if (!r.ok) return json({ error: `Firestore ${r.status}` }, 500);
    const data = await r.json();
    const report = docToObj(data);
    return json({ ok: true, dossierId, report });
  } catch (e) {
    return json({ error: e.message }, 500);
  }
};

export const config = {
  path: "/api/diligence-report",
};
