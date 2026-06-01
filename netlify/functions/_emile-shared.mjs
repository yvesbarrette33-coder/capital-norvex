/**
 * Émile — NORVEX BRIEFING™ — module shared (Netlify JS)
 *
 * Génère un brief pré-RDV premium en consultant un "board of advisors"
 * virtuel via Claude Opus 4.6. Trigger automatique depuis confirm-rdv /
 * rdv-public-approve / rdv-partenaire-book.
 *
 * Garde-fous absolus : aucune approbation, aucun chiffre inventé, posture
 * institutionnelle, AMF + Code professions + Loi 25 respectés.
 */

const ANTHROPIC_MODEL = "claude-opus-4-5";  // méga cerveau Yves

const SYSTEM_PROMPT = `Tu es **Émile**, chef de cabinet du fondateur Yves Barrette de Capital Norvex Inc. (prêteur immobilier privé canadien, propulsé par IA propriétaire).

Tu prépares un brief pré-RDV pour Yves. Tu consultes un **board of advisors** virtuel composé de :

1. **🧑‍⚖️ Camille (Juriste interne)** — AMF, Code des professions QC, Loi 25, Barreau du Québec.
2. **📜 Notaire-conseil** — Hypothèques, conventions, structures de garanties, transferts.
3. **💼 Fiscaliste CPA senior** — Optimisation, structures corporatives, rendements nets après impôt.
4. **🏗️ Hugo (PM Construction)** — Risques techniques, déboursés, expertise immobilière.
5. **💬 Sophie (Relations clients)** — Posture, ton, historique communication.
6. **📊 Banquier d'affaires senior** — Capital structure, mezz, equity, due diligence.
7. **🎯 Stratège M&A** — Positionnement, négociation, signaux prospect.
8. **🧭 Yves (Fondateur)** — Vision business, garde-fous, dernier mot.

Pour chaque cible, tu produis un brief structuré au format JSON suivant exactement :

{
  "lecture_analytique": "1 paragraphe de 60-90 mots interprétant le pattern d'engagement (clics, opens, partages internes). Ton institutionnel, factuel, sans surenchère.",
  "theses_co_financement": [
    "Thèse 1 — refi/equity/mezz selon profil (1 phrase précise)",
    "Thèse 2 — autre angle réaliste",
    "Thèse 3 — option différente"
  ],
  "talking_points": [
    "1. Ouverture (laisser parler en premier)",
    "2. Discipline / positionnement Capital Norvex",
    "3. Rendement / structure (10-12% net annuel, hypothèque 1er rang)",
    "4. Différenciation par écosystème IA (Score / Track / Intel / Brain)",
    "5. Closing (mesurer si deal concret ou exploration)"
  ],
  "donts": [
    "Aucune approbation/engagement avant LOI signée — rester sur 'expression d'intérêt non liante'",
    "Pas de chiffres précis avant qu'il/elle décrive son besoin",
    "Pas de pression sur RDV Teams si profil traditionnel — proposer alternative",
    "Pas de mention compétiteurs (Romspen, Trez, Otera, Fiera) — différencier par écosystème IA",
    "Aucune référence à Drouin/Finstar/LFI ou autres litiges en cours"
  ]
}

GARDE-FOUS ABSOLUS :
- ❌ Tu n'inventes JAMAIS de chiffres (rendements, ratios, projets, taux).
- ❌ Tu ne mentionnes JAMAIS Score Norvex zone interdite.
- ❌ Tu ne dis JAMAIS « approuvé » avant lettre d'engagement.
- ✅ Tu adaptes le ton selon le profil.
- ✅ Tu réponds UNIQUEMENT en JSON valide, rien d'autre.`;

// ─── Pull target Firestore par email (cherche dans 3 collections) ──────────
const COLLECTIONS = ["capitalTargets", "advisorTargets", "promoteurTargets", "courtierTargets"];

