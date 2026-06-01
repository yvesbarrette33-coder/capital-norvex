/**
 * POST /.netlify/functions/diligence-run
 * Header: x-internal-secret
 * Body: {
 *   dossierId: string (requis),
 *
 *   // REQ — entreprise emprunteuse
 *   emprunteurNeq?: string,
 *   emprunteurNom?: string,
 *
 *   // RBQ — entrepreneur (si construction)
 *   rbqLicence?: string,
 *   rbqNom?: string,
 *   typeProjet?: "residentiel" | "commercial" | "industriel",
 *
 *   // OACIQ — courtier immobilier
 *   oaciqNom?: string,
 *   oaciqPermis?: string,
 *
 *   // AMF — courtier hypothécaire
 *   amfNom?: string,
 *   amfInscription?: string,
 *
 *   // RFQ — registre foncier (analyse PDF avocat senior)
 *   rfqPdfBase64?: string,
 *   rfqLoanAmount?: number,
 *   rfqPropertyValue?: number,
 *   rfqPropertyAddress?: string,
 * }
 *
 * Lance les recherches sur tous les registres publics fournis et produit un
 * rapport de due diligence consolidé via Opus 4.6 niveau avocat senior en
 * droit immobilier.
 *
 * Stocké dans Firestore `diligenceReports[dossierId]`.
 * Patche `dossiers[dossierId].diligenceVerdict` (green/yellow/red).
 */

const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
const USER_AGENT =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 " +
  "(Capital-Norvex-Diligence/1.0; +https://capitalnorvex.com)";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status, headers: { "Content-Type": "application/json" },
  });
}

// ── Firestore (réutilise le même pattern que les autres endpoints) ─
async function getFirestoreToken(sa) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: sa.client_email, sub: sa.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now, exp: now + 3600,
    scope: "https://www.googleapis.com/auth/datastore",
  };
  const b64 = (obj) =>
    btoa(JSON.stringify(obj)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const signingInput = `${b64(header)}.${b64(payload)}`;
  const pemBody = sa.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\n/g, "");
  const keyData = Uint8Array.from(atob(pemBody), c => c.charCodeAt(0));
  const privateKey = await crypto.subtle.importKey(
    "pkcs8", keyData.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5", privateKey, new TextEncoder().encode(signingInput)
  );
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: `${signingInput}.${sigB64}`,
    }),
  });
  const data = await r.json();
  if (!data.access_token) throw new Error("Firestore token failed");
  return { token: data.access_token, projectId: sa.project_id };
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
    for (const [k, vv] of Object.entries(v)) fields[k] = toFsValue(vv);
    return { mapValue: { fields } };
  }
  return { stringValue: String(v) };
}

async function fsSet(projectId, token, collection, docId, payload) {
  const fields = {};
  for (const [k, v] of Object.entries(payload)) fields[k] = toFsValue(v);
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collection}/${encodeURIComponent(docId)}`;
  const r = await fetch(url, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });
  if (!r.ok) throw new Error(`fsSet ${r.status}`);
}

async function fsPatch(projectId, token, collection, docId, payload) {
  const fields = {};
  for (const [k, v] of Object.entries(payload)) fields[k] = toFsValue(v);
  const updateMask = Object.keys(payload).map(
    k => `updateMask.fieldPaths=${encodeURIComponent(k)}`
  ).join("&");
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collection}/${encodeURIComponent(docId)}?${updateMask}`;
  const r = await fetch(url, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });
  // On ne fail pas si le dossier n'existe pas (best-effort patch)
}

// ── HTTP fetch avec User-Agent courtois ────────────────────────────
async function fetchHtml(url) {
  const r = await fetch(url, {
    headers: { "User-Agent": USER_AGENT, "Accept": "text/html" },
  });
  if (!r.ok) throw new Error(`HTTP ${r.status} ${url}`);
  return await r.text();
}

// ── Persona avocat senior commune ──────────────────────────────────
const PERSONA = `Tu es Norvex Diligence™, avocat senior en droit immobilier commercial \
QC + ON (20 ans d'expérience cabinet majeur Stikeman/McCarthy/Norton Rose). \
Spécialisé hypothèques commerciales, RDPRM, CCQ, RBQ, OACIQ, AMF.

TON : précis, factuel, conservateur. Signale TOUS les risques. Si info manquante, \
dis-le. Recommandation finale CLAIRE : 🟢 GO / 🟡 À VÉRIFIER / 🔴 STOP.

Réponds UNIQUEMENT avec le JSON demandé.`;

