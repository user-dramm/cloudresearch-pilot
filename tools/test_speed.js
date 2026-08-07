// PLAYBACK SPEED: BLOCKED SILENTLY, AND RECORDED
//
// Capping watch credit at real elapsed time already meant 2x bought nothing - the gate
// costs the same number of real minutes however fast the video is set to play. So forcing
// the rate back is not an anti-cheat measure, it is an anti-CONFUSION one: left alone,
// someone at 2x sees the bar advance at half the pace they expect, decides the page is
// broken, and either messages you or abandons a session you have paid for.
//
// The reset is deliberately SILENT. There is no way to remove the speed control itself:
// the IFrame API cannot hide the settings gear, and controls:0 would take play and pause
// with it. So the rate is snapped back within half a second and nothing is said about it.
// The intro still sets the time expectation, which is what stops someone reaching for the
// control in the first place.
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
  ck(/full time/i.test(intro),'the intro tells them to plan for the full time');
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
  ck(!/speed is back to normal/i.test(st.msg),'the reset is SILENT, no note shown',
     JSON.stringify(st.msg.slice(0,70)));
  ck(st.warned===false,'no warning styling is applied');
  ck(st.maxRate>1,'the attempt is still recorded for the analysis','max_rate='+st.maxRate);
  await p.screenshot({path:'/tmp/speed-note.png'});

  // Credit must not have jumped.
  const after=await p.evaluate(()=>watch[1].vids[0].watched);
  ck((after-before) <= 4.5,'no extra credit was earned during the 2x attempt',
     'gained '+(after-before).toFixed(1)+'s in 3s');

  // It must STAY at 1x, not drift back up after the first reset.
  await p.evaluate(()=>players['1_0'].setPlaybackRate(1.75));
  await p.waitForTimeout(2500);
  await p.evaluate(()=>players['1_0'].setPlaybackRate(2));
  await p.waitForTimeout(2500);
  const later=await p.evaluate(()=>({rate:players['1_0'].getPlaybackRate(),
     msg:(document.querySelector('#gate-msg1_0')||{}).textContent||''}));
  ck(later.rate===1,'repeat attempts are reset too, not just the first','at '+later.rate+'x');
  ck(/unlock/i.test(later.msg),'the gate message is untouched throughout',
     JSON.stringify(later.msg.slice(0,50)));
  console.log('');
  console.log(fails.length? fails.length+' FAILED: '+fails.join('; ') : 'speed is reset silently on every attempt, and still recorded');
  await b.close();
  process.exit(fails.length?1:0);
 }catch(e){ console.log('ERROR: '+e.message); process.exit(1); }
})();
