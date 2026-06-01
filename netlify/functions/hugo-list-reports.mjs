/**
 * POST /.netlify/functions/hugo-list-reports
 * Header: x-internal-secret
 * Body: { verdictFilter?: "all|OK|À surveiller|Critique|DATA_GAP", limit?: number }
 *
 * Liste les rapports Hugo NORVEX CHANTIER™ stockés dans Firestore
 * (`hugoReports`), triés par date desc.
 *
 * Output : { ok, reports: [{id, dossierId, verdictGlobal, ...}] }
 */

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

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
  const b64 = (obj) =>
    btoa(JSON.stringify(obj))
      .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const signingInput = `${b64(header)}.${b64(payload)}`;
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
  if (v.arrayValue !== undefined) return (v.arrayValue.values || []).map(fromFsValue);
  if (v.mapValue !== undefined) {
    const out = {};
    for (const [k, val] of Object.entries(v.mapValue.fields || {})) out[k] = fromFsValue(val);
    return out;
  }
  return null;
}

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
  try { body = await req.json(); }
  catch { return json({ error: "Invalid JSON" }, 400); }

  const verdictFilter = body.verdictFilter || "all";
  const limit = Math.min(body.limit || 50, 200);

  const { getServiceAccount } = await import("./_firebase-sa.mjs");
  let sa;
  try { sa = await getServiceAccount(); }
  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  try {
    const token = await getFirestoreToken(sa);
    const projectId = sa.project_id;

    // RunQuery — filtre + ordre
    const runQueryUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;
    const queryBody = {
      structuredQuery: {
        from: [{ collectionId: "hugoReports" }],
        orderBy: [{ field: { fieldPath: "createdAt" }, direction: "DESCENDING" }],
        limit,
      },
    };
    if (verdictFilter && verdictFilter !== "all") {
      queryBody.structuredQuery.where = {
        fieldFilter: {
          field: { fieldPath: "verdictGlobal" },
          op: "EQUAL",
          value: { stringValue: verdictFilter },
        },
      };
    }

    const r = await fetch(runQueryUrl, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(queryBody),
    });
    if (!r.ok) {
      const errText = await r.text();
      throw new Error(`Firestore query failed: ${r.status} ${errText.slice(0, 200)}`);
    }
    const docs = await r.json();
    const reports = (docs || [])
      .filter(d => d.document)
      .map(d => {
        const out = {};
        const name = d.document.name || "";
        out.id = name.split("/").pop();
        for (const [k, v] of Object.entries(d.document.fields || {})) {
          out[k] = fromFsValue(v);
        }
        // Mappage des fields → camelCase pour la UI
        if (out.recommandationYves === undefined && out.synthesis) {
          out.recommandationYves = out.synthesis;
        }
        return out;
      });

    return json({ ok: true, count: reports.length, reports });
  } catch (e) {
    return json({ error: e.message }, 500);
  }
};

export const config = {
  path: "/api/hugo-list-reports",
};
