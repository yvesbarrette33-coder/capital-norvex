/**
 * POST /api/beatrice-create-draft
 * Header: X-Internal-Secret
 * Body: {
 *   instruction,         // ex: "Écris à patrick.rougeau@desjardins.com pour le remercier de l'appel d'hier"
 *   recipient,           // optionnel
 *   subject,             // optionnel
 *   language,            // optionnel
 *   ccRecipients,        // optionnel
 * }
 *
 * Permet à Yves d'INITIER un courriel via Béatrice (ghostwriter Yves) depuis le
 * dashboard, sans attendre qu'un email entre. Béatrice génère subject + body
 * et stocke avec status `pending_yves_approval`.
 *
 * Béatrice = ghostwriter exclusif Yves (pas de persona Camille).
 */

import {
  createAuditLog,
  getFirestoreToken,
  jsonResponse,
  loadServiceAccount,
} from "./_camille-shared.mjs";
import { signatureYvesHtml } from "./_signature.mjs";

// ─── Upload helper for attachments (Firebase Storage via GCS API) ─────────
// 2026-05-20 — ajout du support pièces jointes. L'utilisateur fournit
// `attachments: [{name, contentBase64, contentType}]` dans le body. On upload
// chaque pièce jointe dans Firebase Storage (path `beatriceAttachments/{draftId}/{name}`)
// puis on stocke `[{name, storagePath, contentType}]` dans le draft Firestore.
// `sendEmailSmart()` (via buildGraphAttachments + downloadStorageAsBase64)
// téléchargera depuis Storage au moment de l'envoi.
//
// On utilise l'endpoint Google Cloud Storage classique (storage.googleapis.com)
// avec scope devstorage.read_write — le même endpoint que `downloadStorageAsBase64`
// utilise pour lire. Le scope read_only par défaut dans `getStorageToken` ne suffit
// pas pour l'upload, donc on génère un token spécifique read_write inline.
async function getStorageWriteToken(sa) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: sa.client_email,
    sub: sa.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
    scope: "https://www.googleapis.com/auth/devstorage.read_write",
  };
  const b64url = (obj) =>
    Buffer.from(JSON.stringify(obj))
      .toString("base64")
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");
  const signingInput = `${b64url(header)}.${b64url(payload)}`;
  const crypto = await import("node:crypto");
  const sig = crypto
    .createSign("RSA-SHA256")
    .update(signingInput)
    .sign(sa.private_key);
  const sigB64 = sig
    .toString("base64")
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
  if (!data.access_token)
    throw new Error("Storage write token failed: " + JSON.stringify(data));
  return data.access_token;
}