// ── Searchers ──────────────────────────────────────────────────────
async function searchREQ({ neq, nom }) {
  if (!neq && !nom) return null;
  const url = neq
    ? `https://www.registreentreprises.gouv.qc.ca/RQEntreprisesGRPubl/GR/GR03/GR03A2_19A_PIU_RechEnt_PC/PageEtatRens.aspx?T1.CodeService=S00436&T1.NoUniqueEnt=${encodeURIComponent(neq.replace(/\s/g, ""))}`
    : `https://www.registreentreprises.gouv.qc.ca/RQEntreprisesGRPubl/GR/GR03/GR03A2_19A_PIU_RechEnt_PC/PageRechSimple.aspx?nom=${encodeURIComponent(nom)}`;
  let html;
  try { html = await fetchHtml(url); }
  catch (e) {
    return _searcherError("req", `HTTP error: ${e.message}`);
  }
  const excerpt = html.slice(0, 60000);
  const sysPrompt = PERSONA + `

TÂCHE : analyse fiche REQ (Registre des entreprises QC).
Extraire : NEQ, dénomination, statut (immatriculée/radiée/dissoute), date constitution, forme juridique, dirigeants, adresse siège, activités.
DRAPEAUX ROUGES : statut radié/dissous, constitution récente <6 mois pour gros prêt, changement récent administrateurs, activités hors immobilier.
JSON : { verdict, neq, denomination, statut, date_constitution, forme_juridique, dirigeants, adresse_siege, activites, drapeaux_rouges, drapeaux_jaunes, verdict_explication, recommandation_yves }`;
  return await callClaude(sysPrompt, `Recherche : ${neq || nom}\n\nHTML brut REQ :\n${excerpt}`,
                          1500, "claude-sonnet-4-6", "req");
}

async function searchRBQ({ licence, nom, typeProjet }) {
  if (!licence && !nom) return null;
  const params = new URLSearchParams();
  if (licence) params.set("numero_licence", licence);
  if (nom) params.set("nom", nom);
  const url = `https://www.rbq.gouv.qc.ca/grand-public/services-en-ligne/recherche-detenteur-licence-rbq.html?${params}`;
  let html;
  try { html = await fetchHtml(url); }
  catch (e) {
    return _searcherError("rbq", `HTTP error: ${e.message}`);
  }
  const excerpt = html.slice(0, 50000);
  const typeHint = typeProjet ? `\nLe projet est de type : ${typeProjet}. Vérifie que les catégories couvrent ce type.` : "";
  const sysPrompt = PERSONA + `

TÂCHE : analyse fiche RBQ (licence entrepreneur). CRUCIAL pour Capital Norvex.
Extraire : numéro licence, statut (valide/suspendu/révoqué/expiré), dates émission/expiration, catégories, cautionnement (montant + émetteur + expiration), antécédents disciplinaires.
DRAPEAUX ROUGES BLOQUANTS : licence suspendue/révoquée, cautionnement expiré ou absent, catégories ne couvrant PAS le projet, sanction récente <2 ans, faillite.
JSON : { verdict, numero_licence, statut, date_emission, date_expiration, categories, cautionnement_montant, cautionnement_emetteur, cautionnement_expiration, couvre_projet, drapeaux_rouges, drapeaux_jaunes, verdict_explication, recommandation_yves }`;
  return await callClaude(sysPrompt,
    `Recherche RBQ : ${licence || nom}${typeHint}\n\nHTML brut :\n${excerpt}`,
    1500, "claude-sonnet-4-6", "rbq");
}

