/**
 * POST /api/camille-refine-draft
 * Header: X-Internal-Secret
 * Body: { draftId, instruction }
 *
 * KILLER FEATURE — Itération conversationnelle Yves ↔ Camille
 *
 * Yves donne une instruction en langage naturel (« Ajoute une référence à
 * la clause 7.2, plus ferme sur la deadline, mentionne le RDPRM »). Camille
 * régénère le corps du draft en appliquant cette instruction et en gardant
 * sa voix propre selon la persona du draft.
 *
 * Workflow :
 * 1. Charge le draft actuel + email original depuis Firestore (Camille collections)
 * 2. Détecte la persona (sourceMailbox = yves@ → ghostwriter, sinon institutional)
 * 3. Appelle Anthropic Opus 4.6 avec :
 *    - System prompt voix Camille adapté à la persona
 *    - User : email original + draft actuel + instruction Yves
 * 4. Récupère le nouveau bodyHtml
 * 5. Extrait la signature actuelle de signedHtml et la réapplique
 *    (préserve le disclaimer art. 132 QC pour la persona institutional)
 * 6. Push nouvelle version dans versions[]
 * 7. Update bodyHtml + signedHtml courants
 */

import {
  createAuditLog,
  getDoc,
  getFirestoreToken,
  jsonResponse,
  loadServiceAccount,
  patchDoc,
} from "./_camille-shared.mjs";

const COLLECTION_DRAFTS = "camilleDrafts";
const COLLECTION_EMAILS = "camilleEmails";

const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
const MODEL_DRAFTING = "claude-opus-4-6";
const MAX_TOKENS = 4096;

// ─── Voix Camille — System prompts de raffinement (2 personas) ────────────
//
// Pour le refine, on utilise un prompt focused sur la voix + l'instruction
// (plutôt que les system prompts de drafting initial qui sont JSON-strict).
// Le draft existant sert de baseline. On demande juste de réviser le corps
// HTML selon l'instruction.

const REFINEMENT_INSTITUTIONAL_PROMPT = `Tu es Camille — NORVEX COUNSEL™, coordonnatrice juridique virtuelle de Capital Norvex Inc.

Tu réécris des courriels juridiques que tu as toi-même rédigés depuis la boîte info@/camille@. Tu signes en ton nom. Tu n'es PAS Yves dans ce contexte.

## Voix Camille (institutional)
- Top-tier (Stikeman / McCarthy / BLG / Davies)
- Strict, ferme, professionnel — JAMAIS impoli, JAMAIS familier
- Bilingue parfait — détecte la langue du destinataire
- Concis et chirurgical — pas de remplissage
- Phrases courtes, paragraphes aérés, listes numérotées si > 1 item
- Référence légale (CCQ art. X, RDPRM, PPSA, LTO, Teraview) UNIQUEMENT si utile à la coordination — pas pour étaler
- Salutations : « Maître, » | « Cher Confrère, » | « Dear Counsel, »
- Clôtures : « Cordialement, » | « Best regards, »

## Garde-fous absolus
- ❌ Tu n'es NI avocate NI notaire — tu es coordonnatrice
- ❌ JAMAIS d'avis juridique, JAMAIS d'opinion légale
- ❌ JAMAIS de signature d'acte, JAMAIS d'autorisation de clause
- ❌ JAMAIS de négociation au nom de Capital Norvex sans validation Yves
- ❌ JAMAIS de pénalité financière au partenaire
- ❌ JAMAIS le mot « investisseur » → toujours « partenaire »
- ✅ Tu coordonnes, tu structures, tu rappelles, tu fais respecter les échéances

## Contexte Capital Norvex
- Plateforme technologique de financement immobilier privé (QC + ON)
- Frais : 3-3,5 % | Rémunération courtier : ≤ 1 %
- Fourchettes : 2,5 M$ à 100 M$ | Taux 10-12 % | Durée 6-24 mois
- Adresse : 2705-1000 André-Prévost, Île-des-Sœurs, Montréal, QC H3E 0G2
- Tagline : « Capital structuré. Ambition maîtrisée. »

## Format de sortie
Tu retournes UNIQUEMENT le nouveau corps HTML du courriel, paragraphes <p>...</p> propres, balises autorisées : <p>, <ul>, <li>, <strong>, <em>, <br>. AUCUN style inline, AUCUNE signature à la fin (elle sera réappliquée automatiquement avec le disclaimer art. 132 QC). PAS de Markdown, PAS de <html>, PAS de <body>.`;

