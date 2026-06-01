// Netlify Background Function — up to 15-minute timeout
// Receives {jobId, model, max_tokens, messages} where PDF documents are
// referenced as {type:"blob_ref", key:"pdf_xxx"} instead of inline base64.
// Expands blob refs from Netlify Blobs before calling Claude API.

import { getStore } from "@netlify/blobs";

export default async (req) => {
  const apiKey = Netlify.env.get("ANTHROPIC_API_KEY");
  if (!apiKey) {
    console.error("[analyze-background] Missing ANTHROPIC_API_KEY");
    return;
  }

  let jobId, payload;
  try {
    const body = await req.json();
    const { jobId: jid, ...rest } = body;
    jobId = jid;
    payload = rest;
  } catch (err) {
    console.error("[analyze-background] Failed to parse body:", err.message);
    return;
  }

  if (!jobId) {
    console.error("[analyze-background] Missing jobId");
    return;
  }

  const store = getStore({ name: "analysis-results", consistency: "strong" });
  await store.setJSON(jobId, { status: "running", startedAt: Date.now() });

  try {
    // Expand blob_ref (Netlify Blobs, <4.5MB) et firebase_url (Firebase Storage, gros fichiers)
    for (const msg of (payload.messages || [])) {
      if (!Array.isArray(msg.content)) continue;
      for (let i = 0; i < msg.content.length; i++) {
        const item = msg.content[i];

        // Petit PDF via Netlify Blobs
        if (item && item.type === "blob_ref" && item.key) {
          try {
            const pdf = await store.get(item.key, { type: "json" });
            if (pdf && pdf.data) {
              msg.content[i] = {
                type: "document",
                source: { type: "base64", media_type: "application/pdf", data: pdf.data }
              };
              // NE PAS supprimer ici — l'agent Python doit pouvoir retélécharger
              // les PDFs pour les copier dans le dossier Bureau du client.
              // Le cleanup se fait via get-score-pdf?cleanup=true côté agent.
            } else {
              msg.content.splice(i, 1); i--;
            }
          } catch (e) {
            console.error("[analyze-background] blob_ref expand failed:", item.key, e.message);
            msg.content.splice(i, 1); i--;
          }
        }

        // Gros PDF en chunks (>4.5MB) — recoller les morceaux (legacy)
        else if (item && item.type === "chunked_ref" && item.key) {
          try {
            console.log("[analyze-background] Recoller chunks pour:", item.name || item.key);
            const meta = await store.get(`${item.key}_meta`, { type: "json" });
            if (!meta || !meta.totalChunks) throw new Error("Meta chunk introuvable");
            let fullBase64 = "";
            for (let c = 0; c < meta.totalChunks; c++) {
              const chunk = await store.get(`${item.key}_chunk_${c}`, { type: "json" });
              if (!chunk || !chunk.data) throw new Error(`Chunk ${c} introuvable`);
              fullBase64 += chunk.data;
            }
            // NE PAS supprimer ici (chunks ni meta) — agent fera cleanup
            msg.content[i] = {
              type: "document",
              source: { type: "base64", media_type: "application/pdf", data: fullBase64 }
            };
            console.log("[analyze-background] Gros PDF reconstitué:", Math.round(fullBase64.length * 0.75 / 1024 / 1024 * 10) / 10, "MB");
          } catch (e) {
            console.error("[analyze-background] chunked_ref failed:", item.name, e.message);
            msg.content.splice(i, 1); i--;
          }
        }

        // Gros PDF via Firebase Storage — passer l'URL publique directement à Claude
        else if (item && item.type === "firebase_url" && item.url) {
          try {
            console.log("[analyze-background] PDF Firebase URL:", item.name || item.path);
            msg.content[i] = {
              type: "document",
              source: { type: "url", url: item.url }
            };
          } catch (e) {
            console.error("[analyze-background] firebase_url failed:", item.name, e.message);
            msg.content.splice(i, 1); i--;
          }
        }
      }
    }

    const streamingPayload = Object.assign({}, payload, { stream: true });

    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "pdfs-2024-09-25"
      },
      body: JSON.stringify(streamingPayload)
    });

    if (!response.ok) {
      const errText = await response.text();
      console.error("[analyze-background] Claude API error:", response.status, errText);
      await store.setJSON(jobId, { status: "error", error: `API ${response.status}: ${errText}`, completedAt: Date.now() });
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let inputTokens = 0, outputTokens = 0;
    let contentBlocks = [], finalMessage = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const data = line.slice(6).trim();
        if (data === "[DONE]") continue;
        let evt; try { evt = JSON.parse(data); } catch { continue; }
        if (evt.type === "message_start" && evt.message) {
          inputTokens = evt.message.usage?.input_tokens || 0; finalMessage = evt.message;
        } else if (evt.type === "content_block_start") {
          contentBlocks[evt.index] = evt.content_block || { type: "text", text: "" };
        } else if (evt.type === "content_block_delta") {
          const block = contentBlocks[evt.index];
          if (block && evt.delta?.type === "text_delta") block.text = (block.text || "") + evt.delta.text;
        } else if (evt.type === "message_delta") {
          outputTokens = evt.usage?.output_tokens || outputTokens;
          if (finalMessage && evt.delta) Object.assign(finalMessage, evt.delta);
        }
      }
    }

    const result = Object.assign({}, finalMessage, {
      content: contentBlocks.filter(Boolean),
      usage: { input_tokens: inputTokens, output_tokens: outputTokens }
    });

    await store.setJSON(jobId, { status: "done", result, completedAt: Date.now() });
    console.log(`[analyze-background] Job ${jobId} done. in=${inputTokens} out=${outputTokens}`);

  } catch (err) {
    console.error(`[analyze-background] Job ${jobId} failed:`, err.message);
    await store.setJSON(jobId, { status: "error", error: err.message, completedAt: Date.now() });
  }
};
