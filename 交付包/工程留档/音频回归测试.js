const { chromium }=require('playwright');const http=require('http');const fs=require('fs');
const ROOT='/data/workspace';let buf;
const srv=http.createServer((q,r)=>{try{buf=fs.readFileSync(ROOT+'/'+decodeURIComponent(q.url.split('?')[0].slice(1)))}catch(e){r.writeHead(404);r.end();return}r.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});r.end(buf)});
const URL='http://localhost:8140/'+encodeURIComponent('大水计算器-合并版.html');
const log=(k,v)=>console.log(`${k}: ${v}`);
const findings=[],errs=[];
const F=(k,v)=>{findings.push([k,v]);console.log(`  [发现] ${k}: ${v}`)};
let browser;
async function open(w=1440,h=900,init){
  const ctx=await browser.newContext({viewport:{width:w,height:h},
    geolocation:{latitude:24.896,longitude:118.605},permissions:['geolocation']});
  if(init) await ctx.addInitScript(init);
  const p=await ctx.newPage();p.on('pageerror',e=>errs.push(e.message));
  await p.goto(URL,{waitUntil:'domcontentloaded'});await p.waitForTimeout(1600);
  return {ctx,p};
}
const SPY=`window.__audioNew=[];window.__sfxLog=[];
  (function(){const A=window.Audio;window.Audio=function(src){window.__audioNew.push(String(src).slice(0,30));return new A(src);};window.Audio.prototype=A.prototype;})();`;

