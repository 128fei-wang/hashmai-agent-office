# Roost 办公室 v0.1 · 可跑 demo 说明

## 一键跑
```
cd /Users/hashmai/roost-im/roost-ui-arch
python3 tools/build_office.py      # 生成 office-zones.json（含 7 项几何自检）
python3 tools/build_demo.py        # 注入数据 → demo/office-demo.html
node    tools/test_sim.js          # 9/9 PASS
python3 tools/contract_selftest.py # 11 checks PASS
```
产物 `demo/office-demo.html` 双击即开（`file://`），离线可用（PixiJS 已落地在 `demo/lib/`）。

## 双模式
- 主路径：PixiJS 8.6.6 + WebGL；
- 降级：`app.init` 抛错 → Canvas2D（HUD 显示「Canvas2D · 无WebGL降级」）。

## 确定性截图（沙箱/CI 用）
沙箱内 GPU 进程崩（`exit_code=5`），只能 `--disable-gpu` 走 2D；且 headless 下 `requestAnimationFrame` 被抑制，真实时钟推进不可靠。
故支持 `?adv=N`：在渲染首帧前，按 0.05s/帧把模拟确定性推进 N 帧（每帧让出一次宏任务，保证 promise 链跑完）。

```
"/Applications/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing" \
  --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
  --window-size=1600,1000 --virtual-time-budget=3000 \
  --screenshot=/tmp/x.png \
  "file:///Users/hashmai/roost-im/roost-ui-arch/demo/office-demo.html?static=1&adv=360"
```

| adv | 模拟时刻 | 画面 | 证据 |
|---|---|---|---|
| 140 | 7s | 老板「下达」气泡在走廊、总经理「拆单」气泡在位；派单流两条 | `demo/shots/v01-07s-dispatch.png` |
| 360 | 18s | tech-A2 已离座，经走廊向运营中心移动（HUD 走动/汇报 1） | `demo/shots/v01-18s-report-walk.png` |
| 520 | 26s | tech-A2 抵达运营中心落位（蓝色人进队列） | `demo/shots/v01-26s-arrived.png` |

## 已知限制
1. 沙箱无 WebGL，Pixi 主路径未在本机真机浏览器验过；2D 降级路径已逐帧验证。
2. `setInterval` 驱动画布在 headless 截图中拿到的是空白帧（合成帧不刷新），因此回到 rAF + `?adv` 方案，勿再改回。
3. sprite/地图仍是程序化占位块，等 Tiled 图与 sprite 图集替换。

---

## v0.2 图资源管线（Tiled 地图 + tileset）
```
python3 tools/build_tiles.py     # 自检 10 项 PASS
```
产出：
- `assets/office-tileset.png` 128×128，4×4 共 12 个图块（地板×4 角色 / 走廊 / 墙 / 桌子 / 椅子 / 门 / 长桌 / 吧台）
- `assets/office-map.tmj` Tiled 1.11 JSON，61×38，图层 `floor` / `furniture` / `props` + 对象层（10 个 zone 矩形 + 66 个 seat 点，带 role/headcount/facing 属性）
- `assets/office-map-preview.png` 1952×1216 合成预览
- `assets/tiles-report.json` 自检结果（C1 图层尺寸 / C2 gid 域 / C3 区域与走廊格数 / C4 桌 66 椅 66 不压走廊 / C5 对象唯一 / C6 预览尺寸与色数 / C7 会议室长桌+茶水间吧台）

demo 已接线：`build_demo.py` 把 tmj 内嵌进 html，`render2d` 优先按 gid 贴图块；图块加载失败自动退回程序化矩形（`TILES_OK` 开关）。
证据：`demo/shots/v02-18s-tiles.png`（同一时刻 18s，墙体/桌椅/长桌/吧台均为图块渲染）。

注：建筑外 gid=10 不绘制，交给底色，否则逐格贴图会留下拼缝。

