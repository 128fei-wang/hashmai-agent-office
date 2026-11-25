#!/bin/sh
# 契约包自验入口。schema 校验零第三方依赖（只用 python3 标准库）；
# D3/D6 两维需外部判据器 p98check.py，用 P98= 必填指定（判据器随源码根分发，不在本包内）。
#
# 用法：
#   P98=/path/to/p98check.py sh verify.sh    # P98 必填
#
# 退出码：
#   0  包内断言全过，且 D3 / D6 两维实跑且 5/5
#   1  有 FAIL（包内断言或判据维任一条失败）
#   2  D3/D6 未测：P98 缺失或判据维记 UNTESTED（包内断言照跑照打印）
set -u
cd "$(dirname "$0")"

python3 - <<'PY'
import json, re, sys

# ------------------------------------------------------------------
# 内置 JSON Schema 子集校验器。
# 支持：$ref(#/$defs/*)、oneOf、type(含 type 数组)、const、enum、required、
#       properties、additionalProperties(false / schema)、items、
#       pattern、min/maxLength、minimum、maximum、minItems、uniqueItems。
# 遇到任何未支持的关键字 -> 抛 Unsupported 并直接失败，绝不静默放行。
# 包内因此不需要 jsonschema，也不需要联网。
# ------------------------------------------------------------------
KNOWN = {'$schema','$id','title','description','$comment','$ref','oneOf','type',
         'const','enum','required','properties','additionalProperties','items',
         'pattern','minimum','maximum','maxLength','minLength','minItems','uniqueItems','$defs'}

class Unsupported(Exception):
    pass

def is_type(v, t):
    if t == 'object':  return isinstance(v, dict)
    if t == 'array':   return isinstance(v, list)
    if t == 'string':  return isinstance(v, str)
    if t == 'integer': return isinstance(v, int) and not isinstance(v, bool)
    if t == 'number':  return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == 'boolean': return isinstance(v, bool)
    if t == 'null':    return v is None
    raise Unsupported('type:' + str(t))

def resolve(root, ref):
    if not ref.startswith('#/'):
        raise Unsupported('external $ref ' + ref)
    cur = root
    for part in ref[2:].split('/'):
        cur = cur[part.replace('~1', '/').replace('~0', '~')]
    return cur

def validate(inst, sch, root, path='$'):
    if sch is True or sch == {}:
        return
    if sch is False:
        raise AssertionError(path + ': schema is false')
    if not isinstance(sch, dict):
        raise Unsupported(path + ': schema node is not dict')
    for k in sch:
        if k not in KNOWN:
            raise Unsupported(path + ': unsupported keyword ' + k)
    if '$ref' in sch:
        validate(inst, resolve(root, sch['$ref']), root, path)
        return
    if 'oneOf' in sch:
        hits = 0
        for br in sch['oneOf']:
            try:
                validate(inst, br, root, path)
                hits += 1
            except AssertionError:
                pass
        if hits != 1:
            raise AssertionError('%s: oneOf matched %d branches (want exactly 1)'
                                 % (path, hits))
        return
    if 'type' in sch:
        ts = sch['type'] if isinstance(sch['type'], list) else [sch['type']]
        if not any(is_type(inst, t) for t in ts):
            raise AssertionError('%s: expect type %s, got %s'
                                 % (path, ts, type(inst).__name__))
    if 'const' in sch and inst != sch['const']:
        raise AssertionError('%s: const mismatch' % path)
    if 'enum' in sch and inst not in sch['enum']:
        raise AssertionError('%s: not in enum %s' % (path, sch['enum']))
    if isinstance(inst, dict):
        for r in sch.get('required', []):
            if r not in inst:
                raise AssertionError('%s: missing required %s' % (path, r))
        props = sch.get('properties', {})
        ap = sch.get('additionalProperties', True)
        for k, v in inst.items():
            if k in props:
                validate(v, props[k], root, path + '.' + k)
            elif ap is False:
                raise AssertionError('%s: unexpected key %s' % (path, k))
            elif isinstance(ap, dict):
                validate(v, ap, root, path + '.' + k)
    if isinstance(inst, list):
        items = sch.get('items')
        if items is not None:
            for i, v in enumerate(inst):
                validate(v, items, root, '%s[%d]' % (path, i))
        if 'minItems' in sch and len(inst) < sch['minItems']:
            raise AssertionError('%s: minItems' % path)
        if sch.get('uniqueItems'):
            seen = {json.dumps(x, sort_keys=True, ensure_ascii=False) for x in inst}
            if len(seen) != len(inst):
                raise AssertionError('%s: items not unique' % path)
    if isinstance(inst, str):
        if 'pattern' in sch and not re.search(sch['pattern'], inst):
            raise AssertionError('%s: pattern %s not matched' % (path, sch['pattern']))
        if 'maxLength' in sch and len(inst) > sch['maxLength']:
            raise AssertionError('%s: maxLength' % path)
        if 'minLength' in sch and len(inst) < sch['minLength']:
            raise AssertionError('%s: minLength' % path)
    if isinstance(inst, (int, float)) and not isinstance(inst, bool):
        if 'minimum' in sch and inst < sch['minimum']:
            raise AssertionError('%s: minimum' % path)
        if 'maximum' in sch and inst > sch['maximum']:
            raise AssertionError('%s: maximum' % path)

FAILS = []
RAN = [0]
def chk(name, fn):
    RAN[0] += 1
    try:
        detail = fn() or ''
        print('PASS %-28s %s' % (name, detail))
    except AssertionError as e:
        FAILS.append(name)
        print('FAIL %-28s %s' % (name, e))
    except Unsupported as e:
        FAILS.append(name)
        print('FAIL %-28s UNSUPPORTED %s' % (name, e))

