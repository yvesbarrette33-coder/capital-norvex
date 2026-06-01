/**
 * POST /.netlify/functions/analyze-invoice
 * Body: {
 *   imageBase64: string,   // image (JPEG/PNG/WEBP) ou PDF en base64
 *   mediaType: string,     // "image/jpeg" | "image/png" | "image/webp" | "application/pdf"
 * }
 * Retourne: { fournisseur, date, numero, montant_ht, tps, tvq, montant_total, categorie, description, confiance }
 */

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
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

  const { imageBase64, mediaType } = body;
  if (!imageBase64) return json({ error: "Missing imageBase64" }, 400);

  const isImage = mediaType && mediaType.startsWith("image/");
  const isPDF = mediaType === "application/pdf";
  if (!isImage && !isPDF) return json({ error: "mediaType doit être image/* ou application/pdf" }, 400);

  const systemPrompt = `Tu es un expert en comptabilité québécoise. Tu analyses des factures, reçus et notes de frais pour en extraire les informations structurées.

Tu dois extraire :
- fournisseur : nom du fournisseur/vendeur
- date : date de la facture (format YYYY-MM-DD, si pas de date → null)
- numero : numéro de facture (si présent, sinon null)
- montant_ht : montant avant taxes (nombre décimal)
- tps : montant TPS/GST (nombre décimal, 0 si absent)
- tvq : montant TVQ/PST/QST (nombre décimal, 0 si absent)
- montant_total : montant total payé TTC (nombre décimal)
- categorie : une seule catégorie parmi : "loyer_bureau" | "salaires_contractuels" | "services_professionnels" | "marketing_pub" | "telecom_logiciels" | "assurances" | "fournitures_bureau" | "transport_deplacement" | "repas_representation" | "formation" | "frais_bancaires" | "autre"
- description : courte description en français de ce que c'est (max 80 chars)
- confiance : "haute" | "moyenne" | "faible" selon la clarté du document

RÈGLES :
- Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après
- Si une valeur n'est pas trouvable, utilise null
- montant_ht = montant_total - tps - tvq (si taxes non visibles, montant_ht = montant_total)
- Les montants sont des nombres décimaux (ex: 125.00)`;

  const contentBlocks = isImage
    ? [
        { type: "image", source: { type: "base64", media_type: mediaType, data: imageBase64 } },
        { type: "text", text: "Analyse cette facture et retourne un objet JSON avec les informations extraites." }
      ]
    : [
        { type: "document", source: { type: "base64", media_type: "application/pdf", data: imageBase64 } },
        { type: "text", text: "Analyse cette facture PDF et retourne un objet JSON avec les informations extraites." }
      ];

  try {
    const claudeResp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "pdfs-2024-09-25",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: "claude-sonnet-4-6",
        max_tokens: 1000,
        system: systemPrompt,
        messages: [{ role: "user", content: contentBlocks }],
      }),
    });

    if (!claudeResp.ok) {
      const err = await claudeResp.text();
      return json({ error: "Claude API error", detail: err }, 502);
    }

    const claudeData = await claudeResp.json();
    const raw = claudeData.content?.[0]?.text?.trim() || "";

    // Extraire le JSON de la réponse
    const jsonMatch = raw.match(/\{[\s\S]*\}/);
    if (!jsonMatch) return json({ error: "Impossible de parser la réponse AI", raw }, 502);

    const extracted = JSON.parse(jsonMatch[0]);
    return json({ success: true, data: extracted });

  } catch (err) {
    return json({ error: err.message }, 500);
  }
};
