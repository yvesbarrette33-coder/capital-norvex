/**
 * POST /.netlify/functions/create-score-upload-url
 * Body: { sessionId, filename, contentType }
 *
 * Variante PUBLIQUE (pas de token requis), réservée à la page Score Norvex
 * pour permettre l'upload de gros PDFs (>4.5MB) directement à Firebase Storage.
 *
 * Génère une **V4 signed URL PUT** vers `storage.googleapis.com/<bucket>/<path>`.
 * Le client fait un simple PUT (pas resumable) — l'API GCS principale renvoie
 * correctement les headers CORS (allow-origin), contrairement au upload host
 * resumable qui omet allow-origin sur la réponse PUT terminale (Safari bloque).
 *
 * Le fichier est stocké à : score-uploads/<sessionId>/<timestamp>_<safeName>
 * Limite pratique : 5 GB par PUT (largement au-dessus des 32 MB Anthropic).
 *
 * Pour rendre l'objet lisible publiquement par Claude (source: url) :
 *  - On ajoute un downloadToken via x-goog-meta-firebaseStorageDownloadTokens
 *    (signé dans le PUT) pour générer un publicUrl Firebase format standard.
 */

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

// Encodage stricte pour V4 (encodeURIComponent + caractères supplémentaires)
function strictEncode(str) {
  return encodeURIComponent(str).replace(
    /[!'()*]/g,
    (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`
  );
}

function uuidv4() {
  return crypto.randomUUID
    ? crypto.randomUUID()
    : Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function createV4SignedUrl({ method, serviceAccount, bucket, objectPath, expiresSeconds, signedMetaHeaders }) {
  const now = new Date();
  const ymd = now.toISOString().slice(0, 10).replace(/-/g, "");
  const hms = now.toISOString().slice(11, 19).replace(/:/g, "");
  const ts = `${ymd}T${hms}Z`;

  const credentialScope = `${ymd}/auto/storage/goog4_request`;
  const credentialValue = `${serviceAccount.client_email}/${credentialScope}`;

  const headersToSign = { host: "storage.googleapis.com", ...(signedMetaHeaders || {}) };
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
    method === "PUT" ? "UNSIGNED-PAYLOAD" : "UNSIGNED-PAYLOAD",
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
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  }
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  let body;
  try { body = await req.json(); }
  catch { return json({ error: "Invalid JSON" }, 400); }

  const { sessionId, filename, contentType } = body;
  if (!sessionId || !filename) return json({ error: "Missing sessionId or filename" }, 400);
  if (!/^[a-zA-Z0-9_\-]{4,64}$/.test(sessionId)) return json({ error: "Invalid sessionId format" }, 400);
  const mimeType = contentType || "application/pdf";
  if (!mimeType.startsWith("application/pdf")) return json({ error: "Only PDF allowed" }, 400);

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let serviceAccount;


  try { serviceAccount = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  const bucket = process.env.FIREBASE_STORAGE_BUCKET || `${serviceAccount.project_id}.appspot.com`;

  const ts = Date.now();
  const safeName = filename.replace(/[^a-zA-Z0-9._\-]/g, "_");
  const storagePath = `score-uploads/${sessionId}/${ts}_${safeName}`;

  let putUrl, publicUrl;
  try {
    // PUT signé V4 (15 min) — pas de metadata custom (Firebase API kébab-case incompatible)
    putUrl = createV4SignedUrl({
      method: "PUT",
      serviceAccount,
      bucket,
      objectPath: storagePath,
      expiresSeconds: 900,
    });
    // GET signé V4 (7 jours = max V4) — pour Claude API source.url + agent download
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
    storagePath,
    bucket,
    publicUrl,
    requiredHeaders: {}, // plus de header signé requis côté client (juste Content-Type)
  });
};
