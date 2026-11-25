#!/bin/sh
# PATCH-01 工位编号统一 —— 合入脚本
# 用法：
#   sh tools/apply_patch_01.sh            # 预演（默认，不改任何文件）
#   sh tools/apply_patch_01.sh --apply    # 真合入：备份 -> 打补丁 -> 重建 demo -> 全量校验
# 判据：check_seat_ids --require-unified rc=0（A1-A6 全 PASS）+ test_sim 9/9
set -e
cd "$(dirname "$0")/.."

DIFF=patches/PATCH-01-seat-id.diff
FILES="demo/office-demo.template.html tools/check_seat_ids.py"
MODE=dry
[ "$1" = "--apply" ] && MODE=apply

[ -f "$DIFF" ] || { echo "缺 $DIFF"; exit 2; }

echo "[1/4] 补丁预检（patch --dry-run）"
patch -p0 --dry-run -i "$DIFF"
echo "  预检通过"

if [ "$MODE" = dry ]; then
  echo "== 预演结束：未修改任何文件。真合入请加 --apply =="
  exit 0
fi

TS=$(date +%Y%m%d-%H%M%S)
echo "[2/4] 备份 -> .bak.$TS"
for f in $FILES; do cp -p "$f" "$f.bak.$TS"; done

echo "[3/4] 打补丁 + 重建 demo"
patch -p0 -i "$DIFF"
python3 tools/build_demo.py

echo "[4/4] 全量校验"
python3 tools/check_seat_ids.py --require-unified
node tools/test_sim.js

echo "== 合入完成（备份后缀 .bak.$TS）。下一步：重取 D6 三件证据 + 重算契约包 SUMS，再请 DS 原样复跑 =="
