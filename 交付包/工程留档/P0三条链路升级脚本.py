# -*- coding: utf-8 -*-
"""P0 剩余三条链路：① 带哈希的审计流水 ② 时段进度差智能提醒 ③ 可信水合指数。
纯逻辑增量，不新增生图/音频，保持单文件零 CDN。"""
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
# 0) HUD 两行新指标
# =========================================================
must('''      <div id="cooldownLine" style="margin-top:7px"></div>
      <div class="btnrow" style="margin-top:9px">''',
     '''      <div id="cooldownLine" style="margin-top:7px"></div>
      <div id="remindLine" class="hi-line"></div>
      <div id="hiLine" class="hi-box"></div>
      <div class="btnrow" style="margin-top:9px">''')

CSS = '''
/* ===== P0：智能提醒 / 可信水合指数 / 审计链 ===== */
.hi-line{font-size:10.5px;color:#5f7b8c;line-height:1.75;margin-top:6px}
.hi-tag{display:inline-block;background:#eaf3f6;border:1px solid rgba(61,109,135,.22);
  border-radius:99px;padding:1px 7px;font-weight:700;color:#3d6d87;margin-right:4px}
.hi-box{margin-top:8px;padding:9px 11px;border:1px solid rgba(90,78,62,.14);
  background:linear-gradient(135deg,#f4f9f7,#f7f3ea);border-radius:12px}
.hi-head{display:flex;align-items:center;gap:8px;font-size:11.5px;color:#3d6d87;line-height:1.6}
.hi-head b{font-size:12.5px;flex:1}
.hi-head span{font-size:10px;color:#8b8276;font-weight:600}
.hi-ticket{border:1px solid rgba(192,138,84,.35);background:#fbf3e8;color:#96652f;
  border-radius:99px;padding:2px 8px;font-size:10.5px;font-family:inherit;font-weight:700;cursor:pointer}
.hi-ticket:hover{background:#f3e4cf}
.hi-bar{height:6px;border-radius:99px;background:#e3e9e6;overflow:hidden;margin:7px 0 5px}
.hi-bar i{display:block;height:100%;border-radius:99px;
  background:linear-gradient(90deg,#7fb2c8,#4a8b6c);transition:width .5s ease}
.hi-foot{font-size:9.5px;color:#8b8276;line-height:1.65}
.hi-foot.bad{color:#a2564e}
@media(max-width:420px){
  .hi-line{font-size:10px;margin-top:4px;line-height:1.5}
  .hi-box{padding:7px 9px;margin-top:6px;border-radius:10px}
  .hi-head{gap:5px;font-size:10.5px;line-height:1.4}.hi-head b{font-size:11.5px}
  .hi-head span{font-size:9px}
  .hi-ticket{padding:1px 6px;font-size:9.5px}
  .hi-bar{height:5px;margin:5px 0 3px}
  .hi-foot{font-size:9px;line-height:1.4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
}
'''
must('</style>', CSS + '</style>')

