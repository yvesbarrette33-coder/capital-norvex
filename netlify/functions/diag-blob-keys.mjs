/**
 * GET /api/diag-blob-keys?keys=k1,k2,k3
 * Vérifie si des keys spécifiques existent dans nos 5 stores Netlify Blobs.
 *
 * Diagnostic temporaire pour Action #3 — Hugo blob_ref not found.
 * À SUPPRIMER après audit.
 *
 * Created 2026-05-13 — Action #3 audit.
 */

import { getStore } from "@netlify/blobs";

const STORES = ["analysis-results", "cn-uploads", "cn-queue", "cn-track-uploads", "cn-tokens"];

export default async (req) => {
  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401, headers: { "Content-Type": "application/json" },
    });
  }
  const url = new URL(req.url);
  const keys = (url.searchParams.get("keys") || "").split(",").map(k => k.trim()).filter(Boolean);
  if (!keys.length) return new Response(JSON.stringify({ error: "keys required" }), {
    status: 400, headers: { "Content-Type": "application/json" },
  });

  const out = {};
  for (const key of keys) {
    out[key] = {};
    for (const storeName of STORES) {
      try {
        const store = getStore({ name: storeName, consistency: "strong" });
        // Try get as json + as raw
        let found = false;
        let kind = null;
        try {
          const meta = await store.getMetadata(key);
          if (meta) { found = true; kind = "metadata_ok"; }
        } catch (e) {
          // Some stores don't support metadata
        }
        if (!found) {
          try {
            const v = await store.get(key, { type: "stream" });
            if (v) { found = true; kind = "raw_ok"; }
          } catch (e) {}
        }
        if (!found) {
          try {
            const v = await store.get(key, { type: "json" });
            if (v) { found = true; kind = "json_ok"; }
          } catch (e) {}
        }
        out[key][storeName] = found ? kind : "not_found";
      } catch (e) {
        out[key][storeName] = "store_error: " + e.message.slice(0, 80);
      }
    }
  }
  return new Response(JSON.stringify({ ok: true, keys: out }, null, 2), {
    status: 200, headers: { "Content-Type": "application/json" },
  });
};

export const config = { path: "/api/diag-blob-keys" };
