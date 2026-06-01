/**
 * POST /.netlify/functions/mark-processed
 * Header: X-Internal-Secret
 * Body: { queueKey, status, error? }
 *
 * Updates the status of a queue item in cn-queue Netlify Blobs.
 * Used by the Python agent after processing a file.
 */
import { getStore } from "@netlify/blobs";

export default async (req) => {
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return new Response("Unauthorized", { status: 401 });
  }

  let body;
  try { body = await req.json(); }
  catch { return new Response("Invalid JSON", { status: 400 }); }

  const { queueKey, status, error } = body;
  if (!queueKey) return new Response("Missing queueKey", { status: 400 });

  const store = getStore({ name: "cn-queue", consistency: "strong" });

  let data;
  try {
    data = await store.get(queueKey, { type: "json" });
  } catch (e) {
    return new Response("Read error: " + e.message, { status: 500 });
  }

  if (!data) return new Response("Queue item not found", { status: 404 });

  const updated = {
    ...data,
    status:      status || "processed",
    processedAt: new Date().toISOString(),
    ...(error ? { error } : {}),
  };

  try {
    await store.setJSON(queueKey, updated);
  } catch (e) {
    return new Response("Write error: " + e.message, { status: 500 });
  }

  return new Response(JSON.stringify({ ok: true }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
};