# =========================================================
# 1) 审计流水：同步 FNV 链（file:// 也能跑，不引入异步）
# =========================================================
AUDIT = r'''
/* ===== P0-2：饮水审计流水（同步哈希链，file:// 可用） =====
   payload 含 prevHash，改任意一笔都会断链；不改动 id/ts/ml/note/photo 等原始字段。 */
const AUDIT_GENESIS='DS-GENESIS';
function auditFnv(str){
  let h=2166136261;
  for(let i=0;i<str.length;i++){ h^=str.charCodeAt(i); h=Math.imul(h,16777619)>>>0; }
  return 'a'+h.toString(16).padStart(8,'0');
}
function auditPayload(l){
  return ['DS1',l.id||'',l.ts||0,l.ml|0,l.type||'',l.localDate||'',
          l.auditSource||'',l.prevHash||''].join('|');
}
function auditHashOf(l){ return auditFnv(auditPayload(l)); }
function verifyAudit(day){
  const logs=(day&&day.logs)||[]; let prev=AUDIT_GENESIS,brokenAt=-1;
  for(let i=0;i<logs.length;i++){
    const l=logs[i];
    if(!l.hash||l.seq!==i||l.prevHash!==prev||l.hash!==auditHashOf(l)){ brokenAt=i; break; }
    prev=l.hash;
  }
  return {ok:brokenAt<0,len:logs.length,head:prev,brokenAt};
}
function auditMigrate(){
  if(S.auditMigrated) return;
  let broken=false;
  const days=PD();
  for(const k in days){
    const logs=days[k].logs||[];
    if(logs.some(l=>l.hash)){ if(!verifyAudit(days[k]).ok) broken=true; continue; }
    let prev=AUDIT_GENESIS;
    logs.forEach((l,i)=>{
      l.localDate=l.localDate||k; l.seq=i;
      l.auditSource=l.auditSource||'legacy'; l.prevHash=prev;
      l.hash=auditHashOf(l); prev=l.hash;
    });
  }
  S.auditBroken=broken; S.auditMigrated=1; save();
}
function appendLog(day,rec,source){
  const logs=day.logs||(day.logs=[]);
  const l=Object.assign({},rec,{
    id:rec.id||uid(), ts:rec.ts||Date.now(),
    localDate:rec.localDate||dkey(new Date(rec.ts||Date.now())),
    seq:logs.length, auditSource:source||rec.auditSource||'quick',
    prevHash:logs.length?logs[logs.length-1].hash:AUDIT_GENESIS
  });
  l.hash=auditHashOf(l);
  logs.push(l);
  return l;
}
'''
must('function checkinState(){', AUDIT + '\nfunction checkinState(){')

# 所有写入口统一走 appendLog
must("  day.logs.push({id:uid(),ts:Date.now(),ml,type:'water',note});",
     "  appendLog(day,{id:uid(),ts:Date.now(),ml,type:'water',note},'quick');")
must("  day.logs.push(rec); save(); renderAll(); sfx('milk');",
     "  appendLog(day,rec,'selfie'); save(); renderAll(); sfx('milk');")
# 旧 AVG 存档迁移：并入时补链（不覆盖原字段）
must("logs.forEach(l=>{ if(!have.has(l.id)){ PD()[k].logs.push(l); moved++; } });",
     "logs.forEach(l=>{ if(!have.has(l.id)){ appendLog(PD()[k],l,'avg-migrate'); moved++; } });")

