/**
 * Scheduled Function — Hugo NORVEX CHANTIER™ AUTO-TRIGGER WATCHER
 *
 * Cron: toutes les 30 minutes
 *
 * Détecte automatiquement les dossiers prêts à être analysés par Hugo et
 * lance `hugo-run-analysis` pour chacun.
 *
 * CRITÈRES DE DÉCLENCHEMENT (verrouillés par Yves 2026-05-05) :
 *   1. Dossier de type CONSTRUCTION (loanType contient "construction")
 *   2. LOI SIGNÉE (stage = `loi_signed` OU plus avancé : at_notary, closing_in_progress, closing, funded)
 *   3. agent_docs a marqué l'analyse complète (status / docsStatus = `analyse_complete`)
 *   4. PAS encore analysé par Hugo dans les dernières 6h (champ `hugoLastAnalyzedAt`)
 *
 * Pourquoi LOI signée ?
 *   « Avant ça, ils ne mettront pas toutes leurs ventilations coûts et plein
 *     de choses qui vont manquer dans le score Norvex. » — Yves
 *
 * Limite : 5 dossiers par run (sécurité budget API + temps Netlify 26s).
 *
 * Manuel : `curl -H "x-internal-secret: $SECRET" https://capitalnorvex.com/.netlify/functions/hugo-watcher?dry=1`
 */

import {
  json,
  unauthorized,
  checkInternalSecret,
  getFirestoreToken,
  firestoreDocToObject,
} from "./_norah-shared.mjs";

/**
 * PATCH partiel d'un document Firestore via updateMask (préserve les autres
 * champs — ne PAS utiliser firestoreCreate avec docId, qui remplace tout).
 */
