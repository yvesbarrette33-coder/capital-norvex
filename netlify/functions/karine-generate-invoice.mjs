/**
 * POST /.netlify/functions/karine-generate-invoice
 * Header: x-internal-secret
 * Body: {
 *   dossierId: string,                 // ID Firestore du dossier
 *   honoraires_montage: number,        // CAD, ex: 165000 (3% de 5,5M$)
 *   frais_analyse?: number,            // CAD, ex: 5000 (frais Score Norvex)
 *   notaireEmail?: string,             // override, sinon prend dossier.notaireEmail
 *   notaireNom?: string,                // override
 *   description?: string,              // ex: "Refinancement 2705-1000 André-Prévost"
 *   force?: boolean,                   // re-générer même si déjà envoyée
 * }
 *
 * Génère une facture Capital Norvex Inc., l'envoie au notaire avec Yves CC,
 * et crée une transaction Firestore `pending_payment`. Karine NORVEX FINANCE™
 * V1.5 — facture auto au notaire au moment du dossier de prêt définitif.
 *
 * Variables d'environnement requises (toutes existent ou à configurer) :
 *   - SENDGRID_API_KEY
 *   - INTERNAL_SECRET
 *   - FIREBASE_SA_B64
 *   - CAPITAL_NORVEX_BANK_INSTITUTION   (ex: "815 — Banque Nationale du Canada")
 *   - CAPITAL_NORVEX_BANK_TRANSIT       (ex: "10721")
 *   - CAPITAL_NORVEX_BANK_ACCOUNT       (ex: "12-345678")
 *   - CAPITAL_NORVEX_GST_NUMBER         (ex: "123456789RT0001")
 *   - CAPITAL_NORVEX_QST_NUMBER         (ex: "1234567890TQ0001")
 */

const NEQ = "1182097890";
const ADRESSE_HTML =
  "2705-1000, rue André-Prévost<br>" +
  "Île-des-Sœurs (Verdun), Montréal, QC&nbsp;&nbsp;H3E&nbsp;0G2";
const TEL = "438-533-PRÊT (7738)";
const EMAIL_FROM = "info@capitalnorvex.com";
const YVES_CC = "yves@capitalnorvex.com";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// ── Firestore helpers (même style que les autres endpoints) ─────────
async function getFirestoreToken(sa) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: sa.client_email, sub: sa.client_email,
    aud: "https://oauth2.googleapis.com/token",
    iat: now, exp: now + 3600,
    scope: "https://www.googleapis.com/auth/datastore",
  };
  const b64 = (obj) =>
    btoa(JSON.stringify(obj))
      .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const signingInput = `${b64(header)}.${b64(payload)}`;
  const pemBody = sa.private_key
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\n/g, "");
  const keyData = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));
  const privateKey = await crypto.subtle.importKey(
    "pkcs8", keyData.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5", privateKey, new TextEncoder().encode(signingInput)
  );
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: `${signingInput}.${sigB64}`,
    }),
  });
  const data = await r.json();
  if (!data.access_token) throw new Error("Firestore token failed");
  return { token: data.access_token, projectId: sa.project_id };
}

function fromFsValue(v) {
  if (!v) return null;
  if (v.nullValue !== undefined) return null;
  if (v.booleanValue !== undefined) return v.booleanValue;
  if (v.integerValue !== undefined) return Number(v.integerValue);
  if (v.doubleValue !== undefined) return v.doubleValue;
  if (v.stringValue !== undefined) return v.stringValue;
  if (v.timestampValue !== undefined) return v.timestampValue;
  if (v.arrayValue !== undefined) return (v.arrayValue.values || []).map(fromFsValue);
  if (v.mapValue !== undefined) {
    const out = {};
    for (const [k, val] of Object.entries(v.mapValue.fields || {})) out[k] = fromFsValue(val);
    return out;
  }
  return null;
}

function docToObj(doc) {
  if (!doc?.fields) return {};
  const out = {};
  for (const [k, v] of Object.entries(doc.fields)) out[k] = fromFsValue(v);
  return out;
}

