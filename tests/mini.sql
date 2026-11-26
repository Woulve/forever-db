CREATE TABLE `creature_template` (
  `Entry` mediumint(8) unsigned NOT NULL,
  `Name` char(100) NOT NULL,
  `SubName` char(100) DEFAULT NULL,
  `MinLevel` tinyint(3) NOT NULL,
  `MaxLevel` tinyint(3) NOT NULL,
  `Rank` tinyint(3) NOT NULL,
  `LootId` mediumint(8) NOT NULL,
  `VendorTemplateId` mediumint(8) NOT NULL,
  PRIMARY KEY (`Entry`)
);
INSERT INTO `creature_template` VALUES (100,'Murloc Raider',NULL,10,12,0,100,0),(101,'Gnoll \'Brute\'',NULL,20,21,1,101,0),(200,'Bob','Trade Goods',30,30,0,0,5);
CREATE TABLE `creature` (
  `guid` int(10) NOT NULL,
  `id` mediumint(8) NOT NULL,
  `map` smallint(5) NOT NULL,
  `position_x` float NOT NULL,
  `position_y` float NOT NULL,
  `position_z` float NOT NULL
);
INSERT INTO `creature` VALUES (1,100,0,-9000.5,120.2,50),(2,100,0,-9010,130,50),(3,200,0,-8800,600,40);
CREATE TABLE `creature_loot_template` (
  `entry` mediumint(8) NOT NULL,
  `item` mediumint(8) NOT NULL,
  `ChanceOrQuestChance` float NOT NULL,
  `groupid` tinyint(3) NOT NULL,
  `mincountOrRef` mediumint(9) NOT NULL,
  `maxcount` tinyint(3) NOT NULL,
  `condition_id` mediumint(8) NOT NULL
);
INSERT INTO `creature_loot_template` VALUES (100,5523,35.5,0,1,1,0),(100,0,100,0,-24000,1,0),(101,0,10,0,-24001,1,0),(101,7000,0,1,1,1,0),(101,7001,0,1,1,1,0),(101,7002,50,1,1,1,0);
CREATE TABLE `reference_loot_template` (
  `entry` mediumint(8) NOT NULL,
  `item` mediumint(8) NOT NULL,
  `ChanceOrQuestChance` float NOT NULL,
  `groupid` tinyint(3) NOT NULL,
  `mincountOrRef` mediumint(9) NOT NULL,
  `maxcount` tinyint(3) NOT NULL,
  `condition_id` mediumint(8) NOT NULL
);
INSERT INTO `reference_loot_template` VALUES (24000,8000,20,0,1,1,0),(24001,8001,50,0,1,1,0);
CREATE TABLE `gameobject_template` (`entry` int, `type` int, `displayId` int, `name` varchar(100), `data0` int, `data1` int);
INSERT INTO `gameobject_template` VALUES (300,3,1,'Battered Chest',0,300),(301,2,1,'Mailbox',0,0),(302,3,1,'Silverleaf',29,302),(303,3,1,'Silverleaf',0,302);
CREATE TABLE `gameobject` (`guid` int, `id` int, `map` int, `position_x` float, `position_y` float, `position_z` float);
INSERT INTO `gameobject` VALUES (9,300,1,100.4,200.6,0),(1000,302,0,0,50,0),(1001,302,0,100,50,0),(1002,302,0,200,50,0),(1003,302,0,300,50,0),(1004,302,0,400,50,0),(1005,302,0,500,50,0),(1006,302,0,600,50,0),(1007,302,0,700,50,0),(1008,302,0,800,50,0),(1009,302,0,900,50,0),(1010,302,0,1000,50,0),(1011,302,0,1100,50,0),(1012,302,0,1200,50,0),(1013,302,0,1300,50,0),(1014,302,0,1400,50,0),(1015,302,0,1500,50,0),(1016,302,0,1600,50,0),(1017,302,0,1700,50,0),(1018,302,0,1800,50,0),(1019,302,0,1900,50,0),(1020,302,0,2000,50,0),(1021,302,0,2100,50,0),(1022,302,0,2200,50,0),(1023,302,0,2300,50,0),(1024,302,0,2400,50,0),(1025,302,0,2500,50,0),(1026,302,0,2600,50,0),(1027,302,0,2700,50,0),(1028,302,0,2800,50,0),(1029,302,0,2900,50,0),(1030,302,0,3000,50,0),(1031,302,0,3100,50,0),(1032,302,0,3200,50,0),(1033,302,0,3300,50,0),(1034,302,0,3400,50,0),(1035,302,0,3500,50,0),(1036,302,0,3600,50,0),(1037,302,0,3700,50,0),(1038,302,0,3800,50,0),(1039,302,0,3900,50,0),(1040,302,0,4000,50,0),(1041,302,0,4100,50,0),(1042,302,0,4200,50,0),(1043,302,0,4300,50,0),(1044,302,0,4400,50,0),(1045,302,0,4500,50,0),(1046,302,0,4600,50,0),(1047,302,0,4700,50,0),(1048,302,0,4800,50,0),(1049,302,0,4900,50,0),(1050,302,0,5000,50,0),(1051,302,0,5100,50,0),(1052,302,0,5200,50,0),(1053,302,0,5300,50,0),(1054,302,0,5400,50,0),(1055,302,0,5500,50,0),(1056,302,0,5600,50,0),(1057,302,0,5700,50,0),(1058,302,0,5800,50,0),(1059,302,0,5900,50,0),(1060,302,0,6000,50,0),(1061,302,0,6100,50,0),(1062,302,0,6200,50,0),(1063,302,0,6300,50,0),(1064,302,0,6400,50,0),(1065,302,0,6500,50,0),(1066,302,0,6600,50,0),(1067,302,0,6700,50,0),(1068,302,0,6800,50,0),(1069,302,0,6900,50,0),(1070,302,0,7000,50,0),(1071,302,0,7100,50,0),(1072,302,0,7200,50,0),(1073,302,0,7300,50,0),(1074,302,0,7400,50,0),(1075,302,0,7500,50,0),(1076,302,0,7600,50,0),(1077,302,0,7700,50,0),(1078,302,0,7800,50,0),(1079,302,0,7900,50,0),(1080,302,0,8000,50,0),(1081,302,0,8100,50,0),(1082,302,0,8200,50,0),(1083,302,0,8300,50,0),(1084,302,0,8400,50,0),(1085,302,0,8500,50,0),(1086,302,0,8600,50,0),(1087,302,0,8700,50,0),(1088,302,0,8800,50,0),(1089,302,0,8900,50,0),(1090,302,0,9000,50,0),(1091,302,0,9100,50,0),(1092,302,0,9200,50,0),(1093,302,0,9300,50,0),(1094,302,0,9400,50,0),(1095,302,0,9500,50,0),(1096,302,0,9600,50,0),(1097,302,0,9700,50,0),(1098,302,0,9800,50,0),(1099,302,0,9900,50,0),(1100,302,0,10000,50,0),(1101,302,0,10100,50,0),(1102,302,0,10200,50,0),(1103,302,0,10300,50,0),(1104,302,0,10400,50,0),(1105,302,0,10500,50,0),(1106,302,0,10600,50,0),(1107,302,0,10700,50,0),(1108,302,0,10800,50,0),(1109,302,0,10900,50,0),(1110,302,0,11000,50,0),(1111,302,0,11100,50,0),(1112,302,0,11200,50,0),(1113,302,0,11300,50,0),(1114,302,0,11400,50,0),(1115,302,0,11500,50,0),(1116,302,0,11600,50,0),(1117,302,0,11700,50,0),(1118,302,0,11800,50,0),(1119,302,0,11900,50,0),(1120,302,0,12000,50,0),(1121,302,0,12100,50,0),(1122,302,0,12200,50,0),(1123,302,0,12300,50,0),(1124,302,0,12400,50,0),(1125,302,0,12500,50,0),(1126,302,0,12600,50,0),(1127,302,0,12700,50,0),(1128,302,0,12800,50,0),(1129,302,0,12900,50,0);
CREATE TABLE `gameobject_loot_template` (`entry` int, `item` int, `ChanceOrQuestChance` float, `groupid` int, `mincountOrRef` int, `maxcount` int, `condition_id` int);
INSERT INTO `gameobject_loot_template` VALUES (300,5523,12,0,1,1,0),(302,765,100,0,1,1,0);
CREATE TABLE `item_template` (`entry` int, `class` int, `name` varchar(255), `Quality` int, `RequiredLevel` int, `startquest` int);
INSERT INTO `item_template` VALUES (5523,0,'Small Barnacled Clam',1,0,0),(7000,4,'Gnoll Hide',0,0,0),(8000,4,'Cloth',1,0,0),(8001,4,'Scroll',1,0,401),(9999,0,'Unused',0,0,0);
CREATE TABLE `item_loot_template` (`entry` int, `item` int, `ChanceOrQuestChance` float, `groupid` int, `mincountOrRef` int, `maxcount` int, `condition_id` int);
INSERT INTO `item_loot_template` VALUES (5523,5503,100,0,1,1,0);
CREATE TABLE `npc_vendor_template` (`entry` int, `item` int, `maxcount` int, `incrtime` int);
INSERT INTO `npc_vendor_template` VALUES (5,5523,0,0);
CREATE TABLE `npc_vendor` (`entry` int, `item` int, `maxcount` int, `incrtime` int);
INSERT INTO `npc_vendor` VALUES (200,8000,0,0);
CREATE TABLE `quest_template` (`entry` int, `ZoneOrSort` int, `MinLevel` int, `QuestLevel` int, `Title` text, `RewChoiceItemId1` int, `RewChoiceItemId2` int, `RewItemId1` int, `RewOrReqMoney` int, `RewMoneyMaxLevel` int);
INSERT INTO `quest_template` VALUES (400,12,8,12,'The Clam Quest',5523,0,0,350,1440),(401,12,1,5,'A Scroll',0,0,0,-100,0);
CREATE TABLE `creature_questrelation` (`id` int, `quest` int);
INSERT INTO `creature_questrelation` VALUES (200,400);
CREATE TABLE `creature_involvedrelation` (`id` int, `quest` int);
INSERT INTO `creature_involvedrelation` VALUES (200,400);
