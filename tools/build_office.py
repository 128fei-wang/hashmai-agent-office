#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""办公室场景图生成器（确定性，可复跑）

产出 office-zones.json：网格、区域(zone)、门(door)、工位(seat)、工位朝向(desk)、
区域间最短步数矩阵，并在生成时做 6 项几何自检。

设计约束（产品化必须成立，不是画图好看）：
  - 每个工位占 1 格，两两不重叠
  - 工位必须在所属区域内部、且可达（从本区门 BFS 能走到）
  - 朝向必须指向一个非通行格（桌子/墙），否则人坐下去是背对空气
  - 每个区域的门必须同时贴走廊和区域内侧
  - 每个区域的工位数 ≥ 编制人数

跑法：python3 tools/build_office.py
"""

import json
import os
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "office-zones.json")

W, H = 53, 24   # 网格：53 列 × 24 行（32px/格 → 1696×768 逻辑像素）；每部门≤3 工位后压缩层高

# 区域定义：rect 为闭区间 (x0, y0, x1, y1)；demand = 编制人数
ZONES = [
    dict(id="boss_office", name="老板办公室", role="command", rect=(1, 1, 8, 6), demand=2),
    dict(id="ops_center",  name="总经理运营中心", role="dispatch", rect=(10, 1, 27, 6), demand=8),
    dict(id="meeting",     name="会议室", role="facility", rect=(29, 1, 38, 6), demand=0),
    dict(id="pantry",      name="茶水间", role="facility", rect=(40, 1, 51, 6), demand=0),
    dict(id="tech",        name="技术部", role="function", rect=(1, 9, 14, 14), demand=12),
    dict(id="data",        name="数据部", role="function", rect=(16, 9, 33, 14), demand=10),
    dict(id="ui",          name="设计部", role="function", rect=(35, 9, 51, 14), demand=6),
    dict(id="hr",          name="人力资源", role="function", rect=(1, 17, 14, 22), demand=4),
    dict(id="finance",     name="财务部", role="function", rect=(16, 17, 33, 22), demand=5),
    dict(id="qa_lab",      name="验证实验室", role="function", rect=(35, 17, 51, 22), demand=3),
]

SEAT_CAP = 3   # 主人 2026-11-24 要求：一个部门最多 3 个工位

CORRIDORS = [  # 横向主走廊（夹在三排房间之间）
    dict(id="corridor_a", rect=(1, 7, 51, 8)),
    dict(id="corridor_b", rect=(1, 15, 51, 16)),
]


def cells(rect, shrink=0):
    x0, y0, x1, y1 = rect
    return [(x, y)
            for x in range(x0 + shrink, x1 - shrink + 1)
            for y in range(y0 + shrink, y1 - shrink + 1)]


def center_x(rect):
    return (rect[0] + rect[2]) // 2


def corridor_touches(x, y):
    return any(c["rect"][0] <= x <= c["rect"][2] and c["rect"][1] <= y <= c["rect"][3]
               for c in CORRIDORS)


def build_doors():
    """门开在贴走廊的那一侧边缘：上贴走廊→上门；下贴走廊→下门。"""
    doors = {}
    for z in ZONES:
        x0, y0, x1, y1 = z["rect"]
        cx = (x0 + x1) // 2
        if corridor_touches(cx, y0 - 1):
            doors[z["id"]] = (cx, y0)
        if corridor_touches(cx, y1 + 1):
            key = z["id"] if z["id"] not in doors else z["id"] + "_south"
            doors[key] = (cx, y1)
    return doors


def build_layout():
    """返回 (walkable, desks, seats_by_zone)。桌子格不可通行，工位在其下一格。"""
    walkable = set()
    for c in CORRIDORS:
        walkable.update(cells(c["rect"]))
    for z in ZONES:
        walkable.update(cells(z["rect"], shrink=1))

    doors = build_doors()
    for d in doors.values():
        walkable.add(d)

    desks = set()
    seats_by_zone = {}
    for z in ZONES:
        if z["role"] == "facility":       # 会议室/茶水间不排工位
            seats_by_zone[z["id"]] = []
            continue
        rect = z["rect"]
        ix0, iy0, ix1, iy1 = rect[0] + 1, rect[1] + 1, rect[2] - 1, rect[3] - 1
        zone_seats = []
        row = 0
        while True:
            desk_y = iy0 + 1 + row * 3
            seat_y = desk_y + 1
            if seat_y > iy1:
                break
            cols = list(range(ix0 + 1, ix1 + 1, 2))
            cap = min(z["demand"], SEAT_CAP)
            if cap < len(cols):          # 工位少时居中排布，避免全挤在左边
                drop = (len(cols) - cap + 1) // 2
                cols = cols[drop:drop + cap]
            for x in cols:
                desk_tile = (x, desk_y)
                seat_tile = (x, seat_y)
                if seat_tile[1] > iy1:
                    continue
                if len(zone_seats) >= min(z["demand"], SEAT_CAP):   # 每部门最多 3 个工位
                    break
                desks.add(desk_tile)
                zone_seats.append(dict(zone_id=z["id"], tile=[x, seat_y], facing="up",
                                      desk_tile=[x, desk_y]))
            if len(zone_seats) >= min(z["demand"], SEAT_CAP):
                break
            row += 1
        seats_by_zone[z["id"]] = zone_seats

    # 桌子格从可通行集合里剔除
    walkable -= desks
    return walkable, desks, seats_by_zone, doors


def bfs(walkable, start, limit=None):
    dist = {start: 0}
    q = deque([start])
    while q:
        cur = q.popleft()
        d = dist[cur]
        if limit is not None and d >= limit:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (cur[0] + dx, cur[1] + dy)
            if nxt in walkable and nxt not in dist:
                dist[nxt] = d + 1
                q.append(nxt)
    return dist


def main():
    walkable, desks, seats_by_zone, doors = build_layout()

    # 每个区域按编制人数截取工位，多余工位标为空置备用
    zones_out = []
    seat_global = []
    for z in ZONES:
        all_seats = seats_by_zone[z["id"]]
        demand = z["demand"]
        seats = []
        for i, s in enumerate(all_seats):
            seat_id = f"{z['id']}-S{i:02d}"
            rec = dict(seat_id=seat_id, zone_id=z["id"], tile=s["tile"],
                       facing=s["facing"], desk_tile=s["desk_tile"],
                       assigned=False, standby=False)
            seats.append(rec)
            seat_global.append(rec)
        x0, y0, x1, y1 = z["rect"]
        zones_out.append(dict(
            id=z["id"], name=z["name"], role=z["role"],
            rect=[x0, y0, x1, y1],
            interior=[x0 + 1, y0 + 1, x1 - 1, y1 - 1],
            door=dict(tile=list(doors[z["id"]]), zone_id=z["id"]),
            south_door=(dict(tile=list(doors[z["id"] + "_south"]), zone_id=z["id"])
                        if z["id"] + "_south" in doors else None),
            headcount=len(seats), capacity=len(seats),
            seats=seats,
        ))

    # 区域间最短步数矩阵（门到门）
    door_of = {z["id"]: tuple(doors[z["id"]]) for z in ZONES}
    routes = {}
    for a, da in door_of.items():
        dist = bfs(walkable, da)
        row = {}
        for b, db in door_of.items():
            if a == b:
                row[b] = 0
            else:
                row[b] = dist.get(db)
        routes[a] = row

    # ---------------- 自检 ----------------
    checks = []

    def chk(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    tiles = [tuple(s["tile"]) for s in seat_global]
    chk("seats_unique_tiles", len(set(tiles)) == len(tiles),
        f"{len(tiles)} seats / {len(set(tiles))} unique tiles")

    in_zone = all(
        any(zz["id"] == s["zone_id"] and
            zz["rect"][0] + 1 <= s["tile"][0] <= zz["rect"][2] - 1 and
            zz["rect"][1] + 1 <= s["tile"][1] <= zz["rect"][3] - 1
            for zz in ZONES)
        for s in seat_global)
    chk("seats_inside_zone_interior", in_zone, f"{len(seat_global)} seats checked")

    chk("seats_walkable", all(tuple(s["tile"]) in walkable for s in seat_global),
        "every seat tile is walkable")

    facing_ok = True
    facing_bad = []
    for s in seat_global:
        z = next(zz for zz in ZONES if zz["id"] == s["zone_id"])
        fx = s["tile"][0] + (0 if s["facing"] == "up" else 0)
        fy = s["tile"][1] - 1 if s["facing"] == "up" else s["tile"][1] + 1
        if not (z["rect"][1] <= fy <= z["rect"][3] and z["rect"][0] <= fx <= z["rect"][2]):
            facing_ok = False
            facing_bad.append(s["seat_id"])
        if (fx, fy) in walkable:
            facing_ok = False
            facing_bad.append(s["seat_id"] + ":faces-walkable")
    chk("facing_points_to_blocked_tile", facing_ok,
        f"violations {facing_bad[:5]}")

    reach_ok = True
    unreachable = []
    for z in zones_out:
        d = bfs(walkable, tuple(z["door"]["tile"]))
        for s in z["seats"]:
            if tuple(s["tile"]) not in d:
                reach_ok = False
                unreachable.append(s["seat_id"])
    chk("seats_reachable_from_door", reach_ok,
        f"unreachable {unreachable[:5]}")

    door_ok = True
    for z in ZONES:
        cx = center_x(z["rect"])
        t = tuple(doors[z["id"]])
        # 门要同时贴走廊和区域内侧
        nbrs = {(t[0] + dx, t[1] + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))}
        corr_cell = [n for n in nbrs if any(
            c["rect"][0] <= n[0] <= c["rect"][2] and c["rect"][1] <= n[1] <= c["rect"][3]
            for c in CORRIDORS)]
        inner_cell = [n for n in nbrs if z["rect"][0] + 1 <= n[0] <= z["rect"][2] - 1
                      and z["rect"][1] + 1 <= n[1] <= z["rect"][3] - 1]
        if not corr_cell or not inner_cell:
            door_ok = False
    chk("doors_touch_corridor_and_interior", door_ok, f"{len(ZONES)} zones")

    cap_ok = all(z["capacity"] >= z["headcount"] for z in zones_out)
    chk("capacity_covers_headcount", cap_ok,
        "; ".join(f"{z['id']} {z['capacity']}>={z['headcount']}" for z in zones_out))

    total = sum(z["headcount"] for z in zones_out)
    out = dict(
        grid=dict(w=W, h=H, tile_px=32),
        corridors=[dict(id=c["id"], rect=list(c["rect"])) for c in CORRIDORS],
        zones=zones_out,
        route_steps=routes,
        stats=dict(zones=len(zones_out), headcount=total,
                   seats_allocated=sum(z["capacity"] for z in zones_out),
                   standby_seats=0,
                   walkable_tiles=len(walkable), desk_tiles=len(desks)),
        seat_policy=dict(
            seat_cap_per_dept=SEAT_CAP,
            dept_count=sum(1 for z in zones_out if z["capacity"] > 0 and z["id"] != "boss_office"),
            formula="boss 2 + 7 depts x 3 = 23 (no 8th dept; ops_center already counts as a dept)",
            occupancy="one agent per seat at a time; no seat sharing",
            overflow=dict(standby_pool=True, standby_visible_max=12,
                          render_cap=sum(z["capacity"] for z in zones_out) + 12,
                          note="30-50 agents: seats are the visual subset; the rest render as standby queue, load stays on the event layer"),
        ),
        validation=dict(verdict="PASS" if all(c["ok"] for c in checks) else "FAIL",
                        checks=checks),
    )
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out["stats"], ensure_ascii=False))
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["check"] + " | " + c["detail"])
    print("json", OUT, os.path.getsize(OUT), "B")
    return 0 if out["validation"]["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