function toFsValue(v) {
  if (v === null || v === undefined) return { nullValue: null };
  if (typeof v === "boolean") return { booleanValue: v };
  if (typeof v === "number") {
    return Number.isInteger(v) ? { integerValue: String(v) } : { doubleValue: v };
  }
  if (typeof v === "string") return { stringValue: v };
  if (Array.isArray(v))
    return { arrayValue: { values: v.map(toFsValue) } };
  if (typeof v === "object") {
    const fields = {};
    for (const [k, vv] of Object.entries(v)) fields[k] = toFsValue(vv);
    return { mapValue: { fields } };
  }
  return { stringValue: String(v) };
}

async function fsGetDoc(projectId, token, collection, docId) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collection}/${encodeURIComponent(docId)}`;
  const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`fsGetDoc ${r.status}`);
  const data = await r.json();
  return docToObj(data);
}

async function fsCreateDoc(projectId, token, collection, payload) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collection}`;
  const fields = {};
  for (const [k, v] of Object.entries(payload)) fields[k] = toFsValue(v);
  const r = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });
  if (!r.ok) throw new Error(`fsCreateDoc ${r.status} ${await r.text()}`);
  const data = await r.json();
  return data.name?.split("/").pop();
}

async function fsPatchDoc(projectId, token, collection, docId, payload) {
  const fields = {};
  for (const [k, v] of Object.entries(payload)) fields[k] = toFsValue(v);
  const updateMask = Object.keys(payload).map(
    (k) => `updateMask.fieldPaths=${encodeURIComponent(k)}`
  ).join("&");
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collection}/${encodeURIComponent(docId)}?${updateMask}`;
  const r = await fetch(url, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });
  if (!r.ok) throw new Error(`fsPatchDoc ${r.status}`);
}

// ── Génération numéro facture séquentiel ────────────────────────────
async function getNextInvoiceNumber(projectId, token) {
  const year = new Date().getFullYear();
  const counterDoc = `invoiceCounter-${year}`;
  const existing = await fsGetDoc(projectId, token, "counters", counterDoc);
  const next = (existing?.value || 0) + 1;
  // Upsert
  if (existing) {
    await fsPatchDoc(projectId, token, "counters", counterDoc,
      { value: next, lastUpdated: new Date().toISOString() });
  } else {
    await fsCreateDoc(projectId, token, "counters",
      { _id: counterDoc, value: next, year, lastUpdated: new Date().toISOString() });
  }
  return `NORV-${year}-${String(next).padStart(4, "0")}`;
}

function fmtCAD(n) {
  return new Intl.NumberFormat("fr-CA", {
    style: "currency", currency: "CAD",
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  }).format(n || 0);
}

// ── Template HTML facture ───────────────────────────────────────────
function buildInvoiceHTML({
  invoiceNumber, dateIso, dossierId, clientNom, projetDesc,
  honoraires, fraisAnalyse, total, notaireNom,
  bankInstitution, bankTransit, bankAccount,
  gstNumber, qstNumber,
}) {
  const dateFmt = new Date(dateIso).toLocaleDateString("fr-CA", {
    year: "numeric", month: "long", day: "numeric",
  });
  const lignes = [
    {
      desc: `Honoraires de montage — Capital Norvex Inc.<br>` +
            `<span style="color:#666;font-size:.85em">Dossier ${dossierId}${projetDesc ? ` · ${projetDesc}` : ""}</span>`,
      montant: honoraires,
    },
  ];
  if (fraisAnalyse > 0) {
    lignes.push({
      desc: `Frais d'analyse Score Norvex™`,
      montant: fraisAnalyse,
    });
  }
  const lignesHtml = lignes.map((l, i) => `
    <tr>
      <td style="padding:14px 12px;border-bottom:1px solid #e6dfd0;font-size:13px;line-height:1.5">${l.desc}</td>
      <td style="padding:14px 12px;border-bottom:1px solid #e6dfd0;text-align:right;font-family:'DM Mono',monospace,monospace;font-size:13px;font-variant-numeric:tabular-nums">${fmtCAD(l.montant)}</td>
    </tr>
  `).join("");

  return `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8"/>
<title>Facture ${invoiceNumber} — Capital Norvex Inc.</title>
</head>
<body style="margin:0;padding:0;background:#fdfcf6;font-family:Georgia,'Times New Roman',serif;color:#1a1a1a;line-height:1.5">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#fdfcf6;padding:24px 0">
    <tr><td align="center">
      <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="background:#fefef9;border:1px solid #d4c89a;max-width:640px">

        <!-- Header -->
        <tr>
          <td style="background:#0a0a0a;color:#c9a227;padding:24px 32px;font-family:Georgia,serif">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="vertical-align:middle">
                  <div style="font-family:Georgia,serif;font-size:22px;letter-spacing:2px;font-weight:bold">CAPITAL NORVEX</div>
                  <div style="font-style:italic;font-size:12px;color:#fff;margin-top:4px">Capital structuré. Ambition maîtrisée.</div>
                </td>
                <td style="text-align:right;vertical-align:middle">
                  <div style="font-size:11px;color:#c9a227;letter-spacing:2px;text-transform:uppercase">Facture</div>
                  <div style="font-family:'DM Mono',Menlo,monospace;font-size:18px;color:#fff;margin-top:4px">${invoiceNumber}</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Date + Adressee -->
        <tr>
          <td style="padding:24px 32px 8px 32px">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="vertical-align:top;font-size:12px;color:#666;width:50%">
                  <div style="font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#8a7d5f;margin-bottom:8px">Émetteur</div>
                  <strong style="color:#1a1a1a;font-size:13px">Capital Norvex Inc.</strong><br>
                  ${ADRESSE_HTML}<br>
                  Tél : ${TEL}<br>
                  ${EMAIL_FROM}<br>
                  NEQ : ${NEQ}
                </td>
                <td style="vertical-align:top;font-size:12px;color:#666;width:50%;text-align:right">
                  <div style="font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#8a7d5f;margin-bottom:8px">Destinataire</div>
                  <strong style="color:#1a1a1a;font-size:13px">${notaireNom || "Le notaire instrumentant"}</strong><br>
                  ${clientNom ? `Dossier : ${clientNom}` : ""}<br>
                  <br>
                  <div style="font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#8a7d5f;margin-bottom:4px">Date d'émission</div>
                  ${dateFmt}
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Lignes facture -->
        <tr>
          <td style="padding:24px 32px">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:2px solid #c9a227;border-bottom:2px solid #c9a227">
              <thead>
                <tr style="background:#f7f1e0">
                  <th align="left" style="padding:10px 12px;font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#8a7d5f;border-bottom:1px solid #d4c89a">Description</th>
                  <th align="right" style="padding:10px 12px;font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#8a7d5f;border-bottom:1px solid #d4c89a;width:140px">Montant</th>
                </tr>
              </thead>
              <tbody>
                ${lignesHtml}
                <tr>
                  <td style="padding:14px 12px;font-weight:bold;font-size:14px">Total à prélever</td>
                  <td style="padding:14px 12px;text-align:right;font-family:'DM Mono',Menlo,monospace;font-size:15px;font-weight:bold;color:#c9a227;font-variant-numeric:tabular-nums">${fmtCAD(total)}</td>
                </tr>
              </tbody>
            </table>
            <p style="margin:12px 0 0 0;font-size:10.5px;color:#666;font-style:italic">
              Note : Capital Norvex Inc. exerce des activités de services financiers exonérés (prêt privé hypothécaire commercial). Aucune TPS/TVQ n'est facturée sur les honoraires de montage ni sur les frais d'analyse, conformément à la partie VII de l'annexe V de la <em>Loi sur la taxe d'accise</em> (TPS) et à l'article 138 de la <em>Loi sur la taxe de vente du Québec</em> (TVQ).
            </p>
          </td>
        </tr>

        <!-- Modalités paiement -->
        <tr>
          <td style="padding:0 32px 24px 32px">
            <div style="background:#0a0a0a;color:#fefef9;padding:18px 22px;border-left:4px solid #c9a227">
              <div style="font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#c9a227;margin-bottom:10px">Modalités de paiement</div>
              <p style="margin:0 0 10px 0;font-size:12px;line-height:1.55;color:#fefef9">
                Le présent montant doit être <strong style="color:#c9a227">prélevé au moment du déboursé</strong> du prêt et viré sans délai au compte bancaire de Capital Norvex Inc. selon les coordonnées ci-dessous.
              </p>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-family:'DM Mono',Menlo,monospace;font-size:11.5px;color:#fefef9">
                <tr>
                  <td style="padding:3px 12px 3px 0;color:#c9a227">Institution</td>
                  <td style="padding:3px 0">${bankInstitution || "[À configurer dans Netlify env]"}</td>
                </tr>
                <tr>
                  <td style="padding:3px 12px 3px 0;color:#c9a227">Transit</td>
                  <td style="padding:3px 0">${bankTransit || "[À configurer]"}</td>
                </tr>
                <tr>
                  <td style="padding:3px 12px 3px 0;color:#c9a227">Compte</td>
                  <td style="padding:3px 0">${bankAccount || "[À configurer]"}</td>
                </tr>
                <tr>
                  <td style="padding:3px 12px 3px 0;color:#c9a227">Bénéficiaire</td>
                  <td style="padding:3px 0">Capital Norvex Inc.</td>
                </tr>
              </table>
              <p style="margin:14px 0 0 0;font-size:10.5px;color:#a89b73;font-style:italic">
                Référence à inscrire sur le virement : <strong style="color:#fefef9">${invoiceNumber}</strong>
              </p>
            </div>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f7f1e0;padding:16px 32px;border-top:1px solid #d4c89a;font-size:10px;color:#666;text-align:center;line-height:1.5">
            Pour toute question : <a href="mailto:yves@capitalnorvex.com" style="color:#c9a227;text-decoration:none">yves@capitalnorvex.com</a> · ${TEL}<br>
            Document généré automatiquement par Karine NORVEX FINANCE™
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>`;
}

