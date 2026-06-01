/**
 * POST /.netlify/functions/propose-rdv
 * Header: X-Internal-Secret
 * Body: { dossierId }
 *
 * 1. Lit le dossier Firestore (email + nom client + langue)
 * 2. Interroge Graph free/busy pour yves@capitalnorvex.com (14 prochains jours)
 * 3. Sélectionne les 2 premiers créneaux libres mar/mer/jeu, 7:00–15:30,
 *    sans chevaucher 12:30–13:00, durée 45 min
 * 4. Génère 2 tokens HMAC signés (payload = dossierId + slot + exp)
 * 5. Envoie un email au client avec 2 boutons → /confirm-rdv?token=…
 * 6. Met à jour le dossier: rdv_status='proposed', rdv_proposed_slots, rdv_proposed_at
 */

const ORGANIZER_EMAIL = "yves@capitalnorvex.com";
const TZ = "America/Toronto";
const SLOT_MINUTES = 45;
const LOOKAHEAD_DAYS = 14;
const TOKEN_TTL_DAYS = 7;
const SITE_URL = process.env.SITE_URL || "https://capitalnorvex.com";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// ── Firestore JWT (RS256) ─────────────────────────────────────────────────
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
    btoa(JSON.stringify(obj)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
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
  if (!data.access_token) throw new Error("Firestore token failed: " + JSON.stringify(data));
  return data.access_token;
}

// ── Graph token (client_credentials) ──────────────────────────────────────
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

// ── HMAC token signé ──────────────────────────────────────────────────────
async function signToken(payload, secret) {
  const data = btoa(JSON.stringify(payload))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false, ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(data));
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return `${data}.${sigB64}`;
}

// ── Génération des créneaux candidats (mar/mer/jeu, 7:00–15:30) ───────────
// Renvoie ISO UTC strings. On utilise l'offset DST de Toronto pour la date donnée.
function torontoOffsetMinutes(dateUtc) {
  // EDT = UTC-4 (mars→nov), EST = UTC-5 (nov→mars). Approche simple: dérive via Intl.
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: TZ, timeZoneName: "shortOffset",
  });
  const parts = fmt.formatToParts(dateUtc);
  const tz = parts.find((p) => p.type === "timeZoneName")?.value || "GMT-5";
  const m = tz.match(/GMT([+-])(\d+)(?::(\d+))?/);
  if (!m) return -300;
  const sign = m[1] === "+" ? 1 : -1;
  const h = parseInt(m[2], 10);
  const mn = parseInt(m[3] || "0", 10);
  return sign * (h * 60 + mn);
}

function buildLocalUtc(year, month, day, hour, minute) {
  // Construit une date UTC qui correspond à hour:minute heure locale Toronto
  // 1ère approx avec offset à minuit local, puis raffinement.
  const guess = new Date(Date.UTC(year, month - 1, day, hour, minute, 0));
  const off = torontoOffsetMinutes(guess);
  return new Date(guess.getTime() - off * 60 * 1000);
}

function generateCandidateSlots(fromUtc) {
  // 7 jours d'avance, mardi(2) mercredi(3) jeudi(4)
  const slots = [];
  const startTimes = [
    [7, 0], [7, 45], [8, 30], [9, 15], [10, 0], [10, 45], [11, 30],
    [13, 0], [13, 45], [14, 30], [15, 30],
  ];
  for (let i = 0; i < LOOKAHEAD_DAYS; i++) {
    const probe = new Date(fromUtc.getTime() + i * 86400000);
    // Calculer le jour de semaine en heure Toronto
    const localDow = parseInt(
      new Intl.DateTimeFormat("en-US", { timeZone: TZ, weekday: "short" })
        .format(probe)
        .replace(/Mon/, "1").replace(/Tue/, "2").replace(/Wed/, "3")
        .replace(/Thu/, "4").replace(/Fri/, "5").replace(/Sat/, "6").replace(/Sun/, "0"),
      10
    );
    if (![2, 3, 4].includes(localDow)) continue;

    const dateParts = new Intl.DateTimeFormat("en-CA", {
      timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit",
    }).formatToParts(probe);
    const y = parseInt(dateParts.find((p) => p.type === "year").value, 10);
    const m = parseInt(dateParts.find((p) => p.type === "month").value, 10);
    const d = parseInt(dateParts.find((p) => p.type === "day").value, 10);

    for (const [h, mn] of startTimes) {
      const startUtc = buildLocalUtc(y, m, d, h, mn);
      // Skip si dans le passé (>30 min après now)
      if (startUtc.getTime() < Date.now() + 30 * 60 * 1000) continue;
      const endUtc = new Date(startUtc.getTime() + SLOT_MINUTES * 60 * 1000);
      slots.push({ start: startUtc, end: endUtc });
    }
  }
  return slots;
}

