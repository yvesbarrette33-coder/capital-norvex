/**
 * GET  /api/beatrice-reject?draft=<id>&exp=<iso>&token=<hmac>
 * POST /api/beatrice-reject  body: { draftId, reason? } + header X-Internal-Secret
 *
 * Rejette un draft Béatrice (sans envoyer). Audit trail complet.
 */

import {
  createAuditLog,
  getDoc,
  getFirestoreToken,
  htmlResponse,
  jsonResponse,
  loadServiceAccount,
  patchDoc,
  verifyApprovalToken,
} from "./_camille-shared.mjs";

const COLLECTION_DRAFTS = "beatriceDrafts";

async function rejectDraft(projectId, fsToken, draftId, reason = "") {
  const draft = await getDoc(projectId, fsToken, COLLECTION_DRAFTS, draftId);
  if (!draft) {
    return { ok: false, status: 404, message: "Draft introuvable" };
  }

  const status = draft.status;
  if (status === "sent") {
    return {
      ok: false,
      status: 409,
      message: `Déjà envoyé le ${draft.sentAt} — impossible de rejeter.`,
    };
  }
  if (status === "rejected") {
    return {
      ok: true,
      status: 200,
      message: `Déjà rejeté le ${draft.rejectedAt}.`,
      already: true,
    };
  }

  await patchDoc(projectId, fsToken, COLLECTION_DRAFTS, draftId, {
    status: "rejected",
    rejectedAt: new Date(),
    rejectedBy: "Yves Barrette (via lien email)",
    rejectionReason: reason || "(pas de raison fournie)",
  });
  await createAuditLog(projectId, fsToken, {
    agent: "beatrice",
    action: "reject_draft",
    targetType: COLLECTION_DRAFTS,
    targetId: draftId,
    result: "success",
    details: { reason, subject: draft.subject, toRecipient: draft.toRecipient },
  });

  return {
    ok: true,
    status: 200,
    message: "Draft rejeté",
    subject: draft.subject,
    toRecipient: draft.toRecipient,
  };
}

export default async function handler(req) {
  const url = new URL(req.url);
  const isPost = req.method === "POST";

  let draftId, exp, token, reason;

  if (isPost) {
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
    reason = body.reason || "";
  } else {
    draftId = url.searchParams.get("draft");
    exp = url.searchParams.get("exp");
    token = url.searchParams.get("token");
    reason = url.searchParams.get("reason") || "(rejeté via lien email)";
    const v = verifyApprovalToken({
      draftId,
      action: "reject",
      expIso: exp,
      token,
    });
    if (!v.ok) {
      return htmlResponse(
        "Lien invalide",
        `<p class="err">⛔ Ce lien de rejet est invalide ou expiré.</p>
         <p>Raison : ${v.error}</p>
         <a class="btn" href="/beatrice-admin.html">Ouvrir le dashboard Béatrice</a>`,
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

    const result = await rejectDraft(projectId, fsToken, draftId, reason);

    if (isPost) return jsonResponse(result, result.status);

    if (result.ok && result.already) {
      return htmlResponse(
        "Déjà rejeté",
        `<p>${result.message}</p>
         <a class="btn" href="/beatrice-admin.html">Ouvrir le dashboard Béatrice</a>`
      );
    }
    if (result.ok) {
      return htmlResponse(
        "❌ Draft rejeté",
        `<p><strong>${result.message}</strong></p>
         <p><strong>Objet :</strong> ${result.subject}<br>
            <strong>Destinataire :</strong> ${result.toRecipient}</p>
         <p>Aucun courriel n'a été envoyé. Le draft est archivé dans Firestore.</p>
         <a class="btn" href="/beatrice-admin.html">Ouvrir le dashboard Béatrice</a>`
      );
    }
    return htmlResponse(
      "Action impossible",
      `<p class="err">${result.message}</p>
       <a class="btn" href="/beatrice-admin.html">Dashboard</a>`,
      result.status
    );
  } catch (e) {
    return isPost
      ? jsonResponse({ error: e.message }, 500)
      : htmlResponse("Erreur serveur", `<p class="err">${e.message}</p>`, 500);
  }
}

export const config = {
  path: "/api/beatrice-reject",
};
