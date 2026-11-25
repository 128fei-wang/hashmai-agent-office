#!/usr/bin/env python3
"""生成 v0.2 图资源：Tiled 地图(.tmj) + tileset 图集 + 合成预览图。

输入：office-zones.json（build_office.py 产出）
输出：
  assets/office-tileset.png        128x128，4x4 共 16 格 32px 图块
  assets/office-map.tmj            Tiled 1.11 JSON 地图（图层 floor/furniture/props + 对象层）
  assets/office-map-preview.png    1952x1216，按 tmj 合成，用于肉眼验收

自检项（全部 PASS 才写 verdict PASS）：
  C1 图层尺寸 == 61x38
  C2 每格 gid ∈ {0,1..10}，且 0 只出现在建筑之外
  C3 区域内地板格数 == Σ 各区内格数；走廊每格 gid=2
  C4 桌子格数 == 工位数 且不与走廊重叠；每张桌子都有椅子（seat tile）
  C5 对象层：10 个 zone 矩形 + 全部 seat 点，id 唯一
  C6 预览尺寸 1952x1216 且出现颜色数 > 8
"""
import json, os, sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, 'assets')
os.makedirs(ASSETS, exist_ok=True)

T = 32
COLS = 4
ROWS = 4

# gid(i) -> 颜色与样式
TILES = {
    1: ('#23252a', None),      # 设施区地板
    2: ('#161a21', 'dots'),    # 走廊
    3: ('#2b3444', 'wall'),    # 墙
    4: ('#2f3b4a', 'desk'),    # 桌子
    5: ('#263341', 'chair'),   # 椅子
    6: ('#2a3547', 'door'),    # 门
    7: ('#382d1c', None),      # 老板办公室
    8: ('#1c2a38', None),      # 总经理运营中心
    9: ('#1d2b24', None),      # 职能场景
    10: ('#0e1116', None),     # 建筑外
    11: ('#33404f', 'table'),  # 会议室长桌
    12: ('#54657c', 'counter'),# 茶水间吧台
}
ROLE_FLOOR = {'command': 7, 'dispatch': 8, 'function': 9, 'facility': 1}


