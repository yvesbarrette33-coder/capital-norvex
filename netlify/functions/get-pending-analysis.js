const { listDocs } = require('../lib/firestore');

// Retourne les dossiers en stage "docs" qui ont reçu le courriel de bienvenue
// mais qui n'ont pas encore de Score Norvex calculé
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
        d.stage === 'docs' &&
        d.welcomeEmailSent === true &&
        !d.scoreNorvex
    );

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ ok: true, dossiers }),
    };
  } catch (err) {
    console.error('get-pending-analysis error:', err);
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ ok: false, error: err.message }),
    };
  }
};
