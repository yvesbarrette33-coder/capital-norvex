/**
 * Scheduled Function — Norvex Maestro™ Brief quotidien
 *
 * Cron : 45 11 * * *  (UTC) = 7h45 EDT (été) / 6h45 EST (hiver)
 *        → 15 minutes après brain-daily-brief (qui part à 7h00 EDT)
 *
 * Ce que fait ce brief :
 *   1. Lit `maestroDispatch` des 24 dernières heures
 *   2. Lit `maestroObservations` (alertes urgentes non vues)
 *   3. Lit le compte de drafts pending par agent (Camille/Sophie/Béatrice + transactions Karine)
 *   4. Génère un email synthèse HTML via Opus 4.6 (style Comité de direction)
 *   5. Envoie à yves@capitalnorvex.com via SendGrid
 *
 * Manuel : appel direct
 *   curl -H "x-internal-secret: $INTERNAL_SECRET" https://capitalnorvex.com/api/maestro-daily-brief
 *   curl -H "x-internal-secret: $INTERNAL_SECRET" "https://capitalnorvex.com/api/maestro-daily-brief?dry=1"  ← retourne le HTML sans envoyer
 */

const NEQ = "1182097890";

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
    iss: sa.client_email, sub: sa.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now, exp: now + 3600,
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
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5", privateKey, new TextEncoder().encode(signingInput)
  );
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: `${signingInput}.${sigB64}`,
    }),
  });
  const data = await r.json();
  if (!data.access_token) throw new Error("Firestore token failed");
  return { token: data.access_token, projectId: sa.project_id };
}

function fromFsValue(v) {
  if (!v) return null;
  if (v.nullValue !== undefined) return null;
  if (v.booleanValue !== undefined) return v.booleanValue;
  if (v.integerValue !== undefined) return Number(v.integerValue);
  if (v.doubleValue !== undefined) return v.doubleValue;
  if (v.stringValue !== undefined) return v.stringValue;
  if (v.timestampValue !== undefined) return v.timestampValue;
  if (v.arrayValue !== undefined) return (v.arrayValue.values || []).map(fromFsValue);
  if (v.mapValue !== undefined) {
    const out = {};
    for (const [k, val] of Object.entries(v.mapValue.fields || {})) out[k] = fromFsValue(val);
    return out;
  }
  return null;
}

function docToObj(doc) {
  if (!doc?.fields) return {};
  const out = {};
  for (const [k, v] of Object.entries(doc.fields)) out[k] = fromFsValue(v);
  return out;
}

async function listSince(projectId, token, collection, dateField, sinceIso, limit = 200) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;
  const r = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      structuredQuery: {
        from: [{ collectionId: collection }],
        where: {
          fieldFilter: {
            field: { fieldPath: dateField },
            op: "GREATER_THAN_OR_EQUAL",
            value: { stringValue: sinceIso },
          },
        },
        orderBy: [{ field: { fieldPath: dateField }, direction: "DESCENDING" }],
        limit,
      },
    }),
  });
  if (!r.ok) return [];
  const arr = await r.json();
  return (arr || []).filter(x => x.document).map(x => docToObj(x.document));
}

async function listByFilter(projectId, token, collection, fieldPath, op, value, limit = 100) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;
  const r = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      structuredQuery: {
        from: [{ collectionId: collection }],
        where: {
          fieldFilter: {
            field: { fieldPath },
            op,
            value: typeof value === "string" ? { stringValue: value } : { booleanValue: value },
          },
        },
        limit,
      },
    }),
  });
  if (!r.ok) return [];
  const arr = await r.json();
  return (arr || []).filter(x => x.document).map(x => docToObj(x.document));
}

const ROUTE_LABELS = {
  to_camille: "Camille (juridique)",
  to_sophie: "Sophie (relations)",
  to_beatrice: "Béatrice (exécutif)",
  to_karine: "Karine (finance)",
  to_hugo_pipeline: "Hugo (pipeline)",
  to_yves_directly: "Yves directement",
  alert_yves_priority: "URGENCES",
  ignore_no_reply: "Ignorés (no-reply)",
};

