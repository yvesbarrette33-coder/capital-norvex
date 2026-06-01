/**
 * POST /.netlify/functions/norah-verify-identity
 * Header: X-Internal-Secret
 * Body JSON: { caller_phone: "+15145551234", role_hint: "client|courtier|partenaire|yves" }
 *
 * Tool ElevenLabs #1 — verify_caller_identity
 *
 * Étapes:
 *   1. Normalise le numéro de téléphone
 *   2. Selon le rôle déclaré, cherche l'appelant dans la bonne collection Firebase:
 *      - "courtier"   → collection `brokers` (doit avoir `accredite=true` ou `status=approved`)
 *      - "partenaire" → collection `partenaires` (VIP co-prêteurs)
 *      - "yves"       → vérifie que phone == YVES_VIP_PHONE
 *      - "client"     → toujours autorisé (identification finale via le numéro de dossier après 2FA)
 *   3. Si l'identité est valide, envoie un code 2FA via Twilio Verify (SMS)
 *   4. Retourne le résultat à ElevenLabs (identified true/false, raison, prénom pour personnaliser)
 *
 * Réponses:
 *   200 { identified: true, role, display_name, sms_sent: true }
 *   200 { identified: false, reason: "non_accredite" | "non_partenaire" | "phone_mismatch_yves" }
 *   400 { error: "..." }
 *   401 { error: "Unauthorized" }
 *   500 { error: "..." }
 */

import {
  json,
  unauthorized,
  badRequest,
  serverError,
  checkInternalSecret,
  firestoreFindOne,
  twilioSendVerification,
  normalizePhone,
  YVES_VIP_PHONE,
} from "./_norah-shared.mjs";

export default async (req) => {
  if (req.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405 });
  }

  if (!checkInternalSecret(req)) return unauthorized();

  let body;
  try {
    body = await req.json();
  } catch {
    return badRequest("Invalid JSON body");
  }

  const phone = normalizePhone(body.caller_phone);
  const roleHint = (body.role_hint || "").toLowerCase().trim();

  if (!phone) return badRequest("caller_phone manquant ou invalide");
  if (!["client", "courtier", "partenaire", "yves"].includes(roleHint)) {
    return badRequest(`role_hint invalide: ${roleHint}`);
  }

  // ───── Routage par rôle ─────────────────────────────────────────────────

  let identified = false;
  let role = roleHint;
  let displayName = null;
  let reason = null;

  try {
    if (roleHint === "yves") {
      // Yves: doit appeler depuis son cellulaire VIP
      if (phone === YVES_VIP_PHONE) {
        identified = true;
        displayName = "Yves Barrette";
      } else {
        reason = "phone_mismatch_yves";
      }
    } else if (roleHint === "courtier") {
      const broker = await firestoreFindOne("brokers", "phone", phone);
      // Tolérance: certains schémas utilisent `tel` au lieu de `phone`
      const fallback = broker || (await firestoreFindOne("brokers", "tel", phone));
      const found = broker || fallback;

      if (!found) {
        reason = "non_accredite";
      } else {
        // Critère d'accréditation: champ `accredite=true` OU `status=approved`
        const isAccredited =
          found.accredite === true ||
          found.status === "approved" ||
          found.status === "active" ||
          found.status === "active_partner";

        if (!isAccredited) {
          reason = "non_accredite";
        } else {
          identified = true;
          displayName =
            found.displayName ||
            found.fullName ||
            [found.prenom, found.nom].filter(Boolean).join(" ") ||
            "Courtier";
        }
      }
    } else if (roleHint === "partenaire") {
      const partner = await firestoreFindOne("partenaires", "phone", phone);
      if (!partner) {
        reason = "non_partenaire";
      } else {
        identified = true;
        displayName =
          partner.displayName ||
          partner.fullName ||
          [partner.prenom, partner.nom].filter(Boolean).join(" ") ||
          "Partenaire";
      }
    } else if (roleHint === "client") {
      // Pour les clients: on autorise toujours le 2FA. L'identification finale
      // se fera via le numéro de dossier après validation du code.
      identified = true;
      displayName = "Client";
    }
  } catch (e) {
    return serverError("Identity lookup failed: " + e.message);
  }

  // Si non-identifié, on ne déclenche PAS de SMS (économie + sécurité)
  if (!identified) {
    return json({
      identified: false,
      role,
      reason,
      sms_sent: false,
    });
  }

  // ───── Envoi du code 2FA via Twilio Verify ──────────────────────────────

  let smsResult;
  try {
    smsResult = await twilioSendVerification(phone);
  } catch (e) {
    return serverError("Twilio Verify error: " + e.message);
  }

  if (!smsResult.success) {
    return json({
      identified: true,
      role,
      display_name: displayName,
      sms_sent: false,
      sms_error: smsResult.error,
    });
  }

  return json({
    identified: true,
    role,
    display_name: displayName,
    sms_sent: true,
    verify_status: smsResult.status, // "pending" en général
  });
};
