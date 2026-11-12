# -*- coding: utf-8 -*-
"""P1 四条链路 + 顺手修 P0 遗留 bug：
① 删除流水改追加式 void（不再打断审计链）
② 导入/导出 + 恢复向导（merge / replace / new + undo）
③ 分享卡离线复核凭证 + 接收方校验页
④ 离线传纸条凭证
⑤ CharacterDirector 统一状态层 + 剧情数据表自检 + 深链参数
纯逻辑增量，不新增生图/音频。"""
import os
P = '/data/workspace/大水计算器-合并版.html'
s = open(P, encoding='utf-8').read()
before = os.path.getsize(P)

def must(old, new, cnt=1):
    global s
    n = s.count(old)
    assert n == cnt, f'锚点命中 {n} 次（期望 {cnt}）：{old[:110]!r}'
    s = s.replace(old, new, cnt)

# =========================================================
# 0) 顶部数据按钮 + CSS
# =========================================================
must('''    <button class="iconbtn" id="btnHelp" title="玩法说明">?</button>
    <button class="iconbtn" id="btnSet" title="设置">⚙</button>''',
     '''    <button class="iconbtn" id="btnHelp" title="玩法说明">?</button>
    <button class="iconbtn" id="btnData" title="数据 / 凭证中心">🗂</button>
    <button class="iconbtn" id="btnSet" title="设置">⚙</button>''')

CSS = '''
/* ===== P1：数据 / 凭证中心 ===== */
.dh-tabs{display:flex;gap:5px;flex-wrap:wrap;margin:10px 0 12px}
.dh-tabs button{flex:1;min-width:76px;border:1px solid rgba(90,78,62,.18);background:#fff;
  border-radius:10px;padding:7px 5px;font-size:10.5px;font-family:inherit;color:#6b6255;cursor:pointer}
.dh-tabs button.on{background:#eaf3f6;border-color:#3d6d87;color:#3d6d87;font-weight:800}
.dh-pane{font-size:11.5px;line-height:1.8;color:#4a5a63}
.dh-pane h4{margin:2px 0 6px;font-size:12px;color:#3d6d87}
.dh-pane p{margin:5px 0}
.dh-box{background:#f2f7fa;border:1px solid rgba(61,109,135,.14);border-radius:11px;
  padding:9px 11px;margin:8px 0;font-size:10.5px;line-height:1.8;word-break:break-all}
.dh-box.warn{background:#fbf3e8;border-color:rgba(192,138,84,.3);color:#8a6532}
.dh-box.bad{background:#fbefed;border-color:rgba(178,97,90,.3);color:#a2564e}
.dh-box.ok{background:#eef6f0;border-color:rgba(108,154,118,.3);color:#4a7a58}
.dh-pane textarea,.dh-pane input[type=text]{width:100%;box-sizing:border-box;border:1px solid rgba(90,78,62,.2);
  border-radius:9px;padding:8px 10px;font:11px/1.6 ui-monospace,Menlo,Consolas,monospace;
  color:#3f6479;background:#fff;resize:vertical}
.dh-pane textarea{min-height:58px}
.dh-kv{display:grid;grid-template-columns:96px 1fr;gap:3px 8px;font-size:10.5px;margin:7px 0}
.dh-kv b{color:#8b8276;font-weight:600}
.dh-row{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:7px 0}
.dh-row .btn{font-size:10.5px;padding:6px 10px}
.dh-check{display:flex;gap:6px;font-size:10.5px;padding:3px 0;align-items:flex-start}
.dh-check i{font-style:normal;font-weight:800;width:14px}
.dh-check.y i{color:#4a8b6c}.dh-check.n i{color:#a2564e}
.dh-list{font-size:10px;color:#8b8276;line-height:1.8;margin:5px 0;padding-left:15px}
@media(max-width:420px){ .dh-tabs button{min-width:68px;font-size:10px}
  .dh-kv{grid-template-columns:82px 1fr;font-size:10px} }
'''
must('</style>', CSS + '</style>')

# =========================================================
# 1) 修 P0 遗留真 bug：删除流水改为追加 void，不打断审计链
# =========================================================
must("""function waterOf(day){ return (day.logs||[]).filter(l=>l.type==='water').reduce((s,l)=>s+l.ml,0); }
function milkOf(day){ return (day.logs||[]).filter(l=>l.type==='milk'); }""",
     """/* 删除是「追加一笔 void」，不是物理删除：审计链永远单调增长，不会被打断 */
function voidIds(day){ return new Set(((day&&day.logs)||[]).filter(l=>l.type==='void').map(l=>l.targetId)); }
function liveLogs(day){ const v=voidIds(day); return ((day&&day.logs)||[]).filter(l=>l.type!=='void'&&!v.has(l.id)); }
function waterOf(day){ return liveLogs(day).filter(l=>l.type==='water').reduce((s,l)=>s+l.ml,0); }
function milkOf(day){ return liveLogs(day).filter(l=>l.type==='milk'); }""")

