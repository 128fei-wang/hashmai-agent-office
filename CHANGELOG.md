## v0.10 (2026-11-25 · 待发版)

- **MOCK 标注重建**：流水条右下角三行固定标注（任务流水 / MOCK 模拟事件 / 来源：页面内预置演示脚本），防止把演示数据误读为真实遥测。重建后产物：
  - `demo/office-demo.html` → **78,485 B** · `a96bad44fbbe6c3f7a0786fdcac8bc3a6c89f7b7399939b9b4f96041adbc8e27`
  - `demo/office-demo-single.html` → **755,547 B** · `e84075267f45e234d79587d16ae3dbabe2cba51516ec6e6ff23cc4467df964dc`
  - 均可由 `tools/build_demo.py` / `tools/build_single_file.py` 从模板逐字节复现。
- **契约入树**：`CONTRACT-01.md` 盖入 v1.2 定稿（8,183 B · sha256 `a1c031148a037569f52942ad488925c816dd6c94e904d27a23ed7427ec2ad536`），信封 `v/seq/ts(epoch ms)/kind` 不动，只增 5 事件 / 3 状态 / 2 snapshot 字段。
- **D6 证据件换当前基线**：`D6-FPS-EVIDENCE.md` 由「历史 `0170be02` 待替换」改为三分结构（当前 `a96bad44` 60.0 fps / 历史 0170be02 / 自我限定）；fps 与 p5x 一律取 DS canonical `d6-fps.json`（`56c5b0dc…f3249`，1600×800、慢帧 0）。
- **已知未补齐**：`tools/contract_selftest.py` 在干净 clone 下 `schema_validated` 为 `ok:true` 但 `detail=SKIP`（jsonschema 未装），12 条里 1 条空过 —— 不得计作「schema 校验通过」，待换零依赖校验器。

## v0.9 (2026-11-25)

- 对外显示名定为 **RoostOffice**：`demo/office-demo.template.html` 两处旧名（`<title>` 与 HUD 面板名）改为 `RoostOffice`；README / README.en / `package.json` 同步。
- 重建产物（**已被 v0.10 重出覆盖**）：`demo/office-demo.html` 78,028 B · `d30c99ee…46e5` → 现 78,485 B · `a96bad44…8e27`；`demo/office-demo-single.html` 755,090 B · `b9e84d50…477e` → 现 755,547 B · `e8407526…64dc`。
- 契约 §5/§6 重写：仓库内原件与契约包内原件分列；自验入口拆成「clone 后零依赖 `tools/contract_selftest.py`」与「包内 `verify.sh`（需判据器，缺失 rc=2）」两条，标明依赖不同、不等价。
- 移除过程补丁 `PATCH-04-NAME.patch`；D6 证据件改名为 `D6-FPS-EVIDENCE.md`（v0.10 已将其更新为当前基线）。

# 更新日志（Changelog）

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 `MAJOR.MINOR.PATCH`（当前处于 0.x，API 与产物结构仍可能调整）。

## [Unreleased]

### 变更
- 许可证定为 **Apache-2.0**（原 MIT），补 `NOTICE`、同步 README / package.json / THIRD-PARTY-NOTICES。

### 计划
- 接真实事件流（store）替换模拟数据；点席位查看详情；30 秒回放；30/50 agent 渲染压测。
- `nonblank_ratio` 判据改为「固定视口 + 前置断言 viewport / cam」后再作为门槛。

## [0.8.0] - 2026-11-25

### 新增
- 产品显示名改为 **哈希麦多agent办公室**（页面标题与 HUD 面板名同步）。

### 修复
- **首帧 HUD 显示「在岗 0」**：HUD 原先只靠 `setInterval(updateHud, 300)` 驱动，
  进入页面后前 300ms 读到的是空值。改为在定时器注册前同步调用一次 `updateHud()`。
  首帧取证：修复前 `h-on=0`，修复后 `h-on=23`。

