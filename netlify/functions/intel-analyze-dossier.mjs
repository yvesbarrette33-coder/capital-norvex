/**
 * POST /.netlify/functions/intel-analyze-dossier
 * Header: x-internal-secret
 * Body: {
 *   dossierId,
 *   documents?: [
 *     // Format A — base64 inline (legacy, taille limitée par Netlify body cap ~6 MB)
 *     { name, mediaType, contentBase64 },
 *     // Format B — storage path (ajouté 2026-05-13, Intel télécharge lui-même)
 *     { name, mediaType, storagePath }
 *   ]
 * }
 *
 * UPGRADE 2026-05-05 pour Hugo NORVEX CHANTIER™ —
 * Endpoint orchestrateur Norvex Intel V3 (mode documents).
 *
 * Hugo passe les PDFs pertinents du dossier (titres, baux, états financiers,
 * évaluation initiale, photos…). Claude Opus 4.6 multimodal lit les
 * documents, extrait les données pertinentes et calcule lui-même les
 * 3 approches d'évaluation immobilière (revenu, comparables, coût) +
 * réconciliation + valeur prêteur conservative + verdict.
 *
 * Si pas de documents fournis : fallback sur les données dossier Firestore
 * (sujet de base + données financières si déjà saisies via UI Intel).
 *
 * UPGRADE 2026-05-13 — Hugo audit Action #1 :
 *   - Accepte format B : { name, storagePath, mediaType } → Intel télécharge
 *     directement depuis Firebase Storage (bypass Netlify body cap).
 *   - Format A (contentBase64) toujours supporté pour rétrocompatibilité.
 *   - Mixé : si les deux présents, storagePath prime (plus fiable serveur-à-serveur).
 *
 * Limites :
 * - Max 8 PDFs par appel (timeout Netlify 26s + payload Anthropic)
 * - Documents > 32 MB total → erreur
 *
 * Output JSON :
 *   { dossierId, mode: "from_docs"|"from_dossier", evaluation: {...},
 *     extracted_data: {...}, analyzed_at, model }
 */

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// ─── Firestore auth (réutilise pattern existant) ──────────────────────────
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
      .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const signingInput = `${b64(header)}.${b64(payload)}`;
  const pemBody = sa.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\n/g, "");
  const keyData = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));
  const privateKey = await crypto.subtle.importKey(
    "pkcs8", keyData.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]
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

// ─── Prompt expert Intel V3 (mode documents multimodal) ──────────────────

