const { chromium } = require('playwright');

const HTTP_URL = process.env.HTTP_URL || 'http://localhost:6080/';
const HTTPS_URL = process.env.HTTPS_URL || 'https://localhost:6081/';

async function checkPage(browser, url, label, contextOpts = {}) {
  const errors = [];
  const logs = [];
  const context = await browser.newContext(contextOpts);
  const page = await context.newPage();
  page.on('console', msg => {
    logs.push(msg.text());
    if (msg.type() === 'error' && msg.text().includes('FATAL')) {
      errors.push(msg.text());
    }
  });
  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);
  const preflightPassed = logs.some(l => l.includes('Pre-flight checks passed'));
  const hasSecureContextError = logs.some(l => l.includes('Not in a secure context'));
  const hasVideoDecoderError = logs.some(l => l.includes('does not support the VideoDecoder'));
  console.log(`[${label}] Console logs: ${logs.length}, Pre-flight passed: ${preflightPassed}, Secure context error: ${hasSecureContextError}, VideoDecoder error: ${hasVideoDecoderError}, FATAL errors: ${errors.length}`);
  if (errors.length > 0) {
    errors.forEach(e => console.error(`  [${label}] ${e}`));
  }
  await context.close();
  if (hasSecureContextError || hasVideoDecoderError || errors.length > 0) {
    throw new Error(`${label}: Selkies web UI failed to initialize correctly`);
  }
  if (!preflightPassed) {
    throw new Error(`${label}: Selkies pre-flight checks did not pass`);
  }
  console.log(`[${label}] Selkies web UI loaded successfully`);
}

(async () => {
  const browser = await chromium.launch();
  try {
    await checkPage(browser, HTTPS_URL, 'HTTPS', { ignoreHTTPSErrors: true });
    await checkPage(browser, HTTP_URL, 'HTTP (localhost)');
  } catch (err) {
    console.error(`::error::${err.message}`);
    await browser.close();
    process.exit(1);
  }
  await browser.close();
  console.log('All browser checks passed');
})();
