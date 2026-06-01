/**
 * POST /.netlify/functions/mark-track-alert
 * Header: x-internal-secret
 * Body: { alertId: "...", status: "processed" }
 *
 * Marque un trackAlert comme traité dans Firestore.
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
    iss: serviceAccount.client_email, sub: serviceAccount.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now, exp: now + 3600,
    scope: "https://www.googleapis.com/auth/datastore",
  };
  const b64url = (obj) => btoa(JSON.stringify(obj)).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,"");
  const signingInput = `${b64url(header)}.${b64url(payload)}`;
  const pemBody = serviceAccount.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/,"").replace(/-----END PRIVATE KEY-----/,"").replace(/\n/g,"");
  const keyData = Uint8Array.from(atob(pemBody), c => c.charCodeAt(0));
  const privateKey = await crypto.subtle.importKey(
    "pkcs8", keyData.buffer, { name:"RSASSA-PKCS1-v1_5", hash:"SHA-256" }, false, ["sign"]
  );
  const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", privateKey, new TextEncoder().encode(signingInput));
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig))).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,"");
  const jwt = `${signingInput}.${sigB64}`;
  const tr = await fetch("https://oauth2.googleapis.com/token", {
    method:"POST",
    headers:{"Content-Type":"application/x-www-form-urlencoded"},
    body: new URLSearchParams({ grant_type:"urn:ietf:params:oauth:grant-type:jwt-bearer", assertion:jwt }),
  });
  return (await tr.json()).access_token;
}

export default async (req) => {
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return json({ error: "Unauthorized" }, 401);
  }

  let body;
  try { body = await req.json(); }
  catch { return json({ error: "Invalid JSON" }, 400); }

  const { alertId, status = "processed" } = body;
  if (!alertId) return json({ error: "Missing alertId" }, 400);

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let serviceAccount;


  try { serviceAccount = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  let accessToken;
  try { accessToken = await getFirestoreToken(serviceAccount); }
  catch (e) { return json({ error: "Auth failed: " + e.message }, 500); }

  const projectId = serviceAccount.project_id;
  const docUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/trackAlerts/${alertId}?updateMask.fieldPaths=status&updateMask.fieldPaths=processedAt`;

  try {
    await fetch(docUrl, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        fields: {
          status: { stringValue: status },
          processedAt: { stringValue: new Date().toISOString() },
        },
      }),
    });
  } catch (e) {
    return json({ error: "Firestore update failed: " + e.message }, 500);
  }

  return json({ ok: true, alertId, status });
};
