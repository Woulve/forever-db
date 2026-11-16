# forever-db

A World of Warcraft: Forever database that rebuilds itself and feeds any number of addons.

**Sources** (a "hive": every source adds what the others are missing, and they are cross-checked)

| Source | What it brings | Licence |
|---|---|---|
| [QuestieDB](https://github.com/Questie/QuestieDB) (Forever flavor + its Forever corrections) | The only open data with **WoW Forever** content: Forever-only quests, NPCs, items and objects, new zones (Zephras Isle, Riverglades, Mount Hyjal...), Forever map positions, links from player traces | GPL-3.0 (see LICENSE-DATA.txt) |
| [VMaNGOS](https://github.com/vmangos/core) nightly dump | Very accurate 1.12 drop rates, vendors, quests, spawns | GPL-2.0-or-later |
| [cMaNGOS classic-db](https://github.com/cmangos/classic-db) | Same kinds of data, independently maintained | GPL-3.0 |
| [pfQuest](https://github.com/shagu/pfQuest) | Drop rates, map positions, names in 9 languages | MIT |
| Command Center recordings (`CommandCenterCollect`) | What players actually see in Forever; replaces a drop rate once something was looted 20+ times | - |

Left out on purpose: MaNGOS Zero (CC BY-NC-SA, not compatible with GPL or CurseForge rewards).
Wowhead is **not** scraped (their terms forbid it). Note: QuestieDB's *generated delta-base*
was built by the Questie team from Wowhead's Forever pages; set the repository variable
`QUESTIE_GENERATED` to `off` to leave that part out (traces and hand-written fixes stay).

**How sources are combined** (`tools/merge.py`, report in `REPORT.md` and the release):
- Every entry any source has is kept.
- Names, levels, ranks, quality: Forever data wins any field it has; otherwise the value most
  sources agree on (ties: VMaNGOS > cMaNGOS > pfQuest).
- Quest givers/enders, vendors, rewards: union of all sources.
- Drop rates: median of the sources that give one; `0` = known to drop there, rate unknown.
- Map positions: world coordinates from the server databases, Forever map positions from
  QuestieDB/pfQuest (Classic positions moved onto Forever's redrawn maps with QuestieDB's
  conversion factors).
- The report lists, per source, how many entries it has and how many only it has, plus every
  field where sources disagree, with examples.

## How it updates

1. Twice a day (07:17 and 19:17 UTC), and whenever new recordings arrive, `Build database`:
   - fetches the newest version of **every** source (QuestieDB, VMaNGOS, cMaNGOS, pfQuest);
   - re-imports only the sources that changed (cached by their version);
   - merges and cross-checks them (`dist/report.md`), then adds every recording;
   - and, only when the data's hash changed (or when run by hand with *force*):
     - rebuilds the **ForeverDB** addon in `ForeverDB/`;
     - commits it with `REPORT.md`, tags it `vYYYY.MM.DD.N`;
     - uploads it to CurseForge (project 1807282);
     - refreshes the `latest` GitHub release (full `forever.json.gz` with translations, the report, slices).
2. Your PC's scheduled task pushes new recordings to the addon repo (`collected/`), which pings this repo.
3. Repos listed in `DB_CONSUMERS` get a `db-updated` ping.

The **ForeverDB** addon is published on its own. Addons that use it list it as a required dependency on CurseForge, and the CurseForge app installs it for players. It is LoadOnDemand: an addon calls `C_AddOns.LoadAddOn("ForeverDB")`, then reads the global `ForeverDB`. Command Center does this.

## Layout

```
tools/import_base.py   MaNGOS-family SQL dump (cMaNGOS, VMaNGOS) -> source json
tools/lua/export.lua   loads pfQuest / QuestieDB Lua data (+ QuestieDB's Forever corrections) -> json
tools/import_addons.py pfQuest / QuestieDB json -> source json (Forever map positions)
tools/merge.py         all source jsons -> base.json + cross-check report
tools/build.py         base + recordings -> master forever.json (+ meta.hash)
tools/slice.py         master -> Lua data files for one addon (spec in slices/)
tools/sqldump.py       dump reader (no MySQL needed)
tools/luatable.py      SavedVariables reader
slices/<name>.json     what each addon gets; slices/<name>.toc = its data addon's toc
tests/run_tests.py     end-to-end test on a tiny sample
ForeverDB/             the shared data addon (generated - do not edit; uploaded to CurseForge)
.pkgmeta               CurseForge packaging for ForeverDB/
```

## Using it in another addon

**Easiest:** use the shared **ForeverDB** addon.
1. Add it as a required dependency in your `.pkgmeta` (`required-dependencies`).
2. Load it when you need it: `C_AddOns.LoadAddOn("ForeverDB")`.
3. Read the global `ForeverDB` (tables below). `ForeverDB.meta` has the build date, hash and counts.

**Own slice** (other tables or limits, shipped inside your addon):
1. Add `slices/myaddon.json`, for example:
   ```json
   {"global": "MyAddon_DB", "files": "Data", "target": "MyAddon_Data", "toc": "MyAddon_Data.toc",
    "tables": ["npc", "quest", "qg", "spw", "spm"], "prune": false}
   ```
   Optionally add `slices/myaddon.toc` if the slice should be its own LoadOnDemand addon.
2. Every slice is attached to the `latest` release as `myaddon.zip`.
3. Add your repo to `DB_CONSUMERS` and download that asset on the `db-updated` ping.

Tables:

| Table | Contents |
|---|---|
| `npc` | name, sub, minLv, maxLv, rank |
| `obj` | name |
| `item` | name, quality, reqLevel |
| `quest` | title, level, minLevel |
| `qg` / `qe` | quest givers / enders ("c123" creature, "o45" object) |
| `drop` / `odrop` / `idrop` | per item: {source, chance per 10000, ...} (0 = rate unknown) |
| `vend` | per item: vendor ids |
| `vp` | prices seen |
| `rew` | quest rewards |
| `start` | item starts a quest |
| `world` | world drops (minimum level) |
| `spw` | spawn world coordinates per map. Convert in game with `C_Map.GetMapPosFromWorldPos` |
| `spm` | map spots (uiMap, 0-1000): Forever positions for things without world coordinates + recordings |

The master `forever.json` (release asset) also has `spz` (all Forever map positions), `loc`
(names in 9 languages) and `src` (which sources have each entry, bit k = k-th source).

## Settings (repository → Settings → Secrets and variables → Actions)

- **Variable `ADDON_REPO`:** `owner/CommandCenter`, the repo holding `collected/`.
- **Variable `DB_CONSUMERS`** (optional): other addon repos to ping.
- **Secret `PIPELINE_TOKEN`:** a fine-grained GitHub token with Contents (read/write) and Actions (read/write) on both repos.
- **Variable `QUESTIE_GENERATED`** (optional): `off` leaves out QuestieDB's Wowhead-derived delta-base.
- **Secret `CF_API_KEY`:** CurseForge API token (https://legacy.curseforge.com/account/api-tokens), used to upload ForeverDB.

## Licence

The merged data is GPL-3.0. Every slice ships `LICENSE-DATA.txt` (sources and their licences),
`LICENSE-GPL.txt` and `LICENSE-pfQuest.txt` (MIT notice).
