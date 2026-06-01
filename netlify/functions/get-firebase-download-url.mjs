/**
 * GET /.netlify/functions/get-firebase-download-url?path=STORAGE_PATH
 * Header: X-Internal-Secret
 *
 * Usage interne (agent Python uniquement).
 * Génère un token OAuth2 avec scope storage, retourne l'URL de téléchargement direct.
 * L'agent télécharge ensuite directement depuis Firebase Storage avec ce token.
 */

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function getStorageToken(serviceAccount) {
  const now = Math.floor(Date.now() / 1000);
  const header  = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: serviceAccount.client_email,
    sub: serviceAccount.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
    scope: "https://www.googleapis.com/auth/devstorage.read_only",
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

export default async (req) => {
  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return json({ error: "Unauthorized" }, 401);
  }

  const url          = new URL(req.url);
  const storagePath  = url.searchParams.get("path");
  if (!storagePath) return json({ error: "Missing path" }, 400);

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let serviceAccount;


  try { serviceAccount = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  const bucket = process.env.FIREBASE_STORAGE_BUCKET || `${serviceAccount.project_id}.appspot.com`;

  let accessToken;
  try { accessToken = await getStorageToken(serviceAccount); }
  catch (e) { return json({ error: "Auth failed: " + e.message }, 500); }

  // URL de téléchargement direct GCS
  const encodedPath = encodeURIComponent(storagePath);
  const downloadUrl = `https://storage.googleapis.com/storage/v1/b/${encodeURIComponent(bucket)}/o/${encodedPath}?alt=media`;

  return json({ downloadUrl, bearerToken: accessToken });
};
