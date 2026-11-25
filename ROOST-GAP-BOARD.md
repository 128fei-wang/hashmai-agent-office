# Roost 主线缺口板（GAP-BOARD-01）

更新时间：2026-11-24 07:10Z ｜ 口径以本文为准，单项细节见各分件
总进度严格口径：**2/12 = 16.7%**（未增加）

## 一、六维判据现状

| 维度 | 现读 | 谁出件 | 缺什么 / 下一步 | 卡点 |
|---|---|---|---|---|
| D1 功能 | 4/5 | CC2 实现 + DS 判 | store-04 交 DS 原样跑 v4 期望（17/17） | 等 DS 回执 |
| D2 工具 | — | DS | Roost 对应件未产出 | 无件可读，不记分 |
| D3 结构 | 5/5 | 我（契约包） | 已定稿，`verify.sh` 5/5 | 无 |
| D4 数据 | 2/5 | 我 + DS | 事件回放件未产；store-04 只是实现层切片 | 需 CC2 12 事件流接入 |
| D5 性能 | 无 | DS | 30–50 agent 压测：n≥50 / p95≤200ms / err≤1% / RSS≤800MB / ≥300s | 无任何产品级数，DS 已认领为下一件 |
| D6 UI | 5/5 | 我 | v0.6 定稿，DS 判「不用重跑」 | 无 |

判级权在能实操的席（Codex 持唯一派单与判级），我出的 `SCORE d3=9.8` 只是公式输出，不是授予。

## 二、产品侧缺口（我这条线）

1. **工位编号三套体系未统一**——`seat_id` = `tech-S00..S02`，demo agent id = `tech-A0..A2`，牌面 = `技术-01..03`，恒偏 1，全楼 23 席一致。
   - 已出 `SEAT-ID-MAP.md` + `tools/check_seat_ids.py`（当前 rc=0，A6 INFO 偏移 [1]）。
   - 未改码：改显示层要重建 `demo/office-demo.html` + 重跑 D6 自检/fps/`p98check --dim d6` + 重算 SUMS，会作废 DS 已验收的 v0.6 基线。
   - 决定：与 CC2 的 12 事件流接入一起做；验收门槛 `check_seat_ids.py --require-unified`。
2. **连线只覆盖当轮任务四段路径**，没有跨任务汇总的枢纽图；底部流水条是单任务串行，并发多任务互相覆盖 → 需 CC2 事件流后改多轨。
3. **idle 小动作只有 ±1.2px 呼吸，歪头（head tilt）未做**。
4. 2D 降级自检件与三张 v05 截图未进契约包 SUMS（DS 认只影响包内自证，不算停点）。

## 三、协作侧缺口

| 件 | 状态 | 归属 | 停点 |
|---|---|---|---|
| `CC-1124-P98-SPEC-01` | **blocked 逾期**（原定 11:45） | CC 席 | 未交件 |
| CC2 单 renderer 舞台 | 待回执 | CC2 | 我已定调「不用补 Node，舞台在 Mac 建」 |
| `P98-EVIDENCE-MAP-DB-1124`（484 条目 / 492,557 B） | 落盘，未外发 | 我 | 附件通道 REST 401 |
| 看板 v2 `progress-board-v2-20261124.png` | 已生成，未外发 | 我 | 同上；另权重口径与暂定标准不一致未解 |

## 四、通道与运维

- 附件通道：附件上传 / `send_file` / `list_conversations` 全 401（`state.json` token 停在 11-17，bridge 只在内存持新 token 不回写）。可选＝让 bridge 落盘一次 refresh，或给一次重启窗口；改写 `state.json` 被规则禁止。
- cron：实测 **30 个启用任务全部 `M * * * *`、分钟位覆盖 0,2,…,58 全部偶数分钟**，等效每 2 分钟一轮、30 份相同工作；`17909147647746`（即时轮14）挂「本地电脑」且最后运行 11-18 10:16，已 6 天未跑。
- 方案已提：留 `17910067857154` 改 `*/5 * * * *` 作唯一 kickstart 授权轮，删其余 29 → 12 轮/小时、减 60% 空转。**主人未回「改」，未动任何 cron。**
- 每轮都带 `!online → kickstart -k` 是 06:22「每 60 秒一次 sigterm」的成因（30 份同时开火互打断重连）。

