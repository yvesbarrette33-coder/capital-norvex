// Archive Sent Items via Graph — partagé avec Camille/Sophie/Béatrice.
// Permet à Yves de voir les emails outreach dans son Outlook Sent Items.
import { copyToSentItemsViaGraph } from "./_camille-shared.mjs";

/**
 * POST /.netlify/functions/agent-send-outreach
 * Header: X-Internal-Secret
 * Body JSON: {
 *   collection: 'promoteurTargets' | 'capitalTargets' | 'brokers',
 *   docId: string,
 *   isTest?: boolean,            // si true, envoie à testTo et NE marque PAS comme envoyé
 *   testTo?: string,             // override destinataire (test)
 *   action?: 'preview' | 'send'  // 'preview' renvoie juste le HTML du draft
 * }
 *
 * Lit `pendingDraft` du document Firestore, envoie via Microsoft Graph
 * (fallback SendGrid), met à jour sentAt + audit log.
 */

// Décision Yves 2026-05-04 : From conditionnel selon la collection.
//
// - Brokers / Promoteurs (mass outreach) → info@capitalnorvex.com
//   Signature « L'équipe Capital Norvex ». Replies arrivent à info@ où Sophie
//   les trie en autonomie + escalade Yves seulement sur CC_YVES_CATEGORIES.
// RÈGLE VERROUILLÉE YVES 25 MAI 2026 PM (révision majeure) :
// JAMAIS envoyer un courriel de sollicitation (mass OU intime) depuis yves@capitalnorvex.com.
// Ça a l'air amateur. TOUTES les sollicitations partent de info@capitalnorvex.com.
// Le brand institutionnel passe avant la relation personnelle perçue.
// Citation Yves verrouillée : « Je vais bien te dire de jamais envoyer des
// courriels, courtier, capital, n'importe quoi, par mon courriel à moi.
// On l'avait dit clairement dans nos règles. Ça a l'air amateur. »
const FROM_BY_COLLECTION = {
  capitalTargets:   { user: "info@capitalnorvex.com", name: "Capital Norvex" },
  brokers:          { user: "info@capitalnorvex.com", name: "Capital Norvex" },
  promoteurTargets: { user: "info@capitalnorvex.com", name: "Capital Norvex" },
  advisorTargets:   { user: "info@capitalnorvex.com", name: "Capital Norvex" },
};
const FROM_DEFAULT = { user: "info@capitalnorvex.com", name: "Capital Norvex" };

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// ── Firestore auth ────────────────────────────────────────────────────────
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
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false, ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5", privateKey,
    new TextEncoder().encode(signingInput)
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

// ── Storage token (scope: full_control pour download) ─────────────────────
async function getStorageToken(sa) {
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
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false, ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5", privateKey,
    new TextEncoder().encode(signingInput)
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
  if (!data.access_token) throw new Error("Storage token failed");
  return data.access_token;
}

async function downloadHtmlFromStorage(sa, storagePath) {
  const projectId = sa.project_id;
  const bucket = process.env.FIREBASE_STORAGE_BUCKET || `${projectId}.appspot.com`;
  const token = await getStorageToken(sa);
  const url = `https://storage.googleapis.com/storage/v1/b/${bucket}/o/${encodeURIComponent(storagePath)}?alt=media`;
  const r = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) {
    const txt = await r.text();
    throw new Error(`Storage download failed (${r.status}): ${txt.slice(0, 200)}`);
  }
  return await r.text();
}

// ── Graph token (pour envoi via Microsoft Graph) ──────────────────────────
async function getGraphToken() {
  const tenant = process.env.AZURE_TENANT_ID;
  const clientId = process.env.AZURE_CLIENT_ID;
  const clientSecret = process.env.AZURE_CLIENT_SECRET;
  if (!tenant || !clientId || !clientSecret) {
    throw new Error("AZURE_TENANT_ID/CLIENT_ID/CLIENT_SECRET manquants");
  }
  const r = await fetch(`https://login.microsoftonline.com/${tenant}/oauth2/v2.0/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "client_credentials",
      client_id: clientId,
      client_secret: clientSecret,
      scope: "https://graph.microsoft.com/.default",
    }),
  });
  const data = await r.json();
  if (!data.access_token) throw new Error("Graph token failed: " + JSON.stringify(data));
  return data.access_token;
}

// ── Encodage Firestore ────────────────────────────────────────────────────
function toFsValue(v) {
  if (v === null || v === undefined) return { nullValue: null };
  if (typeof v === "boolean") return { booleanValue: v };
  if (typeof v === "number") {
    return Number.isInteger(v) ? { integerValue: String(v) } : { doubleValue: v };
  }
  if (typeof v === "string") return { stringValue: v };
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

async function getDoc(projectId, fsToken, collection, docId) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collection}/${docId}`;
  const r = await fetch(url, {
    headers: { Authorization: `Bearer ${fsToken}` },
  });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`Firestore GET failed: ${await r.text()}`);
  const doc = await r.json();
  return fsDocToObj(doc);
}

