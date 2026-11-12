# -*- coding: utf-8 -*-
"""音频专项：给合并版加 音效/背景音乐（默认关但功能完整）+ 内嵌音频视觉 + 全链路钩子。"""
import re, json, io, base64, os
from PIL import Image

ROOT = '/data/workspace'
P = ROOT + '/大水计算器-合并版.html'
AVG = ROOT + '/大水计算器-哈士喵AVG.html'
B = ROOT + '/美术产出'
s = open(P, encoding='utf-8').read()

def must(old, new, cnt=1):
    global s
    n = s.count(old)
    assert n == cnt, f'锚点命中 {n} 次（期望 {cnt}）：{old[:90]!r}'
    s = s.replace(old, new, cnt)

def uri(path, size, q=74):
    im = Image.open(path).convert('RGB').resize(size, Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, 'WEBP', quality=q, method=6)
    return 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode()

# ---------------- 1) 取 AVG 现成 4 段音频 ----------------
avg = open(AVG, encoding='utf-8').read()
A = json.loads(re.search(r'const A = (\{.*?\});\n', avg, re.S).group(1))
AUDIO = A['audio']                       # 轻快 / 安静 / 揭晓 / tick（ogg data URI）
print('现成音频:', list(AUDIO.keys()))

hm_raw = re.search(r'const HM = (\{[^\n]*\});', s).group(1)
HM = json.loads(hm_raw); HM['audio'] = AUDIO
must('const HM = ' + hm_raw + ';', 'const HM = ' + json.dumps(HM, ensure_ascii=False, separators=(',', ':')) + ';')

# ---------------- 2) 内嵌音频专项美术 ----------------
art_raw = re.search(r'const ART = (\{[^\n]*\});', s).group(1)
ART = json.loads(art_raw)
icons = {}
for key, fn in [('water','1_打卡叮咚'),('block','2_防作弊拦截'),('quote','3_语录风铃'),
                ('milk','4_奶茶自首'),('end','5_结局揭晓'),('bgm','6_背景音乐')]:
    icons[key] = uri(f'{B}/音效图标/{fn}.png', (96, 96))
ART['audio'] = {'banner': uri(f'{B}/音频专项-音乐主视觉.png', (480, 270), 74), 'icons': icons}
must('const ART = ' + art_raw + ';', 'const ART = ' + json.dumps(ART, ensure_ascii=False, separators=(',', ':')) + ';')
print('音频美术内嵌: 1 横幅 +', len(icons), '枚图标')

# ---------------- 3) 默认关：DEFAULT + 老存档一次性迁移 ----------------
must("mood:'通透', sound:true, patrol:true, notify:true, autoGoalByWeather:true,",
     "mood:'通透', sound:false, bgm:false, volume:0.35, bgmTrack:'轻快', patrol:true, notify:true, autoGoalByWeather:true,")

must('let S = load();', '''let S = load();
/* 音频默认关：一次性迁移，老存档里开着的 sound / bgm 也重置为关闭（用户仍可手动开） */
try{
  if(!localStorage.getItem('dashui.audio.defaultOff')){
    S.settings.sound=false; S.settings.bgm=false;
    S.settings.volume=Number(S.settings.volume)||0.35;
    S.settings.bgmTrack=S.settings.bgmTrack||'轻快';
    save(); localStorage.setItem('dashui.audio.defaultOff','1');
  }
}catch(e){}''')

