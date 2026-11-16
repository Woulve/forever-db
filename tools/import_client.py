"""WoW Forever client tables (wago.tools CSV exports, as committed by AllTheThings under MIT in
.contrib/.db/forever/.config/.wago/<Table>.<build>.csv) -> source json for tools/merge.py.

  python tools/import_client.py <csv folder> work/src-client.json

The client is the most exact source for what Forever's game files hold, so tools/merge.py
treats it as a Forever source (it wins the fields it has). Besides item names/quality/levels it
adds tables no other source has:

  taxi   flight masters      {id: [name, continent, x, y, z, flags, mountH, mountA]}
  umap   UI maps             {id: [name, parent, type, flags]}
  umaa   UI map placement    {assignmentId: [uiMap, mapID, areaID, uiMinX, uiMinY, uiMaxX, uiMaxY, minX, minY, minZ, maxX, maxY, maxZ]}
  area   zones / sub-zones   {id: [name, continent, parent, explorationLevel, factionMask, flags]}
  ach    achievements        {id: [title, description, reward, category, points, faction, flags, icon, criteriaTree, rewardItem, instance]}
  ctree  criteria trees      {id: [description, parent, amount, operator, criteria, order, flags]}
  crit   criteria            {id: [type, asset, modifierTree, startEvent, startAsset, failEvent, failAsset, flags]}
  mtree  modifier trees      {id: [parent, operator, amount, type, asset, secondaryAsset]}
  hol    holidays            {id: [name, looping, region, priority, filter, flags, durations[], dates[]]}
  sla    skill line spells   {spell: [[skillLine, minRank, trivialLow, trivialHigh, acquire, classMask, numSkillUps, supersedes], ...]}
  ieff   item use effects    {item: [[spell, trigger, charges, cooldownMs, categoryCooldownMs], ...]}
  seff   spell effects       {spell: [[index, effect, aura, triggerSpell, itemType, amplitude, auraPeriod], ...]}
  tset   transmog sets       {id: [name, classMask, flags, group, items[]]}
  bpet   battle pet species  {id: [creature, summonSpell, icon, petType, flags, source]}
  ctun   content tuning      {id: [lfgMinLevel, lfgMaxLevel, minLevelSquish, maxLevelSquish, ilvl, xpMultQuest]}
  wmo    map overlays        {id: [uiMapArt, width, height, offX, offY, areas[]]}
Item rows: [name, quality, reqLevel, itemLevel, class, subclass, inventoryType, icon,
            allowableClass, requiredSkill, requiredSkillRank, allowableRaces, minFaction, minReputation].
"""
import csv, glob, json, os, re, sys


def table(folder, name):
    files = [f for f in glob.glob(os.path.join(folder, name + ".*.csv")) if re.match(r".*/" + re.escape(name) + r"\.\d", f)]
    if not files:
        return [], None
    path = sorted(files)[-1]
    build = re.search(r"\.(\d+\.\d+\.\d+\.\d+)\.csv$", path)
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f)), build.group(1) if build else None


def n(v):
    if v is None or v == "":
        return None
    try:
        return int(v)
    except ValueError:
        try:
            f = float(v)
            return int(f) if f == int(f) else round(f, 2)
        except ValueError:
            return v


def s(v):
    return v if v not in (None, "") else None