const REFINEMENT_GHOSTWRITER_PROMPT = `Tu rédiges au nom d'Yves Barrette, Directeur-Fondateur de Capital Norvex Inc., depuis sa boîte personnelle yves@capitalnorvex.com.

⚠️ RÈGLE ABSOLUE : tu es un GHOSTWRITER INVISIBLE.
- AUCUNE mention de « Camille », « assistant », « assistante », « IA », « AI », « équipe juridique », « département », « coordonnatrice »
- Le destinataire doit croire que Yves a écrit ce courriel lui-même
- Style : président d'entreprise expérimenté qui rédige rapidement mais avec rigueur

## Voix d'Yves
- Direct et factuel — pas de formules institutionnelles longues
- Cordial mais pas familier (sauf avec contacts proches connus)
- Ouverture courte : « Bonjour Maître, » | « Bonjour [prénom], » | « Hi [first name], »
- Phrases courtes, pas de jargon inutile
- Niveau de langue SOUTENU (pas familier, pas guindé)
- Tutoiement OK avec contacts proches si l'historique le suggère

## Contexte Capital Norvex
- Plateforme de financement immobilier privé (QC + ON)
- Frais 3-3,5 % | Fourchettes 2,5 M$ à 100 M$ | Taux 10-12 %
- Adresse : 2705-1000 André-Prévost, Île-des-Sœurs, Montréal, QC H3E 0G2
- Tél compagnie : 438-533-PRÊT (7738)
- Equipe : Suzanne Breton (Administratrice), Sophie (info@), Camille (juridique), Norah (téléphone)

## Garde-fous
- Aucune promesse de taux/montant exact sans LOI signée
- Pas de divulgation d'infos confidentielles d'autres dossiers
- Si juridique technique → renvoyer vers notaire/avocat
- Si demande hors-scope → demander clarification poliment

## Format de sortie
Tu retournes UNIQUEMENT le nouveau corps HTML, paragraphes <p>...</p>, sans <html>, sans <body>, sans signature (elle sera ajoutée automatiquement). PAS de Markdown.`;

// ─── Helper : appel Anthropic ────────────────────────────────────────────

async function callAnthropic(systemPrompt, userMessage) {
  if (!ANTHROPIC_API_KEY) {
    throw new Error("ANTHROPIC_API_KEY manquant");
  }
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      model: MODEL_DRAFTING,
      max_tokens: MAX_TOKENS,
      system: systemPrompt,
      messages: [{ role: "user", content: userMessage }],
    }),
  });
  if (!response.ok) {
    const errText = await response.text();
    throw new Error(
      `Anthropic API error ${response.status}: ${errText.slice(0, 300)}`
    );
  }
  const data = await response.json();
  const blocks = data.content || [];
  const textBlock = blocks.find((b) => b.type === "text");
  if (!textBlock) {
    throw new Error("Aucun contenu texte retourné par Anthropic");
  }
  return textBlock.text;
}

// ─── Helper : extraction signature depuis signedHtml ──────────────────────
//
// La signature Camille (institutional) inclut le disclaimer art. 132 QC qui
// est généré côté Python via signature_block.signature_camille(). Pour le
// refine, on préserve ce bloc tel quel en l'extrayant du signedHtml courant
// (= signedHtml.replace(bodyHtml, '')). Si l'extraction échoue, on retourne
// chaîne vide (signedHtml = bodyHtml seul, signature perdue pour cette
// révision — Yves voit et peut rejeter).

function extractSignatureBlock(signedHtml, bodyHtml) {
  if (!signedHtml || !bodyHtml) return "";
  const idx = signedHtml.indexOf(bodyHtml);
  if (idx === -1) return "";
  return signedHtml.substring(idx + bodyHtml.length);
}

// ─── Helper : nettoyage du HTML retourné par Opus ─────────────────────────

function cleanModelOutput(raw) {
  let s = raw.trim();
  s = s.replace(/^```html\s*/i, "").replace(/\s*```$/i, "");
  s = s.replace(/^<html[^>]*>/i, "").replace(/<\/html>$/i, "");
  s = s.replace(/^<body[^>]*>/i, "").replace(/<\/body>$/i, "");
  return s.trim();
}

// ─── Détection persona à partir du draft ──────────────────────────────────

function detectPersona(draft) {
  // sourceMailbox stocke yves@... pour ghostwriter, info@/camille@ pour institutional
  const src = (draft.sourceMailbox || draft.fromUser || "").toLowerCase();
  if (src.startsWith("yves@") || src.includes("yvesbarrette")) {
    return "ghostwriter";
  }
  return "institutional";
}

// ─── Handler ─────────────────────────────────────────────────────────────