# ---------------- 4) 音频引擎（放在 beep 之前，全局可用） ----------------
ENGINE = r'''
/* ===== 音效 / 背景音乐：默认关闭，用户开启后才发声 ===== */
let audioEl=null, curBgm='', userActed=false;
function auVol(v){ return Math.max(0,Math.min(1,Number((v===undefined?S.settings.volume:v)||0.35))); }
function auTone(seq,dur,type,vol){
  try{
    const AC=window.AudioContext||window.webkitAudioContext; if(!AC)return;
    const ac=new AC(), t0=ac.currentTime, v=auVol()*vol;
    seq.forEach(([f,off])=>{
      const o=ac.createOscillator(), g=ac.createGain();
      o.type=type||'sine'; o.frequency.setValueAtTime(f,t0+off);
      g.gain.setValueAtTime(.0001,t0+off);
      g.gain.exponentialRampToValueAtTime(Math.max(v,.0002),t0+off+.02);
      g.gain.exponentialRampToValueAtTime(.0001,t0+off+dur);
      o.connect(g); g.connect(ac.destination); o.start(t0+off); o.stop(t0+off+dur+.02);
    });
    setTimeout(()=>{ try{ac.close();}catch(e){} },(dur+1)*1000);
  }catch(e){}
}
function auNoise(){
  try{
    const AC=window.AudioContext||window.webkitAudioContext; if(!AC)return;
    const ac=new AC(), len=Math.floor(ac.sampleRate*.09);
    const buf=ac.createBuffer(1,len,ac.sampleRate), d=buf.getChannelData(0);
    for(let i=0;i<len;i++) d[i]=(Math.random()*2-1)*Math.pow(1-i/len,3);
    const src=ac.createBufferSource(); src.buffer=buf;
    const f=ac.createBiquadFilter(); f.type='highpass'; f.frequency.value=900;
    const g=ac.createGain(); g.gain.value=auVol()*.7;
    src.connect(f); f.connect(g); g.connect(ac.destination); src.start();
    setTimeout(()=>{ try{ac.close();}catch(e){} },400);
  }catch(e){}
}
function playClip(name,vol){
  try{
    const a=new Audio(HM.audio[name]||HM.audio['tick']);
    a.volume=Math.max(0,Math.min(1,vol===undefined?auVol()*.9:vol));
    a.play().catch(()=>{});
  }catch(e){}
}
/* force=true 用于「音效试听」：不受开关限制，仅本次响一下 */
function sfx(k='tick',force){
  if(!force&&(!S.settings.sound||!userActed)) return;
  try{
    if(k==='water'){ auTone([[660,0],[880,.09]],.26,'sine',.42); return; }
    if(k==='block'){ auTone([[190,0],[150,.12]],.22,'triangle',.38); return; }
    if(k==='quote'){ auTone([[784,0],[988,.08],[1175,.16]],.42,'sine',.30); return; }
    if(k==='milk'){ auNoise(); return; }
    if(k==='end'){ playClip('揭晓'); return; }
    if(k==='switch'){ auTone([[520,0],[700,.06]],.16,'sine',.28); return; }
    playClip(k==='tick'?'tick':'轻快');
  }catch(e){}
}
function bgm(name){
  if(!S.settings.bgm){ bgmStop(); return; }
  if(!HM.audio[name]) name='轻快';
  if(curBgm===name&&audioEl) return;
  curBgm=name;
  try{
    if(audioEl) audioEl.pause();
    audioEl=new Audio(HM.audio[name]); audioEl.loop=true;
    audioEl.volume=auVol()*.6;
    audioEl.play().catch(()=>{});
  }catch(e){}
}
function bgmStop(){
  if(audioEl){ try{audioEl.pause();}catch(e){} audioEl=null; }
  curBgm='';
}
function applyAudio(){
  if(S.settings.bgm) bgm(S.settings.bgmTrack||'轻快');
  else bgmStop();
  if(audioEl) audioEl.volume=auVol()*.6;
}
function audioStateLine(){
  return (S.settings.sound?'🔊 音效开':'🔇 音效关')+' · '+(S.settings.bgm?'🎵 音乐开':'🔕 音乐关');
}
/* 浏览器自动播放限制：首次交互后再补一次播放；默认关时什么都不做 */
document.addEventListener('pointerdown',()=>{
  userActed=true;
  if(S.settings.bgm){ if(audioEl) audioEl.play().catch(()=>{}); else applyAudio(); }
},{once:true});

'''
must('function beep(){', ENGINE + 'function beep(){')

# ---------------- 5) 音效钩子 ----------------
# addWater / selfReport 两处 beep 分别换成对应音效
old = 'save(); renderAll(); beep();'
assert s.count(old) == 2
s = s.replace(old, 'save(); renderAll(); sfx(\'water\');', 1)
s = s.replace(old, 'save(); renderAll(); sfx(\'milk\');', 1)

