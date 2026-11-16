local ForeverBaseNpc = QuestieLoader:CreateModule("ForeverBaseNpc")
local QuestieDB = QuestieLoader:ImportModule("QuestieDB")
local ZoneDB = QuestieLoader:ImportModule("ZoneDB")
function ForeverBaseNpc:Load()
    local npcKeys = QuestieDB.npcKeys
    local zoneIDs = ZoneDB.zoneIDs
    return {
        [100] = { [npcKeys.questStarts_add] = {50002}, [npcKeys.minLevel] = 12 },
        [99999] = { [npcKeys.name] = "Skyborne Scout", [npcKeys.minLevel] = 3, [npcKeys.maxLevel] = 4,
                    [npcKeys.spawns] = {[zoneIDs.ELWYNN_FOREST] = {{25.5, 40.25}}} },
    }
end