## 五、待主人拍板（我不自行决定）

1. cron 治理：是否按上述方案执行；`17909147647746` 换环境还是直接删。
2. 巡检频率放宽到 5–10 分钟（已累计 8 轮以上建议，未答）。
3. 附件通道是否给一次 bridge 重启窗口。
4. 45.8s 那张 agent 表附图字不可读（1776×600 源帧放大 4 倍仍是色块），是否在 Roost 群公开提示「别引用它做判断」。
5. C1 编制：现行「老板 2 + 7 部 × 3 = 23」；DS fixture 拆 `gm-ops`/`ops` 得 26，是否真要拆两个场景。
6. `qa_lab` 保留（现按 23 席）还是回滚 20 席。
7. 「每部门 ≤3」是否也约束老板/运营（现按全楼 ≤3、老板 2 执行）。
8. 六维权重两版并存（功能25/工具25/结构15/数据15/性能10/UI10），由谁定稿。

## 六、复跑入口（本板所有结论可复验）

```
cd /Users/hashmai/clawchat-out/roost-contract-01 && shasum -a 256 -c SHA256SUMS.txt   # 16/16 OK
cd /Users/hashmai/clawchat-out/roost-contract-01 && sh verify.sh                       # 17 断言 + D3/D6
cd /Users/hashmai/roost-im/roost-ui-arch && python3 tools/check_seat_ids.py           # rc=0, A6 INFO
cd /Users/hashmai/roost-im/roost-ui-arch && node tools/test_sim.js                    # PASS 9/9
```

## 七、进度快照（2026-11-24 09:11Z，逐轮滚动更新）

- 契约包（架构线）：16 件 SUMS 16/16 OK、`verify.sh` 17/17 pass、D3 5/5、D6 5/5、rc=0（09:06Z 实测）。
- 工位编号补丁 PATCH-01：副本预演 A1–A6 全 PASS、`test_sim` 9/9、体积 +54 B；**正式树仍未改**，建议与 CC2 的 12 事件流同批合入。
- CC2 `roost-store-04`：DS 原样复跑 **17/17**（24,104 B，sha `5f14b157…3b15af4`，包内 SUMS 11/11）；复核-07 两处（U1 续期、U10 墙钟）确认已修。
- **新缺陷 U11（DS 实测，待修）**：同一份快照重复发时，席位在「留给暂离者」与「补位给待命者」之间每 15s 反复切换（8 帧 3 周期：保留 a00／席空／standby 7 ↔ 无保留／席上 x0／standby 6）。根因 `apply_snapshot` 先 `_free_all_seats()` 再归约。修法两处：B 锚点记 `_left_at`（截止按离座时刻算）、A 归约分两遍（先在岗绑席再处理暂离）。
- 因此 D1/D4 仍判 **4/5**，等 U1+U10+U11 三支全过才给 5/5。
- D5 性能维：仍无产品级数，DS 认领 30/50 两档压测，出吞吐／p95／满编抖动三行数。
- `CC-1124-P98-SPEC-01`（CC 席产品规格门）：blocked，逾期未交件。
- 项目总进度严格口径：**2/12 = 16.7%**，未变。

## 八、恢复快照（2026-11-25 02:14Z，离线 16h31m 后）

- **离线窗口**：11-24 09:41Z → 11-25 02:12:23Z 共 16h31m，宿主整机从环境注册表消失（`ENV_NOT_FOUND`），期间 30 个定时轮全部空转、无通道读写。
- **自愈方式**：无需人工 kickstart。launchd 在宿主回来后自拉 bridge：新 pid 813（旧 3053 已退出），日志 `connecting attempt 1` → `relay-up 127.0.0.1:51555` → `ws-open` → `hello-ok device_replay ack_mode=legacy` → `replay.done`，`last_close_code=4000` 仍为正常关闭值。
- **漏件判定**：`replay.done` 后 `inbox.jsonl` 500 行 / `peer.jsonl` 2,162 行，按 `processed.jsonl`（4,913 行）去重后未处理 **0 条**；`last_inbound_at` 仍停在 09:06:19.298Z，可判离线期间对端无新件或已全量重放。
- **重启后产物完好（02:13Z 实测）**：
  - 契约包 `verify.sh` → `PKG_CHECKS pass=17 fail=0`、D3 5/5、D6 5/5、rc=0；`shasum -c SHA256SUMS.txt` → **16/16 OK**。
  - 正式树三哈希与基线逐字节一致：`demo/office-demo.html` 75,278 B `10d360a57ee11c55`｜模板 51,229 B `d12e43a442b16329`｜检查器 `6c19c3980d5753cc`。
  - `check_seat_ids.py` → `seats=23 zones=8 fail=0` rc=0（A6 INFO 偏移 [1] 仍存，属已知）；`test_sim.js` → PASS 9/9。
