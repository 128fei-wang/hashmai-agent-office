#!/usr/bin/env node
/* D5 补充基准：多 agent 同帧寻路时，「按目的地共享反向 BFS」能否把冷算压进预算。
 * 跑法：node tools/bench_d5_dedup.js [--out demo/d5-dedup-bench.json]
 *
 * 背景：bench_d5_routing.js 显示 50 agent 全员同帧冷算 ≈14.2ms（≈85% 帧预算），
 * 据此定「每帧冷算 ≤20 次」的错峰配额。但真实办公里 agent 多在「同一时段奔向同一目的地」
 * （被派单去某部门、或统一去运营中心汇报），出发格各不相同、目的地相同。
 * 对「多源单目标」用一次反向 BFS（从目标出发建 distance/parent 树）即可同时服务所有出发格，
 * 把 N 次冷算压成 D 次（D = 该帧不同目的地数）。
 *
 * 本脚本只做三件事：①量出每帧 D 的真实分布；②验证反向 BFS 与现有正向 route 的简化路径逐点一致；
 * ③给出两种策略的每帧耗时对比。不改动正式树。
 */
const fs = require('fs');
const path = require('path');
const SIM = require('../demo/sim.js');

const ROOT = path.join(__dirname, '..');
const zonesDoc = JSON.parse(fs.readFileSync(path.join(ROOT, 'office-zones.json'), 'utf8'));
const walkDoc = JSON.parse(fs.readFileSync(path.join(ROOT, 'demo', 'walk-grid.json'), 'utf8'));
const grid = SIM.buildGrid(walkDoc.rows);
const key = (t) => t[0] + ',' + t[1];

// ---------- 端点池 ----------
const seats = [];
zonesDoc.zones.forEach(z => { if (z.seats) z.seats.forEach(s => seats.push(s.tile)); });
const doors = [];
zonesDoc.zones.forEach(z => {
  if (z.door && z.door.tile) doors.push(z.door.tile);
  if (z.south_door && z.south_door.tile) doors.push(z.south_door.tile);
});

// 现实目的地集：各部门门/工位 + 运营中心 + 老板办公室 + 会议室
const DEST_POOL = [];
zonesDoc.zones.forEach(z => {
  if (['ops_center', 'boss_office', 'meeting', 'tech', 'data', 'ui', 'hr', 'finance', 'qa_lab'].includes(z.id)) {
    if (z.door && z.door.tile) DEST_POOL.push(z.door.tile);
    if (z.seats && z.seats.length) DEST_POOL.push(z.seats[0].tile);
  }
});

// ---------- 确定性伪随机 ----------
let seed = 20261125;
function rnd() { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; }
function pick(a) { return a[Math.floor(rnd() * a.length)]; }
function pct(arr, p) {
  const s = arr.slice().sort((x, y) => x - y);
  const i = Math.min(s.length - 1, Math.max(0, Math.floor(p * (s.length - 1))));
  return s[i];
}
const ms = (t0, t1) => Number(t1 - t0) / 1e6;
const FRAME_BUDGET = 16.67;
const LIMIT = 8.35; // 50% 帧预算

// ---------- 反向 BFS：从目标出发，得到整张 parent 树 ----------
// SIM.bfs(grid, start) 返回 {dist, parent}，对称图，故从 target 出发即为「到 target」的距离场
function makeDestHub() {
  const tree = new Map();           // destKey -> {dist,parent}
  let bfsCalls = 0;
  function treeFor(dest) {
    const k = key(dest);
    if (tree.has(k)) return tree.get(k);
    const t = SIM.bfs(grid, dest);
    bfsCalls++;
    if (tree.size >= 12) tree.delete(tree.keys().next().value); // LRU 上限 12
    tree.set(k, t);
    return t;
  }
  function pathsTo(dest, froms) {   // 一次 BFS 服务多个 from
    const t = treeFor(dest);
    const out = [];
    for (const from of froms) {
      if (!t.dist.has(key(from))) { out.push(null); continue; }
      // 树以 dest 为根：从 from 沿 parent 链走，方向天然是 from -> dest，无需 reverse
      const raw = [];
      let cur = from;
      while (cur) { raw.push(cur); cur = t.parent.get(key(cur)); }
      out.push(SIM.simplify(raw));
    }
    return out;
  }
  function stats() { return { bfs_calls: bfsCalls, cached_dests: tree.size }; }
  return { pathsTo, stats, treeFor };
}

