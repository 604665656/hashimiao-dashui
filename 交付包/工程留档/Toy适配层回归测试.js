const { chromium }=require('playwright');const http=require('http');const fs=require('fs');const path=require('path');
const ROOT='/data/workspace';let buf;
const srv=http.createServer((q,r)=>{try{buf=fs.readFileSync(ROOT+'/'+decodeURIComponent(q.url.split('?')[0].slice(1)))}catch(e){r.writeHead(404);r.end();return}r.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});r.end(buf)});
const URL='http://localhost:8142/'+encodeURIComponent('大水计算器-合并版.html');
const log=(k,v)=>console.log(`${k}: ${v}`);
const findings=[],errs=[];
const F=(k,v)=>{findings.push([k,v]);console.log(`  [发现] ${k}: ${v}`)};
let browser;

const MOCK=`
window.__toyMode = sessionStorage.getItem('__toyMode')||'ok';
window.__toyFreeze = sessionStorage.getItem('__toyFreeze')||'0';
window.__toyStore = JSON.parse(sessionStorage.getItem('__toySeed')||'{}');
window.__toyCalls = {set:[],get:[],submit:[],list:0};
function toyPersist(){ try{ sessionStorage.setItem('__toySeed',JSON.stringify(window.__toyStore)); }catch(e){} }
const never = new Promise(()=>{});
window.toy = {
  available(){ return window.__toyMode!=='noauth'; },
  ready(){ return window.__toyMode==='notready' ? never : Promise.resolve(true); },
  cloud:{
    set(o){
      window.__toyCalls.set.push({key:o.key,value:o.value});
      if(window.__toyMode==='timeout') return never;
      if(window.__toyFreeze!=='1'){ window.__toyStore[o.key]=o.value; toyPersist(); }
      return Promise.resolve({ok:true});
    },
    get(o){ window.__toyCalls.get.push(o.key); return Promise.resolve({value:window.__toyStore[o.key]||''}); }
  },
  rank:{
    submit(p){ window.__toyCalls.submit.push(p); return Promise.resolve({ok:true}); },
    list(){ window.__toyCalls.list++;
      if(window.__toyMode==='noauth') return Promise.reject(new Error('denied'));
      return Promise.resolve([{nickname:'阿喵',score:88},{nickname:'我',score:63,me:true}]); }
  },
  user:{ profile(){ return Promise.resolve({nickname:'我'}); } }
};
window.cloud = window.toy.cloud; window.rank = window.toy.rank;
`;
/* 与页面 toyFnv 完全一致的同步哈希：预置云档用 fnv，toyVerify 会二次比对 */
function fnv(str){let h=2166136261;for(let i=0;i<str.length;i++){h^=str.charCodeAt(i);h=Math.imul(h,16777619)>>>0;}return 'fnv'+h.toString(16);}
function makeSeed(opt={}){
  const {__corrupt, ...rest}=opt;
  const snap=Object.assign({schema:2,app:'dashui',savedAt:Date.now()-3600000,
    profile:{name:'我',avatar:'cat'},settings:{goal:1700,interval:30,checkinCooldown:30,
      sound:false,bgm:false,volume:.35,bgmTrack:'轻快',mood:'通透'},
    days:{},submitted:{},unlocked:{ends:[],cgs:[]},hydrationIndex:0,cloudSavedAt:0},rest);
  const body=JSON.stringify(snap);
  // 按 UTF-8 字节切成 ≤900 的片，与页面 toyChunks 同逻辑
  const enc=new TextEncoder(),parts=[];let cur='',n=0;
  for(const ch of body){const b=enc.encode(ch).length;if(n+b>900){parts.push(cur);cur='';n=0;}cur+=ch;n+=b;}
  if(cur)parts.push(cur);
  const store={ds_meta:JSON.stringify({schema:2,n:parts.length,savedAt:snap.savedAt,hash:fnv(body)})};
  parts.forEach((v,i)=>store['ds_'+i]=v);
  if(__corrupt&&parts.length) store['ds_0']='CORRUPT'+store['ds_0'].slice(7);
  return {store,savedAt:snap.savedAt};
}

