/**
 * Helpers partagés Camille — NORVEX COUNSEL™
 *
 * - Auth Firestore via service account
 * - HMAC sign/verify pour les liens d'approbation cliquables
 * - Lecture/écriture documents Firestore
 *
 * Convention HMAC :
 *   token = base64url(HMAC-SHA256(`${draftId}.${action}.${expIso}`, CAMILLE_HMAC_SECRET))
 *   URL   = /api/camille-{action}?draft=<id>&exp=<iso>&token=<token>
 *   Expire après 7 jours (laisse Yves partir en weekend sans casser les liens)
 */

import crypto from "node:crypto";

// ── HMAC ────────────────────────────────────────────────────────────────────

const HMAC_SECRET_ENV = "CAMILLE_HMAC_SECRET";
const TOKEN_TTL_DAYS = 7;

export function getHmacSecret() {
  const s = process.env[HMAC_SECRET_ENV];
  if (!s || s.length < 16) {
    throw new Error(
      `${HMAC_SECRET_ENV} env var missing or too short (min 16 chars).`
    );
  }
  return s;
}

function b64url(buf) {
  return Buffer.from(buf)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

export function signApprovalToken(draftId, action, expIso) {
  const secret = getHmacSecret();
  const payload = `${draftId}.${action}.${expIso}`;
  const sig = crypto.createHmac("sha256", secret).update(payload).digest();
  return b64url(sig);
}

export function verifyApprovalToken({ draftId, action, expIso, token }) {
  if (!draftId || !action || !expIso || !token) {
    return { ok: false, error: "Missing fields" };
  }
  // Vérif expiration
  const exp = new Date(expIso);
  if (Number.isNaN(exp.getTime())) {
    return { ok: false, error: "Invalid exp" };
  }
  if (exp.getTime() < Date.now()) {
    return { ok: false, error: "Token expired" };
  }
  // Vérif signature (constant-time)
  const expected = signApprovalToken(draftId, action, expIso);
  const a = Buffer.from(token);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) {
    return { ok: false, error: "Invalid signature" };
  }
  return { ok: true };
}

export function buildApprovalUrl(baseUrl, draftId, action) {
  const expIso = new Date(
    Date.now() + TOKEN_TTL_DAYS * 24 * 3600 * 1000
  ).toISOString();
  const token = signApprovalToken(draftId, action, expIso);
  const u = new URL(`/api/camille-${action}`, baseUrl);
  u.searchParams.set("draft", draftId);
  u.searchParams.set("exp", expIso);
  u.searchParams.set("token", token);
  return u.toString();
}

// ── Firestore (réutilise pattern agent-send-outreach.mjs) ──────────────────

let _saCache = null;
export async function loadServiceAccount() {
  if (_saCache) return _saCache;
  // 1) Première préférence: Netlify Blobs (norah-config / firebase-sa) — pas de limite 4KB AWS Lambda
  try {
    const { getStore } = await import("@netlify/blobs");
    const store = getStore("norah-config");
    const saJson = await store.get("firebase-sa");
    if (saJson) {
      _saCache = JSON.parse(saJson);
      return _saCache;
    }
  } catch (_e) { /* fallback env */ }
  // 2) Fallback: env var FIREBASE_SA_B64 (peut dépasser 4KB)
  let saRaw = null;
  if (process.env.FIREBASE_SA_B64) {
    saRaw = Buffer.from(process.env.FIREBASE_SA_B64, "base64").toString("utf-8");
  } else if (process.env.FIREBASE_SERVICE_ACCOUNT_KEY) {
    saRaw = process.env.FIREBASE_SERVICE_ACCOUNT_KEY;
  }
  if (!saRaw) throw new Error("Firebase SA not found (no blob, no env var)");
  _saCache = JSON.parse(saRaw);
  return _saCache;
}

export async function getFirestoreToken(sa) {
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
  const headerB64 = b64url(JSON.stringify(header));
  const payloadB64 = b64url(JSON.stringify(payload));
  const signingInput = `${headerB64}.${payloadB64}`;

  const pemBody = sa.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\s+/g, "");
  const keyBuf = Buffer.from(pemBody, "base64");

  const signer = crypto.createSign("RSA-SHA256");
  signer.update(signingInput);
  const signature = signer.sign({
    key: crypto.createPrivateKey({ key: keyBuf, format: "der", type: "pkcs8" }),
  });
  const sigB64 = b64url(signature);
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
  if (!data.access_token) {
    throw new Error("Firestore token failed: " + JSON.stringify(data));
  }
  return data.access_token;
}

