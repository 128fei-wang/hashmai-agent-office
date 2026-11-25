#!/usr/bin/env python3
"""从 office-zones.json 导出 D3 判据形状的 seat-model.json（P98-CRITERIA-01 v0.1 D3）。"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "office-zones.json")
OUT = os.path.join(ROOT, "seat-model.json")

data = json.load(open(SRC, encoding="utf-8"))
boss = 0
zones = []
for z in data["zones"]:
    n = len(z["seats"])
    if n == 0:
        continue
    if z["id"] == "boss_office":
        boss = n
    else:
        zones.append(dict(id=z["id"], name=z.get("name", z["id"]), seats=n))

model = dict(
    zones=zones,
    boss=boss,
    declared_total=boss + sum(z["seats"] for z in zones),
    entry_commands=1,
    occupancy_mode="one_agent_per_seat",
    occupancy_note=("one agent per seat, no sharing; agents beyond seat count go to standby pool "
                    "and are counted, not seated"),
    seat_cap_per_dept=3,
    source="office-zones.json",
    grid=data["grid"],
    standby_policy=dict(pool=True, visible_max=12,
                        render_cap=boss + sum(z["seats"] for z in zones) + 12),
)

json.dump(model, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(dict(boss=boss, depts=len(zones), declared_total=model["declared_total"],
                      occupancy_mode=model["occupancy_mode"]), ensure_ascii=False))
print("json", OUT, os.path.getsize(OUT), "B")
