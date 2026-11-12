const { chromium }=require('playwright');const http=require('http');const fs=require('fs');
const ROOT='/data/workspace';let buf;
const srv=http.createServer((q,r)=>{try{buf=fs.readFileSync(ROOT+'/'+decodeURIComponent(q.url.split('?')[0].slice(1)))}catch(e){r.writeHead(404);r.end();return}r.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});r.end(buf)});
const URL='http://localhost:8144/'+encodeURIComponent('大水计算器-合并版.html');
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
  const {w=1440,h=900,toy=false}=opt;
  const ctx=await browser.newContext({viewport:{width:w,height:h},
    geolocation:{latitude:24.896,longitude:118.605},permissions:['geolocation']});
  if(toy) await ctx.addInitScript(MOCK);
  const p=await ctx.newPage();p.on('pageerror',e=>errs.push(e.message));
  await p.goto(URL,{waitUntil:'domcontentloaded'});await p.waitForTimeout(toy?2300:1750);
  return {ctx,p};
}
const AT=(h,m)=>new Date(2026,10,12,h,m||0,0).getTime();   // 2026-11-12 固定日

(async()=>{
 await new Promise(r=>srv.listen(8144,r));
 browser=await chromium.launch({headless:true,executablePath:'/usr/local/bin/chromium',args:['--no-sandbox']});

 // ===== 1) 审计链：打卡写入 + 校验 =====
 {
   const {ctx,p}=await open();
   await p.click('.watergrid .btn[data-ml="250"]');await p.waitForTimeout(220);
   const a=await p.evaluate(()=>{
     const d=today(), l=d.logs[0], v=verifyAudit(d);
     return {has:!!(l.hash&&l.prevHash&&l.localDate&&l.auditSource&&l.seq===0),
       fields:[l.seq,l.prevHash,l.hash,l.localDate,l.auditSource],v,
       rawUnchanged:l.ml===250&&l.type==='water'&&!!l.id&&!!l.note};
   });
   log('① 打卡审计链',JSON.stringify(a));
   if(!a.has||!a.v.ok||a.v.len!==1||!a.rawUnchanged)F('① 审计链写入异常',JSON.stringify(a));
   if(a.fields[1]!=='DS-GENESIS')F('① 首笔 prevHash 错误',a.fields[1]);
   // 第二笔：链头连接
   const b=await p.evaluate(()=>{
     const d=today(), t=Date.now()-40*60000;
     appendLog(d,{id:'manual2',ts:t,ml:200,type:'water',note:'补录'},'manual');
     return {v:verifyAudit(d),first:d.logs[0].hash,prev2:d.logs[1].prevHash,src:d.logs[1].auditSource};
   });
   log('① 第二笔链',JSON.stringify(b));
   if(!b.v.ok||b.prev2!==b.first||b.src!=='manual')F('① 链式衔接异常',JSON.stringify(b));
   await ctx.close();
 }

 // ===== 2) 篡改检出，且不静默覆盖原记录 =====
 {
   const {ctx,p}=await open();
   await p.click('.watergrid .btn[data-ml="250"]');await p.waitForTimeout(200);
   const d=await p.evaluate(()=>{
     const day=today(); day.logs[0].ml=9999;       // 直接改 localStorage 式篡改
     const v=verifyAudit(day);
     return {v,ml:day.logs[0].ml,foot:$('#hiLine .hi-foot').textContent.trim(),
       brokenClass:$('#hiLine .hi-foot').className};
   });
   log('② 篡改检出',JSON.stringify(d));
   if(d.v.ok||d.v.brokenAt!==0)F('② 篡改未检出',JSON.stringify(d));
   if(d.ml!==9999)F('② 原记录被静默覆盖',d.ml);
   await p.evaluate(()=>renderHydration());await p.waitForTimeout(150);
   const foot=await p.evaluate(()=>({t:$('#hiLine .hi-foot').textContent.trim(),c:$('#hiLine .hi-foot').className}));
   log('② HUD 异常提示',JSON.stringify(foot));
   if(!foot.t.includes('断开')||!foot.c.includes('bad'))F('② HUD 未标异常',JSON.stringify(foot));
   await ctx.close();
 }

 // ===== 3) 老存档一次性迁移，原字段不动 =====
 {
   const {ctx,p}=await open();
   await p.evaluate(()=>{
     const raw=JSON.parse(localStorage.getItem('dashui.pet.v1'));
     const k=dkey(); raw.profiles[0].days[k]={logs:[
       {id:'old1',ts:Date.now()-7200000,ml:300,type:'water',note:'旧记录'},
       {id:'old2',ts:Date.now()-3600000,ml:0,type:'milk',note:'旧奶茶',photo:'data:image/png;base64,AAA'}
     ],reminds:[]};
     delete raw.auditMigrated;
     localStorage.setItem('dashui.pet.v1',JSON.stringify(raw));
   });
   await p.reload({waitUntil:'domcontentloaded'});await p.waitForTimeout(1750);
   const d=await p.evaluate(()=>{
     const day=today(), v=verifyAudit(day);
     return {mig:S.auditMigrated,v,ml:day.logs[0].ml,note:day.logs[0].note,
       photo:day.logs[1].photo,src:day.logs[0].auditSource,seqs:day.logs.map(l=>l.seq)};
   });
   log('③ 老存档迁移',JSON.stringify({mig:d.mig,v:d.v,seqs:d.seqs,src:d.src,note:d.note,photo:d.photo.slice(0,24)}));
   if(!d.mig||!d.v.ok||d.v.len!==2||d.seqs.join()!=='0,1')F('③ 迁移未成链',JSON.stringify(d));
   if(d.ml!==300||d.note!=='旧记录'||!d.photo.startsWith('data:image'))F('③ 原字段被改',JSON.stringify(d));
   if(d.src!=='legacy')F('③ 来源标记错误',d.src);
   await ctx.close();
 }

 // ===== 4) 自首 / 剧场 / AVG 迁移都带链 =====
 {
   const {ctx,p}=await open();
   await p.click('#btnSin');await p.waitForTimeout(2200);
   if(await p.locator('#nClose').count()) await p.click('#nClose');
   await p.waitForTimeout(200);
   const a=await p.evaluate(()=>{const d=today();return {v:verifyAudit(d),
     last:d.logs[d.logs.length-1].auditSource,photo:!!d.logs[d.logs.length-1].photo};});
   log('④ 自首入链',JSON.stringify(a));
   if(!a.v.ok||a.last!=='selfie'||!a.photo)F('④ 自首未带链或照片丢失',JSON.stringify(a));
   await p.click('#btnStory');await p.waitForTimeout(350);
   await p.click('#stClose');
   await ctx.close();
 }

 // ===== 5) 智能提醒：时段进度差 / 达标停催 / 免打扰 =====
 {
   const {ctx,p}=await open();
   const r=await p.evaluate(()=>{
     const AT=(h,m)=>new Date(2026,10,12,h,m||0,0).getTime();
     const goal=goalOf();
     const set=(ml)=>{
       const d=today(); d.logs=[];
       if(ml) appendLog(d,{id:'seed',ts:Date.now()-45*60000,ml,type:'water',note:'种子'},'test');
       S.lastRemindAt=AT(14,0);   // 15:00 时已过 60 分钟
       S.focusUntil=0; S.remindIgnores=0; S.settings.remindMode='smart';
     };
     const now=AT(15,0);
     set(0); const behind=reminderDecision(now);           // 应喝 935，实喝 0
     set(900); const onTrack=reminderDecision(now);        // 落后 35 < 250
     set(2000); const achieved=reminderDecision(now);      // 达标
     const night=reminderDecision(AT(23,0));
     const dawn=reminderDecision(AT(4,0));
     set(0); S.settings.remindMode='fixed'; S.lastRemindAt=now-31*60000;
     const fixed=reminderDecision(now);
     set(0); S.settings.remindMode='smart'; S.focusUntil=now+20*60000;
     const focus=reminderDecision(now);
     set(0); S.remindIgnores=2;
     const gentle=reminderDecision(now);
     set(0); S.lastRemindAt=now-5*60000;
     const tooSoon=reminderDecision(now);
     return {goal,behind,onTrack,achieved,night,dawn,fixed,focus,gentle,tooSoon,
       ideal15:idealPctAt(new Date(now))};
   });
   log('⑤ 智能提醒',JSON.stringify(r));
   if(!r.behind.fire||!r.behind.why.includes('落后'))F('⑤ 落后未触发',JSON.stringify(r.behind));
   if(r.onTrack.fire||!r.onTrack.why.includes('跟得上'))F('⑤ 跟得上仍打扰',JSON.stringify(r.onTrack));
   if(r.achieved.fire||!r.achieved.why.includes('已达标'))F('⑤ 达标未停催',JSON.stringify(r.achieved));
   if(r.night.fire||r.dawn.fire||!r.night.why.includes('免打扰'))F('⑤ 免打扰失效',JSON.stringify({n:r.night,d:r.dawn}));
   if(!r.fixed.fire||!r.fixed.why.includes('固定间隔'))F('⑤ 固定模式失效',JSON.stringify(r.fixed));
   if(r.focus.fire||!r.focus.why.includes('专注'))F('⑤ 专注延期失效',JSON.stringify(r.focus));
   if(!r.gentle.fire||!r.gentle.gentle)F('⑤ 柔性升级失效',JSON.stringify(r.gentle));
   if(r.tooSoon.fire||!r.tooSoon.why.includes('不足'))F('⑤ 重复提醒',JSON.stringify(r.tooSoon));
   if(Math.abs(r.ideal15-.55)>.001)F('⑤ 时段曲线错误',r.ideal15);
   await ctx.close();
 }

 // ===== 6) 提醒真的写入 / 忽略累计 / 喝水清零 =====
 {
   const {ctx,p}=await open();
   const d=await p.evaluate(()=>{
     const now=Date.now();
     const day=today(); day.logs=[]; day.reminds=[];
     S.lastRemindAt=now-31*60000; S.remindIgnores=0; S.focusUntil=0;
     S.settings.remindMode='smart'; S.settings.notify=false; S.settings.patrol=false;
     remind({why:'测试落后',gap:500,gentle:false});
     const after={ignores:S.remindIgnores,reminds:day.reminds.length,last:S.lastRemindAt};
     addWater(250);                       // 冷却为空，可打卡
     return {after,afterDrink:S.remindIgnores,v:verifyAudit(today())};
   });
   log('⑥ 提醒落地',JSON.stringify(d));
   if(d.after.ignores!==1||d.after.reminds!==1)F('⑥ 提醒未记录',JSON.stringify(d.after));
   if(d.afterDrink!==0)F('⑥ 喝水未清忽略累计',d.afterDrink);
   if(!d.v.ok)F('⑥ 提醒链路破坏审计',JSON.stringify(d.v));
   const hud=await p.evaluate(()=>{renderRemindLine();return $('#remindLine').textContent.trim();});
   log('⑥ HUD 提醒行',hud);
   if(!hud.includes('智能提醒'))F('⑥ HUD 缺提醒策略',hud);
   await ctx.close();
 }

 // ===== 7) 可信水合指数：不清零 / 轻扣 / 里程碑发券 / 修复券 =====
 {
   const {ctx,p}=await open();
   const r=await p.evaluate(()=>{
     const fresh=hydrationIndex();
     const day=today(); day.logs=[];
     appendLog(day,{id:'h1',ts:Date.now()-40*60000,ml:800,type:'water',note:'a'},'test');
     appendLog(day,{id:'h2',ts:Date.now()-10,ml:600,type:'water',note:'b'},'test');
     const after=hydrationIndex();
     appendLog(day,{id:'m1',ts:Date.now()-5,ml:0,type:'milk',note:'小甜水'},'selfie');
     const milk=hydrationIndex();
     // 昨天有成绩、今天零记录：漏记不清零
     const past=dkey(new Date(Date.now()-86400000));
     PD()[past]={logs:[{id:'y1',ts:Date.now()-86400000,ml:1700,type:'water',note:'昨'}],reminds:[]};
     day.logs=[];
     renderHydration();
     const missed=hydrationIndex();
     // 里程碑发券：造满 7 天达标
     for(let i=2;i<=8;i++){
       const k=dkey(new Date(Date.now()-i*86400000));
       PD()[k]={logs:[{id:'p'+i,ts:Date.now()-i*86400000,ml:1700,type:'water',note:'满'}],reminds:[]};
     }
     appendLog(day,{id:'t1',ts:Date.now()-40*60000,ml:1700,type:'water',note:'达标'},'test');
     renderHydration();
     const high={v:hydrationIndex(),tickets:S.hiTickets,best:S.hiBest,awards:S.hiAwards};
     const before=hydrationIndex(); useRepairTicket();
     const used={tickets:S.hiTickets,repairAt:!!S.hiRepairAt,v:hydrationIndex(),before};
     return {fresh,after,milk,missed,high,used,
       hud:$('#hiLine').textContent.replace(/\s+/g,' ').trim().slice(0,140)};
   });
   log('⑦ 水合指数',JSON.stringify(r));
   if(r.after<=r.fresh)F('⑦ 打卡后指数未涨',JSON.stringify({f:r.fresh,a:r.after}));
   if(r.milk>=r.after||r.after-r.milk>HI_MAX())F('⑦ 奶茶扣分异常',JSON.stringify({a:r.after,m:r.milk}));
   if(r.missed===0)F('⑦ 漏记被清零',r.missed);
   if(r.high.v<60||Number(r.high.tickets||0)<1||!(r.high.awards||[]).length)
     F('⑦ 里程碑未发券',JSON.stringify(r.high));
   if(Number(r.used.tickets)!==Number(r.high.tickets)-1||!r.used.repairAt)
     F('⑦ 修复券未生效',JSON.stringify(r.used));
   if(!r.hud.includes('可信水合指数')||!r.hud.includes('审计链'))F('⑦ HUD 缺指标',r.hud);
   await ctx.close();
 }
 function HI_MAX(){return 6;}

 // ===== 7b) 券状态持久化 / 老存档首次静默补齐 / 新用户基线 =====
 {
   const {ctx,p}=await open();
   const fresh=await p.evaluate(()=>({v:hydrationIndex(),base:HI_CFG.baseline}));
   log('⑦b 新用户基线',JSON.stringify(fresh));
   if(fresh.v!==fresh.base)F('⑦b 新用户不是信任基线',JSON.stringify(fresh));
   const a=await p.evaluate(()=>{
     const day=today(); day.logs=[];
     appendLog(day,{id:'b1',ts:Date.now()-40*60000,ml:1700,type:'water',note:'达标'},'test');
     renderHydration();
     return {tickets:S.hiTickets,awards:S.hiAwards.slice(),init:S.hiAwardsInit,
       persisted:JSON.parse(localStorage.getItem('dashui.pet.v1')).hiTickets};
   });
   log('⑦b 首次发券',JSON.stringify(a));
   if(Number(a.tickets||0)<1||!a.init||a.persisted!==a.tickets)
     F('⑦b 券未落盘',JSON.stringify(a));
   await p.reload({waitUntil:'domcontentloaded'});await p.waitForTimeout(1750);
   const b=await p.evaluate(()=>({tickets:S.hiTickets,awards:S.hiAwards.slice(),
     toasts:document.querySelectorAll('#toast.show').length}));
   log('⑦b 刷新后',JSON.stringify(b));
   if(Number(b.tickets)!==Number(a.tickets))F('⑦b 刷新重复发券',JSON.stringify({a,b}));
   // 老存档：指数已高但无 hiAwardsInit → 静默补齐，不补发券
   await p.evaluate(()=>{
     const raw=JSON.parse(localStorage.getItem('dashui.pet.v1'));
     delete raw.hiAwardsInit; delete raw.hiAwards; delete raw.hiTickets; delete raw.hiBest;
     localStorage.setItem('dashui.pet.v1',JSON.stringify(raw));
   });
   await p.reload({waitUntil:'domcontentloaded'});await p.waitForTimeout(1750);
   const c=await p.evaluate(()=>({tickets:Number(S.hiTickets||0),awards:S.hiAwards.slice(),
     init:S.hiAwardsInit,toasts:document.querySelectorAll('#toast.show').length}));
   log('⑦b 老存档首次',JSON.stringify(c));
   if(!c.init||c.tickets>0||c.toasts>0)F('⑦b 老存档补发券/刷屏',JSON.stringify(c));
   await ctx.close();
 }

 // ===== 8) 分享卡文案 / 卡面 / 云档接入 =====
 {
   const {ctx,p}=await open({toy:true});
   await p.click('.watergrid .btn[data-ml="250"]');await p.waitForTimeout(200);
   await p.click('#btnShare');await p.waitForSelector('#scImg');
   const d=await p.evaluate(()=>{
     const text=buildShareText({mode:'daily',sc:todayScore(),date:'11月12日',time:'15:00',
       mood:'通透',code:'DW-ABC123',quote:''});
     const snap=toySnapshot();
     return {hasHi:text.includes('可信水合指数'),hasHead:text.includes('审计链'),
       cardW:$('#scImg').naturalWidth,cardH:$('#scImg').naturalHeight,
       cloudHead:snap.days[dkey()].auditHead,chain:verifyAudit(today()).head,
       cloudOK:snap.days[dkey()].auditOK,cloudHi:snap.hydrationIndex,
       cloudAudit:toySensitiveAudit(snap)};
   });
   log('⑧ 分享卡/云档',JSON.stringify(d));
   if(!d.hasHi||!d.hasHead)F('⑧ 分享文案缺新指标',JSON.stringify(d));
   if(d.cardW!==640||d.cardH!==960)F('⑧ 卡面绘制异常',JSON.stringify(d));
   if(d.cloudHead!==d.chain||!d.cloudOK||!d.cloudAudit)F('⑧ 云档审计头异常',JSON.stringify(d));
   if(typeof d.cloudHi!=='number'||d.cloudHi<0)F('⑧ 云档水合指数未实时',d.cloudHi);
   await p.click('#scShut');
   await ctx.close();
 }

 // ===== 9) 设置面板：提醒策略 / 专注延期 =====
 {
   const {ctx,p}=await open();
   await p.click('#btnSet');await p.waitForSelector('#sRemindMode');
   await p.selectOption('#sRemindMode','fixed');
   await p.click('#sSave');await p.waitForTimeout(250);
   const a=await p.evaluate(()=>S.settings.remindMode);
   log('⑨ 提醒策略保存',a); if(a!=='fixed')F('⑨ 策略未保存',a);
   await p.click('#btnSet');await p.waitForSelector('#sFocus');
   await p.click('#sFocus');await p.waitForTimeout(250);
   const b=await p.evaluate(()=>({until:!!S.focusUntil,count:S.snoozeCount,
     future:S.focusUntil>Date.now(),why:reminderDecision(Date.now()).why}));
   log('⑨ 专注延期',JSON.stringify(b));
   if(!b.until||!b.future||b.count!==1||!b.why.includes('专注'))F('⑨ 专注失效',JSON.stringify(b));
   // 上限 3 次
   const c=await p.evaluate(()=>{
     for(let i=0;i<5;i++){
       if(S.snoozeDate!==dkey()){S.snoozeDate=dkey();S.snoozeCount=0;}
       if(Number(S.snoozeCount||0)<3){S.snoozeCount++;S.focusUntil=Date.now()+1800000;}
     }
     return S.snoozeCount;
   });
   log('⑨ 延期上限',c); if(c!==3)F('⑨ 延期次数未封顶',c);
   await ctx.close();
 }

 // ===== 10) Toy 层冒烟 + 原有全链路回归 =====
 {
   const {ctx,p}=await open();
   const base=await p.evaluate(()=>({mode:TOY.mode,on:TOY.on,sound:S.settings.sound,
     bgm:S.settings.bgm,defaultOff:localStorage.getItem('dashui.audio.defaultOff')}));
   log('⑩ 本地形态',JSON.stringify(base));
   if(base.mode!=='local'||base.on||base.sound||base.bgm)F('⑩ 本地/默认关异常',JSON.stringify(base));
   // 4 形象
   for(const id of ['cat','bean','daily','drop']){
     await p.click(`#avatarRow [data-av="${id}"]`);await p.waitForTimeout(100);
     const r=await p.evaluate(()=>S.avatar);
     if(r!==id)F('⑩ 形象异常',id+'→'+r);
   }
   log('⑩ 4 形象','通过');
   // 防作弊连点
   await p.click('.watergrid .btn[data-ml="250"]');await p.waitForTimeout(160);
   await p.click('.watergrid .btn[data-ml="250"]');await p.waitForTimeout(160);
   const n=await p.evaluate(()=>today().logs.filter(l=>l.type==='water').length);
   log('⑩ 防作弊连点',n); if(n!==1)F('⑩ 防作弊失效',n);
   // 双榜
   await p.click('#btnBoard');await p.waitForSelector('#scList');
   await p.locator('#scWrap [data-bt="all"]').click();await p.waitForTimeout(200);
   const banner=await p.locator('.sc-banner').count();
   log('⑩ 历史总榜横幅',banner); if(banner!==1)F('⑩ 横幅缺失',banner);
   await p.click('#scClose');
   // 音频面板
   await p.click('#btnAudio');await p.waitForSelector('#auState');
   const ap=await p.evaluate(()=>({icons:document.querySelectorAll('.au-grid img').length,
     banner:$('.au-banner img')?.naturalWidth>0}));
   log('⑩ 音频面板',JSON.stringify(ap));
   if(ap.icons!==6||!ap.banner)F('⑩ 音频面板异常',JSON.stringify(ap));
   await p.click('#auDone');
   // 剧场
   await p.click('#btnStory');await p.waitForTimeout(350);
   const st=await p.evaluate(()=>$('#storyLayer').classList.contains('show'));
   log('⑩ 剧情层',st); if(!st)F('⑩ 剧情层未开','');
   await p.click('#stClose');
   // 凌晨语录
   const night=await p.evaluate(()=>{
     if(!isDeepNight()) return {deep:false,bad:[],slot:timeSlot()};
     const bad=[];for(let i=0;i<20;i++){const q=localQuote(buildCtx()).text;
       if(/太阳挺好|天刚亮|刚开机/.test(q))bad.push(q);}
     return {deep:true,bad:bad.slice(0,2)};
   });
   log('⑩ 凌晨语录',JSON.stringify(night));
   if(night.deep&&night.bad.length)F('⑩ 凌晨仍有白天词',JSON.stringify(night.bad));
   // 刷新持久化 + 审计链仍完整
   await p.evaluate(()=>{S.avatar='bean';save();});
   await p.reload({waitUntil:'domcontentloaded'});await p.waitForTimeout(1750);
   const after=await p.evaluate(()=>({av:S.avatar,v:verifyAudit(today()),mig:S.auditMigrated,hi:hydrationIndex()}));
   log('⑩ 刷新后',JSON.stringify(after));
   if(after.av!=='bean'||!after.v.ok||after.mig!==1)F('⑩ 刷新持久化异常',JSON.stringify(after));
   await ctx.close();
 }

 // ===== 11) Toy 形态冒烟 =====
 {
   const {ctx,p}=await open({toy:true});
   const d=await p.evaluate(()=>({mode:TOY.mode,ready:TOY.ready,chip:$('#toyChip').textContent.trim(),
     hi:hydrationIndex(),v:verifyAudit(today()).ok}));
   log('⑪ Toy 冒烟',JSON.stringify(d));
   if(d.mode!=='cloud'||!d.ready||!d.chip.includes('云存档')||!d.v)F('⑪ Toy 形态异常',JSON.stringify(d));
   await p.click('#btnBoard');await p.waitForSelector('#scWrap');
   const tabs=await p.locator('#scWrap [data-bt]').allTextContents();
   log('⑪ 榜单 tab',JSON.stringify(tabs));
   if(tabs.length!==3)F('⑪ 平台榜 tab 缺失',JSON.stringify(tabs));
   await p.click('#scClose');
   await ctx.close();
 }

 // ===== 12) 375px 窄屏 =====
 {
   const {ctx,p}=await open({w:375,h:812});
   const ov=await p.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
   const box=await p.evaluate(()=>{const e=$('#hiLine');return {h:e.offsetHeight,
     w:e.scrollWidth,cw:e.clientWidth};});
   log('⑫ 375px',JSON.stringify({ov,box}));
   if(ov>2||box.w>box.cw+2)F('⑫ 窄屏溢出',JSON.stringify({ov,box}));
   await p.screenshot({path:ROOT+'/大水计算器-合并版-P0指标-手机预览.png'});
   await ctx.close();
 }

 // ===== 13) 体积 / 零外链 =====
 {
   const st=fs.statSync(ROOT+'/大水计算器-合并版.html');
   const html=fs.readFileSync(ROOT+'/大水计算器-合并版.html','utf8');
   const base=fs.statSync(ROOT+'/_base_before_p0.html').size;
   const ext=html.match(/(?:src|href)\s*=\s*["'](?!data:)(?:https?:|\/\/|\.\/|\/)[^"']+/gi)||[];
   const delta=Math.round((st.size-base)/1024*10)/10;
   log('⑬ 体积/增量/外链',`${Math.round(st.size/1024*10)/10} KiB / +${delta} KiB / ${JSON.stringify(ext)}`);
   if(ext.length||/cdn\.jsdelivr|unpkg\.com|cdnjs/.test(html))F('⑬ 出现外链',JSON.stringify(ext));
   if(st.size>1024*1024)F('⑬ 体积超 1 MiB',st.size);
 }

 console.log('\n=== 巡检汇总 ===');
 console.log('发现项:',findings.length);findings.forEach(([k,v])=>console.log('  ·',k,'→',v));
 console.log('控制台错误:',errs.length);errs.forEach(e=>console.log('  ·',e));
 await browser.close();srv.close();
 process.exit(findings.length||errs.length?1:0);
})().catch(e=>{console.error('FATAL',e);if(browser)browser.close();srv.close();process.exit(2)});
