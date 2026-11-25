/* ROOST office sim — 纯逻辑，不依赖 Pixi，可在 node 里直接测
 * 提供：网格 → BFS 寻路 → 拐点简化 → 工位分配
 * 浏览器：window.ROOST_SIM；node：module.exports
 */
(function (root) {
  'use strict';

  function buildGrid(rows) {
    const h = rows.length, w = rows[0].length;
    const grid = { w: w, h: h, rows: rows };
    grid.walk = function (x, y) {
      if (x < 0 || y < 0 || x >= w || y >= h) return false;
      return rows[y].charCodeAt(x) === 49; // '1'
    };
    return grid;
  }

  function key(p) { return p[0] + ',' + p[1]; }

  // BFS：返回 {dist: Map, parent: Map}
  function bfs(grid, start, limit) {
    const dist = new Map(), parent = new Map();
    dist.set(key(start), 0);
    parent.set(key(start), null);
    const q = [start];
    let head = 0;
    const MAX = limit === undefined ? Infinity : limit;
    while (head < q.length) {
      const cur = q[head++];
      const d = dist.get(key(cur));
      if (d >= MAX) continue;
      const nb = [[cur[0] + 1, cur[1]], [cur[0] - 1, cur[1]], [cur[0], cur[1] + 1], [cur[0], cur[1] - 1]];
      for (let i = 0; i < 4; i++) {
        const n = nb[i];
        if (!grid.walk(n[0], n[1])) continue;
        const k = key(n);
        if (dist.has(k)) continue;
        dist.set(k, d + 1);
        parent.set(k, cur);
        q.push(n);
      }
    }
    return { dist: dist, parent: parent };
  }

  // 单次寻路 + 缓存
  function makeRouter(grid) {
    const cacheRaw = new Map(), cacheSim = new Map();
    function findPath(from, to) {                 // 原始逐格路径
      const ck = key(from) + '>' + key(to);
      if (cacheRaw.has(ck)) return cacheRaw.get(ck);
      const r = bfs(grid, from);
      if (!r.dist.has(key(to))) { cacheRaw.set(ck, null); return null; }
      const path = [];
      let cur = to;
      while (cur) { path.push(cur); cur = r.parent.get(key(cur)); }
      path.reverse();
      cacheRaw.set(ck, path);
      return path;
    }
    findPath.simplified = function (from, to) {   // 拐点简化后的路径
      const ck = key(from) + '>' + key(to);
      if (cacheSim.has(ck)) return cacheSim.get(ck);
      const raw = findPath(from, to);
      const s = raw ? simplify(raw) : null;
      cacheSim.set(ck, s);
      return s;
    };
    return findPath;
  }

  // 拐点简化：只保留方向改变的格，端点必留
  function simplify(path) {
    if (!path || path.length <= 2) return path ? path.slice() : [];
    const out = [path[0]];
    for (let i = 1; i < path.length - 1; i++) {
      const a = path[i - 1], b = path[i], c = path[i + 1];
      const d1 = [b[0] - a[0], b[1] - a[1]];
      const d2 = [c[0] - b[0], c[1] - b[1]];
      if (d1[0] !== d2[0] || d1[1] !== d2[1]) out.push(b);
    }
    out.push(path[path.length - 1]);
    return out;
  }

  function pathLength(path) {
    let n = 0;
    for (let i = 1; i < path.length; i++) {
      n += Math.abs(path[i][0] - path[i - 1][0]) + Math.abs(path[i][1] - path[i - 1][1]);
    }
    return n;
  }

  // 工位分配：按编制人数填正式工位，其余留给备用（空椅子）
  function assignSeats(zones, agentsPerZone) {
    const out = [];
    zones.forEach(function (z) {
      if (z.role === 'facility') return;
      const want = agentsPerZone[z.id] !== undefined ? agentsPerZone[z.id] : z.headcount;
      z.seats.forEach(function (s, i) {
        if (i >= want) { s.occupiedBy = null; s.standby = true; return; }
        s.occupiedBy = z.id + '-A' + String(i).padStart(2, '0');
        s.standby = false;
        out.push({ id: s.occupiedBy, zone_id: z.id, seat_id: s.seat_id, tile: s.tile, desk: s.desk_tile });
      });
    });
    return out;
  }

  const api = { buildGrid: buildGrid, bfs: bfs, makeRouter: makeRouter, simplify: simplify,
                pathLength: pathLength, assignSeats: assignSeats };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ROOST_SIM = api;
})(typeof window !== 'undefined' ? window : globalThis);
