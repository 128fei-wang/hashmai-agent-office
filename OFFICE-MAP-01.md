# 办公室场景图 · 数据模型与规则（ROOST-OFFICE-01 · 23 席版）

> **本文件 2026-11-24 12:10 按 53×24 / 23 席重述。** 上一版写的是 61×38 / 66 工位 / 编制 50，那批数字已经作废（`office-zones.json`、`seat-model.json`、`office-map.tmj` 全是 23 席版，只有这份文档没跟上）。
> 老板下达命令 → 总经理运营中心拆单派发 → 各职能场景执行。这张图不是背景板，是组织结构的空间表达。
> 生成器 `tools/build_office.py`，产物 `office-zones.json`（12,264 B），确定性可复跑。

---

## 1. 图规格

| 项 | 值 |
|---|---|
| 网格 | 53 × 24 格 |
| 单格 | 32 px（逻辑像素），整图 1696 × 768 |
| 走廊 | `corridor_a` [1,7,51,8]、`corridor_b` [1,15,51,16]，横向贯通 |
| 区域 | 10 个：老板办公室、总经理运营中心、会议室、茶水间、技术部、数据部、设计部、人力资源、财务部、验证实验室 |
| 编制 | **23 人**；工位 **23 个**（`standby_seats=0`） |
| 可走格 | 698；桌子格 23 |

区域矩形一律为闭区间 `[x0, y0, x1, y1]`，墙厚 1 格，`interior = [x0+1, y0+1, x1-1, y1-1]`。桌子占 1 格且不可通行，人坐在桌子正下方（`facing: up`）。**这个朝向不是装饰**：人必须面朝办公桌，否则坐下去背对空气，一看就是假图。

编制分配（每部门上限 3，硬线，见 `seat_policy`）：

| zone_id | 名称 | role | 工位 | 矩形 |
|---|---|---|---|---|
| boss_office | 老板办公室 | command | 2 | [1,1,8,6] |
| ops_center | 总经理运营中心 | dispatch | 3 | [10,1,27,6] |
| meeting | 会议室 | facility | 0 | [29,1,38,6] |
| pantry | 茶水间 | facility | 0 | [40,1,51,6] |
| tech | 技术部 | function | 3 | [1,9,14,14] |
| data | 数据部 | function | 3 | [16,9,33,14] |
| ui | 设计部 | function | 3 | [35,9,51,14] |
| hr | 人力资源 | function | 3 | [1,17,14,22] |
| finance | 财务部 | function | 3 | [16,17,33,22] |
| qa_lab | 验证实验室 | function | 3 | [35,17,51,22] |

`2 + 7×3 = 23`。`ops_center` 算部门，不再另立"总经理"与"运营"两间。

---

## 2. 数据模型

```jsonc
// zone（字段与 office-zones.json 一致）
{
  "id": "tech", "name": "技术部", "role": "function",   // command | dispatch | function | facility
  "rect": [1, 9, 14, 14],
  "interior": [2, 10, 13, 13],
  "door": { "tile": [7, 9], "zone_id": "tech" },
  "south_door": { "tile": [7, 14], "zone_id": "tech" },
  "headcount": 3, "capacity": 3,
  "seats": [
    {
      "seat_id": "tech-S01",
      "zone_id": "tech",
      "tile": [5, 11],           // 人站立的格
      "desk_tile": [5, 10],      // 桌子格（不可通行）
      "facing": "up",
      "assigned": false          // 由运行时绑定 agent；seat_id 稳定，不随 agent 变
    }
  ]
}
```

**绑定规则（三条，运行时严格遵守）**

1. `seat_id` 是稳定主键（格式 `<zone_id>-S<NN>`），**不随 agent 变化**。agent 进出只改 `assigned` 与绑定表，绝不重排座位 —— 重排会让"谁坐哪儿"的记忆断裂，用户第一眼就发现不对。
2. 一个 agent 同时最多占 1 个工位；一个工位同时最多 1 个 agent（`seat_policy.occupancy = one_agent_per_seat`）。冲突时新来的进**待命池**（`state=standby`，渲染在门口/走廊排队），不硬塞、不共享工位。
3. 编制 `headcount` 与席位数恒等（23=23）。**没有"备用空位"这个概念**：座位空缺一律用「agent 不在座」表达（空椅子 + 无名牌），由 `seat.claim/seat.release` 事件驱动。上一版的 `seat.standby` 属性已删除。

### 状态枚举（与 `agent-event.schema.json` v1.2 完全一致，共 9 态）

`idle` / `thinking` / `working` / `blocked` / `done` / `error` / `commuting` / `reporting` / `standby`

- `commuting`：离开工位、在走廊行走，`seat_id=null`
- `reporting`：已到上级工位/会议室，播说话动画
- `standby`：超编无空位，在待命池，**不占工位、不进 HUD「在岗」计数**

> 旧文档里的 `queued` **作废**，统一叫 `standby`。理由：`queued` 从来没有机器件，且与 `seat_policy` 的 `standby_pool` 撞义。

---

## 3. LOD：三层，不靠缩小 sprite

23 个工位铺满 1696×768，全屏缩放下一个 sprite 只有十几像素，全帧动画等于没做。所以按摄像机缩放分三层：

