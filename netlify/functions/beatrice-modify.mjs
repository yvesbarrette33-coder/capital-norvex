/**
 * GET /api/beatrice-modify?draft=<id>&exp=<iso>&token=<hmac>
 *
 * Bouton "Modifier" dans la notif email → redirige vers le dashboard
 * Béatrice avec le draft déjà ouvert pour édition.
 *
 * On ne fait PAS d'action serveur ici — juste une redirection 302.
 * Le dashboard charge le draft, Yves modifie, puis approuve depuis là.
 */

import { verifyApprovalToken } from "./_camille-shared.mjs";

export default async function handler(req) {
  const url = new URL(req.url);
  const draftId = url.searchParams.get("draft");
  const exp = url.searchParams.get("exp");
  const token = url.searchParams.get("token");

  const v = verifyApprovalToken({
    draftId,
    action: "modify",
    expIso: exp,
    token,
  });
  if (!v.ok) {
    const html = `<!DOCTYPE html><html lang="fr"><head>
<meta charset="utf-8"><title>Lien invalide</title>
<style>body{font-family:-apple-system,sans-serif;max-width:600px;margin:60px auto;padding:0 24px}
h1{color:#C9A227}.err{color:#c33}a.btn{display:inline-block;background:#1a1a1a;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;margin-top:12px}</style>
</head><body>
<h1>Béatrice — NORVEX RELATIONS™</h1>
<p class="err">⛔ Ce lien de modification est invalide ou expiré.</p>
<p>Raison : ${v.error}</p>
<a class="btn" href="/beatrice-admin.html">Ouvrir le dashboard Béatrice</a>
</body></html>`;
    return new Response(html, {
      status: 401,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  }

  // Redirection vers le dashboard avec le draft pré-sélectionné
  const target = `/beatrice-admin.html?edit=${encodeURIComponent(draftId)}`;
  return new Response(null, {
    status: 302,
    headers: { Location: target },
  });
}

export const config = {
  path: "/api/beatrice-modify",
};
