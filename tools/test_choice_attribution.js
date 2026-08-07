// DOES THE FORM RECORD THE VIDEO THEY ACTUALLY PICKED?
//
// The single most dangerous silent failure in the whole study. h2h_choice_key is the field
// clauses 1 and 2 are computed from, so recording the wrong one does not break anything
// visibly: it reverses the finding and looks perfectly valid doing so.
//
// This gap was real. Flipping one character in payload() so the OTHER slot's key is
// recorded left consistency, report attribution, rating attribution, sheet columns and
// interaction ALL PASSING, because the two attribution suites test the analysis against
// synthetic CSV rows whose keys they construct themselves. Nothing exercised the form.
//
// So this drives the real form and checks the chain end to end, in both orders:
//
//   the radio they clicked -> the slot number recorded
//                          -> the key recorded
//                          -> the key config assigns to that slot
//                          -> the YouTube id actually mounted in that slot's player
//
// That last link matters: it ties the recorded answer to the video on screen, not merely
// to another field in the same payload.
//
//   cd ~/cloudresearch_pilot && python3 -m http.server 8795 &
//   PLAYWRIGHT_PATH=... node tools/test_choice_attribution.js

const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const fs = require('fs');
const PORT = process.env.PORT || 8795;
const fails = [];
const ck = (c, l, d = '') => { if (!c) fails.push(l);
  console.log((c ? '  ok    ' : '  FAIL  ') + l + (!c && d ? '   [' + d + ']' : '')); };

// The public config, so the test knows which key each pair's slots may hold.
global.window = {};
eval(fs.readFileSync('config.js', 'utf8'));
const CFG = global.window.STUDY_CONFIG;

async function walk(browser, pid, whichOption) {
  const p = await (await browser.newContext()).newPage();
  await p.goto('http://localhost:' + PORT + '/index.html?participantId=' + pid + '&selftest=1',
               { waitUntil: 'domcontentloaded' });
  await p.waitForFunction(() => { const i = document.querySelector('#s-intro');
    return i && getComputedStyle(i).display !== 'none'; }, { timeout: 150000 });
  await p.locator('#btn-start').click();
  await p.waitForSelector('#gate-pct1_0', { state: 'attached', timeout: 60000 });

  // What is actually mounted in each slot's player, read from the DOM.
  const mounted = {};
  for (const s of [1, 2]) {
    if (s === 2) {
      await p.evaluate(() => {
        watch[1].vids.forEach(v => { v.duration = 540; v.watched = 540; v.open = true; });
        watch[1].open = true;
        const c = document.querySelector('#qs1-card'); if (c) c.classList.remove('locked');
        document.querySelectorAll('#qs1-card .q').forEach(q => {
          const rs = q.querySelectorAll('input[type=radio]'); if (rs.length) rs[3].click(); });
        const cw = document.querySelector('#cw1');
        if (cw) { cw.value = 'x'; cw.dispatchEvent(new Event('input', { bubbles: true })); }
        go(2);
      });
      await p.waitForSelector('#gate-pct2_0', { state: 'attached', timeout: 60000 });
    }
    mounted[s] = await p.evaluate(sl => {
      const f = document.querySelector('#vwrap' + sl + '_0 iframe[src*="youtube"]')
             || document.querySelector('#s-v' + sl + ' iframe[src*="youtube"]');
      const m = f && f.src.match(/embed\/([\w-]+)/);
      return m ? m[1] : null;
    }, s);
  }

  const res = await p.evaluate(opt => {
    for (const s of [1, 2]) {
      watch[s].vids.forEach(v => { v.duration = 540; v.watched = 540; v.open = true; });
      watch[s].open = true;
      const c = document.querySelector('#qs' + s + '-card'); if (c) c.classList.remove('locked');
      document.querySelectorAll('#qs' + s + '-card .q').forEach(q => {
        const rs = q.querySelectorAll('input[type=radio]'); if (rs.length) rs[3].click(); });
      const cw = document.querySelector('#cw' + s);
      if (cw) { cw.value = 'x'; cw.dispatchEvent(new Event('input', { bubbles: true })); }
    }
    go(3);
    // Click the requested option BY ITS VISIBLE LABEL, the way a rater does.
    const q = document.querySelector('[data-qid="h2h_choice"]');
    const want = [...q.querySelectorAll('input[type=radio]')].find(r => r.value === opt);
    if (!want) return { error: 'option not found: ' + opt };
    want.click();
    document.querySelectorAll('#h2h-qs .q').forEach(x => {
      if (getComputedStyle(x).display === 'none') return;
      const rs = x.querySelectorAll('input[type=radio]');
      if (rs.length && !x.querySelector('input[type=radio]:checked')) rs[0].click();
      const ta = x.querySelector('textarea'); if (ta && !ta.value) ta.value = 'x';
    });
    collect(QS, 's1_'); collect(QS, 's2_'); collect(H2H, '');
    const d = payload();
    return { pair: d.pair_id, choice: d.h2h_choice, slot: d.h2h_choice_slot,
             key: d.h2h_choice_key, s1: d.slot1_key, s2: d.slot2_key };
  }, whichOption);
  await p.context().close();
  return { ...res, mounted };
}

(async () => {
 try {
  const b = await chromium.launch({ channel: 'chrome', args: ['--mute-audio'] });

  for (const [opt, wantSlot] of [['The first video', 1], ['The second video', 2]]) {
    const r = await walk(b, 'ATTR' + wantSlot, opt);
    if (r.error) { ck(false, 'walk for ' + opt, r.error); continue; }
    const label = '"' + opt + '"';
    console.log('\n' + label + '  pair ' + r.pair + '  slot1=' + r.s1 + ' slot2=' + r.s2);

    ck(r.slot === wantSlot, label + ' records slot ' + wantSlot, 'got ' + JSON.stringify(r.slot));
    const expectKey = wantSlot === 1 ? r.s1 : r.s2;
    ck(r.key === expectKey, label + ' records THAT slot\'s key, not the other one',
       'recorded ' + r.key + ', that slot holds ' + expectKey);

    // Tie it to the video the rater actually saw in that slot.
    const pair = CFG.pairs.find(x => x.id === r.pair);
    const keyOfMounted = s => {
      const v = pair && pair.versions.find(v => (v.yts || []).includes(r.mounted[s]));
      return v ? v.key : null;
    };
    const seenKey = keyOfMounted(wantSlot);
    ck(seenKey !== null, label + ' the video mounted in slot ' + wantSlot + ' is one of the pair',
       'mounted ' + r.mounted[wantSlot]);
    ck(seenKey === r.key, label + ' the recorded key IS the video that played in that slot',
       'played ' + r.mounted[wantSlot] + ' (' + seenKey + '), recorded ' + r.key);
    ck(r.mounted[1] !== r.mounted[2], label + ' the two slots held different videos',
       r.mounted[1] + ' vs ' + r.mounted[2]);
  }

  console.log('');
  console.log(fails.length ? fails.length + ' FAILED: ' + fails.join('; ')
    : 'the form records the video the rater actually chose, in both orders');
  await b.close();
  process.exit(fails.length ? 1 : 0);
 } catch (e) { console.log('ERROR: ' + e.message); process.exit(1); }
})();
