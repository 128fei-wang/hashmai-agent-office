#!/usr/bin/env node
/* D5 部分负载基准（仅寻路/状态机 CPU，不含渲染）
 * 跑法：node tools/bench_d5_routing.js [--out demo/d5-routing-bench.json]
 * 两个口径：
 *   warm —— 路由缓存命中（稳态，同一批 OD 反复走，接近真实「来回巡逻/复走」）
 *   cold —— 每单新建 router（BFS 全量，最坏情况：每帧全新 OD）
 * 用途：为 D5（30–50 agent）给出可复跑的非渲染证据；不能替代渲染实测，判级标签 partial。
 */
const fs = require('fs');
const path = require('path');
const SIM = require('../demo/sim.js');

const ROOT = path.join(__dirname, '..');
const zonesDoc = JSON.parse(fs.readFileSync(path.join(ROOT, 'office-zones.json'), 'utf8'));
const walkDoc = JSON.parse(fs.readFileSync(path.join(ROOT, 'demo', 'walk-grid.json'), 'utf8'));
const grid = SIM.buildGrid(walkDoc.rows);

// 端点池：工位 + 门 + 走廊抽样点
const points = [];
zonesDoc.zones.forEach(z => {
  if (z.seats) z.seats.forEach(s => points.push(s.tile));
  if (z.door && z.door.tile) points.push(z.door.tile);
  if (z.south_door && z.south_door.tile) points.push(z.south_door.tile);
});
for (let x = 3; x < zonesDoc.grid.w - 3; x += 5) { points.push([x, 7]); points.push([x, 15]); }

let seed = 20261125;
function rnd() { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; }
function pick() { return points[Math.floor(rnd() * points.length)]; }
function pct(arr, p) {
  const s = arr.slice().sort((a, b) => a - b);
  const i = Math.min(s.length - 1, Math.max(0, Math.floor(p * (s.length - 1))));
  return s[i];
}
const ms = (t0, t1) => Number(t1 - t0) / 1e6;

// warm：共享 router，缓存命中
function benchWarm(nAgents, frames) {
  const router = SIM.makeRouter(grid);
  for (let i = 0; i < nAgents; i++) router.simplified(pick(), pick());  // 预热 + 填缓存
  const perFrame = [], perPath = [];
  let paths = 0, unroutable = 0;
  const t0 = process.hrtime.bigint();
  for (let f = 0; f < frames; f++) {
    const fs0 = process.hrtime.bigint();
    for (let a = 0; a < nAgents; a++) {
      const from = pick(), to = pick();
      const p1 = process.hrtime.bigint();
      const p = router.simplified(from, to);
      perPath.push(ms(p1, process.hrtime.bigint()));
      paths++; if (!p || !p.length) unroutable++;
    }
    perFrame.push(ms(fs0, process.hrtime.bigint()));
  }
  const total = ms(t0, process.hrtime.bigint());
  return {
    mode: 'warm', agents: nAgents, frames, paths, unroutable,
    total_ms: +total.toFixed(1), paths_per_sec: +(paths / (total / 1000)).toFixed(0),
    per_path_ms: { p50: +pct(perPath, .5).toFixed(4), p95: +pct(perPath, .95).toFixed(4), p99: +pct(perPath, .99).toFixed(4), max: +Math.max(...perPath).toFixed(4) },
    per_frame_ms: { p50: +pct(perFrame, .5).toFixed(3), p95: +pct(perFrame, .95).toFixed(3), p99: +pct(perFrame, .99).toFixed(3), max: +Math.max(...perFrame).toFixed(3), budget_16_7ms_used_p95: +(pct(perFrame, .95) / 16.67 * 100).toFixed(1) }
  };
}

// cold：每单新建 router，强制 BFS
function benchCold(nAgents, samplesPerAgent) {
  const perPath = [];
  let unroutable = 0, paths = 0;
  const t0 = process.hrtime.bigint();
  for (let a = 0; a < nAgents; a++) {
    for (let k = 0; k < samplesPerAgent; k++) {
      const router = SIM.makeRouter(grid);
      const from = pick(), to = pick();
      const p1 = process.hrtime.bigint();
      const p = router.simplified(from, to);
      perPath.push(ms(p1, process.hrtime.bigint()));
      paths++; if (!p || !p.length) unroutable++;
    }
  }
  const total = ms(t0, process.hrtime.bigint());
  const perAgentAvg = total / nAgents;
  return {
    mode: 'cold', agents: nAgents, paths, unroutable,
    total_ms: +total.toFixed(1), paths_per_sec: +(paths / (total / 1000)).toFixed(0),
    per_path_ms: { p50: +pct(perPath, .5).toFixed(3), p95: +pct(perPath, .95).toFixed(3), p99: +pct(perPath, .99).toFixed(3), max: +Math.max(...perPath).toFixed(3) },
    cost_if_all_agents_repath_in_one_frame_ms: +perAgentAvg.toFixed(2)
  };
}

const scales = [23, 30, 50];
const results = { warm: [], cold: [] };
scales.forEach(n => { results.warm.push(benchWarm(n, 240)); results.cold.push(benchCold(n, 60)); });

const out = {
  artifact: 'd5-routing-bench',
  generated_at: new Date().toISOString(),
  scope: 'partial',
  scope_note: '仅寻路/状态机 CPU 成本，不含 WebGL 渲染、纹理上传、HUD/DOM 更新；不可作为 D5 渲染维判级依据。',
  env: { node: process.version, os: process.platform, arch: process.arch },
  scene: {
    grid: `${zonesDoc.grid.w}x${zonesDoc.grid.h}`, tile_px: zonesDoc.grid.tile_px,
    zones: zonesDoc.stats.zones, seats: zonesDoc.stats.seats_allocated,
    walkable_tiles: zonesDoc.stats.walkable_tiles, endpoints: points.length,
    seat_capacity_note: '席位 23；30/50 agent 属超编，按待命/漫游处理，寻路照常计价'
  },
  results
};
const argv = process.argv.slice(2);
const outPath = (argv.indexOf('--out') >= 0 && argv[argv.indexOf('--out') + 1]) || path.join(ROOT, 'demo', 'd5-routing-bench.json');
fs.writeFileSync(outPath, JSON.stringify(out, null, 2));
console.log(JSON.stringify(results, null, 1));
console.log('written', outPath, fs.statSync(outPath).size, 'B');

// 判据：寻路占帧预算 <= 50%（即 p95 <= 8.35ms）；超了就必须错峰摊销
const warm = results.warm, cold = results.cold;
const LIMIT = 8.35;
const warmOk = warm.every(r => r.per_frame_ms.p95 <= LIMIT && r.unroutable === 0);
const coldOk = cold.every(r => r.cost_if_all_agents_repath_in_one_frame_ms <= LIMIT && r.unroutable === 0);
const overWarm = warm.filter(r => r.per_frame_ms.p95 > LIMIT).map(r => r.agents);
const overCold = cold.filter(r => r.cost_if_all_agents_repath_in_one_frame_ms > LIMIT).map(r => r.agents);
console.log(`ROUTING warm ${warmOk ? 'PASS' : 'FAIL'} | cold ${coldOk ? 'PASS' : 'FAIL'} | 超 50% 帧预算: warm=[${overWarm}] cold=[${overCold}] | unroutable=${warm.concat(cold).reduce((s, r) => s + r.unroutable, 0)}`);
process.exit(warmOk && coldOk ? 0 : 1);
