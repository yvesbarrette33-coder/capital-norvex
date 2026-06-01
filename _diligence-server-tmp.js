const express = require('express');
const { chromium } = require('playwright');
require('dotenv').config({ path: '/opt/norvex-diligence/.env' });

const TOKEN = process.env.DILIGENCE_TOKEN;
const PORT = process.env.PORT || 3000;
const VERSION = '2.0.0';

if (!TOKEN) {
  console.error('FATAL: DILIGENCE_TOKEN not set');
  process.exit(1);
}

const app = express();
app.use(express.json({ limit: '1mb' }));

function auth(req, res, next) {
  const h = req.headers.authorization || '';
  const provided = h.replace(/^Bearer\s+/i, '');
  if (provided !== TOKEN) return res.status(401).json({ error: 'Unauthorized' });
  next();
}

// User agent + context standard
async function newCtx(browser) {
  return browser.newContext({
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    locale: 'fr-CA',
    timezoneId: 'America/Toronto',
    viewport: { width: 1366, height: 900 },
  });
}

// Helper : essaie plusieurs sélecteurs jusqu'à trouver un champ visible
async function tryFill(page, selectors, value) {
  for (const sel of selectors) {
    try {
      const loc = page.locator(sel).first();
      if (await loc.isVisible({ timeout: 2000 })) {
        await loc.fill(String(value));
        return sel;
      }
    } catch {}
  }
  return null;
}

async function tryClick(page, selectors) {
  for (const sel of selectors) {
    try {
      const loc = page.locator(sel).first();
      if (await loc.isVisible({ timeout: 2000 })) {
        await loc.click();
        return sel;
      }
    } catch {}
  }
  return null;
}

// Helper debug : retourne info sur la page (title, url, inputs visibles, body preview)
async function debugPage(page, errorMsg) {
  const title = await page.title().catch(() => '');
  const url = page.url();
  const bodyText = await page.evaluate(() => document.body?.innerText || '').catch(() => '');
  const inputs = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('input, button, select, textarea')).slice(0, 30).map(el => ({
      tag: el.tagName.toLowerCase(),
      type: el.type || null,
      id: el.id || null,
      name: el.name || null,
      placeholder: el.placeholder || null,
      value: (el.value || '').slice(0, 80) || null,
      visible: !!(el.offsetWidth || el.offsetHeight),
    }));
  }).catch(() => []);
  return {
    error: errorMsg,
    debug: { title, url, body_preview: bodyText.slice(0, 1500), inputs },
  };
}

// ─── Health ──────────────────────────────────────────────────
app.get('/health', (req, res) => {
  res.json({ ok: true, service: 'norvex-diligence', version: VERSION, ts: new Date().toISOString() });
});

// ─── REQ ─────────────────────────────────────────────────────
app.post('/scrape-req', auth, async (req, res) => {
  const { neq, name } = req.body || {};
  if (!neq && !name) return res.status(400).json({ error: 'Provide neq or name' });
  let browser;
  try {
    browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
    const ctx = await newCtx(browser);
    const page = await ctx.newPage();
    await page.goto('https://www.registreentreprises.gouv.qc.ca/RQEntrepriseGRPublic/GR/GR03/GR03A2_19A_PIU_RechEnt_PC/PageRechSimple.aspx', { waitUntil: 'networkidle', timeout: 30000 });

    // Accept conditions if present
    await tryClick(page, [
      'text=/J.accepte/i',
      'button:has-text("Accepter")',
      'a:has-text("Continuer")',
    ]);
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    // Fill NEQ or name
    let filled;
    if (neq) {
      filled = await tryFill(page, [
        'input[id*="NEQ" i]',
        'input[name*="NEQ" i]',
        'input[id*="numEntr" i]',
        'input[name*="numEntr" i]',
        'input[type="text"]:visible',
      ], neq);
    } else {
      filled = await tryFill(page, [
        'input[id*="NomAssuj" i]',
        'input[name*="NomAssuj" i]',
        'input[id*="nom" i][type="text"]',
        'input[type="text"]:visible',
      ], name);
    }

    if (!filled) {
      const dbg = await debugPage(page, 'REQ: input field not found');
      return res.status(500).json(dbg);
    }

    // Submit
    await tryClick(page, [
      'input[value*="Rechercher" i]',
      'button:has-text("Rechercher")',
      'input[type="submit"]',
    ]);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});

    const text = await page.evaluate(() => document.body.innerText).catch(() => '');
    const url = page.url();
    res.json({
      ok: true,
      registre: 'REQ',
      query: { neq, name },
      filled_selector: filled,
      url,
      text: text.slice(0, 8000),
      text_size: text.length,
    });
  } catch (e) {
    let dbg = { error: e.message };
    try { dbg = await debugPage(req._page, e.message); } catch {}
    res.status(500).json(dbg);
  } finally {
    if (browser) await browser.close();
  }
});

