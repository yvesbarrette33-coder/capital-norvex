/**
 * GET /.netlify/functions/confirm-rdv?token=…
 *
 * 1. Vérifie le token HMAC (signé par propose-rdv)
 * 2. Lit le dossier Firestore
 * 3. Si rdv déjà confirmé → page d'info avec lien Teams existant
 * 4. Sinon: crée l'événement Graph (avec Teams meeting auto) sur yves@capitalnorvex.com,
 *    invite le client en attendee
 * 5. Met à jour Firestore: rdv_status='confirmed', rdv_confirmed_slot, rdv_teams_join_url, rdv_teams_event_id
 * 6. Retourne une page HTML de confirmation avec le lien Teams + détails
 */

const ORGANIZER_EMAIL = "yves@capitalnorvex.com";
const TZ = "America/Toronto";

function htmlResponse(body, status = 200) {
  return new Response(body, {
    status,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}

// ── Firestore JWT ─────────────────────────────────────────────────────────
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
  if (!data.access_token) throw new Error("Firestore token failed");
  return data.access_token;
}

// ── Graph token ───────────────────────────────────────────────────────────
async function getGraphToken() {
  const r = await fetch(
    `https://login.microsoftonline.com/${process.env.AZURE_TENANT_ID}/oauth2/v2.0/token`,
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "client_credentials",
        client_id: process.env.AZURE_CLIENT_ID,
        client_secret: process.env.AZURE_CLIENT_SECRET,
        scope: "https://graph.microsoft.com/.default",
      }),
    }
  );
  const data = await r.json();
  if (!data.access_token) throw new Error("Graph token failed: " + JSON.stringify(data));
  return data.access_token;
}

// ── Vérification du token HMAC ────────────────────────────────────────────
async function verifyToken(token, secret) {
  const [data, sig] = token.split(".");
  if (!data || !sig) return null;
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false, ["verify"]
  );
  const sigBytes = Uint8Array.from(
    atob(sig.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(sig.length / 4) * 4, "=")),
    (c) => c.charCodeAt(0)
  );
  const ok = await crypto.subtle.verify(
    "HMAC", key, sigBytes, new TextEncoder().encode(data)
  );
  if (!ok) return null;
  let payload;
  try {
    const padded = data.replace(/-/g, "+").replace(/_/g, "/")
      .padEnd(Math.ceil(data.length / 4) * 4, "=");
    payload = JSON.parse(atob(padded));
  } catch { return null; }
  if (payload.x && payload.x < Math.floor(Date.now() / 1000)) return null;
  return payload;
}

// ── Format affichage ──────────────────────────────────────────────────────
function fmtDateLong(date, lang) {
  const opts = { timeZone: TZ, weekday: "long", day: "numeric", month: "long", year: "numeric" };
  const locale = lang === "en" ? "en-CA" : "fr-CA";
  const d = new Intl.DateTimeFormat(locale, opts).format(date);
  return lang === "en" ? d : d.charAt(0).toUpperCase() + d.slice(1);
}
function fmtTime(date, lang) {
  return new Intl.DateTimeFormat(lang === "en" ? "en-CA" : "fr-CA", {
    timeZone: TZ, hour: "2-digit", minute: "2-digit", hour12: lang === "en",
  }).format(date);
}

