/**
 * _norah-shared.mjs
 * Helpers réutilisables par toutes les fonctions Norah V2.
 *
 * - Auth: vérification du header X-Internal-Secret (appelé par ElevenLabs/Twilio webhooks)
 * - Firestore: signature JWT + accès REST
 * - Twilio Verify: envoi/validation de codes 2FA
 * - Réponses JSON normalisées
 *
 * Convention: les fichiers commençant par _ ne sont pas exposés comme endpoints
 * Netlify (ils servent uniquement de modules importés).
 */

// ─────────────────────────────────────────────────────────────────────────────
// CONSTANTES
// ─────────────────────────────────────────────────────────────────────────────

export const TWILIO_VERIFY_SERVICE_SID =
  process.env.TWILIO_VERIFY_SERVICE_SID || "VA03c9809e3c37897b89a0309c0d08f187";
export const TWILIO_FROM_NUMBER = "+14385337738"; // Norah
export const YVES_VIP_PHONE = "+15145312705";
export const YVES_EMAIL = "yves@capitalnorvex.com";
export const SENDGRID_FROM_EMAIL = "info@capitalnorvex.com";

// Signature/coordonnées officielles Capital Norvex Inc. — réutilisable dans
// tous les emails et documents générés.
export const CAPITAL_NORVEX_SIGNATURE_HTML = `
  <div style="margin-top:24px;padding-top:16px;border-top:1px solid #cbd5e1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:11px;color:#64748b;line-height:1.5;letter-spacing:.3px">
    <strong style="color:#0f172a;font-size:12px;letter-spacing:1px">CAPITAL NORVEX INC.</strong><br>
    2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
    Téléphone : <a href="tel:+14385337738" style="color:#b8975a;text-decoration:none">1-(438)-533-PRET (7738)</a><br>
    Courriel : <a href="mailto:info@capitalnorvex.com" style="color:#b8975a;text-decoration:none">info@capitalnorvex.com</a> ·
    <a href="https://capitalnorvex.com" style="color:#b8975a;text-decoration:none">capitalnorvex.com</a>
  </div>
`;

export const CAPITAL_NORVEX_SIGNATURE_TEXT = `
—
CAPITAL NORVEX INC.
2705-1000 André-Prévost
Île-des-Sœurs (Verdun), Montréal, Québec  H3E 0G2
Téléphone : 1-(438)-533-PRET (7738)
info@capitalnorvex.com · capitalnorvex.com
`;

// ─────────────────────────────────────────────────────────────────────────────
// RÉPONSES HTTP
// ─────────────────────────────────────────────────────────────────────────────

export function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function unauthorized(reason = "Unauthorized") {
  return json({ error: reason }, 401);
}

export function badRequest(reason) {
  return json({ error: reason }, 400);
}

export function serverError(reason) {
  return json({ error: reason }, 500);
}

// ─────────────────────────────────────────────────────────────────────────────
// AUTH — vérifie le header X-Internal-Secret
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Renvoie true si la requête est autorisée (secret valide).
 * Tous les endpoints Norah (sauf webhooks Twilio publics) doivent l'utiliser.
 */
