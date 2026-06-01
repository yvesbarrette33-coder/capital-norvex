/**
 * POST /.netlify/functions/hugo-run-analysis
 * Header: x-internal-secret
 * Body: { dossierId, skipDocuments?: bool }
 *
 * Lance l'analyse Hugo NORVEX CHANTIER™ depuis l'UI dashboard :
 *   1. Charge les PDFs pertinents du dossier depuis Firebase Storage / Netlify Blobs
 *      (defensif : si échec, continue sans documents en mode dégradé)
 *   2. Appelle EN PARALLÈLE les 3 endpoints orchestrateurs (Intel, Track, Cost)
 *      → Intel reçoit les PDFs en multimodal pour pré-évaluation 3 approches
 *   3. Synthétise les 3 verdicts via Claude Opus 4.6
 *   4. Pousse le rapport dans Norvex Brain
 *   5. Retourne {reportId, verdictGlobal, documentsLoaded, ...}
 *
 * UPGRADE 2026-05-13 — Action #1 audit : pont Firebase Storage → Intel V3.
 *   - Charge les pdfBlobs[] du dossier (blob_ref + firebase_url)
 *   - Cap : max 5 PDFs, 4 MB chacun, 8s budget total téléchargement
 *   - Fallback : si chargement échoue ou pdfBlobs vide, Hugo continue
 *     en mode data-only (comportement identique à avant l'upgrade)
 *   - `skipDocuments: true` dans body force le mode data-only (test/debug)
 *
 * Timeout : 30s (8s docs + 3 calls parallèles ~18s + Claude synthesis ~8s + push ~2s)
 */

const SITE_URL = process.env.SITE_URL || "https://capitalnorvex.com";

// ─── Caps & limits ────────────────────────────────────────────────────────
// Note : Anthropic PDF beta accepte 32 MB de payload total.
// On reste défensif : 5 PDFs × ~6 MB = 30 MB raw, marge pour le prompt.
// Les évaluations immobilières font typiquement 8-15 MB (la pièce la
// plus volumineuse), les autres docs (titres, baux, états fin) <3 MB.
const MAX_DOCS_FOR_INTEL = 5;                // limite parallélisme + payload
const MAX_DOC_SIZE_BYTES = 12 * 1024 * 1024; // 12 MB par PDF (évaluations souvent ~10 MB)
const MAX_TOTAL_BYTES    = 28 * 1024 * 1024; // 28 MB raw total (marge sous 32 MB Anthropic)
const DOC_LOAD_BUDGET_MS = 10000;            // budget total chargement PDFs
const PER_DOC_TIMEOUT_MS = 8000;             // timeout par PDF (gros PDFs peuvent prendre 5-7s)

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// ─── Firestore + Storage auth helpers (réutilisés pour charger pdfBlobs) ──
// Pattern identique à get-firebase-download-url.mjs (zone connue, déjà en prod).

async function getGoogleToken(sa, scope) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: sa.client_email,
    sub: sa.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
    scope,
  };
  const b64 = (obj) =>
    btoa(JSON.stringify(obj))
      .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const signingInput = `${b64(header)}.${b64(payload)}`;
  const pemBody = sa.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\n/g, "");
  const keyData = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));
  const privateKey = await crypto.subtle.importKey(
    "pkcs8", keyData.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false, ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5", privateKey, new TextEncoder().encode(signingInput)
  );
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const jwt = `${signingInput}.${sigB64}`;
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: jwt,
    }),
  });
  const data = await r.json();
  if (!data.access_token) throw new Error("Token failed: " + JSON.stringify(data).slice(0, 200));
  return data.access_token;
}

function fromFsValue(v) {
  if (!v) return null;
  if (v.nullValue !== undefined) return null;
  if (v.booleanValue !== undefined) return v.booleanValue;
  if (v.integerValue !== undefined) return Number(v.integerValue);
  if (v.doubleValue !== undefined) return v.doubleValue;
  if (v.stringValue !== undefined) return v.stringValue;
  if (v.timestampValue !== undefined) return v.timestampValue;
  if (v.arrayValue !== undefined) {
    return (v.arrayValue.values || []).map(fromFsValue);
  }
  if (v.mapValue !== undefined) {
    const out = {};
    for (const [k, val] of Object.entries(v.mapValue.fields || {})) {
      out[k] = fromFsValue(val);
    }
    return out;
  }
  return null;
}