export default async function handler(req) {
  if (req.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405);
  }
  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return jsonResponse({ error: "Unauthorized" }, 401);
  }

  let body;
  try {
    body = await req.json();
  } catch {
    return jsonResponse({ error: "Invalid JSON" }, 400);
  }

  const { draftId, instruction } = body;
  if (!draftId) return jsonResponse({ error: "draftId requis" }, 400);
  if (
    !instruction ||
    typeof instruction !== "string" ||
    instruction.trim().length < 3
  ) {
    return jsonResponse(
      { error: "instruction requise (texte langage naturel ≥ 3 caractères)" },
      400
    );
  }

  try {
    const sa = await loadServiceAccount();
    const projectId = sa.project_id;
    const fsToken = await getFirestoreToken(sa);

    // Charge le draft actuel
    const draft = await getDoc(projectId, fsToken, COLLECTION_DRAFTS, draftId);
    if (!draft) return jsonResponse({ error: "Draft introuvable" }, 404);
    if (draft.status === "sent") {
      return jsonResponse(
        { error: "Draft déjà envoyé, raffinement interdit" },
        409
      );
    }

    // Détecte persona
    const persona = detectPersona(draft);
    const systemPrompt =
      persona === "ghostwriter"
        ? REFINEMENT_GHOSTWRITER_PROMPT
        : REFINEMENT_INSTITUTIONAL_PROMPT;

    // Charge l'email original (si lié)
    let originalEmail = "(email original non trouvé — refine sans contexte amont)";
    if (draft.incomingEmailId) {
      const originalDoc = await getDoc(
        projectId,
        fsToken,
        COLLECTION_EMAILS,
        draft.incomingEmailId
      );
      if (originalDoc) {
        const from = originalDoc.from || "(inconnu)";
        const subj = originalDoc.subject || "";
        const bodyText = originalDoc.bodyText || originalDoc.bodyPreview || "";
        originalEmail = `De : ${from}\nSujet : ${subj}\n\n${bodyText}`;
      }
    }

    // Détecte la langue (depuis triage snapshot ou défaut FR)
    const lang =
      (draft.triageSnapshot && draft.triageSnapshot.language) ||
      draft.language ||
      "fr";

    // Construit le user message
    const currentBody = draft.bodyHtml || "(draft vide)";
    const dossierHint =
      (draft.triageSnapshot && draft.triageSnapshot.dossierIdGuess) ||
      draft.dossierId ||
      "(dossier non identifié)";

    const userMessage = `EMAIL ORIGINAL REÇU :
${originalEmail}

DOSSIER : ${dossierHint}
LANGUE : ${lang}
PERSONA ACTIVE : ${persona === "ghostwriter" ? "Ghostwriter (signe Yves Barrette)" : "Institutional (signe Camille)"}

DRAFT ACTUEL (à réviser) :
${currentBody}

🚨 INSTRUCTION DU PATRON YVES POUR CETTE RÉVISION (À RESPECTER ABSOLUMENT) :
${instruction}

Réécris le corps du courriel en appliquant l'instruction ci-dessus, en gardant la voix appropriée à la persona ${persona}. Retourne UNIQUEMENT le nouveau HTML du body (paragraphes <p>...</p>), sans <html>, sans <body>, sans signature. La signature sera ajoutée automatiquement.`;

    // Appel Opus
    const rawOutput = await callAnthropic(systemPrompt, userMessage);
    const newBodyHtml = cleanModelOutput(rawOutput);

    // Extrait la signature actuelle (préserve disclaimer art. 132 QC pour
    // institutional, ou bloc signature Yves pour ghostwriter)
    const signatureBlock = extractSignatureBlock(
      draft.signedHtml || "",
      draft.bodyHtml || ""
    );
    const newSignedHtml = signatureBlock
      ? newBodyHtml + signatureBlock
      : newBodyHtml;

    // Push nouvelle version
    const previousVersions = Array.isArray(draft.versions)
      ? draft.versions
      : [];
    const versionEntry = {
      version: previousVersions.length + 1,
      bodyHtml: newBodyHtml,
      signedHtml: newSignedHtml,
      instruction: instruction,
      persona: persona,
      createdAt: new Date().toISOString(),
      generatedBy: `camille-refine-draft (Opus 4.6, persona=${persona})`,
    };
    let finalVersions = [...previousVersions, versionEntry];

    // Si c'est la première fois qu'on raffine, on archive aussi la v1
    // originale pour que l'historique soit complet
    if (previousVersions.length === 0) {
      const v1Entry = {
        version: 1,
        bodyHtml: draft.bodyHtml || "",
        signedHtml: draft.signedHtml || "",
        instruction: "(version initiale auto-générée)",
        persona: persona,
        createdAt: draft.createdAt || new Date().toISOString(),
        generatedBy: "camille-orchestrator (initial)",
      };
      finalVersions = [v1Entry, { ...versionEntry, version: 2 }];
    }

    // Update draft
    const patch = {
      bodyHtml: newBodyHtml,
      signedHtml: newSignedHtml,
      versions: finalVersions,
      lastModifiedAt: new Date(),
      lastModifiedBy: "Yves Barrette (refine via dashboard)",
      lastInstruction: instruction,
      currentVersion: finalVersions.length,
    };

    await patchDoc(projectId, fsToken, COLLECTION_DRAFTS, draftId, patch);

    await createAuditLog(projectId, fsToken, {
      agent: "camille",
      action: "refine_draft",
      targetType: COLLECTION_DRAFTS,
      targetId: draftId,
      result: "success",
      details: {
        instruction: instruction.slice(0, 200),
        persona: persona,
        newVersion: finalVersions.length,
        signaturePreserved: signatureBlock.length > 0,
      },
    });

    return jsonResponse({
      ok: true,
      draftId,
      version: finalVersions.length,
      persona: persona,
      newBodyHtml: newBodyHtml,
      newSignedHtml: newSignedHtml,
      versionsCount: finalVersions.length,
      signaturePreserved: signatureBlock.length > 0,
    });
  } catch (e) {
    return jsonResponse(
      { error: e.message, where: "camille-refine-draft" },
      500
    );
  }
}

export const config = {
  path: "/api/camille-refine-draft",
};