export function checkInternalSecret(req) {
  const secret = req.headers.get("x-internal-secret");
  return Boolean(
    process.env.INTERNAL_SECRET && secret === process.env.INTERNAL_SECRET
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// FIRESTORE — token + queries REST
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Récupère le service account Firebase.
 * Stratégie:
 *   1. Lit depuis Netlify Blobs (norah-config / firebase-sa) — recommandé
 *   2. Fallback: lit depuis l'env var FIREBASE_SA_B64
 * Cache en mémoire pour éviter les lectures répétées.
 */
let _saCache = null;
async function getServiceAccount() {
  if (_saCache) return _saCache;

  // 1) Tentative via Netlify Blobs
  try {
    const { getStore } = await import("@netlify/blobs");
    const store = getStore("norah-config");
    const saJson = await store.get("firebase-sa");
    if (saJson) {
      _saCache = JSON.parse(saJson);
      return _saCache;
    }
  } catch (_e) {
    // Continue vers fallback
  }

  // 2) Fallback: env var
  const b64 = process.env.FIREBASE_SA_B64;
  if (!b64) throw new Error("FIREBASE_SA_B64 not set and no blob found");
  const saJson = atob(b64);
  _saCache = JSON.parse(saJson);
  return _saCache;
}

/**
 * Génère un access token Firestore via JWT signé avec le service account.
 * Réutilise le même pattern que get-new-dossiers.mjs / get-track-alerts.mjs.
 */
export async function getFirestoreToken() {
  const serviceAccount = await getServiceAccount();

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

  const b64url = (obj) =>
    btoa(JSON.stringify(obj))
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");

  const signingInput = `${b64url(header)}.${b64url(payload)}`;

  const pemBody = serviceAccount.private_key
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

  const tokenResp = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: jwt,
    }),
  });
  const tokenData = await tokenResp.json();
  if (!tokenData.access_token) {
    throw new Error("Firestore auth failed: " + JSON.stringify(tokenData));
  }

  return { accessToken: tokenData.access_token, projectId: serviceAccount.project_id };
}

/**
 * Convertit un document Firestore REST (avec fields typés) en objet JS plat.
 * Ex: { name: "...", fields: { foo: { stringValue: "bar" } } } → { id: ..., foo: "bar" }
 */
export function firestoreDocToObject(doc) {
  if (!doc || !doc.fields) return null;
  const id = doc.name?.split("/").pop();
  const obj = { id };

  for (const [key, val] of Object.entries(doc.fields)) {
    obj[key] = firestoreValueToJS(val);
  }
  return obj;
}

function firestoreValueToJS(val) {
  if (val == null) return null;
  if ("stringValue" in val) return val.stringValue;
  if ("integerValue" in val) return parseInt(val.integerValue, 10);
  if ("doubleValue" in val) return val.doubleValue;
  if ("booleanValue" in val) return val.booleanValue;
  if ("timestampValue" in val) return val.timestampValue;
  if ("nullValue" in val) return null;
  if ("mapValue" in val) {
    const out = {};
    for (const [k, v] of Object.entries(val.mapValue.fields || {})) {
      out[k] = firestoreValueToJS(v);
    }
    return out;
  }
  if ("arrayValue" in val) {
    return (val.arrayValue.values || []).map(firestoreValueToJS);
  }
  return null;
}

/**
 * Convertit un objet JS en valeurs typées Firestore.
 */
export function jsToFirestoreFields(obj) {
  const fields = {};
  for (const [key, val] of Object.entries(obj)) {
    fields[key] = jsToFirestoreValue(val);
  }
  return fields;
}

function jsToFirestoreValue(val) {
  if (val === null || val === undefined) return { nullValue: null };
  if (typeof val === "string") return { stringValue: val };
  if (typeof val === "boolean") return { booleanValue: val };
  if (typeof val === "number") {
    return Number.isInteger(val)
      ? { integerValue: String(val) }
      : { doubleValue: val };
  }
  if (val instanceof Date) return { timestampValue: val.toISOString() };
  if (Array.isArray(val)) {
    return { arrayValue: { values: val.map(jsToFirestoreValue) } };
  }
  if (typeof val === "object") {
    const fields = {};
    for (const [k, v] of Object.entries(val)) {
      fields[k] = jsToFirestoreValue(v);
    }
    return { mapValue: { fields } };
  }
  return { nullValue: null };
}

/**
 * Cherche un document par champ dans une collection.
 * Retourne le premier match ou null.
 */