must("  try{ toast(`⛔ 防作弊：${cooldownMin()} 分钟内只能打卡一次，还要等 ${fmtWait(st.waitMs)}`); }catch(e){}\n  return false;",
     "  try{ toast(`⛔ 防作弊：${cooldownMin()} 分钟内只能打卡一次，还要等 ${fmtWait(st.waitMs)}`); }catch(e){}\n  sfx('block');\n  return false;")

must("  say(q.text,5200);\n}", "  say(q.text,5200);\n  sfx('quote');\n}")

must("  S.avatar=id; save(); renderAvatar();", "  S.avatar=id; save(); renderAvatar(); sfx('switch');")

# ---------------- 6) 主面板入口 ----------------
must('<button class="btn primary" id="btnStory" style="font-size:11px">🎬 剧情互动</button>',
     '<button class="btn primary" id="btnStory" style="font-size:11px">🎬 剧情互动</button>\n'
     '        <button class="btn ghost" id="btnAudio" style="font-size:11px">🔇 音效与音乐</button>')

# ---------------- 7) 设置面板：加 BGM 开关 + 独立面板入口 ----------------
must('''        <button class="chip ${s.sound?'on':''}" data-tog="sound">🔊 提示音</button>''',
     '''        <button class="chip ${s.sound?'on':''}" data-tog="sound">🔊 音效</button>
        <button class="chip ${s.bgm?'on':''}" data-tog="bgm">🎵 背景音乐</button>
        <button class="chip" id="sAudioPanel">🎛 音效与音乐设置</button>''')

must("  $('#sLoc').onclick=()=>{ closeModal(); openLocationPicker(); };",
     "  $('#sLoc').onclick=()=>{ closeModal(); openLocationPicker(); };\n"
     "  $('#sAudioPanel').onclick=()=>{ closeModal(); openAudioPanel(); };")

must("    S.lastRemindAt=Date.now(); save(); closeModal(); renderAll();",
     "    S.lastRemindAt=Date.now(); save(); closeModal(); renderAll(); applyAudio();")

# ---------------- 8) 剧场 HUD 快捷开关 ----------------
must('''  <div id="stHud"><b>🎬 大水监察司 · 剧场</b><span id="stHudInfo"></span>
    <button class="st-close" id="stClose">✕ 回仪表盘</button></div>''',
     '''  <div id="stHud"><b>🎬 大水监察司 · 剧场</b><span id="stHudInfo"></span>
    <button class="st-close" id="stSnd" title="音效开关">🔇</button>
    <button class="st-close" id="stBgm" title="背景音乐开关">🔕</button>
    <button class="st-close" id="stClose">✕ 回仪表盘</button></div>''')

# ---------------- 9) CSS ----------------
CSS = '''
/* ===== 音频专项：音效与音乐面板 ===== */
.au-banner{position:relative;width:100%;border-radius:14px;overflow:hidden;margin:4px 0 12px;
  border:1px solid rgba(90,78,62,.14)}
.au-banner img{width:100%;display:block}
.au-banner .t{position:absolute;left:14px;top:12px;display:flex;flex-direction:column;gap:3px;
  text-shadow:0 1px 6px rgba(255,255,255,.8)}
.au-banner .t b{font-size:15px;color:#3d6d87;font-weight:800}
.au-banner .t span{font-size:10px;color:#6b6255}
.au-sw{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px}
.au-sw button{display:flex;align-items:center;gap:7px;border:1px solid rgba(90,78,62,.18);
  background:#fff;border-radius:12px;padding:9px 10px;font-family:inherit;cursor:pointer;
  text-align:left;color:#6b6255;transition:.18s}
.au-sw button.on{border-color:#3d6d87;background:#eaf3f6;color:#3d6d87}
.au-sw button img{width:28px;height:28px;object-fit:contain}
.au-sw button b{display:block;font-size:12px}
.au-sw button small{display:block;font-size:10px;opacity:.7;margin-top:2px}
.au-vol{width:100%;accent-color:#3d6d87}
.au-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;margin-top:6px}
.au-grid button{display:flex;flex-direction:column;align-items:center;gap:3px;
  border:1px solid rgba(90,78,62,.16);background:#fff;border-radius:11px;padding:8px 3px;
  font-family:inherit;font-size:10px;font-weight:700;color:#6b6255;cursor:pointer;transition:.16s}
.au-grid button:hover{background:#eaf3f6;border-color:#3d6d87;color:#3d6d87}
.au-grid img{width:40px;height:40px;object-fit:contain}
#stHud{gap:5px}
#stHud .st-close{padding:5px 9px;font-size:12px}
@media(max-width:420px){
  .au-banner .t b{font-size:13px}.au-banner .t span{font-size:9px}
  .au-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:5px}
  .au-grid img{width:34px;height:34px}.au-grid button{font-size:9px;padding:6px 2px}
  .au-sw button{padding:7px 6px;gap:5px}.au-sw button img{width:24px;height:24px}
}
'''
must('</style>', CSS + '</style>')