// ── Génération HTML brief ───────────────────────────────────────────
async function generateBriefHTML(stats) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) throw new Error("ANTHROPIC_API_KEY manquant");

  const dateFmt = new Date().toLocaleDateString("fr-CA", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });

  const userPayload = `Date du brief : ${dateFmt}

═══════════════════════════════════════════
ACTIVITÉ MAESTRO 24H DERNIÈRES
═══════════════════════════════════════════

Total emails routés : ${stats.totalDispatches}
Alertes urgentes : ${stats.alertsCount}

Répartition par spécialiste :
${Object.entries(stats.byRoute)
  .sort((a, b) => b[1] - a[1])
  .map(([r, c]) => `  - ${ROUTE_LABELS[r] || r} : ${c}`)
  .join("\n") || "  (aucun email routé)"}

Par boîte mail :
${Object.entries(stats.byMailbox)
  .map(([m, c]) => `  - ${m} : ${c}`)
  .join("\n") || "  (aucun)"}

Par priorité :
${Object.entries(stats.byPriority)
  .map(([p, c]) => `  - ${p} : ${c}`)
  .join("\n") || "  (aucune)"}

═══════════════════════════════════════════
DRAFTS EN ATTENTE D'APPROBATION
═══════════════════════════════════════════

- Camille (juridique) : ${stats.pendingDrafts.camille} drafts
- Sophie (relations) : ${stats.pendingDrafts.sophie} drafts
- Béatrice (exécutif) : ${stats.pendingDrafts.beatrice} drafts
- Karine (transactions pending) : ${stats.pendingDrafts.karine} transactions

═══════════════════════════════════════════
ALERTES URGENTES NON CONFIRMÉES
═══════════════════════════════════════════

${stats.recentAlerts.length === 0 ? "  Aucune alerte urgente." :
  stats.recentAlerts.map(a => `  - [${a.estimated_priority}] ${a.from}\n    « ${a.subject} »\n    ${a.summary || ""}`).join("\n\n")}

Génère le brief HTML niveau Comité de direction comme demandé dans ton system prompt.`;

  const systemPrompt = `Tu es **Norvex Maestro™**, méta-orchestrateur de Capital Norvex Inc. (NEQ ${NEQ}).

Tu produis le brief quotidien d'Yves Barrette (Directeur-Fondateur). Niveau Comité de direction. Style sobre, factuel, niveau institutionnel (Stikeman/BlackRock).

Tu dois générer un EMAIL HTML envoyé à yves@capitalnorvex.com avec ces sections :

1. **État de la circulation** (1 phrase) : "Hier, X emails analysés, Y drafts créés, état : sain / attention / alerte"
2. **À ton attention** : drafts en attente par agent, format compact
3. **Alertes & recommandations** : 3 plus importantes max, ou "Aucune alerte"
4. **Activité Maestro** : tableau routes × volumes 24h

Style HTML strict :
  - Police Georgia serif 14px line-height 1.6
  - Palette Norvex : or #c9a227, encre #1a1a1a, crème #fdfcf6
  - Pas de Markdown, pas d'émojis (sauf ⚠ pour alertes critiques)
  - Liens vers https://capitalnorvex.com/capital-norvex-brain.html#maestro
  - Signature "Norvex Maestro™ · Méta-orchestrateur · ${dateFmt}"
  - Maximum 600 mots
  - Tables HTML propres avec border-collapse:collapse, width:100%

Réponds UNIQUEMENT avec un objet JSON :
{
  "subject": "Norvex Maestro™ — Brief du [JJ MMMM]",
  "body_html": "<!DOCTYPE html>...",
  "alerts_count": ${stats.alertsCount}
}`;

  const r = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "claude-opus-4-6",
      max_tokens: 4000,
      system: systemPrompt,
      messages: [{ role: "user", content: userPayload }],
    }),
  });
  if (!r.ok) {
    const err = await r.text();
    throw new Error(`Anthropic ${r.status}: ${err.slice(0, 300)}`);
  }
  const data = await r.json();
  const raw = data.content?.[0]?.text?.trim() || "";
  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}");
  if (start === -1 || end === -1) {
    throw new Error("Brief non parsable");
  }
  return JSON.parse(raw.slice(start, end + 1));
}