export async function pullTargetByEmail(projectId, fsToken, email) {
  if (!email) return null;
  // Cherche dans 3 emplacements possibles selon collection :
  //  - publicContact.email (capitalTargets / advisorTargets)
  //  - email (promoteurTargets / courtierTargets)
  //  - sentTo (fallback historique)
  const fieldPaths = ["publicContact.email", "email", "sentTo"];
  for (const col of COLLECTIONS) {
    for (const fieldPath of fieldPaths) {
      const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;
      const body = {
        structuredQuery: {
          from: [{ collectionId: col }],
          where: {
            fieldFilter: {
              field: { fieldPath },
              op: "EQUAL",
              value: { stringValue: email },
            },
          },
          limit: 1,
        },
      };
      try {
        const r = await fetch(url, {
          method: "POST",
          headers: { Authorization: `Bearer ${fsToken}`, "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        const data = await r.json();
        const found = (Array.isArray(data) ? data : []).find((d) => d.document);
        if (found) {
          const parsed = parseFsDoc(found.document);
          // Normalise email pour le rendering
          if (!parsed.publicContact || typeof parsed.publicContact !== "object") {
            parsed.publicContact = {};
          }
          if (!parsed.publicContact.email) {
            parsed.publicContact.email = parsed.email || parsed.sentTo || email;
          }
          return {
            collection: col,
            docId: found.document.name.split("/").pop(),
            data: parsed,
          };
        }
      } catch (e) {
        console.warn(`[Émile] query ${col}/${fieldPath}/${email} failed:`, e.message);
      }
    }
  }
  return null;
}

function parseFsDoc(doc) {
  const out = {};
  if (!doc.fields) return out;
  for (const [k, v] of Object.entries(doc.fields)) {
    out[k] = parseFsValue(v);
  }
  return out;
}

function parseFsValue(v) {
  if (v.stringValue !== undefined) return v.stringValue;
  if (v.integerValue !== undefined) return Number(v.integerValue);
  if (v.doubleValue !== undefined) return v.doubleValue;
  if (v.booleanValue !== undefined) return v.booleanValue;
  if (v.timestampValue !== undefined) return v.timestampValue;
  if (v.nullValue !== undefined) return null;
  if (v.arrayValue) return (v.arrayValue.values || []).map(parseFsValue);
  if (v.mapValue) {
    const m = {};
    for (const [k, vv] of Object.entries(v.mapValue.fields || {})) m[k] = parseFsValue(vv);
    return m;
  }
  return null;
}

// ─── SendGrid stats ────────────────────────────────────────────────────────
export async function pullSendGridStats(email) {
  const key = process.env.SENDGRID_API_KEY;
  if (!key || !email) return { perso: { opens: 0, clicks: 0, messages: 0 }, org_contacts: [] };

  const persoQuery = `to_email = "${email}" AND last_event_time > TIMESTAMP "2026-04-25T00:00:00Z"`;
  const persoR = await fetch(
    `https://api.sendgrid.com/v3/messages?query=${encodeURIComponent(persoQuery)}&limit=50`,
    { headers: { Authorization: `Bearer ${key}` } }
  );
  const persoMsgs = (await persoR.json()).messages || [];

  let orgContacts = [];
  if (email.includes("@")) {
    const domain = email.split("@").pop();
    const orgQuery = `to_email LIKE "%@${domain}" AND last_event_time > TIMESTAMP "2026-04-25T00:00:00Z"`;
    const orgR = await fetch(
      `https://api.sendgrid.com/v3/messages?query=${encodeURIComponent(orgQuery)}&limit=100`,
      { headers: { Authorization: `Bearer ${key}` } }
    );
    const orgMsgs = (await orgR.json()).messages || [];
    const agg = new Map();
    for (const m of orgMsgs) {
      const em = m.to_email;
      if (!em) continue;
      const cur = agg.get(em) || { email: em, opens: 0, clicks: 0 };
      cur.opens += m.opens_count || 0;
      cur.clicks += m.clicks_count || 0;
      agg.set(em, cur);
    }
    orgContacts = Array.from(agg.values()).sort(
      (a, b) => b.clicks - a.clicks || b.opens - a.opens
    );
  }

  return {
    primary_email: email,
    perso: {
      opens: persoMsgs.reduce((s, m) => s + (m.opens_count || 0), 0),
      clicks: persoMsgs.reduce((s, m) => s + (m.clicks_count || 0), 0),
      messages: persoMsgs.length,
    },
    org_contacts: orgContacts,
    total_opens: orgContacts.reduce((s, c) => s + c.opens, 0),
    total_clicks: orgContacts.reduce((s, c) => s + c.clicks, 0),
  };
}

// ─── Board of Advisors (Claude Opus) ───────────────────────────────────────
export async function callBoardOfAdvisors(target, engagement) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) return fallbackBrief(target);

  const userPrompt = buildUserPrompt(target, engagement);

  try {
    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: ANTHROPIC_MODEL,
        max_tokens: 2500,
        system: SYSTEM_PROMPT,
        messages: [{ role: "user", content: userPrompt }],
      }),
    });
    const data = await r.json();
    let raw = (data.content?.[0]?.text || "").trim();
    if (raw.startsWith("```")) {
      raw = raw.split("```")[1].replace(/^json\s*/, "").trim();
    }
    return JSON.parse(raw);
  } catch (e) {
    console.warn("[Émile] board call failed:", e.message);
    return fallbackBrief(target);
  }
}

