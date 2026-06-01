/**
 * POST /.netlify/functions/norah-get-assigned-agent
 * Header: X-Internal-Secret
 * Body: { caller_phone, dossier_id }
 *
 * Tool ElevenLabs #6 — get_assigned_agent
 *
 * Retourne le nom et l'email de l'agent IA Analyste attitré au dossier.
 * Norah peut dire: "Votre dossier est suivi par [Agent], joignable au [email]."
 */

import {
  json,
  unauthorized,
  badRequest,
  serverError,
  checkInternalSecret,
  requireValidSession,
  firestoreGet,
  canCallerAccessDossier,
  normalizePhone,
} from "./_norah-shared.mjs";

const DEFAULT_AGENT = {
  nom: "L'équipe Capital Norvex",
  email: "info@capitalnorvex.com",
};

export default async (req) => {
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });
  if (!checkInternalSecret(req)) return unauthorized();

  let body;
  try { body = await req.json(); } catch { return badRequest("Invalid JSON body"); }

  const phone = normalizePhone(body.caller_phone);
  const dossierId = String(body.dossier_id || "").trim();
  if (!phone) return badRequest("caller_phone manquant");
  if (!dossierId) return badRequest("dossier_id manquant");

  let sessionCheck;
  try { sessionCheck = await requireValidSession(phone); }
  catch (e) { return serverError("Session check failed: " + e.message); }
  if (!sessionCheck.valid) return json({ ok: false, reason: sessionCheck.reason }, 403);

  let dossier;
  try { dossier = await firestoreGet("dossiers", dossierId); }
  catch (e) { return serverError("Firestore get failed: " + e.message); }
  if (!dossier) return json({ ok: false, reason: "dossier_introuvable" }, 404);
  if (!canCallerAccessDossier(sessionCheck.session, dossier)) {
    return json({ ok: false, reason: "acces_refuse" }, 403);
  }

  const nom = dossier.agent_attitre || dossier.assigned_agent || DEFAULT_AGENT.nom;
  const email = dossier.agent_email || dossier.assigned_agent_email || DEFAULT_AGENT.email;
  const last = dossier.derniere_communication || dossier.last_communication || null;

  return json({
    ok: true,
    agent: { nom, email },
    derniere_communication: last,
  });
};
