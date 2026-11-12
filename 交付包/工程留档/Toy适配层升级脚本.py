# -*- coding: utf-8 -*-
"""给合并版加一层 Toy 能力探测 + 云存档 + 平台分数榜 + 自动降级。
硬约束：同一个 HTML，本地双击零联网；Toy 容器才挂平台能力；敏感数据永不上云。"""
import re, os
P = '/data/workspace/大水计算器-合并版.html'
s = open(P, encoding='utf-8').read()
before = os.path.getsize(P)

def must(old, new, cnt=1):
    global s
    n = s.count(old)
    assert n == cnt, f'锚点命中 {n} 次（期望 {cnt}）：{old[:100]!r}'
    s = s.replace(old, new, cnt)

# ---------- 1) HUD chip ----------
must('''      <div id="avatarRow" class="av-row"></div>
    </div>''',
     '''      <div id="avatarRow" class="av-row"></div>
      <button id="toyChip" class="toy-chip" title="查看存档状态">💾 本地档案</button>
    </div>''')

# ---------- 2) CSS ----------
CSS = '''
/* ===== Toy 上架适配层：存档状态 / 平台榜 ===== */
.toy-chip{display:inline-flex;align-items:center;gap:5px;margin-top:8px;border:1px dashed rgba(90,78,62,.28);
  background:rgba(255,255,255,.6);border-radius:99px;padding:5px 11px;font-size:10.5px;font-weight:700;
  color:#6b6255;cursor:pointer;font-family:inherit;transition:.18s}
.toy-chip:hover{border-style:solid;background:#eaf3f6;color:#3d6d87}
.toy-chip.cloud{border-color:#6c9a76;background:#eef6f0;color:#4a7a58}
.toy-chip.degraded{border-color:#c08a54;background:#fbf3e8;color:#96652f}
.toy-kv{display:grid;grid-template-columns:88px 1fr;gap:5px 9px;font-size:11.5px;line-height:1.75;
  color:#4a5a63;margin:9px 0}
.toy-kv b{color:#8b8276;font-weight:600}
.toy-note{background:#f2f7fa;border-radius:11px;padding:9px 11px;font-size:10.5px;
  line-height:1.85;color:#4a5a63;margin:8px 0}
.toy-note.warn{background:#fbf3e8;color:#8a6532}
.toy-list{font-size:10.5px;line-height:1.9;color:#6b6255;margin:7px 0 2px;padding-left:16px}
.toy-row{display:flex;align-items:center;gap:9px;border:1px solid rgba(90,78,62,.14);
  background:#fff;border-radius:11px;padding:9px 11px;margin-bottom:6px;font-size:11.5px}
.toy-row .n{width:26px;font-weight:800;color:#3d6d87;text-align:center}
.toy-row .nm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.toy-row .pt{font-weight:800;color:#3d6d87}
.toy-row.me{background:#eaf3f6;border-color:#3d6d87}
.toy-empty{text-align:center;color:#8b8276;font-size:11px;padding:16px 8px;line-height:1.8}
@media(max-width:420px){ .toy-kv{grid-template-columns:76px 1fr;font-size:10.5px} }
'''
must('</style>', CSS + '</style>')

# ---------- 3) 分享卡与文案按形态切换 ----------
must("    `校验码 ${o.code}（本机防作弊，数据不上传）\\n`+",
     "    `校验码 ${o.code} · ${toyShareNote()}\\n`+")
must("  g.fillText('本机防作弊校验码 · 打卡冷却 '+cooldownMin()+' 分钟（独立于提醒间隔）',154,908);",
     "  g.fillText(toyCardNote(),154,908);")