function buildUserPrompt(target, engagement) {
  const cap = target.capitalEstimate || {};
  const capStr = cap.min
    ? `${(cap.min / 1e6).toFixed(0)}M-${(cap.max / 1e6).toFixed(0)}M$`
    : "—";
  const perso = engagement.perso || {};
  return `**Cible à briefer** :

- Nom : ${target.name || ""}
- Organisation : ${target.organization || ""}
- Titre/poste : ${target.title || ""}
- Région : ${target.region || ""}
- Capital estimé : ${capStr}
- Thèse business : ${target.investmentThesis || ""}
- Langue préférée : ${target.language || "fr"}

**Historique communication Capital Norvex** :
- Dernier sujet envoyé : ${target.sentSubject || "—"}
- Date envoi : ${target.sentAt || "—"}

**Engagement live (SendGrid)** :
- Email principal ${engagement.primary_email}: ${perso.opens || 0} opens / ${perso.clicks || 0} clicks (${perso.messages || 0} messages)
- Total domaine : ${engagement.total_opens || 0} opens / ${engagement.total_clicks || 0} clicks sur ${(engagement.org_contacts || []).length} contacts

Génère le brief JSON selon ton format strict. Adapte le ton et les thèses au profil spécifique.`;
}

function fallbackBrief(target) {
  return {
    lecture_analytique: `Pattern d'engagement à interpréter manuellement. ${target.organization || "Cette organisation"} reste à analyser plus en profondeur avant l'appel.`,
    theses_co_financement: [
      "Refi senior debt sur asset stabilisé — sortie d'une dette bancaire vers structure flexible Capital Norvex.",
      "Co-investissement equity/mezz sur projet en pré-vente — couche capital structurée 10-12%.",
      "Plateforme courtier partenaire — intégration réseau de financement avec rémunération transparente négociée selon le dossier.",
    ],
    talking_points: [
      "1. Ouverture : laisser parler en premier, comprendre l'angle.",
      "2. Capital Norvex = prêteur privé canadien garanti par hypothèque 1er rang, propulsé par IA propriétaire.",
      "3. Rendement 10-12% net annuel, transparence + discipline institutionnelle.",
      "4. Différenciation par écosystème IA (Score, Track, Intel, Brain).",
      "5. Closing : dossier précis ou exploration ?",
    ],
    donts: [
      "Aucune approbation/engagement avant LOI signée.",
      "Pas de chiffres précis avant que la cible décrive son besoin.",
      "Pas de pression sur RDV Teams si profil traditionnel.",
      "Pas de mention compétiteurs.",
      "Aucune référence à dossiers en litige.",
    ],
  };
}

