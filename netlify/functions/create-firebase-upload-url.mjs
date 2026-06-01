/**
 * POST /.netlify/functions/create-firebase-upload-url
 * Body: { token, filename, contentType }
 *
 * 1. Valide le token client (cn-tokens)
 * 2. Génère une **V4 signed URL PUT** vers `storage.googleapis.com/<bucket>/<path>`
 *    (l'API GCS principale renvoie correctement les CORS headers, contrairement
 *    au resumable upload host qui omet allow-origin sur la réponse PUT — Safari/Chrome bloquent).
 * 3. Retourne aussi un signed GET URL V4 (7 jours, max V4) pour lecture par l'agent.
 *
 * Le client fait un simple PUT (pas resumable, pas de chunks).
 * Limite pratique : 5 GB par PUT.
 */
import { getStore } from "@netlify/blobs";
import crypto from "node:crypto";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

function strictEncode(str) {
  return encodeURIComponent(str).replace(
    /[!'()*]/g,
    (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`
  );
}

function createV4SignedUrl({ method, serviceAccount, bucket, objectPath, expiresSeconds }) {
  const now = new Date();
  const ymd = now.toISOString().slice(0, 10).replace(/-/g, "");
  const hms = now.toISOString().slice(11, 19).replace(/:/g, "");
  const ts = `${ymd}T${hms}Z`;

  const credentialScope = `${ymd}/auto/storage/goog4_request`;
  const credentialValue = `${serviceAccount.client_email}/${credentialScope}`;

  const headersToSign = { host: "storage.googleapis.com" };
  const signedHeaderNames = Object.keys(headersToSign).map((k) => k.toLowerCase()).sort();
  const canonicalHeaders =
    signedHeaderNames.map((h) => `${h}:${headersToSign[h]}`).join("\n") + "\n";
  const signedHeadersStr = signedHeaderNames.join(";");

  const encodedPath = objectPath.split("/").map(strictEncode).join("/");
  const canonicalUri = `/${bucket}/${encodedPath}`;

  const params = {
    "X-Goog-Algorithm": "GOOG4-RSA-SHA256",
    "X-Goog-Credential": credentialValue,
    "X-Goog-Date": ts,
    "X-Goog-Expires": String(expiresSeconds),
    "X-Goog-SignedHeaders": signedHeadersStr,
  };
  const canonicalQueryString = Object.keys(params)
    .sort()
    .map((k) => `${strictEncode(k)}=${strictEncode(params[k])}`)
    .join("&");

  const canonicalRequest = [
    method,
    canonicalUri,
    canonicalQueryString,
    canonicalHeaders,
    signedHeadersStr,
    "UNSIGNED-PAYLOAD",
  ].join("\n");

  const hashCanonical = crypto.createHash("sha256").update(canonicalRequest).digest("hex");
  const stringToSign = [
    "GOOG4-RSA-SHA256",
    ts,
    credentialScope,
    hashCanonical,
  ].join("\n");

  const signer = crypto.createSign("RSA-SHA256");
  signer.update(stringToSign);
  const signature = signer.sign(serviceAccount.private_key, "hex");

  return `https://storage.googleapis.com${canonicalUri}?${canonicalQueryString}&X-Goog-Signature=${signature}`;
}

export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  }
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  let body;
  try { body = await req.json(); }
  catch { return json({ error: "Invalid JSON" }, 400); }

  const { token, filename, contentType } = body;
  if (!token || !filename) return json({ error: "Missing token or filename" }, 400);

  // ── Validate token from Netlify Blobs ──────────────────────────────────────
  const tokenStore = getStore({ name: "cn-tokens", consistency: "strong" });
  let tokenData;
  try { tokenData = await tokenStore.get(token, { type: "json" }); }
  catch (e) { return json({ error: "Token read error: " + e.message }, 500); }

  if (!tokenData || tokenData.active === false) {
    return json({ error: "Invalid or expired token" }, 403);
  }

  const { dossierID = "", clientNom = "", clientEmail = "" } = tokenData;

  // ── Firebase Storage credentials ──────────────────────────────────────────
  const { getServiceAccount } = await import("./_firebase-sa.mjs");

  let serviceAccount;

  try { serviceAccount = await getServiceAccount(); }

  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  const bucket = process.env.FIREBASE_STORAGE_BUCKET || `${serviceAccount.project_id}.appspot.com`;

  const ts = Date.now();
  const safeName = filename.replace(/[^a-zA-Z0-9._\-]/g, "_");
  const storagePath = `uploads/${dossierID}/${ts}_${safeName}`;
  const mimeType = contentType || "application/octet-stream";

  let putUrl, publicUrl;
  try {
    putUrl = createV4SignedUrl({
      method: "PUT",
      serviceAccount,
      bucket,
      objectPath: storagePath,
      expiresSeconds: 900,
    });
    publicUrl = createV4SignedUrl({
      method: "GET",
      serviceAccount,
      bucket,
      objectPath: storagePath,
      expiresSeconds: 7 * 24 * 3600,
    });
  } catch (e) {
    return json({ error: "Sign failed: " + e.message }, 500);
  }

  return json({
    ok: true,
    putUrl,
    publicUrl,
    storagePath,
    bucket,
    dossierID,
    clientNom,
    clientEmail,
    mimeType,
  });
};
