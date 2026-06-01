/**
 * Hugo NORVEX CHANTIER™ — Background Orchestrator (15 min budget)
 *
 * Netlify Background Function (suffixe "-background" non requis si on déclare
 * `type: "background"` dans la config exportée).
 *
 * Reçoit { jobId, dossierId, skipNorvexFinal? } via POST.
 * Retourne 202 immédiatement, continue à tourner en arrière-plan.
 *
 * Pipeline :
 *   1. Charge dossier + pdfBlobs depuis Firestore
 *   2. Évaluation Intel V3 multimodale INLINE
 *      → appelle directement Anthropic Claude Sonnet 4.6 avec PDFs (URLs ou base64)
 *      → pas de roundtrip HTTP vers intel-analyze-dossier (bypass Netlify body cap)
 *      → 15 min budget (vs 26 s du sync function cap)
 *   3. Track + Cost en HTTP parallèle (payloads small, data-only)
 *   4. Synthèse Opus 4.6 (3 rapports → verdict business consolidé)
 *   5. Push Brain
 *   6. Norvex Final (si verdict ≠ Critique et skipNorvexFinal ≠ true)
 *   7. Update job status dans Firestore (hugoJobs/{jobId})
 *
 * Created 2026-05-13 — Action #1 audit Hugo, phase finale.
 *
 * NOTE : Le déclencheur est `hugo-run-analysis` (sync, thin) qui :
 *   - crée jobId
 *   - persiste {status:"pending"} dans hugoJobs/{jobId}
 *   - fire-and-forget POST vers hugo-bg-orchestrator
 *   - retourne 202 {jobId} au client
 *
 * Le client/UI/watcher poll ensuite hugo-job-status?jobId=xxx.
 */

import { getStore } from "@netlify/blobs";
import crypto from "node:crypto";

const SITE_URL = process.env.SITE_URL || "https://capitalnorvex.com";

// ─── V4 signed URL just-in-time (régénère depuis storagePath) ─────────────
// Évite de dépendre d'URLs stockées qui expirent après 7 jours max.
// À chaque run Hugo, on regénère une URL fraîche 7j.