function buildPromptFromDocs(dossier, documentsCount) {
  return `Tu es un évaluateur immobilier expert (équivalent OEAQ) avec 20+ ans d'expérience en financement privé immobilier institutionnel au Québec et Ontario chez Capital Norvex.

Tu as reçu ${documentsCount} document(s) PDF concernant un dossier de financement immobilier. Lis les documents fournis, extrais les données pertinentes, puis produis une PRÉ-ÉVALUATION rigoureuse en 3 approches.

═══════════════════════════════════════════════════════════════════
DOSSIER (contexte fourni par Hugo)
═══════════════════════════════════════════════════════════════════
ID : ${dossier?.id || "N/D"}
Emprunteur : ${dossier?.borrowerName || dossier?.name || "N/D"}
Type de prêt : ${dossier?.loanType || "N/D"}
Adresse projet : ${dossier?.projectAddress || "N/D"}
Type d'actif : ${dossier?.assetType || "N/D"}
Phase : ${dossier?.phase || dossier?.status || "N/D"}

═══════════════════════════════════════════════════════════════════
TÂCHE — PRÉ-ÉVALUATION COMPLÈTE
═══════════════════════════════════════════════════════════════════

ÉTAPE 1 — Extraction des données depuis les PDFs :
- Adresse exacte, type d'actif, superficies (terrain, bâtiment), année construction
- Évaluation municipale (si visible)
- Données financières : NOI, revenus bruts, charges, loyers/unités, baux
- Données coût : coût de construction, terrain
- Comparables marché (si évaluation incluse)
- Tout autre élément pertinent (titres, RDPRM, hypothèques existantes)

ÉTAPE 2 — Calcul des 3 approches :
1. **Revenu** (cap rate marché QC/ON 2026 selon type/secteur, NOI / cap)
2. **Comparables** ($/pi² ou $/porte selon ventes récentes similaires)
3. **Coût** (coût remplacement + dépréciation + terrain)

ÉTAPE 3 — Réconciliation pondérée selon type d'actif

ÉTAPE 4 — Valeur prêteur (réconciliée − marge sécurité 10-15 %)

ÉTAPE 5 — Stress tests (loyers -10 %, cap rate +1 pt)

ÉTAPE 6 — Verdict avec niveau de confiance + risques principaux

═══════════════════════════════════════════════════════════════════
FORMAT DE SORTIE — JSON STRICT (aucun texte avant/après)
═══════════════════════════════════════════════════════════════════

{
  "extracted_data": {
    "adresse": "<...>",
    "type_actif": "<...>",
    "superficie_terrain": <nombre|null>,
    "superficie_batiment": <nombre|null>,
    "annee_construction": <nombre|null>,
    "eval_muni": <nombre|null>,
    "noi_estime": <nombre|null>,
    "revenus_bruts": <nombre|null>,
    "charges": <nombre|null>,
    "cout_construction": <nombre|null>,
    "documents_lus": ["<nom1.pdf>", "<nom2.pdf>"],
    "data_quality": "complete|partielle|insuffisante"
  },
  "approche_revenu": { "noi_utilise": <nombre|null>, "cap_rate": <nombre>, "cap_rate_justification": "<court>", "valeur": <nombre>, "applicable": <bool>, "notes": "<court>" },
  "approche_comparables": { "ratio_unitaire": <nombre>, "ratio_unite": "<...>", "ratio_justification": "<court>", "valeur": <nombre>, "applicable": <bool>, "notes": "<court>" },
  "approche_cout": { "cout_neuf_pi2": <nombre>, "depreciation_pct": <nombre>, "valeur_terrain": <nombre>, "valeur": <nombre>, "applicable": <bool>, "notes": "<court>" },
  "reconciliation": { "poids_revenu_pct": <nombre>, "poids_comparables_pct": <nombre>, "poids_cout_pct": <nombre>, "justification_ponderation": "<court>", "valeur_mid": <nombre>, "valeur_low": <nombre>, "valeur_high": <nombre> },
  "valeur_preteur": { "marge_securite_pct": <nombre>, "marge_justification": "<court>", "valeur": <nombre> },
  "stress_tests": { "loyers_moins_10": <nombre>, "cap_rate_plus_1pt": <nombre>, "scenario_defavorable": "<court>" },
  "verdict": { "confiance": "élevé|modéré|faible", "confiance_justification": "<court>", "recommandation": "financement_ok|ok_avec_conditions|a_approfondir|refus_recommande", "recommandation_texte": "<1-2 phrases>", "risques_principaux": ["<risque 1>", "<risque 2>", "<risque 3>"] },
  "disclaimer": "Pré-évaluation IA Norvex Intel V3 (mode documents). Sert à la décision interne et la LOI préliminaire. Ne remplace PAS une évaluation OEAQ certifiée pour closing."
}`;
}