# ---------- 3.5) 顺手修既有 bug：凌晨 0-6 点被当成「清晨」，语录会说太阳挺好 ----------
must('''/* 深夜不出现「太阳挺好」这类白天词，按实际时段换一套 */''',
     '''/* 凌晨 0-6 点在积分口径里仍算 dawn，但文案不能说「天刚亮 / 太阳挺好」 */
function isDeepNight(){ const h=new Date().getHours(); return h>=22||h<6; }
const DEEP_NIGHT_TIME_WORD=['凌晨这一点','夜深了','灯还亮着','大半夜里'];
/* 深夜不出现「太阳挺好」这类白天词，按实际时段换一套 */''')
must("  const w=(slot==='night'?NIGHT_WEATHER_WORD[kind]:WEATHER_WORD[kind])||WEATHER_WORD[kind]||WEATHER_WORD['阴'];",
     "  const dark = slot==='night'||isDeepNight();\n  const w=(dark?NIGHT_WEATHER_WORD[kind]:WEATHER_WORD[kind])||WEATHER_WORD[kind]||WEATHER_WORD['阴'];")
must("  const night = ctx.slot==='night';",
     "  const night = ctx.slot==='night'||isDeepNight();")
must("      `${rnd(TIME_WORD[ctx.slot])}，${weatherWord(ctx.kind,ctx.slot)}，${rnd(MOOD_WORD[ctx.mood])}——`,",
     "      `${rnd(isDeepNight()?DEEP_NIGHT_TIME_WORD:TIME_WORD[ctx.slot])}，${weatherWord(ctx.kind,ctx.slot)}，${rnd(MOOD_WORD[ctx.mood])}——`,")
must("    '⏰ '+ctx.date+' '+ctx.time+' '+({dawn:'清晨',morning:'上午',noon:'午间',afternoon:'下午',evening:'傍晚',night:'深夜'}[ctx.slot]),",
     "    '⏰ '+ctx.date+' '+ctx.time+' '+(isDeepNight()?'深夜':({dawn:'清晨',morning:'上午',noon:'午间',afternoon:'下午',evening:'傍晚',night:'深夜'}[ctx.slot])),")

