/**
 * POST /.netlify/functions/confirm-firebase-upload
 * Body: { token, storagePath, bucket, filename, fileSize, dossierID, clientNom, clientEmail }
 *
 * Appelé par le client APRÈS que l'upload Firebase Storage a réussi.
 * Revalide le token, puis ajoute l'entrée dans la queue agent (cn-queue).
 * Le blobKey est préfixé "firebase:" pour que l'agent sache où télécharger.
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

  let body;
  try { body = await req.json(); }
  catch { return json({ error: "Invalid JSON" }, 400); }

  const {
    token, storagePath, bucket, filename,
    fileSize, dossierID, clientNom, clientEmail,
  } = body;

  if (!token || !storagePath) return json({ error: "Missing token or storagePath" }, 400);

  // ── Re-validate token ─────────────────────────────────────────────────────
  const tokenStore = getStore({ name: "cn-tokens", consistency: "strong" });
  let tokenData;
  try { tokenData = await tokenStore.get(token, { type: "json" }); }
  catch (e) { return json({ error: "Token read error: " + e.message }, 500); }

  if (!tokenData || tokenData.active === false) {
    return json({ error: "Invalid or expired token" }, 403);
  }

  // ── Add to agent queue (cn-queue) ─────────────────────────────────────────
  const queueKey   = genKey();
  const blobKey    = `firebase:${storagePath}`;
  const queueStore = getStore({ name: "cn-queue", consistency: "strong" });

  try {
    await queueStore.setJSON(queueKey, {
      dossierID:   dossierID   || tokenData.dossierID   || "",
      tokenID:     token,
      clientNom:   clientNom   || tokenData.clientNom   || "",
      clientEmail: clientEmail || tokenData.clientEmail || "",
      lang:        tokenData.lang || "fr",
      filename:    filename    || storagePath.split("/").pop(),
      blobKey,
      storagePath,
      bucket:      bucket || "",
      fileSize:    fileSize || 0,
      storageType: "firebase",
      uploadedAt:  new Date().toISOString(),
      status:      "pending",
    });
  } catch (e) {
    console.error("Queue write failed:", e.message);
    return json({ ok: true, blobKey, warning: "Queue write failed: " + e.message });
  }

  return json({ ok: true, blobKey, queueKey });
};
