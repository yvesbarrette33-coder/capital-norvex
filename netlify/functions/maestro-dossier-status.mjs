/**
 * GET /.netlify/functions/maestro-dossier-status
 * Header: x-internal-secret
 *
 * Retourne la matrice d'avancement de TOUS les dossiers actifs.
 *
 * Pour chaque dossier, calcule l'état des 9 étapes du pipeline :
 *   1. Score Norvex          (champ: score)
 *   2. agent_docs Welcome    (champ: welcomeEmailSentAt OU agentDocsWelcomeSent)
 *   3. Docs reçus            (champ: docsComplete OR docsCount > 0)
 *   4. Hugo Chantier         (champ: hugoReport.verdictGlobal)
 *   5. Norvex Final          (champ: finalScore OR finalReport)
 *   6. RDV Teams (Norah)     (champ: teamsRdvCompletedAt OR teamsRdvScheduled)
 *   7. Diligence             (champ: diligenceReport.verdictGlobal)
 *   8. Camille — Engagement  (champ: engagementLetterSentAt)
 *   9. Notaire dispatch      (champ: notaryDispatchedAt)
 *
 * Retourne aussi : prochaine étape recommandée par dossier (l'étape ⏳ la plus avancée).
 */

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "private, max-age=15" },
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
  return { token: data.access_token, projectId: sa.project_id };
}

function fromFsValue(v) {
  if (!v) return null;
  if (v.nullValue !== undefined) return null;
  if (v.booleanValue !== undefined) return v.booleanValue;
  if (v.integerValue !== undefined) return Number(v.integerValue);
  if (v.doubleValue !== undefined) return v.doubleValue;
  if (v.stringValue !== undefined) return v.stringValue;
  if (v.timestampValue !== undefined) return v.timestampValue;
  if (v.arrayValue !== undefined) return (v.arrayValue.values || []).map(fromFsValue);
  if (v.mapValue !== undefined) {
    const out = {};
    for (const [k, val] of Object.entries(v.mapValue.fields || {})) out[k] = fromFsValue(val);
    return out;
  }
  return null;
}

function docToObj(doc) {
  if (!doc?.fields) return {};
  const out = {};
  for (const [k, v] of Object.entries(doc.fields)) out[k] = fromFsValue(v);
  return out;
}

async function listDossiers(projectId, token) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;
  // ⚠️ FIX 2026-05-07 : retiré orderBy car les dossiers Firestore utilisent
  // `created_at` (snake_case) — pas `createdAt`. Un orderBy sur un champ
  // inexistant fait que Firestore retourne 0 résultat.
  // Tri fait côté JS plus bas (sur created_at OU createdAt en fallback).
  const structuredQuery = {
    from: [{ collectionId: "dossiers" }],
    limit: 200,
  };
  const r = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ structuredQuery }),
  });
  if (!r.ok) return [];
  const data = await r.json();
  if (!Array.isArray(data)) return [];
  return data.filter((r) => r.document).map((r) => ({
    id: r.document.name.split("/").pop(),
    ...docToObj(r.document),
  }));
}

const STEPS = [
  { key: "score",       label: "Score Norvex",       link: "/capital-norvex-pipeline.html" },
  { key: "welcome",     label: "Welcome agent_docs", link: "/capital-norvex-pipeline.html" },
  { key: "docs",        label: "Docs reçus",         link: "/capital-norvex-pipeline.html" },
  { key: "hugo",        label: "Hugo Chantier",      link: "/hugo-admin.html" },
  { key: "final",       label: "Norvex Final",       link: "/capital-norvex-pipeline.html" },
  { key: "rdv",         label: "RDV Teams (Norah)",  link: "/capital-norvex-pipeline.html" },
  { key: "diligence",   label: "Diligence",          link: "/diligence-admin.html" },
  { key: "engagement",  label: "Camille engagement", link: "/camille-admin.html" },
  { key: "notaire",     label: "Notaire",            link: "/capital-norvex-pipeline.html" },
];

function isDone(d, stepKey) {
  switch (stepKey) {
    case "score":
      return Number.isFinite(d.score) || Number.isFinite(d.scoreFinal);
    case "welcome":
      return Boolean(d.welcomeEmailSentAt || d.agentDocsWelcomeSent || d.docsRequestedAt);
    case "docs":
      return Boolean(d.docsComplete) || (Number.isFinite(d.docsReceivedCount) && d.docsReceivedCount > 0);
    case "hugo":
      return Boolean(d.hugoReport?.verdictGlobal || d.hugoVerdict);
    case "final":
      return Boolean(d.finalReport?.finalScore) || Number.isFinite(d.finalScore) || Number.isFinite(d.finalRate);
    case "rdv":
      return Boolean(d.teamsRdvCompletedAt || d.rdvCompletedAt);
    case "diligence":
      return Boolean(d.diligenceReport?.verdictGlobal || d.diligenceVerdict);
    case "engagement":
      return Boolean(d.engagementLetterSentAt || d.engagementLetterSent);
    case "notaire":
      return Boolean(d.notaryDispatchedAt || d.notaryDispatched);
    default:
      return false;
  }
}