(async()=>{
 await new Promise(r=>srv.listen(8140,r));
 browser=await chromium.launch({headless:true,executablePath:'/usr/local/bin/chromium',args:['--no-sandbox']});

 // ===== 1) 默认关（全新用户）+ 加载时不自动播放 =====
 {
   const {ctx,p}=await open(1440,900,SPY+`
     window.addEventListener('load',()=>{
       const _sfx=window.sfx; window.sfx=function(k,f){window.__sfxLog.push(k);return _sfx(k,f);};
     });`);
   const d=await p.evaluate(()=>({sound:S.settings.sound,bgm:S.settings.bgm,
     volume:S.settings.volume,track:S.settings.bgmTrack,
     audioEl:!!audioEl,newAudio:window.__audioNew.length,
     flag:localStorage.getItem('dashui.audio.defaultOff'),
     btn:$('#btnAudio').textContent.trim(),stSnd:$('#stSnd').textContent,stBgm:$('#stBgm').textContent}));
   log('全新默认',JSON.stringify(d));
   if(d.sound!==false||d.bgm!==false)F('默认未关',JSON.stringify(d));
   if(d.audioEl||d.newAudio!==0)F('加载时自动播放',JSON.stringify(d));
   if(!d.flag)F('默认关迁移标记缺失','');
   if(!d.btn.includes('🔇'))F('主面板未显示静音态',d.btn);
   await ctx.close();
 }

 // ===== 2) 老存档（sound:true / bgm:true）一次性迁移为关 =====
 {
   const {ctx,p}=await open(1200,900);
   await p.evaluate(()=>{
     const raw=JSON.parse(localStorage.getItem('dashui.pet.v1')||'null')||{};
     raw.settings=Object.assign({},raw.settings,{sound:true,bgm:true});
     localStorage.setItem('dashui.pet.v1',JSON.stringify(raw));
     localStorage.removeItem('dashui.audio.defaultOff');
   });
   await p.reload({waitUntil:'domcontentloaded'});await p.waitForTimeout(1500);
   const d=await p.evaluate(()=>({sound:S.settings.sound,bgm:S.settings.bgm,flag:localStorage.getItem('dashui.audio.defaultOff')}));
   log('老存档迁移',JSON.stringify(d));
   if(d.sound!==false||d.bgm!==false||d.flag!=='1')F('老存档未重置为关',JSON.stringify(d));
   await ctx.close();
 }

 // ===== 3) 音频面板：素材、开关、音量、曲目、试听 =====
 {
   const {ctx,p}=await open(1440,900,SPY+`
     window.addEventListener('load',()=>{
       const _sfx=window.sfx; window.sfx=function(k,f){window.__sfxLog.push(k);return _sfx(k,f);};
       const _pc=window.playClip; window.playClip=function(n,v){window.__sfxLog.push('clip:'+n);return _pc(n,v);};
     });`);
   await p.click('#btnAudio');await p.waitForSelector('#auState');
   const panel=await p.evaluate(()=>({
     title:$('#modalBox .mtitle').textContent.trim(),
     state:$('#auState').textContent.trim(),
     banner:$('.au-banner img')?.getAttribute('src')?.slice(0,30),
     bannerOK:$('.au-banner img')?.complete&&$('.au-banner img')?.naturalWidth>0,
     icons:document.querySelectorAll('.au-grid img').length,
     iconsOK:[...document.querySelectorAll('.au-grid img')].every(i=>i.complete&&i.naturalWidth>0),
     sw:document.querySelectorAll('[data-au-tog]').length,
     tracks:document.querySelectorAll('[data-track]').length,
     vol:$('#auVol').value
   }));
   log('音频面板',JSON.stringify(panel));
   if(!panel.bannerOK||!panel.iconsOK||panel.icons!==6||panel.sw!==2||panel.tracks!==3)
     F('音频面板素材/结构异常',JSON.stringify(panel));
   if(!panel.state.includes('默认全部关闭'))F('面板未标注默认关',panel.state);

   // 开启音效 + BGM
   await p.click('[data-au-tog="sound"]');await p.click('[data-au-tog="bgm"]');await p.waitForTimeout(250);
   const on=await p.evaluate(()=>({sound:S.settings.sound,bgm:S.settings.bgm,audioEl:!!audioEl,
     cur:curBgm,state:$('#auState').textContent.trim(),
     newAudio:window.__audioNew.length,btn:$('#btnAudio').textContent.trim()}));
   log('开启后',JSON.stringify(on));
   if(!on.sound||!on.bgm||!on.audioEl||on.cur!=='轻快')F('开启未生效',JSON.stringify(on));
   if(!on.btn.includes('🔊'))F('主面板未更新为开',on.btn);

   // 音量
   await p.locator('#auVol').fill('70');await p.waitForTimeout(150);
   const vol=await p.evaluate(()=>({v:S.settings.volume,txt:$('#auVolTxt').textContent,el:audioEl?.volume}));
   log('音量 70%',JSON.stringify(vol));
   if(Math.abs(vol.v-.7)>.001||vol.txt!=='70%')F('音量未写入',JSON.stringify(vol));

   // 曲目
   await p.click('[data-track="安静"]');await p.waitForTimeout(200);
   const tr=await p.evaluate(()=>({track:S.settings.bgmTrack,cur:curBgm,on:document.querySelector('[data-track="安静"]').classList.contains('on')}));
   log('切曲目 安静',JSON.stringify(tr));
   if(tr.track!=='安静'||tr.cur!=='安静'||!tr.on)F('曲目切换异常',JSON.stringify(tr));

   // 6 个试听
   await p.evaluate(()=>window.__sfxLog=[]);
   for(const k of ['water','block','quote','milk','end','bgm']) await p.click(`[data-try="${k}"]`);
   await p.waitForTimeout(200);
   const tries=await p.evaluate(()=>window.__sfxLog.slice());
   log('6 个试听调用',JSON.stringify(tries));
   // end 走 playClip('揭晓')、bgm 走 playClip(曲目)，会被二次记录，故按 kind 集合断言
   const need=['water','block','quote','milk','end'];
   if(!need.every(k=>tries.includes(k))||!tries.some(k=>k.startsWith('clip:')))
     F('试听未全部触发',JSON.stringify(tries));

   await p.click('#auDone');await p.waitForTimeout(200);
   // 刷新持久化
   await p.reload({waitUntil:'domcontentloaded'});await p.waitForTimeout(1500);
   const save=await p.evaluate(()=>({sound:S.settings.sound,bgm:S.settings.bgm,
     volume:S.settings.volume,track:S.settings.bgmTrack,
     btn:$('#btnAudio').textContent.trim()}));
   log('刷新后音频设置',JSON.stringify(save));
   if(!save.sound||!save.bgm||Math.abs(save.volume-.7)>.001||save.track!=='安静')F('音频设置未持久化',JSON.stringify(save));

   // 关闭 BGM 应 pause 并清空
   await p.click('#btnAudio');await p.waitForSelector('#auState');
   await p.click('[data-au-tog="bgm"]');await p.waitForTimeout(200);
   const off=await p.evaluate(()=>({bgm:S.settings.bgm,audioEl:!!audioEl,cur:curBgm}));
   log('关闭 BGM',JSON.stringify(off));
   if(off.bgm||off.audioEl||off.cur)F('关闭 BGM 未停',JSON.stringify(off));
   await p.click('#auDone');
   await ctx.close();
 }

 // ===== 4) 音效钩子：仪表盘 + 剧场 =====
 {
   const {ctx,p}=await open(1440,900,SPY+`
     window.addEventListener('load',()=>{
       const _sfx=window.sfx; window.sfx=function(k,f){window.__sfxLog.push(k);return _sfx(k,f);};
     });`);
   // 先开启音效与音乐（用面板，用户手势）
   await p.click('#btnAudio');await p.waitForSelector('#auState');
   await p.click('[data-au-tog="sound"]');await p.click('[data-au-tog="bgm"]');
   await p.click('#auDone');await p.waitForTimeout(150);
   await p.evaluate(()=>window.__sfxLog=[]);

   // 切换形象 → switch
   await p.click('#avatarRow [data-av="cat"]');await p.waitForTimeout(120);
   // 喝水 → water；第二次 → block
   await p.click('.watergrid .btn[data-ml="250"]');await p.waitForTimeout(180);
   await p.click('.watergrid .btn[data-ml="250"]');await p.waitForTimeout(180);
   // 语录 → quote
   await p.click('#btnQuote');await p.waitForTimeout(600);
   // 奶茶自首 → milk
   await p.click('#btnSin');await p.waitForTimeout(2200);
   // 自首通知书会开一个模态，先关掉再继续
   if(await p.locator('#nClose').count()) await p.click('#nClose');
   await p.waitForTimeout(250);
   const l1=await p.evaluate(()=>window.__sfxLog.slice());
   log('仪表盘音效钩子',JSON.stringify(l1));
   for(const k of ['switch','water','block','quote','milk']) if(!l1.includes(k))F('仪表盘缺少音效 '+k,JSON.stringify(l1));

   // 剧场：开场 BGM / 拦截 / 结局
   await p.evaluate(()=>window.__sfxLog=[]);
   await p.click('#btnStory');await p.waitForTimeout(400);
   const bgmOn=await p.evaluate(()=>({el:!!audioEl,cur:curBgm,snd:$('#stSnd').textContent,bg:$('#stBgm').textContent}));
   log('剧场开场音频',JSON.stringify(bgmOn));
   if(!bgmOn.el||bgmOn.cur!=='轻快')F('开场 BGM 未起',JSON.stringify(bgmOn));
   // 剧场 HUD 快捷开关
   await p.click('#stSnd');await p.waitForTimeout(150);
   const hud1=await p.evaluate(()=>({sound:S.settings.sound,icon:$('#stSnd').textContent}));
   log('剧场 HUD 音效切换',JSON.stringify(hud1));
   if(hud1.icon!=='🔇')F('剧场 HUD 图标未同步',JSON.stringify(hud1));
   await p.click('#stSnd');await p.waitForTimeout(150);
   // 跳过打字机 → 枢纽
   const skip=async()=>{await p.locator('#stText').click({timeout:8000}).catch(()=>{});await p.waitForTimeout(180);};
   await skip();
   await p.locator('#stChoices .st-ch').filter({hasText:'接下这瓶大水'}).click();await p.waitForTimeout(250);
   await skip();
   await p.locator('#stChoices .st-ch').filter({hasText:'去工位'}).click();await p.waitForTimeout(250);
   await skip();
   // 拦截（仪表盘刚打过卡，仍在冷却）
   await p.locator('#stChoices .st-ch').filter({hasText:'吨一口'}).click();await p.waitForTimeout(250);
   await skip();
   const blocked=await p.locator('#stText').textContent();
   log('剧场拦截台词',blocked.includes('防作弊铁律')?'✓':'✗');
   await p.locator('#stChoices .st-ch').filter({hasText:'乖乖等一会儿'}).click();await p.waitForTimeout(250);
   await skip();
   // 结算 → 结局
   await p.locator('#stChoices .st-ch').filter({hasText:'今日结算'}).click();await p.waitForTimeout(250);
   await skip();
   await p.locator('#stChoices .st-ch').filter({hasText:'揭晓今日结局'}).click();
   await p.waitForSelector('#stEnd.show',{timeout:8000});
   const l2=await p.evaluate(()=>window.__sfxLog.slice());
   log('剧场音效钩子',JSON.stringify(l2));
   for(const k of ['block','end']) if(!l2.includes(k))F('剧场缺少音效 '+k,JSON.stringify(l2));
   const endBgm=await p.evaluate(()=>curBgm);
   log('结局 BGM',endBgm);
   if(endBgm!=='揭晓')F('结局未切揭晓曲',endBgm);
   // 音乐关闭时，结局也不该偷偷自动播放
   const noPlay=await p.evaluate(()=>{ S.settings.bgm=false; save(); bgm('揭晓');
     return {el:!!audioEl,cur:curBgm}; });
   log('音乐关时结局不自动播',JSON.stringify(noPlay));
   if(noPlay.el||noPlay.cur)F('音乐关时仍自动播放',JSON.stringify(noPlay));
   await p.click('#seHome');await p.waitForTimeout(200);
   await ctx.close();
 }

 // ===== 5) 375px 窄屏 + 音频面板 + 控制台错误 =====
 {
   const {ctx,p}=await open(375,812);
   const ov=await p.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
   log('375px 横向溢出',ov+'px'); if(ov>2)F('窄屏溢出',ov+'px');
   await p.click('#btnAudio');await p.waitForSelector('#auState');
   const lay=await p.evaluate(()=>{const b=document.querySelector('#modalBox');const r=b.getBoundingClientRect();
     return {sw:b.scrollWidth,cw:b.clientWidth,l:Math.round(r.left),rr:Math.round(r.right),win:innerWidth,
       gridCols:getComputedStyle(document.querySelector('.au-grid')).gridTemplateColumns,
       imgsOK:[...document.querySelectorAll('.au-grid img')].every(i=>i.complete&&i.naturalWidth>0)};});
   log('音频面板 375px',JSON.stringify(lay));
   if(lay.sw>lay.cw+2||lay.rr>lay.win+2||lay.l<-2)F('音频面板窄屏溢出',JSON.stringify(lay));
   if(!lay.imgsOK)F('窄屏图标未解码',JSON.stringify(lay));
   await p.screenshot({path:ROOT+'/大水计算器-合并版-音频面板-手机预览.png'});
   await ctx.close();
 }

 // ===== 6) 原有全链路回归（确认音频改造没碰坏旧功能） =====
 {
   const {ctx,p}=await open(1440,900);
   // 形象 4 选 1 + 外观
   for(const id of ['cat','bean','daily','drop']){
     await p.click(`#avatarRow [data-av="${id}"]`);await p.waitForTimeout(120);
     const r=await p.evaluate(()=>({av:S.avatar,on:$('#pet').classList.contains('art-on'),src:$('#petArt').getAttribute('src')}));
     const expect=id==='daily'?await p.evaluate(()=>avatarId()):id;
     if(r.av!==id)F('形象切换异常',id+' / '+JSON.stringify(r));
     if(expect!=='drop'&&!r.on)F('形象外观异常',id);
   }
   log('4 形象切换','全部通过');
   // 防作弊连点
   await p.click('.watergrid .btn[data-ml="250"]');await p.waitForTimeout(180);
   await p.click('.watergrid .btn[data-ml="250"]');await p.waitForTimeout(180);
   const n=await p.evaluate(()=>today().logs.filter(l=>l.type==='water').length);
   log('防作弊连点后记录',n); if(n!==1)F('防作弊失效',n);
   // 分享卡
   await p.click('#btnShare');await p.waitForSelector('#scImg');
   const card=await p.evaluate(()=>({png:$('#scImg').src.startsWith('data:image/png'),
     w:$('#scImg').naturalWidth,h:$('#scImg').naturalHeight,code:$('#scCode').textContent.trim()}));
   log('分享卡',JSON.stringify(card));
   if(!card.png||card.w!==640||card.h!==960||!/^DW-[A-Z0-9]{6}$/.test(card.code))F('分享卡异常',JSON.stringify(card));
   await p.click('#scShut');
   // 排行榜徽章 + 横幅
   await p.click('#btnBoard');await p.waitForSelector('#scList');
   const medals=await p.locator('#scList .sc-medal').count();
   await p.locator('#scWrap [data-bt="all"]').click();await p.waitForTimeout(220);
   const banner=await p.locator('.sc-banner').count();
   log('排行榜奖牌 / 横幅',medals+' / '+banner);
   if(banner!==1)F('历史总榜横幅缺失',banner);
   await p.click('#scClose');
   // 设置面板新增 BGM 开关 + 音频面板入口
   await p.click('#btnSet');await p.waitForSelector('#setAvatars .chip');
   const set=await p.evaluate(()=>({bgm:!!document.querySelector('[data-tog="bgm"]'),
     entry:!!document.querySelector('#sAudioPanel'),avatars:document.querySelectorAll('#setAvatars .chip').length}));
   log('设置面板',JSON.stringify(set));
   if(!set.bgm||!set.entry||set.avatars!==4)F('设置面板结构异常',JSON.stringify(set));
   await p.click('#sCancel');
   // 剧情序章仍可开
   await p.click('#btnStory');await p.waitForTimeout(350);
   const st=await p.evaluate(()=>({show:$('#storyLayer').classList.contains('show'),
     hud:$('#stHud').textContent.includes('剧场')}));
   log('剧情层',JSON.stringify(st));
   if(!st.show||!st.hud)F('剧情层异常',JSON.stringify(st));
   await p.click('#stClose');
   await ctx.close();
 }

 console.log('\n=== 巡检汇总 ===');
 console.log('发现项:',findings.length);findings.forEach(([k,v])=>console.log('  ·',k,'→',v));
 console.log('控制台错误:',errs.length);errs.forEach(e=>console.log('  ·',e));
 await browser.close();srv.close();
 process.exit(findings.length||errs.length?1:0);
})().catch(e=>{console.error('FATAL',e);if(browser)browser.close();srv.close();process.exit(2)});
