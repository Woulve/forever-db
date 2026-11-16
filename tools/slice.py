"""Cut a slice of the master database for one addon and write it as Lua.

  python tools/slice.py slices/commandcenter.json dist/forever.json <addon folder>

Spec (slices/<name>.json):
  {
    "global": "ForeverDB",               Lua global the data lands in
    "files": "ForeverDB",                file name prefix (ForeverDB.lua, ForeverDB_2.lua, ...)
    "toc": "ForeverDB.toc",             optional: rewrite the file list + version in this toc
    "tables": ["npc", "drop", ...],      which master tables to include
    "prune": true,                       keep only npcs/objects/quests/items referenced by the other tables
    "fields": {"npc": [0, 1, 2, 3, 4]}   optional: which columns of a row to keep
    "max_rows": {"drop": 40}             optional: keep only the best N sources per item
  }
Flattening done for Lua: drop/odrop/idrop rows [[src, chance], ...] -> {src, chance, src, chance, ...}.
Big tables are written in chunks wrapped in functions (Lua's per-function constant limit),
and split over several files (MAX_FILE bytes each).
"""
import json, os, re, sys

CHUNK = 3000
MAX_FILE = 3_500_000


def lua_str(s):
    s = str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")
    return '"' + s + '"'


def lua(v):
    if v is None:
        return "nil"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, (int,)):
        return str(v)
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else repr(round(v, 4))
    if isinstance(v, str):
        return lua_str(v)
    if isinstance(v, list):
        # trailing nils trimmed; inner nils kept positional
        while v and v[-1] is None:
            v = v[:-1]
        return "{" + ",".join(lua(x) for x in v) + "}"
    if isinstance(v, dict):
        parts = []
        for k in sorted(v, key=lambda k: (0, int(k)) if str(k).lstrip("-").isdigit() else (1, str(k))):
            ks = str(k)
            if ks.lstrip("-").isdigit():
                parts.append("[%s]=%s" % (ks, lua(v[k])))
            elif re.match(r"^[A-Za-z_]\w*$", ks):
                parts.append("%s=%s" % (ks, lua(v[k])))
            else:
                parts.append("[%s]=%s" % (lua_str(ks), lua(v[k])))
        return "{" + ",".join(parts) + "}"
    raise TypeError(type(v))


def referenced(db, tables):
    npcs, objs, quests, items = set(), set(), set(), set()
    for f in ("drop", "odrop", "idrop", "vend", "rew", "start", "world"):
        if f in tables:
            items.update(int(k) for k in db.get(f, {}))
    for f, bucket in (("drop", npcs), ("odrop", objs), ("idrop", items)):
        if f in tables:
            for rows in db.get(f, {}).values():
                bucket.update(r[0] for r in rows)
    if "vend" in tables:
        for rows in db.get("vend", {}).values():
            npcs.update(rows)
    for f in ("rew",):
        if f in tables:
            for rows in db.get(f, {}).values():
                quests.update(rows)
    if "start" in tables:
        quests.update(db.get("start", {}).values())
    if "qx" in tables:
        # questing data: every quest, the creatures / objects / items its objectives need
        quests.update(int(k) for k in db.get("qx", {}))
        quests.update(int(k) for k in db.get("qg", {}))
        for row in db.get("qx", {}).values():
            for col, bucket in ((7, npcs), (8, objs), (9, items)):
                if len(row) > col and row[col]:
                    bucket.update(row[col])
    for f in ("qg", "qe"):
        if f in tables:
            for q, ws in db.get(f, {}).items():
                if int(q) in quests:
                    for w in ws:
                        (npcs if w[0] == "c" else objs).add(int(w[1:]))
    return npcs, objs, quests, items