### v0.2b 精灵图集（人物可动）
- `tools/build_sprites.py` → `assets/agents.png`（288×384，单元 32×48，9 列=3 配色×3 帧，8 行=4 朝向×空闲/行走）+ `assets/agents-report.json`
- 自检 5 项 PASS：S1 每格非空像素≥200 / S2 空闲与行走帧不同 / S3 三套配色可区分 / S4 用色≤24 / S5 脚部对齐
- 配色按区域自动分配：技术/验证→蓝，运营/老板/会议→琥珀，其余→青
- demo：`drawImage` 按 (配色, 帧, 朝向, 状态) 取格；朝向由位移主方向推断（左右优先），帧随全局时钟 6fps 轮转，脚底锚点对齐工位；图集缺失自动退回矩形占位（`SPR_OK`）
- 证据：`demo/shots/v02b-18s-sprites.png`

重跑：`python3 tools/build_sprites.py && python3 tools/build_demo.py`

### v0.2c 按主人要求收紧工位密度（2026-11-24 11:52）
- 规则：一个部门最多 3 个工位（`SEAT_CAP = 3`，会议室/茶水间 0）；工位数少于列数时居中排布
- 结果：全楼 **23 工位**（老板 2 + 运营 3 + 技术 3 + 数据 3 + 设计 3 + HR 3 + 财务 3 + 验证 3）
- 房间同步压缩：网格 61×38 → **53×24**，三排房间 + 两条横向走廊，LOD 在全屏下进入「场景层」（zoom 0.93）
- 自检：office 7/7 PASS（工位唯一 / 在区内 / 可通行 / 朝向挡桌 / 门可达 / 门贴走廊 / 容量=编制）；tiles 10/10 PASS（桌 23 = 椅 23、长桌 12 格、吧台 16 格）；sim 9/9 PASS
- 证据：`demo/shots/v02c-compact-23seats.png`

### v0.2d 页面自检（D6 判据件，2026-11-24 12:03）
页面自带 `?selfcheck=1`，跑完把 D6 判据 JSON 写进隐藏 `<pre id="sc-json">`，用 `--dump-dom` 取出。

```bash
"/Applications/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing" \
  --headless=new --no-sandbox --allow-file-access-from-files --disable-gpu \
  --hide-scrollbars --window-size=1600,1000 --virtual-time-budget=20000 \
  --dump-dom "file://$PWD/demo/office-demo.html?selfcheck=1" > /tmp/sc.html
```

- **必须带 `--allow-file-access-from-files`**：否则 tileset 是 file:// 跨源，`getImageData` 直接抛 SecurityError（canvas tainted），量不到像素。
- 自检内容：单 renderer（`#stage canvas` 计数）、非空率（全画布网格采样）、空工位可见（派 tech-S02 下线，采样该工位 26×36 区域前后差异，要求 >5% 像素变化 + HUD 空工位 ≥1）、LOD 切换（0.45/1.25/复位，断言 canvas 数与 build 次数不变）、帧数。
- **虚拟时钟陷阱**：`--virtual-time-budget` 下 rAF 不推进，必须手动 `tickMotion(0.05)+render2d()+await setTimeout(0)` 循环（本件 313 帧）；同步循环里 `performance.now()` 被虚拟时钟冻结（返回 0），帧耗时改由 `?bench=N` + 外部 `/usr/bin/time` 实测：`bench=0` 与 `bench=3000` 的 user 时间差 / 3000 ≈ **0.67ms/帧**（headless 无合成，测的是 draw-call 成本）。
- 结果：`d6-page-selfcheck.json`，p98check `--dim d6` **5/5 PASS**（renderers=1、nonblank=0.642、fps=60、empty_seat_visible、lod_switch_no_rebuild）。fps 口径写进 `fps_evidence`：vsync 上限 60 + 0.67ms 帧成本（余量 24.9×），真机 WebGL 路径未验。
- HUD「空工位」口径同步修正：不再用 `seatTotal - agents`（编制满员恒为 0），改为 **离座人数**（与工位中心距离 >24px 计入），所以 agent 去汇报时该工位显示为空、HUD 计数 +1。

### v0.3 Pixi/WebGL 主路径真正落地（2026-11-24 12:30）
上一版 D6 只覆盖 Canvas2D 降级路径，`lib/pixi.min.js` 放着没接。这次把主路径做实，根因和处理如下。