- **PATCH-01** 仍未合入（42 行 diff + dry-run 脚本在位），维持「与 CC2 的 12 事件流同批」的时点判断。
- **未推进项（不变）**：D5 30–50 agent 产品级数仍缺（DS 欠件）；U11 待 store-05；D1/D4 仍 4/5、2/5；`CC-1124-P98-SPEC-01` blocked；总进度 **2/12 = 16.7%**。
- **教训固化**：headless Chrome 长跑是宿主掉线主因（两次均在被 Bash 超时掐断后整机 offline，`Retired/` 下留有多份 Chrome Helper `Aperitif` 崩溃 `.ips`）。此后 D6/D5 的浏览器类复跑必须单轮最多一次、先确认宿主稳定，不在高频定时轮里连跑。

## 九、D5 部分实测：寻路/状态机 CPU（2026-11-25 02:20Z，非渲染）

件：`tools/bench_d5_routing.js`（Node，可复跑）→ `demo/d5-routing-bench.json`（3,215 B）。场景 53×24、698 可行走格、23 席、56 端点；30/50 agent 按超编待命计价。

| 规模 | warm 帧 p50 | warm 帧 p95 | 占 16.7ms 预算 | cold 单次 p95 | 全员同帧重算 |
|---|---|---|---|---|---|
| 23 agent | 2.41 ms | 5.20 ms | 31.2% | 0.270 ms | 14.29 ms |
| 30 agent | 2.26 ms | 6.24 ms | 37.4% | 0.264 ms | 14.11 ms |
| 50 agent | 0.02 ms | 9.66 ms | 57.9%（max 12.21） | 0.282 ms | 14.23 ms |

- **0 条不可达**（全 30,900 次寻路（warm 24,720 + cold 6,180）`unroutable=0`）；warm 的 p50 极低（0.0003–0.0013 ms）说明绝大多数是缓存命中，p95 抓的是新 OD 的冷算。
- **结论（可执行）**：单次 BFS 约 0.22–0.28 ms，因此「每帧全员重算」在 23/30/50 都稳定吃掉 **约 14 ms ≈ 85% 帧预算**，必然掉帧。50 agent 必须做错峰冷算——按 4.5 ms 预算折算，**每帧冷算配额 ≤ 20 次**（其余走缓存或沿用上一帧路径）；23/30 agent 也建议同款配额，理由同上。
- **判级**：本件只覆盖寻路/状态机，不含 WebGL 渲染、纹理上传、HUD 更新，**D5 记 partial**，不能据此判 9.8；D5 渲染实跑仍等 DS 的 30/50 两档产品级数（或宿主稳定窗口内由我方单跑一次 Chrome 探针）。

## 十、RQ-DATA-01/02 封装层三方闭环（02:32Z）

**结论：封装层已闭环，无异议；对象级判级在 Codex，不在我席。**

- 三方口径：WB 自证（`WB-1124-RQDATA-0102-02`）／我席独立复跑（`xcheck-wb-corrected/`）／DS 正式复核（`DS-1125-RQDATA-0102-COR-XCHECK-01`，20,250 B、sha256 `99bf7cdce538cebe2cc7378b67ab902cf9d4d3e3613407e9538619a30fd882c3`、包内 `SHA256SUMS` 12/12 OK）。
- 三项核心完全收敛：①外层哈希逐字节一致（RQ01 `e2082c08…`、RQ02 `5f166cee…`）；②全量 sums 103/103、90/90，0 fail；③路径例外各 4 件，声明集=实际集，DS 另加验「同一文件内无非声明的第二种绝对路径」→ PASS。
- DS 补齐我未做的三项，全 pass：旧包逐文件比对（RQ01 102/104、RQ02 89/91 字节相同，仅 `manifest.json`/`sha256sums.txt` 变、`snapshot_id` 集合不变）、11/11 真包篡改全抓、6/6 黑盒负控非零退出；C1–C4 复跑 RQ01 177/179、RQ02 160/161，两处 fail 为已知非阻断（`S.no_absolute_paths` 已被 C5 v2 取代、`R.input_json@runs/d23-direct` 旧包即有）。
- Codex 02:30:45Z 已派 `CODEX-1125-DS-RECHECK-AUDIT-01` 给 Milo（从原始包复跑 C5 v2，截止 10:50 CST＝02:50Z）。我席独立件里的「4 文件/4 例外集合相等」实测可直接引用，不必重跑。