// ── Encodage Firestore REST ────────────────────────────────────────────────

export function toFsValue(v) {
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

export function fromFsValue(v) {
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

export function fsDocToObj(doc) {
  const out = { _id: doc.name.split("/").pop() };
  const fields = doc.fields || {};
  for (const [k, v] of Object.entries(fields)) out[k] = fromFsValue(v);
  return out;
}

// ── Firestore CRUD ──────────────────────────────────────────────────────────

export async function getDoc(projectId, fsToken, collection, docId) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collection}/${encodeURIComponent(docId)}`;
  const r = await fetch(url, {
    headers: { Authorization: `Bearer ${fsToken}` },
  });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`Firestore GET failed: ${await r.text()}`);
  const doc = await r.json();
  return fsDocToObj(doc);
}

export async function patchDoc(projectId, fsToken, collection, docId, fields) {
  const fieldPaths = Object.keys(fields)
    .map((k) => `updateMask.fieldPaths=${encodeURIComponent(k)}`)
    .join("&");
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collection}/${encodeURIComponent(docId)}?${fieldPaths}`;
  const fsFields = {};
  for (const [k, v] of Object.entries(fields)) fsFields[k] = toFsValue(v);
  const r = await fetch(url, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${fsToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ fields: fsFields }),
  });
  if (!r.ok) throw new Error(`Firestore PATCH failed: ${await r.text()}`);
  return await r.json();
}

export async function listDocs(
  projectId,
  fsToken,
  collection,
  { limit = 50, where = null, orderBy = null } = {}
) {
  // Firestore REST :list paginate. On suit nextPageToken jusqu'à atteindre
  // `limit` ou épuiser la collection. Sans ça, on perd silencieusement des
  // docs (root cause du bug Béatrice/Sophie/Camille count=0).
  const PAGE = Math.min(limit, 300);
  const out = [];
  let pageToken = null;
  let safetyCounter = 0;

  while (out.length < limit && safetyCounter < 20) {
    safetyCounter += 1;
    const params = new URLSearchParams();
    params.set("pageSize", String(PAGE));
    if (orderBy) params.set("orderBy", orderBy);
    if (pageToken) params.set("pageToken", pageToken);
    const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collection}?${params}`;
    const r = await fetch(url, {
      headers: { Authorization: `Bearer ${fsToken}` },
    });
    if (!r.ok) throw new Error(`Firestore LIST failed: ${await r.text()}`);
    const data = await r.json();
    const docs = (data.documents || []).map(fsDocToObj);
    out.push(...docs);
    pageToken = data.nextPageToken || null;
    if (!pageToken) break;
  }

  return out.slice(0, limit);
}

// Vraie query Firestore avec filtre + tri côté serveur (runQuery).
// À utiliser quand on connaît le filtre (ex: status='pending_yves_approval').
// Plus efficace que listDocs+filter côté client.
export async function queryDocs(
  projectId,
  fsToken,
  collection,
  {
    whereField = null,
    whereOp = "EQUAL",
    whereValue = null,
    orderByField = null,
    orderByDirection = "DESCENDING",
    limit = 50,
  } = {}
) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;
  const structuredQuery = { from: [{ collectionId: collection }], limit };
  if (whereField && whereValue !== null && whereValue !== undefined) {
    structuredQuery.where = {
      fieldFilter: {
        field: { fieldPath: whereField },
        op: whereOp,
        value: toFsValue(whereValue),
      },
    };
  }
  if (orderByField) {
    structuredQuery.orderBy = [
      {
        field: { fieldPath: orderByField },
        direction: orderByDirection,
      },
    ];
  }
  const r = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${fsToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ structuredQuery }),
  });
  if (!r.ok) {
    const errText = await r.text();
    // Fallback automatique : si index manquant ou en cours de build, on fait
    // un listDocs paginé + filtre/tri côté client. Plus lent mais robuste.
    if (
      errText.includes("FAILED_PRECONDITION") ||
      errText.includes("requires an index")
    ) {
      const all = await listDocs(projectId, fsToken, collection, {
        limit: 1000,
      });
      let filtered = all;
      if (whereField && whereValue !== null && whereValue !== undefined) {
        filtered = all.filter((d) => d[whereField] === whereValue);
      }
      if (orderByField) {
        filtered.sort((a, b) => {
          const av = a[orderByField] || "";
          const bv = b[orderByField] || "";
          if (orderByDirection === "DESCENDING") {
            return av < bv ? 1 : av > bv ? -1 : 0;
          }
          return av < bv ? -1 : av > bv ? 1 : 0;
        });
      }
      return filtered.slice(0, limit);
    }
    throw new Error(`Firestore runQuery failed: ${errText}`);
  }
  const arr = await r.json();
  const out = [];
  for (const row of arr) {
    if (row.document) out.push(fsDocToObj(row.document));
  }
  return out;
}

export async function createAuditLog(projectId, fsToken, log) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/agentAuditLog`;
  const fields = {};
  const data = { ...log, createdAt: new Date().toISOString() };
  for (const [k, v] of Object.entries(data)) fields[k] = toFsValue(v);
  await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${fsToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ fields }),
  });
}

