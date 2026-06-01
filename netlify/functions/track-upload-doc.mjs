/**
 * POST /.netlify/functions/track-upload-doc
 * ?token=TRACK_TOKEN&dossierId=ID&name=filename&type=facture&desc=description
 * Body: raw binary file content
 *
 * Valide le trackClientToken ou trackPartnerToken contre Firestore,
 * stocke le fichier dans Netlify Blobs (cn-track-uploads),
 * retourne { ok: true, blobKey }.
 * Le frontend log ensuite dans Firestore trackUploads sous-collection.
 */
import { getStore } from "@netlify/blobs";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
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
  const td = await tokenResp.json();
  return td.access_token;
}

export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  }
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  const url      = new URL(req.url);
  const token    = url.searchParams.get("token");
  const dossierId = url.searchParams.get("dossierId");
  const name     = url.searchParams.get("name") || "document";
  const docType  = url.searchParams.get("type") || "autre";

  if (!token || !dossierId) return json({ error: "Missing token or dossierId" }, 400);

  // ── Valider le token contre Firestore ─────────────────────────────────────
  const { getServiceAccount } = await import("./_firebase-sa.mjs");

  let serviceAccount;

  try { serviceAccount = await getServiceAccount(); }

  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  let accessToken;
  try { accessToken = await getFirestoreToken(serviceAccount); }
  catch (e) { return json({ error: "Auth failed: " + e.message }, 500); }

  const projectId = serviceAccount.project_id;
  const docUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/dossiers/${dossierId}`;

  let dossierData;
  try {
    const resp = await fetch(docUrl, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!resp.ok) return json({ error: "Dossier not found" }, 404);
    dossierData = await resp.json();
  } catch (e) {
    return json({ error: "Firestore read failed: " + e.message }, 500);
  }

  // Vérifier que le token correspond au trackClientToken ou trackPartnerToken
  const fields = dossierData.fields || {};
  const clientToken  = fields.trackClientToken?.stringValue  || "";
  const partnerToken = fields.trackPartnerToken?.stringValue || "";

  if (token !== clientToken && token !== partnerToken) {
    return json({ error: "Invalid or expired token" }, 403);
  }

  // ── Lire le fichier ───────────────────────────────────────────────────────
  let fileBuffer;
  try { fileBuffer = await req.arrayBuffer(); }
  catch (e) { return json({ error: "Failed to read file: " + e.message }, 400); }

  if (!fileBuffer || fileBuffer.byteLength === 0) return json({ error: "Empty file" }, 400);
  if (fileBuffer.byteLength > 20 * 1024 * 1024) return json({ error: "File too large (max 20 MB)" }, 413);

  // ── Stocker dans Netlify Blobs ────────────────────────────────────────────
  const ts = Date.now();
  const safeName = name.replace(/[^a-zA-Z0-9._\-]/g, "_");
  const blobKey  = `${dossierId}/${ts}_${safeName}`;
  const store = getStore({ name: "cn-track-uploads", consistency: "strong" });

  try {
    await store.set(blobKey, fileBuffer, {
      metadata: { filename: name, dossierId, docType },
    });
  } catch (e) {
    return json({ error: "Storage failed: " + e.message }, 500);
  }

  return json({ ok: true, blobKey, dossierId, docType });
};
