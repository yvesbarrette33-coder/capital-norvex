/**
 * POST /.netlify/functions/track-analyze-dossier
 * Header: x-internal-secret
 * Body: {
 *   dossierId,
 *   documents?: [{ name, mediaType, contentBase64 }],  // rapports, photos, factures
 *   force_opus_validation?: bool
 * }
 *
 * UPGRADE 2026-05-05 SOIR (V2) — Hugo NORVEX CHANTIER™ :
 *   - max_tokens 1500 → 2500
 *   - Mode multimodal (rapports d'avancement, photos chantier, factures)
 *   - Stress tests (retard 1 mois, dépassement 10 %, sur-déboursement)
 *   - Validation Opus 4.6 second-pass si verdict Critique
 *
 * Output JSON :
 *   { dossierId, hasData, mode, stats, ecarts, ventilation_count,
 *     verdict_global, synthesis, alertes, retards_potentiels,
 *     deboursement_risk, recommendation, stress_tests,
 *     opus_validation?, analyzed_at, model }
 */

// ─── Firebase Storage download (format storagePath, comme Intel V2) ──────
// Permet à Hugo de passer des références storagePath au lieu de base64 inline
// (contourne body cap inter-functions Netlify ~6 MB).

async function getStorageToken(sa) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: sa.client_email,
    sub: sa.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
    scope: "https://www.googleapis.com/auth/devstorage.read_only",
  };
  const b64fn = (obj) =>
    btoa(JSON.stringify(obj))
      .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const signingInput = `${b64fn(header)}.${b64fn(payload)}`;
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
  if (!data.access_token) throw new Error("Storage token failed");
  return data.access_token;
}

function arrayBufferToBase64(buf) {
  const bytes = new Uint8Array(buf);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

async function downloadFromStorage(storagePath, accessToken, bucket, maxBytes = 14 * 1024 * 1024) {
  const url =
    `https://storage.googleapis.com/storage/v1/b/${encodeURIComponent(bucket)}` +
    `/o/${encodeURIComponent(storagePath)}?alt=media`;
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), 10000);
  try {
    const r = await fetch(url, {
      headers: { Authorization: `Bearer ${accessToken}` },
      signal: ctrl.signal,
    });
    clearTimeout(t);
    if (!r.ok) return null;
    const buf = await r.arrayBuffer();
    if (buf.byteLength === 0 || buf.byteLength > maxBytes) return null;
    return arrayBufferToBase64(buf);
  } catch {
    clearTimeout(t);
    return null;
  }
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function getFirestoreToken(sa) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: sa.client_email,
    sub: sa.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
    scope: "https://www.googleapis.com/auth/datastore",
  };
  const b64 = (obj) =>
    btoa(JSON.stringify(obj))
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");
  const signingInput = `${b64(header)}.${b64(payload)}`;
  const pemBody = sa.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\n/g, "");
  const keyData = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));
  const privateKey = await crypto.subtle.importKey(
    "pkcs8",
    keyData.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    privateKey,
    new TextEncoder().encode(signingInput)
  );
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
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
  if (!data.access_token) throw new Error("Firestore token failed");
  return data.access_token;
}

function toFsValue(v) {
  if (v === null || v === undefined) return { nullValue: null };
  if (typeof v === "boolean") return { booleanValue: v };
  if (typeof v === "number") {
    return Number.isInteger(v) ? { integerValue: String(v) } : { doubleValue: v };
  }
  if (typeof v === "string") return { stringValue: v };
  if (Array.isArray(v)) return { arrayValue: { values: v.map(toFsValue) } };
  if (typeof v === "object") {
    const fields = {};
    for (const [k, val] of Object.entries(v)) fields[k] = toFsValue(val);
    return { mapValue: { fields } };
  }
  return { stringValue: String(v) };
}

