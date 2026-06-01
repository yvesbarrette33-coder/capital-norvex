export default async (req) => {
  const key = Netlify.env.get('ANTHROPIC_API_KEY');
  if (!key) {
    return new Response(JSON.stringify({ error: 'not configured' }), { status: 500 });
  }
  return new Response(JSON.stringify({ key }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
};
