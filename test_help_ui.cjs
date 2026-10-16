/* Offline help stays in the app, with matching platform/language and no popup. */
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
(async () => {
  const root = path.join(__dirname, 'ui');
  const server = http.createServer((req, res) => {
    const pathname = new URL(req.url, 'http://localhost').pathname;
    if (pathname === '/test.html') {
      res.setHeader('Content-Type', 'text/html');
      return res.end('<link rel="stylesheet" href="style.css"><a id="open" href="help.html" target="_blank">Help</a><script>const S={data:{settings:{os:"posix"}}};window.SmartlightI18n={language:"en"};</script><script src="help-ui.js"></script>');
    }
    const file = path.join(root, path.basename(pathname));
    if (!fs.existsSync(file)) { res.writeHead(404); return res.end(); }
    res.setHeader('Content-Type', file.endsWith('.js') ? 'application/javascript' : file.endsWith('.css') ? 'text/css' : file.endsWith('.svg') ? 'image/svg+xml' : 'text/html');
    res.end(fs.readFileSync(file));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({headless:true, channel:'msedge'});
    const page = await browser.newPage({viewport:{width:1420,height:900}});
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(`http://127.0.0.1:${server.address().port}/test.html`);
    for (const os of ['posix', 'nt']) for (const language of ['en', 'it']) {
      await page.evaluate(({os,language}) => {S.data.settings.os=os;window.SmartlightI18n.language=language;}, {os,language});
      await page.locator('#open').click();
      const frame = page.frameLocator('#help-dialog iframe');
      await frame.locator('#help-language').waitFor();
      await page.waitForFunction(lang => document.querySelector('#help-dialog iframe').contentWindow.helpLanguage === lang, language);
      assert.equal(await frame.locator('#help-language').inputValue(), language);
      assert((await page.locator('#help-dialog iframe').getAttribute('src')).includes(os==='posix'?'help-linux.html':'help.html'));
      assert.equal(page.context().pages().length, 1);
      const box = await page.locator('#help-dialog').boundingBox();
      assert(box.x>=0 && box.y>=0 && box.x+box.width<=1420 && box.y+box.height<=900);
      if (os==='posix' && language==='en') {
        fs.mkdirSync('.testdata', {recursive:true});
        await page.screenshot({path:'.testdata/help-in-app.png'});
      }
      await frame.locator('a.brand').click();
      assert.equal(await page.locator('#help-dialog').isVisible(), false);
      await page.locator('#open').click();
      await page.locator('#help-dialog button').click();
      await page.locator('#open').click();
      await frame.locator('#help-language').focus();
      await page.keyboard.press('Escape');
      assert.equal(await page.locator('#help-dialog').isVisible(), false);
      assert.equal(await page.locator('#help-dialog').count(), 1);
    }
    assert.deepEqual(errors, []);
    console.log('Help: both platforms/languages, no browser popup, close/reopen/Escape and layout passed.');
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(e => { console.error(e); process.exitCode=1; });