async function fsPatch(projectId, token, path, patch) {
  const fieldPaths = Object.keys(patch)
    .map((k) => `updateMask.fieldPaths=${encodeURIComponent(k)}`)
    .join("&");
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${path}?${fieldPaths}`;
  const fields = {};
  for (const [k, v] of Object.entries(patch)) fields[k] = toFsValue(v);
  const r = await fetch(url, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });
  if (!r.ok) {
    const txt = await r.text();
    throw new Error(`Firestore PATCH ${path} failed: ${r.status} ${txt.slice(0, 200)}`);
  }
  return true;
}

async function updateTrackJob(projectId, token, jobId, patch) {
  try {
    await fsPatch(projectId, token, `trackJobs/${jobId}`, patch);
  } catch (e) {
    console.error(`[track-bg] updateTrackJob(${jobId}) failed:`, e.message);
  }
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
  const r = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
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

// ─── Calculs déterministes ───────────────────────────────────────────────

function computeStats(ventilation) {
  if (!Array.isArray(ventilation) || ventilation.length === 0) return null;
  let totalBudget = 0;
  let totalDebourse = 0;
  let totalRetenu = 0;
  let weighted_pct = 0;
  for (const p of ventilation) {
    const budget = Number(p.budgetPrevu || p.budget || 0);
    const debourse = Number(p.montantApprouve || p.debourse || 0);
    const retenu = Number(p.retenu || 0);
    totalBudget += budget;
    totalDebourse += debourse;
    totalRetenu += retenu;
    weighted_pct += (Number(p.pctActuel || 0) * budget);
  }
  return {
    totalBudget: Math.round(totalBudget),
    totalDebourse: Math.round(totalDebourse),
    totalRetenu: Math.round(totalRetenu),
    pctOverall: totalBudget > 0 ? Math.round(weighted_pct / totalBudget) : 0,
  };
}

function computeEcarts(ventilation) {
  if (!Array.isArray(ventilation)) return [];
  const ecarts = [];
  for (const p of ventilation) {
    const budget = Number(p.budgetPrevu || p.budget || 0);
    const reel = Number(p.montantApprouve || p.debourse || 0);
    if (budget === 0) continue;
    const ecart_pct = ((reel - budget) / budget) * 100;
    let severite = "OK";
    if (ecart_pct > 20) severite = "Critique";
    else if (ecart_pct > 10) severite = "À surveiller";
    if (severite !== "OK") {
      ecarts.push({
        poste: p.poste || p.id,
        cat: p.cat,
        budget,
        reel,
        ecart_pct: Math.round(ecart_pct * 10) / 10,
        severite,
      });
    }
  }
  return ecarts.sort((a, b) => b.ecart_pct - a.ecart_pct);
}

function buildPrompt(dossier, trackData, stats, ecarts, hasDocuments, documentsCount) {
  const docsBlock = hasDocuments
    ? `═══════════════════════════════════════════════════════════════════
DOCUMENTS PDF/IMAGES FOURNIS (${documentsCount})
═══════════════════════════════════════════════════════════════════
Tu as reçu ${documentsCount} document(s) (rapports d'avancement, photos chantier, factures, soumissions). Lis-les et croise-les avec les données Track ci-dessous. Détecte tout écart entre saisie UI et réalité documentée. Si photos chantier : commente l'avancement visible.

`
    : "";

  return `Tu es un expert en suivi de chantier de construction immobilière au Québec, avec 20+ ans d'expérience en financement privé chez Capital Norvex.

Analyse ce dossier de chantier et produis un rapport de risque structuré pour l'orchestrateur Hugo NORVEX CHANTIER™. Inclus des STRESS TESTS de résilience.

═══════════════════════════════════════════════════════════════════
DOSSIER
═══════════════════════════════════════════════════════════════════
ID : ${dossier?.id || "N/D"}
Emprunteur : ${dossier?.borrowerName || dossier?.name || "N/D"}
Type de prêt : ${dossier?.loanType || "N/D"}
Adresse : ${dossier?.projectAddress || "N/D"}

${docsBlock}═══════════════════════════════════════════════════════════════════
STATS PRÉCALCULÉES
═══════════════════════════════════════════════════════════════════
Budget total : ${stats?.totalBudget?.toLocaleString("fr-CA") || "N/D"} $
Déboursé total : ${stats?.totalDebourse?.toLocaleString("fr-CA") || "N/D"} $
Retenu total : ${stats?.totalRetenu?.toLocaleString("fr-CA") || "N/D"} $
Avancement pondéré : ${stats?.pctOverall || 0} %

═══════════════════════════════════════════════════════════════════
ÉCARTS BUDGET vs RÉEL DÉTECTÉS (auto)
═══════════════════════════════════════════════════════════════════
${ecarts.length === 0 ? "Aucun écart > 10 %" : JSON.stringify(ecarts, null, 2)}

═══════════════════════════════════════════════════════════════════
VENTILATION DÉTAILLÉE
═══════════════════════════════════════════════════════════════════
${JSON.stringify(trackData?.ventilation || [], null, 2).slice(0, 4000)}

═══════════════════════════════════════════════════════════════════
TÂCHE
═══════════════════════════════════════════════════════════════════

Produis un rapport de risque chantier en JSON STRICT :

{
  "verdict_global": "OK | À surveiller | Critique",
  "verdict_global_justification": "<court 1-2 phrases>",
  "synthesis": "<résumé textuel 3-5 phrases sur l'état du chantier>",
  "alertes": [
    { "niveau": "info|warning|critical", "message": "<...>", "action_requise": "<...>" }
  ],
  "retards_potentiels": "<analyse des retards si visible>",
  "deboursement_risk": "<analyse du risque de déboursement (sur/sous-déboursé vs avancement)>",
  "recommendation": "<recommandation actionnable Hugo>",
  "stress_tests": {
    "scenario_a_retard_1mois": { "cout_supplementaire": <nombre|null>, "verdict": "OK | À surveiller | Critique", "notes": "<court>" },
    "scenario_b_depassement_10pct_restant": { "budget_total_revise": <nombre|null>, "verdict": "OK | À surveiller | Critique", "notes": "<court>" },
    "scenario_c_sur_deboursement_15pts": { "exposition_supplementaire": <nombre|null>, "verdict": "OK | À surveiller | Critique", "notes": "<court>" }
  },
  "ecarts_documents_vs_saisie": ${hasDocuments ? '"<liste des écarts détectés entre PDFs/photos et saisie UI, ou \\"aucun écart\\">"' : "null"},
  "data_gaps": ["<données manquantes pour analyse complète>"]
}

Règles d'évaluation :
- Verdict "Critique" si ≥ 1 écart > 20 % OU déboursé > avancement de plus de 15 points OU rapports d'avancement absents
- Verdict "À surveiller" si écarts entre 10-20 % OU déboursé > avancement de 5-15 points
- Verdict "OK" sinon`;
}

function buildOpusValidationPrompt(originalAnalysis, dossier, stats, ecarts) {
  return `Tu es un VP Crédit institutionnel chez Capital Norvex (niveau Stikeman/BlackRock/Brookfield). Une analyse Track a été produite par un analyste Sonnet et a soulevé un verdict Critique. Ta tâche : VALIDATION INDÉPENDANTE.

═══════════════════════════════════════════════════════════════════
DOSSIER
═══════════════════════════════════════════════════════════════════
${JSON.stringify({ id: dossier.id, borrowerName: dossier.borrowerName || dossier.name, loanType: dossier.loanType, projectAddress: dossier.projectAddress }, null, 2)}

═══════════════════════════════════════════════════════════════════
STATS + ÉCARTS
═══════════════════════════════════════════════════════════════════
${JSON.stringify({ stats, ecarts }, null, 2)}

═══════════════════════════════════════════════════════════════════
ANALYSE INITIALE (Sonnet 4.6)
═══════════════════════════════════════════════════════════════════
${JSON.stringify(originalAnalysis, null, 2)}

═══════════════════════════════════════════════════════════════════
TÂCHE
═══════════════════════════════════════════════════════════════════

Challenge l'analyse Sonnet :
1. Es-tu d'accord avec le verdict global ?
2. Risques NON identifiés ?
3. Faux positifs ?
4. Recommandation finale au Comité Crédit ?

Sortie JSON STRICT :
{
  "validation_verdict": "confirme | override_plus_severe | override_plus_souple",
  "verdict_global_final": "OK | À surveiller | Critique",
  "raisons_override": "<court ou null>",
  "risques_supplementaires_detectes": ["<...>"],
  "faux_positifs_corriges": ["<...>"],
  "recommandation_comite_credit": "<1-2 phrases>",
  "decision_suggeree": "continuer_deboursements | conditions_supplementaires | suspendre_deboursements | escalade_seance_speciale"
}`;
}

function parseJsonOutput(raw) {
  let s = raw.trim();
  s = s.replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/\s*```$/i, "");
  const match = s.match(/\{[\s\S]*\}/);
  if (match) s = match[0];
  return JSON.parse(s);
}

