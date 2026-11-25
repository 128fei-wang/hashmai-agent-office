#!/usr/bin/env node
/* sim.js 逻辑测试：寻路、路径连续性、Python/JS 双实现一致性、工位分配
 * 跑法：node tools/test_sim.js
 */
const fs = require('fs');
const path = require('path');
const SIM = require('../demo/sim.js');

const ROOT = path.join(__dirname, '..');
const zonesDoc = JSON.parse(fs.readFileSync(path.join(ROOT, 'office-zones.json'), 'utf8'));
const walkDoc = JSON.parse(fs.readFileSync(path.join(ROOT, 'demo', 'walk-grid.json'), 'utf8'));

const checks = [];
function chk(name, ok, detail) {
  checks.push({ check: name, ok: !!ok, detail: detail || '' });
}

const grid = SIM.buildGrid(walkDoc.rows);
const router = SIM.makeRouter(grid);

chk('grid_dims', grid.w === zonesDoc.grid.w && grid.h === zonesDoc.grid.h,
  `${grid.w}x${grid.h}`);
chk('walkable_count', grid.walk && countWalk() === zonesDoc.stats.walkable_tiles,
  `${countWalk()} vs ${zonesDoc.stats.walkable_tiles}`);
function countWalk() {
  let n = 0;
  for (let y = 0; y < grid.h; y++) for (let x = 0; x < grid.w; x++) if (grid.walk(x, y)) n++;
  return n;
}

// 1) 每个工位从本区门可达，且路径每一步都相邻、可通行
let seatFail = [];
let stepFail = [];
let seats = 0;
zonesDoc.zones.forEach(z => {
  const door = z.door.tile;
  z.seats.forEach(s => {
    seats++;
    const raw = router(door, s.tile);
    if (!raw) { seatFail.push(s.seat_id); return; }
    for (let i = 1; i < raw.length; i++) {
      const md = Math.abs(raw[i][0] - raw[i - 1][0]) + Math.abs(raw[i][1] - raw[i - 1][1]);
      if (md !== 1 || !grid.walk(raw[i][0], raw[i][1])) stepFail.push(s.seat_id);
    }
  });
});
chk('all_seats_reachable', seatFail.length === 0, `${seats} seats, unreachable ${seatFail.slice(0, 5)}`);
chk('paths_stepwise_valid', stepFail.length === 0, `invalid ${stepFail.slice(0, 5)}`);

// 2) 简化后的路径仍连通（拐点之间直线可走）
let straightFail = [];
zonesDoc.zones.forEach(z => {
  const door = z.door.tile;
  z.seats.forEach(s => {
    const p = router.simplified(door, s.tile);
    if (!p) return;
    for (let i = 1; i < p.length; i++) {
      const a = p[i - 1], b = p[i];
      const dx = Math.sign(b[0] - a[0]), dy = Math.sign(b[1] - a[1]);
      if (dx !== 0 && dy !== 0) { straightFail.push(s.seat_id); break; }
      let x = a[0], y = a[1];
      while (x !== b[0] || y !== b[1]) {
        x += dx; y += dy;
        if (!grid.walk(x, y)) { straightFail.push(s.seat_id); break; }
      }
    }
  });
});
chk('simplified_legs_walkable', straightFail.length === 0, `broken ${straightFail.slice(0, 5)}`);

// 3) Python BFS 与 JS BFS 步数一致（两套实现互相证伪）
let mismatch = [];
Object.keys(zonesDoc.route_steps).forEach(a => {
  const za = zonesDoc.zones.find(z => z.id === a);
  Object.keys(zonesDoc.route_steps[a]).forEach(b => {
    const py = zonesDoc.route_steps[a][b];
    const zb = zonesDoc.zones.find(z => z.id === b);
    if (a === b) return;
    const p = router(za.door.tile, zb.door.tile);
    const js = p ? SIM.pathLength(p) : null;
    const jsRaw = p ? pathGridSteps(za.door.tile, zb.door.tile) : null;
    if (jsRaw !== py) mismatch.push(`${a}->${b} py=${py} js=${jsRaw}`);
  });
});
function pathGridSteps(from, to) {
  const r = SIM.bfs(grid, from);
  return r.dist.has(to[0] + ',' + to[1]) ? r.dist.get(to[0] + ',' + to[1]) : null;
}
chk('py_js_route_agree', mismatch.length === 0, `mismatch ${mismatch.slice(0, 4)}`);

// 4) 工位分配：编制人数 = 50，备用工位 = 66-50
const agentsPerZone = {};
zonesDoc.zones.forEach(z => { agentsPerZone[z.id] = z.headcount; });
const assigned = SIM.assignSeats(JSON.parse(JSON.stringify(zonesDoc.zones)), agentsPerZone);
const totalHead = zonesDoc.zones.reduce((s, z) => s + (z.role === 'facility' ? 0 : z.headcount), 0);
chk('assign_count', assigned.length === totalHead, `${assigned.length} vs ${totalHead}`);
chk('assign_unique_seats', new Set(assigned.map(a => a.seat_id)).size === assigned.length, '');

// 5) 关键路由存在性：老板→运营中心、各职能区→运营中心
const boss = zonesDoc.zones.find(z => z.id === 'boss_office');
const ops = zonesDoc.zones.find(z => z.id === 'ops_center');
const keyRoutes = zonesDoc.zones.filter(z => z.role === 'function').map(z => {
  const p = router(z.door.tile, ops.door.tile);
  return { zone: z.id, ok: !!p, steps: p ? pathGridSteps(z.door.tile, ops.door.tile) : null };
});
chk('reporting_routes_exist', keyRoutes.every(k => k.ok),
  keyRoutes.map(k => `${k.zone}:${k.steps}`).join(' '));

const verdict = checks.every(c => c.ok) ? 'PASS' : 'FAIL';
checks.forEach(c => console.log((c.ok ? 'PASS ' : 'FAIL ') + c.check + ' | ' + c.detail));
console.log(verdict + ' — ' + checks.filter(c => c.ok).length + '/' + checks.length);
fs.writeFileSync(path.join(ROOT, 'demo', 'sim-test.json'),
  JSON.stringify({ verdict, checks, generated_at: new Date().toISOString() }, null, 1));
process.exit(verdict === 'PASS' ? 0 : 1);