async function uploadAttachmentToStorage({
  bucketName,
  storagePath,
  contentBase64,
  contentType,
  storageWriteToken,
}) {
  const bytes = Buffer.from(contentBase64, "base64");
  // Endpoint GCS classique pour upload (même domaine que downloadStorageAsBase64)
  const url = `https://storage.googleapis.com/upload/storage/v1/b/${bucketName}/o?uploadType=media&name=${encodeURIComponent(
    storagePath
  )}`;
  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${storageWriteToken}`,
      "Content-Type": contentType || "application/octet-stream",
      "Content-Length": String(bytes.length),
    },
    body: bytes,
  });
  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(
      `Storage upload error ${resp.status}: ${errText.slice(0, 300)}`
    );
  }
  return await resp.json();
}

const COLLECTION_DRAFTS = "beatriceDrafts";
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
const MODEL = "claude-opus-4-6";
const MAX_TOKENS = 4096;

// ─── System prompt — Béatrice ghostwriter Yves ────────────────────────────

const CREATE_GHOSTWRITER_PROMPT = `Tu es l'assistante exécutive ghostwriter d'Yves Barrette, Directeur-Fondateur de Capital Norvex Inc.

Yves te demande d'INITIER un courriel depuis sa boîte yves@capitalnorvex.com. Tu génères : sujet, corps HTML, et un éventuel rappel pour Yves.

⚠️ RÈGLE ABSOLUE : tu es invisible. Toutes tes réponses sont signées « Yves Barrette ». AUCUNE mention de « Béatrice », « assistant », « assistante », « IA », « AI », « équipe ». Le destinataire doit croire qu'Yves a écrit ce courriel lui-même.

## Voix d'Yves
- Ultra professionnel, niveau institutionnel (Stikeman, BlackRock, Brookfield)
- Humain et chaleureux — JAMAIS robotique
- Direct, droit au point, sans blabla
- Courtois, formules sobres
- JAMAIS d'humour, blagues, familiarité
- JAMAIS d'émojis dans les courriels d'affaires
- JAMAIS de tournures « IA évidente » : « Je serais ravi », « Je reste à votre entière disposition »
- Niveau de langue SOUTENU
- FR québécois soutenu / EN canadien neutre

## Contexte Capital Norvex (1000%)
- Plateforme technologique de financement immobilier privé (QC + ON)
- Frais Capital Norvex : 3 % à 3,5 % (prélevés au notaire/avocat)
- Rémunération courtier : jusqu'à 1,00 % maximum
- Fourchettes : 2,5 M$ à 100 M$, taux 10-12 %, durée 6-24 mois
- Processus : Score Norvex → LOI → Lettre d'engagement → Notaire → Déboursé
- Tagline : « Capital structuré. Ambition maîtrisée. »
- Adresse : 2705-1000 André-Prévost, Île-des-Sœurs (Verdun), Montréal, QC H3E 0G2
- Tél : 438-533-PRÊT (7738)
- Equipe : Suzanne Breton (Administratrice), Sophie (relations clients), Camille (juridique), Norah (téléphone)

## Garde-fous
- Aucune promesse de taux/montant exact sans LOI signée
- Pas de divulgation d'infos confidentielles d'autres dossiers
- Si juridique technique → renvoyer vers notaire/avocat ou Camille
- Si demande hors-scope ou ambiguë → demander clarification poliment

## Format de sortie — JSON STRICT
{
  "subject": "objet concis",
  "language": "fr" | "en",
  "body_html": "<p>Corps en HTML propre.</p>",
  "internal_note_for_yves": "rappel court pour toi-même Yves, ou null"
}

Pas de signature dans body_html (ajoutée auto). HTML propre : <p>, <ul>, <li>, <strong>, <em>, <br>. Pas de Markdown, pas de <html>/<body>, pas de style inline.

Réponds UNIQUEMENT avec le JSON.`;

// Signature Yves : voir _signature.mjs (charge le vrai logo PNG + signature
// manuscrite scannée en base64 inline). Bug fix 2026-05-08 : avant, ce fichier
// avait un clone local avec un fallback texte « M » au lieu du vrai logo.

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

function parseJsonOutput(raw) {
  let s = raw.trim();
  s = s.replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/\s*```$/i, "");
  return JSON.parse(s);
}

// ─── Firestore createDoc ──────────────────────────────────────────────────

async function createDoc(projectId, fsToken, collection, docId, fields) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collection}?documentId=${encodeURIComponent(
    docId
  )}`;
  const fsValue = (v) => {
    if (v === null || v === undefined) return { nullValue: null };
    if (typeof v === "string") return { stringValue: v };
    if (typeof v === "boolean") return { booleanValue: v };
    if (typeof v === "number")
      return Number.isInteger(v)
        ? { integerValue: String(v) }
        : { doubleValue: v };
    if (v instanceof Date) return { timestampValue: v.toISOString() };
    if (Array.isArray(v))
      return { arrayValue: { values: v.map(fsValue) } };
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
    language: forcedLang,
    ccRecipients = [],
    attachments: rawAttachments = [],
  } = body;

  // Validation attachments (optionnel, rétrocompatible)
  // Format attendu : [{ name: "file.pdf", contentBase64: "...", contentType: "application/pdf" }]
  // Max 5 attachments, max 4 MB chacun (limite payload Netlify Lambda 6 MB).
  if (rawAttachments && !Array.isArray(rawAttachments)) {
    return jsonResponse(
      { error: "attachments doit être un array" },
      400
    );
  }
  if (rawAttachments.length > 5) {
    return jsonResponse(
      { error: "Maximum 5 pièces jointes par draft" },
      400
    );
  }
  for (const a of rawAttachments) {
    if (!a || typeof a !== "object" || !a.name || !a.contentBase64) {
      return jsonResponse(
        { error: "Chaque attachment doit avoir { name, contentBase64, contentType }" },
        400
      );
    }
    const sizeBytes = Math.floor((a.contentBase64.length * 3) / 4);
    if (sizeBytes > 4 * 1024 * 1024) {
      return jsonResponse(
        { error: `Attachment ${a.name} dépasse 4 MB (limite Netlify Lambda)` },
        413
      );
    }
  }

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

  try {
    const sa = await loadServiceAccount();
    const projectId = sa.project_id;
    const fsToken = await getFirestoreToken(sa);

    const userMessage = `INSTRUCTION DU PATRON YVES :
