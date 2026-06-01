/**
 * GET /.netlify/functions/get-token-info?t=TOKEN
 *
 * Returns token metadata so upload.html can show the client's name/project.
 * Public endpoint — returns only display fields, not internal data.
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
  const url   = new URL(req.url);
  const token = url.searchParams.get("t");
  if (!token) return json({ error: "Missing token" }, 400);

  const store = getStore({ name: "cn-tokens", consistency: "strong" });

  let data;
  try {
    data = await store.get(token, { type: "json" });
  } catch (e) {
    return json({ error: "Storage error" }, 500);
  }

  if (!data || data.active === false) {
    return json({ error: "Invalid or expired token" }, 404);
  }

  return json({
    clientNom:   data.clientNom,
    clientEmail: data.clientEmail,
    projet:      data.projet,
    lang:        data.lang,
    dossierID:   data.dossierID,
  });
};
