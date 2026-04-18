// v1 Lambda format — 6MB body limit (vs ~1MB for v2 streaming)
const { getStore } = require("@netlify/blobs");

exports.handler = async function(event) {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method Not Allowed" }; 
  }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    return {
      statusCode: 500,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ error: "API key not configured" })
    };
  }

  let payload;
  try {
    payload = JSON.parse(event.body);
  } catch (err) {
    console.error("[submit-analysis] JSON parse failed:", err.message);
    return {
      statusCode: 400,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ error: "Invalid JSON body: " + err.message })
    };
  }

  const jobId = `job_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  const store = getStore({ name: "analysis-results", consistency: "strong" });

  try {
    await store.setJSON(`payload_${jobId}`, payload);
    await store.setJSON(jobId, { status: "pending", startedAt: Date.now() });
  } catch (err) {
    console.error("[submit-analysis] Blobs error:", err.message);
    return {
      statusCode: 500,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ error: "Failed to queue analysis: " + err.message })
    };
  }

  // Déclencher la fonction background (fire-and-forget)
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

  return {
    statusCode: 202,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jobId })
  };
};
