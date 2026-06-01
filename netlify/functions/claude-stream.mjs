// Netlify Functions v2 — true streaming proxy
// Returns a TransformStream immediately so Netlify never times out waiting.
// Claude API response is piped asynchronously into the stream.

export default async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      }
    });
  }

  if (req.method !== 'POST') {
    return new Response('Method Not Allowed', { status: 405 });
  }

  const apiKey = Netlify.env.get('ANTHROPIC_API_KEY');
  if (!apiKey) {
    return new Response(JSON.stringify({ error: 'API key not configured' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  let payload;
  try {
    payload = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid JSON' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Create a TransformStream — return it immediately so Netlify never times out.
  // Claude API is called asynchronously and its SSE stream is piped into the writer.
  const { readable, writable } = new TransformStream();
  const writer = writable.getWriter();
  const encoder = new TextEncoder();

  (async () => {
    try {
      const claudeResp = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': apiKey,
          'anthropic-version': '2023-06-01',
          'anthropic-beta': 'pdfs-2024-09-25'
        },
        body: JSON.stringify({ ...payload, stream: true })
      });

      if (!claudeResp.ok) {
        const errText = await claudeResp.text();
        // Send error as SSE event so the frontend can detect it
        await writer.write(encoder.encode(`data: ${JSON.stringify({ type: 'error', error: errText, status: claudeResp.status })}\n\n`));
      } else {
        // Pipe Claude SSE stream directly
        const reader = claudeResp.body.getReader();
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          await writer.write(value);
        }
      }
    } catch (err) {
      try {
        await writer.write(encoder.encode(`data: ${JSON.stringify({ type: 'error', error: err.message })}\n\n`));
      } catch {}
    } finally {
      try { await writer.close(); } catch {}
    }
  })();

  return new Response(readable, {
    status: 200,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'X-Accel-Buffering': 'no',
      'Access-Control-Allow-Origin': '*'
    }
  });
};