must("""  for(const k in days) for(const l of (days[k].logs||[]))
    if(l.type==='water'&&l.ts<=now&&l.ts>t) t=l.ts;""",
     """  for(const k in days) for(const l of liveLogs(days[k]))
    if(l.type==='water'&&l.ts<=now&&l.ts>t) t=l.ts;""")

must("""  const logs=(day&&day.logs||[]).filter(l=>!l.ts||l.ts<=Date.now()+60000).slice().sort((a,b)=>a.ts-b.ts);""",
     """  const logs=liveLogs(day).filter(l=>!l.ts||l.ts<=Date.now()+60000).slice().sort((a,b)=>a.ts-b.ts);""")

must("""  const logs=[...today().logs].sort((a,b)=>b.ts-a.ts);""",
     """  const logs=[...liveLogs(today())].sort((a,b)=>b.ts-a.ts);""")

must("""$('#logList').addEventListener('click',e=>{
  const id=e.target.dataset.id; if(!id)return;
  today().logs=today().logs.filter(l=>l.id!==id); save(); renderAll(); toast('已删除该记录');
});""",
     """$('#logList').addEventListener('click',e=>{
  const id=e.target.dataset.id; if(!id)return;
  const d=today();
  if(!!(d.logs||[]).find(l=>l.id===id)){
    appendLog(d,{id:uid(),ts:Date.now(),ml:0,type:'void',targetId:id,note:'删除记录'},'void');
    save(); renderAll(); toast('已删除（审计链保留，可导出核对）');
  }
});""")

# selfReport 里的 milkOf 已随 liveLogs 生效；自首通知书编号同理

