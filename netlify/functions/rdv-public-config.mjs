/**
 * GET  /api/rdv-public-config              → public, retourne { responseSlaHours, hasTeamsLink }
 * POST /api/rdv-public-config              → auth INTERNAL_SECRET requis
 *      Body: { responseSlaHours?, teamsMeetingLink? }
 *
 * Stocke dans Firestore : settings/rdvPublic
 */

const ENC = new TextEncoder();

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
  });
}

async function getFirestoreToken(sa) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: sa.client_email, sub: sa.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now, exp: now + 3600,
    scope: "https://www.googleapis.com/auth/datastore",
  };
  const b64 = (obj) => btoa(JSON.stringify(obj))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const signingInput = `${b64(header)}.${b64(payload)}`;
  const pemBody = sa.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\n/g, "");
  const keyData = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));
  const privateKey = await crypto.subtle.importKey("pkcs8", keyData.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", privateKey, ENC.encode(signingInput));
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const jwt = `${signingInput}.${sigB64}`;
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: jwt,
    }),
  });
  const data = await r.json();
  if (!data.access_token) throw new Error("Firestore token failed");
  return { token: data.access_token, projectId: sa.project_id };
}

function fromFsValue(v) {
  if (!v) return null;
  if (v.nullValue !== undefined) return null;
  if (v.booleanValue !== undefined) return v.booleanValue;
  if (v.integerValue !== undefined) return Number(v.integerValue);
  if (v.stringValue !== undefined) return v.stringValue;
  if (v.timestampValue !== undefined) return v.timestampValue;
  return null;
}
function toFsValue(v) {
  if (v === null || v === undefined) return { nullValue: null };
  if (typeof v === "number") return { integerValue: String(Math.round(v)) };
  if (typeof v === "string") return { stringValue: v };
  return { stringValue: String(v) };
}

async function getDoc(projectId, token, path) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${path}`;
  const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (r.status === 404) return null;
  if (!r.ok) return null;
  const data = await r.json();
  if (!data.fields) return null;
  const out = {};
  for (const [k, v] of Object.entries(data.fields)) out[k] = fromFsValue(v);
  return out;
}

async function setDoc(projectId, token, path, fields) {
  const fieldNames = Object.keys(fields);
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${path}?` +
    fieldNames.map(f => `updateMask.fieldPaths=${encodeURIComponent(f)}`).join("&");
  const fsFields = {};
  for (const [k, v] of Object.entries(fields)) fsFields[k] = toFsValue(v);
  const r = await fetch(url, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ fields: fsFields }),
  });
  if (!r.ok) throw new Error(`Firestore patch ${r.status}`);
}

export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-internal-secret",
      },
    });
  }

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let sa;


  try { sa = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  try {
    const { token, projectId } = await getFirestoreToken(sa);

    if (req.method === "GET") {
      const doc = await getDoc(projectId, token, "settings/rdvPublic");
      const sla = Number(doc?.responseSlaHours) > 0 ? Number(doc.responseSlaHours) : 24;
      return json({
        ok: true,
        responseSlaHours: sla,
        teamsMeetingLink: doc?.teamsMeetingLink || "",
        hasTeamsLink: !!(doc?.teamsMeetingLink && doc.teamsMeetingLink.trim()),
      });
    }

    if (req.method === "POST") {
      const secret = req.headers.get("x-internal-secret");
      if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
        return json({ error: "Unauthorized" }, 401);
      }
      let body;
      try { body = await req.json(); }
      catch { return json({ error: "Invalid JSON" }, 400); }

      const updates = {};
      if (body.responseSlaHours !== undefined) {
        const n = Number(body.responseSlaHours);
        if (!Number.isFinite(n) || n < 1 || n > 240) {
          return json({ error: "responseSlaHours doit être entre 1 et 240" }, 400);
        }
        updates.responseSlaHours = Math.round(n);
      }
      if (body.teamsMeetingLink !== undefined) {
        const link = String(body.teamsMeetingLink).trim().slice(0, 800);
        updates.teamsMeetingLink = link;
      }
      if (Object.keys(updates).length === 0) {
        return json({ error: "Aucune modification" }, 400);
      }
      await setDoc(projectId, token, "settings/rdvPublic", updates);
      return json({ ok: true, updated: updates });
    }

    return json({ error: "Method not allowed" }, 405);
  } catch (e) {
    return json({ error: e.message }, 500);
  }
};

export const config = {
  path: "/api/rdv-public-config",
};
