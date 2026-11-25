# Roost 事件与工位契约 v1.2（2026-11-24 12:10Z 定版）

> **定版裁定（CC 可据此直接开工）：以 `agent-event.schema.json` v1.2 为唯一机器基准，信封 `v/seq/ts(epoch ms)/kind` 不动。**
> 此前本文件 §3 与 `OFFICE-MAP-01.md` §2/5 描述的那套 `agent.join/leave/task.*/seat.*` + ISO8601 信封（群里称 "B 世代"）**作废**——它不是我要的契约，是我上一版文档把草稿贴进了成品，schema 里从来没存在过，`sample-envelope.json` 也不支持它。
> 修法：不换信封，只在 schema 上做**增**（5 个新事件 + 3 个新状态 + 2 个 snapshot 字段），CC 已按信封建立的部分零返工。

## 1. 编制口径（消除 23 / 26 争议）

**结论：23 = 老板办公室 2 + 7 个部门 × 3。**

| zone_id | 名称 | 工位 |
|---|---|---|
| boss_office | 老板办公室 | 2 |
| ops_center | 总经理运营中心 | 3 |
| tech | 技术部 | 3 |
| data | 数据部 | 3 |
| ui | 设计部 | 3 |
| hr | 人力资源 | 3 |
| finance | 财务部 | 3 |
| qa_lab | 验证实验室 | 3 |
| meeting | 会议室 | 0 |
| pantry | 茶水间 | 0 |

部门只有 7 个：`ops_center` 是部门（总经理直辖），不是"老板直管 + 8 部门"的第 8 个。DS 算的 26 是把运营中心算成第 8 个生产部门后再加老板 2，重复了一层。机器可验：`office-zones.json` → `stats.headcount = 23`，`sum(len(zone.seats)) = 23`，`validation 7/7 PASS`；D3 判据件 `seat-model.json` 经 `p98check.py --dim d3` = **5/5 PASS**。

> `qa_lab` 是否保留属产品定义，待飞哥一句确认；不认就变 20 席（2+6×3），`seat-model.json` 与 zones 同步重生成，判据不用重开。

## 2. 30–50 个 agent 与 23 个工位（超编规则）

**规则：席位 = 可视子集，永久成立；超编 agent 不进座位，进「待命池」。**

- 一个工位同一时刻只坐 1 个 agent（`one_agent_per_seat`），不做共享，避免名牌/状态歧义。
- agent 总数 N（30–50）→ 23 常驻席 + 流入。一个 agent 只在 `commuting` 期间离开座位；无空位时进 `standby`（渲染成门口/走廊排队小人，最多 12 个可见，其余折叠成数字角标）。
- 绑定关系：`agent_id → seat_id` 是「占用中」的瞬时映射；`store` 保留 `pending_seat`，空位释放后按 `priority` + 等待时长分配。
- `standby` 计数进 HUD「待命 N」，**不计入「在岗」**。
- 吞吐压力只落事件层：可见 sprite 上限 23 + 12 = 35，超出不渲染、只计数。

## 3. 事件契约（真实形态，机器可验）

`agent-event.schema.json`（JSON Schema 2020-12，**信封 1 + 事件 12 分支 oneOf**）：

**信封**：`v`(integer, const 1) / `seq`(全局单调 integer) / `ts`(**epoch ms integer**) / `kind` ∈ `snapshot|delta|heartbeat|error` / 可选 `schema_rev` ∈ `1.1|1.2`；`additionalProperties:false`。

**遥测事件（v1 原有 7 个，字段未改一个）**：
`agent_upsert`｜`agent_state`｜`agent_progress`｜`usage_delta`｜`agent_remove`｜`log`｜`heartbeat`

**v1.2 新增 5 个 task/seat 事件**：

| 事件 | 必填 | 可选 |
|---|---|---|
| `task_dispatch` | `task_id` `agent_id` `zone_id` `at` | `from_agent_id` `at_zone` `title` |
| `task_accept` | `task_id` `agent_id` `at` | `zone_id` |
| `task_report` | `task_id` `agent_id` `status` `at` | `zone_id` `summary` |
| `seat_claim` | `agent_id` `seat_id` `zone_id` `at` | — |
| `seat_release` | `agent_id` `seat_id` `at` | `zone_id` `reason` ∈ `report\|leave\|standby\|removed` |

`seat_id` 格式 `<zone_id>-S<NN>`；`zone_id` 必须能在 `office-zones.json` 的 `zones[].id` 里命中；`status` ∈ `ok|fail|blocked|partial`。

### 3.1 状态枚举（9 态，与 schema 逐字一致）

`idle` / `thinking` / `working` / `blocked` / `done` / `error` / `commuting` / `reporting` / `standby`

- `commuting`：离座行走，`seat_id=null`
- `reporting`：已到上级区汇报
- `standby`：超编待命，不占位、不进「在岗」
- **`queued` 作废**，统一 `standby`（`queued` 无机器件，且与 `seat_policy.standby_pool` 撞义）

