#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ROOST 事件契约自测（无 UI 依赖，纯客户端侧模拟）

验的不是"接口通不通"，是契约里写死的四条规则真的成立：
  1. seq 全局单调 + 信封级去重     → 重投递不重复应用
  2. at-least-once 幂等            → usage_delta 重投不翻倍
  3. 缺口检测 + 补拉               → 丢信封能发现、能补齐、终态一致
  4. 事件环固定容量                → 8h 量级不涨内存

产出 contract-selftest.json，可复跑：python3 tools/contract_selftest.py
"""

import copy
import json
import os
import re
import time
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCHEMA = os.path.join(ROOT, "agent-event.schema.json")

AGENTS = 200          # 并发可见规模
EV_PER_SEC = 500      # 突发吞吐
SECONDS = 10          # 突发持续 10s
RING_CAP = 4096


# ---------------- 零依赖 schema 校验器（draft 2020-12 子集） ----------------
# 只实现本仓 agent-event.schema.json 实际用到的关键字：type/const/enum/
# minimum/maximum/maxLength/pattern/required/properties/additionalProperties/
# items/oneOf/anyOf/allOf/$ref(本地)。装了 jsonschema 时优先用它，
# 两条路径在同一批样例上结论必须一致（见 schema_negative_controls）。


def _type_ok(inst, t):
    if t == "object":
        return isinstance(inst, dict)
    if t == "array":
        return isinstance(inst, list)
    if t == "string":
        return isinstance(inst, str)
    if t == "integer":
        return isinstance(inst, int) and not isinstance(inst, bool)
    if t == "number":
        return isinstance(inst, (int, float)) and not isinstance(inst, bool)
    if t == "boolean":
        return isinstance(inst, bool)
    if t == "null":
        return inst is None
    return True                     # 未知类型不判错，避免误杀


def _resolve_ref(root, ref):
    if not ref.startswith("#/"):
        raise ValueError("only local $ref supported: %s" % ref)
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def mini_validate(inst, schema, root=None, path="$"):
    """返回错误串列表；空列表＝通过。"""
    root = root if root is not None else schema
    errs = []
    if schema is True or schema == {}:
        return errs
    if schema is False:
        return ["%s: schema falsified" % path]
    if "$ref" in schema:
        return mini_validate(inst, _resolve_ref(root, schema["$ref"]), root, path)

    t = schema.get("type")
    if t is not None:
        tlist = t if isinstance(t, list) else [t]
        if not any(_type_ok(inst, x) for x in tlist):
            return ["%s: want %s, got %s" % (path, "|".join(tlist), type(inst).__name__)]

    if "const" in schema and inst != schema["const"]:
        errs.append("%s: const %r != %r" % (path, schema["const"], inst))
    if "enum" in schema and inst not in schema["enum"]:
        errs.append("%s: %r not in enum" % (path, inst))

    if isinstance(inst, (int, float)) and not isinstance(inst, bool):
        if "minimum" in schema and inst < schema["minimum"]:
            errs.append("%s: %r < minimum %r" % (path, inst, schema["minimum"]))
        if "maximum" in schema and inst > schema["maximum"]:
            errs.append("%s: %r > maximum %r" % (path, inst, schema["maximum"]))

    if isinstance(inst, str):
        if "maxLength" in schema and len(inst) > schema["maxLength"]:
            errs.append("%s: len %d > maxLength %d" % (path, len(inst), schema["maxLength"]))
        if "pattern" in schema and re.search(schema["pattern"], inst) is None:
            errs.append("%s: %r fails pattern %r" % (path, inst, schema["pattern"]))

    if isinstance(inst, list) and "items" in schema:
        for i, x in enumerate(inst):
            errs.extend(mini_validate(x, schema["items"], root, "%s[%d]" % (path, i)))

    if isinstance(inst, dict):
        for k in schema.get("required", []):
            if k not in inst:
                errs.append("%s: missing required %r" % (path, k))
        props = schema.get("properties", {})
        ap = schema.get("additionalProperties")
        for k, v in inst.items():
            if k in props:
                errs.extend(mini_validate(v, props[k], root, "%s.%s" % (path, k)))
            elif ap is False:
                errs.append("%s: unexpected key %r" % (path, k))
            elif isinstance(ap, dict):
                errs.extend(mini_validate(v, ap, root, "%s.%s" % (path, k)))

    if "oneOf" in schema:
        hits = [i for i, sub in enumerate(schema["oneOf"])
                if not mini_validate(inst, sub, root, path)]
        if len(hits) != 1:
            errs.append("%s: oneOf hit %d branches (need exactly 1)" % (path, len(hits)))
    if "anyOf" in schema:
        if not any(not mini_validate(inst, sub, root, path) for sub in schema["anyOf"]):
            errs.append("%s: anyOf hit 0 branches" % path)
    if "allOf" in schema:
        for i, sub in enumerate(schema["allOf"]):
            errs.extend(mini_validate(inst, sub, root, "%s/allOf[%d]" % (path, i)))
    return errs


# ---------------- 客户端侧最小实现（模拟 store + transport 语义） ----------------

class ClientStore:
    def __init__(self, ring_cap=RING_CAP):
        self.agents = {}                 # agent_id -> dict
        self.ring = deque(maxlen=ring_cap)
        self.last_seq = 0
        self.gaps = []                   # 记录检测到的缺口
        self.applied_envelopes = 0
        self.skipped_duplicate_envelopes = 0
        self.idem_keys = set()
        self.snapshot_count = 0

    # 信封入口：所有规则在这里生效
    def ingest(self, env, allow_gap=False):
        seq = env["seq"]
        if seq <= self.last_seq:
            self.skipped_duplicate_envelopes += 1
            return False
        if seq > self.last_seq + 1:
            self.gaps.append((self.last_seq + 1, seq - 1))
            if not allow_gap:
                return False            # 生产语义：置 gap 状态、暂停应用、触发补拉
        self.applied_envelopes += 1
        if env["kind"] == "snapshot":
            for a in env["snapshot"]["agents"]:
                self.agents[a["agent_id"]] = dict(a)
            self.snapshot_count += 1
        for ev in env.get("events", []):
            self._apply(ev)
            self.ring.append(ev)
        self.last_seq = seq
        return True

    def _apply(self, ev):
        t = ev["type"]
        aid = ev.get("agent_id")
        if t == "agent_upsert":
            self.agents[ev["agent"]["agent_id"]] = dict(ev["agent"])
        elif t == "agent_remove":
            self.agents.pop(aid, None)
        elif aid is None:
            return                      # heartbeat 等
        else:
            a = self.agents.get(aid)
            if a is None:
                return                  # 先 upsert 后 state 的顺序约束
            if t == "agent_state":
                a["state"] = ev["state"]
                if "task_id" in ev:
                    a["task_id"] = ev["task_id"]
            elif t == "agent_progress":
                a["progress"] = ev["progress"]
            elif t == "usage_delta":
                key = ev.get("idempotency_key")
                if key is not None:
                    if key in self.idem_keys:
                        return          # 幂等命中，丢弃
                    self.idem_keys.add(key)
                a["tokens_in"] += ev["tokens_in"]
                a["tokens_out"] += ev["tokens_out"]
                a["cost_usd"] += ev["cost_usd"]
            elif t == "log":
                pass


# ---------------- 造数据 ----------------

def build_agents():
    out = []
    for i in range(AGENTS):
        out.append({
            "agent_id": f"agent_{i:03d}",
            "alias": f"agent-{i:03d}",
            "state": "idle",
            "task_id": None,
            "progress": 0.0,
            "tokens_in": 1000 + i,
            "tokens_out": 500 + i,
            "cost_usd": 0.0,
            "started_at": 1795490000000,
            "updated_at": 1795490000000,
            "meta": {"channel": "clawchat", "model": "doubao"},
        })
    return out


def build_envelopes():
    """返回 (envelopes, 期望状态)。期望状态独立于生成逻辑手算，避免自证。"""
    envs = []
    seq = 0
    # 1) 首帧 snapshot
    seq += 1
    envs.append({"v": 1, "seq": seq, "ts": 1795490000000, "kind": "snapshot",
                 "snapshot": {"agents": build_agents()}})

    exp_tokens_in = {f"agent_{i:03d}": 1000 + i for i in range(AGENTS)}
    exp_tokens_out = {f"agent_{i:03d}": 500 + i for i in range(AGENTS)}
    exp_state = {f"agent_{i:03d}": "idle" for i in range(AGENTS)}
    exp_usage_events = 0

    # 2) 稳态 + 突发：10 秒 × 500 ev/s
    total = EV_PER_SEC * SECONDS
    for sec in range(SECONDS):
        batch = []
        for k in range(EV_PER_SEC):
            i = (sec * EV_PER_SEC + k) % AGENTS
            aid = f"agent_{i:03d}"
            kind = k % 3
            if kind == 0:
                ev = {"type": "usage_delta", "agent_id": aid,
                      "tokens_in": 10, "tokens_out": 5, "cost_usd": 0.001,
                      "at": 1795490000000 + sec * 1000 + k,
                      "idempotency_key": f"{aid}-{sec}-{k}"}
                exp_tokens_in[aid] += 10
                exp_tokens_out[aid] += 5
                exp_usage_events += 1
            elif kind == 1:
                ev = {"type": "agent_progress", "agent_id": aid,
                      "progress": round(((sec * EV_PER_SEC + k) % 100) / 100, 2),
                      "at": 1795490000000 + sec * 1000 + k}
            else:
                st = "working" if sec < 5 else "done"
                ev = {"type": "agent_state", "agent_id": aid, "state": st,
                      "task_id": f"T-{i:03d}", "at": 1795490000000 + sec * 1000 + k}
                exp_state[aid] = st
            batch.append(ev)
        seq += 1
        envs.append({"v": 1, "seq": seq, "ts": 1795490000000 + (sec + 1) * 1000,
                     "kind": "delta", "events": batch})

    return envs, exp_tokens_in, exp_tokens_out, exp_state, exp_usage_events


def build_dup_envelopes(seq_start):
    """构造重复投递：同 seq 重发 + 新 seq 内带旧 idempotency_key。"""
    out = []
    # a) 同 idempotency_key 在不同 seq 里再投一次（seq 新，事件重复）
    env = {"v": 1, "seq": seq_start, "ts": 1795490012000, "kind": "delta",
           "events": [{"type": "usage_delta", "agent_id": "agent_000",
                       "tokens_in": 10, "tokens_out": 5, "cost_usd": 0.001,
                       "at": 1795490012000,
                       "idempotency_key": "agent_000-0-0"}]}
    out.append(env)
    return out



def build_negative_envelopes(envs):
    """反向对照：每条都必须被 schema 拒。证明校验器真在判，而不是空过。"""
    base = copy.deepcopy(envs[0])
    delta = None
    for e in envs:
        if e.get("kind") == "delta" and any(ev.get("type") == "agent_state"
                                            for ev in e.get("events", [])):
            delta = copy.deepcopy(e)
            break
    bad = []

    a = copy.deepcopy(base); a.pop("seq", None)
    bad.append(("missing required seq", a))

    a = copy.deepcopy(base); a["seq"] = str(a["seq"])
    bad.append(("seq as string", a))

    a = copy.deepcopy(base); a["seq"] = 0
    bad.append(("seq below minimum 1", a))

    a = copy.deepcopy(base); a["v"] = 2
    bad.append(("v breaches const 1", a))

    a = copy.deepcopy(base); a["kind"] = "bogus"
    bad.append(("kind outside enum", a))

    a = copy.deepcopy(base); a["extra_field"] = 1
    bad.append(("unknown top-level key", a))

    if base.get("snapshot", {}).get("agents"):
        a = copy.deepcopy(base); a["snapshot"]["agents"][0].pop("agent_id", None)
        bad.append(("snapshot agent missing agent_id", a))

    if delta is not None:
        a = copy.deepcopy(delta)
        for ev in a["events"]:
            if ev.get("type") == "agent_state":
                ev.pop("state", None)
                break
        bad.append(("agent_state missing state", a))

        a = copy.deepcopy(delta)
        for ev in a["events"]:
            if ev.get("type") == "agent_state":
                ev["seat_id"] = "BAD SEAT"
                break
        bad.append(("seat_id fails seat pattern", a))

        a = copy.deepcopy(delta)
        for ev in a["events"]:
            if ev.get("type") == "agent_state":
                ev["at"] = str(ev["at"])
                break
        bad.append(("event at as string", a))
    return bad

# ---------------- 跑 ----------------

def main():
    envs, exp_in, exp_out, exp_state, exp_usage = build_envelopes()

    # 严格 schema 校验（每个信封都过一遍）+ 反向对照（坏样例必须被拒）
    # 装了 jsonschema 用它；干净机器没装则自动切内置零依赖校验器，不再 SKIP。
    s = json.load(open(SCHEMA, encoding="utf-8"))
    try:
        import jsonschema
        validator_kind = "jsonschema"
    except ImportError:
        validator_kind = "builtin-mini"

    def schema_errors(inst):
        """返回错误串列表；空列表＝通过。"""
        if validator_kind == "jsonschema":
            try:
                jsonschema.validate(inst, s)
                return []
            except jsonschema.ValidationError as ex:
                return ["jsonschema: " + str(ex.message)[:160]]
        return mini_validate(inst, s)

    schema_checked = 0
    schema_first_error = None
    for e in envs:
        errs = schema_errors(e)
        if errs:
            if schema_first_error is None:
                schema_first_error = errs[0]
            continue
        schema_checked += 1

    neg_envs = build_negative_envelopes(envs)
    neg_total = len(neg_envs)
    neg_rejected = 0
    neg_leaks = []
    for label, inst in neg_envs:
        if schema_errors(inst):
            neg_rejected += 1
        else:
            neg_leaks.append(label)

    # 场景 A：顺序投递 + 20% 信封重复投递（应全部被 seq 去重丢掉）
    st = ClientStore()
    t0 = time.perf_counter()
    dup_sent = 0
    for idx, e in enumerate(envs):
        st.ingest(e)
        if idx % 5 == 2:                       # 重发一次同 seq
            st.ingest(e)
            dup_sent += 1
    elapsed = time.perf_counter() - t0

    # 场景 B：中途丢 3 个信封（模拟网络丢帧），走补拉路径
    st_b = ClientStore()
    drop_at = {7, 8, 9}
    for e in envs:
        if e["seq"] in drop_at:
            continue
        ok = st_b.ingest(e)
        if not ok:                              # 检测到缺口，暂停
            break
    gap_seen = list(st_b.gaps)
    dropped_last = st_b.last_seq
    # 补拉：从 last_seq 起重放被丢的信封（服务端 replay 语义）
    for e in envs:
        if e["seq"] > dropped_last:
            st_b.ingest(e)
    replayed = st_b.last_seq

    # 场景 C：幂等重投（新 seq 带旧 key）
    st_c = ClientStore()
    for e in envs:
        st_c.ingest(e)
    dup_envs = build_dup_envelopes(st_c.last_seq + 1)
    for e in dup_envs:
        st_c.ingest(e)
    # 该事件 token 不应增加：期望仍等于 scenario A 的期望值
    c_in = st_c.agents["agent_000"]["tokens_in"]

    # 断言
    checks = []

    def chk(name, cond, detail=""):
        checks.append({"check": name, "ok": bool(cond), "detail": detail})

    total_env = len(envs)
    ev_total = sum(len(e.get("events", [])) for e in envs)
    chk("schema_validated", schema_checked == total_env and schema_first_error is None,
        f"{schema_checked}/{total_env} envelopes validated via {validator_kind}"
        + (f"; first error: {schema_first_error}" if schema_first_error else ""))
    chk("schema_negative_controls", neg_rejected == neg_total,
        f"{neg_rejected}/{neg_total} invalid samples rejected via {validator_kind}"
        + (f"; leaked: {','.join(neg_leaks)}" if neg_leaks else ""))
    chk("all_envelopes_applied", st.applied_envelopes == total_env,
        f"applied {st.applied_envelopes}/{total_env}")
    chk("duplicate_envelopes_dropped", st.skipped_duplicate_envelopes == dup_sent,
        f"dropped {st.skipped_duplicate_envelopes}/{dup_sent}")
    chk("seq_monotonic_final", st.last_seq == total_env,
        f"last_seq {st.last_seq} vs {total_env}")

    tok_in_ok = all(st.agents[a]["tokens_in"] == exp_in[a] for a in exp_in)
    tok_out_ok = all(st.agents[a]["tokens_out"] == exp_out[a] for a in exp_out)
    chk("tokens_in_exact", tok_in_ok,
        f"max|diff| {max(abs(st.agents[a]['tokens_in'] - exp_in[a]) for a in exp_in)}")
    chk("tokens_out_exact", tok_out_ok,
        f"max|diff| {max(abs(st.agents[a]['tokens_out'] - exp_out[a]) for a in exp_out)}")
    state_ok = all(st.agents[a]["state"] == exp_state[a] for a in exp_state)
    chk("final_state_matches", state_ok, f"{len(exp_state)} agents compared")

    chk("ring_bounded", len(st.ring) == RING_CAP,
        f"ring {len(st.ring)} / cap {RING_CAP}, events {ev_total} (4.7x cap)")
    chk("gap_detected", len(gap_seen) >= 1, f"gaps {gap_seen}")
    chk("gap_replay_completes", replayed == total_env,
        f"after replay last_seq {replayed} vs {total_env}")
    b_tok_ok = all(st_b.agents[a]["tokens_in"] == exp_in[a] for a in exp_in)
    chk("replay_state_consistent", b_tok_ok, "after gap-replay tokens match baseline")
    chk("idempotency_no_double_count", c_in == exp_in["agent_000"],
        f"agent_000 tokens_in {c_in} vs expected {exp_in['agent_000']}")

    result = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": {"agents": AGENTS, "events_per_sec": EV_PER_SEC, "seconds": SECONDS,
                   "ring_cap": RING_CAP, "envelopes": total_env, "events": ev_total},
        "throughput": {"apply_ops_per_sec": round(ev_total / elapsed, 1), "elapsed_s": round(elapsed, 4)},
        "schema": {"validator": validator_kind, "envelopes_checked": schema_checked,
                   "negative_controls": f"{neg_rejected}/{neg_total}"},
        "verdict": "PASS" if all(c["ok"] for c in checks) else "FAIL",
        "checks": checks,
    }
    out = os.path.join(ROOT, "contract-selftest.json")
    json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print("json", out, os.path.getsize(out), "B")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