# ---------------- 10) 独立音频面板 + 剧场钩子 ----------------
PANEL = r'''
/* ===== 音效与音乐：独立面板 ===== */
function renderAudioHud(){
  const a=$('#stSnd'), b=$('#stBgm');
  if(a) a.textContent=S.settings.sound?'🔊':'🔇';
  if(b) b.textContent=S.settings.bgm?'🎵':'🔕';
  const btn=$('#btnAudio'); if(btn) btn.textContent=(S.settings.sound||S.settings.bgm?'🔊':'🔇')+' 音效与音乐';
}
function openAudioPanel(){
  const ic=ART.audio.icons;
  const items=[['water','打卡叮咚'],['block','防作弊拦截'],['quote','语录风铃'],
               ['milk','奶茶自首'],['end','结局揭晓'],['bgm','背景音乐']];
  const tracks=['轻快','安静','揭晓'];
  openModal(`<div class="mtitle">🎛 音效与音乐</div>
    <div class="msub" id="auState">${audioStateLine()} · 默认全部关闭</div>
    <div class="au-banner"><img src="${ART.audio.banner}" alt="音乐主视觉">
      <div class="t"><b>大水监察司 · 八音盒</b><span>4 段音频 + 6 种音效 · 全部内嵌 · 不联网</span></div></div>
    <div class="au-sw">
      <button data-au-tog="sound" class="${S.settings.sound?'on':''}"><img src="${ic.water}" alt=""><span><b>🔊 音效</b><small>${S.settings.sound?'已开启':'已关闭'}</small></span></button>
      <button data-au-tog="bgm" class="${S.settings.bgm?'on':''}"><img src="${ic.bgm}" alt=""><span><b>🎵 背景音乐</b><small>${S.settings.bgm?'已开启':'已关闭'}</small></span></button>
    </div>
    <div class="field"><label>🔉 音量 <span id="auVolTxt">${Math.round(auVol()*100)}%</span></label>
      <input class="au-vol" type="range" id="auVol" min="0" max="100" value="${Math.round(auVol()*100)}"></div>
    <div class="field"><label>🎼 背景音乐曲目（剧场会随场景自动切）</label>
      <div class="chips" id="auTracks">${tracks.map(t=>`<button class="chip ${S.settings.bgmTrack===t?'on':''}" data-track="${t}">${t}</button>`).join('')}</div></div>
    <div class="field"><label>🎧 音效试听（点一下响一次，不受开关影响）</label>
      <div class="au-grid">${items.map(([k,n])=>`<button data-try="${k}"><img src="${ic[k]}" alt=""><span>${n}</span></button>`).join('')}</div></div>
    <div class="hint" style="font-size:10px;line-height:1.8;margin-top:9px">
      默认关闭：不自动播放、不联网、不上传。开启后浏览器要求先有一次点击才会出声；音量、开关与曲目都存在本机。
      剧场里喝水 / 拦截 / 语录 / 结局会跟着响，BGM 会按场景换曲。</div>
    <div class="btnrow"><button class="btn primary" id="auDone">完成</button></div>`);
  const refresh=()=>{
    $$('#modalBox [data-au-tog]').forEach(b=>{
      const on=!!S.settings[b.dataset.auTog];
      b.classList.toggle('on',on);
      const sm=b.querySelector('small'); if(sm) sm.textContent=on?'已开启':'已关闭';
    });
    const st=$('#auState'); if(st) st.textContent=audioStateLine()+' · 默认全部关闭';
    renderAudioHud();
  };
  $$('#modalBox [data-au-tog]').forEach(b=>b.onclick=()=>{
    S.settings[b.dataset.auTog]=!S.settings[b.dataset.auTog];
    save(); applyAudio(); refresh(); sfx('switch',true);
  });
  $$('#modalBox [data-track]').forEach(b=>b.onclick=()=>{
    S.settings.bgmTrack=b.dataset.track; save();
    $$('#modalBox [data-track]').forEach(x=>x.classList.toggle('on',x===b));
    if(S.settings.bgm) bgm(S.settings.bgmTrack);
    sfx('switch',true);
  });
  $('#auVol').oninput=e=>{
    S.settings.volume=Number(e.target.value)/100;
    $('#auVolTxt').textContent=e.target.value+'%';
    if(audioEl) audioEl.volume=auVol()*.6;
  };
  $('#auVol').onchange=()=>save();
  $$('#modalBox [data-try]').forEach(b=>b.onclick=()=>{
    const k=b.dataset.try;
    if(k==='bgm') playClip(S.settings.bgmTrack||'轻快');
    else sfx(k,true);
  });
  $('#auDone').onclick=()=>{ save(); applyAudio(); refresh(); closeModal(); toast('🎛 '+audioStateLine()); };
}
$('#btnAudio').onclick=openAudioPanel;
$('#stSnd').onclick=()=>{ S.settings.sound=!S.settings.sound; save(); renderAudioHud(); sfx('switch',true); toast('🔊 音效'+(S.settings.sound?'已开启':'已关闭')); };
$('#stBgm').onclick=()=>{ S.settings.bgm=!S.settings.bgm; save(); applyAudio(); renderAudioHud(); toast('🎵 背景音乐'+(S.settings.bgm?'已开启':'已关闭')); };
renderAudioHud();

'''
must('const ST={open:false,typing:null,cgKeys:Object.keys(HM.cg),face:\'平静\'};',
     PANEL + "const ST={open:false,typing:null,cgKeys:Object.keys(HM.cg),face:'平静'};")