# =========================================================
# 2) P0-1：智能提醒（时段进度差 + 免打扰 + 柔性提醒）
# =========================================================
REMIND = r'''
/* ===== P0-1：智能提醒 =====
   7→22 点分段累计曲线：早段 30% / 中段 50% / 晚段 20%，可解释、不靠大模型调度。 */
const REMIND_CFG={wake:7,sleep:22,tolerance:250,gentleAfter:2,maxSnooze:3};
function idealPctAt(d){
  const h=d.getHours()+d.getMinutes()/60;
  if(h<=REMIND_CFG.wake) return 0;
  if(h>=REMIND_CFG.sleep) return 1;
  if(h<=12) return .30*(h-REMIND_CFG.wake)/(12-REMIND_CFG.wake);
  if(h<=18) return .30+.50*(h-12)/6;
  return .80+.20*(h-18)/(REMIND_CFG.sleep-18);
}
function reminderDecision(now){
  const mins=Number(S.settings.interval)||30;
  const since=S.lastRemindAt?now-S.lastRemindAt:Infinity;
  const mode=S.settings.remindMode||'smart';
  const h=new Date(now).getHours()+new Date(now).getMinutes()/60;
  const goal=goalOf(), ml=waterOf(today());
  /* 「别吵我」是用户明确意图，两种模式都要生效；1 分钟演示模式豁免免打扰以便快速看效果 */
  if(S.focusUntil&&now<S.focusUntil)
    return {fire:false,why:'🎯 专注中，延期至 '+fmtTime(S.focusUntil),gap:0,gentle:false};
  if(Number(S.settings.interval)!==1&&(h>=REMIND_CFG.sleep||h<REMIND_CFG.wake))
    return {fire:false,why:'🌙 免打扰 22:00–07:00',gap:0,gentle:false};
  if(ml>=goal) return {fire:false,why:'✓ 今日已达标，停止催水',gap:0,gentle:false};
  if(mode==='fixed'){
    const fire=since>=mins*60000;
    return {fire,why:fire?'固定间隔 '+mins+' 分钟':'距上次提醒 '+Math.max(1,Math.ceil((mins*60000-since)/60000))+' 分钟',
      gap:Math.max(0,goal-ml),gentle:false};
  }
  if(since<mins*60000)
    return {fire:false,why:'距上次提醒不足 '+mins+' 分钟',gap:0,gentle:false};
  const gap=Math.max(0,Math.round(idealPctAt(new Date(now))*goal-ml));
  if(gap<REMIND_CFG.tolerance)
    return {fire:false,why:'进度跟得上（落后不足 '+REMIND_CFG.tolerance+'ml）',gap,gentle:false};
  return {fire:true,why:'落后 '+gap+'ml',gap,gentle:Number(S.remindIgnores||0)>=REMIND_CFG.gentleAfter};
}
function renderRemindLine(){
  const el=$('#remindLine'); if(!el) return;
  const d=reminderDecision(Date.now());
  const mode=(S.settings.remindMode||'smart')==='smart'?'智能提醒':'固定间隔';
  el.innerHTML=`<span class="hi-tag">⏰ ${mode}</span>${esc(d.why)}`+
    (d.fire?' · <b>下次检查即提醒</b>':'');
}
'''
must('function remind(reason){', REMIND + '\nfunction remind(reason){')

must('''function remind(reason){
  S.lastRemindAt=Date.now(); today().reminds.push(Date.now()); save();
  beep();
  const q=localQuote(buildCtx());
  say('⏰ '+q.text,7000);
  toast('⏰ 半小时到，起来喝大水');
  makeQuote();''',
     '''function remind(d){
  d=d||{why:'半小时到',gap:0,gentle:false};
  const now=Date.now(), prev=S.lastRemindAt||now;
  /* 上次提醒后没喝水才算「忽略」，最多累计到柔性升级，不变成轰炸 */
  const drank=(today().logs||[]).some(l=>l.type==='water'&&l.ts>prev-1000);
  if(prev<now&&!drank) S.remindIgnores=Math.min(REMIND_CFG.gentleAfter+1,Number(S.remindIgnores||0)+1);
  S.lastRemindAt=now;
  const day=today(); (day.reminds||(day.reminds=[])).push(now); save();
  beep();
  const q=localQuote(buildCtx());
  const lead=d.gentle?'🫧 温柔提醒':'⏰ 该喝大水了';
  say(lead+'：'+d.why+'。'+q.text,7000);
  toast(lead+' · '+d.why,d.gentle?2600:4200);
  makeQuote();''')

must('''function tick(){
  const mins=Number(S.settings.interval)||30;
  const last=S.lastRemindAt||Date.now();
  if(!S.lastRemindAt){ S.lastRemindAt=Date.now(); save(); return; }
  if(Date.now()-last >= mins*60*1000) remind();
}''',
     '''function tick(){
  if(!S.lastRemindAt){ S.lastRemindAt=Date.now(); save(); renderRemindLine(); return; }
  const d=reminderDecision(Date.now());
  if(d.fire) remind(d);
  renderRemindLine();
}''')
# 喝水后清零「忽略」累计，并清掉柔性标记
must("  save(); renderAll(); sfx('water');",
     "  S.remindIgnores=0; save(); renderAll(); sfx('water');", 1)
# 15 秒刷新里补上新指标
must("  setInterval(()=>{ renderProgress(); renderScore(); renderWeek(); updateClock(); },15000);",
     "  setInterval(()=>{ renderProgress(); renderScore(); renderWeek(); updateClock(); renderRemindLine(); renderHydration(); },15000);")