async function getFsDoc(projectId, token, path) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${path}`;
  const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`Firestore GET ${path} failed: ${r.status}`);
  const data = await r.json();
  if (!data.fields) return null;
  const out = {};
  for (const [k, v] of Object.entries(data.fields)) {
    out[k] = fromFsValue(v);
  }
  return out;
}

// ─── Préparation des références PDFs pour Intel (sans téléchargement HTTP) ──
// Intel V3 télécharge lui-même depuis Firebase Storage (upgrade 2026-05-13)
// pour bypasser la limite de payload Netlify (~6 MB sync function body).
//
// Hugo se contente de :
//   1. Lire dossier.pdfBlobs[] depuis Firestore
//   2. Filtrer/cap les blobs (max 5)
//   3. Passer à Intel sous la forme :
//      - firebase_url → { name, mediaType, storagePath }
//      - blob_ref → { name, mediaType, storagePath: "netlify:<key>" }  (TODO Phase 2)
//
// Backward-compatible : tout échec retourne {docs:[]} sans throw,
// pour que Hugo continue en mode data-only comme avant l'upgrade.

/**
 * Prépare la liste des références PDFs pour Intel V3 (format storagePath).
 *
 * Retour : { docs: [{name, mediaType, storagePath}], stats: {...} }
 *
 * Échec silencieux : si Firestore inaccessible, pdfBlobs vide, ou aucun
 * doc Firebase utilisable, retourne { docs: [], stats: { reason: "..." } }
 * sans throw. Hugo tourne alors en mode data-only.
 *
 * Note Phase 1 : seuls les blobs `firebase_url` sont passés.
 * Les `blob_ref` (Netlify Blobs) seront supportés en Phase 2 via un
 * endpoint Intel séparé ou un mécanisme de re-upload temporaire.
 */
async function loadDossierDocuments(dossierId, secret) {
  const stats = {
    attempted: 0,
    selected_firebase: 0,
    skipped_blob_ref: 0,
    skipped_unknown: 0,
    reason: "ok",
    types: { blob_ref: 0, chunked_ref: 0, firebase_url: 0, unknown: 0 },
  };

  const { getServiceAccount } = await import("./_firebase-sa.mjs");
  let sa;
  try {
    sa = await getServiceAccount();
  } catch (e) {
    stats.reason = "no_firebase_sa: " + e.message;
    return { docs: [], stats };
  }

  // 1. Lire dossier.pdfBlobs depuis Firestore
  let dossier;
  try {
    const fsToken = await getGoogleToken(
      sa,
      "https://www.googleapis.com/auth/datastore"
    );
    dossier = await getFsDoc(sa.project_id, fsToken, `dossiers/${dossierId}`);
  } catch (e) {
    stats.reason = "firestore_error: " + e.message;
    return { docs: [], stats };
  }
  if (!dossier) {
    stats.reason = "dossier_not_found";
    return { docs: [], stats };
  }

  const pdfBlobs = Array.isArray(dossier.pdfBlobs) ? dossier.pdfBlobs : [];
  if (pdfBlobs.length === 0) {
    stats.reason = "no_pdfBlobs";
    return { docs: [], stats };
  }

  // 2. Filtrer : seuls les firebase_url sont supportés en Phase 1
  // (Intel télécharge directement depuis Storage, pas de proxy Netlify).
  const docs = [];
  for (const blob of pdfBlobs) {
    if (docs.length >= MAX_DOCS_FOR_INTEL) break;
    const blobType = blob.type || "unknown";
    stats.types[blobType] !== undefined
      ? stats.types[blobType]++
      : stats.types.unknown++;
    stats.attempted++;

    if (blobType === "firebase_url") {
      const storagePath = blob.path || blob.key;
      if (storagePath) {
        docs.push({
          name: blob.name || "document.pdf",
          mediaType: "application/pdf",
          storagePath,
        });
        stats.selected_firebase++;
      } else {
        stats.skipped_unknown++;
      }
    } else if (blobType === "blob_ref" || blobType === "chunked_ref") {
      // TODO Phase 2 : exposer un endpoint Intel-internal-storage pour Netlify Blobs.
      // Pour l'instant on les skip pour ne pas casser Hugo.
      stats.skipped_blob_ref++;
    } else {
      stats.skipped_unknown++;
    }
  }

  if (docs.length === 0 && stats.reason === "ok") {
    stats.reason =
      stats.skipped_blob_ref > 0 ? "only_blob_refs_available" : "no_supported_blobs";
  }
  return { docs, stats };
}

// Appel sécurisé à un endpoint orchestrateur
async function callEndpoint(name, path, body, secret, timeoutMs = 22000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(`${SITE_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-internal-secret": secret,
      },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    });
    clearTimeout(t);
    if (!r.ok) {
      const errText = await r.text();
      return { error: `HTTP ${r.status}: ${errText.slice(0, 200)}`, module: name };
    }
    return await r.json();
  } catch (e) {
    clearTimeout(t);
    return { error: e.message, module: name };
  }
}