// ── Page HTML ─────────────────────────────────────────────────────────────
function pageConfirmed({ clientPrenom, start, end, joinUrl, lang }) {
  const fr = lang !== "en";
  const t = fr ? {
    title: "Rendez-vous confirmé",
    h1: "Votre rendez-vous est confirmé",
    salut: `Merci ${clientPrenom || ""}.`,
    intro: "Vous recevrez sous peu une invitation Teams par courriel avec le lien de la réunion et un événement calendrier.",
    when: "Quand",
    teams: "Lien de la réunion Teams",
    join: "Rejoindre la réunion",
    note: "Si vous devez annuler ou reporter, répondez simplement à ce courriel.",
  } : {
    title: "Meeting confirmed",
    h1: "Your meeting is confirmed",
    salut: `Thank you ${clientPrenom || ""}.`,
    intro: "You'll receive a Teams invitation by email shortly with the meeting link and a calendar event.",
    when: "When",
    teams: "Teams meeting link",
    join: "Join the meeting",
    note: "If you need to reschedule, simply reply to that email.",
  };

  return `<!DOCTYPE html><html lang="${fr ? "fr" : "en"}"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${t.title} — Capital Norvex</title>
<style>
  body{margin:0;background:#f5f3ef;font-family:'Helvetica Neue',Arial,sans-serif;color:#1a1a1a}
  .wrap{max-width:640px;margin:48px auto;background:#fff;border:1px solid #e0d8cc}
  .hdr{background:#0a0d13;padding:24px 40px}
  .hdr img{height:42px}
  .body{padding:48px 40px}
  h1{font-family:Georgia,serif;font-size:26px;font-weight:300;color:#0a0d13;margin:0 0 8px}
  .check{display:inline-block;width:46px;height:46px;border-radius:50%;background:#52b788;color:#fff;text-align:center;line-height:46px;font-size:24px;margin-bottom:18px}
  p{font-size:14px;line-height:1.7;color:#3a3a3a;margin:0 0 14px}
  .meta{margin:28px 0;padding:22px 26px;background:#faf8f4;border-left:3px solid #b8975a}
  .meta-label{font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#999;margin-bottom:4px}
  .meta-value{font-size:15px;color:#1a1a1a;margin-bottom:14px}
  .meta-value:last-child{margin-bottom:0}
  .btn{display:inline-block;padding:16px 28px;background:#0a0d13;border:1px solid #b8975a;color:#b8975a;text-decoration:none;font-family:Georgia,serif;letter-spacing:1px;margin-top:6px}
  .btn:hover{background:#b8975a;color:#0a0d13}
  .ftr{background:#0a0d13;padding:18px;text-align:center}
  .ftr p{margin:0;color:#b8975a;font-size:10px;letter-spacing:2px}
</style></head>
<body><div class="wrap">
  <div class="hdr"><img src="/norvex-v2/assets/logo.png" alt="Capital Norvex"></div>
  <div class="body">
    <div class="check">✓</div>
    <h1>${t.h1}</h1>
    <p>${t.salut}</p>
    <p>${t.intro}</p>
    <div class="meta">
      <div class="meta-label">${t.when}</div>
      <div class="meta-value">${fmtDateLong(start, lang)}<br>${fmtTime(start, lang)} – ${fmtTime(end, lang)} (${TZ})</div>
      <div class="meta-label">${t.teams}</div>
      <div class="meta-value"><a class="btn" href="${joinUrl}" target="_blank" rel="noopener">${t.join}</a></div>
    </div>
    <p style="font-size:12px;color:#888;margin-top:32px">${t.note}</p>
  </div>
  <div class="ftr"><p>CAPITAL NORVEX · capitalnorvex.com</p></div>
</div>  <div style="margin-top:24px;padding-top:14px;border-top:1px solid #cbd5e1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:11px;color:#64748b;line-height:1.5;letter-spacing:.3px;text-align:center">
    <strong style="color:#0f172a;font-size:12px;letter-spacing:1px">CAPITAL NORVEX INC.</strong><br>
    2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
    Téléphone : 1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
  </div>
</body></html>`;
}

function pageError(msg, lang = "fr") {
  const fr = lang !== "en";
  return `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>${fr ? "Erreur" : "Error"}</title>
<style>body{margin:0;background:#f5f3ef;font-family:Arial,sans-serif;display:flex;min-height:100vh;align-items:center;justify-content:center}
.box{background:#fff;border:1px solid #e0d8cc;padding:40px 50px;max-width:480px;text-align:center}
h1{font-family:Georgia,serif;color:#0a0d13;font-weight:300}
p{color:#666;font-size:14px;line-height:1.6}</style></head>
<body><div class="box"><h1>${fr ? "Lien invalide" : "Invalid link"}</h1>
<p>${msg}</p>
<p style="margin-top:28px;font-size:12px">${fr ? "Veuillez nous contacter à" : "Please contact us at"} <strong>info@capitalnorvex.com</strong></p>
</div>  <div style="margin-top:24px;padding-top:14px;border-top:1px solid #cbd5e1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:11px;color:#64748b;line-height:1.5;letter-spacing:.3px;text-align:center">
    <strong style="color:#0f172a;font-size:12px;letter-spacing:1px">CAPITAL NORVEX INC.</strong><br>
    2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
    Téléphone : 1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
  </div>
</body></html>`;
}

