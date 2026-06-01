/**
 * POST /.netlify/functions/create-upload-token
 * Body: { dossierID, clientNom, clientEmail, projet, lang }
 *
 * Generates a secure upload token, stores it in Netlify Blobs (cn-tokens),
 * and returns { token, url }.  No Firebase required.
 */
import { getStore } from "@netlify/blobs";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  }

  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  let body;
  try { body = await req.json(); }
  catch { return json({ error: "Invalid JSON" }, 400); }

  const { dossierID, clientNom, clientEmail, projet, lang } = body;
  if (!dossierID) return json({ error: "Missing dossierID" }, 400);

  // Generate cryptographically random token (36 hex chars)
  const bytes = new Uint8Array(18);
  crypto.getRandomValues(bytes);
  const token = Array.from(bytes).map(b => b.toString(16).padStart(2, "0")).join("");

  const tokenData = {
    dossierID,
    clientNom:   clientNom   || "",
    clientEmail: clientEmail || "",
    projet:      projet      || "",
    lang:        lang        || "fr",
    active:      true,
    createdAt:   new Date().toISOString(),
  };

  const store = getStore({ name: "cn-tokens", consistency: "strong" });
  try {
    await store.setJSON(token, tokenData);
  } catch (e) {
    return json({ error: "Token storage failed: " + e.message }, 500);
  }

  const url = `https://capitalnorvex.com/upload.html?t=${token}`;
  return json({ token, url });
};
