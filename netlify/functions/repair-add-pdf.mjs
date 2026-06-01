/**
 * POST /api/repair-add-pdf?dossierId=X&filename=Y
 * Headers: X-Internal-Secret, Content-Type: application/pdf
 * Body: raw PDF binary
 *
 * Endpoint admin-only pour AJOUTER un PDF à un dossier existant.
 * Utilité : réparer un dossier où des PDFs ont été perdus (Netlify Blobs
 * disparus, fichiers oubliés, etc.) — OU ajouter manuellement un doc
 * obtenu hors flow Score Norvex normal.
 *
 * Le PDF va DIRECT dans Firebase Storage (jamais Netlify Blobs).
 * On stocke `path` dans pdfBlobs[] (pas `url`) — Hugo regénère la signed URL
 * just-in-time, donc plus de problème d'expiration 7 jours.
 *
 * Created 2026-05-13 — Action #3 systémique.
 */

import crypto from "node:crypto";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// ─── Google OAuth (JWT bearer) ────────────────────────────────────────────

async function getGoogleToken(sa, scope) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: sa.client_email,
    sub: sa.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
    scope,
  };
  const b64 = (obj) =>
    Buffer.from(JSON.stringify(obj))
      .toString("base64")
      .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const signingInput = `${b64(header)}.${b64(payload)}`;

  const pemBody = sa.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\n/g, "");
  const keyData = Buffer.from(pemBody, "base64");
  const privateKey = crypto.createPrivateKey({
    key: keyData, format: "der", type: "pkcs8",
  });
  const sig = crypto.sign("RSA-SHA256", Buffer.from(signingInput), privateKey);
  const sigB64 = sig.toString("base64")
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const jwt = `${signingInput}.${sigB64}`;

  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: jwt,
    }),
  });
  const data = await r.json();
  if (!data.access_token) throw new Error("Google token failed: " + JSON.stringify(data).slice(0, 200));
  return data.access_token;
}

// ─── Firestore helpers ────────────────────────────────────────────────────

async function fsGet(projectId, token, path) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${path}`;
  const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`FS GET ${r.status}: ${(await r.text()).slice(0, 200)}`);
  return await r.json();
}

function fromFsValue(v) {
  if (!v) return null;
  if (v.nullValue !== undefined) return null;
  if (v.booleanValue !== undefined) return v.booleanValue;
  if (v.integerValue !== undefined) return Number(v.integerValue);
  if (v.doubleValue !== undefined) return v.doubleValue;
  if (v.stringValue !== undefined) return v.stringValue;
  if (v.timestampValue !== undefined) return v.timestampValue;
  if (v.arrayValue !== undefined) {
    return (v.arrayValue.values || []).map(fromFsValue);
  }
  if (v.mapValue !== undefined) {
    const out = {};
    for (const [k, val] of Object.entries(v.mapValue.fields || {})) {
      out[k] = fromFsValue(val);
    }
    return out;
  }
  return null;
}

function toFsValue(v) {
  if (v === null || v === undefined) return { nullValue: null };
  if (typeof v === "boolean") return { booleanValue: v };
  if (typeof v === "number") {
    return Number.isInteger(v) ? { integerValue: String(v) } : { doubleValue: v };
  }
  if (typeof v === "string") return { stringValue: v };
  if (Array.isArray(v)) {
    return { arrayValue: { values: v.map(toFsValue) } };
  }
  if (typeof v === "object") {
    const fields = {};
    for (const [k, val] of Object.entries(v)) fields[k] = toFsValue(val);
    return { mapValue: { fields } };
  }
  return { stringValue: String(v) };
}

async function fsPatchField(projectId, token, path, fieldName, fieldValue) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${path}?updateMask.fieldPaths=${encodeURIComponent(fieldName)}`;
  const fields = { [fieldName]: toFsValue(fieldValue) };
  const r = await fetch(url, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });
  if (!r.ok) throw new Error(`FS PATCH ${r.status}: ${(await r.text()).slice(0, 200)}`);
  return true;
}

// ─── Handler ──────────────────────────────────────────────────────────────

