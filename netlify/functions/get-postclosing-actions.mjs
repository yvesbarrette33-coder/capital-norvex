/**
 * GET /.netlify/functions/get-postclosing-actions
 * Header: X-Internal-Secret
 *
 * Retourne les dossiers signés/complétés qui nécessitent une action de suivi :
 *
 * Phase 1 — Suivi post-clôture :
 *   - stage IN ('signe','complete')
 *   - postClosingFollowupSent !== true
 *   - signedAt / completedAt > 1 jour (délai pour s'assurer que la clôture est finalisée)
 *
 * Phase 2 — Alerte de renouvellement :
 *   - renewalAlertSent !== true
 *   - maturityDate défini ET dans <= 90 jours
 */

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function getFirestoreToken(serviceAccount) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: serviceAccount.client_email,
    sub: serviceAccount.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
    scope: "https://www.googleapis.com/auth/datastore",
  };
  const b64 = (obj) =>
    btoa(JSON.stringify(obj))
      .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const signingInput = `${b64(header)}.${b64(payload)}`;
  const pemBody = serviceAccount.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\n/g, "");
  const keyData = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));
  const privateKey = await crypto.subtle.importKey(
    "pkcs8", keyData.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false, ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5", privateKey, new TextEncoder().encode(signingInput)
  );
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const jwt = `${signingInput}.${sigB64}`;
  const tokenResp = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: jwt,
    }),
  });
  return (await tokenResp.json()).access_token;
}

function daysSince(isoStr) {
  if (!isoStr) return null;
  const t = new Date(isoStr).getTime();
  if (isNaN(t)) return null;
  return Math.floor((Date.now() - t) / 86400000);
}

function daysUntil(isoStr) {
  if (!isoStr) return null;
  const t = new Date(isoStr).getTime();
  if (isNaN(t)) return null;
  return Math.ceil((t - Date.now()) / 86400000);
}

export default async (req) => {
  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return json({ error: "Unauthorized" }, 401);
  }

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let serviceAccount;


  try { serviceAccount = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  let accessToken;
  try { accessToken = await getFirestoreToken(serviceAccount); }
  catch (e) { return json({ error: "Auth failed: " + e.message }, 500); }

  const projectId = serviceAccount.project_id;
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;

  // Query: stage IN ('signe', 'complete') OR (maturityDate set AND renewalAlertSent != true)
  // On fait 2 queries et on merge

  const queryStages = {
    structuredQuery: {
      from: [{ collectionId: "dossiers" }],
      where: {
        fieldFilter: {
          field: { fieldPath: "stage" },
          op: "IN",
          value: {
            arrayValue: {
              values: [
                { stringValue: "signe" },
                { stringValue: "complete" },
              ],
            },
          },
        },
      },
      limit: 200,
    },
  };

  let results1 = [], results2 = [];

  try {
    const r1 = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(queryStages),
    });
    results1 = await r1.json();
  } catch (_) {}

  // Query 2: renewalAlertSent == false ET maturityDate existe (approximatif — on filtre côté serveur)
  const queryRenewal = {
    structuredQuery: {
      from: [{ collectionId: "dossiers" }],
      where: {
        fieldFilter: {
          field: { fieldPath: "renewalAlertSent" },
          op: "EQUAL",
          value: { booleanValue: false },
        },
      },
      limit: 200,
    },
  };

  try {
    const r2 = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(queryRenewal),
    });
    results2 = await r2.json();
  } catch (_) {}

  // Fusionner sans doublons
  const seen = new Set();
  const allResults = [];
  for (const r of [...(Array.isArray(results1) ? results1 : []),
                    ...(Array.isArray(results2) ? results2 : [])]) {
    if (!r.document) continue;
    const id = r.document.name.split("/").pop();
    if (!seen.has(id)) { seen.add(id); allResults.push(r); }
  }

  const str  = (f) => f?.stringValue  || "";
  const bool = (f) => f?.booleanValue || false;
  const tsToIso = (f) => f?.timestampValue || null;

  const followupNeeded  = [];
  const renewalNeeded   = [];

  for (const result of allResults) {
    const doc    = result.document;
    const fields = doc.fields || {};
    const id     = doc.name.split("/").pop();
    const stage  = str(fields.stage);
    const email  = str(fields.email);
    if (!email) continue;

    const base = {
      id,
      prenom:   str(fields.prenom),
      nom:      str(fields.nom),
      email,
      tel:      str(fields.tel),
      type:     str(fields.type),
      montant:  str(fields.montant),
      adresse:  str(fields.adresse),
      stage,
      lang:     str(fields.lang) || "fr",
      maturityDate: tsToIso(fields.maturityDate) || str(fields.maturityDate) || null,
    };

    // Phase 1 : post-clôture (stage signe/complete, suiviPas encore envoyé, > 1j)
    if ((stage === "signe" || stage === "complete") && !bool(fields.postClosingFollowupSent)) {
      const closedAt = tsToIso(fields.signedAt) || tsToIso(fields.completedAt) || tsToIso(fields.updatedAt);
      const days = daysSince(closedAt);
      if (days !== null && days >= 1) {
        followupNeeded.push({ ...base, action: "followup", daysSinceClosed: days });
      }
    }

    // Phase 2 : renouvellement (maturityDate dans 90j ou moins)
    if (!bool(fields.renewalAlertSent) && base.maturityDate) {
      const daysLeft = daysUntil(base.maturityDate);
      if (daysLeft !== null && daysLeft <= 90) {
        renewalNeeded.push({ ...base, action: "renewal", daysUntilMaturity: daysLeft });
      }
    }
  }

  return json({ followup: followupNeeded, renewal: renewalNeeded });
};