// ── Microsoft Graph (envoi email) ───────────────────────────────────────────

export async function getGraphToken() {
  const tenant = process.env.AZURE_TENANT_ID;
  const clientId = process.env.AZURE_CLIENT_ID;
  const clientSecret = process.env.AZURE_CLIENT_SECRET;
  if (!tenant || !clientId || !clientSecret) {
    throw new Error("AZURE_TENANT_ID/CLIENT_ID/CLIENT_SECRET manquants");
  }
  const r = await fetch(
    `https://login.microsoftonline.com/${tenant}/oauth2/v2.0/token`,
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "client_credentials",
        client_id: clientId,
        client_secret: clientSecret,
        scope: "https://graph.microsoft.com/.default",
      }),
    }
  );
  const data = await r.json();
  if (!data.access_token) {
    throw new Error("Graph token failed: " + JSON.stringify(data));
  }
  return data.access_token;
}

// Récupère un token Google avec scope Storage (read-only).
// Utilisé pour télécharger les pièces jointes stockées dans Firebase Storage.
export async function getStorageToken(sa) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: sa.client_email,
    sub: sa.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
    scope: "https://www.googleapis.com/auth/devstorage.read_only",
  };
  const b64 = (obj) =>
    Buffer.from(JSON.stringify(obj))
      .toString("base64")
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");
  const signingInput = `${b64(header)}.${b64(payload)}`;
  const crypto = await import("node:crypto");
  const sig = crypto
    .createSign("RSA-SHA256")
    .update(signingInput)
    .sign(sa.private_key);
  const sigB64 = sig
    .toString("base64")
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
  if (!data.access_token) throw new Error("Storage token failed: " + JSON.stringify(data));
  return data.access_token;
}

// Télécharge un fichier Firebase Storage et retourne son contenu en base64.
export async function downloadStorageAsBase64({ bucketName, storagePath, storageToken }) {
  const url = `https://storage.googleapis.com/${bucketName}/${encodeURI(storagePath)}`;
  const r = await fetch(url, {
    headers: { Authorization: `Bearer ${storageToken}` },
  });
  if (!r.ok) {
    const errText = await r.text();
    throw new Error(`Storage download failed (${r.status}): ${errText.slice(0, 200)}`);
  }
  const buf = await r.arrayBuffer();
  return Buffer.from(buf).toString("base64");
}

// Construit la liste de pièces jointes Microsoft Graph à partir des refs
// stockées dans Firestore (drafts.attachments = [{name, storagePath, contentType}]).
export async function buildGraphAttachments({ attachments, sa }) {
  if (!Array.isArray(attachments) || attachments.length === 0) return [];
  const bucketName =
    process.env.FIREBASE_STORAGE_BUCKET || `${sa.project_id}-uploads`;
  const storageToken = await getStorageToken(sa);
  const out = [];
  for (const a of attachments) {
    if (!a || !a.storagePath || !a.name) continue;
    const contentBytes = await downloadStorageAsBase64({
      bucketName,
      storagePath: a.storagePath,
      storageToken,
    });
    out.push({
      "@odata.type": "#microsoft.graph.fileAttachment",
      name: a.name,
      contentType: a.contentType || "application/octet-stream",
      contentBytes,
    });
  }
  return out;
}