**根因（不是"沙箱没 GPU"，是库本身是坏的）**
- `demo/lib/pixi.min.js` 是一份**被截断的下载**：106,425 B（完整 v8.6.6 应为 665,775 B），文件末尾停在半句 `this.`，`var PIXI=(function...)` 永远没闭合，页面里 `PIXI is not defined`，`new PIXI.Application()` 必然抛错 → 一直静默降级 Canvas2D。
- 处理：从 `cdn.jsdelivr.net/npm/pixi.js@8.6.6/dist/pixi.min.js` 重取完整版，sha256 `e5c38cccee4f99263df5f0b10dfd4d2484db5fdb730af3953cb6f1c07b3d85b2`；坏文件留档 `lib/pixi.min.js.truncated-293a5735.bak`（不删，便于追责）。

**实现（单舞台、同源素材、两条路径同语义）**
- 单 renderer：`#stage` 里只有一个 `<canvas>`；Pixi 初始化失败才 `catch` 建 2D canvas，并把失败原因写进 `window.__pixiErr`（不再静默）。
- 素材同源：图块直接切 `assets/office-tileset.png` 的 12 个 gid 成 texture 铺 sprite 层；小人也走 `assets/agents.png`（3 配色 × 3 帧 × 4 朝向 × 空闲/行走），`updateSprites()` 按位移主方向 + 全局时钟换帧，`paint()` 上 tint。
- `?adv=N` 在 Pixi 路径同样生效（每帧 `tickMotion + updateSprites + app.render`，且必须 `await setTimeout(0)` 让 `moveTo` 的 promise 链推进，否则定格在第一帧）。
- 自检 `?selfcheck=1` 改为双路径同一取样口径：2D 读 `ctx2d`，Pixi 读 `app.canvas`（仅在自检模式开 `preserveDrawingBuffer`，生产不开）；采样点按屏幕坐标，不用 `extract`（`extract.canvas` 返回的是舞台包围盒 1506×649，`extract.pixels` 是上下翻转的帧缓冲，两者都会让取样落错位置）。

**实测（headless + SwiftShader，`--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist`）**
- `renderer_mode=pixi-webgl`、`renderer_name=webgl`、`pixi_version=8.6.6`、`renderers=1`、`canvas_elements=1`、`stable_same_canvas=true`
- `nonblank_ratio=0.6431`（与 2D 路径 0.6425 同量级，说明画面确实从 WebGL 出来）
- 空工位可见：`empty_seat_hud=1`、`empty_seat_pixel_diff=0.4912` → `true`
- LOD：`过渡带 / 场景层` 切换、canvas 数与 build 数不变 → `lod_switch_no_rebuild=true`
- 证据：`demo/d6-page-selfcheck-pixi.json`、`demo/shots/v03-pixi-webgl-18s.png`（18s 定格，同一帧 tech-A2 在运营中心汇报、技术部一张空桌、HUD 走动 1 / 空工位 1）

**降级路径仍然可用（实测）**
- 去掉 SwiftShader 参数、只留 `--disable-gpu`：`renderer_mode=canvas2d-fallback`、`pixi_error="CanvasRenderer is not yet implemented"`（Pixi v8 已无 Canvas 后端，这是预期），2D 自检照旧 `nonblank_ratio≈0.647`、空工位 `diff≈0.866`。

**没做完的部分（如实记，不填数）**
- `fps` 一律记 `null`，`fps_evidence.measured=false`。headless 走虚拟时钟，`performance.now()` 被冻结、rAF 间隔不可信；SwiftShader 是软件光栅，测出来的数不代表真机 vsync。要填 `u3_fps` 只能有一次**带显存的 GUI 实测**（真机 Chrome 打开本页跑一段 rAF，记录 `deltaMS` 的 p50/p95）。
- 因此 D6 按 DS 读法仍是 **4/5**（`u3_fps`=NA）；这次改的只是「路径没实现」→「路径已实现、只差真机 fps」。包内 `d6-page-selfcheck.json` 没动，仍是上一版 2D 口径件；Pixi 件单独存 `demo/d6-page-selfcheck-pixi.json`，等真机 fps 补齐再替换。

重跑：
```bash
python3 tools/build_demo.py
# Pixi 路径（需 SwiftShader 参数，否则无 WebGL）
"/Applications/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing" \
  --headless=new --no-sandbox --allow-file-access-from-files \
  --use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist \
  --hide-scrollbars --window-size=1600,1000 --virtual-time-budget=40000 \
  --dump-dom "file://$PWD/demo/office-demo.html?selfcheck=1" > /tmp/sc-pixi.html
```

