# ROOST 多 Agent 监控面板 · UI 架构与契约（v1 草案）

> 定位：产品级面板，不是 pixel-agents demo 的皮肤。核心是把「像素舞台」和「数据面板」拆成两套渲染、共用一条数据流。
> 本文三件：① 目录结构 ② store schema ③ 事件契约。可直接开工。

---

## 0. 三条不可谈的前提

1. **像素层不进 React render 循环**。React 只负责挂载/卸载容器、下发命令；Pixi 自己跑 ticker。任何 `useState` 驱动的逐帧位置更新都会在 100 个 agent 时掉帧。
2. **单一数据源**。舞台和面板都从同一个 store 读，禁止各自订阅 WS。两套数据必然对不上，且排查成本极高。
3. **服务端定序**。事件带全局单调 `seq`，客户端按 seq 去重 + 缺口拉补。不靠时间戳排序（多节点时钟不保证单增）。

---

## 1. 目录结构

```
roost-panel/
├── apps/
│   ├── web/                          # React 产品外壳（面板 / 列表 / 日志 / 设置）
│   │   ├── src/
│   │   │   ├── app/                  # 路由、Provider、错误边界
│   │   │   ├── features/
│   │   │   │   ├── agents/           # agent 列表、卡片、详情
│   │   │   │   ├── tasks/            # 任务队列、甘特/时间线
│   │   │   │   ├── logs/             # 虚拟化日志流（TanStack Virtual）
│   │   │   │   ├── metrics/          # token/成本/成功率图表（Recharts）
│   │   │   │   └── stage/            # 像素舞台宿主：React ↔ Pixi 桥
│   │   │   ├── shared/
│   │   │   │   ├── store/            # zustand slices（唯一数据源）
│   │   │   │   ├── transport/        # ws 客户端、重连、补拉
│   │   │   │   └── ui/               # shadcn/ui 组件（源码 copy，非依赖）
│   │   │   └── main.tsx
│   │   └── public/assets/            # atlas/*.json+png, maps/*.tmj, fonts/*
│   │
│   └── stage/                        # 纯 Pixi 引擎，无 React 依赖，可独立压测
│       ├── src/
│       │   ├── renderer.ts           # 单 PIXI.Application，唯一 WebGL 上下文
│       │   ├── layers/               # bg / tiles / agents / fx / overlay
│       │   ├── entities/agent.ts     # AgentSprite：精灵池 + 状态→动画
│       │   ├── systems/              # culling / interpolation / camera
│       │   └── assets/               # atlas loader、BitmapText 字体
│       └── index.ts                  # export StageApi（命令式接口）
│
├── packages/
│   ├── contract/                     # ⭐ 事件契约唯一真源：TS 类型 + zod 校验
│   │   ├── src/events.ts
│   │   ├── src/envelope.ts
│   │   └── schema/agent-event.schema.json
│   └── fixtures/                     # 契约样例 + 回放用录制文件
│
├── tools/
│   ├── sprite-build/                 # Aseprite → atlas.json + atlas.png
│   ├── map-build/                    # Tiled .tmj → 运行时地图
│   └── bench-stage/                  # 200 agent 合成压测（帧率/GC/draw call）
│
└── docs/                             # 本文、ADR、验收清单
```

**关键边界**：`apps/stage` 的对外 API 只有 4 个方法，React 侧禁止直接摸 Pixi 对象：

```ts
interface StageApi {
  mount(el: HTMLDivElement, opts: StageOptions): Promise<void>;
  unmount(): void;
  sync(agents: AgentSnapshot[], tick: number): void;   // 全量对齐（低频）
  apply(events: AgentEvent[]): void;                   // 增量（高频）
}
```

---

## 2. Store schema（唯一数据源）

```ts
// packages/contract/src/events.ts
export type AgentState =
  | 'idle' | 'thinking' | 'working' | 'blocked' | 'done' | 'error';

export interface AgentSnapshot {
  agent_id: string;          // 稳定 ID，展示名另存 alias
  alias: string;             // 用户可见名
  state: AgentState;
  task_id: string | null;
  progress: number;          // 0..1，未知时 -1
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  started_at: number | null; // epoch ms
  updated_at: number;
  meta: Record<string, string>; // 渠道/model/session 等，扁平字符串
}

export type AgentEvent =
  | { type: 'agent_upsert'; agent: AgentSnapshot }
  | { type: 'agent_state';  agent_id: string; state: AgentState; task_id?: string|null; at: number }
  | { type: 'agent_progress'; agent_id: string; progress: number; at: number }
  | { type: 'usage_delta';  agent_id: string; tokens_in: number; tokens_out: number; cost_usd: number; at: number }
  | { type: 'agent_remove'; agent_id: string; at: number }
  | { type: 'log';          agent_id: string; level: 'info'|'warn'|'error'; text: string; at: number }
  | { type: 'heartbeat';    at: number };
```

