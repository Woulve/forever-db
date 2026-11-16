local ForeverNpcFixes = QuestieLoader:CreateModule("ForeverNpcFixes")
local QuestieDB = QuestieLoader:ImportModule("QuestieDB")
function ForeverNpcFixes:Load()
    local npcKeys = QuestieDB.npcKeys
    return { [101] = { [npcKeys.name] = "Kobold Tunneler" } }
end
function ForeverNpcFixes:LoadDynamic()
    return { [101] = { [QuestieDB.npcKeys.name] = "SHOULD NOT APPLY" } }
end