### 3.2 `AgentSnapshot` 字段

原有 `agent_id/alias/state/task_id/progress/tokens_in/tokens_out/cost_usd/started_at/updated_at/meta`；
**v1.2 新增** `seat_id`(可 null) / `zone_id`(可 null)。`agent_state` 事件同步可带 `zone_id` / `seat_id`，一次落位。

### 3.3 样例与自测

- 样例：`sample-envelope.json`（v1 原样，仍通过）+ `sample-envelope-v12.json`（完整走一遍 dispatch→release→commuting→accept→reporting→report→standby→claim→working）。
- 校验：包内内置 JSON Schema 子集校验器（只 python3 标准库、无 jsonschema 依赖，见 §6）实跑，2 个样例全过；四条反例全部被拒——B 世代信封（缺 `kind` / `ts` 为 ISO8601）、事件带未知键、`state=queued`、非法 `seat_id`。
- 契约自测：`sh verify.sh`（17 项包内断言，见 §6）。

## 4. 职责边界

- 豆包（我）：架构与资产 —— 事件契约、zone/seat 数据模型、Tiled `.tmj`、sprite 图集、目录结构、契约自测。
- CC（`usr_01M83ERNPDFVG9NRXZZ2SDMXPM`）：实现层 —— WS→store→工位绑定、`commuting/reporting` 状态机、单 renderer 舞台。**schema v1.2 已可照建，不需自造补件。**
- DS（`usr_01M7KM2S72EMZTFQYREYFY2EQ9`）：判据与独立复跑，不自证自己判的东西。判据基准 = schema v1.2。
- 硬线（进判据）：**每部门 ≤3 工位**、`headcount` 与 `seat sum` 必须相等、`standby` 不占位、`seat_id` 唯一且稳定。

## 5. 原件位置

包目录（本包根 `roost-contract-01/`）：
`agent-event.schema.json`（v1.2）、`CONTRACT-01.md`（本文件）、`office-zones.json`、`seat-model.json`、`sample-envelope.json`、`sample-envelope-v12.json`、`OFFICE-MAP-01.md`（23 席重述版）、`ROOST-UI-ARCH-01.md`、`office-map.tmj`、`office-tileset.png`（128×128，之前漏发）、`agents.png`、`d6-page-selfcheck.json`（Pixi 单舞台路径 + 真 GPU fps）、`d6-fps.json`（fps 原始探针输出，DS canonical 落盘原件 `56c5b0dc`）、`SHA256SUMS.txt`、`verify.sh`（包自验入口）。

源码根与判据器随仓库分发，不在此写本机绝对路径；判据器按 §6 的查找顺序（`$P98` → `./p98check.py` → `../p98-criteria-01/*/`）定位。

## 6. 包自验入口（零依赖，可复现）

```sh
cd roost-contract-01 && sh verify.sh                 # 自动找判据器
P98=/path/p98check.py sh verify.sh                   # 显式指定
```

- **不依赖第三方库**：schema 校验用包内内置的 JSON Schema 子集校验器（只 python3 标准库），不需要 `pip install jsonschema`、不联网。
- 覆盖 **17 条**包内断言：schema 2020-12 / 12 事件 / 9 态 / 两份样例合法 / 四条反例必须被拒（B 世代信封、未知事件键、`state=queued`、非法 `seat_id`）/ headcount 23 = 席位和 / 7 部门各 ≤3 / boss 2 / `standby_seats=0` 且 cap=3 / `seat_id` 命名与 zone 绑定 / seat-model 与 zones 一致。
- 退出码：**0 全过（含 D3/D6 实跑 5/5）｜1 有 FAIL｜2 判据器缺失或维记 UNTESTED**。不再用 `|| true` 吞失败。
- 实测：`sh verify.sh` → `PKG_CHECKS pass=17 fail=0`，D3 5/5、D6 5/5，rc=0；`P98=/nonexistent` → rc=2；故意把 `seat-model.json` 改 20 席 → rc=1 且两行 FAIL。

> 判据口径说明：`s4_entry_commands` 现在**可执行验证**（跑 `verify.sh` 拿退出码），不再只读声明字段。D6 的 `u3_fps` 已从「未测」变成**实测**：`d6-page-selfcheck.json` 换为 Pixi 单舞台（WebGL2）路径的页面自检，帧率取 `d6-fps.json`（DS canonical 落盘原件 `56c5b0dc`）——本机 M5、ANGLE Metal 真 GPU、真实 `performance.now`（不设 `--virtual-time-budget`），丢 90 帧预热后采 300 帧：**60.0 fps、p50 16.7ms、p95 16.8ms、p99 16.8ms、>20ms 慢帧 0**；`--force-device-scale-factor=2`（3200×1600 背衬）复跑同为 60.0 fps、慢帧 0。口径边界写清：headless 无窗口管理器，60Hz 是 BeginFrame 节拍，所以结论只能到「≥60 且零掉帧」，不等于设备天花板。D6 因此记 **5/5**，是否采信由 DS 复跑后定。
