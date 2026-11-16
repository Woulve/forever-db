-- VMaNGOS-style rows: one row per patch, patch ranges, several creatures per spawn
CREATE TABLE `creature_template` (
  `entry` int, `patch` int, `name` varchar(100), `subname` varchar(100), `level_min` int, `level_max` int,
  `rank` int, `loot_id` int, `vendor_id` int
);
INSERT INTO `creature_template` VALUES (300,0,'Old Name',NULL,1,2,0,300,0),(300,7,'New Name',NULL,3,4,0,300,0),(301,0,'Wolf',NULL,5,6,0,301,0);
CREATE TABLE `creature` ( `guid` int, `id` int, `id2` int, `id3` int, `id4` int, `map` int, `position_x` float, `position_y` float, `patch_min` int, `patch_max` int );
INSERT INTO `creature` VALUES (1,300,301,0,0,0,100.4,200.6,0,10),(2,301,0,0,0,0,300,400,0,5);
CREATE TABLE `creature_loot_template` ( `entry` int, `item` int, `ChanceOrQuestChance` float, `groupid` int, `mincountOrRef` int, `patch_min` int, `patch_max` int );
INSERT INTO `creature_loot_template` VALUES (300,9000,50,0,1,0,10),(300,9001,50,0,1,0,4);
CREATE TABLE `item_template` ( `entry` int, `patch` int, `name` varchar(100), `quality` int, `required_level` int, `start_quest` int );
INSERT INTO `item_template` VALUES (9000,0,'Pelt',1,0,0),(9001,0,'Old Pelt',1,0,0);
