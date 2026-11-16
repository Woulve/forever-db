# ForeverDB merge report

Sources in priority order: questie, vmangos, cmangos, pfquest (Forever sources win any field they have; otherwise the most common value wins).

## Entries per source

| Source | npc | obj | item | quest |
|---|---|---|---|---|
| questie | 15564 (5442 only here) | 7289 (627 only here) | 24111 (9096 only here) | 5914 (1662 only here) |
| vmangos | 10381 (0 only here) | 9368 (507 only here) | 17707 (0 only here) | 4433 (0 only here) |
| cmangos | 10384 (0 only here) | 10743 (650 only here) | 17718 (0 only here) | 4245 (0 only here) |
| pfquest | 10385 (4 only here) | 8985 (19 only here) | 17712 (0 only here) | 4433 (0 only here) |

Merged: npc 15830, obj 11920, item 26814, quest 6095, qg 5410, qe 5744, vend 3923, rew 2563, drop 9818, odrop 3718, idrop 2746, qx 5914, nfac 7458, start 653, world 3136, spw 15877, spz 16320

Forever-only entries (only the Forever source has them): npc 5442, obj 627, item 9096, quest 1662

## Disagreements

| Field | Entries where sources disagree |
|---|---|
| npc.minLv | 641 |
| npc.maxLv | 628 |
| item.reqLevel | 321 |
| quest.minLevel | 208 |
| quest.level | 128 |
| item.name | 54 |
| obj.name | 41 |
| quest.title | 32 |
| item.quality | 20 |
| npc.name | 12 |
| npc.sub | 11 |
| npc.rank | 1 |

Drop rates compared across 2+ sources: 231978, differing more than 3x: 6776

## Examples

**npc.minLv**
- 1: {"questie": 1, "vmangos": 63, "cmangos": 1, "pfquest": 63} -> chose 1
- 2: {"questie": 1, "vmangos": 63, "cmangos": 1, "pfquest": 63} -> chose 1
- 43: {"questie": 7, "vmangos": 8, "cmangos": 8, "pfquest": 8} -> chose 7
- 72: {"vmangos": 1, "cmangos": 20, "pfquest": 1} -> chose 1
- 89: {"questie": 51, "vmangos": 50, "cmangos": 50, "pfquest": 50} -> chose 51
- 167: {"questie": 15, "vmangos": 13, "cmangos": 13, "pfquest": 13} -> chose 15
- 219: {"questie": 45, "vmangos": 20, "cmangos": 20, "pfquest": 20} -> chose 45
- 226: {"questie": 28, "vmangos": 30, "cmangos": 30, "pfquest": 30} -> chose 28

**npc.maxLv**
- 1: {"questie": 1, "vmangos": 63, "cmangos": 1, "pfquest": 63} -> chose 1
- 2: {"questie": 1, "vmangos": 63, "cmangos": 1, "pfquest": 63} -> chose 1
- 72: {"vmangos": 1, "cmangos": 20, "pfquest": 1} -> chose 1
- 89: {"questie": 50, "vmangos": 50, "cmangos": 60, "pfquest": 50} -> chose 50
- 125: {"questie": 19, "vmangos": 20, "cmangos": 20, "pfquest": 20} -> chose 19
- 129: {"questie": 63, "vmangos": 50, "cmangos": 63, "pfquest": 50} -> chose 63
- 167: {"questie": 15, "vmangos": 13, "cmangos": 13, "pfquest": 13} -> chose 15
- 219: {"questie": 45, "vmangos": 20, "cmangos": 20, "pfquest": 20} -> chose 45

**item.reqLevel**
- 872: {"questie": 18, "vmangos": 16, "cmangos": 16} -> chose 18
- 1076: {"questie": 21, "vmangos": 20, "cmangos": 20} -> chose 21
- 1082: {"questie": 5, "vmangos": 10, "cmangos": 10} -> chose 5
- 1187: {"questie": 27, "vmangos": 20, "cmangos": 20} -> chose 27
- 1214: {"questie": 14, "vmangos": 12, "cmangos": 12} -> chose 14
- 1215: {"questie": 19, "vmangos": 17, "cmangos": 17} -> chose 19
- 1314: {"questie": 16, "vmangos": 15, "cmangos": 15} -> chose 16
- 1355: {"questie": 12, "vmangos": 10, "cmangos": 10} -> chose 12

