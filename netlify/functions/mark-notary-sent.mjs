/**
 * POST /.netlify/functions/mark-notary-sent
 * Header: X-Internal-Secret
 * Body: { dossierId }
 *
 * Met a jour le dossier Firestore:
 *   - notaryPackageSent = true
 *   - notarySentAt      = ISO now
 *   - stage             = "notaire" (si pas deja en stage superieur)
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
  return (await tokenResp.json()).access_token;
}

// Stages ou on NE change PAS le stage (deja plus avance)
const STAGES_AVANCES = new Set(["pret_a_clore", "signe", "complete", "ferme", "annule"]);

export default async (req) => {
  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return json({ error: "Unauthorized" }, 401);
  }

  let body;
  try { body = await req.json(); }
  catch { return json({ error: "Invalid JSON" }, 400); }

  const { dossierId } = body;
  if (!dossierId) return json({ error: "Missing dossierId" }, 400);

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let serviceAccount;


  try { serviceAccount = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  let accessToken;
  try { accessToken = await getFirestoreToken(serviceAccount); }
  catch (e) { return json({ error: "Auth failed: " + e.message }, 500); }

  const projectId = serviceAccount.project_id;

  // Lire le stage actuel avant de modifier
  const getUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/dossiers/${dossierId}`;
  let currentStage = "";
  try {
    const getResp = await fetch(getUrl, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (getResp.ok) {
      const doc = await getResp.json();
      currentStage = doc.fields?.stage?.stringValue || "";
    }
  } catch (_) {}

  const fieldPaths = ["notaryPackageSent", "notarySentAt"];
  const fields = {
    notaryPackageSent: { booleanValue: true },
    notarySentAt:      { timestampValue: new Date().toISOString() },
  };

  // Avancer le stage a "notaire" seulement si pas deja plus avance
  if (!STAGES_AVANCES.has(currentStage) && currentStage !== "notaire") {
    fieldPaths.push("stage");
    fields.stage = { stringValue: "notaire" };
  }

  const mask = fieldPaths.map(f => `updateMask.fieldPaths=${f}`).join("&");
  const docUrl = `${getUrl}?${mask}&currentDocument.exists=true`;

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

  return json({ ok: true, dossierId });
};