// ── SendGrid ────────────────────────────────────────────────────────
async function sendInvoiceEmail({ to, cc, subject, html, invoiceNumber }) {
  const apiKey = process.env.SENDGRID_API_KEY;
  if (!apiKey) throw new Error("SENDGRID_API_KEY manquant");

  const personalizations = [
    {
      to: [{ email: to }],
      cc: cc ? [{ email: cc }] : undefined,
      subject,
    },
  ];

  const r = await fetch("https://api.sendgrid.com/v3/mail/send", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      personalizations,
      from: { email: EMAIL_FROM, name: "Capital Norvex Inc." },
      reply_to: { email: YVES_CC, name: "Yves Barrette" },
      content: [{ type: "text/html", value: html }],
      headers: {
        "X-Capital-Norvex-Type": "invoice-notary",
        "X-Capital-Norvex-Invoice": invoiceNumber,
        "X-Auto-Response-Suppress": "All",
      },
    }),
  });

  if (!r.ok) {
    const errText = await r.text();
    throw new Error(`SendGrid ${r.status}: ${errText.slice(0, 300)}`);
  }
  return true;
}

// ── Handler principal ───────────────────────────────────────────────
export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-internal-secret",
      },
    });
  }
  if (req.method !== "POST")
    return new Response("Method Not Allowed", { status: 405 });

  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return json({ error: "Unauthorized" }, 401);
  }

  let body;
  try { body = await req.json(); }
  catch { return json({ error: "Invalid JSON" }, 400); }

  const {
    dossierId,
    honoraires_montage,
    frais_analyse = 0,
    notaireEmail: overrideNotaireEmail,
    notaireNom: overrideNotaireNom,
    description: overrideDescription,
    force = false,
  } = body;

  if (!dossierId) return json({ error: "dossierId requis" }, 400);
  if (!honoraires_montage || honoraires_montage <= 0)
    return json({ error: "honoraires_montage > 0 requis" }, 400);

  const { getServiceAccount } = await import("./_firebase-sa.mjs");


  let sa;


  try { sa = await getServiceAccount(); }


  catch (e) { return json({ error: "SA load failed: " + e.message }, 500); }

  try {
    const { token, projectId } = await getFirestoreToken(sa);

    const dossier = await fsGetDoc(projectId, token, "dossiers", dossierId);
    if (!dossier) return json({ error: `Dossier ${dossierId} introuvable` }, 404);

    if (dossier.invoiceNotaireSentAt && !force) {
      return json({
        error: `Facture déjà envoyée le ${dossier.invoiceNotaireSentAt}. Utilise force=true pour renvoyer.`,
        invoiceNumber: dossier.invoiceNotaireNumber,
      }, 409);
    }

    const notaireEmail = (overrideNotaireEmail || dossier.notaireEmail
                          || dossier.notaireQc || "").trim();
    if (!notaireEmail || !notaireEmail.includes("@"))
      return json({ error: "Email notaire manquant (param notaireEmail ou champ dossier.notaireEmail)" }, 400);

    const notaireNom = overrideNotaireNom || dossier.notaireNom
                        || dossier.notaireQc || "Le notaire instrumentant";

    const clientNom = `${dossier.prenom || ""} ${dossier.nom || ""}`.trim()
                      || dossier.borrowerName || dossier.name || "";

    const projetDesc = overrideDescription || dossier.adresse
                        || dossier.projectAddress || dossier.type || "";

    const total = Number(honoraires_montage) + Number(frais_analyse);
    const invoiceNumber = await getNextInvoiceNumber(projectId, token);
    const nowIso = new Date().toISOString();

    // Build HTML
    const html = buildInvoiceHTML({
      invoiceNumber, dateIso: nowIso, dossierId,
      clientNom, projetDesc,
      honoraires: Number(honoraires_montage),
      fraisAnalyse: Number(frais_analyse),
      total,
      notaireNom,
      bankInstitution: process.env.CAPITAL_NORVEX_BANK_INSTITUTION || "",
      bankTransit: process.env.CAPITAL_NORVEX_BANK_TRANSIT || "",
      bankAccount: process.env.CAPITAL_NORVEX_BANK_ACCOUNT || "",
      gstNumber: process.env.CAPITAL_NORVEX_GST_NUMBER || "",
      qstNumber: process.env.CAPITAL_NORVEX_QST_NUMBER || "",
    });

    // Envoi email au notaire (CC Yves)
    const subject = `Facture ${invoiceNumber} — Capital Norvex Inc. (dossier ${clientNom || dossierId})`;
    await sendInvoiceEmail({
      to: notaireEmail,
      cc: YVES_CC,
      subject,
      html,
      invoiceNumber,
    });

    // Création transaction Firestore (revenu, pending_payment)
    const txId = await fsCreateDoc(projectId, token, "transactions", {
      type: "revenu",
      date: nowIso.slice(0, 10),
      montant: total,
      categorie: frais_analyse > 0 ? "honoraires_montage" : "honoraires_montage",
      description: `${invoiceNumber} — ${clientNom || dossierId}`,
      statut: "pending_payment",
      dossierId,
      dossierNom: clientNom,
      source: "karine_norvex_finance",
      agent: "karine_norvex_finance",
      // Champs étendus Karine
      fournisseur: notaireNom,  // ici le "payeur" est le notaire
      numero_facture: invoiceNumber,
      montant_ht: total,
      tps: 0,
      tvq: 0,
      devise: "CAD",
      tax_note: "Honoraires de montage hypothécaire — services financiers exonérés TPS/TVQ (annexe V partie VII LTA / art. 138 LTV).",
      requires_yves_review: false,
      confidence: 100,
      sourceEmailFrom: notaireEmail,
      sourceEmailSubject: subject,
      sourceEmailDate: nowIso,
      honorairesMontage: Number(honoraires_montage),
      fraisAnalyse: Number(frais_analyse),
      createdAt: nowIso,
    });

    // Patch dossier (anti-doublon + audit)
    await fsPatchDoc(projectId, token, "dossiers", dossierId, {
      invoiceNotaireSentAt: nowIso,
      invoiceNotaireNumber: invoiceNumber,
      invoiceNotaireAmount: total,
      invoiceNotaireEmail: notaireEmail,
      invoiceTransactionId: txId,
    });

    return json({
      ok: true,
      invoiceNumber,
      dossierId,
      transactionId: txId,
      sentTo: notaireEmail,
      cc: YVES_CC,
      total,
      currency: "CAD",
    });
  } catch (e) {
    return json({ error: e.message }, 500);
  }
};

export const config = {
  path: "/api/karine-generate-invoice",
};
