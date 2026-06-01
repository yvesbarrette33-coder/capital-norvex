/**
 * POST /.netlify/functions/cost-analyze-dossier
 * Header: x-internal-secret
 * Body: {
 *   dossierId,
 *   documents?: [{ name, mediaType, contentBase64 }],  // PDFs factures/devis
 *   force_opus_validation?: bool                        // forcer pass Opus
 * }
 *
 * UPGRADE 2026-05-05 SOIR (V2) — Hugo NORVEX CHANTIER™ :
 *   - max_tokens 1500 → 2500
 *   - Mode multimodal (factures, devis, rapports architecte)
 *   - Stress tests intégrés (dépassement +15 %, retard, taux sup)
 *   - Validation Opus 4.6 second-pass si verdict Critique (ou forcé)
 *
 * Output JSON :
 *   {
 *     dossierId, hasData, mode: "data_only"|"multimodal",
 *     inputs, verdicts, verdict_global, synthesis, recommendation,
 *     stress_tests, opus_validation? (si effectuée),
 *     analyzed_at, model
 *   }
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

// ─── Firestore auth ───────────────────────────────────────────────────────
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

// ─── Prompt expert (data-only ou multimodal) ──────────────────────────────

function buildPrompt(dossier, costData, hasDocuments, documentsCount) {
  const docsBlock = hasDocuments
    ? `═══════════════════════════════════════════════════════════════════
DOCUMENTS PDF FOURNIS (${documentsCount})
═══════════════════════════════════════════════════════════════════
Tu as reçu ${documentsCount} document(s) (factures, devis, soumissions, rapports). Lis-les et croise-les avec les données Cost Analyzer ci-dessous. Détecte tout écart entre saisie UI et factures réelles.

`
    : "";

  return `Tu es un expert en analyse financière de projets de construction immobilière au Québec et en Ontario, avec 20+ ans d'expérience en prêt privé institutionnel chez Capital Norvex.

Tu analyses les données financières d'un projet de construction pour produire un rapport de risque structuré sur les 5 modules clés : équité, honoraires, coût/porte, holdback, soft costs. Tu inclus aussi des STRESS TESTS pour évaluer la résilience du projet.

═══════════════════════════════════════════════════════════════════
DOSSIER
═══════════════════════════════════════════════════════════════════
ID : ${dossier?.id || "N/D"}
Nom emprunteur : ${dossier?.borrowerName || dossier?.name || "N/D"}
Type de prêt : ${dossier?.loanType || "N/D"}
Adresse projet : ${dossier?.projectAddress || "N/D"}
Type d'actif : ${dossier?.assetType || "N/D"}
Phase : ${dossier?.phase || dossier?.status || "N/D"}

${docsBlock}═══════════════════════════════════════════════════════════════════
DONNÉES COST ANALYZER (saisie UI)
═══════════════════════════════════════════════════════════════════
${JSON.stringify(costData, null, 2)}

═══════════════════════════════════════════════════════════════════
TÂCHE — ANALYSE 5 MODULES + STRESS TESTS
═══════════════════════════════════════════════════════════════════

Analyse les 5 modules selon les standards Capital Norvex :

1. **ÉQUITÉ** — Mise de fonds vs LTC (Loan-to-Cost)
   - Cible : équité ≥ 25-30 % du coût total projet
   - Verdict : OK / À surveiller / Critique

2. **HONORAIRES** — % d'honoraires sur coûts durs
   - Cible : honoraires ≤ 8-12 % des coûts durs
   - Verdict : OK / À surveiller / Critique

3. **COÛT/PORTE** — Comparaison vs marché
   - Cible : ne dépasse pas +20 % du coût/porte marché du secteur
   - Verdict : OK / À surveiller / Critique

4. **HOLDBACK** — Couverture
   - Cible : holdback effectif ≥ 100 % du holdback requis (5 % coûts durs)
   - Verdict : OK / À surveiller / Critique

5. **SOFT COSTS** — Ratio sur projet total
   - Cible : soft costs ≤ 15-20 % du coût total projet
   - Verdict : OK / À surveiller / Critique

Si une donnée manque pour un module, marque le verdict "EN_ATTENTE" et note ce qui manque.

STRESS TESTS (obligatoires) :
- Scénario A : dépassement coûts durs +15 %
- Scénario B : retard 3 mois → +intérêts + soft costs
- Scénario C : taux d'intérêt +1,5 pt
Pour chaque scénario, indique l'impact sur la couverture (équité résiduelle, LTC final).

═══════════════════════════════════════════════════════════════════
FORMAT DE SORTIE — JSON STRICT (aucun texte avant/après)
═══════════════════════════════════════════════════════════════════

{
  "verdicts": {
    "equity": { "status": "OK | À surveiller | Critique | EN_ATTENTE", "value_pct": <nombre|null>, "notes": "<court>" },
    "honoraires": { "status": "...", "value_pct": <nombre|null>, "notes": "<court>" },
    "cout_porte": { "status": "...", "value": <nombre|null>, "notes": "<court>" },
    "holdback": { "status": "...", "coverage_pct": <nombre|null>, "notes": "<court>" },
    "soft_costs": { "status": "...", "value_pct": <nombre|null>, "notes": "<court>" }
  },
  "verdict_global": "OK | À surveiller | Critique",
  "verdict_global_justification": "<court>",
  "synthesis": "<résumé textuel 3-5 phrases>",
  "recommendation": "<recommandation actionnable Hugo : ce qu'il faut faire/demander/clarifier>",
  "stress_tests": {
    "scenario_a_depassement_15pct": { "ltc_final_pct": <nombre|null>, "equite_residuelle_pct": <nombre|null>, "verdict": "OK | À surveiller | Critique", "notes": "<court>" },
    "scenario_b_retard_3mois": { "cout_supplementaire": <nombre|null>, "verdict": "OK | À surveiller | Critique", "notes": "<court>" },
    "scenario_c_taux_plus_1_5pt": { "interet_supplementaire_annuel": <nombre|null>, "verdict": "OK | À surveiller | Critique", "notes": "<court>" }
  },
  "ecarts_documents_vs_saisie": ${hasDocuments ? '"<liste des écarts détectés entre PDFs et saisie UI, ou \\"aucun écart\\">"' : "null"},
  "data_gaps": ["<liste des données manquantes pour analyse complète>"]
}`;
}

function buildOpusValidationPrompt(originalAnalysis, dossier, costData) {
  return `Tu es un VP Crédit institutionnel chez Capital Norvex (Stikeman/BlackRock/Brookfield niveau). Une analyse Cost Analyzer a été produite par un analyste Sonnet et a soulevé un verdict Critique (ou borderline). Ta tâche : VALIDATION INDÉPENDANTE.

═══════════════════════════════════════════════════════════════════
DOSSIER
═══════════════════════════════════════════════════════════════════
${JSON.stringify({ id: dossier.id, borrowerName: dossier.borrowerName || dossier.name, loanType: dossier.loanType, projectAddress: dossier.projectAddress, assetType: dossier.assetType }, null, 2)}

═══════════════════════════════════════════════════════════════════
DONNÉES COST ANALYZER
═══════════════════════════════════════════════════════════════════
${JSON.stringify(costData, null, 2)}

═══════════════════════════════════════════════════════════════════
ANALYSE INITIALE (Sonnet 4.6)
═══════════════════════════════════════════════════════════════════
${JSON.stringify(originalAnalysis, null, 2)}

═══════════════════════════════════════════════════════════════════
TÂCHE
═══════════════════════════════════════════════════════════════════

Challenge l'analyse Sonnet :
1. Es-tu d'accord avec le verdict global ? (override possible)
2. Y a-t-il des risques NON identifiés que tu vois ?
3. Y a-t-il des faux positifs (verdict trop sévère) ?
4. Quelle est ta recommandation finale au Comité Crédit ?

Sortie JSON STRICT :
{
  "validation_verdict": "confirme | override_plus_severe | override_plus_souple",
  "verdict_global_final": "OK | À surveiller | Critique",
  "raisons_override": "<court ou null>",
  "risques_supplementaires_detectes": ["<...>"],
  "faux_positifs_corriges": ["<...>"],
  "recommandation_comite_credit": "<1-2 phrases>",
  "decision_suggeree": "approuver | approuver_avec_conditions | reporter | refuser"
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
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON" }, 400);
  }

  const { dossierId, documents, force_opus_validation } = body;
  if (!dossierId) return json({ error: "dossierId required" }, 400);

  const KEY = process.env.ANTHROPIC_API_KEY;
  if (!KEY) return json({ error: "ANTHROPIC_API_KEY not set" }, 500);

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let sa;


  try { sa = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  try {
    const token = await getFirestoreToken(sa);
    const projectId = sa.project_id;

    const dossier = await getFsDoc(projectId, token, `dossiers/${dossierId}`);
    if (!dossier) return json({ error: "Dossier introuvable" }, 404);
    dossier.id = dossierId;

    const costData = await getFsDoc(
      projectId,
      token,
      `dossiers/${dossierId}/costAnalyzer/current`
    );

    if (!costData) {
      return json({
        dossierId,
        hasData: false,
        message:
          "Aucune donnée Cost Analyzer pour ce dossier. Faire d'abord saisir la ventilation dans capital-norvex-cost-analyzer.html.",
      });
    }

    // Construire content blocks (multimodal si documents fournis)
    // Accepte contentBase64 OU storagePath (download server-side via Firebase Storage)
    const docsArr = Array.isArray(documents) ? documents : [];
    if (docsArr.length > 8) {
      return json({ error: "Maximum 8 documents par appel" }, 400);
    }

    let storageToken = null;
    const bucket = process.env.FIREBASE_STORAGE_BUCKET || `${sa.project_id}.appspot.com`;
    const needsStorage = docsArr.some(
      (d) => !d.contentBase64 && (d.storagePath || d.path)
    );
    if (needsStorage) {
      try { storageToken = await getStorageToken(sa); }
      catch (e) { return json({ error: "Storage auth failed: " + e.message }, 500); }
    }

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
    const prompt = buildPrompt(dossier, costData, hasDocuments, contentBlocks.length);
    contentBlocks.push({ type: "text", text: prompt });

    // Pass #1 : Sonnet 4.6 (rapide, économique)
    const headers1 = {
      "x-api-key": KEY,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    };
    if (hasDocuments) headers1["anthropic-beta"] = "pdfs-2024-09-25";

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

    // Pass #2 : Opus 4.6 validation si verdict Critique ou forcé
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
                content: buildOpusValidationPrompt(analysis, dossier, costData),
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

    return json({
      dossierId,
      hasData: true,
      mode: hasDocuments ? "multimodal" : "data_only",
      documents_count: docsArr.length,
      inputs: costData,
      ...analysis,
      opus_validation: opusValidation,
      analyzed_at: new Date().toISOString(),
      model: "claude-sonnet-4-6" + (opusValidation ? " + claude-opus-4-6 (validation)" : ""),
    });
  } catch (e) {
    return json({ error: e.message }, 500);
  }
};

export const config = {
  path: "/api/cost-analyze-dossier",
};
