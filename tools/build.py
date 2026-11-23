"""Merge the open base database with everyone's in-game recordings into the master database.

  python tools/build.py --base data/base.json --collected <folder(s) with *.lua> --out dist/forever.json

RULE (user, 2026-11-21): WoW Forever client data and everything recorded in game is what the release
uses, and it is never overwritten.
  - merge.py: the client tables win every field they have (first FOREVER source).
  - Recordings (CommandCenterCollect from Command Center's Collector, QuesticusCollect from Questicus)
    override the base and Drop Tables: names / levels, Forever-only creatures, items, vendors, quests,
    drops (a recorded chance always replaces the base / Drop Tables chance, from the first loot),
    money, skinning, fishing, map spots. No minimum counts for our own recordings.
  - Recordings are kept for good (--keep): each recording file is merged into recorded/<name>.json with
    a high-water mark (counts never go down, lists and keys are only added), so a reset SavedVariables
    or a deleted file can't take recorded data out of the database.
  - fixes.json (hand-checked in game) still corrects the sources, but recorded spots survive it.
  - slice.py never cuts a recorded drop / skin row with its max_rows caps.
  - Drop Tables (other players' recordings) replaces a base rate after DT_RATE_MIN kills.
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

DT_RATE_MIN = 20          # Drop Tables kills before its rate replaces a base rate (our recordings: always)
DT_NEW_MIN = 3            # Drop Tables kills before a drop the base doesn't have is added
SPOT_NEAR = 15
SPOT_MAX = 400            # recorded spots per map (deduplicated SPOT_NEAR apart)


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
            # utf-8-sig: the PC's sync script (PowerShell) writes a byte-order mark, which hid every
            # recording from the build until 2026-11-21
            with open(path, encoding="utf-8-sig", errors="replace") as f:
                text = f.read()
            for var in ("CommandCenterCollect", "QuesticusCollect"):
                v = load_var(text, var)
                if isinstance(v, dict):
                    recs.append((path, var, v))
    return recs


# ------------------------------------------------------------------ recordings kept for good
def high_water(old, new):
    """Merge two snapshots of the same recording: numbers never go down, dict keys and list entries are
    only added, text takes the newest non-empty value."""
    if isinstance(old, dict) and isinstance(new, dict):
        out = dict(old)
        for k, v in new.items():
            out[k] = high_water(old[k], v) if k in old else v
        return out
    if isinstance(old, list) and isinstance(new, list):
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in old + new):
            if len(old) % 2 == 0 and len(new) % 2 == 0:          # flat x, y spot lists: add new pairs
                out = list(old)
                have = {(old[i], old[i + 1]) for i in range(0, len(old), 2)}
                for i in range(0, len(new), 2):
                    if (new[i], new[i + 1]) not in have:
                        out += [new[i], new[i + 1]]
                        have.add((new[i], new[i + 1]))
                return out
            return new if len(new) >= len(old) else old
        out = list(old)
        seen = {json.dumps(v, sort_keys=True) for v in old}
        for v in new:
            s = json.dumps(v, sort_keys=True)
            if s not in seen:
                out.append(v)
                seen.add(s)
        return out
    if isinstance(old, bool) or isinstance(new, bool):
        return new if new is not None else old
    if isinstance(old, (int, float)) and isinstance(new, (int, float)):
        return max(old, new)
    return new if new not in (None, "") else old


def json_keys(v):
    """JSON can't keep int keys: make every key a string, the way a reload gives them back."""
    if isinstance(v, dict):
        return {str(k): json_keys(x) for k, x in v.items()}
    if isinstance(v, list):
        return [json_keys(x) for x in v]
    return v