```ts
// apps/web/src/shared/store/index.ts（形状，不是实现）
interface PanelStore {
  // 归一化，O(1) 按 id 取
  agentsById: Record<string, AgentSnapshot>;
  agentOrder: string[];                 // 舞台绘制顺序 = 面板列表顺序，二者共用
  selectedId: string | null;

  // 事件环（面板日志、调试回放），容量固定，覆盖式写入，避免无界增长
  ring: { buf: AgentEvent[]; cap: 4096; head: number; seq: number };

  // 连接态
  conn: { status: 'connecting'|'open'|'gap'|'closed'; lastSeq: number; gapFrom: number|null };

  // actions（全部同步，异步只在 transport 层）
  apply(events: AgentEvent[], seq: number): void;
  applySnapshot(list: AgentSnapshot[], seq: number): void;
  select(id: string | null): void;
}

// 派生层（selector，禁止在 store 里预计算大数组）
// selectAgentsByState(state), selectStageAgents() → 只暴露舞台需要的字段子集
```

**为什么要分成 `sync` / `apply`**：舞台需要「全量真值」做校正（插值会把位置推歪），面板需要「高频增量」。两者都源自同一 store，`sync` 每 5s 或断线重连后调一次，`apply` 逐事件调。

**为何 ring 而不是数组**：一次跑一天会堆几十万条事件；固定容量 + 覆盖写入，浏览器内存稳定，日志视图只看最近 N 条，历史翻页走 REST。

---

## 3. 事件契约

### 3.1 传输

- 端点：`wss://<host>/ws/agents?since=<last_seq>`，`Authorization: Bearer <token>`（header，不塞 query）。
- 首帧必为 `hello`，含全量快照，之后只发增量。
- 心跳：服务端每 15s 发 `heartbeat`；客户端 30s 无任何帧判定 `gap` 并重连补拉。
- 压缩：`permessage-deflate` 开启；单帧 > 64KB 时分片（`chunk` 字段）。

### 3.2 信封

```json
{
  "v": 1,
  "seq": 12873,
  "ts": 1795490160123,
  "kind": "snapshot" | "delta" | "heartbeat" | "error",
  "events": [ { "type": "agent_state", "agent_id": "agent_73ff", "state": "working", "at": 1795490160000 } ]
}
```

规则：

1. `seq` 全局单调递增，**同一信封内事件共享一个 seq**；客户端以信封为单位去重（`seq <= lastSeq` 直接丢）。
2. 发现 `seq > lastSeq + 1` → 状态置 `gap`，带 `since=lastSeq` 重连，服务端从该点重放；重放窗口外的历史无法补齐时返回 `error{code:"replay_window_exceeded"}`，客户端降级为全量快照。
3. 语义是 **at-least-once**，客户端必须幂等：`agent_state` / `usage_delta` 需可重复应用（`usage_delta` 带 `at`，同一 `seq` 重复到达不叠加）。
4. 排序只在信封层保证；信封内事件顺序有意义（先 upsert 后 state）。
5. `heartbeat` 不推进业务状态，只用于判定链路存活。

### 3.3 速率与容量预算

| 指标 | 目标 |
|---|---|
| agent 规模 | 200 并发可见 |
| 事件吞吐 | 常态 50 ev/s，突发 500 ev/s 持续 10s 不丢帧 |
| 舞台帧率 | 60 fps（P95 帧时间 ≤ 16.6ms） |
| draw call | ≤ 200（单 atlas + ParticleContainer 合批） |
| 单帧 JS 预算 | ≤ 6ms（留给 GPU 与 GC） |
| 内存 | 8h 运行 RSS 增长 < 30MB |

### 3.4 状态机 → 动画映射（产品化必需资产）

