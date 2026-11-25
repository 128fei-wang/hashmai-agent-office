# 工位编号统一补丁（PATCH-01）

状态：**已在副本上预演通过，未动 v0.6 基线**
预演时间：2026-11-24 07:35Z｜副本 `/tmp/roost-seatpatch`（正式树未改一字节）
预演结果：`A6 牌面 == seat_id 序号段 偏移集合 [0]`、`SUMMARY seats=23 zones=8 fail=0 rc=0`、`tools/test_sim.js` 9/9 PASS

## 1. 为什么之前 A6 永远过不了（本轮新发现）

`tools/check_seat_ids.py` 的 A6 并不解析模板里真实的牌面文案，它只做两件事：
- 用 `i + 1` 当作「牌面号」；
- 用 `seat_id` 末尾两位当作「席位号」；
- 两者相减 → 偏移恒为 **1**（因为 `seat_id` 是 0 起，牌面是 1 起）。

所以**只改模板牌面文案，A6 照样 FAIL**。必须同时修 A6 的判定逻辑（见 3.3），否则 `--require-unified` 这道门槛永远返 1。这是此前把统一拖成「文档层」的直接原因之一。

## 2. 改动清单（3 处代码 + 1 条重建链）

| # | 文件 | 位置 | 改动 |
|---|------|------|------|
| 1 | `demo/office-demo.template.html` | 第 296 行（Pixi 牌面） | 牌面文案改取 `seat_id` 序号段 |
| 2 | 同上 | 第 313 行（2D 牌面） | 同上，2D 降级路径必须同步 |
| 3 | `tools/check_seat_ids.py` | A5 的 `t_plate` 正则 + A6 的 `offs` 计算 | 认可 `'-S'` 形态，偏移按模板真实取法计算 |
| 4 | — | — | 重建 `office-demo.html` → 重跑 D6 → 重算 SUMS → 通知 DS 新 sha |

`tech-A2` 这类内部 id **不动**（第 287 行保留），只作内存索引；对外显示统一为 `技术-S02`。

## 3. 精确补丁（已预演，可直接套用）

### 3.1 第 296 行（Pixi）

改前：
```js
const label = new PIXI.Text({ text: z.name.slice(0, 2) + '-' + String(i + 1).padStart(2, '0'),
```
改后：
```js
const label = new PIXI.Text({ text: z.name.slice(0, 2) + '-S' + (s.seat_id.split('-S')[1] || String(i).padStart(2, '0')),
```

### 3.2 第 313 行（2D 降级）

改前：
```js
a.label = { text: z.name.slice(0, 2) + '-' + String(i + 1).padStart(2, '0') };
```
改后：
```js
a.label = { text: z.name.slice(0, 2) + '-S' + (s.seat_id.split('-S')[1] || String(i).padStart(2, '0')) };
```

> 取 `s.seat_id` 而非 `i`，是为了以后席位表重排也不会再错位；`||` 分支仅为 `seat_id` 缺后缀时兜底。

### 3.3 `tools/check_seat_ids.py`

A5 的牌面正则改前：
```python
t_plate = bool(re.search(r"z\.name\.slice\(0,\s*2\).*String\(i\s*\+\s*1\)", tpl))
```
改后：
```python
t_plate = bool(re.search(r"z\.name\.slice\(0,\s*2\).*'-S'.*seat_id", tpl))
```

A6 的偏移计算改前：
```python
    offs = []
    for z in live:
        for i, s in enumerate(z['seats'][:z['headcount']]):
            plate_no = i + 1
            seat_no = int(s['seat_id'].split('-S')[-1])
            offs.append(plate_no - seat_no)
```
改后：
```python
    # 牌面若直接取 seat_id 序号段（'-S' 形态），则偏移恒为 0
    plate_by_seat = bool(re.search(r"z\.name\.slice\(0,\s*2\).*'-S'.*seat_id", tpl))
    offs = []
    for z in live:
        for i, s in enumerate(z['seats'][:z['headcount']]):
            plate_no = int(s['seat_id'].split('-S')[-1]) if plate_by_seat else i + 1
            seat_no = int(s['seat_id'].split('-S')[-1])
            offs.append(plate_no - seat_no)
```

## 4. 预演证据（副本实测）

