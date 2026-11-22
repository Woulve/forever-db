"""Zone and sub-zone borders from WoW Forever's own terrain -> source json for tools/merge.py.

Outdoors, the game decides which zone / sub-zone you're in from the map chunk you stand on: every ADT
tile has 16 x 16 chunks (MCNK, 33 1/3 yards square) and each one carries an AreaTable ID (at 0x34 of its
header). This reads every outdoor continent's WDT (which tiles exist, MAID: their root ADT file IDs) and
each root ADT, builds the continent's 1024 x 1024 chunk grid of area IDs, and turns it into borders:

  zbord[zone areaID]    = {"c": continent mapID, "ui": uiMapID (0: none), "n": chunks,
                           "w": [[x, y, x, y, ...] loop, ...]   world yards, outlines + holes,
                           "m": [[x, y, ...], ...]              the same on the zone's own map, 0..1000}
  abord[sub-zone areaID] = the same for every other area (towns, camps, caves' outdoor ground ...)
  agrid[continent]       = {"o": 17066.67, "c": 33.333, "z": {row: "zoneID*count,zoneID*count,..."}}
                           which zone each chunk belongs to (rows from the top, runs from col 0; 0 = none):
                           world X = o - (row + 0.5) * c, Y = o - (col + 0.5) * c. A point-in-zone lookup.

Zones are the top of AreaTable's ParentAreaID chain. Loops are traced round the chunks' edges (the
inside on the left) and simplified (Douglas-Peucker, SIMPLIFY chunks); loops of fewer than SMALL chunks
are left out. The way OpenMap (MIT, github.com/openmap-world/openmap, tools/map-data/explore.py) reads
the terrain was the model for this.

Files come from wago.tools by file ID for the client build (kept in <cache>), or from --files (a folder
of <fileID>.bin, for the tests). Needs the client's AreaTable, UiMap, UiMapAssignment and Map CSVs.

  python tools/import_terrain.py <csv folder> <cache dir> <out.json> [--files DIR] [--build B] [--maps 0,1]
"""
import argparse, csv, glob, json, os, re, struct, sys, time, urllib.request

O = 32 * 1600 / 3          # yards from a continent's corner to its middle
CHUNK = 1600 / 3 / 16      # a map chunk's side, yards
N = 1024                   # chunks along a continent
SIMPLIFY = 0.75            # chunks an outline may stray from the chunks' edges
SMALL = 3                  # chunks a loop must enclose to be kept


def table(folder, name):
    files = sorted(f for f in glob.glob(os.path.join(folder, name + ".*.csv")) if re.match(r".*[/\\]" + re.escape(name) + r"\.\d", f))
    if not files:
        p = os.path.join(folder, name + ".csv")
        files = [p] if os.path.exists(p) else []
    if not files:
        return [], None
    m = re.search(r"\.(\d+\.\d+\.\d+\.\d+)\.csv$", files[-1])
    with open(files[-1], encoding="utf-8-sig") as f:
        return list(csv.DictReader(f)), m.group(1) if m else None


def chunks(data):
    out, i = [], 0
    while i + 8 <= len(data):
        tag = data[i:i + 4][::-1].decode("latin1")
        size = struct.unpack_from("<I", data, i + 4)[0]
        out.append((tag, data[i + 8:i + 8 + size]))
        i += 8 + size
    return out