// ─── SendGrid (bypass M365 5.7.708 pour destinataires externes) ─────────────
//
// Microsoft 365 a un problème de réputation IP qui fait que certains serveurs
// distants (notamment hôteliers, banques, notaires anciens, corporates qui
// filtrent strict) bouncent avec « 550 5.7.708 Service unavailable. Access
// denied, traffic not accepted from this IP. ». SendGrid bypass ce problème
// (Domain Auth Verified — voir project_email_delivery_sendgrid.md).
//
// Tous les destinataires @capitalnorvex.com → Graph (interne, marche toujours).
// Au moins un destinataire externe → SendGrid prioritaire, Graph fallback.

const INTERNAL_DOMAIN = "capitalnorvex.com";

export function isExternalRecipient(email) {
  if (!email || typeof email !== "string") return false;
  const at = email.lastIndexOf("@");
  if (at === -1) return false;
  return email.slice(at + 1).toLowerCase() !== INTERNAL_DOMAIN;
}

export async function sendViaSendGrid({
  to,
  cc,
  subject,
  html,
  fromUser,
  attachments = [],
  replyTo,
}) {
  const apiKey = process.env.SENDGRID_API_KEY;
  if (!apiKey) {
    return { ok: false, via: "sendgrid", error: "SENDGRID_API_KEY not set" };
  }
  const toList = (Array.isArray(to) ? to : [to]).filter(Boolean);
  const ccList = (Array.isArray(cc) ? cc : []).filter(Boolean);
  const personalization = {
    to: toList.map((addr) => ({ email: addr })),
  };
  if (ccList.length > 0) {
    personalization.cc = ccList.map((addr) => ({ email: addr }));
  }
  const fromNameMap = {
    "yves@capitalnorvex.com": "Yves Barrette",
    "info@capitalnorvex.com": "Capital Norvex",
    "camille@capitalnorvex.com": "Camille — NORVEX COUNSEL",
  };
  const fromName = fromNameMap[fromUser] || "Capital Norvex";

  const payload = {
    personalizations: [personalization],
    from: { email: fromUser, name: fromName },
    subject,
    content: [{ type: "text/html", value: html }],
    reply_to: { email: replyTo || fromUser, name: fromName },
    headers: {
      "X-Capital-Norvex-Type": "camille-counsel",
      "X-Auto-Response-Suppress": "All",
    },
  };

  if (Array.isArray(attachments) && attachments.length > 0) {
    payload.attachments = attachments.map((a) => ({
      content: a.contentBytes || a.content,
      filename: a.name || a.filename,
      type: a.contentType || a.type || "application/octet-stream",
      disposition: "attachment",
    }));
  }

  const resp = await fetch("https://api.sendgrid.com/v3/mail/send", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (resp.ok || resp.status === 202) {
    return { ok: true, via: "sendgrid" };
  }
  const txt = await resp.text();
  return {
    ok: false,
    via: "sendgrid",
    error: `SendGrid ${resp.status}: ${txt.slice(0, 300)}`,
  };
}

// Routeur intelligent : choisit SendGrid ou Graph selon destinataires.
// 🛡️ Blacklist permanente Yves 2026-05-08 — anti-récidive de sollicitation
// vers domaines en litige ou interdits (TCJ, Langlois). Le check Firestore
// `excluded=true` peut être contourné par bug ou agent autonome — ce check
// hardcodé est le dernier rempart avant SendGrid/Graph.
const BLACKLIST_DOMAINS = new Set([
  "groupetcj.ca",          // Therrien Couture Joli-Cœur — LITIGE 2026-05-08
  "therriencouture.com",   // ancien domaine TCJ — LITIGE 2026-05-08
  "langlois.ca",           // Langlois Avocats — relations personnelles Yves 2026-05-08
  "gfaa.ca",               // Groupe FAA Construction — historique projet 2026-05-11
  "habra.ca",              // Habitations Raymond Allard — historique projet 2026-05-11
  "groupefaa.ca",          // site web Groupe FAA — historique projet 2026-05-11
  "groupeevoludev.com",    // Groupe Evoludev — décision Yves 2026-05-12
  "groupeevex.com",        // Groupe EVEX — décision Yves 2026-05-12
  "groupemainland.ca",     // Groupe Mainland — décision Yves 2026-05-12
]);
const BLACKLIST_EMAILS = new Set([
  "claude.tessier@couche-tard.com", // RETRAITE depuis 2023 — boîte désactivée (confirmé Yves 2026-05-12)
  "hwu@pmml.ca",                    // Hao Wu PMML — boîte fermée (mx_connect_refused) — bounces quotidiens à Yves 2026-05-26
]);

export function isBlacklisted(email) {
  if (!email || typeof email !== "string") return false;
  const e = email.trim().toLowerCase();
  if (BLACKLIST_EMAILS.has(e)) return true;
  const domain = e.includes("@") ? e.split("@").pop() : "";
  return BLACKLIST_DOMAINS.has(domain);
}

function blacklistReason(email) {
  if (!email) return "";
  const e = email.trim().toLowerCase();
  if (BLACKLIST_EMAILS.has(e)) return `email_banned:${e}`;
  const domain = e.includes("@") ? e.split("@").pop() : "";
  return BLACKLIST_DOMAINS.has(domain) ? `domain_banned:${domain}` : "";
}

export async function sendEmailSmart({
  to,
  cc = [],
  subject,
  html,
  fromUser,
  attachments = [],
  forceGraph = false,
}) {
  const allRecipients = [
    ...(Array.isArray(to) ? to : [to]),
    ...(Array.isArray(cc) ? cc : []),
  ].filter(Boolean);

  // Garde-fou blacklist — refus immédiat si UN destinataire (To ou CC) est banni
  const blocked = allRecipients.find((addr) => isBlacklisted(addr));
  if (blocked) {
    console.warn(`[sendEmailSmart] ⛔ BLACKLIST refusé : ${blocked} — ${blacklistReason(blocked)}`);
    return {
      ok: false,
      via: "blacklist_blocked",
      error: `Refus d'envoi à ${blocked} — ${blacklistReason(blocked)}`,
    };
  }

  // Communications individuelles clients (Camille → client) : Graph obligatoire
  // (règle 2026-05-28 — saveToSentItems=true, pas de risque filtre spam SendGrid)
  if (forceGraph) {
    return await sendViaGraph({ to, cc, subject, html, fromUser, attachments });
  }

  const hasExternal = allRecipients.some((addr) => isExternalRecipient(addr));

  if (!hasExternal) {
    return await sendViaGraph({ to, cc, subject, html, fromUser, attachments });
  }

  const sgResult = await sendViaSendGrid({
    to,
    cc,
    subject,
    html,
    fromUser,
    attachments,
  });
  if (sgResult.ok) {
    // 📭 Bug fix traçabilité 2026-05-11 : SendGrid n'écrit PAS dans Sent Items
    // Outlook du sender. On copie manuellement via Graph pour qu'Yves ait une
    // trace dans sa boîte. Best-effort synchrone — si Graph échoue, on log
    // l'erreur mais on retourne quand même ok=true (l'envoi à destinataire
    // a réussi via SendGrid).
    const archive = await copyToSentItemsViaGraph({
      to,
      cc,
      subject,
      html,
      fromUser,
      attachments,
    });
    if (!archive.ok) {
      console.warn(
        `[sendEmailSmart] ⚠️ Envoi OK mais copie Sent Items échouée pour ${fromUser}: ${archive.error}`
      );
    }
    return {
      ok: true,
      via: "sendgrid",
      sentItemsArchived: archive.ok,
      sentItemsError: archive.ok ? undefined : archive.error,
    };
  }

  console.warn("SendGrid failed, falling back to Graph:", sgResult.error);
  const graphResult = await sendViaGraph({
    to,
    cc,
    subject,
    html,
    fromUser,
    attachments,
  });
  if (graphResult.ok) {
    // Graph utilise déjà saveToSentItems:true donc pas besoin de re-archiver
    return { ok: true, via: "graph_fallback", sgError: sgResult.error };
  }
  return {
    ok: false,
    via: "both_failed",
    error: `SendGrid: ${sgResult.error} | Graph: ${graphResult.error}`,
  };
}

// ─── Copie dans Sent Items via Graph (traçabilité post-SendGrid) ────────────
// 2026-05-11 : appelée par sendEmailSmart après chaque envoi SendGrid réussi
// pour que le sender (Yves, Camille, etc.) ait une trace dans Sent Items.
// Ne réenvoie PAS l'email — utilise POST direct dans mailFolders/sentitems.

export async function copyToSentItemsViaGraph({
  to,
  cc = [],
  subject,
  html,
  fromUser,
  attachments = [],
}) {
  try {
    const token = await getGraphToken();
    const toRecipients = (Array.isArray(to) ? to : [to])
      .filter(Boolean)
      .map((addr) => ({ emailAddress: { address: addr } }));
    const ccRecipients = (Array.isArray(cc) ? cc : [cc])
      .filter(Boolean)
      .map((addr) => ({ emailAddress: { address: addr } }));
    const message = {
      subject,
      body: { contentType: "HTML", content: html },
      toRecipients,
      ccRecipients,
      from: { emailAddress: { address: fromUser } },
      sender: { emailAddress: { address: fromUser } },
      sentDateTime: new Date().toISOString(),
      isRead: true,
      internetMessageHeaders: [
        { name: "X-Capital-Norvex-Source", value: "sendgrid-archive" },
        { name: "X-Auto-Response-Suppress", value: "All" },
      ],
    };
    if (Array.isArray(attachments) && attachments.length > 0) {
      message.attachments = attachments;
    }
    const url = `https://graph.microsoft.com/v1.0/users/${encodeURIComponent(
      fromUser
    )}/mailFolders/sentitems/messages`;
    const r = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(message),
    });
    if (r.status >= 200 && r.status < 300) {
      return { ok: true };
    }
    const errText = await r.text();
    return {
      ok: false,
      error: `Graph ${r.status}: ${errText.slice(0, 300)}`,
    };
  } catch (e) {
    return { ok: false, error: e.message || String(e) };
  }
}