async function patchDoc(projectId, fsToken, collection, docId, fields) {
  const fieldPaths = Object.keys(fields)
    .map((k) => `updateMask.fieldPaths=${encodeURIComponent(k)}`)
    .join("&");
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collection}/${docId}?${fieldPaths}`;
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

async function createAuditLog(projectId, fsToken, log) {
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

// ── Envoi via Microsoft Graph ─────────────────────────────────────────────
async function sendViaGraph({ to, subject, html, fromUser }) {
  const token = await getGraphToken();
  const message = {
    subject,
    body: { contentType: "HTML", content: html },
    toRecipients: [{ emailAddress: { address: to } }],
    from: { emailAddress: { address: fromUser } },
    replyTo: [{ emailAddress: { address: fromUser } }],
    internetMessageHeaders: [
      { name: "X-Capital-Norvex-Type", value: "outreach" },
      { name: "X-Auto-Response-Suppress", value: "All" },
    ],
  };
  const url = `https://graph.microsoft.com/v1.0/users/${fromUser}/sendMail`;
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
  return { ok: false, via: "graph", error: `Graph ${r.status}: ${errText.slice(0, 300)}` };
}

// ── Fallback SendGrid ─────────────────────────────────────────────────────
async function sendViaSendGrid({ to, subject, html, fromUser, fromName }) {
  const sgKey = process.env.SENDGRID_API_KEY;
  if (!sgKey) return { ok: false, via: "sendgrid", error: "SENDGRID_API_KEY missing" };
  const r = await fetch("https://api.sendgrid.com/v3/mail/send", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${sgKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      personalizations: [{ to: [{ email: to }] }],
      from: { email: fromUser, name: fromName },
      subject,
      content: [{ type: "text/html", value: html }],
    }),
  });
  if (r.status >= 200 && r.status < 300) return { ok: true, via: "sendgrid" };
  const errText = await r.text();
  return { ok: false, via: "sendgrid", error: `SendGrid ${r.status}: ${errText.slice(0, 300)}` };
}

