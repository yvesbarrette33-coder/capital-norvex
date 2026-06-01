/**
 * POST /api/beatrice-stats
 * Header: X-Internal-Secret
 *
 * Retourne les stats 24h de Béatrice depuis agentAuditLog.
 * { autoRepliesSkipped, draftsCreated, dedupSkipped, personalSkipped,
 *   noReplySkipped, totalProcessed, lastRunAt }
 */

import {
  getFirestoreToken,
  jsonResponse,
  listDocs,
  loadServiceAccount,
} from "./_camille-shared.mjs";

const COLLECTION = "agentAuditLog";

export default async function handler(req) {
  if (req.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405);
  }
  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return jsonResponse({ error: "Unauthorized" }, 401);
  }

  try {
    const sa = await loadServiceAccount();
    const projectId = sa.project_id;
    const fsToken = await getFirestoreToken(sa);

    // Récupère 500 derniers audits (1 jour de Béatrice ~144 runs × ~5 emails ~720 events max)
    const all = await listDocs(projectId, fsToken, COLLECTION, { limit: 500 });

    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    const stats = {
      autoRepliesSkipped: 0,
      draftsCreated: 0,
      dedupSkipped: 0,
      personalSkipped: 0,
      noReplySkipped: 0,
      totalProcessed: 0,
      lastRunAt: null,
      todayWindow: "24h",
    };

    for (const d of all) {
      const f = d.fields || {};
      const agent = f.agent?.stringValue;
      if (agent !== "beatrice") continue;

      const tsStr = f.createdAt?.timestampValue || f.createdAt?.stringValue;
      if (!tsStr) continue;
      const ts = new Date(tsStr).getTime();
      if (ts < cutoff) continue;

      stats.totalProcessed += 1;
      if (!stats.lastRunAt || ts > new Date(stats.lastRunAt).getTime()) {
        stats.lastRunAt = tsStr;
      }

      const action = f.action?.stringValue || "";
      if (action === "skip_per_maestro") stats.autoRepliesSkipped += 1;
      else if (action === "skip_dedup") stats.dedupSkipped += 1;
      else if (action === "skip_no_reply_pre_filter") stats.noReplySkipped += 1;
      else if (action.startsWith("skip_personal")) stats.personalSkipped += 1;
      else if (action === "draft_created" || action === "drafted") stats.draftsCreated += 1;
    }

    return jsonResponse({ ok: true, stats });
  } catch (err) {
    return jsonResponse({ error: err.message }, 500);
  }
}