// ─── RBQ ─────────────────────────────────────────────────────
// Régie du bâtiment du Québec — registre public des détenteurs de licence
app.post('/scrape-rbq', auth, async (req, res) => {
  const { licence, name, neq } = req.body || {};
  if (!licence && !name && !neq) {
    return res.status(400).json({ error: 'Provide licence, name or neq' });
  }
  let browser;
  try {
    browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
    const ctx = await newCtx(browser);
    const page = await ctx.newPage();

    // RBQ entry URL (registre public)
    await page.goto('https://www.rbq.gouv.qc.ca/registre-des-detenteurs-de-licence/', {
      waitUntil: 'networkidle', timeout: 30000,
    });

    // Accept cookies/conditions if banner shows
    await tryClick(page, [
      'button:has-text("Accepter")',
      'button:has-text("J\'accepte")',
      'a:has-text("Accepter")',
    ]);

    // Fill licence > NEQ > name (priority order)
    let filled;
    if (licence) {
      filled = await tryFill(page, [
        'input[name*="numLicence" i]',
        'input[id*="numLicence" i]',
        'input[name*="licence" i]',
        'input[id*="licence" i]',
        'input[placeholder*="licence" i]',
      ], licence);
    } else if (neq) {
      filled = await tryFill(page, [
        'input[name*="NEQ" i]',
        'input[id*="NEQ" i]',
        'input[placeholder*="NEQ" i]',
      ], neq);
    } else {
      filled = await tryFill(page, [
        'input[name*="raisonSociale" i]',
        'input[id*="raisonSociale" i]',
        'input[name*="nomEntreprise" i]',
        'input[name*="nom" i]',
        'input[placeholder*="entreprise" i]',
      ], name);
    }

    if (!filled) {
      const dbg = await debugPage(page, 'RBQ: input field not found');
      return res.status(500).json(dbg);
    }

    // Submit
    await tryClick(page, [
      'button:has-text("Rechercher")',
      'input[value*="Rechercher" i]',
      'button[type="submit"]',
      'input[type="submit"]',
    ]);
    await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});

    const text = await page.evaluate(() => document.body.innerText).catch(() => '');
    const url = page.url();
    res.json({
      ok: true,
      registre: 'RBQ',
      query: { licence, name, neq },
      filled_selector: filled,
      url,
      text: text.slice(0, 8000),
      text_size: text.length,
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  } finally {
    if (browser) await browser.close();
  }
});

// ─── DEBUG : retourne le HTML/structure d'une URL pour ajuster sélecteurs ──
app.post('/debug-url', auth, async (req, res) => {
  const { url } = req.body || {};
  if (!url) return res.status(400).json({ error: 'Provide url' });
  let browser;
  try {
    browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
    const ctx = await newCtx(browser);
    const page = await ctx.newPage();
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    const dbg = await debugPage(page, 'debug snapshot');
    res.json({ ok: true, ...dbg });
  } catch (e) {
    res.status(500).json({ error: e.message });
  } finally {
    if (browser) await browser.close();
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Norvex Diligence API v${VERSION} live on port ${PORT}`);
});
