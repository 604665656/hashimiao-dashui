const { chromium }=require('playwright');const http=require('http');const fs=require('fs');
const ROOT='/data/workspace';let buf;
const srv=http.createServer((q,r)=>{try{buf=fs.readFileSync(ROOT+'/'+decodeURIComponent(q.url.split('?')[0].slice(1)))}catch(e){r.writeHead(404);r.end();return}r.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});r.end(buf)});
const BASE='http://localhost:8146/'+encodeURIComponent('大水计算器-合并版.html');
const log=(k,v)=>console.log(`${k}: ${v}`);
const findings=[],errs=[];
const F=(k,v)=>{findings.push([k,v]);console.log(`  [发现] ${k}: ${v}`)};
let browser;
const MOCK=`
window.toy={available:()=>true,ready:()=>Promise.resolve(true),
 cloud:{set:()=>Promise.resolve({ok:true}),get:()=>Promise.resolve({value:''})},
 rank:{submit:()=>Promise.resolve({ok:true}),list:()=>Promise.resolve([])},
 user:{profile:()=>Promise.resolve({nickname:'我'})}};
window.cloud=window.toy.cloud;window.rank=window.toy.rank;
`;
async function open(opt={}){
  const {w=1440,h=900,toy=false,query=''}=opt;
  const ctx=await browser.newContext({viewport:{width:w,height:h},
    geolocation:{latitude:24.896,longitude:118.605},permissions:['geolocation']});
  if(toy) await ctx.addInitScript(MOCK);
  const p=await ctx.newPage();p.on('pageerror',e=>errs.push(e.message));
  p.on('dialog',d=>d.accept());
  await p.goto(BASE+query,{waitUntil:'domcontentloaded'});await p.waitForTimeout(toy?2300:1800);
  return {ctx,p};
}
const SEED=`const t=Date.now(),d=today(); d.logs=[];
  appendLog(d,{id:'s1',ts:t-100*60000,ml:300,type:'water',note:'早'},'quick');
  appendLog(d,{id:'s2',ts:t-60*60000,ml:250,type:'water',note:'午'},'quick');
  appendLog(d,{id:'s3',ts:t-20*60000,ml:0,type:'milk',note:'奶茶',photo:'data:image/png;base64,AAAA'},'selfie');
  S.settings.notify=false; S.settings.patrol=false; _saveBase(); renderAll();`;

