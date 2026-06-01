/**
 * POST /.netlify/functions/norvex-final-analyze
 * Header: x-internal-secret
 * Body: {
 *   dossierId,
 *   sendEmail?: bool = true,        // envoie le Brief HTML à yves@
 *   forceRecalc?: bool = false      // refait même si finalRate déjà calculé
 * }
 *
 * Norvex Final™ — Score Norvex FINAL post-Hugo.
 * 2026-05-05 soir.
 *
 * Workflow :
 *   1. Charge dossier Firestore (score initial, type, montant, addr…)
 *   2. Charge dernier rapport Hugo (collection hugoReports)
 *   3. Claude Opus 4.6 — analyse Comité Crédit institutionnel niveau grande banque
 *   4. PATCH dossier : finalScore, finalRate, finalAmount, finalDecision, finalConditions
 *   5. Crée doc norvexFinalReports + audit log + brainAlert si NO_GO
 *   6. Génère Brief HTML premium (palette Norvex) + envoie à yves@ via SendGrid
 *
 * Output : { ok, reportId, finalScore, finalRate, finalAmount, finalDecision,
 *            emailSent, briefHtml }
 *
 * NE TOUCHE PAS au Score Norvex initial (porte d'entrée client) ni aux
 * lettres V8/V9 verrouillées. Écrit uniquement les champs `final*` du dossier.
 */

// ─── Helpers HTTP ──────────────────────────────────────────────────────────

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// ─── Firestore auth + helpers ──────────────────────────────────────────────

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

function toFsValue(v) {
  if (v === null || v === undefined) return { nullValue: null };
  if (typeof v === "boolean") return { booleanValue: v };
  if (typeof v === "number") {
    return Number.isInteger(v) ? { integerValue: String(v) } : { doubleValue: v };
  }
  if (typeof v === "string") return { stringValue: v };
  if (v instanceof Date) return { timestampValue: v.toISOString() };
  if (Array.isArray(v)) return { arrayValue: { values: v.map(toFsValue) } };
  if (typeof v === "object") {
    const fields = {};
    for (const [k, val] of Object.entries(v)) fields[k] = toFsValue(val);
    return { mapValue: { fields } };
  }
  return { stringValue: String(v) };
}