export async function firestoreFindOne(collection, fieldPath, value) {
  const { accessToken, projectId } = await getFirestoreToken();
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;

  const query = {
    structuredQuery: {
      from: [{ collectionId: collection }],
      where: {
        fieldFilter: {
          field: { fieldPath },
          op: "EQUAL",
          value: jsToFirestoreValue(value),
        },
      },
      limit: 1,
    },
  };

  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(query),
  });

  const results = await resp.json();
  if (!Array.isArray(results)) return null;
  for (const r of results) {
    if (r.document) return firestoreDocToObject(r.document);
  }
  return null;
}

/**
 * Lit un document par son ID dans une collection.
 */
export async function firestoreGet(collection, docId) {
  const { accessToken, projectId } = await getFirestoreToken();
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collection}/${docId}`;

  const resp = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (resp.status === 404) return null;
  if (!resp.ok) throw new Error(`Firestore get failed: ${resp.status}`);
  const doc = await resp.json();
  return firestoreDocToObject(doc);
}

/**
 * Liste les documents d'une collection avec filtre optionnel sur un champ
 * de timestamp (created_at, ended_at, etc.).
 *
 * @param {string} collection - Nom de la collection Firestore
 * @param {object} opts - { sinceField?, sinceDate?, limit?, orderBy? }
 */
export async function firestoreList(collection, opts = {}) {
  const { accessToken, projectId } = await getFirestoreToken();
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;

  const structured = {
    from: [{ collectionId: collection }],
    limit: opts.limit || 500,
  };

  if (opts.sinceField && opts.sinceDate) {
    structured.where = {
      fieldFilter: {
        field: { fieldPath: opts.sinceField },
        op: "GREATER_THAN_OR_EQUAL",
        value: { timestampValue: new Date(opts.sinceDate).toISOString() },
      },
    };
  }

  if (opts.orderBy) {
    structured.orderBy = [{ field: { fieldPath: opts.orderBy }, direction: "DESCENDING" }];
  }

  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ structuredQuery: structured }),
  });

  const results = await resp.json();
  if (!Array.isArray(results)) return [];
  const docs = [];
  for (const r of results) {
    if (r.document) docs.push(firestoreDocToObject(r.document));
  }
  return docs;
}

/**
 * Crée un document dans une collection (auto-id) ou avec un ID fourni.
 */
export async function firestoreCreate(collection, data, docId = null) {
  const { accessToken, projectId } = await getFirestoreToken();
  const base = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collection}`;
  const url = docId ? `${base}/${docId}` : base;
  const method = docId ? "PATCH" : "POST";

  const body = JSON.stringify({ fields: jsToFirestoreFields(data) });

  const resp = await fetch(url, {
    method,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body,
  });

  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(`Firestore create failed: ${resp.status} ${txt}`);
  }
  const doc = await resp.json();
  return firestoreDocToObject(doc);
}

// ─────────────────────────────────────────────────────────────────────────────
// TWILIO VERIFY — 2FA SMS
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Récupère les credentials Twilio.
 * Stratégie:
 *   1. Lit depuis Netlify Blobs (norah-config / twilio)
 *   2. Fallback: env vars TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN
 */
let _twilioCache = null;
async function getTwilioCreds() {
  if (_twilioCache) return _twilioCache;

  try {
    const { getStore } = await import("@netlify/blobs");
    const store = getStore("norah-config");
    const raw = await store.get("twilio");
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed.account_sid && parsed.auth_token) {
        _twilioCache = parsed;
        return _twilioCache;
      }
    }
  } catch (_e) {
    // fallback
  }

  const sid = process.env.TWILIO_ACCOUNT_SID;
  const token = process.env.TWILIO_AUTH_TOKEN;
  if (!sid || !token) {
    throw new Error("Twilio credentials not found (no blob, no env)");
  }
  _twilioCache = { account_sid: sid, auth_token: token };
  return _twilioCache;
}

/**
 * Construit le header Authorization Basic Twilio.
 */
async function twilioAuthHeader() {
  const { account_sid, auth_token } = await getTwilioCreds();
  return "Basic " + btoa(`${account_sid}:${auth_token}`);
}