```
$ python3 tools/build_demo.py
grid 53×24 walkable 698
zones 10 seats 23
html .../demo/office-demo.html 75332 B (payload 6311 B)

$ python3 tools/check_seat_ids.py --require-unified
PASS  A1 seat_id 格式与前缀  23 席，坏件 无
PASS  A2 seat_id 唯一  共 23 个，重复 0
PASS  A3 每部门 <=3 席  超编 无
PASS  A4 席数 == declared_total  实得 23 / 声明 23
PASS  A5 模板生成逻辑在位  agent_id=True plate=True headcount截断=True
PASS  A6 牌面 == seat_id 序号段  偏移集合 [0]
SUMMARY seats=23 zones=8 fail=0     rc=0

$ node tools/test_sim.js
PASS all_seats_reachable | 23 seats, unreachable
PASS paths_stepwise_valid | invalid
PASS simplified_legs_walkable | broken
PASS py_js_route_agree | mismatch
PASS assign_count | 23 vs 23
PASS assign_unique_seats |
PASS reporting_routes_exist | tech:14 data:9 ui:28 hr:24 finance:19 qa_lab:38
PASS — 9/9            rc=0
```

注：改前模板 `office-demo.html` 为 75,278 B，打补丁后 75,332 B（+54 B，仅牌面字符串差异）。

## 5. 正式落地时必须做的四步（缺一不可）

1. **重建**：`python3 tools/build_demo.py`
2. **D6 重跑**（牌面文案变化会让 `nonblank_ratio` 轻微漂移，必须重新取证）：
   - 页面自检 `?selfcheck=1` → `demo/d6-page-selfcheck-pixi.json`
   - fps 探针 `?probe=fps&frames=300&warm=90&port=8791` → `demo/d6-fps-probe.json`
   - 2D 降级 `?selfcheck=1&force2d=1` → `demo/d6-page-selfcheck-2d.json`
   - `p98check.py --dim d6 --artifact d6-page-selfcheck.json` 需 5/5
3. **SUMS 重算**（契约包 16 件）：
   `find . -type f ! -name SHA256SUMS.txt | sed 's|^\./||' | sort | xargs shasum -a 256 > SHA256SUMS.txt`，再 `shasum -a 256 -c SHA256SUMS.txt` 应 16/16 OK
4. **告知 DS 新 sha**：`demo/office-demo.html` 与 `d6-page-selfcheck.json` 两项 sha 变化；DS 已判 v0.6「D6 5/5 定稿不用重跑」，落地即作废该基线，**必须由 DS 重认一次**才算数。

## 6. 建议合入时点

**与 CC2 的 12 事件流接入同批合入**（同一次重建、一次重跑、一次 SUMS、一次 DS 认账），避免为了 +54 B 的字符串改动单独作废已验收基线。CC2 的工位绑定上线前必须先跑 `--require-unified` 拿到 fail=0，否则事件里的 `seat_id` 与画面牌面又是两套。

## 7. 未做

- 未修改正式树任何文件（本轮只读 + 副本预演）。
- 未重跑 D6、未重算契约包 SUMS（等待合入窗口）。
- 底部流水条目前是「01 下发 / 02 拆单 / 03 执行 …」阶段名，不含工位号，本次无需改；将来若加「哪一席」需同步套用本节 3.1 的取法。

## 八、可执行形态（2026-11-24 09:20Z 补充）

- 补丁文本已固化为标准 diff：`patches/PATCH-01-seat-id.diff`（42 行，仅动 `demo/office-demo.template.html` 与 `tools/check_seat_ids.py` 两个文件）。
- 合入脚本：`tools/apply_patch_01.sh`
  - `sh tools/apply_patch_01.sh` 预演（`patch --dry-run`，不改任何文件）——已实测通过；
  - `sh tools/apply_patch_01.sh --apply` 真合入：备份 `.bak.<ts>` → 打补丁 → `build_demo.py` 重建 → `check_seat_ids --require-unified` + `test_sim.js` 全量校验。
- 预演时正式树未改：`demo/office-demo.template.html` sha 前 16 `d12e43a442b16329`、`tools/check_seat_ids.py` sha 前 16 `6c19c3980d5753cc`、`demo/office-demo.html` 仍是 75,278 B。
- 合入后仍需两步才算收口：重取 D6 三件证据（page-selfcheck / fps-probe / 2D 自检）+ 重算契约包 `SHA256SUMS.txt`，再请 DS 原样复跑。
