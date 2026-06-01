/**
 * POST /.netlify/functions/send-invoice
 * Envoie une facture Capital Norvex par email au notaire
 * Copies optionnelles au client et/ou au partenaire
 *
 * Body: {
 *   invoice: { numero, date, dossierNom, montant, description, notaireNom, notaireEmail,
 *              clientNom?, clientEmail?, partenaireNom?, partenaireEmail? }
 * }
 */

import nodemailer from 'nodemailer';
import { getStore } from "@netlify/blobs";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
  });
}

function buildInvoiceHtml(inv) {
  const fmt$ = v => new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD' }).format(v);
  const montantFmt = fmt$(inv.montant);
  const montantPretFmt = inv.montantPret ? fmt$(inv.montantPret) : null;
  const tauxLabel = inv.taux ? `${inv.taux}%` : null;
  const dossierId = [inv.dossierNom, inv.adresse].filter(Boolean).join(' — ');

  return `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body{margin:0;padding:0;background:#f5f3ef;font-family:'Helvetica Neue',Arial,sans-serif;color:#1a1a1a}
  .wrapper{max-width:700px;margin:40px auto;background:#fff;border:1px solid #e0d8cc}
  .header{background:#0a0d13;padding:28px 48px;display:flex;justify-content:space-between;align-items:center}
  .logo-img{height:50px;object-fit:contain}
  .inv-label{text-align:right}
  .inv-label .title{color:#b8975a;font-size:11px;letter-spacing:3px;text-transform:uppercase}
  .inv-label .numero{color:#fff;font-size:20px;font-weight:300;margin-top:4px;font-family:Georgia,serif}
  .body{padding:48px}
  .meta-grid{display:grid;grid-template-columns:1fr 1fr;gap:32px;margin-bottom:40px}
  .meta-label{font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#999;margin-bottom:6px}
  .meta-value{font-size:13px;color:#1a1a1a;line-height:1.55}
  .divider{border:none;border-top:1px solid #e8e3da;margin:32px 0}
  .table{width:100%;border-collapse:collapse}
  .table thead tr{border-bottom:2px solid #0a0d13}
  .table th{padding:10px 12px;font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#666;font-weight:400;text-align:left}
  .table th:last-child,.table td:last-child{text-align:right}
  .table td{padding:16px 12px;font-size:13px;border-bottom:1px solid #f0ebe3;vertical-align:top}
  .table td:last-child{font-weight:600;white-space:nowrap}
  .td-sub{font-size:11px;color:#888;margin-top:4px}
  .total-row{background:#0a0d13}
  .total-row td{color:#fff;font-size:14px;padding:16px 12px;border:none}
  .total-row td:last-child{color:#b8975a;font-size:17px;font-weight:700}
  .note{margin-top:40px;padding:20px 24px;background:#faf8f4;border-left:3px solid #b8975a;font-size:12px;color:#666;line-height:1.75}
  .footer{background:#0a0d13;padding:24px 48px;text-align:center}
  .footer p{color:#4a5568;font-size:10px;letter-spacing:1px;margin:3px 0}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <img src="https://capitalnorvex.com/norvex-v2/assets/logo.png" class="logo-img" alt="Capital Norvex">
    <div class="inv-label">
      <div class="title">Facture</div>
      <div class="numero">${inv.numero}</div>
    </div>
  </div>

  <div class="body">
    <div class="meta-grid">
      <div>
        <div class="meta-label">Émetteur</div>
        <div class="meta-value"><strong>Capital Norvex</strong><br>2705-1000 André-Prévost<br>Verdun, QC  H3E 0G2<br>info@capitalnorvex.com</div>
      </div>
      <div>
        <div class="meta-label">Facturé à</div>
        <div class="meta-value"><strong>${inv.notaireNom}</strong>${dossierId ? `<br>Dossier : ${dossierId}` : ''}</div>
      </div>
      <div>
        <div class="meta-label">Date d'émission</div>
        <div class="meta-value">${inv.date}</div>
      </div>
      <div>
        <div class="meta-label">Payable à</div>
        <div class="meta-value">À la clôture notariale</div>
      </div>
    </div>

    <hr class="divider">

    <table class="table">
      <thead>
        <tr>
          <th>Description</th>
          ${montantPretFmt ? '<th>Montant prêt</th>' : ''}
          <th>Taux</th>
          <th>Honoraires</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>
            <div>Frais d'analyse</div>
            ${inv.adresse ? `<div class="td-sub">${inv.adresse}</div>` : ''}
            ${inv.dossierNom ? `<div class="td-sub">Client : ${inv.dossierNom}</div>` : ''}
          </td>
          ${montantPretFmt ? `<td>${montantPretFmt}</td>` : ''}
          <td>${tauxLabel || '—'}</td>
          <td>${montantFmt}</td>
        </tr>
      </tbody>
      <tfoot>
        <tr class="total-row">
          <td colspan="${montantPretFmt ? 2 : 1}" style="color:#fff">Total dû — Aucune taxe applicable (TPS/TVQ)</td>
          <td></td>
          <td>${montantFmt}</td>
        </tr>
      </tfoot>
    </table>

    <div class="note">
      Les frais de Capital Norvex sont des honoraires de financement privé. <strong>Aucune taxe applicable (TPS/TVQ).</strong><br>
      Payable à la clôture devant notaire. Pour toute question : <strong>info@capitalnorvex.com</strong>
    </div>
  </div>

  <div class="footer">
    <p style="color:#7a8294">2705-1000 André-Prévost, Verdun, QC  H3E 0G2</p>
    <p style="color:#b8975a;letter-spacing:2px">CAPITAL NORVEX · capitalnorvex.com</p>
  </div>
</div>
</body>
</html>`;
}