// ── Free/busy Graph ───────────────────────────────────────────────────────
async function getBusyIntervals(graphToken, fromUtc, toUtc) {
  const r = await fetch(
    `https://graph.microsoft.com/v1.0/users/${ORGANIZER_EMAIL}/calendar/getSchedule`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${graphToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        schedules: [ORGANIZER_EMAIL],
        startTime: { dateTime: fromUtc.toISOString(), timeZone: "UTC" },
        endTime: { dateTime: toUtc.toISOString(), timeZone: "UTC" },
        availabilityViewInterval: 15,
      }),
    }
  );
  const data = await r.json();
  if (!r.ok) throw new Error("getSchedule failed: " + JSON.stringify(data));
  const items = data.value?.[0]?.scheduleItems || [];
  return items
    .filter((x) => x.status === "busy" || x.status === "oof" || x.status === "tentative")
    .map((x) => ({
      start: new Date(x.start.dateTime + "Z"),
      end: new Date(x.end.dateTime + "Z"),
    }));
}

function slotIsFree(slot, busy) {
  for (const b of busy) {
    if (slot.start < b.end && slot.end > b.start) return false;
  }
  return true;
}

function pickTwoSlots(candidates, busy) {
  const picked = [];
  for (const s of candidates) {
    if (slotIsFree(s, busy)) {
      // Espacer les 2 propositions: la 2e doit être un autre jour si possible
      if (picked.length === 0) picked.push(s);
      else {
        const sameDay =
          new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(s.start) ===
          new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(picked[0].start);
        if (!sameDay) {
          picked.push(s);
          break;
        }
      }
    }
  }
  // Fallback: si on n'a pas trouvé 2 jours différents, accepter même jour
  if (picked.length < 2) {
    for (const s of candidates) {
      if (picked.find((p) => p.start.getTime() === s.start.getTime())) continue;
      if (slotIsFree(s, busy)) {
        picked.push(s);
        if (picked.length === 2) break;
      }
    }
  }
  return picked;
}

// ── Format date pour affichage email ──────────────────────────────────────
function formatSlotFr(slot) {
  const d = new Intl.DateTimeFormat("fr-CA", {
    timeZone: TZ, weekday: "long", day: "numeric", month: "long", year: "numeric",
  }).format(slot.start);
  const h = new Intl.DateTimeFormat("fr-CA", {
    timeZone: TZ, hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(slot.start);
  const hEnd = new Intl.DateTimeFormat("fr-CA", {
    timeZone: TZ, hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(slot.end);
  return `${d.charAt(0).toUpperCase() + d.slice(1)}, ${h} – ${hEnd}`;
}

function formatSlotEn(slot) {
  const d = new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ, weekday: "long", day: "numeric", month: "long", year: "numeric",
  }).format(slot.start);
  const h = new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ, hour: "2-digit", minute: "2-digit", hour12: true,
  }).format(slot.start);
  const hEnd = new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ, hour: "2-digit", minute: "2-digit", hour12: true,
  }).format(slot.end);
  return `${d}, ${h} – ${hEnd}`;
}

