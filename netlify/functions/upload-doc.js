const { getStore } = require('@netlify/blobs');

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

  const token = event.queryStringParameters?.token;
  const filename = (event.queryStringParameters?.name || 'document')
    .replace(/[^a-zA-Z0-9._\-() ]/g, '_');

  if (!token) {
    return {
      statusCode: 400,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ ok: false, error: 'Missing token' }),
    };
  }

  try {
    // Validate token
    const tokenStore = getStore('upload-tokens');
    const tokenData = await tokenStore.get(token, { type: 'json' });

    if (!tokenData) {
      return {
        statusCode: 403,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
        body: JSON.stringify({ ok: false, error: 'Invalid or expired token' }),
      };
    }

    if (tokenData.expiresAt && new Date(tokenData.expiresAt) < new Date()) {
      return {
        statusCode: 410,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
        body: JSON.stringify({ ok: false, error: 'Invalid or expired token' }),
      };
    }

    // Store file in Netlify Blobs
    const docStore = getStore('dossier-docs');
    const blobKey = `${tokenData.dossierID}/${Date.now()}_${filename}`;

    const buffer = event.isBase64Encoded
      ? Buffer.from(event.body, 'base64')
      : Buffer.from(event.body, 'binary');

    await docStore.set(blobKey, buffer, {
      metadata: {
        filename,
        dossierID: tokenData.dossierID,
        contentType: event.headers['content-type'] || 'application/octet-stream',
        uploadedAt: new Date().toISOString(),
      },
    });

    // Record new doc in token metadata for later retrieval
    tokenData.docs = tokenData.docs || [];
    tokenData.docs.push({ blobKey, filename, uploadedAt: new Date().toISOString() });
    await tokenStore.set(token, JSON.stringify(tokenData));

    return {
      statusCode: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
      body: JSON.stringify({ ok: true, blobKey }),
    };
  } catch (err) {
    console.error('upload-doc error:', err);
    return {
      statusCode: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
      body: JSON.stringify({ ok: false, error: err.message }),
    };
  }
};
