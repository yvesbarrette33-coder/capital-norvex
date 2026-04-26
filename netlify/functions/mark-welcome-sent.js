const { getDoc, updateDoc } = require('../lib/firestore');

// Called by the agent after sending the welcome email for a dossier.
// Body: { dossierId }
// Marks welcomeEmailSent=true so the dossier moves from get-new-dossiers → get-pending-analysis.
exports.handler = async (event) => {
  const secret = event.headers['x-internal-secret'];
  if (!secret || secret !== process.env.INTERNAL_SECRET) {
    return {
      statusCode: 401,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'Unauthorized' }),
    };
  }

  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  let body;
  try {
    body = JSON.parse(event.body);
  } catch {
    return {
      statusCode: 400,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'JSON invalide' }),
    };
  }

  const { dossierId } = body;

  if (!dossierId) {
    return {
      statusCode: 400,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'Champ requis: dossierId' }),
    };
  }

  try {
    const dossier = await getDoc('dossiers', dossierId);
    if (!dossier) {
      return {
        statusCode: 404,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: 'Dossier introuvable' }),
      };
    }

    await updateDoc('dossiers', dossierId, {
      welcomeEmailSent: true,
      welcomeEmailDate: new Date().toISOString(),
    });

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ ok: true, dossierId }),
    };
  } catch (err) {
    console.error('mark-welcome-sent error:', err);
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ ok: false, error: err.message }),
    };
  }
};
