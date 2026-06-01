/**
 * POST /api/camille-create-draft
 * Header: X-Internal-Secret
 * Body: {
 *   instruction,         // ex: "Écris à jacques@example.com pour confirmer la signature de jeudi"
 *   recipient,           // optionnel : email destinataire (Camille déduira sinon)
 *   subject,             // optionnel : sujet imposé (sinon généré)
 *   persona,             // optionnel : "institutional" (défaut) | "ghostwriter"
 *   language,            // optionnel : "fr" | "en" (auto-détecte sinon)
 *   ccRecipients,        // optionnel : array
 *   dossierId,           // optionnel : pour contextualiser
 * }
 *
 * Permet à Yves d'INITIER un courriel via Camille depuis le dashboard,
 * sans attendre qu'un email entre. Camille génère subject + body + signature
 * et stocke le tout en Firestore avec status `pending_yves_approval`.
 *
 * Persona :
 * - institutional : Camille parle pour Camille, signe en son nom (boîte info@/camille@)
 *                   avec disclaimer art. 132 QC.
 * - ghostwriter   : Camille écrit au nom de Yves (boîte yves@), signature Yves,
 *                   AUCUNE mention de Camille/IA.
 */

import {
  createAuditLog,
  getFirestoreToken,
  jsonResponse,
  loadServiceAccount,
  patchDoc,
} from "./_camille-shared.mjs";
import { signatureYvesHtml, signatureCamilleHtml } from "./_signature.mjs";

const COLLECTION_DRAFTS = "camilleDrafts";
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
const MODEL = "claude-opus-4-6";
const MAX_TOKENS = 4096;

// ─── System prompts pour création FROM SCRATCH (initiée par Yves) ─────────

const CREATE_INSTITUTIONAL_PROMPT = `Tu es Camille — NORVEX COUNSEL™, coordonnatrice juridique virtuelle de Capital Norvex Inc.

Yves Barrette (Directeur-Fondateur) te demande d'INITIER un courriel depuis info@capitalnorvex.com (institutionnel — tu signes en ton nom). Tu génères un courriel complet : sujet, corps HTML, et un éventuel rappel pour Yves.

## Voix Camille (institutional)
- Top-tier (Stikeman / McCarthy / BLG / Davies)
- Strict, ferme, professionnel — JAMAIS impoli, JAMAIS familier
- Bilingue parfait — choisis la langue selon le contexte ou l'instruction d'Yves
- Concis et chirurgical — pas de remplissage
- Phrases courtes, paragraphes aérés, listes numérotées si > 1 item
- Référence légale (CCQ art. X, RDPRM, PPSA, LTO) UNIQUEMENT si utile
- Salutations : « Maître, » | « Cher Confrère, » | « Dear Counsel, »
- Clôtures : « Cordialement, » | « Best regards, »

## Garde-fous absolus
- ❌ Tu n'es NI avocate NI notaire — tu es coordonnatrice
- ❌ JAMAIS d'avis juridique, JAMAIS d'opinion légale
- ❌ JAMAIS de signature d'acte, JAMAIS d'autorisation de clause
- ❌ JAMAIS de négociation au nom de Capital Norvex sans validation Yves
- ❌ JAMAIS de pénalité financière au partenaire
- ❌ JAMAIS le mot « investisseur » → toujours « partenaire »

## Contexte Capital Norvex
- Plateforme technologique de financement immobilier privé (QC + ON)
- Frais : 3-3,5 % | Rémunération courtier : ≤ 1 %
- Fourchettes : 2,5 M$ à 100 M$ | Taux 10-12 % | Durée 6-24 mois
- Adresse : 2705-1000 André-Prévost, Île-des-Sœurs, Montréal, QC H3E 0G2

## Format de sortie — JSON STRICT
{
  "subject": "objet concis (5-10 mots)",
  "language": "fr" | "en",
  "body_html": "<p>Corps en HTML propre.</p>",
  "internal_note_for_yves": "rappel court 1-2 phrases ou null"
}

Le HTML : <p>, <ul>, <li>, <strong>, <em>, <br> seulement. AUCUN style inline. AUCUNE signature à la fin (ajoutée auto). AUCUN <html>/<body>. PAS de Markdown.

Réponds UNIQUEMENT avec le JSON.`;