// ─── Handler ──────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────
// Background Function (suffixe -background) — timeout 15 min Netlify.
// Reçoit { jobId, dossierId, documents?, force_opus_validation? }
// Écrit le résultat (ou l'erreur) dans Firestore trackJobs/{jobId}.
// Le client poll /api/track-job-status?jobId=xxx pour récupérer.
// ─────────────────────────────────────────────────────────────────────
export default async (req) => {
  if (req.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405 });
  }

  let body;
  try {
    body = await req.json();
  } catch {
    return new Response("Invalid JSON", { status: 400 });
  }

  const { jobId, dossierId, documents, force_opus_validation } = body;
  if (!jobId || !dossierId) {
    return new Response("Missing jobId or dossierId", { status: 400 });
  }

  const KEY = process.env.ANTHROPIC_API_KEY;
  if (!KEY) {
    return new Response("Server config error (no ANTHROPIC_API_KEY)", { status: 500 });
  }

  const { getServiceAccount } = await import("./_firebase-sa.mjs");
  let sa;
  try {
    sa = await getServiceAccount();
  } catch (e) {
    return new Response("Invalid SA: " + e.message, { status: 500 });
  }

  const projectId = sa.project_id;
  let token;

  try {
    token = await getFirestoreToken(sa);

    // Mark job running
    await updateTrackJob(projectId, token, jobId, {
      status: "running",
      startedAt: new Date().toISOString(),
    });

    const dossier = await getFsDoc(projectId, token, `dossiers/${dossierId}`);
    if (!dossier) {
      await updateTrackJob(projectId, token, jobId, {
        status: "error",
        completedAt: new Date().toISOString(),
        error: "Dossier introuvable",
      });
      return new Response(JSON.stringify({ ok: false, error: "Dossier introuvable" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    dossier.id = dossierId;

    const ventilation = dossier.ventilation || [];
    if (!Array.isArray(ventilation) || ventilation.length === 0) {
      const result = {
        dossierId,
        hasData: false,
        message:
          "Aucune ventilation Track pour ce dossier. Initialiser via capital-norvex-track.html.",
      };
      await updateTrackJob(projectId, token, jobId, {
        status: "done",
        completedAt: new Date().toISOString(),
        result,
      });
      return new Response(JSON.stringify({ ok: true, jobId, result }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    const trackData = {
      ventilation,
      demandes: dossier.demandes || [],
      trackPct: dossier.trackPct,
      trackDebourse: dossier.trackDebourse,
    };

    const stats = computeStats(ventilation);
    const ecarts = computeEcarts(ventilation);

    // Multimodal optionnel — accepte contentBase64 OU storagePath (download server-side)
    const docsArr = Array.isArray(documents) ? documents : [];
    if (docsArr.length > 8) {
      return json({ error: "Maximum 8 documents par appel" }, 400);
    }

    // Storage token lazy (créé seulement si au moins un doc a storagePath)
    let storageToken = null;
    const bucket = process.env.FIREBASE_STORAGE_BUCKET || `${sa.project_id}.appspot.com`;
    const needsStorage = docsArr.some(
      (d) => !d.contentBase64 && (d.storagePath || d.path)
    );
    if (needsStorage) {
      try { storageToken = await getStorageToken(sa); }
      catch (e) { return json({ error: "Storage auth failed: " + e.message }, 500); }
    }

    // Résolution parallèle des PDFs (download depuis Firebase Storage si storagePath)
    const resolved = await Promise.all(
      docsArr.map(async (doc) => {
        const mediaType = doc.mediaType || "application/pdf";
        let base64 = doc.contentBase64;
        if (!base64) {
          const path = doc.storagePath || doc.path;
          if (path && storageToken) {
            base64 = await downloadFromStorage(path, storageToken, bucket);
            if (!base64) return null;
          } else {
            return null;
          }
        }
        return { name: doc.name || "document.pdf", mediaType, base64 };
      })
    );

    const contentBlocks = [];
    for (const doc of resolved) {
      if (!doc || !doc.base64) continue;
      if (doc.mediaType === "application/pdf") {
        contentBlocks.push({
          type: "document",
          source: { type: "base64", media_type: "application/pdf", data: doc.base64 },
        });
      } else if (doc.mediaType.startsWith("image/")) {
        contentBlocks.push({
          type: "image",
          source: { type: "base64", media_type: doc.mediaType, data: doc.base64 },
        });
      }
    }

    const hasDocuments = contentBlocks.length > 0;
    const prompt = buildPrompt(dossier, trackData, stats, ecarts, hasDocuments, contentBlocks.length);
    contentBlocks.push({ type: "text", text: prompt });

    const headers1 = {
      "x-api-key": KEY,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    };
    if (hasDocuments) headers1["anthropic-beta"] = "pdfs-2024-09-25";

    // Pass #1 : Sonnet 4.6
    const claudeResp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: headers1,
      body: JSON.stringify({
        model: "claude-sonnet-4-6",
        max_tokens: 2500,
        messages: [{ role: "user", content: contentBlocks }],
      }),
    });

    if (!claudeResp.ok) {
      const err = await claudeResp.text();
      return json({ error: "Claude API error: " + err.slice(0, 300) }, 502);
    }

    const claudeData = await claudeResp.json();
    const rawText = claudeData.content?.[0]?.text || "";

    let analysis;
    try {
      analysis = parseJsonOutput(rawText);
    } catch (e) {
      return json(
        { error: "Parse JSON failed: " + e.message, raw: rawText.slice(0, 300) },
        500
      );
    }

    // Pass #2 : Opus validation si Critique ou forcé
    let opusValidation = null;
    const shouldValidate =
      force_opus_validation === true ||
      analysis.verdict_global === "Critique";

    if (shouldValidate) {
      try {
        const opusResp = await fetch("https://api.anthropic.com/v1/messages", {
          method: "POST",
          headers: {
            "x-api-key": KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
          },
          body: JSON.stringify({
            model: "claude-opus-4-6",
            max_tokens: 1500,
            messages: [
              {
                role: "user",
                content: buildOpusValidationPrompt(analysis, dossier, stats, ecarts),
              },
            ],
          }),
        });
        if (opusResp.ok) {
          const opusData = await opusResp.json();
          const opusRaw = opusData.content?.[0]?.text || "";
          try {
            opusValidation = parseJsonOutput(opusRaw);
          } catch {
            opusValidation = { error: "Opus JSON parse failed", raw: opusRaw.slice(0, 300) };
          }
        } else {
          opusValidation = { error: "Opus API error: " + (await opusResp.text()).slice(0, 200) };
        }
      } catch (e) {
        opusValidation = { error: "Opus validation exception: " + e.message };
      }
    }

    const result = {
      dossierId,
      hasData: true,
      mode: hasDocuments ? "multimodal" : "data_only",
      documents_count: docsArr.length,
      stats,
      ecarts,
      ventilation_count: ventilation.length,
      ...analysis,
      opus_validation: opusValidation,
      analyzed_at: new Date().toISOString(),
      model: "claude-sonnet-4-6" + (opusValidation ? " + claude-opus-4-6 (validation)" : ""),
    };

    await updateTrackJob(projectId, token, jobId, {
      status: "done",
      completedAt: new Date().toISOString(),
      result,
    });

    return new Response(JSON.stringify({ ok: true, jobId, result }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error(`[track-bg] Job ${jobId} FAILED:`, e.message);
    try {
      const fsTok = token || (await getFirestoreToken(sa));
      await updateTrackJob(projectId, fsTok, jobId, {
        status: "error",
        completedAt: new Date().toISOString(),
        error: (e.message || "unknown").slice(0, 1000),
      });
    } catch (_) {
      // non-fatal
    }
    return new Response(JSON.stringify({ ok: false, error: e.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
};
