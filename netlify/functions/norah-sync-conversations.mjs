/**
 * SCHEDULED FUNCTION — toutes les 10 minutes
 *
 * Sync robuste ElevenLabs → Firestore `appels`. Fallback indépendant de Norah :
 * peu importe si elle appelle log_call ou pas à la fin d'une conversation,
 * cette fonction garantit que chaque conv ElevenLabs apparaît dans le dashboard.
 *
 * Logique :
 *   1. List dernières 50 conversations Norah ElevenLabs (24h glissantes)
 *   2. Pour chaque conv : check si conv_id déjà dans Firestore `appels`
 *   3. Sinon → fetch transcript complet → create doc Firestore avec scénario "autre"
 *   4. Si conv qualifiée (durée > 30s et > 4 messages user) → flag pour review Yves
 *
 * Créé 2026-05-27 PM après diagnostic : Norah n'appelle pas log_call fiable (LLM
 * dit « je vais logger » sans appeler le tool). Solution : ne pas dépendre d'elle.
 */
import {
  json,
  firestoreCreate,
  sendgridSend,
  YVES_EMAIL,
} from "./_norah-shared.mjs";

const ELEVENLABS_API_KEY = process.env.ELEVENLABS_API_KEY;
const AGENT_ID = "agent_0601kqmazb5aev48s2n87d0gevfw";
const FIRESTORE_PROJECT_ID = process.env.FIREBASE_PROJECT_ID || "capital-norvex";

export const config = {
  // SAFETY NET seulement — 2 runs/jour (matin + fin journée EDT, jamais la nuit)
  // Voie principale = Post-Call Webhook ElevenLabs (event-driven, déclenché à chaque
  // fin d'appel — zéro polling, zéro gaspillage de coût).
  // Cette scheduled function ne catche que les appels que le webhook aurait raté.
  schedule: "0 12,22 * * *", // 8h00 EDT + 18h00 EDT (12h00 + 22h00 UTC)
};

async function listRecentConversations() {
  const url = `https://api.elevenlabs.io/v1/convai/conversations?agent_id=${AGENT_ID}&page_size=50`;
  const r = await fetch(url, { headers: { "xi-api-key": ELEVENLABS_API_KEY } });
  if (!r.ok) throw new Error(`ElevenLabs list HTTP ${r.status}`);
  const data = await r.json();
  return data.conversations || [];
}

async function fetchConversation(conversationId) {
  const url = `https://api.elevenlabs.io/v1/convai/conversations/${conversationId}`;
  const r = await fetch(url, { headers: { "xi-api-key": ELEVENLABS_API_KEY } });
  if (!r.ok) throw new Error(`ElevenLabs fetch HTTP ${r.status}`);
  return await r.json();
}

async function getFirestoreToken() {
  const { getServiceAccount } = await import("./_firebase-sa.mjs");
  const sa = await getServiceAccount();
  const now = Math.floor(Date.now() / 1000);
  const jwtHeader = Buffer.from(JSON.stringify({ alg: "RS256", typ: "JWT" })).toString("base64url");
  const jwtPayload = Buffer.from(JSON.stringify({
    iss: sa.client_email,
    scope: "https://www.googleapis.com/auth/datastore",
    aud: "https://oauth2.googleapis.com/token",
    exp: now + 3600,
    iat: now,
  })).toString("base64url");
  const crypto = await import("crypto");
  const signer = crypto.createSign("RSA-SHA256");
  signer.update(`${jwtHeader}.${jwtPayload}`);
  const sig = signer.sign(sa.private_key, "base64url");
  const jwt = `${jwtHeader}.${jwtPayload}.${sig}`;
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=${jwt}`,
  });
  const t = await r.json();
  return t.access_token;
}

async function existingConversationIds(token) {
  // RunQuery pour chercher tous les conv_id existants dans appels
  const url = `https://firestore.googleapis.com/v1/projects/${FIRESTORE_PROJECT_ID}/databases/(default)/documents:runQuery`;
  const body = {
    structuredQuery: {
      from: [{ collectionId: "appels" }],
      select: { fields: [{ fieldPath: "conversation_id" }] },
      where: {
        fieldFilter: {
          field: { fieldPath: "created_at" },
          op: "GREATER_THAN",
          value: { timestampValue: new Date(Date.now() - 7 * 24 * 3600 * 1000).toISOString() },
        },
      },
    },
  };
  const r = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) return new Set();
  const data = await r.json();
  const ids = new Set();
  for (const row of data) {
    const cid = row?.document?.fields?.conversation_id?.stringValue;
    if (cid) ids.add(cid);
  }
  return ids;
}

