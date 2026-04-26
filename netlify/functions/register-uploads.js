const { getStore } = require('@netlify/blobs');
const { updateDoc } = require('../lib/firestore');

// Appelé par upload.html après que le client a uploadé ses fichiers vers Firebase Storage.
// Body: { token, files: [{path, filename, size}] }
// Met à jour le token dans Blobs ET le dossier dans Firestore.
exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
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
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ error: 'JSON invalide' }),
    };
  }

  const { token, files } = body;
  if (!token || !Array.isArray(files) || files.length === 0) {
    return {
      statusCode: 400,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ error: 'token et files requis' }),
    };
  }

  try {
    const tokenStore = getStore('upload-tokens');
    const tokenData = await tokenStore.get(token, { type: 'json' });

    if (!tokenData) {
      return {
        statusCode: 403,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
        body: JSON.stringify({ error: 'Token invalide ou expiré' }),
      };
    }

    const uploadedAt = new Date().toISOString();
    const storageDocs = files.map(f => ({
      path: f.path,
      filename: f.filename,
      size: f.size || 0,
      uploadedAt,
    }));

    // Mettre à jour le token dans Blobs
    tokenData.storageDocs = [...(tokenData.storageDocs || []), ...storageDocs];
    tokenData.uploadedAt = uploadedAt;
    await tokenStore.setJSON(token, tokenData);

    // Mettre à jour le dossier dans Firestore — signal pour l'agent que les docs sont prêts
    await updateDoc('dossiers', tokenData.dossierID, {
      uploadedDocs: storageDocs,
      uploadedAt,
      docsReady: true,
    });

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ ok: true }),
    };
  } catch (err) {
    console.error('register-uploads error:', err);
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ ok: false, error: err.message }),
    };
  }
};
