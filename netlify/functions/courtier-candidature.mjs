/**
 * POST /.netlify/functions/courtier-candidature
 *
 * Reçoit une candidature courtier soumise depuis /courtier-candidature.html.
 *
 * Actions :
 *   1. Valide les champs requis du formulaire
 *   2. Crée un document Firestore : brokerApplications/{id} (status="pending_review")
 *   3. Envoie email confirmation au courtier (SendGrid, en français ou anglais)
 *   4. Notifie Yves par email (résumé de la candidature)
 *   5. Retourne 200 + applicationId
 *
 * Aucune authentification : c'est un formulaire public.
 * Rate limiting basique par IP via headers (à durcir si abus).
 */

const ORGANIZER_EMAIL = "yves@capitalnorvex.com";
const ORGANIZER_NAME = "Capital Norvex";
const NOTIFY_EMAIL = process.env.INTERNAL_NOTIFY_EMAIL || ORGANIZER_EMAIL;

// ── Firestore JWT (même pattern que confirm-rdv.mjs) ─────────────────────
async function getFirestoreToken(sa) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: sa.client_email,
    sub: sa.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
    scope: "https://www.googleapis.com/auth/datastore",
  };
  const b64 = (obj) =>
    btoa(JSON.stringify(obj))
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");
  const signingInput = `${b64(header)}.${b64(payload)}`;
  const pemBody = sa.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\n/g, "");
  const keyData = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));
  const privateKey = await crypto.subtle.importKey(
    "pkcs8",
    keyData.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    privateKey,
    new TextEncoder().encode(signingInput)
  );
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
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
  if (!data.access_token) {
    throw new Error("Firestore token failed: " + JSON.stringify(data));
  }
  return data.access_token;
}

// ── Conversion JS objet → Firestore "fields" ─────────────────────────────
function toFsValue(v) {
  if (v === null || v === undefined) return { nullValue: null };
  if (typeof v === "boolean") return { booleanValue: v };
  if (typeof v === "number") {
    return Number.isInteger(v)
      ? { integerValue: String(v) }
      : { doubleValue: v };
  }
  if (typeof v === "string") return { stringValue: v };
  if (Array.isArray(v)) {
    return {
      arrayValue: { values: v.map(toFsValue) },
    };
  }
  if (typeof v === "object") {
    const fields = {};
    for (const [k, val] of Object.entries(v)) fields[k] = toFsValue(val);
    return { mapValue: { fields } };
  }
  return { stringValue: String(v) };
}

function objToFsFields(obj) {
  const fields = {};
  for (const [k, v] of Object.entries(obj)) fields[k] = toFsValue(v);
  return fields;
}

// ── Email helpers ────────────────────────────────────────────────────────
async function sendGridEmail({ to, subject, html, replyTo }) {
  const sgKey = process.env.SENDGRID_API_KEY;
  if (!sgKey) return { ok: false, error: "SENDGRID_API_KEY not set" };
  try {
    const r = await fetch("https://api.sendgrid.com/v3/mail/send", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${sgKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        personalizations: [{ to: [{ email: to }] }],
        from: { email: ORGANIZER_EMAIL, name: ORGANIZER_NAME },
        reply_to: replyTo
          ? { email: replyTo }
          : { email: ORGANIZER_EMAIL, name: ORGANIZER_NAME },
        subject,
        content: [{ type: "text/html", value: html }],
        headers: {
          "X-Capital-Norvex-Type": "courtier-candidature",
          "X-Auto-Response-Suppress": "All",
        },
        tracking_settings: {
          click_tracking: { enable: false, enable_text: false },
          open_tracking: { enable: false },
        },
      }),
    });
    if (r.ok || r.status === 202) return { ok: true };
    const txt = await r.text();
    return { ok: false, error: `SendGrid ${r.status}: ${txt.slice(0, 200)}` };
  } catch (e) {
    return { ok: false, error: "SendGrid exception: " + e.message };
  }
}

