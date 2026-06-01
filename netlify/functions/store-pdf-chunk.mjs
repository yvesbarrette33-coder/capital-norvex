// Netlify Function v2 — stocke un morceau (chunk) de gros PDF dans Netlify Blobs
// Accepte JSON: { key, chunkIndex, totalChunks, data (base64 partiel) }
// Retourne { ok: true }

import { getStore } from "@netlify/blobs";

export default async (req) => {
  if (req.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405 });
  }

  let body;
  try {
    body = await req.json();
  } catch (err) {
    return new Response(JSON.stringify({ error: "Invalid JSON: " + err.message }), {
      status: 400, headers: { "Content-Type": "application/json" }
    });
  }

  const { key, chunkIndex, totalChunks, data } = body;

  if (!key || chunkIndex === undefined || !totalChunks || !data) {
    return new Response(JSON.stringify({ error: "Missing required fields" }), {
      status: 400, headers: { "Content-Type": "application/json" }
    });
  }

  const store = getStore({ name: "analysis-results", consistency: "strong" });

  try {
    const chunkKey = `${key}_chunk_${chunkIndex}`;
    await store.setJSON(chunkKey, { data, chunkIndex, totalChunks, parentKey: key });

    // Si c'est le dernier chunk, marquer que tous les chunks sont prêts
    if (chunkIndex === totalChunks - 1) {
      await store.setJSON(`${key}_meta`, { totalChunks, name: body.name || "document.pdf", ready: true });
    }

    return new Response(JSON.stringify({ ok: true, chunkKey }), {
      status: 200, headers: { "Content-Type": "application/json" }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: "Storage failed: " + err.message }), {
      status: 500, headers: { "Content-Type": "application/json" }
    });
  }
};