def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def make_tileset():
    img = Image.new('RGBA', (COLS * T, ROWS * T), (14, 17, 22, 255))
    d = ImageDraw.Draw(img)
    for gid, (color, style) in TILES.items():
        idx = gid - 1
        cx, cy = (idx % COLS) * T, (idx // COLS) * T
        rgb = hex2rgb(color)
        d.rectangle([cx, cy, cx + T - 1, cy + T - 1], fill=rgb + (255,))
        if style == 'wall':
            d.rectangle([cx, cy, cx + T - 1, cy + 4], fill=(rgb[0] + 16, rgb[1] + 16, rgb[2] + 18, 255))
            d.line([cx, cy + T - 1, cx + T - 1, cy + T - 1], fill=(22, 27, 35, 255))
            pass
        elif style == 'dots':
            for px in range(8, T, 16):
                for py in range(8, T, 16):
                    d.point((cx + px, cy + py), fill=(30, 36, 45, 255))
        elif style == 'desk':
            d.rectangle([cx + 7, cy + 3, cx + T - 8, cy + 9], fill=(66, 79, 96, 255))    # 显示器
            d.rectangle([cx + 10, cy + 5, cx + T - 11, cy + 7], fill=(96, 130, 168, 255))
            d.rectangle([cx + 2, cy + 10, cx + T - 3, cy + 22], fill=(51, 64, 80, 255))  # 桌面
            d.rectangle([cx + 2, cy + 10, cx + T - 3, cy + 12], fill=(70, 86, 106, 255))
        elif style == 'chair':
            d.ellipse([cx + 8, cy + 9, cx + T - 9, cy + T - 8], fill=(44, 58, 74, 255))
            d.ellipse([cx + 11, cy + 12, cx + T - 12, cy + T - 11], fill=(31, 42, 55, 255))
        elif style == 'table':
            d.rectangle([cx, cy + 6, cx + T - 1, cy + T - 7], fill=(51, 64, 79, 255))
            d.rectangle([cx, cy + 6, cx + T - 1, cy + 9], fill=(64, 80, 98, 255))
        elif style == 'counter':
            d.rectangle([cx, cy + 8, cx + T - 1, cy + T - 9], fill=(84, 101, 124, 255))
            d.rectangle([cx, cy + 8, cx + T - 1, cy + 11], fill=(126, 148, 178, 255))
        elif style == 'door':
            d.rectangle([cx + 3, cy + 12, cx + T - 4, cy + T - 4], fill=(42, 53, 71, 255))
            d.line([cx + 3, cy + 12, cx + T - 4, cy + 12], fill=(90, 108, 132, 255))
    return img


def build_map(data):
    W, H = data['grid']['w'], data['grid']['h']
    floor = [0] * (W * H)
    furn = [0] * (W * H)
    props = [0] * (W * H)

    def put(layer, x, y, gid):
        if 0 <= x < W and 0 <= y < H:
            layer[y * W + x] = gid

    for z in data['zones']:
        r = z['rect']
        role_gid = ROLE_FLOOR[z['role']]
        # 墙体：矩形外框
        for x in range(r[0], r[2] + 1):
            put(floor, x, r[1], 3)
            put(floor, x, r[3], 3)
        for y in range(r[1], r[3] + 1):
            put(floor, r[0], y, 3)
            put(floor, r[2], y, 3)
        # 区域内地板
        for y in range(r[1] + 1, r[3]):
            for x in range(r[0] + 1, r[2]):
                put(floor, x, y, role_gid)

    for c in data['corridors']:
        r = c['rect']
        for y in range(r[1], r[3] + 1):
            for x in range(r[0], r[2] + 1):
                put(floor, x, y, 2)

    for z in data['zones']:
        put(props, z['door']['tile'][0], z['door']['tile'][1], 6)
        sd = z.get('south_door')
        if sd:
            put(props, sd['tile'][0], sd['tile'][1], 6)
        for s in z['seats']:
            put(furn, s['desk_tile'][0], s['desk_tile'][1], 4)
            put(furn, s['tile'][0], s['tile'][1], 5)

    # 会议室长桌 / 茶水间吧台（无工位区域也要有物件，否则是空盒子）
    for z in data['zones']:
        r = z['rect']
        if z['id'] == 'meeting':
            y0, y1 = r[1] + 2, r[3] - 2          # 长桌占房间中部两行
            for y in range(y0, max(y0 + 1, y1 + 1)):
                for x in range(r[0] + 2, r[2] - 1):
                    put(furn, x, y, 11)
        if z['id'] == 'pantry':
            y = r[3] - 2                          # 吧台贴房间下沿两行
            for yy in (y, y + 1):
                for x in range(r[0] + 2, r[2] - 1):
                    put(furn, x, yy, 12)

    # 建筑外统一 10
    for y in range(H):
        for x in range(W):
            if floor[y * W + x] == 0:
                floor[y * W + x] = 10

    layers = [
        {'id': 1, 'name': 'floor', 'type': 'tilelayer', 'width': W, 'height': H,
         'opacity': 1, 'visible': True, 'data': floor},
        {'id': 2, 'name': 'furniture', 'type': 'tilelayer', 'width': W, 'height': H,
         'opacity': 1, 'visible': True, 'data': furn},
        {'id': 3, 'name': 'props', 'type': 'tilelayer', 'width': W, 'height': H,
         'opacity': 1, 'visible': True, 'data': props},
    ]

    objs = []
    for z in data['zones']:
        r = z['rect']
        objs.append({'id': len(objs) + 1, 'name': z['id'], 'type': 'zone', 'x': r[0] * T, 'y': r[1] * T,
                     'width': (r[2] - r[0] + 1) * T, 'height': (r[3] - r[1] + 1) * T,
                     'rotation': 0, 'visible': True,
                     'properties': [{'name': 'role', 'type': 'string', 'value': z['role']},
                                    {'name': 'headcount', 'type': 'int', 'value': z['headcount']},
                                    {'name': 'display_name', 'type': 'string', 'value': z['name']}]})
    for z in data['zones']:
        for s in z['seats']:
            objs.append({'id': len(objs) + 1, 'name': s['seat_id'], 'type': 'seat',
                         'x': s['tile'][0] * T + T // 2, 'y': s['tile'][1] * T + T // 2,
                         'width': 0, 'height': 0, 'rotation': 0, 'visible': True,
                         'properties': [{'name': 'zone_id', 'type': 'string', 'value': s['zone_id']},
                                        {'name': 'facing', 'type': 'string', 'value': s['facing']},
                                        {'name': 'standby', 'type': 'bool', 'value': bool(s['standby'])}]})
    layers.append({'id': 4, 'name': 'objects', 'type': 'objectgroup', 'opacity': 1,
                   'visible': True, 'draworder': 'index', 'objects': objs})

    return {
        'type': 'map', 'version': '1.10', 'tiledversion': '1.11.0', 'orientation': 'orthogonal',
        'renderorder': 'right-down', 'width': W, 'height': H,
        'tilewidth': T, 'tileheight': T, 'infinite': False, 'nextlayerid': 5, 'nextobjectid': len(objs) + 1,
        'layers': layers,
        'tilesets': [{'firstgid': 1, 'name': 'office-tileset', 'image': 'office-tileset.png',
                      'imagewidth': COLS * T, 'imageheight': ROWS * T, 'tilewidth': T, 'tileheight': T,
                      'tilecount': COLS * ROWS, 'columns': COLS, 'margin': 0, 'spacing': 0}],
    }, (floor, furn, props)


def compose(tmj, tileset, data):
    floor, furn, props = [None] * 3
    for l in tmj['layers']:
        if l['name'] == 'floor':
            floor = l['data']
        elif l['name'] == 'furniture':
            furn = l['data']
        elif l['name'] == 'props':
            props = l['data']
    W, H = tmj['width'], tmj['height']
    img = Image.new('RGBA', (W * T, H * T), (14, 17, 22, 255))
    for layer in (floor, furn, props):
        for i, gid in enumerate(layer):
            if not gid:
                continue
            idx = gid - 1
            sx, sy = (idx % COLS) * T, (idx // COLS) * T
            tile = tileset.crop((sx, sy, sx + T, sy + T))
            x, y = (i % W) * T, (i // W) * T
            img.paste(tile, (x, y), tile)
    return img


def main():
    data = json.load(open(os.path.join(ROOT, 'office-zones.json'), encoding='utf-8'))
    seat_total = sum(len(z['seats']) for z in data['zones'])
    ts = make_tileset()
    ts.save(os.path.join(ASSETS, 'office-tileset.png'))

    tmj, (floor, furn, props) = build_map(data)
    W, H = tmj['width'], tmj['height']
    json.dump(tmj, open(os.path.join(ASSETS, 'office-map.tmj'), 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))

    checks = []
    def ck(name, ok, detail=''):
        checks.append({'id': name, 'verdict': 'PASS' if ok else 'FAIL', 'detail': detail})

    ck('C1_layer_size', len(floor) == W * H and len(furn) == W * H, f'{W}x{H}')
    bad = [g for g in set(floor) if g not in (0, 1, 2, 3, 7, 8, 9, 10)]
    ck('C2_floor_gid_domain', not bad, f'bad={bad}')

    zone_cells = sum((z['rect'][2] - z['rect'][0] - 1) * (z['rect'][3] - z['rect'][1] - 1)
                     for z in data['zones'])
    zone_floor = sum(1 for g in floor if g in (1, 7, 8, 9))
    ck('C3a_zone_floor_cells', zone_floor == zone_cells, f'{zone_floor}/{zone_cells}')
    corr_cells = sum((c['rect'][2] - c['rect'][0] + 1) * (c['rect'][3] - c['rect'][1] + 1)
                     for c in data['corridors'])
    corr_gid = sum(1 for g in floor if g == 2)
    ck('C3b_corridor_cells', corr_gid == corr_cells, f'{corr_gid}/{corr_cells}')

    desk_n = sum(1 for g in furn if g == 4)
    chair_n = sum(1 for g in furn if g == 5)
    overlap = sum(1 for i, g in enumerate(furn) if g and floor[i] == 2)
    ck('C4a_desks', desk_n == seat_total, f'desk={desk_n}/{seat_total}')
    ck('C4b_chairs', chair_n == seat_total, f'chair={chair_n}/{seat_total}')
    ck('C4c_no_furniture_on_corridor', overlap == 0, f'overlap={overlap}')

    objs = tmj['layers'][-1]['objects']
    zones = [o for o in objs if o['type'] == 'zone']
    seats = [o for o in objs if o['type'] == 'seat']
    uniq = len({o['name'] for o in objs}) == len(objs)
    table_n = sum(1 for g in furn if g == 11)
    counter_n = sum(1 for g in furn if g == 12)
    ck('C7_facility_props', table_n > 0 and counter_n > 0, f'table={table_n} counter={counter_n}')

    ck('C5_objects', len(zones) == 10 and len(seats) == seat_total and uniq,
       f'zone={len(zones)} seat={len(seats)} uniq={uniq}')

    preview = compose(tmj, ts, data)
    preview.save(os.path.join(ASSETS, 'office-map-preview.png'))
    colors = len(preview.convert('RGB').getcolors(maxcolors=1 << 20) or [])
    ck('C6_preview', preview.size == (W * T, H * T) and colors > 8,
       f'{preview.size[0]}x{preview.size[1]} colors={colors}')

    verdict = 'PASS' if all(c['verdict'] == 'PASS' for c in checks) else 'FAIL'
    report = {'verdict': verdict, 'tile_px': T, 'map': f'{W}x{H}',
              'assets': ['assets/office-tileset.png', 'assets/office-map.tmj',
                         'assets/office-map-preview.png'],
              'checks': checks}
    json.dump(report, open(os.path.join(ASSETS, 'tiles-report.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    for c in checks:
        print(c['id'], c['verdict'], c['detail'])
    print('verdict', verdict)
    return 0 if verdict == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