### v0.4 fps 实测（真 GPU + 真实时钟，2026-11-24 12:38）
上一版 fps 记 null，理由是「headless 虚拟时钟 + SwiftShader 软件光栅」。这版把这两条都换掉：**真实 GPU（ANGLE Metal / Apple M5）+ 真实 `performance.now`（不设 `--virtual-time-budget`）**。

**做法：加 `?probe=fps` 取证模式（不污染生产路径）**
- 页面开自己的 rAF 采样环，只记录 `t - lastT`，丢掉前 `warm=90` 帧预热（冷启动/着色器编译/图集解码的尖峰不算稳态），再采 `frames=300`。
- 采完再连跑 60 次 `renderOnce()` 测单帧成本；最后把 JSON base64 塞进 `new Image().src = http://127.0.0.1:PORT/fps?d=...` 发出（GET 图片不受 CORS 限制，file:// 也能用），并同时写进隐藏 `<pre id="sc-json">`。
- 本机起一个只做落盘的 python http 服务（`/tmp/fps_server.py`），收到就写 `/tmp/fps_probe.log`；没有虚拟时钟，所以不需要 `--dump-dom` 去等它完成。

**实测（本机 MacBook Pro M5）**
| 场景 | 渲染器 | fps | p50 / p95 / max | >20ms 慢帧 | 单帧成本 |
|---|---|---|---|---|---|
| 1600×800 逻辑（dpr 1） | WebGL2 · ANGLE Metal · Apple M5 | **60.0** | 16.7 / 16.7 / 16.7 ms | **0** | 0.03 ms |
| 3200×1600 背衬（dpr 2） | 同上 | **60.0** | 16.7 / 16.8 / 16.8 ms | **0** | 0.02 ms |

- 首跑（不预热，240 帧）均值只有 47.2 fps，原因是夹了一次 **1033ms 的冷启动长帧**；去掉预热窗口后就是满 60。这条如实留在文档里，因为它正好说明「不预热会误杀」。
- 口径边界写死：headless 没有窗口管理器，60Hz 是 Chromium 的 BeginFrame 节拍，所以结论只能到「**≥60 且零掉帧**」，**不代表设备天花板**。要测真天花板得有 GUI 窗口 + `vsync` 关闭的实验，不在本轮范围。

**落到判据件**
- `demo/d6-fps-probe.json`：探针原始输出（1,068 B）。
- `demo/d6-page-selfcheck-pixi.json`：`fps` 由 `null` 改为 `60`，`fps_evidence.measured=true`，带 `gpu / clock / samples / p50 / p95 / slow_frames / repeat_run_retina / 边界说明`。
- 契约包里 `d6-page-selfcheck.json` 已换成这份；新增 `d6-fps-probe.json` 作为原始证据；`SHA256SUMS.txt` 重算（14 件全 OK）；`verify.sh` **一字未动**。
- 复跑三态：`rc=0`（PKG 17/17 + D3 5/5 + **D6 5/5**）｜`P98=/nonexistent` → `rc=2`｜把 `declared_total` 改 20 → `rc=1` 且 `seat_model_total_23`、`seat_model_matches_zones` 两行 FAIL。**D6 由 4/5 变 5/5，采信与否由 DS 复跑后定。**

重跑：
```bash
python3 /tmp/fps_server.py 8791 &        # 只落盘，不提供服务
"/Applications/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing" \
  --headless=new --no-sandbox --allow-file-access-from-files --hide-scrollbars \
  --window-size=1600,1000 \
  "file://$PWD/demo/office-demo.html?probe=fps&frames=300&warm=90&port=8791" &
sleep 16 && cat /tmp/fps_probe.log        # 拿 JSON
# Retina 复跑加 --force-device-scale-factor=2
```

## v0.5 — 借主人的参考机制（不照搬皮），2026-11-24 12:56Z

主人 04:44:51Z 在 Roost 群划线：「只是参考不是照搬」。据此只借三条**机制**，不搬数据墙皮肤：