export async function sendViaGraph({
  to,
  cc,
  subject,
  html,
  fromUser,
  attachments = [],
}) {
  const token = await getGraphToken();
  const toRecipients = (Array.isArray(to) ? to : [to]).map((addr) => ({
    emailAddress: { address: addr },
  }));
  const ccRecipients = (cc || []).map((addr) => ({
    emailAddress: { address: addr },
  }));
  const message = {
    subject,
    body: { contentType: "HTML", content: html },
    toRecipients,
    ccRecipients,
    from: { emailAddress: { address: fromUser } },
    replyTo: [{ emailAddress: { address: fromUser } }],
    internetMessageHeaders: [
      { name: "X-Capital-Norvex-Type", value: "camille-counsel" },
      { name: "X-Auto-Response-Suppress", value: "All" },
    ],
  };
  if (Array.isArray(attachments) && attachments.length > 0) {
    message.attachments = attachments;
  }
  const url = `https://graph.microsoft.com/v1.0/users/${encodeURIComponent(fromUser)}/sendMail`;
  const r = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message, saveToSentItems: true }),
  });
  if (r.status >= 200 && r.status < 300) return { ok: true, via: "graph" };
  const errText = await r.text();
  return {
    ok: false,
    via: "graph",
    error: `Graph ${r.status}: ${errText.slice(0, 300)}`,
  };
}

