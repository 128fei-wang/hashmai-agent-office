# PATCH-03：任务流水条改「一单一行」，并发不再互相覆盖

状态：**副本验证通过，正式树未动**。与 PATCH-01／PATCH-02 无冲突，可同批（推荐顺序 P1 → P2 → P3，最后只 rebuild 一次）。

## 问题（不改会一直误导人）

`demo/office-demo.template.html` 的底部流水条是**全局单条**：`setPipe(n)` 直接 `querySelectorAll('#pipe .pnode')` 全量刷。两单并发时后一单从 `01 下发` 起步，会把前一单的 `03 执行` 打回去，肉眼看到的是「一直在 01/03 之间跳」；`if (!busyZones.size) setPipe(0)` 又在最后一单结束时把整条清空。连线（`flows`）本身是一单一线、支持并发，所以缺口只在流水条这一处。

## 改法（只改模板，146 行 diff / 6,527 B）

- CSS：`#pipe` 由单行 flex 改为 `align-items:flex-start` 的竖排容器，新增 `#pipe .prows`（列）、`#pipe .prow`（行）、`#pipe .ptag`（行首标签，宽 104px、超长省略）。
- HTML：`<div id="pipe">` 内不再硬编码 5 个 `pnode`，改为 `<div class="prows" id="prows"></div>`，行由 JS 建。
- JS：`setPipe(n)` → `pipeOpen(label)` / `setPipe(row, n)` / `pipeClose(row, delay)` 三件套，行状态挂在 `PROWS` 数组上：
  - `pipeOpen('技术部 · A2')` 建一行：标签 + 5 个 `pnode` + 4 个连接线，`data-active="1"`。
  - `setPipe(row, n)` 只动这一行的节点：`k<=n` 亮、`k===n` 高亮、`i<n` 连线亮。
  - `pipeClose(row, 1600)` 标 `data-active="0"` 并在 1.6s 后摘除，行随单来随单走。
- `runTask` 开头 `const row = pipeOpen(部门 + ' · ' + agent 编号)`，五处 `setPipe(n)` 改 `setPipe(row, n)`，结尾 `pipeClose(row)` 取代 `if (!busyZones.size) setPipe(0)`。

DOM 仍在画布外，不参与 D6 取样；行数上限天然等于并发单数（`TASKS` 最多 4）。

## 验证

| 项 | 结果 |
|---|---|
| `patch -p0 --dry-run` 打干净基线树 | rc=0 |
| 打 P1+P2 之后再打 P3（`--dry-run`） | rc=0，无 `.rej` |
| 基线+P3 `build_demo.py` | rc=0，`demo/office-demo.html` **76,679 B**（payload 6,311），template **52,630 B** |
| 基线+P3 `node tools/test_sim.js` | **PASS 9/9** |
| 基线+P3 `check_seat_ids.py` | rc=0，`seats=23 zones=8 fail=0`，A6 INFO `[1]`（未打 P1 即如此，符合预期） |
| P1+P2+P3 三补丁合演 `build_demo.py` | rc=0，html **77,937 B**，template **53,888 B** |
| 三补丁合演 `check_seat_ids.py --require-unified` | **rc=0，A6 偏移 `[0]`，`fail=0`** |
| 三补丁合演 `node tools/test_sim.js` | **PASS 9/9** |
| 行逻辑单测（Node + 桩 DOM，直接 eval 模板里那段真实代码） | 两行并存：r1 第 3 段 `now`、r2 第 2 段 `now`；r1 连线 1/2 亮、3/4 灭；`pipeClose` 后行摘除 |

单测复跑：`node /tmp/pipe_unit.js`（桩 DOM，无浏览器）。

## 未验证项（如实标注）

**没有视觉截图，也没重取 D6 证据。** 本机 headless Chrome for Testing 两次启动都在 GPU 进程阶段 `FATAL: GPU process isn't usable. Goodbye.`（`Trace/BPT trap: 5`，exit 133），`--disable-gpu` 同样崩；日志见 `/tmp/chrome_p3.log`、`/tmp/chrome_p3b.log`，`~/Library/Logs/DiagnosticReports/` 新增 `Google Chrome for Testing Helper-2026-11-25-1115xx.ips`。按历史教训（同类崩溃曾导致整机离线 16h31m）**立即停手，不再重试**，Chrome 残留进程数已确认 0。

因此 P3 的「两行外观是否真的好看、行高会不会挤到 HUD」尚未目测；D6 的 `nonblank`、fps、单 renderer 三项也需在宿主 GPU 恢复后重取。这两条不过，P3 不进正式树。

## 合入纪律（与 P1/P2 一致）

1. 宿主稳定后先补一次 `?static=1&tasks=2` 截图（两行可见、无重叠）与 D6 三件重取。
2. 全绿再走 `tools/apply_patch_batch.sh`（当前脚本只打 P1+P2；P3 手动 `patch -p0 -i patches/PATCH-03-pipe-per-task.diff` 接在后面，然后一次 `build_demo.py`）。
3. 重建后 html 体积应为 **77,937 B**；不是这个数说明顺序或锚点错了，停下核对。
4. 同步契约包 `demo/office-demo.html` 并重算 `SHA256SUMS.txt`，交 DS 原样复跑。

## 回滚

`cp demo/office-demo.template.html.bak.<时间戳> demo/office-demo.template.html && python3 tools/build_demo.py`（按批合脚本自动留的备份），或 `patch -R -p0 -i patches/PATCH-03-pipe-per-task.diff` 后重建。

## 补记（2026-11-25 12:1xZ）：视觉与 D6 已在云主机补齐

- 宿主 headless Chrome GPU 崩后，D6 迁到 **云主机 vm**（Chromium 146 + ANGLE/SwiftShader，WebGL2 可用）。跨机搬运走 `FileBatchUpload` → `aka.doubaocdn.com/s/<id>` → `curl -sSL`（**302 必带 `-L`**）；`lib/pixi.min.js` 取 CDN `pixi.js@8.6.6` 同 sha `e5c38ccc…`。
- P1+P2+P3 树（html 77,937 B `5f0bab64…`）`?static=1&tasks=2&adv=240`：底部两行并存（技术部·A2 / 财务部·A2），各自 01→05 段位正确，行首标签 104px 对齐，画布外、不挤 HUD。证据 `demo/shots/p3b-pipe-two-rows.png`。
- 同树 `?selfcheck=1`（视口 1600×913）：`nonblank 0.6187`、`pixdiff 0.4646`、`renderers 1`、`lod_switch_no_rebuild true` → D6 三项过。
- 仍缺 fps：vm 为软件渲染，帧率无代表性，须真 GPU 单跑一次。
- 口径提醒：`nonblank` 随视口/缩放漂移（1600×800 → 0.4958 假 FAIL），取样须固定视口。
