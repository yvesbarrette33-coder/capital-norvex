/**
 * /api/beatrice-toggle-mobile-mode
 *
 * GET  → lit l'état actuel  { mobile_mode: bool, updatedAt, updatedBy }
 * POST → met à jour          body: { mobile_mode: bool }
 *
 * Header: X-Internal-Secret
 *
 * Stocké dans Firestore : system/beatrice_settings
 *
 * Quand mobile_mode = true, l'orchestrateur Béatrice envoie aussi un SMS
 * à Yves (via Twilio) en plus de l'email d'approbation habituel. Yves peut
 * tap les liens HMAC depuis son iPhone sans ouvrir le dashboard.
 */

import {
  getDoc,
  getFirestoreToken,
  jsonResponse,
  loadServiceAccount,
  patchDoc,
} from "./_camille-shared.mjs";

const COLLECTION = "system";
const DOC_ID = "beatrice_settings";

export default async function handler(req) {
  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return jsonResponse({ error: "Unauthorized" }, 401);
  }

  try {
    const sa = await loadServiceAccount();
    const projectId = sa.project_id;
    const fsToken = await getFirestoreToken(sa);

    if (req.method === "GET") {
      const doc = await getDoc(projectId, fsToken, COLLECTION, DOC_ID);
      return jsonResponse({
        ok: true,
        mobile_mode: !!(doc && doc.mobile_mode),
        updatedAt: doc ? doc.updatedAt : null,
        updatedBy: doc ? doc.updatedBy : null,
      });
    }

    if (req.method === "POST") {
      let body;
      try {
        body = await req.json();
      } catch {
        return jsonResponse({ error: "Invalid JSON" }, 400);
      }
      const target = !!body.mobile_mode;
      await patchDoc(projectId, fsToken, COLLECTION, DOC_ID, {
        mobile_mode: target,
        updatedAt: new Date(),
        updatedBy: "Yves Barrette (dashboard)",
      });
      return jsonResponse({
        ok: true,
        mobile_mode: target,
        message: target
          ? "Mode Mobile ACTIVÉ — Béatrice enverra des SMS"
          : "Mode Bureau — Béatrice attendra dans le dashboard",
      });
    }

    return jsonResponse({ error: "Method not allowed" }, 405);
  } catch (e) {
    return jsonResponse({ error: e.message }, 500);
  }
}

export const config = {
  path: "/api/beatrice-toggle-mobile-mode",
};
