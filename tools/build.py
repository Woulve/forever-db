"""Merge the open base database with everyone's in-game recordings into the master database.

  python tools/build.py --base data/base.json --collected <folder(s) with *.lua> --out dist/forever.json

Recordings (CommandCenterCollect from Command Center's Collector) override the base for
names / levels (WoW Forever renamed or changed things), add Forever-only creatures, items,
vendors, quests, drops and map spots, and replace a base drop chance once enough loots
were recorded (FOREVER_RATE_MIN) because Forever changed many rates.
Master format = import_base.py format plus:
  spm  {"c123": {uiMap: [x, y, ...]}}       map spots (0-1000) seen in game
  vp   {npc: {item: [price, stack, limited, costs]}}
  seen {"c123": {item: [count, outOf]}}     raw loot counts (for future rate refinement)
  meta {build, sources, counts}
"""
import argparse, glob, json, os, sys, hashlib, datetime

sys.path.insert(0, os.path.dirname(__file__))
from luatable import load_var

FOREVER_RATE_MIN = 20     # looted this many times before a recorded rate replaces the base rate
NEW_RATE_MIN = 3          # recorded drops shown when the base doesn't have them at all
SPOT_NEAR = 15
SPOT_MAX = 60


def keyed(d):
    return {int(k) if isinstance(k, str) and k.lstrip("-").isdigit() else k: v for k, v in (d or {}).items()}


def as_dict(v):
    if isinstance(v, list):
        return {i + 1: x for i, x in enumerate(v)}
    return v or {}


def load_recordings(folders):
    recs = []
    for folder in folders:
        for path in sorted(glob.glob(os.path.join(folder, "**", "*.lua"), recursive=True)):
            with open(path, encoding="utf-8", errors="replace") as f:
                v = load_var(f.read(), "CommandCenterCollect")
            if isinstance(v, dict):
                recs.append((path, v))
    return recs


def merge_recordings(recs):
    agg = {"loot": {}, "vend": {}, "qst": {}, "npc": {}, "obj": {}, "sp": {}, "item": {}}
    for _, r in recs:
        for key, e in as_dict(r.get("loot")).items():
            e = as_dict(e)
            a = agg["loot"].setdefault(key, {"n": 0, "i": {}})
            a["n"] += int(e.get("n") or 0)
            for it, c in as_dict(e.get("i")).items():
                a["i"][int(it)] = a["i"].get(int(it), 0) + int(c)
        for npc, lst in as_dict(r.get("vend")).items():
            lst = as_dict(lst)
            cur = agg["vend"].get(int(npc))
            if cur is None or (lst.get("t") or 0) >= (cur.get("t") or 0):
                agg["vend"][int(npc)] = lst
        for qid, e in as_dict(r.get("qst")).items():
            e = as_dict(e)
            a = agg["qst"].setdefault(int(qid), {})
            for k in ("n", "lv"):
                if e.get(k):
                    a[k] = e[k]
            for k in ("g", "e", "r", "c"):
                for v in (e.get(k) or []):
                    a.setdefault(k, [])
                    if v not in a[k]:
                        a[k].append(v)
        for npc, e in as_dict(r.get("npc")).items():
            e = e if isinstance(e, list) else [as_dict(e).get(k) for k in range(1, 6)]
            e = (e + [None] * 5)[:5]
            a = agg["npc"].get(int(npc))
            if a is None:
                agg["npc"][int(npc)] = list(e)
            else:
                a[0] = e[0] or a[0]
                if isinstance(e[1], int) and e[1] > 0:
                    a[1] = min(a[1], e[1]) if isinstance(a[1], int) and a[1] > 0 else e[1]
                if isinstance(e[2], int) and e[2] > 0:
                    a[2] = max(a[2] or 0, e[2])
                a[3] = e[3] if e[3] is not None else a[3]
                a[4] = e[4] if e[4] is not None else a[4]
        for oid, e in as_dict(r.get("obj")).items():
            e = e if isinstance(e, list) else [as_dict(e).get(1)]
            if e and e[0]:
                agg["obj"][int(oid)] = [e[0]]
        for key, maps in as_dict(r.get("sp")).items():
            a = agg["sp"].setdefault(key, {})
            for m, pts in as_dict(maps).items():
                lst = a.setdefault(int(m), [])
                for k in range(0, len(pts) - 1, 2):
                    x, y = int(pts[k]), int(pts[k + 1])
                    if len(lst) >= SPOT_MAX * 2:
                        break
                    if not any(abs(lst[j] - x) <= SPOT_NEAR and abs(lst[j + 1] - y) <= SPOT_NEAR for j in range(0, len(lst), 2)):
                        lst += [x, y]
        for it, e in as_dict(r.get("item")).items():
            e = e if isinstance(e, list) else [as_dict(e).get(1), as_dict(e).get(2)]
            if e and e[0]:
                agg["item"][int(it)] = [e[0], e[1] if len(e) > 1 else None]
    return agg