# =========================================================
# 3) P0-3：可信水合指数（漏记不清零，缓慢回落 + 修复券）
# =========================================================
HI = r'''
/* ===== P0-3：可信水合指数 0–100 =====
   与积分/榜单/Rank 解耦；漏记只缓慢回落，不清零；奶茶与连打是低风险扣分，不重罚。 */
const HI_CFG={baseline:15,wFill:.55,wRhythm:.20,wWeek:.25,decayPerHour:2,maxDecay:12,
  milkPenalty:3,cheatPenalty:2,milestones:[60,80,95]};
function hiDayFill(day,goal){ return Math.min(1,waterOf(day)/goal); }
function hiRaw(){
  const goal=goalOf(), d=today(), sc=scoreDay(d,goal);
  const fill=hiDayFill(d,goal);
  const expect=Math.max(3,Math.ceil(goal/300));
  const rhythm=Math.min(1,sc.valid/expect);
  const days=PD(), past=Object.keys(days).sort().slice(-8,-1);
  const week=past.length?past.reduce((a,k)=>a+hiDayFill(days[k],goal),0)/past.length:fill*.55;
  /* 新用户不是 0 分：给一个「信任基线」，避免一打开就像被清零 */
  let v=HI_CFG.baseline+(fill*HI_CFG.wFill+rhythm*HI_CFG.wRhythm+week*HI_CFG.wWeek)*(100-HI_CFG.baseline);
  /* 长时间空白缓慢衰减，夜间不计（睡觉不算断签） */
  const h=new Date().getHours(), last=lastWaterTs();
  if(last&&h>=REMIND_CFG.wake&&h<REMIND_CFG.sleep){
    const idle=(Date.now()-last)/3600000;
    v-=Math.min(HI_CFG.maxDecay,Math.max(0,idle-2)*HI_CFG.decayPerHour);
  }
  v-=sc.milk*HI_CFG.milkPenalty+sc.cheat*HI_CFG.cheatPenalty;
  return clamp(v,0,100);
}
function hydrationIndex(){
  const v=hiRaw();
  /* 修复券只抬展示值，绝不参与里程碑判定，避免「用券→抬高→又发券」的自我循环 */
  const shown=(S.hiRepairAt&&Date.now()-S.hiRepairAt<3600000)
    ? Math.max(v,Number(S.hiRepairBase||v)) : v;
  return Math.round(clamp(shown,0,100));
}
function hiSync(){
  const shown=hydrationIndex(), raw=hiRaw();
  const got=S.hiAwards||(S.hiAwards=[]);
  const first=!S.hiAwardsInit;          // 老存档首次：静默补齐历史里程碑，不补发券、不弹满屏 toast
  let dirty=false;
  if(shown>Number(S.hiBest||0)){ S.hiBest=shown; dirty=true; }
  for(const m of HI_CFG.milestones){
    if(raw>=m&&!got.includes(m)){
      got.push(m); dirty=true;
      if(!first){
        S.hiTickets=Number(S.hiTickets||0)+1;
        try{ toast('🎫 水合指数首次达到 '+m+'，获得 1 张修复券'); }catch(e){}
      }
    }
  }
  if(first){ S.hiAwardsInit=1; dirty=true; }
  if(dirty) save();                     // 只在状态真的变了才落盘，避免 15 秒定时器反复写
}
function useRepairTicket(){
  if(Number(S.hiTickets||0)<1){ toast('暂无修复券：指数首次到 60 / 80 / 95 会送'); return; }
  S.hiTickets=Number(S.hiTickets||0)-1;
  S.hiRepairAt=Date.now(); S.hiRepairBase=hydrationIndex()+12;
  save(); renderHydration();
  try{ say('哈士喵把监察本翻到空白的一页：「今天不算断签，补一口就续上，喵。」',6000); }catch(e){}
  toast('🎫 已用修复券：一小时内的空白衰减清零');
}
function renderHydration(){
  const el=$('#hiLine'); if(!el) return;
  hiSync();
  const v=hydrationIndex(), a=verifyAudit(today());
  el.innerHTML=`<div class="hi-head"><b>💧 可信水合指数 ${v}</b>
      <span>最高 ${Number(S.hiBest||0)}</span>
      <button class="hi-ticket" id="hiRepair" title="消耗修复券，抵消一小时空白衰减">🎫 ${Number(S.hiTickets||0)}</button></div>
    <div class="hi-bar"><i style="width:${v}%"></i></div>
    <div class="hi-foot ${a.ok?'':'bad'}">${a.ok
      ? '✓ 审计链 '+a.len+' 笔 · '+String(a.head).slice(0,10)
      : '⚠ 审计链在第 '+(a.brokenAt+1)+' 笔断开（原记录已保留，建议导出核对）'}
      · 漏记不清零，只缓慢回落</div>`;
  const b=$('#hiRepair'); if(b) b.onclick=useRepairTicket;
}
'''
must('function renderAll(){', HI + '\nfunction renderAll(){')
must('function renderAll(){ renderMoods(); renderWeather(); renderProgress(); renderScore(); renderLogs(); renderWeek(); updateClock(); }',
     'function renderAll(){ renderMoods(); renderWeather(); renderProgress(); renderScore(); renderLogs(); renderWeek(); updateClock(); renderRemindLine(); renderHydration(); }')