function _strictEncode(str) {
  return encodeURIComponent(str).replace(
    /[!'()*]/g,
    (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`
  );
}

function createV4SignedGetUrl(serviceAccount, bucket, objectPath, expiresSeconds = 7 * 24 * 3600) {
  const now = new Date();
  const ymd = now.toISOString().slice(0, 10).replace(/-/g, "");
  const hms = now.toISOString().slice(11, 19).replace(/:/g, "");
  const ts = `${ymd}T${hms}Z`;

  const credentialScope = `${ymd}/auto/storage/goog4_request`;
  const credentialValue = `${serviceAccount.client_email}/${credentialScope}`;

  const headersToSign = { host: "storage.googleapis.com" };
  const signedHeaderNames = Object.keys(headersToSign).map((k) => k.toLowerCase()).sort();
  const canonicalHeaders =
    signedHeaderNames.map((h) => `${h}:${headersToSign[h]}`).join("\n") + "\n";
  const signedHeadersStr = signedHeaderNames.join(";");

  const encodedPath = objectPath.split("/").map(_strictEncode).join("/");
  const canonicalUri = `/${bucket}/${encodedPath}`;

  const params = {
    "X-Goog-Algorithm": "GOOG4-RSA-SHA256",
    "X-Goog-Credential": credentialValue,
    "X-Goog-Date": ts,
    "X-Goog-Expires": String(expiresSeconds),
    "X-Goog-SignedHeaders": signedHeadersStr,
  };
  const canonicalQueryString = Object.keys(params)
    .sort()
    .map((k) => `${_strictEncode(k)}=${_strictEncode(params[k])}`)
    .join("&");

  const canonicalRequest = [
    "GET",
    canonicalUri,
    canonicalQueryString,
    canonicalHeaders,
    signedHeadersStr,
    "UNSIGNED-PAYLOAD",
  ].join("\n");

  const hashedRequest = crypto.createHash("sha256").update(canonicalRequest).digest("hex");
  const stringToSign = [
    "GOOG4-RSA-SHA256",
    ts,
    credentialScope,
    hashedRequest,
  ].join("\n");

  const pemBody = serviceAccount.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\n/g, "");
  const keyData = Buffer.from(pemBody, "base64");
  const privateKey = crypto.createPrivateKey({
    key: keyData, format: "der", type: "pkcs8",
  });
  const signature = crypto.sign("RSA-SHA256", Buffer.from(stringToSign), privateKey).toString("hex");

  return `https://storage.googleapis.com${canonicalUri}?${canonicalQueryString}&X-Goog-Signature=${signature}`;
}

// ─── Helpers JSON / Firestore ─────────────────────────────────────────────

async function getFirestoreToken(sa, scope = "https://www.googleapis.com/auth/datastore") {
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
  if (!data.access_token) throw new Error("Firestore token failed: " + JSON.stringify(data).slice(0, 200));
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

async function fsGet(projectId, token, path) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${path}`;
  const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`Firestore GET ${path} failed: ${r.status}`);
  const data = await r.json();
  if (!data.fields) return null;
  const out = {};
  for (const [k, v] of Object.entries(data.fields)) out[k] = fromFsValue(v);
  return out;
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
    throw new Error(`Firestore PATCH failed: ${r.status} ${txt.slice(0, 200)}`);
  }
  return true;
}

// ─── Job status updates ───────────────────────────────────────────────────
// hugoJobs/{jobId} = { status, dossierId, startedAt, completedAt, result, error }

async function updateJobStatus(jobId, sa, patch) {
  try {
    const token = await getFirestoreToken(sa);
    await fsPatch(sa.project_id, token, `hugoJobs/${jobId}`, patch);
  } catch (e) {
    console.error(`[hugo-bg] updateJobStatus(${jobId}) failed:`, e.message);
  }
}

// ─── Email notification Yves quand job done ───────────────────────────────
// On envoie un email LÉGER (verdict + résumé + lien dashboard).
// Si Norvex Final a déjà envoyé son brief détaillé, on skip (anti-duplication).
// Failure non-fatal : job est déjà done, l'email c'est du bonus.

function escHtml(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, c =>
    ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c])
  );
}

function fmtMoney(n) {
  if (n == null || isNaN(n)) return "—";
  if (n >= 1e6) return "$" + (n / 1e6).toFixed(2) + " M";
  if (n >= 1e3) return "$" + Math.round(n).toLocaleString("fr-CA");
  return "$" + Number(n).toFixed(2);
}

function buildHugoCompletionEmail(payload) {
  const {
    dossierId, jobId, verdictGlobal, actionRecommandee, synthesisText,
    reportId, pdfCount, intelMode, intelError,
    norvexFinalStatus, norvexFinalRate, norvexFinalAmount, norvexFinalDecision,
  } = payload;

  const verdictColor =
    verdictGlobal === "OK" ? "#2d8a3e" :
    verdictGlobal === "À surveiller" ? "#d6a800" :
    verdictGlobal === "Critique" ? "#c33" : "#1d4ed8";

  const intelLine = intelMode === "multimodal"
    ? `<span style="color:#2d8a3e">✓ Intel multimodal (${pdfCount} PDF${pdfCount > 1 ? "s" : ""})</span>`
    : intelMode === "error"
    ? `<span style="color:#c33">✗ Intel erreur : ${escHtml(intelError || "?")}</span>`
    : `<span style="color:#777">— Intel skipped (pas de PDFs)</span>`;

  const norvexLine =
    norvexFinalStatus === "ok"
      ? `Norvex Final : <strong>${escHtml(norvexFinalDecision || "?")}</strong> · taux ${escHtml(String(norvexFinalRate || "?"))}% · ${fmtMoney(norvexFinalAmount)}<br><em style="color:#777;font-size:12px">Brief détaillé envoyé séparément.</em>`
      : norvexFinalStatus === "skipped_hugo_critique"
      ? `<span style="color:#c33">Norvex Final SKIPPED (verdict Hugo = Critique).</span>`
      : norvexFinalStatus === "error"
      ? `<span style="color:#c33">Norvex Final ERREUR.</span>`
      : `<span style="color:#777">Norvex Final non exécuté.</span>`;

  return `<!DOCTYPE html>
<html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.5; color: #1a1a1a; max-width: 640px; margin: 0 auto; padding: 24px;">
  <div style="border-top: 4px solid #C9A227; padding-top: 16px;">
    <div style="font-size: 11px; letter-spacing: 2px; color: #777; text-transform: uppercase;">Hugo — Norvex Chantier™</div>
    <h1 style="font-family: 'Playfair Display', Georgia, serif; font-size: 22px; margin: 8px 0 4px 0; color: #1a1a1a;">Analyse complétée</h1>
    <div style="font-size: 13px; color: #777;">Dossier <code>${escHtml(dossierId)}</code> · Job <code>${escHtml(jobId)}</code></div>
  </div>

  <div style="background: #fafbfc; border-left: 5px solid ${verdictColor}; padding: 16px 20px; margin: 20px 0; border-radius: 4px;">
    <div style="font-size: 11px; letter-spacing: 2px; color: #777; text-transform: uppercase;">Verdict global</div>
    <div style="font-size: 22px; font-weight: 700; font-family: 'Playfair Display', Georgia, serif; color: ${verdictColor}; margin: 4px 0;">${escHtml(verdictGlobal || "?")}</div>
    <div style="font-size: 13px; color: #444; font-family: ui-monospace, 'SF Mono', Menlo, monospace;">→ ${escHtml(actionRecommandee || "—")}</div>
  </div>

  <h3 style="font-size: 12px; letter-spacing: 1.5px; text-transform: uppercase; color: #a48618; margin: 24px 0 8px 0;">Synthèse exécutive</h3>
  <p style="line-height: 1.7; font-size: 14px;">${escHtml(synthesisText || "(aucune)")}</p>

  <h3 style="font-size: 12px; letter-spacing: 1.5px; text-transform: uppercase; color: #a48618; margin: 24px 0 8px 0;">Modules</h3>
  <ul style="list-style: none; padding: 0; font-size: 13px; line-height: 1.9;">
    <li>${intelLine}</li>
    <li><span style="color: #2d8a3e">✓ Track + Cost (data-only)</span></li>
    <li>${norvexLine}</li>
  </ul>

  <div style="margin: 32px 0 16px 0; padding-top: 16px; border-top: 1px solid #e5e5e7;">
    <a href="${SITE_URL}/hugo-admin.html"
       style="display: inline-block; background: #0a0a0a; color: #C9A227; padding: 10px 22px; border-radius: 6px; text-decoration: none; font-weight: 700; letter-spacing: 0.5px;">
      Voir le rapport complet →
    </a>
  </div>

  <div style="font-size: 11px; color: #aaa; margin-top: 32px; padding-top: 12px; border-top: 1px solid #e5e5e7; font-family: ui-monospace, 'SF Mono', Menlo, monospace;">
    Capital Norvex Inc. · NEQ 1182097890<br>
    2705-1000 André-Prévost, Île-des-Sœurs, Montréal, QC H3E 0G2<br>
    Hugo NORVEX CHANTIER™ · Background job ${escHtml(jobId)} · Brain reportId ${escHtml(reportId || "—")}
  </div>
</body></html>`;
}

async function sendHugoEmail(toEmail, subject, html) {
  const apiKey = process.env.SENDGRID_API_KEY;
  if (!apiKey) return { ok: false, error: "SENDGRID_API_KEY not set" };
  const payload = {
    personalizations: [{ to: [{ email: toEmail }] }],
    from: { email: "info@capitalnorvex.com", name: "Capital Norvex · Hugo" },
    subject,
    content: [{ type: "text/html", value: html }],
    reply_to: { email: "yves@capitalnorvex.com", name: "Yves Barrette" },
    headers: {
      "X-Capital-Norvex-Type": "hugo-completion",
      "X-Auto-Response-Suppress": "All",
    },
  };
  const resp = await fetch("https://api.sendgrid.com/v3/mail/send", {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const err = await resp.text();
    return { ok: false, error: `SendGrid ${resp.status}: ${err.slice(0, 200)}` };
  }
  return { ok: true, messageId: resp.headers.get("x-message-id") || null };
}

// ─── Prompt Intel V3 (copié de intel-analyze-dossier.mjs) ─────────────────

function buildIntelPrompt(dossier, documentsCount) {
  return `Tu es un évaluateur immobilier expert (équivalent OEAQ) avec 20+ ans d'expérience en financement privé immobilier institutionnel au Québec et Ontario chez Capital Norvex.

Tu as reçu ${documentsCount} document(s) PDF concernant un dossier de financement immobilier. Lis les documents fournis, extrais les données pertinentes, puis produis une PRÉ-ÉVALUATION rigoureuse en 3 approches.

═══════════════════════════════════════════════════════════════════
DOSSIER (contexte fourni par Hugo)
═══════════════════════════════════════════════════════════════════
ID : ${dossier?.id || "N/D"}
Emprunteur : ${dossier?.borrowerName || dossier?.nom || dossier?.name || "N/D"}
Type de prêt : ${dossier?.loanType || dossier?.typePret || "N/D"}
Adresse projet : ${dossier?.projectAddress || dossier?.adresse || "N/D"}
Type d'actif : ${dossier?.assetType || dossier?.typeActif || "N/D"}
Phase : ${dossier?.phase || dossier?.stage || dossier?.status || "N/D"}

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

function parseJsonOutput(raw) {
  let s = raw.trim();
  s = s.replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/\s*```$/i, "");
  const match = s.match(/\{[\s\S]*\}/);
  if (match) s = match[0];
  return JSON.parse(s);
}

// ─── Construction des blocs PDF pour Anthropic (URL ou base64) ────────────
// Préfère le passage par URL (firebase_url.url) car :
// - Pas de body cap (URL = quelques bytes)
// - Anthropic télécharge directement
// - Économise la bande passante de la fonction Netlify

async function expandBlobsToContent(pdfBlobs, store, sa, bucket) {
  const content = [];
  const errors = [];
  for (const blob of pdfBlobs) {
    const blobType = blob.type || "unknown";
    if (blobType === "firebase_url") {
      // Priorité 1 : régénérer URL signée fraîche depuis `path` (anti-expiration)
      // Priorité 2 : utiliser `url` stockée (legacy, peut être expirée après 7j)
      let urlToUse = null;
      if (blob.path && sa && bucket) {
        try {
          urlToUse = createV4SignedGetUrl(sa, bucket, blob.path);
        } catch (e) {
          errors.push(`signed_url_regen_failed ${blob.path}: ${e.message}`);
        }
      }
      if (!urlToUse && blob.url) {
        urlToUse = blob.url;
      }
      if (urlToUse) {
        content.push({
          type: "document",
          source: { type: "url", url: urlToUse },
        });
      } else {
        errors.push(`firebase_url missing both path and url: ${blob.name || "?"}`);
      }
    } else if (blobType === "blob_ref" && blob.key) {
      try {
        const pdf = await store.get(blob.key, { type: "json" });
        if (pdf && pdf.data) {
          content.push({
            type: "document",
            source: { type: "base64", media_type: "application/pdf", data: pdf.data },
          });
        } else {
          errors.push(`blob_ref not found: ${blob.key}`);
        }
      } catch (e) {
        errors.push(`blob_ref error ${blob.key}: ${e.message}`);
      }
    } else if (blobType === "chunked_ref" && blob.key) {
      try {
        const meta = await store.get(`${blob.key}_meta`, { type: "json" });
        if (!meta || !meta.totalChunks) {
          errors.push(`chunked_ref meta missing: ${blob.key}`);
          continue;
        }
        let fullBase64 = "";
        let ok = true;
        for (let i = 0; i < meta.totalChunks; i++) {
          const chunk = await store.get(`${blob.key}_chunk_${i}`, { type: "json" });
          if (!chunk || !chunk.data) {
            ok = false;
            errors.push(`chunked_ref chunk ${i} missing: ${blob.key}`);
            break;
          }
          fullBase64 += chunk.data;
        }
        if (ok) {
          content.push({
            type: "document",
            source: { type: "base64", media_type: "application/pdf", data: fullBase64 },
          });
        }
      } catch (e) {
        errors.push(`chunked_ref error ${blob.key}: ${e.message}`);
      }
    } else {
      errors.push(`unknown blob type or missing fields: ${JSON.stringify(blob).slice(0, 100)}`);
    }
  }
  return { content, errors };
}

// ─── Appel HTTP générique ─────────────────────────────────────────────────

async function callEndpoint(name, path, body, secret, timeoutMs = 60000) {
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

// ─── Synthèse Opus 4.6 ────────────────────────────────────────────────────

const SYNTHESIS_SYSTEM = `Tu es Hugo — NORVEX CHANTIER™, coordonnateur technique chantier IA de Capital Norvex Inc.

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

async function synthesize(dossierId, reports, anthropicKey) {
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
      // 4000 tokens : marge pour synthèse JSON complète avec alertes_consolidees
      // (peut contenir plusieurs entrées) + recommandation_yves + next_steps détaillés.
      // L'expérience a montré que 2000 tronque sur les évaluations longues.
      max_tokens: 4000,
      system: SYNTHESIS_SYSTEM,
      messages: [{ role: "user", content: userMsg }],
    }),
  });
  if (!r.ok) throw new Error("Synthesis error: " + (await r.text()).slice(0, 200));
  const data = await r.json();
  const text = data.content?.[0]?.text || "";
  return parseJsonOutput(text);
}

// ─── Handler ──────────────────────────────────────────────────────────────

export default async (req) => {
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  let body;
  try { body = await req.json(); }
  catch {
    console.error("[hugo-bg] Invalid JSON body");
    return new Response("Invalid JSON", { status: 400 });
  }

  const { jobId, dossierId, skipNorvexFinal, forceEmail } = body;
  if (!jobId || !dossierId) {
    console.error("[hugo-bg] Missing jobId or dossierId");
    return new Response("Missing fields", { status: 400 });
  }

  const secret = process.env.INTERNAL_SECRET;
  const anthropicKey = process.env.ANTHROPIC_API_KEY;
  if (!secret || !anthropicKey) {
    console.error("[hugo-bg] Missing env vars (INTERNAL_SECRET or ANTHROPIC_API_KEY)");
    return new Response("Server config error", { status: 500 });
  }

  const { getServiceAccount } = await import("./_firebase-sa.mjs");
  let sa;
  try { sa = await getServiceAccount(); }
  catch (e) {
    console.error("[hugo-bg] SA load failed:", e.message);
    return new Response("Invalid SA: " + e.message, { status: 500 });
  }

  console.log(`[hugo-bg] Job ${jobId} starting for dossier ${dossierId}`);
  await updateJobStatus(jobId, sa, {
    status: "running",
    dossierId,
    startedAt: new Date().toISOString(),
  });

  try {
    // 1. Charger dossier
    const fsToken = await getFirestoreToken(sa);
    const dossier = await fsGet(sa.project_id, fsToken, `dossiers/${dossierId}`);
    if (!dossier) throw new Error("Dossier not found");
    dossier.id = dossierId;

    // Anti-spam email : capture pre-run state AVANT overwrite à l'étape 9.
    // Si Hugo a déjà tourné avec succès sur ce dossier, on n'envoie PAS
    // d'email à Yves sauf si forceEmail=true. Évite re-runs auto/manuels
    // de spammer la boîte avec le même verdict.
    const wasPreviouslyAnalyzed = Boolean(dossier.hugoLastReportId);

    const pdfBlobs = Array.isArray(dossier.pdfBlobs) ? dossier.pdfBlobs : [];
    console.log(`[hugo-bg] ${pdfBlobs.length} pdfBlobs in dossier`);

    // 2. Expansion blobs → blocs Anthropic
    //    Passe SA + bucket pour régénérer signed URLs just-in-time (anti-expiration 7j)
    const store = getStore({ name: "analysis-results", consistency: "strong" });
    const storageBucket = process.env.FIREBASE_STORAGE_BUCKET || `${sa.project_id}.appspot.com`;
    const { content: pdfBlocks, errors: blobErrors } = await expandBlobsToContent(
      pdfBlobs, store, sa, storageBucket
    );
    console.log(`[hugo-bg] ${pdfBlocks.length} PDFs prêts pour Anthropic`);
    if (blobErrors.length) console.warn(`[hugo-bg] blob errors:`, blobErrors);

    // 3. Évaluation Intel V3 INLINE (multimodal Sonnet 4.6)
    let intelReport = null;
    if (pdfBlocks.length === 0) {
      intelReport = {
        hasDocuments: false,
        message: "No PDFs to analyze (pdfBlobs empty or all errored)",
        blob_errors: blobErrors,
      };
    } else {
      const intelBlocks = [
        ...pdfBlocks,
        { type: "text", text: buildIntelPrompt(dossier, pdfBlocks.length) },
      ];
      console.log(`[hugo-bg] Intel: calling Anthropic Sonnet 4.6 with ${pdfBlocks.length} PDFs`);
      const intelResp = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "x-api-key": anthropicKey,
          "anthropic-version": "2023-06-01",
          "anthropic-beta": "pdfs-2024-09-25",
          "content-type": "application/json",
        },
        body: JSON.stringify({
          model: "claude-sonnet-4-6",
          // 5000 tokens : marge pour JSON complet sur évaluations détaillées
          // (extraction + 3 approches + réconciliation + stress tests + verdict).
          // L'expérience Henri Petit a montré que 3000 tronque le JSON.
          max_tokens: 5000,
          messages: [{ role: "user", content: intelBlocks }],
        }),
      });
      if (!intelResp.ok) {
        const err = await intelResp.text();
        intelReport = { error: "Intel Anthropic error: " + err.slice(0, 300), module: "intel" };
        console.error(`[hugo-bg] Intel API error:`, err.slice(0, 300));
      } else {
        const intelData = await intelResp.json();
        const rawText = intelData.content?.[0]?.text || "";
        try {
          const evaluation = parseJsonOutput(rawText);
          intelReport = {
            dossierId,
            mode: "from_docs",
            documents_analyzed: pdfBlocks.length,
            blob_errors: blobErrors,
            evaluation,
            analyzed_at: new Date().toISOString(),
            model: "claude-sonnet-4-6",
          };
          console.log(`[hugo-bg] Intel done. Verdict: ${evaluation.verdict?.recommandation || "n/a"}`);
        } catch (e) {
          intelReport = {
            error: "Intel JSON parse failed: " + e.message,
            raw_preview: rawText.slice(0, 500),
          };
        }
      }
    }

    // 4. Track + Cost en parallèle (mode multimodal si docs disponibles)
    //    On passe les storagePaths Firebase (les endpoints téléchargent eux-mêmes,
    //    bypass body cap inter-functions). Limit 8 docs / module.
    const trackCostDocs = pdfBlobs
      .filter((b) => b.type === "firebase_url" && b.path)
      .slice(0, 8)
      .map((b) => ({
        name: b.name || "document.pdf",
        mediaType: "application/pdf",
        storagePath: b.path,
      }));
    console.log(`[hugo-bg] Calling Track + Cost (${trackCostDocs.length} docs each)...`);
    const trackBody = trackCostDocs.length > 0
      ? { dossierId, documents: trackCostDocs }
      : { dossierId };
    const costBody = trackCostDocs.length > 0
      ? { dossierId, documents: trackCostDocs }
      : { dossierId };
    const [trackReport, costReport] = await Promise.all([
      callEndpoint("track", "/api/track-analyze-dossier", trackBody, secret, 90000),
      callEndpoint("cost", "/api/cost-analyze-dossier", costBody, secret, 90000),
    ]);

    const reports = { intel: intelReport, track: trackReport, cost: costReport };
    console.log(`[hugo-bg] Modules done. Intel: ${intelReport?.error ? "error" : "ok"}, Track: ${trackReport?.error ? "error" : "ok"}, Cost: ${costReport?.error ? "error" : "ok"}`);

    // 5. Synthèse Opus 4.6
    console.log(`[hugo-bg] Synthesizing...`);
    let synthesis;
    try {
      synthesis = await synthesize(dossierId, reports, anthropicKey);
    } catch (e) {
      throw new Error("Synthesis failed: " + e.message);
    }
    console.log(`[hugo-bg] Synthesis verdict: ${synthesis.verdict_global}`);

    // 6. Push Brain
    console.log(`[hugo-bg] Pushing to Brain...`);
    const brainResult = await callEndpoint(
      "brain_push",
      "/api/brain-push-from-hugo",
      {
        dossierId,
        agent: "hugo_norvex_chantier_bg",
        verdictGlobal: synthesis.verdict_global,
        actionRecommandee: synthesis.action_recommandee,
        synthesis: synthesis.synthesis,
        modulesSummary: synthesis.modules_summary || {},
        alertesConsolidees: synthesis.alertes_consolidees || [],
        deboursementAutorise: synthesis.deboursement_autorise ?? null,
        valeurPreteeRecommandee: synthesis.valeur_pretee_recommandee ?? null,
        confianceGlobale: synthesis.confiance_globale,
        rawReports: {
          intel_status: intelReport?.error ? "error" : (intelReport?.evaluation ? "ok" : "skipped"),
          track_status: trackReport?.error ? "error" : "ok",
          cost_status: costReport?.error ? "error" : "ok",
        },
        createdAt: new Date().toISOString(),
      },
      secret,
      30000
    );

    // 7. Norvex Final (sauf si Critique ou skipped)
    let norvexFinalResult = null;
    const hugoCritique = synthesis.verdict_global === "Critique";
    if (!skipNorvexFinal && !hugoCritique) {
      console.log(`[hugo-bg] Triggering Norvex Final...`);
      norvexFinalResult = await callEndpoint(
        "norvex_final",
        "/api/norvex-final-analyze",
        { dossierId, sendEmail: true },
        secret,
        60000
      );
    }

    // 8. Update job status DONE
    await updateJobStatus(jobId, sa, {
      status: "done",
      dossierId,
      completedAt: new Date().toISOString(),
      verdictGlobal: synthesis.verdict_global,
      actionRecommandee: synthesis.action_recommandee,
      synthesisText: synthesis.synthesis,
      reportId: brainResult?.reportId || null,
      intelMode:
        intelReport?.evaluation
          ? "multimodal"
          : intelReport?.error
          ? "error"
          : "skipped",
      intelError: intelReport?.error || null,
      pdfCount: pdfBlocks.length,
      blobErrors: JSON.stringify(blobErrors).slice(0, 1000),
      norvexFinalStatus: norvexFinalResult
        ? (norvexFinalResult.error ? "error" : "ok")
        : (hugoCritique ? "skipped_hugo_critique" : "skipped_by_request"),
      norvexFinalRate: norvexFinalResult?.finalRate ?? null,
      norvexFinalAmount: norvexFinalResult?.finalAmount ?? null,
      norvexFinalDecision: norvexFinalResult?.finalDecision || null,
    });

    // 9. Mettre à jour dossier (compat watcher)
    try {
      await fsPatch(sa.project_id, fsToken, `dossiers/${dossierId}`, {
        hugoLastAnalyzedAt: new Date().toISOString(),
        hugoLastVerdict: synthesis.verdict_global,
        hugoLastReportId: brainResult?.reportId || null,
        hugoLastAction: synthesis.action_recommandee,
        hugoLastJobId: jobId,
      });
    } catch (e) {
      console.error(`[hugo-bg] dossier update failed (non-fatal):`, e.message);
    }

    // 10. Email Yves (notification légère que Hugo est terminé)
    //     Anti-duplication #1 : si Norvex Final a envoyé son brief détaillé,
    //                            on saute pour éviter 2 emails coup sur coup.
    //     Anti-spam #2 (2026-05-13) : si Hugo a déjà tourné sur ce dossier,
    //                                  on saute SAUF si forceEmail=true.
    //                                  → Une seule notif par dossier par défaut.
    const nfEmailSent = norvexFinalResult?.emailSent === true;
    const skipEmailReanalysis = wasPreviouslyAnalyzed && forceEmail !== true;
    if (!nfEmailSent && !skipEmailReanalysis) {
      try {
        const subject = `Hugo — ${synthesis.verdict_global || "?"} — ${dossierId}`;
        const html = buildHugoCompletionEmail({
          dossierId,
          jobId,
          verdictGlobal: synthesis.verdict_global,
          actionRecommandee: synthesis.action_recommandee,
          synthesisText: synthesis.synthesis,
          reportId: brainResult?.reportId || null,
          pdfCount: pdfBlocks.length,
          intelMode:
            intelReport?.evaluation ? "multimodal"
            : intelReport?.error ? "error"
            : "skipped",
          intelError: intelReport?.error || null,
          norvexFinalStatus: norvexFinalResult
            ? (norvexFinalResult.error ? "error" : "ok")
            : (hugoCritique ? "skipped_hugo_critique" : "skipped_by_request"),
          norvexFinalRate: norvexFinalResult?.finalRate ?? null,
          norvexFinalAmount: norvexFinalResult?.finalAmount ?? null,
          norvexFinalDecision: norvexFinalResult?.finalDecision || null,
        });
        const mailResult = await sendHugoEmail("yves@capitalnorvex.com", subject, html);
        if (!mailResult.ok) {
          console.error(`[hugo-bg] email send failed (non-fatal):`, mailResult.error);
        } else {
          console.log(`[hugo-bg] email sent to yves@ (messageId=${mailResult.messageId})`);
        }
      } catch (e) {
        console.error(`[hugo-bg] email build/send threw (non-fatal):`, e.message);
      }
    } else if (skipEmailReanalysis) {
      console.log(`[hugo-bg] email skipped (re-analyse, dossier déjà analysé une fois, forceEmail=false)`);
    } else {
      console.log(`[hugo-bg] email skipped (Norvex Final already emailed)`);
    }

    console.log(`[hugo-bg] Job ${jobId} DONE in dossier ${dossierId}`);
    return new Response(JSON.stringify({ ok: true, jobId }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    console.error(`[hugo-bg] Job ${jobId} FAILED:`, err.message);
    await updateJobStatus(jobId, sa, {
      status: "error",
      dossierId,
      completedAt: new Date().toISOString(),
      error: err.message?.slice(0, 1000) || "unknown",
    });

    // Email Yves pour erreur (anti-silence)
    try {
      const errHtml = `<!DOCTYPE html>
<html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.5; color: #1a1a1a; max-width: 640px; margin: 0 auto; padding: 24px;">
  <div style="border-top: 4px solid #c33; padding-top: 16px;">
    <div style="font-size: 11px; letter-spacing: 2px; color: #777; text-transform: uppercase;">Hugo — Norvex Chantier™</div>
    <h1 style="font-family: 'Playfair Display', Georgia, serif; font-size: 22px; margin: 8px 0 4px 0; color: #c33;">Analyse ÉCHOUÉE</h1>
    <div style="font-size: 13px; color: #777;">Dossier <code>${escHtml(dossierId)}</code> · Job <code>${escHtml(jobId)}</code></div>
  </div>
  <div style="background: #fdf0f0; border-left: 5px solid #c33; padding: 16px 20px; margin: 20px 0; border-radius: 4px;">
    <div style="font-size: 11px; letter-spacing: 2px; color: #777; text-transform: uppercase;">Erreur</div>
    <pre style="font-size: 13px; white-space: pre-wrap; margin: 8px 0 0 0; color: #8c1f1f;">${escHtml((err.message || "unknown").slice(0, 800))}</pre>
  </div>
  <div style="margin-top: 24px;">
    <a href="${SITE_URL}/hugo-admin.html" style="display: inline-block; background: #0a0a0a; color: #C9A227; padding: 10px 22px; border-radius: 6px; text-decoration: none; font-weight: 700;">
      Ouvrir Hugo Dashboard →
    </a>
  </div>
  <div style="font-size: 11px; color: #aaa; margin-top: 32px; font-family: ui-monospace, monospace;">
    Capital Norvex Inc. · Hugo background error · Job ${escHtml(jobId)}
  </div>
</body></html>`;
      await sendHugoEmail(
        "yves@capitalnorvex.com",
        `Hugo ÉCHEC — ${dossierId}`,
        errHtml
      );
    } catch (e) {
      console.error(`[hugo-bg] error email send failed (non-fatal):`, e.message);
    }

    return new Response(JSON.stringify({ ok: false, error: err.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
};

// Netlify détecte le mode background via le suffixe `-background` dans
// le nom de fichier. Path par défaut :
//   /.netlify/functions/hugo-orchestrator-background
