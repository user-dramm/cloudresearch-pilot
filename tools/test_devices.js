// DEVICE GATING
// Which devices see the study and which get the 'use a desktop' block.
// Both directions matter: a tablet that slips through gives a degraded session, but a
// laptop that gets blocked destroys a paid one. Run against a local server on 8792.
//
//   cd ~/cloudresearch_pilot && python3 -m http.server 8792 &
//   node tools/test_devices.js

const { chromium, devices } = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const U='http://localhost:8792/index.html?participantId=DEV1';
const fails=[];
const ck=(c,l,d='')=>{ if(!c) fails.push(l); console.log((c?'  ok    ':'  FAIL  ')+l+(!c&&d?'   ['+d+']':'')); };
(async()=>{
  const b=await chromium.launch({channel:'chrome',args:['--mute-audio']});
  const blocked=async ctx=>{ const p=await ctx.newPage();
    await p.goto(U,{waitUntil:'domcontentloaded'}); await p.waitForTimeout(1200);
    const r=await p.evaluate(()=>{
      const mb=document.querySelector('.mobile-block'), d=document.querySelector('.desktop-only');
      return { block:mb?getComputedStyle(mb).display!=='none':null,
               study:d?getComputedStyle(d).display!=='none':null }; });
    await p.close(); return r; };

  // MUST be blocked
  for (const d of ['iPhone 13','iPhone SE','iPad Mini','iPad (gen 7)','Galaxy Tab S4','Pixel 7']) {
    if(!devices[d]) { console.log('  (skip '+d+')'); continue; }
    const r=await blocked(await b.newContext({...devices[d]}));
    ck(r.block===true && r.study===false, d+' ('+devices[d].viewport.width+'px) blocked');
  }
  // MUST NOT be blocked - real desktops and laptops, including a touchscreen laptop
  for (const [w,h,label,extra] of [
      [1024,768,'small laptop 1024x768',{}],
      [1280,800,'laptop 1280x800',{}],
      [1440,900,'MacBook 1440x900',{}],
      [1920,1080,'desktop 1920x1080',{}],
      [1366,768,'touchscreen laptop 1366x768',{hasTouch:true}]]) {
    const r=await blocked(await b.newContext({viewport:{width:w,height:h},...extra}));
    ck(r.block===false && r.study===true, label+' NOT blocked');
  }
  console.log('');
  console.log(fails.length? fails.length+' FAILED: '+fails.join('; ') : 'device gating correct in every case');
  await b.close();
})();
