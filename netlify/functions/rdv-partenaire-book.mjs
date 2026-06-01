/**
 * POST /.netlify/functions/rdv-partenaire-book
 *
 * Body: { token, slotStart, slotEnd, contactEmail, contactName, contactPhone? }
 *
 * 1. Vérifie token HMAC (signé INTERNAL_SECRET, kind=partner)
 * 2. Vérifie que le créneau est encore libre via Graph free/busy
 * 3. Crée un événement Microsoft Teams (avec lien réunion) sur le calendrier
 *    de yves@capitalnorvex.com — invite le contactEmail
 * 4. Envoie email de confirmation au Partenaire (SendGrid)
 * 5. Notifie Yves par email (SendGrid)
 * 6. Update Firestore : capitalTargets/{targetId}
 *      .rdvBooked = true
 *      .rdvBookedAt = timestamp
 *      .rdvSlot = { start, end, contactEmail, contactName }
 */

const ORGANIZER_EMAIL = process.env.CAPITAL_NORVEX_ORGANIZER || "yves@capitalnorvex.com";
const SITE_URL = process.env.SITE_URL || "https://capitalnorvex.com";
const TZ = "America/Toronto";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

function dataB64Pad(s) {
  const pad = s.length % 4;
  return pad ? s + "=".repeat(4 - pad) : s;
}

async function verifyToken(token, secret) {
  if (!token || !token.includes(".")) return null;
  const [dataB64, sigB64] = token.split(".");
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["verify"]
  );
  const sigBytes = Uint8Array.from(
    atob(dataB64Pad(sigB64).replace(/-/g, "+").replace(/_/g, "/")),
    (c) => c.charCodeAt(0)
  );
  const ok = await crypto.subtle.verify(
    "HMAC",
    key,
    sigBytes,
    new TextEncoder().encode(dataB64)
  );
  if (!ok) return null;
  let payload;
  try {
    payload = JSON.parse(
      atob(dataB64Pad(dataB64).replace(/-/g, "+").replace(/_/g, "/"))
    );
  } catch {
    return null;
  }
  const now = Math.floor(Date.now() / 1000);
  if (payload.x && payload.x < now) return null;
  return payload;
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
  if (!data.access_token)
    throw new Error("Firestore token failed: " + JSON.stringify(data));
  return data.access_token;
}

async function getGraphToken() {
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
  if (!data.access_token)
    throw new Error("Graph token failed: " + JSON.stringify(data));
  return data.access_token;
}

async function checkSlotStillFree(graphToken, startUtc, endUtc) {
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
        startTime: { dateTime: startUtc.toISOString(), timeZone: "UTC" },
        endTime: { dateTime: endUtc.toISOString(), timeZone: "UTC" },
        availabilityViewInterval: 15,
      }),
    }
  );
  const data = await r.json();
  if (!r.ok) throw new Error("getSchedule failed: " + JSON.stringify(data));
  const items = data.value?.[0]?.scheduleItems || [];
  // S'il y a un seul item busy/oof/tentative dans l'intervalle, slot pris
  for (const x of items) {
    if (x.status === "busy" || x.status === "oof" || x.status === "tentative") {
      const bs = new Date(x.start.dateTime + "Z");
      const be = new Date(x.end.dateTime + "Z");
      if (startUtc < be && endUtc > bs) return false;
    }
  }
  return true;
}