// ── Handler ───────────────────────────────────────────────────────────────
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
    return json({ error: "Invalid JSON body" }, 400);
  }

  const ALLOWED_COLLECTIONS = ["promoteurTargets", "capitalTargets", "brokers", "advisorTargets"];
  const collection = body.collection;
  const docId = body.docId;
  const isTest = !!body.isTest;
  const testTo = body.testTo;
  const action = body.action || "send";

  if (!ALLOWED_COLLECTIONS.includes(collection)) {
    return json({ error: "Invalid collection" }, 400);
  }
  if (!docId) return json({ error: "docId required" }, 400);
  if (isTest && (!testTo || !testTo.includes("@"))) {
    return json({ error: "testTo email required when isTest=true" }, 400);
  }

  try {
    const sa = await loadServiceAccount();
    const projectId = sa.project_id;
    const fsToken = await getFirestoreToken(sa);

    const target = await getDoc(projectId, fsToken, collection, docId);
    if (!target) return json({ error: `${collection}/${docId} not found` }, 404);

    const draft = target.pendingDraft;
    if (!draft || !draft.subject || !draft.storagePath) {
      const moduleByCollection = {
        promoteurTargets: "agents.promoteurs.outreach",
        capitalTargets: "agents.capital.outreach",
        brokers: "agents.courtiers.outreach",
        advisorTargets: "agents.advisors.outreach",
      };
      const mod = moduleByCollection[collection] || "agents.promoteurs.outreach";
      return json({
        error: `Aucun draft prêt pour ${collection}/${docId}.`,
        hint: `Pour générer le draft, lance dans le terminal :\n   cd ~/Desktop/capitalnorvex-site && python3 -m ${mod} --queue ${docId}\n\nOu pour TOUS les drafts manquants de cette catégorie :\n   cd ~/Desktop/capitalnorvex-site && python3 -m ${mod} --queue-top 200`,
        collection,
        docId,
        needsDraft: true,
      }, 400);
    }

    // Télécharge le HTML depuis Firebase Storage
    let html;
    try {
      html = await downloadHtmlFromStorage(sa, draft.storagePath);
    } catch (e) {
      return json({ error: "Téléchargement HTML échoué: " + e.message }, 500);
    }

    // Mode preview: renvoie le HTML rendu
    if (action === "preview") {
      return json({
        ok: true,
        preview: {
          html,
          subject: draft.subject,
          to: draft.to,
          toName: draft.toName,
          lang: draft.lang,
        },
      });
    }

    // ── RÈGLE ANTI-HARCÈLEMENT (verrouillée par Yves 2026-05-11) ──
    // Max 2 envois total · 14 jours min entre les 2 · 60 jours avant 3e
    // Flag bypassRateLimit ajouté 2026-05-26 par GO Yves explicite :
    // « à 1-2 jours près demander à Yves, pas appliquer mécaniquement »
    const bypassRateLimit = !!body.bypassRateLimit;
    if (!isTest && !bypassRateLimit) {
      const sentCount = target.sentCount ?? (target.sentAt ? 1 : 0);
      const lastSentAt = target.lastSentAt || target.sentAt;
      if (lastSentAt) {
        const lastSent = new Date(lastSentAt);
        const daysSinceLast = (Date.now() - lastSent.getTime()) / 86400000;
        if (sentCount >= 2 && daysSinceLast < 60) {
          return json({
            error: `Rate-limit : ${sentCount} envois déjà effectués. 3e touch interdit avant ${Math.ceil(60 - daysSinceLast)} jours (cooldown 60j).`,
            rule: "max2_60dcooldown",
            sentCount,
            daysSinceLast: Math.round(daysSinceLast * 10) / 10,
          }, 429);
        }
        if (sentCount === 1 && daysSinceLast < 14) {
          return json({
            error: `Rate-limit : dernier envoi il y a ${daysSinceLast.toFixed(1)}j. Min 14j entre touches (anti-harcèlement).`,
            rule: "min14d_between_touches",
            sentCount,
            daysSinceLast: Math.round(daysSinceLast * 10) / 10,
          }, 429);
        }
      }
    }
    if (bypassRateLimit) {
      console.log(`[outreach] BYPASS rate-limit accepté pour ${collection}/${docId} — décision Yves explicite`);
    }

    // Anti-doublon par email (skipOutreach=true posé par dedupe)
    if (target.skipOutreach && !isTest) {
      return json({ error: `skipOutreach=true (${target.skipReason || 'duplicate'})` }, 409);
    }

    const to = isTest ? testTo : draft.to;
    if (!to || !to.includes("@")) {
      return json({ error: "Destinataire invalide" }, 400);
    }

    // SendGrid PRIMARY pour outreach (Domain Auth vérifié, pas de bounce
    // 550 5.7.708 HRDP M365). Graph en fallback si SendGrid échoue.
    // From conditionnel selon collection (capitalTargets → yves@, autres → info@).
    const fromConfig = FROM_BY_COLLECTION[collection] || FROM_DEFAULT;
    let result = await sendViaSendGrid({
      to,
      subject: draft.subject,
      html,
      fromUser: fromConfig.user,
      fromName: fromConfig.name,
    });
    // 🚫 RÈGLE YVES 25 MAI 2026 PM : NE PAS archiver les outreach mass dans Outlook Sent Items.
    // Citation Yves : « N'envoyez pas ça par mon Outlook. Avant non, c'est tout. »
    // Cohérent avec règle 20 mai : « pas de trace Sent Items pour les vagues outreach ».
    // Le destinataire reçoit le mail via SendGrid (delivery confirmé), c'est suffisant.
    // Traçabilité = SendGrid Activity dashboard + audit_logs Firestore + sentAt patché.
    let sentItemsArchived = false;
    let sentItemsError = "skipped_per_yves_rule_25mai_no_outlook_pollution";
    if (!result.ok) {
      const fallback = await sendViaGraph({
        to,
        subject: draft.subject,
        html,
        fromUser: fromConfig.user,
      });
      if (fallback.ok) {
        result = fallback;
      } else {
        await createAuditLog(projectId, fsToken, {
          timestamp: new Date().toISOString(),
          agent: "agent-send-outreach",
          action: "outreach_failed",
          targetType: collection,
          targetId: docId,
          result: "failure",
          details: { to, isTest, sendGridError: result.error, graphError: fallback.error },
        });
        return json({
          error: "Échec d'envoi (SendGrid + Graph)",
          sendGridError: result.error,
          graphError: fallback.error,
        }, 502);
      }
    }

    // Update Firestore
    const now = new Date().toISOString();
    if (isTest) {
      await patchDoc(projectId, fsToken, collection, docId, {
        lastTestAt: now,
        lastTestTo: to,
        lastTestVia: result.via,
        lastUpdated: now,
      });
    } else {
      await patchDoc(projectId, fsToken, collection, docId, {
        sentAt: now,
        sentTo: to,
        sentSubject: draft.subject,
        sentVia: result.via,
        sentBy: "agent-send-outreach",
        status: "sent",
        pendingDraft: null,
        lastUpdated: now,
      });
    }

    await createAuditLog(projectId, fsToken, {
      timestamp: now,
      agent: "agent-send-outreach",
      action: "outreach_sent",
      targetType: collection,
      targetId: docId,
      result: "success",
      details: {
        to,
        subject: draft.subject,
        via: result.via,
        isTest,
        companyName: target.companyName || target.name || null,
      },
    });

    return json({ ok: true, via: result.via, to, isTest });
  } catch (e) {
    return json({ error: e.message }, 500);
  }
}

export const config = {
  path: "/api/agent-send-outreach",
};
