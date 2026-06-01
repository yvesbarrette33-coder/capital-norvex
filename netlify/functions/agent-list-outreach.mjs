/**
 * GET /.netlify/functions/agent-list-outreach
 * Header: X-Internal-Secret
 *
 * Retourne pour les 3 agents (capital, courtiers, promoteurs):
 *  - la liste des cibles avec statut envoi (pendingDraft / sentAt / lastTestAt)
 *  - les compteurs (total, en attente, envoyés, tests)
 *  - une vue "history" agrégée triée par date
 *
 * Collections lues:
 *  - capitalTargets       (status, pendingDraft, sentAt, sentTo, sentSubject)
 *  - brokers              (status, pendingDraft, sentAt, sentTo, sentSubject)
 *  - promoteurTargets     (status, pendingDraft, sentAt, sentTo, sentSubject)
 *  - agentAuditLog        (timestamp desc, limit 100, action ~ outreach_*)
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
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");
  const signingInput = `${b64(header)}.${b64(payload)}`;
  const pemBody = sa.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\n/g, "");
  const keyData = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));
  const privateKey = await crypto.subtle.importKey(
    "pkcs8",
    keyData.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    privateKey,
    new TextEncoder().encode(signingInput)
  );
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
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
  if (v.arrayValue !== undefined) {
    return (v.arrayValue.values || []).map(fromFsValue);
  }
  if (v.mapValue !== undefined) {
    const out = {};
    const fields = v.mapValue.fields || {};
    for (const [k, val] of Object.entries(fields)) out[k] = fromFsValue(val);
    return out;
  }
  return null;
}

function fsDocToObj(doc) {
  const out = { id: doc.name.split("/").pop() };
  const fields = doc.fields || {};
  for (const [k, v] of Object.entries(fields)) out[k] = fromFsValue(v);
  return out;
}

let _saCache = null;
async function loadServiceAccount() {
  if (_saCache) return _saCache;
  try {
    const { getStore } = await import("@netlify/blobs");
    const store = getStore("norah-config");
    const saJson = await store.get("firebase-sa");
    if (saJson) {
      _saCache = JSON.parse(saJson);
      return _saCache;
    }
  } catch (_e) { /* fallback env */ }
  let saRaw = null;
  if (process.env.FIREBASE_SA_B64) {
    saRaw = atob(process.env.FIREBASE_SA_B64);
  } else if (process.env.FIREBASE_SERVICE_ACCOUNT_KEY) {
    saRaw = process.env.FIREBASE_SERVICE_ACCOUNT_KEY;
  }
  if (!saRaw) throw new Error("Firebase SA not found (no blob, no env var)");
  _saCache = JSON.parse(saRaw);
  return _saCache;
}

async function listCollection(projectId, fsToken, collectionId, limit = 500) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collectionId}?pageSize=${limit}`;
  const r = await fetch(url, {
    headers: { Authorization: `Bearer ${fsToken}` },
  });
  if (!r.ok) {
    // Collection peut ne pas exister encore — renvoyer []
    return [];
  }
  const data = await r.json();
  return (data.documents || []).map(fsDocToObj);
}

async function listRecentAuditLogs(projectId, fsToken, limit = 100) {
  const queryUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;
  const structuredQuery = {
    from: [{ collectionId: "agentAuditLog" }],
    orderBy: [
      { field: { fieldPath: "timestamp" }, direction: "DESCENDING" },
    ],
    limit,
  };
  const r = await fetch(queryUrl, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${fsToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ structuredQuery }),
  });
  if (!r.ok) return [];
  const rows = await r.json();
  return (rows || []).filter((r) => r.document).map((r) => fsDocToObj(r.document));
}

function summarize(rows) {
  const total = rows.length;
  const pending = rows.filter((r) => r.pendingDraft && !r.sentAt).length;
  const sent = rows.filter((r) => r.sentAt).length;
  const tested = rows.filter((r) => r.lastTestAt).length;
  return { total, pending, sent, tested };
}

export default async function handler(req) {
  if (req.method !== "GET") return json({ error: "Method not allowed" }, 405);

  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return json({ error: "Unauthorized" }, 401);
  }

  try {
    const sa = await loadServiceAccount();
    const projectId = sa.project_id;
    const fsToken = await getFirestoreToken(sa);

    const [capital, brokers, promoteurs, advisors, audit] = await Promise.all([
      listCollection(projectId, fsToken, "capitalTargets"),
      listCollection(projectId, fsToken, "brokers"),
      listCollection(projectId, fsToken, "promoteurTargets"),
      listCollection(projectId, fsToken, "advisorTargets"),
      listRecentAuditLogs(projectId, fsToken, 100),
    ]);

    // On enlève le HTML des pendingDraft pour alléger la réponse principale.
    // Le HTML complet sera récupéré via agent-send-outreach (mode preview).
    const stripDraft = (rows) =>
      rows.map((r) => {
        if (r.pendingDraft && r.pendingDraft.html) {
          const { html, ...meta } = r.pendingDraft;
          return { ...r, pendingDraft: { ...meta, hasHtml: true } };
        }
        return r;
      });

    return json({
      ok: true,
      capital: {
        rows: stripDraft(capital),
        counts: summarize(capital),
      },
      courtiers: {
        rows: stripDraft(brokers),
        counts: summarize(brokers),
      },
      promoteurs: {
        rows: stripDraft(promoteurs),
        counts: summarize(promoteurs),
      },
      advisors: {
        rows: stripDraft(advisors),
        counts: summarize(advisors),
      },
      history: audit
        .filter((a) => (a.action || "").startsWith("outreach_"))
        .slice(0, 50),
    });
  } catch (e) {
    return json({ error: e.message }, 500);
  }
}

export const config = {
  path: "/api/agent-list-outreach",
};