// ── Email HTML ────────────────────────────────────────────────────────────
function buildEmailHtml({ clientPrenom, slots, tokens, lang, dossierId, portalUrl }) {
  const fr = lang !== "en";
  const fmt = fr ? formatSlotFr : formatSlotEn;
  const t = fr
    ? {
        salut: `Bonjour ${clientPrenom || ""},`,
        intro:
          "Suite à l'analyse approfondie de votre dossier, nous aimerions planifier un appel Teams de 45 minutes pour discuter de la suite. Veuillez choisir l'un des deux créneaux ci-dessous :",
        choisir: "Choisir ce créneau",
        note:
          "L'invitation Teams (avec lien de réunion et événement calendrier) vous sera envoyée immédiatement après votre confirmation.",
        dossierLbl: "Numéro de dossier",
        portalLbl: "Suivre votre dossier en ligne",
        portalCta: "Accéder à votre espace client",
        portalNote:
          "Notre équipe vous remercie pour les documents transmis. Si certains documents requis sont encore manquants, vous pouvez les déposer en toute sécurité via votre espace client (lien ci-dessus).",
        signature: "Yves Barrette<br>Capital Norvex",
      }
    : {
        salut: `Hello ${clientPrenom || ""},`,
        intro:
          "Following the in-depth analysis of your file, we'd like to schedule a 45-minute Teams call to discuss next steps. Please pick one of the two time slots below:",
        choisir: "Pick this slot",
        note:
          "The Teams invite (with meeting link and calendar event) will be sent to you immediately after confirmation.",
        dossierLbl: "File number",
        portalLbl: "Track your file online",
        portalCta: "Access your client portal",
        portalNote:
          "Thank you for the documents already submitted. If any required documents are still missing, you can securely upload them through your client portal (link above).",
        signature: "Yves Barrette<br>Capital Norvex",
      };

  const btn = (slot, token) => `
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:14px 0">
      <tr><td style="background:#0a0d13;border:1px solid #b8975a">
        <a href="${SITE_URL}/.netlify/functions/confirm-rdv?token=${token}"
           style="display:block;padding:18px 28px;color:#b8975a;text-decoration:none;font-family:Georgia,serif;font-size:15px;letter-spacing:1px">
          <div style="font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#7a8294;margin-bottom:6px">${t.choisir}</div>
          <div style="color:#fff;font-size:16px">${fmt(slot)}</div>
        </a>
      </td></tr>
    </table>`;

  const dossierBlock = dossierId ? `
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 18px;border-collapse:collapse">
      <tr>
        <td style="padding:6px 14px;background:#0a0d13;border-left:3px solid #b8975a;font-size:11px;letter-spacing:2px;color:#b8975a;text-transform:uppercase">${t.dossierLbl}</td>
        <td style="padding:6px 14px;background:#faf8f4;border:1px solid #e0d8cc;border-left:none;font-family:'SF Mono',Menlo,monospace;font-size:13px;color:#0a0d13;letter-spacing:1px"><strong>${dossierId}</strong></td>
      </tr>
    </table>` : "";

  const portalBlock = portalUrl ? `
    <div style="margin:24px 0 8px;padding:18px 20px;background:#faf8f4;border:1px solid #e0d8cc">
      <p style="margin:0 0 10px;font-size:11px;letter-spacing:2px;color:#b8975a;text-transform:uppercase">${t.portalLbl}</p>
      <p style="margin:0 0 14px;font-size:13px;line-height:1.7;color:#3a3a3a">${t.portalNote}</p>
      <a href="${portalUrl}" style="display:inline-block;padding:12px 22px;background:#0a0d13;border:1px solid #b8975a;color:#b8975a;text-decoration:none;font-size:12px;letter-spacing:2px;text-transform:uppercase">${t.portalCta} →</a>
    </div>` : "";

  return `<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f5f3ef;font-family:'Helvetica Neue',Arial,sans-serif;color:#1a1a1a">
<div style="max-width:640px;margin:40px auto;background:#fff;border:1px solid #e0d8cc">
  <div style="background:#0a0d13;padding:24px 40px">
    <img src="${SITE_URL}/norvex-v2/assets/logo.png" alt="Capital Norvex" style="height:42px">
  </div>
  <div style="padding:40px">
    <p style="font-size:15px;line-height:1.6;margin:0 0 18px">${t.salut}</p>
    ${dossierBlock}
    <p style="font-size:14px;line-height:1.7;margin:0 0 18px;color:#3a3a3a">${t.intro}</p>
    ${btn(slots[0], tokens[0])}
    ${btn(slots[1], tokens[1])}
    <p style="margin-top:32px;padding:16px 20px;background:#faf8f4;border-left:3px solid #b8975a;font-size:12px;line-height:1.7;color:#666">
      ${t.note}
    </p>
    ${portalBlock}
    <p style="margin-top:32px;font-size:13px;line-height:1.6;color:#3a3a3a">${t.signature}</p>
  </div>
  <div style="background:#0a0d13;padding:18px;text-align:center">
    <p style="margin:0;color:#b8975a;font-size:10px;letter-spacing:2px">CAPITAL NORVEX · capitalnorvex.com</p>
  </div>
</div>  <div style="margin-top:24px;padding-top:14px;border-top:1px solid #cbd5e1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:11px;color:#64748b;line-height:1.5;letter-spacing:.3px;text-align:center">
    <strong style="color:#0f172a;font-size:12px;letter-spacing:1px">CAPITAL NORVEX INC.</strong><br>
    2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
    Téléphone : 1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
  </div>
</body></html>`;
}