function isInProgress(d, stepKey) {
  // Étape "en cours" = drapeau demandé mais pas encore envoyé/complété
  switch (stepKey) {
    case "welcome":
      return Boolean(d.welcomeEmailRequested && !d.welcomeEmailSentAt);
    case "rdv":
      return Boolean(d.teamsRdvScheduled && !d.teamsRdvCompletedAt);
    case "engagement":
      return Boolean(d.engagementLetterRequested && !d.engagementLetterSentAt);
    case "notaire":
      return Boolean(d.notaryDispatchRequested && !d.notaryDispatchedAt);
    case "diligence":
      return Boolean(d.diligenceRequested && !d.diligenceReport);
    default:
      return false;
  }
}

function isBlocked(d, stepKey) {
  // Étape "bloquée" = un verdict négatif a été émis
  if (stepKey === "hugo" && d.hugoReport?.verdictGlobal === "Critique") return true;
  if (stepKey === "diligence" && d.diligenceReport?.verdictGlobal === "rouge") return true;
  if (stepKey === "final" && d.finalDecision === "NO_GO") return true;
  return false;
}

function computeMatrix(d) {
  const matrix = STEPS.map((s) => {
    if (isBlocked(d, s.key)) return { ...s, status: "blocked", icon: "🔴" };
    if (isDone(d, s.key)) return { ...s, status: "done", icon: "✅" };
    if (isInProgress(d, s.key)) return { ...s, status: "in_progress", icon: "⏳" };
    return { ...s, status: "pending", icon: "⚪" };
  });
  // Prochaine étape recommandée = première non-done qui n'est pas blocked
  const nextStep = matrix.find((m) => m.status === "in_progress")
    || matrix.find((m) => m.status === "pending" && !matrix.some((p, i) => p.status === "blocked" && i < matrix.indexOf(p)))
    || null;
  // Compteur progression
  const doneCount = matrix.filter((m) => m.status === "done").length;
  const blockedCount = matrix.filter((m) => m.status === "blocked").length;
  return {
    matrix,
    nextStep,
    doneCount,
    blockedCount,
    progressPct: Math.round((doneCount / STEPS.length) * 100),
  };
}

export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-internal-secret",
      },
    });
  }

  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return json({ error: "Unauthorized" }, 401);
  }

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let sa;


  try { sa = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  try {
    const { token, projectId } = await getFirestoreToken(sa);
    const dossiers = await listDossiers(projectId, token);

    // Filtre : ignorer dossiers fermés/rejetés
    const active = dossiers.filter((d) => {
      const s = (d.status || d.stage || "").toString().toLowerCase();
      return !["closed", "rejected", "archived", "deboursed", "deboursé"].includes(s);
    });

    const enriched = active.map((d) => {
      const { matrix, nextStep, doneCount, blockedCount, progressPct } = computeMatrix(d);
      // ⚠️ FIX 2026-05-07 : fallback sur les noms de champ FR (prenom/nom/type/montant/created_at)
      // utilisés par le système Score Norvex.
      const borrowerName = d.borrowerName
        || d.name
        || `${d.prenom || ""} ${d.nom || ""}`.trim()
        || "(sans nom)";
      return {
        id: d.id,
        borrowerName,
        loanType: d.loanType || d.type || "—",
        loanAmount: d.loanAmount || d.montantApprouve || d.montant || null,
        status: d.status || d.stage || "—",
        score: d.score || d.scoreFinal || d.norvexFinalScore || null,
        finalRate: d.finalRate || d.norvexFinalRate || null,
        createdAt: d.createdAt || d.created_at || null,
        updatedAt: d.updatedAt || d.lastUpdated || d.created_at || null,
        matrix,
        nextStep,
        doneCount,
        blockedCount,
        progressPct,
        totalSteps: STEPS.length,
      };
    });

    // Tri : dossiers avec progression EN COURS (in_progress) en premier,
    // puis par updatedAt DESC.
    enriched.sort((a, b) => {
      const aHasProgress = a.matrix.some((m) => m.status === "in_progress");
      const bHasProgress = b.matrix.some((m) => m.status === "in_progress");
      if (aHasProgress !== bHasProgress) return aHasProgress ? -1 : 1;
      return (b.updatedAt || "").localeCompare(a.updatedAt || "");
    });

    return json({
      ok: true,
      count: enriched.length,
      steps: STEPS.map((s) => ({ key: s.key, label: s.label, link: s.link })),
      dossiers: enriched,
    });
  } catch (e) {
    return json({ error: e.message }, 500);
  }
};

export const config = {
  path: "/api/maestro-dossier-status",
};