// Synthèse Claude Opus
async function synthesize(dossierId, reports, anthropicKey) {
  const SYSTEM_PROMPT = `Tu es Hugo — NORVEX CHANTIER™, coordonnateur technique chantier IA de Capital Norvex Inc.

Tu synthétises 3 rapports d'analyse (Norvex Intel, Norvex Track, Norvex Cost Analyzer) en UN verdict business consolidé pour Yves Barrette.

LOGIQUE DE DÉCISION :
- Si AU MOINS UN module = "Critique" OU "refus_recommande" → verdict_global = "Critique" → action = "BLOCK_DISBURSEMENT_ESCALATE_YVES"
- Si AU MOINS UN module = "À surveiller" OU "ok_avec_conditions" → verdict_global = "À surveiller" → action = "REQUEST_CLARIFICATION" ou "AUTHORIZE_WITH_CONDITIONS"
- Si TOUS = "OK" OU "financement_ok" → verdict_global = "OK" → action = "AUTHORIZE_DISBURSEMENT"
- Si données INSUFFISANTES → verdict_global = "DATA_GAP" → action = "REQUEST_DOCUMENTS"

Conservatisme prêteur : en cas de doute, mieux "À surveiller" que "OK".

Tu réponds UNIQUEMENT en JSON STRICT :
{
  "verdict_global": "OK | À surveiller | Critique | DATA_GAP",
  "action_recommandee": "AUTHORIZE_DISBURSEMENT | AUTHORIZE_WITH_CONDITIONS | REQUEST_CLARIFICATION | REQUEST_DOCUMENTS | BLOCK_DISBURSEMENT_ESCALATE_YVES",
  "synthesis": "<résumé exécutif 4-6 phrases pour Yves>",
  "modules_summary": {
    "intel": { "verdict": "<...>", "key_finding": "<court>" },
    "track": { "verdict": "<...>", "key_finding": "<court>" },
    "cost": { "verdict": "<...>", "key_finding": "<court>" }
  },
  "alertes_consolidees": [{ "niveau": "info|warning|critical", "module": "intel|track|cost", "message": "<...>", "action_requise": "<...>" }],
  "data_gaps_consolides": ["<liste>"],
  "recommandation_yves": "<recommandation actionnable claire>",
  "next_steps": ["<étape 1>", "<étape 2>", "<étape 3>"],
  "valeur_pretee_recommandee": <nombre ou null>,
  "deboursement_autorise": <true|false|null>,
  "confiance_globale": "élevé | modéré | faible"
}`;

  const userMsg = `DOSSIER ID : ${dossierId}

═══════════ INTEL ═══════════
${JSON.stringify(reports.intel, null, 2)}

═══════════ TRACK ═══════════
${JSON.stringify(reports.track, null, 2)}

═══════════ COST ═══════════
${JSON.stringify(reports.cost, null, 2)}`;

  const r = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": anthropicKey,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      model: "claude-opus-4-6",
      max_tokens: 2000,
      system: SYSTEM_PROMPT,
      messages: [{ role: "user", content: userMsg }],
    }),
  });
  if (!r.ok) {
    const err = await r.text();
    throw new Error(`Synthesis Claude error: ${err.slice(0, 200)}`);
  }
  const data = await r.json();
  const text = data.content[0].text.trim();
  let cleaned = text;
  if (cleaned.startsWith("```")) {
    cleaned = cleaned.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/i, "");
  }
  const start = cleaned.indexOf("{");
  const end = cleaned.lastIndexOf("}");
  if (start >= 0 && end > start) cleaned = cleaned.substring(start, end + 1);
  return JSON.parse(cleaned);
}