export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  }
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  const MAIL_USER = process.env.MAIL_USER || "info@capitalnorvex.com";
  const MAIL_PASSWORD = process.env.MAIL_PASSWORD;
  const MAIL_HOST = process.env.MAIL_HOST || "mail.capitalnorvex.com";

  if (!MAIL_PASSWORD) return json({ error: "MAIL_PASSWORD not set" }, 500);

  let body;
  try { body = await req.json(); }
  catch { return json({ error: "Invalid JSON" }, 400); }

  const { invoice } = body;
  if (!invoice?.notaireEmail || !invoice?.montant) {
    return json({ error: "notaireEmail et montant requis" }, 400);
  }

  const html = buildInvoiceHtml(invoice);
  const subject = `Facture ${invoice.numero} — Capital Norvex${invoice.dossierNom ? ' · ' + invoice.dossierNom : ''}`;

  // Destinataires
  const to = [invoice.notaireEmail];
  const cc = [];
  if (invoice.clientEmail) cc.push(invoice.clientEmail);
  if (invoice.partenaireEmail) cc.push(invoice.partenaireEmail);

  // Récupérer les documents du dossier si dossierID fourni
  const attachments = [];
  if (invoice.dossierID) {
    try {
      const uploadStore = getStore({ name: "cn-uploads", consistency: "strong" });
      const { blobs } = await uploadStore.list({ prefix: `${invoice.dossierID}/` });
      for (const blob of blobs) {
        try {
          const fileBuffer = await uploadStore.get(blob.key, { type: "arrayBuffer" });
          if (fileBuffer) {
            const filename = blob.key.split('/').pop().replace(/^\d+_/, ''); // remove timestamp prefix
            attachments.push({ filename, content: Buffer.from(fileBuffer) });
          }
        } catch(e) { console.warn('Blob fetch error:', blob.key, e.message); }
      }
    } catch(e) { console.warn('Blob list error:', e.message); }
  }

  try {
    const transporter = nodemailer.createTransport({
      host: MAIL_HOST,
      port: 465,
      secure: true,
      auth: { user: MAIL_USER, pass: MAIL_PASSWORD },
    });

    await transporter.sendMail({
      from: `Capital Norvex <${MAIL_USER}>`,
      to: to.join(', '),
      cc: cc.length ? cc.join(', ') : undefined,
      subject,
      html,
      attachments,
    });

    return json({ success: true, sentTo: to, cc, docsAttached: attachments.length });
  } catch (err) {
    return json({ error: err.message }, 500);
  }
};