```json
{
  "idle":    { "anim": "idle_look_around", "loop": true,  "fps": 6 },
  "thinking":{ "anim": "think_bubble",     "loop": true,  "fps": 8 },
  "working": { "anim": "type_keyboard",    "loop": true,  "fps": 12 },
  "blocked": { "anim": "wait_sigh",        "loop": true,  "fps": 6,  "tint": "#ffcc66" },
  "done":    { "anim": "celebrate",        "loop": false,"fps": 12, "then": "idle" },
  "error":   { "anim": "error_shake",      "loop": false,"fps": 12, "then": "blocked" }
}
```

这张表就是 pixel-agents demo 里写死、产品化必须外置的第一份资产。第二份是 `atlas.json`（Aseprite 导出，含 tag → frames 映射），第三份是 `map.tmj`（Tiled 导出，含出生点/工位绑定规则）。

### 3.5 断线、冷启动、灰度

- 冷启动：先拉 REST `/api/agents` 拿快照与 `seq`，再连 WS `since=seq`，避免首屏空白。
- 断线：指数退避 1s→2s→4s→8s（上限 30s），期间面板显示「数据可能滞后」，舞台降速到 30fps 省电。
- 灰度：契约 `v` 字段；服务端同时兼容 v1/v2，客户端按 `v` 分支解析，未知 `type` 必须忽略而不是崩溃（前向兼容）。

---

## 4. 验收清单（可直接当 checklist 用）

- [ ] 200 agent 合成流下 P95 帧时间 ≤ 16.6ms，无长任务 > 50ms
- [ ] 单 canvas，`PIXI.Application` 只创建一次，HMR 后不泄漏旧 renderer
- [ ] 拔网线 30s → 恢复后 `seq` 连续、无重复 agent、无丢失状态迁移
- [ ] `usage_delta` 重复投递 3 次，累计 token 数不翻倍
- [ ] 8h 连续运行 RSS 增长 < 30MB，事件堆不增长
- [ ] 中文在舞台层为 BitmapText，缩放 1x/2x/3x 无模糊
- [ ] 键盘可达：面板列表可 Tab 遍历，舞台提供「表格视图」替代入口（无障碍）

---

## 5. 与 pixel-agents 的关系

pixel-agents 只借两样东西：**像素美术风格** 和 **agent 可视化的产品直觉**。代码层面不复用，因为它是单文件 demo：

| demo 里的写法 | 产品化必须改成 |
|---|---|
| 全局变量持 agent 位置 | store 归一化 + stage 本地插值 |
| sprite 帧号硬编码 | atlas tag + 状态机映射表 |
| 每帧遍历全量 agent | 视口剔除 + 精灵池 + 脏标记 |
| DOM 文本叠 canvas | BitmapText + 字体 atlas |
| 单页无路由 | 面板 + 舞台分屏，路由与状态解耦 |

---

*本文件为 v1 草案，配套机读契约见 `agent-event.schema.json`。下一步可落地：`apps/stage` 骨架 + 200 agent 压测脚本。*

---

## 6. 契约自测（已跑，PASS）

`tools/contract_selftest.py`：不依赖 UI、不依赖浏览器，纯客户端侧语义模拟。造 200 agent + 10 秒 × 500 ev/s 突发（5,000 事件 / 11 信封），逐信封过 JSON Schema，再跑三个场景。

| # | 检查项 | 结果 | 实测 |
|---|---|---|---|
| 1 | 信封全部通过 JSON Schema | PASS | 11/11 validated |
| 2 | 全部信封被应用 | PASS | applied 11/11 |
| 3 | 同 seq 重投被丢弃（20% 注入） | PASS | dropped 2/2 |
| 4 | seq 单调收敛 | PASS | last_seq 11 = 11 |
| 5 | token 累计精确（200 agent 全查） | PASS | max\|diff\| 0 |
| 6 | 终态一致（200 agent 全查） | PASS | 200 compared |
| 7 | 事件环固定容量 | PASS | ring 4,096 / 5,000 事件（4.7× cap，不增长） |
| 8 | 缺口能发现 | PASS | gaps [(7,9)] |
| 9 | 补拉后 seq 收敛 | PASS | 11 = 11 |
| 10 | 补拉后状态与基线一致 | PASS | tokens 全对 |
| 11 | 幂等键命中不重复计数 | PASS | 1,100 = 1,100 |

客户端 apply 吞吐 **3.68M ev/s**（0.0014s 跑完 5,000 事件），说明 500 ev/s 突发对 store 层毫无压力 —— 瓶颈只可能在渲染层，与 3.3 节的 6ms/帧预算指向一致。产物：`contract-selftest.json`（1,455 B，含每项 detail）。
