const {chromium}=require('playwright');const http=require('http');const fs=require('fs');
let buf;const srv=http.createServer((q,r)=>{try{buf=fs.readFileSync('/data/workspace/'+decodeURIComponent(q.url.split('?')[0].slice(1)))}catch(e){r.writeHead(404);r.end();return}r.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});r.end(buf)});
const MOCK=`
window.toy={available:()=>true,ready:()=>Promise.resolve(true),
 cloud:{set:()=>Promise.resolve({ok:true}),get:()=>Promise.resolve({value:''})},
 rank:{submit:()=>Promise.resolve({ok:true}),list:()=>Promise.resolve([
   {nickname:'大水仙人',score:103},{nickname:'阿喵',score:88},{nickname:'我',score:63,me:true},
   {nickname:'丰泽区摸鱼王',score:55},{nickname:'小水滴酱',score:41}])},
 user:{profile:()=>Promise.resolve({nickname:'我'})}};
window.cloud=window.toy.cloud;window.rank=window.toy.rank;
`;
(async()=>{await new Promise(r=>srv.listen(8143,r));
const b=await chromium.launch({headless:true,executablePath:'/usr/local/bin/chromium',args:['--no-sandbox']});
const U='http://localhost:8143/'+encodeURIComponent('大水计算器-合并版.html');

// A · 本地版主界面
{
 const c=await b.newContext({viewport:{width:1440,height:900},
   geolocation:{latitude:24.896,longitude:118.605},permissions:['geolocation']});
 const p=await c.newPage();
 await p.goto(U,{waitUntil:'domcontentloaded'});await p.waitForTimeout(1800);
 await p.evaluate(()=>{
   const t=Date.now()-35*60000;
   today().logs.push({id:'demo1',ts:t,ml:750,type:'water',note:'喝大水'});
   S.settings.mood='通透';S.avatar='cat';_saveBase();renderAll();
   ['#toast','#mask','#bubble'].forEach(s=>document.querySelector(s)?.classList.remove('show'));
 });
 await p.waitForTimeout(400);
 await p.screenshot({path:'/data/workspace/大水计算器-合并版-本地版-预览.png'});
 console.log('A 本地版主界面 ✓',(await p.textContent('#toyChip')).trim());
 await c.close();
}

// B · Toy 版主界面 + 存档状态面板 + 平台榜
{
 const c=await b.newContext({viewport:{width:1440,height:900},
   geolocation:{latitude:24.896,longitude:118.605},permissions:['geolocation']});
 await c.addInitScript(MOCK);
 const p=await c.newPage();const errs=[];p.on('pageerror',e=>errs.push(e.message));
 await p.goto(U,{waitUntil:'domcontentloaded'});await p.waitForTimeout(2300);
 await p.evaluate(()=>{
   const t=Date.now()-35*60000;
   today().logs.push({id:'demo1',ts:t,ml:750,type:'water',note:'喝大水'});
   S.settings.mood='通透';S.avatar='cat';_saveBase();renderAll();
   ['#toast','#mask','#bubble'].forEach(s=>document.querySelector(s)?.classList.remove('show'));
 });
 await p.waitForTimeout(400);
 await p.screenshot({path:'/data/workspace/大水计算器-合并版-Toy版-预览.png'});
 console.log('B Toy 版主界面 ✓',(await p.textContent('#toyChip')).trim());

 await p.evaluate(()=>{ TOY.remote={snap:toySnapshot(),meta:{hash:'demo-abc123def456'}};
   TOY.lastSync=Date.now(); TOY.lastErr=''; renderToyChip(); });
 await p.click('#toyChip');await p.waitForSelector('#tpSync');await p.waitForTimeout(300);
 await p.screenshot({path:'/data/workspace/大水计算器-合并版-Toy存档面板-预览.png'});
 console.log('C 存档状态面板 ✓',(await p.textContent('#modalBox .mtitle')).trim());
 await p.click('#tpClose');

 await p.evaluate(()=>{ TOY.consent=true; TOY.rankList=[
   {name:'大水仙人',score:103},{name:'阿喵',score:88},{name:'我',score:63,me:true},
   {name:'丰泽区摸鱼王',score:55},{name:'小水滴酱',score:41}]; TOY.rankLoaded=true; });
 await p.click('#btnBoard');await p.waitForSelector('#scWrap');
 await p.locator('#scWrap [data-bt="toy"]').click();await p.waitForTimeout(400);
 await p.screenshot({path:'/data/workspace/大水计算器-合并版-平台榜-预览.png'});
 console.log('D 平台榜 ✓',await p.locator('#scList .toy-row').count(),'行');
 console.log('控制台错误:',errs.length,errs.join(' | '));
 await c.close();
}
await b.close();srv.close();})();
