// Synchronous function to poll for analysis result stored in Netlify Blobs
import { getStore } from "@netlify/blobs";

// FIX 2026-05-25 PM : Headers défensifs contre ERR_HTTP2_PROTOCOL_ERROR Chrome
// (polling rapide 1-1.5s + HTTP/2 multiplexing Netlify cause des protocol errors).
// Cache-Control:no-store + Pragma + X-Accel-Buffering désactive le chunked broken.
const RESPONSE_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store, no-cache, must-revalidate, private, max-age=0",
  "Pragma": "no-cache",
  "Expires": "0",
  "X-Accel-Buffering": "no",
  "Vary": "*"
};

export default async (req) => {
  const url = new URL(req.url);
  const jobId = url.searchParams.get("jobId");

  if (!jobId) {
    return new Response(JSON.stringify({ error: "Missing jobId" }), {
      status: 400,
      headers: RESPONSE_HEADERS
    });
  }

  // consistency "eventual" + Promise.race timeout 8s pour fail-fast
  const store = getStore({ name: "analysis-results", consistency: "eventual" });

  try {
    const data = await Promise.race([
      store.get(jobId, { type: "json" }),
      new Promise((_, reject) => setTimeout(() => reject(new Error("blob_get_timeout_8s")), 8000))
    ]);

    if (!data) {
      return new Response(JSON.stringify({ status: "pending" }), {
        status: 200,
        headers: RESPONSE_HEADERS
      });
    }

    if (data.status === "done" || data.status === "error") {
      store.delete(jobId).catch(() => {});
    }

    return new Response(JSON.stringify(data), {
      status: 200,
      headers: RESPONSE_HEADERS
    });

  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: RESPONSE_HEADERS
    });
  }
};