**停点**：①对象级 pass 等 Codex；②契约包与交件包仍卡 REST 401（需 bridge 落一次 refresh 或给重启窗口，`state.json` 按规则不动）。

### 十·补：Milo 席 blocked 与我席通道可用（02:34Z）

- Milo 10:32 CST 报 `blocked`：三件附件在本席均返回「只能读取当前用户在当前会话发送的附件；附件不存在或已清理」，且 `get_agent_instances` 为空无 runner，故不转引任何哈希，RQ-DATA-01/02 维持 blocked。其结论「不把 DS 自报升级为验收」是对的。
- 但其「两条独立通道同时不可用」不含我席。我席在 Mac 本机 HTTP 直取三件并实跑：外层哈希/体积、全量 sums（103/103、90/90、12/12，exit 0）、路径例外 4/4 集合相等、无第二种绝对路径、清单口径自洽（102/104、89/91）。全部 pass，命令与原始输出已存 `xcheck-wb-corrected/RECHECK-TRANSCRIPT.md`（4,961 B）。
- 处置：不刷群。等 Codex 开口即一条引用过去，省一轮复跑。

### 九·补：D5 寻路有了更优解（02:38Z，PATCH-02 候选）

- 原结论「50 agent 必须错峰冷算、每帧 ≤20 次」是在「50 个互不相干的 OD」假设下推的。真实场景是**多源单目标**（同段奔少数目的地：派单到某部门、统一去运营中心、回工位）。网格 BFS 对称，可从目标建一次树同时服务所有出发格 → 冷算从 N 次降到 D 次。
- 实测（240 帧、K=4 活跃任务、目的地随帧推进）：23/30/50 agent 每帧 p95 由 5.88/7.31/12.11ms 降到 **1.17/1.21/1.29ms**（5.03x / 6.04x / 9.39x），全部 ≤8.35ms（50% 帧预算）；目的树 LRU 12 跨帧命中后每帧实际 BFS p95 = 2；`unroutable=0`。
- 等价性用正确判据（端点 + Manhattan 总步数 + 无对角穿越）验：392/392 全等价。首版脚本误用逐点相等，必然 392/392 不符——最短路径不唯一，tie-break 不同，这是判据错不是实现错。
- 件：`tools/bench_d5_dedup.js`、`demo/d5-dedup-bench.json`（4,668 B）、`patches/PATCH-02-dest-shared-route.diff`（45 行）、`D5-DEST-SHARED-ROUTE.md`。副本预演：`patch --dry-run` rc=0、`build_demo.py` → 76,482 B、`test_sim.js` 9/9（含 py_js_route_agree）。
- 合入纪律：与 PATCH-01 同批，单个不合；合完重取 D6 三件 + 重算 SUMS + 交 DS 重认。**正式树未动一字节**，D5 仍记 partial。

### 十一：U11 独立复核完成，缺陷已量化并给出可采纳修法（2026-11-25 11:1xZ）

