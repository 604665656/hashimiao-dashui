const {chromium}=require('playwright');const http=require('http');const fs=require('fs');
let buf;const srv=http.createServer((q,r)=>{try{buf=fs.readFileSync('/data/workspace/'+decodeURIComponent(q.url.split('?')[0].slice(1)))}catch(e){r.writeHead(404);r.end();return}r.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});r.end(buf)});
const U='http://localhost:8145/'+encodeURIComponent('大水计算器-合并版.html');
const DATA=`
  const t=Date.now();
  const d=today(); d.logs=[];
  appendLog(d,{id:'demo1',ts:t-150*60000,ml:350,type:'water',note:'晨起第一口'},'quick');
  appendLog(d,{id:'demo2',ts:t-95*60000,ml:250,type:'water',note:'喝大水'},'quick');
  appendLog(d,{id:'demo3',ts:t-38*60000,ml:400,type:'water',note:'喝大水'},'quick');
  S.settings.mood='通透'; S.avatar='cat'; S.lastRemindAt=t-35*60000;
  S.settings.remindMode='smart'; S.remindIgnores=0; S.focusUntil=0;
  S.settings.notify=false; S.settings.patrol=false;
  _saveBase(); renderAll();
  ['#toast','#mask','#bubble'].forEach(s=>document.querySelector(s)?.classList.remove('show'));
`;
(async()=>{await new Promise(r=>srv.listen(8145,r));
const b=await chromium.launch({headless:true,executablePath:'/usr/local/bin/chromium',args:['--no-sandbox']});
const c=await b.newContext({viewport:{width:1440,height:900},
  geolocation:{latitude:24.896,longitude:118.605},permissions:['geolocation']});
const p=await c.newPage();const errs=[];p.on('pageerror',e=>errs.push(e.message));
await p.goto(U,{waitUntil:'domcontentloaded'});await p.waitForTimeout(1800);

// A · 主界面（三项新指标）
await p.evaluate(DATA);await p.waitForTimeout(450);
await p.screenshot({path:'/data/workspace/大水计算器-合并版-P0主界面-预览.png'});
console.log('A 主界面 ✓',await p.evaluate(()=>({
  hi:hydrationIndex(),remind:$('#remindLine').textContent.trim(),
  audit:verifyAudit(today()).head})));
console.log('   ',await p.evaluate(()=>$('#hiLine').textContent.replace(/\\s+/g,' ').trim()));

// B · 设置面板（提醒策略 + 专注）
await p.click('#btnSet');await p.waitForSelector('#sRemindMode');await p.waitForTimeout(300);
await p.screenshot({path:'/data/workspace/大水计算器-合并版-P0设置-预览.png'});
console.log('B 设置面板 ✓',await p.textContent('#sRemindMode'));
await p.click('#sCancel');

// C · 打卡分享卡（640×960 原尺寸）
const png=await p.evaluate(()=>{
  const sc=todayScore();
  return drawShareCard({mode:'daily',sc,date:'11月12日',time:fmtTime(Date.now()),
    mood:S.settings.mood,code:checkCode(PROFILE().id+dkey()+sc.total+sc.valid),
    quote:($('#quoteText').textContent||'').trim(),
    boardLine:'今日榜第 1 名 · 历史总榜第 1 名'});
});
fs.writeFileSync('/data/workspace/大水计算器-合并版-P0打卡分享卡.png',
  Buffer.from(png.split(',')[1],'base64'));
console.log('C 分享卡 ✓',round(fs.statSync('/data/workspace/大水计算器-合并版-P0打卡分享卡.png').size/1024,1),'KiB');

// D · 手机预览
const m=await b.newContext({viewport:{width:375,height:812},
  geolocation:{latitude:24.896,longitude:118.605},permissions:['geolocation']});
const mp=await m.newPage();mp.on('pageerror',e=>errs.push(e.message));
await mp.goto(U,{waitUntil:'domcontentloaded'});await mp.waitForTimeout(1700);
await mp.evaluate(DATA);await mp.waitForTimeout(400);
await mp.screenshot({path:'/data/workspace/大水计算器-合并版-P0首屏-手机预览.png'});
await mp.evaluate(()=>{const e=$('#hiLine');e.scrollIntoView({block:'center'});});
await mp.waitForTimeout(300);
await mp.screenshot({path:'/data/workspace/大水计算器-合并版-P0指标-手机预览.png'});
console.log('D 手机首屏 + 指标特写 ✓');
console.log('控制台错误:',errs.length,errs.join(' | '));
await b.close();srv.close();})();
function round(x,n){return Math.round(x*Math.pow(10,n))/Math.pow(10,n)}