# ---------- 4) 第三个 script：适配层 ----------
TOY_JS = r'''
/* ==================================================================
   Toy 上架适配层（纯增量，本地双击时完全不启用）
   - 平台云存档只放「最小可重建摘要」；照片 / API Key / 精确坐标永不上云
   - SDK 未就绪 / 未授权 / 报错 → 静默回退 localStorage
   - 读档：先本地、再云、冲突重读、绝不自动以空档覆盖本地
   ================================================================== */
const TOY = {
  on:false, ready:false, mode:'local', kind:'', sdk:null, consent:false,
  lastSync:0, lastErr:'', remote:null, rankList:[], rankLoaded:false, writing:false
};
let _cloudTimer=null, _toyBooted=false;

function toyFnv(str){ let h=2166136261; for(let i=0;i<str.length;i++){h^=str.charCodeAt(i);h=Math.imul(h,16777619)>>>0;} return 'fnv'+h.toString(16); }
async function toyHash(str){
  try{
    if(window.crypto&&crypto.subtle&&window.TextEncoder){
      const b=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(str));
      return [...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('').slice(0,16);
    }
  }catch(e){}
  return toyFnv(str);
}
async function toyVerify(body,hash){
  if(await toyHash(body)===hash) return true;
  return toyFnv(body)===hash;          // 写入时若 subtle 不可用，用同一 fallback 复核
}
function withTimeout(p,ms){
  return Promise.race([Promise.resolve(p),new Promise((_,rej)=>setTimeout(()=>rej(new Error('toy-timeout')),ms))]);
}
function toyProbe(){
  const c=[];
  if(window.toy) c.push(['toy',window.toy]);
  if(window.studio&&window.studio.sdk&&window.studio.sdk.toy) c.push(['studio',window.studio.sdk.toy]);
  if(window.ToySDK) c.push(['ToySDK',window.ToySDK]);
  if(window.bl&&(window.bl.setUserCloudStorage||window.bl.getUserCloudStorage)) c.push(['bl',window.bl]);
  for(const [kind,t] of c){
    if(typeof t.available==='function'){
      try{ if(t.available()===false) continue; }catch(e){ continue; }
    }
    TOY.sdk=t; TOY.kind=kind; TOY.on=true; return t;
  }
  return null;
}
function toyCloud(){
  const t=TOY.sdk; if(!t) return null;
  if(t.cloud&&(t.cloud.set||t.cloud.get)) return {kind:'ns',api:t.cloud};
  if(window.cloud&&typeof window.cloud.set==='function') return {kind:'ns',api:window.cloud};
  if(t.setUserCloudStorage||window.bl&&window.bl.setUserCloudStorage) return {kind:'bl',api:(t.setUserCloudStorage?t:window.bl)};
  return null;
}
function toyRank(){
  const t=TOY.sdk; if(!t) return null;
  if(t.rank&&(t.rank.submit||t.rank.list)) return t.rank;
  if(window.rank&&(window.rank.submit||window.rank.list)) return window.rank;
  if(typeof t.submitScore==='function'||typeof t.getRankList==='function') return t;
  return null;
}
function toyVal(x){
  if(x==null) return '';
  if(typeof x==='string') return x;
  if(typeof x==='object'){
    if(typeof x.value==='string') return x.value;
    if(x.data&&typeof x.data.value==='string') return x.data.value;
    if(x.KVDataList) return x;
  }
  return '';
}
async function toyWriteSlices(c,slices){
  if(c.kind==='bl'){
    await c.api.setUserCloudStorage({KVDataList:slices.map(x=>({key:x.key,value:x.value,order:x.order}))});
    return;
  }
  for(const x of slices){
    const r=c.api.set({key:x.key,value:x.value,order:x.order});
    if(r&&typeof r.then==='function') await r;
  }
}
async function toyReadSlices(c,n){
  if(c.kind==='bl'){
    const keys=['ds_meta',...Array.from({length:n},(_,i)=>'ds_'+i)];
    const r=await c.api.getUserCloudStorage({keyList:keys});
    const arr=(r&&r.KVDataList)||(r&&r.data&&r.data.KVDataList)||[];
    const map={}; arr.forEach(x=>{ if(x&&x.key) map[x.key]=x.value; });
    return ['ds_meta',...Array.from({length:n},(_,i)=>'ds_'+i)].map(k=>map[k]||'');
  }
  const out=[];
  for(let i=-1;i<n;i++){
    const k=i<0?'ds_meta':'ds_'+i;
    const r=await c.api.get({key:k});
    out.push(toyVal(r));
  }
  return out;
}
function toyChunks(str,max){
  const enc=new TextEncoder(),out=[];let cur='',n=0;
  for(const ch of str){
    const b=enc.encode(ch).length;
    if(n+b>max){ out.push(cur);cur='';n=0; }
    cur+=ch;n+=b;
  }
  if(cur)out.push(cur);
  return out.length?out:[''];
}

/* ---- 云档：白名单构造，绝不 spread 整个 S ---- */
function toySnapshot(){
  const p=PROFILE(), days=p.days||{}, out={}, submitted={};
  for(const k in days){
    const d=days[k]||{}, logs=d.logs||[];
    let sc={ml:0,valid:0,cheat:0,milk:0,achieved:false,achievedAt:0,total:0};
    try{ sc=scoreDay(d,d.goalSnapshot||goalOf()); }catch(e){}
    out[k]={ml:sc.ml,valid:sc.valid,cheat:sc.cheat,milk:sc.milk,
      achieved:!!sc.achieved,achievedAt:sc.achievedAt||0,score:sc.total,
      mood:d.mood||'',auditLen:logs.length,auditHead:checkCode(logs.map(l=>l.id||'').join('|'))};
  }
  for(const k in (p.submitted||{})){
    const r=p.submitted[k]; submitted[k]={score:r.score,ml:r.ml,at:r.at,code:r.code};
  }
  const st=S.settings;
  return {
    schema:2, app:'dashui', savedAt:Date.now(),
    profile:{name:p.name||'',avatar:S.avatar||'drop'},
    settings:{goal:st.goal,interval:st.interval,checkinCooldown:st.checkinCooldown,
      sound:!!st.sound,bgm:!!st.bgm,volume:st.volume,bgmTrack:st.bgmTrack,mood:st.mood},
    days:out, submitted,
    unlocked:{ends:(S.story&&S.story.ends||[]).slice(),cgs:(S.story&&S.story.cgs||[]).slice()},
    hydrationIndex:Number(S.hydrationIndex||0),
    cloudSavedAt:Number(S.cloudSavedAt||0)
  };
}
function toySensitiveAudit(snap){
  /* 只查键名，不查值：用户档案名叫 "latte" 之类不应被误判 */
  const keys=new Set();
  (function walk(x){ if(x&&typeof x==='object'&&!Array.isArray(x)){
    Object.keys(x).forEach(k=>{ keys.add(k); walk(x[k]); }); } })(snap);
  return !['photo','photos','key','apiKey','endpoint','lat','lng','latitude','longitude',
    'llm','location','logs','quote'].some(k=>keys.has(k));
}
async function toyWrite(){
  if(!TOY.on||!TOY.ready||TOY.writing) return false;
  const c=toyCloud(); if(!c) return false;
  TOY.writing=true;
  try{
    const snap=toySnapshot();
    if(!toySensitiveAudit(snap)){ TOY.lastErr='敏感字段拦截，已跳过云写入'; renderToyChip(); return false; }
    const body=JSON.stringify(snap), hash=await toyHash(body), parts=toyChunks(body,900);
    const slices=[{key:'ds_meta',value:JSON.stringify({schema:2,n:parts.length,savedAt:snap.savedAt,hash}),order:1000}]
      .concat(parts.map((v,i)=>({key:'ds_'+i,value:v,order:999-i})));
    await withTimeout(toyWriteSlices(c,slices),6000);
    TOY.lastSync=Date.now(); TOY.lastErr=''; TOY.mode='cloud';
    /* 不把 savedAt 回写本地：写入「结果未确认」，留待下次读档重读验证 */
    renderToyChip(); return true;
  }catch(e){ TOY.lastErr='写入未确认（已保留本机）'; TOY.mode='degraded'; renderToyChip(); return false; }
  finally{ TOY.writing=false; }
}
async function toyRead(){
  const c=toyCloud(); if(!c) return null;
  try{
    const metaRaw=await withTimeout(c.kind==='bl'
      ? c.api.getUserCloudStorage({keyList:['ds_meta']})
      : c.api.get({key:'ds_meta'}),4000);
    let raw=c.kind==='bl'
      ? (((metaRaw&&metaRaw.KVDataList)||[]).find(x=>x.key==='ds_meta')||{}).value
      : toyVal(metaRaw);
    const meta=JSON.parse(raw||'null');
    if(!meta||meta.schema!==2||!meta.n||meta.n>120||!meta.hash) return null;
    const arr=await withTimeout(toyReadSlices(c,meta.n),6000);
    const body=arr.slice(1).join('');
    if(!body||!(await toyVerify(body,meta.hash))) return null;
    const snap=JSON.parse(body);
    if(snap.schema!==2||snap.app!=='dashui') return null;
    return {snap,meta};
  }catch(e){ return null; }
}
function toyMergeUnlocked(snap){
  S.story=S.story||{ends:[],cgs:[]};
  const u=snap.unlocked||{};
  (u.ends||[]).forEach(x=>{if(!S.story.ends.includes(x))S.story.ends.push(x);});
  (u.cgs||[]).forEach(x=>{if(!S.story.cgs.includes(x))S.story.cgs.push(x);});
}
/* 「用云端」只覆盖白名单摘要字段；本地 logs / 照片 / llm / location 一律保留 */
function toyApplyRemote(snap){
  const p=PROFILE();
  if(snap.profile){ if(snap.profile.name)p.name=snap.profile.name; S.avatar=snap.profile.avatar||S.avatar; }
  if(snap.settings) ['goal','interval','checkinCooldown','sound','bgm','volume','bgmTrack','mood']
    .forEach(k=>{ if(snap.settings[k]!==undefined) S.settings[k]=snap.settings[k]; });
  if(snap.submitted){
    p.submitted=p.submitted||{};
    for(const k in snap.submitted){
      const r=snap.submitted[k];
      if(!p.submitted[k]) p.submitted[k]={date:k,score:r.score,ml:r.ml,at:r.at,code:r.code};
      else if((r.score||0)>(p.submitted[k].score||0)) p.submitted[k].score=r.score;
    }
  }
  toyMergeUnlocked(snap);
  S.cloudSavedAt=snap.savedAt||0;
  _saveBase();
  try{ renderAll(); }catch(e){}
}
function openToyConflict(r){
  TOY.remote=r;
  const s=r.snap;
  openModal(`<div class="mtitle">⚠ 发现另一份云存档</div>
    <div class="msub">两份进度不一致，先重读了一次，仍不同。请选一个处理方式。</div>
    <div class="toy-kv"><b>云端版本</b><span>${esc(fmtTime(s.savedAt||0))} · 校验和 ${esc(String(r.meta.hash).slice(0,12))}</span>
      <b>本机版本</b><span>${esc(fmtTime(Number(S.cloudSavedAt||0)||Date.now()))} · ${esc(PROFILE().name)}</span>
      <b>云端摘要</b><span>${Object.keys(s.days||{}).length} 天记录 · ${Object.keys(s.submitted||{}).length} 天成绩 · ${((s.unlocked||{}).ends||[]).length} 个结局</span></div>
    <div class="toy-note warn">不会自动用空档覆盖本机。照片、API Key、精确坐标只留在本机，任何选项都不会把它们上传或删除。</div>
    <div class="btnrow"><button class="btn primary" id="tcMerge">合并（解锁取并集）</button>
      <button class="btn ghost" id="tcRemote">用云端</button>
      <button class="btn ghost" id="tcLocal">用本机并覆盖云端</button></div>
    <div class="btnrow"><button class="btn ghost" id="tcLater">先不管，继续用本机</button></div>`);
  const done=(msg)=>{ try{closeModal();}catch(e){} try{toast(msg);}catch(e){} renderToyChip(); scheduleCloud(1200); };
  $('#tcMerge').onclick=()=>{ toyMergeUnlocked(s); S.cloudSavedAt=s.savedAt||0; _saveBase(); done('已合并解锁内容'); };
  $('#tcRemote').onclick=()=>{ toyApplyRemote(s); done('已用云端摘要重建进度'); };
  $('#tcLocal').onclick=()=>{ done('保留本机，稍后覆盖云端'); };
  $('#tcLater').onclick=()=>{ try{closeModal();}catch(e){} renderToyChip(); };
}
async function toyInit(){
  if(_toyBooted) return; _toyBooted=true;
  if(!toyProbe()){ TOY.mode='local'; renderToyChip(); return; }
  let ok=false;
  try{ ok=await withTimeout((async()=>{
    const t=TOY.sdk;
    if(typeof t.ready==='function') await Promise.resolve(t.ready());
    return true;
  })(),1200); }catch(e){
    /* 宿主注入竞态：再给一次短窗口，仍不就绪就立即降级，别把启动拖到 5 秒 */
    try{ await withTimeout(Promise.resolve(TOY.sdk.ready?TOY.sdk.ready():true),800); ok=true; }catch(_){}
  }
  if(!ok){ TOY.mode='degraded'; TOY.lastErr='SDK 未就绪，已存本机'; renderToyChip(); return; }
  TOY.ready=true; TOY.mode='cloud'; renderToyChip();
  let r=await toyRead();
  if(!r){
    /* 空档 / 校验失败 / 超时：保留本地，绝不覆盖 */
    TOY.lastErr='云端暂无可用存档';
    scheduleCloud(1500); renderToyChip(); return;
  }
  TOY.remote=r;
  const localMark=Number(S.cloudSavedAt||0), remoteMark=Number(r.snap.savedAt||0);
  if(localMark&&remoteMark!==localMark){
    const r2=await toyRead();                       /* 冲突 → 重新读取一次 */
    if(r2&&Number(r2.snap.savedAt||0)===remoteMark){ openToyConflict(r2); return; }
    if(r2){ TOY.remote=r2; r=r2; }
  }
  toyMergeUnlocked(r.snap);
  TOY.lastErr='';                     /* 云档已读到，清掉「暂无可用存档」的旧提示 */
  S.cloudSavedAt=Number(r.snap.savedAt||0); _saveBase();
  renderToyChip();
}
function scheduleCloud(ms){
  if(!TOY.on||!TOY.ready) return;
  clearTimeout(_cloudTimer);
  _cloudTimer=setTimeout(()=>{ toyWrite(); },ms===undefined?8000:ms);
}
function flushCloud(){ if(TOY.on&&TOY.ready){ clearTimeout(_cloudTimer); toyWrite(); } }
function toyShareNote(){
  return TOY.mode==='cloud'?'平台成绩 + 本机审计摘要（客户端休闲成绩展示）'
    :TOY.mode==='degraded'?'降级中，已存本机 · 数据未上传':'本机防作弊，数据不上传';
}
function toyCardNote(){
  return TOY.mode==='cloud'?'平台成绩 + 本机审计摘要 · 客户端休闲成绩展示'
    :TOY.mode==='degraded'?'降级中（已存本机）· 本机防作弊校验码'
    :'本机防作弊校验码 · 打卡冷却 '+cooldownMin()+' 分钟（独立于提醒间隔）';
}
function renderToyChip(){
  const b=$('#toyChip'); if(!b) return;
  b.className='toy-chip'+(TOY.mode==='cloud'?' cloud':TOY.mode==='degraded'?' degraded':'');
  b.textContent=TOY.mode==='cloud'?'☁ 云存档'+(TOY.lastSync?' · 已同步':'')
    :TOY.mode==='degraded'?'⚠ 降级中（已存本机）':'💾 本地档案';
  b.title='查看存档状态 / 来源：'+TOY.mode;
}
function openToyPanel(){
  const c=toyCloud(), r=TOY.remote;
  const st=TOY.mode==='cloud'?'☁ 云存档'+(TOY.lastSync?' · 上次同步 '+fmtTime(TOY.lastSync):' · 待同步')
    :TOY.mode==='degraded'?'⚠ 降级中 · 已存本机':'💾 本地档案（纯离线）';
  openModal(`<div class="mtitle">💾 存档状态</div>
    <div class="msub">同一个 HTML · 本地双击零联网 · Toy 容器才挂平台能力</div>
    <div class="toy-kv"><b>当前形态</b><span>${esc(st)}</span>
      <b>平台 SDK</b><span>${TOY.on?esc(TOY.kind)+(c?' · '+esc(c.kind):''):'未检测到（正常，本地版不需要）'}</span>
      <b>云档校验和</b><span>${r?esc(String(r.meta.hash).slice(0,16)):'—'}</span>
      <b>云档版本</b><span>${r?esc(fmtTime(r.snap.savedAt||0)):'—'}</span>
      <b>最后状态</b><span>${esc(TOY.lastErr||'正常')}</span>
      <b>平台榜</b><span>${TOY.consent?'已参加':'未参加'}</span></div>
    <div class="toy-note"><b>✅ 上云（最小可重建摘要）</b><ul class="toy-list">
      <li>schema 版本、每日水量 / 有效打卡 / 拦截 / 奶茶 / 审计哈希头</li>
      <li>积分与结算成绩、达标时刻、Rank / CG 解锁 id</li>
      <li>形象选择、心情枚举、设置项、水合指数、校验和</li></ul>
      <b>❌ 永不上云</b><ul class="toy-list">
      <li>奶茶抓拍照片（base64）、完整饮水流水</li>
      <li>在线大模型 API Key / endpoint</li>
      <li>精确 GPS 经纬度、通知 / 摄像头授权状态、完整语录上下文</li></ul></div>
    <div class="toy-note warn">写入「结果未确认」不等于失败：超时 / 取消都不能证明云端没提交，所以读档一律重读，绝不用空档覆盖本机。平台接口未见版本比较写入，请<b>单设备编辑</b>；云档丢了能重建进度，但重建不了照片。</div>
    <div class="btnrow"><button class="btn primary" id="tpSync">☁ 立即同步</button>
      <button class="btn ghost" id="tpRank">${TOY.consent?'退出平台榜':'参加平台榜'}</button>
      <button class="btn ghost" id="tpExport">导出本机镜像</button></div>
    <div class="btnrow"><button class="btn ghost" id="tpClose">关闭</button></div>`);
  $('#tpSync').onclick=async()=>{ const ok=await toyWrite(); try{toast(ok?'已同步云存档':'同步未完成，本机数据完好');}catch(e){} try{closeModal();}catch(e){} };
  $('#tpRank').onclick=()=>{ TOY.consent=!TOY.consent; S.toyRankConsent=TOY.consent; _saveBase();
    try{closeModal();}catch(e){} try{toast(TOY.consent?'已参加平台榜（结算时提交）':'已退出平台榜');}catch(e){} };
  $('#tpExport').onclick=()=>{
    try{
      const blob=new Blob([JSON.stringify(S,null,2)],{type:'application/json'});
      const a=document.createElement('a'); a.href=URL.createObjectURL(blob);
      a.download='大水计算器_本机镜像_'+dkey()+'.json'; a.click();
      setTimeout(()=>URL.revokeObjectURL(a.href),1500);
      toast('本机镜像已导出（含照片，请自行保管）');
    }catch(e){}
  };
  $('#tpClose').onclick=()=>{ try{closeModal();}catch(e){} };
}
/* ---- 平台分数榜：双轨，本机榜始终保留 ---- */
let _rankLoading=false;
async function toyRankLoad(){
  /* 只负责拉取，绝不在这里触发重绘；否则 then→render→load 会形成无限微任务链 */
  if(!TOY.on||!TOY.consent||_rankLoading) return;
  const k=toyRank(); if(!k) return;
  _rankLoading=true;
  try{
    const r=await withTimeout(Promise.resolve(k.list?k.list():k.getRankList()),5000);
    let arr=r;
    if(r&&!Array.isArray(r)) arr=r.list||r.data||r.rankList||[];
    TOY.rankList=Array.isArray(arr)?arr.slice(0,20).map(x=>({
      name:x.nickname||x.name||x.nick||'玩家',score:Number(x.score||x.value||0)||0,
      me:!!x.me })):[];
    TOY.rankLoaded=true;
  }catch(e){ TOY.lastErr='平台榜读取未确认'; renderToyChip(); }
  finally{ _rankLoading=false; }
}
function toyBoardRefresh(root){
  toyRankLoad().then(()=>{
    if(root.isConnected&&$('#modalBox')===root&&boardTab==='toy') renderToyBoard(root);
  });
}
function renderToyBoard(root){
  /* 平台榜不是本机档案榜：隐藏「新增本机选手」控件，副标题按形态切换 */
  const nw=root.querySelector('#scWrap .sc-new'); if(nw) nw.style.display='none';
  const sub=root.querySelector('.msub');
  if(sub) sub.textContent='☁ 平台分数榜 · 客户端休闲成绩展示 · 本机档案榜仍完整保留';
  root.querySelectorAll('.sc-banner').forEach(x=>x.remove());
  root.querySelector('#scRule').innerHTML=`<b>☁ 平台分数榜</b>：只提交「总分 / 达标时刻 / 规则版本」三个数，不传饮水明细、天气、定位与心情原文。客户端休闲成绩展示，<b>非官方认证、无服务器反作弊</b>；本机档案榜仍完整保留。`;
  root.querySelector('#scTip').textContent='平台榜需玩家点击授权后才参加；成绩只在结算时写入';
  root.querySelectorAll('[data-bt]').forEach(b=>b.classList.toggle('on',b.dataset.bt==='toy'));
  const list=root.querySelector('#scList');
  if(!TOY.consent){
    list.innerHTML=`<div class="toy-empty">还没参加平台榜。<br>点下面的按钮授权后，结算成绩才会提交。</div>
      <div style="text-align:center"><button class="btn primary" id="tbJoin" style="font-size:11px">☁ 参加平台榜</button></div>`;
    const j=root.querySelector('#tbJoin');
    if(j) j.onclick=()=>{ TOY.consent=true; S.toyRankConsent=true; _saveBase();
      renderToyBoard(root); toyBoardRefresh(root); };   // 先渲染，再拉一次
    return;
  }
  list.innerHTML=TOY.rankList.length
    ? TOY.rankList.map((r,i)=>`<div class="toy-row ${r.me?'me':''}"><span class="n">${i+1}</span>
        <span class="nm">${esc(r.name)}${r.me?' <small>本机</small>':''}</span><span class="pt">${r.score}</span></div>`).join('')
    : `<div class="toy-empty">暂无平台成绩。<br>完成一次今日结算后就会出现在榜单里。</div>`;
}
async function toySubmitScore(rec){
  if(!TOY.on||!TOY.ready||!TOY.consent) return;
  const k=toyRank(); if(!k) return;
  try{
    const payload={score:rec.score,extra:JSON.stringify({at:rec.achievedAt||0,rule:2})};
    await withTimeout(Promise.resolve(k.submit?k.submit(payload):k.submitScore(payload)),5000);
  }catch(e){ /* 静默：不打断结算 */ }
}

/* ---- 包装：业务写入排队、结算立即同步、榜单加第三 tab ---- */
const _saveBase=save;
save=function(){ _saveBase(); scheduleCloud(8000); };
const _submitDayBase=submitDay;
submitDay=function(dk,q,m){
  const r=_submitDayBase(dk,q,m);
  if(r){ scheduleCloud(0); if(TOY.consent) toySubmitScore(r); }
  return r;
};
const _leaderboardBase=leaderboardHTML;
leaderboardHTML=function(){
  let h=_leaderboardBase();          /* 原函数返回的是已插值的 HTML */
  if(TOY.on){
    h=h.replace(/(<button data-bt="all"[^>]*>🏅 历史总榜<\/button>)(<\/div>)/,
      `$1<button data-bt="toy" class="">☁ 平台榜</button>$2`);
  }
  return h;
};
/* 注意：script0 里可能有 `$('#btnBoard').onclick=openBoard` 这类「值拷贝」绑定，
   单纯重新赋值 openBoard 对已绑定的处理器无效。改为包装 bindBoard（每次开榜都会动态调用），
   并顺手把按钮引用重新指向新函数。 */
const _bindBoardBase=bindBoard;
bindBoard=function(root){
  _bindBoardBase(root);
  if(!TOY.on||!root) return;
  root.addEventListener('click',e=>{
    const bt=e.target.closest&&e.target.closest('[data-bt]');
    if(bt&&bt.dataset.bt==='toy'){
      e.stopPropagation(); e.preventDefault();   // capture 阶段截断，避免原 onclick 再渲染本机榜
      boardTab='toy'; renderToyBoard(root); toyBoardRefresh(root);
    }else if(bt){
      const nw=root.querySelector('#scWrap .sc-new'); if(nw) nw.style.display='';
      const sub=root.querySelector('.msub');
      if(sub) sub.textContent='本机多档案 · 打卡冷却 '+cooldownMin()+' 分钟（独立于提醒间隔）· 数据不上传';
    }
  },true);
  if(boardTab==='toy') renderToyBoard(root);
};
const _openBoardBase=openBoard;
openBoard=function(){ _openBoardBase(); };
try{ $('#btnBoard').onclick=()=>openBoard(); }catch(e){}

/* ---- 启动 ---- */
try{ TOY.consent=!!S.toyRankConsent; }catch(e){}
renderToyChip();
$('#toyChip').onclick=openToyPanel;
window.addEventListener('pagehide',flushCloud);
document.addEventListener('visibilitychange',()=>{ if(document.hidden) flushCloud(); });
toyInit();
'''
must('</body>', '<script>\n' + TOY_JS + '\n</script>\n</body>')

open(P, 'w', encoding='utf-8').write(s)
after = os.path.getsize(P)
print('适配层已写入', P)
print('  体积:', round(before/1024,1),'→',round(after/1024,1),'KiB  | 增量', round((after-before)/1024,1),'KiB')
print('  script 段:', s.count('<script>'))
print('  零 CDN:', not any(x in s for x in ['cdn.jsdelivr','unpkg.com','cdnjs']))
print('  内嵌位图/音频:', s.count('data:image/webp;base64,'), '/', s.count('data:audio/ogg;base64,'))
