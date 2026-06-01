/**
 * POST /.netlify/functions/admin-broker-decision
 * Header: X-Admin-Password
 * Body: {
 *   applicationId: string,
 *   action: "approve" | "decline",
 *   notes?: string,           // notes internes
 *   reason?: string           // raison communiquée au courtier (decline)
 * }
 *
 * Actions :
 *   1. Met à jour brokerApplications/{id} : status, reviewedAt, reviewedBy, reviewNotes
 *   2. Si approve : met à jour brokers/{brokerId}.relationshipStatus = "cold"
 *      Si decline : met à jour brokers/{brokerId}.relationshipStatus = "declined"
 *   3. Envoie email approprié au courtier (avec grille commission si approve)
 *   4. Retourne ok + applicationId + action
 */

const ORGANIZER_EMAIL = "yves@capitalnorvex.com";
const ORGANIZER_NAME = "Capital Norvex";
const ENC = new TextEncoder();
const SITE_URL = "https://capitalnorvex.com";

// ── HMAC token pour lien convention ──────────────────────────────────────
function b64urlEncodeBytes(bytes) {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}
function b64urlEncodeString(s) {
  return btoa(unescape(encodeURIComponent(s)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}
async function hmacSign(secret, message) {
  const key = await crypto.subtle.importKey(
    "raw",
    ENC.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, ENC.encode(message));
  return b64urlEncodeBytes(sig);
}
async function generateConventionToken(brokerId, secret, ttlDays = 30) {
  const exp = Date.now() + ttlDays * 24 * 60 * 60 * 1000;
  const payloadB64 = b64urlEncodeString(JSON.stringify({ brokerId, exp }));
  const sig = await hmacSign(secret, payloadB64);
  return `${payloadB64}.${sig}`;
}

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
  if (v.nullValue !== undefined) return null;
  if (v.booleanValue !== undefined) return v.booleanValue;
  if (v.integerValue !== undefined) return Number(v.integerValue);
  if (v.doubleValue !== undefined) return v.doubleValue;
  if (v.stringValue !== undefined) return v.stringValue;
  if (v.timestampValue !== undefined) return v.timestampValue;
  if (v.arrayValue !== undefined)
    return (v.arrayValue.values || []).map(fromFsValue);
  if (v.mapValue !== undefined) {
    const out = {};
    for (const [k, val] of Object.entries(v.mapValue.fields || {}))
      out[k] = fromFsValue(val);
    return out;
  }
  return null;
}

function fsDocToObj(doc) {
  const out = {};
  for (const [k, v] of Object.entries(doc.fields || {}))
    out[k] = fromFsValue(v);
  return out;
}

let _saCache = null;
async function loadServiceAccount() {
  if (_saCache) return _saCache;
  // 1) Netlify Blobs (norah-config / firebase-sa) — évite limite 4KB AWS Lambda
  try {
    const { getStore } = await import("@netlify/blobs");
    const store = getStore("norah-config");
    const saJson = await store.get("firebase-sa");
    if (saJson) {
      _saCache = JSON.parse(saJson);
      return _saCache;
    }
  } catch (_e) { /* fallback env */ }
  // 2) Fallback: env vars (legacy)
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

// ── Email templates ──────────────────────────────────────────────────────

function approvalEmail({ fullName, brokerNumber, lang, conventionUrl }) {
  const isEn = lang === "en";
  const conventionBlockEn = conventionUrl
    ? `<div style="margin:24px 0;padding:24px;background:#FCF8EE;border:2px solid #C8B070;text-align:center;">
<div style="font-size:11px;letter-spacing:2.5px;text-transform:uppercase;color:#9A8554;margin-bottom:10px;">⚖️ Required next step — Sign your partner agreement</div>
<p style="margin:0 0 14px 0;font-size:13.5px;color:#0A0A0A;">To activate your file in our system, please review and electronically sign the Partner Broker Agreement (5 pages, ~5 min).</p>
<a href="${conventionUrl}" style="display:inline-block;background:#0A0A0A;color:#C8B070;padding:14px 32px;text-decoration:none;font-weight:bold;letter-spacing:2px;font-size:13px;border:1px solid #C8B070;">✍️ READ AND SIGN THE AGREEMENT</a>
<p style="margin:14px 0 0 0;font-size:11.5px;color:#888;font-style:italic;">Personal &amp; secure link · Valid 30 days · One-time use</p>
</div>`
    : "";
  const conventionBlockFr = conventionUrl
    ? `<div style="margin:24px 0;padding:24px;background:#FCF8EE;border:2px solid #C8B070;text-align:center;">
<div style="font-size:11px;letter-spacing:2.5px;text-transform:uppercase;color:#9A8554;margin-bottom:10px;">⚖️ Étape requise — Signer votre convention partenaire</div>
<p style="margin:0 0 14px 0;font-size:13.5px;color:#0A0A0A;">Pour activer votre dossier dans notre système, veuillez consulter et signer électroniquement la Convention de partenariat (5 pages, ~5 min).</p>
<a href="${conventionUrl}" style="display:inline-block;background:#0A0A0A;color:#C8B070;padding:14px 32px;text-decoration:none;font-weight:bold;letter-spacing:2px;font-size:13px;border:1px solid #C8B070;">✍️ LIRE ET SIGNER LA CONVENTION</a>
<p style="margin:14px 0 0 0;font-size:11.5px;color:#888;font-style:italic;">Lien personnel &amp; sécurisé · Valide 30 jours · Usage unique</p>
</div>`
    : "";
  if (isEn) {
    return {
      subject: `Welcome to the Capital Norvex Partner Broker Program — Broker # ${brokerNumber}`,
      html: `<!DOCTYPE html><html><body style="margin:0;padding:0;background:#FBF7EB;font-family:Georgia,serif;color:#0A0A0A;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#FBF7EB;">
<tr><td style="background:#0A0A0A;padding:28px 24px;text-align:center;">
<div style="color:#C8B070;font-family:Georgia,serif;font-size:22px;letter-spacing:3px;">CAPITAL NORVEX</div>
<div style="color:#C8B070;font-style:italic;font-size:12px;letter-spacing:1.5px;margin-top:8px;opacity:0.85;">Structured capital. Measured ambition.</div>
</td></tr>
<tr><td style="height:3px;background:linear-gradient(90deg,transparent 0%,#C8B070 50%,transparent 100%);"></td></tr>
<tr><td style="padding:36px;font-size:14px;line-height:1.7;">
<p>Dear ${fullName},</p>
<p>It is our pleasure to confirm that <strong>your application has been accepted</strong>. Welcome to the Capital Norvex Partner Broker Program.</p>

<div style="margin:24px 0;padding:24px;background:#0A0A0A;border:1px solid #C8B070;text-align:center;">
<div style="font-size:10px;letter-spacing:3px;color:#C8B070;text-transform:uppercase;margin-bottom:8px;">Your Partner Broker Number</div>
<div style="font-family:Georgia,serif;font-size:28px;color:#C8B070;letter-spacing:3px;font-weight:bold;">${brokerNumber}</div>
<div style="font-size:11.5px;color:#999;margin-top:10px;">⚠ Required to submit any client file. Without it, your file cannot be processed and analysis fees will not be refunded.</div>
</div>

${conventionBlockEn}

<div style="margin:24px 0;padding:18px 22px;background:#FCF8EE;border-left:3px solid #C8B070;">
<div style="font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:#9A8554;margin-bottom:8px;">Broker compensation</div>
<p style="margin:0;font-size:13.5px;line-height:1.7;">Capital Norvex's file fees (<strong>3% to 3.5%</strong>) are collected by the closing officer (notary in Quebec, lawyer in other Canadian jurisdictions) at closing and paid <strong>exclusively to Capital Norvex</strong>. The Broker's compensation is <strong>negotiated case by case</strong> for each referred file (based on loan size, complexity, file quality and Broker's value-add), in addition to Capital Norvex's fees.</p>
<p style="margin:10px 0 0 0;font-size:12.5px;color:#666;">The Broker submits an invoice to Capital Norvex before closing. At closing, the closing officer deducts the compensation from the proceeds of the approved financing and pays it directly to the Broker — no separate disbursement required from the client.</p>
</div>

<div style="margin:24px 0;padding:18px 22px;background:#FCF8EE;border-left:3px solid #C8B070;">
<div style="font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:#9A8554;margin-bottom:10px;">Program rules — what we accept and what we do not</div>
<ul style="padding-left:18px;margin:0;font-size:13px;">
<li style="margin-bottom:8px;"><strong>No double commission:</strong> the broker is compensated solely under our grid; no additional fee may be charged to the client on the same file.</li>
<li style="margin-bottom:8px;"><strong>File exclusivity:</strong> a file submitted to Capital Norvex must not be simultaneously placed with another private lender.</li>
<li style="margin-bottom:8px;"><strong>Mandatory broker number:</strong> any submission requires your broker number ${brokerNumber}. A submission made without a valid number will be rejected and analysis fees will not be refunded.</li>
<li style="margin-bottom:8px;"><strong>You remain at the center of your client relationship:</strong> every communication with your client (LOI, updates, meetings) is shared with you in parallel. You are present at every meeting. The LOI is sent to your client with you in copy — your role as advisor remains intact.</li>
<li style="margin-bottom:8px;"><strong>Signed broker agreement required</strong> before processing the first file.</li>
<li style="margin-bottom:0;"><strong>Closing fees</strong> (3–3.5%) are collected at closing, <em>exclusively</em> to Capital Norvex — never charged to the broker's commission.</li>
</ul>
</div>

<div style="margin:24px 0;padding:22px;background:#0A0A0A;border:1px solid #C8B070;text-align:center;">
<div style="font-size:10px;letter-spacing:3px;color:#C8B070;text-transform:uppercase;margin-bottom:10px;">Your Broker Workspace</div>
<div style="color:#FBF7EB;font-family:Georgia,serif;font-size:18px;line-height:1.4;margin-bottom:14px;">Submit your clients' files, track every dossier in real time, download your LOIs — 24/7.</div>
<a href="https://capitalnorvex.com/espace-courtier.html" style="display:inline-block;background:#C8B070;color:#0A0A0A;padding:14px 32px;text-decoration:none;font-weight:bold;letter-spacing:2px;font-size:13px;">🚀 OPEN MY BROKER WORKSPACE</a>
<div style="font-size:11.5px;color:#999;margin-top:12px;">Magic-link sign-in (no password) · Installable as an app on your phone and desktop</div>
</div>

<div style="margin:18px 0;padding:18px 22px;background:#FCF8EE;border-left:3px solid #C8B070;font-size:13px;line-height:1.7;">
<div style="font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:#9A8554;margin-bottom:10px;font-weight:bold;">📱 Install your app — 30 seconds</div>
<div style="margin-bottom:10px;"><strong>On iPhone / iPad (Safari):</strong> open the link, tap the <strong>Share</strong> icon (square with up arrow), then <strong>« Add to Home Screen »</strong>. Your Capital Norvex logo appears on your home screen — one tap to launch.</div>
<div style="margin-bottom:10px;"><strong>On Android (Chrome):</strong> open the link, tap the <strong>three-dot menu</strong>, then <strong>« Install app »</strong> or <strong>« Add to home screen »</strong>.</div>
<div><strong>On Mac / PC (Chrome / Edge):</strong> open the link, look for the <strong>install icon</strong> in the address bar (small computer with arrow) or use <strong>menu → Install Capital Norvex</strong>. The app opens in its own window.</div>
</div>

<p><strong>Next steps</strong> :</p>
<ol style="padding-left:20px;">
<li>Open your <strong>Broker Workspace</strong> at <a href="https://capitalnorvex.com/espace-courtier.html" style="color:#9A8554;">capitalnorvex.com/espace-courtier.html</a> — enter your email and we'll send you a secure sign-in link.</li>
<li>Sign the broker agreement (link above) — required before processing your first file.</li>
<li>Submit your first client file directly from your Workspace using your broker number ${brokerNumber}.</li>
</ol>

<p style="margin-top:24px;">Warmly,</p>
<p><strong>The Capital Norvex Team</strong><br><em style="color:#9A8554;font-size:12.5px;letter-spacing:0.5px;">Partner Broker Program</em><br><span style="color:#666;">Capital Norvex Inc.</span></p>
</td></tr>
<tr><td style="background:#0A0A0A;padding:18px;text-align:center;color:#C8B070;font-size:11px;letter-spacing:1px;">
<a href="https://capitalnorvex.com" style="color:#C8B070;text-decoration:none;">capitalnorvex.com</a>
</td></tr>
</table></td></tr></table>  <div style="margin-top:24px;padding-top:14px;border-top:1px solid #cbd5e1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:11px;color:#64748b;line-height:1.5;letter-spacing:.3px;text-align:center">
    <strong style="color:#0f172a;font-size:12px;letter-spacing:1px">CAPITAL NORVEX INC.</strong><br>
    2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
    Téléphone : 1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
  </div>
</body></html>`,
    };
  }
  return {
    subject: `Bienvenue au Programme Courtier Partenaire — N° courtier ${brokerNumber}`,
    html: `<!DOCTYPE html><html><body style="margin:0;padding:0;background:#FBF7EB;font-family:Georgia,serif;color:#0A0A0A;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#FBF7EB;">
<tr><td style="background:#0A0A0A;padding:28px 24px;text-align:center;">
<div style="color:#C8B070;font-family:Georgia,serif;font-size:22px;letter-spacing:3px;">CAPITAL NORVEX</div>
<div style="color:#C8B070;font-style:italic;font-size:12px;letter-spacing:1.5px;margin-top:8px;opacity:0.85;">Capital structuré. Ambition maîtrisée.</div>
</td></tr>
<tr><td style="height:3px;background:linear-gradient(90deg,transparent 0%,#C8B070 50%,transparent 100%);"></td></tr>
<tr><td style="padding:36px;font-size:14px;line-height:1.7;">
<p>Bonjour ${fullName},</p>
<p>Nous avons le plaisir de vous confirmer que <strong>votre candidature a été retenue</strong>. Bienvenue au Programme Courtier Partenaire de Capital Norvex.</p>

<div style="margin:24px 0;padding:24px;background:#0A0A0A;border:1px solid #C8B070;text-align:center;">
<div style="font-size:10px;letter-spacing:3px;color:#C8B070;text-transform:uppercase;margin-bottom:8px;">Votre numéro de courtier partenaire</div>
<div style="font-family:Georgia,serif;font-size:28px;color:#C8B070;letter-spacing:3px;font-weight:bold;">${brokerNumber}</div>
<div style="font-size:11.5px;color:#999;margin-top:10px;">⚠ Obligatoire pour soumettre tout dossier client. Sans ce numéro, votre dossier ne pourra être traité et les frais d'analyse ne seront pas remboursés.</div>
</div>

${conventionBlockFr}

<div style="margin:24px 0;padding:18px 22px;background:#FCF8EE;border-left:3px solid #C8B070;">
<div style="font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:#9A8554;margin-bottom:8px;">Rémunération du courtier</div>
<p style="margin:0;font-size:13.5px;line-height:1.7;">Les frais de dossier de Capital Norvex (<strong>3 % à 3,5 %</strong>) sont prélevés par l'officier instrumentant (notaire au Québec, avocat dans les autres juridictions canadiennes) à la clôture et versés <strong>exclusivement à Capital Norvex</strong>. La rémunération du Courtier est <strong>négociée au cas par cas</strong> pour chaque dossier référé (selon la taille du prêt, la complexité, la qualité du dossier et la valeur apportée par le Courtier), en sus des frais de Capital Norvex.</p>
<p style="margin:10px 0 0 0;font-size:12.5px;color:#666;">Le Courtier transmet sa facture à Capital Norvex avant la clôture. À la clôture, l'officier instrumentant prélève la rémunération à même les fonds du financement accepté et la verse directement au Courtier — sans déboursé séparé exigé du client.</p>
</div>

<div style="margin:24px 0;padding:18px 22px;background:#FCF8EE;border-left:3px solid #C8B070;">
<div style="font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:#9A8554;margin-bottom:10px;">Règles du programme — ce qu'on accepte et ce qu'on n'accepte pas</div>
<ul style="padding-left:18px;margin:0;font-size:13px;">
<li style="margin-bottom:8px;"><strong>Pas de double commission :</strong> le courtier est rémunéré exclusivement selon notre grille ; aucun frais additionnel ne peut être facturé au client sur le même dossier.</li>
<li style="margin-bottom:8px;"><strong>Exclusivité du dossier :</strong> un dossier soumis à Capital Norvex ne doit pas être simultanément placé chez un autre prêteur privé.</li>
<li style="margin-bottom:8px;"><strong>Numéro de courtier obligatoire :</strong> toute soumission requiert votre numéro ${brokerNumber}. Une soumission faite sans numéro valide sera refusée et les frais d'analyse ne seront pas remboursés.</li>
<li style="margin-bottom:8px;"><strong>Vous restez au centre de votre relation client :</strong> chaque communication avec votre client (LOI, mises à jour, rendez-vous) vous est transmise en parallèle. Vous êtes présent à chaque rencontre. La LOI est envoyée à votre client avec vous en copie — votre rôle de conseiller demeure intact.</li>
<li style="margin-bottom:8px;"><strong>Convention courtier signée obligatoire</strong> avant traitement du premier dossier.</li>
<li style="margin-bottom:0;"><strong>Frais de dossier</strong> (3 à 3,5 %) prélevés au notaire, <em>exclusivement</em> à Capital Norvex — jamais imputés sur la commission courtier.</li>
</ul>
</div>

<div style="margin:24px 0;padding:22px;background:#0A0A0A;border:1px solid #C8B070;text-align:center;">
<div style="font-size:10px;letter-spacing:3px;color:#C8B070;text-transform:uppercase;margin-bottom:10px;">Votre Espace Courtier</div>
<div style="color:#FBF7EB;font-family:Georgia,serif;font-size:18px;line-height:1.4;margin-bottom:14px;">Soumettez les dossiers de vos clients, suivez chaque dossier en temps réel, téléchargez vos LOI.</div>
<a href="https://capitalnorvex.com/espace-courtier.html" style="display:inline-block;background:#C8B070;color:#0A0A0A;padding:14px 32px;text-decoration:none;font-weight:bold;letter-spacing:2px;font-size:13px;">🚀 OUVRIR MON ESPACE COURTIER</a>
<div style="font-size:11.5px;color:#999;margin-top:12px;">Connexion par lien magique (sans mot de passe) · Installable comme application sur votre téléphone et votre ordinateur</div>
</div>

<div style="margin:18px 0;padding:18px 22px;background:#FCF8EE;border-left:3px solid #C8B070;font-size:13px;line-height:1.7;">
<div style="font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:#9A8554;margin-bottom:10px;font-weight:bold;">📱 Installez votre application — 30 secondes</div>
<div style="margin-bottom:10px;"><strong>Sur iPhone / iPad (Safari) :</strong> ouvrez le lien, appuyez sur l'icône <strong>Partager</strong> (carré avec flèche vers le haut), puis <strong>« Sur l'écran d'accueil »</strong>. Le logo Capital Norvex apparaît sur votre écran d'accueil — un tap pour lancer.</div>
<div style="margin-bottom:10px;"><strong>Sur Android (Chrome) :</strong> ouvrez le lien, appuyez sur le <strong>menu trois-points</strong>, puis <strong>« Installer l'application »</strong> ou <strong>« Ajouter à l'écran d'accueil »</strong>.</div>
<div><strong>Sur Mac / PC (Chrome / Edge) :</strong> ouvrez le lien, repérez l'<strong>icône d'installation</strong> dans la barre d'adresse (petit ordinateur avec flèche) ou utilisez <strong>menu → Installer Capital Norvex</strong>. L'application s'ouvre dans sa propre fenêtre.</div>
</div>

<p><strong>Prochaines étapes</strong> :</p>
<ol style="padding-left:20px;">
<li>Ouvrez votre <strong>Espace Courtier</strong> à <a href="https://capitalnorvex.com/espace-courtier.html" style="color:#9A8554;">capitalnorvex.com/espace-courtier.html</a> — entrez votre courriel et nous vous enverrons un lien de connexion sécurisé.</li>
<li>Signez la convention courtier (lien ci-dessus) — obligatoire avant traitement du premier dossier.</li>
<li>Soumettez votre premier dossier client directement depuis votre Espace, avec votre numéro ${brokerNumber}.</li>
</ol>

<p style="margin-top:24px;">Avec considération,</p>
<p><strong>L'équipe Capital Norvex</strong><br><em style="color:#9A8554;font-size:12.5px;letter-spacing:0.5px;">Programme courtier partenaire</em><br><span style="color:#666;">Capital Norvex Inc.</span></p>
</td></tr>
<tr><td style="background:#0A0A0A;padding:18px;text-align:center;color:#C8B070;font-size:11px;letter-spacing:1px;">
<a href="https://capitalnorvex.com" style="color:#C8B070;text-decoration:none;">capitalnorvex.com</a>
</td></tr>
</table></td></tr></table>  <div style="margin-top:24px;padding-top:14px;border-top:1px solid #cbd5e1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:11px;color:#64748b;line-height:1.5;letter-spacing:.3px;text-align:center">
    <strong style="color:#0f172a;font-size:12px;letter-spacing:1px">CAPITAL NORVEX INC.</strong><br>
    2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
    Téléphone : 1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
  </div>
</body></html>`,
  };
}

function declineEmail({ fullName, reason, lang }) {
  const isEn = lang === "en";
  const reasonBlock = reason
    ? isEn
      ? `<p style="font-size:13px;color:#555;font-style:italic;">${reason}</p>`
      : `<p style="font-size:13px;color:#555;font-style:italic;">${reason}</p>`
    : "";
  if (isEn) {
    return {
      subject: "Capital Norvex Partner Broker Program — Application update",
      html: `<!DOCTYPE html><html><body style="margin:0;padding:0;background:#FBF7EB;font-family:Georgia,serif;color:#0A0A0A;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#FBF7EB;">
<tr><td style="background:#0A0A0A;padding:28px 24px;text-align:center;">
<div style="color:#C8B070;font-family:Georgia,serif;font-size:22px;letter-spacing:3px;">CAPITAL NORVEX</div>
<div style="color:#C8B070;font-style:italic;font-size:12px;letter-spacing:1.5px;margin-top:8px;opacity:0.85;">Structured capital. Measured ambition.</div>
</td></tr>
<tr><td style="height:3px;background:linear-gradient(90deg,transparent 0%,#C8B070 50%,transparent 100%);"></td></tr>
<tr><td style="padding:36px;font-size:14px;line-height:1.7;">
<p>Dear ${fullName},</p>
<p>First and foremost, <strong>thank you sincerely for taking the time to apply</strong> to the Capital Norvex Partner Broker Program. We know that putting together an application like yours requires effort, and we genuinely appreciate it.</p>
<p>After a careful review, we have concluded that <strong>your profile does not, at this stage, meet all the criteria</strong> we apply when admitting brokers to our restricted partner circle. Our program is intentionally limited so that we can offer each partner a dedicated follow-up agent, attentive support, and a compensation grid aligned with our institutional standard.</p>
${reasonBlock}
<p><strong>This does not close any doors.</strong> Our partner circle is reviewed periodically, and we sincerely invite you to submit a new application in the coming months should your situation evolve (deal volume, type of files, experience in private financing). We will be glad to look at it again.</p>
<p>In the meantime, we wish you continued success in your activities, and we remain at your disposal for any question.</p>
<p style="margin-top:24px;">With consideration,</p>
<p><strong>The Capital Norvex Team</strong><br><span style="color:#666;">Capital Norvex Inc.</span><br><a href="mailto:info@capitalnorvex.com" style="color:#9A8554;text-decoration:none;">info@capitalnorvex.com</a></p>
</td></tr>
<tr><td style="background:#0A0A0A;padding:18px;text-align:center;color:#C8B070;font-size:11px;letter-spacing:1px;">
<a href="https://capitalnorvex.com" style="color:#C8B070;text-decoration:none;">capitalnorvex.com</a>
</td></tr>
</table></td></tr></table>  <div style="margin-top:24px;padding-top:14px;border-top:1px solid #cbd5e1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:11px;color:#64748b;line-height:1.5;letter-spacing:.3px;text-align:center">
    <strong style="color:#0f172a;font-size:12px;letter-spacing:1px">CAPITAL NORVEX INC.</strong><br>
    2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
    Téléphone : 1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
  </div>
</body></html>`,
    };
  }
  return {
    subject: "Programme Courtier Capital Norvex — Suivi de votre candidature",
    html: `<!DOCTYPE html><html><body style="margin:0;padding:0;background:#FBF7EB;font-family:Georgia,serif;color:#0A0A0A;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#FBF7EB;">
<tr><td style="background:#0A0A0A;padding:28px 24px;text-align:center;">
<div style="color:#C8B070;font-family:Georgia,serif;font-size:22px;letter-spacing:3px;">CAPITAL NORVEX</div>
<div style="color:#C8B070;font-style:italic;font-size:12px;letter-spacing:1.5px;margin-top:8px;opacity:0.85;">Capital structuré. Ambition maîtrisée.</div>
</td></tr>
<tr><td style="height:3px;background:linear-gradient(90deg,transparent 0%,#C8B070 50%,transparent 100%);"></td></tr>
<tr><td style="padding:36px;font-size:14px;line-height:1.7;">
<p>Bonjour ${fullName},</p>
<p>D'abord et avant tout, <strong>merci sincèrement d'avoir pris le temps de soumettre votre candidature</strong> au Programme Courtier Partenaire de Capital Norvex. Nous savons que constituer un dossier comme le vôtre demande du temps, et nous l'apprécions.</p>
<p>Après un examen attentif, nous concluons que <strong>votre profil ne rencontre pas, à ce stade, l'ensemble des critères</strong> que nous appliquons pour intégrer notre cercle restreint de courtiers partenaires. Notre programme est volontairement limité afin d'offrir à chaque partenaire un agent de suivi dédié, un accompagnement attentif et une grille de rémunération à la hauteur de notre standard institutionnel.</p>
${reasonBlock}
<p><strong>Cela ne ferme aucune porte.</strong> Notre cercle partenaire est revu périodiquement, et nous vous invitons sincèrement à soumettre une nouvelle candidature dans les prochains mois si votre situation évolue (volume d'affaires, type de dossiers, expérience en financement privé). Nous serons heureux de la réexaminer.</p>
<p>En attendant, nous vous souhaitons beaucoup de succès dans la poursuite de vos activités, et nous restons à votre disposition pour toute question.</p>
<p style="margin-top:24px;">Avec considération,</p>
<p><strong>L'équipe Capital Norvex</strong><br><span style="color:#666;">Capital Norvex Inc.</span><br><a href="mailto:info@capitalnorvex.com" style="color:#9A8554;text-decoration:none;">info@capitalnorvex.com</a></p>
</td></tr>
<tr><td style="background:#0A0A0A;padding:18px;text-align:center;color:#C8B070;font-size:11px;letter-spacing:1px;">
<a href="https://capitalnorvex.com" style="color:#C8B070;text-decoration:none;">capitalnorvex.com</a>
</td></tr>
</table></td></tr></table>  <div style="margin-top:24px;padding-top:14px;border-top:1px solid #cbd5e1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:11px;color:#64748b;line-height:1.5;letter-spacing:.3px;text-align:center">
    <strong style="color:#0f172a;font-size:12px;letter-spacing:1px">CAPITAL NORVEX INC.</strong><br>
    2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
    Téléphone : 1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
  </div>
</body></html>`,
  };
}

// Génère un numéro courtier au format CN-AAAA-NNN (séquentiel par année)
async function generateBrokerNumber(projectId, fsToken) {
  const year = new Date().getFullYear();
  const prefix = `CN-${year}-`;
  // Query brokers avec brokerNumber commençant par CN-{year}-
  const queryUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;
  const structuredQuery = {
    from: [{ collectionId: "brokers" }],
    where: {
      compositeFilter: {
        op: "AND",
        filters: [
          {
            fieldFilter: {
              field: { fieldPath: "brokerNumber" },
              op: "GREATER_THAN_OR_EQUAL",
              value: { stringValue: prefix },
            },
          },
          {
            fieldFilter: {
              field: { fieldPath: "brokerNumber" },
              op: "LESS_THAN",
              value: { stringValue: prefix + "999\uffff" },
            },
          },
        ],
      },
    },
    orderBy: [
      { field: { fieldPath: "brokerNumber" }, direction: "DESCENDING" },
    ],
    limit: 1,
  };
  const r = await fetch(queryUrl, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${fsToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ structuredQuery }),
  });
  let nextSeq = 1;
  if (r.ok) {
    const rows = await r.json();
    const docs = (rows || []).filter((row) => row.document);
    if (docs.length > 0) {
      const lastNum =
        docs[0].document.fields?.brokerNumber?.stringValue || "";
      const m = lastNum.match(/CN-\d{4}-(\d+)/);
      if (m) nextSeq = parseInt(m[1], 10) + 1;
    }
  }
  return `${prefix}${String(nextSeq).padStart(3, "0")}`;
}

