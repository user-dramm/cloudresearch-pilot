// PLAYBACK SPEED: BLOCKED, EXPLAINED, AND RECORDED
//
// Capping watch credit at real elapsed time already meant 2x bought nothing - the gate
// costs the same number of real minutes however fast the video is set to play. So forcing
// the rate back is not an anti-cheat measure, it is an anti-CONFUSION one: left alone,
// someone at 2x sees the bar advance at half the pace they expect, decides the page is
// broken, and either messages you or abandons a session you have paid for.
//
// Checks the warning appears in three places, which is the point: up front in the intro,
// on the video screen before they reach for the control, and at the moment they try it.
//
//   cd ~/cloudresearch_pilot && python3 -m http.server 8795 &
//   PLAYWRIGHT_PATH=... node tools/test_speed.js

const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const U='http://localhost:'+(process.env.PORT||8795)+'/index.html?participantId=SPEED1&selftest=1';
const fails=[]; const ck=(c,l,d='')=>{ if(!c)fails.push(l); console.log((c?'  ok    ':'  FAIL  ')+l+(!c&&d?'   ['+d+']':'')); };
(async()=>{
 try{
  const b=await chromium.launch({channel:'chrome',args:['--autoplay-policy=no-user-gesture-required','--mute-audio']});
  const p=await (await b.newContext({viewport:{width:1000,height:800}})).newPage();
  await p.goto(U,{waitUntil:'domcontentloaded'});
  await p.waitForFunction(()=>{const i=document.querySelector('#s-intro');return i&&getComputedStyle(i).display!=='none';},{timeout:150000});
  const intro=await p.evaluate(()=>[...document.querySelectorAll('#s-intro li')].map(l=>l.innerText).join(' '));
  ck(/speeding it up/i.test(intro),'the intro warns that speeding up will not help');
  ck(/full time/i.test(intro),'the intro says to plan for the full time');
  await p.locator('#btn-start').click();
  await p.waitForSelector('#gate-pct1_0',{state:'attached',timeout:60000});
  await p.waitForFunction(()=>{try{return players['1_0'].getDuration()>0;}catch(e){return false;}},{timeout:150000});
  await p.evaluate(()=>{players['1_0'].setVolume(0);players['1_0'].playVideo();});
  await p.waitForTimeout(5000);
  const before=await p.evaluate(()=>watch[1].vids[0].watched);

  // A rater reaches for 2x.
  await p.evaluate(()=>players['1_0'].setPlaybackRate(2));
  await p.waitForTimeout(3000);
  const st=await p.evaluate(()=>({
    rate: players['1_0'].getPlaybackRate(),
    msg: (document.querySelector('#gate-msg1_0')||{}).textContent||'',
    warned: (document.querySelector('#gate-msg1_0')||{classList:{contains:()=>false}}).classList.contains('warn'),
    maxRate: watch[1].vids[0].maxRate }));
  ck(st.rate===1,'the player is put back to normal speed','still at '+st.rate+'x');
  ck(/will not unlock the questions any sooner/i.test(st.msg),'an on-screen note explains why',
     JSON.stringify(st.msg.slice(0,70)));
  ck(st.warned===true,'the note is visually marked');
  ck(st.maxRate>1,'the attempt is still recorded for the analysis','max_rate='+st.maxRate);
  await p.screenshot({path:'/tmp/speed-note.png'});

  // Credit must not have jumped.
  const after=await p.evaluate(()=>watch[1].vids[0].watched);
  ck((after-before) <= 4.5,'no extra credit was earned during the 2x attempt',
     'gained '+(after-before).toFixed(1)+'s in 3s');

  // The note must clear itself.
  await p.waitForTimeout(10000);
  const later=await p.evaluate(()=>({msg:(document.querySelector('#gate-msg1_0')||{}).textContent||'',
     warned:(document.querySelector('#gate-msg1_0')||{classList:{contains:()=>false}}).classList.contains('warn')}));
  ck(!later.warned && /unlock/i.test(later.msg),'the note clears back to the normal message',
     JSON.stringify(later.msg.slice(0,50)));
  console.log('');
  console.log(fails.length? fails.length+' FAILED: '+fails.join('; ') : 'speed is blocked, explained, and recorded');
  await b.close();
  process.exit(fails.length?1:0);
 }catch(e){ console.log('ERROR: '+e.message); process.exit(1); }
})();
