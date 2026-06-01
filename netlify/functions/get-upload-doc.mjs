/**
 * GET /.netlify/functions/get-upload-doc?key=dossierID/ts_filename.pdf
 * Header: X-Internal-Secret: <INTERNAL_SECRET env var>
 *
 * Used by the Python agent to download uploaded files from Netlify Blobs.
 * Secured with a shared secret so only the agent can access files.
 */
import { getStore } from "@netlify/blobs";

export default async (req) => {
  // ── Auth ──────────────────────────────────────────────────────────────────
  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return new Response("Unauthorized", { status: 401 });
  }

  // ── Parse key ─────────────────────────────────────────────────────────────
  const url = new URL(req.url);
  const key = url.searchParams.get("key");
  if (!key) return new Response("Missing key", { status: 400 });

  // ── Fetch from Netlify Blobs ──────────────────────────────────────────────
  const store = getStore({ name: "cn-uploads", consistency: "strong" });

  let blob;
  try {
    blob = await store.get(key, { type: "arrayBuffer" });
  } catch (e) {
    return new Response("Blob fetch error: " + e.message, { status: 500 });
  }

  if (!blob) {
    return new Response("Not found", { status: 404 });
  }

  const filename = key.split("/").pop();
  const ext      = filename.split(".").pop().toLowerCase();
  const mimeMap  = { pdf: "application/pdf", png: "image/png", jpg: "image/jpeg",
                     jpeg: "image/jpeg", xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     xls: "application/vnd.ms-excel", docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                     doc: "application/msword" };
  const mime = mimeMap[ext] || "application/octet-stream";

  return new Response(blob, {
    headers: {
      "Content-Type":        mime,
      "Content-Disposition": `attachment; filename="${filename}"`,
      "Content-Length":      String(blob.byteLength),
    },
  });
};