async function searchOACIQ({ nom, permis }) {
  if (!nom && !permis) return null;
  const params = new URLSearchParams();
  if (nom) params.set("q", nom);
  if (permis) params.set("permis", permis);
  const url = `https://www.oaciq.com/fr/grand-public/registre-titulaires-permis?${params}`;
  let html;
  try { html = await fetchHtml(url); }
  catch (e) {
    return _searcherError("oaciq", `HTTP error: ${e.message}`);
  }
  const excerpt = html.slice(0, 50000);
  const sysPrompt = PERSONA + `

TÂCHE : analyse fiche OACIQ (permis courtage immobilier).
Extraire : numéro permis, type, statut (actif/suspendu/révoqué/inactif), agence affiliée, sanctions disciplinaires.
DRAPEAUX ROUGES : permis suspendu/révoqué, sanction récente <3 ans (surtout fraude/déclaration), permis résidentiel pour dossier commercial.
JSON : { verdict, numero_permis, nom_courtier, type_permis, statut, agence, sanctions, drapeaux_rouges, drapeaux_jaunes, verdict_explication, recommandation_yves }`;
  return await callClaude(sysPrompt, `Recherche OACIQ : ${nom || permis}\n\nHTML brut :\n${excerpt}`,
                          1200, "claude-sonnet-4-6", "oaciq");
}

async function searchAMF({ nom, inscription }) {
  if (!nom && !inscription) return null;
  const params = new URLSearchParams();
  if (nom) params.set("q", nom);
  if (inscription) params.set("no", inscription);
  const url = `https://lautorite.qc.ca/grand-public/registres/registre-des-entreprises-et-des-individus-autorises-a-exercer?${params}`;
  let html;
  try { html = await fetchHtml(url); }
  catch (e) {
    return _searcherError("amf", `HTTP error: ${e.message}`);
  }
  const excerpt = html.slice(0, 50000);
  const sysPrompt = PERSONA + `

TÂCHE : analyse fiche AMF (Autorité des marchés financiers — courtier hypothécaire).
Extraire : numéro inscription, catégorie, statut (autorisé/suspendu/radié), discipline, cabinet d'attache, sanctions/avis publics.
DRAPEAUX ROUGES : inscription suspendue/radiée, sanction disciplinaire récente, avis de blocage, mention liste d'avertissements AMF.
JSON : { verdict, numero_inscription, nom_personne_ou_cabinet, categorie, statut, cabinet_attache, sanctions, drapeaux_rouges, drapeaux_jaunes, verdict_explication, recommandation_yves }`;
  return await callClaude(sysPrompt, `Recherche AMF : ${nom || inscription}\n\nHTML brut :\n${excerpt}`,
                          1200, "claude-sonnet-4-6", "amf");
}