**quest.minLevel**
- 17: {"questie": 38, "vmangos": 38, "cmangos": 36, "pfquest": 38} -> chose 38
- 117: {"questie": 10, "vmangos": 0, "cmangos": 0} -> chose 10
- 172: {"questie": 10, "vmangos": 10, "cmangos": 10, "pfquest": 26} -> chose 10
- 299: {"questie": 22, "vmangos": 25, "cmangos": 25, "pfquest": 25} -> chose 22
- 303: {"questie": 22, "vmangos": 25, "cmangos": 25, "pfquest": 25} -> chose 22
- 421: {"questie": 12, "vmangos": 9, "cmangos": 9, "pfquest": 9} -> chose 12
- 618: {"questie": 40, "vmangos": 37, "cmangos": 40, "pfquest": 37} -> chose 40
- 619: {"questie": 35, "vmangos": 1, "cmangos": 1, "pfquest": 1} -> chose 35

**quest.level**
- 172: {"questie": 60, "vmangos": 60, "cmangos": 60, "pfquest": 29} -> chose 60
- 299: {"questie": 27, "vmangos": 28, "cmangos": 28, "pfquest": 28} -> chose 27
- 349: {"questie": 45, "vmangos": 35, "cmangos": 45, "pfquest": 35} -> chose 45
- 490: {"questie": 8, "vmangos": 7, "pfquest": 7} -> chose 8
- 544: {"questie": 33, "vmangos": 34, "cmangos": 34, "pfquest": 34} -> chose 33
- 556: {"questie": 33, "vmangos": 32, "cmangos": 32, "pfquest": 32} -> chose 33
- 557: {"questie": 33, "vmangos": 34, "cmangos": 34, "pfquest": 34} -> chose 33
- 614: {"questie": 51, "vmangos": 47, "cmangos": 51, "pfquest": 47} -> chose 51

**item.name**
- 1262: {"questie": "Keg of Thunderbrew", "vmangos": "Keg of Thunderbrew Lager", "cmangos": "Keg of Thunderbrew Lager", "pfquest": "Keg of Thunderbrew Lager"} -> chose 'Keg of Thunderbrew'
- 2550: {"questie": "Monster - Bow, Brown", "vmangos": "Monster - Bow, Short", "cmangos": "Monster - Bow, Brown", "pfquest": "Monster - Bow, Short"} -> chose 'Monster - Bow, Brown'
- 2695: {"questie": "Monster - Mace, Board with Nail Club", "vmangos": "Monster - Mace, Spiked Club", "cmangos": "Monster - Mace, Board with Nail Club", "pfquest": "Monster - Mace, Spiked Club"} -> chose 'Monster - Mace, Board with Nail Club'
- 3034: {"questie": "Glyphed Breastplate", "vmangos": "BKP \"Impact\" Shot", "cmangos": "Deprecated BKP \"Impact\" Shot", "pfquest": "BKP \"Impact\" Shot"} -> chose 'Glyphed Breastplate'
- 3148: {"questie": "Work Shirt", "vmangos": "Deprecated Work Shirt", "cmangos": "Work Shirt", "pfquest": "Work Shirt"} -> chose 'Work Shirt'
- 5229: {"questie": "Handstitched Leather Bracers", "vmangos": "Empty Greater Bloodstone", "cmangos": "Handstitched Leather Bracers", "pfquest": "Empty Greater Bloodstone"} -> chose 'Handstitched Leather Bracers'
- 5259: {"questie": "Monster - Flaming Arrows", "vmangos": "Monster - Bow, Red", "cmangos": "Monster - Flaming Arrows", "pfquest": "Monster - Bow, Red"} -> chose 'Monster - Flaming Arrows'
- 6232: {"questie": "Monster - Item, Flowers - Bouquet Roses", "vmangos": "Monster - Item, Flowers  - Boquet Roses", "cmangos": "Monster - Item, Flowers - Bouquet Roses", "pfquest": "Monster - Item, Flowers  - Boquet Roses"} -> chose 'Monster - Item, Flowers - Bouquet Roses'