def make_slice(db, spec):
    tables = spec["tables"]
    out = {}
    keep = None
    caps = spec.get("max_rows", {})
    if caps:
        db = dict(db)
        for t, n in caps.items():
            if t in db:
                db[t] = {k: v[:n] for k, v in db[t].items()}
    if spec.get("prune"):
        npcs, objs, quests, items = referenced(db, tables)
        keep = {"npc": npcs, "obj": objs, "quest": quests, "qg": quests, "qe": quests, "item": items,
                "vp": npcs, "qx": quests, "nfac": npcs}
    for t in tables:
        src = db.get(t, {})
        res = {}
        for k, v in src.items():
            ik = int(k) if str(k).lstrip("-").isdigit() else k
            if keep and t in keep and ik not in keep[t]:
                continue
            if keep and t in ("spw", "spm", "seen"):
                kind, num = str(k)[0], int(str(k)[1:])
                if (kind == "c" and num not in keep["npc"]) or (kind == "o" and num not in keep["obj"]):
                    continue
            if t in ("drop", "odrop", "idrop"):
                cap = spec.get("max_rows", {}).get(t)
                if cap:
                    v = v[:cap]
                v = [x for pair in v for x in pair]
            elif t in ("vend", "rew") and spec.get("max_rows", {}).get(t):
                v = v[:spec["max_rows"][t]]
            cols = spec.get("fields", {}).get(t)
            if cols and isinstance(v, list):
                v = [v[c] if c < len(v) else None for c in cols]
            res[ik] = v
        out[t] = res
    out["meta"] = dict(db.get("meta", {}))
    return out


def write_lua(sl, spec, folder):
    g = spec["global"]
    prefix = spec.get("files", "Data")
    files, cur, size = [], [], 0

    def flush():
        nonlocal cur, size
        if cur:
            files.append(cur)
        cur, size = [], 0

    head = ["-- generated by forever-db (tools/slice.py) - do not edit",
            "%s = %s or {}" % (g, g), "local D = %s" % g]
    meta = sl.pop("meta", {})
    cur.append("D.meta = %s" % lua(meta)); size += 200
    for t, rows in sl.items():
        keys = sorted(rows, key=lambda k: (0, k) if isinstance(k, int) else (1, str(k)))
        cur.append("D.%s = D.%s or {}" % (t, t))
        for n in range(0, max(1, len(keys)), CHUNK):
            part = keys[n:n + CHUNK]
            if not part:
                continue
            body = [";(function() local t = D.%s" % t]
            for k in part:
                ks = "[%d]" % k if isinstance(k, int) else "[%s]" % lua_str(k)
                body.append("t%s=%s" % (ks, lua(rows[k])))
            body.append("end)()")
            text = "\n".join(body)
            if size + len(text) > MAX_FILE and size > 0:
                flush()
                cur.append("D.%s = D.%s or {}" % (t, t))
            cur.append(text); size += len(text)
    flush()
    names = []
    os.makedirs(folder, exist_ok=True)
    for i, chunk in enumerate(files):
        name = "%s.lua" % prefix if i == 0 else "%s_%d.lua" % (prefix, i + 1)
        with open(os.path.join(folder, name), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(head + chunk) + "\n")
        names.append(name)
    # remove stale extra files
    for fn in os.listdir(folder):
        if re.match(re.escape(prefix) + r"_\d+\.lua$", fn) and fn not in names:
            os.remove(os.path.join(folder, fn))
    if spec.get("toc"):
        p = os.path.join(folder, spec["toc"])
        with open(p, encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if l.startswith("##") or not l.strip()]
        lines = [l for l in lines if l.strip()]
        lines = [("## Version: %s" % meta.get("build", "0")) if l.startswith("## Version:") else l for l in lines]
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n\n" + "\n".join(names) + "\n")
    return names


def main():
    spec_path, master, folder = sys.argv[1:4]
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    with open(master, encoding="utf-8") as f:
        db = json.load(f)
    sl = make_slice(db, spec)
    counts = {k: len(v) for k, v in sl.items() if isinstance(v, dict) and k != "meta"}
    names = write_lua(sl, spec, folder)
    total = sum(os.path.getsize(os.path.join(folder, n)) for n in names)
    print("slice", spec_path, "->", folder, names, "%.1f MB" % (total / 1e6), counts)


if __name__ == "__main__":
    main()