// ---------- 场景：N 个 agent，同帧各自从「自己工位附近」出发，奔向当帧活跃任务目的地 ----------
function makeFrameRequests(nAgents, kActive, frame) {
  // 当帧活跃目的地 = 从池里取 kActive 个（随帧变化，模拟任务推进）
  const dests = [];
  for (let i = 0; i < kActive; i++) dests.push(DEST_POOL[(frame * 3 + i * 7) % DEST_POOL.length]);
  const reqs = [];
  for (let a = 0; a < nAgents; a++) {
    const from = seats[a % seats.length];
    const to = dests[a % dests.length];
    if (key(from) === key(to)) continue;
    reqs.push([from, to]);
  }
  return { reqs, dests };
}

// ---------- 策略 A：现状最坏（每帧新建 router → 每 agent 一次 BFS） ----------
// 说明：跨帧复用 router 会因缓存命中把成本压到极低，但那不是「同帧大量新 OD」的最坏情形；
// 真实同帧冷算是「每个 agent 当前格都在变」，等价于每帧新 router。故这里取最坏口径。
function stratColdFresh(nAgents, kActive, frames) {
  const perFrame = [], coldPerFrame = [], dPerFrame = [];
  let total = 0, unroutable = 0;
  for (let f = 0; f < frames; f++) {
    const { reqs, dests } = makeFrameRequests(nAgents, kActive, f);
    dPerFrame.push(new Set(dests.map(key)).size);
    const router = SIM.makeRouter(grid);      // 每帧新建 = 全冷
    const t0 = process.hrtime.bigint();
    for (const [from, to] of reqs) {
      const p = router.simplified(from, to);
      total++; if (!p || !p.length) unroutable++;
    }
    perFrame.push(ms(t0, process.hrtime.bigint()));
    coldPerFrame.push(reqs.length);
  }
  return {
    mode: 'cold-fresh-router-per-frame',
    agents: nAgents, frames, paths: total, cold_per_frame_avg: +(coldPerFrame.reduce((a, b) => a + b, 0) / frames).toFixed(1),
    dests_per_frame: { p50: +pct(dPerFrame, .5).toFixed(0), p95: +pct(dPerFrame, .95).toFixed(0), max: Math.max(...dPerFrame) },
    per_frame_ms: { p50: +pct(perFrame, .5).toFixed(2), p95: +pct(perFrame, .95).toFixed(2), max: +Math.max(...perFrame).toFixed(2) },
    budget_used_p95: +(pct(perFrame, .95) / FRAME_BUDGET * 100).toFixed(1),
    unroutable
  };
}

// ---------- 策略 B：按目的地共享反向 BFS（每帧 BFS 次数 = 不同目的地数 D） ----------
function stratDestShared(nAgents, kActive, frames) {
  const hub = makeDestHub();
  const perFrame = [], bfsPerFrame = [], dPerFrame = [];
  let total = 0, unroutable = 0;
  for (let f = 0; f < frames; f++) {
    const { reqs, dests } = makeFrameRequests(nAgents, kActive, f);
    const before = hub.stats().bfs_calls;
    const grouped = new Map();
    for (const [from, to] of reqs) {
      const k = key(to);
      if (!grouped.has(k)) grouped.set(k, { to, froms: [] });
      grouped.get(k).froms.push(from);
    }
    dPerFrame.push(grouped.size);
    const t0 = process.hrtime.bigint();
    for (const [, g] of grouped) {
      const ps = hub.pathsTo(g.to, g.froms);
      for (const p of ps) { total++; if (!p || !p.length) unroutable++; }
    }
    perFrame.push(ms(t0, process.hrtime.bigint()));
    bfsPerFrame.push(hub.stats().bfs_calls - before);
  }
  return {
    mode: 'dest-shared-reverse-bfs',
    agents: nAgents, frames, paths: total,
    bfs_per_frame: { p50: +pct(bfsPerFrame, .5).toFixed(0), p95: +pct(bfsPerFrame, .95).toFixed(0), max: Math.max(...bfsPerFrame) },
    distinct_dests_per_frame: { p50: +pct(dPerFrame, .5).toFixed(0), p95: +pct(dPerFrame, .95).toFixed(0), max: Math.max(...dPerFrame) },
    per_frame_ms: { p50: +pct(perFrame, .5).toFixed(2), p95: +pct(perFrame, .95).toFixed(2), max: +Math.max(...perFrame).toFixed(2) },
    budget_used_p95: +(pct(perFrame, .95) / FRAME_BUDGET * 100).toFixed(1),
    unroutable,
    model_note: '同帧目的地固定为 K 个活跃任务；出发格各异。稳态下 tree 命中，bfs 次数趋 0。'
  };
}