// ─── Render HTML brief premium ─────────────────────────────────────────────
export function renderBriefHTML(target, engagement, advisor) {
  const name = target.name || "Cible";
  const org = target.organization || "";
  const title = target.title || "";
  const region = target.region || "";
  const cap = target.capitalEstimate || {};
  const capStr = cap.min ? `${(cap.min / 1e6).toFixed(0)}M – ${(cap.max / 1e6).toFixed(0)}M$` : "—";
  const thesis = target.investmentThesis || "Profil business à enrichir.";

  const perso = engagement.perso || {};
  const today = new Date().toISOString().slice(0, 10);
  const firstName = name.split(" ")[0];

  const theses = (advisor.theses_co_financement || []).map((t) => `<li>${esc(t)}</li>`).join("\n");
  const tp = (advisor.talking_points || []).map((p) => `<li>${esc(p)}</li>`).join("\n");
  const donts = (advisor.donts || []).map((d) => `<li>${esc(d)}</li>`).join("\n");

  return `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Brief pré-call — ${esc(name)} — Capital Norvex</title>
<style>
  @page { size: letter; margin: 18mm; }
  * { box-sizing: border-box; }
  body { font-family: Georgia, serif; color: #0a0d13; background: #faf8f4; margin: 0; padding: 28px 36px; line-height: 1.55; font-size: 13.5px; }
  .header { border-bottom: 2px solid #b8975a; padding-bottom: 10px; margin-bottom: 18px; }
  .kicker { font-size: 10px; letter-spacing: 3px; text-transform: uppercase; color: #b8975a; font-family: Arial, sans-serif; }
  h1 { font-size: 22px; margin: 4px 0 0 0; font-weight: normal; }
  h1 em { color: #b8975a; font-style: italic; }
  h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 2px; color: #0a0d13; border-bottom: 1px solid #d4c298; padding-bottom: 3px; margin: 18px 0 8px 0; font-family: Arial, sans-serif; }
  .signal-row { display: flex; gap: 8px; margin: 8px 0; }
  .signal { flex: 1; background: #fff; border: 1px solid #e3d9c0; padding: 8px 10px; border-radius: 3px; }
  .signal .num { font-size: 22px; color: #b8975a; font-weight: bold; font-family: Arial, sans-serif; font-variant-numeric: tabular-nums lining-nums; }
  .signal .label { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: #6c6356; font-family: Arial, sans-serif; }
  ul { padding-left: 18px; margin: 6px 0 12px 0; }
  li { margin-bottom: 4px; }
  .talking-points { background: #fff; border-left: 3px solid #b8975a; padding: 10px 14px; margin: 8px 0; }
  .talking-points li::marker { color: #b8975a; }
  .danger { background: #fff5f0; border-left: 3px solid #c73c2e; padding: 10px 14px; margin: 8px 0; }
  .danger ul li::marker { color: #c73c2e; }
  .footer { margin-top: 22px; padding-top: 10px; border-top: 1px solid #d4c298; font-size: 10.5px; color: #6c6356; text-align: center; font-family: Arial, sans-serif; letter-spacing: 1px; }
  strong { color: #0a0d13; }
  .meta-line { font-size: 11px; color: #6c6356; margin-top: 6px; font-family: Arial, sans-serif; }
  .lecture { font-size: 12px; color: #4a4337; background: #fff; border: 1px solid #e3d9c0; padding: 10px 14px; border-radius: 3px; margin-top: 8px; }
</style>
</head>
<body>

<div class="header">
  <div class="kicker">Émile · Norvex Briefing™ · Confidentiel</div>
  <h1>${esc(name)} — <em>${esc(org)}</em></h1>
  <div class="meta-line">${esc(title) || "—"} · ${esc(region) || "—"} · Capital estimé : ${capStr} · Mis à jour ${today}</div>
</div>

<h2>Profil &amp; Thèse</h2>
<p>${esc(thesis)}</p>

<h2>Signal d'intérêt — Engagement Capital Norvex</h2>
<div class="signal-row">
  <div class="signal"><div class="num">${perso.opens || 0}</div><div class="label">Opens — perso</div></div>
  <div class="signal"><div class="num">${perso.clicks || 0}</div><div class="label">Clicks — perso</div></div>
  <div class="signal"><div class="num">${engagement.total_opens || 0}</div><div class="label">Opens — domaine</div></div>
  <div class="signal"><div class="num">${engagement.total_clicks || 0}</div><div class="label">Clicks — domaine</div></div>
</div>
<div class="meta-line">Contact principal : ${esc(engagement.primary_email || "—")} · ${(engagement.org_contacts || []).length} contact(s) actif(s) sur le domaine</div>

<h2>Lecture analytique du board</h2>
<div class="lecture">${esc(advisor.lecture_analytique || "")}</div>

<h2>Thèses de co-financement plausibles</h2>
<ul>${theses}</ul>

<h2>Talking points si ${esc(firstName)} appelle</h2>
<div class="talking-points"><ol>${tp}</ol></div>

<h2>Ce qu'il faut <span style="color:#c73c2e;">PAS</span> faire</h2>
<div class="danger"><ul>${donts}</ul></div>

<div class="footer">ÉMILE · NORVEX BRIEFING™ · CAPITAL NORVEX INC. · 2705-1000 ANDRÉ-PRÉVOST · CAPITALNORVEX.COM</div>

</body>
</html>`;
}

function esc(s) {
  if (!s) return "";
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
