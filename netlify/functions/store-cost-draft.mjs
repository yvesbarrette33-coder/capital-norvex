/**
 * POST /.netlify/functions/store-cost-draft
 * Header: x-internal-secret
 * Body: { dossierId, inputs: { valeurMarchande, coutTotalProjet, ... } }
 *
 * Écrit les données extraites de la ventilation de coûts dans Firestore
 * sous dossiers/{dossierId}/costAnalyzer/current (isDraft: true).
 * Le Cost Analyzer les charge automatiquement à l'ouverture du dossier.
 */

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function getFirestoreToken(serviceAccount) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: serviceAccount.client_email,
    sub: serviceAccount.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
    scope: "https://www.googleapis.com/auth/datastore",
  };

  const b64url = (obj) =>
    btoa(JSON.stringify(obj))
      .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

  const signingInput = `${b64url(header)}.${b64url(payload)}`;

  const pemBody = serviceAccount.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\n/g, "");
  const keyData = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));
  const privateKey = await crypto.subtle.importKey(
    "pkcs8", keyData.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false, ["sign"]
  );

  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5", privateKey, new TextEncoder().encode(signingInput)
  );
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

  const jwt = `${signingInput}.${sigB64}`;

  const tokenResp = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: jwt,
    }),
  });
  const tokenData = await tokenResp.json();
  return tokenData.access_token;
}

/** Convertit un objet JS plat en champs Firestore typés */
function toFirestoreFields(obj) {
  const fields = {};
  for (const [k, v] of Object.entries(obj)) {
    if (v === null || v === undefined) continue;
    if (typeof v === "number")       fields[k] = { doubleValue: v };
    else if (typeof v === "boolean") fields[k] = { booleanValue: v };
    else if (typeof v === "string")  fields[k] = { stringValue: v };
  }
  return fields;
}

export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-internal-secret",
      },
    });
  }

  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  // Auth — INTERNAL_SECRET (agent Python uniquement)
  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return json({ error: "Unauthorized" }, 401);
  }

  let body;
  try { body = await req.json(); }
  catch { return json({ error: "Invalid JSON" }, 400); }

  const { dossierId, inputs } = body;
  if (!dossierId || !inputs) return json({ error: "Missing dossierId or inputs" }, 400);

  // Firebase
  const { getServiceAccount } = await import("./_firebase-sa.mjs");

  let serviceAccount;

  try { serviceAccount = await getServiceAccount(); }

  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  let accessToken;
  try { accessToken = await getFirestoreToken(serviceAccount); }
  catch (e) { return json({ error: "Auth failed: " + e.message }, 500); }

  const projectId = serviceAccount.project_id;

  // Construire le document Firestore
  // Path: dossiers/{dossierId}/costAnalyzer/current
  const docUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/dossiers/${dossierId}/costAnalyzer/current`;

  const inputFields = toFirestoreFields(inputs);

  const firestoreDoc = {
    fields: {
      inputs: {
        mapValue: { fields: inputFields }
      },
      isDraft:     { booleanValue: true },
      source:      { stringValue: "agent_extracted" },
      extractedAt: { stringValue: new Date().toISOString() },
    }
  };

  try {
    const resp = await fetch(docUrl, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(firestoreDoc),
    });

    if (!resp.ok) {
      const err = await resp.text();
      return json({ error: "Firestore write failed: " + err }, 500);
    }
  } catch (e) {
    return json({ error: "Firestore error: " + e.message }, 500);
  }

  return json({ ok: true, dossierId, fieldsWritten: Object.keys(inputFields).length });
};
