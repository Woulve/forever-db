"""Merge the open base database with everyone's in-game recordings into the master database.

  python tools/build.py --base data/base.json --collected <folder(s) with *.lua> --out dist/forever.json

Recordings (CommandCenterCollect from Command Center's Collector, QuesticusCollect from Questicus) override the base for
names / levels (WoW Forever renamed or changed things), add Forever-only creatures, items,
vendors, quests, drops and map spots, and replace a base drop chance once enough loots
were recorded (FOREVER_RATE_MIN) because Forever changed many rates.
Master format = import_base.py format plus:
  spm  {"c123": {uiMap: [x, y, ...]}}       map spots (0-1000) seen in game
  vp   {npc: {item: [price, stack, limited, costs]}}
  seen {"c123": {item: [count, outOf]}}     raw loot counts (for future rate refinement)
  qsp  {quest: {uiMap: [x, y, ...]}}        where players made progress on a quest's objectives (Questicus)
  qsrc {quest: ["o645516", "c123", ...]}    what players looted right before an objective counted up (Questicus)
  ptl  {"c123": {uiMap: [x, y, ...]}}       a patrolling mob's path, in walking order (Questicus /qc patrol)
  qwk  {quest: [seconds, runs]}             how long the quest really takes (active time, Questicus)
Removed spots (QuesticusCollect.removed, players Ctrl-clicked "nothing here") delete the matching
spw / spm points of that npc / object after the recordings are merged.
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
                text = f.read()
            for var in ("CommandCenterCollect", "QuesticusCollect"):
                v = load_var(text, var)
                if isinstance(v, dict):
                    recs.append((path, v))
    return recs


def merge_recordings(recs):
    agg = {"loot": {}, "vend": {}, "qst": {}, "npc": {}, "obj": {}, "sp": {}, "item": {}, "qsp": {}, "qsrc": {},
           "ptl": {}, "qwk": {}, "removed": {}}
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
        for qid, maps in as_dict(r.get("qsp")).items():
            a = agg["qsp"].setdefault(int(qid), {})
            for m, pts in as_dict(maps).items():
                lst = a.setdefault(int(m), [])
                for k in range(0, len(pts) - 1, 2):
                    x, y = int(pts[k]), int(pts[k + 1])
                    if len(lst) >= SPOT_MAX * 2:
                        break
                    if not any(abs(lst[j] - x) <= SPOT_NEAR and abs(lst[j + 1] - y) <= SPOT_NEAR for j in range(0, len(lst), 2)):
                        lst += [x, y]
        for qid, srcs in as_dict(r.get("qsrc")).items():
            a = agg["qsrc"].setdefault(int(qid), {})
            for key, c in as_dict(srcs).items():
                key = str(key).replace(":", "")
                a[key] = a.get(key, 0) + int(c or 0)
        # patrol paths: the longest recording of each mob wins (they're walked in order, not merged)
        for key, maps in as_dict(r.get("patrol")).items():
            key = str(key).replace(":", "")
            for m, pts in as_dict(maps).items():
                pts = [int(v) for v in (pts if isinstance(pts, list) else list(as_dict(pts).values()))]
                cur = agg["ptl"].setdefault(key, {})
                if len(pts) >= 6 and len(pts) > len(cur.get(int(m), [])):
                    cur[int(m)] = pts[:400]
        # spots players removed in game ("nothing here")
        for key, lst in as_dict(r.get("removed")).items():
            key = str(key).replace(":", "")
            items = lst if isinstance(lst, list) else list(as_dict(lst).values())
            for e in items:
                e = as_dict(e)
                agg["removed"].setdefault(key, []).append(e)
        # active work time per quest: averaged over every run
        for qid, w in as_dict(r.get("qwork")).items():
            w = as_dict(w)
            s, n = float(w.get("s") or 0), int(w.get("n") or 0)
            if s > 5 and n > 0:
                a = agg["qwk"].setdefault(int(qid), [0.0, 0])
                a[0] += s * n
                a[1] += n
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
    # map positions from the addon databases (Forever maps) for anything without world coordinates
    db["spm"] = {k: v for k, v in (db.get("spz") or {}).items() if k not in db["spw"]}
    db["vp"], db["seen"] = {}, {}
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
    # quest objective areas / sources seen in game (Questicus)
    db["qsp"] = {q: {m: p for m, p in maps.items() if p} for q, maps in agg["qsp"].items()}
    db["qsrc"] = {}
    for q, srcs in agg["qsrc"].items():
        keep = [k for k, c in sorted(srcs.items(), key=lambda kv: -kv[1]) if c >= 2][:6]
        if keep:
            db["qsrc"][q] = keep
    db["ptl"] = {k: v for k, v in agg["ptl"].items() if v}
    db["qwk"] = {q: [round(a[0] / a[1]), a[1]] for q, a in agg["qwk"].items() if a[1] > 0}
    # map spots
    for key, maps in agg["sp"].items():
        kind, sid = who(key)
        cur = db["spm"].setdefault(kind + str(sid), {})
        for m, pts in maps.items():
            lst = cur.setdefault(str(m), [])
            for k in range(0, len(pts) - 1, 2):
                if not any(abs(lst[j] - pts[k]) <= SPOT_NEAR and abs(lst[j + 1] - pts[k + 1]) <= SPOT_NEAR for j in range(0, len(lst) - 1, 2)):
                    lst += [pts[k], pts[k + 1]]
    remove_spots(db, agg["removed"])      # last: also catches spots players recorded themselves
    return db


REMOVE_WORLD = 12       # yards
REMOVE_MAP = 15         # 0-1000 map units


def remove_spots(db, removed):
    """Delete spw / spm points near the spots players removed in game."""
    n = 0
    for key, spots in removed.items():
        world = [(int(float(e.get("i") or -1)), float(e.get("x") or 0), float(e.get("y") or 0)) for e in spots if e.get("i") is not None]
        maps = [(int(float(e.get("m"))), int(float(e.get("mx"))), int(float(e.get("my")))) for e in spots
                if e.get("m") not in (None, False) and e.get("mx") is not None and e.get("my") is not None]
        groups = db.get("spw", {}).get(key)
        if groups:
            keep = []
            for g in groups:
                inst, pts = g[0], g[1:]
                out = [inst]
                for k in range(0, len(pts) - 1, 2):
                    x, y = pts[k], pts[k + 1]
                    if any(i == inst and abs(x - rx) <= REMOVE_WORLD and abs(y - ry) <= REMOVE_WORLD for i, rx, ry in world):
                        n += 1
                        continue
                    out += [x, y]
                if len(out) > 1:
                    keep.append(out)
            db["spw"][key] = keep
        cur = db.get("spm", {}).get(key)
        if cur:
            for m in list(cur.keys()):
                pts = cur[m]
                out = []
                for k in range(0, len(pts) - 1, 2):
                    x, y = pts[k], pts[k + 1]
                    if any(str(mm) == str(m) and abs(x - rx) <= REMOVE_MAP and abs(y - ry) <= REMOVE_MAP for mm, rx, ry in maps):
                        n += 1
                        continue
                    out += [x, y]
                cur[m] = out
    db.setdefault("meta", {})["removedSpots"] = n
    return n


def digest(db):
    return hashlib.sha256(json.dumps(db, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def chain_prereqs(db):
    """A quest that another quest names as its next one (qx 7) but has no prerequisite of its own
    (qx 3 / 4) needs one of those quests first. QuestieDB often has only the forward link, e.g.
    The Goblin Trader -> Smuggler's Paradise. Returns how many quests got a prerequisite."""
    qx = db.get("qx") or {}
    prev = {}
    for q, row in qx.items():
        if len(row) > 6 and row[6]:
            prev.setdefault(int(row[6]), set()).add(int(q))
    n = 0
    for q, prevs in prev.items():
        row = qx.get(q) if q in qx else qx.get(str(q))
        if row is None:
            continue
        has = (len(row) > 2 and row[2]) or (len(row) > 3 and row[3])
        if has:
            continue
        while len(row) < 3:
            row.append(None)
        row[2] = sorted(prevs)
        n += 1
    return n


