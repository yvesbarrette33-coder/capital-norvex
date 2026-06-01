/**
 * POST /.netlify/functions/norvex-intel
 * Analyse IA d'évaluation immobilière — Norvex Intel™
 *
 * MODE DUAL (depuis 2026-05-05) :
 *
 * MODE A — VALIDATION/RÉCONCILIATION (existant, préservé) :
 *   Body : { sujet, resultats } (l'utilisateur a déjà calculé les 3 approches)
 *   Output : { analysis: "<texte>" }  ← analyse expert en 4 sections
 *
 * MODE B — AUTO-ÉVALUATION IA (nouveau 2026-05-05) :
 *   Body : { mode: "auto", sujet, financier? }
 *     sujet = { adresse, type_actif, marche, superficie_terrain,
 *               superficie_batiment, annee_construction, eval_muni,
 *               req_nom?, req_statut?, rbq_numero?, rbq_statut? }
 *     financier = { noi?, revenus_bruts?, charges?, loyers_unites?,
 *                   cout_construction_estime? }
 *   Claude Opus calcule LUI-MÊME :
 *     - Approche revenu (cap rate marché QC/ON par type/secteur)
 *     - Approche comparables (ventes récentes similaires)
 *     - Approche coût (coût remplacement + dépréciation + terrain)
 *     - Réconciliation pondérée selon type d'actif
 *     - Valeur prêteur conservative
 *     - Stress tests
 *     - Verdict + niveau de confiance
 *   Output : { mode: "auto", evaluation: { ... structure complète ... },
 *              analysis_text: "<rapport>", confidence: "...", disclaimer: "..." }
 *
 * Détection de mode :
 *   - Si body.mode === "auto" → Mode B
 *   - Sinon → Mode A (compatibilité descendante)
 */

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

function fmt(n) {
  if (!n && n !== 0) return "N/D";
  if (n >= 1000000) return "$" + (n / 1000000).toFixed(2) + "M";
  if (n >= 1000) return "$" + Math.round(n).toLocaleString("fr-CA");
  return "$" + n.toFixed(2);
}

// ═══════════════════════════════════════════════════════════════════
// MODE A — Analyse de validation (prompt existant préservé)
// ═══════════════════════════════════════════════════════════════════
function buildPromptModeA(sujet, resultats) {
  return `Tu es un expert en évaluation immobilière commerciale et résidentielle au Québec, avec 20+ ans d'expérience en financement privé.

SUJET
Adresse : ${sujet.adresse}
Type d'actif : ${sujet.type_actif}
Marché : ${sujet.marche}
Superficie terrain : ${sujet.superficie_terrain} pi²
Superficie bâtiment : ${sujet.superficie_batiment} pi²
Année construction : ${sujet.annee_construction}
Évaluation municipale : ${fmt(sujet.eval_muni)}

DATA BRIDGE
REQ — Société : ${sujet.req_nom} | Statut : ${sujet.req_statut}
RBQ — Licence : ${sujet.rbq_numero} | Catégorie : ${sujet.rbq_categorie} | Statut : ${sujet.rbq_statut}
Registre foncier — Dernier acte : ${sujet.foncier_date} | Montant : ${fmt(sujet.foncier_montant)}
Judiciaire / Notes : ${sujet.judiciaire_notes || "Aucune note"}

RÉSULTATS D'ÉVALUATION
Approche revenu  : ${fmt(resultats.revenu_valeur)}  (NOI : ${fmt(resultats.noi)} / cap rate : ${resultats.cap_rate}%)
Approche coût    : ${fmt(resultats.cout_valeur)}
Comparables      : ${fmt(resultats.comp_valeur)}

Réconciliation (${resultats.poids_revenu}% revenu / ${resultats.poids_cout}% coût / ${resultats.poids_comp}% comparables)
Valeur réconciliée : ${fmt(resultats.valeur_mid)}
Low : ${fmt(resultats.valeur_low)} — High : ${fmt(resultats.valeur_high)}
Divergence entre méthodes : ${resultats.divergence_pct}%${resultats.flag_divergence ? " ⚠️ ÉCART IMPORTANT" : ""}

Valeur prêteur (conservative) : ${fmt(resultats.valeur_preteur)}

ANALYSE DE SENSIBILITÉ
Loyers -10% → valeur : ${fmt(resultats.stress_loyers)}
Cap rate +1% → valeur : ${fmt(resultats.stress_cap)}

---

Fournis une analyse professionnelle en 4 sections COURTES (total ≤ 250 mots) :

1. **Réconciliation** : Quelle méthode prioriser et pourquoi, compte tenu du type d'actif et du marché.
2. **Risques principaux** : 2-3 facteurs de risque clés à surveiller (data bridge, marché, sensibilité).
3. **Valeur prêteur** : Justification de la valeur conservative retenue vs valeur marché.
4. **Verdict** : Confiance (élevé / modéré / faible) et recommandation courte en 1-2 phrases.

Format : sections en **gras**, français professionnel, aucun en-tête superflu.`;
}

