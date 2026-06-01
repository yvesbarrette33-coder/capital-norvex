/**
 * POST /api/espace-courtier-verify-token
 * Body : { token: string } (magic token reçu par email)
 *
 * Vérifie le magic token, charge le broker, retourne :
 *   { ok:true, sessionToken: "...", broker: {...} }
 *
 * Le sessionToken sert ensuite pour authentifier les calls API.
 * Durée du sessionToken : 7 jours.
 */

import {
  json,
  verifyToken,
  makeToken,
  getBrokerById,
} from "./_espace-courtier-shared.mjs";

const SESSION_TTL_DAYS = 7;

export default async (req) => {
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  let body;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON body" }, 400);
  }

  const magicToken = body.token;
  if (!magicToken || typeof magicToken !== "string") {
    return json({ error: "Missing token" }, 400);
  }

  const secret = process.env.INTERNAL_SECRET;
  if (!secret) return json({ error: "Server misconfigured" }, 500);

  // 1. Vérifier le magic token
  const result = await verifyToken(magicToken, secret);
  if (!result.ok) {
    return json({ error: "Invalid or expired token", reason: result.reason }, 401);
  }
  const payload = result.payload;
  if (payload.type !== "magic") {
    return json({ error: "Wrong token type" }, 401);
  }
  if (!payload.brokerId) {
    return json({ error: "Token missing brokerId" }, 401);
  }

  // 2. Recharger le broker depuis Firestore (au cas où l'état aurait changé)
  let broker;
  try {
    broker = await getBrokerById(payload.brokerId);
  } catch (err) {
    return json({ error: "Broker lookup failed: " + err.message }, 500);
  }
  if (!broker) {
    return json({ error: "Broker not found" }, 404);
  }
  // Accepter status OU relationshipStatus = active_partner (cohérent avec
  // findBrokerByEmail — le workflow d'approbation met à jour relationshipStatus).
  const s = (broker.status || "").toLowerCase();
  const rs = (broker.relationshipStatus || "").toLowerCase();
  const isAccredited =
    s === "active_partner" ||
    rs === "active_partner" ||
    rs === "active" ||
    rs === "cold";
  if (!isAccredited) {
    return json({ error: "Broker not accredited" }, 403);
  }

  // 3. Générer le sessionToken (TTL 7 jours)
  const exp = Date.now() + SESSION_TTL_DAYS * 24 * 3600 * 1000;
  const sessionToken = await makeToken(secret, {
    type: "session",
    brokerId: broker.id,
    email: broker.email,
    exp,
  });

  // 4. Retourner les infos utiles du broker (pas tout)
  const safeBroker = {
    id: broker.id,
    name: broker.name || broker.fullName || "",
    email: broker.email,
    phone: broker.phone || "",
    agency: broker.agency || broker.firmName || "",
    province: broker.province || "",
    code: broker.brokerNumber || broker.code || broker.id,
    accreditedAt: broker.activatedAt || broker.approvedAt || broker.createdAt || null,
    conventionUrl: broker.conventionUrl || null,
  };

  return json({
    ok: true,
    sessionToken,
    broker: safeBroker,
    expiresInDays: SESSION_TTL_DAYS,
  });
};

export const config = { path: "/api/espace-courtier-verify-token" };