const CREATE_GHOSTWRITER_PROMPT = `Tu rédiges au nom d'Yves Barrette, Directeur-Fondateur de Capital Norvex Inc., depuis sa boîte personnelle yves@capitalnorvex.com.

⚠️ RÈGLE ABSOLUE : tu es un GHOSTWRITER INVISIBLE. AUCUNE mention de « Camille », « assistant », « IA », « équipe ». Le destinataire doit croire qu'Yves a écrit ce courriel lui-même.

Yves te demande d'INITIER un courriel. Tu génères : sujet, corps HTML, rappel éventuel pour Yves lui-même.

## Voix d'Yves
- Direct et factuel, cordial mais pas familier
- Phrases courtes, pas de jargon inutile
- Ouverture : « Bonjour Maître, » | « Bonjour [prénom], » | « Hi [first name], »
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
- Si juridique technique → renvoyer vers notaire/avocat ou Camille
- Si demande hors-scope → demander clarification poliment

## Format de sortie — JSON STRICT
{
  "subject": "objet concis",
  "language": "fr" | "en",
  "body_html": "<p>Corps HTML propre.</p>",
  "internal_note_for_yves": "rappel court ou null"
}

Aucune signature dans body_html (ajoutée auto). PAS de Markdown.

Réponds UNIQUEMENT avec le JSON.`;

// Signatures Yves + Camille : voir _signature.mjs (vrai logo PNG + signature
// manuscrite en base64 inline). Bug fix 2026-05-08.

// ─── Helper Anthropic ────────────────────────────────────────────────────

async function callAnthropic(systemPrompt, userMessage) {
  if (!ANTHROPIC_API_KEY) throw new Error("ANTHROPIC_API_KEY manquant");
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      model: MODEL,
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
  if (!textBlock) throw new Error("Aucun contenu texte retourné");
  return textBlock.text;
}

// ─── Parse JSON output (tolérant aux ```json fences) ─────────────────────

