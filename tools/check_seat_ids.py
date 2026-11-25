#!/usr/bin/env python3
"""工位编号一致性检查（零依赖）。

用途：CC2 把 12 事件流接进来、或任何人改 demo 显示层之后，跑一遍确认
「seat_id / agent 内部 id / 工位牌文案」三者没有再出现错位。

结构断言（永远必须成立）：
  A1 seat_id 格式 ^[a-z0-9_]+-S[0-9]{2}$ 且以 <zone_id>- 开头
  A2 seat_id 全楼唯一
  A3 每部门工位 <= 3（主人硬规格）
  A4 在岗席数 == seat-model.json 的 declared_total（默认 23）
  A5 demo 模板里的 agent 生成与牌面生成仍按 headcount 截断（不会给空席发 agent）

编号对齐（--require-unified 时才当硬门槛）：
  A6 牌面序号段 == seat_id 序号段（如 技术-S02，而不是 技术-03）
  未加 --require-unified 时，只报告当前偏移量（期望 1），退出码仍可为 0。

退出码：0 = 结构全过且（未要求统一 或 已统一）；1 = 有 FAIL。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / 'demo' / 'office-demo.template.html'
SEAT_RE = re.compile(r'^[a-z0-9_]+-S[0-9]{2}$')

fails = []


def check(ok, name, detail):
    print(f'{"PASS" if ok else "FAIL"}  {name}  {detail}')
    if not ok:
        fails.append(name)


def main():
    zones = json.load(open(ROOT / 'office-zones.json', encoding='utf-8'))
    model = json.load(open(ROOT / 'seat-model.json', encoding='utf-8'))
    tpl = TPL.read_text(encoding='utf-8') if TPL.exists() else ''

    live = [z for z in zones['zones'] if z.get('role') != 'facility']
    seats = [s for z in live for s in z['seats'][:z['headcount']]]
    ids = [s['seat_id'] for s in seats]

    bad = []
    for z in live:
        for s in z['seats']:
            if not SEAT_RE.match(s['seat_id']) or not s['seat_id'].startswith(z['id'] + '-'):
                bad.append(f'{z["id"]}/{s["seat_id"]}')
    check(not bad, 'A1 seat_id 格式与前缀', f'{len(seats)} 席，坏件 {bad or "无"}')

    check(len(ids) == len(set(ids)), 'A2 seat_id 唯一', f'共 {len(ids)} 个，重复 {len(ids) - len(set(ids))}')

    over = [f'{z["id"]}={z["headcount"]}' for z in live if z['headcount'] > 3]
    check(not over, 'A3 每部门 <=3 席', f'超编 {over or "无"}')

    declared = model.get('declared_total')
    check(len(seats) == declared, 'A4 席数 == declared_total', f'实得 {len(seats)} / 声明 {declared}')

    t_agent = bool(re.search(r"id:\s*z\.id\s*\+\s*'-A'\s*\+\s*i", tpl))
    t_plate = bool(re.search(r"z\.name\.slice\(0,\s*2\).*'-S'.*seat_id", tpl))
    t_cap = bool(re.search(r'if\s*\(i\s*>=\s*z\.headcount\)\s*return', tpl))
    check(t_agent and t_plate and t_cap, 'A5 模板生成逻辑在位',
          f'agent_id={t_agent} plate={t_plate} headcount截断={t_cap}')

    # 牌面若直接取 seat_id 序号段（'-S' 形态），则偏移恒为 0
    plate_by_seat = bool(re.search(r"z\.name\.slice\(0,\s*2\).*'-S'.*seat_id", tpl))
    offs = []
    for z in live:
        for i, s in enumerate(z['seats'][:z['headcount']]):
            plate_no = int(s['seat_id'].split('-S')[-1]) if plate_by_seat else i + 1
            seat_no = int(s['seat_id'].split('-S')[-1])
            offs.append(plate_no - seat_no)

    unified = all(o == 0 for o in offs)
    if '--require-unified' in sys.argv:
        check(unified, 'A6 牌面 == seat_id 序号段', f'偏移集合 {sorted(set(offs))}')
    else:
        print(f'INFO  A6 当前牌面偏移 = {sorted(set(offs))}（{len(offs)} 席）；'
              f'{"已统一" if unified else "未统一，见 SEAT-ID-MAP.md"}')

    print(f'SUMMARY seats={len(seats)} zones={len(live)} fail={len(fails)}')
    if fails:
        print('FAILED:', ', '.join(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
