#!/bin/sh
# PATCH-01 + PATCH-02 同批合入脚本（两条必须同批：单打任一条都不能让 A6 偏移归零）
#
# 用法：
#   sh tools/apply_patch_batch.sh              # 预演（默认）：只在临时副本上打+重建+校验，真树一字节不动
#   sh tools/apply_patch_batch.sh --apply      # 真合入：先预演，全绿才备份+打补丁+重建+校验，任一步失败自动回滚
#   ROOT=/tmp/xxx sh tools/apply_patch_batch.sh --apply   # 在指定根目录上跑（用于验证脚本本身）
#
# 判据（全绿才算通过）：
#   patch 两条顺序打、零 .rej
#   python3 tools/build_demo.py                -> 76,536 B / payload 6,311 B
#   python3 tools/check_seat_ids.py --require-unified -> A6 偏移 [0]、SUMMARY fail=0、rc=0
#   node tools/test_sim.js                     -> 9/9 PASS、rc=0
#
# 合入后手工收口（脚本不碰契约包）：重取 D6 三件证据 -> 重算 SHA256SUMS -> 请 DS 原样复跑
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${ROOT:-$(cd "$HERE/.." && pwd)}
cd "$ROOT"

P1=patches/PATCH-01-seat-id.diff
P2=patches/PATCH-02-dest-shared-route.diff
TOUCHED="demo/office-demo.template.html tools/check_seat_ids.py demo/office-demo.html"
MODE=dry
[ "$1" = "--apply" ] && MODE=apply

[ -f "$P1" ] || { echo "缺 $P1"; exit 2; }
[ -f "$P2" ] || { echo "缺 $P2"; exit 2; }

STAGE=$(mktemp -d /tmp/roost-batch.XXXXXX)
cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT INT TERM

echo "[1/5] 预演：树镜像到临时副本 (排除 shots/.bak/.git): $STAGE"
rsync -a --exclude shots --exclude '.bak.*' --exclude .git --exclude '*.tar.gz' \
      --exclude 'd5-*-bench.json' ./ "$STAGE"/
cd "$STAGE"

echo "[2/5] 顺序打两个补丁（预演副本）"
patch -p0 -i "$P1"
patch -p0 -i "$P2"
REJ=$(find . -name '*.rej' | wc -l | tr -d ' ')
echo "  rej=$REJ"
[ "$REJ" = "0" ] || { echo "FAIL 出现 .rej，停止"; exit 1; }

echo "[3/5] 重建 demo + 三项校验"
python3 tools/build_demo.py | tail -2
HTML_B=$(wc -c < demo/office-demo.html | tr -d ' ')
echo "  html=$HTML_B B"
[ "$HTML_B" = "76536" ] || { echo "FAIL html 体积不符预期 76536"; exit 1; }

set +e
python3 tools/check_seat_ids.py --require-unified > /tmp/roost-batch.seat.txt 2>&1
SEAT_RC=$?
node tools/test_sim.js > /tmp/roost-batch.sim.txt 2>&1
SIM_RC=$?
set -e
tail -3 /tmp/roost-batch.seat.txt
echo "  seat_rc=$SEAT_RC"
grep -E "^(PASS|FAIL)" /tmp/roost-batch.sim.txt | tail -2
echo "  sim_rc=$SIM_RC"
[ "$SEAT_RC" = "0" ] && [ "$SIM_RC" = "0" ] || { echo "FAIL 校验未全绿，停止（真树未动）"; exit 1; }
echo "== 预演全绿 =="

if [ "$MODE" = dry ]; then
  echo "== 预演模式结束：真树未改。真合入请加 --apply =="
  exit 0
fi

cd "$ROOT"
TS=$(date +%Y%m%d-%H%M%S)
echo "[4/5] 备份 -> *.bak.$TS 并打补丁"
for f in $TOUCHED; do [ -f "$f" ] && cp -p "$f" "$f.bak.$TS"; done
if ! patch -p0 -i "$P1" || ! patch -p0 -i "$P2"; then
  echo "补丁失败，回滚"
  for f in $TOUCHED; do [ -f "$f.bak.$TS" ] && mv -f "$f.bak.$TS" "$f"; done
  exit 1
fi
if ! python3 tools/build_demo.py > /tmp/roost-batch.build.txt 2>&1; then
  echo "重建失败，回滚"
  for f in $TOUCHED; do [ -f "$f.bak.$TS" ] && mv -f "$f.bak.$TS" "$f"; done
  exit 1
fi

echo "[5/5] 真树全量校验"
set +e
python3 tools/check_seat_ids.py --require-unified > /tmp/roost-batch.seat.txt 2>&1; SEAT_RC=$?
node tools/test_sim.js > /tmp/roost-batch.sim.txt 2>&1; SIM_RC=$?
set -e
tail -3 /tmp/roost-batch.seat.txt
echo "  seat_rc=$SEAT_RC  sim_rc=$SIM_RC"
if [ "$SEAT_RC" != "0" ] || [ "$SIM_RC" != "0" ]; then
  echo "真树校验未过，回滚到合入前"
  for f in $TOUCHED; do [ -f "$f.bak.$TS" ] && mv -f "$f.bak.$TS" "$f"; done
  python3 tools/build_demo.py > /dev/null 2>&1
  echo "已回滚（备份已还原，demo 已按回滚后的模板重建）"
  exit 1
fi

echo "== 合入完成，备份后缀: .bak.$TS =="
echo "下一步必做：①重取 D6 三件证据（page-selfcheck / fps-probe / 2D）；②重算契约包 SHA256SUMS；③请 DS 原样复跑；④看板记录 A6 偏移 [0] + html 76,536 B"
