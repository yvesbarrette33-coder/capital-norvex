/**
 * POST /.netlify/functions/norah-webhook-postcall
 *
 * Endpoint reçu par ElevenLabs Post-Call Webhook (event-driven).
 * Déclenché AUTOMATIQUEMENT par ElevenLabs à la fin de chaque conversation.
 * → ZÉRO polling, ZÉRO gaspillage. La voie principale de capture des appels.
 *
 * Auth : HMAC signature ElevenLabs via header `ElevenLabs-Signature`
 *   (https://elevenlabs.io/docs/agents-platform/customization/agent-transfer/webhooks)
 *
 * Payload : ElevenLabs envoie l'objet conversation complet (metadata + transcript)
 *
 * Action : crée doc Firestore `appels` avec transcript complet + email alerte à Yves
 *
 * Configuration côté ElevenLabs (workspace settings) :
 *   - Webhook URL : https://capitalnorvex.com/.netlify/functions/norah-webhook-postcall
 *   - Event type : post_call_transcription
 *   - HMAC secret : à stocker dans Netlify env var ELEVENLABS_WEBHOOK_SECRET
 */
import crypto from "crypto";
import {
  json,
  badRequest,
  unauthorized,
  serverError,
  firestoreCreate,
  sendgridSend,
  YVES_EMAIL,
} from "./_norah-shared.mjs";

const WEBHOOK_SECRET = process.env.ELEVENLABS_WEBHOOK_SECRET;

function verifyHmac(rawBody, signatureHeader) {
  if (!WEBHOOK_SECRET) return true; // mode permissif si secret pas encore configuré
  if (!signatureHeader) return false;
  // Format ElevenLabs : "t=TIMESTAMP,v0=HEX_SIGNATURE"
  const parts = signatureHeader.split(",").reduce((acc, p) => {
    const [k, v] = p.split("=");
    if (k && v) acc[k.trim()] = v.trim();
    return acc;
  }, {});
  const timestamp = parts.t;
  const sig = parts.v0;
  if (!timestamp || !sig) return false;
  const expected = crypto.createHmac("sha256", WEBHOOK_SECRET)
    .update(`${timestamp}.${rawBody}`).digest("hex");
  try {
    return crypto.timingSafeEqual(Buffer.from(sig, "hex"), Buffer.from(expected, "hex"));
  } catch {
    return false;
  }
}

function inferScenario(transcript) {
  const text = (transcript || []).map((m) => (m.message || "").toLowerCase()).join(" ");
  if (text.includes("courtier") && text.includes("dossier")) return "courtier_nouveau_dossier";
  if (text.includes("courtier")) return "courtier_verifie_statut";
  if (text.includes("promoteur") || text.includes("développ")) return "promoteur_premiere_fois";
  if (text.includes("notaire") || text.includes("closing")) return "notaire_closing";
  if (text.includes("avocat")) return "avocat_partenaire";
  if (text.includes("urgent") || text.includes("urgence")) return "urgence_closing";
  if (text.includes("information") || text.includes("infos")) return "info_generale";
  return "autre";
}

function summarize(transcript) {
  const msgs = (transcript || [])
    .filter((m) => m.role === "user" && (m.message || "").trim())
    .map((m) => m.message.trim());
  if (!msgs.length) return "Aucun message audible de l'appelant.";
  return msgs.slice(0, 3).join(" / ").slice(0, 600);
}

function buildTranscriptHtml(transcript) {
  if (!transcript?.length) return "<em>(transcript vide)</em>";
  return transcript.map((m) => {
    const role = (m.role || "?").toLowerCase();
    const txt = (m.message || "").trim();
    if (!txt) return "";
    const color = role === "agent" ? "#1a4587" : "#2a7a3f";
    const bg = role === "agent" ? "#f0f4f9" : "#f0f9f4";
    const label = role === "agent" ? "Norah" : "Appelant";
    const safe = txt.replace(/[<>&]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c]));
    return `<div style="margin:6px 0;padding:6px 10px;background:${bg};border-left:3px solid ${color}"><strong style="color:${color}">${label}:</strong> ${safe}</div>`;
  }).join("");
}