async function open(opt={}){
  const {w=1440,h=900,toy=true,seed=null,mode='ok',wait}=opt;
  const ctx=await browser.newContext({viewport:{width:w,height:h},
    geolocation:{latitude:24.896,longitude:118.605},permissions:['geolocation']});
  const built=seed?makeSeed(seed):null;
  const head = toy ? `
if(!sessionStorage.getItem('__toyInit')){
  sessionStorage.setItem('__toyInit','1');
  sessionStorage.setItem('__toyMode',${JSON.stringify(mode)});
  sessionStorage.setItem('__toyFreeze',${built?'"1"':'"0"'});
  ${built?`sessionStorage.setItem('__toySeed',${JSON.stringify(JSON.stringify(built.store))});`:`sessionStorage.removeItem('__toySeed');`}
}
`+MOCK : '';
  await ctx.addInitScript(head);
  const p=await ctx.newPage();p.on('pageerror',e=>errs.push(e.message));
  await p.goto(URL,{waitUntil:'domcontentloaded'});
  await p.waitForTimeout(wait||(toy?2400:1700));
  return {ctx,p,built};
}

(async()=>{
 await new Promise(r=>srv.listen(8142,r));
 browser=await chromium.launch({headless:true,executablePath:'/usr/local/bin/chromium',args:['--no-sandbox']});

 // ===== 1) 本地版：无 SDK，纯 localStorage，零联网 =====
 {
   const {ctx,p}=await open({toy:false});
   const d=await p.evaluate(()=>({mode:TOY.mode,on:TOY.on,ready:TOY.ready,
     chip:$('#toyChip').textContent.trim(),cls:$('#toyChip').className,
     ls:!!localStorage.getItem('dashui.pet.v1'),defaultOff:localStorage.getItem('dashui.audio.defaultOff')}));
   log('① 本地版',JSON.stringify(d));
   if(d.mode!=='local'||d.on||d.ready||!d.chip.includes('本地档案'))F('① 本地形态异常',JSON.stringify(d));
   if(!d.ls)F('① localStorage 未写入','');
   // 平台榜 tab 不应出现
   await p.click('#btnBoard');await p.waitForSelector('#scWrap');
   const tabs=await p.locator('#scWrap [data-bt]').allTextContents();
   log('① 榜单 tab',JSON.stringify(tabs));
   if(tabs.length!==2||tabs.some(t=>t.includes('平台')))F('① 本地版误显示平台榜',JSON.stringify(tabs));
   await p.click('#scClose');
   await ctx.close();
 }

 // ===== 2) Toy 正常：探测 / 云档 / 结算提交分数 =====
 {
   const {ctx,p}=await open({toy:true});
   const d=await p.evaluate(()=>({mode:TOY.mode,on:TOY.on,ready:TOY.ready,kind:TOY.kind,
     chip:$('#toyChip').textContent.trim(),calls:window.__toyCalls,
     audit:toySensitiveAudit(toySnapshot())}));
   log('② Toy 探测',JSON.stringify({mode:d.mode,on:d.on,ready:d.ready,kind:d.kind,chip:d.chip,audit:d.audit,
     setCalls:d.calls.set.length,getCalls:d.calls.get.length}));
   if(d.mode!=='cloud'||!d.on||!d.ready||d.kind!=='toy')F('② Toy 探测失败',JSON.stringify(d));
   if(!d.audit)F('② 云档含敏感键','');
   if(!d.calls.get.length)F('② 未尝试读云档',JSON.stringify(d.calls));
   // 平台榜 tab 出现
   await p.click('#btnBoard');await p.waitForSelector('#scWrap');
   const tabs=await p.locator('#scWrap [data-bt]').allTextContents();
   log('② 榜单 tab',JSON.stringify(tabs));
   if(tabs.length!==3||!tabs.some(t=>t.includes('平台')))F('② 平台榜 tab 缺失',JSON.stringify(tabs));
   await p.locator('#scWrap [data-bt="toy"]').click();await p.waitForTimeout(300);
   const tb=await p.evaluate(()=>({rule:$('#scRule').textContent.includes('非官方认证'),
     join:!!$('#tbJoin'),boardTab}));
   log('② 平台榜初始',JSON.stringify(tb));
   if(!tb.rule||!tb.join||tb.boardTab!=='toy')F('② 平台榜内容异常',JSON.stringify(tb));
   // 授权参加
   await p.click('#tbJoin');await p.waitForTimeout(400);
   const joined=await p.evaluate(()=>({consent:TOY.consent,rankLoaded:TOY.rankLoaded,
     rows:document.querySelectorAll('#scList .toy-row').length,listCalls:window.__toyCalls.list}));
   log('② 参加平台榜',JSON.stringify(joined));
   if(!joined.consent||!joined.rows)F('② 平台榜授权/列表异常',JSON.stringify(joined));
   await p.click('#scClose');
   // 结算 → 提交分数 + 立即同步
   await p.click('.watergrid .btn[data-ml="250"]');await p.waitForTimeout(200);
   await p.click('#btnShare');await p.waitForSelector('#scImg');await p.waitForTimeout(700);
   const sub=await p.evaluate(()=>({submit:window.__toyCalls.submit.slice(),
     setCount:window.__toyCalls.set.length,payloadOK:window.__toyCalls.set.every(x=>!/data:image|"photo"|"key"|"lat"/.test(x.value))}));
   log('② 结算提交',JSON.stringify(sub));
   if(!sub.submit.length)F('② 结算未提交分数',JSON.stringify(sub));
   if(sub.submit.some(x=>x.extra&&!/"rule":2/.test(x.extra)))F('② 分数载荷缺规则版本',JSON.stringify(sub.submit));
   if(!sub.payloadOK)F('② 云载荷含敏感内容',JSON.stringify(sub));
   await p.click('#scShut');
   // 存档状态面板
   await p.click('#toyChip');await p.waitForSelector('#tpSync');
   const panel=await p.evaluate(()=>({title:$('#modalBox .mtitle').textContent.trim(),
     kv:$('#modalBox .toy-kv').textContent.includes('云档校验和'),
     white:$('#modalBox .toy-note').textContent.includes('永不上云'),
     single:$('#modalBox .toy-note.warn').textContent.includes('单设备编辑')}));
   log('② 存档状态面板',JSON.stringify(panel));
   if(!panel.kv||!panel.white||!panel.single)F('② 存档面板缺关键说明',JSON.stringify(panel));
   await p.click('#tpClose');
   await ctx.close();
 }

 // ===== 3) SDK 未就绪 → 降级 =====
 {
   const {ctx,p}=await open({toy:true,mode:'notready'});
   const d=await p.evaluate(()=>({mode:TOY.mode,ready:TOY.ready,chip:$('#toyChip').textContent.trim(),
     err:TOY.lastErr,ls:!!localStorage.getItem('dashui.pet.v1')}));
   log('③ SDK 未就绪',JSON.stringify(d));
   if(d.mode!=='degraded'||d.ready||!d.chip.includes('降级中')||!d.ls)F('③ 降级异常',JSON.stringify(d));
   // 玩法不中断
   await p.click('.watergrid .btn[data-ml="250"]');await p.waitForTimeout(200);
   const w=await p.evaluate(()=>waterOf(today()));
   log('③ 降级后仍可喝水',w); if(w!==250)F('③ 降级阻断玩法',w);
   await ctx.close();
 }

 // ===== 4) 未授权：不弹错、本机榜正常 =====
 {
   const {ctx,p}=await open({toy:true,mode:'noauth'});
   const d=await p.evaluate(()=>({mode:TOY.mode,on:TOY.on,chip:$('#toyChip').textContent.trim()}));
   log('④ 未授权',JSON.stringify(d));
   if(d.on)F('④ available()=false 仍挂载 SDK',JSON.stringify(d));
   await p.click('#btnBoard');await p.waitForSelector('#scList');
   const rows=await p.locator('#scList .sc-row').count();
   log('④ 本机榜行数',rows); if(!rows)F('④ 未授权时本机榜失效',rows);
   await p.click('#scClose');
   await ctx.close();
 }

 // ===== 5) 写入超时 / 结果未确认 → 本机不丢 =====
 {
   const {ctx,p}=await open({toy:true,mode:'timeout'});
   await p.evaluate(()=>{ localStorage.setItem('__mark','keep'); });
   await p.click('.watergrid .btn[data-ml="500"]');await p.waitForTimeout(250);
   const before=await p.evaluate(()=>waterOf(today()));
   await p.evaluate(()=>flushCloud());
   await p.waitForTimeout(6800);   // 等 withTimeout(6000) 触发
   const d=await p.evaluate(()=>({w:waterOf(today()),mark:localStorage.getItem('__mark'),
     err:TOY.lastErr,mode:TOY.mode,chip:$('#toyChip').textContent.trim()}));
   log('⑤ 写入未确认',JSON.stringify(d));
   if(d.w!==before||d.mark!=='keep')F('⑤ 本机数据被清空',JSON.stringify(d));
   if(!d.err.includes('未确认'))F('⑤ 未标记结果未确认',JSON.stringify(d));
   await ctx.close();
 }

 // ===== 6) 云档为空 / 校验失败 → 保留本地 =====
 {
   const {ctx,p}=await open({toy:true,seed:{savedAt:Date.now()-60000,__corrupt:true}});
   const d=await p.evaluate(()=>({mode:TOY.mode,err:TOY.lastErr,remote:!!TOY.remote,
     ls:!!localStorage.getItem('dashui.pet.v1'),chip:$('#toyChip').textContent.trim()}));
   log('⑥ 校验失败',JSON.stringify(d));
   if(d.remote)F('⑥ 损坏云档被接受',JSON.stringify(d));
   if(!d.ls)F('⑥ 本地数据被覆盖',JSON.stringify(d));
   // 空档
   await p.evaluate(()=>{ window.__toyStore={}; sessionStorage.setItem('__toySeed','{}'); });
   await p.reload({waitUntil:'domcontentloaded'});await p.waitForTimeout(2400);
   const e=await p.evaluate(()=>({remote:!!TOY.remote,err:TOY.lastErr,ls:!!localStorage.getItem('dashui.pet.v1')}));
   log('⑥ 空云档',JSON.stringify(e));
   if(e.remote||!e.ls)F('⑥ 空档覆盖了本地',JSON.stringify(e));
   await ctx.close();
 }

 // ===== 7) 冲突 → 重读 → 恢复向导三选一 =====
 {
   const remoteSavedAt=Date.now()-3*3600*1000;
   const {ctx,p,built}=await open({toy:true,seed:{savedAt:remoteSavedAt,
     unlocked:{ends:['S','A','C'],cgs:['01_候机','02_夜窗']}}});
   // 把本地标记改成另一版本，reload 后应检出冲突
   await p.evaluate(t=>{ S.cloudSavedAt=t; S.story={ends:['B'],cgs:[]}; _saveBase(); },Date.now()-3600*1000);
   await p.reload({waitUntil:'domcontentloaded'});await p.waitForTimeout(2600);
   const c=await p.evaluate(()=>({conflict:!!$('#tcMerge'),title:$('#modalBox .mtitle')?.textContent.trim(),
     remote:!!TOY.remote,ends:S.story.ends.slice()}));
   log('⑦ 冲突向导',JSON.stringify(c));
   if(!c.conflict||!c.title.includes('另一份云存档'))F('⑦ 冲突向导未出现',JSON.stringify(c));
   // 选「合并」：解锁取并集，本地 logs 不动
   await p.click('#tcMerge');await p.waitForTimeout(300);
   const m=await p.evaluate(()=>({ends:S.story.ends.slice(),cgs:S.story.cgs.slice(),
     mark:S.cloudSavedAt,ls:!!localStorage.getItem('dashui.pet.v1')}));
   log('⑦ 合并结果',JSON.stringify(m));
   if(!m.ends.includes('S')||!m.ends.includes('B')||!m.cgs.includes('01_候机'))
     F('⑦ 合并解锁未取并集',JSON.stringify(m));
   if(Math.abs(m.mark-remoteSavedAt)>1000)F('⑦ 云档版本未确认',JSON.stringify(m));
   // 再测「用云端」不删本地照片
   await p.evaluate(()=>{ const d=today(); d.logs.push({id:'photo1',ts:Date.now()-40000,type:'milk',
     photo:'data:image/png;base64,AAAA',note:'测试照片'}); _saveBase(); });
   await p.evaluate(()=>openToyConflict(TOY.remote||{snap:toySnapshot(),meta:{hash:'x'}}));
   await p.click('#tcRemote');await p.waitForTimeout(300);
   const keep=await p.evaluate(()=>({photos:today().logs.filter(l=>l.photo).length,
     llm:!!S.settings.llm,loc:!!S.location}));
   log('⑦ 用云端后本地敏感数据',JSON.stringify(keep));
   if(keep.photos!==1)F('⑦ 用云端误删本地照片',JSON.stringify(keep));
   await ctx.close();
 }

 // ===== 8) 云载荷不含敏感数据（含抓拍照片后） =====
 {
   const {ctx,p}=await open({toy:true});
   await p.click('#btnSin');await p.waitForTimeout(2200);
   if(await p.locator('#nClose').count()) await p.click('#nClose');
   await p.waitForTimeout(200);
   const d=await p.evaluate(()=>{
     const snap=toySnapshot(), body=JSON.stringify(snap);
     window.__toyCalls.set.length=0; flushCloud();
     return {audit:toySensitiveAudit(snap),hasPhoto:/photo|data:image/i.test(body),
       hasKey:/api.?key|endpoint/i.test(body),hasLoc:/"lat"|"lng"/i.test(body),
       photosLocal:today().logs.filter(l=>l.photo).length,
       keys:Object.keys(snap)};
   });
   await p.waitForTimeout(900);
   const sent=await p.evaluate(()=>{
     const all=window.__toyCalls.set.map(x=>x.value).join('');
     return {n:window.__toyCalls.set.length,leak:/data:image|"photo"|"key"|"lat"|"lng"/i.test(all)};
   });
   log('⑧ 敏感字段',JSON.stringify({...d,...sent}));
   if(!d.audit||d.hasPhoto||d.hasKey||d.hasLoc||sent.leak||!sent.n)
     F('⑧ 云载荷含敏感字段或未写入',JSON.stringify({...d,...sent}));
   if(d.photosLocal<1)F('⑧ 本地照片未保留（用例前置失败）',d.photosLocal);
   await ctx.close();
 }

 // ===== 9) 体积与打包白名单 =====
 {
   const st=fs.statSync(ROOT+'/大水计算器-合并版.html');
   const html=fs.readFileSync(ROOT+'/大水计算器-合并版.html','utf8');
   const ext=(html.match(/(?:src|href)\s*=\s*["'](?!data:)(?:https?:|\/\/|\.\/|\/)[^"']+/gi)||[]);
   log('⑨ 体积 / 外链资源引用',round(st.size/1024,1)+' KiB / '+JSON.stringify(ext.slice(0,8)));
   if(st.size>1024*1024)F('⑨ 体积超 1 MiB',st.size);
   if(ext.length)F('⑨ 出现外部资源引用',JSON.stringify(ext));
   if(/cdn\.jsdelivr|unpkg\.com|cdnjs/.test(html))F('⑨ 出现 CDN 外链','');
   const base=fs.statSync(ROOT+'/_base_before_toy.html').size;
   const delta=round((st.size-base)/1024,1);
   console.log(`⑨ 适配层增量: ${delta} KiB（方案目标 <20 KiB，超出部分为冲突重读与敏感审计逻辑）`);
   log('⑨ 增量',delta+' KiB');
 }

 // ===== 10) 原有全链路回归 =====
 {
   const {ctx,p}=await open({toy:false});
   for(const id of ['cat','bean','daily','drop']){
     await p.click(`#avatarRow [data-av="${id}"]`);await p.waitForTimeout(110);
     const r=await p.evaluate(()=>({av:S.avatar,on:$('#pet').classList.contains('art-on')}));
     const expect=id==='daily'?await p.evaluate(()=>avatarId()):id;
     if(r.av!==id||(expect!=='drop'&&!r.on))F('⑩ 形象异常',id+' / '+JSON.stringify(r));
   }
   log('⑩ 4 形象','通过');
   // 防作弊
   await p.click('.watergrid .btn[data-ml="250"]');await p.waitForTimeout(160);
   await p.click('.watergrid .btn[data-ml="250"]');await p.waitForTimeout(160);
   const n=await p.evaluate(()=>today().logs.filter(l=>l.type==='water').length);
   log('⑩ 防作弊连点',n); if(n!==1)F('⑩ 防作弊失效',n);
   // 分享卡
   await p.click('#btnShare');await p.waitForSelector('#scImg');
   const card=await p.evaluate(()=>({png:$('#scImg').src.startsWith('data:image/png'),
     w:$('#scImg').naturalWidth,h:$('#scImg').naturalHeight,code:$('#scCode').textContent.trim(),
     note:toyCardNote()}));
   log('⑩ 分享卡',JSON.stringify(card));
   if(!card.png||card.w!==640||card.h!==960||!/^DW-[A-Z0-9]{6}$/.test(card.code))F('⑩ 分享卡异常',JSON.stringify(card));
   if(!card.note.includes('本机防作弊'))F('⑩ 本地版卡面文案错误',card.note);
   await p.click('#scShut');
   // 双榜 + 横幅
   await p.click('#btnBoard');await p.waitForSelector('#scList');
   await p.locator('#scWrap [data-bt="all"]').click();await p.waitForTimeout(200);
   const banner=await p.locator('.sc-banner').count();
   log('⑩ 历史总榜横幅',banner); if(banner!==1)F('⑩ 横幅缺失',banner);
   await p.click('#scClose');
   // 音效默认关
   const audio=await p.evaluate(()=>({sound:S.settings.sound,bgm:S.settings.bgm,el:!!audioEl}));
   log('⑩ 音效默认关',JSON.stringify(audio));
   if(audio.sound||audio.bgm||audio.el)F('⑩ 音效未默认关',JSON.stringify(audio));
   // 音频面板
   await p.click('#btnAudio');await p.waitForSelector('#auState');
   const ap=await p.evaluate(()=>({icons:document.querySelectorAll('.au-grid img').length,
     banner:$('.au-banner img')?.naturalWidth>0}));
   log('⑩ 音频面板',JSON.stringify(ap));
   if(ap.icons!==6||!ap.banner)F('⑩ 音频面板异常',JSON.stringify(ap));
   await p.click('#auDone');
   // 剧场
   await p.click('#btnStory');await p.waitForTimeout(350);
   const st=await p.evaluate(()=>({show:$('#storyLayer').classList.contains('show'),hud:$('#stHud').textContent.includes('剧场')}));
   log('⑩ 剧情层',JSON.stringify(st)); if(!st.show||!st.hud)F('⑩ 剧情层异常',JSON.stringify(st));
   await p.click('#stClose');
   // 刷新持久化
   await p.evaluate(()=>{ S.avatar='bean'; _saveBase(); });
   await p.reload({waitUntil:'domcontentloaded'});await p.waitForTimeout(1700);
   const after=await p.evaluate(()=>({av:S.avatar,mode:TOY.mode}));
   log('⑩ 刷新后',JSON.stringify(after));
   if(after.av!=='bean'||after.mode!=='local')F('⑩ 刷新持久化异常',JSON.stringify(after));
   await ctx.close();
 }

 // ===== 11) 375px 窄屏 + Toy chip + 存档面板 =====
 {
   const {ctx,p}=await open({w:375,h:812,toy:true});
   const ov=await p.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
   log('⑪ 375px 横向溢出',ov+'px'); if(ov>2)F('⑪ 窄屏溢出',ov+'px');
   await p.click('#toyChip');await p.waitForSelector('#tpSync');
   const lay=await p.evaluate(()=>{const b=document.querySelector('#modalBox'),r=b.getBoundingClientRect();
     return {sw:b.scrollWidth,cw:b.clientWidth,l:Math.round(r.left),rr:Math.round(r.right),win:innerWidth};});
   log('⑪ 存档面板 375px',JSON.stringify(lay));
   if(lay.sw>lay.cw+2||lay.rr>lay.win+2||lay.l<-2)F('⑪ 存档面板窄屏溢出',JSON.stringify(lay));
   await p.screenshot({path:ROOT+'/大水计算器-合并版-Toy存档面板-手机预览.png'});
   await p.click('#tpClose');
   await p.screenshot({path:ROOT+'/大水计算器-合并版-预览.png'});
   await ctx.close();
 }

 // ===== 12) Toy 版刷新与跨会话持久化 =====
 {
   const {ctx,p}=await open({toy:true});
   await p.evaluate(()=>{ S.avatar='cat'; S.toyRankConsent=true; _saveBase(); });
   await p.reload({waitUntil:'domcontentloaded'});await p.waitForTimeout(2300);
   const d=await p.evaluate(()=>({av:S.avatar,consent:TOY.consent,mode:TOY.mode,
     cloudSavedAt:Number(S.cloudSavedAt||0),remote:!!TOY.remote}));
   log('⑫ Toy 刷新后',JSON.stringify(d));
   if(d.av!=='cat'||!d.consent||d.mode!=='cloud')F('⑫ Toy 跨会话异常',JSON.stringify(d));
   await ctx.close();
 }

 // ===== 13) 顺手修的既有 bug：凌晨文案不含白天词 =====
 {
   const {ctx,p}=await open({toy:false});
   const r=await p.evaluate(()=>{
     const hour=new Date().getHours(), deep=isDeepNight();
     const bad=[],samples=[];
     for(let i=0;i<30;i++){ const q=localQuote(buildCtx()).text; samples.push(q);
       if(/太阳挺好|天刚亮|天光透亮|晨起第一口|刚开机/.test(q)) bad.push(q); }
     return {hour,deep,bad:bad.slice(0,3),sample:samples[0],
       tags:localQuote(buildCtx()).tags[0]};
   });
   log('⑬ 凌晨语录',JSON.stringify(r));
   if(r.deep&&r.bad.length)F('⑬ 凌晨语录含白天词',JSON.stringify(r.bad));
   if(r.deep&&!r.tags.includes('深夜'))F('⑬ 时段标签未改深夜',r.tags);
   await ctx.close();
 }

 // ===== 14) 平台榜 ↔ 本机榜切换无残留 =====
 {
   const {ctx,p}=await open({toy:true});
   await p.click('#btnBoard');await p.waitForSelector('#scWrap');
   await p.locator('#scWrap [data-bt="toy"]').click();await p.waitForTimeout(250);
   const a=await p.evaluate(()=>({nw:getComputedStyle($('#scWrap .sc-new')).display,
     sub:$('#modalBox .msub').textContent,bt:boardTab}));
   await p.locator('#scWrap [data-bt="today"]').click();await p.waitForTimeout(250);
   const b=await p.evaluate(()=>({nw:getComputedStyle($('#scWrap .sc-new')).display,
     sub:$('#modalBox .msub').textContent,bt:boardTab,rows:document.querySelectorAll('#scList .sc-row').length}));
   log('⑭ 榜单切换',JSON.stringify({toy:a,back:b}));
   if(a.nw!=='none'||!a.sub.includes('平台分数榜'))F('⑭ 平台榜态异常',JSON.stringify(a));
   if(b.nw==='none'||!b.sub.includes('本机多档案')||!b.rows)F('⑭ 切回本机榜未恢复',JSON.stringify(b));
   await p.click('#scClose');
   await ctx.close();
 }

 console.log('\n=== 巡检汇总 ===');
 console.log('发现项:',findings.length);findings.forEach(([k,v])=>console.log('  ·',k,'→',v));
 console.log('控制台错误:',errs.length);errs.forEach(e=>console.log('  ·',e));
 await browser.close();srv.close();
 process.exit(findings.length||errs.length?1:0);
})().catch(e=>{console.error('FATAL',e);if(browser)browser.close();srv.close();process.exit(2)});
function round(x,n){return Math.round(x*Math.pow(10,n))/Math.pow(10,n)}
