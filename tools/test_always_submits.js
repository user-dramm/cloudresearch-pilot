// A COMPLETE ANSWER MUST ALWAYS SUBMIT
//
// The failure that costs most is the invisible one: a rater does everything asked and the
// form still will not let them finish. They abandon, you pay nothing and learn nothing,
// and they leave a review that slows your next study.
//
// So this walks many DIFFERENT complete answers, not one. Combinations that route through
// different branches of the form: the lowest narration rating, which reveals a conditional
// follow-up; the magnitude that hides the "why" box and the one that shows it; every
// optional box empty; every optional box full; long text; punctuation that has to survive
// JSON and a spreadsheet. Every one of them must reach the end screen.
//
//   cd ~/cloudresearch_pilot && python3 -m http.server 8795 &
//   PLAYWRIGHT_PATH=... node tools/test_always_submits.js

const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const PORT = process.env.PORT || 8795;
const fails = [];

const CASES = [
  { name: 'top marks, no writing',        rate: 4, mag: 'Much better',            text: '' },
  { name: 'bottom marks, no writing',     rate: 0, mag: 'Barely any difference',  text: '' },
  { name: 'lowest narration (reveals follow-up)', rate: 0, mag: 'Clearly better', text: 'ok' },
  { name: 'magnitude that HIDES why',     rate: 2, mag: 'Barely any difference',  text: 'ok' },
  { name: 'magnitude that SHOWS why',     rate: 2, mag: 'Clearly better',         text: 'ok' },
  { name: 'middle marks, long writing',   rate: 2, mag: 'Slightly better',
    text: 'This is a long answer. '.repeat(30) },
  { name: 'quotes, commas and newlines',  rate: 3, mag: 'Much better',
    text: 'She said "it was clearer", then, after a pause,\nadded: 100% better; worth it.' },
  { name: 'emoji and accents',            rate: 1, mag: 'Clearly better',
    text: 'Très clair \u{1F44D} the narrator’s tone was warm' },
];

(async () => {
 try {
  const b = await chromium.launch({ channel: 'chrome', args: ['--mute-audio'] });
  for (const [n, c] of CASES.entries()) {
    const p = await (await b.newContext()).newPage();
    const errs = []; p.on('pageerror', e => errs.push(String(e)));
    await p.goto('http://localhost:' + PORT + '/index.html?participantId=ALW' + n + '&selftest=1',
                 { waitUntil: 'domcontentloaded' });
    await p.waitForFunction(() => { const i = document.querySelector('#s-intro');
      return i && getComputedStyle(i).display !== 'none'; }, { timeout: 150000 });
    await p.locator('#btn-start').click();
    await p.waitForSelector('#gate-pct1_0', { state: 'attached', timeout: 60000 });
    await p.evaluate(cc => {
      for (const s of [1, 2]) {
        watch[s].vids.forEach(v => { v.duration = 540; v.watched = 540; v.open = true; v.furthest = 540; });
        watch[s].open = true;
        const card = document.querySelector('#qs' + s + '-card');
        if (card) card.classList.remove('locked');
        card.querySelectorAll('.q').forEach(q => {
          const rs = q.querySelectorAll('input[type=radio]');
          if (rs.length) rs[cc.rate].click();
        });
        const cw = document.querySelector('#cw' + s);
        if (cw) { cw.value = 'aword'; cw.dispatchEvent(new Event('input', { bubbles: true })); }
      }
      // Fill any conditional follow-up the low rating just revealed.
      for (const s of [1, 2]) {
        document.querySelectorAll('#qs' + s + '-card .q').forEach(q => {
          if (getComputedStyle(q).display === 'none') return;
          const t = q.querySelector('textarea, input[type=text]');
          if (t && !t.value && cc.text) { t.value = cc.text;
            t.dispatchEvent(new Event('input', { bubbles: true })); }
        });
      }
      go(3);
      const pick = (qid, val) => {
        const q = document.querySelector('[data-qid="' + qid + '"]'); if (!q) return;
        const r = [...q.querySelectorAll('input[type=radio]')].find(x => x.value === val)
               || q.querySelectorAll('input[type=radio]')[0];
        if (r) r.click();
      };
      pick('h2h_choice', 'The second video');
      pick('h2h_magnitude', cc.mag);
      pick('standby', 'Yes, with some reservations');
      document.querySelectorAll('#h2h-qs .q').forEach(q => {
        if (getComputedStyle(q).display === 'none') return;
        const ta = q.querySelector('textarea');
        if (ta && cc.text) { ta.value = cc.text; ta.dispatchEvent(new Event('input', { bubbles: true })); }
      });
      document.querySelector('#btn-submit').click();
    }, c);

    await p.waitForFunction(() => {
      const shown = x => x && getComputedStyle(x).display !== 'none';
      return shown(document.querySelector('#s-done')) ||
             shown(document.querySelector('#s-fallback')) ||
             [...document.querySelectorAll('.err.show')].some(e => e.textContent.trim());
    }, { timeout: 90000 }).catch(() => {});
    const r = await p.evaluate(() => {
      const shown = x => x && getComputedStyle(x).display !== 'none';
      return { done: shown(document.querySelector('#s-done')),
               fb: shown(document.querySelector('#s-fallback')),
               err: ([...document.querySelectorAll('.err.show')]
                      .map(e => e.textContent.trim()).filter(Boolean)[0] || '').slice(0, 60) };
    });
    const okNow = r.done || r.fb;
    if (!okNow) fails.push(c.name + ' -> "' + r.err + '"');
    if (errs.length) fails.push(c.name + ' threw: ' + errs[0].slice(0, 50));
    console.log('  ' + (okNow ? 'ok    ' : 'FAIL  ') + c.name.padEnd(34) +
                (okNow ? (r.done ? 'submitted and saved' : 'submitted, fallback shown')
                       : 'BLOCKED: ' + r.err));
    await p.context().close();
  }
  await b.close();
  console.log('');
  console.log(fails.length ? fails.length + ' FAILED: ' + fails.join('; ')
    : 'every complete answer submits, whichever route through the form it took');
  process.exit(fails.length ? 1 : 0);
 } catch (e) { console.log('ERROR: ' + e.message); process.exit(1); }
})();