/**
 * Envoie un code 2FA par SMS via Twilio Verify.
 * Twilio gère: génération code, expiration (10 min par défaut), anti-replay.
 *
 * @param {string} phone - Numéro E.164 (ex: +15145551234)
 * @returns {Promise<{success:boolean, status?:string, error?:string}>}
 */
export async function twilioSendVerification(phone) {
  const url = `https://verify.twilio.com/v2/Services/${TWILIO_VERIFY_SERVICE_SID}/Verifications`;

  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: await twilioAuthHeader(),
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      To: phone,
      Channel: "sms",
      Locale: "fr",
    }),
  });

  const data = await resp.json();
  if (!resp.ok) {
    return { success: false, error: data.message || "Twilio Verify failed" };
  }
  return { success: true, status: data.status };
}

/**
 * Valide un code 2FA reçu de l'appelant.
 *
 * @param {string} phone - Numéro E.164
 * @param {string} code - Code 4 chiffres entré par l'appelant
 * @returns {Promise<{approved:boolean, status?:string, error?:string}>}
 */
export async function twilioCheckVerification(phone, code) {
  const url = `https://verify.twilio.com/v2/Services/${TWILIO_VERIFY_SERVICE_SID}/VerificationCheck`;

  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: await twilioAuthHeader(),
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      To: phone,
      Code: code,
    }),
  });

  const data = await resp.json();
  if (!resp.ok) {
    return { approved: false, error: data.message || "Twilio check failed" };
  }
  return {
    approved: data.status === "approved",
    status: data.status,
  };
}

/**
 * Envoie un SMS direct (hors Verify) — pour alertes VIP, lien candidature, etc.
 *
 * @param {string} to - Destinataire E.164
 * @param {string} body - Texte du SMS
 */
export async function twilioSendSMS(to, body) {
  const { account_sid: sid } = await getTwilioCreds();
  const url = `https://api.twilio.com/2010-04-01/Accounts/${sid}/Messages.json`;

  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: await twilioAuthHeader(),
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      To: to,
      From: TWILIO_FROM_NUMBER,
      Body: body,
    }),
  });

  const data = await resp.json();
  if (!resp.ok) {
    return { success: false, error: data.message || "Twilio SMS failed" };
  }
  return { success: true, sid: data.sid };
}

// ─────────────────────────────────────────────────────────────────────────────
// SESSIONS NORAH — état "vérifié" après 2FA réussi
// ─────────────────────────────────────────────────────────────────────────────

export const SESSION_TTL_MINUTES = 30;

/**
 * Crée une session valide après 2FA réussi.
 * L'ID du document est le numéro de téléphone normalisé (un caller = une session).
 */
export async function createNorahSession({ phone, role, dossierId = null, displayName = null }) {
  const expiresAt = new Date(Date.now() + SESSION_TTL_MINUTES * 60 * 1000).toISOString();
  // Firestore n'accepte pas le `+` dans les IDs, on l'enlève
  const docId = phone.replace(/^\+/, "p");
  return firestoreCreate(
    "norahSessions",
    {
      phone,
      role,
      dossier_id: dossierId,
      display_name: displayName,
      verified_at: new Date(),
      expires_at: expiresAt,
    },
    docId
  );
}

/**
 * Récupère une session valide (non-expirée) pour un numéro.
 * Retourne null si aucune session active.
 */
export async function getValidNorahSession(phone) {
  if (!phone) return null;
  const docId = phone.replace(/^\+/, "p");
  const session = await firestoreGet("norahSessions", docId);
  if (!session) return null;
  const expiresAt = new Date(session.expires_at);
  if (Date.now() > expiresAt.getTime()) return null;
  return session;
}

/**
 * Vérifie qu'une requête a une session valide pour un numéro donné.
 * Retourne { valid: true, session } ou { valid: false, reason }.
 *
 * Optionnel: rolesAllowed pour restreindre à certains rôles.
 */