- DS 的 `P98-STORE-04-PROBE` 我独立复跑：**v4 17/17 PASS、`selftest` 74/74 PASS**，包内 SUMS 3/3 与外层 sha `43cca7f7…` 一致。他覆盖的边界确实成立。
- 但 v4 打的是「重复 upsert」，没打「同一全量快照每 15s 反复刷新」。我自写 v5 探针专打后者：**未修版 10/12**——目标席每 15s 在「留给暂离者」与「补位给待命者」之间来回切（含 hb 帧 occ 序列 `[0,1,0,1,…]`），保留截止随快照续期（`[10,25,40,55,70,85,100]`）。
- 修法收敛为**一处 23 行 diff**（`xcheck-ds-0300/patch/U11-store-left-at.diff`）：保留截止改按「首次离座时刻 + `RESERVE_MS`」只锁一次（`_left_at`）。此前板上的「A 归约分两遍」**不再是必需项**——单靠 `_left_at` 即 12/12。
- 两个必守点（实测会破）：`_left_at` 过期释放时**不清**（清了抖动复现）；**不要**改成帧末无条件 `_promote_standby()`（试过打挂 v4 U7.1 → 16/17、selftest → 72/74）。
- 修后：v5 **12/12**、v4 **17/17**、`selftest` **74/74**，零回归。证据与复跑命令见 `xcheck-ds-0300/U11-INDEPENDENT-FINDING.md`；交接包 `/Users/hashmai/clawchat-out/U11-STORE-04-FIX-20261125.tar.gz`（9,983 B、sha `6200c2f2…`）。
- 待 CC2 采纳进 `store-05`；D1/D4 在 U11 闭合前维持 4/5、2/5。

### 十二：PATCH-03（流水条一单一行）副本已验；宿主 headless Chrome GPU 崩，视觉与 D6 待补（2026-11-25 11:1xZ）

- 缺口：底部流水条原为全局单条，两单并发时后一单把前一单的段位打回、最后一单结束又整条清空。连线本身一单一线、支持并发，缺口只在流水条。
- 改法：`patches/PATCH-03-pipe-per-task.diff`（146 行 / 6,527 B，只改模板）→ `pipeOpen` / `setPipe(row,n)` / `pipeClose` 三件套，DOM 行随单走；仍在画布外、不影响 D6 取样。
- 副本验证：基线+P3 html **76,679 B**、`test_sim` 9/9、`check_seat_ids` rc=0；P1+P2+P3 三补丁同树 html **77,937 B**、`--require-unified` **A6 `[0]` rc=0**、`test_sim` 9/9、零 `.rej`；行逻辑用 Node 桩 DOM 直接 eval 模板真实代码，两行并存、各自段位正确、关闭即摘除。
- **未验证（如实记）**：本机 headless Chrome 连续两次在 GPU 进程 `FATAL: GPU process isn't usable`（exit 133，`--disable-gpu` 亦然），新增 3 份 `Chrome for Testing Helper … .ips`；按历史教训（同类崩溃曾致整机离线 16h31m）已停手，残留进程 0。故「两行外观 / 是否挤 HUD」与 D6 `nonblank`、fps、单 renderer 均未重取 → P3 不进正式树。
- 正式树三哈希复核仍为 `10d360a5…`、`d12e43a4…`、`6c19c398…`（未动一字节）。
- 待宿主 GPU 恢复：补 `?static=1&tasks=2` 截图 + D6 三件，再与 P1/P2 同批合入并重算契约包 SUMS。

### 十三：D6 迁到云主机跑通，PATCH-03 视觉与 D6 缺口已闭合（2026-11-25 12:1xZ）

结论：宿主 Chrome GPU 崩不是死路——**D6 可整体迁到云主机（vm, linux）执行**，且数值与 Mac 基线逐位一致；PATCH-03 欠的两项证据（两行外观、D6 复取）当轮补齐。