async function sendGridEmail({ to, subject, html }) {
  const sgKey = process.env.SENDGRID_API_KEY;
  if (!sgKey) return { ok: false, error: "SENDGRID_API_KEY not set" };
  try {
    const r = await fetch("https://api.sendgrid.com/v3/mail/send", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${sgKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        personalizations: [{ to: [{ email: to }] }],
        from: { email: ORGANIZER_EMAIL, name: ORGANIZER_NAME },
        reply_to: { email: ORGANIZER_EMAIL, name: ORGANIZER_NAME },
        subject,
        content: [{ type: "text/html", value: html }],
        tracking_settings: {
          click_tracking: { enable: false, enable_text: false },
          open_tracking: { enable: false },
        },
      }),
    });
    if (r.ok || r.status === 202) return { ok: true };
    const txt = await r.text();
    return { ok: false, error: `SendGrid ${r.status}: ${txt.slice(0, 200)}` };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

// ── Handler ──────────────────────────────────────────────────────────────
export default async function handler(req) {
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

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

  const { applicationId, action, notes = "", reason = "" } = body;
  if (!applicationId) return json({ error: "applicationId required" }, 400);
  if (!["approve", "decline"].includes(action))
    return json({ error: "action must be 'approve' or 'decline'" }, 400);

  try {
    const sa = await loadServiceAccount();
    const projectId = sa.project_id;
    const fsToken = await getFirestoreToken(sa);

    // 1) Lire la candidature
    const appDocUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/brokerApplications/${applicationId}`;
    const appResp = await fetch(appDocUrl, {
      headers: { Authorization: `Bearer ${fsToken}` },
    });
    if (!appResp.ok) {
      return json({ error: "Application not found" }, 404);
    }
    const appDoc = await appResp.json();
    const application = fsDocToObj(appDoc);
    if (!application.email) return json({ error: "Application incomplete" }, 500);

    const newStatus = action === "approve" ? "approved" : "declined";
    const nowIso = new Date().toISOString();

    // 2) Update brokerApplications/{id}
    const appPatchUrl =
      appDocUrl +
      "?updateMask.fieldPaths=status" +
      "&updateMask.fieldPaths=reviewedAt" +
      "&updateMask.fieldPaths=reviewedBy" +
      "&updateMask.fieldPaths=reviewNotes";
    const appPatch = await fetch(appPatchUrl, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${fsToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        fields: {
          status: { stringValue: newStatus },
          reviewedAt: { stringValue: nowIso },
          reviewedBy: { stringValue: "yves@capitalnorvex.com" },
          reviewNotes: { stringValue: notes },
        },
      }),
    });
    if (!appPatch.ok) {
      const txt = await appPatch.text();
      return json(
        { error: "Application update failed: " + txt.slice(0, 200) },
        500
      );
    }

    // 3) Génération numéro courtier si approve
    let brokerNumber = null;
    if (action === "approve") {
      brokerNumber = await generateBrokerNumber(projectId, fsToken);
    }

    // 4) Update brokers/{brokerId} si présent
    if (application.brokerId) {
      const brokerDocUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/brokers/${application.brokerId}`;
      const brokerNewStatus = action === "approve" ? "cold" : "declined";
      const fieldsToUpdate = {
        relationshipStatus: { stringValue: brokerNewStatus },
        approvedAt: {
          stringValue: action === "approve" ? nowIso : "",
        },
        approvedBy: {
          stringValue: action === "approve" ? "yves@capitalnorvex.com" : "",
        },
        lastTouchpoint: { stringValue: nowIso },
      };
      let updateMask =
        "?updateMask.fieldPaths=relationshipStatus" +
        "&updateMask.fieldPaths=approvedAt" +
        "&updateMask.fieldPaths=approvedBy" +
        "&updateMask.fieldPaths=lastTouchpoint";
      if (brokerNumber) {
        fieldsToUpdate.brokerNumber = { stringValue: brokerNumber };
        updateMask += "&updateMask.fieldPaths=brokerNumber";
      }
      await fetch(brokerDocUrl + updateMask, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${fsToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ fields: fieldsToUpdate }),
      }).catch(() => {});
    }

    // 5) Email courtier — pour approve, on génère le token HMAC + lien convention
    const fullName = application.fullName || "";
    const lang = application.lang === "en" ? "en" : "fr";
    let conventionUrl = null;
    if (action === "approve" && application.brokerId && process.env.INTERNAL_SECRET) {
      const convToken = await generateConventionToken(
        application.brokerId,
        process.env.INTERNAL_SECRET,
        30
      );
      const convPage = lang === "en" ? "courtier-convention-en.html" : "courtier-convention.html";
      conventionUrl = `${SITE_URL}/${convPage}?token=${encodeURIComponent(convToken)}`;
    }
    const mail =
      action === "approve"
        ? approvalEmail({ fullName, brokerNumber, lang, conventionUrl })
        : declineEmail({ fullName, reason, lang });
    const sent = await sendGridEmail({
      to: application.email,
      subject: mail.subject,
      html: mail.html,
    });

    return json({
      ok: true,
      applicationId,
      brokerId: application.brokerId || null,
      brokerNumber,
      action,
      newStatus,
      emailSent: sent.ok,
      emailError: sent.ok ? null : sent.error,
    });
  } catch (e) {
    return json({ error: e.message }, 500);
  }
}

export const config = {
  path: "/api/admin-broker-decision",
};
