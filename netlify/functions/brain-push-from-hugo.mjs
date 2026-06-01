/**
 * POST /.netlify/functions/brain-push-from-hugo
 * Header: x-internal-secret
 * Body: {
 *   dossierId,
 *   agent,                       // "hugo_norvex_chantier"
 *   verdictGlobal,               // "OK | À surveiller | Critique | DATA_GAP"
 *   actionRecommandee,           // string
 *   synthesis,                   // string (résumé Hugo pour Yves)
 *   modulesSummary,              // {intel, track, cost} chacun {verdict, key_finding}
 *   alertesConsolidees,          // [{niveau, module, message, action_requise}]
 *   deboursementAutorise,        // bool|null
 *   valeurPreteeRecommandee,     // number|null
 *   confianceGlobale,            // "élevé|modéré|faible"
 *   rawReports,                  // {intel_status, track_status, cost_status}
 *   createdAt,                   // ISO timestamp
 * }
 *
 * UPGRADE 2026-05-05 — pour Hugo NORVEX CHANTIER™.
 *
 * Endpoint qui reçoit la synthèse Hugo et la pousse dans Norvex Brain :
 *   1. Stocke un document dans `hugoReports` (dossierId + verdict + détails)
 *   2. Crée un audit log dans `agentAuditLog`
 *   3. Si verdict critique → crée une entrée `brainAlerts` (visible Brain home)
 *
 * Sortie : { ok: true, reportId, alertId? }
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

// Convertit JS → Firestore values
function toFsValue(v) {
  if (v === null || v === undefined) return { nullValue: null };
  if (typeof v === "boolean") return { booleanValue: v };
  if (typeof v === "number") {
    return Number.isInteger(v)
      ? { integerValue: String(v) }
      : { doubleValue: v };
  }
  if (typeof v === "string") return { stringValue: v };
  if (v instanceof Date) return { timestampValue: v.toISOString() };
  if (Array.isArray(v)) {
    return { arrayValue: { values: v.map(toFsValue) } };
  }
  if (typeof v === "object") {
    const fields = {};
    for (const [k, val] of Object.entries(v)) fields[k] = toFsValue(val);
    return { mapValue: { fields } };
  }
  return { stringValue: String(v) };
}

async function createDoc(projectId, fsToken, collection, docId, data) {
  const docPath = docId
    ? `${collection}?documentId=${encodeURIComponent(docId)}`
    : collection;
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${docPath}`;
  const fields = {};
  for (const [k, v] of Object.entries(data)) fields[k] = toFsValue(v);
  const r = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${fsToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ fields }),
  });
  if (!r.ok) {
    const errText = await r.text();
    throw new Error(`Firestore POST ${collection} failed: ${r.status} ${errText.slice(0, 200)}`);
  }
  const responseData = await r.json();
  // Extraire l'ID du nom (format: projects/.../documents/collection/docId)
  const name = responseData.name || "";
  const id = name.split("/").pop();
  return id;
}

// ─── Handler ──────────────────────────────────────────────────────────────

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

  const {
    dossierId,
    agent = "hugo_norvex_chantier",
    verdictGlobal,
    actionRecommandee,
    synthesis,
    modulesSummary,
    alertesConsolidees = [],
    deboursementAutorise,
    valeurPreteeRecommandee,
    confianceGlobale,
    rawReports,
    createdAt,
  } = body;

  if (!dossierId) return json({ error: "dossierId required" }, 400);
  if (!verdictGlobal) return json({ error: "verdictGlobal required" }, 400);

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let sa;


  try { sa = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  try {
    const token = await getFirestoreToken(sa);
    const projectId = sa.project_id;
    const now = new Date();

    // 1. Stocker rapport complet dans hugoReports
    const reportData = {
      dossierId,
      agent,
      verdictGlobal,
      actionRecommandee: actionRecommandee || null,
      synthesis: synthesis || null,
      modulesSummary: modulesSummary || {},
      alertesConsolidees,
      deboursementAutorise: deboursementAutorise === undefined ? null : deboursementAutorise,
      valeurPreteeRecommandee: valeurPreteeRecommandee === undefined ? null : valeurPreteeRecommandee,
      confianceGlobale: confianceGlobale || null,
      rawReports: rawReports || {},
      createdAt: createdAt || now.toISOString(),
      ingestedAt: now,
    };
    const reportId = await createDoc(projectId, token, "hugoReports", null, reportData);

    // 2. Audit log
    await createDoc(projectId, token, "agentAuditLog", null, {
      agent,
      action: "hugo_brain_push",
      targetType: "dossiers",
      targetId: dossierId,
      result: "success",
      details: {
        verdictGlobal,
        actionRecommandee: actionRecommandee || null,
        reportId,
      },
      createdAt: now,
    });

    // 3. Si verdict critique OU action escalade → créer brainAlert
    let alertId = null;
    const isCritical =
      verdictGlobal === "Critique" ||
      actionRecommandee === "BLOCK_DISBURSEMENT_ESCALATE_YVES";
    if (isCritical) {
      alertId = await createDoc(projectId, token, "brainAlerts", null, {
        source: "hugo",
        dossierId,
        severity: "critical",
        title: `Hugo : ${verdictGlobal} sur dossier ${dossierId}`,
        message: synthesis || actionRecommandee,
        relatedReportId: reportId,
        status: "pending",
        createdAt: now,
      });
    }

    return json({
      ok: true,
      reportId,
      alertId,
      isCritical,
    });
  } catch (e) {
    return json({ error: e.message }, 500);
  }
};

export const config = {
  path: "/api/brain-push-from-hugo",
};
