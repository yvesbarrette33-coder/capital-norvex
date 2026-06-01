/**
 * POST /.netlify/functions/analyze-track
 * Body: {
 *   pdfBase64: string,        // PDF du rapport architecte/inspecteur
 *   ventilation: [{id, poste, cat, pctActuel}, ...]
 * }
 *
 * Claude AI lit le rapport et extrait le % d'avancement pour chaque poste.
 * Retourne: { updates: [{id, poste, pctActuel, pctNouveau, note}, ...] }
 */

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  }
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
  if (!ANTHROPIC_API_KEY) return json({ error: "ANTHROPIC_API_KEY not set" }, 500);

  let body;
  try { body = await req.json(); }
  catch { return json({ error: "Invalid JSON" }, 400); }

  const { pdfBase64, ventilation } = body;
  if (!pdfBase64) return json({ error: "Missing pdfBase64" }, 400);
  if (!ventilation || !ventilation.length) return json({ error: "Missing ventilation" }, 400);

  // Préparer la liste des postes pour Claude
  const postesList = ventilation.map((p, i) =>
    `[${p.id}] ${p.cat} > ${p.poste} (actuellement à ${p.pctActuel}%)`
  ).join("\n");

  const systemPrompt = `Tu es un expert en gestion de projets de construction au Québec. Tu analyses des rapports d'architecte, d'inspecteur en bâtiment ou de visite de chantier pour extraire l'avancement de chaque poste de construction.

Tu reçois :
1. Un rapport PDF (rapport d'architecte, inspecteur, visite de chantier, PIIA, etc.)
2. La liste des postes de construction avec leur avancement actuel

Ta tâche : pour chaque poste mentionné dans le rapport, détermine le pourcentage d'avancement (0-100%) basé sur les informations du rapport. Si le rapport ne mentionne pas un poste, conserve le pourcentage actuel.

RÈGLES STRICTES :
- Réponds UNIQUEMENT avec un tableau JSON valide, sans texte avant ni après
- Format exact : [{"id":"p01","pctNouveau":75},{"id":"p02","pctNouveau":100}, ...]
- N'inclus que les postes où tu peux déterminer un avancement à partir du rapport
- Les pourcentages sont des entiers (0, 5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 75, 80, 85, 90, 95, 100)
- 100% = travaux complétés et acceptés
- 0% = pas commencé
- Sois conservateur : si tu n'es pas certain, conserve le % actuel`;

  const userPrompt = `Analyse ce rapport de chantier et extrait les pourcentages d'avancement.

POSTES DE CONSTRUCTION À ANALYSER :
${postesList}

Retourne un tableau JSON avec uniquement les postes que tu peux évaluer d'après le rapport. Format : [{"id":"p01","pctNouveau":75}, ...]`;

  try {
    const claudeResp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: "claude-sonnet-4-6",
        max_tokens: 2000,
        system: systemPrompt,
        messages: [{
          role: "user",
          content: [
            {
              type: "document",
              source: {
                type: "base64",
                media_type: "application/pdf",
                data: pdfBase64,
              },
            },
            { type: "text", text: userPrompt },
          ],
        }],
      }),
    });

    if (!claudeResp.ok) {
      const err = await claudeResp.text();
      return json({ error: "Claude API error: " + err }, 500);
    }

    const claudeData = await claudeResp.json();
    const rawText = claudeData.content?.[0]?.text || "[]";

    // Parser la réponse JSON de Claude
    let aiUpdates;
    try {
      // Extraire le JSON si Claude a mis du texte autour
      const jsonMatch = rawText.match(/\[[\s\S]*\]/);
      aiUpdates = JSON.parse(jsonMatch ? jsonMatch[0] : rawText);
    } catch {
      return json({ error: "Claude returned invalid JSON: " + rawText.slice(0, 200) }, 500);
    }

    // Merger les résultats avec la ventilation complète
    const updates = ventilation.map(p => {
      const aiUpdate = aiUpdates.find(u => u.id === p.id);
      return {
        id: p.id,
        poste: p.poste,
        cat: p.cat,
        pctActuel: p.pctActuel,
        pctNouveau: aiUpdate ? Math.min(100, Math.max(0, Math.round(aiUpdate.pctNouveau))) : p.pctActuel,
      };
    });

    return json({ ok: true, updates, postsAnalyzed: aiUpdates.length });

  } catch (e) {
    return json({ error: "Request failed: " + e.message }, 500);
  }
};