function parseJsonOutput(raw) {
  let s = raw.trim();
  s = s.replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/\s*```$/i, "");
  return JSON.parse(s);
}

// ─── Firestore helper : POST nouveau doc ──────────────────────────────────

async function createDoc(projectId, fsToken, collection, docId, fields) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collection}?documentId=${encodeURIComponent(
    docId
  )}`;
  const fsValue = (v) => {
    if (v === null || v === undefined) return { nullValue: null };
    if (typeof v === "string") return { stringValue: v };
    if (typeof v === "boolean") return { booleanValue: v };
    if (typeof v === "number") return Number.isInteger(v) ? { integerValue: String(v) } : { doubleValue: v };
    if (v instanceof Date) return { timestampValue: v.toISOString() };
    if (Array.isArray(v))
      return {
        arrayValue: { values: v.map(fsValue) },
      };
    if (typeof v === "object") {
      const fields = {};
      for (const [k, val] of Object.entries(v)) fields[k] = fsValue(val);
      return { mapValue: { fields } };
    }
    return { stringValue: String(v) };
  };
  const fsFields = {};
  for (const [k, v] of Object.entries(fields)) fsFields[k] = fsValue(v);

  const r = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${fsToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ fields: fsFields }),
  });
  if (!r.ok) {
    const errText = await r.text();
    throw new Error(
      `Firestore createDoc error ${r.status}: ${errText.slice(0, 300)}`
    );
  }
  return await r.json();
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

  const {
    instruction,
    recipient,
    subject: forcedSubject,
    persona: rawPersona = "institutional",
    language: forcedLang,
    ccRecipients = [],
    dossierId = null,
  } = body;

  if (
    !instruction ||
    typeof instruction !== "string" ||
    instruction.trim().length < 5
  ) {
    return jsonResponse(
      { error: "instruction requise (texte langage naturel ≥ 5 caractères)" },
      400
    );
  }

  const persona = rawPersona === "ghostwriter" ? "ghostwriter" : "institutional";
  const sourceMailbox =
    persona === "ghostwriter"
      ? "yves@capitalnorvex.com"
      : "info@capitalnorvex.com";
  const systemPrompt =
    persona === "ghostwriter"
      ? CREATE_GHOSTWRITER_PROMPT
      : CREATE_INSTITUTIONAL_PROMPT;

  try {
    const sa = await loadServiceAccount();
    const projectId = sa.project_id;
    const fsToken = await getFirestoreToken(sa);

    // Construit user message
    const userMessage = `INSTRUCTION DU PATRON YVES :
${instruction}

CONTEXTE :
- Destinataire (si fourni) : ${recipient || "(à déduire de l'instruction si possible — sinon laisser pour Yves de compléter)"}
- Sujet imposé (si fourni) : ${forcedSubject || "(à générer)"}
- Langue imposée (si fournie) : ${forcedLang || "(détecte selon contexte)"}
- Dossier : ${dossierId || "(non précisé)"}
- Persona active : ${persona}

Génère le courriel en JSON strict. Si tu n'as pas l'info nécessaire pour rédiger correctement, mets une note dans internal_note_for_yves et propose le mieux possible — Yves pourra raffiner ensuite.`;

    const rawOutput = await callAnthropic(systemPrompt, userMessage);
    let parsed;
    try {
      parsed = parseJsonOutput(rawOutput);
    } catch (e) {
      throw new Error(
        `Parse JSON échoué : ${e.message}. Output : ${rawOutput.slice(0, 200)}`
      );
    }

    const subject = forcedSubject || parsed.subject || "(sans objet)";
    const language = forcedLang || parsed.language || "fr";
    const bodyHtml = parsed.body_html || "";
    const note = parsed.internal_note_for_yves || null;

    if (!bodyHtml) {
      throw new Error("Camille n'a pas généré de corps HTML");
    }

    // Construit signedHtml = bodyHtml + signature
    const signature =
      persona === "ghostwriter"
        ? signatureYvesHtml(language)
        : signatureCamilleHtml(language);
    const signedHtml = bodyHtml + signature;

    // Génère un draftId unique
    const draftId = `outbound_${Date.now()}_${Math.random()
      .toString(36)
      .slice(2, 8)}`;

    // Auto-CC Yves sur persona institutional (Camille écrit pour Capital Norvex,
    // Yves doit être en CC pour le suivi). Sur persona ghostwriter, Yves EST déjà
    // l'expéditeur (boîte yves@) — pas de self-CC.
    // Bug fix 2026-05-05 : avant ce patch, le draft sortait sans Yves en CC alors
    // que le body de Camille pouvait dire « M. Barrette est en copie » → décalage.
    const ccInput = Array.isArray(ccRecipients) ? ccRecipients.filter(Boolean) : [];
    let finalCc = ccInput;
    if (persona === "institutional") {
      const yvesEmail = "yves@capitalnorvex.com";
      const hasYves = ccInput.some(
        (e) => typeof e === "string" && e.toLowerCase().trim() === yvesEmail
      );
      if (!hasYves) finalCc = [...ccInput, yvesEmail];
    }

    // Stockage Firestore
    const draftDoc = {
      sourceMailbox,
      fromUser: sourceMailbox,
      toRecipient: recipient || "",
      ccRecipients: finalCc,
      subject,
      bodyHtml,
      signedHtml,
      language,
      status: "pending_yves_approval",
      createdAt: new Date(),
      createdBy: "Yves Barrette (command bar dashboard)",
      origin: "outbound_yves_initiated",
      persona,
      dossierId,
      initialInstruction: instruction.slice(0, 500),
      internalNoteForYves: note,
      versions: [
        {
          version: 1,
          bodyHtml,
          signedHtml,
          instruction: instruction.slice(0, 500),
          persona,
          createdAt: new Date().toISOString(),
          generatedBy: `camille-create-draft (Opus 4.6, persona=${persona})`,
        },
      ],
      currentVersion: 1,
    };

    await createDoc(projectId, fsToken, COLLECTION_DRAFTS, draftId, draftDoc);

    await createAuditLog(projectId, fsToken, {
      agent: "camille",
      action: "create_outbound_draft",
      targetType: COLLECTION_DRAFTS,
      targetId: draftId,
      result: "success",
      details: {
        persona,
        recipient: recipient || "(none)",
        instruction: instruction.slice(0, 200),
      },
    });

    return jsonResponse({
      ok: true,
      draftId,
      persona,
      subject,
      language,
      bodyHtml,
      signedHtml,
      sourceMailbox,
      internalNoteForYves: note,
    });
  } catch (e) {
    return jsonResponse(
      { error: e.message, where: "camille-create-draft" },
      500
    );
  }
}

export const config = {
  path: "/api/camille-create-draft",
};