# 剧场钩子
must("  stBG('01_主页书架'); stFace('平静'); stHud();\n  stGo('intro');",
     "  stBG('01_主页书架'); stFace('平静'); stHud();\n  renderAudioHud(); bgm(S.settings.bgmTrack||'轻快');\n  stGo('intro');")
must("  document.body.style.overflow='';\n  renderAll();\n}",
     "  document.body.style.overflow='';\n  renderAll(); applyAudio();\n}")
must("  if(!ok){\n    $('#stBg').style.opacity='0';",
     "  if(!ok){\n    sfx('block');\n    $('#stBg').style.opacity='0';")
must("S.settings.mood=m; today().mood=m; save(); renderMoods(); renderAvatar();\n",
     "S.settings.mood=m; today().mood=m; save(); renderMoods(); renderAvatar(); sfx('switch');\n")
must("  $('#stEnd').classList.add('show');",
     "  sfx('end'); bgm('揭晓');\n  $('#stEnd').classList.add('show');")

# ---------------- 11) 保存 ----------------
open(P, 'w', encoding='utf-8').write(s)
print('升级完成:', P, round(os.path.getsize(P)/1024, 1), 'KiB')
print('  内嵌位图:', s.count('data:image/webp;base64,'), '张 | 内嵌音频:', s.count('data:audio/ogg;base64,'), '段')
print('  音频入口:', all(x in s for x in ['openAudioPanel','function sfx(','function bgm(','data-au-tog','stSnd']))
