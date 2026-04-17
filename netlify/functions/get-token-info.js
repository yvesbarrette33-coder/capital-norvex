const { getStore } = require('@netlify/blobs');

exports.handler = async (event) => {
  if (event.httpMethod !== 'GET') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  const token = event.queryStringParameters?.t;
  if (!token) {
    return {
      statusCode: 400,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'Missing token' }),
    };
  }

  try {
    const store = getStore('upload-tokens');
    const data = await store.get(token, { type: 'json' });

    if (!data) {
      return {
        statusCode: 404,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: 'Invalid or expired token' }),
      };
    }

    if (data.expiresAt && new Date(data.expiresAt) < new Date()) {
      return {
        statusCode: 410,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: 'Invalid or expired token' }),
      };
    }

    return {
      statusCode: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
      body: JSON.stringify({
        ok: true,
        dossierID: data.dossierID,
        clientNom: data.clientNom,
        projet: data.projet || '',
        lang: data.lang || 'fr',
      }),
    };
  } catch (err) {
    console.error('get-token-info error:', err);
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: err.message }),
    };
  }
};
