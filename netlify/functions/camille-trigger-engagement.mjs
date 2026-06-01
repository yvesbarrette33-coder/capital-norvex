/**
 * POST /api/camille-trigger-engagement
 * Header: X-Internal-Secret
 * Body  : { dossierId }
 *
 * Bouton « 📧 Envoyer lettre d'engagement (Camille) » dans le Pipeline.
 * Met un flag Firestore `engagementLetterRequested=true` sur le dossier.
 * Le cron Camille local (Python) détecte le flag et envoie la lettre dans la
 * prochaine ronde (10 min).
 *
 * NE TOUCHE PAS au workflow Score Norvex / agent_docs.py (règle Yves 2026-05-04).
 */

import {
  createAuditLog,
  getDoc,
  getFirestoreToken,
  jsonResponse,
  loadServiceAccount,
  patchDoc,
  sendViaGraph,
} from "./_camille-shared.mjs";

const COLLECTION = "dossiers";
const YVES_NOTIF = "yves@capitalnorvex.com";

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

  const dossierId = body.dossierId;
  if (!dossierId) {
    return jsonResponse({ error: "dossierId required" }, 400);
  }

  try {
    const sa = await loadServiceAccount();
    const projectId = sa.project_id;
    const fsToken = await getFirestoreToken(sa);

    const dossier = await getDoc(projectId, fsToken, COLLECTION, dossierId);
    if (!dossier) {
      return jsonResponse({ error: "Dossier introuvable" }, 404);
    }
    if (dossier.engagementSentAt) {
      return jsonResponse(
        {
          error: `Lettre d'engagement déjà envoyée le ${dossier.engagementSentAt}.`,
          alreadySent: true,
          sentAt: dossier.engagementSentAt,
        },
        409
      );
    }

    // Set flag → Camille (Python cron 10 min) le détecte et envoie
    await patchDoc(projectId, fsToken, COLLECTION, dossierId, {
      engagementLetterRequested: true,
      engagementRequestedAt: new Date(),
      engagementRequestedBy: "Yves Barrette (via Pipeline)",
    });

    await createAuditLog(projectId, fsToken, {
      agent: "pipeline-ui",
      action: "request_engagement_letter",
      targetType: COLLECTION,
      targetId: dossierId,
      result: "success",
      details: {
        type: dossier.type,
        clientEmail: dossier.email,
        clientName: `${dossier.prenom || ""} ${dossier.nom || ""}`.trim(),
      },
    });

    // Notif info Yves : "Camille va envoyer dans 10 min"
    const clientName = `${dossier.prenom || ""} ${dossier.nom || ""}`.trim() || "Client";
    const notifBody = `<!DOCTYPE html><html lang="fr"><body style="font-family:-apple-system,sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#1a1a1a">
<div style="background:linear-gradient(135deg,#1a1a1a 0%,#2a2a2a 100%);color:white;padding:24px;border-radius:12px 12px 0 0">
  <div style="font-size:12px;letter-spacing:2px;color:#C9A227;font-weight:600">CAMILLE — NORVEX COUNSEL™</div>
  <div style="font-size:22px;font-family:'Playfair Display',Georgia,serif;margin-top:4px">Demande d'envoi enregistrée</div>
</div>
<div style="background:#fafafa;padding:24px;border:1px solid #e5e5e7;border-top:none;border-radius:0 0 12px 12px">
<p>Tu as demandé l'envoi de la <strong>lettre d'engagement</strong> pour le dossier suivant :</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
  <tr><td style="padding:6px 0;color:#666;font-size:13px">Dossier</td><td style="padding:6px 0;font-family:monospace"><strong>${dossierId}</strong></td></tr>
  <tr><td style="padding:6px 0;color:#666;font-size:13px">Client</td><td style="padding:6px 0">${clientName}</td></tr>
  <tr><td style="padding:6px 0;color:#666;font-size:13px">Type</td><td style="padding:6px 0">${dossier.type || "?"}</td></tr>
  <tr><td style="padding:6px 0;color:#666;font-size:13px">Email destinataire</td><td style="padding:6px 0;font-family:monospace">${dossier.email || "?"}</td></tr>
</table>
<p>Camille s'en occupe à la prochaine ronde (10 min max). Tu seras en CC du courriel sortant.</p>
<p style="color:#777;font-size:12px;margin-top:24px">Si tu veux annuler : ouvre le Pipeline et change le stage du dossier.</p>
</div></body></html>`;

    await sendViaGraph({
      to: YVES_NOTIF,
      subject: `[Camille] Demande d'envoi enregistrée — ${dossierId}`,
      html: notifBody,
      fromUser: YVES_NOTIF,
    });

    return jsonResponse({
      ok: true,
      dossierId,
      message: "Demande enregistrée. Camille enverra la lettre dans les 10 prochaines minutes.",
      clientEmail: dossier.email,
      type: dossier.type,
    });
  } catch (e) {
    return jsonResponse({ error: e.message }, 500);
  }
}

export const config = {
  path: "/api/camille-trigger-engagement",
};