async function firestorePatchFields(collection, docId, patch) {
  const { accessToken, projectId } = await getFirestoreToken();

  // Construit fields Firestore (typage explicite)
  const fields = {};
  for (const [k, v] of Object.entries(patch)) {
    if (v === null || v === undefined) {
      fields[k] = { nullValue: null };
    } else if (typeof v === "boolean") {
      fields[k] = { booleanValue: v };
    } else if (typeof v === "number" && Number.isInteger(v)) {
      fields[k] = { integerValue: String(v) };
    } else if (typeof v === "number") {
      fields[k] = { doubleValue: v };
    } else {
      fields[k] = { stringValue: String(v) };
    }
  }

  const fieldPaths = Object.keys(patch)
    .map((k) => `updateMask.fieldPaths=${encodeURIComponent(k)}`)
    .join("&");

  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collection}/${docId}?${fieldPaths}`;

  const resp = await fetch(url, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ fields }),
  });

  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(`Firestore PATCH failed: ${resp.status} ${txt.slice(0, 200)}`);
  }
  return true;
}

const SITE_URL = process.env.SITE_URL || "https://capitalnorvex.com";
const HUGO_COOLDOWN_HOURS = 6;
const MAX_DOSSIERS_PER_RUN = 5;

// Stages où Hugo peut analyser (LOI signée et au-delà, jusqu'au funded)
const ELIGIBLE_STAGES = new Set([
  "loi_signed",
  "at_notary",
  "closing_in_progress",
  "closing",
  "funded",
]);

/** Query Firestore : dossiers stage = X */
async function queryDossiersByStage(stage) {
  const { accessToken, projectId } = await getFirestoreToken();
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;

  const structuredQuery = {
    from: [{ collectionId: "dossiers" }],
    where: {
      fieldFilter: {
        field: { fieldPath: "stage" },
        op: "EQUAL",
        value: { stringValue: stage },
      },
    },
    limit: 50,
  };

  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ structuredQuery }),
  });

  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(`Firestore query (stage=${stage}) failed: ${resp.status} ${txt.slice(0, 200)}`);
  }

  const results = await resp.json();
  if (!Array.isArray(results)) return [];
  return results
    .filter((r) => r.document)
    .map((r) => {
      const obj = firestoreDocToObject(r.document);
      // L'ID complet est dans r.document.name : ".../dossiers/<id>"
      const docName = r.document.name || "";
      obj._docId = docName.split("/").pop();
      return obj;
    });
}

/** Vérifie si un dossier est de type construction. */
function isConstructionLoan(dossier) {
  const raw = (dossier.loanType || dossier.typePret || dossier.financingType || "").toString().toLowerCase();
  if (!raw) return false;
  return raw.includes("construction") || raw.includes("chantier") || raw.includes("build");
}

/** Vérifie si agent_docs a complété la collecte. */
function isDocsAnalysisComplete(dossier) {
  const status = (dossier.docsStatus || dossier.documentsStatus || dossier.status || "").toString().toLowerCase();
  return status === "analyse_complete" || status === "analyse_complete_construction" || status === "complete";
}

/** Cooldown : Hugo ne ré-analyse pas si dernière run < 6h. */
function isRecentlyAnalyzedByHugo(dossier) {
  const last = dossier.hugoLastAnalyzedAt;
  if (!last) return false;
  try {
    const t = new Date(last).getTime();
    if (Number.isNaN(t)) return false;
    const diffMs = Date.now() - t;
    return diffMs < HUGO_COOLDOWN_HOURS * 60 * 60 * 1000;
  } catch {
    return false;
  }
}

/**
 * Anti-spam (verrouillé 2026-05-13 par Yves) : si Hugo a déjà produit un
 * rapport pour ce dossier (hugoLastReportId non-null), le watcher ne
 * ré-déclenche PAS. Une re-analyse doit être demandée manuellement via UI
 * dashboard ou curl avec `forceEmail: true`. Évite la boucle « toutes les
 * 30 min ça relance le même dossier et envoie un email ».
 */
function hasExistingHugoReport(dossier) {
  return Boolean(dossier.hugoLastReportId);
}

/** Lance hugo-run-analysis pour un dossier (timeout 24s). */
async function runHugoForDossier(dossierId, secret) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), 24000);
  try {
    const r = await fetch(`${SITE_URL}/api/hugo-run-analysis`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-internal-secret": secret,
      },
      body: JSON.stringify({ dossierId }),
      signal: ctrl.signal,
    });
    clearTimeout(t);
    if (!r.ok) {
      const errText = await r.text();
      return { ok: false, error: `HTTP ${r.status}: ${errText.slice(0, 200)}` };
    }
    return { ok: true, data: await r.json() };
  } catch (e) {
    clearTimeout(t);
    return { ok: false, error: e.message };
  }
}

/** Met à jour le dossier Firestore avec timestamp + verdict Hugo. */
async function markDossierAnalyzed(dossierId, hugoResult) {
  try {
    // PATCH minimal : on ajoute hugoLastAnalyzedAt + hugoLastVerdict + hugoLastReportId
    const patch = {
      hugoLastAnalyzedAt: new Date().toISOString(),
      hugoLastVerdict: hugoResult?.verdictGlobal || "unknown",
      hugoLastReportId: hugoResult?.reportId || null,
      hugoLastAction: hugoResult?.actionRecommandee || null,
    };
    await firestorePatchFields("dossiers", dossierId, patch);
    return true;
  } catch (e) {
    console.error(`markDossierAnalyzed(${dossierId}) failed:`, e.message);
    return false;
  }
}

// ─── Handler ──────────────────────────────────────────────────────────────

export default async (req, context) => {
  const isScheduled = Boolean(context?.scheduledTime);
  if (!isScheduled && !checkInternalSecret(req)) {
    return unauthorized();
  }

  const url = new URL(req.url);
  const isDry = url.searchParams.get("dry") === "1";

  const secret = process.env.INTERNAL_SECRET;
  if (!secret) return json({ error: "INTERNAL_SECRET not set" }, 500);

  const startedAt = new Date().toISOString();
  const summary = {
    startedAt,
    scheduled: isScheduled,
    dry: isDry,
    candidates_total: 0,
    triggered: 0,
    skipped_reasons: { not_construction: 0, docs_incomplete: 0, recent_hugo: 0 },
    runs: [],
    errors: [],
  };

  try {
    // 1. Récupérer tous les dossiers candidats (par stage éligible)
    const allCandidates = [];
    for (const stage of ELIGIBLE_STAGES) {
      try {
        const docs = await queryDossiersByStage(stage);
        allCandidates.push(...docs);
      } catch (e) {
        summary.errors.push(`query(${stage}): ${e.message}`);
      }
    }

    summary.candidates_total = allCandidates.length;
    summary.skipped_reasons.already_has_report = 0;

    // 2. Filtrer
    const eligible = [];
    for (const d of allCandidates) {
      if (!isConstructionLoan(d)) {
        summary.skipped_reasons.not_construction++;
        continue;
      }
      if (!isDocsAnalysisComplete(d)) {
        summary.skipped_reasons.docs_incomplete++;
        continue;
      }
      // Anti-spam : un seul rapport Hugo par dossier en mode auto.
      // Re-analyse = action manuelle explicite (UI ou curl avec forceEmail).
      if (hasExistingHugoReport(d)) {
        summary.skipped_reasons.already_has_report++;
        continue;
      }
      if (isRecentlyAnalyzedByHugo(d)) {
        summary.skipped_reasons.recent_hugo++;
        continue;
      }
      eligible.push(d);
    }

    summary.eligible = eligible.length;

    // 3. Limiter à MAX_DOSSIERS_PER_RUN
    const toRun = eligible.slice(0, MAX_DOSSIERS_PER_RUN);

    // 4. Pour chacun : trigger Hugo (sauf en mode dry)
    for (const d of toRun) {
      const dossierId = d._docId;
      const runEntry = { dossierId, loanType: d.loanType, stage: d.stage };

      if (isDry) {
        runEntry.dry = true;
        summary.runs.push(runEntry);
        continue;
      }

      const result = await runHugoForDossier(dossierId, secret);
      if (!result.ok) {
        runEntry.error = result.error;
        summary.errors.push(`hugo(${dossierId}): ${result.error}`);
      } else {
        runEntry.verdictGlobal = result.data?.verdictGlobal;
        runEntry.actionRecommandee = result.data?.actionRecommandee;
        runEntry.reportId = result.data?.reportId;
        // Norvex Final chaîné par hugo-run-analysis (sauf si Critique)
        if (result.data?.norvex_final) {
          runEntry.norvex_final = {
            status: result.data.norvex_final.status,
            finalDecision: result.data.norvex_final.finalDecision || null,
            finalRate: result.data.norvex_final.finalRate || null,
            emailSent: result.data.norvex_final.emailSent || false,
          };
        }
        // Marquer le dossier (PATCH Firestore)
        await markDossierAnalyzed(dossierId, result.data);
        summary.triggered++;
      }
      summary.runs.push(runEntry);
    }

    summary.completedAt = new Date().toISOString();
    return json({ ok: true, ...summary });
  } catch (e) {
    summary.errors.push(`fatal: ${e.message}`);
    return json({ ok: false, ...summary }, 500);
  }
};

// Cron Netlify : toutes les 30 minutes
export const config = {
  schedule: "*/30 * * * *",
};
