// ANTI-CHEAT, MEASURED LIVE
// These are the layers that justify rejecting a paid participant, so they are measured
// against a real YouTube player rather than trusted from reading the code:
//   A. seeking forward earns no credit AND rewinds you to where you actually got to
//   B. 2x playback earns no more than real elapsed time, and is recorded in max_rate
//   C. removing the .locked class by hand does not let Continue through
//   D. a paused video accrues nothing
//
//   cd ~/cloudresearch_pilot && python3 -m http.server 8795 &
//   PLAYWRIGHT_PATH=... node tools/test_anticheat.js
//
// Takes about a minute, because it has to accrue real playback time to prove anything.

const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const U='http://localhost:'+(process.env.PORT||8795)+'/index.html?participantId=CHEAT1&selftest=1';
const fails=[]; const ck=(c,l,d='')=>{ if(!c)fails.push(l); console.log((c?'  ok    ':'  FAIL  ')+l+(!c&&d?'   ['+d+']':'')); };
(async()=>{
 try{
  const b=await chromium.launch({channel:'chrome',args:['--autoplay-policy=no-user-gesture-required','--mute-audio']});
  const p=await (await b.newContext()).newPage();
  await p.goto(U,{waitUntil:'domcontentloaded'});
  await p.waitForFunction(()=>{const i=document.querySelector('#s-intro');return i&&getComputedStyle(i).display!=='none';},{timeout:150000});
  await p.locator('#btn-start').click();
  await p.waitForSelector('#gate-pct1_0',{state:'attached',timeout:60000});
  await p.waitForFunction(()=>{try{return players['1_0'].getDuration()>0;}catch(e){return false;}},{timeout:150000});
  const dur=await p.evaluate(()=>players['1_0'].getDuration());
  console.log('video is '+Math.round(dur)+'s, gate needs 90% of it\n');

  // --- A. seeking forward earns nothing and rewinds you --------------------
  await p.evaluate(()=>players['1_0'].playVideo());
  await p.waitForTimeout(9000);
  const before=await p.evaluate(()=>({w:watch[1].vids[0].watched, f:watch[1].vids[0].furthest}));
  await p.evaluate(d=>players['1_0'].seekTo(d*0.8, true), dur);
  await p.waitForTimeout(6000);
  const after=await p.evaluate(()=>({w:watch[1].vids[0].watched, f:watch[1].vids[0].furthest,
    seek:watch[1].vids[0].seekFwd, t:players['1_0'].getCurrentTime()}));
  console.log('  jumped to 80% of the video');
  ck(after.w - before.w < 12, 'skipping earns no watch credit',
     'credit went '+before.w.toFixed(0)+'s -> '+after.w.toFixed(0)+'s');
  ck(after.t < dur*0.5, 'player was rewound to where they actually got to',
     'now at '+after.t.toFixed(0)+'s of '+Math.round(dur));
  ck(after.seek >= 1, 'the forward seek was counted and recorded', 'seek_fwd='+after.seek);

  // --- B. 2x playback earns no extra credit, and is recorded ---------------
  const w0=await p.evaluate(()=>watch[1].vids[0].watched);
  await p.evaluate(()=>{players['1_0'].setPlaybackRate(2);players['1_0'].playVideo();});
  await p.waitForTimeout(12000);
  const st=await p.evaluate(()=>({w:watch[1].vids[0].watched, r:watch[1].vids[0].maxRate,
    rate:players['1_0'].getPlaybackRate()}));
  const gained=st.w-w0;
  console.log('\n  played at '+st.rate+'x for 12 real seconds');
  ck(gained <= 14, 'double speed earns no more than real elapsed time',
     'gained '+gained.toFixed(1)+'s of credit in 12s');
  ck(st.r > 1, 'the fast playback is recorded for the analysis', 'max_rate='+st.r);

  // --- C. the gate cannot be opened from the console -----------------------
  await p.evaluate(()=>{players['1_0'].setPlaybackRate(1);players['1_0'].pauseVideo();});
  const forced=await p.evaluate(()=>{
    const card=document.querySelector('#qs1-card');
    const wasLocked=card.classList.contains('locked');
    card.classList.remove('locked');           // pretend a rater unlocked the card
    const btn=[...document.querySelectorAll('button')].find(x=>/continue/i.test(x.textContent)&&x.offsetParent);
    document.querySelectorAll('#qs1-card .q').forEach(q=>{
      const rs=q.querySelectorAll('input[type=radio]'); if(rs.length) rs[3].click();});
    const cw=document.querySelector('#cw1'); if(cw){cw.value='x';cw.dispatchEvent(new Event('input',{bubbles:true}));}
    btn.click();
    return { wasLocked, advanced: getComputedStyle(document.querySelector('#s-v1')).display==='none' };
  });
  console.log('\n  un-locked the question card by hand and pressed Continue');
  ck(forced.wasLocked===true, 'the card really was locked beforehand');
  ck(forced.advanced===false, 'Continue still refuses while the watch gate is unmet');

  // --- D. pausing stops the clock -----------------------------------------
  const pa=await p.evaluate(()=>watch[1].vids[0].watched);
  await p.waitForTimeout(7000);
  const pb=await p.evaluate(()=>watch[1].vids[0].watched);
  console.log('\n  left it paused for 7 seconds');
  ck(Math.abs(pb-pa) < 1.5, 'a paused video accrues no credit',
     'credit moved '+pa.toFixed(1)+' -> '+pb.toFixed(1));
  console.log('');
  console.log(fails.length? fails.length+' FAILED: '+fails.join('; ') : 'every anti-cheat layer holds');
  await b.close();
 }catch(e){ console.log('ERROR: '+e.message); }
})();
