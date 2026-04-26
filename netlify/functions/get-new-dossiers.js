const { listDocs } = require('../lib/firestore');

// Retourne les dossiers qui n'ont pas encore reçu le courriel de bienvenue
// (stages: nouvelle, analyse, docs)
exports.handler = async (event) => {
  const secret = event.headers['x-internal-secret'];
  if (!secret || secret !== process.env.INTERNAL_SECRET) {
    return {
      statusCode: 401,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'Unauthorized' }),
    };
  }

  if (event.httpMethod !== 'GET') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  try {
    const all = await listDocs('dossiers');
    const dossiers = all.filter(
      (d) =>
        d &&
        ['nouvelle', 'analyse', 'docs'].includes(d.stage) &&
        !d.welcomeEmailSent
    );

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ ok: true, dossiers }),
    };
  } catch (err) {
    console.error('get-new-dossiers error:', err);
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ ok: false, error: err.message }),
    };
  }
};