// ═══════════════════════════════════════════════════════════════════
// MODE B — Auto-évaluation IA (nouveau)
// ═══════════════════════════════════════════════════════════════════
function buildPromptModeB(sujet, financier) {
  return `Tu es un évaluateur immobilier expert (équivalent OEAQ) avec 20+ ans d'expérience en financement privé immobilier au Québec et en Ontario. Tu produis une PRÉ-ÉVALUATION rigoureuse pour Capital Norvex (prêteur privé institutionnel) à partir des inputs ci-dessous.

⚠️ CADRE DE TON ANALYSE
- Marché : Québec et Ontario, 2026
- Tes connaissances : cap rates par type/secteur (multi-résidentiel, commercial, industriel, terrain), coûts de construction par région, comparables marchés récents
- Tu produis une valeur prêteur CONSERVATIVE (LTV-ready), pas une valeur marché optimiste
- Cette pré-évaluation sert à émettre une LOI préliminaire — elle ne remplace PAS une évaluation certifiée OEAQ pour le closing

SUJET DU DOSSIER
Adresse : ${sujet.adresse || "(non fournie)"}
Type d'actif : ${sujet.type_actif || "(non fourni)"}
Marché / MRC : ${sujet.marche || "(non fourni)"}
Superficie terrain : ${sujet.superficie_terrain || "N/D"} pi²
Superficie bâtiment : ${sujet.superficie_batiment || "N/D"} pi²
Année construction : ${sujet.annee_construction || "N/D"}
Évaluation municipale : ${fmt(sujet.eval_muni)}

DATA BRIDGE (si disponibles)
REQ : ${sujet.req_nom || "N/D"} | Statut : ${sujet.req_statut || "N/D"}
RBQ : ${sujet.rbq_numero || "N/D"} | Statut : ${sujet.rbq_statut || "N/D"}

DONNÉES FINANCIÈRES
NOI estimé : ${fmt((financier || {}).noi)}
Revenus bruts annuels : ${fmt((financier || {}).revenus_bruts)}
Charges d'exploitation : ${fmt((financier || {}).charges)}
Loyers/unités (détail) : ${(financier || {}).loyers_unites || "N/D"}
Coût de construction estimé : ${fmt((financier || {}).cout_construction_estime)}
Notes : ${(financier || {}).notes || "Aucune"}

═══════════════════════════════════════════════════════════════════
TÂCHE — PRÉ-ÉVALUATION COMPLÈTE EN 3 APPROCHES
═══════════════════════════════════════════════════════════════════

Calcule TOI-MÊME les 3 approches à partir de tes connaissances du marché QC/ON et des inputs ci-dessus :

1. **APPROCHE REVENU**
   - Si NOI fourni → utilise-le
   - Si NOI absent mais revenus bruts + charges → calcule NOI = revenus_bruts − charges
   - Si pas de NOI ni revenus → estime à partir de loyers de marché par type et superficie
   - Cap rate : choisis un cap rate de marché QC/ON 2026 cohérent avec le type d'actif, l'âge, la localisation. Justifie ton choix.
   - Valeur revenu = NOI / cap rate

2. **APPROCHE COMPARABLES**
   - Estime une valeur basée sur des ventes récentes similaires (type, secteur, superficie, âge)
   - Donne une fourchette $/pi² ou $/porte selon le type d'actif
   - Justifie tes hypothèses

3. **APPROCHE COÛT**
   - Coût de remplacement neuf au pi² (selon type/région 2026)
   - Dépréciation physique + fonctionnelle + économique selon âge
   - + Valeur du terrain (estimation marché)
   - = Valeur coût

4. **RÉCONCILIATION**
   - Pondère selon type d'actif :
     • Multi-rés / commercial locatif → revenu prédominant (60-70% rev / 20-30% comp / 10% coût)
     • Industriel / spécialisé → 40-50% rev, 30-40% coût, 20% comp
     • Terrain → 80-90% comp / 10-20% coût (revenu N/A)
     • Acquisition immeuble locatif → 50-60% rev / 30-40% comp / 10% coût
   - Justifie ta pondération.
   - Calcule valeur réconciliée mid + fourchette low/high (±10%).

5. **VALEUR PRÊTEUR (conservative)**
   - = valeur réconciliée − marge de sécurité 10-15% selon risque
   - Justifie ta marge.

6. **STRESS TESTS**
   - Loyers/revenus -10% → recalcule valeur revenu et valeur réconciliée
   - Cap rate +1 point → recalcule valeur revenu et valeur réconciliée
   - Identifie le scénario le plus défavorable.

7. **VERDICT**
   - Niveau de confiance : élevé / modéré / faible (justifie selon la qualité des inputs)
   - Recommandation pour Capital Norvex (financement OK, OK avec conditions, à approfondir, refus recommandé)
   - Risques principaux à surveiller (2-3 points)

═══════════════════════════════════════════════════════════════════
FORMAT DE SORTIE — JSON STRICT
═══════════════════════════════════════════════════════════════════

Réponds UNIQUEMENT avec ce JSON (aucun texte avant ou après) :

{
  "approche_revenu": {
    "noi_utilise": <nombre ou null>,
    "noi_source": "fourni / calculé / estimé",
    "cap_rate": <nombre, ex: 5.5>,
    "cap_rate_justification": "<courte phrase>",
    "valeur": <nombre>,
    "applicable": <true|false>,
    "notes": "<court>"
  },
  "approche_comparables": {
    "ratio_unitaire": <nombre, ex: 350>,
    "ratio_unite": "$/pi² | $/porte | $/acre",
    "ratio_justification": "<courte phrase>",
    "valeur": <nombre>,
    "applicable": <true|false>,
    "notes": "<court>"
  },
  "approche_cout": {
    "cout_neuf_pi2": <nombre>,
    "depreciation_pct": <nombre>,
    "valeur_terrain": <nombre>,
    "valeur": <nombre>,
    "applicable": <true|false>,
    "notes": "<court>"
  },
  "reconciliation": {
    "poids_revenu_pct": <nombre>,
    "poids_comparables_pct": <nombre>,
    "poids_cout_pct": <nombre>,
    "justification_ponderation": "<courte phrase>",
    "valeur_mid": <nombre>,
    "valeur_low": <nombre>,
    "valeur_high": <nombre>
  },
  "valeur_preteur": {
    "marge_securite_pct": <nombre>,
    "marge_justification": "<courte phrase>",
    "valeur": <nombre>
  },
  "stress_tests": {
    "loyers_moins_10": <nombre>,
    "cap_rate_plus_1pt": <nombre>,
    "scenario_defavorable": "<court>"
  },
  "verdict": {
    "confiance": "élevé | modéré | faible",
    "confiance_justification": "<court>",
    "recommandation": "financement_ok | ok_avec_conditions | a_approfondir | refus_recommande",
    "recommandation_texte": "<1-2 phrases>",
    "risques_principaux": ["<risque 1>", "<risque 2>", "<risque 3>"]
  },
  "disclaimer": "Pré-évaluation IA Norvex Intel basée sur inputs limités et connaissances marché 2026. Ne remplace PAS une évaluation certifiée OEAQ requise pour closing. Sert à la LOI préliminaire et la décision interne Capital Norvex."
}`;
}