async function searchRFQ({ pdfBase64, loanAmount, propertyValue, address, borrowerName }) {
  if (!pdfBase64) return null;

  const ctx = [];
  if (borrowerName) ctx.push(`Emprunteur déclaré : ${borrowerName}`);
  if (address) ctx.push(`Adresse de l'immeuble : ${address}`);
  if (loanAmount) ctx.push(`Prêt demandé à Capital Norvex : ${loanAmount.toLocaleString("fr-CA")} $`);
  if (propertyValue) ctx.push(`Valeur estimée immeuble : ${propertyValue.toLocaleString("fr-CA")} $`);
  const ctxStr = ctx.length ? ctx.join("\n") : "Aucun contexte fourni.";

  const sysPrompt = PERSONA + `

⚠️ TÂCHE LA PLUS CRITIQUE : analyse RFQ (Registre foncier QC) — TITRE & HYPOTHÈQUES.

Yves prête plusieurs millions $. Ton interprétation détermine si Capital Norvex est en première charge.

EXTRAIRE & ANALYSER :
1. IDENTIFICATION IMMEUBLE : lot, circonscription, adresse, type, superficie, propriétaire actuel (vérifier match emprunteur)
2. CHAÎNE DES TITRES : 3 derniers actes (vente/donation/succession), cohérence
3. HYPOTHÈQUES : pour chaque inscription : créancier, montant, date, nature, RANG (1er/2e/3e), statut (active/radiée). Calculer position Capital Norvex si engagé. Calculer marge libre = valeur - hypothèques actives.
4. CHARGES FLOTTANTES & SÛRETÉS MOBILIÈRES (RDPRM si visible)
5. SAISIES, PRÉAVIS, ORDONNANCES (DRAPEAUX ROUGES MAJEURS) : préavis exercice 60j/20j → ROUGE, saisie → ROUGE, vente sous contrôle de justice → ROUGE
6. SERVITUDES, RESTRICTIONS : passage, vue, non-construction, conservation, patrimoine culturel, expropriation

ANALYSE NIVEAU NOTE D'OPINION JURIDIQUE :
- Interprétation de chaque inscription importante
- Calcul marge libre
- Position recommandée pour Capital Norvex
- Risques (avec gravité)
- Recommandation finale (GO / GO conditionnel / STOP)

JSON : { verdict, immeuble: {lot,circonscription,adresse,type,superficie,proprietaire_actuel,match_emprunteur}, chaine_titres:[], hypotheques_actives:[{rang_estime,creancier,montant_nominal,date_inscription,nature,numero_inscription}], hypotheques_radiees:[], marge_libre_estimee, position_capital_norvex_si_engage, saisies_preavis:[], servitudes_restrictions:[], autres_inscriptions_significatives:[], drapeaux_rouges:[], drapeaux_jaunes:[], analyse_avocat: "200-400 mots note d'opinion", verdict_explication, recommandation_yves }`;

  const userText = `Document RFQ ci-joint.\n\nContexte du dossier :\n${ctxStr}\n\nProduis ton analyse niveau avocat senior et le JSON demandé.`;

  try {
    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "pdfs-2024-09-25",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "claude-opus-4-6",
        max_tokens: 4500,
        system: sysPrompt,
        messages: [{
          role: "user",
          content: [
            { type: "document", source: { type: "base64", media_type: "application/pdf", data: pdfBase64 } },
            { type: "text", text: userText },
          ],
        }],
      }),
    });
    if (!r.ok) {
      const errText = await r.text();
      return _searcherError("rfq", `Anthropic ${r.status}: ${errText.slice(0, 300)}`);
    }
    const data = await r.json();
    const raw = data.content?.[0]?.text?.trim() || "";
    const start = raw.indexOf("{"); const end = raw.lastIndexOf("}");
    if (start === -1 || end === -1) return _searcherError("rfq", "non parsable");
    const parsed = JSON.parse(raw.slice(start, end + 1));
    parsed._source = "rfq";
    return parsed;
  } catch (e) {
    return _searcherError("rfq", e.message);
  }
}

async function callClaude(systemPrompt, userMessage, maxTokens, model, source) {
  try {
    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        max_tokens: maxTokens,
        system: systemPrompt,
        messages: [{ role: "user", content: userMessage }],
      }),
    });
    if (!r.ok) {
      const errText = await r.text();
      return _searcherError(source, `Anthropic ${r.status}: ${errText.slice(0, 300)}`);
    }
    const data = await r.json();
    const raw = data.content?.[0]?.text?.trim() || "";
    const start = raw.indexOf("{"); const end = raw.lastIndexOf("}");
    if (start === -1 || end === -1) return _searcherError(source, "non parsable");
    const parsed = JSON.parse(raw.slice(start, end + 1));
    parsed._source = source;
    return parsed;
  } catch (e) {
    return _searcherError(source, e.message);
  }
}

function _searcherError(source, msg) {
  return {
    _source: source,
    verdict: "yellow",
    drapeaux_jaunes: [msg],
    drapeaux_rouges: [],
    verdict_explication: msg,
    recommandation_yves: "Vérifier manuellement",
  };
}

// ── Synthèse Opus 4.6 ──────────────────────────────────────────────
async function synthesize(searcherResults) {
  const verdicts = Object.values(searcherResults).map(r => r?.verdict || "gray");
  const rank = { red: 3, yellow: 2, green: 1, gray: 0 };
  const worst = verdicts.reduce((a, b) => (rank[a] >= rank[b] ? a : b), "gray");

  const sysPrompt = PERSONA + `

TÂCHE : SYNTHÈSE FINALE due diligence consolidée pour Yves.

Verdict global = pire des verdicts individuels (sauf si yellow négligeable).

Format brief (cabinet juridique) :
1. Verdict global (green/yellow/red)
2. Synthèse 1-paragraphe (4-6 phrases — où en est le dossier)
3. Points forts (3-5 bullets)
4. Points de vigilance (3-5 bullets)
5. Drapeaux rouges (avec sévérité : mineur/majeur/bloquant)
6. Recommandation finale (conditions si GO, vérifs si CONDITIONNEL, raison si STOP)
7. Prochaines étapes (1-3 actions concrètes)

JSON : { verdict_global, synthese, points_forts, points_vigilance, drapeaux_rouges:[{description,severite}], recommandation_finale, conditions_engagement:[], prochaines_etapes:[] }`;

  const userMsg = `Résultats individuels (JSON) :

${JSON.stringify(searcherResults, null, 2)}

Verdicts : ${JSON.stringify(verdicts)}
Pire verdict mécanique : ${worst}

Produis la synthèse globale.`;

  return await callClaude(sysPrompt, userMsg, 2500, "claude-opus-4-6", "synthesis");
}