class Files:
    def __init__(self, cache, build, local=None):
        self.cache, self.build, self.local, self.fetched = cache, build, local, 0
        os.makedirs(cache, exist_ok=True)

    def get(self, fid):
        if not fid:
            return None
        if self.local:
            p = os.path.join(self.local, "%d.bin" % fid)
            return open(p, "rb").read() if os.path.exists(p) else None
        p = os.path.join(self.cache, "%d.bin" % fid)
        if not os.path.exists(p):
            url = "https://wago.tools/api/casc/%d?download&version=%s" % (fid, self.build)
            for attempt in range(4):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "forever-db/1 (github.com/foreverfraddons)"})
                    data = urllib.request.urlopen(req, timeout=120).read()
                    break
                except Exception as e:                      # (a busy server: wait and try again)
                    if attempt == 3:
                        print("terrain: file %d not fetched: %s" % (fid, e), file=sys.stderr)
                        return None
                    time.sleep(2 + attempt * 3)
            with open(p, "wb") as f:
                f.write(data)
            self.fetched += 1
            time.sleep(0.05)
        data = open(p, "rb").read()
        self.last = p
        return data if len(data) > 100 else None            # (a missing file answers with an empty or tiny body)

    def forget(self):
        """drop the file just read (only the per-continent grids are kept)"""
        if not self.local and getattr(self, "last", None) and os.path.exists(self.last):
            os.remove(self.last)


def grid(files, wdt_fid, keep=None):
    """the continent's chunks' area IDs: g[row][col], row along -X, col along -Y. Kept in <keep> (one small
    JSON per continent and build) so the 1-2 GB of terrain files are only fetched once per build."""
    if keep and os.path.exists(keep):
        with open(keep) as fi:
            k = json.load(fi)
        g = [[0] * N for _ in range(N)]
        for r, line in k["g"].items():
            c = 0
            for run in line.split(","):
                v, n = run.split("*")
                v, n = int(v), int(n)
                if v:
                    g[int(r)][c:c + n] = [v] * n
                c += n
        return g, k["tiles"]
    wdt = files.get(wdt_fid)
    if not wdt:
        return None
    w = dict(chunks(wdt))
    if "MAIN" not in w or "MAID" not in w:
        return None
    g = [[0] * N for _ in range(N)]
    tiles = missing = 0
    for n in range(4096):
        if not struct.unpack_from("<I", w["MAIN"], n * 8)[0] & 1:
            continue
        data = files.get(struct.unpack_from("<I", w["MAID"], n * 32)[0])      # (the tile's root file)
        if not data:
            missing += 1
            continue
        tiles += 1
        ty, tx = divmod(n, 64)
        for tag, d in chunks(data):
            if tag != "MCNK" or len(d) < 0x38:
                continue
            ix, iy = struct.unpack_from("<2I", d, 4)
            if ix < 16 and iy < 16:
                g[ty * 16 + iy][tx * 16 + ix] = struct.unpack_from("<I", d, 0x34)[0]
        files.forget()
    if missing:
        print("terrain: %d tiles not read (the grid isn't kept: the next build tries again)" % missing, flush=True)
    if keep and not missing:
        rows = {}
        for r in range(N):
            if any(g[r]):
                runs, cur, cnt = [], g[r][0], 0
                for v in g[r]:
                    if v == cur:
                        cnt += 1
                    else:
                        runs.append("%d*%d" % (cur, cnt))
                        cur, cnt = v, 1
                runs.append("%d*%d" % (cur, cnt))
                rows[r] = ",".join(runs)
        with open(keep, "w") as fo:
            json.dump({"tiles": tiles, "g": rows}, fo, separators=(",", ":"))
    return g, tiles


def loops(cells):
    """the edges of a set of (row, col) cells, joined into closed loops of grid corners (inside on the left)"""
    nxt = {}
    def add(a, b):
        nxt.setdefault(a, []).append(b)
    for r, c in cells:
        if (r - 1, c) not in cells: add((r, c + 1), (r, c))              # top: right to left
        if (r + 1, c) not in cells: add((r + 1, c), (r + 1, c + 1))      # bottom: left to right
        if (r, c - 1) not in cells: add((r, c), (r + 1, c))              # left: down
        if (r, c + 1) not in cells: add((r + 1, c + 1), (r, c + 1))      # right: up
    out = []
    while nxt:
        start = next(iter(nxt))
        loop, at = [start], start
        while True:
            ways = nxt[at]
            to = ways.pop()
            if not ways:
                del nxt[at]
            if to == start:
                break
            loop.append(to)
            at = to
        out.append(loop)
    return out


