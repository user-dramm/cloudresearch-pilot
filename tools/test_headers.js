// SHEET COLUMN COVERAGE
// Does every answer the form sends have its own column in the Apps Script HEADERS?
//
// This exists because the two drifted apart badly without anyone noticing: 12 real
// answers, including both clarity ratings, h2h_magnitude and standby, were being written
// into the extra_json blob while 15 columns sat permanently blank from an earlier
// question set. Nothing was lost, because every reader resolves fields through a helper
// that unpacks the overflow - but the Sheet is the view used to spot-check raters and
// approve payment, and it showed blank columns and JSON where the answers should be.
//
//   cd ~/cloudresearch_pilot && python3 -m http.server 8795 &
//   PLAYWRIGHT_PATH=... node tools/test_headers.js
//
// NOTE ON APPLYING A HEADERS CHANGE: rows are written positionally as HEADERS.map(...),
// and the header row is created only once. Reordering or inserting mid-study writes new
// rows against the old header row and silently misaligns everything. Safe only while the
// sheet has no real rows: delete every row INCLUDING the header, then submit once.

const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const fs = require('fs');
const PORT = process.env.PORT || 8795;

(async () => {
  const gs = fs.readFileSync('apps_script/Code.gs', 'utf8');
  const HEAD = [...gs.match(/var HEADERS = \[([\s\S]*?)\];/)[1].matchAll(/"([^"]+)"/g)].map(m => m[1]);

  // Two sources, because neither alone is complete. A live run misses fields set by the
  // Continue handler when a test drives go() directly; a static scan misses fields
  // assigned in object literals inside payload().
  const html = fs.readFileSync('index.html', 'utf8');
  const derived = new Set();
  for (const m of html.matchAll(/\bD\.([a-z0-9_]+)\s*=/g)) derived.add(m[1]);
  for (const m of html.matchAll(/D\[\s*"([a-z0-9_]+)"\s*\]\s*=/g)) derived.add(m[1]);
  for (const m of html.matchAll(/D\[\s*"s"\s*\+\s*\w+\s*\+\s*"(_[a-z0-9_]+)"\s*\]\s*=/g)) {
    derived.add('s1' + m[1]); derived.add('s2' + m[1]);
  }
  const grab = (name, pre) => {
    const i = html.indexOf('const ' + name + ' = [');
    const blk = html.slice(i, html.indexOf('];', i));
    for (const m of blk.matchAll(/\{\s*id:"([a-z0-9_]+)"/g)) {
      if (pre) { derived.add('s1_' + m[1]); derived.add('s2_' + m[1]); } else derived.add(m[1]);
    }
  };
  grab('QS', true); grab('H2H', false);

  const b = await chromium.launch({ channel: 'chrome', args: ['--mute-audio'] });
  const p = await (await b.newContext()).newPage();
  await p.goto('http://localhost:' + PORT + '/index.html?participantId=HDR&selftest=1',
               { waitUntil: 'domcontentloaded' });
  await p.waitForFunction(() => { const i = document.querySelector('#s-intro');
    return i && getComputedStyle(i).display !== 'none'; }, { timeout: 120000 });
  await p.locator('#btn-start').click();
  await p.waitForSelector('#gate-pct1_0', { state: 'attached', timeout: 30000 });
  const runtime = await p.evaluate(() => {
    for (const s of [1, 2]) {
      watch[s].vids.forEach(v => { v.duration = 540; v.watched = 540; v.open = true; });
      watch[s].open = true;
      document.querySelectorAll('#qs' + s + '-card .q').forEach(q => {
        const rs = q.querySelectorAll('input[type=radio]'); if (rs.length) rs[0].click(); });
      const cw = document.querySelector('#cw' + s);
      if (cw) { cw.value = 'x'; cw.dispatchEvent(new Event('input', { bubbles: true })); }
    }
    go(3);
    document.querySelectorAll('#h2h-qs .q').forEach(q => {
      const rs = q.querySelectorAll('input[type=radio]'); if (rs.length) rs[0].click();
      const ta = q.querySelector('textarea'); if (ta) ta.value = 'x'; });
    collect(QS, 's1_'); collect(QS, 's2_'); collect(H2H, '');
    return Object.keys(payload());
  });
  await b.close();

  const sends = new Set([...runtime, ...derived]);
  // `token` is a constant on every row and has no column by design; doPost drops it.
  const missing = [...sends].filter(k => k !== 'token' && !HEAD.includes(k)).sort();
  const blank   = HEAD.filter(h => !sends.has(h) && !['row_id', 'ts_server'].includes(h));
  const dupes   = [...new Set(HEAD)].filter(h => HEAD.filter(x => x === h).length > 1);

  const fails = [];
  const ck = (c, l, d) => { if (!c) fails.push(l);
    console.log((c ? '  ok    ' : '  FAIL  ') + l + (!c && d ? '   [' + d + ']' : '')); };

  console.log('HEADERS columns: ' + HEAD.length + '   fields the form can send: ' + sends.size);
  ck(missing.length === 0, 'every answer the form sends has its own column', missing.join(', '));
  ck(blank.length === 0, 'no column is permanently blank', blank.join(', '));
  ck(dupes.length === 0, 'no duplicate columns', dupes.join(', '));
  ck(HEAD[0] === 'row_id' && HEAD[1] === 'ts_server',
     'row_id and ts_server stay first, as the script fills them');
  console.log('');
  console.log(fails.length ? fails.length + ' FAILED' : 'the Sheet has exactly one column per answer');
  process.exit(fails.length ? 1 : 0);
})();
