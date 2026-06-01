// Norvex Visibility — Aggregates SendGrid Email Activity (last N days)
// GET /api/visibility-snapshot?days=14
// Returns: { totals, topClickers, topOpeners, recent }
// Auth: x-internal-secret header

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });

// Bot UA patterns (same logic as Python top_humains_snapshot.py)
const BOT_UA_PATTERNS = [
  "fortimail", "fortinet", "fortigate", "barracuda",
  "proofpoint", "mimecast", "microsoft outlook", "outlook protect",
  "googleimageproxy", "google image proxy",
  "yahoomailproxy", "yahoo! mail proxy",
  "applemail-imageproxy", "apple mail",
  "spamtitan", "ironport", "symantec", "trend micro",
];

function isBotUA(ua) {
  if (!ua) return true;
  const low = ua.toLowerCase();
  for (const p of BOT_UA_PATTERNS) if (low.includes(p)) return true;
  return false;
}

async function fetchSendGridMessages(query, apiKey, limit = 1000) {
  const url = `https://api.sendgrid.com/v3/messages?query=${encodeURIComponent(query)}&limit=${Math.min(limit, 1000)}`;
  const r = await fetch(url, {
    headers: { Authorization: `Bearer ${apiKey}` },
  });
  if (!r.ok) {
    const txt = await r.text();
    throw new Error(`SendGrid ${r.status}: ${txt.slice(0, 200)}`);
  }
  const data = await r.json();
  return data.messages || [];
}

async function fetchSendGridEvents(msgId, apiKey) {
  const url = `https://api.sendgrid.com/v3/messages/${msgId}`;
  const r = await fetch(url, {
    headers: { Authorization: `Bearer ${apiKey}` },
  });
  if (!r.ok) return { events: [] };
  return await r.json();
}

export default async function handler(req) {
  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return json({ error: "Unauthorized" }, 401);
  }

  const apiKey = process.env.SENDGRID_API_KEY;
  if (!apiKey) return json({ error: "SENDGRID_API_KEY missing" }, 500);

  const url = new URL(req.url);
  const days = Math.max(1, Math.min(parseInt(url.searchParams.get("days") || "14", 10), 30));
  const detailed = url.searchParams.get("detailed") === "1";

  const now = new Date();
  const startTs = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
  const startISO = startTs.toISOString().split("T")[0];
  const endISO = now.toISOString().split("T")[0];

  const query = `last_event_time > TIMESTAMP "${startISO}T00:00:00Z" AND last_event_time < TIMESTAMP "${endISO}T23:59:59Z"`;

  try {
    const allMsgs = await fetchSendGridMessages(query, apiKey, 1000);
    const engaged = allMsgs.filter(
      m => (m.opens_count || 0) > 0 || (m.clicks_count || 0) > 0
    );

    // Aggregate per recipient (message-level counts, no UA filter unless detailed)
    const perEmail = {};
    for (const m of engaged) {
      const email = (m.to_email || "").toLowerCase();
      if (!email) continue;
      if (!perEmail[email]) {
        perEmail[email] = {
          email,
          rawOpens: 0,
          rawClicks: 0,
          humanOpens: 0,
          humanClicks: 0,
          uas: new Set(),
          lastEventAt: null,
          subjects: new Set(),
          fromEmails: new Set(),
        };
      }
      const e = perEmail[email];
      e.rawOpens += m.opens_count || 0;
      e.rawClicks += m.clicks_count || 0;
      if (m.subject) e.subjects.add(m.subject);
      if (m.from_email) e.fromEmails.add(m.from_email);
      if (m.last_event_time) {
        if (!e.lastEventAt || m.last_event_time > e.lastEventAt) {
          e.lastEventAt = m.last_event_time;
        }
      }
    }

    // Optional: detailed mode fetches per-message events for human filtering
    if (detailed) {
      // Limit to top 50 by raw activity to keep timeout
      const top = Object.values(perEmail)
        .sort((a, b) => (b.rawClicks * 10 + b.rawOpens) - (a.rawClicks * 10 + a.rawOpens))
        .slice(0, 50);
      const topEmails = new Set(top.map(t => t.email));

      // Fetch events for messages of those top emails
      const promises = engaged
        .filter(m => topEmails.has((m.to_email || "").toLowerCase()))
        .slice(0, 100) // hard cap
        .map(m => fetchSendGridEvents(m.msg_id, apiKey).then(details => ({ msg: m, details })));

      const results = await Promise.allSettled(promises);
      for (const r of results) {
        if (r.status !== "fulfilled") continue;
        const { msg, details } = r.value;
        const email = (msg.to_email || "").toLowerCase();
        const bucket = perEmail[email];
        if (!bucket) continue;
        for (const ev of details.events || []) {
          if (ev.event_name === "open" && !isBotUA(ev.user_agent || "")) {
            bucket.humanOpens += 1;
            if (ev.user_agent) bucket.uas.add(ev.user_agent);
          } else if (ev.event_name === "click" && !isBotUA(ev.user_agent || "")) {
            bucket.humanClicks += 1;
            if (ev.user_agent) bucket.uas.add(ev.user_agent);
          }
        }
      }
    }

    // Build final lists
    const list = Object.values(perEmail).map(e => ({
      email: e.email,
      rawOpens: e.rawOpens,
      rawClicks: e.rawClicks,
      humanOpens: e.humanOpens,
      humanClicks: e.humanClicks,
      uniqueUAs: e.uas.size,
      lastEventAt: e.lastEventAt,
      subject: Array.from(e.subjects)[0] || "",
      fromEmail: Array.from(e.fromEmails)[0] || "",
    }));

    const topClickers = [...list]
      .filter(e => (detailed ? e.humanClicks : e.rawClicks) > 0)
      .sort((a, b) => (detailed ? b.humanClicks - a.humanClicks : b.rawClicks - a.rawClicks))
      .slice(0, 30);

    const topOpeners = [...list]
      .filter(e => (detailed ? e.humanOpens : e.rawOpens) > 0)
      .sort((a, b) => (detailed ? b.humanOpens - a.humanOpens : b.rawOpens - a.rawOpens))
      .slice(0, 30);

    const recent = [...list]
      .filter(e => e.lastEventAt)
      .sort((a, b) => (b.lastEventAt || "").localeCompare(a.lastEventAt || ""))
      .slice(0, 50);

    const totals = {
      totalMessagesScanned: allMsgs.length,
      totalEngagedMessages: engaged.length,
      totalRecipientsWithActivity: list.length,
      totalRawOpens: list.reduce((s, e) => s + e.rawOpens, 0),
      totalRawClicks: list.reduce((s, e) => s + e.rawClicks, 0),
      totalHumanOpens: list.reduce((s, e) => s + e.humanOpens, 0),
      totalHumanClicks: list.reduce((s, e) => s + e.humanClicks, 0),
      windowDays: days,
      windowStart: startISO,
      windowEnd: endISO,
      detailed,
      generatedAt: new Date().toISOString(),
    };

    return json({ totals, topClickers, topOpeners, recent });
  } catch (e) {
    return json({ error: String(e.message || e) }, 500);
  }
}

export const config = { path: "/api/visibility-snapshot" };