# 启动最早做一次老存档审计链迁移
must('''async function init(){
  ensureProfiles();
  renderAll();''',
     '''async function init(){
  ensureProfiles();
  auditMigrate();          // 老存档补审计链：必须在任何 verifyAudit / renderHydration 之前
  renderAll();''')

# =========================================================
# 4) 设置面板：提醒策略 + 专注免打扰
# =========================================================
must('''      <div class="hint">两次喝水打卡至少间隔这么久，冷却期内再点会被拦下。独立于提醒间隔，切「1 分钟演示模式」也不会放宽。改小后历史连打判定会同步变化。</div></div>
    <div class="field"><label>📍 位置''',
     '''      <div class="hint">两次喝水打卡至少间隔这么久，冷却期内再点会被拦下。独立于提醒间隔，切「1 分钟演示模式」也不会放宽。改小后历史连打判定会同步变化。</div></div>
    <div class="field"><label>⏰ 提醒策略</label>
      <select id="sRemindMode">
        <option value="smart" ${(s.remindMode||'smart')==='smart'?'selected':''}>智能提醒（推荐）· 按进度差 / 免打扰</option>
        <option value="fixed" ${s.remindMode==='fixed'?'selected':''}>固定间隔 · 沿用老习惯</option>
      </select>
      <div class="hint">智能模式按 7:00–22:00 的时段预算算「此刻应喝多少」，落后超 250ml 才提醒；达标即停催、22:00–07:00 免打扰、刚提醒过不重复催；连续忽略 2 次只升级一次温柔提醒。两种模式都受下方间隔约束。</div></div>
    <div class="field"><label>🎯 专注免打扰</label>
      <button class="btn ghost" id="sFocus" style="width:100%">延期 30 分钟（今日还可 ${Math.max(0,3-Number(S.snoozeDate===dkey()?S.snoozeCount:0))} 次）</button>
      <div class="hint">开会 / 专注时按一下，这段时间不弹提醒；每天最多 3 次，喝水打卡会自动清掉忽略累计。</div></div>
    <div class="field"><label>📍 位置''')

must("""    S.settings.interval=Number($('#sInterval').value);""",
     """    S.settings.interval=Number($('#sInterval').value);
    S.settings.remindMode=$('#sRemindMode').value==='fixed'?'fixed':'smart';""")