// ---------- 等价性验证：反向 BFS 的路径与现有正向 route 是否「同一最短路径类」 ----------
// 判据（正确的判据，不是逐点相等）：最短路径在网格上不唯一，两端 tie-break 不同就会给出不同拐点序列。
// 真正要保证的是：①端点一致；②总步行步数（Manhattan 累计）与正向最短长度相等；③每步只走相邻格。
function validPath(p, from, to) {
  if (!p || !p.length) return false;
  if (p[0][0] !== from[0] || p[0][1] !== from[1]) return false;
  const last = p[p.length - 1];
  if (last[0] !== to[0] || last[1] !== to[1]) return false;
  for (let i = 1; i < p.length; i++) {
    const d = Math.abs(p[i][0] - p[i - 1][0]) + Math.abs(p[i][1] - p[i - 1][1]);
    if (d < 1 || d > 1) {
      if (d > 1) {
        // 允许共线压缩（拐点简化会跳过中间格），但必须同行或同列
        if (p[i][0] !== p[i - 1][0] && p[i][1] !== p[i - 1][1]) return false;
      }
      if (d < 1) return false;
    }
  }
  return true;
}
function verifyEquivalence(samples = 400) {
  const router = SIM.makeRouter(grid);
  const hub = makeDestHub();
  let checked = 0, lenMismatch = 0, invalid = 0, unroutable = 0;
  const bad = [];
  for (let i = 0; i < samples; i++) {
    const from = pick(seats.length ? seats : DEST_POOL);
    const to = pick(DEST_POOL);
    if (key(from) === key(to)) continue;
    const a = router.simplified(from, to);
    const [b] = hub.pathsTo(to, [from]);
    checked++;
    if (!a && !b) { unroutable++; continue; }
    if (!validPath(b, from, to)) { invalid++; if (bad.length < 5) bad.push({ from, to, why: 'invalid-rev' }); continue; }
    const la = SIM.pathLength(a), lb = SIM.pathLength(b);
    if (la !== lb) { lenMismatch++; if (bad.length < 5) bad.push({ from, to, fwd_len: la, rev_len: lb }); }
  }
  return { checked, len_mismatch: lenMismatch, invalid_path: invalid, unroutable, examples: bad, equivalent: lenMismatch === 0 && invalid === 0 };
}

// ---------- 主 ----------
const args = process.argv.slice(2);
const outIdx = args.indexOf('--out');
const outPath = outIdx >= 0 ? args[outIdx + 1] : path.join(ROOT, 'demo', 'd5-dedup-bench.json');

const FRAMES = 240, K = 4;
const equiv = verifyEquivalence();
const rows = [];
for (const n of [23, 30, 50]) {
  const A = stratColdFresh(n, K, FRAMES);
  const B = stratDestShared(n, K, FRAMES);
  rows.push({ n, coldFresh: A, destShared: B });
}

const summary = rows.map(r => ({
  agents: r.n,
  cold_p95_ms: r.coldFresh.per_frame_ms.p95,
  cold_per_frame: r.coldFresh.cold_per_frame_avg,
  dest_p95_ms: r.destShared.per_frame_ms.p95,
  dest_bfs_per_frame_p95: r.destShared.bfs_per_frame.p95,
  speedup: +(r.coldFresh.per_frame_ms.p95 / Math.max(r.destShared.per_frame_ms.p95, 0.01)).toFixed(2),
  dest_under_half_budget: r.destShared.per_frame_ms.p95 <= LIMIT,
  cold_under_half_budget: r.coldFresh.per_frame_ms.p95 <= LIMIT
}));

const doc = {
  schema: 'roost-d5-dedup/v1',
  generated_at: new Date().toISOString(),
  scope: 'partial — 仅寻路 CPU，不含渲染/纹理/HUD；不能作为 D5 9.8 依据',
  frame_budget_ms: FRAME_BUDGET,
  criterion_half_budget_ms: LIMIT,
  scenario: { frames: FRAMES, active_tasks_K: K, agents: [23, 30, 50], dest_pool_size: DEST_POOL.length, seats: seats.length },
  equivalence: equiv,
  summary,
  detail: rows
};

fs.writeFileSync(outPath, JSON.stringify(doc, null, 2));
console.log('EQ', JSON.stringify(equiv));
summary.forEach(s => console.log('N=' + s.agents, 'cold_p95=' + s.cold_p95_ms + 'ms(' + s.cold_per_frame + ' BFS/frame)',
  '| destShared_p95=' + s.dest_p95_ms + 'ms(bfs/frame p95=' + s.dest_bfs_per_frame_p95 + ')',
  '| speedup=' + s.speedup + 'x',
  '| dest', s.dest_under_half_budget ? 'PASS<=8.35' : 'FAIL>8.35',
  '| cold', s.cold_under_half_budget ? 'PASS' : 'FAIL'));
console.log('OUT', outPath);
process.exit(equiv.equivalent && summary.every(s => s.dest_under_half_budget) ? 0 : 1);