def who(key):
    """'c:123' -> ('c', 123)"""
    k, _, i = str(key).partition(":")
    return k, int(i)


def build(base, agg):
    db = {k: keyed(v) for k, v in base.items() if k != "meta"}
    for k in ["npc", "obj", "item", "quest", "qg", "qe", "drop", "odrop", "idrop", "vend", "rew", "start", "world", "spw"]:
        db.setdefault(k, {})
    db["spm"], db["vp"], db["seen"] = {}, {}, {}
    # names / levels
    for npc, e in agg["npc"].items():
        b = db["npc"].get(npc)
        if b is None:
            db["npc"][npc] = [e[0], None, e[1], e[2], e[3] or 0]
        else:
            if e[0]:
                b[0] = e[0]
            if isinstance(e[1], int) and e[1] != 0:
                b[2], b[3] = e[1], e[2]
            if e[3] is not None:
                b[4] = e[3]
    for oid, e in agg["obj"].items():
        db["obj"][oid] = [e[0]]
    for it, e in agg["item"].items():
        b = db["item"].get(it)
        db["item"][it] = [e[0], e[1] if e[1] is not None else (b[1] if b else None), b[2] if b else None]
    # loot
    field = {"c": "drop", "o": "odrop", "i": "idrop"}
    for key, e in agg["loot"].items():
        kind, sid = who(key)
        f = field.get(kind)
        if not f or e["n"] <= 0:
            continue
        db["seen"][kind + str(sid)] = {it: [c, e["n"]] for it, c in e["i"].items()}
        for it, c in e["i"].items():
            ch = int(round(min(1.0, c / e["n"]) * 10000))
            lst = db[f].setdefault(it, [])
            cur = next((p for p in lst if p[0] == sid), None)
            if cur is None:
                if e["n"] >= NEW_RATE_MIN or c >= 2 or not lst:
                    lst.append([sid, ch])
            elif e["n"] >= FOREVER_RATE_MIN:
                cur[1] = ch
            lst.sort(key=lambda p: -p[1])
    # vendors
    for npc, lst in agg["vend"].items():
        for it, v in lst.items():
            if it == "t":
                continue
            it = int(it)
            vl = db["vend"].setdefault(it, [])
            if npc not in vl:
                vl.append(npc)
            v = v if isinstance(v, list) else [as_dict(v).get(k) for k in range(1, 5)]
            db["vp"].setdefault(npc, {})[it] = (v + [None] * 4)[:4]
    # quests
    for qid, e in agg["qst"].items():
        b = db["quest"].get(qid)
        db["quest"][qid] = [e.get("n") or (b[0] if b else None), e.get("lv") or (b[1] if b else None), b[2] if b else None]
        for src, dst in (("g", "qg"), ("e", "qe")):
            for w in e.get(src, []):
                w = str(w).replace(":", "")
                lst = db[dst].setdefault(qid, [])
                if w not in lst:
                    lst.append(w)
        for it in e.get("r", []) + e.get("c", []):
            lst = db["rew"].setdefault(int(it), [])
            if qid not in lst:
                lst.append(qid)
    # map spots
    for key, maps in agg["sp"].items():
        kind, sid = who(key)
        db["spm"][kind + str(sid)] = maps
    return db


def digest(db):
    return hashlib.sha256(json.dumps(db, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--collected", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--source-note", default="cMaNGOS classic-db (GPL-3.0) + WoW Forever in-game recordings")
    a = ap.parse_args()
    with open(a.base, encoding="utf-8") as f:
        base = json.load(f)
    recs = load_recordings(a.collected)
    agg = merge_recordings(recs)
    db = build(base, agg)
    h = digest(db)
    db["meta"] = {
        "build": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "hash": h[:16],
        "sources": a.source_note,
        "recordings": len(recs),
        "counts": {k: len(v) for k, v in db.items() if isinstance(v, dict)},
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(db, f, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
    print("master:", a.out, db["meta"])


if __name__ == "__main__":
    main()