async function createTeamsEvent(graphToken, params) {
  const { startUtc, endUtc, partnerName, partnerEmail, organization, lang } = params;
  const isEn = lang === "en";

  const subject = isEn
    ? `Capital Norvex × ${organization || partnerName} — Initial discussion`
    : `Capital Norvex × ${organization || partnerName} — Discussion initiale`;

  const bodyContent = isEn
    ? `<p>Confidential 30-minute discussion between ${partnerName} and Yves Barrette, Founder & Director, Capital Norvex Inc.</p>
       <p>Microsoft Teams meeting link generated automatically.</p>
       <p style="margin-top:18px;color:#666;font-size:12px;">— Capital Norvex / Norvex Agents 2026</p>`
    : `<p>Discussion confidentielle de 30 minutes entre ${partnerName} et Yves Barrette, Directeur-fondateur, Capital Norvex Inc.</p>
       <p>Lien de réunion Microsoft Teams généré automatiquement.</p>
       <p style="margin-top:18px;color:#666;font-size:12px;">— Capital Norvex / Norvex Agents 2026</p>`;

  const r = await fetch(
    `https://graph.microsoft.com/v1.0/users/${ORGANIZER_EMAIL}/events`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${graphToken}`,
        "Content-Type": "application/json",
        Prefer: `outlook.timezone="${TZ}"`,
      },
      body: JSON.stringify({
        subject,
        body: { contentType: "HTML", content: bodyContent },
        start: { dateTime: startUtc.toISOString(), timeZone: "UTC" },
        end: { dateTime: endUtc.toISOString(), timeZone: "UTC" },
        attendees: [
          {
            emailAddress: { address: partnerEmail, name: partnerName },
            type: "required",
          },
        ],
        isOnlineMeeting: true,
        onlineMeetingProvider: "teamsForBusiness",
        responseRequested: true,
        importance: "high",
      }),
    }
  );
  const data = await r.json();
  if (!r.ok) throw new Error("Event creation failed: " + JSON.stringify(data));
  return {
    eventId: data.id,
    joinUrl: data.onlineMeeting?.joinUrl || data.onlineMeetingUrl || null,
    webLink: data.webLink,
  };
}

async function sendConfirmationEmails(params) {
  const {
    partnerEmail,
    partnerName,
    startUtc,
    endUtc,
    joinUrl,
    organization,
    lang,
  } = params;
  const isEn = lang === "en";

  const dayFmt = new Intl.DateTimeFormat(isEn ? "en-CA" : "fr-CA", {
    timeZone: TZ,
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  const timeFmt = new Intl.DateTimeFormat(isEn ? "en-CA" : "fr-CA", {
    timeZone: TZ,
    hour: "2-digit",
    minute: "2-digit",
    hour12: isEn,
  });
  const dateStr = dayFmt.format(startUtc);
  const startStr = timeFmt.format(startUtc);
  const endStr = timeFmt.format(endUtc);
  const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

  const tzLabel = "Heure de Montréal (America/Toronto)";

  // Email au Partenaire
  const partnerSubject = isEn
    ? `Confirmed: your Capital Norvex discussion — ${cap(dateStr)}`
    : `Confirmé : votre discussion Capital Norvex — ${cap(dateStr)}`;

  const partnerHtml = isEn
    ? `<!DOCTYPE html><html><body style="font-family:Georgia,serif;background:#F5EFE0;margin:0;padding:24px;">
<table width="600" cellpadding="0" cellspacing="0" style="margin:0 auto;background:#F5EFE0;">
  <tr><td style="background:#0A0A0A;padding:24px;text-align:center;">
    <div style="color:#C8B070;font-size:22px;letter-spacing:2px;">CAPITAL NORVEX</div>
    <div style="color:#C8B070;font-size:11px;font-style:italic;letter-spacing:1px;margin-top:6px;">Structured capital. Measured ambition.</div>
  </td></tr>
  <tr><td style="padding:32px 28px;color:#0A0A0A;">
    <p>Hello ${partnerName},</p>
    <p>Your meeting is confirmed.</p>
    <table cellpadding="0" cellspacing="0" style="margin:18px 0;width:100%;">
      <tr><td style="padding:14px 18px;background:#FAF6EA;border-left:3px solid #C8B070;">
        <div style="font-size:11px;letter-spacing:2px;color:#9A8554;">DATE</div>
        <div style="font-size:15px;margin:4px 0 12px 0;">${cap(dateStr)}</div>
        <div style="font-size:11px;letter-spacing:2px;color:#9A8554;">TIME (${tzLabel})</div>
        <div style="font-size:15px;margin-top:4px;">${startStr} – ${endStr}</div>
      </td></tr>
    </table>
    ${joinUrl ? `<p style="text-align:center;margin:24px 0;"><a href="${joinUrl}" style="display:inline-block;background:#0A0A0A;color:#C8B070;border:1px solid #C8B070;padding:14px 32px;text-decoration:none;letter-spacing:1.5px;">Join Microsoft Teams →</a></p>` : ""}
    <p style="font-size:13px;color:#555;">A calendar invite has also been sent to your inbox. If you need to reschedule, simply reply to this email.</p>
    <p style="margin-top:24px;">Sincerely,</p>
    <p><strong>Yves Barrette</strong><br><em style="color:#666;">Founder &amp; Director</em><br>Capital Norvex Inc.</p>
  </td></tr>
  <tr><td style="background:#0A0A0A;padding:18px;text-align:center;color:#C8B070;font-size:11px;">
    capitalnorvex.com · ${process.env.CAPITAL_NORVEX_PHONE || "438-533-7738"}
  </td></tr>
</table>  <div style="margin-top:24px;padding-top:14px;border-top:1px solid #cbd5e1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:11px;color:#64748b;line-height:1.5;letter-spacing:.3px;text-align:center">
    <strong style="color:#0f172a;font-size:12px;letter-spacing:1px">CAPITAL NORVEX INC.</strong><br>
    2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
    Téléphone : 1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
  </div>
</body></html>`
    : `<!DOCTYPE html><html><body style="font-family:Georgia,serif;background:#F5EFE0;margin:0;padding:24px;">
<table width="600" cellpadding="0" cellspacing="0" style="margin:0 auto;background:#F5EFE0;">
  <tr><td style="background:#0A0A0A;padding:24px;text-align:center;">
    <div style="color:#C8B070;font-size:22px;letter-spacing:2px;">CAPITAL NORVEX</div>
    <div style="color:#C8B070;font-size:11px;font-style:italic;letter-spacing:1px;margin-top:6px;">Capital structuré. Ambition maîtrisée.</div>
  </td></tr>
  <tr><td style="padding:32px 28px;color:#0A0A0A;">
    <p>Bonjour ${partnerName},</p>
    <p>Votre rencontre est confirmée.</p>
    <table cellpadding="0" cellspacing="0" style="margin:18px 0;width:100%;">
      <tr><td style="padding:14px 18px;background:#FAF6EA;border-left:3px solid #C8B070;">
        <div style="font-size:11px;letter-spacing:2px;color:#9A8554;">DATE</div>
        <div style="font-size:15px;margin:4px 0 12px 0;">${cap(dateStr)}</div>
        <div style="font-size:11px;letter-spacing:2px;color:#9A8554;">HEURE (${tzLabel})</div>
        <div style="font-size:15px;margin-top:4px;">${startStr} – ${endStr}</div>
      </td></tr>
    </table>
    ${joinUrl ? `<p style="text-align:center;margin:24px 0;"><a href="${joinUrl}" style="display:inline-block;background:#0A0A0A;color:#C8B070;border:1px solid #C8B070;padding:14px 32px;text-decoration:none;letter-spacing:1.5px;">Rejoindre Microsoft Teams →</a></p>` : ""}
    <p style="font-size:13px;color:#555;">Une invitation calendrier a également été envoyée à votre boîte. Pour reporter, répondez simplement à ce courriel.</p>
    <p style="margin-top:24px;">Avec considération,</p>
    <p><strong>Yves Barrette</strong><br><em style="color:#666;">Directeur-fondateur</em><br>Capital Norvex Inc.</p>
  </td></tr>
  <tr><td style="background:#0A0A0A;padding:18px;text-align:center;color:#C8B070;font-size:11px;">
    capitalnorvex.com · ${process.env.CAPITAL_NORVEX_PHONE || "438-533-7738"}
  </td></tr>
</table>  <div style="margin-top:24px;padding-top:14px;border-top:1px solid #cbd5e1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:11px;color:#64748b;line-height:1.5;letter-spacing:.3px;text-align:center">
    <strong style="color:#0f172a;font-size:12px;letter-spacing:1px">CAPITAL NORVEX INC.</strong><br>
    2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
    Téléphone : 1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
  </div>
</body></html>`;

  // Notification à Yves
  const yvesHtml = `<!DOCTYPE html><html><body style="font-family:Georgia,serif;padding:20px;">
<h2 style="color:#0A0A0A;">Nouveau RDV Partenaire confirmé</h2>
<p><strong>Partenaire :</strong> ${partnerName}${organization ? ` (${organization})` : ""}<br>
<strong>Email :</strong> ${partnerEmail}<br>
<strong>Date :</strong> ${cap(dateStr)}<br>
<strong>Heure :</strong> ${startStr} – ${endStr} (${TZ})</p>
${joinUrl ? `<p><a href="${joinUrl}">Lien Teams</a></p>` : ""}
<p style="color:#666;font-size:11px;">— Norvex Agents 2026</p>
  <div style="margin-top:24px;padding-top:14px;border-top:1px solid #cbd5e1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:11px;color:#64748b;line-height:1.5;letter-spacing:.3px;text-align:center">
    <strong style="color:#0f172a;font-size:12px;letter-spacing:1px">CAPITAL NORVEX INC.</strong><br>
    2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
    Téléphone : 1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
  </div>
</body></html>`;

  const sgKey = process.env.SENDGRID_API_KEY;
  if (!sgKey) return { sent: false, reason: "SENDGRID_API_KEY not set" };

  // Envoi 1 : Partenaire
  await fetch("https://api.sendgrid.com/v3/mail/send", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${sgKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      personalizations: [{ to: [{ email: partnerEmail, name: partnerName }] }],
      from: { email: ORGANIZER_EMAIL, name: "Capital Norvex" },
      reply_to: { email: ORGANIZER_EMAIL, name: "Yves Barrette" },
      subject: partnerSubject,
      content: [{ type: "text/html", value: partnerHtml }],
      tracking_settings: {
        click_tracking: { enable: false, enable_text: false },
        open_tracking: { enable: false },
      },
    }),
  });

  // Envoi 2 : Yves
  await fetch("https://api.sendgrid.com/v3/mail/send", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${sgKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      personalizations: [{ to: [{ email: ORGANIZER_EMAIL, name: "Yves Barrette" }] }],
      from: { email: ORGANIZER_EMAIL, name: "Norvex Agents" },
      subject: `[RDV PARTENAIRE] ${partnerName} — ${cap(dateStr)} ${startStr}`,
      content: [{ type: "text/html", value: yvesHtml }],
    }),
  });

  return { sent: true };
}

async function updateTargetFirestore(sa, fsToken, targetId, params) {
  const projectId = sa.project_id;
  const collection = params.collection || "capitalTargets";
  const docUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collection}/${targetId}`;

  const updateFields = {
    rdvBooked: { booleanValue: true },
    rdvBookedAt: { timestampValue: new Date().toISOString() },
    rdvSlot: {
      mapValue: {
        fields: {
          start: { timestampValue: params.startUtc.toISOString() },
          end: { timestampValue: params.endUtc.toISOString() },
          contactEmail: { stringValue: params.contactEmail },
          contactName: { stringValue: params.contactName },
          eventId: { stringValue: params.eventId || "" },
          joinUrl: { stringValue: params.joinUrl || "" },
        },
      },
    },
    status: { stringValue: "rdv_booked" },
  };
  const maskQuery = Object.keys(updateFields)
    .map((k) => `updateMask.fieldPaths=${k}`)
    .join("&");

  await fetch(`${docUrl}?${maskQuery}&currentDocument.exists=true`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${fsToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ fields: updateFields }),
  });
}

