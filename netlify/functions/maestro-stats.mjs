/**
 * GET /.netlify/functions/maestro-stats?hours=24
 * Header: x-internal-secret
 *
 * Retourne les stats Norvex Maestro™ pour le tile Brain :
 *   - dispatches récents par route
 *   - alertes en attente (alert_yves_now=true non encore vues)
 *   - dispatches par mailbox
 *   - dernière exécution Maestro
 */

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "private, max-age=15" },
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
  return { token: data.access_token, projectId: sa.project_id };
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

function docToObj(doc) {
  if (!doc?.fields) return {};
  const out = {};
  for (const [k, v] of Object.entries(doc.fields)) out[k] = fromFsValue(v);
  return out;
}

export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-internal-secret",
      },
    });
  }

  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return json({ error: "Unauthorized" }, 401);
  }

  const url = new URL(req.url);
  const hours = Math.max(1, Math.min(168, Number(url.searchParams.get("hours")) || 24));

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let sa;


  try { sa = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  try {
    const { token, projectId } = await getFirestoreToken(sa);

    // Query maestroDispatch des dernières N heures
    const cutoff = new Date(Date.now() - hours * 3600 * 1000).toISOString();
    const dispatchUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;
    const r = await fetch(dispatchUrl, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        structuredQuery: {
          from: [{ collectionId: "maestroDispatch" }],
          where: {
            fieldFilter: {
              field: { fieldPath: "dispatchedAt" },
              op: "GREATER_THAN_OR_EQUAL",
              value: { stringValue: cutoff },
            },
          },
          orderBy: [{ field: { fieldPath: "dispatchedAt" }, direction: "DESCENDING" }],
          limit: 200,
        },
      }),
    });
    let dispatches = [];
    if (r.ok) {
      const arr = await r.json();
      dispatches = (arr || []).filter(x => x.document).map(x => docToObj(x.document));
    } else {
      // Fallback : sans index, retour vide mais 200 OK
      dispatches = [];
    }

    // Aggregate stats
    const byRoute = {};
    const byMailbox = {};
    const byPriority = { low: 0, medium: 0, high: 0, critical: 0 };
    let alertsCount = 0;
    const recentAlerts = [];

    for (const d of dispatches) {
      const route = d.route || "unknown";
      byRoute[route] = (byRoute[route] || 0) + 1;
      const mb = d.mailbox || "unknown";
      byMailbox[mb] = (byMailbox[mb] || 0) + 1;
      const prio = d.estimated_priority || "medium";
      byPriority[prio] = (byPriority[prio] || 0) + 1;
      if (d.alert_yves_now) {
        alertsCount += 1;
        if (recentAlerts.length < 10) {
          recentAlerts.push({
            messageId: d.messageId,
            mailbox: d.mailbox,
            from: d.from,
            subject: d.subject,
            summary: d.summary,
            priority: d.estimated_priority,
            dispatchedAt: d.dispatchedAt,
          });
        }
      }
    }

    return json({
      ok: true,
      hours,
      total: dispatches.length,
      byRoute,
      byMailbox,
      byPriority,
      alertsCount,
      recentAlerts,
      generatedAt: new Date().toISOString(),
    });
  } catch (e) {
    return json({ error: e.message }, 500);
  }
};

export const config = {
  path: "/api/maestro-stats",
};