def area2(loop):
    s = 0
    for i in range(len(loop)):
        (r1, c1), (r2, c2) = loop[i], loop[(i + 1) % len(loop)]
        s += r1 * c2 - r2 * c1
    return abs(s) / 2


def thin(pts, tol):
    """Douglas-Peucker on an open run of points (iterative)"""
    if len(pts) < 3:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = pts[a], pts[b]
        L = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        i, dm = 0, -1.0
        for k in range(a + 1, b):
            x, y = pts[k]
            d = abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1) / L if L else ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
            if d > dm:
                i, dm = k, d
        if dm > tol:
            keep[i] = True
            stack += [(a, i), (i, b)]
    return [p for p, k in zip(pts, keep) if k]


def thin_loop(loop, tol):
    far = max(range(len(loop)), key=lambda k: (loop[k][0] - loop[0][0]) ** 2 + (loop[k][1] - loop[0][1]) ** 2)
    a = thin(loop[:far + 1], tol)
    b = thin(loop[far:] + [loop[0]], tol)
    return a[:-1] + b[:-1]


def straight(lp):
    """a loop without the points that lie on a straight line between their neighbours"""
    out = list(lp)
    changed = True
    while changed and len(out) > 3:
        changed = False
        for i in range(len(out)):
            (r0, c0), (r1, c1), (r2, c2) = out[i - 1], out[i], out[(i + 1) % len(out)]
            if (r1 - r0) * (c2 - c1) == (r2 - r1) * (c1 - c0):
                del out[i]
                changed = True
                break
    return out


def f(r, k):
    try:
        return float(r[k])
    except (KeyError, TypeError, ValueError):
        return 0.0


def to_map(row, x, y):
    """world yards -> the uiMap's 0..1 (as C_Map.GetMapPosFromWorldPos does), from its UiMapAssignment row"""
    u = f(row, "UiMin_0") + (f(row, "Region_4") - y) / ((f(row, "Region_4") - f(row, "Region_1")) or 1) * (f(row, "UiMax_0") - f(row, "UiMin_0"))
    v = f(row, "UiMin_1") + (f(row, "Region_3") - x) / ((f(row, "Region_3") - f(row, "Region_0")) or 1) * (f(row, "UiMax_1") - f(row, "UiMin_1"))
    return u, v