// ── HTML response helpers ───────────────────────────────────────────────────

export function htmlResponse(title, body, status = 200) {
  const html = `<!DOCTYPE html><html lang="fr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title} — Camille NORVEX COUNSEL™</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #f7f7f9; color: #1a1a1a; max-width: 640px;
         margin: 60px auto; padding: 0 24px; line-height: 1.55; }
  h1 { font-family: "Playfair Display", Georgia, serif; color: #C9A227; font-size: 28px; }
  .card { background: white; border: 1px solid #e5e5e7; border-radius: 12px;
          padding: 32px; margin: 24px 0; box-shadow: 0 2px 8px rgba(0,0,0,.04); }
  .ok    { color: #2d8a3e; }
  .err   { color: #c33; }
  .meta  { color: #777; font-size: 13px; margin-top: 24px; }
  a.btn  { display: inline-block; background: #1a1a1a; color: white;
           padding: 12px 24px; border-radius: 6px; text-decoration: none;
           margin-top: 12px; font-weight: 500; }
  a.btn:hover { background: #C9A227; }
  pre   { background: #f4f4f4; padding: 12px; border-radius: 6px; font-size: 12px;
          white-space: pre-wrap; word-break: break-word; }
</style>
</head><body>
<h1>Camille — NORVEX COUNSEL™</h1>
<div class="card">${body}</div>
<p class="meta">Capital Norvex Inc. · ${new Date().toLocaleString("fr-CA")}</p>
</body></html>`;
  return new Response(html, {
    status,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}

export function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
