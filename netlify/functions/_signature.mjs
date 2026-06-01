/**
 * Helper signatures email Capital Norvex (clone JS de agents/shared/signature_block.py).
 *
 * Charge les PNG compressés (~49KB logo + ~217KB signature manuscrite) au démarrage
 * et les encode en base64 inline.
 *
 * Décision Yves 2026-05-05 : base64 inline avec versions COMPRESSÉES (`-mail.png`).
 * Outlook bloque les images externes par défaut (URL hostée invisible jusqu'à clic
 * « Charger les images »), donc inline. Versions compressées pour rester sous la
 * limite 1MB de Firestore signedHtml.
 *
 * Bug fix 2026-05-08 : avant ce fichier, `beatrice-create-draft.mjs`,
 * `beatrice-refine-draft.mjs` et `camille-create-draft.mjs` avaient chacun leur
 * clone JS avec un fallback texte « M » au lieu du vrai logo PNG.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));

// ─── Chargement des PNG compressés au démarrage ────────────────────────────

function loadAssetDataUri(filename) {
  const tryPaths = [
    path.join(HERE, "assets", filename),
    // Fallback : repo root (pour dev local)
    path.join(HERE, "..", "..", "assets", filename),
    path.join(HERE, "..", "..", filename),
  ];
  for (const p of tryPaths) {
    try {
      if (fs.existsSync(p)) {
        const buf = fs.readFileSync(p);
        return `data:image/png;base64,${buf.toString("base64")}`;
      }
    } catch {
      // ignore et essaie le suivant
    }
  }
  return "";
}

const LOGO_DATA_URI = loadAssetDataUri("logo-norvex-officiel-mail.png");
const SIG_YVES_DATA_URI = loadAssetDataUri("Signature-Yves-mail.png");

// ─── Couleurs / identité (synchro Python) ──────────────────────────────────

const COLOR_INK = "#0A0A0A";
const COLOR_GOLD = "#C8B070";
const COLOR_GOLD_DARK = "#9A8554";
const COLOR_TEXT = "#222";
const COLOR_MUTED = "#666";
const COLOR_FAINT = "#888";

const COMPANY_NAME = "Capital Norvex Inc.";
const COMPANY_TAGLINE_FR = "Capital structuré. Ambition maîtrisée.";
const COMPANY_TAGLINE_EN = "Structured capital. Measured ambition.";
const COMPANY_PHONE_DISPLAY_FR = "438-533-PRÊT (7738)";
const COMPANY_PHONE_DISPLAY_EN = "+1 (438) 533-PRÊT (7738)";
const COMPANY_PHONE_HREF = "+14385337738";

const COMPANY_ADDRESS_HTML =
  "2705-1000 André-Prévost<br>Île-des-Sœurs (Verdun)<br>Montréal, QC H3E 0G2";

const CONFIDENTIALITY_FR =
  "Ce message et tout document joint sont strictement confidentiels et destinés exclusivement au destinataire désigné. Toute diffusion, copie, distribution ou utilisation non autorisée est interdite et peut faire l'objet de poursuites. Si vous avez reçu ce courriel par erreur, veuillez le supprimer immédiatement et en aviser l'expéditeur.";

const CONFIDENTIALITY_EN =
  "This message and any attached documents are strictly confidential and intended exclusively for the designated recipient. Any unauthorized disclosure, copying, distribution or use is prohibited and may be subject to legal action. If you received this email in error, please delete it immediately and notify the sender.";

// ─── Signature Yves (style noir horizontal compact) ───────────────────────
// Clone de build_dark_signature_block() + signature_yves() en Python.

export function signatureYvesHtml(language = "fr") {
  const isEn = language === "en";
  const tagline = isEn ? COMPANY_TAGLINE_EN : COMPANY_TAGLINE_FR;
  const phoneDisplay = isEn ? COMPANY_PHONE_DISPLAY_EN : COMPANY_PHONE_DISPLAY_FR;
  const titleMain = isEn ? "Founder & Director" : "Directeur-Fondateur";
  const titleSub = isEn
    ? "Commercial real estate financing"
    : "Financement immobilier commercial";
  const closingWord = isEn ? "Best regards" : "Cordialement";
  const confidentiality = isEn ? CONFIDENTIALITY_EN : CONFIDENTIALITY_FR;

  // Closing au-dessus du bandeau noir
  const closingHtml = `<p style="margin:0 0 12px 0;font-family:Georgia,serif;font-size:13.5px;color:${COLOR_TEXT};">${closingWord},</p>`;

  // Image manuscrite scannée DÉSACTIVÉE 2026-05-11 PM (préférence Yves :
  // une seule signature visuelle = bandeau noir uniquement, pas de double
  // signature dans les courriels). Voir preference_signature_simple_2026-05-11.md.
  const manuscriptHtml = "";

  // Cellule logo gauche : vrai PNG si disponible, sinon fallback texte « M »
  const logoCell = LOGO_DATA_URI
    ? `<td valign="middle" align="center" style="width:90px;padding:0 10px 0 4px;background:${COLOR_INK};"><img src="${LOGO_DATA_URI}" alt="Capital Norvex" style="width:78px;height:auto;display:block;"></td>`
    : `<td valign="middle" align="center" style="width:90px;padding:0 10px;background:${COLOR_INK};color:${COLOR_GOLD};font-family:Georgia,serif;font-weight:bold;font-size:28px;letter-spacing:4px;">M</td>`;

  const textCell = `<td valign="middle" style="padding:13px 16px 13px 4px;background:${COLOR_INK};font-family:Georgia,serif;color:#FFFFFF;line-height:1.45;">
<div style="font-size:16px;color:#FFFFFF;letter-spacing:0.4px;">Yves Barrette</div>
<div style="font-size:11px;color:${COLOR_GOLD};margin-top:1px;font-style:italic;letter-spacing:0.2px;">${titleMain}<span style="color:${COLOR_GOLD};font-style:italic;font-size:10.5px;"> | ${titleSub}</span></div>
<div style="font-size:11.5px;color:#FFFFFF;font-weight:bold;margin-top:6px;letter-spacing:0.3px;">${COMPANY_NAME}</div>
<div style="font-size:10px;color:${COLOR_GOLD};font-style:italic;margin-top:1px;letter-spacing:0.4px;">${tagline}</div>
<div style="font-family:Arial,Helvetica,sans-serif;font-variant-numeric:tabular-nums lining-nums;font-size:10.5px;color:#E8E8E8;margin-top:7px;white-space:nowrap;letter-spacing:0.2px;line-height:1.4;">
<span style="color:${COLOR_GOLD};font-style:italic;">Tél.</span>&nbsp;<a href="tel:${COMPANY_PHONE_HREF}" style="color:#E8E8E8;text-decoration:none;">${phoneDisplay}</a><span style="color:${COLOR_GOLD};">&nbsp;&nbsp;·&nbsp;&nbsp;</span><a href="mailto:yves@capitalnorvex.com" style="color:#E8E8E8;text-decoration:none;">yves@capitalnorvex.com</a>
</div>
<div style="font-family:Arial,Helvetica,sans-serif;font-variant-numeric:tabular-nums lining-nums;font-size:9.5px;color:#BBBBBB;margin-top:4px;line-height:1.4;">${COMPANY_ADDRESS_HTML}</div>
<div style="font-size:8.5px;color:#999999;font-style:italic;margin-top:7px;line-height:1.4;border-top:1px solid #333;padding-top:6px;">${confidentiality}</div>
</td>`;

  return `<div style="margin-top:28px;max-width:520px;">${closingHtml}${manuscriptHtml}<table role="presentation" cellpadding="0" cellspacing="0" style="border-collapse:collapse;background:${COLOR_INK};max-width:520px;width:100%;border:1px solid ${COLOR_GOLD_DARK};"><tr>${logoCell}${textCell}</tr></table></div>`;
}

// ─── Signature Camille (style clair institutionnel + bandeau noir + logo) ──
// Clone simplifié de build_signature_block() + signature_camille() en Python.

export function signatureCamilleHtml(language = "fr") {
  const isEn = language === "en";
  const tagline = isEn ? COMPANY_TAGLINE_EN : COMPANY_TAGLINE_FR;
  const confidentiality = isEn ? CONFIDENTIALITY_EN : CONFIDENTIALITY_FR;
  const title = isEn ? "Legal Coordinator" : "Coordonnatrice juridique";
  const ai = isEn
    ? "Camille is an AI legal coordinator at Capital Norvex Inc. All financial and legal decisions are made and approved by management."
    : "Camille est une coordonnatrice juridique IA de Capital Norvex Inc. Toutes les décisions financières et juridiques sont prises et validées par la direction.";
  const bar = isEn
    ? "Any legal decision remains that of the retained professional advisors."
    : "Toute décision juridique demeure celle des conseillers professionnels mandatés.";

  // Bandeau noir avec logo centré
  const logoHtml = LOGO_DATA_URI
    ? `<img src="${LOGO_DATA_URI}" alt="Capital Norvex" style="max-width:140px;height:auto;display:block;margin:0 auto;">`
    : `<div style="font-family:Georgia,serif;font-size:22px;letter-spacing:4px;color:${COLOR_GOLD};font-weight:bold;">CAPITAL NORVEX</div>`;

  const headerHtml = `<table role="presentation" cellpadding="0" cellspacing="0" style="border-collapse:collapse;width:100%;max-width:560px;"><tr><td style="background:${COLOR_INK};padding:18px 24px;text-align:center;">${logoHtml}<div style="margin-top:8px;color:${COLOR_GOLD};font-family:Georgia,serif;font-style:italic;font-size:11px;letter-spacing:1.5px;">${tagline}</div></td></tr><tr><td style="height:2px;background:linear-gradient(90deg, transparent 0%, ${COLOR_GOLD} 50%, transparent 100%);"></td></tr></table>`;

  const identityHtml = `<div style="margin-top:14px;font-family:Georgia,serif;font-size:13px;line-height:1.55;color:${COLOR_TEXT};">
<strong style="font-size:14.5px;">Camille</strong><br>
<em style="color:${COLOR_MUTED};font-style:italic;">${title}</em><br>
<span style="color:${COLOR_MUTED};">NORVEX COUNSEL™ — ${COMPANY_NAME}</span><br>
<span style="color:${COLOR_MUTED};font-size:12.5px;">${COMPANY_ADDRESS_HTML}</span><br>
<span style="font-size:12.5px;margin-top:4px;display:inline-block;"><a href="mailto:camille@capitalnorvex.com" style="color:${COLOR_TEXT};text-decoration:none;">camille@capitalnorvex.com</a> &nbsp;·&nbsp; <a href="https://capitalnorvex.com" style="color:${COLOR_TEXT};text-decoration:none;">capitalnorvex.com</a></span>
</div>`;

  const extrasHtml = `<p style="margin:8px 0 0 0;font-family:Arial,sans-serif;font-size:11px;line-height:1.5;color:${COLOR_FAINT};font-style:italic;">${ai} ${bar}</p>`;

  const confidentialityHtml = `<p style="margin:14px 0 0 0;font-family:Arial,sans-serif;font-size:10.5px;line-height:1.5;color:${COLOR_FAINT};font-style:italic;border-top:1px solid #DDD;padding-top:10px;">${confidentiality}</p>`;

  return `<div style="margin-top:32px;max-width:560px;">${headerHtml}<div style="padding:0 4px;">${identityHtml}${extrasHtml}${confidentialityHtml}</div></div>`;
}