# 专注按钮事件（插在 #sLoc 绑定旁）
must("  $('#sLoc').onclick=()=>{ closeModal(); openLocationPicker(); };",
     """  $('#sLoc').onclick=()=>{ closeModal(); openLocationPicker(); };
  $('#sFocus').onclick=()=>{
    if(S.snoozeDate!==dkey()){ S.snoozeDate=dkey(); S.snoozeCount=0; }
    if(Number(S.snoozeCount||0)>=3){ toast('今日延期次数已用完，喵'); return; }
    S.snoozeCount=Number(S.snoozeCount||0)+1;
    S.focusUntil=Date.now()+30*60*1000; save(); closeModal(); renderAll();
    toast('🎯 专注中，30 分钟内不弹提醒');
  };""")

# =========================================================
# 5) 分享卡 / 云档 / 结算接入
# =========================================================
must("""    `💭 心情：${o.mood}${o.quote?'\\n✦ '+o.quote:''}\\n`+
    `校验码 ${o.code} · ${toyShareNote()}\\n`+""",
     """    `💭 心情：${o.mood}${o.quote?'\\n✦ '+o.quote:''}\\n`+
    `💧 可信水合指数 ${hydrationIndex()} · 审计链 ${String(verifyAudit(today()).head).slice(0,10)}\\n`+
    `校验码 ${o.code} · ${toyShareNote()}\\n`+""")

must("""  g.fillText(o.code,154,890);
  g.fillStyle='#8b8276'; g.font=`600 10px ${F}`;""",
     """  g.fillText(o.code,154,890);
  g.fillStyle='#7a90a0'; g.font=`600 10px ${F}`;
  g.fillText('水合 '+hydrationIndex()+' · 链 '+String(verifyAudit(today()).head).slice(0,9),330,890);
  g.fillStyle='#8b8276'; g.font=`600 10px ${F}`;""")

must("""      卡片与成绩在本机生成，校验码用于核对「${cooldownMin()} 分钟冷却」下的打卡记录；不联网、不上传，也不是联网认证榜单。</div>`);""",
     """      卡片与成绩在本机生成，校验码用于核对「${cooldownMin()} 分钟冷却」下的打卡记录；水合指数与审计链头一并写入文案，接收方可按同版本规则复核。不联网、不上传，也不是联网认证榜单。</div>`);""")

# Toy 云档：auditHead 改用链头，水合指数改为实时值
must("      mood:d.mood||'',auditLen:logs.length,auditHead:checkCode(logs.map(l=>l.id||'').join('|'))};",
     "      mood:d.mood||'',auditLen:logs.length,auditHead:verifyAudit(d).head,auditOK:verifyAudit(d).ok};")
must("    hydrationIndex:Number(S.hydrationIndex||0),",
     "    hydrationIndex:hydrationIndex(),hiBest:Number(S.hiBest||0),hiTickets:Number(S.hiTickets||0),")

# 结算台补一行指数
must("    `「今日结算，喵。」\\n白水 ${ml} / ${goal} ml（${Math.round(ml/goal*100)}%）· 小甜水 ${milk} 杯 · 有效打卡 ${sc.valid} 次\\n今日积分 ${sc.total} 分 · 心情 ${S.settings.mood} · 校验码 ${checkCode(PROFILE().id+dkey()+sc.total+sc.valid)}`,",
     "    `「今日结算，喵。」\\n白水 ${ml} / ${goal} ml（${Math.round(ml/goal*100)}%）· 小甜水 ${milk} 杯 · 有效打卡 ${sc.valid} 次\\n今日积分 ${sc.total} 分 · 可信水合指数 ${hydrationIndex()} · 心情 ${S.settings.mood} · 校验码 ${checkCode(PROFILE().id+dkey()+sc.total+sc.valid)}`,")

open(P, 'w', encoding='utf-8').write(s)
after = os.path.getsize(P)
print('P0 三条链路已写入', P)
print('  体积:', round(before/1024,1),'→',round(after/1024,1),'KiB  | 增量',round((after-before)/1024,1),'KiB')
print('  零 CDN:', not any(x in s for x in ['cdn.jsdelivr','unpkg.com','cdnjs']))
print('  内嵌图/音频:', s.count('data:image/webp;base64,'),'/',s.count('data:audio/ogg;base64,'))
