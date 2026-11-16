"""Plain addon data exports (tools/lua/export.lua ns ...) -> source json for tools/merge.py.

  python tools/import_extra.py legacy work/legacy.json work/src-legacy.json [--locations tools/locations.json]
  python tools/import_extra.py spf    work/spf.json    work/src-spf.json

legacy  LegacyForever (GPL-3.0-or-later, github.com/cjber/legacy-forever): WoW Forever's
        Legacy challenges -> tables `legacy` (completion, feeds, rewards, zones, build),
        `explore` (exploration area outlines per uiMap) and `lcrit` (where each criterion
        happens: uiMap, kind, instance, evidence; from its reviewed tools/locations.json).
spf     Shortest Path Forever (GPL-3.0-or-later, github.com/cjber/shortest-path-forever): the
        travel network -> table `spf` with TaxiNodes, TaxiPaths (with flight times), Docks,
        Routes (boat/zeppelin timetables), Portals, Teleports, Entrances, trainers,
        battlemasters, food/drink vendors, TownAreas, Zones, Walks.
"""
import argparse, json, os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["legacy", "spf"])
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--locations")
    a = ap.parse_args()
    d = json.load(open(a.src, encoding="utf-8"))
    out = {}
    if a.kind == "legacy":
        out["legacy"] = d.get("Data") or {}
        out["explore"] = (d.get("Explore") or {}).get("zones") or {}
        if a.locations and os.path.exists(a.locations):
            out["lcrit"] = json.load(open(a.locations, encoding="utf-8"))
    else:
        out["spf"] = d
    print(a.kind, {k: len(v) for k, v in out.items()})
    os.makedirs(os.path.dirname(a.dst) or ".", exist_ok=True)
    json.dump(out, open(a.dst, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main()
