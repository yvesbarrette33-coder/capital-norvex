const { getDoc, updateDoc } = require('../lib/firestore');

// Appelé par l'agent après avoir calculé le Score Norvex
// Body: { dossierId, scoreNorvex, decision, commentaires }
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

  const { dossierId, scoreNorvex, decision, commentaires } = body;

  if (!dossierId || scoreNorvex === undefined || !decision) {
    return {
      statusCode: 400,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'Champs requis: dossierId, scoreNorvex, decision' }),
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

    // Pipeline: nouvelle → analyse → loi → docs → final → notaire → decaisse
    // Après calcul du Score Norvex (en stage "docs") :
    //   - approuvé → "final" (analyse finale)
    //   - refusé   → "refuse" (terminal)
    //   - autre    → "docs"  (reste en attente)
    const prochainStage = decision === 'approuve' ? 'final' :
                          decision === 'refuse' ? 'refuse' : 'docs';

    await updateDoc('dossiers', dossierId, {
      scoreNorvex,
      decision,
      commentaires: commentaires || '',
      stage: prochainStage,
      analysisDate: new Date().toISOString(),
    });

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ ok: true, dossierId, stage: prochainStage }),
    };
  } catch (err) {
    console.error('mark-analysis-done error:', err);
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ ok: false, error: err.message }),
    };
  }
};
