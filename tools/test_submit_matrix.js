// CAN THEY SUBMIT, AND DOES IT COUNT?
//
// The two questions are separate and constantly conflated. A gate either stops someone
// finishing, or it lets them finish and keeps their row out of the average. Getting that
// backwards is expensive in both directions: a gate that blocks wrongly loses a paid
// session, and a gate that counts wrongly poisons the result.
//
// This drives the real form through each failure mode and reports which happened.
//
//   cd ~/cloudresearch_pilot && python3 -m http.server 8795 &
//   PLAYWRIGHT_PATH=... node tools/test_submit_matrix.js

const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const PORT = process.env.PORT || 8795;
const rows = [];
const fails = [];

async function run(b, label, opts) {
  const p = await (await b.newContext()).newPage();
  const errs = [];
  p.on('pageerror', e => errs.push(String(e)));
  await p.goto('http://localhost:' + PORT + '/index.html?participantId=MTX' +
               Math.abs(label.length * 977 % 9999) + '&selftest=1',
               { waitUntil: 'domcontentloaded' });
  await p.waitForFunction(() => { const i = document.querySelector('#s-intro');
    return i && getComputedStyle(i).display !== 'none'; }, { timeout: 150000 });
  await p.locator('#btn-start').click();
  await p.waitForSelector('#gate-pct1_0', { state: 'attached', timeout: 60000 });

  const out = await p.evaluate(o => {
    const res = { blockedAt: null, msg: '', submitted: false };
    for (const s of [1, 2]) {
      // Grant the watch gate unless the scenario is specifically about not watching.
      if (!(o.underWatch && s === 1)) {
        watch[s].vids.forEach(v => { v.duration = 540; v.watched = 540; v.open = true; v.furthest = 540; });
        watch[s].open = true;
        const c = document.querySelector('#qs' + s + '-card'); if (c) c.classList.remove('locked');
      } else {
        watch[s].vids.forEach(v => { v.duration = 540; v.watched = 200; v.open = false; });
        watch[s].open = false;
      }
      document.querySelectorAll('#qs' + s + '-card .q').forEach((q, i) => {
        if (o.missRating && s === 1 && i === 1) return;      // leave one rating blank
        const rs = q.querySelectorAll('input[type=radio]');
        if (rs.length) rs[[4, 3, 2, 3][i % 4]].click();
      });
      const cw = document.querySelector('#cw' + s);
      if (cw) {
        let v = 'CORRECTWORD';
        if (o.blankCw && s === 1) v = '';
        if (o.wrongOne && s === 1) v = 'zzznotit';
        if (o.wrongBoth) v = 'zzznotit';
        cw.value = v; cw.dispatchEvent(new Event('input', { bubbles: true }));
      }
    }
    // Try to leave section 1 the way a rater does.
    const cont = () => [...document.querySelectorAll('button')]
      .find(x => /continue/i.test(x.textContent) && x.offsetParent);
    const before = getComputedStyle(document.querySelector('#s-v1')).display;
    const b1 = cont(); if (b1) b1.click();
    const movedOn = getComputedStyle(document.querySelector('#s-v1')).display !== before
                 || getComputedStyle(document.querySelector('#s-v1')).display === 'none';
    if (!movedOn) {
      const e = [...document.querySelectorAll('.err.show, .show')]
        .map(x => x.textContent.trim()).filter(Boolean);
      res.blockedAt = 'video 1 Continue';
      res.msg = (e[0] || '').slice(0, 70);
      return res;
    }
    go(3);
    document.querySelectorAll('#h2h-qs .q').forEach(q => {
      if (getComputedStyle(q).display === 'none') return;
      if (o.noChoice && q.dataset.qid === 'h2h_choice') return;
      if (o.blankOptional && /comment|other|why/.test(q.dataset.qid || '')) return;
      const rs = q.querySelectorAll('input[type=radio]');
      if (rs.length && !q.querySelector('input[type=radio]:checked')) rs[0].click();
      const ta = q.querySelector('textarea');
      if (ta && !o.blankOptional) ta.value = 'A real sentence of feedback.';
    });
    // Click and RETURN. Whether it went through is decided outside, by waiting: the
    // submit is a network call, so the end screen is still on display for a moment
    // afterwards. Reading the DOM immediately made every successful submission look
    // blocked, which is the opposite of the truth and the sort of result that would
    // have had us "fixing" a form that was working.
    document.querySelector('#btn-submit').click();
    res.clicked = true;
    return res;
  }, opts);

  // Decide by WAITING: either an end screen appears, or validation refused and we are
  // still on the head-to-head with a message.
  if (out.clicked) {
    await p.waitForFunction(() => {
      const d = document.querySelector('#s-done'), f = document.querySelector('#s-fallback');
      const shown = x => x && getComputedStyle(x).display !== 'none';
      if (shown(d) || shown(f)) return true;
      return [...document.querySelectorAll('.err.show')].some(e => e.textContent.trim());
    }, { timeout: 90000 }).catch(() => {});
    const after = await p.evaluate(() => {
      const shown = x => x && getComputedStyle(x).display !== 'none';
      return {
        done: shown(document.querySelector('#s-done')),
        fallback: shown(document.querySelector('#s-fallback')),
        err: ([...document.querySelectorAll('.err.show')]
               .map(e => e.textContent.trim()).filter(Boolean)[0] || '').slice(0, 70),
      };
    });
    out.submitted = after.done || after.fallback;
    out.done = after.done;
    if (!out.submitted) { out.blockedAt = 'Submit'; out.msg = after.err; }
  }
  rows.push({ label, ...out, errs: errs.length });
  await p.context().close();
}

(async () => {
 try {
  const b = await chromium.launch({ channel: 'chrome', args: ['--mute-audio'] });
  await run(b, 'everything correct',                {});
  await run(b, 'optional boxes left blank',         { blankOptional: true });
  await run(b, 'code word wrong on ONE video',      { wrongOne: true });
  await run(b, 'code word wrong on BOTH videos',    { wrongBoth: true });
  await run(b, 'code word left blank',              { blankCw: true });
  await run(b, 'one rating not answered',           { missRating: true });
  await run(b, 'no head-to-head choice',            { noChoice: true });
  await run(b, 'has not watched enough',            { underWatch: true });
  await b.close();

  console.log('');
  console.log('  SCENARIO                          CAN THEY SUBMIT?   WHERE THEY ARE STOPPED');
  console.log('  ' + '-'.repeat(84));
  for (const r of rows) {
    const can = r.submitted ? (r.done ? 'yes, saved' : 'yes, fallback') : 'NO';
    console.log('  ' + r.label.padEnd(34) + can.padEnd(19) +
                (r.blockedAt ? r.blockedAt + ': "' + r.msg + '"' : '-'));
    if (r.errs) fails.push(r.label + ' threw a js error');
  }
  console.log('');
  // What SHOULD block: blank code word, missing rating, no choice, not watched.
  const expectBlocked = ['code word left blank', 'one rating not answered',
                         'no head-to-head choice', 'has not watched enough'];
  for (const r of rows) {
    const should = expectBlocked.includes(r.label);
    const did = !r.submitted;
    if (should !== did) fails.push(r.label + ': expected ' +
      (should ? 'BLOCKED' : 'submittable') + ', got the opposite');
  }
  console.log(fails.length ? fails.length + ' FAILED: ' + fails.join('; ')
    : 'incomplete work is stopped at the form; everything else submits and is judged later');
  process.exit(fails.length ? 1 : 0);
 } catch (e) { console.log('ERROR: ' + e.message); process.exit(1); }
})();