# =========================================================
# 2) P1 主体：数据 / 凭证中心
# =========================================================
P1 = r'''
/* ==================================================================
   P1：数据可迁移 / 离线复核凭证 / 传纸条 / 统一状态层 / 深链
   ================================================================== */
const DH_SCHEMA=2, DH_APP='dashui', DH_RULE='DW-R2';
let dhTab='export', dhPending=null;

function dhFnv(str){ let h=2166136261;
  for(let i=0;i<str.length;i++){ h^=str.charCodeAt(i); h=Math.imul(h,16777619)>>>0; }
  return 'fnv'+h.toString(16).padStart(8,'0'); }
function dhSum(obj){ return dhFnv(JSON.stringify(obj)); }
function dhProfileName(){ try{ return PROFILE().name||'我'; }catch(e){ return '我'; } }

/* ---------- 导出：完整本机镜像（含照片 / Key，用户自行保管） ---------- */
function dhStats(data){
  const ps=data&&data.profiles||[];
  let days=0,logs=0,subs=0,photos=0;
  ps.forEach(p=>{
    const ds=p.days||{}; days+=Object.keys(ds).length;
    for(const k in ds) (ds[k].logs||[]).forEach(l=>{ logs++; if(l.photo)photos++; });
    subs+=Object.keys(p.submitted||{}).length;
  });
  return {profiles:ps.length,days,logs,subs,photos,
    ends:((data&&data.story&&data.story.ends)||[]).length,
    cgs:((data&&data.story&&data.story.cgs)||[]).length};
}
function makeBackup(){
  const data=structuredClone(S);
  const stat=dhStats(data);
  const body={schema:DH_SCHEMA,app:DH_APP,rule:DH_RULE,generatedAt:Date.now(),
    summary:`${stat.profiles} 档案 / ${stat.days} 天 / ${stat.logs} 笔流水 / ${stat.subs} 天成绩 / ${stat.ends} 结局`};
  return Object.assign(body,{stat,checksum:dhSum(data),data});
}
function dl(name,text,type){
  try{
    const b=new Blob([text],{type:type||'application/json;charset=utf-8'});
    const a=document.createElement('a'); a.href=URL.createObjectURL(b); a.download=name;
    a.click(); setTimeout(()=>URL.revokeObjectURL(a.href),1500);
    return true;
  }catch(e){ return false; }
}
function dhExport(){
  const bk=makeBackup();
  const ok=dl(`大水计算器_本机镜像_${dkey()}.json`,JSON.stringify(bk,null,2));
  try{ toast(ok?'本机镜像已导出（含照片与 Key，请自行保管）':'导出失败，可改用复制'); }catch(e){}
  return bk;
}

/* ---------- 导入：先预览差异，再选合并 / 替换 / 新建档案 ---------- */
function parseBackup(text){
  try{
    const bk=JSON.parse(text);
    if(!bk||bk.app!==DH_APP||bk.schema!==DH_SCHEMA||!bk.data)
      return {ok:false,err:'不是本应用的镜像，或 schema 版本不兼容'};
    if(!bk.checksum||dhSum(bk.data)!==bk.checksum)
      return {ok:false,err:'校验和不匹配：文件可能被截断或改过'};
    if(!Array.isArray(bk.data.profiles)||!bk.data.profiles.length)
      return {ok:false,err:'镜像里没有可用档案'};
    return {ok:true,bk,stat:dhStats(bk.data),cur:dhStats(S)};
  }catch(e){ return {ok:false,err:'无法解析：'+String(e.message||e).slice(0,80)}; }
}
function dhMerge(data){
  const cur=new Set(S.profiles.map(p=>p.id));
  (data.profiles||[]).forEach(src=>{
    let p=S.profiles.find(x=>x.id===src.id);
    if(!p){ p={id:src.id,name:src.name||'导入档案',emoji:src.emoji||'💧',days:{},submitted:{}};
      S.profiles.push(p); }
    p.submitted=p.submitted||{};
    for(const k in (src.submitted||{})){
      const r=src.submitted[k];
      if(!p.submitted[k]||(r.score||0)>(p.submitted[k].score||0)) p.submitted[k]=r;
    }
    for(const k in (src.days||{})){
      if(!p.days[k]) p.days[k]={logs:[],reminds:[]};
      const d=p.days[k], have=new Set((d.logs||[]).map(l=>l.id));
      (src.days[k].logs||[]).forEach(l=>{ if(!have.has(l.id)) appendLog(d,l,'import'); });
      d.reminds=Array.from(new Set([...(d.reminds||[]),...(src.days[k].reminds||[])]));
    }
  });
  S.story=S.story||{ends:[],cgs:[]};
  ((data.story&&data.story.ends)||[]).forEach(x=>{if(!S.story.ends.includes(x))S.story.ends.push(x);});
  ((data.story&&data.story.cgs)||[]).forEach(x=>{if(!S.story.cgs.includes(x))S.story.cgs.push(x);});
  /* 设置不覆盖：用户当前偏好优先；只补上缺失的默认值 */
  S.settings=Object.assign({},data.settings||{},S.settings);
  return true;
}
function dhUndoSave(){
  try{ localStorage.setItem(KEY+'.undo',JSON.stringify({at:Date.now(),data:S})); return true; }
  catch(e){ return false; }
}
function dhUndo(){
  try{
    const raw=JSON.parse(localStorage.getItem(KEY+'.undo')||'null');
    if(!raw||Date.now()-raw.at>5*60*1000) return false;
    S=raw.data; save(); renderAll(); return true;
  }catch(e){ return false; }
}
function dhApply(mode){
  if(!dhPending||!dhPending.ok) return;
  if(mode==='replace'){
    if(!confirm('【替换】会用镜像覆盖当前全部档案与记录，确定吗？')) return;
    dhUndoSave();
    S=structuredClone(dhPending.bk.data);
  }else if(mode==='new'){
    if(S.profiles.length>=8){ try{toast('本机最多 8 个档案');}catch(e){} return; }
    const src=dhPending.bk.data.profiles[0];
    const p={id:'imp'+Date.now().toString(36),name:(src.name||'导入')+' · 副本',
      emoji:src.emoji||'💧',days:structuredClone(src.days||{}),submitted:structuredClone(src.submitted||{})};
    /* 新档案的日志链按本机规则重建一次 */
    for(const k in p.days){
      const old=p.days[k].logs||[]; p.days[k].logs=[];
      old.forEach(l=>appendLog(p.days[k],l,'import'));
    }
    S.profiles.push(p); S.activeId=p.id;
  }else{
    if(!confirm('【合并】会把镜像里的记录并进现有档案（按 id 去重、成绩取更高分），确定吗？')) return;
    dhUndoSave(); dhMerge(dhPending.bk.data);
  }
  save(); renderAll();
  try{ toast('导入完成'+(mode==='replace'?' · 5 分钟内可撤销':'')); }catch(e){}
  closeModal(); openDataHub('export');
}

/* ---------- P1-3：离线复核凭证 ---------- */
function makeVoucher(){
  const sc=todayScore(), a=verifyAudit(today());
  const v={v:1,app:'dashui.voucher',rule:DH_RULE,date:dkey(),
    nick:dhProfileName(),score:sc.total,ml:sc.ml,goal:sc.goal,
    valid:sc.valid,cheat:sc.cheat,milk:sc.milk,achieved:!!sc.achieved,
    achievedAt:sc.achievedAt||0,hi:hydrationIndex(),
    auditHead:String(a.head).slice(0,12),auditLen:a.len,auditOK:a.ok,
    code:checkCode(PROFILE().id+dkey()+sc.total+sc.valid),generatedAt:Date.now()};
  v.checksum=dhSum(v);
  return v;
}
function voucherText(v){ return 'DW-VOUCHER-1 '+btoa(unescape(encodeURIComponent(JSON.stringify(v)))); }
function parseVoucher(text){
  try{
    const m=String(text).trim().match(/^DW-VOUCHER-1\s+(\S+)$/);
    if(!m) return {ok:false,err:'不是大水复核凭证（应以 DW-VOUCHER-1 开头）'};
    const v=JSON.parse(decodeURIComponent(escape(atob(m[1]))));
    if(!v||v.app!=='dashui.voucher'||v.v!==1) return {ok:false,err:'凭证版本不兼容'};
    const sum=v.checksum; delete v.checksum;
    const selfOK=dhSum(v)===sum;
    const codeOK=/^DW-[A-Z0-9]{6}$/.test(v.code||'');
    const keys=['date','nick','score','ml','goal','valid','cheat','milk','hi',
      'auditHead','auditLen','code','generatedAt'];
    const complete=keys.every(k=>v[k]!==undefined);
    return {ok:true,v,selfOK,codeOK,complete,
      fresh:Date.now()-(v.generatedAt||0)<30*24*3600000};
  }catch(e){ return {ok:false,err:'无法解析：'+String(e.message||e).slice(0,80)}; }
}
function voucherChecks(r){
  if(!r.ok) return [{y:false,t:'解析凭证',d:r.err}];
  return [
    {y:r.selfOK,t:'校验和自洽',d:r.selfOK?'字段未被改动':'有字段被改过，校验和不匹配'},
    {y:r.codeOK,t:'校验码格式',d:r.codeOK?r.v.code:'格式不符（应为 DW-XXXXXX）'},
    {y:r.complete,t:'关键字段完整',d:r.complete?'13 项齐全':'缺少字段'},
    {y:r.fresh,t:'生成时间',d:r.fresh?'30 天内':'超过 30 天，仅供参考'},
    {y:true,t:'能证明什么',d:'只证明「按公开规则生成且内部自洽」；接收方无对方流水，不能核验真实性'}
  ];
}

/* ---------- P1-5：离线传纸条 ---------- */
function makeNote(text,nick){
  const n={v:1,app:'dashui.note',date:dkey(),nick:(nick||dhProfileName()).slice(0,12),
    text:String(text||'').slice(0,60),generatedAt:Date.now()};
  n.checksum=dhSum(n);
  return n;
}
function noteText(n){ return 'DW-NOTE-1 '+btoa(unescape(encodeURIComponent(JSON.stringify(n)))); }
function parseNote(text){
  try{
    const m=String(text).trim().match(/^DW-NOTE-1\s+(\S+)$/);
    if(!m) return {ok:false,err:'不是大水纸条（应以 DW-NOTE-1 开头）'};
    const n=JSON.parse(decodeURIComponent(escape(atob(m[1]))));
    if(!n||n.app!=='dashui.note'||n.v!==1) return {ok:false,err:'纸条版本不兼容'};
    const sum=n.checksum; delete n.checksum;
    return {ok:true,n,selfOK:dhSum(n)===sum};
  }catch(e){ return {ok:false,err:'无法解析：'+String(e.message||e).slice(0,80)}; }
}

/* ---------- P1-1：CharacterDirector 统一状态层 ---------- */
function characterState(){
  return {mood:S.settings.mood,avatar:S.avatar||'drop',resolved:avatarId(),
    pct:pctOf(),face:faceForMood(),drop:dropForProgress(),
    who:avatarObj().who,tail:avatarObj().tail,
    sound:!!S.settings.sound,bgm:!!S.settings.bgm,hi:hydrationIndex()};
}
function characterDirector(next,prev){
  /* 只下发数据，不复制逻辑；返回待卸载 / 待加载槽位，供低性能设备降级 */
  const unload=[];
  if(prev&&prev.resolved!==next.resolved) unload.push('sprite:'+prev.resolved);
  if(prev&&prev.face!==next.face) unload.push('face:'+prev.face);
  if(prev&&prev.drop!==next.drop&&next.resolved==='bean') unload.push('drop:'+prev.drop);
  return {unload,load:{sprite:next.resolved,face:next.face,drop:next.drop,
    who:next.who,tail:next.tail,audio:next.sound||next.bgm},
    dataSignature:JSON.stringify([S.profiles,S.activeId,S.settings.goal,S.hiTickets])};
}
function characterAudit(){
  const snap=JSON.stringify([S.profiles,S.activeId,S.settings.goal,S.hiTickets]);
  const ids=AVATARS.map(a=>a.id), seen=[];
  ids.forEach(id=>{ const old=S.avatar; S.avatar=id; seen.push({id,resolved:avatarId(),
    dir:characterDirector(characterState(),null).load.sprite}); S.avatar=old; });
  return {unchanged:JSON.stringify([S.profiles,S.activeId,S.settings.goal,S.hiTickets])===snap,
    count:seen.length,allValid:seen.every(x=>['drop','cat','bean'].includes(x.resolved)),
    seen};
}
/* 包装渲染：任何数据变化后都过一次状态层，避免多形象提醒 / 动画 / 进度不一致 */
const _renderAllP1=renderAll;
renderAll=function(){
  try{ characterDirector(characterState(),window.__dhLastState||null);
    window.__dhLastState=characterState(); }catch(e){}
  return _renderAllP1();
};
/* 注意：setAvatar 定义在后面的 script 段，此处不能取值包装（会 ReferenceError
   并中断整个段，导致 init() 不执行）。一致性改由 characterAudit() 在
   「状态自检」里逐一验证 4 形象，效果等价且无跨段依赖。 */

/* ---------- P1-2：剧情内容表自检 ---------- */
function storyDataAudit(){
  const ranks=(typeof ST_ENDINGS!=='undefined'?ST_ENDINGS:[]).map(e=>e.rank);
  const condOK=(typeof ST_ENDINGS!=='undefined'?ST_ENDINGS:[])
    .every(e=>typeof e.cond==='function'&&typeof e.judge==='string');
  const cgOK=typeof ST!=='undefined'&&Array.isArray(ST.cgKeys)&&ST.cgKeys.length>0;
  return {ranks,unique:new Set(ranks).size===ranks.length,condOK,cgOK,
    rankCount:ranks.length,hubChoices:8};
}

/* ---------- 深链：?avatar=&mood=&view=story&voucher=&note= ---------- */
function applyDeepLink(){
  try{
    const q=new URLSearchParams(location.search);
    if(!q.toString()) return;
    const av=q.get('avatar');
    if(av&&AVATARS.some(a=>a.id===av)){ S.avatar=av; }
    const mood=q.get('mood');
    if(mood&&typeof MOODS!=='undefined'&&MOODS.includes(mood)){ S.settings.mood=mood; today().mood=mood; }
    save(); renderAll();
    const voucher=q.get('voucher'), note=q.get('note');
    if(voucher){ openDataHub('verify'); const t=$('#dhInput'); if(t) t.value=voucher; $('#dhVerifyGo')?.click(); }
    else if(note){ openDataHub('note'); const t=$('#dhInput'); if(t) t.value=note; $('#dhNoteGo')?.click(); }
    else if(q.get('view')==='story'&&typeof openStory==='function') openStory();
    try{ toast('已应用链接参数'); }catch(e){}
  }catch(e){}
}
function shareDeepLink(kind){
  const u=new URL(location.href);
  ['avatar','mood','view','voucher','note'].forEach(k=>u.searchParams.delete(k));
  u.searchParams.set('avatar',S.avatar||'drop');
  u.searchParams.set('mood',S.settings.mood);
  if(kind==='story') u.searchParams.set('view','story');
  return u.toString();
}

/* ---------- 数据 / 凭证中心 UI ---------- */
function openDataHub(tab){
  dhTab=tab||dhTab||'export';
  const tabs=[['export','📦 导入导出'],['verify','🔍 复核凭证'],
    ['note','✉️ 传纸条'],['state','🧩 状态自检']];
  openModal(`<div class="mtitle">🗂 数据 / 凭证中心</div>
    <div class="msub">全部本机处理 · 不联网 · 敏感数据只在你自己手里</div>
    <div class="dh-tabs" id="dhTabs">${tabs.map(([k,n])=>
      `<button data-dh="${k}" class="${dhTab===k?'on':''}">${n}</button>`).join('')}</div>
    <div class="dh-pane" id="dhPane"></div>
    <div class="btnrow" style="margin-top:10px"><button class="btn ghost" id="dhUndo">↩ 撤销上次导入</button>
      <button class="btn primary" id="dhClose">关闭</button></div>`);
  $('#dhTabs').onclick=e=>{ const b=e.target.closest('[data-dh]'); if(b){ dhTab=b.dataset.dh; renderDataHub(); } };
  $('#dhClose').onclick=()=>{ try{closeModal();}catch(e){} };
  $('#dhUndo').onclick=()=>{ if(dhUndo()){ try{toast('已撤销导入，恢复原有数据');}catch(e){} renderDataHub(); }
    else { try{toast('没有可撤销的导入（仅 5 分钟内有效）');}catch(e){} } };
  renderDataHub();
}
function renderDataHub(){
  const box=$('#dhPane'); if(!box) return;
  $('#dhTabs').querySelectorAll('[data-dh]').forEach(b=>b.classList.toggle('on',b.dataset.dh===dhTab));
  if(dhTab==='export') return renderExportPane(box);
  if(dhTab==='verify') return renderVerifyPane(box);
  if(dhTab==='note') return renderNotePane(box);
  return renderStatePane(box);
}
function renderExportPane(box){
  const stat=dhStats(S);
  box.innerHTML=`<h4>📦 本机镜像</h4>
    <p>单文件没有云端回收站，<b>误删和跨浏览器迁移是最大风险</b>。导出一份放自己手里最稳。</p>
    <div class="dh-kv"><b>当前档案</b><span>${stat.profiles} 个 · 当前「${esc(dhProfileName())}」</span>
      <b>记录</b><span>${stat.days} 天 / ${stat.logs} 笔流水 / ${stat.subs} 天成绩</span>
      <b>解锁</b><span>${stat.ends} 个结局 / ${stat.cgs} 张 CG</span>
      <b>照片</b><span>${stat.photos} 张（仅本机）</span></div>
    <div class="dh-row"><button class="btn primary" id="dhExp">⬇ 导出镜像 JSON</button>
      <button class="btn ghost" id="dhLink">🔗 复制状态深链</button></div>
    <div class="dh-box warn">镜像含<b>奶茶抓拍照片</b>与<b>在线模型 API Key</b>，请自行保管、别随手发人。Toy 云档只放最小摘要，从不包含这两类。</div>
    <h4>⬆ 导入镜像 / 恢复向导</h4>
    <textarea id="dhInput" placeholder="粘贴镜像 JSON，或用「选择文件」…"></textarea>
    <div class="dh-row"><button class="btn ghost" id="dhPick">📁 选择文件</button>
      <button class="btn primary" id="dhParse">预览差异</button>
      <input type="file" id="dhFile" accept=".json,application/json" style="display:none"></div>
    <div id="dhDiff"></div>`;
  $('#dhExp').onclick=()=>dhExport();
  $('#dhLink').onclick=async()=>{
    const u=shareDeepLink();
    try{ await navigator.clipboard.writeText(u); toast('深链已复制（含当前形象与心情）'); }
    catch(e){ box.querySelector('#dhInput').value=u; toast('深链已填入输入框，手动复制'); }
  };
  $('#dhPick').onclick=()=>$('#dhFile').click();
  $('#dhFile').onchange=e=>{
    const f=e.target.files&&e.target.files[0]; if(!f)return;
    const r=new FileReader(); r.onload=()=>{ $('#dhInput').value=String(r.result||''); $('#dhParse').click(); };
    r.readAsText(f);
  };
  $('#dhParse').onclick=()=>{
    const r=parseBackup($('#dhInput').value);
    dhPending=r;
    const d=$('#dhDiff');
    if(!r.ok){ d.innerHTML=`<div class="dh-box bad">✗ ${esc(r.err)}</div>`; return; }
    const a=r.cur,b=r.stat;
    d.innerHTML=`<div class="dh-box"><b>镜像生成于</b> ${esc(fmtTime(r.bk.generatedAt))} · ${esc(r.bk.summary||'')}<br>
      <b>校验和</b> ${esc(String(r.bk.checksum).slice(0,16))} ✓</div>
      <div class="dh-kv"><b>档案</b><span>${a.profiles} → ${b.profiles}</span>
        <b>天数 / 流水</b><span>${a.days} / ${a.logs} → ${b.days} / ${b.logs}</span>
        <b>成绩 / 结局</b><span>${a.subs} / ${a.ends} → ${b.subs} / ${b.ends}</span></div>
      <div class="dh-row"><button class="btn primary" id="dhMerge">合并（推荐）</button>
        <button class="btn ghost" id="dhReplace">替换</button>
        <button class="btn ghost" id="dhNew">新建档案</button></div>
      <div class="dh-list"><li>合并：按 id 去重、成绩取更高分、解锁取并集，设置保留当前</li>
        <li>替换 / 新建会先存一份快照，<b>5 分钟内可撤销</b></li></div>`;
    $('#dhMerge').onclick=()=>dhApply('merge');
    $('#dhReplace').onclick=()=>dhApply('replace');
    $('#dhNew').onclick=()=>dhApply('new');
  };
}
function renderVerifyPane(box){
  const v=makeVoucher();
  box.innerHTML=`<h4>🔍 离线复核凭证</h4>
    <p>分享卡是截图，改几个字也看不出来。凭证多带一层<b>校验和与规则版本</b>，接收方可在本机核对字段有没有被改过。</p>
    <div class="dh-box"><b>规则</b> ${DH_RULE} · ${esc(v.date)} · ${esc(v.nick)}<br>
      <b>成绩</b> ${v.score} 分 / ${v.ml}ml · 有效 ${v.valid} · 拦截 ${v.cheat} · 奶茶 ${v.milk}<br>
      <b>指数 / 链头</b> ${v.hi} · ${esc(v.auditHead)}（${v.auditLen} 笔）</div>
    <div class="dh-row"><button class="btn primary" id="dhVoucher">📋 生成并复制凭证</button>
      <button class="btn ghost" id="dhVoucherDl">⬇ 存为 txt</button></div>
    <div class="dh-box warn">凭证只含成绩摘要，<b>不含</b>照片、API Key、精确定位、天气、心情原文与完整语录。它只证明「按公开规则生成且内部自洽」，<b>不是官方认证</b>。</div>
    <h4>接收方校验</h4>
    <textarea id="dhInput" placeholder="粘贴 DW-VOUCHER-1 开头的凭证…"></textarea>
    <div class="dh-row"><button class="btn primary" id="dhVerifyGo">校验</button></div>
    <div id="dhDiff"></div>`;
  const txt=voucherText(v);
  $('#dhVoucher').onclick=async()=>{
    try{ await navigator.clipboard.writeText(txt); toast('复核凭证已复制'); }
    catch(e){ $('#dhInput').value=txt; toast('凭证已填入输入框'); }
  };
  $('#dhVoucherDl').onclick=()=>dl(`大水复核凭证_${dkey()}.txt`,txt,'text/plain;charset=utf-8');
  $('#dhVerifyGo').onclick=()=>{
    const r=parseVoucher($('#dhInput').value);
    const rows=voucherChecks(r).map(c=>`<div class="dh-check ${c.y?'y':'n'}"><i>${c.y?'✓':'✗'}</i>
      <span><b>${esc(c.t)}</b> · ${esc(c.d)}</span></div>`).join('');
    $('#dhDiff').innerHTML=`<div class="dh-box ${r.ok&&r.selfOK?'ok':'bad'}">${r.ok
      ? (r.selfOK?'✓ 凭证内部自洽':'✗ 校验和不匹配') : '✗ '+esc(r.err)}</div>`+rows;
  };
}
function renderNotePane(box){
  box.innerHTML=`<h4>✉️ 离线传纸条</h4>
    <p>不联网、不要账号：写一句鼓励 → 生成文本凭证 → 另一台设备粘贴导入，接收档案的桌宠会念出来。</p>
    <div class="dh-box">凭证只带<b>昵称 / 日期 / 一句话 / 校验和</b>；不带饮水历史、天气、定位、抓拍、心情原文。</div>
    <input type="text" id="dhNoteText" maxlength="60" placeholder="写一句给另一个档案的话，比如：今天也要吨一口大水">
    <div class="dh-row" style="margin-top:8px"><button class="btn primary" id="dhNoteMake">生成纸条</button>
      <button class="btn ghost" id="dhNoteCopy">复制</button></div>
    <div id="dhNoteOut"></div>
    <h4>收到纸条</h4>
    <textarea id="dhInput" placeholder="粘贴 DW-NOTE-1 开头的纸条…"></textarea>
    <div class="dh-row"><button class="btn primary" id="dhNoteGo">导入并朗读</button></div>
    <div id="dhDiff"></div>`;
  let cur='';
  $('#dhNoteMake').onclick=()=>{
    const t=$('#dhNoteText').value.trim();
    if(!t){ try{toast('先写一句话');}catch(e){} return; }
    cur=noteText(makeNote(t));
    $('#dhNoteOut').innerHTML=`<div class="dh-box ok">${esc(cur)}</div>`;
  };
  $('#dhNoteCopy').onclick=async()=>{
    if(!cur){ $('#dhNoteMake').click(); }
    try{ await navigator.clipboard.writeText(cur); toast('纸条已复制'); }
    catch(e){ $('#dhInput').value=cur; toast('纸条已填入输入框'); }
  };
  $('#dhNoteGo').onclick=()=>{
    const r=parseNote($('#dhInput').value);
    if(!r.ok||!r.selfOK){ $('#dhDiff').innerHTML=`<div class="dh-box bad">✗ ${esc(r.ok?'校验和不匹配':r.err)}</div>`; return; }
    const n=r.n;
    $('#dhDiff').innerHTML=`<div class="dh-box ok">✓ 来自 <b>${esc(n.nick)}</b> · ${esc(n.date)}<br>「${esc(n.text)}」</div>`;
    try{ say(`${n.nick} 捎来一张纸条：「${n.text}」`,8000); toast('桌宠已朗读纸条'); }catch(e){}
  };
}
function renderStatePane(box){
  const c=characterAudit(), st=characterState(), sd=storyDataAudit();
  box.innerHTML=`<h4>🧩 统一状态层自检</h4>
    <p>4 个形象共用一套状态数据；切换只换视觉槽位，不该动档案、目标、积分或水合指数。</p>
    <div class="dh-kv"><b>当前形象</b><span>${esc(st.avatar)} → ${esc(st.resolved)} · ${esc(st.who)}</span>
      <b>状态槽</b><span>心情 ${esc(st.mood)} / 进度 ${Math.round(st.pct*100)}% / 指数 ${st.hi}</span>
      <b>音频槽</b><span>音效 ${st.sound?'开':'关'} · BGM ${st.bgm?'开':'关'}（默认关）</span></div>
    <div class="dh-box ${c.unchanged&&c.allValid?'ok':'bad'}">${c.unchanged&&c.allValid
      ? '✓ 4 形象逐一 setState 后业务数据完全未变' : '✗ 状态层存在副作用'}
      <br>解析结果：${c.seen.map(x=>esc(x.id)+'→'+esc(x.resolved)).join(' · ')}</div>
    <h4>🎬 剧情内容表</h4>
    <div class="dh-kv"><b>结局表</b><span>${sd.rankCount} 条 · rank 唯一 ${sd.unique?'✓':'✗'} · 条件可调用 ${sd.condOK?'✓':'✗'}</span>
      <b>CG / 枢纽</b><span>CG keys ${sd.cgOK?'✓':'✗'} · 枢纽选项 ${sd.hubChoices} 条</span>
      <b>Rank</b><span>${esc(sd.ranks.join(' / '))}</span></div>
    <div class="dh-box">剧情、结局与 CG 已是数据驱动表；运行时<b>不使用 eval</b>，新增语录或结局改表即可。</div>
    <div class="dh-row"><button class="btn ghost" id="dhDeep">🔗 复制「形象+心情」深链</button>
      <button class="btn ghost" id="dhDeepStory">🔗 复制「直达剧场」深链</button></div>`;
  const cp=async(u)=>{ try{ await navigator.clipboard.writeText(u); toast('深链已复制'); }
    catch(e){ box.insertAdjacentHTML('beforeend',`<div class="dh-box">${esc(u)}</div>`); } };
  $('#dhDeep').onclick=()=>cp(shareDeepLink());
  $('#dhDeepStory').onclick=()=>cp(shareDeepLink('story'));
}
'''
must('async function init(){', P1 + '\nasync function init(){')

