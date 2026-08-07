// SUBMIT FAILURE AND RECOVERY
// The one failure a rater feels as "I did 25 minutes and lost it". The endpoint is an
// Apps Script web app and was measured returning Google's error HTML for roughly one
// anonymous request in four, so this path is not hypothetical.
//
//   A. endpoint dead at submit -> a fallback screen appears, holding the raw answers
//   B. the answers are still in localStorage, so nothing is lost
//   C. endpoint restored -> retry succeeds and the completion code appears
//
//   cd ~/cloudresearch_pilot && python3 -m http.server 8795 &
//   PLAYWRIGHT_PATH=... node tools/test_submit_failure.js

const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const PORT = process.env.PORT || 8795;
const U = 'http://localhost:' + PORT + '/index.html?participantId=SUBFAIL1&selftest=1';
const fails = [];
const ck = (c, l, d = '') => { if (!c) fails.push(l);
  console.log((c ? '  ok    ' : '  FAIL  ') + l + (!c && d ? '   [' + d + ']' : '')); };

(async () => {
 try {
  const b = await chromium.launch({ channel: 'chrome', args: ['--mute-audio'] });
  const ctx = await b.newContext();
  const p = await ctx.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));

  // Fill a complete session, then break the endpoint only for the SUBMIT.
  await p.goto(U, { waitUntil: 'domcontentloaded' });
  await p.waitForFunction(() => { const i = document.querySelector('#s-intro');
    return i && getComputedStyle(i).display !== 'none'; }, { timeout: 150000 });
  await p.locator('#btn-start').click();
  await p.waitForSelector('#gate-pct1_0', { state: 'attached', timeout: 60000 });
  await p.evaluate(() => {
    for (const s of [1, 2]) {
      watch[s].vids.forEach(v => { v.duration = 540; v.watched = 540; v.open = true; v.furthest = 540; });
      watch[s].open = true;
      const c = document.querySelector('#qs' + s + '-card'); if (c) c.classList.remove('locked');
      document.querySelectorAll('#qs' + s + '-card .q').forEach((q, i) => {
        const rs = q.querySelectorAll('input[type=radio]'); if (rs.length) rs[[4, 3, 2, 3][i % 4]].click(); });
      const cw = document.querySelector('#cw' + s);
      if (cw) { cw.value = 'w' + s; cw.dispatchEvent(new Event('input', { bubbles: true })); }
    }
    go(3);
    document.querySelectorAll('#h2h-qs .q').forEach(q => {
      const rs = q.querySelectorAll('input[type=radio]'); if (rs.length) rs[0].click();
      const ta = q.querySelector('textarea');
      if (ta) ta.value = 'A full answer that must survive a failed submission.'; });
  });
  await p.waitForTimeout(600);

  // --- A. break the endpoint, then submit ---------------------------------
  await p.route('**script.google.com**', r => r.abort());
  await p.evaluate(() => document.querySelector('#btn-submit').click());
  await p.waitForFunction(() => {
    const f = document.querySelector('#s-fallback');
    return f && getComputedStyle(f).display !== 'none';
  }, { timeout: 120000 }).catch(() => {});
  const st = await p.evaluate(() => ({
    fallback: (() => { const f = document.querySelector('#s-fallback');
      return f ? getComputedStyle(f).display !== 'none' : false; })(),
    done: (() => { const d = document.querySelector('#s-done');
      return d ? getComputedStyle(d).display !== 'none' : false; })(),
    text: (document.querySelector('#s-fallback') || {}).innerText || '',
  }));
  ck(st.fallback === true, 'a dead endpoint shows the fallback screen, not a dead page');
  ck(st.done === false, 'it does NOT claim success when nothing was saved');
  ck(/\{|answers|copy|paste|email/i.test(st.text),
     'the fallback holds the answers so they can be recovered by hand',
     JSON.stringify(st.text.slice(0, 80)));

  // --- B. work still in localStorage --------------------------------------
  const saved = await p.evaluate(() => {
    const k = Object.keys(localStorage).find(x => x.startsWith('embr_pilot'));
    return k ? JSON.parse(localStorage.getItem(k)) : null; });
  ck(!!(saved && saved.d && saved.d.s1_overall),
     'the session is still saved locally after the failure');

  // --- C. restore the endpoint and retry ----------------------------------
  await p.unroute('**script.google.com**');
  const retry = await p.evaluate(() => {
    const btn = [...document.querySelectorAll('#s-fallback button, button')]
      .find(x => /try again|retry|resend|submit/i.test(x.textContent) && x.offsetParent);
    if (btn) { btn.click(); return btn.textContent.trim(); }
    return null;
  });
  ck(retry !== null, 'the fallback offers a retry button', 'found: ' + retry);
  if (retry) {
    await p.waitForFunction(() => { const d = document.querySelector('#s-done');
      return d && getComputedStyle(d).display !== 'none'; }, { timeout: 120000 }).catch(() => {});
    const after = await p.evaluate(() => ({
      done: (() => { const d = document.querySelector('#s-done');
        return d ? getComputedStyle(d).display !== 'none' : false; })(),
      code: (document.querySelector('.code') || {}).textContent || '',
      receipt: (document.querySelector('#done-receipt') || {}).textContent || '' }));
    ck(after.done === true, 'retry against a live endpoint succeeds');
    ck(/EMBR7K2QX4/.test(after.code), 'the completion code is shown after recovery',
       JSON.stringify(after.code.trim()));
    console.log('        ' + after.receipt.trim());
  }
  ck(errs.length === 0, 'no js errors through the failure and recovery', errs.slice(0, 1).join(''));
  console.log('');
  console.log(fails.length ? fails.length + ' FAILED: ' + fails.join('; ')
                           : 'a failed submission cannot cost a rater their session');
  await b.close();
 } catch (e) { console.log('ERROR: ' + e.message); }
})();
