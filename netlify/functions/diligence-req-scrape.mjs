/**
 * POST /api/diligence-req-scrape
 * Header: x-internal-secret
 * Body: { neq?: string, name?: string }
 *
 * Automatise la recherche au Registre des entreprises du Québec (REQ) via
 * Chromium headless (Sparticuz + puppeteer-core).
 *
 * Workflow :
 *   1. Lance Chromium serverless
 *   2. Navigue vers la page de recherche REQ (ASP.NET MVC nouvelle gen)
 *   3. Coche la case "Je reconnais avoir lu... conditions d'utilisation"
 *   4. Remplit le champ "Objet de la recherche" (NEQ ou nom)
 *   5. Clique "Rechercher"
 *   6. Attend le rendu des résultats
 *   7. Capture le HTML de la liste de résultats
 *   8. Si recherche par NEQ et 1 seul résultat → clique "Consulter" pour fiche détaillée
 *   9. Retourne { html, screenshot, source_url }
 *
 * Le HTML est ensuite passé à Claude (côté Python) pour analyse niveau avocat.
 *
 * Timeout : 60 sec (Netlify Functions standard)
 * Cold start : ~3-5 sec (Chromium binary)
 */

import chromium from "@sparticuz/chromium";
import puppeteerCore from "puppeteer-core";
import { addExtra } from "puppeteer-extra";
import StealthPlugin from "puppeteer-extra-plugin-stealth";

// Wrap puppeteer-core avec puppeteer-extra + stealth pour bypass anti-bot
const puppeteer = addExtra(puppeteerCore);
puppeteer.use(StealthPlugin());

const REQ_SEARCH_URL =
  "https://www.registreentreprises.gouv.qc.ca/REQNA/GR/GR03/GR03A71.RechercheRegistre.MVC/Index";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function launchBrowser() {
  // Args supplémentaires pour camoufler le navigateur headless
  const stealthArgs = [
    ...chromium.args,
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
  ];
  return await puppeteer.launch({
    args: stealthArgs,
    defaultViewport: { width: 1366, height: 768 },
    executablePath: await chromium.executablePath(),
    headless: chromium.headless,
    ignoreHTTPSErrors: true,
  });
}

async function waitForCloudflare(page, maxMs = 15000) {
  // Si "Just a moment..." est affiché, on attend que le challenge passe
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    const title = await page.title().catch(() => "");
    if (!/just a moment|un instant|moment/i.test(title)) return true;
    await new Promise((r) => setTimeout(r, 1500));
  }
  return false;
}

