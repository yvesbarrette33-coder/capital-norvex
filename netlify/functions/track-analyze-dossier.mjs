/**
 * POST /api/track-analyze-dossier  (thin sync wrapper)
 * Header: x-internal-secret
 * Body: { dossierId, documents?, force_opus_validation? }
 *
 * Pattern background (UPGRADE 2026-05-19 — fix timeout 504) :
 *   1. Valide auth + dossier exists + ventilation > 0
 *   2. Crée jobId, persiste {status:"pending"} dans Firestore trackJobs/{jobId}
 *   3. Fire-and-forget POST → track-analyze-dossier-background (15 min budget)
 *   4. Retourne 202 {jobId, poll_url}
 *
 * Le client poll /api/track-job-status?jobId=xxx pour récupérer le résultat.
 *
 * Avant 2026-05-19 : ce endpoint faisait tout en synchrone et timeout à 26 s.
 */

const SITE_URL = process.env.SITE_URL || "https://capitalnorvex.com";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

// ─── Firestore minimal helpers ────────────────────────────────────────────

async function getFirestoreToken(sa) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: sa.client_email,
    sub: sa.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
    scope: "https://www.googleapis.com/auth/datastore",
  };
  const b64fn = (obj) =>
    btoa(JSON.stringify(obj))
      .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const signingInput = `${b64fn(header)}.${b64fn(payload)}`;
  const pemBody = sa.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\n/g, "");
  const keyData = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));
  const privateKey = await crypto.subtle.importKey(
    "pkcs8", keyData.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5", privateKey, new TextEncoder().encode(signingInput)
  );
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=${signingInput}.${sigB64}`,
  });
  const data = await r.json();
  if (!r.ok) throw new Error("Token: " + JSON.stringify(data));
  return data.access_token;
}

function fromFsValue(v) {
  if (!v) return null;
  if (v.nullValue !== undefined) return null;
  if (v.booleanValue !== undefined) return v.booleanValue;
  if (v.integerValue !== undefined) return Number(v.integerValue);
  if (v.doubleValue !== undefined) return v.doubleValue;
  if (v.stringValue !== undefined) return v.stringValue;
  if (v.timestampValue !== undefined) return v.timestampValue;
  if (v.arrayValue !== undefined) {
    return (v.arrayValue.values || []).map(fromFsValue);
  }
  if (v.mapValue !== undefined) {
    const out = {};
    for (const [k, val] of Object.entries(v.mapValue.fields || {})) {
      out[k] = fromFsValue(val);
    }
    return out;
  }
  return null;
}

function toFsValue(v) {
  if (v === null || v === undefined) return { nullValue: null };
  if (typeof v === "boolean") return { booleanValue: v };
  if (typeof v === "number") {
    return Number.isInteger(v) ? { integerValue: String(v) } : { doubleValue: v };
  }
  if (typeof v === "string") return { stringValue: v };
  if (Array.isArray(v)) return { arrayValue: { values: v.map(toFsValue) } };
  if (typeof v === "object") {
    const fields = {};
    for (const [k, val] of Object.entries(v)) fields[k] = toFsValue(val);
    return { mapValue: { fields } };
  }
  return { stringValue: String(v) };
}

async function fsGet(projectId, token, path) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${path}`;
  const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`Firestore GET ${path} failed: ${r.status}`);
  const data = await r.json();
  if (!data.fields) return null;
  const out = {};
  for (const [k, v] of Object.entries(data.fields)) out[k] = fromFsValue(v);
  return out;
}

async function fsCreate(projectId, token, collection, docId, data) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collection}?documentId=${encodeURIComponent(docId)}`;
  const fields = {};
  for (const [k, v] of Object.entries(data)) fields[k] = toFsValue(v);
  const r = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });
  if (!r.ok) {
    const txt = await r.text();
    throw new Error(`Firestore CREATE failed: ${r.status} ${txt.slice(0, 200)}`);
  }
  return true;
}

// ─── Main handler ─────────────────────────────────────────────────────────

export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-internal-secret",
      },
    });
  }
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return json({ error: "Unauthorized" }, 401);
  }

  let body;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON" }, 400);
  }

  const { dossierId, documents, force_opus_validation } = body;
  if (!dossierId) return json({ error: "dossierId required" }, 400);

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let sa;


  try { sa = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  try {
    const token = await getFirestoreToken(sa);
    const projectId = sa.project_id;

    // 1. Vérifier que le dossier existe et a une ventilation
    const dossier = await fsGet(projectId, token, `dossiers/${dossierId}`);
    if (!dossier) return json({ error: "Dossier introuvable" }, 404);

    const ventilation = dossier.ventilation || [];
    if (!Array.isArray(ventilation) || ventilation.length === 0) {
      return json({
        dossierId,
        hasData: false,
        message:
          "Aucune ventilation Track pour ce dossier. Initialiser via capital-norvex-track.html.",
      });
    }

    // 2. Créer le job dans Firestore trackJobs/{jobId}
    const jobId = `tjob_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    try {
      await fsCreate(projectId, token, "trackJobs", jobId, {
        status: "pending",
        dossierId,
        createdAt: new Date().toISOString(),
      });
    } catch (e) {
      console.error("[track-wrapper] trackJobs init failed:", e.message);
      // On continue quand même — le background pourra créer/écraser le doc
    }

    // 3. POST vers le background (Netlify Background Function, 15 min).
    // IMPORTANT : on AWAIT pour s'assurer que Netlify n'a pas tué le process
    // parent avant l'envoi (fire-and-forget non garanti sur Netlify v2).
    // Le background retourne 202 quasi-immédiatement (~200 ms), donc on bloque pas.
    const bgUrl = `${SITE_URL}/.netlify/functions/track-analyze-dossier-background`;
    try {
      await fetch(bgUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jobId,
          dossierId,
          documents,
          force_opus_validation,
        }),
      });
    } catch (e) {
      console.error("[track-wrapper] bg trigger failed:", e.message);
      // On continue quand même — job pending, retourne 202 au client.
    }

    // 4. Retourne 202 quasi-immédiatement
    return json(
      {
        ok: true,
        mode: "background",
        jobId,
        dossierId,
        status: "pending",
        message: `Analyse Track lancée en arrière-plan. Poll /api/track-job-status?jobId=${jobId} pour le résultat.`,
        poll_url: `/api/track-job-status?jobId=${jobId}`,
      },
      202
    );
  } catch (e) {
    return json({ error: e.message }, 500);
  }
};

export const config = {
  path: "/api/track-analyze-dossier",
};
