/**
 * POST /.netlify/functions/upload-doc?token=TOKEN&name=filename.pdf
 * Body: raw binary file content
 *
 * Validates token from Netlify Blobs (cn-tokens), stores file in Netlify Blobs (cn-uploads),
 * then adds an entry to the agent queue (cn-queue).  Zero Firebase.
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

function genKey() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
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

  const url   = new URL(req.url);
  const token = url.searchParams.get("token");
  const name  = url.searchParams.get("name") || "document";

  if (!token) return json({ error: "Missing token" }, 400);

  // ── Validate token from Netlify Blobs ─────────────────────────────────────
  const tokenStore = getStore({ name: "cn-tokens", consistency: "strong" });
  let tokenData;
  try {
    tokenData = await tokenStore.get(token, { type: "json" });
  } catch (e) {
    return json({ error: "Token read error: " + e.message }, 500);
  }

  if (!tokenData || tokenData.active === false) {
    return json({ error: "Invalid or expired token" }, 403);
  }

  const { dossierID = "", clientNom = "", clientEmail = "", lang = "fr" } = tokenData;

  // ── Read file body ─────────────────────────────────────────────────────────
  let fileBuffer;
  try {
    fileBuffer = await req.arrayBuffer();
  } catch (e) {
    return json({ error: "Failed to read file: " + e.message }, 400);
  }

  if (!fileBuffer || fileBuffer.byteLength === 0) {
    return json({ error: "Empty file" }, 400);
  }

  // ── Store file in Netlify Blobs (cn-uploads) ──────────────────────────────
  const ts       = Date.now();
  const safeName = name.replace(/[^a-zA-Z0-9._\-]/g, "_");
  const blobKey  = `${dossierID}/${ts}_${safeName}`;
  const uploadStore = getStore({ name: "cn-uploads", consistency: "strong" });

  try {
    await uploadStore.set(blobKey, fileBuffer, {
      metadata: { filename: name, dossierID, clientNom },
    });
  } catch (e) {
    return json({ error: "File storage failed: " + e.message }, 500);
  }

  // ── Add to agent queue (cn-queue) ─────────────────────────────────────────
  const queueKey = genKey();
  const queueStore = getStore({ name: "cn-queue", consistency: "strong" });

  try {
    await queueStore.setJSON(queueKey, {
      dossierID,
      tokenID:     token,
      clientNom,
      clientEmail,
      lang,
      filename:    name,
      blobKey,
      fileSize:    fileBuffer.byteLength,
      uploadedAt:  new Date().toISOString(),
      status:      "pending",
    });
  } catch (e) {
    // File is stored — queue write failed but don't make the client retry
    console.error("Queue write failed:", e.message);
    return json({ ok: true, blobKey, warning: "Queue write failed" });
  }

  return json({ ok: true, blobKey, queueKey });
};
