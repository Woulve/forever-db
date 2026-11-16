local QuestieDB = QuestieLoader:ImportModule("QuestieDB");
QuestieDB.questKeys = { ['name'] = 1, ['startedBy'] = 2, ['finishedBy'] = 3, ['requiredLevel'] = 4, ['questLevel'] = 5 }
QuestieDB.questData = [[return {
[50001] = {'Clam Quest',{{100}},{{100}},5,8},
}]]