(async()=>{
 await new Promise(r=>srv.listen(8146,r));
 browser=await chromium.launch({headless:true,executablePath:'/usr/local/bin/chromium',args:['--no-sandbox']});

 // ===== 1) 顺手修的真 bug：删除改 void，不再打断审计链 =====
 {
   const {ctx,p}=await open();
   await p.evaluate(SEED);await p.waitForTimeout(200);
   const before=await p.evaluate(()=>({w:waterOf(today()),m:milkOf(today()).length,
     v:verifyAudit(today()),n:today().logs.length}));
   await p.evaluate(()=>{
     const row=$$('#logList .logrow').find(x=>x.textContent.includes('午'));
     row.querySelector('.del').click();
   });
   await p.waitForTimeout(250);
   const after=await p.evaluate(()=>({w:waterOf(today()),m:milkOf(today()).length,
     v:verifyAudit(today()),n:today().logs.length,
     types:today().logs.map(l=>l.type),voidTarget:today().logs.at(-1).targetId,
     rows:document.querySelectorAll('#logList .logrow').length,
     hud:$('#hiLine .hi-foot').textContent.trim()}));
   log('① 删除前',JSON.stringify(before));
   log('① 删除后',JSON.stringify(after));
   if(before.w!==550||before.m!==1||!before.v.ok)F('① 用例前置失败',JSON.stringify(before));
   if(!after.v.ok||after.v.len!==4)F('① 删除打断审计链',JSON.stringify(after.v));
   if(after.w!==300||after.m!==1)F('① void 后计算错误',JSON.stringify(after));
   if(after.n!==4||after.types.at(-1)!=='void'||after.voidTarget!=='s2')
     F('① 未追加 void',JSON.stringify(after));
   if(after.rows!==2)F('① UI 仍显示已删记录',after.rows);
   if(after.hud.includes('断开'))F('① HUD 误报断链',after.hud);
   // 再删一笔奶茶：链继续增长
   await p.evaluate(()=>{const r=$$('#logList .logrow').find(x=>x.textContent.includes('奶茶'));
     r.querySelector('.del').click();});
   await p.waitForTimeout(200);
   const c=await p.evaluate(()=>({v:verifyAudit(today()),m:milkOf(today()).length,w:waterOf(today())}));
   log('① 连续删除',JSON.stringify(c));
   if(!c.v.ok||c.m!==0||c.w!==300)F('① 连续删除异常',JSON.stringify(c));
   await ctx.close();
 }

 // ===== 2) 导出镜像：校验和 / 摘要 / 含照片 =====
 {
   const {ctx,p}=await open();
   await p.evaluate(SEED);
   const r=await p.evaluate(()=>{
     const bk=makeBackup(), parsed=parseBackup(JSON.stringify(bk));
     return {schema:bk.schema,app:bk.app,rule:bk.rule,sum:bk.checksum.slice(0,12),
       summary:bk.summary,stat:bk.stat,parsedOK:parsed.ok,
       photo:JSON.stringify(bk.data).includes('data:image/png;base64,AAAA'),
       hasVoucher:JSON.stringify(bk.data).includes('DW-VOUCHER')};
   });
   log('② 导出镜像',JSON.stringify(r));
   if(!r.parsedOK||r.stat.logs!==3||r.stat.photos!==1||!r.photo)
     F('② 导出/解析异常',JSON.stringify(r));
   // 篡改 / 截断被拒
   const bad=await p.evaluate(()=>{
     const bk=makeBackup(); bk.data.profiles[0].name='被改了';
     const a=parseBackup(JSON.stringify(bk));
     const b=parseBackup('{"app":"dashui","schema":2,');
     const c=parseBackup(JSON.stringify(Object.assign(makeBackup(),{app:'other'})));
     return [a,b,c].map(x=>({ok:x.ok,err:x.err}));
   });
   log('② 坏镜像',JSON.stringify(bad));
   if(bad.some(x=>x.ok))F('② 坏镜像被接受',JSON.stringify(bad));
   await ctx.close();
 }

 // ===== 3) 恢复向导：merge / replace / new + undo =====
 {
   const {ctx,p}=await open();
   await p.evaluate(SEED);
   // 造一个来自「另一台设备」的镜像
   const bkText=await p.evaluate(()=>{
     const bk=makeBackup();
     const k=dkey(new Date(Date.now()-86400000));
     bk.data.profiles[0].days[k]={logs:[
       {id:'remote1',ts:Date.now()-86400000,ml:1700,type:'water',note:'昨日达标'}],reminds:[]};
     bk.data.profiles[0].submitted[k]={date:k,score:103,ml:1700,at:Date.now()-86400000,code:'DW-REMOTE'};
     bk.data.story=bk.data.story||{ends:[],cgs:[]}; bk.data.story.ends=['S'];
     bk.checksum=dhSum(bk.data);
     return JSON.stringify(bk);
   });
   const merge=await p.evaluate(t=>{
     dhPending=parseBackup(t);
     const d=today(), before={logs:d.logs.length,subs:Object.keys(PROFILE().submitted||{}).length};
     dhApply('merge');
     return {before,after:{logs:today().logs.length,
       subs:Object.keys(PROFILE().submitted||{}).length,
       ends:S.story.ends.slice(),v:verifyAudit(today())},
       yesterday:!!PD()[dkey(new Date(Date.now()-86400000))]};
   },bkText);
   log('③ 合并',JSON.stringify(merge));
   if(!merge.after.v.ok||!merge.yesterday||!merge.after.ends.includes('S'))
     F('③ 合并异常',JSON.stringify(merge));
   if(merge.after.logs!==merge.before.logs)F('③ 合并重复写入当日流水',JSON.stringify(merge));

   // 替换 + undo
   const rep=await p.evaluate(t=>{
     dhPending=parseBackup(t);
     const before=PROFILE().name;
     PROFILE().name='改过的本机名'; _saveBase();
     dhApply('replace');
     const after=PROFILE().name;
     const ok=dhUndo();
     return {before,after,undo:ok,restored:PROFILE().name};
   },bkText);
   log('③ 替换+撤销',JSON.stringify(rep));
   if(!rep.undo||rep.restored!=='改过的本机名')F('③ 撤销失效',JSON.stringify(rep));

   // 新建档案
   const nw=await p.evaluate(t=>{
     dhPending=parseBackup(t);
     const n=S.profiles.length;
     dhApply('new');
     return {before:n,after:S.profiles.length,active:S.activeId,
       chain:verifyAudit(today())};
   },bkText);
   log('③ 新建档案',JSON.stringify(nw));
   if(nw.after!==nw.before+1||!nw.chain.ok)F('③ 新建档案异常',JSON.stringify(nw));
   await ctx.close();
 }

 // ===== 4) 数据 / 凭证中心 UI =====
 {
   const {ctx,p}=await open();
   await p.click('#btnData');await p.waitForSelector('#dhTabs');
   const tabs=await p.locator('#dhTabs [data-dh]').allTextContents();
   log('④ 中心 tab',JSON.stringify(tabs));
   if(tabs.length!==4)F('④ tab 数量异常',JSON.stringify(tabs));
   // 导入预览差异
   await p.evaluate(()=>{ $('#dhInput').value=JSON.stringify(makeBackup()); $('#dhParse').click(); });
   await p.waitForTimeout(200);
   const diff=await p.evaluate(()=>({txt:$('#dhDiff').textContent.replace(/\s+/g,' ').trim().slice(0,120),
     hasMerge:!!$('#dhMerge'),hasReplace:!!$('#dhReplace'),hasNew:!!$('#dhNew')}));
   log('④ 导入预览',JSON.stringify(diff));
   if(!diff.hasMerge||!diff.hasReplace||!diff.hasNew)F('④ 三选一缺失',JSON.stringify(diff));
   // 切到各 tab 都能渲染
   for(const t of ['verify','note','state']){
     await p.click(`#dhTabs [data-dh="${t}"]`);await p.waitForTimeout(180);
     const n=await p.evaluate(()=>$('#dhPane').textContent.trim().length);
     log(`④ tab ${t} 内容长度`,n);
     if(n<40)F(`④ ${t} 空白`,n);
   }
   await p.click('#dhClose');
   await ctx.close();
 }

 // ===== 5) 离线复核凭证 =====
 {
   const {ctx,p}=await open();
   await p.evaluate(SEED);
   const r=await p.evaluate(()=>{
     const v=makeVoucher(), txt=voucherText(v), good=parseVoucher(txt);
     const obj=JSON.parse(decodeURIComponent(escape(atob(txt.split(/\s+/)[1]))));
     obj.score=99999; delete obj.checksum; obj.checksum=dhSum(obj);
     const tampered='DW-VOUCHER-1 '+btoa(unescape(encodeURIComponent(JSON.stringify(obj))));
     const kept=parseVoucher(tampered);           // 自洽但数值被改
     const raw=JSON.stringify(v);
     return {goodOK:good.ok,selfOK:good.selfOK,codeOK:good.codeOK,
       complete:good.complete,checks:voucherChecks(good).length,
       noSensitive:!/photo|data:image|api.?key|endpoint|latitude|"lat"|"lng"/i.test(raw),
       fields:Object.keys(v).filter(k=>k!=='checksum').length,
       tamperSelfOK:kept.selfOK,tamperScore:kept.v&&kept.v.score,
       bad:parseVoucher('随便一段文本').ok};
   });
   log('⑤ 凭证',JSON.stringify(r));
   if(!r.goodOK||!r.selfOK||!r.codeOK||!r.complete||r.checks!==5)
     F('⑤ 凭证生成/校验异常',JSON.stringify(r));
   if(!r.noSensitive)F('⑤ 凭证含敏感字段',JSON.stringify(r));
   if(r.bad)F('⑤ 乱码被接受','');
   // 接收方校验页真的能跑
   await p.evaluate(()=>{ openDataHub('verify'); $('#dhInput').value=voucherText(makeVoucher()); $('#dhVerifyGo').click(); });
   await p.waitForTimeout(200);
   const ui=await p.evaluate(()=>({ok:$('#dhDiff .dh-box.ok')!==null,
     rows:document.querySelectorAll('#dhDiff .dh-check').length,
     y:document.querySelectorAll('#dhDiff .dh-check.y').length}));
   log('⑤ 校验页',JSON.stringify(ui));
   if(!ui.ok||ui.rows!==5||ui.y<4)F('⑤ 校验页异常',JSON.stringify(ui));
   await ctx.close();
 }

 // ===== 6) 离线传纸条 =====
 {
   const {ctx,p}=await open();
   const r=await p.evaluate(()=>{
     const txt=noteText(makeNote('今天也要吨一口大水','阿喵'));
     const good=parseNote(txt), raw=decodeURIComponent(escape(atob(txt.split(/\s+/)[1])));
     return {ok:good.ok,selfOK:good.selfOK,nick:good.n.nick,text:good.n.text,
       fields:Object.keys(good.n),
       noSensitive:!/photo|data:image|"lat"|"lng"|weather|mood|logs|quote/i.test(raw),
       bad:parseNote('DW-NOTE-1 !!!').ok};
   });
   log('⑥ 纸条',JSON.stringify(r));
   if(!r.ok||!r.selfOK||r.nick!=='阿喵'||r.bad)F('⑥ 纸条生成/解析异常',JSON.stringify(r));
   if(r.fields.length!==6||!r.noSensitive)F('⑥ 纸条带多余字段',JSON.stringify(r));
   await p.evaluate(()=>{ openDataHub('note'); $('#dhInput').value=noteText(makeNote('冲大水！','阿喵')); $('#dhNoteGo').click(); });
   await p.waitForTimeout(200);
   const ui=await p.evaluate(()=>({ok:!!$('#dhDiff .dh-box.ok'),bubble:$('#bubbleText').textContent.trim()}));
   log('⑥ 纸条朗读',JSON.stringify(ui));
   if(!ui.ok||!ui.bubble.includes('冲大水'))F('⑥ 纸条未朗读',JSON.stringify(ui));
   await ctx.close();
 }

 // ===== 7) CharacterDirector / 剧情表 / 深链 =====
 {
   const {ctx,p}=await open({query:'?avatar=bean&mood=开心'});
   const r=await p.evaluate(()=>({av:S.avatar,mood:S.settings.mood,
     c:characterAudit(),sd:storyDataAudit(),st:characterState(),
     link:shareDeepLink('story')}));
   log('⑦ 状态层',JSON.stringify({av:r.av,mood:r.mood,c:{unchanged:r.c.unchanged,
     allValid:r.c.allValid,seen:r.c.seen},sd:r.sd}));
   if(r.av!=='bean'||r.mood!=='开心')F('⑦ 深链参数未应用',JSON.stringify({a:r.av,m:r.mood}));
   if(!r.c.unchanged||!r.c.allValid||r.c.count!==4)F('⑦ 状态层有副作用',JSON.stringify(r.c));
   if(!r.sd.unique||!r.sd.condOK||!r.sd.cgOK||r.sd.rankCount!==6)
     F('⑦ 剧情表自检失败',JSON.stringify(r.sd));
   if(!r.link.includes('view=story')||!r.link.includes('avatar=bean'))
     F('⑦ 深链生成异常',r.link);
   // 逐一切换 4 形象，业务数据不变
   const sw=await p.evaluate(()=>{
     const snap=JSON.stringify([S.profiles,S.activeId,S.settings.goal,S.hiTickets]);
     ['drop','cat','bean','daily'].forEach(id=>{ S.avatar=id; renderAll(); });
     return snap===JSON.stringify([S.profiles,S.activeId,S.settings.goal,S.hiTickets]);
   });
   log('⑦ 4 形象切换数据不变',sw); if(!sw)F('⑦ 切换形象改动了业务数据','');
   await ctx.close();
 }
 {
   const {ctx,p}=await open({query:'?view=story'});
   await p.waitForTimeout(350);
   const st=await p.evaluate(()=>$('#storyLayer').classList.contains('show'));
   log('⑦ 深链直达剧场',st); if(!st)F('⑦ 深链未打开剧场','');
   await ctx.close();
 }

 // ===== 8) 分享卡「复核凭证」入口 =====
 {
   const {ctx,p}=await open();
   await p.evaluate(SEED);
   await p.click('#btnShare');await p.waitForSelector('#scImg');
   const has=await p.evaluate(()=>!!$('#scVoucher'));
   log('⑧ 分享卡凭证入口',has); if(!has)F('⑧ 入口缺失','');
   await p.click('#scVoucher');await p.waitForSelector('#dhTabs');
   const t=await p.evaluate(()=>$('#dhPane h4').textContent.trim());
   log('⑧ 跳转',t); if(!t.includes('离线复核'))F('⑧ 跳转错误',t);
   await p.click('#dhClose');
   await ctx.close();
 }

 // ===== 9) P0 / Toy / 原有全链路回归 =====
 {
   const {ctx,p}=await open();
   const base=await p.evaluate(()=>({mode:TOY.mode,on:TOY.on,sound:S.settings.sound,
     bgm:S.settings.bgm,hi:hydrationIndex(),audit:verifyAudit(today()).ok,
     remind:reminderDecision(Date.now()).why,
     boot:!!S.auditMigrated&&$('#mlTxt').textContent!=='0'||$('#mlTxt').textContent==='0',
     scoreRendered:$('#scoreLine').textContent.includes('分'),
     quoteRendered:$('#quoteText').textContent.trim().length>5}));
   log('⑨ 基础状态',JSON.stringify(base));
   if(base.mode!=='local'||base.on||base.sound||base.bgm||!base.audit)
     F('⑨ 基础状态异常',JSON.stringify(base));
   if(!base.scoreRendered||!base.quoteRendered)
     F('⑨ init() 未完整执行（启动渲染/语录缺失）',JSON.stringify(base));
   // 防作弊
   await p.click('.watergrid .btn[data-ml="250"]');await p.waitForTimeout(160);
   await p.click('.watergrid .btn[data-ml="250"]');await p.waitForTimeout(160);
   const n=await p.evaluate(()=>liveLogs(today()).filter(l=>l.type==='water').length);
   log('⑨ 防作弊连点',n); if(n!==1)F('⑨ 防作弊失效',n);
   // 双榜 + 横幅
   await p.click('#btnBoard');await p.waitForSelector('#scList');
   await p.locator('#scWrap [data-bt="all"]').click();await p.waitForTimeout(200);
   const banner=await p.locator('.sc-banner').count();
   log('⑨ 横幅',banner); if(banner!==1)F('⑨ 横幅缺失',banner);
   await p.click('#scClose');
   // 音频面板
   await p.click('#btnAudio');await p.waitForSelector('#auState');
   const ap=await p.evaluate(()=>({icons:document.querySelectorAll('.au-grid img').length,
     banner:$('.au-banner img')?.naturalWidth>0}));
   log('⑨ 音频面板',JSON.stringify(ap));
   if(ap.icons!==6||!ap.banner)F('⑨ 音频面板异常',JSON.stringify(ap));
   await p.click('#auDone');
   // 剧场 + 结局表
   await p.click('#btnStory');await p.waitForTimeout(350);
   const st=await p.evaluate(()=>({show:$('#storyLayer').classList.contains('show'),
     ranks:ST_ENDINGS.map(e=>e.rank).join('')}));
   log('⑨ 剧场',JSON.stringify(st));
   if(!st.show||st.ranks!=='?SABCD')F('⑨ 剧场异常',JSON.stringify(st));
   await p.click('#stClose');
   // 设置：智能提醒 / 专注
   await p.click('#btnSet');await p.waitForSelector('#sRemindMode');
   await p.selectOption('#sRemindMode','fixed');await p.click('#sSave');await p.waitForTimeout(220);
   const mode=await p.evaluate(()=>S.settings.remindMode);
   log('⑨ 提醒策略保存',mode); if(mode!=='fixed')F('⑨ 设置未保存',mode);
   // 分享卡
   await p.click('#btnShare');await p.waitForSelector('#scImg');
   const card=await p.evaluate(()=>{
     const text=buildShareText({mode:'daily',sc:todayScore(),date:'11月12日',time:'15:00',
       mood:'通透',code:'DW-ABC123',quote:''});
     return {w:$('#scImg').naturalWidth,h:$('#scImg').naturalHeight,
       hi:text.includes('水合指数'),chain:text.includes('审计链')};
   });
   log('⑨ 分享卡',JSON.stringify(card));
   if(card.w!==640||card.h!==960||!card.hi||!card.chain)
     F('⑨ 分享卡异常',JSON.stringify(card));
   await p.click('#scShut');
   // 刷新持久化
   await p.evaluate(()=>{ S.avatar='cat'; save(); });
   await p.reload({waitUntil:'domcontentloaded'});await p.waitForTimeout(1800);
   const after=await p.evaluate(()=>({av:S.avatar,v:verifyAudit(today()),mig:S.auditMigrated}));
   log('⑨ 刷新后',JSON.stringify(after));
   if(after.av!=='cat'||!after.v.ok||after.mig!==1)F('⑨ 刷新持久化异常',JSON.stringify(after));
   await ctx.close();
 }

 // ===== 10) Toy 形态冒烟 =====
 {
   const {ctx,p}=await open({toy:true});
   const d=await p.evaluate(()=>({mode:TOY.mode,ready:TOY.ready,
     chip:$('#toyChip').textContent.trim(),snap:toySnapshot().hydrationIndex,
     audit:toySensitiveAudit(toySnapshot())}));
   log('⑩ Toy 冒烟',JSON.stringify(d));
   if(d.mode!=='cloud'||!d.ready||!d.audit||typeof d.snap!=='number')
     F('⑩ Toy 形态异常',JSON.stringify(d));
   await p.click('#btnBoard');await p.waitForSelector('#scWrap');
   const tabs=await p.locator('#scWrap [data-bt]').allTextContents();
   log('⑩ 榜单 tab',JSON.stringify(tabs));
   if(tabs.length!==3)F('⑩ 平台榜 tab 缺失',JSON.stringify(tabs));
   await p.click('#scClose');
   await ctx.close();
 }

 // ===== 11) 375px 窄屏 + 中心弹层 =====
 {
   const {ctx,p}=await open({w:375,h:812});
   const ov=await p.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
   await p.click('#btnData');await p.waitForSelector('#dhTabs');
   const box=await p.evaluate(()=>{const e=document.querySelector('#modalBox'),r=e.getBoundingClientRect();
     return {sw:e.scrollWidth,cw:e.clientWidth,l:Math.round(r.left),rr:Math.round(r.right),win:innerWidth};});
   log('⑪ 375px',JSON.stringify({ov,box}));
   if(ov>2||box.sw>box.cw+2||box.rr>box.win+2||box.l<-2)
     F('⑪ 窄屏溢出',JSON.stringify({ov,box}));
   await p.screenshot({path:ROOT+'/大水计算器-合并版-P1数据中心-手机预览.png'});
   await p.click('#dhClose');
   await ctx.close();
 }

 // ===== 12) 体积 / 零外链 =====
 {
   const st=fs.statSync(ROOT+'/大水计算器-合并版.html');
   const html=fs.readFileSync(ROOT+'/大水计算器-合并版.html','utf8');
   const baseSize=fs.statSync(ROOT+'/_base_before_p1.html').size;
   const ext=html.match(/(?:src|href)\s*=\s*["'](?!data:)(?:https?:|\/\/|\.\/|\/)[^"']+/gi)||[];
   const delta=Math.round((st.size-baseSize)/1024*10)/10;
   log('⑫ 体积/增量/外链',`${Math.round(st.size/1024*10)/10} KiB / +${delta} KiB / ${JSON.stringify(ext)}`);
   if(ext.length||/cdn\.jsdelivr|unpkg\.com|cdnjs/.test(html))F('⑫ 出现外链',JSON.stringify(ext));
   if(st.size>1024*1024)F('⑫ 体积超 1 MiB',st.size);
   if(html.includes('eval('))F('⑫ 运行时含 eval','');
 }

 console.log('\n=== 巡检汇总 ===');
 console.log('发现项:',findings.length);findings.forEach(([k,v])=>console.log('  ·',k,'→',v));
 console.log('控制台错误:',errs.length);errs.forEach(e=>console.log('  ·',e));
 await browser.close();srv.close();
 process.exit(findings.length||errs.length?1:0);
})().catch(e=>{console.error('FATAL',e);if(browser)browser.close();srv.close();process.exit(2)});