function emailToBroker({ fullName, lang }) {
  const isEn = lang === "en";
  // Premier prénom seulement (élégance + chaleureux)
  const firstName = (fullName || "").trim().split(/\s+/)[0] || (isEn ? "there" : "");
  if (isEn) {
    return {
      subject: "🤝 Welcome — Capital Norvex Partner Broker Program",
      html: `<!DOCTYPE html><html><body style="margin:0;padding:0;background:#FBF7EB;font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#0A0A0A;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#FBF7EB;padding:24px 12px;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="max-width:620px;width:100%;background:#FFFFFF;border-radius:2px;box-shadow:0 2px 18px rgba(0,0,0,0.05);">

<!-- HEADER -->
<tr><td style="background:#0A0A0A;padding:32px 24px;text-align:center;">
<div style="color:#C8B070;font-family:'Playfair Display',Georgia,serif;font-size:26px;letter-spacing:4px;font-weight:400;">CAPITAL NORVEX</div>
<div style="color:#C8B070;font-style:italic;font-size:11.5px;letter-spacing:2px;margin-top:10px;opacity:0.78;">Structured capital. Measured ambition.</div>
</td></tr>
<tr><td style="height:3px;background:linear-gradient(90deg,transparent 0%,#C8B070 50%,transparent 100%);"></td></tr>

<!-- HERO -->
<tr><td style="padding:36px 40px 18px;">
<div style="font-size:10.5px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">Partner broker program · Welcome</div>
<h1 style="font-family:'Playfair Display',Georgia,serif;font-size:28px;line-height:1.25;font-weight:400;color:#0A0A0A;margin:0 0 8px;">Welcome, ${firstName}.</h1>
<p style="font-family:Georgia,serif;font-size:15px;color:#3a3a3a;line-height:1.7;margin:14px 0 0;">Your accreditation request has been received and is now in our hands.</p>
</td></tr>

<!-- COMMITMENT BLOCK -->
<tr><td style="padding:8px 40px 24px;">
<div style="background:#FCF8EE;border-left:3px solid #C8B070;padding:18px 22px;margin-top:10px;">
<div style="font-size:10px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">Our commitment to you</div>
<div style="font-family:'Playfair Display',Georgia,serif;font-size:19px;color:#0A0A0A;line-height:1.4;margin-bottom:14px;">
You keep 100 % control over your client relationship.
</div>
<div style="font-size:13.5px;color:#3a3a3a;line-height:1.7;">
You remain <strong>at the center</strong> of every communication with your client. The LOI is sent to your client with you in copy. At every meeting &mdash; typically before final signing &mdash; <strong>you are present</strong>. It's your client, your relationship, your advisor role. We work in partnership with you.
</div>
</div>
</td></tr>

<!-- NEXT STEPS -->
<tr><td style="padding:8px 40px 24px;">
<div style="font-size:10px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:14px;">What happens next</div>
<table cellpadding="0" cellspacing="0" style="width:100%;font-size:13.5px;color:#3a3a3a;">
<tr><td style="padding:8px 0;vertical-align:top;width:30px;"><span style="display:inline-block;width:22px;height:22px;background:#0A0A0A;color:#C8B070;border-radius:11px;text-align:center;line-height:22px;font-size:12px;font-weight:600;">1</span></td><td style="padding:8px 0 8px 10px;line-height:1.65;">Capital Norvex management reviews your file within <strong>24 business hours</strong>.</td></tr>
<tr><td style="padding:8px 0;vertical-align:top;"><span style="display:inline-block;width:22px;height:22px;background:#0A0A0A;color:#C8B070;border-radius:11px;text-align:center;line-height:22px;font-size:12px;font-weight:600;">2</span></td><td style="padding:8px 0 8px 10px;line-height:1.65;">You receive a personal email with our decision &mdash; and, if accredited, your unique broker code along with access to your personal Broker Workspace.</td></tr>
<tr><td style="padding:8px 0;vertical-align:top;"><span style="display:inline-block;width:22px;height:22px;background:#0A0A0A;color:#C8B070;border-radius:11px;text-align:center;line-height:22px;font-size:12px;font-weight:600;">3</span></td><td style="padding:8px 0 8px 10px;line-height:1.65;">From there, you submit your clients' files in a few clicks. We power the financing engine. You keep the relationship.</td></tr>
</table>
</td></tr>

<!-- SIGN -->
<tr><td style="padding:24px 40px 40px;font-size:14px;line-height:1.7;color:#3a3a3a;">
<p style="margin:0 0 16px;">In the meantime, if you have any questions, feel free to reply directly to this email.</p>
<p style="margin:24px 0 0;">Warmly,</p>
<p style="margin:8px 0 0;"><strong style="color:#0A0A0A;">The Capital Norvex Team</strong><br><em style="color:#9A8554;font-size:12.5px;letter-spacing:0.5px;">Partner Broker Program</em><br><span style="color:#888;font-size:12px;">Capital Norvex Inc.</span></p>
</td></tr>

<!-- FOOTER -->
<tr><td style="background:#0A0A0A;padding:18px;text-align:center;color:#C8B070;font-size:11px;letter-spacing:1.2px;">
<a href="https://capitalnorvex.com" style="color:#C8B070;text-decoration:none;">capitalnorvex.com</a>
</td></tr>

</table>
</td></tr></table>
<div style="margin-top:6px;padding:14px 16px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:10.5px;color:#64748b;line-height:1.55;letter-spacing:.3px;text-align:center;">
<strong style="color:#0f172a;font-size:11.5px;letter-spacing:1px;">CAPITAL NORVEX INC.</strong><br>
2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
</div>
</body></html>`,
    };
  }
  return {
    subject: "🤝 Bienvenue — Programme Courtier Partenaire Capital Norvex",
    html: `<!DOCTYPE html><html><body style="margin:0;padding:0;background:#FBF7EB;font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#0A0A0A;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#FBF7EB;padding:24px 12px;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="max-width:620px;width:100%;background:#FFFFFF;border-radius:2px;box-shadow:0 2px 18px rgba(0,0,0,0.05);">

<!-- HEADER -->
<tr><td style="background:#0A0A0A;padding:32px 24px;text-align:center;">
<div style="color:#C8B070;font-family:'Playfair Display',Georgia,serif;font-size:26px;letter-spacing:4px;font-weight:400;">CAPITAL NORVEX</div>
<div style="color:#C8B070;font-style:italic;font-size:11.5px;letter-spacing:2px;margin-top:10px;opacity:0.78;">Capital structuré. Ambition maîtrisée.</div>
</td></tr>
<tr><td style="height:3px;background:linear-gradient(90deg,transparent 0%,#C8B070 50%,transparent 100%);"></td></tr>

<!-- HERO -->
<tr><td style="padding:36px 40px 18px;">
<div style="font-size:10.5px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">Programme courtier partenaire · Bienvenue</div>
<h1 style="font-family:'Playfair Display',Georgia,serif;font-size:28px;line-height:1.25;font-weight:400;color:#0A0A0A;margin:0 0 8px;">Bienvenue, ${firstName}.</h1>
<p style="font-family:Georgia,serif;font-size:15px;color:#3a3a3a;line-height:1.7;margin:14px 0 0;">Votre demande d'accréditation est entre nos mains.</p>
</td></tr>

<!-- COMMITMENT BLOCK -->
<tr><td style="padding:8px 40px 24px;">
<div style="background:#FCF8EE;border-left:3px solid #C8B070;padding:18px 22px;margin-top:10px;">
<div style="font-size:10px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:10px;">Notre engagement envers vous</div>
<div style="font-family:'Playfair Display',Georgia,serif;font-size:19px;color:#0A0A0A;line-height:1.4;margin-bottom:14px;">
Vous gardez 100 % le contrôle de votre relation client.
</div>
<div style="font-size:13.5px;color:#3a3a3a;line-height:1.7;">
Vous restez <strong>au centre</strong> de chaque communication avec votre client. La LOI est envoyée à votre client avec vous en copie. À chaque rencontre &mdash; typiquement avant signature finale &mdash; <strong>vous êtes présent</strong>. C'est votre client, votre relation, votre rôle de conseiller. Nous travaillons en partenariat avec vous.
</div>
</div>
</td></tr>

<!-- NEXT STEPS -->
<tr><td style="padding:8px 40px 24px;">
<div style="font-size:10px;letter-spacing:2.5px;color:#9A8554;text-transform:uppercase;margin-bottom:14px;">Prochaines étapes</div>
<table cellpadding="0" cellspacing="0" style="width:100%;font-size:13.5px;color:#3a3a3a;">
<tr><td style="padding:8px 0;vertical-align:top;width:30px;"><span style="display:inline-block;width:22px;height:22px;background:#0A0A0A;color:#C8B070;border-radius:11px;text-align:center;line-height:22px;font-size:12px;font-weight:600;">1</span></td><td style="padding:8px 0 8px 10px;line-height:1.65;">La direction de Capital Norvex examine votre dossier sous <strong>24 h ouvrables</strong>.</td></tr>
<tr><td style="padding:8px 0;vertical-align:top;"><span style="display:inline-block;width:22px;height:22px;background:#0A0A0A;color:#C8B070;border-radius:11px;text-align:center;line-height:22px;font-size:12px;font-weight:600;">2</span></td><td style="padding:8px 0 8px 10px;line-height:1.65;">Vous recevez un courriel personnel avec notre décision &mdash; et, si accrédité, votre code courtier unique ainsi que l'accès à votre Espace Courtier personnel.</td></tr>
<tr><td style="padding:8px 0;vertical-align:top;"><span style="display:inline-block;width:22px;height:22px;background:#0A0A0A;color:#C8B070;border-radius:11px;text-align:center;line-height:22px;font-size:12px;font-weight:600;">3</span></td><td style="padding:8px 0 8px 10px;line-height:1.65;">Ensuite, vous soumettez les dossiers de vos clients en quelques clics. Nous, on est le moteur de financement. Vous, vous gardez la relation.</td></tr>
</table>
</td></tr>

<!-- SIGN -->
<tr><td style="padding:24px 40px 40px;font-size:14px;line-height:1.7;color:#3a3a3a;">
<p style="margin:0 0 16px;">D'ici là, si vous avez des questions, n'hésitez pas à répondre directement à ce courriel.</p>
<p style="margin:24px 0 0;">Avec considération,</p>
<p style="margin:8px 0 0;"><strong style="color:#0A0A0A;">L&#x27;équipe Capital Norvex</strong><br><em style="color:#9A8554;font-size:12.5px;letter-spacing:0.5px;">Programme courtier partenaire</em><br><span style="color:#888;font-size:12px;">Capital Norvex Inc.</span></p>
</td></tr>

<!-- FOOTER -->
<tr><td style="background:#0A0A0A;padding:18px;text-align:center;color:#C8B070;font-size:11px;letter-spacing:1.2px;">
<a href="https://capitalnorvex.com" style="color:#C8B070;text-decoration:none;">capitalnorvex.com</a>
</td></tr>

</table>
</td></tr></table>
<div style="margin-top:6px;padding:14px 16px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:10.5px;color:#64748b;line-height:1.55;letter-spacing:.3px;text-align:center;">
<strong style="color:#0f172a;font-size:11.5px;letter-spacing:1px;">CAPITAL NORVEX INC.</strong><br>
2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
Téléphone : 1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
</div>
</body></html>`,
  };
}