export async function requireValidSession(phone, rolesAllowed = null) {
  const session = await getValidNorahSession(phone);
  if (!session) return { valid: false, reason: "session_expired_or_missing" };
  if (rolesAllowed && !rolesAllowed.includes(session.role)) {
    return { valid: false, reason: "role_not_allowed" };
  }
  return { valid: true, session };
}

// ─────────────────────────────────────────────────────────────────────────────
// AUTORISATION D'ACCÈS À UN DOSSIER selon le rôle
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Vérifie qu'une session a le droit de voir un dossier donné.
 * Retourne true/false selon le rôle et les liens dossier ↔ caller.
 */
export function canCallerAccessDossier(session, dossier) {
  if (!session || !dossier) return false;
  if (session.role === "yves") return true;
  const phone = session.phone;

  if (session.role === "client") {
    return (
      dossier.tel === phone ||
      dossier.client_phone === phone ||
      dossier.phone === phone
    );
  }
  if (session.role === "courtier") {
    return (
      dossier.courtier_phone === phone ||
      dossier.broker_phone === phone
    );
  }
  if (session.role === "partenaire") {
    const partners =
      dossier.partenaires_coprêteurs || dossier.partners || [];
    if (Array.isArray(partners)) {
      return partners.some((p) =>
        typeof p === "string" ? p === phone : p && p.phone === phone
      );
    }
  }
  return false;
}

// ─────────────────────────────────────────────────────────────────────────────
// SENDGRID — envoi d'emails
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Envoie un email via SendGrid API.
 * @param {object} params - { to, subject, html, text, replyTo? }
 */
export async function sendgridSend({ to, subject, html, text, replyTo }) {
  const apiKey = process.env.SENDGRID_API_KEY;
  if (!apiKey) throw new Error("SENDGRID_API_KEY not set");

  const personalization = {
    to: Array.isArray(to)
      ? to.map((t) => (typeof t === "string" ? { email: t } : t))
      : [{ email: to }],
  };

  const payload = {
    personalizations: [personalization],
    from: { email: SENDGRID_FROM_EMAIL, name: "Capital Norvex" },
    subject,
    content: [
      ...(text ? [{ type: "text/plain", value: text }] : []),
      ...(html ? [{ type: "text/html", value: html }] : []),
    ],
  };
  if (replyTo) payload.reply_to = { email: replyTo };

  const resp = await fetch("https://api.sendgrid.com/v3/mail/send", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!resp.ok && resp.status !== 202) {
    const txt = await resp.text();
    throw new Error(`SendGrid send failed: ${resp.status} ${txt}`);
  }

  // 📭 Archive Sent Items pour traçabilité Outlook Yves (best-effort, non-bloquant).
  try {
    const { copyToSentItemsViaGraph } = await import("./_camille-shared.mjs");
    await copyToSentItemsViaGraph({
      to,
      subject,
      html: html || (text ? `<pre>${text}</pre>` : ""),
      fromUser: SENDGRID_FROM_EMAIL,
    });
  } catch (e) {
    console.warn("[norah-sendgridSend] Sent Items archive failed (non-fatal):", e.message);
  }

  return { success: true };
}

// ─────────────────────────────────────────────────────────────────────────────
// NORMALISATION DE NUMÉROS DE TÉLÉPHONE
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Normalise un numéro NA en format E.164 (+1XXXXXXXXXX).
 * Accepte: 5145551234, 514-555-1234, (514) 555-1234, +15145551234, etc.
 */
export function normalizePhone(raw) {
  if (!raw) return null;
  const digits = String(raw).replace(/\D/g, "");
  if (digits.length === 10) return `+1${digits}`;
  if (digits.length === 11 && digits.startsWith("1")) return `+${digits}`;
  if (digits.length === 11) return `+${digits}`;
  return null;
}
