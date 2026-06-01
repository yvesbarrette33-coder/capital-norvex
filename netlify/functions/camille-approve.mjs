/**
 * GET  /api/camille-approve?draft=<id>&exp=<iso>&token=<hmac>
 * POST /api/camille-approve  body: { draftId } + header X-Internal-Secret
 *
 * Approuve un draft Camille et l'envoie immédiatement via Microsoft Graph
 * (CC = Yves selon config).
 *
 * Mode 1 (lien email) : Yves clique le bouton ✅ Approuver dans la notif email.
 *                       Token HMAC valide → action exécutée → page de confirmation.
 * Mode 2 (dashboard)  : POST authentifié depuis le dashboard /camille-admin.
 */

import {
  buildApprovalUrl,
  buildGraphAttachments,
  createAuditLog,
  getDoc,
  getFirestoreToken,
  htmlResponse,
  jsonResponse,
  loadServiceAccount,
  patchDoc,
  sendEmailSmart,
  verifyApprovalToken,
} from "./_camille-shared.mjs";

const COLLECTION_DRAFTS = "camilleDrafts";

async function approveAndSend(projectId, fsToken, draftId) {
  const draft = await getDoc(projectId, fsToken, COLLECTION_DRAFTS, draftId);
  if (!draft) {
    return { ok: false, status: 404, message: "Draft introuvable" };
  }

  const status = draft.status;
  if (status === "sent") {
    return {
      ok: false,
      status: 409,
      message: `Déjà envoyé le ${draft.sentAt}.`,
    };
  }
  if (status === "rejected") {
    return {
      ok: false,
      status: 409,
      message: `Draft a été rejeté le ${draft.rejectedAt} — impossible d'approuver.`,
    };
  }
  if (status !== "pending_yves_approval" && status !== "approved") {
    return {
      ok: false,
      status: 409,
      message: `Status inattendu : ${status}`,
    };
  }

  const fromUser = draft.sourceMailbox || draft.fromUser;
  const toRecipient = draft.toRecipient;
  const subject = draft.subject;
  const html = draft.signedHtml || draft.bodyHtml;
  const cc = draft.ccRecipients || [];

  if (!fromUser || !toRecipient || !html || !subject) {
    return {
      ok: false,
      status: 400,
      message: "Draft incomplet (from/to/subject/html manquant)",
    };
  }

  // Marque approuvé AVANT envoi (audit trail clean)
  await patchDoc(projectId, fsToken, COLLECTION_DRAFTS, draftId, {
    status: "approved",
    approvedAt: new Date(),
    approvedBy: "Yves Barrette (via lien email)",
  });

  // Construit les pièces jointes éventuelles (depuis Firebase Storage)
  let graphAttachments = [];
  try {
    const sa = await loadServiceAccount();
    graphAttachments = await buildGraphAttachments({
      attachments: draft.attachments || [],
      sa,
    });
  } catch (e) {
    // En cas d'échec download attachment, on log et on continue sans
    // (Yves préfère un envoi sans pièce jointe à un blocage complet —
    // il pourra renvoyer manuellement le PDF s'il le faut).
    console.error("buildGraphAttachments failed:", e.message);
  }

  // Microsoft Graph obligatoire pour communications individuelles clients
  // (règle 2026-05-28 — saveToSentItems=true + fiabilité livraison externe).
  const result = await sendEmailSmart({
    to: toRecipient,
    cc,
    subject,
    html,
    fromUser,
    attachments: graphAttachments,
    forceGraph: true,
  });

  if (!result.ok) {
    await patchDoc(projectId, fsToken, COLLECTION_DRAFTS, draftId, {
      status: "send_failed",
      sendError: result.error,
      sendFailedAt: new Date(),
    });
    await createAuditLog(projectId, fsToken, {
      agent: "camille",
      action: "approve_send_failed",
      targetType: COLLECTION_DRAFTS,
      targetId: draftId,
      result: "error",
      details: { error: result.error, fromUser, toRecipient },
    });
    return {
      ok: false,
      status: 502,
      message: "Approuvé mais envoi échoué : " + result.error,
    };
  }

  // Marque envoyé
  await patchDoc(projectId, fsToken, COLLECTION_DRAFTS, draftId, {
    status: "sent",
    sentAt: new Date(),
    sentVia: result.via,
  });
  await createAuditLog(projectId, fsToken, {
    agent: "camille",
    action: "approve_and_send",
    targetType: COLLECTION_DRAFTS,
    targetId: draftId,
    result: "success",
    details: { fromUser, toRecipient, subject, via: result.via },
  });

  return {
    ok: true,
    status: 200,
    message: "Draft approuvé et envoyé",
    fromUser,
    toRecipient,
    subject,
  };
}

export default async function handler(req) {
  const url = new URL(req.url);
  const isPost = req.method === "POST";

  let draftId, exp, token;

  if (isPost) {
    // Mode dashboard : vérification INTERNAL_SECRET
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
    draftId = body.draftId;
  } else {
    // Mode lien email : vérification HMAC
    draftId = url.searchParams.get("draft");
    exp = url.searchParams.get("exp");
    token = url.searchParams.get("token");
    const v = verifyApprovalToken({
      draftId,
      action: "approve",
      expIso: exp,
      token,
    });
    if (!v.ok) {
      return htmlResponse(
        "Lien invalide",
        `<p class="err">⛔ Ce lien d'approbation est invalide ou expiré.</p>
         <p>Raison : ${v.error}</p>
         <p>Va sur le dashboard pour approuver manuellement :</p>
         <a class="btn" href="/camille-admin.html">Ouvrir le dashboard Camille</a>`,
        401
      );
    }
  }

  if (!draftId) {
    if (isPost) return jsonResponse({ error: "draftId required" }, 400);
    return htmlResponse("Erreur", `<p class="err">draftId manquant</p>`, 400);
  }

  try {
    const sa = await loadServiceAccount();
    const projectId = sa.project_id;
    const fsToken = await getFirestoreToken(sa);

    const result = await approveAndSend(projectId, fsToken, draftId);

    if (isPost) {
      return jsonResponse(result, result.status);
    }

    if (result.ok) {
      return htmlResponse(
        "✅ Approuvé et envoyé",
        `<p class="ok"><strong>${result.message}</strong></p>
         <p><strong>De :</strong> ${result.fromUser}<br>
            <strong>À :</strong> ${result.toRecipient}<br>
            <strong>Objet :</strong> ${result.subject}</p>
         <p>Yves est en CC. Le destinataire vient de recevoir le courriel.</p>
         <a class="btn" href="/camille-admin.html">Ouvrir le dashboard Camille</a>`,
        200
      );
    }

    return htmlResponse(
      "Action impossible",
      `<p class="err">${result.message}</p>
       <a class="btn" href="/camille-admin.html">Ouvrir le dashboard Camille</a>`,
      result.status
    );
  } catch (e) {
    return isPost
      ? jsonResponse({ error: e.message }, 500)
      : htmlResponse(
          "Erreur serveur",
          `<p class="err">Erreur : ${e.message}</p>
           <a class="btn" href="/camille-admin.html">Dashboard Camille</a>`,
          500
        );
  }
}

export const config = {
  path: "/api/camille-approve",
};
