/**
 * GET /.netlify/functions/norah-dashboard-data?range=today|week|all
 * Header: X-Internal-Secret
 *
 * Endpoint backend pour le dashboard Norah (capital-norvex-norah.html).
 * Retourne:
 *   - Stats du jour / semaine / total
 *   - Liste des appels (max 100, ordre desc)
 *   - Alertes VIP en attente
 *   - Rappels en attente
 */

import {
  json,
  unauthorized,
  serverError,
  checkInternalSecret,
  firestoreList,
} from "./_norah-shared.mjs";

export default async (req) => {
  if (!checkInternalSecret(req)) return unauthorized();

  const url = new URL(req.url);
  const range = url.searchParams.get("range") || "today";

  let since = new Date();
  if (range === "today") {
    since.setHours(0, 0, 0, 0);
  } else if (range === "week") {
    since.setDate(since.getDate() - 7);
  } else if (range === "all") {
    since = new Date(2020, 0, 1);
  } else {
    since.setHours(0, 0, 0, 0);
  }

  const errors = [];
  let appels = [];
  let alertes = [];
  let rappels = [];

  try {
    appels = await firestoreList("appels", {
      sinceField: "created_at",
      sinceDate: since,
      limit: 100,
    });
  } catch (e) {
    errors.push("appels: " + e.message);
  }

  try {
    alertes = await firestoreList("notifications", {
      sinceField: "created_at",
      sinceDate: since,
      limit: 50,
    });
  } catch (e) {
    errors.push("notifications: " + e.message);
  }

  try {
    rappels = await firestoreList("appels_rappels", {
      sinceField: "created_at",
      sinceDate: since,
      limit: 50,
    });
  } catch (e) {
    errors.push("rappels: " + e.message);
  }

  // Tri par created_at desc (pour pas dépendre d'index Firestore)
  const sortDesc = (a, b) => {
    const ta = a.created_at ? new Date(a.created_at).getTime() : 0;
    const tb = b.created_at ? new Date(b.created_at).getTime() : 0;
    return tb - ta;
  };
  appels.sort(sortDesc);
  alertes.sort(sortDesc);
  rappels.sort(sortDesc);

  // Stats
  const stats = {
    total: appels.length,
    qualified: appels.filter((a) => a.qualified).length,
    vip: alertes.length,
    rappels_pending: rappels.filter((r) => r.status === "pending").length,
  };

  // Top scénarios
  const byScenario = {};
  for (const a of appels) {
    const s = a.scenario || "autre";
    byScenario[s] = (byScenario[s] || 0) + 1;
  }
  const topScenarios = Object.entries(byScenario)
    .sort((a, b) => b[1] - a[1])
    .map(([scenario, count]) => ({ scenario, count }));

  return json({
    ok: true,
    range,
    since: since.toISOString(),
    stats,
    top_scenarios: topScenarios,
    appels,
    alertes,
    rappels,
    errors: errors.length ? errors : undefined,
  });
};
