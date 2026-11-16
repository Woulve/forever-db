"""Import a MaNGOS-family world database dump (cMaNGOS classic-db, VMaNGOS, ...) into the
source format (one JSON per source; tools/merge.py combines them).

VMaNGOS keeps one row per patch (column `patch`) or a patch range (`patch_min`/`patch_max`);
only rows valid in the final patch (1.12) are used.

  python tools/import_base.py <folder with .sql/.sql.gz/.zip dumps> data/base.json

Master format (JSON keys are strings; ids are numbers in the values):
  npc   {id: [name, subname, minLv, maxLv, rank]}
  obj   {id: [name]}
  item  {id: [name, quality, reqLevel]}
  quest {id: [title, level, minLevel]}
  qg    {questId: ["c123", "o45"]}       quest givers
  qe    {questId: ["c123"]}              quest enders
  drop  {itemId: [[npc, chance], ...]}   chance per 10000
  odrop {itemId: [[obj, chance], ...]}
  idrop {itemId: [[containerItem, chance], ...]}
  vend  {itemId: [npc, ...]}
  rew   {itemId: [questId, ...]}
  start {itemId: questId}
  world {itemId: minLevel}               world drops (shared loot tables)
  spw   {"c123": [[map, x, y, x, y, ...], ...]}   world coordinates per map
"""
import json, sys, os
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from sqldump import read_tables, Table, find_dumps

TABLES = ["creature_template", "creature", "gameobject_template", "gameobject", "item_template",
          "creature_loot_template", "gameobject_loot_template", "item_loot_template", "reference_loot_template",
          "npc_vendor", "npc_vendor_template", "quest_template", "creature_questrelation",
          "creature_involvedrelation", "gameobject_questrelation", "gameobject_involvedrelation",
          "quest_relations"]

WORLD_DROP_USERS = 40     # a shared loot table used by this many creatures = world drop
SPAWN_CAP = 120           # spawn points kept per creature/object
MIN_CHANCE = 1            # per 10000; smaller drops are dropped


FINAL_PATCH = 10          # VMaNGOS patch index of 1.12


def final_patch(raw):
    """Keep only rows valid in the last patch: newest `patch` row per entry, patch_max >= 1.12."""
    if not raw or not raw.get("cols"):
        return raw
    cols = raw["cols"]
    rows = raw["rows"]
    if "patch_max" in cols:
        k = cols.index("patch_max")
        rows = [r for r in rows if r[k] is None or r[k] >= FINAL_PATCH]
    if "patch" in cols and "entry" in cols:
        kp, ke = cols.index("patch"), cols.index("entry")
        best = {}
        for r in rows:
            p = r[kp] or 0
            if p <= FINAL_PATCH and (r[ke] not in best or p >= (best[r[ke]][kp] or 0)):
                best[r[ke]] = r
        rows = list(best.values())
    return {"cols": cols, "rows": rows}


