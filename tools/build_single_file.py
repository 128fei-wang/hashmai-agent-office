#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 demo/office-demo.html 打成自包含单文件（可直接双击打开、可发给别人）。

内联三件外部依赖：
  ./lib/pixi.min.js      -> <script> 内联
  ./sim.js               -> <script> 内联
  ../assets/office-tileset.png 与 ../assets/agents.png -> data:image/png;base64

用法：python3 tools/build_single_file.py
产物：demo/office-demo-single.html（不覆盖正式树 office-demo.html）
"""
import base64, hashlib, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(ROOT, "demo")
SRC = os.path.join(DEMO, "office-demo.html")
OUT = os.path.join(DEMO, "office-demo-single.html")


def read_text(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def data_uri(p):
    with open(p, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")


def must_replace(text, old, new, label):
    if old not in text:
        raise SystemExit("缺少锚点，拒绝产出：%s" % label)
    if text.count(old) != 1:
        raise SystemExit("锚点出现 %d 次，拒绝产出：%s" % (text.count(old), label))
    return text.replace(old, new)


def main():
    html = read_text(SRC)
    pixi = read_text(os.path.join(DEMO, "lib", "pixi.min.js"))
    sim = read_text(os.path.join(DEMO, "sim.js"))

    html = must_replace(
        html,
        '<script src="./lib/pixi.min.js"></script>',
        "<script>\n" + pixi + "\n</script>",
        "pixi 内联",
    )
    html = must_replace(
        html,
        '<script src="./sim.js"></script>',
        "<script>\n" + sim + "\n</script>",
        "sim 内联",
    )
    html = must_replace(
        html,
        "TILES_IMG.src = '../assets/office-tileset.png';",
        "TILES_IMG.src = '%s';" % data_uri(os.path.join(ROOT, "assets", "office-tileset.png")),
        "tileset 内联",
    )
    html = must_replace(
        html,
        "SPR_IMG.src = '../assets/agents.png';",
        "SPR_IMG.src = '%s';" % data_uri(os.path.join(ROOT, "assets", "agents.png")),
        "agents 内联",
    )

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)

    raw = open(OUT, "rb").read()
    print("src  %s  %d B" % (os.path.relpath(SRC, ROOT), os.path.getsize(SRC)))
    print("out  %s  %d B" % (os.path.relpath(OUT, ROOT), len(raw)))
    print("sha256 %s" % hashlib.sha256(raw).hexdigest())
    # 单文件不允许残留任何外部引用
    for bad in ('src="./lib/pixi.min.js"', 'src="./sim.js"', "'../assets/"):
        if bad in html:
            raise SystemExit("残留外部引用：%s" % bad)


if __name__ == "__main__":
    main()