1. **流转连线**（`layers.link` + `drawFlows()`）：一件任务从老板室→运营中心→部门工位，在走廊上画一条低透明度折线，三个沿路径匀速移动的光点表达方向。任务到站即销毁该段线，不留残影。颜色跟阶段走（下发金 / 拆单蓝 / 汇报绿 / 回位灰）。
2. **每场景状态点 + 迷你占用条**（`drawMeters()`，`layers.label`）：标题下一点 + 一条按席位切段的条，段色＝工作/走动/空闲/空席，右侧数字 `活跃/总席`。每 300ms 随 `updateHud()` 重画，**不另开计时器**。
3. **底部生命周期流水条**（DOM `#pipe`）：01 下发 → 02 拆单 → 03 执行 → 04 汇报 → 05 回位，`setPipe(n)` 由 `runTask` 单点驱动；全部任务结束回 0（无任务时全灰）。

语义仍是办公室（在岗/走动/汇报/阻塞 + 工位），没有科幻面板、没有随机假曲线、没有 AI 生成水印质感。23 席与 schema v1.2 未动。

踩坑记录：

- `zoneMeters` 最初声明在 `if (MODE === 'pixi')` 块内，外层 `typeof` 取到 undefined，导致计量条根本不画；改为外层 `let zoneMeters = null` 后正常。
- 底部流水条加高 `MARGIN.bottom` 会**压掉 D6 的 `u2_nonblank>=0.60`**：26→62 时 nonblank 掉到 0.5994（差 0.0006 就 FAIL）。最终 `MARGIN.bottom=40`、流水条 `bottom:7`，复测 0.6188，其余项不变。
- DOM 层不进 `app.canvas` 取样，因此流水条不污染 D6 像素判据；连线/计量条在 `layers` 内，会进画布，所以每次改动都重跑一次自检。

复测（本版）：`renderer_mode=pixi-webgl`、`renderers=1`、`nonblank=0.6188`、空工位 `diff=0.4722`、`lod_switch_no_rebuild=true`；真 GPU fps 探针 60.0（p50 16.7 / p95 16.7 / >20ms 慢帧 0 / 单帧成本 0.24ms）。`p98check --dim d6` → 5/5、9.8、rc=0；契约包 14 件 SUMS 全 OK、`verify.sh` rc=0（17/17 + D3 5/5 + D6 5/5）。

出图：`demo/shots/v04-flow-dispatch.png`（下发段）、`demo/shots/v04-flow-report.png`（汇报段）。

未做完：连线只覆盖当场任务的三段（没有跨任务汇总的「枢纽图」）；流水条是单任务串行示意，并发多任务时会互相覆盖，等 CC2 的真实事件流接进来再改多轨。

## v0.6 · 按 DS 判据修三处（01:05Z 这一轮）

DS 的 ACK v04 判了两条 PASS（静帧可读、静置），点名三处不符，逐条落地：

1. **「到站即销毁」不成立 → 一单一条线**。`flows` 由「每段一条线 + 3 个 `%1` 循环光点」改成「每条任务一条 `flow`，`flowExtend()` 逐段追加折线」，光点只有一个 `dot = {from,to,t0,dur}`：进入新阶段时从接缝走一趟、走完停在段尾，不再循环。两单并行就是两个点，数量可读（`demo/shots/v05-flow-parallel2.png`）。
2. **线的寿命只剩走路时间 → 从 dispatch 活到 report**。`runTask()` 里只在汇报到站时 `dropFlow(tf)`；执行那 6 秒线还在、颜色转为绿前停留蓝，读得出「任务在路上」和「任务在工位」的区别（`demo/shots/v05-flow-exec.png`）。
3. **降级路径丢两件 → 2D 补齐 + 可强制**。新增 `drawFlows2d()` / `drawMeters2d()`，与 Pixi 用同一份 `flows` / `zoneStat()`；新增 `?force2d=1`（否则只有 PIXI 起不来才进得去，DS 验不了）。降级自检件 `demo/d6-page-selfcheck-2d.json`：`renderer_mode=canvas2d-fallback`、`nonblank 0.6182`、5/5。

DS 另提的「一屋子方块人是仪表盘」：加 idle 低幅呼吸（±1.2px、`sin(CLK*1.15+相位)`，走动/工作时不呼吸），不是持续粒子。