### 产物
- `demo/office-demo.html` → 78,058 B / `0170be02…`（模板 `8cfaddd1…`）
- `demo/office-demo-single.html` → 755,120 B / `1c721b20…`

### 验收
- 自检：`renderer_name=webgl`、23 席、`nonblank 0.6187`、LOD 切档不重建；
  强制 `?force2d=1` 走 `canvas2d` 正常。
- 第三方复测（WebGL2 / ANGLE Metal，1600×800）：60.0 fps、p50/p95/p99/max
  16.7/16.8/16.8/16.8 ms、慢帧 0。D6 五项全过。

## [0.7.0] - 2026-11-25

### 新增
- 任务流水条按工位**两行并排**，每条任务显示 `01→05` 步进。
- 工位牌编号与 `seat_id` 统一为同一套（`技术-S00/S01/S02`），修掉此前三套编号并存的问题。

### 校验
- `check_seat_ids.py --require-unified` rc=0：23 席 / 8 区 / 偏移 `[0]`。
- `test_sim.js` 9/9。

## [0.6.0] - 2026-11-24

### 新增
- 可机读自检：`?selfcheck=1` 在页面 `<pre id="sc-json">` 输出渲染/席位/网格/LOD 指标。
- **单文件验收版**：`tools/build_single_file.py` 把 PixiJS、`sim.js`、贴图内联为 data URI，
  锚点缺失或重复直接拒绝产出，产物末尾断言无外部引用残留。
- 跨机（macOS ↔ Linux 无头 Chromium）复验同一份产物，确认不依赖目录结构。

## [0.5.0] - 2026-11-24

### 新增
- 任务执行态与并行双线演示（`v05-flow-exec` / `v05-flow-parallel2`）。
- Canvas2D 降级路径完善：`?force2d=1` 全流程可用，作为 WebGL 不可用时的兜底。

## [0.4.0] - 2026-11-24

### 新增
- 派单与回报两条动线闭环（老板 → 运营中心 → 部门 → 回报）。
- LOD 分档：远景合并绘制，近景细节绘制；切档不重建场景。

## [0.3.0] - 2026-11-24

### 新增
- 渲染层由 Canvas 2D 切到 **PixiJS 8（WebGL）**，保持 Canvas2D 可回退。
- 内置 `demo/lib/pixi.min.js`（8.6.6），保证离线可用。

## [0.2.0] - 2026-11-24

### 新增
- 贴图集与角色精灵生成脚本（`build_tiles.py` / `build_sprites.py`），替换占位色块。
- 地图压缩到 53×24 / zoom 0.93，23 工位在 1600 宽的视口内不重叠。

## [0.1.0] - 2026-11-23

### 新增
- 首个可跑版本：办公室地图、10 个区域、23 个工位、基础 HUD。
- 地图数据 `TMAP` 内联、可行走格与寻路网格生成（`build_office.py`）。

[Unreleased]: https://github.com/128fei-wang/hashmai-agent-office/compare/v0.8.0...HEAD
[0.8.0]: https://github.com/128fei-wang/hashmai-agent-office/releases/tag/v0.8.0
[0.7.0]: https://github.com/128fei-wang/hashmai-agent-office/releases/tag/v0.7.0
[0.6.0]: https://github.com/128fei-wang/hashmai-agent-office/releases/tag/v0.6.0
[0.5.0]: https://github.com/128fei-wang/hashmai-agent-office/releases/tag/v0.5.0
[0.4.0]: https://github.com/128fei-wang/hashmai-agent-office/releases/tag/v0.4.0
[0.3.0]: https://github.com/128fei-wang/hashmai-agent-office/releases/tag/v0.3.0
[0.2.0]: https://github.com/128fei-wang/hashmai-agent-office/releases/tag/v0.2.0
[0.1.0]: https://github.com/128fei-wang/hashmai-agent-office/releases/tag/v0.1.0