// Push vers Brain
async function pushToBrain(dossierId, synthesis, reports, secret) {
  const payload = {
    dossierId,
    agent: "hugo_norvex_chantier",
    verdictGlobal: synthesis.verdict_global,
    actionRecommandee: synthesis.action_recommandee,
    synthesis: synthesis.synthesis,
    modulesSummary: synthesis.modules_summary || {},
    alertesConsolidees: synthesis.alertes_consolidees || [],
    deboursementAutorise:
      synthesis.deboursement_autorise === undefined
        ? null
        : synthesis.deboursement_autorise,
    valeurPreteeRecommandee:
      synthesis.valeur_pretee_recommandee === undefined
        ? null
        : synthesis.valeur_pretee_recommandee,
    confianceGlobale: synthesis.confiance_globale,
    rawReports: {
      intel_status: "evaluation" in (reports.intel || {}) ? "ok" : "error",
      track_status: "verdict_global" in (reports.track || {}) ? "ok" : "error",
      cost_status: "verdict_global" in (reports.cost || {}) ? "ok" : "error",
    },
    createdAt: new Date().toISOString(),
  };
  return await callEndpoint(
    "brain_push",
    "/api/brain-push-from-hugo",
    payload,
    secret,
    20000
  );
}

// ─── Handler ──────────────────────────────────────────────────────────────

