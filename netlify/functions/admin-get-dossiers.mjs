/**
 * GET /.netlify/functions/admin-get-dossiers
 * Header: X-Admin-Password
 *
 * Retourne tous les dossiers Firestore pour le panneau admin.
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

  const b64 = (obj) =>
    btoa(JSON.stringify(obj))
      .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

  const signingInput = `${b64(header)}.${b64(payload)}`;

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

export default async (req) => {
  // Auth
  const pw = req.headers.get("x-admin-password");
  if (!process.env.ADMIN_PASSWORD || pw !== process.env.ADMIN_PASSWORD) {
    return json({ error: "Unauthorized" }, 401);
  }

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let serviceAccount;


  try { serviceAccount = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  let accessToken;
  try { accessToken = await getFirestoreToken(serviceAccount); }
  catch (e) { return json({ error: "Auth failed: " + e.message }, 500); }

  const projectId = serviceAccount.project_id;
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;

  const query = {
    structuredQuery: {
      from: [{ collectionId: "dossiers" }],
      orderBy: [{ field: { fieldPath: "created_at" }, direction: "DESCENDING" }],
      limit: 200,
    },
  };

  let results;
  try {
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(query),
    });
    results = await resp.json();
  } catch (e) {
    return json({ error: "Firestore query failed: " + e.message }, 500);
  }

  const str = (f) => f?.stringValue || "";
  const dossiers = [];

  for (const result of results) {
    if (!result.document) continue;
    const doc = result.document;
    const fields = doc.fields || {};
    const id = doc.name.split("/").pop();

    dossiers.push({
      id,
      prenom:   str(fields.prenom),
      nom:      str(fields.nom),
      email:    str(fields.email),
      tel:      str(fields.tel),
      type:     str(fields.type),
      montant:  str(fields.montant),
      adresse:  str(fields.adresse),
      stage:    str(fields.stage) || "analyse",
      score:    fields.score?.integerValue || fields.score?.doubleValue || null,
      decision: str(fields.decision),
      lang:     str(fields.lang) || "fr",
      welcomeEmailSent:    fields.welcomeEmailSent?.booleanValue || false,
      documentsGenerated:  fields.documentsGenerated?.booleanValue || false,
      partnerEmail:        str(fields.partnerEmail),
      partnerName:         str(fields.partnerName),
      partnerLang:         str(fields.partnerLang) || "fr",
      partnerSummarySent:  fields.partnerSummarySent?.booleanValue || false,
      createdAt: fields.created_at?.timestampValue || str(fields.created_at) || str(fields.createdAt),
    });
  }

  return json({ dossiers });
};
