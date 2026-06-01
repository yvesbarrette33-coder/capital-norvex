/**
 * GET /.netlify/functions/get-dossiers-relances
 * Header: X-Internal-Secret
 *
 * Retourne les dossiers qui ont besoin d'une relance automatique.
 * Critères:
 *   - welcomeEmailSent === true (le client a deja recu son email de bienvenue)
 *   - stage NOT IN ['approuve','approuve_yves','approuve_final','refuse','ferme','annule','signe']
 *   - relanceLevel < 4 (max 4 relances, apres = alerte Yves seulement)
 *   - lastRelanceAt > X jours OU welcomeEmailSentAt > X jours si jamais relance
 *
 * Niveaux:
 *   1 = 3 jours apres bienvenue (sympathique)
 *   2 = 7 jours apres bienvenue (rappel)
 *   3 = 14 jours apres bienvenue (urgence + alerte Yves)
 *   4 = 21 jours apres bienvenue (dossier dormant, alerte Yves seulement)
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

const STAGES_FERMES = new Set([
  "approuve", "approuve_yves", "approuve_final",
  "refuse", "ferme", "annule", "signe", "complete",
]);

const SEUILS_JOURS = { 1: 3, 2: 7, 3: 14, 4: 21 };

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

  // Recupere tous les dossiers ou welcomeEmailSent === true
  const query = {
    structuredQuery: {
      from: [{ collectionId: "dossiers" }],
      where: {
        fieldFilter: {
          field: { fieldPath: "welcomeEmailSent" },
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

    const stage = str(fields.stage);
    if (STAGES_FERMES.has(stage)) continue;

    const email = str(fields.email);
    if (!email) continue;

    const relanceLevel = intg(fields.relanceLevel);
    if (relanceLevel >= 4) continue; // deja relance niveau max

    // Date de reference: lastRelanceAt si existe, sinon welcomeEmailSentAt, sinon createdAt
    const lastEvent = tsToIso(fields.lastRelanceAt)
                   || tsToIso(fields.welcomeEmailSentAt)
                   || tsToIso(fields.createdAt)
                   || str(fields.created);
    const days = daysSince(lastEvent);
    if (days === null) continue;

    const nextLevel = relanceLevel + 1;
    const seuil = SEUILS_JOURS[nextLevel];
    if (!seuil || days < seuil) continue;

    aRelancer.push({
      id,
      prenom:    str(fields.prenom),
      nom:       str(fields.nom),
      email,
      tel:       str(fields.tel),
      type:      str(fields.type),
      adresse:   str(fields.adresse),
      stage,
      lang:      str(fields.lang) || "fr",
      relanceLevel,
      nextLevel,
      daysSinceLastEvent: days,
    });
  }

  return json({ dossiers: aRelancer });
};