| 层 | 触发条件 | 渲染内容 | 帧率策略 |
|---|---|---|---|
| 场景层 | `zoom ≥ 0.75`（1 格 ≥ 24px） | 全帧动画、名牌、状态气泡、走动路径 | 60 fps（只渲染视口 ±2 格） |
| 过渡带 | `0.4 ≤ zoom < 0.75` | 动画抽帧、不要名牌、只要状态点 | 30 fps |
| 鸟瞰层 | `zoom < 0.4` | 4px 简化 sprite、部门色块、状态点、房间轮廓 | 20 fps，镜头静止时 10 fps |

补充规则：

- **切换用 layer 显隐 + 纹理替换，禁止重建 renderer**（重建 WebGL 上下文会有 300ms 级黑屏）。机器可验：`?selfcheck=1` 的 `lod_switch_no_rebuild`。
- `zoom < 0.4` 时走廊格不渲染，只画房间色块。
- **LOD 阈值可配置但不可自适应**：按帧时间动态调整阈值会让画面忽清忽糊，比掉帧更伤。掉帧就走降帧率，不降 LOD。

---

## 4. 汇报线路由

`route_steps` 是门到门的 BFS 最短步数矩阵（10×10 全连通，无 `null`）。现行数值：老板办公室 → 运营中心 **16 格**；技术部 → 运营中心 **14 格**；技术部 → 验证实验室 **46 格**；设计部 → 运营中心 **28 格**。

**行走速度与时间映射**（与真实事件时间对齐，不是随便走）：

| 场景 | 速度 | 换算 |
|---|---|---|
| 房间内普通步行 | 4 格/秒 | 8 格 = 2s |
| 走廊行进 | 8 格/秒 | 16 格 ≈ 2s |
| 超过 40 格的跨区（技术→实验室 46 格） | 走廊 8 格/秒 + 尾段瞬移 | 上限 10s，超出部分淡出淡入 |

规则：

1. **任务气泡沿路由走，人不提前跑**。气泡抵达目标区域的门，该区域的人才起身 —— 否则看起来像"人知道还没下达的命令"。
2. 跨区汇报（下级→上级）**必须真的走到上级房间**，不能原地弹个 toast。这是"像公司"和"像监控大屏"的分界线。
3. 同区域内的任务不下发气泡，直接头顶弹一个 0.5s 的任务标签，成本更低。
4. 路由只做静态预计算（本文件矩阵），运行时不做 A*。动态障碍（有人挡道）用简单的侧身让位，不做绕路重算。

---

## 5. 状态机（9 态，事件驱动）

```
         ┌──────────── seat_claim ────────────┐
idle ──→ commuting ──→ working ⇄ blocked ──→ done
           │              │
           └─ reporting ←─┘（task.report，播完回 seat）
                            │
                     无空位 → standby ──(空位释放)──→ idle
error → blocked（需人介入）
```

｜动作｜时长｜
|---|---|
| 起身 → 走到上级/目标区 | 按路由算，上限 10s |
| 开工动画起手 | 400ms |
| 完成后走回上级汇报 | 按路由算，上限 10s |
| 汇报播放 | 2s（可被点击跳过） |
| 汇报完回座 | 按路由算，上限 10s |

对应事件（`agent-event.schema.json` v1.2，全部机器可验）：

| 状态变化 | 事件 | 必填字段 |
|---|---|---|
| 下任务 | `task_dispatch` | `task_id` `agent_id` `zone_id` `at`（+`from_agent_id` `at_zone` `title`） |
| 离座去汇报 | `seat_release`(reason=`report`) + `agent_state`(commuting) | `seat_id` `zone_id` |
| 到上级区 | `task_accept` + `agent_state`(reporting) | `task_id` `zone_id` |
| 汇报完 | `task_report`(status) | `status` ∈ ok/fail/blocked/partial |
| 回座 | `seat_claim` + `agent_state`(working) | `seat_id` `seat_id=` 同 zone |
| 超编待命 | `agent_state`(standby) | `seat_id=null` |

---

## 6. 生成时自检（7/7 PASS）

| 检查项 | 结果 | 实测 |
|---|---|---|
| 工位两两不重叠 | PASS | 23 工位 / 23 唯一格 |
| 工位在所属区域内 | PASS | 23 全查 |
| 工位格可通行 | PASS | 全部 |
| 朝向指向桌子/墙（非通行格） | PASS | 0 违规 |
| 每个工位从本区门可达 | PASS | 0 不可达 |
| 门同时贴走廊与区域内侧 | PASS | 10 区 |
| 工位数 ≥ 编制 | PASS | 2≥2 / 3≥3 / 3≥3 …；会议室、茶水间 0 |

可达性用 BFS 实测，不是就能性判断 —— 改任何一个矩形或门位置，重跑会立刻报错。

---

## 7. 上屏状态（已出件，非待办）

1. **Tiled 图**：`assets/office-map.tmj`（Tiled 1.11，53×24，3 个 tilelayer + 对象层 10 zone + 23 seat），tileset 引 `assets/office-tileset.png`（128×128，12 gid）。
2. **sprite**：`assets/agents.png`（288×384，9 列 = 3 配色 × 3 帧，8 行 = 4 朝向 × 空闲/行走，单元 32×48）。
3. **走动路径**：`demo/walk-grid.json` 由同一张 walkable 网格导出，数据同源，不会出现"人穿墙"。