async function sendBrief({ subject, html }) {
  const apiKey = process.env.SENDGRID_API_KEY;
  if (!apiKey) throw new Error("SENDGRID_API_KEY manquant");
  const r = await fetch("https://api.sendgrid.com/v3/mail/send", {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      personalizations: [{
        to: [{ email: "yves@capitalnorvex.com" }],
        subject,
      }],
      from: { email: "info@capitalnorvex.com", name: "Norvex Maestro™" },
      reply_to: { email: "yves@capitalnorvex.com" },
      content: [{ type: "text/html", value: html }],
      headers: {
        "X-Capital-Norvex-Type": "maestro-daily-brief",
        "X-Auto-Response-Suppress": "All",
      },
    }),
  });
  if (!r.ok) throw new Error(`SendGrid ${r.status}: ${await r.text()}`);
  return true;
}

export default async (req) => {
  // Cron Netlify scheduled : pas d'auth requise (Netlify trigger)
  // Manuel : x-internal-secret OBLIGATOIRE
  const secret = req.headers.get("x-internal-secret");
  const isCronTrigger = req.headers.get("x-netlify-functions-event-version") ||
                         req.headers.get("netlify-invocation-source") === "scheduled";
  if (!isCronTrigger) {
    if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
      return json({ error: "Unauthorized" }, 401);
    }
  }

  const url = new URL(req.url);
  const dryRun = url.searchParams.get("dry") === "1";

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let sa;


  try { sa = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  try {
    const { token, projectId } = await getFirestoreToken(sa);
    const sinceIso = new Date(Date.now() - 24 * 3600 * 1000).toISOString();

    // 1. Dispatches Maestro 24h
    const dispatches = await listSince(projectId, token, "maestroDispatch",
                                        "dispatchedAt", sinceIso, 300);
    const byRoute = {};
    const byMailbox = {};
    const byPriority = { low: 0, medium: 0, high: 0, critical: 0 };
    let alertsCount = 0;
    const recentAlerts = [];
    for (const d of dispatches) {
      byRoute[d.route || "unknown"] = (byRoute[d.route || "unknown"] || 0) + 1;
      byMailbox[d.mailbox || "?"] = (byMailbox[d.mailbox || "?"] || 0) + 1;
      const p = d.estimated_priority || "medium";
      byPriority[p] = (byPriority[p] || 0) + 1;
      if (d.alert_yves_now) {
        alertsCount += 1;
        if (recentAlerts.length < 5) {
          recentAlerts.push({
            from: d.from || "?",
            subject: d.subject || "",
            summary: d.summary || "",
            estimated_priority: d.estimated_priority || "medium",
          });
        }
      }
    }

    // 2. Drafts pending par agent
    const [camDrafts, sopDrafts, beaDrafts, karTx] = await Promise.all([
      listByFilter(projectId, token, "camilleDrafts", "status", "EQUAL",
                   "pending_yves_approval", 100),
      listByFilter(projectId, token, "sophieDrafts", "status", "EQUAL",
                   "pending_yves_approval", 100),
      listByFilter(projectId, token, "beatriceDrafts", "status", "EQUAL",
                   "pending_yves_approval", 100),
      listByFilter(projectId, token, "transactions", "statut", "EQUAL",
                   "pending", 100),
    ]);

    const stats = {
      totalDispatches: dispatches.length,
      byRoute,
      byMailbox,
      byPriority,
      alertsCount,
      recentAlerts,
      pendingDrafts: {
        camille: camDrafts.length,
        sophie: sopDrafts.length,
        beatrice: beaDrafts.length,
        karine: karTx.filter(t => t.source === "karine_norvex_finance").length,
      },
    };

    // 3. Génère HTML via Opus 4.6
    const brief = await generateBriefHTML(stats);

    if (dryRun) {
      return new Response(brief.body_html, {
        headers: { "Content-Type": "text/html; charset=utf-8" },
      });
    }

    // 4. Envoi SendGrid
    await sendBrief({ subject: brief.subject, html: brief.body_html });

    return json({
      ok: true,
      subject: brief.subject,
      stats,
      sentTo: "yves@capitalnorvex.com",
    });
  } catch (e) {
    return json({ error: e.message }, 500);
  }
};

export const config = {
  schedule: "45 11 * * *",  // 7h45 EDT (été) / 6h45 EST (hiver)
};
