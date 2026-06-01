/**
 * POST /.netlify/functions/admin-update-stage
 * Header: X-Admin-Password
 * Body: { dossierId, stage }
 *
 * Met à jour le stage d'un dossier Firestore depuis le panneau admin.
 * Stages valides: analyse, nouvelle, docs, approuve, engagement
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

const VALID_STAGES = ["analyse", "nouvelle", "docs", "approuve", "engagement"];

export default async (req) => {
  // Auth
  const pw = req.headers.get("x-admin-password");
  if (!process.env.ADMIN_PASSWORD || pw !== process.env.ADMIN_PASSWORD) {
    return json({ error: "Unauthorized" }, 401);
  }

  let body;
  try { body = await req.json(); }
  catch { return json({ error: "Invalid JSON" }, 400); }

  const { dossierId, stage, partnerEmail, partnerName, partnerLang, partnerSummarySent } = body;
  if (!dossierId) return json({ error: "Missing dossierId" }, 400);
  if (!stage || !VALID_STAGES.includes(stage)) {
    return json({ error: "Invalid stage" }, 400);
  }

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let serviceAccount;


  try { serviceAccount = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  let accessToken;
  try { accessToken = await getFirestoreToken(serviceAccount); }
  catch (e) { return json({ error: "Auth failed: " + e.message }, 500); }

  const projectId = serviceAccount.project_id;

  // Build fields to update
  const fields = { stage: { stringValue: stage } };
  const maskPaths = ["stage"];

  if (partnerEmail) {
    fields.partnerEmail = { stringValue: partnerEmail };
    maskPaths.push("partnerEmail");
  }
  if (partnerName) {
    fields.partnerName = { stringValue: partnerName };
    maskPaths.push("partnerName");
  }
  if (partnerLang) {
    fields.partnerLang = { stringValue: partnerLang };
    maskPaths.push("partnerLang");
  }
  if (typeof partnerSummarySent === "boolean") {
    fields.partnerSummarySent = { booleanValue: partnerSummarySent };
    maskPaths.push("partnerSummarySent");
  }

  const maskQuery = maskPaths.map(p => `updateMask.fieldPaths=${p}`).join("&");
  const docUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/dossiers/${dossierId}?${maskQuery}&currentDocument.exists=true`;

  try {
    const resp = await fetch(docUrl, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ fields }),
    });
    if (!resp.ok) {
      const err = await resp.text();
      return json({ error: "Firestore update failed: " + err }, 500);
    }
  } catch (e) {
    return json({ error: "Firestore update error: " + e.message }, 500);
  }

  return json({ ok: true });
};
