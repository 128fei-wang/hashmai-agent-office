# D5 寻路：目的地共享反向 BFS（PATCH-02 候选）

**结论：比「每帧冷算 ≤20 次」的错峰配额更省——把「多源单目标」的冷算从 N 次压到 D 次。50 agent 每帧 p95 从 12.11ms 降到 1.29ms（9.39x），全部落进 50% 帧预算（≤8.35ms），且路径长度与现有正向路由逐例等价（392/392）。**

- 件：`tools/bench_d5_dedup.js` → `demo/d5-dedup-bench.json`（4,668 B）
- 补丁候选：`patches/PATCH-02-dest-shared-route.diff`（45 行，只改 `demo/office-demo.template.html`）
- 状态：**未合入正式树**（与 PATCH-01 同批，合入后需重取 D6 三件证据 + 重算 SUMS）
- 判级：仍属 **D5 partial**（不含渲染/纹理上传/HUD），不能据此判 9.8

---

## 1. 为什么这条路成立

`bench_d5_routing.js` 的 cold 口径是「每个 agent 各建一个 router，各自跑一次 BFS」，于是 50 agent 一帧 = 50 次 BFS ≈ 12–14ms（≈73–85% 帧预算）。据此我曾给出「每帧冷算 ≤20 次」的错峰配额。

但真实办公场景不是 50 个互不相干的 OD：一个时段里，agent 往往**奔向少数几个目的地**（被派单去某部门、统一去运营中心汇报、回自己工位），**出发格各异、目的地相同**。这是「多源单目标」结构。网格 BFS 是对称的——从目标出发建一次距离/父指针树，就能同时回答所有出发格到该目标的最短路径。故成本从 N 次 BFS 变为 **D 次 BFS（D = 该帧不同目的地数）**。

## 2. 实测（240 帧 × 每帧 N agent，K=4 活跃任务、目的地随帧推进）

| agent | 现状（每帧全冷）p95 | 目的地共享 p95 | 提速 | 目的地共享占帧预算 | 判定 |
|---:|---:|---:|---:|---:|---|
| 23 | 5.88 ms（22.5 BFS/帧） | **1.17 ms** | 5.03x | 7.0% | PASS ≤8.35 |
| 30 | 7.31 ms（29.4 BFS/帧） | **1.21 ms** | 6.04x | 7.3% | PASS ≤8.35 |
| 50 | 12.11 ms（48.9 BFS/帧） | **1.29 ms** | 9.39x | 7.7% | **PASS ≤8.35**（现状 FAIL）|

- 目的地树 LRU 上限 12，跨帧命中后每帧实际 BFS 次数 p95 = **2**（多数帧为 0–2）。
- `unroutable = 0`。
- 说明：这是「同帧目的地集中」的模型。若某帧 50 agent 各奔完全不同的 50 个目的地（D=50），本优化退化为原成本——那时才需要错峰配额。两条措施不互斥：**先按目的地合并，剩下的残余冷算再错峰**。

## 3. 等价性（关键，不能只看速度）

最短路径在网格上不唯一，正向 BFS 与反向 BFS 的 tie-break 不同，**逐点比对必然不等**（首版脚本就误用逐点相等，报 392/392 不符，属判据错不是实现错）。正确判据是：

1. 端点一致（首点=from、末点=to）；
2. 总步行步数（Manhattan 累计）与正向最短长度相等；
3. 拐点之间只走同行或同列（无对角穿越）。

结果：`checked=392`、`len_mismatch=0`、`invalid_path=0`、`unroutable=0` → **equivalent=true**。

## 4. 补丁内容与预演

`patches/PATCH-02-dest-shared-route.diff` 两处：

1. 第 92 行 `const router = SIM.makeRouter(grid);` → 换成一个自包含的 `RHUB`（`treeFor` 带 LRU、`route(from,to)` 同步返回简化路径）。**全同步、无 Promise、不引入 await**，故 `chain()`/`route()` 的调用形态完全不变。
2. `route()` 内 `router.simplified(from, to)` → `RHUB.route(from, to)`。

预演（干净副本 `/tmp/dry2`，非正式树）：
```
patch -p0 --dry-run < patches/PATCH-02-dest-shared-route.diff   → patching file ... (rc=0)
patch -p0        < patches/PATCH-02-dest-shared-route.diff      → OK
python3 tools/build_demo.py                                     → html 76,482 B（payload 6,311 B）
node tools/test_sim.js                                          → PASS 9/9（含 py_js_route_agree）
```
- 模板 +1,045 字符（49,094 → 50,139）；产物 html 由 75,278 B 变 76,482 B（+1,204 B）。
- `check_seat_ids.py --require-unified` 在副本上仍是 A6 FAIL（偏移集合 [1]）——**这是 PATCH-01 未合入的既有状态，与 PATCH-02 无关**，同批合入后应回 PASS。

## 5. 合入纪律（与 PATCH-01 同一批）

单个补丁不合，理由与 PATCH-01 相同：正式树一旦动，已验收的 D6 5/5 基线与契约包 16/16 SUMS 都会失效。合入顺序：

1. `patch -p0` 依次打 PATCH-01、PATCH-02（两者改的是模板不同位置，无冲突）；
2. `python3 tools/build_demo.py`；
3. `python3 tools/check_seat_ids.py --require-unified`（要求 rc=0、A1–A6 全 PASS）；
4. `node tools/test_sim.js`（9/9）；
5. 重取 D6 三件证据（`d6-page-selfcheck-pixi.json`、`d6-fps-probe.json`、2D 件）；
6. 重算契约包 `SHA256SUMS.txt` 并全量 `shasum -a 256 -c`；
7. 交 DS 重认。

在 1–7 全部完成前，**正式树保持不动**，D5 仍记 `partial`。

## 6. 复跑

```
cd /Users/hashmai/roost-im/roost-ui-arch
node tools/bench_d5_dedup.js          # 输出 demo/d5-dedup-bench.json；等价性失败或超预算则 rc=1
```

---

## 7. 同批合入合演结果（10:42Z，副本 `/tmp/merge12`，正式树未动）

PATCH-01 与 PATCH-02 改的是同一份模板的不同位置，**顺序打、零冲突、零 .rej**：

```
patch -p0 < patches/PATCH-01-seat-id.diff            rc=0（template + check_seat_ids.py）
patch -p0 < patches/PATCH-02-dest-shared-route.diff  rc=0（template）
python3 tools/build_demo.py        → html 76,536 B（payload 6,311 B）
python3 tools/check_seat_ids.py --require-unified → SUMMARY seats=23 zones=8 fail=0，A6 偏移集合 [0]，rc=0
node tools/test_sim.js             → PASS — 9/9，rc=0
```

- 体积推演闭合：75,278（基线）+ 54（P1）+ 1,204（P2）= **76,536 B**，与实测一致。
- 关键：**只有两个补丁同时在场，A6 偏移集合才是 [0]**（单打 P2 仍是 [1]、单打 P1 时 P2 未合也回 PASS 但模板里没有目的地共享）。故两条必须同批，不能拆。
- 合入正式树仍是最后一步，前置条件已全绿：`demo/office-demo.html` 将变 76,536 B，之后必须重取 D6 三件证据 + 重算契约包 16 件 SUMS + 交 DS 重认。