**obj.name**
- 12653: {"vmangos": "Ghost Saber Trap", "cmangos": "Cat Figurine Trap"} -> chose 'Ghost Saber Trap'
- 19538: {"questie": "World Tree Portal", "vmangos": "Small Wisp", "cmangos": "World Tree Portal", "pfquest": "Small Wisp"} -> chose 'World Tree Portal'
- 19539: {"questie": "Grinding Wheel", "vmangos": "Medium Wisp", "cmangos": "Grinding Wheel", "pfquest": "Medium Wisp"} -> chose 'Grinding Wheel'
- 19540: {"questie": "Orc Manacle", "vmangos": "Large Wisp", "cmangos": "Orc Manacle", "pfquest": "Large Wisp"} -> chose 'Orc Manacle'
- 19550: {"questie": "Starbreeze Village Moonwell", "vmangos": "Starbreeze Moonwell", "cmangos": "Starbreeze Village Moonwell", "pfquest": "Starbreeze Moonwell"} -> chose 'Starbreeze Village Moonwell'
- 20917: {"questie": "Blue aura. short column. scale 3", "vmangos": "Blue aura, short column, scale 3", "cmangos": "Blue aura. short column. scale 3", "pfquest": "Blue aura, short column, scale 3"} -> chose 'Blue aura. short column. scale 3'
- 48404: {"questie": "Campfire", "vmangos": "Dwarven Campfire", "cmangos": "Campfire", "pfquest": "Campfire"} -> chose 'Campfire'
- 152093: {"questie": "Talon Den", "vmangos": "Kadrak Flag Spell Focus (DND)", "cmangos": "Talon Den", "pfquest": "Talon Den"} -> chose 'Talon Den'

**quest.title**
- 117: {"questie": "Thunderbrew", "vmangos": "Thunderbrew", "cmangos": "Thunderbrew Lager", "pfquest": "Thunderbrew"} -> chose 'Thunderbrew'
- 172: {"questie": "Children's Week", "vmangos": "Children's Week", "cmangos": "Children's Week", "pfquest": "Ambushed In The Forest"} -> chose "Children's Week"
- 490: {"questie": "Bounty: Gnarlpine Furbolg", "vmangos": "<UNUSED>", "pfquest": "<UNUSED>"} -> chose 'Bounty: Gnarlpine Furbolg'
- 636: {"questie": "Legends of the Earth", "vmangos": "Legends of the Earth <NYI>", "cmangos": "Legends of the Earth", "pfquest": "Legends of the Earth <NYI>"} -> chose 'Legends of the Earth'
- 684: {"questie": "WANTED: Marez Cowl", "vmangos": "Wanted!  Marez Cowl", "cmangos": "Wanted!  Marez Cowl", "pfquest": "Wanted!  Marez Cowl"} -> chose 'WANTED: Marez Cowl'
- 685: {"questie": "WANTED: Otto and Falconcrest", "vmangos": "Wanted!  Otto and Falconcrest", "cmangos": "Wanted!  Otto and Falconcrest", "pfquest": "Wanted!  Otto and Falconcrest"} -> chose 'WANTED: Otto and Falconcrest'
- 1658: {"questie": "Crashing the Wickerman Festival", "vmangos": "Crashing the Wickerman Festival", "cmangos": "Crashing the Wickerman Festival (PvP)", "pfquest": "Crashing the Wickerman Festival"} -> chose 'Crashing the Wickerman Festival'
- 4002: {"questie": "The Eastern Kingdom", "vmangos": "The Eastern Kingdoms", "cmangos": "The Eastern Kingdom", "pfquest": "The Eastern Kingdoms"} -> chose 'The Eastern Kingdom'

