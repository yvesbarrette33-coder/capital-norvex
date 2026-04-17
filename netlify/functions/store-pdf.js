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

  try {
    const filename = (event.queryStringParameters?.name || 'document.pdf')
      .replace(/[^a-zA-Z0-9._\-() ]/g, '_');
    const key = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}_${filename}`;

    const buffer = event.isBase64Encoded
      ? Buffer.from(event.body, 'base64')
      : Buffer.from(event.body, 'binary');

    const store = getStore('pdfs');
    await store.set(key, buffer, {
      metadata: {
        filename,
        contentType: 'application/pdf',
        uploadedAt: new Date().toISOString(),
      },
    });

    return {
      statusCode: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
      body: JSON.stringify({ ok: true, key }),
    };
  } catch (err) {
    console.error('store-pdf error:', err);
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
