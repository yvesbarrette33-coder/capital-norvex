/**
 * POST /api/espace-courtier-magic-link
 * Body : { email: string }
 *
 * Vérifie qu'un broker accrédité existe avec cet email.
 * Si oui : génère un magic token (TTL 15 min) + envoie un courriel avec lien.
 * Si non : retourne 404 (sans révéler si l'email existe ailleurs).
 */

import {
  json,
  makeToken,
  findBrokerByEmail,
  sendMagicLinkEmail,
} from "./_espace-courtier-shared.mjs";

const SITE_URL = "https://capitalnorvex.com";
const TOKEN_TTL_MINUTES = 15;

export default async (req) => {
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  let body;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON body" }, 400);
  }

  const email = (body.email || "").trim().toLowerCase();
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return json({ error: "Invalid email" }, 400);
  }

  const secret = process.env.INTERNAL_SECRET;
  if (!secret) return json({ error: "Server misconfigured: INTERNAL_SECRET missing" }, 500);

  // 1. Vérifier qu'un broker accrédité existe
  let broker;
  try {
    broker = await findBrokerByEmail(email);
  } catch (err) {
    return json({ error: "Lookup failed: " + err.message }, 500);
  }
  if (!broker) {
    // Réponse 404 sans révéler de détails
    return json({ error: "No accredited broker found for this email" }, 404);
  }

  // 2. Générer le magic token (type = "magic", TTL 15 min)
  const exp = Date.now() + TOKEN_TTL_MINUTES * 60 * 1000;
  const magicToken = await makeToken(secret, {
    type: "magic",
    brokerId: broker.id,
    email: broker.email,
    exp,
  });

  const magicUrl = `${SITE_URL}/espace-courtier.html?mt=${encodeURIComponent(magicToken)}`;

  // 3. Envoyer le courriel
  try {
    await sendMagicLinkEmail({
      to: broker.email,
      name: broker.name || broker.fullName,
      magicUrl,
      expiresInMinutes: TOKEN_TTL_MINUTES,
    });
  } catch (err) {
    return json({ error: "Email send failed: " + err.message }, 500);
  }

  return json({
    ok: true,
    message: "Magic link sent",
    expiresIn: TOKEN_TTL_MINUTES * 60,
  });
};

export const config = { path: "/api/espace-courtier-magic-link" };