export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-Internal-Secret",
      },
    });
  }
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  // Auth
  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return json({ error: "Unauthorized" }, 401);
  }

  // Params
  const url = new URL(req.url);
  const dossierId = url.searchParams.get("dossierId");
  const filename = url.searchParams.get("filename");
  if (!dossierId) return json({ error: "dossierId required (?dossierId=)" }, 400);
  if (!filename) return json({ error: "filename required (?filename=)" }, 400);
  if (!/^[a-zA-Z0-9._\-]+$/.test(dossierId)) return json({ error: "Invalid dossierId format" }, 400);

  // Read body
  let pdfBuffer;
  try {
    const buf = await req.arrayBuffer();
    pdfBuffer = Buffer.from(buf);
  } catch (e) {
    return json({ error: "Failed to read body: " + e.message }, 400);
  }
  if (!pdfBuffer || pdfBuffer.length === 0) {
    return json({ error: "Empty body — pass PDF bytes" }, 400);
  }
  // Sanity check : first 4 bytes = %PDF
  if (pdfBuffer.slice(0, 4).toString() !== "%PDF") {
    return json({ error: "Body does not look like a PDF (missing %PDF header)" }, 400);
  }

  // Service account
  const { getServiceAccount } = await import("./_firebase-sa.mjs");

  let sa;

  try { sa = await getServiceAccount(); }

  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  const bucket = process.env.FIREBASE_STORAGE_BUCKET || `${sa.project_id}.appspot.com`;
  const ts = Date.now();
  const safeName = filename.replace(/[^a-zA-Z0-9._\-]/g, "_");
  const storagePath = `repair-uploads/${dossierId}/${ts}_${safeName}`;

  // 1. Verify dossier exists
  let fsToken;
  try {
    fsToken = await getGoogleToken(sa, "https://www.googleapis.com/auth/datastore");
  } catch (e) {
    return json({ error: "Firestore auth failed: " + e.message }, 500);
  }

  let dossierDoc;
  try {
    dossierDoc = await fsGet(sa.project_id, fsToken, `dossiers/${dossierId}`);
  } catch (e) {
    return json({ error: "Firestore read failed: " + e.message }, 500);
  }
  if (!dossierDoc) return json({ error: `Dossier ${dossierId} not found` }, 404);

  // 2. Upload to Firebase Storage via GCS upload API
  let storageToken;
  try {
    storageToken = await getGoogleToken(sa, "https://www.googleapis.com/auth/devstorage.read_write");
  } catch (e) {
    return json({ error: "Storage auth failed: " + e.message }, 500);
  }

  const uploadUrl = `https://storage.googleapis.com/upload/storage/v1/b/${encodeURIComponent(bucket)}/o?uploadType=media&name=${encodeURIComponent(storagePath)}`;
  try {
    const uploadResp = await fetch(uploadUrl, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${storageToken}`,
        "Content-Type": "application/pdf",
      },
      body: pdfBuffer,
    });
    if (!uploadResp.ok) {
      const err = await uploadResp.text();
      return json({ error: `GCS upload failed: ${uploadResp.status} ${err.slice(0, 200)}` }, 500);
    }
  } catch (e) {
    return json({ error: "GCS upload exception: " + e.message }, 500);
  }

  // 3. Append new pdfBlobs entry (read-modify-write — race-safe enough for manual repair)
  const existingBlobs = fromFsValue(dossierDoc.fields?.pdfBlobs) || [];
  const newEntry = {
    type: "firebase_url",
    path: storagePath,
    name: filename,
    fileSize: pdfBuffer.length,
    uploadedAt: new Date().toISOString(),
    source: "repair-add-pdf",
    // PAS de url stockée — Hugo régénère just-in-time depuis path
  };
  const updatedBlobs = [...existingBlobs, newEntry];

  try {
    await fsPatchField(sa.project_id, fsToken, `dossiers/${dossierId}`, "pdfBlobs", updatedBlobs);
  } catch (e) {
    return json({
      error: "Firestore patch failed (but file uploaded): " + e.message,
      storagePath,
    }, 500);
  }

  return json({
    ok: true,
    dossierId,
    filename,
    storagePath,
    fileSize: pdfBuffer.length,
    pdfBlobsLength: updatedBlobs.length,
    message: `Ajouté à dossier ${dossierId}. Path Firebase: ${storagePath}. Hugo regénère URL signée just-in-time.`,
  });
};

export const config = { path: "/api/repair-add-pdf" };