def outline(cells, assign):
    """{"w": world loops, "m": map loops} for a set of chunks"""
    w, m = [], []
    for lp in loops(cells):
        if area2(lp) < SMALL:
            continue
        lp = straight(thin_loop(lp, SIMPLIFY))
        if len(lp) < 3:
            continue
        wl, ml = [], []
        for r, c in lp:
            x, y = O - r * CHUNK, O - c * CHUNK
            wl += [int(round(x)), int(round(y))]
            if assign:
                u, v = to_map(assign, x, y)
                ml += [int(round(u * 1000)), int(round(v * 1000))]
        w.append(wl)
        if assign:
            m.append(ml)
    return w, m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("cache")
    ap.add_argument("out")
    ap.add_argument("--files", help="a folder of <fileID>.bin instead of wago.tools (tests)")
    ap.add_argument("--build")
    ap.add_argument("--maps", help="only these continents (mapIDs, comma separated)")
    a = ap.parse_args()

    areas, build = table(a.csv, "AreaTable")
    uimaps = {r["ID"]: r for r in table(a.csv, "UiMap")[0]}
    assigns = table(a.csv, "UiMapAssignment")[0]
    maps = table(a.csv, "Map")[0]
    build = a.build or build
    if not areas or not maps:
        sys.exit("terrain: AreaTable and Map CSVs are needed in %s" % a.csv)
    parent = {int(r["ID"]): int(r.get("ParentAreaID") or 0) for r in areas}

    zcache = {}
    def zone_of(aid):
        if aid in zcache:
            return zcache[aid]
        a0, seen = aid, 0
        while parent.get(aid) and seen < 10:
            aid, seen = parent[aid], seen + 1
        zcache[a0] = aid
        return aid

    # the uiMap that shows an area: an assignment for exactly that area, on its continent, not a WMO's floor
    ui_of = {}
    for r in assigns:
        if r.get("WMOGroupID") not in ("-1", "0") or r.get("AreaID") in (None, "", "0"):
            continue
        key = (int(r["AreaID"]), int(r["MapID"]))
        typ = int((uimaps.get(r["UiMapID"]) or {}).get("Type") or 9)
        best = ui_of.get(key)
        if best is None or (typ, int(r.get("OrderIndex") or 0)) < best[0]:
            ui_of[key] = ((typ, int(r.get("OrderIndex") or 0)), r)

    want = {int(x) for x in a.maps.split(",")} if a.maps else None
    files = Files(a.cache, build, a.files)
    out = {"zbord": {}, "abord": {}, "agrid": {}, "terrainBuild": build}
    for mrow in sorted(maps, key=lambda r: int(r["ID"])):
        mid = int(mrow["ID"])
        if want is not None and mid not in want:
            continue
        if want is None and (mrow.get("InstanceType") not in ("0", None) or not int(mrow.get("WdtFileDataID") or 0)):
            continue
        if want is None and not any(int(r.get("ContinentID") or -1) == mid for r in areas):
            continue
        got = grid(files, int(mrow.get("WdtFileDataID") or 0),
                   None if a.files else os.path.join(a.cache, "grid-%d-%s.json" % (mid, build)))
        if not got:
            continue
        g, tiles = got
        by_area, by_zone = {}, {}
        runs = {}
        for r in range(N):
            row = g[r]
            line, cur, cnt = [], None, 0
            for c in range(N):
                aid = row[c]
                z = zone_of(aid) if aid else 0
                if aid:
                    by_area.setdefault(aid, set()).add((r, c))
                    by_zone.setdefault(z, set()).add((r, c))
                if z == cur:
                    cnt += 1
                else:
                    if cur is not None:
                        line.append("%d*%d" % (cur, cnt))
                    cur, cnt = z, 1
            if cur != 0 or len(line):
                line.append("%d*%d" % (cur, cnt))
                runs[r] = ",".join(line)
        if not by_zone:
            continue
        out["agrid"][mid] = {"o": round(O, 2), "c": round(CHUNK, 3), "z": runs}
        for z, cells in by_zone.items():
            asg = (ui_of.get((z, mid)) or (None, None))[1]
            w, m = outline(cells, asg)
            if w:
                out["zbord"][z] = {"c": mid, "ui": int(asg["UiMapID"]) if asg else 0, "n": len(cells), "w": w, "m": m}
        for aid, cells in by_area.items():
            if aid == zone_of(aid):
                continue
            z = zone_of(aid)
            asg = (ui_of.get((z, mid)) or (None, None))[1]          # (sub-zones on their zone's map)
            w, m = outline(cells, asg)
            if w:
                out["abord"][aid] = {"c": mid, "z": z, "ui": int(asg["UiMapID"]) if asg else 0, "n": len(cells), "w": w, "m": m}
        print("terrain: map %d (%s): %d tiles, %d zones, %d areas" % (mid, mrow.get("MapName_lang") or "", tiles, len(by_zone), len(by_area)), flush=True)
    print("terrain: %d zone borders, %d sub-zone borders, %d continents, %d files fetched (build %s)" % (
        len(out["zbord"]), len(out["abord"]), len(out["agrid"]), files.fetched, build))
    with open(a.out, "w", encoding="utf-8") as fo:
        json.dump(out, fo, separators=(",", ":"))


if __name__ == "__main__":
    main()