def keep_recordings(recs, folder):
    """Merge every recording into folder/<file>.<var>.json and return the kept copies (all of them, also the
    ones whose recording file is gone)."""
    if not folder:
        return recs
    os.makedirs(folder, exist_ok=True)
    kept = {}
    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        with open(path, encoding="utf-8") as f:
            kept[os.path.basename(path)[:-5]] = json.load(f)
    changed = 0
    for path, var, v in recs:
        name = "%s.%s" % (os.path.splitext(os.path.basename(path))[0], var)
        v = json_keys(v)
        merged = high_water(kept[name], v) if name in kept else v
        if kept.get(name) != merged:
            kept[name] = merged
            with open(os.path.join(folder, name + ".json"), "w", encoding="utf-8") as f:
                json.dump(merged, f, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
            changed += 1
    print("recordings kept: %d (%d updated) in %s" % (len(kept), changed, folder))
    return [(os.path.join(folder, n + ".json"), n.rsplit(".", 1)[-1], v) for n, v in sorted(kept.items())]


def merge_recordings(recs):
    agg = {"loot": {}, "vend": {}, "qst": {}, "npc": {}, "obj": {}, "sp": {}, "item": {}, "qsp": {}, "qsrc": {},
           "ptl": {}, "qwk": {}, "removed": {}}
    for _, _, r in recs:
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


# ------------------------------------------------------------------ Questicus recorder, part 2 (Record.lua)
FISH_MIN = 1           # catches in a zone before its fishing chances are kept
SKIN_MIN = 1           # skinned corpses before a recorded skinning chance is kept
GOLD_MIN = 1           # looted corpses before a recorded money average is kept
QMISS_MIN = 1          # times an NPC didn't offer a quest before it's flagged


def xp_penalty(qlvl, plvl):
    """The game's grey-quest XP penalty (Questicus Quests.lua / Record.lua use the same)."""
    d = plvl - (qlvl or plvl)
    if d >= 10:
        return 0.1
    if d > 5:
        return 1 - 0.2 * (d - 5)
    return 1


def merge_extra(recs, agg):
    """The tables only Questicus' Record.lua fills: money, skinning, fishing, flight costs, trainers,
    quest details, offers, reputation, subzones, encounters, rares, gathering skills, items, creature types."""
    x = {k: {} for k in ("gold", "skinl", "fishl", "fcost", "trn", "qinfo", "qoff", "qmiss", "qrep", "zsub", "enc",
                         "rare", "oskill", "itemx", "ctype", "resp", "vendx", "osummon", "zcross")}
    for _, _, r in recs:
        for npc, e in as_dict(r.get("gold")).items():
            e = as_dict(e)
            a = x["gold"].setdefault(int(npc), {"n": 0, "c": 0, "lo": None, "hi": None})
            a["n"] += int(e.get("n") or 0)
            a["c"] += int(e.get("c") or 0)
            for k, f in (("lo", min), ("hi", max)):
                if e.get(k) is not None:
                    a[k] = e[k] if a[k] is None else f(a[k], e[k])
        for src, dst in (("skinl", "skinl"), ("fishl", "fishl")):
            for key, e in as_dict(r.get(src)).items():
                e = as_dict(e)
                a = x[dst].setdefault(int(key), {"n": 0, "i": {}})
                a["n"] += int(e.get("n") or 0)
                for it, c in as_dict(e.get("i")).items():
                    a["i"][int(it)] = a["i"].get(int(it), 0) + int(c or 0)
        for npc, e in as_dict(r.get("taxi")).items():
            e = as_dict(e)
            cur = x["fcost"].get(int(npc))
            if cur is None or (e.get("t") or 0) >= (cur.get("t") or 0):
                x["fcost"][int(npc)] = e
        for npc, e in as_dict(r.get("trn")).items():
            e = as_dict(e)
            cur = x["trn"].get(int(npc))
            if cur is None or (e.get("t") or 0) >= (cur.get("t") or 0):
                x["trn"][int(npc)] = e
        for qid, e in as_dict(r.get("qinfo")).items():
            e = as_dict(e)
            a = x["qinfo"].setdefault(int(qid), {})
            for k in ("o", "grp", "item", "lv"):
                if e.get(k):
                    a[k] = e[k]
            # rewards as the game showed them (0 money and empty item lists count: the game said so)
            if e.get("m") is not None:
                a["m"] = int(e["m"])
            for k in ("ch", "rw"):
                if e.get(k) is not None:
                    v = e[k] if isinstance(e[k], list) else list(as_dict(e[k]).values())
                    a[k] = [int(i) for i in v]
            if e.get("xb"):
                a["xb"] = int(e["xb"])
            for lv, xp in as_dict(e.get("xl")).items():
                a.setdefault("xl", {})[int(lv)] = int(xp)
            if e.get("minlv"):
                a["minlv"] = min(a.get("minlv") or 999, int(e["minlv"]))
        # XP / money really received at a turn-in (Details.lua): fills what the windows didn't
        for qid, e in as_dict(r.get("qact")).items():
            e = as_dict(e)
            a = x["qinfo"].setdefault(int(qid), {})
            if e.get("xp") and e.get("lv"):
                a.setdefault("act", {})[int(e["lv"])] = int(e["xp"])
            if e.get("money") is not None and "m" not in a:
                a["mact"] = int(e["money"])
        for npc, qs in as_dict(r.get("qoff")).items():
            for qid, lv in as_dict(qs).items():
                a = x["qoff"].setdefault(int(qid), {})
                lv = int(lv or 0)
                a[int(npc)] = min(a[int(npc)], lv) if a.get(int(npc)) and lv else (lv or a.get(int(npc)) or 0)
        for qid, npcs in as_dict(r.get("qmiss")).items():
            for npc, lv in as_dict(npcs).items():
                a = x["qmiss"].setdefault(int(qid), {}).setdefault(int(npc), [0, 0])
                a[0] += 1
                a[1] = max(a[1], int(lv or 0))
        for qid, facs in as_dict(r.get("qrep")).items():
            x["qrep"].setdefault(int(qid), {}).update({str(f): int(v) for f, v in as_dict(facs).items()})
        for m, subs in as_dict(r.get("area")).items():
            for name, pts in as_dict(subs).items():
                lst = x["zsub"].setdefault(int(m), {}).setdefault(str(name), [])
                pts = pts if isinstance(pts, list) else list(as_dict(pts).values())
                for k in range(0, len(pts) - 1, 2):
                    px, py = int(pts[k]), int(pts[k + 1])
                    if len(lst) < 120 and not any(abs(lst[j] - px) <= SPOT_NEAR and abs(lst[j + 1] - py) <= SPOT_NEAR
                                                  for j in range(0, len(lst), 2)):
                        lst += [px, py]
        for eid, e in as_dict(r.get("enc")).items():
            e = e if isinstance(e, list) else [as_dict(e).get(k) for k in range(1, 4)]
            x["enc"][int(eid)] = e
        for npc, l in as_dict(r.get("rare")).items():
            l = l if isinstance(l, list) else list(as_dict(l).values())
            a = x["rare"].setdefault(int(npc), [])
            for s in l:
                s = s if isinstance(s, list) else [as_dict(s).get(k) for k in range(1, 5)]
                if s and s[0] and s not in a:
                    a.append(s)
        for oid, e in as_dict(r.get("oskill")).items():
            e = e if isinstance(e, list) else [as_dict(e).get(1), as_dict(e).get(2)]
            if e and e[0]:
                x["oskill"][int(oid)] = e
        for it, e in as_dict(r.get("itemx")).items():
            e = e if isinstance(e, list) else [as_dict(e).get(k) for k in range(1, 10)]
            if e and e[0]:
                x["itemx"][int(it)] = e
        # vendors as players saw them (Record.lua): the newest visit of each vendor wins
        for npc, e in as_dict(r.get("vendx")).items():
            e = as_dict(e)
            cur = x["vendx"].get(int(npc))
            if cur is None or (e.get("t") or 0) >= (cur.get("t") or 0):
                x["vendx"][int(npc)] = e
        # objects that only appear when you do something (use an item on a mob, kill it): no timer
        for key, n in as_dict(r.get("osummon")).items():
            x["osummon"][str(key).replace(":", "")] = x["osummon"].get(str(key).replace(":", ""), 0) + int(n or 0)
        # zone border crossings players walked (Questicus Nav.lua): [continent]["zoneA-zoneB"] = {x, y, ...}
        for cont, prs in as_dict(r.get("zcross")).items():
            for pk, pts in as_dict(prs).items():
                pts = pts if isinstance(pts, list) else list(as_dict(pts).values())
                lst = x["zcross"].setdefault((int(cont), str(pk)), [])
                for j in range(0, len(pts) - 1, 2):
                    if isinstance(pts[j], (int, float)) and isinstance(pts[j + 1], (int, float)):
                        lst.append((float(pts[j]), float(pts[j + 1])))
        # respawn times measured at quest spots (Spots.lua): sum / count, shortest, "not back after"
        for key, e in as_dict(r.get("resp")).items():
            e = as_dict(e)
            key = str(key).replace(":", "")
            a = x["resp"].setdefault(key, {"n": 0, "s": 0.0, "lo": 0})
            a["n"] += int(e.get("n") or 0)
            a["s"] += float(e.get("s") or 0)
            a["lo"] = max(a["lo"], float(e.get("lo") or 0))
            if e.get("hi"):        # "found back by then": the respawn is at most this
                a["hi"] = min(a.get("hi") or 1e9, float(e.get("hi")))
        for npc, e in as_dict(r.get("ctype")).items():
            e = e if isinstance(e, list) else [as_dict(e).get(1), as_dict(e).get(2)]
            if e and e[0]:
                x["ctype"][int(npc)] = e
    # an NPC really offering a quest makes it a giver (fixes missing / wrong givers)
    for qid, npcs in x["qoff"].items():
        a = agg["qst"].setdefault(qid, {})
        for npc in npcs:
            a.setdefault("g", [])
            if "c:%d" % npc not in a["g"]:
                a["g"].append("c:%d" % npc)
    agg["x"] = x
    return x


def apply_extra(db, x):
    """Put Record.lua's tables in the master database (after Drop Tables, so recordings add to theirs)."""
    if not x:
        return {}
    gold, skin = db.setdefault("gold", {}), db.setdefault("skin", {})
    for npc, g in x["gold"].items():
        if g["n"] < GOLD_MIN:
            continue
        gold[npc] = [int(round(g["c"] / g["n"])), g["lo"], g["hi"], g["n"]]   # ours replace Drop Tables
    for npc, e in x["skinl"].items():
        if e["n"] < SKIN_MIN:
            continue
        for it, c in e["i"].items():
            lst = skin.setdefault(it, [])
            ch = int(round(min(1.0, c / e["n"]) * 10000))
            for p in lst:
                if p[0] == npc:
                    p[1] = ch                    # ours replace Drop Tables
                    break
            else:
                lst.append([npc, ch])
            lst.sort(key=lambda p: -p[1])
    # fishing: [[item, chance x 10000], ...] per uiMap
    db["fish"] = {m: sorted([[it, int(round(min(1.0, c / e["n"]) * 10000))] for it, c in e["i"].items()],
                            key=lambda p: -p[1])
                  for m, e in x["fishl"].items() if e["n"] >= FISH_MIN}
    # flight masters: { at = node, nodes = { name = [cost, x, y] } }
    db["fcost"] = {npc: {"at": e.get("at"), "nodes": {str(n): (v if isinstance(v, list) else list(as_dict(v).values()))[:3]
                                                       for n, v in as_dict(e.get("nodes")).items()}}
                   for npc, e in x["fcost"].items()}
    db["trn"] = {npc: {str(n): (v if isinstance(v, list) else [as_dict(v).get(k) for k in range(1, 5)])
                       for n, v in as_dict(e.get("s")).items()} for npc, e in x["trn"].items()}
    # class training: every ability's cost and level per class, from class trainers players opened
    # ("Name (Rank 2)" -> [cost copper, level]); older recordings keep the state in the name: dropped
    import re
    train = {}
    for npc, e in x["trn"].items():
        cls = e.get("cls")
        if not cls:
            continue
        t = train.setdefault(str(cls), {})
        for n, v in as_dict(e.get("s")).items():
            v = v if isinstance(v, list) else [as_dict(v).get(k) for k in range(1, 5)]
            name = re.sub(r" \((available|unavailable|used)\)$", "", str(n))
            if v and v[0] is not None and len(v) > 1 and v[1] is not None:
                cur = t.get(name)
                if cur is None or (e.get("t") or 0) >= cur[2]:
                    t[name] = [int(v[0]), int(v[1]), e.get("t") or 0]
    db["train"] = {c: {n: v[:2] for n, v in t.items()} for c, t in train.items()}
    # quest rewards: WoW Forever's own numbers replace the base table (qrw: money, full XP, choices, fixed)
    db.setdefault("qrw", {})
    qfix = 0
    for qid, e in x["qinfo"].items():
        q = db["quest"].get(qid)
        if e.get("lv") and q:
            q[1] = e["lv"]                          # the level the game gives the quest
        ql = e.get("lv") or (q[1] if q else None)
        full = e.get("xb")
        if not full:                                # work back from a level with a penalty (not grey)
            for lv, xp in sorted(list((e.get("xl") or {}).items()) + list((e.get("act") or {}).items())):
                p = xp_penalty(ql, lv)
                if p > 0.1:
                    full = int(round(xp / p))
                    break
        if full:
            e["xb"] = full
        money = e.get("m", e.get("mact"))
        if full or money is not None or "ch" in e or "rw" in e:
            b = list(db["qrw"].get(qid) or [0, 0, None, None])
            b += [None] * (4 - len(b))
            new = [money if money is not None else b[0], full or b[1],
                   (e["ch"] or None) if "ch" in e else b[2], (e["rw"] or None) if "rw" in e else b[3]]
            if new != b:
                qfix += 1
            db["qrw"][qid] = new
        for k in ("xl", "act", "mact"):
            e.pop(k, None)
    db["qinfo"] = x["qinfo"]
    for qid, e in x["qinfo"].items():
        q = db["quest"].get(qid)
        if q and len(q) > 2 and not q[2] and e.get("minlv"):
            q[2] = e["minlv"]                       # the lowest level it was offered at, when nothing else says
        if e.get("item"):
            db["start"].setdefault(int(e["item"]), qid)   # item -> the quest it starts
    db["qmiss"] = {qid: {npc: v[1] for npc, v in npcs.items() if v[0] >= QMISS_MIN}
                   for qid, npcs in x["qmiss"].items()}
    db["qmiss"] = {q: v for q, v in db["qmiss"].items() if v}
    db["qrep"] = x["qrep"]
    db["zsub"] = x["zsub"]
    db["enc"] = x["enc"]
    # rares: where they're seen, and the shortest gap between two sightings (a respawn hint, seconds)
    rare = {}
    for npc, l in x["rare"].items():
        l = sorted(l, key=lambda s: s[0])
        gaps = [b[0] - a[0] for a, b in zip(l, l[1:]) if b[0] - a[0] > 600]
        rare[npc] = {"n": len(l), "gap": min(gaps) if gaps else None,
                     "at": [[s[1], s[2], s[3]] for s in l[-10:] if len(s) >= 4]}
    db["rare"] = rare
    # respawn seconds per creature / object ("c123" / "o456"): the measured average, never less than
    # the longest time it was seen still gone
    resp = {}
    for key, a in x["resp"].items():
        if a["n"] > 0:
            t = a["s"] / a["n"]
            if a["lo"] > t:
                t = a["lo"] * 1.1
        elif a.get("hi") and a["lo"] > 0 and a["hi"] > a["lo"]:
            t = (a["lo"] + a["hi"]) / 2
        elif a.get("hi"):
            t = min(60, a["hi"])
        elif a["lo"] > 0:
            t = a["lo"] * 1.25
        else:
            continue
        resp[key] = int(round(min(3600, max(10, t))))
    # border crossings: points within 40 yards are one crossing (their average), most walked first, 12 per pair
    zc = {}
    for (cont, pk), pts in sorted(x["zcross"].items()):
        cl = []
        for px, py in pts:
            for c in cl:
                if (c[0] / c[2] - px) ** 2 + (c[1] / c[2] - py) ** 2 < 40 * 40:
                    c[0] += px; c[1] += py; c[2] += 1
                    break
            else:
                cl.append([px, py, 1])
        cl.sort(key=lambda c: -c[2])
        flat = []
        for c in cl[:12]:
            flat += [int(round(c[0] / c[2])), int(round(c[1] / c[2]))]
        zc.setdefault(str(cont), {})[pk] = flat
    db["zcross"] = zc
    # an object reported as "appears on a kill / item use" never gets a respawn time
    db["osummon"] = {k: 1 for k, n in x["osummon"].items() if n >= 2}
    for k in db["osummon"]:
        resp.pop(k, None)
    db["resp"] = resp
    # vendors: { item: {p price, s stack, n limited, c other costs, r requirements, u usable} }, and
    # the plain item -> vendors list gets every item seen for sale
    vendx = {}
    for npc, e in x["vendx"].items():
        rows = {}
        for it, row in as_dict(e.get("i")).items():
            row = as_dict(row)
            out = {"p": int(row.get("p") or 0), "s": int(row.get("s") or 1)}
            if row.get("n"):
                out["n"] = int(row["n"])
            if row.get("c"):
                out["c"] = [list(c) if isinstance(c, list) else list(as_dict(c).values()) for c in
                            (row["c"] if isinstance(row["c"], list) else list(as_dict(row["c"]).values()))]
            if row.get("r"):
                out["r"] = [str(t) for t in (row["r"] if isinstance(row["r"], list) else list(as_dict(row["r"]).values()))]
            if row.get("u") is False:
                out["u"] = False
            rows[int(it)] = out
            lst = db["vend"].setdefault(int(it), [])
            if isinstance(lst, list) and npc not in lst:
                lst.append(npc)
        if rows:
            vendx[npc] = rows
    db["vendx"] = vendx
    db["oskill"] = x["oskill"]
    db["ctype"] = x["ctype"]
    for it, e in x["itemx"].items():
        if it not in db["item"]:
            db["item"][it] = [e[0], e[1]]
    db["itemx"] = x["itemx"]
    return {"questRewardsFromGame": qfix}


# ------------------------------------------------------------------ Drop Tables
# github.com/valcheffnet/DropTables data/shared.json (CC BY-SA 4.0): loot counts players record on WoW
# Forever (their own shares + Blackthornes Farmer (MIT), EG Link (CC BY 4.0) and Everloot (CC BY-SA 4.0)).
# Its rates replace a base rate after DT_RATE_MIN kills; our own recordings always win over it.
DT_CELLS = 50          # shared.json spots: a 50 x 50 grid per uiMap
DT_SKIN_MIN = 3        # skinned corpses before a skinning chance is kept


def load_droptables(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def merge_droptables(agg, dt):
    """Add Drop Tables' counts to the recordings: loot per kill, kill spots, names and levels."""
    stats = {"mobs": 0, "kills": 0}
    if not dt:
        return stats
    for sid, m in (dt.get("mobs") or {}).items():
        if not str(sid).isdigit():
            continue
        npc = int(sid)
        kills = lootable = opened = 0
        items = {}
        for b in (m.get("buckets") or {}).values():
            kills += int(b.get("kills") or 0)
            lootable += int(b.get("lootable") or 0)
            opened += int(b.get("opened") or 0)
            for it, e in (b.get("items") or {}).items():
                items[int(it)] = items.get(int(it), 0) + int(e.get("drops") or 0)
        if kills > 0 and opened > 0:
            # chance per kill = lootable / kills * drops / opened (Drop Tables' own formula)
            share = min(1.0, lootable / kills) / opened
            a = agg.setdefault("dtloot", {}).setdefault("c:%d" % npc, {"n": 0, "i": {}})
            a["n"] += kills
            for it, d in items.items():
                a["i"][it] = a["i"].get(it, 0) + d * share * kills
            stats["mobs"] += 1
            stats["kills"] += kills
        sp = agg.setdefault("dtsp", {}).setdefault("c:%d" % npc, {})
        for mp, cells in (m.get("spots") or {}).items():
            lst = sp.setdefault(int(mp), [])
            for c, _ in sorted(cells.items(), key=lambda kv: -kv[1]):
                c = int(c)
                x = int(((c // DT_CELLS) + 0.5) / DT_CELLS * 1000)
                y = int(((c % DT_CELLS) + 0.5) / DT_CELLS * 1000)
                if len(lst) >= SPOT_MAX * 2:
                    break
                if not any(abs(lst[j] - x) <= SPOT_NEAR and abs(lst[j + 1] - y) <= SPOT_NEAR for j in range(0, len(lst), 2)):
                    lst += [x, y]
        if not sp:
            del agg["dtsp"]["c:%d" % npc]
    return stats


def droptables_tables(db, dt):
    """Tables only Drop Tables has: skinning (skin), money (gold), and npcs no other source knows."""
    if not dt:
        return
    skin, gold = db.setdefault("skin", {}), db.setdefault("gold", {})
    for sid, m in (dt.get("mobs") or {}).items():
        if not str(sid).isdigit():
            continue
        npc = int(sid)
        if npc not in db["npc"] and m.get("name"):
            db["npc"][npc] = [m["name"], None, m.get("minLevel"), m.get("maxLevel"), 0]
        s = m.get("skins") or {}
        n = int(s.get("skinned") or 0)
        if n >= DT_SKIN_MIN:
            for it, e in (s.get("items") or {}).items():
                lst = skin.setdefault(int(it), [])
                lst.append([npc, int(round(min(1.0, int(e.get("drops") or 0) / n) * 10000))])
                lst.sort(key=lambda p: -p[1])
        kills = lootable = opened = copper = 0
        lo = hi = None
        for b in (m.get("buckets") or {}).values():
            kills += int(b.get("kills") or 0)
            lootable += int(b.get("lootable") or 0)
            opened += int(b.get("opened") or 0)
            mo = b.get("money") or {}
            copper += int(mo.get("copper") or 0)
            if mo.get("min") is not None:
                lo = mo["min"] if lo is None else min(lo, mo["min"])
            if mo.get("max") is not None:
                hi = mo["max"] if hi is None else max(hi, mo["max"])
        if kills > 0 and opened > 0 and copper > 0:
            # average copper per kill, smallest and largest pile, kills counted
            gold[npc] = [int(round(min(1.0, lootable / kills) * copper / opened)), lo, hi, kills]


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
    # loot: Drop Tables first (other players' counts), then our own recordings on top
    field = {"c": "drop", "o": "odrop", "i": "idrop"}
    for key, e in agg.get("dtloot", {}).items():
        kind, sid = who(key)
        f = field.get(kind)
        if not f or e["n"] <= 0:
            continue
        db["seen"].setdefault(kind + str(sid), {it: [int(round(c)), e["n"]] for it, c in e["i"].items()})
        for it, c in e["i"].items():
            ch = int(round(min(1.0, c / e["n"]) * 10000))
            lst = db[f].setdefault(it, [])
            cur = next((p for p in lst if p[0] == sid), None)
            if cur is None:
                if e["n"] >= DT_NEW_MIN or not lst:
                    lst.append([sid, ch])
            elif e["n"] >= DT_RATE_MIN:
                cur[1] = ch
            lst.sort(key=lambda p: -p[1])
    for key, e in agg["loot"].items():
        kind, sid = who(key)
        f = field.get(kind)
        if not f or e["n"] <= 0:
            continue
        db["seen"][kind + str(sid)] = {it: [int(round(c)), e["n"]] for it, c in e["i"].items()}
        for it, c in e["i"].items():
            ch = int(round(min(1.0, c / e["n"]) * 10000))
            lst = db[f].setdefault(it, [])
            cur = next((p for p in lst if p[0] == sid), None)
            if cur is None:
                lst.append([sid, ch])            # recorded in WoW Forever: always kept
            else:
                cur[1] = ch                      # and its chance always replaces the base / Drop Tables one
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
        # a source needs two credits at least (one kill just before some progress is chance), and
        # once an object is a source, creatures with far fewer credits are left out
        top_o = max([c for k, c in srcs.items() if str(k).startswith("o")] or [0])
        keep = [k for k, c in sorted(srcs.items(), key=lambda kv: -kv[1])
                if c >= 2 and not (str(k).startswith("c") and top_o >= 3 * c)]
        if keep:
            db["qsrc"][q] = keep
    db["ptl"] = {k: v for k, v in agg["ptl"].items() if v}
    db["qwk"] = {q: [round(a[0] / a[1]), a[1]] for q, a in agg["qwk"].items() if a[1] > 0}
    # map spots (Drop Tables' kill spots, then ours)
    for key, maps in list(agg.get("dtsp", {}).items()) + list(agg["sp"].items()):
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


def apply_fixes(db, path, recorded_sp=None):
    """fixes.json: hand-checked corrections that win over the sources. Spots recorded in game stay."""
    if not path or not os.path.exists(path):
        return 0
    fx = json.load(open(path, encoding="utf-8"))
    n = 0
    spm = db.setdefault("spm", {})
    for key, maps in (fx.get("spm") or {}).items():
        spm[key] = {int(m): list(p) for m, p in maps.items()}
        for m, pts in ((recorded_sp or {}).get(key[0] + ":" + key[1:]) or {}).items():
            lst = spm[key].setdefault(int(m), [])
            for k in range(0, len(pts) - 1, 2):
                if not any(abs(lst[j] - pts[k]) <= SPOT_NEAR and abs(lst[j + 1] - pts[k + 1]) <= SPOT_NEAR
                           for j in range(0, len(lst) - 1, 2)):
                    lst += [pts[k], pts[k + 1]]
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
    ap.add_argument("--keep", help="folder that keeps every recording for good (recorded/ in the repo)")
    ap.add_argument("--droptables", help="Drop Tables data/shared.json (CC BY-SA 4.0)")
    ap.add_argument("--sources-json", help="JSON list of {name, repo, ref, licence} for meta.sourceList")
    ap.add_argument("--fixes", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fixes.json"),
                    help="hand-checked corrections (default: fixes.json in the repo)")
    a = ap.parse_args()
    with open(a.base, encoding="utf-8") as f:
        base = json.load(f)
    recs = keep_recordings(load_recordings(a.collected), a.keep)
    agg = merge_recordings(recs)
    merge_extra(recs, agg)
    dt = load_droptables(a.droptables)
    dts = merge_droptables(agg, dt)
    db = build(base, agg)
    droptables_tables(db, dt)
    extra = apply_extra(db, agg.get("x"))
    chained = chain_prereqs(db)
    fixed = apply_fixes(db, a.fixes, agg["sp"])
    h = digest(db)
    db["meta"] = {
        "build": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "hash": h[:16],
        "sources": a.source_note,
        "recordings": len(recs),
        "dropTables": dict(dts, built=(dt or {}).get("built"), submissions=(dt or {}).get("submissions")),
        "fixes": fixed,
        "chainPrereqs": chained,
        "recorded": extra,
        "sourceList": json.load(open(a.sources_json)) if a.sources_json and os.path.exists(a.sources_json) else [],
        "counts": {k: len(v) for k, v in db.items() if isinstance(v, dict) and k not in ("loc", "src")},
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(db, f, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
    print("master:", a.out, db["meta"])


if __name__ == "__main__":
    main()
