# forever-db

A World of Warcraft: Forever database that rebuilds itself and feeds any number of addons.

**Sources**
- **Base:** the open vanilla world database [cMaNGOS classic-db](https://github.com/cmangos/classic-db) (GPL-3.0), which gives loot with real drop chances, vendors, quests, NPCs, objects and spawn points.
- **Forever:** in-game recordings from Command Center's recorder (`CommandCenterCollect`). These add Forever-only creatures, items, vendors, quests and map spots, fix renamed things, and replace a base drop rate once something has been looted 20+ times.

Wowhead is **not** scraped. Their terms forbid it.

## How it updates

1. Your PC's scheduled task pushes new recordings to the addon repo (`collected/`).
2. The addon repo pings this repo, which also runs daily on its own. `Build database` then:
   - re-imports the base when it changes;
   - merges every recording;
   - and, only when the data's hash changed (or when run by hand with *force*):
     - rebuilds the **ForeverDB** addon in `ForeverDB/`;
     - commits it and tags it `vYYYY.MM.DD.N`;
     - uploads it to CurseForge (project 1807282);
     - refreshes the `latest` GitHub release.
3. Repos listed in `DB_CONSUMERS` get a `db-updated` ping.

The **ForeverDB** addon is published on its own. Addons that use it list it as a required dependency on CurseForge, and the CurseForge app installs it for players. It is LoadOnDemand: an addon calls `C_AddOns.LoadAddOn("ForeverDB")`, then reads the global `ForeverDB`. Command Center does this.

## Layout

```
tools/import_base.py   MaNGOS-family SQL dump -> base.json
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
| `drop` / `odrop` / `idrop` | per item: {source, chance per 10000, ...} |
| `vend` | per item: vendor ids |
| `vp` | prices seen |
| `rew` | quest rewards |
| `start` | item starts a quest |
| `world` | world drops (minimum level) |
| `spw` | spawn world coordinates per map. Convert in game with `C_Map.GetMapPosFromWorldPos` |
| `spm` | recorded map spots (uiMap, 0-1000) |

## Settings (repository → Settings → Secrets and variables → Actions)

- **Variable `ADDON_REPO`:** `owner/CommandCenter`, the repo holding `collected/`.
- **Variable `DB_CONSUMERS`** (optional): other addon repos to ping.
- **Secret `PIPELINE_TOKEN`:** a fine-grained GitHub token with Contents (read/write) and Actions (read/write) on both repos.
- **Secret `CF_API_KEY`:** CurseForge API token (https://legacy.curseforge.com/account/api-tokens), used to upload ForeverDB.

## Licence

The generated data includes GPL-3.0 data from cMaNGOS. Every slice ships `LICENSE-DATA.txt` and `LICENSE-GPL.txt`.
