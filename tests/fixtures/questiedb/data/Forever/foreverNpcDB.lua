-- test fixture in QuestieDB's raw data layout
local QuestieDB = QuestieLoader:ImportModule("QuestieDB");
QuestieDB.npcKeys = { ['name'] = 1, ['minLevel'] = 4, ['maxLevel'] = 5, ['rank'] = 6, ['spawns'] = 7, ['questStarts'] = 10, ['questEnds'] = 11, ['subName'] = 14 }
QuestieDB.npcData = [[return {
[100] = {'Murloc Raider',nil,nil,10,11,0,{[12]={{50,60}}},nil,nil,nil,nil,nil,nil,nil},
[101] = {'Kobold',nil,nil,5,6,0,nil,nil,nil,nil,nil,nil,nil,nil},
}]]