def main():
    folder, dst = sys.argv[1], sys.argv[2]
    out = {k: {} for k in ["npc", "obj", "item", "quest", "qg", "qe", "drop", "odrop", "idrop", "vend", "rew", "start",
                           "world", "spw", "spz", "loc", "taxi", "umap", "area", "ach", "ctree", "crit", "mtree", "hol",
                           "sla", "ieff", "seff", "tset", "bpet", "ctun", "wmo"]}
    out["umaa"] = {}
    builds = set()

    items, b = table(folder, "Item"); builds.add(b)
    for r in items:
        out["item"][n(r["ID"])] = [None, None, None, None, n(r["ClassID"]), n(r["SubclassID"]), n(r["InventoryType"]),
                                   n(r["IconFileDataID"]), None, None, None, None, None, None]
    names, b = table(folder, "ItemSearchName"); builds.add(b)
    for r in names:
        row = out["item"].setdefault(n(r["ID"]), [None] * 14)
        while len(row) < 14:
            row.append(None)
        row[0], row[1], row[2], row[3] = s(r["Display_lang"]), n(r["OverallQualityID"]), n(r["RequiredLevel"]), n(r["ItemLevel"])
        row[8], row[9], row[10] = n(r["AllowableClass"]), n(r["RequiredSkill"]), n(r["RequiredSkillRank"])
        row[11] = n(r.get("AllowableRaces_0"))
        # reputation needed to buy / use it: faction id + standing (0 Hated ... 7 Exalted)
        if n(r.get("MinFactionID")):
            row[12], row[13] = n(r.get("MinFactionID")), n(r.get("MinReputation"))

    rows, b = table(folder, "TaxiNodes"); builds.add(b)
    for r in rows:
        out["taxi"][n(r["ID"])] = [s(r["Name_lang"]), n(r["ContinentID"]), n(r["Pos_0"]), n(r["Pos_1"]), n(r["Pos_2"]),
                                   n(r["Flags"]), n(r["MountCreatureID_0"]), n(r["MountCreatureID_1"])]
    rows, b = table(folder, "UiMap"); builds.add(b)
    for r in rows:
        out["umap"][n(r["ID"])] = [s(r["Name_lang"]), n(r["ParentUiMapID"]), n(r["Type"]), n(r["Flags"])]
    rows, b = table(folder, "UiMapAssignment"); builds.add(b)
    for r in rows:
        out["umaa"][n(r["ID"])] = ([n(r["UiMapID"]), n(r["MapID"]), n(r["AreaID"]), n(r["UiMin_0"]), n(r["UiMin_1"]), n(r["UiMax_0"]),
                            n(r["UiMax_1"]), n(r["Region_0"]), n(r["Region_1"]), n(r["Region_2"]), n(r["Region_3"]),
                            n(r["Region_4"]), n(r["Region_5"])])
    rows, b = table(folder, "AreaTable"); builds.add(b)
    for r in rows:
        out["area"][n(r["ID"])] = [s(r["AreaName_lang"]), n(r["ContinentID"]), n(r["ParentAreaID"]), n(r["ExplorationLevel"]),
                                   n(r["FactionGroupMask"]), n(r["Flags_0"])]
    rows, b = table(folder, "Achievement"); builds.add(b)
    for r in rows:
        out["ach"][n(r["ID"])] = [s(r["Title_lang"]), s(r["Description_lang"]), s(r["Reward_lang"]), n(r["Category"]),
                                  n(r["Points"]), n(r["Faction"]), n(r["Flags"]), n(r["IconFileID"]), n(r["Criteria_tree"]),
                                  n(r["RewardItemID"]), n(r["Instance_ID"])]
    rows, b = table(folder, "CriteriaTree"); builds.add(b)
    for r in rows:
        out["ctree"][n(r["ID"])] = [s(r["Description_lang"]), n(r["Parent"]), n(r["Amount"]), n(r["Operator"]),
                                    n(r["CriteriaID"]), n(r["OrderIndex"]), n(r["Flags"])]
    rows, b = table(folder, "Criteria"); builds.add(b)
    for r in rows:
        out["crit"][n(r["ID"])] = [n(r["Type"]), n(r["Asset"]), n(r["Modifier_tree_ID"]), n(r["Start_event"]),
                                   n(r["Start_asset"]), n(r["Fail_event"]), n(r["Fail_asset"]), n(r["Flags"])]
    rows, b = table(folder, "ModifierTree"); builds.add(b)
    for r in rows:
        out["mtree"][n(r["ID"])] = [n(r["Parent"]), n(r["Operator"]), n(r["Amount"]), n(r["Type"]), n(r["Asset"]),
                                    n(r["SecondaryAsset"])]
    hn, b = table(folder, "HolidayNames")
    hnames = {n(r["ID"]): s(r["Name_lang"]) for r in hn}
    rows, b = table(folder, "Holiday"); builds.add(b)
    for r in rows:
        durs = [n(r[k]) for k in r if k.startswith("Duration_") and n(r[k])]
        dates = [n(r[k]) for k in r if k.startswith("Date_") and n(r[k])]
        out["hol"][n(r["ID"])] = [hnames.get(n(r["HolidayNameID"])), n(r["Looping"]), n(r["Region"]), n(r["Priority"]),
                                  n(r["CalendarFilterType"]), n(r["Flags"]), durs, dates]
    rows, b = table(folder, "SkillLineAbility"); builds.add(b)
    for r in rows:
        out["sla"].setdefault(n(r["Spell"]), []).append([n(r["SkillLine"]), n(r["MinSkillLineRank"]), n(r["TrivialSkillLineRankLow"]),
                                                         n(r["TrivialSkillLineRankHigh"]), n(r["AcquireMethod"]), n(r["ClassMask"]),
                                                         n(r["NumSkillUps"]), n(r["SupercedesSpell"])])
    eff, b = table(folder, "ItemEffect"); builds.add(b)
    effs = {n(r["ID"]): r for r in eff}
    rows, b = table(folder, "ItemXItemEffect"); builds.add(b)
    for r in rows:
        e = effs.get(n(r["ItemEffectID"]))
        if e:
            out["ieff"].setdefault(n(r["ItemID"]), []).append([n(e["SpellID"]), n(e["TriggerType"]), n(e["Charges"]),
                                                              n(e["CoolDownMSec"]), n(e["CategoryCoolDownMSec"])])
    rows, b = table(folder, "SpellEffect"); builds.add(b)
    for r in rows:
        sp = n(r.get("SpellID"))
        if sp is None:
            continue
        out["seff"].setdefault(sp, []).append([n(r["EffectIndex"]), n(r["Effect"]), n(r["EffectAura"]), n(r["EffectTriggerSpell"]),
                                               n(r["EffectItemType"]), n(r["EffectAmplitude"]), n(r["EffectAuraPeriod"])])
    ima, b = table(folder, "ItemModifiedAppearance")
    ima_item = {n(r["ID"]): n(r["ItemID"]) for r in ima}
    sets, b = table(folder, "TransmogSet")
    for r in sets:
        out["tset"][n(r["ID"])] = [s(r["Name_lang"]), n(r["ClassMask"]), n(r["Flags"]), n(r["TransmogSetGroupID"]), []]
    rows, b = table(folder, "TransmogSetItem")
    for r in rows:
        t = out["tset"].get(n(r["TransmogSetID"]))
        it = ima_item.get(n(r["ItemModifiedAppearanceID"]))
        if t is not None and it and it not in t[4]:
            t[4].append(it)
    rows, b = table(folder, "BattlePetSpecies")
    for r in rows:
        out["bpet"][n(r["ID"])] = [n(r["CreatureID"]), n(r["SummonSpellID"]), n(r["IconFileDataID"]), n(r["PetTypeEnum"]),
                                   n(r["Flags"]), n(r["SourceTypeEnum"])]
    rows, b = table(folder, "ContentTuning")
    for r in rows:
        out["ctun"][n(r["ID"])] = [n(r.get("LfgMinLevel")), n(r.get("LfgMaxLevel")), n(r.get("MinLevelSquish")),
                                   n(r.get("MaxLevelSquish")), n(r.get("ILevel")), n(r.get("XpMultQuest"))]
    rows, b = table(folder, "WorldMapOverlay")
    for r in rows:
        out["wmo"][n(r["ID"])] = [n(r["UiMapArtID"]), n(r["TextureWidth"]), n(r["TextureHeight"]), n(r["OffsetX"]),
                                  n(r["OffsetY"]), [n(r[k]) for k in r if k.startswith("AreaID_") and n(r[k])]]
    builds.discard(None)
    out["clientBuild"] = sorted(builds)[-1] if builds else None
    print("client", out["clientBuild"], {k: len(v) for k, v in out.items() if isinstance(v, (dict, list))})
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main()