// ── Handler ───────────────────────────────────────────────────────────────
export default async (req) => {
  const url = new URL(req.url);
  const token = url.searchParams.get("token");
  if (!token) return htmlResponse(pageError("Token manquant."), 400);

  const secret = process.env.INTERNAL_SECRET;
  const payload = await verifyToken(token, secret);
  if (!payload) {
    return htmlResponse(pageError("Ce lien est invalide ou expiré."), 400);
  }

  const { d: dossierId, s: startIso, e: endIso } = payload;
  const start = new Date(startIso);
  const end = new Date(endIso);

  // Firestore
  const { getServiceAccount } = await import("./_firebase-sa.mjs");
  const sa = await getServiceAccount();
  const fsToken = await getFirestoreToken(sa);
  const projectId = sa.project_id;
  const docUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/dossiers/${dossierId}`;

  const docResp = await fetch(docUrl, { headers: { Authorization: `Bearer ${fsToken}` } });
  if (!docResp.ok) {
    return htmlResponse(pageError("Dossier introuvable."), 404);
  }
  const doc = await docResp.json();
  const f = doc.fields || {};
  const str = (x) => x?.stringValue || "";
  const clientEmail = str(f.email);
  const clientPrenom = str(f.prenom);
  const clientNom = str(f.nom);
  const lang = str(f.lang) || "fr";
  const rdvStatus = str(f.rdv_status);

  // Idempotence: si déjà confirmé, montrer la page existante
  if (rdvStatus === "confirmed") {
    const existingJoin = str(f.rdv_teams_join_url);
    const existingStart = f.rdv_confirmed_slot?.mapValue?.fields?.start?.timestampValue;
    const existingEnd = f.rdv_confirmed_slot?.mapValue?.fields?.end?.timestampValue;
    if (existingJoin && existingStart && existingEnd) {
      return htmlResponse(pageConfirmed({
        clientPrenom,
        start: new Date(existingStart),
        end: new Date(existingEnd),
        joinUrl: existingJoin,
        lang,
      }));
    }
  }

  // Créer l'événement Graph (qui crée aussi la réunion Teams)
  let graphToken;
  try { graphToken = await getGraphToken(); }
  catch (e) {
    console.error("Graph token error:", e.message);
    return htmlResponse(pageError("Erreur de connexion au service de réunion."), 500);
  }

  const subject = lang === "en"
    ? `Capital Norvex · Call with ${clientPrenom} ${clientNom}`.trim()
    : `Capital Norvex · Appel avec ${clientPrenom} ${clientNom}`.trim();
  const bodyContent = lang === "en"
    ? `Discussion following the analysis of your file.<br>Capital Norvex.`
    : `Échange suite à l'analyse de votre dossier.<br>Capital Norvex.`;

  // Créer l'événement SANS attendee — sinon M365 envoie une invitation calendrier
  // qui bounce 5.7.708. On enverra une confirmation au client via SendGrid à la place.
  const eventBody = {
    subject,
    body: { contentType: "HTML", content: bodyContent + `<br><br>Client: ${clientPrenom} ${clientNom} &lt;${clientEmail}&gt;` },
    start: { dateTime: start.toISOString().replace(/\.\d{3}Z$/, ""), timeZone: "UTC" },
    end:   { dateTime: end.toISOString().replace(/\.\d{3}Z$/, ""),   timeZone: "UTC" },
    isOnlineMeeting: true,
    onlineMeetingProvider: "teamsForBusiness",
    allowNewTimeProposals: false,
  };

  // Header Prefer:outlook.suppress-notifications par sécurité (au cas où Graph ajouterait des notifs)
  const evResp = await fetch(
    `https://graph.microsoft.com/v1.0/users/${ORGANIZER_EMAIL}/events`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${graphToken}`,
        "Content-Type": "application/json",
        Prefer: 'outlook.suppress-notifications',
      },
      body: JSON.stringify(eventBody),
    }
  );
  const evData = await evResp.json();
  if (!evResp.ok) {
    console.error("Event create failed:", evData);
    return htmlResponse(pageError("Impossible de créer la réunion. Veuillez nous contacter."), 500);
  }

  const joinUrl = evData.onlineMeeting?.joinUrl || "";
  const eventId = evData.id || "";

  // ── Envoi confirmation au client via SendGrid (bypass M365 outbound 5.7.708) ──
  try {
    const sgKey = process.env.SENDGRID_API_KEY;
    if (sgKey) {
      // Génère un fichier .ics pour que le client ajoute le RDV à son calendrier
      const icsDt = (d) => d.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
      const icsUid = `rdv-${eventId || Date.now()}@capitalnorvex.com`;
      const icsDesc = (lang === "en"
        ? `Capital Norvex Teams call.\\nJoin: ${joinUrl}`
        : `Appel Teams Capital Norvex.\\nLien: ${joinUrl}`).replace(/\n/g, "\\n");
      const icsContent = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Capital Norvex//RDV//FR",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        `UID:${icsUid}`,
        `DTSTAMP:${icsDt(new Date())}`,
        `DTSTART:${icsDt(start)}`,
        `DTEND:${icsDt(end)}`,
        `SUMMARY:${subject}`,
        `DESCRIPTION:${icsDesc}`,
        `LOCATION:Microsoft Teams`,
        `URL:${joinUrl}`,
        "STATUS:CONFIRMED",
        "END:VEVENT",
        "END:VCALENDAR",
      ].join("\r\n");

      const startLocal = start.toLocaleString(lang === "en" ? "en-CA" : "fr-CA", {
        timeZone: "America/Toronto",
        weekday: "long", year: "numeric", month: "long", day: "numeric",
        hour: "2-digit", minute: "2-digit",
      });
      const endLocal = end.toLocaleString(lang === "en" ? "en-CA" : "fr-CA", {
        timeZone: "America/Toronto", hour: "2-digit", minute: "2-digit",
      });

      const confSubject = lang === "en"
        ? `Confirmation: Capital Norvex call · ${startLocal}`
        : `Confirmation: Appel Capital Norvex · ${startLocal}`;
      const confHtml = lang === "en"
        ? `<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#f0ece4;padding:24px 0;">
<table width="620" align="center" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:4px;border:1px solid #e0d9cc;">
<tr><td style="background:#0a0d13;padding:24px 40px;color:#C9A84C;font-size:20px;letter-spacing:3px;font-family:Georgia,serif;">CAPITAL NORVEX</td></tr>
<tr><td style="height:2px;background:linear-gradient(90deg,#7a5c10 0%,#C9A84C 50%,#7a5c10 100%)"></td></tr>
<tr><td style="padding:32px 40px;color:#1a1a1a;font-size:14px;line-height:1.7;">
<p>Hello <strong>${clientPrenom}</strong>,</p>
<p>Your Capital Norvex Teams call is <strong>confirmed</strong>:</p>
<table style="background:#fafaf8;border-left:3px solid #C9A84C;padding:18px 24px;margin:18px 0;font-size:14px;">
<tr><td><strong>Date:</strong> ${startLocal}<br><strong>End:</strong> ${endLocal}</td></tr></table>
<p style="text-align:center;margin:30px 0;">
<a href="${joinUrl}" style="display:inline-block;background:#C9A84C;color:#0a0d13;padding:14px 36px;font-weight:700;letter-spacing:1px;text-decoration:none;border-radius:2px;">JOIN TEAMS MEETING</a></p>
<p style="font-size:12px;color:#666;">A calendar invitation (.ics) is attached — you can add the meeting to your calendar.</p>
<p style="margin-top:30px;">— Capital Norvex Team</p>
</td></tr></table>  <div style="margin-top:24px;padding-top:14px;border-top:1px solid #cbd5e1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:11px;color:#64748b;line-height:1.5;letter-spacing:.3px;text-align:center">
    <strong style="color:#0f172a;font-size:12px;letter-spacing:1px">CAPITAL NORVEX INC.</strong><br>
    2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
    Téléphone : 1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
  </div>
</body></html>`
        : `<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#f0ece4;padding:24px 0;">
<table width="620" align="center" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:4px;border:1px solid #e0d9cc;">
<tr><td style="background:#0a0d13;padding:24px 40px;color:#C9A84C;font-size:20px;letter-spacing:3px;font-family:Georgia,serif;">CAPITAL NORVEX</td></tr>
<tr><td style="height:2px;background:linear-gradient(90deg,#7a5c10 0%,#C9A84C 50%,#7a5c10 100%)"></td></tr>
<tr><td style="padding:32px 40px;color:#1a1a1a;font-size:14px;line-height:1.7;">
<p>Bonjour <strong>${clientPrenom}</strong>,</p>
<p>Votre appel Teams avec Capital Norvex est <strong>confirmé</strong> :</p>
<table style="background:#fafaf8;border-left:3px solid #C9A84C;padding:18px 24px;margin:18px 0;font-size:14px;">
<tr><td><strong>Date :</strong> ${startLocal}<br><strong>Fin :</strong> ${endLocal}</td></tr></table>
<p style="text-align:center;margin:30px 0;">
<a href="${joinUrl}" style="display:inline-block;background:#C9A84C;color:#0a0d13;padding:14px 36px;font-weight:700;letter-spacing:1px;text-decoration:none;border-radius:2px;">REJOINDRE LA RÉUNION TEAMS</a></p>
<p style="font-size:12px;color:#666;">Une invitation calendrier (.ics) est jointe — vous pouvez l'ajouter à votre calendrier en un clic.</p>
<p style="margin-top:30px;">— L'équipe Capital Norvex</p>
</td></tr></table>  <div style="margin-top:24px;padding-top:14px;border-top:1px solid #cbd5e1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:11px;color:#64748b;line-height:1.5;letter-spacing:.3px;text-align:center">
    <strong style="color:#0f172a;font-size:12px;letter-spacing:1px">CAPITAL NORVEX INC.</strong><br>
    2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
    Téléphone : 1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
  </div>
</body></html>`;

      const icsB64 = btoa(unescape(encodeURIComponent(icsContent)));
      await fetch("https://api.sendgrid.com/v3/mail/send", {
        method: "POST",
        headers: { Authorization: `Bearer ${sgKey}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          personalizations: [{ to: [{ email: clientEmail }] }],
          from:     { email: ORGANIZER_EMAIL, name: "Capital Norvex" },
          reply_to: { email: ORGANIZER_EMAIL, name: "Capital Norvex" },
          subject:  confSubject,
          content:  [{ type: "text/html", value: confHtml }],
          attachments: [{
            content:     icsB64,
            type:        "text/calendar; method=PUBLISH",
            filename:    "capital-norvex-rdv.ics",
            disposition: "attachment",
          }],
          headers: {
            "X-Capital-Norvex-Type":    "rdv-confirmation",
            "X-Auto-Response-Suppress": "All",
          },
          tracking_settings: {
            click_tracking: { enable: false, enable_text: false },
            open_tracking:  { enable: false },
          },
        }),
      });
    }
  } catch (e) {
    console.warn("SendGrid confirmation email failed (non-fatal):", e.message);
  }

  // Update Firestore
  const updateFields = {
    rdv_status: { stringValue: "confirmed" },
    rdv_confirmed_at: { timestampValue: new Date().toISOString() },
    rdv_confirmed_slot: {
      mapValue: {
        fields: {
          start: { timestampValue: start.toISOString() },
          end:   { timestampValue: end.toISOString() },
        },
      },
    },
    rdv_teams_join_url: { stringValue: joinUrl },
    rdv_teams_event_id: { stringValue: eventId },
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

  return htmlResponse(pageConfirmed({ clientPrenom, start, end, joinUrl, lang }));
};
