/**
 * GET /.netlify/functions/rdv-partenaire-availability?token=XXX
 *
 * Page publique RDV Partenaire — appelée par rdv-partenaire.html
 *
 * 1. Vérifie le token HMAC (signé par INTERNAL_SECRET, payload = targetId/lang/exp/kind)
 * 2. Lit la cible Firestore (capitalTargets/{targetId}) pour récupérer le nom
 * 3. Interroge Graph free/busy pour yves@capitalnorvex.com (10 prochains jours ouvrables)
 * 4. Génère les créneaux selon les règles Yves Partenaires :
 *    - Lundi-vendredi
 *    - 9h00 → 21h00 (étendu pour les premières semaines)
 *    - Slots de 30 min
 *    - Buffer de 2h après now
 *    - Exclure les créneaux déjà occupés (busy/oof/tentative)
 * 5. Retourne JSON : { partner: {name, lang}, slots: [{start, end, label}], lang }
 */

const ORGANIZER_EMAIL = process.env.CAPITAL_NORVEX_ORGANIZER || "yves@capitalnorvex.com";
const TZ = "America/Toronto";
const SLOT_MINUTES = 30;
const LOOKAHEAD_DAYS = 14;
const BUFFER_HOURS = 2;

// Heures ouvrables étendues pour Partenaires (jusqu'à 21h les premières semaines)
const HOUR_START = 9;   // 9h00
const HOUR_END = 21;    // 21h00 (dernier slot commence à 20h30)

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store",
    },
  });
}

// ── HMAC verification ─────────────────────────────────────────────────────
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
  // Check expiration
  const now = Math.floor(Date.now() / 1000);
  if (payload.x && payload.x < now) return null;
  return payload;
}

function dataB64Pad(s) {
  // Add padding back for atob
  const pad = s.length % 4;
  return pad ? s + "=".repeat(4 - pad) : s;
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

// ── Graph token ───────────────────────────────────────────────────────────
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
    .filter(
      (x) => x.status === "busy" || x.status === "oof" || x.status === "tentative"
    )
    .map((x) => ({
      start: new Date(x.start.dateTime + "Z"),
      end: new Date(x.end.dateTime + "Z"),
    }));
}

// ── Slot generation ───────────────────────────────────────────────────────
function torontoOffsetMinutes(dateUtc) {
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: TZ,
    timeZoneName: "shortOffset",
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
  const guess = new Date(Date.UTC(year, month - 1, day, hour, minute, 0));
  const off = torontoOffsetMinutes(guess);
  return new Date(guess.getTime() - off * 60 * 1000);
}