export default async (req) => {
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  const rawBody = await req.text();
  const sigHeader = req.headers.get("elevenlabs-signature") || req.headers.get("ElevenLabs-Signature");
  if (!verifyHmac(rawBody, sigHeader)) {
    console.error("[norah-webhook] HMAC verification failed");
    return unauthorized();
  }

  let payload;
  try { payload = JSON.parse(rawBody); } catch { return badRequest("Invalid JSON"); }

  // ElevenLabs envoie : { type: "post_call_transcription", data: { conversation_id, agent_id, transcript, metadata, ... } }
  const eventType = payload.type || "";
  const data = payload.data || payload;
  const cid = data.conversation_id || data.conversation_initiation_client_data?.conversation_id;

  if (!eventType.includes("post_call") && !cid) {
    return json({ ok: true, skipped: "not post_call_transcription event" });
  }

  const transcript = data.transcript || [];
  const meta = data.metadata || {};
  const phoneMeta = meta.phone_call || data.phone_call || {};
  const callerPhone = phoneMeta.external_number || phoneMeta.caller_id || "unknown";
  const durationSec = meta.call_duration_secs || data.call_duration_secs || 0;
  const userMsgs = transcript.filter((m) => m.role === "user").length;
  const qualified = durationSec > 30 && userMsgs > 2;

  const transcript_full = transcript.map((m) => ({
    role: m.role || "?",
    message: (m.message || "").slice(0, 2000),
    time_in_call_secs: m.time_in_call_secs || null,
  })).filter((m) => m.message.trim().length > 0);

  const log = {
    conversation_id: cid,
    caller_phone: callerPhone,
    caller_role: null,
    caller_identified: false,
    dossier_id: null,
    scenario: inferScenario(transcript),
    summary: summarize(transcript),
    action_taken: "Webhook ElevenLabs Post-Call (event-driven)",
    qualified,
    transcript_url: cid ? `https://elevenlabs.io/app/conversational-ai/history/${cid}` : null,
    transcript: transcript_full,
    started_at: meta.start_time_unix_secs ? new Date(meta.start_time_unix_secs * 1000).toISOString() : new Date().toISOString(),
    ended_at: meta.start_time_unix_secs ? new Date((meta.start_time_unix_secs + durationSec) * 1000).toISOString() : new Date().toISOString(),
    duration_sec: durationSec,
    source: "elevenlabs_webhook_postcall",
    message_count: transcript.length,
    created_at: new Date(),
  };

  let doc;
  try {
    doc = await firestoreCreate("appels", log);
  } catch (e) {
    return serverError("Firestore create failed: " + e.message);
  }

  // Si qualifié → email à Yves avec transcript complet
  if (qualified) {
    try {
      await sendgridSend({
        to: YVES_EMAIL,
        subject: `📞 Appel Norah — ${callerPhone} (${durationSec}s)`,
        html: `
          <div style="font-family:Inter,Arial,sans-serif;max-width:700px">
            <div style="background:#0a0a0a;color:#c9a560;padding:16px 22px">
              <h2 style="margin:0">📞 Nouvel appel Norah</h2>
              <div style="font-size:12px;color:#d4c5a8;margin-top:4px">Webhook ElevenLabs · ${new Date().toLocaleString("fr-CA",{timeZone:"America/Toronto"})}</div>
            </div>
            <div style="border:1px solid #e6dfd0;margin:16px 0;padding:16px;background:#fff">
              <h3 style="margin:0 0 8px;color:#8a6f2e">📞 ${callerPhone} · ${durationSec}s · ${log.scenario.replaceAll("_"," ")}</h3>
              <div style="font-size:12px;color:#6b5a3a;margin-bottom:10px">Conv ID: ${cid}</div>
              <h4 style="margin:14px 0 6px;color:#1a1a1a;font-size:13px;text-transform:uppercase">Transcript</h4>
              ${buildTranscriptHtml(transcript_full)}
            </div>
          </div>`,
      });
    } catch (e) {
      console.error("[norah-webhook] email failed:", e.message);
    }
  }

  return json({ ok: true, appel_id: doc?.id, qualified, message_count: transcript_full.length });
};