**item.quality**
- 3034: {"vmangos": 1, "cmangos": 2} -> chose 1
- 3148: {"vmangos": 1, "cmangos": 0} -> chose 1
- 3396: {"vmangos": 2, "cmangos": 1} -> chose 2
- 3777: {"vmangos": 0, "cmangos": 1} -> chose 0
- 5446: {"vmangos": 0, "cmangos": 1} -> chose 0
- 5447: {"vmangos": 0, "cmangos": 1} -> chose 0
- 5448: {"vmangos": 0, "cmangos": 1} -> chose 0
- 5451: {"vmangos": 0, "cmangos": 1} -> chose 0

**npc.name**
- 219: {"questie": "Groundskeeper Lomar", "vmangos": "[UNUSED] Logan Mar", "cmangos": "[UNUSED] Logan Mar", "pfquest": "[UNUSED] Logan Mar"} -> chose 'Groundskeeper Lomar'
- 1233: {"vmangos": "Shaethis Darkoak", "cmangos": "[UNUSED] Shaethis Darkoak", "pfquest": "Shaethis Darkoak"} -> chose 'Shaethis Darkoak'
- 2614: {"questie": "Argent Medic", "vmangos": "[UNUSED] Stromgarde Horseman", "cmangos": "[UNUSED] Stromgarde Horseman", "pfquest": "[UNUSED] Stromgarde Horseman"} -> chose 'Argent Medic'
- 2756: {"questie": "Grund Drokda", "vmangos": "UNUSED Grund Drokda", "cmangos": "UNUSED Grund Drokda", "pfquest": "UNUSED Grund Drokda"} -> chose 'Grund Drokda'
- 7383: {"questie": "Black Tabby", "vmangos": "Black Tabby", "cmangos": "Black Tabby", "pfquest": "Maine Coon"} -> chose 'Black Tabby'
- 10776: {"questie": "Pip Quickwit", "vmangos": "Finkle Einhorn", "cmangos": "Finkle Einhorn", "pfquest": "Finkle Einhorn"} -> chose 'Pip Quickwit'
- 11058: {"questie": "Ezra Grimm", "vmangos": "Fras Siabi", "cmangos": "Fras Siabi", "pfquest": "Fras Siabi"} -> chose 'Ezra Grimm'
- 14242: {"questie": "Sulhasa", "vmangos": "[UNUSED] Sulhasa", "cmangos": "[UNUSED] Sulhasa", "pfquest": "Sulhasa"} -> chose 'Sulhasa'

**npc.sub**
- 3690: {"questie": "Kodo Riding Instructor", "vmangos": "Riding Trainer", "cmangos": "Kodo Riding Instructor"} -> chose 'Kodo Riding Instructor'
- 4732: {"questie": "Horse Riding Instructor", "vmangos": "Riding Trainer", "cmangos": "Horse Riding Instructor"} -> chose 'Horse Riding Instructor'
- 4752: {"questie": "Wolf Riding Instructor", "vmangos": "Riding Trainer", "cmangos": "Wolf Riding Instructor"} -> chose 'Wolf Riding Instructor'
- 4753: {"questie": "Nightsaber Riding Instructor", "vmangos": "Riding Trainer", "cmangos": "Nightsaber Riding Instructor"} -> chose 'Nightsaber Riding Instructor'
- 4772: {"questie": "Ram Riding Instructor", "vmangos": "Riding Trainer", "cmangos": "Ram Riding Instructor"} -> chose 'Ram Riding Instructor'
- 4773: {"questie": "Undead Horse Riding Instructor", "vmangos": "Riding Trainer", "cmangos": "Undead Horse Riding Instructor"} -> chose 'Undead Horse Riding Instructor'
- 5492: {"questie": "Church of the Holy Light", "vmangos": "Paladin Trainer", "cmangos": "Paladin Trainer"} -> chose 'Church of the Holy Light'
- 6777: {"questie": "Specialty Engineer", "vmangos": "Speciality Engineer", "cmangos": "Speciality Engineer"} -> chose 'Specialty Engineer'

**npc.rank**
- 219: {"questie": 1, "vmangos": 0, "cmangos": 0} -> chose 1

