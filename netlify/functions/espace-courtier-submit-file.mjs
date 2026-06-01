/**
 * POST /api/espace-courtier-submit-file
 * Header : Authorization: Bearer {sessionToken}
 * Body :
 *   {
 *     clientName, clientEmail, clientPhone, clientCompany,
 *     loanType, loanAmount, province, projectDescription, projectAddress
 *   }
 *
 * Crée un nouveau dossier dans Firestore avec :
 *   - referrerBrokerId = brokerId du courtier connecté
 *   - referrerBrokerCode = code du courtier
 *   - stage = "submitted" (en attente d'analyse)
 *   - source = "espace-courtier"
 *
 * Retourne : { ok:true, dossierId }
 *
 * Envoie aussi un courriel à Yves pour notification (TODO Phase B).
 */

import {
  json,
  requireSession,
  getBrokerById,
  createDossier,
} from "./_espace-courtier-shared.mjs";

const ALLOWED_LOAN_TYPES = [
  "acquisition",
  "construction",
  "refinancement",
  "terrain",
  "multi-residentielle",
  "commercial",
  "autre",
];

const ALLOWED_PROVINCES = ["QC", "ON"];

export default async (req) => {
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  const secret = process.env.INTERNAL_SECRET;
  if (!secret) return json({ error: "Server misconfigured" }, 500);

  // 1. Vérifier session
  const session = await requireSession(req, secret);
  if (!session.ok) return json({ error: "Unauthorized", reason: session.reason }, 401);

  // 2. Charger le broker (pour son code + nom)
  let broker;
  try {
    broker = await getBrokerById(session.brokerId);
  } catch (err) {
    return json({ error: "Broker lookup failed: " + err.message }, 500);
  }
  if (!broker) return json({ error: "Broker not found" }, 404);

  // 3. Parser et valider le body
  let body;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON body" }, 400);
  }

  const clientName = String(body.clientName || "").trim();
  const loanType = String(body.loanType || "").trim().toLowerCase();
  const loanAmount = Number(body.loanAmount) || 0;
  const province = String(body.province || "").trim().toUpperCase();
  const projectDescription = String(body.projectDescription || "").trim();

  if (!clientName) return json({ error: "clientName required" }, 400);
  if (!ALLOWED_LOAN_TYPES.includes(loanType)) {
    return json({ error: "Invalid loanType" }, 400);
  }
  if (!ALLOWED_PROVINCES.includes(province)) {
    return json({ error: "Invalid province" }, 400);
  }
  if (!projectDescription) {
    return json({ error: "projectDescription required" }, 400);
  }
  if (loanAmount < 0 || loanAmount > 500_000_000) {
    return json({ error: "Invalid loanAmount" }, 400);
  }

  // 4. Construire le dossier
  // On split clientName en prenom + nom basique pour compat avec le pipeline existant
  const parts = clientName.split(/\s+/);
  const prenom = parts[0] || clientName;
  const nom = parts.slice(1).join(" ") || "—";

  const now = new Date().toISOString();
  const dossierData = {
    // Champs standard du pipeline Norvex existant
    prenom,
    nom,
    courriel: String(body.clientEmail || "").trim().toLowerCase(),
    telephone: String(body.clientPhone || "").trim(),
    societe: String(body.clientCompany || "").trim(),
    type: loanType,
    montant: loanAmount,
    province,
    description: projectDescription,
    adresse: String(body.projectAddress || "").trim(),
    stage: "submitted",
    source: "espace-courtier",
    created_at: now,
    submittedAt: now,
    // Champs courtier-spécifiques
    referrerBrokerId: broker.id,
    referrerBrokerCode: broker.brokerNumber || broker.code || broker.id,
    referrerBrokerName: broker.name || broker.fullName || "",
    referrerBrokerAgency: broker.agency || broker.firmName || "",
    referrerBrokerEmail: broker.email || "",
    // Champs flags
    submittedByBroker: true,
    docsReceivedCount: 0,
    docsRequiredCount: 0,
  };

  // 5. Créer le dossier en Firestore
  let dossierId;
  try {
    dossierId = await createDossier(dossierData);
  } catch (err) {
    return json({ error: "Dossier creation failed: " + err.message }, 500);
  }

  return json({
    ok: true,
    dossierId,
    message: "Dossier créé. Vous le retrouvez dans Mes dossiers.",
  });
};

export const config = { path: "/api/espace-courtier-submit-file" };