sch = json.load(open('agent-event.schema.json', encoding='utf-8'))

def c_schema():
    assert sch['$schema'].endswith('2020-12/schema')
    assert len(sch['$defs']['AgentEvent']['oneOf']) == 12
    assert len(sch['$defs']['AgentState']['enum']) == 9
    return '12 events / 9 states'

def c_sample(fn):
    def f():
        validate(json.load(open(fn, encoding='utf-8')), sch, sch)
        return fn
    return f

BAD = {
 'reject_B_gen_envelope':
   {"v":1,"seq":1,"ts":"2026-11-24T12:00:00Z","type":"task.dispatch","agent_id":"a","payload":{}},
 'reject_unknown_event_key':
   {"v":1,"seq":2,"ts":1,"kind":"delta","events":[
     {"type":"seat_claim","agent_id":"a","seat_id":"tech-S02","zone_id":"tech","at":1,"x":1}]},
 'reject_state_queued':
   {"v":1,"seq":3,"ts":1,"kind":"delta","events":[
     {"type":"agent_state","agent_id":"a","state":"queued","at":1}]},
 'reject_bad_seat_id':
   {"v":1,"seq":4,"ts":1,"kind":"delta","events":[
     {"type":"seat_claim","agent_id":"a","seat_id":"seat02","zone_id":"tech","at":1}]},
}

def c_reject(name):
    def f():
        try:
            validate(BAD[name], sch, sch)
        except AssertionError:
            return 'rightly rejected'
        raise AssertionError('accepted, should have been rejected')
    return f

chk('schema_2020_12_12_9', c_schema)
chk('sample_v1_valid', c_sample('sample-envelope.json'))
chk('sample_v12_valid', c_sample('sample-envelope-v12.json'))
for name in BAD:
    chk(name, c_reject(name))

z = json.load(open('office-zones.json', encoding='utf-8'))

def c_headcount():
    assert z['stats']['headcount'] == 23
    return str(z['stats']['headcount'])

def c_seatsum():
    tot = sum(len(x.get('seats', [])) for x in z['zones'])
    assert tot == z['stats']['headcount']
    return str(tot)

def depts():
    return [x for x in z['zones'] if x['role'] != 'facility' and x['id'] != 'boss_office']

def c_depts():
    assert len(depts()) == 7, len(depts())
    return '7 depts'

def c_cap():
    bad = [x['id'] for x in depts() if len(x['seats']) > 3]
    assert not bad, bad
    return 'all <=3'

def c_boss():
    boss = [x for x in z['zones'] if x['id'] == 'boss_office'][0]
    assert len(boss['seats']) == 2
    return '2'

def c_standby():
    assert z['stats']['standby_seats'] == 0
    assert z['seat_policy']['seat_cap_per_dept'] == 3
    return '0 / cap3'

def c_seatid():
    for x in z['zones']:
        for s in x.get('seats', []):
            assert re.match(r'^[a-z0-9_]+-S\d{2}$', s['seat_id']), s['seat_id']
            assert s['seat_id'].startswith(x['id'] + '-'), s['seat_id']
            assert s['zone_id'] == x['id'], s['seat_id']
    return 'naming + zone binding'

chk('headcount_23', c_headcount)
chk('seats_sum_eq_headcount', c_seatsum)
chk('dept_count_7', c_depts)
chk('per_dept_le3', c_cap)
chk('boss_seats_2', c_boss)
chk('standby_seats_0_cap3', c_standby)
chk('seat_id_format_binding', c_seatid)

sm = json.load(open('seat-model.json', encoding='utf-8'))

def c_sm_total():
    assert sm.get('declared_total') == 23, sm.get('declared_total')
    return '23'

def c_sm_occ():
    assert sm.get('occupancy_mode') == 'one_agent_per_seat', sm.get('occupancy_mode')
    return sm['occupancy_mode']

def c_sm_consist():
    zsum = sum(len(x.get('seats', [])) for x in z['zones'])
    assert sm.get('declared_total') == zsum
    return 'zones / seat-model agree'

chk('seat_model_total_23', c_sm_total)
chk('seat_model_occupancy', c_sm_occ)
chk('seat_model_matches_zones', c_sm_consist)

print('PKG_CHECKS pass=%d fail=%d total=%d' % (RAN[0] - len(FAILS), len(FAILS), RAN[0]))
sys.exit(0 if not FAILS else 1)
PY
RC=$?

# ---- 判据维：P98= 必填；缺失就如实记未测、退出码 2，不吞失败、不自动找 ----
P98="${P98:-}"
if [ -z "$P98" ] || [ ! -f "$P98" ]; then
  echo "D3/D6 未测：P98= 必填（p98check.py 判据器路径，随源码根分发，不在本包内）"
  if [ "$RC" -eq 0 ]; then exit 2; else exit 1; fi
fi

echo "---- p98check @ $P98"
python3 "$P98" --dim d3 --artifact seat-model.json; D3=$?
python3 "$P98" --dim d6 --artifact d6-page-selfcheck.json; D6=$?
echo "D3 rc=$D3  D6 rc=$D6   (0=全过 1=有FAIL 2=未测)"

if [ "$RC" -ne 0 ] || [ "$D3" -eq 1 ] || [ "$D6" -eq 1 ]; then exit 1; fi
if [ "$D3" -ne 0 ] || [ "$D6" -ne 0 ]; then exit 2; fi
exit 0
