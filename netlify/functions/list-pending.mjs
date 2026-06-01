/**
 * GET /.netlify/functions/list-pending
 * Header: X-Internal-Secret
 *
 * Returns all pending upload queue items from Netlify Blobs (cn-queue store).
 * Used by the Python agent to discover files that need processing.
 */
import { getStore } from "@netlify/blobs";

export default async (req) => {
  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return new Response("Unauthorized", { status: 401 });
  }

  const store = getStore({ name: "cn-queue", consistency: "strong" });

  let blobs;
  try {
    const result = await store.list();
    blobs = result.blobs || [];
  } catch (e) {
    return new Response(JSON.stringify({ error: "List failed: " + e.message }), {
      status: 500, headers: { "Content-Type": "application/json" },
    });
  }

  const pending = [];
  for (const blob of blobs) {
    try {
      const data = await store.get(blob.key, { type: "json" });
      if (data && data.status === "pending") {
        pending.push({ queueKey: blob.key, ...data });
      }
    } catch {
      // Skip unreadable blobs
    }
  }

  return new Response(JSON.stringify({ pending }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
};