async function scrapeREQ({ neq, name }) {
  const browser = await launchBrowser();
  let page;
  try {
    page = await browser.newPage();
    await page.setUserAgent(
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    );

    // 1. Page de recherche REQ
    await page.goto(REQ_SEARCH_URL, {
      waitUntil: "domcontentloaded",
      timeout: 30000,
    });

    // 1bis. Attendre que Cloudflare challenge passe (si présent)
    const cfPassed = await waitForCloudflare(page, 15000);
    if (!cfPassed) {
      const title = await page.title().catch(() => "");
      throw new Error(`Cloudflare challenge non résolu (title: ${title})`);
    }
    // Marge supplémentaire après CF pour rendu complet
    await new Promise((r) => setTimeout(r, 1500));

    // 2. Cocher case conditions d'utilisation
    //    Le checkbox a typiquement id "ConditionsUtilisation" ou similaire
    const cguChecked = await page.evaluate(() => {
      const candidates = Array.from(
        document.querySelectorAll('input[type="checkbox"]')
      );
      for (const cb of candidates) {
        const label =
          cb.parentElement?.textContent ||
          cb.closest("label")?.textContent ||
          "";
        if (
          /conditions.*utilisation|reconnais avoir lu/i.test(label) &&
          !cb.checked
        ) {
          cb.click();
          return true;
        }
      }
      return false;
    });

    // 3. Remplir le champ "Objet de la recherche"
    const query = (neq || name || "").trim();
    if (!query) throw new Error("NEQ ou nom requis");

    await page.evaluate((q) => {
      const inputs = Array.from(
        document.querySelectorAll(
          'input[type="text"], input[type="search"], input:not([type])'
        )
      );
      // Priorité : input avec name/id contenant "objet" ou "recherche"
      let target =
        inputs.find((i) => /objet|recherche/i.test(i.name + " " + i.id)) ||
        inputs.find((i) => i.placeholder && /entreprise|nom/i.test(i.placeholder)) ||
        inputs[0];
      if (target) {
        target.focus();
        target.value = q;
        target.dispatchEvent(new Event("input", { bubbles: true }));
        target.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }, query);

    // 4. Cliquer "Rechercher"
    const clickResult = await page.evaluate(() => {
      const buttons = Array.from(
        document.querySelectorAll(
          'button, input[type="submit"], input[type="button"], a[role="button"]'
        )
      );
      const allButtons = buttons.map((b) => ({
        tag: b.tagName,
        type: b.type || "",
        text: (b.textContent || b.value || "").trim().slice(0, 50),
        id: b.id,
        name: b.name,
        cls: b.className.slice(0, 80),
      }));
      const target = buttons.find((b) => {
        const txt = (b.textContent || b.value || "").trim().toLowerCase();
        return /^rechercher$|chercher|submit|envoyer/.test(txt);
      });
      if (target) {
        target.click();
        return { clicked: true, allButtons };
      }
      return { clicked: false, allButtons };
    });

    if (!clickResult.clicked) {
      // Debug : retourne ce qu'on a trouvé pour comprendre la structure
      const initialHtml = await page.content();
      throw new Error(
        `Bouton Rechercher introuvable. Boutons détectés : ${JSON.stringify(
          clickResult.allButtons
        )}. URL: ${page.url()}. HTML head: ${initialHtml.slice(0, 800)}`
      );
    }

    // 5. Attendre la page de résultats (navigation ou rendu AJAX)
    await page
      .waitForNavigation({ waitUntil: "networkidle2", timeout: 20000 })
      .catch(() => {}); // Parfois c'est AJAX, pas navigation
    await new Promise((r) => setTimeout(r, 2000)); // marge de rendu

    // 6. Si recherche par NEQ et 1 seul résultat → cliquer "Consulter"
    let detailFetched = false;
    if (neq) {
      const consulted = await page.evaluate(() => {
        const links = Array.from(document.querySelectorAll("a, button"));
        const target = links.find((l) =>
          /consulter|d[ée]tail/i.test((l.textContent || "").trim())
        );
        if (target) {
          target.click();
          return true;
        }
        return false;
      });
      if (consulted) {
        await page
          .waitForNavigation({ waitUntil: "networkidle2", timeout: 20000 })
          .catch(() => {});
        await new Promise((r) => setTimeout(r, 1500));
        detailFetched = true;
      }
    }

    // 7. Capture HTML + URL finale
    const finalUrl = page.url();
    const finalHtml = await page.content();

    return {
      ok: true,
      query,
      cguChecked,
      detailFetched,
      finalUrl,
      html: finalHtml,
      htmlLength: finalHtml.length,
    };
  } finally {
    if (page) await page.close().catch(() => {});
    await browser.close().catch(() => {});
  }
}

export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-internal-secret",
      },
    });
  }

  if (req.method !== "POST") {
    return json({ error: "Method not allowed" }, 405);
  }

  const secret = req.headers.get("x-internal-secret");
  if (!process.env.INTERNAL_SECRET || secret !== process.env.INTERNAL_SECRET) {
    return json({ error: "Unauthorized" }, 401);
  }

  let body;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON" }, 400);
  }

  const { neq, name } = body || {};
  if (!neq && !name) {
    return json({ error: "neq ou name requis" }, 400);
  }

  try {
    const result = await scrapeREQ({ neq, name });
    return json(result);
  } catch (e) {
    return json(
      {
        ok: false,
        error: e.message,
        stack: e.stack?.slice(0, 600),
      },
      500
    );
  }
};

export const config = {
  path: "/api/diligence-req-scrape",
};
