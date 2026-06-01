// Receives the full analysis payload from the browser, stores it in Netlify Blobs,
// triggers the background analysis, and returns a jobId immediately for async polling.
// V2 ESM format — Blobs context auto-configured by Netlify runtime.
import { getStore } from "@netlify/blobs";

export default async (req) => {
  if (req.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405 });
  }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    return new Response(JSON.stringify({ error: "API key not configured" }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }

  let payload;
  try {
    payload = await req.json();
  } catch (err) {
    console.error("[submit-analysis] JSON parse failed:", err.message);
    return new Response(JSON.stringify({ error: "Invalid JSON body: " + err.message }), {
      status: 400,
      headers: { "Content-Type": "application/json" }
    });
  }

  // 1. Create jobId
  const jobId = `job_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  const store = getStore({ name: "analysis-results", consistency: "strong" });

  // 2. Persist payload + initial status to Blobs
  try {
    await store.setJSON(`payload_${jobId}`, payload);
    await store.setJSON(jobId, { status: "pending", startedAt: Date.now() });
  } catch (err) {
    console.error("[submit-analysis] Blobs error:", err.message);
    return new Response(JSON.stringify({ error: "Failed to queue analysis: " + err.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }

  // 3. Trigger background analysis function (fire-and-forget)
  try {
    const bgUrl = process.env.URL + "/.netlify/functions/analyze-background";
    fetch(bgUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jobId, ...payload })
    }).catch(() => {});
  } catch (e) {
    console.error("[submit-analysis] Could not invoke background:", e.message);
  }

  // 4. Return jobId immediately for client polling
  return new Response(JSON.stringify({ jobId }), {
    status: 202,
    headers: { "Content-Type": "application/json" }
  });
};