def build(tables):
    T = {k: Table(final_patch(tables.get(k))) for k in TABLES}
    out = {k: {} for k in ["npc", "obj", "item", "quest", "qg", "qe", "drop", "odrop", "idrop", "vend", "rew", "start", "world", "spw", "qrw"]}

    # --- creatures
    ct = T["creature_template"]
    c_entry, c_name, c_sub = ct.col("entry"), ct.col("name"), ct.col("subname")
    c_min, c_max, c_rank = ct.col("minlevel", "level_min"), ct.col("maxlevel", "level_max"), ct.col("rank")
    c_loot, c_vtpl = ct.col("lootid", "loot_id"), ct.col("vendortemplateid", "vendor_id")
    npc_loot, npc_vtpl, npc_level = {}, {}, {}
    for r in ct:
        e = r[c_entry]
        out["npc"][e] = [r[c_name], r[c_sub] or None if c_sub is not None else None,
                         r[c_min] if c_min is not None else None, r[c_max] if c_max is not None else None,
                         r[c_rank] if c_rank is not None else 0]
        npc_level[e] = r[c_min] if c_min is not None else 0
        if c_loot is not None and r[c_loot]:
            npc_loot[e] = r[c_loot]
        elif c_loot is None:
            npc_loot[e] = e
        if c_vtpl is not None and r[c_vtpl]:
            npc_vtpl[e] = r[c_vtpl]

    # --- objects
    gt = T["gameobject_template"]
    g_entry, g_name, g_type, g_d1 = gt.col("entry"), gt.col("name"), gt.col("type"), gt.col("data1")
    obj_loot = {}
    for r in gt:
        out["obj"][r[g_entry]] = [r[g_name]]
        if g_type is not None and r[g_type] in (3, 25) and g_d1 is not None and r[g_d1]:   # chest / fishing hole
            obj_loot[r[g_entry]] = r[g_d1]

    # --- items
    it = T["item_template"]
    i_entry, i_name, i_q, i_req, i_sq = it.col("entry"), it.col("name"), it.col("quality"), it.col("requiredlevel", "required_level"), it.col("startquest", "start_quest")
    for r in it:
        out["item"][r[i_entry]] = [r[i_name], r[i_q] if i_q is not None else None, r[i_req] if i_req is not None else None]
        if i_sq is not None and r[i_sq]:
            out["start"][r[i_entry]] = r[i_sq]

    # --- loot tables
    def loot_map(t):
        m = defaultdict(list)
        e, item, ch, grp, mc = t.col("entry"), t.col("item"), t.col("chanceorquestchance", "chance"), t.col("groupid"), t.col("mincountorref", "mincount")
        ref = t.col("reference")
        for r in t:
            m[r[e]].append((r[item], float(r[ch] or 0), r[grp] or 0 if grp is not None else 0,
                            (r[mc] if mc is not None else 1), (r[ref] if ref is not None else 0)))
        return m

    refs = loot_map(T["reference_loot_template"])
    # how many creatures use each reference table (directly)
    ref_users = defaultdict(set)
    cl = loot_map(T["creature_loot_template"])
    for npc, lid in npc_loot.items():
        for (_, _, _, mc, ref) in cl.get(lid, []):
            rid = -mc if mc and mc < 0 else ref
            if rid:
                ref_users[rid].add(npc)
    world_refs = {rid for rid, users in ref_users.items() if len(users) >= WORLD_DROP_USERS}

    def expand(rows, mult, depth, sink, world_level=None):
        if depth > 6:
            return
        # equal-share chances inside groups
        groups = defaultdict(lambda: [0.0, 0])
        for (_, ch, grp, mc, ref) in rows:
            if grp and ch == 0 and not (mc and mc < 0):
                groups[grp][1] += 1
            elif grp:
                groups[grp][0] += abs(ch)
        for (item, ch, grp, mc, ref) in rows:
            rid = -mc if mc and mc < 0 else ref
            c = abs(ch)
            if grp and c == 0:
                left, n = groups[grp]
                c = max(0.0, 100.0 - left) / max(1, n)
            if rid:
                if rid in world_refs and world_level is not None:
                    for (it2, *_r) in refs.get(rid, []):
                        if it2:
                            old = out["world"].get(it2)
                            out["world"][it2] = world_level if old is None else min(old, world_level)
                    continue
                expand(refs.get(rid, []), mult * (c or 100.0) / 100.0, depth + 1, sink, world_level)
            elif item:
                sink[item] = sink.get(item, 0.0) + mult * c

    def add_drops(field, src, rows, world_level=None):
        sink = {}
        expand(rows, 1.0, 0, sink, world_level)
        for item, c in sink.items():
            ch = int(round(min(100.0, c) * 100))
            if ch >= MIN_CHANCE:
                out[field].setdefault(item, []).append([src, ch])

    for npc, lid in npc_loot.items():
        if lid in cl:
            add_drops("drop", npc, cl[lid], npc_level.get(npc) or 0)
    gl = loot_map(T["gameobject_loot_template"])
    for obj, lid in obj_loot.items():
        if lid in gl:
            add_drops("odrop", obj, gl[lid])
    il = loot_map(T["item_loot_template"])
    for item, rows in il.items():
        add_drops("idrop", item, rows)
    for f in ("drop", "odrop", "idrop"):
        for item in out[f]:
            out[f][item].sort(key=lambda p: -p[1])

    # --- vendors
    def vend(t, owner_map=None):
        e, item = t.col("entry"), t.col("item")
        for r in t:
            owners = owner_map.get(r[e], []) if owner_map is not None else [r[e]]
            for npc in owners:
                lst = out["vend"].setdefault(r[item], [])
                if npc not in lst:
                    lst.append(npc)
    vend(T["npc_vendor"])
    tpl_users = defaultdict(list)
    for npc, tpl in npc_vtpl.items():
        tpl_users[tpl].append(npc)
    vend(T["npc_vendor_template"], tpl_users)

    # --- quests
    qt = T["quest_template"]
    q_e, q_t, q_lv, q_min = qt.col("entry"), qt.col("title"), qt.col("questlevel"), qt.col("minlevel")
    rew_cols = [qt.col("rewchoiceitemid%d" % k) for k in range(1, 7)] + [qt.col("rewitemid%d" % k) for k in range(1, 5)]
    rew_cols = [c for c in rew_cols if c is not None]
    # rewards: money, full XP (classic formula from RewMoneyMaxLevel), choice items, fixed items
    q_money, q_maxmoney = qt.col("reworreqmoney"), qt.col("rewmoneymaxlevel")
    ch_cols = [(qt.col("rewchoiceitemid%d" % k), qt.col("rewchoiceitemcount%d" % k)) for k in range(1, 7)]
    fx_cols = [(qt.col("rewitemid%d" % k), qt.col("rewitemcount%d" % k)) for k in range(1, 5)]

    def full_xp(qlvl, maxmoney):
        """XP at full value (no grey penalty), cMaNGOS classic Quest::XPValue."""
        if not maxmoney:
            return 0
        qlvl = qlvl or 1          # quests up to level 60 give RewMoneyMaxLevel / 0.6 (higher levels scale down)
        div = 6.0 if qlvl >= 65 else {64: 4.8, 63: 3.6, 62: 2.4, 61: 1.2}.get(qlvl, 0.6)
        return int(round(maxmoney / div))

    for r in qt:
        out["quest"][r[q_e]] = [r[q_t], r[q_lv] if q_lv is not None else None, r[q_min] if q_min is not None else None]
        money = r[q_money] if q_money is not None else 0
        maxm = r[q_maxmoney] if q_maxmoney is not None else 0
        ch = [r[a] for a, _ in ch_cols if a is not None and r[a]]
        fixed = [r[a] for a, _ in fx_cols if a is not None and r[a]]
        xp = full_xp(r[q_lv] if q_lv is not None else None, maxm)
        if money > 0 or xp or ch or fixed:
            out["qrw"][r[q_e]] = [max(0, money or 0), xp, ch or None, fixed or None]
        for c in rew_cols:
            if r[c]:
                lst = out["rew"].setdefault(r[c], [])
                if r[q_e] not in lst:
                    lst.append(r[q_e])

    def rel(t, field, kind):
        a, q = t.col("id", "entry"), t.col("quest")
        for r in t:
            w = "%s%d" % (kind, r[a])
            lst = out[field].setdefault(r[q], [])
            if w not in lst:
                lst.append(w)
    rel(T["creature_questrelation"], "qg", "c")
    rel(T["gameobject_questrelation"], "qg", "o")
    rel(T["creature_involvedrelation"], "qe", "c")
    rel(T["gameobject_involvedrelation"], "qe", "o")
    qr = T["quest_relations"]     # newer cMaNGOS: actor 0/1 creature/object, role 0 start / 1 end
    if len(qr):
        a, e, q, role = qr.col("actor"), qr.col("entry"), qr.col("quest"), qr.col("role")
        for r in qr:
            w = ("c" if r[a] == 0 else "o") + str(r[e])
            lst = out["qg" if r[role] == 0 else "qe"].setdefault(r[q], [])
            if w not in lst:
                lst.append(w)

    # --- spawns
    def spawns(t, kind):
        m, x, y = t.col("map"), t.col("position_x"), t.col("position_y")
        ids = [c for c in (t.col("id"), t.col("id2"), t.col("id3"), t.col("id4"), t.col("id5")) if c is not None]
        grouped = defaultdict(lambda: defaultdict(list))
        for r in t:
            for i in ids:                    # VMaNGOS: a spawn point can hold one of several creatures
                if r[i]:
                    grouped[r[i]][r[m]].append((int(round(r[x])), int(round(r[y]))))
        for ent, maps in grouped.items():
            res, total = [], 0
            for mp, pts in sorted(maps.items(), key=lambda kv: -len(kv[1])):
                flat = [mp]
                for (px, py) in pts:
                    if total >= SPAWN_CAP:
                        break
                    flat += [px, py]
                    total += 1
                if len(flat) > 1:
                    res.append(flat)
            if res:
                out["spw"]["%s%d" % (kind, ent)] = res
    spawns(T["creature"], "c")
    spawns(T["gameobject"], "o")
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    dumps = find_dumps(src)
    if not dumps:
        sys.exit("no .sql dumps found in " + src)
    tables = read_tables(dumps, TABLES)
    print("tables:", {k: len(v["rows"]) for k, v in tables.items()})
    out = build(tables)
    print("built:", {k: len(v) for k, v in out.items()})
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main()
