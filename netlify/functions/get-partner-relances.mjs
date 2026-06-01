/**
 * GET /.netlify/functions/get-partner-relances
 * Header: X-Internal-Secret
 *
 * Retourne les dossiers ou le partenaire a recu le sommaire executif mais
 * n'a pas encore confirme son acceptation, et qui necessitent une relance.
 *
 * Critères:
 *   - partnerSummarySent === true
 *   - partnerEmail present
 *   - partnerAccepted !== true
 *   - partnerRelanceLevel < 3 (max 3 relances partenaire)
 *   - lastPartnerRelanceAt > X jours OU partnerSentAt > X jours si jamais relance
 *
 * Niveaux:
 *   1 = 5 jours (rappel courtois)
 *   2 = 12 jours (rappel ferme + alerte Yves)
 *   3 = 21 jours (escalade Yves uniquement)
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

const SEUILS_PARTNER = { 1: 5, 2: 12, 3: 21 };

function daysSince(isoStr) {
  if (!isoStr) return null;
  const t = new Date(isoStr).getTime();
  if (isNaN(t)) return null;
  return Math.floor((Date.now() - t) / 86400000);
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

  // Recupere tous les dossiers ou partnerSummarySent === true
  const query = {
    structuredQuery: {
      from: [{ collectionId: "dossiers" }],
      where: {
        fieldFilter: {
          field: { fieldPath: "partnerSummarySent" },
          op: "EQUAL",
          value: { booleanValue: true },
        },
      },
      limit: 200,
    },
  };

  let results;
  try {
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(query),
    });
    results = await resp.json();
  } catch (e) {
    return json({ error: "Firestore query failed: " + e.message }, 500);
  }

  const str  = (f) => f?.stringValue || "";
  const bool = (f) => f?.booleanValue || false;
  const intg = (f) => parseInt(f?.integerValue || "0", 10);
  const tsToIso = (f) => f?.timestampValue || null;

  const aRelancer = [];

  for (const result of results) {
    if (!result.document) continue;
    const doc = result.document;
    const fields = doc.fields || {};
    const id = doc.name.split("/").pop();

    const partnerEmail = str(fields.partnerEmail);
    if (!partnerEmail) continue;

    if (bool(fields.partnerAccepted)) continue;
    if (bool(fields.partnerRefused)) continue;

    const relanceLevel = intg(fields.partnerRelanceLevel);
    if (relanceLevel >= 3) continue;

    const lastEvent = tsToIso(fields.lastPartnerRelanceAt)
                   || tsToIso(fields.partnerSentAt)
                   || tsToIso(fields.createdAt);
    const days = daysSince(lastEvent);
    if (days === null) continue;

    const nextLevel = relanceLevel + 1;
    const seuil = SEUILS_PARTNER[nextLevel];
    if (!seuil || days < seuil) continue;

    aRelancer.push({
      id,
      prenom:       str(fields.prenom),
      nom:          str(fields.nom),
      email:        str(fields.email),
      type:         str(fields.type),
      adresse:      str(fields.adresse),
      stage:        str(fields.stage),
      partnerEmail,
      partnerName:  str(fields.partnerName),
      partnerLang:  str(fields.partnerLang) || "fr",
      partnerRelanceLevel: relanceLevel,
      nextLevel,
      daysSinceLastEvent: days,
    });
  }

  return json({ dossiers: aRelancer });
};
