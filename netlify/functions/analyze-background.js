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

  // Préférer la clé serveur (env Netlify); fallback sur header x-api-key envoyé par le navigateur
  const apiKey = process.env.ANTHROPIC_API_KEY || event.headers['x-api-key'];

  if (!apiKey) {
    return {
      statusCode: 401,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ error: 'API key not configured (set ANTHROPIC_API_KEY or send x-api-key header)' }),
    };
  }

  try {
    const { pdfKeys = [], inlinePdfs = [], storageFiles = [], prompt, model = 'claude-opus-4-7' } =
      JSON.parse(event.body);

    const FIREBASE_API_KEY = process.env.FIREBASE_SERVICE_ACCOUNT;
    const STORAGE_BUCKET = 'capital-norvex.firebasestorage.app';

    const store = getStore('pdfs');
    const content = [];

    for (const key of pdfKeys) {
      try {
        const buffer = await store.get(key, { type: 'arrayBuffer' });
        if (buffer && buffer.byteLength > 0) {
          const b64 = Buffer.from(buffer).toString('base64');
          content.push({
            type: 'document',
            source: { type: 'base64', media_type: 'application/pdf', data: b64 },
          });
        } else {
          console.warn('analyze-background: empty blob for key', key);
        }
      } catch (e) {
        console.warn('analyze-background: failed to read key', key, e.message);
      }
    }

    // Télécharger les fichiers depuis Firebase Storage
    for (const sf of storageFiles) {
      try {
        const encodedPath = encodeURIComponent(sf.path);
        const dlUrl = `https://firebasestorage.googleapis.com/v0/b/${STORAGE_BUCKET}/o/${encodedPath}?alt=media&key=${FIREBASE_API_KEY}`;
        const dlResp = await fetch(dlUrl);
        if (dlResp.ok) {
          const buffer = await dlResp.arrayBuffer();
          const b64 = Buffer.from(buffer).toString('base64');
          const mime = sf.path.toLowerCase().endsWith('.pdf') ? 'application/pdf' : (sf.mime || 'application/pdf');
          content.push({
            type: 'document',
            source: { type: 'base64', media_type: mime, data: b64 },
          });
        } else {
          console.warn('analyze-background: Firebase Storage download failed', sf.path, dlResp.status);
        }
      } catch (e) {
        console.warn('analyze-background: Firebase Storage error', sf.path, e.message);
      }
    }

    for (const doc of inlinePdfs) {
      content.push(doc);
    }

    if (prompt) {
      content.push({ type: 'text', text: prompt });
    }

    const resp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model,
        max_tokens: 4000,
        messages: [{ role: 'user', content }],
      }),
    });

    const data = await resp.text();
    return {
      statusCode: resp.status,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
      body: data,
    };
  } catch (err) {
    console.error('analyze-background error:', err);
    return {
      statusCode: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
      body: JSON.stringify({ error: err.message }),
    };
  }
};