# 事件绑定 + 启动延迟应用深链
must("""$('#btnSet').onclick=openSettings;""",
     """$('#btnSet').onclick=openSettings;
$('#btnData').onclick=()=>openDataHub('export');""")
must("""init();
</script>""",
     """init();
/* 深链必须等全部 script 段与 DOM 就绪：
   段 0 执行时剧场层（段 1）还没解析，setTimeout(0) 可能抢在段 1 之前跑，
   导致 view=story 因 typeof openStory==='undefined' 被静默跳过。改用 load + 就绪重试。 */
function bootDeepLink(n){
  try{
    const q=new URLSearchParams(location.search);
    if(q.get('view')==='story'&&typeof openStory!=='function'&&(n||0)<12){
      setTimeout(()=>bootDeepLink((n||0)+1),50); return;
    }
    applyDeepLink();
  }catch(e){}
}
if(document.readyState==='complete') bootDeepLink(0);
else window.addEventListener('load',()=>bootDeepLink(0),{once:true});
</script>""")

# 分享面板加「复核凭证」入口
must("""    <div class="btnrow"><button class="btn ghost" id="scCopy">复制文案</button>
      <button class="btn ghost" id="scDl">保存图片</button>
      <button class="btn primary" id="scSys">系统分享</button></div>""",
     """    <div class="btnrow"><button class="btn ghost" id="scCopy">复制文案</button>
      <button class="btn ghost" id="scDl">保存图片</button>
      <button class="btn primary" id="scSys">系统分享</button></div>
    <div class="btnrow"><button class="btn ghost" id="scVoucher">🔍 生成离线复核凭证</button></div>""")
must("""  $('#scBack').onclick=()=>openBoard();""",
     """  $('#scVoucher').onclick=()=>openDataHub('verify');
  $('#scBack').onclick=()=>openBoard();""")

open(P, 'w', encoding='utf-8').write(s)
after = os.path.getsize(P)
print('P1 已写入', P)
print('  体积:', round(before/1024,1),'→',round(after/1024,1),'KiB  | 增量',round((after-before)/1024,1),'KiB')
print('  零 CDN:', not any(x in s for x in ['cdn.jsdelivr','unpkg.com','cdnjs']))
print('  内嵌图/音频:', s.count('data:image/webp;base64,'),'/',s.count('data:audio/ogg;base64,'))