// ── Handler principal ──────────────────────────────────────────────
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
  if (req.method !== "POST")
    return new Response("Method Not Allowed", { status: 405 });

  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET)
    return json({ error: "Unauthorized" }, 401);

  if (!ANTHROPIC_API_KEY) return json({ error: "ANTHROPIC_API_KEY manquant" }, 500);

  let body;
  try { body = await req.json(); } catch { return json({ error: "Invalid JSON" }, 400); }
  const { dossierId } = body;
  if (!dossierId) return json({ error: "dossierId requis" }, 400);

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let sa;


  try { sa = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  try {
    const { token, projectId } = await getFirestoreToken(sa);

    // Lance les 5 searchers en parallèle (selon ce qui est applicable)
    const [reqRes, rbqRes, oaciqRes, amfRes, rfqRes] = await Promise.all([
      searchREQ({ neq: body.emprunteurNeq, nom: body.emprunteurNom }),
      searchRBQ({ licence: body.rbqLicence, nom: body.rbqNom, typeProjet: body.typeProjet }),
      searchOACIQ({ nom: body.oaciqNom, permis: body.oaciqPermis }),
      searchAMF({ nom: body.amfNom, inscription: body.amfInscription }),
      searchRFQ({
        pdfBase64: body.rfqPdfBase64,
        loanAmount: body.rfqLoanAmount,
        propertyValue: body.rfqPropertyValue,
        address: body.rfqPropertyAddress,
        borrowerName: body.emprunteurNom,
      }),
    ]);

    const searchers = {};
    if (reqRes) searchers.req = reqRes;
    if (rbqRes) searchers.rbq = rbqRes;
    if (oaciqRes) searchers.oaciq = oaciqRes;
    if (amfRes) searchers.amf = amfRes;
    if (rfqRes) searchers.rfq = rfqRes;

    if (Object.keys(searchers).length === 0) {
      return json({
        error: "Aucune source fournie (au moins un de : emprunteurNeq, rbqLicence, oaciqNom, amfNom, rfqPdfBase64)"
      }, 400);
    }

    // Synthèse via Opus
    const synthesis = await synthesize(searchers);
    const verdictGlobal = synthesis?.verdict_global || "yellow";

    const generatedAt = new Date().toISOString();
    const report = {
      dossierId,
      searchers,
      verdict_global: verdictGlobal,
      synthese: synthesis?.synthese || "",
      points_forts: synthesis?.points_forts || [],
      points_vigilance: synthesis?.points_vigilance || [],
      drapeaux_rouges: synthesis?.drapeaux_rouges || [],
      recommandation_finale: synthesis?.recommandation_finale || "",
      conditions_engagement: synthesis?.conditions_engagement || [],
      prochaines_etapes: synthesis?.prochaines_etapes || [],
      generatedAt,
      agent: "norvex_diligence",
    };

    await fsSet(projectId, token, "diligenceReports", dossierId, report);
    await fsPatch(projectId, token, "dossiers", dossierId, {
      diligenceVerdict: verdictGlobal,
      diligenceSummary: (report.synthese || "").slice(0, 300),
      diligenceUpdatedAt: generatedAt,
    });

    return json({ ok: true, dossierId, verdict_global: verdictGlobal, report });
  } catch (e) {
    return json({ error: e.message, stack: (e.stack || "").slice(0, 500) }, 500);
  }
};

export const config = {
  path: "/api/diligence-run",
};