def apply_fixes(db, path):
    """fixes.json: hand-checked corrections that win over every source and recording."""
    if not path or not os.path.exists(path):
        return 0
    fx = json.load(open(path, encoding="utf-8"))
    n = 0
    spm = db.setdefault("spm", {})
    for key, maps in (fx.get("spm") or {}).items():
        spm[key] = {int(m): list(p) for m, p in maps.items()}
        if key in db.get("spw", {}):
            del db["spw"][key]           # the corrected map spots replace the world spawns too
        n += 1
    for t in ("qg", "qe"):
        tbl = db.setdefault(t, {})
        for q, keys in (fx.get(t) or {}).items():
            cur = tbl.setdefault(int(q), [])
            for k in keys:
                if k not in cur:
                    cur.append(k)
                    n += 1
    for q, pre in (fx.get("pre") or {}).items():     # prerequisite quests (any one of them)
        row = db.setdefault("qx", {}).setdefault(int(q), [])
        while len(row) < 3:
            row.append(None)
        row[2] = list(pre)
        n += 1
    for q, mask in (fx.get("races") or {}).items():  # who can take the quest (race mask, 0 = everyone)
        row = db.setdefault("qx", {}).setdefault(int(q), [])
        while len(row) < 1:
            row.append(None)
        row[0] = int(mask)
        n += 1
    note = db.setdefault("note", {})
    for key, text in (fx.get("note") or {}).items():
        note[key] = text
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--collected", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--source-note", default="cMaNGOS classic-db (GPL-3.0) + WoW Forever in-game recordings")
    ap.add_argument("--sources-json", help="JSON list of {name, repo, ref, licence} for meta.sourceList")
    ap.add_argument("--fixes", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fixes.json"),
                    help="hand-checked corrections (default: fixes.json in the repo)")
    a = ap.parse_args()
    with open(a.base, encoding="utf-8") as f:
        base = json.load(f)
    recs = load_recordings(a.collected)
    agg = merge_recordings(recs)
    db = build(base, agg)
    chained = chain_prereqs(db)
    fixed = apply_fixes(db, a.fixes)
    h = digest(db)
    db["meta"] = {
        "build": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "hash": h[:16],
        "sources": a.source_note,
        "recordings": len(recs),
        "fixes": fixed,
        "chainPrereqs": chained,
        "sourceList": json.load(open(a.sources_json)) if a.sources_json and os.path.exists(a.sources_json) else [],
        "counts": {k: len(v) for k, v in db.items() if isinstance(v, dict) and k not in ("loc", "src")},
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(db, f, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
    print("master:", a.out, db["meta"])


if __name__ == "__main__":
    main()
