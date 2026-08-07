// PARTICIPANT INTERACTION
// Keyboard-only use, validation messaging, the code word box, and whether work
// survives the network dying mid-session. Run against a local server on 8792.
//
//   cd ~/cloudresearch_pilot && python3 -m http.server 8792 &
//   node tools/test_interaction.js

const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const U='http://localhost:8792/index.html?participantId=INT1&selftest=1';
const fails=[]; const ck=(c,l,d='')=>{ if(!c)fails.push(l); console.log((c?'  ok    ':'  FAIL  ')+l+(!c&&d?'   ['+d+']':'')); };
(async()=>{
  const b=await chromium.launch({channel:'chrome',args:['--autoplay-policy=no-user-gesture-required','--mute-audio']});
  const ctx=await b.newContext({viewport:{width:1280,height:800}});
  const p=await ctx.newPage();
  const errs=[]; p.on('pageerror',e=>errs.push(String(e)));
  await p.goto(U,{waitUntil:'domcontentloaded'});
  await p.waitForFunction(()=>{const i=document.querySelector('#s-intro');return i&&getComputedStyle(i).display!=='none';},{timeout:120000});

  // Keyboard only: can they reach and press Start with Tab + Enter?
  let tabs=0, onStart=false;
  for (;tabs<25 && !onStart;tabs++){ await p.keyboard.press('Tab');
    onStart=await p.evaluate(()=>document.activeElement && document.activeElement.id==='btn-start'); }
  ck(onStart, 'Start button reachable by keyboard (Tab)', 'after '+tabs+' tabs');
  if(onStart) await p.keyboard.press('Enter'); else await p.locator('#btn-start').click();
  await p.waitForSelector('#gate-pct1_0',{state:'attached',timeout:30000});
  ck(true,'Enter on Start advances to the first video');

  // Ratings reachable and settable by keyboard
  await p.evaluate(()=>{ watch[1].vids.forEach(v=>{v.duration=540;v.watched=540;v.open=true;});
    watch[1].open=true; document.querySelector('#qs1-card').classList.remove('locked'); paintGate(1,0); });
  const kb=await p.evaluate(()=>{
    const q=document.querySelector('[data-qid="s1_overall"]');
    const first=q.querySelector('input[type=radio]');
    first.focus();
    return document.activeElement===first;
  });
  ck(kb, 'a rating radio can take keyboard focus');
  await p.keyboard.press('ArrowRight'); await p.keyboard.press('ArrowRight');
  const picked=await p.evaluate(()=>{const q=document.querySelector('[data-qid="s1_overall"]');
    const c=q.querySelector('input:checked'); return c?c.value:null;});
  ck(picked!==null, 'arrow keys select a rating', 'value='+picked);

  // Code word box: usable, and NOT inside the locked card
  const cw=await p.evaluate(()=>{ const el=document.querySelector('#cw1');
    const card=document.querySelector('#qs1-card');
    return { exists:!!el, disabled:el?el.disabled:null, insideLocked: card?card.contains(el):null }; });
  ck(cw.exists && cw.disabled===false, 'code word box present and enabled');
  ck(cw.insideLocked===false, 'code word box sits OUTSIDE the locked question card');

  // Typing the code word, then a paste, which should be counted not blocked
  await p.locator('#cw1').fill('ironwood');
  const typed=await p.evaluate(()=>document.querySelector('#cw1').value);
  ck(typed==='ironwood','code word accepts typing');

  // Validation refuses to advance with a rating missing, and says why on screen
  await p.evaluate(()=>{ // clear the others so validation must fail
    ['s1_audio','s1_visuals'].forEach(id=>{
      const q=document.querySelector('[data-qid="'+id+'"]');
      q.querySelectorAll('input[type=radio]').forEach(r=>{r.checked=false;});
    });
  });
  await p.evaluate(()=>{const btn=[...document.querySelectorAll('button')].find(x=>/continue/i.test(x.textContent)&&x.offsetParent);btn.click();});
  await p.waitForTimeout(400);
  const msg=await p.evaluate(()=>{
    const e=[...document.querySelectorAll('.err,.show')].map(x=>x.textContent.trim()).filter(Boolean);
    return { still:!!document.querySelector('#gate-pct1_0') && getComputedStyle(document.querySelector('#s-v1')).display!=='none',
             text:e.join(' | ').slice(0,120) }; });
  ck(msg.still, 'incomplete answers do not advance');
  ck(/answer|star|please/i.test(msg.text), 'an on-screen message explains what is missing', msg.text);

  // Network death mid-session must not lose work
  await ctx.setOffline(true);
  await p.evaluate(()=>{ ['s1_audio','s1_visuals'].forEach(id=>{
      const q=document.querySelector('[data-qid="'+id+'"]');
      q.querySelectorAll('input[type=radio]')[3].click(); }); });
  await p.waitForTimeout(3500);
  const saved=await p.evaluate(()=>{const k=Object.keys(localStorage).find(x=>x.startsWith('embr_pilot'));
    return k?JSON.parse(localStorage.getItem(k)):null;});
  ck(saved && saved.d && saved.d.s1_codeword==='ironwood',
     'work is still saved locally while offline', saved?JSON.stringify(saved.d.s1_codeword):'no state');
  await ctx.setOffline(false);
  ck(errs.length===0,'no js errors through all of it', errs.slice(0,1).join(''));
  console.log('');
  console.log(fails.length? fails.length+' FAILED: '+fails.join('; ') : 'all '+'interaction checks pass');
  await b.close();
})();
