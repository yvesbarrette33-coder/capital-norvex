/**
 * GET /api/espace-courtier-my-files
 * Header : Authorization: Bearer {sessionToken}
 *
 * Retourne les dossiers où referrerBrokerId == brokerId du sessionToken.
 *
 * Le courtier voit (Loi 25-safe) :
 *   - Statut du dossier
 *   - Montant + taux approuvé (si dispo)
 *   - Commission attendue
 *   - URL de la LOI (si disponible)
 *
 * Le courtier NE voit PAS :
 *   - Analyses internes (Hugo, Norvex Intel, Émile)
 *   - Documents personnels du client uploadés via Score Norvex
 *   - Communications internes
 */

import {
  json,
  requireSession,
  findDossiersByBrokerId,
} from "./_espace-courtier-shared.mjs";

const LOAN_TYPE_LABELS_FR = {
  acquisition: "Acquisition",
  construction: "Construction",
  refinancement: "Refinancement",
  terrain: "Terrain",
  "multi-residentielle": "Multi-résidentiel",
  commercial: "Commercial",
  autre: "Autre",
};

const STAGE_LABELS_FR = {
  submitted: "Soumis",
  docs: "Documents en attente",
  analyzing: "Analyse en cours",
  analysis: "Analyse en cours",
  loi_sent: "LOI envoyée",
  approved: "Approuvé",
  final: "Décision finale",
  rdv: "RDV en préparation",
  engagement: "Engagement signé",
  notary: "Chez le notaire",
  funded: "Décaissé",
  rejected: "Refusé",
  on_hold: "En attente",
};

function commissionEstimate(finalAmount, finalRate) {
  // Estimation indicative : 1 % du principal (variable selon convention courtier)
  if (!finalAmount) return null;
  return Math.round(finalAmount * 0.01);
}

export default async (req) => {
  if (req.method !== "GET" && req.method !== "POST") {
    return json({ error: "Method not allowed" }, 405);
  }

  const secret = process.env.INTERNAL_SECRET;
  if (!secret) return json({ error: "Server misconfigured" }, 500);

  // 1. Vérifier session
  const session = await requireSession(req, secret);
  if (!session.ok) return json({ error: "Unauthorized", reason: session.reason }, 401);

  // 2. Charger les dossiers (filtre referrerBrokerId)
  let dossiers;
  try {
    dossiers = await findDossiersByBrokerId(session.brokerId);
  } catch (err) {
    return json({ error: "Dossier lookup failed: " + err.message }, 500);
  }

  // 3. Filtrer + sanitiser les données (Loi 25 safe — pas d'analyses internes)
  const safe = (dossiers || []).map((d) => ({
    id: d.id,
    clientName: d.prenom && d.nom ? `${d.prenom} ${d.nom}` : (d.clientName || "—"),
    loanType: d.type || d.loanType || "",
    loanTypeLabel: LOAN_TYPE_LABELS_FR[d.type || d.loanType] || d.type || d.loanType || "—",
    province: d.province || "",
    requestedAmount: d.montant || d.loanAmount || d.requestedAmount || null,
    finalAmount: d.finalAmount || d.approvedAmount || null,
    finalRate: d.finalRate || null,
    expectedCommission: commissionEstimate(d.finalAmount || d.approvedAmount, d.finalRate),
    expectedFundingDate: d.expectedFundingDate || null,
    stage: d.stage || "submitted",
    stageLabel: STAGE_LABELS_FR[d.stage] || d.stage || "En cours",
    submittedAt: d.created_at || d.submittedAt || null,
    loiUrl: d.loiUrl || null, // URL Storage du PDF LOI si dispo
  }));

  return json({ ok: true, dossiers: safe, count: safe.length });
};

export const config = { path: "/api/espace-courtier-my-files" };