function generateCandidateSlots(fromUtc) {
  // 14 jours d'avance, lundi-vendredi (1-5)
  const slots = [];
  // Slots de 30 min entre 9h00 et 21h00
  const startTimes = [];
  for (let h = HOUR_START; h < HOUR_END; h++) {
    startTimes.push([h, 0]);
    startTimes.push([h, 30]);
  }
  // Skip lunch noon-13h
  // (les RDV midi dérangent — on garde mais filtrera plus tard si besoin)

  const minTime = fromUtc.getTime() + BUFFER_HOURS * 60 * 60 * 1000;

  for (let i = 0; i < LOOKAHEAD_DAYS; i++) {
    const probe = new Date(fromUtc.getTime() + i * 86400000);
    const dowStr = new Intl.DateTimeFormat("en-US", {
      timeZone: TZ,
      weekday: "short",
    }).format(probe);
    const dowMap = { Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6, Sun: 0 };
    const localDow = dowMap[dowStr];
    if (![1, 2, 3, 4, 5].includes(localDow)) continue;

    const dateParts = new Intl.DateTimeFormat("en-CA", {
      timeZone: TZ,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).formatToParts(probe);
    const y = parseInt(dateParts.find((p) => p.type === "year").value, 10);
    const m = parseInt(dateParts.find((p) => p.type === "month").value, 10);
    const d = parseInt(dateParts.find((p) => p.type === "day").value, 10);

    for (const [h, mn] of startTimes) {
      const startUtc = buildLocalUtc(y, m, d, h, mn);
      if (startUtc.getTime() < minTime) continue;
      const endUtc = new Date(startUtc.getTime() + SLOT_MINUTES * 60 * 1000);
      slots.push({ start: startUtc, end: endUtc });
    }
  }
  return slots;
}

function slotIsFree(slot, busy) {
  for (const b of busy) {
    if (slot.start < b.end && slot.end > b.start) return false;
  }
  return true;
}

function formatSlot(slot, lang) {
  const isEn = lang === "en";
  const dayFmt = new Intl.DateTimeFormat(isEn ? "en-CA" : "fr-CA", {
    timeZone: TZ,
    weekday: "long",
    day: "numeric",
    month: "long",
  });
  const timeFmt = new Intl.DateTimeFormat(isEn ? "en-CA" : "fr-CA", {
    timeZone: TZ,
    hour: "2-digit",
    minute: "2-digit",
    hour12: isEn,
  });
  const dateStr = dayFmt.format(slot.start);
  const startStr = timeFmt.format(slot.start);
  const endStr = timeFmt.format(slot.end);
  const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
  return {
    dateLabel: cap(dateStr),
    timeLabel: `${startStr} – ${endStr}`,
    isoStart: slot.start.toISOString(),
    isoEnd: slot.end.toISOString(),
  };
}

// ── Handler ───────────────────────────────────────────────────────────────
export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  }
  if (req.method !== "GET") return json({ error: "Method Not Allowed" }, 405);

  const url = new URL(req.url);
  const token = url.searchParams.get("token");
  if (!token) return json({ error: "Missing token" }, 400);

  // 1. Verify token
  const secret = process.env.INTERNAL_SECRET;
  if (!secret) return json({ error: "Server misconfigured" }, 500);

  const payload = await verifyToken(token, secret);
  if (!payload) return json({ error: "Invalid or expired token" }, 401);
  if (payload.k !== "partner")
    return json({ error: "Token kind mismatch" }, 403);

  const targetId = payload.t;
  const lang = payload.l || "fr";

  // 2. Read target from Firestore
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
  let lastErr = "";
  for (const col of COLLECTIONS) {
    const tryUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${col}/${targetId}`;
    const r = await fetch(tryUrl, { headers: { Authorization: `Bearer ${fsToken}` } });
    if (r.ok) { doc = await r.json(); break; }
    lastErr = await r.text();
  }
  if (!doc) {
    return json({ error: "Target not found: " + lastErr }, 404);
  }
  const f = doc.fields || {};
  const str = (x) => x?.stringValue || "";
  const partnerName = str(f.name) || str(f.companyName) || "Partner";
  const organization = str(f.organization);

  // 3. Graph free/busy
  let graphToken;
  try {
    graphToken = await getGraphToken();
  } catch (e) {
    return json({ error: e.message }, 500);
  }

  const now = new Date();
  const horizon = new Date(now.getTime() + LOOKAHEAD_DAYS * 86400000);

  let busy;
  try {
    busy = await getBusyIntervals(graphToken, now, horizon);
  } catch (e) {
    return json({ error: e.message }, 500);
  }

  // 4. Generate available slots
  const candidates = generateCandidateSlots(now);
  const free = candidates.filter((s) => slotIsFree(s, busy));

  // Group by day
  const slotsByDay = {};
  for (const s of free) {
    const dayKey = new Intl.DateTimeFormat("en-CA", {
      timeZone: TZ,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(s.start);
    if (!slotsByDay[dayKey]) slotsByDay[dayKey] = [];
    slotsByDay[dayKey].push(formatSlot(s, lang));
  }

  // Limit to 5 days max, max 6 slots per day
  const days = Object.keys(slotsByDay)
    .sort()
    .slice(0, 5)
    .map((dayKey) => ({
      dateKey: dayKey,
      dateLabel: slotsByDay[dayKey][0].dateLabel,
      slots: slotsByDay[dayKey].slice(0, 6),
    }));

  return json({
    ok: true,
    partner: { name: partnerName, organization, lang },
    days,
    timezone: TZ,
    durationMinutes: SLOT_MINUTES,
  });
};