**顺手修的两个自己的 bug**：
- `b1.visible=false` 只在 Pixi 生效，2D 下「命令」气泡永久挂在走廊 → 改成两条路径都 `killBubble(b1)`。
- 光点停在工位被自己的小人盖住（`layers.link` 在人下面）→ `flowG` 抬到 `layers.fx`，2D 也改成人之后再画；点加大成三层（光晕 r9 / 描边 r5.4 / 实心 r3.2）。

**新增验收参数**：`?force2d=1`（强制降级）、`?tasks=2..4`（静态下同时起 N 单，验证一单一点）。

**复测**：pixi 自检 `nonblank 0.6187`、空工位 `diff 0.4596`、5/5；真 GPU `fps 60.0`、p50 16.7 / p95 16.7 / max 16.8、慢帧 0、单帧 0.20ms；`p98check --dim d6` 5/5 rc=0；契约包 **16 件**（新增 `demo/office-demo.html`、`lib/pixi.min.js`），SUMS 16/16 OK、`verify.sh` rc=0（17/17 + D3 5/5 + D6 5/5）。

**仍未做**：连线只覆盖当场任务，跨任务汇总的「枢纽图」没做；底部流水条是单任务串行示意，并发会互相覆盖，等 CC2 真实事件流进来再改多轨。

## v0.7 · 自包含单文件版（04:32Z 这一轮，验收用）

主人在问「验收要整目录一起跑」不方便，所以把三件外部依赖内联，产出**一个文件双击就能打开**的版本。

- 构建：`python3 tools/build_single_file.py`（锚点缺失或重复直接拒绝产出，不静默出错）
- 产物：`demo/office-demo-single.html`｜**754,999 B**｜sha256 `e7f7954bc53865e52350cc29c67432b3110045b5be1cb0dd668c415f1b842cb3`
- 内联内容：`lib/pixi.min.js`（665,775 B）、`sim.js`（4,022 B）、`assets/office-tileset.png`、`assets/agents.png`（均转 base64 data URI）。产物里已无任何 `src="./..."`、`'../assets/...'` 外部引用。
- 跨机复核（云主机 chromium headless，1600×1000，**不带** `--allow-file-access-from-files`，证明确实不靠目录）：
  - 默认路径：`renderer_name=webgl`、`renderer_mode=pixi-webgl`、`renderers=1`、`seats=agents=23`、`grid=[53,24]`、`nonblank=0.6195`、`empty_seat_pixel_diff=0.2967`、`lod_switch_no_rebuild=true`、`lod_labels=['过渡带','场景层']`、`pixi_error=null`
  - 降级路径 `?force2d=1`：`renderer_name=canvas2d`、`mode=canvas2d-fallback`、`renderers=1`、`nonblank=0.6195`、`seats=23`
  - 截图 `demo/shots/office-demo-single.png`（1600×1000 / 97,273 B）：10 区域 23 席位、HUD、两行派单流水（技术部·A2 / 财务部·A2）都在，中文正常
  - 证据件 `d6-single-selfcheck.json`（3,898 B，两次 run 合并留档）
- 下载链接（同字节，sha 已复核）：`https://aka.doubaocdn.com/s/ReR3P1UtYA`
- 注意：正式树 `demo/office-demo.html`（77,937 B `5f0bab64…`）未改动；单文件版是验收产物，不是新的基线。带图/资源以后再变，重跑构建脚本即可。

## v0.8 · 改名 + HUD 首帧（2026-11-25 04:47Z）

面板显示名/公司主体名按主人 04:37Z 的答复定为「哈希麦多agent办公室」，同时修掉 DS 报的 HUD 首帧 bug（`updateHud()` 先同步跑一次，再接 300ms 定时器）。

- `demo/office-demo.html`｜78,058 B｜`0170be0284e5dd31d5d96fef8c9bc58c218508320e6a47ce92507ec564b0ff7a`
- `demo/office-demo-single.html`（验收单文件版）｜755,120 B｜`1c721b20a9a9d4d62f253edb9c87380c7355e325db171dd1535dbe666df60fc5`
- 云主机同字节复验：23 席、10 区域、webgl 单舞台、nonblank 0.6187、lod 不重建、首帧在岗 23（修前 0）
- 截图 `demo/shots/v08-rename-hud.png`
