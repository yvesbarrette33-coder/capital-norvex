const nodemailer = require('nodemailer');

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Content-Type' },
      body: '',
    };
  }

  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  let data;
  try { data = JSON.parse(event.body); }
  catch { return { statusCode: 400, body: JSON.stringify({ error: 'Invalid JSON' }) }; }

  const { id, prenom, nom, email, type, montant, decision, score, conditions = [], lang = 'fr' } = data;

  if (!email) return { statusCode: 400, body: JSON.stringify({ error: 'Email requis' }) };

  const isFr = lang === 'fr';
  const isApproved = decision?.includes('APPROUVÉ') || decision?.includes('APPROVED');
  const isRefused = decision?.includes('REFUSÉ') || decision?.includes('REFUSED') || decision?.includes('DECLINED');

  const fmtCAD = (n) => new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD', maximumFractionDigits: 0 }).format(n);

  const decisionLabel = isApproved
    ? (isFr ? '✅ Approuvé' : '✅ Approved')
    : isRefused
    ? (isFr ? '❌ Refusé' : '❌ Refused')
    : (isFr ? '⚡ Conditionnel' : '⚡ Conditional');

  const conditionsHtml = conditions.length > 0
    ? `<p style="margin:16px 0 8px;font-weight:600;color:#1a1a1a">${isFr ? 'Documents et conditions requis :' : 'Required documents and conditions:'}</p>
       <ul style="margin:0;padding-left:20px;color:#333">
         ${conditions.map(c => `<li style="margin-bottom:6px">${c}</li>`).join('')}
       </ul>`
    : '';

  const subject = isFr
    ? `Capital Norvex — Votre dossier ${id} a été reçu`
    : `Capital Norvex — Your file ${id} has been received`;

  const html = `<!DOCTYPE html>
<html lang="${lang}">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:40px 0">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:4px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)">
        <!-- HEADER -->
        <tr><td style="background:#0F0F0F;padding:28px 40px;text-align:center">
          <p style="margin:0;font-size:10px;letter-spacing:4px;color:#C8A84B;text-transform:uppercase;font-weight:600">${isFr ? 'FINANCEMENT PRIVÉ COMMERCIAL' : 'PRIVATE COMMERCIAL FINANCING'}</p>
          <h1 style="margin:8px 0 4px;font-size:26px;font-weight:700;letter-spacing:3px;color:#fff;font-family:Georgia,serif">CAPITAL NORVEX</h1>
          <p style="margin:0;font-size:10px;color:#888">Québec, Canada · capitalnorvex.ca</p>
        </td></tr>
        <!-- GOLD LINE -->
        <tr><td style="background:#C8A84B;height:2px;padding:0"></td></tr>
        <!-- BODY -->
        <tr><td style="padding:36px 40px">
          <p style="margin:0 0 16px;font-size:15px;color:#333">${isFr ? `Bonjour ${prenom},` : `Hello ${prenom},`}</p>
          <p style="margin:0 0 16px;font-size:14px;color:#555;line-height:1.6">
            ${isFr
              ? `Nous avons bien reçu votre demande de financement et notre système d'analyse Score Norvex™ a complété l'évaluation préliminaire de votre dossier.`
              : `We have received your financing application and our Score Norvex™ analysis system has completed the preliminary evaluation of your file.`}
          </p>
          <!-- DOSSIER BOX -->
          <table width="100%" cellpadding="0" cellspacing="0" style="margin:20px 0">
            <tr><td style="background:#F7F7F7;border-left:3px solid #C8A84B;padding:16px 20px;border-radius:2px">
              <p style="margin:0 0 6px;font-size:12px;color:#666"><strong>${isFr ? 'N° DOSSIER :' : 'FILE No.:'}</strong> ${id}</p>
              <p style="margin:0 0 6px;font-size:12px;color:#666"><strong>${isFr ? 'TYPE :' : 'TYPE:'}</strong> ${type}</p>
              ${montant ? `<p style="margin:0 0 6px;font-size:12px;color:#666"><strong>${isFr ? 'MONTANT :' : 'AMOUNT:'}</strong> ${fmtCAD(montant)}</p>` : ''}
              ${score !== null && score !== undefined ? `<p style="margin:0 0 6px;font-size:12px;color:#666"><strong>SCORE NORVEX™ :</strong> ${score}/100</p>` : ''}
              <p style="margin:0;font-size:12px;color:#666"><strong>${isFr ? 'DÉCISION :' : 'DECISION:'}</strong> ${decisionLabel}</p>
            </td></tr>
          </table>
          ${conditionsHtml}
          ${conditions.length > 0 ? `<p style="margin:16px 0;font-size:14px;color:#555;line-height:1.6">
            ${isFr
              ? 'Afin de compléter l\'analyse de votre dossier et de finaliser votre lettre d\'intention, veuillez nous faire parvenir les documents mentionnés ci-dessus dans les meilleurs délais.'
              : 'In order to complete the analysis of your file and finalize your letter of intent, please send us the documents mentioned above as soon as possible.'}
          </p>` : ''}
          <p style="margin:16px 0;font-size:14px;color:#555;line-height:1.6">
            ${isFr
              ? 'Notre équipe communiquera avec vous sous peu pour discuter des prochaines étapes.'
              : 'Our team will be in touch shortly to discuss the next steps.'}
          </p>
        </td></tr>
        <!-- FOOTER -->
        <tr><td style="background:#F7F7F7;border-top:1px solid #DDD;padding:20px 40px;text-align:center">
          <p style="margin:0 0 4px;font-size:11px;color:#888">Capital Norvex · capitalnorvex.ca</p>
          <p style="margin:0;font-size:10px;color:#AAA">${isFr ? 'Confidentiel — Usage exclusif du destinataire' : 'Confidential — For the exclusive use of the addressee'}</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>`;

  // Configuration SMTP (Gmail App Password)
  const smtpUser = process.env.SMTP_USER;
  const smtpPass = process.env.SMTP_PASS;

  if (!smtpUser || !smtpPass) {
    console.warn('⚠️ SMTP non configuré — email non envoyé');
    return {
      statusCode: 200,
      headers: { 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ ok: false, reason: 'SMTP not configured' }),
    };
  }

  const transporter = nodemailer.createTransporter({
    service: 'gmail',
    auth: { user: smtpUser, pass: smtpPass },
  });

  await transporter.sendMail({
    from: `"Capital Norvex" <${smtpUser}>`,
    to: email,
    bcc: smtpUser, // copie à toi-même
    subject,
    html,
  });

  return {
    statusCode: 200,
    headers: { 'Access-Control-Allow-Origin': '*' },
    body: JSON.stringify({ ok: true, to: email, dossier: id }),
  };
};
