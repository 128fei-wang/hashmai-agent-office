#!/usr/bin/env python3
"""生成 agent 精灵图集：3 配色 × 4 朝向 × 2 状态(空闲/行走) × 3 帧。
逻辑画布 16×24，输出 2x 最近的 32×48 单元。
"""
import json, os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PNG = os.path.join(ROOT, "assets", "agents.png")
OUT_JSON = os.path.join(ROOT, "assets", "agents-report.json")

CW, CH = 16, 24          # 逻辑单元
SC = 2                    # 放大倍数
PW, PH = CW * SC, CH * SC  # 32×48

SKIN = (232, 196, 160, 255)
PANTS = (40, 46, 58, 255)
OUTLINE = (18, 22, 28, 255)

# 三个配色：技术(蓝) / 运营(琥珀) / 职能(青)
PALETTES = [
    {"id": "tech",  "shirt": (86, 148, 212), "hair": (52, 40, 34)},
    {"id": "ops",   "shirt": (222, 168, 74), "hair": (32, 32, 40)},
    {"id": "staff", "shirt": (96, 190, 168), "hair": (70, 46, 32)},
]
DIRS = ["S", "E", "N", "W"]          # 下 / 右 / 上 / 左
STATES = ["idle", "walk"]

# 行走三帧的腿位与身体浮动
WALK = [(0, 0, 0), (1, -1, 1), (0, 0, 0)]   # (腿部偏移, 身体 y 偏移, 摆臂方向)


def draw_cell(d, ox, oy, pal, dirn, state, frame):
    """在逻辑坐标 16×24 内绘制一个 agent。"""
    shirt = pal["shirt"] + (255,)
    hair = pal["hair"] + (255,)
    leg_off, body_dy, arm = WALK[frame]

    # 影子
    d.ellipse([ox + 4, oy + 21, ox + 12, oy + 23], fill=(0, 0, 0, 60))

    body_y = oy + 8 + body_dy
    # 腿
    d.rectangle([ox + 5, body_y + 8, ox + 7, oy + 21 - max(0, leg_off)], fill=PANTS)
    d.rectangle([ox + 9, body_y + 8, ox + 11, oy + 21 + min(0, -leg_off)], fill=PANTS)
    # 躯干
    d.rectangle([ox + 4, body_y, ox + 12, body_y + 9], fill=shirt)
    d.rectangle([ox + 4, body_y, ox + 12, body_y + 9], outline=OUTLINE)
    # 手臂（走路时一前一后）
    if dirn in ("S", "N"):
        d.rectangle([ox + 2, body_y + 1 + arm, ox + 4, body_y + 6 + arm], fill=shirt)
        d.rectangle([ox + 12, body_y + 1 - arm, ox + 14, body_y + 6 - arm], fill=shirt)
    # 头
    hy = body_y - 7
    d.rectangle([ox + 5, hy, ox + 11, hy + 6], fill=SKIN, outline=OUTLINE)
    # 头发按朝向
    if dirn == "N":                 # 背对：整头发
        d.rectangle([ox + 5, hy, ox + 11, hy + 4], fill=hair)
    elif dirn == "S":               # 正面：刘海
        d.rectangle([ox + 5, hy, ox + 11, hy + 2], fill=hair)
        d.point((ox + 6, hy + 4), fill=OUTLINE); d.point((ox + 10, hy + 4), fill=OUTLINE)
    elif dirn == "E":               # 右侧：脸部偏右
        d.rectangle([ox + 5, hy, ox + 9, hy + 3], fill=hair)
        d.point((ox + 10, hy + 4), fill=OUTLINE)
    else:                            # W：脸部偏左
        d.rectangle([ox + 7, hy, ox + 11, hy + 3], fill=hair)
        d.point((ox + 6, hy + 4), fill=OUTLINE)

    # 状态标记：工作中给一点暖色高光点（这里 idle 视为在岗）
    if state == "idle":
        d.point((ox + 12, body_y - 1), fill=(255, 214, 130, 255))


def build():
    cols = len(PALETTES) * len(STATES) * 3   # 18? 用帧维 3
    cols = len(PALETTES) * 3
    rows = len(DIRS) * len(STATES)
    sheet = Image.new("RGBA", (cols * PW, rows * PH), (0, 0, 0, 0))
    d_small = Image.new("RGBA", (cols * CW, rows * CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(d_small)

    for pi, pal in enumerate(PALETTES):
        for di, dirn in enumerate(DIRS):
            for si, st in enumerate(STATES):
                for f in range(3):
                    ox = (pi * 3 + f) * CW
                    oy = (di * len(STATES) + si) * CH
                    draw_cell(d, ox, oy, pal, dirn, st, f)

    sheet = d_small.resize((cols * PW, rows * PH), Image.NEAREST)
    sheet.save(OUT_PNG)

    # 自检
    report = {"verdict": "PASS", "checks": [], "cell": [PW, PH], "grid": [cols, rows],
              "palettes": [p["id"] for p in PALETTES], "dirs": DIRS, "states": STATES}
    px = sheet.load()
    empty = 0
    uniq_colors = set()
    for r in range(rows):
        for c in range(cols):
            cb = 0
            for y in range(PH):
                for x in range(PW):
                    a = px[c * PW + x, r * PH + y][3]
                    if a > 0:
                        cb += 1
                        uniq_colors.add(px[c * PW + x, r * PH + y])
            if cb < 200:
                empty += 1
    report["checks"].append({"id": "S1", "desc": "每格非空像素≥200", "bad_cells": empty, "ok": empty == 0})
    # 行走帧差异：同配色同朝向 idle 与 walk 帧必须不同
    diff_bad = 0
    for r0 in range(0, rows, 2):
        for c in range(cols):
            a = sheet.crop((c * PW, r0 * PH, (c + 1) * PW, (r0 + 1) * PH))
            b = sheet.crop((c * PW, (r0 + 1) * PH, (c + 1) * PW, (r0 + 2) * PH))
            if list(a.getdata()) == list(b.getdata()):
                diff_bad += 1
    report["checks"].append({"id": "S2", "desc": "idle 与 walk 单元必须不同", "same": diff_bad, "ok": diff_bad == 0})
    # 配色可区分：三配色主色不同
    report["checks"].append({"id": "S3", "desc": "三套配色主色互不相同",
                             "colors": [list(p["shirt"]) for p in PALETTES],
                             "ok": len({p["shirt"] for p in PALETTES}) == 3})
    report["checks"].append({"id": "S4", "desc": "色板数量≤24（像素风控制）", "n": len(uniq_colors), "ok": len(uniq_colors) <= 24})
    # 底边对齐：所有单元最后一行（脚部）都应有内容
    foot_bad = 0
    for r in range(rows):
        for c in range(cols):
            has = any(px[c * PW + x, r * PH + PH - 1][3] > 0 for x in range(PW))
            if not has:
                foot_bad += 1
    report["checks"].append({"id": "S5", "desc": "每格脚部（末行）有像素", "bad": foot_bad, "ok": foot_bad == 0})
    report["bad"] = [c for c in report["checks"] if not c["ok"]]
    if report["bad"]:
        report["verdict"] = "FAIL"
    report["size"] = os.path.getsize(OUT_PNG)
    json.dump(report, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return report


if __name__ == "__main__":
    r = build()
    print("verdict", r["verdict"], "sheet", r["grid"], "cell", r["cell"], "bytes", r["size"])
    for c in r["checks"]:
        print(("PASS " if c["ok"] else "FAIL ") + c["id"] + " " + c["desc"])