export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-internal-secret",
      },
    });
  }
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return json({ error: "Unauthorized" }, 401);
  }

  let body;
  try { body = await req.json(); }
  catch { return json({ error: "Invalid JSON" }, 400); }

  const { dossierId } = body;
  if (!dossierId) return json({ error: "dossierId required" }, 400);

  const anthropicKey = process.env.ANTHROPIC_API_KEY;
  if (!anthropicKey) return json({ error: "ANTHROPIC_API_KEY not set" }, 500);

  try {
    // Étape 0 : chargement défensif des PDFs pour Intel (upgrade 2026-05-13).
    // Backward-compatible : si échec, docs=[] → Intel tourne en mode data-only.
    let intelDocs = [];
    let docsStats = { reason: "skipped_by_request" };
    if (body.skipDocuments !== true) {
      const loaded = await loadDossierDocuments(dossierId, secret);
      intelDocs = loaded.docs;
      docsStats = loaded.stats;
    }

    // ─── UPGRADE 2026-05-13 — Switch background pour PDFs ────────────────
    // Si on a des PDFs à analyser, on switch en mode background (15 min budget)
    // car Anthropic + PDFs 10+ MB > 26s Netlify sync cap.
    // Mode sync conservé pour skipDocuments=true OU forceSync=true OU aucun PDF.
    const useBackground =
      body.forceSync !== true &&
      body.skipDocuments !== true &&
      intelDocs.length > 0;

    if (useBackground) {
      const jobId = `hjob_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
      {
        try {
          const { getServiceAccount } = await import("./_firebase-sa.mjs");
          const sa = await getServiceAccount();
          const fsToken = await getGoogleToken(
            sa,
            "https://www.googleapis.com/auth/datastore"
          );
          const url = `https://firestore.googleapis.com/v1/projects/${sa.project_id}/databases/(default)/documents/hugoJobs?documentId=${encodeURIComponent(jobId)}`;
          await fetch(url, {
            method: "POST",
            headers: {
              Authorization: `Bearer ${fsToken}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              fields: {
                status: { stringValue: "pending" },
                dossierId: { stringValue: dossierId },
                createdAt: { stringValue: new Date().toISOString() },
                pdfCountIntended: { integerValue: String(intelDocs.length) },
              },
            }),
          });
        } catch (e) {
          console.error("[hugo-run] hugoJobs init failed:", e.message);
        }
      }

      // POST vers hugo-orchestrator-background (Netlify Background Function).
      // Le suffixe `-background` du nom de fichier active le mode async (15 min).
      // IMPORTANT : on AWAIT la requête pour s'assurer que Netlify n'a pas tué
      // le process parent avant l'envoi (fire-and-forget non garanti sur Netlify v2).
      // Le background retourne 202 quasi-immédiatement (~200 ms), donc on bloque pas.
      const bgUrl = `${SITE_URL}/.netlify/functions/hugo-orchestrator-background`;
      try {
        await fetch(bgUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-internal-secret": secret,
          },
          body: JSON.stringify({
            jobId,
            dossierId,
            skipNorvexFinal: body.skipNorvexFinal === true,
            forceEmail: body.forceEmail === true,
          }),
        });
      } catch (e) {
        console.error("[hugo-run] bg trigger failed:", e.message);
        // On continue quand même — le job sera en pending dans hugoJobs et
        // Yves pourra retry. Plus important : retourner 202 au client maintenant.
      }

      // Retour immédiat (202 Accepted)
      return json(
        {
          ok: true,
          mode: "background",
          jobId,
          dossierId,
          documents_loaded: {
            count: intelDocs.length,
            ...docsStats,
          },
          message:
            `Analyse lancée en arrière-plan (${intelDocs.length} PDF${intelDocs.length === 1 ? "" : "s"}). Poll /api/hugo-job-status?jobId=${jobId} pour le résultat. Email automatique à yves@ une fois terminé.`,
          poll_url: `/api/hugo-job-status?jobId=${jobId}`,
          analyzed_at: null,
        },
        202
      );
    }
    // ─────────────────────────────────────────────────────────────────────
    // Mode sync legacy : pas de PDFs, OU skipDocuments=true, OU forceSync=true.
    // Intel tourne en mode data-only (rapide, <26 s).

    // Étape 1 : appels parallèles aux 3 modules.
    // Intel reçoit les PDFs en multimodal (si docs chargés) ou {dossierId} seul.
    // Track et Cost restent en mode data-only pour cette phase
    // (extension multimodale Track/Cost = Action #3 audit, à venir).
    const intelBody =
      intelDocs.length > 0
        ? { dossierId, documents: intelDocs }
        : { dossierId };

    const [intelReport, trackReport, costReport] = await Promise.all([
      callEndpoint("intel", "/api/intel-analyze-dossier", intelBody, secret),
      callEndpoint("track", "/api/track-analyze-dossier", { dossierId }, secret),
      callEndpoint("cost", "/api/cost-analyze-dossier", { dossierId }, secret),
    ]);

    const reports = {
      intel: intelReport,
      track: trackReport,
      cost: costReport,
    };

    // Étape 2 : synthèse Claude
    const synthesis = await synthesize(dossierId, reports, anthropicKey);

    // Étape 3 : push Brain
    const brainResult = await pushToBrain(dossierId, synthesis, reports, secret);

    // Étape 4 : Norvex Final™ — calcul taux/montant/conditions + Brief Yves
    // Skipé si Hugo verdict = Critique (Yves doit d'abord traiter l'alerte)
    let norvexFinalResult = null;
    const skipNorvexFinal = body.skipNorvexFinal === true;
    const hugoCritique = synthesis.verdict_global === "Critique";
    if (!skipNorvexFinal && !hugoCritique) {
      norvexFinalResult = await callEndpoint(
        "norvex_final",
        "/api/norvex-final-analyze",
        { dossierId, sendEmail: true },
        secret,
        25000
      );
    }

    return json({
      ok: true,
      dossierId,
      verdictGlobal: synthesis.verdict_global,
      actionRecommandee: synthesis.action_recommandee,
      synthesis: synthesis.synthesis,
      documents_loaded: {
        count: intelDocs.length,
        ...docsStats,
      },
      intel_mode: intelDocs.length > 0 ? "multimodal" : "data_only",
      modules_status: {
        intel: intelReport.error ? "error" : "ok",
        track: trackReport.error ? "error" : "ok",
        cost: costReport.error ? "error" : "ok",
      },
      reportId: brainResult.reportId || null,
      alertId: brainResult.alertId || null,
      brain_push_status: brainResult.error ? "error" : "ok",
      norvex_final: norvexFinalResult
        ? {
            status: norvexFinalResult.error ? "error" : "ok",
            error: norvexFinalResult.error || null,
            finalDecision: norvexFinalResult.finalDecision || null,
            finalRate: norvexFinalResult.finalRate || null,
            finalAmount: norvexFinalResult.finalAmount || null,
            reportId: norvexFinalResult.reportId || null,
            emailSent: norvexFinalResult.emailSent || false,
          }
        : { status: skipNorvexFinal ? "skipped" : hugoCritique ? "skipped_hugo_critique" : "not_run" },
      analyzed_at: new Date().toISOString(),
    });
  } catch (e) {
    return json({ error: e.message }, 500);
  }
};

export const config = {
  path: "/api/hugo-run-analysis",
};