// ── Handler ───────────────────────────────────────────────────────────────
export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  }
  if (req.method !== "POST") return json({ error: "Method Not Allowed" }, 405);

  let body;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON" }, 400);
  }

  const { token, slotStart, slotEnd, contactEmail, contactName, contactPhone } = body;
  if (!token || !slotStart || !slotEnd || !contactEmail || !contactName) {
    return json({ error: "Missing required fields" }, 400);
  }

  // Email validation basique
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contactEmail)) {
    return json({ error: "Invalid email format" }, 400);
  }

  const startUtc = new Date(slotStart);
  const endUtc = new Date(slotEnd);
  if (
    isNaN(startUtc.getTime()) ||
    isNaN(endUtc.getTime()) ||
    startUtc >= endUtc ||
    startUtc.getTime() < Date.now() + 30 * 60 * 1000
  ) {
    return json({ error: "Invalid slot times" }, 400);
  }

  // 1. Verify token
  const secret = process.env.INTERNAL_SECRET;
  if (!secret) return json({ error: "Server misconfigured" }, 500);

  const payload = await verifyToken(token, secret);
  if (!payload) return json({ error: "Invalid or expired token" }, 401);
  if (payload.k !== "partner")
    return json({ error: "Token kind mismatch" }, 403);

  const targetId = payload.t;
  const lang = payload.l || "fr";

  // 2. Read target
  const { getServiceAccount } = await import("./_firebase-sa.mjs");

  let sa;

  try { sa = await getServiceAccount(); }

  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  let fsToken;
  try {
    fsToken = await getFirestoreToken(sa);
  } catch (e) {
    return json({ error: "Firestore auth failed: " + e.message }, 500);
  }

  const projectId = sa.project_id;
  // Fallback collections: capitalTargets → advisorTargets → promoteurTargets
  const COLLECTIONS = ["capitalTargets", "advisorTargets", "promoteurTargets"];
  let doc = null;
  let foundCollection = "capitalTargets";
  for (const col of COLLECTIONS) {
    const tryUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${col}/${targetId}`;
    const r = await fetch(tryUrl, { headers: { Authorization: `Bearer ${fsToken}` } });
    if (r.ok) { doc = await r.json(); foundCollection = col; break; }
  }
  if (!doc) return json({ error: "Target not found" }, 404);
  const f = doc.fields || {};
  const str = (x) => x?.stringValue || "";
  const partnerName = str(f.name) || str(f.companyName) || contactName;
  const organization = str(f.organization);

  // Bloquer si déjà booké
  if (f.rdvBooked?.booleanValue === true) {
    return json({ error: "RDV already booked for this target" }, 409);
  }

  // 3. Verify slot still free
  let graphToken;
  try {
    graphToken = await getGraphToken();
  } catch (e) {
    return json({ error: e.message }, 500);
  }

  const stillFree = await checkSlotStillFree(graphToken, startUtc, endUtc);
  if (!stillFree) {
    return json({ error: "Slot no longer available, please pick another" }, 409);
  }

  // 4. Create Teams event
  let event;
  try {
    event = await createTeamsEvent(graphToken, {
      startUtc,
      endUtc,
      partnerName,
      partnerEmail: contactEmail,
      organization,
      lang,
    });
  } catch (e) {
    return json({ error: "Event creation failed: " + e.message }, 500);
  }

  // 5. Send confirmation emails (best-effort, ne bloque pas en cas d'échec)
  let emailResult;
  try {
    emailResult = await sendConfirmationEmails({
      partnerEmail: contactEmail,
      partnerName,
      startUtc,
      endUtc,
      joinUrl: event.joinUrl,
      organization,
      lang,
    });
  } catch (e) {
    emailResult = { sent: false, reason: e.message };
  }

  // 6. Update Firestore
  try {
    await updateTargetFirestore(sa, fsToken, targetId, {
      startUtc,
      endUtc,
      contactEmail,
      contactName,
      eventId: event.eventId,
      joinUrl: event.joinUrl,
      collection: foundCollection,
    });
  } catch (e) {
    console.error("Firestore update failed:", e.message);
  }

  // 🎯 Émile (NORVEX BRIEFING™) — fire-and-forget
  try {
    const internalSecret = process.env.INTERNAL_SECRET || "";
    const baseUrl = process.env.URL || "https://capitalnorvex.com";
    fetch(`${baseUrl}/api/emile-generate-brief`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-internal-secret": internalSecret },
      body: JSON.stringify({
        email: contactEmail,
        rdvDateTime: slotStart,
        source: "rdv-partenaire-book",
      }),
    }).catch((e) => console.warn("[Émile trigger] failed:", e.message));
  } catch {}

  return json({
    ok: true,
    eventId: event.eventId,
    joinUrl: event.joinUrl,
    emailSent: emailResult.sent,
  });
};
