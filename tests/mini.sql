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
INSERT INTO `gameobject_template` VALUES (300,3,1,'Battered Chest',0,300),(301,2,1,'Mailbox',0,0);
CREATE TABLE `gameobject` (`guid` int, `id` int, `map` int, `position_x` float, `position_y` float, `position_z` float);
INSERT INTO `gameobject` VALUES (9,300,1,100.4,200.6,0);
CREATE TABLE `gameobject_loot_template` (`entry` int, `item` int, `ChanceOrQuestChance` float, `groupid` int, `mincountOrRef` int, `maxcount` int, `condition_id` int);
INSERT INTO `gameobject_loot_template` VALUES (300,5523,12,0,1,1,0);
CREATE TABLE `item_template` (`entry` int, `class` int, `name` varchar(255), `Quality` int, `RequiredLevel` int, `startquest` int);
INSERT INTO `item_template` VALUES (5523,0,'Small Barnacled Clam',1,0,0),(7000,4,'Gnoll Hide',0,0,0),(8000,4,'Cloth',1,0,0),(8001,4,'Scroll',1,0,401),(9999,0,'Unused',0,0,0);
CREATE TABLE `item_loot_template` (`entry` int, `item` int, `ChanceOrQuestChance` float, `groupid` int, `mincountOrRef` int, `maxcount` int, `condition_id` int);
INSERT INTO `item_loot_template` VALUES (5523,5503,100,0,1,1,0);
CREATE TABLE `npc_vendor_template` (`entry` int, `item` int, `maxcount` int, `incrtime` int);
INSERT INTO `npc_vendor_template` VALUES (5,5523,0,0);
CREATE TABLE `npc_vendor` (`entry` int, `item` int, `maxcount` int, `incrtime` int);
INSERT INTO `npc_vendor` VALUES (200,8000,0,0);
CREATE TABLE `quest_template` (`entry` int, `ZoneOrSort` int, `MinLevel` int, `QuestLevel` int, `Title` text, `RewChoiceItemId1` int, `RewChoiceItemId2` int, `RewItemId1` int);
INSERT INTO `quest_template` VALUES (400,12,8,12,'The Clam Quest',5523,0,0),(401,12,1,5,'A Scroll',0,0,0);
CREATE TABLE `creature_questrelation` (`id` int, `quest` int);
INSERT INTO `creature_questrelation` VALUES (200,400);
CREATE TABLE `creature_involvedrelation` (`id` int, `quest` int);
INSERT INTO `creature_involvedrelation` VALUES (200,400);