// ── Handler ───────────────────────────────────────────────────────────────
export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-Internal-Secret",
      },
    });
  }
  if (req.method !== "POST") return json({ error: "Method Not Allowed" }, 405);

  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return json({ error: "Unauthorized" }, 401);
  }

  let body;
  try { body = await req.json(); } catch { return json({ error: "Invalid JSON" }, 400); }
  const { dossierId } = body;
  if (!dossierId) return json({ error: "Missing dossierId" }, 400);

  // 1. Firestore — lire dossier
  const { getServiceAccount } = await import("./_firebase-sa.mjs");

  let sa;

  try { sa = await getServiceAccount(); }

  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  let fsToken;
  try { fsToken = await getFirestoreToken(sa); }
  catch (e) { return json({ error: "Firestore auth failed: " + e.message }, 500); }

  const projectId = sa.project_id;
  const docUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/dossiers/${dossierId}`;

  let docResp = await fetch(docUrl, { headers: { Authorization: `Bearer ${fsToken}` } });
  if (!docResp.ok) {
    const err = await docResp.text();
    return json({ error: "Dossier introuvable: " + err }, 404);
  }
  const doc = await docResp.json();
  const f = doc.fields || {};
  const str = (x) => x?.stringValue || "";
  const clientEmail = str(f.email);
  const clientPrenom = str(f.prenom);
  const clientNom = str(f.nom);
  const lang = str(f.lang) || "fr";
  if (!clientEmail) return json({ error: "Dossier sans email client" }, 400);

  // 2. Graph token + free/busy
  let graphToken;
  try { graphToken = await getGraphToken(); }
  catch (e) { return json({ error: e.message }, 500); }

  const now = new Date();
  const horizon = new Date(now.getTime() + LOOKAHEAD_DAYS * 86400000);

  let busy;
  try { busy = await getBusyIntervals(graphToken, now, horizon); }
  catch (e) { return json({ error: e.message }, 500); }

  // 3. Sélection des 2 créneaux
  const candidates = generateCandidateSlots(now);
  const picked = pickTwoSlots(candidates, busy);
  if (picked.length < 2) {
    return json({ error: "Pas assez de créneaux libres dans les 14 prochains jours" }, 409);
  }

  // 4. Tokens HMAC
  const tokenSecret = process.env.INTERNAL_SECRET;
  const expSec = Math.floor(Date.now() / 1000) + TOKEN_TTL_DAYS * 86400;
  const tokens = await Promise.all(picked.map((s) =>
    signToken({
      d: dossierId,
      s: s.start.toISOString(),
      e: s.end.toISOString(),
      x: expSec,
    }, tokenSecret)
  ));

  // 5. Email client — SendGrid en priorité (bypasse M365 outbound 5.7.708), Graph fallback
  const portalUrl = `${SITE_URL}/capital-norvex-portail-client.html`;
  const html = buildEmailHtml({ clientPrenom, slots: picked, tokens, lang, dossierId, portalUrl });
  const subject = lang === "en"
    ? "Schedule your Capital Norvex Teams call"
    : "Choisir un horaire pour votre appel Capital Norvex";

  let mailDelivered = false;
  let mailErrors = [];

  // Tentative 1 — SendGrid
  const sgKey = process.env.SENDGRID_API_KEY;
  if (sgKey) {
    try {
      const sgResp = await fetch("https://api.sendgrid.com/v3/mail/send", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${sgKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          personalizations: [{ to: [{ email: clientEmail }] }],
          from:     { email: ORGANIZER_EMAIL, name: "Capital Norvex" },
          reply_to: { email: ORGANIZER_EMAIL, name: "Capital Norvex" },
          subject,
          content: [{ type: "text/html", value: html }],
          headers: {
            "X-Capital-Norvex-Type":    "rdv-proposal",
            "X-Auto-Response-Suppress": "All",
          },
          tracking_settings: {
            click_tracking: { enable: false, enable_text: false },
            open_tracking:  { enable: false },
          },
        }),
      });
      if (sgResp.ok || sgResp.status === 202) {
        mailDelivered = true;
      } else {
        const errTxt = await sgResp.text();
        mailErrors.push("SendGrid " + sgResp.status + ": " + errTxt.slice(0, 200));
      }
    } catch (e) {
      mailErrors.push("SendGrid exception: " + e.message);
    }
  } else {
    mailErrors.push("SENDGRID_API_KEY not set");
  }

  // Tentative 2 (fallback) — Microsoft Graph (peut bouncer 5.7.708)
  if (!mailDelivered) {
    const mailResp = await fetch(
      `https://graph.microsoft.com/v1.0/users/${ORGANIZER_EMAIL}/sendMail`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${graphToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: {
            subject,
            body: { contentType: "HTML", content: html },
            toRecipients: [{ emailAddress: { address: clientEmail } }],
            replyTo: [{ emailAddress: { address: ORGANIZER_EMAIL, name: "Capital Norvex" } }],
            internetMessageHeaders: [
              { name: "X-Auto-Response-Suppress", value: "All" },
              { name: "X-Capital-Norvex-Type", value: "rdv-proposal" },
            ],
          },
          saveToSentItems: true,
        }),
      }
    );
    if (!mailResp.ok) {
      const err = await mailResp.text();
      mailErrors.push("Graph " + mailResp.status + ": " + err.slice(0, 200));
      return json({ error: "Email send failed (SendGrid+Graph): " + mailErrors.join(" | ") }, 500);
    }
    mailDelivered = true;
  }

  // 6. Update Firestore
  const updateFields = {
    rdv_status: { stringValue: "proposed" },
    rdv_proposed_at: { timestampValue: new Date().toISOString() },
    rdv_proposed_slots: {
      arrayValue: {
        values: picked.map((s) => ({
          mapValue: {
            fields: {
              start: { timestampValue: s.start.toISOString() },
              end: { timestampValue: s.end.toISOString() },
            },
          },
        })),
      },
    },
  };
  const maskQuery = Object.keys(updateFields)
    .map((k) => `updateMask.fieldPaths=${k}`).join("&");
  await fetch(`${docUrl}?${maskQuery}&currentDocument.exists=true`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${fsToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ fields: updateFields }),
  });

  return json({
    ok: true,
    sentTo: clientEmail,
    slots: picked.map((s) => ({ start: s.start.toISOString(), end: s.end.toISOString() })),
    clientName: `${clientPrenom} ${clientNom}`.trim(),
  });
};