function emailToYves(app, applicationId) {
  // Champs optionnels : afficher seulement si présents (formulaire simplifié 2026-05-21)
  const specialties = (app.specialties || []).join(", ");
  const rows = [
    { label: "Courriel", value: `<a href="mailto:${app.email}">${app.email}</a>` },
    { label: "Téléphone", value: app.phone },
    app.licenseNo ? { label: "N° licence", value: app.licenseNo } : null,
    app.yearsExperience ? { label: "Années en prêt privé", value: app.yearsExperience } : null,
    app.annualVolume ? { label: "Volume annuel", value: `<strong>${app.annualVolume}</strong>` } : null,
    app.filesPerYear ? { label: "Dossiers référés/an", value: app.filesPerYear } : null,
    specialties ? { label: "Spécialités", value: specialties } : null,
    app.linkedin ? { label: "LinkedIn / site", value: `<a href="${app.linkedin}">${app.linkedin}</a>` } : null,
  ].filter(Boolean);
  const rowsHtml = rows.map(r => `<tr><td style="padding:6px 0;color:#666;width:200px;">${r.label}</td><td>${r.value}</td></tr>`).join("");
  const motivationBlock = app.motivation ? `
<div style="margin-top:20px;padding:14px 18px;background:#FCF8EE;border-left:2px solid #C8B070;">
<div style="font-size:10px;letter-spacing:2px;color:#9A8554;margin-bottom:6px;">MOTIVATION</div>
<div style="font-size:13px;line-height:1.6;color:#3a3a3a;white-space:pre-wrap;">${app.motivation.replace(/</g, "&lt;")}</div>
</div>` : "";
  return {
    subject: `🆕 Candidature courtier — ${app.fullName} (${app.agency})`,
    html: `<!DOCTYPE html><html><body style="font-family:Georgia,serif;background:#FBF7EB;padding:24px;">
<div style="max-width:640px;margin:0 auto;background:#fff;border-left:3px solid #C8B070;padding:24px;">
<div style="font-size:11px;letter-spacing:2.5px;color:#9A8554;margin-bottom:8px;">NOUVELLE CANDIDATURE COURTIER</div>
<h2 style="margin:0 0 16px 0;color:#0A0A0A;">${app.fullName}</h2>
<p style="color:#555;margin:0 0 18px 0;"><strong>${app.agency}</strong>${app.province ? ` &middot; ${app.province}` : ""}</p>

<table style="width:100%;border-collapse:collapse;font-size:13.5px;">
${rowsHtml}
</table>
${motivationBlock}
<p style="margin-top:24px;font-size:12px;color:#888;">
Application ID : <code>${applicationId}</code><br>
Reçue : ${new Date().toLocaleString("fr-CA", { timeZone: "America/Toronto" })}<br>
Action : ouvrir le <a href="https://capitalnorvex.com/capital-norvex-courtiers-admin.html">dashboard Courtiers</a> &rarr; Approuver / Refuser
</p>
</div>
  <div style="margin-top:24px;padding-top:14px;border-top:1px solid #cbd5e1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:11px;color:#64748b;line-height:1.5;letter-spacing:.3px;text-align:center">
    <strong style="color:#0f172a;font-size:12px;letter-spacing:1px">CAPITAL NORVEX INC.</strong><br>
    2705-1000 André-Prévost · Île-des-Sœurs (Verdun) · Montréal, Québec  H3E 0G2<br>
    Téléphone : 1-(438)-533-PRET (7738) · info@capitalnorvex.com · capitalnorvex.com
  </div>
</body></html>`,
  };
}