async function getFsDoc(projectId, token, path) {
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

// PATCH avec updateMask — clé : ne touche QUE les champs spécifiés
async function patchFsDoc(projectId, token, path, updates) {
  const fieldNames = Object.keys(updates);
  const params = fieldNames.map((f) => `updateMask.fieldPaths=${encodeURIComponent(f)}`).join("&");
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${path}?${params}`;
  const fields = {};
  for (const [k, v] of Object.entries(updates)) fields[k] = toFsValue(v);
  const r = await fetch(url, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });
  if (!r.ok) {
    const err = await r.text();
    throw new Error(`Firestore PATCH ${path} failed: ${r.status} ${err.slice(0, 200)}`);
  }
}

async function createDoc(projectId, fsToken, collection, docId, data) {
  const docPath = docId
    ? `${collection}?documentId=${encodeURIComponent(docId)}`
    : collection;
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${docPath}`;
  const fields = {};
  for (const [k, v] of Object.entries(data)) fields[k] = toFsValue(v);
  const r = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${fsToken}`, "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });
  if (!r.ok) {
    const err = await r.text();
    throw new Error(`Firestore POST ${collection} failed: ${r.status} ${err.slice(0, 200)}`);
  }
  const responseData = await r.json();
  return (responseData.name || "").split("/").pop();
}

// Query : derniers rapports Hugo pour ce dossier
async function getLatestHugoReport(projectId, token, dossierId) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;
  const body = {
    structuredQuery: {
      from: [{ collectionId: "hugoReports" }],
      where: {
        fieldFilter: {
          field: { fieldPath: "dossierId" },
          op: "EQUAL",
          value: { stringValue: dossierId },
        },
      },
      orderBy: [
        { field: { fieldPath: "ingestedAt" }, direction: "DESCENDING" },
      ],
      limit: 1,
    },
  };
  const r = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) return null;
  const data = await r.json();
  if (!Array.isArray(data) || data.length === 0 || !data[0].document) return null;
  const out = {};
  for (const [k, v] of Object.entries(data[0].document.fields || {})) {
    out[k] = fromFsValue(v);
  }
  return out;
}

// ─── Prompt Comité Crédit institutionnel ──────────────────────────────────

function buildPrompt(dossier, hugoReport) {
  return `Tu es Directeur Crédit Senior chez Capital Norvex Inc. (prêt privé institutionnel alternatif au Québec et Ontario, tickets 2,5-100 M$, taux 10-12 %). Tu produis un MEMO COMITÉ CRÉDIT de qualité grande banque (BMO/RBC/BNC/Desjardins) ADAPTÉ à la réalité prêt privé alternatif.

Ce memo est le BRIEF PRÉ-RDV TEAMS d'Yves Barrette (président). Il doit lui donner :
- La note finale et le verdict
- Le taux RECOMMANDÉ à proposer (range 10-12 %)
- Le montant FINAL recommandé
- Les conditions précises à exiger
- Les talking points pour la conversation Teams

═══════════════════════════════════════════════════════════════════
DOSSIER (Score initial)
═══════════════════════════════════════════════════════════════════
${JSON.stringify({
  id: dossier.id,
  borrowerName: dossier.borrowerName || dossier.name,
  loanType: dossier.loanType,
  projectAddress: dossier.projectAddress,
  assetType: dossier.assetType,
  phase: dossier.phase || dossier.status,
  scoreInitial: dossier.score,
  loanAmountRequested: dossier.loanAmount || dossier.montantApprouve || dossier.amountRequested,
  notesScoreInitial: dossier.scoreNotes || dossier.scoreSummary || null,
}, null, 2)}

═══════════════════════════════════════════════════════════════════
HUGO NORVEX CHANTIER™ (Intel + Track + Cost)
═══════════════════════════════════════════════════════════════════
${hugoReport ? JSON.stringify({
  verdictGlobal: hugoReport.verdictGlobal,
  actionRecommandee: hugoReport.actionRecommandee,
  synthesis: hugoReport.synthesis,
  modulesSummary: hugoReport.modulesSummary,
  alertesConsolidees: hugoReport.alertesConsolidees,
  deboursementAutorise: hugoReport.deboursementAutorise,
  valeurPreteeRecommandee: hugoReport.valeurPreteeRecommandee,
  confianceGlobale: hugoReport.confianceGlobale,
  rawReports: hugoReport.rawReports,
}, null, 2) : "AUCUN rapport Hugo disponible — analyse partielle (score initial + dossier seulement)."}

═══════════════════════════════════════════════════════════════════
TÂCHE
═══════════════════════════════════════════════════════════════════

Produis un MEMO COMITÉ CRÉDIT structuré (niveau grande banque, ton institutionnel, factuel, motivé). Adapte la rigueur au contexte prêt privé Norvex (ne pas exiger ce qui n'est pas pertinent — ex. Norvex n'exige pas systématiquement DSCR 1,30 si protection capital vient de l'équité du promoteur).

CRITÈRES D'ÉVALUATION PRÊT PRIVÉ NORVEX :
- Note finale 0-100 (combine score initial pondéré + Hugo + qualité documentaire)
- Taux 10-12 % range étroit selon risque (10-10,75 % faible / 10,75-11,5 % modéré / 11,5-12 % élevé)
- ⚠️ LTV PORTE D'ENTRÉE : MINIMUM 75 %, standard 75-80 %. Capital Norvex est COMPÉTITIF — un client qui obtient 75-80 % ailleurs ne fera JAMAIS affaire avec nous à 65 %. La porte d'entrée doit être attractive. NE PAS recommander en bas de 75 % sauf si dossier vraiment marginal (risque très élevé, équité <10 %).
- Cas par cas, LTV peut aller JUSQU'À 100 % avec collatéraux additionnels (cas exceptionnels). Tu peux recommander librement entre 75 % et 100 % selon solidité du dossier.
  - Dossier solide → 80-85 %
  - Dossier exceptionnel (équité forte, sortie ferme, projet premium) → 90-100 % avec garanties
  - Dossier marginal → 75 % minimum (porte d'entrée)
- IMPORTANT : NE PAS détailler automatiquement quels collatéraux/garanties additionnelles. Si LTV >85 %, indique simplement dans \`finalConditions\` : « Garanties additionnelles à valider avec Yves au RDV Teams » sans détailler. La vérification collatéraux (soldes, valeurs marchandes, 2es hypothèques) est gérée MANUELLEMENT par Yves au RDV Teams.
- Équité promoteur : ≥ 15 % du coût total (résiduelle après stress)
- Holdback construction : 5 % minimum, 10 % préférable
- Protection capital first-mortgage privilégiée
- Sortie viable < 18 mois (refi traditionnel ou vente)

DÉCISION :
- "GO" : tous critères verts, taux dans bas du range
- "GO_CONDITIONNEL" : critères acceptables avec conditions explicites (holdback majoré, garanties additionnelles, appel à équité, MRC en cas de retard…)
- "NO_GO" : red flags structurels (équité < 20 %, valeur Intel critique, pattern de bypass, dossier criminel)

POSTURE NÉGOCIATION :
- "favorable" : on a la main, on peut tenir le taux haut, on n'a pas besoin du dossier
- "neutre" : juste pricing, conditions standards
- "serrée" : Yves doit tester sa réaction sur 2-3 points avant d'engager

═══════════════════════════════════════════════════════════════════
FORMAT DE SORTIE — JSON STRICT (aucun texte avant/après, aucun \`\`\`)
═══════════════════════════════════════════════════════════════════

{
  "finalScore": <0-100>,
  "finalScoreJustification": "<court 2-3 phrases motivant la note>",
  "finalDecision": "GO | GO_CONDITIONNEL | NO_GO",
  "finalDecisionJustification": "<court 1-2 phrases>",
  "finalRate": <nombre, ex 11.25>,
  "finalRateRange": { "low": <nombre>, "high": <nombre> },
  "finalRateJustification": "<court : pourquoi ce taux dans le range Norvex>",
  "finalAmount": <nombre>,
  "finalAmountJustification": "<court : pourquoi ce montant vs demande initiale>",
  "loanTermMonths": <nombre, ex 12>,
  "ltvCalcule": <nombre|null>,
  "ltcCalcule": <nombre|null>,
  "negotiationPosture": "favorable | neutre | serrée",
  "executiveSummary": "<paragraphe 5-7 phrases — ton institutionnel, factuel, dense>",
  "borrowerProfile": "<2-3 phrases sur le promoteur>",
  "projectAnalysis": "<3-4 phrases sur le projet>",
  "financialAnalysis": "<3-5 phrases — équité, LTV, LTC, sortie>",
  "riskAssessment": {
    "strengths": ["<point fort 1>", "<point fort 2>", "<point fort 3>"],
    "concerns": ["<préoccupation 1>", "<préoccupation 2>"],
    "redFlags": ["<red flag 1 ou \\"aucun\\">"]
  },
  "stressTestSummary": "<1-2 phrases sur résilience scénarios défavorables>",
  "finalConditions": [
    "<condition 1 précise et actionnable>",
    "<condition 2>",
    "<condition 3>"
  ],
  "rdvTalkingPoints": [
    { "topic": "<sujet 1>", "objective": "<ce qu'Yves doit tester/valider>", "fallback": "<position de repli si client résiste>" },
    { "topic": "<sujet 2>", "objective": "<...>", "fallback": "<...>" },
    { "topic": "<sujet 3>", "objective": "<...>", "fallback": "<...>" }
  ],
  "documentsManquants": ["<doc 1 à exiger avant closing>", "<doc 2>"],
  "memorandumComite": "<paragraphe final — recommandation formelle au Comité Crédit, ton institutionnel, 4-6 phrases, ce qu'on présenterait en séance Comité>"
}`;
}

function parseJsonOutput(raw) {
  let s = raw.trim();
  s = s.replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/\s*```$/i, "");
  const match = s.match(/\{[\s\S]*\}/);
  if (match) s = match[0];
  return JSON.parse(s);
}

// ─── Brief HTML premium (palette Norvex) ──────────────────────────────────

const COLOR_CREAM = "#FBF7EB";
const COLOR_INK = "#0A0A0A";
const COLOR_GOLD = "#C8B070";
const COLOR_GOLD_DARK = "#9A8554";
const COLOR_GREEN = "#2E7D5C";
const COLOR_AMBER = "#C8923A";
const COLOR_RED = "#A53A2C";

function fmtMoney(n) {
  if (n === null || n === undefined || isNaN(n)) return "—";
  return Math.round(n).toLocaleString("fr-CA") + " $";
}

function fmtPct(n) {
  if (n === null || n === undefined || isNaN(n)) return "—";
  return Number(n).toFixed(2).replace(".", ",") + " %";
}

function decisionStyle(decision) {
  if (decision === "GO") return { color: COLOR_GREEN, label: "GO" };
  if (decision === "GO_CONDITIONNEL") return { color: COLOR_AMBER, label: "GO CONDITIONNEL" };
  if (decision === "NO_GO") return { color: COLOR_RED, label: "NO-GO" };
  return { color: COLOR_INK, label: decision || "—" };
}

function buildBriefHtml(dossier, analysis) {
  const decStyle = decisionStyle(analysis.finalDecision);
  const borrower = dossier.borrowerName || dossier.name || "—";
  const addr = dossier.projectAddress || "—";
  const loanType = dossier.loanType || "—";

  const strengths = (analysis.riskAssessment?.strengths || [])
    .map((s) => `<li style="margin:6px 0;color:#2a2a2a;line-height:1.55;">${s}</li>`)
    .join("");
  const concerns = (analysis.riskAssessment?.concerns || [])
    .map((s) => `<li style="margin:6px 0;color:#2a2a2a;line-height:1.55;">${s}</li>`)
    .join("");
  const redFlags = (analysis.riskAssessment?.redFlags || [])
    .filter((s) => s && s.toLowerCase() !== "aucun")
    .map((s) => `<li style="margin:6px 0;color:${COLOR_RED};font-weight:600;line-height:1.55;">${s}</li>`)
    .join("");
  const conditions = (analysis.finalConditions || [])
    .map((c, i) => `<tr><td style="padding:8px 12px;border-bottom:1px solid #E8E0CC;color:${COLOR_GOLD_DARK};font-weight:700;width:36px;">${i + 1}.</td><td style="padding:8px 12px;border-bottom:1px solid #E8E0CC;color:#2a2a2a;line-height:1.6;">${c}</td></tr>`)
    .join("");
  const talkingPoints = (analysis.rdvTalkingPoints || [])
    .map(
      (tp) => `
        <div style="margin:14px 0;padding:14px 18px;background:#FAF6EA;border-left:3px solid ${COLOR_GOLD};">
          <div style="font-family:Georgia,serif;font-size:14px;color:${COLOR_INK};font-weight:700;margin-bottom:6px;">${tp.topic || ""}</div>
          <div style="font-size:13px;color:#3a3a3a;line-height:1.6;margin-bottom:4px;"><span style="color:${COLOR_GOLD_DARK};font-weight:600;">Objectif RDV :</span> ${tp.objective || ""}</div>
          <div style="font-size:13px;color:#5a5a5a;line-height:1.6;font-style:italic;"><span style="font-style:normal;font-weight:600;">Position de repli :</span> ${tp.fallback || ""}</div>
        </div>
      `
    )
    .join("");
  const docsManq = (analysis.documentsManquants || [])
    .map((d) => `<li style="margin:4px 0;color:#2a2a2a;">${d}</li>`)
    .join("");

  const postureColor =
    analysis.negotiationPosture === "favorable"
      ? COLOR_GREEN
      : analysis.negotiationPosture === "serrée"
      ? COLOR_RED
      : COLOR_AMBER;

  return `<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Norvex Final — Brief Pré-RDV</title>
</head>
<body style="margin:0;padding:0;background:${COLOR_CREAM};font-family:Georgia,'Times New Roman',serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:${COLOR_CREAM};padding:30px 0;">
  <tr><td align="center">
    <table role="presentation" width="720" cellpadding="0" cellspacing="0" style="max-width:720px;width:100%;background:#fff;border:1px solid #E8E0CC;">

      <!-- HEADER bandeau noir + or -->
      <tr><td style="background:${COLOR_INK};padding:24px 36px;border-bottom:3px solid ${COLOR_GOLD};">
        <div style="font-family:Georgia,serif;font-size:11px;letter-spacing:4px;color:${COLOR_GOLD};text-transform:uppercase;">Capital Norvex · Comité Crédit</div>
        <div style="font-family:Georgia,serif;font-size:24px;color:#fff;letter-spacing:2px;margin-top:6px;">NORVEX FINAL™</div>
        <div style="font-family:Georgia,serif;font-size:13px;color:#bdbdbd;margin-top:10px;font-style:italic;">Brief pré-RDV Teams · Document interne confidentiel</div>
      </td></tr>

      <!-- IDENTIFICATION DOSSIER -->
      <tr><td style="padding:28px 36px 8px;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="font-size:10px;letter-spacing:3px;color:${COLOR_GOLD_DARK};text-transform:uppercase;font-family:Georgia,serif;padding-bottom:4px;">Dossier</td>
            <td style="font-size:10px;letter-spacing:3px;color:${COLOR_GOLD_DARK};text-transform:uppercase;font-family:Georgia,serif;padding-bottom:4px;">Type de prêt</td>
          </tr>
          <tr>
            <td style="font-family:Georgia,serif;font-size:16px;color:${COLOR_INK};font-weight:700;padding-bottom:14px;">${dossier.id || "—"}</td>
            <td style="font-family:Georgia,serif;font-size:16px;color:${COLOR_INK};padding-bottom:14px;">${loanType}</td>
          </tr>
          <tr>
            <td colspan="2" style="font-size:10px;letter-spacing:3px;color:${COLOR_GOLD_DARK};text-transform:uppercase;font-family:Georgia,serif;padding-bottom:4px;">Emprunteur · Adresse projet</td>
          </tr>
          <tr>
            <td colspan="2" style="font-family:Georgia,serif;font-size:15px;color:${COLOR_INK};padding-bottom:6px;">${borrower}</td>
          </tr>
          <tr>
            <td colspan="2" style="font-family:Georgia,serif;font-size:14px;color:#3a3a3a;padding-bottom:18px;">${addr}</td>
          </tr>
        </table>
      </td></tr>

      <!-- VERDICT BLOC PRINCIPAL -->
      <tr><td style="padding:8px 36px 8px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:${COLOR_INK};border:1px solid ${COLOR_GOLD};">
          <tr>
            <td style="padding:24px 28px;border-right:1px solid ${COLOR_GOLD_DARK};">
              <div style="font-size:10px;letter-spacing:3px;color:${COLOR_GOLD};text-transform:uppercase;font-family:Georgia,serif;">Note finale</div>
              <div style="font-family:Georgia,serif;font-size:42px;color:#fff;font-weight:700;line-height:1;margin-top:6px;">${
                analysis.finalScore != null ? analysis.finalScore : "—"
              }<span style="font-size:18px;color:${COLOR_GOLD};font-weight:400;"> / 100</span></div>
            </td>
            <td style="padding:24px 28px;text-align:center;">
              <div style="font-size:10px;letter-spacing:3px;color:${COLOR_GOLD};text-transform:uppercase;font-family:Georgia,serif;">Décision</div>
              <div style="font-family:Georgia,serif;font-size:24px;color:${decStyle.color};font-weight:700;letter-spacing:2px;margin-top:8px;">${decStyle.label}</div>
            </td>
          </tr>
        </table>
      </td></tr>

      <!-- PRICING -->
      <tr><td style="padding:18px 36px 8px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #E8E0CC;">
          <tr>
            <td style="padding:18px 22px;border-right:1px solid #E8E0CC;width:33%;text-align:center;">
              <div style="font-size:10px;letter-spacing:3px;color:${COLOR_GOLD_DARK};text-transform:uppercase;font-family:Georgia,serif;">Taux recommandé</div>
              <div style="font-family:Georgia,serif;font-size:28px;color:${COLOR_INK};font-weight:700;margin-top:6px;">${fmtPct(analysis.finalRate)}</div>
              <div style="font-size:11px;color:#888;margin-top:3px;">Range ${fmtPct(analysis.finalRateRange?.low)} – ${fmtPct(analysis.finalRateRange?.high)}</div>
            </td>
            <td style="padding:18px 22px;border-right:1px solid #E8E0CC;width:33%;text-align:center;">
              <div style="font-size:10px;letter-spacing:3px;color:${COLOR_GOLD_DARK};text-transform:uppercase;font-family:Georgia,serif;">Montant</div>
              <div style="font-family:Georgia,serif;font-size:22px;color:${COLOR_INK};font-weight:700;margin-top:6px;">${fmtMoney(analysis.finalAmount)}</div>
              <div style="font-size:11px;color:#888;margin-top:3px;">Terme ${analysis.loanTermMonths || "—"} mois</div>
            </td>
            <td style="padding:18px 22px;width:34%;text-align:center;">
              <div style="font-size:10px;letter-spacing:3px;color:${COLOR_GOLD_DARK};text-transform:uppercase;font-family:Georgia,serif;">Posture négo</div>
              <div style="font-family:Georgia,serif;font-size:18px;color:${postureColor};font-weight:700;margin-top:8px;text-transform:uppercase;letter-spacing:1px;">${analysis.negotiationPosture || "—"}</div>
              <div style="font-size:11px;color:#888;margin-top:3px;">LTV ${analysis.ltvCalcule != null ? Number(analysis.ltvCalcule).toFixed(1) + " %" : "—"} · LTC ${analysis.ltcCalcule != null ? Number(analysis.ltcCalcule).toFixed(1) + " %" : "—"}</div>
            </td>
          </tr>
        </table>
      </td></tr>

      <!-- EXECUTIVE SUMMARY -->
      <tr><td style="padding:24px 36px 8px;">
        <div style="display:inline-block;height:2px;width:40px;background:${COLOR_GOLD};margin-bottom:8px;"></div>
        <div style="font-family:Georgia,serif;font-size:10px;letter-spacing:3px;color:${COLOR_GOLD_DARK};text-transform:uppercase;margin-bottom:10px;">Sommaire exécutif</div>
        <p style="font-family:Georgia,serif;font-size:14px;color:#2a2a2a;line-height:1.7;margin:0 0 12px;">${analysis.executiveSummary || ""}</p>
      </td></tr>

      <!-- ANALYSE -->
      <tr><td style="padding:8px 36px 8px;">
        <div style="margin:14px 0 0;">
          <div style="font-family:Georgia,serif;font-size:13px;color:${COLOR_INK};font-weight:700;margin-bottom:4px;">Profil emprunteur</div>
          <p style="font-family:Georgia,serif;font-size:13px;color:#3a3a3a;line-height:1.65;margin:0 0 12px;">${analysis.borrowerProfile || ""}</p>

          <div style="font-family:Georgia,serif;font-size:13px;color:${COLOR_INK};font-weight:700;margin-bottom:4px;">Projet</div>
          <p style="font-family:Georgia,serif;font-size:13px;color:#3a3a3a;line-height:1.65;margin:0 0 12px;">${analysis.projectAnalysis || ""}</p>

          <div style="font-family:Georgia,serif;font-size:13px;color:${COLOR_INK};font-weight:700;margin-bottom:4px;">Analyse financière</div>
          <p style="font-family:Georgia,serif;font-size:13px;color:#3a3a3a;line-height:1.65;margin:0 0 12px;">${analysis.financialAnalysis || ""}</p>

          <div style="font-family:Georgia,serif;font-size:13px;color:${COLOR_INK};font-weight:700;margin-bottom:4px;">Stress tests</div>
          <p style="font-family:Georgia,serif;font-size:13px;color:#3a3a3a;line-height:1.65;margin:0;">${analysis.stressTestSummary || ""}</p>
        </div>
      </td></tr>

      <!-- FORCES / PRÉOCCUPATIONS / RED FLAGS -->
      <tr><td style="padding:24px 36px 8px;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr><td style="vertical-align:top;width:50%;padding-right:14px;">
            <div style="font-family:Georgia,serif;font-size:10px;letter-spacing:3px;color:${COLOR_GREEN};text-transform:uppercase;margin-bottom:8px;">Forces</div>
            <ul style="margin:0;padding-left:20px;font-family:Georgia,serif;font-size:13px;">${strengths || "<li style=\"color:#888;\">—</li>"}</ul>
          </td><td style="vertical-align:top;width:50%;padding-left:14px;">
            <div style="font-family:Georgia,serif;font-size:10px;letter-spacing:3px;color:${COLOR_AMBER};text-transform:uppercase;margin-bottom:8px;">Préoccupations</div>
            <ul style="margin:0;padding-left:20px;font-family:Georgia,serif;font-size:13px;">${concerns || "<li style=\"color:#888;\">—</li>"}</ul>
          </td></tr>
        </table>
        ${
          redFlags
            ? `<div style="margin-top:16px;padding:14px 18px;background:#FBEEE9;border-left:4px solid ${COLOR_RED};">
                <div style="font-family:Georgia,serif;font-size:10px;letter-spacing:3px;color:${COLOR_RED};text-transform:uppercase;margin-bottom:6px;">⚠ Red flags</div>
                <ul style="margin:0;padding-left:20px;font-family:Georgia,serif;font-size:13px;">${redFlags}</ul>
              </div>`
            : ""
        }
      </td></tr>

      <!-- CONDITIONS -->
      <tr><td style="padding:24px 36px 8px;">
        <div style="display:inline-block;height:2px;width:40px;background:${COLOR_GOLD};margin-bottom:8px;"></div>
        <div style="font-family:Georgia,serif;font-size:10px;letter-spacing:3px;color:${COLOR_GOLD_DARK};text-transform:uppercase;margin-bottom:10px;">Conditions à exiger</div>
        <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #E8E0CC;border-bottom:none;">${conditions || "<tr><td style=\"padding:12px;color:#888;\">Aucune condition spécifique</td></tr>"}</table>
      </td></tr>

      <!-- TALKING POINTS RDV -->
      <tr><td style="padding:24px 36px 8px;">
        <div style="display:inline-block;height:2px;width:40px;background:${COLOR_GOLD};margin-bottom:8px;"></div>
        <div style="font-family:Georgia,serif;font-size:10px;letter-spacing:3px;color:${COLOR_GOLD_DARK};text-transform:uppercase;margin-bottom:10px;">Talking points RDV Teams</div>
        ${talkingPoints || "<p style=\"color:#888;font-style:italic;\">Aucun talking point structuré.</p>"}
      </td></tr>

      ${
        docsManq
          ? `<tr><td style="padding:24px 36px 8px;">
              <div style="display:inline-block;height:2px;width:40px;background:${COLOR_GOLD};margin-bottom:8px;"></div>
              <div style="font-family:Georgia,serif;font-size:10px;letter-spacing:3px;color:${COLOR_GOLD_DARK};text-transform:uppercase;margin-bottom:10px;">Documents à exiger avant closing</div>
              <ul style="margin:0;padding-left:20px;font-family:Georgia,serif;font-size:13px;">${docsManq}</ul>
            </td></tr>`
          : ""
      }

      <!-- MEMO COMITÉ -->
      <tr><td style="padding:24px 36px 28px;">
        <div style="display:inline-block;height:2px;width:40px;background:${COLOR_GOLD};margin-bottom:8px;"></div>
        <div style="font-family:Georgia,serif;font-size:10px;letter-spacing:3px;color:${COLOR_GOLD_DARK};text-transform:uppercase;margin-bottom:10px;">Mémorandum au Comité de Crédit</div>
        <div style="background:#FAF6EA;border-left:3px solid ${COLOR_GOLD};padding:18px 22px;font-family:Georgia,serif;font-size:13.5px;color:#2a2a2a;line-height:1.75;font-style:italic;">${analysis.memorandumComite || ""}</div>
      </td></tr>

      <!-- FOOTER -->
      <tr><td style="background:${COLOR_INK};padding:18px 36px;border-top:2px solid ${COLOR_GOLD};">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="font-family:Georgia,serif;font-size:11px;color:${COLOR_GOLD};letter-spacing:2px;">CAPITAL NORVEX INC.</td>
            <td style="font-family:Georgia,serif;font-size:10px;color:#7a7a7a;text-align:right;font-style:italic;">Document interne · Comité de Crédit · Confidentiel</td>
          </tr>
          <tr>
            <td colspan="2" style="font-family:Georgia,serif;font-size:10px;color:#7a7a7a;padding-top:6px;">Norvex Final™ · Analyse propriétaire combinant Score Norvex initial + NORVEX CHANTIER™ (Intel·Track·Cost) + agent_docs · Validation Comité Crédit IA Opus 4.6</td>
          </tr>
        </table>
      </td></tr>

    </table>
  </td></tr>
</table>
</body></html>`;
}

// ─── SendGrid envoi ────────────────────────────────────────────────────────

async function sendBriefViaSendGrid(toEmail, subject, html) {
  const apiKey = process.env.SENDGRID_API_KEY;
  if (!apiKey) return { ok: false, error: "SENDGRID_API_KEY not set" };

  const payload = {
    personalizations: [{ to: [{ email: toEmail }] }],
    from: { email: "info@capitalnorvex.com", name: "Capital Norvex · Norvex Final" },
    subject,
    content: [{ type: "text/html", value: html }],
    reply_to: { email: "yves@capitalnorvex.com", name: "Yves Barrette" },
    headers: {
      "X-Capital-Norvex-Type": "norvex-final-brief",
      "X-Auto-Response-Suppress": "All",
    },
  };

  const resp = await fetch("https://api.sendgrid.com/v3/mail/send", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    const err = await resp.text();
    return { ok: false, error: `SendGrid ${resp.status}: ${err.slice(0, 200)}` };
  }
  return { ok: true, messageId: resp.headers.get("x-message-id") || null };
}

// ─── Handler ───────────────────────────────────────────────────────────────

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

  const { dossierId, sendEmail = true, forceRecalc = false } = body;
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
    const now = new Date();

    // 1. Charger dossier
    const dossier = await getFsDoc(projectId, token, `dossiers/${dossierId}`);
    if (!dossier) return json({ error: "Dossier introuvable" }, 404);
    dossier.id = dossierId;

    // Skip si déjà fait et pas forcé
    if (!forceRecalc && dossier.finalRate && dossier.norvexFinalReportId) {
      return json({
        ok: true,
        skipped: true,
        reason: "finalRate déjà calculé. Utiliser forceRecalc:true pour refaire.",
        finalRate: dossier.finalRate,
        finalAmount: dossier.finalAmount,
        finalDecision: dossier.finalDecision,
        norvexFinalReportId: dossier.norvexFinalReportId,
      });
    }

    // 2. Charger dernier rapport Hugo
    const hugoReport = await getLatestHugoReport(projectId, token, dossierId);

    // 3. Claude Opus 4.6 — analyse Comité Crédit
    const prompt = buildPrompt(dossier, hugoReport);
    const claudeResp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: "claude-opus-4-6",
        max_tokens: 4000,
        messages: [{ role: "user", content: prompt }],
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
        { error: "Parse JSON failed: " + e.message, raw: rawText.slice(0, 500) },
        500
      );
    }

    // Normalisation défendable (comité crédit / avocat / banque)
    // - finalScore ∈ [0, 100]
    // - finalRate ∈ [10, 12] (range Norvex stricte)
    // - finalRateRange.low/high dans le même range, low ≤ high
    // - finalAmount ≥ 0
    // - loanTermMonths > 0
    const _clamp = (v, lo, hi) => {
      const n = Number(v);
      if (!isFinite(n)) return null;
      return Math.max(lo, Math.min(n, hi));
    };
    if (analysis.finalScore != null) {
      const _s = _clamp(analysis.finalScore, 0, 100);
      analysis.finalScore = _s == null ? null : Math.round(_s);
    }
    if (analysis.finalRate != null) {
      analysis.finalRate = _clamp(analysis.finalRate, 10, 12);
    }
    if (analysis.finalRateRange && typeof analysis.finalRateRange === "object") {
      const lo = _clamp(analysis.finalRateRange.low, 10, 12);
      const hi = _clamp(analysis.finalRateRange.high, 10, 12);
      if (lo != null && hi != null && lo > hi) {
        analysis.finalRateRange = { low: hi, high: lo };
      } else {
        analysis.finalRateRange = { low: lo, high: hi };
      }
    }
    if (analysis.finalAmount != null) {
      const _a = Number(analysis.finalAmount);
      analysis.finalAmount = isFinite(_a) && _a > 0 ? Math.round(_a) : null;
    }
    if (analysis.loanTermMonths != null) {
      const _m = Number(analysis.loanTermMonths);
      analysis.loanTermMonths = isFinite(_m) && _m > 0 ? Math.round(_m) : null;
    }
    if (analysis.ltvCalcule != null) {
      analysis.ltvCalcule = _clamp(analysis.ltvCalcule, 0, 100);
    }
    if (analysis.ltcCalcule != null) {
      analysis.ltcCalcule = _clamp(analysis.ltcCalcule, 0, 100);
    }

    // 4. Créer doc dans norvexFinalReports
    const reportData = {
      dossierId,
      agent: "norvex_final",
      finalScore: analysis.finalScore ?? null,
      finalDecision: analysis.finalDecision ?? null,
      finalRate: analysis.finalRate ?? null,
      finalRateRange: analysis.finalRateRange ?? null,
      finalAmount: analysis.finalAmount ?? null,
      loanTermMonths: analysis.loanTermMonths ?? null,
      ltvCalcule: analysis.ltvCalcule ?? null,
      ltcCalcule: analysis.ltcCalcule ?? null,
      negotiationPosture: analysis.negotiationPosture ?? null,
      executiveSummary: analysis.executiveSummary ?? null,
      memorandumComite: analysis.memorandumComite ?? null,
      borrowerProfile: analysis.borrowerProfile ?? null,
      projectAnalysis: analysis.projectAnalysis ?? null,
      financialAnalysis: analysis.financialAnalysis ?? null,
      stressTestSummary: analysis.stressTestSummary ?? null,
      riskAssessment: analysis.riskAssessment ?? null,
      finalConditions: analysis.finalConditions ?? [],
      rdvTalkingPoints: analysis.rdvTalkingPoints ?? [],
      documentsManquants: analysis.documentsManquants ?? [],
      hugoReportSnapshot: hugoReport ? { verdictGlobal: hugoReport.verdictGlobal, actionRecommandee: hugoReport.actionRecommandee } : null,
      model: "claude-opus-4-6",
      createdAt: now,
      ingestedAt: now,
    };
    const reportId = await createDoc(projectId, token, "norvexFinalReports", null, reportData);

    // 5. PATCH dossier (champs final*)
    await patchFsDoc(projectId, token, `dossiers/${dossierId}`, {
      finalScore: analysis.finalScore ?? null,
      finalRate: analysis.finalRate ?? null,
      finalRateRangeLow: analysis.finalRateRange?.low ?? null,
      finalRateRangeHigh: analysis.finalRateRange?.high ?? null,
      finalAmount: analysis.finalAmount ?? null,
      finalLoanTermMonths: analysis.loanTermMonths ?? null,
      finalDecision: analysis.finalDecision ?? null,
      finalConditions: analysis.finalConditions ?? [],
      norvexFinalReportId: reportId,
      norvexFinalAnalyzedAt: now.toISOString(),
    });

    // 6. Audit log
    await createDoc(projectId, token, "agentAuditLog", null, {
      agent: "norvex_final",
      action: "norvex_final_analysis",
      targetType: "dossiers",
      targetId: dossierId,
      result: "success",
      details: {
        finalDecision: analysis.finalDecision,
        finalRate: analysis.finalRate,
        finalAmount: analysis.finalAmount,
        reportId,
      },
      createdAt: now,
    });

    // 7. brainAlert si NO_GO ou red flags critiques
    let alertId = null;
    if (analysis.finalDecision === "NO_GO") {
      alertId = await createDoc(projectId, token, "brainAlerts", null, {
        source: "norvex_final",
        dossierId,
        severity: "critical",
        title: `Norvex Final : NO_GO sur ${dossierId}`,
        message: analysis.finalDecisionJustification || analysis.executiveSummary,
        relatedReportId: reportId,
        status: "pending",
        createdAt: now,
      });
    }

    // 8. Brief HTML + envoi email (sauf si NO_GO et user pas demandé)
    const briefHtml = buildBriefHtml(dossier, analysis);
    let emailResult = { ok: false, skipped: true };
    if (sendEmail) {
      const decLabel = decisionStyle(analysis.finalDecision).label;
      const subject = `Norvex Final · ${decLabel} · ${dossier.borrowerName || dossier.name || dossierId} · ${fmtPct(analysis.finalRate)}`;
      emailResult = await sendBriefViaSendGrid("yves@capitalnorvex.com", subject, briefHtml);
    }

    return json({
      ok: true,
      reportId,
      alertId,
      dossierId,
      finalScore: analysis.finalScore,
      finalDecision: analysis.finalDecision,
      finalRate: analysis.finalRate,
      finalAmount: analysis.finalAmount,
      negotiationPosture: analysis.negotiationPosture,
      analyzedAt: now.toISOString(),
      hadHugoReport: !!hugoReport,
      emailSent: emailResult.ok,
      emailError: emailResult.error || null,
      model: "claude-opus-4-6",
    });
  } catch (e) {
    return json({ error: e.message }, 500);
  }
};

export const config = {
  path: "/api/norvex-final-analyze",
};