function inferScenario(transcript) {
  const text = (transcript || []).map((m) => (m.message || "").toLowerCase()).join(" ");
  if (text.includes("courtier") && text.includes("dossier")) return "courtier_nouveau_dossier";
  if (text.includes("courtier")) return "courtier_verifie_statut";
  if (text.includes("promoteur") || text.includes("développ")) return "promoteur_premiere_fois";
  if (text.includes("notaire") || text.includes("closing")) return "notaire_closing";
  if (text.includes("avocat")) return "avocat_partenaire";
  if (text.includes("urgent") || text.includes("urgence")) return "urgence_closing";
  if (text.includes("yves") && text.includes("test")) return "autre"; // test Yves
  if (text.includes("information") || text.includes("infos")) return "info_generale";
  return "autre";
}

function summarizeTranscript(transcript) {
  const userMessages = (transcript || [])
    .filter((m) => m.role === "user" && (m.message || "").trim())
    .map((m) => m.message.trim());
  if (userMessages.length === 0) return "Aucun message audible de l'appelant.";
  return userMessages.slice(0, 3).join(" / ").slice(0, 600);
}

export default async (req) => {
  if (!ELEVENLABS_API_KEY) {
    return json({ error: "ELEVENLABS_API_KEY missing" }, 500);
  }

  const result = {
    synced: 0,
    already_existing: 0,
    errors: 0,
    new_calls: [],
  };

  try {
    const convs = await listRecentConversations();
    const token = await getFirestoreToken();
    const existing = await existingConversationIds(token);
    console.log(`[norah-sync] ${convs.length} convs ElevenLabs, ${existing.size} déjà dans Firestore`);

    // Filtrer dernières 24h
    const cutoff = Math.floor(Date.now() / 1000) - 24 * 3600;
    const recent = convs.filter((c) => (c.start_time_unix_secs || 0) > cutoff);

    for (const c of recent) {
      const cid = c.conversation_id;
      if (existing.has(cid)) {
        result.already_existing++;
        continue;
      }
      try {
        const full = await fetchConversation(cid);
        const meta = full.metadata || {};
        const phoneMeta = meta.phone_call || {};
        const transcript = full.transcript || [];
        const userMsgCount = transcript.filter((m) => m.role === "user").length;
        const durationSec = meta.call_duration_secs || 0;
        const qualified = durationSec > 30 && userMsgCount > 2;

        // Stocke transcript COMPLET pour affichage dashboard (chaque message role+text+timestamp)
        const transcript_full = transcript.map((m) => ({
          role: m.role || "?",
          message: (m.message || "").slice(0, 2000),
          time_in_call_secs: m.time_in_call_secs || null,
        })).filter((m) => m.message.trim().length > 0);

        const log = {
          conversation_id: cid,
          caller_phone: phoneMeta.external_number || phoneMeta.caller_id || "unknown",
          caller_role: null,
          caller_identified: false,
          dossier_id: null,
          scenario: inferScenario(transcript),
          summary: summarizeTranscript(transcript),
          action_taken: "Synchronisé automatiquement depuis ElevenLabs (norah-sync-conversations)",
          qualified,
          transcript_url: `https://elevenlabs.io/app/conversational-ai/history/${cid}`,
          transcript: transcript_full,                 // ⭐ transcript complet pour dashboard
          started_at: new Date((meta.start_time_unix_secs || 0) * 1000).toISOString(),
          ended_at: new Date(((meta.start_time_unix_secs || 0) + durationSec) * 1000).toISOString(),
          duration_sec: durationSec,
          source: "elevenlabs_sync_fallback",
          message_count: transcript.length,
          created_at: new Date(),
        };

        const doc = await firestoreCreate("appels", log);
        result.synced++;
        result.new_calls.push({ id: doc?.id, cid: cid.slice(0, 30), full_cid: cid, phone: log.caller_phone, duration: durationSec });
        console.log(`[norah-sync] ✅ ${cid.slice(0, 30)} → ${doc?.id} (${log.caller_phone}, ${durationSec}s)`);
      } catch (e) {
        result.errors++;
        console.error(`[norah-sync] ❌ ${cid}: ${e.message}`);
      }
    }

    // Si nouveaux appels qualifiés (clients réels) → email à Yves avec TRANSCRIPT complet
    const qualifiedNew = result.new_calls.filter((c) => c.duration > 30);
    if (qualifiedNew.length > 0) {
      // Re-fetch les transcripts complets pour chaque appel qualifié pour l'email
      const callsDetail = [];
      for (const c of qualifiedNew) {
        try {
          const url = `https://api.elevenlabs.io/v1/convai/conversations/${c.full_cid || c.cid}`;
          const r = await fetch(url, { headers: { "xi-api-key": ELEVENLABS_API_KEY } });
          if (r.ok) {
            const f = await r.json();
            callsDetail.push({
              phone: c.phone,
              duration: c.duration,
              cid: c.cid,
              transcript: f.transcript || [],
              scenario: f._scenario || "",
              summary: f._summary || "",
            });
          }
        } catch (_) {
          callsDetail.push({ phone: c.phone, duration: c.duration, cid: c.cid, transcript: [] });
        }
      }

      const buildTranscriptHtml = (transcript) => {
        if (!transcript || !transcript.length) return "<em>(transcript indisponible)</em>";
        return transcript.map((m) => {
          const role = (m.role || "?").toLowerCase();
          const txt = (m.message || "").trim();
          if (!txt) return "";
          const color = role === "agent" ? "#1a4587" : "#2a7a3f";
          const label = role === "agent" ? "Norah" : "Appelant";
          return `<div style="margin:6px 0;padding:6px 10px;background:${role==='agent'?'#f0f4f9':'#f0f9f4'};border-left:3px solid ${color}"><strong style="color:${color}">${label}:</strong> ${txt.replace(/[<>&]/g,c=>({"<":"&lt;",">":"&gt;","&":"&amp;"}[c]))}</div>`;
        }).join("");
      };

      const html = `
        <div style="font-family:Inter,Arial,sans-serif;max-width:700px">
          <div style="background:#0a0a0a;color:#c9a560;padding:16px 22px">
            <h2 style="margin:0">📞 ${qualifiedNew.length} appel(s) Norah détecté(s)</h2>
            <div style="font-size:12px;color:#d4c5a8;margin-top:4px">Sync automatique ElevenLabs → Firestore · ${new Date().toLocaleString("fr-CA",{timeZone:"America/Toronto"})}</div>
          </div>
          ${callsDetail.map((c) => `
            <div style="border:1px solid #e6dfd0;margin:16px 0;padding:16px;background:#fff">
              <h3 style="margin:0 0 8px;color:#8a6f2e">📞 ${c.phone} · ${c.duration}s</h3>
              <div style="font-size:12px;color:#6b5a3a;margin-bottom:10px">Conv ID: ${c.cid}…</div>
              <h4 style="margin:14px 0 6px;color:#1a1a1a;font-size:13px;text-transform:uppercase;letter-spacing:0.5px">Transcript</h4>
              ${buildTranscriptHtml(c.transcript)}
            </div>
          `).join("")}
          <p style="font-size:12px;color:#6b5a3a;text-align:center;margin-top:20px">Voir dashboard Capital Norvex Talk pour suivi.</p>
        </div>
      `;

      try {
        await sendgridSend({
          to: YVES_EMAIL,
          subject: `📞 ${qualifiedNew.length} appel Norah — ${qualifiedNew.map(c=>c.phone).join(", ")}`,
          html,
        });
      } catch (e) {
        console.error(`[norah-sync] email failed: ${e.message}`);
      }
    }

    return json({ ok: true, ...result });
  } catch (e) {
    console.error(`[norah-sync] fatal: ${e.message}`);
    return json({ error: e.message, partial: result }, 500);
  }
};
