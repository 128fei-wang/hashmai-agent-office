#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 office-zones.json 注入 demo 模板，生成可直接双击打开的 office-demo.html

依赖：office-zones.json 已由 build_office.py 生成（同一套网格，避免两份数据漂移）
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import build_office  # noqa: E402  复用同一份可通行网格

TEMPLATE = os.path.join(ROOT, "demo", "office-demo.template.html")
OUT = os.path.join(ROOT, "demo", "office-demo.html")
ZONES_JSON = os.path.join(ROOT, "office-zones.json")


def main():
    layout = json.load(open(ZONES_JSON, encoding="utf-8"))
    walkable, desks, _seats, _doors = build_office.build_layout()

    w, h = layout["grid"]["w"], layout["grid"]["h"]
    rows = []
    for y in range(h):
        rows.append("".join("1" if (x, y) in walkable else "0" for x in range(w)))

    touched = sum(r.count("1") for r in rows)
    assert touched == layout["stats"]["walkable_tiles"], (touched, layout["stats"]["walkable_tiles"])

    data = {
        "grid": layout["grid"],
        "walk": rows,
        "corridors": layout["corridors"],
        "zones": [
            {k: z[k] for k in ("id", "name", "role", "rect", "interior", "door", "south_door",
                               "headcount", "capacity", "seats")}
            for z in layout["zones"]
        ],
    }

    # 图块地图（build_tiles.py 产出）；缺失时降级到程序化矩形绘制
    TMAP = os.path.join(ROOT, "assets", "office-map.tmj")
    tmap = json.load(open(TMAP, encoding="utf-8")) if os.path.exists(TMAP) else None

    html = open(TEMPLATE, encoding="utf-8").read()
    assert "__DATA_JSON__" in html, "模板缺少 __DATA_JSON__ 标记"
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = html.replace("__DATA_JSON__", payload)
    assert "__TMAP_JSON__" in html, "模板缺少 __TMAP_JSON__ 标记"
    html = html.replace("__TMAP_JSON__",
                        json.dumps(tmap, ensure_ascii=False, separators=(",", ":")) if tmap else "null")
    open(OUT, "w", encoding="utf-8").write(html)

    json.dump({"w": w, "h": h, "tile_px": layout["grid"]["tile_px"], "rows": rows},
              open(os.path.join(ROOT, "demo", "walk-grid.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    print("grid %d×%d walkable %d" % (w, h, touched))
    print("zones %d seats %d" % (len(data["zones"]), sum(len(z["seats"]) for z in data["zones"])))
    print("html %s %d B (payload %d B)" % (OUT, os.path.getsize(OUT), len(payload)))


if __name__ == "__main__":
    main()
