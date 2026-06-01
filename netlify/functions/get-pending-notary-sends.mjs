/**
 * GET /.netlify/functions/get-pending-notary-sends
 * Header: X-Internal-Secret
 *
 * Retourne les dossiers prets a etre transmis au notaire :
 *   - notaireEmail present
 *   - notaryPackageSent !== true
 *   - stage IN ('notaire','pret_a_signer','pret_a_clore') OU partnerAccepted === true
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

const STAGES_NOTAIRE = new Set(["notaire", "pret_a_signer", "pret_a_clore"]);

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

  // Tous les dossiers où documentsGenerated === true (a passé l'étape engagement)
  const query = {
    structuredQuery: {
      from: [{ collectionId: "dossiers" }],
      where: {
        fieldFilter: {
          field: { fieldPath: "documentsGenerated" },
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

  const dossiers = [];
  for (const result of results) {
    if (!result.document) continue;
    const doc = result.document;
    const fields = doc.fields || {};
    const id = doc.name.split("/").pop();

    const notaireEmail = str(fields.notaireEmail);
    if (!notaireEmail) continue;

    if (bool(fields.notaryPackageSent)) continue;

    const stage = str(fields.stage);
    const partnerAccepted = bool(fields.partnerAccepted);
    if (!STAGES_NOTAIRE.has(stage) && !partnerAccepted) continue;

    dossiers.push({
      id,
      prenom:        str(fields.prenom),
      nom:           str(fields.nom),
      email:         str(fields.email),
      tel:           str(fields.tel),
      type:          str(fields.type),
      montant:       str(fields.montant),
      adresse:       str(fields.adresse),
      stage,
      lang:          str(fields.lang) || "fr",
      notaireNom:    str(fields.notaireNom),
      notaireEmail,
      notaireLang:   str(fields.notaireLang) || str(fields.lang) || "fr",
      partnerName:   str(fields.partnerName),
      partnerEmail:  str(fields.partnerEmail),
      partnerAccepted,
    });
  }

  return json({ dossiers });
};