1) **可行性实测（vm）**：Chromium 146 + Node 22 + 7GB；WebGL2 经 ANGLE/SwiftShader 起来（`webgl2 OK | ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero))`），无需 `--disable-gpu`。命令模板同 Mac，仅需 `--no-sandbox --disable-dev-shm-usage`。
2) **跨机搬运（关键运维发现）**：`FileBatchUpload`（本机 → `aka.doubaocdn.com/s/<id>`）＋ `curl -sSL` 下载可做双向文件转移。注意 **302 必须跟跳（`-L`）**，否则只拿到 2 字节。已实测逐字节一致：html `10d360a5…`(75,278 B)、`sim.js`(4,022 B)、`office-tileset.png`(779 B)、`agents.png`(4,696 B)；`lib/pixi.min.js`(665,775 B) 直接取 CDN `pixi.js@8.6.6` 同 sha `e5c38ccc…`，免搬 665KB。
3) **D6 自检基线复现**：补齐 `demo/sim.js` 与 `assets/*.png` 后 `?selfcheck=1` 出 `SC-DONE`。同视口 1600×913（`--window-size=1600,1000`）→ `renderers=1`、`pixi-webgl`、`nonblank=0.6187`、`empty_seat_pixel_diff=0.4646`、`lod_switch_no_rebuild=true`、`empty_seat_hud=1`、grid 53×24、seats=agents=23 —— **与 Mac 基线 0.6187 / 0.4596 一致**，D6 功能 5/5 可判。
4) **判据缺陷（要记）**：`nonblank_ratio` 随视口高度/相机缩放漂移。同机 1600×800 视口（z=0.758）得 **0.4958 < 0.60 阈值**，1600×913（z=0.905）得 0.6187 过线。故 `u2 nonblank>=0.60` **不能当硬门槛**，必须在固定视口取样，否则同树同代码会假 FAIL；建议判据补 `viewport` 与 `cam` 字段做前置断言。
5) **PATCH-03 视觉（首次取到）**：`/tmp/p3b`（P1+P2+P3，html 77,937 B `5f0bab64…`、`--require-unified` A6 `[0]` rc=0）在 vm 跑 `?static=1&tasks=2&adv=240` → 底部**两行并存**：`技术部 · A2` 与 `财务部 · A2`，各自 `01 下发 → 02 拆单 → 03 执行 → 04 汇报 → 05 回位`，行首标签 104px 省略对齐，均在画布外、**不挤 HUD**（HUD `工作中 2`、`缩放 0.90`）。证据 `demo/shots/p3b-pipe-two-rows.png`（1600×1000 / 124,484 B）。
6) **PATCH-03 的 D6 复取（首次取到）**：同一 P1+P2+P3 树 `?selfcheck=1` → `nonblank 0.6187`、`pixdiff 0.4646`、`renderers 1`、`lod_switch_no_rebuild true`、`lod ['过渡带','场景层']` —— 三项全过，与未打补丁树数值同。另有整屏渲染证据 `demo/shots/vm-d6-render-1600x887.png`（84,405 B）。
7) **仍未取（如实记）**：fps。vm 是 **SwiftShader 软件渲染**，帧率无产品代表性，不能顶 9.8 的 `fps>=55`；D6 的 fps 项仍须真 GPU（宿主恢复或另配带显存的机器）单跑一次。
8) **vm 的显示瑕疵（非产品缺陷）**：缺 CJK 字体族，牌面/HUD 部分中文渲染成方框；不影响几何判据与像素判据，但截图不能直接对外当视觉稿。
9) 正式树仍未动一字节（三哈希同前）；P1+P2+P3 合入时点维持等 CC2 的 12 事件流同批。

## 十四：D6 已补齐（第三方实测，2026-11-25 04:43Z）

DS 在合入后的树（`5f0bab64…`，77,937 B）上实测真机帧率：1600×800 视口对齐 v05 基线、WebGL2/ANGLE Metal M5、300 样本、4,999.8ms 真实时钟 → 60.0fps、p95 16.8、max 16.8、`>20ms` 慢帧 0、23 席；`?force2d=1` 自跑 `canvas2d`、23 席、慢帧 0。他据此判 **D6 = 5/5**，并核过包内 SUMS 16/16。

我方据此更新口径：D6 由 4/5（9.3）恢复 **5/5（9.8）**，fps 证据归属 DS、其余四项归属 selfcheck。注意该结论绑定旧 sha `5f0bab64…`；v0.8（改名+HUD 首帧）合入后需在新树上重取一次。

**基线已换**：v0.8（改名 + HUD 首帧）04:47Z 合入，正式树 sha `5f0bab64…` → `0170be02…`（78,058 B）。第十四节的 D6 5/5 结论仍属旧 sha，新树 fps 待 DS 复测一次后重挂。

**D6 在新基线已补齐（第三方实测）**：DS 04:50Z 在 `0170be02` 上复测 fps 60.0 / p50-p99-max 16.7-16.8 / 慢帧 0 / 视口 1600×800（与 v05 同视口），判 **D6 5/5**；`?force2d=1` 降级路径同样 60fps、0 慢帧。证据见 `D6-FPS-EVIDENCE-0170BE02.md`。本机 `verify.sh` 仍显 4/5 是因本机 fps 未测，不是缺陷。
