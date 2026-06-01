/**
 * GET /.netlify/functions/get-score-pdf?key=xxx&type=blob_ref|chunked_ref
 * Header: X-Internal-Secret
 *
 * Retrieves a PDF stored in the analysis-results Netlify Blobs store
 * during the Score Norvex form submission. Returns raw PDF bytes.
 */
import { getStore } from "@netlify/blobs";

export default async (req) => {
  // Auth
  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401, headers: { "Content-Type": "application/json" },
    });
  }

  const url = new URL(req.url);
  const key     = url.searchParams.get("key");
  const type    = url.searchParams.get("type") || "blob_ref";
  const cleanup = url.searchParams.get("cleanup") === "true";

  if (!key) {
    return new Response(JSON.stringify({ error: "key required" }), {
      status: 400, headers: { "Content-Type": "application/json" },
    });
  }

  const store = getStore({ name: "analysis-results", consistency: "strong" });

  try {
    let base64;

    if (type === "blob_ref") {
      // Simple upload — stored as JSON { data: base64, name }
      const entry = await store.get(key, { type: "json" });
      if (!entry) {
        return new Response(JSON.stringify({ error: "Blob not found" }), {
          status: 404, headers: { "Content-Type": "application/json" },
        });
      }
      base64 = entry.data;
      if (cleanup) store.delete(key).catch(() => {});

    } else if (type === "chunked_ref") {
      // Chunked upload — read meta then reassemble chunks
      const meta = await store.get(`${key}_meta`, { type: "json" });
      if (!meta) {
        return new Response(JSON.stringify({ error: "Chunked blob meta not found" }), {
          status: 404, headers: { "Content-Type": "application/json" },
        });
      }
      const { totalChunks } = meta;
      const parts = [];
      for (let i = 0; i < totalChunks; i++) {
        const chunk = await store.get(`${key}_chunk_${i}`, { type: "json" });
        if (!chunk) {
          return new Response(JSON.stringify({ error: `Chunk ${i} not found` }), {
            status: 404, headers: { "Content-Type": "application/json" },
          });
        }
        parts.push(chunk.data);
      }
      base64 = parts.join("");
      if (cleanup) {
        for (let i = 0; i < totalChunks; i++) {
          store.delete(`${key}_chunk_${i}`).catch(() => {});
        }
        store.delete(`${key}_meta`).catch(() => {});
      }

    } else {
      return new Response(JSON.stringify({ error: "Invalid type" }), {
        status: 400, headers: { "Content-Type": "application/json" },
      });
    }

    // Decode base64 → binary
    const binary = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));

    return new Response(binary, {
      status: 200,
      headers: { "Content-Type": "application/pdf" },
    });

  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500, headers: { "Content-Type": "application/json" },
    });
  }
};
