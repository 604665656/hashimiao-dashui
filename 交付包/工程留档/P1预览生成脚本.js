const {chromium}=require('playwright');const http=require('http');const fs=require('fs');
let buf;const srv=http.createServer((q,r)=>{try{buf=fs.readFileSync('/data/workspace/'+decodeURIComponent(q.url.split('?')[0].slice(1)))}catch(e){r.writeHead(404);r.end();return}r.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});r.end(buf)});
const U='http://localhost:8148/'+encodeURIComponent('大水计算器-合并版.html');
const DATA=`
 const t=Date.now(),d=today(); d.logs=[];
 appendLog(d,{id:'p1',ts:t-145*60000,ml:350,type:'water',note:'晨起第一口'},'quick');
 appendLog(d,{id:'p2',ts:t-92*60000,ml:250,type:'water',note:'喝大水'},'quick');
 appendLog(d,{id:'p3',ts:t-38*60000,ml:400,type:'water',note:'喝大水'},'quick');
 appendLog(d,{id:'p4',ts:t-15*60000,ml:0,type:'milk',note:'偷喝奶茶 · 已自首',
   photo:'data:image/png;base64,AAAA'},'selfie');
 S.settings.mood='通透';S.avatar='cat';S.lastRemindAt=t-35*60000;
 S.settings.notify=false;S.settings.patrol=false;
 _saveBase();renderAll();
 ['#toast','#mask','#bubble'].forEach(s=>document.querySelector(s)?.classList.remove('show'));
`;
(async()=>{await new Promise(r=>srv.listen(8148,r));
const b=await chromium.launch({headless:true,executablePath:'/usr/local/bin/chromium',args:['--no-sandbox']});
const c=await b.newContext({viewport:{width:1440,height:900},
  geolocation:{latitude:24.896,longitude:118.605},permissions:['geolocation']});
const p=await c.newPage();const errs=[];p.on('pageerror',e=>errs.push(e.message));
p.on('dialog',d=>d.accept());
await p.goto(U,{waitUntil:'domcontentloaded'});await p.waitForTimeout(1850);
await p.evaluate(DATA);await p.waitForTimeout(400);

// A · 主界面（新增 🗂 按钮）
await p.screenshot({path:'/data/workspace/大水计算器-合并版-P1主界面-预览.png'});
console.log('A 主界面 ✓',await p.evaluate(()=>({hi:hydrationIndex(),chain:verifyAudit(today()).head})));

// B · 导入导出 + 预览差异
await p.click('#btnData');await p.waitForSelector('#dhTabs');
await p.evaluate(()=>{ $('#dhInput').value=JSON.stringify(makeBackup()); $('#dhParse').click(); });
await p.waitForTimeout(350);
await p.screenshot({path:'/data/workspace/大水计算器-合并版-P1导入导出-预览.png'});
console.log('B 导入导出 ✓',await p.evaluate(()=>!!$('#dhMerge')));

// C · 复核凭证（校验结果）
await p.click('#dhTabs [data-dh="verify"]');await p.waitForTimeout(200);
await p.evaluate(()=>{ $('#dhInput').value=voucherText(makeVoucher()); $('#dhVerifyGo').click(); });
await p.waitForTimeout(300);
await p.screenshot({path:'/data/workspace/大水计算器-合并版-P1复核凭证-预览.png'});
console.log('C 复核凭证 ✓',await p.evaluate(()=>document.querySelectorAll('#dhDiff .dh-check.y').length),'项通过');

// D · 状态自检
await p.click('#dhTabs [data-dh="state"]');await p.waitForTimeout(250);
await p.screenshot({path:'/data/workspace/大水计算器-合并版-P1状态自检-预览.png'});
console.log('D 状态自检 ✓',await p.evaluate(()=>!!$('#dhPane .dh-box.ok')));

// E · 传纸条（导入并朗读）
await p.click('#dhTabs [data-dh="note"]');await p.waitForTimeout(200);
await p.evaluate(()=>{ $('#dhInput').value=noteText(makeNote('今天也要吨一口大水，喵','阿喵')); $('#dhNoteGo').click(); });
await p.waitForTimeout(300);
await p.screenshot({path:'/data/workspace/大水计算器-合并版-P1传纸条-预览.png'});
console.log('E 传纸条 ✓',await p.evaluate(()=>$('#dhDiff .dh-box.ok')?.textContent.trim().slice(0,50)));
await p.click('#dhClose');

// F · 手机端数据中心
const m=await b.newContext({viewport:{width:375,height:812},
  geolocation:{latitude:24.896,longitude:118.605},permissions:['geolocation']});
const mp=await m.newPage();mp.on('pageerror',e=>errs.push(e.message));
await mp.goto(U,{waitUntil:'domcontentloaded'});await mp.waitForTimeout(1750);
await mp.evaluate(DATA);await mp.waitForTimeout(300);
await mp.click('#btnData');await mp.waitForSelector('#dhTabs');await mp.waitForTimeout(250);
await mp.screenshot({path:'/data/workspace/大水计算器-合并版-P1数据中心-手机预览.png'});
console.log('F 手机端 ✓');
console.log('控制台错误:',errs.length,errs.join(' | '));
await b.close();srv.close();})();