// ─── Firebase Storage download (pour format B : storagePath) ──────────────
// Réutilise le pattern get-firebase-download-url.mjs (zone connue, prod).

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

  const { dossierId, documents } = body;
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

    const docsArr = Array.isArray(documents) ? documents : [];
    if (docsArr.length === 0) {
      return json({
        dossierId,
        hasDocuments: false,
        message:
          "Aucun document fourni. Hugo doit passer body.documents = [{name, mediaType, contentBase64}] OU [{name, mediaType, storagePath}] (Intel téléchargera depuis Firebase Storage).",
      });
    }
    if (docsArr.length > 8) {
      return json(
        {
          error:
            "Maximum 8 documents par appel (limite Netlify timeout + payload Claude)",
        },
        400
      );
    }

    // Token Storage lazy : créé seulement si au moins un doc a storagePath
    let storageToken = null;
    const bucket =
      process.env.FIREBASE_STORAGE_BUCKET ||
      `${sa.project_id}.appspot.com`;
    const needsStorage = docsArr.some(
      (d) => !d.contentBase64 && (d.storagePath || d.path)
    );
    if (needsStorage) {
      try {
        storageToken = await getStorageToken(sa);
      } catch (e) {
        return json(
          { error: "Storage auth failed: " + e.message },
          500
        );
      }
    }

    // Résolution des documents : download storage paths si nécessaire (parallèle)
    const downloadStats = {
      from_base64: 0,
      from_storage: 0,
      storage_failed: 0,
    };
    const resolved = await Promise.all(
      docsArr.map(async (doc) => {
        const mediaType = doc.mediaType || "application/pdf";
        let base64 = doc.contentBase64;
        if (!base64) {
          const path = doc.storagePath || doc.path;
          if (path && storageToken) {
            base64 = await downloadFromStorage(path, storageToken, bucket);
            if (base64) {
              downloadStats.from_storage++;
            } else {
              downloadStats.storage_failed++;
              return null;
            }
          } else {
            return null;
          }
        } else {
          downloadStats.from_base64++;
        }
        return {
          name: doc.name || "document.pdf",
          mediaType,
          contentBase64: base64,
        };
      })
    );

    // Construire le contenu multimodal pour Claude
    const contentBlocks = [];
    for (const doc of resolved) {
      if (!doc || !doc.contentBase64) continue;
      const mediaType = doc.mediaType || "application/pdf";
      if (mediaType === "application/pdf") {
        contentBlocks.push({
          type: "document",
          source: {
            type: "base64",
            media_type: "application/pdf",
            data: doc.contentBase64,
          },
        });
      } else if (mediaType.startsWith("image/")) {
        contentBlocks.push({
          type: "image",
          source: {
            type: "base64",
            media_type: mediaType,
            data: doc.contentBase64,
          },
        });
      }
    }

    if (contentBlocks.length === 0) {
      return json({
        error: "Aucun document valide téléchargé/fourni",
        download_stats: downloadStats,
      }, 400);
    }

    contentBlocks.push({
      type: "text",
      text: buildPromptFromDocs(dossier, contentBlocks.length),
    });

    const claudeResp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": KEY,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "pdfs-2024-09-25",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        // UPGRADE 2026-05-13 : passage Opus → Sonnet 4.6 pour tenir le
        // budget Netlify 26s sur PDFs volumineux (évaluations 8-15 MB).
        // Sonnet 4.6 reste excellent pour extraction + 3 approches.
        // Garde-fou : si verdict borderline/Critique, on pourrait ajouter
        // validation Opus second-pass (pattern Track/Cost déjà en prod).
        model: "claude-sonnet-4-6",
        max_tokens: 3000,
        messages: [{ role: "user", content: contentBlocks }],
      }),
    });

    if (!claudeResp.ok) {
      const err = await claudeResp.text();
      return json({ error: "Claude API error: " + err.slice(0, 300) }, 502);
    }

    const claudeData = await claudeResp.json();
    const rawText = claudeData.content?.[0]?.text || "";

    let evaluation;
    try {
      evaluation = parseJsonOutput(rawText);
    } catch (e) {
      return json(
        { error: "Parse JSON failed: " + e.message, raw: rawText.slice(0, 500) },
        500
      );
    }

    return json({
      dossierId,
      mode: "from_docs",
      documents_analyzed: contentBlocks.length - 1, // -1 pour le bloc text
      download_stats: downloadStats,
      evaluation,
      analyzed_at: new Date().toISOString(),
      model: "claude-sonnet-4-6",
    });
  } catch (e) {
    return json({ error: e.message }, 500);
  }
};

export const config = {
  path: "/api/intel-analyze-dossier",
};