// ── Validation ───────────────────────────────────────────────────────────
// Formulaire simplifié 2026-05-20 : seuls les 4 champs essentiels sont requis.
// Les autres (licenseNo, province, yearsExperience, annualVolume, filesPerYear,
// specialties, motivation, linkedin) sont acceptés mais optionnels — on les
// recueillera lors de l'appel de suivi avec l'agent dédié.
function validate(body) {
  const required = ["fullName", "email", "phone", "agency"];
  for (const f of required) {
    if (body[f] === undefined || body[f] === null || body[f] === "") {
      return `Champ requis manquant : ${f}`;
    }
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(body.email)) {
    return "Adresse courriel invalide";
  }
  // motivation reste vérifié uniquement si fourni (rétro-compatibilité)
  if (
    body.motivation !== undefined &&
    body.motivation !== null &&
    typeof body.motivation === "string" &&
    body.motivation.length > 2000
  ) {
    return "Motivation invalide (max 2000 caractères)";
  }
  return null;
}

// ── Handler ──────────────────────────────────────────────────────────────
export default async function handler(req) {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  let body;
  try {
    body = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: "Invalid JSON" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const validationError = validate(body);
  if (validationError) {
    return new Response(JSON.stringify({ error: validationError }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const lang = body.lang === "en" ? "en" : "fr";
  const ip =
    req.headers.get("x-forwarded-for") ||
    req.headers.get("x-real-ip") ||
    "unknown";

  // Document Firestore
  // Tous les champs optionnels sont sécurisés avec fallback "" / 0 / [] pour
  // accepter à la fois le formulaire simplifié (4 champs) et un éventuel
  // formulaire enrichi (rétro-compatibilité avec anciens envois).
  const application = {
    fullName: String(body.fullName).trim(),
    email: String(body.email).trim().toLowerCase(),
    phone: String(body.phone).trim(),
    linkedin: body.linkedin ? String(body.linkedin).trim() : "",
    agency: String(body.agency).trim(),
    licenseNo: body.licenseNo ? String(body.licenseNo).trim() : "",
    province: body.province ? String(body.province).trim() : "",
    yearsExperience: body.yearsExperience ? Number(body.yearsExperience) || 0 : 0,
    annualVolume: body.annualVolume ? String(body.annualVolume).trim() : "",
    specialties: Array.isArray(body.specialties)
      ? body.specialties.map((s) => String(s))
      : [],
    filesPerYear: body.filesPerYear ? Number(body.filesPerYear) || 0 : 0,
    motivation: body.motivation ? String(body.motivation).trim() : "",
    lang,
    status: "pending_review",
    submittedAt: new Date().toISOString(),
    reviewedAt: null,
    reviewedBy: null,
    reviewNotes: "",
    sourceIp: ip.split(",")[0].trim(),
    userAgent: req.headers.get("user-agent") || "",
  };

  // Firestore : POST collection (Firestore génère l'ID)
  let applicationId = null;
  try {
    // Service Account via helper centralisé (Blobs first, env var fallback)
    const { getServiceAccount } = await import("./_firebase-sa.mjs");
    let sa;
    try {
      sa = await getServiceAccount();
    } catch (e) {
      throw new Error("Firebase SA load failed: " + e.message);
    }
    if (!sa.client_email || !sa.private_key) {
      throw new Error(
        "Firebase SA invalid (missing client_email or private_key)"
      );
    }
    const projectId = sa.project_id || process.env.FIREBASE_PROJECT_ID;
    if (!projectId) throw new Error("project_id missing");
    const fsToken = await getFirestoreToken(sa);

    // 1) Création de la candidature dans brokerApplications
    const appUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/brokerApplications`;
    const appResp = await fetch(appUrl, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${fsToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ fields: objToFsFields(application) }),
    });
    if (!appResp.ok) {
      const txt = await appResp.text();
      throw new Error(
        "Firestore brokerApplications write failed " +
          appResp.status +
          ": " +
          txt.slice(0, 200)
      );
    }
    const appDoc = await appResp.json();
    applicationId = appDoc.name.split("/").pop();

    // 2) Création du dossier opérationnel dans brokers/{brokerId}
    //    Profile minimal compatible avec agent Python existant
    //    (relationshipStatus, dealsReceived, dealsClosed, lastTouchpoint)
    const nowIso = new Date().toISOString();
    const brokerProfile = {
      // Identité (miroir de la candidature)
      name: application.fullName,
      email: application.email,
      phone: application.phone,
      linkedin: application.linkedin || "",
      agency: application.agency,
      licenseNo: application.licenseNo,
      province: application.province,
      yearsExperience: application.yearsExperience,
      annualVolume: application.annualVolume,
      specialties: application.specialties,
      filesPerYear: application.filesPerYear,
      lang: application.lang,

      // Statut opérationnel — l'agent Python lit ce champ
      relationshipStatus: "applicant",
      dealsReceived: 0,
      dealsClosed: 0,
      lastTouchpoint: nowIso,

      // Lien vers la candidature
      applicationId: applicationId,
      createdFrom: "self_application",
      createdAt: nowIso,
      approvedAt: null,
      approvedBy: null,

      // Notes opérationnelles vides au départ
      operationalNotes: "",
    };

    const brokerUrl = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/brokers`;
    const brokerResp = await fetch(brokerUrl, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${fsToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ fields: objToFsFields(brokerProfile) }),
    });
    let brokerId = null;
    if (brokerResp.ok) {
      const brokerDoc = await brokerResp.json();
      brokerId = brokerDoc.name.split("/").pop();

      // Lier le brokerId dans la candidature (PATCH)
      const patchUrl =
        appUrl +
        "/" +
        applicationId +
        "?updateMask.fieldPaths=brokerId";
      await fetch(patchUrl, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${fsToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          fields: { brokerId: { stringValue: brokerId } },
        }),
      }).catch(() => {});
    } else {
      // Pas de blocage si broker creation échoue : la candidature existe
      const txt = await brokerResp.text();
      console.error(
        "Firestore brokers write failed " +
          brokerResp.status +
          ": " +
          txt.slice(0, 200)
      );
    }
    // Conserver brokerId pour la réponse
    application._brokerId = brokerId;
  } catch (e) {
    console.error("Firestore error:", e.message);
    return new Response(
      JSON.stringify({ error: "Storage error: " + e.message }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }

  // Email confirmation au courtier (best-effort)
  const brokerMail = emailToBroker({
    fullName: application.fullName,
    lang,
  });
  const brokerSent = await sendGridEmail({
    to: application.email,
    subject: brokerMail.subject,
    html: brokerMail.html,
  });

  // Email notification à Yves (best-effort)
  const yvesMail = emailToYves(application, applicationId);
  const yvesSent = await sendGridEmail({
    to: NOTIFY_EMAIL,
    subject: yvesMail.subject,
    html: yvesMail.html,
    replyTo: application.email,
  });

  return new Response(
    JSON.stringify({
      ok: true,
      applicationId,
      brokerId: application._brokerId || null,
      brokerEmailSent: brokerSent.ok,
      yvesEmailSent: yvesSent.ok,
      ...(brokerSent.ok && yvesSent.ok
        ? {}
        : { warnings: { broker: brokerSent.error, yves: yvesSent.error } }),
    }),
    {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }
  );
}

export const config = {
  path: "/api/courtier-candidature",
};
