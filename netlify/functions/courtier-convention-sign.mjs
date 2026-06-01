/**
 * POST /.netlify/functions/courtier-convention-sign
 * Body: {
 *   token: string,                  // HMAC token reçu dans le courriel
 *   signatureDataUrl: "data:image/png;base64,...",
 *   signerName: string,
 *   accepted: true,
 *   signedAt: ISOstring
 * }
 *
 * Actions :
 *   1. Vérifie le token
 *   2. Charge brokers/{brokerId}, refuse si déjà signé
 *   3. Update brokers/{brokerId} avec signature + relationshipStatus = "active_partner"
 *   4. Envoie courriel de confirmation au courtier
 *   5. Envoie courriel d'alerte à Yves
 */

const ENC = new TextEncoder();
const ORGANIZER_EMAIL = "yves@capitalnorvex.com";
const ORGANIZER_NAME = "Capital Norvex";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

// ── HMAC ─────────────────────────────────────────────────────────────────
function b64urlDecode(s) {
  const pad = s.length % 4 === 0 ? "" : "=".repeat(4 - (s.length % 4));
  return atob(s.replace(/-/g, "+").replace(/_/g, "/") + pad);
}
function b64urlEncodeBytes(bytes) {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
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
async function verifyToken(token, secret) {
  if (!token || !token.includes(".")) return { ok: false, reason: "invalid" };
  const [payloadB64, sigB64] = token.split(".");
  const expected = await hmacSign(secret, payloadB64);
  if (expected !== sigB64) return { ok: false, reason: "invalid" };
  let payload;
  try {
    payload = JSON.parse(b64urlDecode(payloadB64));
  } catch {
    return { ok: false, reason: "invalid" };
  }
  if (!payload.brokerId || !payload.exp) return { ok: false, reason: "invalid" };
  if (Date.now() > payload.exp) return { ok: false, reason: "expired" };
  return { ok: true, payload };
}

// ── Firestore ─────────────────────────────────────────────────────────────
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
  if (v.stringValue !== undefined) return v.stringValue;
  if (v.timestampValue !== undefined) return v.timestampValue;
  return null;
}
function fsDocToObj(doc) {
  const out = {};
  for (const [k, v] of Object.entries(doc.fields || {})) out[k] = fromFsValue(v);
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

// ── SendGrid ─────────────────────────────────────────────────────────────
async function sendGridEmail({ to, subject, html, attachments }) {
  const sgKey = process.env.SENDGRID_API_KEY;
  if (!sgKey) return { ok: false, error: "SENDGRID_API_KEY not set" };
  try {
    const body = {
      personalizations: [{ to: [{ email: to }] }],
      from: { email: ORGANIZER_EMAIL, name: ORGANIZER_NAME },
      reply_to: { email: ORGANIZER_EMAIL, name: ORGANIZER_NAME },
      subject,
      content: [{ type: "text/html", value: html }],
      tracking_settings: {
        click_tracking: { enable: false, enable_text: false },
        open_tracking: { enable: false },
      },
    };
    if (attachments && attachments.length > 0) body.attachments = attachments;
    const r = await fetch("https://api.sendgrid.com/v3/mail/send", {
      method: "POST",
      headers: { Authorization: `Bearer ${sgKey}`, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (r.ok || r.status === 202) return { ok: true };
    const txt = await r.text();
    return { ok: false, error: `SendGrid ${r.status}: ${txt.slice(0, 200)}` };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

// ── Email templates ──────────────────────────────────────────────────────
function brokerConfirmEmail({ name, brokerNumber }) {
  return {
    subject: `✅ Convention de partenariat signée — Bienvenue chez Capital Norvex`,
    html: `<!DOCTYPE html><html><body style="margin:0;padding:0;background:#FBF7EB;font-family:Georgia,serif;color:#0A0A0A;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#FBF7EB;">
<tr><td style="background:#0A0A0A;padding:28px 24px;text-align:center;">
<div style="color:#C8B070;font-family:Georgia,serif;font-size:22px;letter-spacing:3px;">CAPITAL NORVEX</div>
<div style="color:#C8B070;font-style:italic;font-size:12px;letter-spacing:1.5px;margin-top:8px;opacity:0.85;">Capital structuré. Ambition maîtrisée.</div>
</td></tr>
<tr><td style="height:3px;background:linear-gradient(90deg,transparent 0%,#C8B070 50%,transparent 100%);"></td></tr>
<tr><td style="padding:36px;font-size:14px;line-height:1.7;">
<p>Bonjour ${name},</p>
<p>Nous confirmons la <strong>réception de votre signature électronique</strong> sur la Convention de partenariat courtier hypothécaire de Capital Norvex Inc.</p>

<div style="margin:22px 0;padding:22px;background:#0A0A0A;border:1px solid #C8B070;text-align:center;">
<div style="font-size:10px;letter-spacing:3px;color:#C8B070;text-transform:uppercase;margin-bottom:8px;">Numéro de courtier partenaire</div>
<div style="font-family:Georgia,serif;font-size:26px;color:#C8B070;letter-spacing:3px;font-weight:bold;">${brokerNumber}</div>
</div>

<p>Vous êtes désormais officiellement <strong>Courtier Partenaire — Capital Norvex</strong>. Voici les prochaines étapes&nbsp;:</p>
<ol style="padding-left:20px;">
<li>Votre <strong>agent de suivi dédié</strong> vous contactera sous peu pour se présenter.</li>
<li>Vous pouvez dès maintenant nous référer des dossiers à <a href="https://capitalnorvex.com" style="color:#9A8554;">capitalnorvex.com</a> en utilisant votre numéro <strong>${brokerNumber}</strong>.</li>
<li>Une copie complète de la convention signée est conservée à des fins de preuve&nbsp;; vous pouvez nous la redemander à tout moment.</li>
</ol>

<p style="margin-top:22px;">Bienvenue dans le cercle restreint des courtiers partenaires Capital Norvex.</p>
<p>Avec considération,</p>
<p><strong>Yves Barrette</strong><br><em style="color:#666;">Directeur-fondateur</em><br><span style="color:#666;">Capital Norvex Inc.</span></p>
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

function ownerNotifyEmail({ name, agency, brokerNumber, signedFromIp, signedAt }) {
  return {
    subject: `🟢 Nouveau partenaire actif : ${name} (${brokerNumber})`,
    html: `<!DOCTYPE html><html><body style="font-family:-apple-system,sans-serif;color:#0A0A0A;font-size:14px;line-height:1.6;padding:24px;">
<h2 style="color:#9A8554;margin:0 0 12px 0;">Convention courtier signée</h2>
<table style="border-collapse:collapse;width:100%;max-width:540px;">
<tr><td style="padding:6px 12px;background:#FBF7EB;width:40%;"><strong>Nom</strong></td><td style="padding:6px 12px;background:#fff;">${name}</td></tr>
<tr><td style="padding:6px 12px;background:#FBF7EB;"><strong>Cabinet</strong></td><td style="padding:6px 12px;background:#fff;">${agency || "—"}</td></tr>
<tr><td style="padding:6px 12px;background:#FBF7EB;"><strong>N° courtier</strong></td><td style="padding:6px 12px;background:#fff;"><strong>${brokerNumber}</strong></td></tr>
<tr><td style="padding:6px 12px;background:#FBF7EB;"><strong>Signé le</strong></td><td style="padding:6px 12px;background:#fff;">${signedAt}</td></tr>
<tr><td style="padding:6px 12px;background:#FBF7EB;"><strong>IP signature</strong></td><td style="padding:6px 12px;background:#fff;">${signedFromIp || "—"}</td></tr>
</table>
<p style="margin-top:20px;">Statut Firestore mis à jour : <code>relationshipStatus = "active_partner"</code>.</p>
<p>Pensez à attribuer un agent de suivi dédié.</p>
  <div style="margin-top:24px;padding-top:14px;border-top:1px solid #cbd5e1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:11px;color:#64748b;line-height:1.5;letter-spacing:.3px;text-align:center">
    <strong style="color:#0f172a;font-size:12px;letter-spacing:1px">CAPITAL NORVEX INC.</strong><br>
    2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
    Téléphone : 1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
  </div>
</body></html>`,
  };
}

// ── Handler ──────────────────────────────────────────────────────────────
export default async function handler(req) {
  if (req.method !== "POST") return json({ ok: false, error: "Method not allowed" }, 405);

  const secret = process.env.INTERNAL_SECRET;
  if (!secret) return json({ ok: false, error: "server_misconfigured" }, 500);

  let body;
  try {
    body = await req.json();
  } catch {
    return json({ ok: false, error: "Invalid JSON" }, 400);
  }

  const { token, signatureDataUrl, signerName, accepted, signedAt } = body;
  if (!token || !signatureDataUrl || !signerName || !accepted) {
    return json({ ok: false, error: "missing_fields" }, 400);
  }
  if (!signatureDataUrl.startsWith("data:image/png;base64,")) {
    return json({ ok: false, error: "bad_signature" }, 400);
  }
  if (signatureDataUrl.length > 800_000) {
    return json({ ok: false, error: "signature_too_large" }, 400);
  }

  const verified = await verifyToken(token, secret);
  if (!verified.ok) return json({ ok: false, error: verified.reason }, 401);

  // IP / UA pour audit
  const ip =
    req.headers.get("x-nf-client-connection-ip") ||
    req.headers.get("x-forwarded-for") ||
    "";
  const ua = req.headers.get("user-agent") || "";
  const nowIso = new Date().toISOString();
  const signedAtIso = signedAt || nowIso;

  try {
    const sa = await loadServiceAccount();
    const projectId = sa.project_id;
    const fsToken = await getFirestoreToken(sa);

    const brokerId = verified.payload.brokerId;
    const docUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/brokers/${brokerId}`;

    // 1) Lire le broker
    const r = await fetch(docUrl, { headers: { Authorization: `Bearer ${fsToken}` } });
    if (!r.ok) return json({ ok: false, error: "broker_not_found" }, 404);
    const broker = fsDocToObj(await r.json());

    if (broker.contractSignedAt) {
      return json({ ok: false, error: "already_signed" }, 409);
    }

    // 2) Patch broker — signature + statut active_partner
    const patchUrl =
      docUrl +
      "?updateMask.fieldPaths=relationshipStatus" +
      "&updateMask.fieldPaths=contractSignedAt" +
      "&updateMask.fieldPaths=contractSignerName" +
      "&updateMask.fieldPaths=contractSignedFromIp" +
      "&updateMask.fieldPaths=contractSignedUserAgent" +
      "&updateMask.fieldPaths=contractSignatureDataUrl" +
      "&updateMask.fieldPaths=lastTouchpoint";
    const patchResp = await fetch(patchUrl, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${fsToken}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        fields: {
          relationshipStatus: { stringValue: "active_partner" },
          contractSignedAt: { stringValue: signedAtIso },
          contractSignerName: { stringValue: signerName },
          contractSignedFromIp: { stringValue: ip },
          contractSignedUserAgent: { stringValue: ua },
          contractSignatureDataUrl: { stringValue: signatureDataUrl },
          lastTouchpoint: { stringValue: nowIso },
        },
      }),
    });
    if (!patchResp.ok) {
      const txt = await patchResp.text();
      return json({ ok: false, error: "update_failed: " + txt.slice(0, 200) }, 500);
    }

    // 3) Courriels (best effort, ne bloquent pas)
    const name = broker.name || broker.fullName || signerName;
    const brokerNumber = broker.brokerNumber || "—";
    const email = broker.email || "";
    const agency = broker.agency || "";

    if (email) {
      const c = brokerConfirmEmail({ name, brokerNumber });
      await sendGridEmail({ to: email, subject: c.subject, html: c.html }).catch(() => {});
    }
    const owner = ownerNotifyEmail({
      name,
      agency,
      brokerNumber,
      signedFromIp: ip,
      signedAt: signedAtIso,
    });
    await sendGridEmail({
      to: ORGANIZER_EMAIL,
      subject: owner.subject,
      html: owner.html,
    }).catch(() => {});

    return json({ ok: true, brokerNumber });
  } catch (e) {
    return json({ ok: false, error: e.message }, 500);
  }
}

export const config = {
  path: "/api/courtier-convention-sign",
};