${instruction}

CONTEXTE :
- Destinataire (si fourni) : ${recipient || "(à déduire de l'instruction si possible)"}
- Sujet imposé (si fourni) : ${forcedSubject || "(à générer)"}
- Langue imposée (si fournie) : ${forcedLang || "(détecte selon contexte)"}

Génère le courriel en JSON strict. Si l'info manque, mets une note dans internal_note_for_yves et propose le mieux possible — Yves pourra raffiner ensuite via le dashboard.`;

    const rawOutput = await callAnthropic(CREATE_GHOSTWRITER_PROMPT, userMessage);
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
      throw new Error("Béatrice n'a pas généré de corps HTML");
    }

    const signature = signatureYvesHtml(language);
    const signedHtml = bodyHtml + signature;

    const draftId = `outbound_${Date.now()}_${Math.random()
      .toString(36)
      .slice(2, 8)}`;

    // Upload des attachments vers Firebase Storage (si fournis)
    // Format stocké dans Firestore : [{ name, storagePath, contentType }]
    // sendEmailSmart() téléchargera depuis Storage au moment de l'envoi.
    const storedAttachments = [];
    if (rawAttachments.length > 0) {
      const bucketName =
        process.env.FIREBASE_STORAGE_BUCKET || `${projectId}-uploads`;
      const storageWriteToken = await getStorageWriteToken(sa);
      for (const a of rawAttachments) {
        const safeName = a.name.replace(/[^a-zA-Z0-9._-]/g, "_");
        const storagePath = `beatriceAttachments/${draftId}/${safeName}`;
        await uploadAttachmentToStorage({
          bucketName,
          storagePath,
          contentBase64: a.contentBase64,
          contentType: a.contentType || "application/octet-stream",
          storageWriteToken,
        });
        storedAttachments.push({
          name: a.name,
          storagePath,
          contentType: a.contentType || "application/octet-stream",
        });
      }
    }

    const draftDoc = {
      sourceMailbox: "yves@capitalnorvex.com",
      fromUser: "yves@capitalnorvex.com",
      toRecipient: recipient || "",
      ccRecipients: Array.isArray(ccRecipients) ? ccRecipients : [],
      subject,
      bodyHtml,
      signedHtml,
      language,
      status: "pending_yves_approval",
      createdAt: new Date(),
      createdBy: "Yves Barrette (command bar dashboard)",
      origin: "outbound_yves_initiated",
      initialInstruction: instruction.slice(0, 500),
      internalNoteForYves: note,
      attachments: storedAttachments,
      versions: [
        {
          version: 1,
          bodyHtml,
          signedHtml,
          instruction: instruction.slice(0, 500),
          createdAt: new Date().toISOString(),
          generatedBy: "beatrice-create-draft (Opus 4.6)",
        },
      ],
      currentVersion: 1,
    };

    await createDoc(projectId, fsToken, COLLECTION_DRAFTS, draftId, draftDoc);

    await createAuditLog(projectId, fsToken, {
      agent: "beatrice",
      action: "create_outbound_draft",
      targetType: COLLECTION_DRAFTS,
      targetId: draftId,
      result: "success",
      details: {
        recipient: recipient || "(none)",
        instruction: instruction.slice(0, 200),
      },
    });

    return jsonResponse({
      ok: true,
      draftId,
      subject,
      language,
      bodyHtml,
      signedHtml,
      sourceMailbox: "yves@capitalnorvex.com",
      internalNoteForYves: note,
    });
  } catch (e) {
    return jsonResponse(
      { error: e.message, where: "beatrice-create-draft" },
      500
    );
  }
}

export const config = {
  path: "/api/beatrice-create-draft",
};
