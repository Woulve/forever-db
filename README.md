# forever-db

A World of Warcraft: Forever database that rebuilds itself and feeds any number of addons.

**Sources**
- **Base:** the open vanilla world database [cMaNGOS classic-db](https://github.com/cmangos/classic-db) (GPL-2.0), which gives loot with real drop chances, vendors, quests, NPCs, objects and spawn points.
- **Forever:** in-game recordings from Command Center's recorder (`CommandCenterCollect`). These add Forever-only creatures, items, vendors, quests and map spots, fix renamed things, and replace a base drop rate once something has been looted 20+ times.

Wowhead is **not** scraped. Their terms forbid it.

## How it updates

1. Your PC's scheduled task pushes new recordings to the addon repo (`collected/`).
2. The addon repo pings this repo, which also runs daily on its own. `Build database` then:
   - re-imports the base when it changes;
   - merges every recording;
   - publishes a new `latest` release only when the data's hash changed.
3. Each addon repo listed gets a `db-updated` ping and pulls its slice.
4. The addon repo's daily release job uploads to CurseForge only if something changed.

## Layout

```
tools/import_base.py   MaNGOS-family SQL dump -> base.json
tools/build.py         base + recordings -> master forever.json (+ meta.hash)
tools/slice.py         master -> Lua data files for one addon (spec in slices/)
tools/sqldump.py       dump reader (no MySQL needed)
tools/luatable.py      SavedVariables reader
slices/<name>.json     what each addon gets; slices/<name>.toc = its data addon's toc
tests/run_tests.py     end-to-end test on a tiny sample
```

## Using it in another addon

1. Add `slices/myaddon.json`, for example:
   ```json
   {"global": "MyAddon_DB", "files": "Data", "target": "MyAddon_Data", "toc": "MyAddon_Data.toc",
    "tables": ["npc", "quest", "qg", "spw", "spm"], "prune": false}
   ```
   Optionally add `slices/myaddon.toc` if the slice should be its own LoadOnDemand addon.
2. Add the addon's repo to the `DB_CONSUMERS` repository variable.
3. In that repo, copy `update-db.yml` from CommandCenter and change the asset name to `myaddon.zip`.

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

## Licence

The generated data includes GPL-2.0 data from cMaNGOS. Every slice ships `LICENSE-DATA.txt` and `GPL-2.0.txt`.