// ═══════════════════════════════════════════════════════════════════
// Parser JSON tolérant
// ═══════════════════════════════════════════════════════════════════
function parseJsonOutput(raw) {
  let s = raw.trim();
  s = s.replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/\s*```$/i, "");
  // Extraire le premier {...} block si du texte avant/après
  const match = s.match(/\{[\s\S]*\}/);
  if (match) s = match[0];
  return JSON.parse(s);
}

// ═══════════════════════════════════════════════════════════════════
// Handler principal
// ═══════════════════════════════════════════════════════════════════
export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  }
  if (req.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405 });
  }

  const KEY = process.env.ANTHROPIC_API_KEY;
  if (!KEY) return json({ error: "ANTHROPIC_API_KEY not set" }, 500);

  let body;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON" }, 400);
  }

  const mode = body.mode === "auto" ? "auto" : "validation";
  const sujet = body.sujet || {};

  let prompt;
  let maxTokens;
  let parseAsJson = false;

  if (mode === "auto") {
    // ─── MODE B — Auto-évaluation IA ─────────────────────────────────────
    const financier = body.financier || {};
    if (!sujet.adresse || !sujet.type_actif) {
      return json(
        {
          error:
            "Mode auto requiert au minimum sujet.adresse et sujet.type_actif",
        },
        400
      );
    }
    prompt = buildPromptModeB(sujet, financier);
    maxTokens = 2000;
    parseAsJson = true;
  } else {
    // ─── MODE A — Validation/réconciliation (compatibilité descendante) ──
    const resultats = body.resultats || {};
    if (!sujet.adresse || !resultats) {
      return json(
        { error: "Mode validation requiert sujet et resultats" },
        400
      );
    }
    prompt = buildPromptModeA(sujet, resultats);
    maxTokens = 600;
  }

  try {
    const resp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        // Mode auto = Sonnet (plus rapide, suffisant pour analyse structurée
        // 3 approches). Mode validation = Opus (analyse experte qualitative
        // en 4 sections, qualité prime sur vitesse).
        model: mode === "auto" ? "claude-sonnet-4-6" : "claude-opus-4-6",
        max_tokens: maxTokens,
        messages: [{ role: "user", content: prompt }],
      }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      return json({ error: data.error?.message || "API error" }, 500);
    }

    const rawText = data.content[0].text;

    if (parseAsJson) {
      // Mode auto : parse JSON
      try {
        const evaluation = parseJsonOutput(rawText);
        return json({
          mode: "auto",
          evaluation,
          generated_at: new Date().toISOString(),
        });
      } catch (e) {
        return json(
          {
            error: `Parse JSON échoué : ${e.message}`,
            raw_output: rawText.slice(0, 500),
          },
          500
        );
      }
    }

    // Mode validation : retourne le texte brut
    return json({ mode: "validation", analysis: rawText });
  } catch (e) {
    return json({ error: e.message }, 500);
  }
};
