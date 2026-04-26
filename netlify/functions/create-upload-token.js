const { getStore } = require('@netlify/blobs');
const crypto = require('crypto');

// Appelé par l'agent pour générer un lien d'upload sécurisé à inclure dans le courriel de bienvenue.
// Body: { dossierId, clientNom, projet, lang, expiresInDays }
// Retourne: { ok: true, token, uploadUrl }
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

  const { dossierId, clientNom, projet, lang = 'fr', expiresInDays = 14 } = body;

  if (!dossierId || !clientNom) {
    return {
      statusCode: 400,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'Champs requis: dossierId, clientNom' }),
    };
  }

  try {
    const token = crypto.randomBytes(24).toString('hex');
    const expiresAt = new Date(Date.now() + expiresInDays * 24 * 60 * 60 * 1000).toISOString();

    const store = getStore('upload-tokens');
    await store.setJSON(token, {
      dossierID: dossierId,
      clientNom,
      projet: projet || '',
      lang,
      expiresAt,
      createdAt: new Date().toISOString(),
      docs: [],
    });

    const baseUrl = process.env.SITE_URL || 'https://capitalnorvex.com';
    const uploadUrl = `${baseUrl}/upload.html?t=${token}`;

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ ok: true, token, uploadUrl, expiresAt }),
    };
  } catch (err) {
    console.error('create-upload-token error:', err);
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ ok: false, error: err.message }),
    };
  }
};
