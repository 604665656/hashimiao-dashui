# 大水计算器 · 合并版（桌宠 + 哈士喵剧场）

> 弱者喝饮料，强者喝大水。

单文件 HTML：桌宠仪表盘 + 哈士喵剧情剧场 + 可切换虚拟形象，一份数据两种视图。
成品就是根目录 `index.html`。

## 在线玩

- **GitHub Pages（已上线，现在可玩）**：https://604665656.github.io/hashimiao-dashui/ （HTTP 200，返回内容与本仓 `index.html` 逐字节一致）
- **B站 TOY（已上线）**：https://www.bilibili.com/toy/hashimiao-dashui/index.html — id `54285278645248`，2026-11-12 提交，同日复审后 `published`
- **源码仓库**：https://github.com/604665656/hashimiao-dashui （commit `4564f3d`，55 文件）

## 合并口径

之前是两个独立文件：

- `大水计算器.html` —— 桌宠仪表盘版
- `大水计算器-哈士喵AVG.html` —— 剧情互动版

本版合成一个文件、一份数据、两种视图，虚拟形象做成可切换选项（💧 大水滴 / 🐱 哈士喵 / 🫧 小水滴酱 / 🎲 每日轮换）。
数据沿用 `dashui.pet.v1`；启动时对 `dashui.avg.v1` 做一次**只补不覆盖**的安全合并（饮水流水、结局解锁、CG 解锁），并打标记防重复。

## Toy 形态适配

- **能力探测**：`window.toy` / `studio.sdk.toy` / `ToySDK` / `bl` 四种形态 duck typing，`available()` 与 `ready()` 带超时（1200+800ms）和一次短重试
- **静默降级**：探测不到 / 未授权 / 超时 → `mode='local'` 或 `degraded`，本地形态完全离线可玩
- **云存档**：只放白名单最小可重建摘要，分片 `ds_meta` + `ds_0…`（≤900B / 片）
- **永不上云**：抓拍照片、完整流水、API Key / endpoint、精确 GPS、通知 / 摄像头授权状态、完整语录上下文
- **平台分数榜**：只在 Toy 形态出现，玩家点击授权后才 `rank.submit({score, extra:{at, rule:2}})`；界面明确「客户端休闲成绩展示，非官方认证、无服务器反作弊」
- **榜单双轨**：平台分数榜 + 本机多档案榜；身份用平台用户资料，不自建账号

## 网络边界（实测，重要）

源码共 3 处 `fetch(`，逐处核对如下：

| # | 调用 | 目标 | 默认是否触发 |
| --- | --- | --- | --- |
| 1 | `fetch(png)` | `drawShareCard()` 产出的**本地 data URL**，用于系统分享 | 仅玩家点「系统分享」，非网络请求 |
| 2 | `fetch(u)` | `https://api.open-meteo.com/v1/forecast` 天气 | **是**：启动链 `init()` → `initLocation()` → `applyLocation()` → `fetchWeather(true)`，另有 30 分钟轮询；7s `AbortController` 超时，失败静默降级为「（离线，手动设定）」 |
| 3 | `fetch(cfg.endpoint + '/chat/completions')` | 可选在线大模型语录 | **否**：`llm.endpoint` / `llm.key` 默认均为空字符串，需玩家自行填写且 `if(cfg.endpoint && cfg.key)` 才发 |

补充：

- 定位走 `navigator.geolocation` + **内置本地区县表** `geoNearest()`，不请求第三方定位服务
- 定位失败（Toy iframe 常见）会弹「选择你所在的位置」引导，可点「先用默认位置」跳过，不影响可玩性
- 全文件唯一的外部域名是 `api.open-meteo.com`；`http://www.w3.org/2000/svg` 只是 SVG namespace
- **零外链资源**：0 个 `script[src]`、0 个 `link stylesheet`、0 个 `http(s) src/href`；零 CDN、零追踪
- 若 Toy 容器 CSP 拦截天气请求，游戏自动降级手动天气，主体功能不受影响

## 技术规格（实测，非文档转述）

| 项 | 值 |
| --- | --- |
| 成品 | `大水计算器-合并版.html` |
| 体积 | 892,131 B = 871.2 KiB（< 1 MiB Toy 入口硬闸门） |
| SHA256 | `73e9b02f488b8fe12ce2b0de627f0232028b96580f5c25e52415a87ab00c37ad` |
| 一致性 | 交付 ZIP 内同名 HTML 与桌面单文件**逐字节一致** |
| 内联 script / style | 3 / 1 |
| 外部 script / stylesheet / http(s) 资源 | 0 / 0 / 0 |
| `fetch(` / `XMLHttpRequest` | 3 / 0 |
| 内嵌图片 | 62 处 `data:image` |
| `localStorage` | 15 处 |
| `node --check` | 3/3 PASS |
| `tools/verify.py` | 26/26 PASS |

### 文档数值差异（避免对外写错）

交付包说明写「产物 833.3 KiB、61 张内嵌 WebP + 4 段 ogg」，是**阶段性**数值。
当前成品实测 **892,131 B（871.2 KiB）**、`data:image` **62** 处、`fetch(` **3** 处。
对外文案一律以实测为准；`tools/verify.py` 已把 62 / 3 / sha256 固化成断言，防止后续改版误引入默认外联。

## 合规与边界

- 照片、饮水记录、心情、位置、档案与成绩、形象选择、剧情解锁、分享校验码**全部只存本机 localStorage**，不上传
- 云存档为 Toy 形态增量能力，走白名单最小摘要；未授权 / SDK 未就绪即静默回退本地
- 美术与音频素材来自交付包自有体系；Toy 封面 / 图标全部由交付包内官方预览 PNG 裁切合成，未臆造游戏画面
- Toy 入口 < 1 MiB，**单文件直传、未分包、未改动用户成品一个字节**

## 目录

```
index.html              GitHub Pages 可玩入口（与 Toy 入口逐字节一致）
.nojekyll
toy/index.html          B站 TOY 上传入口
toy/build_meta.json     构建元信息（含网络边界说明）
icon.png / poster.png   上架图标 / 1200×675 封面
tools/verify.py         26 项静态校验（含 3 处 fetch 边界）
交付包/                 用户原始交付包完整解包（cp437 中文名已恢复）
```

## 复现

```bash
python _prepare_new_games.py     # 工作区根目录：解包 + 校验 + 生成 Toy/Pages 入口
python _make_assets_new.py       # 用官方预览图生成封面 / 图标
python tools/verify.py           # 26 项断言
python tools/verify.py toy/index.html
```
