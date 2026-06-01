// Accepts a raw binary PDF (Content-Type: application/pdf) via POST.
// Stores it as base64 in Netlify Blobs and returns a key.
// This bypasses the 6MB JSON body limit — binary upload has no base64 overhead.
import { getStore } from "@netlify/blobs";

export default async (req) => {
  if (req.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405 });
  }

  const url = new URL(req.url);
  const name = url.searchParams.get("name") || "document.pdf";

  let base64;
  try {
    const buf = await req.arrayBuffer();
    base64 = Buffer.from(buf).toString("base64");
  } catch (err) {
    return new Response(JSON.stringify({ error: "Failed to read PDF: " + err.message }), {
      status: 400, headers: { "Content-Type": "application/json" }
    });
  }

  const key = `pdf_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  const store = getStore({ name: "analysis-results", consistency: "strong" });

  try {
    await store.setJSON(key, { data: base64, name });
  } catch (err) {
    return new Response(JSON.stringify({ error: "Storage failed: " + err.message }), {
      status: 500, headers: { "Content-Type": "application/json" }
    });
  }

  return new Response(JSON.stringify({ key }), {
    status: 200, headers: { "Content-Type": "application/json" }
  });
};
