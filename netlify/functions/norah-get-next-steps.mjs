/**
 * POST /.netlify/functions/norah-get-next-steps
 * Header: X-Internal-Secret
 * Body: { caller_phone, dossier_id }
 *
 * Tool ElevenLabs #5 — get_next_steps
 *
 * Retourne la prochaine étape attendue dans le pipeline 8 étapes:
 *   1. Soumission → 2. Analyse préliminaire → 3. LOI → 4. Collecte doc
 *   → 5. Analyse complète → 6. Approbation finale → 7. Notaire → 8. Déboursé
 *
 * Norah donne UN FAIT (l'étape suivante), JAMAIS une décision.
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

const PIPELINE_STEPS = [
  { id: 1, code: "soumission", label: "Soumission" },
  { id: 2, code: "analyse_preliminaire", label: "Analyse préliminaire (30 min)" },
  { id: 3, code: "loi", label: "Lettre d'intérêt (LOI)" },
  { id: 4, code: "collecte_documentaire", label: "Collecte documentaire" },
  { id: 5, code: "analyse_complete", label: "Analyse complète" },
  { id: 6, code: "approbation_finale", label: "Approbation finale" },
  { id: 7, code: "notaire", label: "Notaire & signature" },
  { id: 8, code: "debourse", label: "Déboursé" },
];

// Mapping des stages legacy vers les étapes 1-8
const LEGACY_STAGE_MAP = {
  nouvelle: 1,
  analyse: 2,
  loi: 3,
  collecte: 4,
  approuve: 6,
  approuvé: 6,
  notaire: 7,
  closed: 8,
  ferme: 8,
};

function findCurrentStep(dossier) {
  // Priorité 1: champ explicite
  if (dossier.etape_actuelle) {
    const code = String(dossier.etape_actuelle).toLowerCase();
    const step = PIPELINE_STEPS.find((s) => s.code === code || s.label.toLowerCase() === code);
    if (step) return step;
  }
  // Priorité 2: stage legacy
  if (dossier.stage) {
    const stage = String(dossier.stage).toLowerCase();
    const stepId = LEGACY_STAGE_MAP[stage];
    if (stepId) return PIPELINE_STEPS.find((s) => s.id === stepId);
  }
  // Default: étape 1
  return PIPELINE_STEPS[0];
}

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

  const current = findCurrentStep(dossier);
  const next = PIPELINE_STEPS.find((s) => s.id === current.id + 1) || null;

  return json({
    ok: true,
    etape_actuelle: { id: current.id, code: current.code, label: current.label },
    prochaine_etape: next ? { id: next.id, code: next.code, label: next.label } : null,
    pipeline_complet: !next,
  });
};
