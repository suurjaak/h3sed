# -*- coding: utf-8 -*-
"""
Constants, data store and savefile functionality.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   22.03.2020
@modified  06.08.2025
------------------------------------------------------------------------------
"""
from collections import Counter, defaultdict, OrderedDict
import contextlib
import copy
import datetime
import gzip
import logging
import os
import re

import h3sed
from . lib import util


logger = logging.getLogger(__package__)


"""Blank value bytes."""
BLANK = b"\xFF"
NULL  = b"\x00"


"""Index for various byte starts in savefile bytearray."""
BYTE_POSITIONS = {
    "version_major":    8,  # Game major version byte
    "version_minor":   12,  # Game minor version byte
}


"""Hero primary attributes, in file order, as {name: label}."""
PRIMARY_ATTRIBUTES = OrderedDict([
    ('attack', 'Attack'),      ('defense',   'Defense'),
    ('power',  'Spell Power'), ('knowledge', 'Knowledge')
])


"""Hero skills, in file order."""
SKILLS = [
    "Pathfinding", "Archery", "Logistics", "Scouting", "Diplomacy", "Navigation",
    "Leadership", "Wisdom", "Mysticism", "Luck", "Ballistics", "Eagle Eye",
    "Necromancy", "Estates", "Fire Magic", "Air Magic", "Water Magic",
    "Earth Magic", "Scholar", "Tactics", "Artillery", "Learning", "Offense",
    "Armorer", "Intelligence", "Sorcery", "Resistance", "First Aid",
]


"""Hero skill levels, in ascending order."""
SKILL_LEVELS = ["Basic", "Advanced", "Expert"]


"""Slots for hero artifact locations, mapping equivalents like "side1" and "side" to "side"."""
EQUIPMENT_SLOTS = {"armor": "armor", "cloak": "cloak", "feet": "feet", "helm": "helm",
                   "lefthand": "hand", "neck": "neck", "righthand": "hand", "shield": "shield",
                   "side1": "side", "side2": "side", "side3": "side", "side4": "side",
                   "side5": "side", "weapon": "weapon"}


"""Hero primary attribute value range, as (min, max)."""
PRIMARY_ATTRIBUTE_RANGE = (0, 127)


"""Allowed (min, max) ranges for various hero properties."""
HERO_RANGES = {
    "attack":          PRIMARY_ATTRIBUTE_RANGE,
    "defense":         PRIMARY_ATTRIBUTE_RANGE,
    "power":           PRIMARY_ATTRIBUTE_RANGE,
    "knowledge":       PRIMARY_ATTRIBUTE_RANGE,

    "exp":             ( 0, 2**32 - 1),
    "level":           ( 0, 75),
    "mana_left":       ( 0, 2**16 - 1),
    "movement_left":   ( 0, 2**32 - 1),
    "movement_total":  ( 0, 2**32 - 1),

    "army":            ( 0, 7),
    "army.count":      ( 1, 2**32 - 1),
    "inventory":       ( 0, 64),
    "skills":          ( 0, 28),
}


"""Index for byte start of various attributes in hero bytearray."""
HERO_BYTE_POSITIONS = {
    "movement_total":     0, # Movement points in total
    "movement_left":      4, # Movement points remaining

    "exp":                8, # Experience points
    "mana_left":         16, # Spell points remaining
    "level":             18, # Hero level

    "skills_count":      12, # Skills count
    "skills_level":     151, # Skill levels
    "skills_slot":      179, # Skill slots

    "army_types":        82, # Creature type IDs
    "army_counts":      110, # Creature counts

    "spells_book":      211, # Spells in book
    "spells_available": 281, # All spells available for casting

    "attack":           207, # Primary attribute: Attack
    "defense":          208, # Primary attribute: Defense
    "power":            209, # Primary attribute: Spell Power
    "knowledge":        210, # Primary attribute: Knowledge

    "helm":             351, # Helm slot
    "cloak":            359, # Cloak slot
    "neck":             367, # Neck slot
    "weapon":           375, # Weapon slot
    "shield":           383, # Shield slot
    "armor":            391, # Armor slot
    "lefthand":         399, # Left hand slot
    "righthand":        407, # Right hand slot
    "feet":             415, # Feet slot
    "side1":            423, # Side slot 1
    "side2":            431, # Side slot 2
    "side3":            439, # Side slot 3
    "side4":            447, # Side slot 4
    "ballista":         455, # Ballista slot
    "ammo":             463, # Ammo Cart slot
    "tent":             471, # First Aid Tent slot
    "catapult":         479, # Catapult slot
    "spellbook":        487, # Spellbook slot
    "side5":            495, # Side slot 5
    "inventory":        503, # Inventory start

    "reserved": {            # Slots reserved by combination artifacts
        "helm":        1016,
        "cloak":       1017,
        "neck":        1018,
        "weapon":      1019,
        "shield":      1020,
        "armor":       1021,
        "hand":        1022, # For both left and right hand, \x00-\x02
        "feet":        1023,
        "side":        1024, # For all side slots, \x00-\x05
    },
}


"""Regulax expression for finding hero struct in savefile bytes."""
HERO_REGEX = re.compile(b"""
    # There are at least 60 bytes more at front, but those can also include
    # hero biography, making length indeterminate.
    # Bio ends at position -32 from total movement point start.
    # If bio end position is \x00, then bio is empty, otherwise bio extends back
    # until a 4-byte span giving bio length (which always ends with \x00).

    .{4}                     #   4 bytes: movement points in total             000-003
    .{4}                     #   4 bytes: movement points remaining            004-007
    .{4}                     #   4 bytes: experience                           008-011
    [\x00-\x1C][\x00]{3}     #   4 bytes: skill slots used                     012-015
    .{2}                     #   2 bytes: spell points remaining               016-017
    .{1}                     #   1 byte:  hero level                           018-018

    .{63}                    #  63 bytes: unknown                              019-081

    .{28}                    #  28 bytes: 7 4-byte creature IDs                082-109
    .{28}                    #  28 bytes: 7 4-byte creature counts             110-137

                             #  13 bytes: hero name, null-padded               138-150
    (?P<name>[^\x00-\x20].{11}\x00)
    [\x00-\x03]{28}          #  28 bytes: skill levels                         151-178
    [\x00-\x1C]{28}          #  28 bytes: skill slots                          179-206
    .{4}                     #   4 bytes: primary stats                        207-210

    [\x00-\x01]{70}          #  70 bytes: spells in book                       211-280
    [\x00-\x01]{70}          #  70 bytes: spells available                     281-350

                             # 152 bytes: 19 8-byte equipments worn            351-502
                             # Blank spots:   FF FF FF FF XY XY XY XY
                             # Artifacts:     XY 00 00 00 FF FF FF FF
                             # Scrolls:       XY 00 00 00 00 00 00 00
    (?P<equipment>(          # Catapult etc:  XY 00 00 00 XY XY 00 00
      (\xFF{4} .{4}) | (.\x00{3} (\x00{4} | \xFF{4})) | (.\x00{3}.{2}\x00{2})
    ){19})

                             # 512 bytes: 64 8-byte artifacts in inventory     503-1014
    ( ((.\x00{3}) | \xFF{4}){2} ){64}

                             # 10 bytes: slots taken by combination artifacts 1015-1024
    .[\x00-\x01]{6}[\x00-\x02][\x00-\x01][\x00-\x05]
""", re.VERBOSE | re.DOTALL)


"""Hero levels mapped to minimum experience points required."""
EXPERIENCE_LEVELS = {
     1:          0,
     2:       1000,
     3:       2000,
     4:       3200,
     5:       4600,
     6:       6200,
     7:       8000,
     8:      10000,
     9:      12200,
    10:      14700,
    11:      17500,
    12:      20600,
    13:      24320,
    14:      28784,
    15:      34140,
    16:      40567,
    17:      48279,
    18:      57533,
    19:      68637,
    20:      81961,
    21:      97949,
    22:     117134,
    23:     140156,
    24:     167782,
    25:     200933,
    26:     240714,
    27:     288451,
    28:     345735,
    29:     414475,
    30:     496963,
    31:     595948,
    32:     714730,
    33:     857268,
    34:    1028313,
    35:    1233567,
    36:    1479871,
    37:    1775435,
    38:    2130111,
    39:    2555722,
    40:    3066455,
    41:    3679334,
    42:    4414788,
    43:    5297332,
    44:    6356384,
    45:    7627246,
    46:    9152280,
    47:   10982320,
    48:   13178368,
    49:   15813625,
    50:   18975933,
    51:   22770702,
    52:   27324424,
    53:   32788890,
    54:   39346249,
    55:   47215079,
    56:   56657675,
    57:   67988790,
    58:   81586128,
    59:   97902933,
    60:  117483099,
    61:  140979298,
    62:  169174736,
    63:  203009261,
    64:  243610691,
    65:  292332407,
    66:  350798466,
    67:  420957736,
    68:  505148860,
    69:  606178208,
    70:  727413425,
    71:  872895685,
    72: 1047474397,
    73: 1256968851,
    74: 1508362195,
    75: 1810034207,
}


"""Hero artifacts, for wearing and side slots, excluding spell scrolls."""
ARTIFACTS = [
    "Ambassador's Sash",
    "Amulet of the Undertaker",
    "Angel Feather Arrows",
    "Angel Wings",
    "Armor of Wonder",
    "Arms of Legion",
    "Badge of Courage",
    "Bird of Perception",
    "Blackshard of the Dead Knight",
    "Boots of Levitation",
    "Boots of Polarity",
    "Boots of Speed",
    "Bow of Elven Cherrywood",
    "Bowstring of the Unicorn's Mane",
    "Breastplate of Brimstone",
    "Breastplate of Petrified Wood",
    "Buckler of the Gnoll King",
    "Cape of Conjuring",
    "Cape of Velocity",
    "Cards of Prophecy",
    "Celestial Necklace of Bliss",
    "Centaur's Axe",
    "Charm of Mana",
    "Clover of Fortune",
    "Collar of Conjuring",
    "Crest of Valor",
    "Crown of Dragontooth",
    "Crown of the Supreme Magi",
    "Dead Man's Boots",
    "Diplomat's Ring",
    "Dragon Scale Armor",
    "Dragon Scale Shield",
    "Dragon Wing Tabard",
    "Dragonbone Greaves",
    "Emblem of Cognizance",
    "Endless Bag of Gold",
    "Endless Purse of Gold",
    "Endless Sack of Gold",
    "Equestrian's Gloves",
    "Everflowing Crystal Cloak",
    "Everpouring Vial of Mercury",
    "Eversmoking Ring of Sulfur",
    "Garniture of Interference",
    "Glyph of Gallantry",
    "Golden Bow",
    "Greater Gnoll's Flail",
    "Head of Legion",
    "Hellstorm Helmet",
    "Helm of Chaos",
    "Helm of Heavenly Enlightenment",
    "Helm of the Alabaster Unicorn",
    "Hourglass of the Evil Hour",
    "Inexhaustible Cart of Lumber",
    "Inexhaustible Cart of Ore",
    "Ladybird of Luck",
    "Legs of Legion",
    "Lion's Shield of Courage",
    "Loins of Legion",
    "Mystic Orb of Mana",
    "Necklace of Dragonteeth",
    "Necklace of Ocean Guidance",
    "Necklace of Swiftness",
    "Ogre's Club of Havoc",
    "Orb of Driving Rain",
    "Orb of the Firmament",
    "Orb of Inhibition",
    "Orb of Silt",
    "Orb of Tempestuous Fire",
    "Orb of Vulnerability",
    "Pendant of Courage",
    "Pendant of Death",
    "Pendant of Dispassion",
    "Pendant of Free Will",
    "Pendant of Holiness",
    "Pendant of Life",
    "Pendant of Negativity",
    "Pendant of Second Sight",
    "Pendant of Total Recall",
    "Quiet Eye of the Dragon",
    "Recanter's Cloak",
    "Red Dragon Flame Tongue",
    "Rib Cage",
    "Ring of Conjuring",
    "Ring of Infinite Gems",
    "Ring of Life",
    "Ring of the Wayfarer",
    "Ring of Vitality",
    "Sandals of the Saint",
    "Scales of the Greater Basilisk",
    "Sea Captain's Hat",
    "Sentinel's Shield",
    "Shackles of War",
    "Shield of the Damned",
    "Shield of the Dwarven Lords",
    "Shield of the Yawning Dead",
    "Skull Helmet",
    "Speculum",
    "Spellbinder's Hat",
    "Sphere of Permanence",
    "Spirit of Oppression",
    "Spyglass",
    "Statesman's Medal",
    "Still Eye of the Dragon",
    "Stoic Watchman",
    "Surcoat of Counterpoise",
    "Sword of Hellfire",
    "Sword of Judgement",
    "Talisman of Mana",
    "Targ of the Rampaging Ogre",
    "Thunder Helmet",
    "Titan's Cuirass",
    "Titan's Gladius",
    "Tome of Air",
    "Tome of Earth",
    "Tome of Fire",
    "Tome of Water",
    "Torso of Legion",
    "Tunic of the Cyclops King",
    "Vampire's Cowl",
    "Vial of Lifeblood",
]


"""Special artifacts like Ballista."""
SPECIAL_ARTIFACTS = [
    "Ammo Cart",
    "Ballista",
    "Catapult",
    "First Aid Tent",
    "Spellbook",
]


"""Creatures for hero army slots."""
CREATURES = [
    "Air Elemental",
    "Ancient Behemoth",
    "Angel",
    "Arch Devil",
    "Arch Mage",
    "Archangel",
    "Archer",
    "Basilisk",
    "Battle Dwarf",
    "Behemoth",
    "Beholder",
    "Black Dragon",
    "Black Knight",
    "Bone Dragon",
    "Cavalier",
    "Centaur",
    "Centaur Captain",
    "Cerberus",
    "Champion",
    "Chaos Hydra",
    "Crusader",
    "Cyclops",
    "Cyclops King",
    "Demon",
    "Dread Knight",
    "Dendroid Guard",
    "Dendroid Soldier",
    "Devil",
    "Diamond Golem",
    "Dragon Fly",
    "Dwarf",
    "Earth Elemental",
    "Efreeti",
    "Efreet Sultan",
    "Evil Eye",
    "Familiar",
    "Fire Elemental",
    "Genie",
    "Ghost Dragon",
    "Giant",
    "Gnoll",
    "Gnoll Marauder",
    "Goblin",
    "Gog",
    "Gold Dragon",
    "Gold Golem",
    "Gorgon",
    "Grand Elf",
    "Greater Basilisk",
    "Green Dragon",
    "Gremlin",
    "Griffin",
    "Halberdier",
    "Harpy",
    "Harpy Hag",
    "Hell Hound",
    "Hobgoblin",
    "Horned Demon",
    "Hydra",
    "Imp",
    "Infernal Troglodyte",
    "Iron Golem",
    "Lich",
    "Lizard Warrior",
    "Lizardman",
    "Mage",
    "Magog",
    "Manticore",
    "Marksman",
    "Master Genie",
    "Master Gremlin",
    "Medusa",
    "Medusa Queen",
    "Mighty Gorgon",
    "Minotaur",
    "Minotaur King",
    "Monk",
    "Naga",
    "Naga Queen",
    "Obsidian Gargoyle",
    "Ogre",
    "Ogre Mage",
    "Orc",
    "Orc Chieftain",
    "Pegasus",
    "Pikeman",
    "Pit Fiend",
    "Pit Lord",
    "Power Lich",
    "Red Dragon",
    "Roc",
    "Royal Griffin",
    "Scorpicore",
    "Serpent Fly",
    "Silver Pegasus",
    "Skeleton",
    "Skeleton Warrior",
    "Stone Gargoyle",
    "Stone Golem",
    "Swordsman",
    "Zealot",
    "Zombie",
    "Thunderbird",
    "Titan",
    "Troglodyte",
    "Unicorn",
    "Walking Dead",
    "Vampire",
    "Vampire Lord",
    "War Unicorn",
    "Water Elemental",
    "Wight",
    "Wolf Raider",
    "Wolf Rider",
    "Wood Elf",
    "Wraith",
    "Wyvern",
    "Wyvern Monarch",
]


"""Spells for hero to cast."""
SPELLS = [
    "Air Shield",
    "Animate Dead",
    "Anti-Magic",
    "Armageddon",
    "Berserk",
    "Bless",
    "Blind",
    "Bloodlust",
    "Chain Lightning",
    "Clone",
    "Counterstrike",
    "Cure",
    "Curse",
    "Death Ripple",
    "Destroy Undead",
    "Dimension Door",
    "Disguise",
    "Dispel",
    "Disrupting Ray",
    "Earthquake",
    "Fire Shield",
    "Fire Wall",
    "Fireball",
    "Fly",
    "Force Field",
    "Forgetfulness",
    "Fortune",
    "Frenzy",
    "Frost Ring",
    "Haste",
    "Hypnotize",
    "Ice Bolt",
    "Implosion",
    "Inferno",
    "Land Mine",
    "Lightning Bolt",
    "Magic Arrow",
    "Magic Mirror",
    "Meteor Shower",
    "Mirth",
    "Misfortune",
    "Prayer",
    "Precision",
    "Protection from Air",
    "Protection from Earth",
    "Protection from Fire",
    "Protection from Water",
    "Quicksand",
    "Remove Obstacle",
    "Resurrection",
    "Sacrifice",
    "Scuttle Boat",
    "Shield",
    "Slayer",
    "Slow",
    "Sorrow",
    "Stone Skin",
    "Summon Air Elemental",
    "Summon Boat",
    "Summon Earth Elemental",
    "Summon Fire Elemental",
    "Summon Water Elemental",
    "Teleport",
    "Town Portal",
    "Water Walk",
    "Weakness",
    "View Air",
    "View Earth",
    "Visions",
]


"""IDs of all items in savefile."""
IDS = {
    # Artifacts
    "Ambassador's Sash":                 0x44,
    "Amulet of the Undertaker":          0x36,
    "Angel Feather Arrows":              0x3E,
    "Angel Wings":                       0x48,
    "Armor of Wonder":                   0x1F,
    "Arms of Legion":                    0x79,
    "Badge of Courage":                  0x31,
    "Bird of Perception":                0x3F,
    "Blackshard of the Dead Knight":     0x08,
    "Boots of Levitation":               0x5A,
    "Boots of Polarity":                 0x3B,
    "Boots of Speed":                    0x62,
    "Bow of Elven Cherrywood":           0x3C,
    "Bowstring of the Unicorn's Mane":   0x3D,
    "Breastplate of Brimstone":          0x1D,
    "Breastplate of Petrified Wood":     0x19,
    "Buckler of the Gnoll King":         0x0F,
    "Cape of Conjuring":                 0x4E,
    "Cape of Velocity":                  0x63,
    "Cards of Prophecy":                 0x2F,
    "Celestial Necklace of Bliss":       0x21,
    "Centaur's Axe":                     0x07,
    "Charm of Mana":                     0x49,
    "Clover of Fortune":                 0x2E,
    "Collar of Conjuring":               0x4C,
    "Crest of Valor":                    0x32,
    "Crown of Dragontooth":              0x2C,
    "Crown of the Supreme Magi":         0x16,
    "Dead Man's Boots":                  0x38,
    "Diplomat's Ring":                   0x43,
    "Dragon Scale Armor":                0x28,
    "Dragon Scale Shield":               0x27,
    "Dragon Wing Tabard":                0x2A,
    "Dragonbone Greaves":                0x29,
    "Emblem of Cognizance":              0x41,
    "Endless Bag of Gold":               0x74,
    "Endless Purse of Gold":             0x75,
    "Endless Sack of Gold":              0x73,
    "Equestrian's Gloves":               0x46,
    "Everflowing Crystal Cloak":         0x6D,
    "Everpouring Vial of Mercury":       0x6F,
    "Eversmoking Ring of Sulfur":        0x71,
    "Garniture of Interference":         0x39,
    "Glyph of Gallantry":                0x33,
    "Golden Bow":                        0x5B,
    "Greater Gnoll's Flail":             0x09,
    "Head of Legion":                    0x7A,
    "Hellstorm Helmet":                  0x17,
    "Helm of Chaos":                     0x15,
    "Helm of Heavenly Enlightenment":    0x24,
    "Helm of the Alabaster Unicorn":     0x13,
    "Hourglass of the Evil Hour":        0x55,
    "Inexhaustible Cart of Lumber":      0x72,
    "Inexhaustible Cart of Ore":         0x70,
    "Ladybird of Luck":                  0x30,
    "Legs of Legion":                    0x76,
    "Lion's Shield of Courage":          0x22,
    "Loins of Legion":                   0x77,
    "Mystic Orb of Mana":                0x4B,
    "Necklace of Dragonteeth":           0x2B,
    "Necklace of Ocean Guidance":        0x47,
    "Necklace of Swiftness":             0x61,
    "Ogre's Club of Havoc":              0x0A,
    "Orb of Driving Rain":               0x52,
    "Orb of the Firmament":              0x4F,
    "Orb of Inhibition":                 0x7E,
    "Orb of Silt":                       0x50,
    "Orb of Tempestuous Fire":           0x51,
    "Orb of Vulnerability":              0x5D,
    "Pendant of Courage":                0x6C,
    "Pendant of Death":                  0x68,
    "Pendant of Dispassion":             0x64,
    "Pendant of Free Will":              0x69,
    "Pendant of Holiness":               0x66,
    "Pendant of Life":                   0x67,
    "Pendant of Negativity":             0x6A,
    "Pendant of Second Sight":           0x65,
    "Pendant of Total Recall":           0x6B,
    "Quiet Eye of the Dragon":           0x25,
    "Recanter's Cloak":                  0x53,
    "Red Dragon Flame Tongue":           0x26,
    "Rib Cage":                          0x1A,
    "Ring of Conjuring":                 0x4D,
    "Ring of Infinite Gems":             0x6E,
    "Ring of Life":                      0x5F,
    "Ring of the Wayfarer":              0x45,
    "Ring of Vitality":                  0x5E,
    "Sandals of the Saint":              0x20,
    "Scales of the Greater Basilisk":    0x1B,
    "Sea Captain's Hat":                 0x7B,
    "Sentinel's Shield":                 0x12,
    "Shackles of War":                   0x7D,
    "Shield of the Damned":              0x11,
    "Shield of the Dwarven Lords":       0x0D,
    "Shield of the Yawning Dead":        0x0E,
    "Skull Helmet":                      0x14,
    "Speculum":                          0x34,
    "Spellbinder's Hat":                 0x7C,
    "Sphere of Permanence":              0x5C,
    "Spirit of Oppression":              0x54,
    "Spyglass":                          0x35,
    "Statesman's Medal":                 0x42,
    "Still Eye of the Dragon":           0x2D,
    "Stoic Watchman":                    0x40,
    "Surcoat of Counterpoise":           0x3A,
    "Sword of Hellfire":                 0x0B,
    "Sword of Judgement":                0x23,
    "Talisman of Mana":                  0x4A,
    "Targ of the Rampaging Ogre":        0x10,
    "Thunder Helmet":                    0x18,
    "Titan's Cuirass":                   0x1E,
    "Titan's Gladius":                   0x0C,
    "Tome of Air":                       0x57,
    "Tome of Earth":                     0x59,
    "Tome of Fire":                      0x56,
    "Tome of Water":                     0x58,
    "Torso of Legion":                   0x78,
    "Tunic of the Cyclops King":         0x1C,
    "Vampire's Cowl":                    0x37,
    "Vial of Lifeblood":                 0x60,

    # Special artifacts
    "Ammo Cart":                         0x05,
    "Ballista":                          0x04,
    "Catapult":                          0x03,
    "First Aid Tent":                    0x06,
    "Spell Scroll":                      0x01,
    "Spellbook":                         0x00,
    "The Grail":                         0x02,

    # Creatures
    "Air Elemental":                     0x70,
    "Ancient Behemoth":                  0x61,
    "Angel":                             0x0C,
    "Arch Devil":                        0x37,
    "Arch Mage":                         0x23,
    "Archangel":                         0x0D,
    "Archer":                            0x02,
    "Basilisk":                          0x6A,
    "Battle Dwarf":                      0x11,
    "Behemoth":                          0x60,
    "Beholder":                          0x4A,
    "Black Dragon":                      0x53,
    "Black Knight":                      0x42,
    "Bone Dragon":                       0x44,
    "Cavalier":                          0x0A,
    "Centaur":                           0x0E,
    "Centaur Captain":                   0x0F,
    "Cerberus":                          0x2F,
    "Champion":                          0x0B,
    "Chaos Hydra":                       0x6F,
    "Crusader":                          0x07,
    "Cyclops":                           0x5E,
    "Cyclops King":                      0x5F,
    "Demon":                             0x30,
    "Dread Knight":                      0x43,
    "Dendroid Guard":                    0x16,
    "Dendroid Soldier":                  0x17,
    "Devil":                             0x36,
    "Diamond Golem":                     0x75,
    "Dragon Fly":                        0x69,
    "Dwarf":                             0x10,
    "Earth Elemental":                   0x71,
    "Efreeti":                           0x34,
    "Efreet Sultan":                     0x35,
    "Evil Eye":                          0x4B,
    "Familiar":                          0x2B,
    "Fire Elemental":                    0x72,
    "Genie":                             0x24,
    "Ghost Dragon":                      0x45,
    "Giant":                             0x28,
    "Gnoll":                             0x62,
    "Gnoll Marauder":                    0x63,
    "Goblin":                            0x54,
    "Gog":                               0x2C,
    "Gold Dragon":                       0x1B,
    "Gold Golem":                        0x74,
    "Gorgon":                            0x66,
    "Grand Elf":                         0x13,
    "Greater Basilisk":                  0x6B,
    "Green Dragon":                      0x1A,
    "Gremlin":                           0x1C,
    "Griffin":                           0x04,
    "Halberdier":                        0x01,
    "Harpy":                             0x48,
    "Harpy Hag":                         0x49,
    "Hell Hound":                        0x2E,
    "Hobgoblin":                         0x55,
    "Horned Demon":                      0x31,
    "Hydra":                             0x6E,
    "Imp":                               0x2A,
    "Infernal Troglodyte":               0x47,
    "Iron Golem":                        0x21,
    "Lich":                              0x40,
    "Lizard Warrior":                    0x65,
    "Lizardman":                         0x64,
    "Mage":                              0x22,
    "Magog":                             0x2D,
    "Manticore":                         0x50,
    "Marksman":                          0x03,
    "Master Genie":                      0x25,
    "Master Gremlin":                    0x1D,
    "Medusa":                            0x4C,
    "Medusa Queen":                      0x4D,
    "Mighty Gorgon":                     0x67,
    "Minotaur":                          0x4E,
    "Minotaur King":                     0x4F,
    "Monk":                              0x08,
    "Naga":                              0x26,
    "Naga Queen":                        0x27,
    "Obsidian Gargoyle":                 0x1F,
    "Ogre":                              0x5A,
    "Ogre Mage":                         0x5B,
    "Orc":                               0x58,
    "Orc Chieftain":                     0x59,
    "Pegasus":                           0x14,
    "Pikeman":                           0x00,
    "Pit Fiend":                         0x32,
    "Pit Lord":                          0x33,
    "Power Lich":                        0x41,
    "Red Dragon":                        0x52,
    "Roc":                               0x5C,
    "Royal Griffin":                     0x05,
    "Scorpicore":                        0x51,
    "Serpent Fly":                       0x68,
    "Silver Pegasus":                    0x15,
    "Skeleton":                          0x38,
    "Skeleton Warrior":                  0x39,
    "Stone Gargoyle":                    0x1E,
    "Stone Golem":                       0x20,
    "Swordsman":                         0x06,
    "Zealot":                            0x09,
    "Zombie":                            0x3B,
    "Thunderbird":                       0x5D,
    "Titan":                             0x29,
    "Troglodyte":                        0x46,
    "Unicorn":                           0x18,
    "Walking Dead":                      0x3A,
    "Vampire":                           0x3E,
    "Vampire Lord":                      0x3F,
    "War Unicorn":                       0x19,
    "Water Elemental":                   0x73,
    "Wight":                             0x3C,
    "Wolf Raider":                       0x57,
    "Wolf Rider":                        0x56,
    "Wood Elf":                          0x12,
    "Wraith":                            0x3D,
    "Wyvern":                            0x6C,
    "Wyvern Monarch":                    0x6D,

    # Skills
    "Air Magic":                         0x0F,
    "Archery":                           0x01,
    "Armorer":                           0x17,
    "Artillery":                         0x14,
    "Ballistics":                        0x0A,
    "Diplomacy":                         0x04,
    "Eagle Eye":                         0x0B,
    "Earth Magic":                       0x11,
    "Estates":                           0x0D,
    "Fire Magic":                        0x0E,
    "First Aid":                         0x1B,
    "Intelligence":                      0x18,
    "Leadership":                        0x06,
    "Learning":                          0x15,
    "Logistics":                         0x02,
    "Luck":                              0x09,
    "Mysticism":                         0x08,
    "Navigation":                        0x05,
    "Necromancy":                        0x0C,
    "Offense":                           0x16,
    "Pathfinding":                       0x00,
    "Resistance":                        0x1A,
    "Scholar":                           0x12,
    "Scouting":                          0x03,
    "Sorcery":                           0x19,
    "Tactics":                           0x13,
    "Water Magic":                       0x10,
    "Wisdom":                            0x07,

    # Skill levels
    "Basic":                             0x01,
    "Advanced":                          0x02,
    "Expert":                            0x03,

    # Spells
    "Air Shield":                        0x1C,
    "Animate Dead":                      0x27,
    "Anti-Magic":                        0x22,
    "Armageddon":                        0x1A,
    "Berserk":                           0x3B,
    "Bless":                             0x29,
    "Blind":                             0x3E,
    "Bloodlust":                         0x2B,
    "Chain Lightning":                   0x13,
    "Clone":                             0x41,
    "Counterstrike":                     0x3A,
    "Cure":                              0x25,
    "Curse":                             0x2A,
    "Death Ripple":                      0x18,
    "Destroy Undead":                    0x19,
    "Dimension Door":                    0x08,
    "Disguise":                          0x04,
    "Dispel":                            0x23,
    "Disrupting Ray":                    0x2F,
    "Earthquake":                        0x0E,
    "Fire Shield":                       0x1D,
    "Fire Wall":                         0x0D,
    "Fireball":                          0x15,
    "Fly":                               0x06,
    "Force Field":                       0x0C,
    "Forgetfulness":                     0x3D,
    "Fortune":                           0x33,
    "Frenzy":                            0x38,
    "Frost Ring":                        0x14,
    "Haste":                             0x35,
    "Hypnotize":                         0x3C,
    "Ice Bolt":                          0x10,
    "Implosion":                         0x12,
    "Inferno":                           0x16,
    "Land Mine":                         0x0B,
    "Lightning Bolt":                    0x11,
    "Magic Arrow":                       0x0F,
    "Magic Mirror":                      0x24,
    "Meteor Shower":                     0x17,
    "Mirth":                             0x31,
    "Misfortune":                        0x34,
    "Prayer":                            0x30,
    "Precision":                         0x2C,
    "Protection from Air":               0x1E,
    "Protection from Earth":             0x21,
    "Protection from Fire":              0x1F,
    "Protection from Water":             0x20,
    "Quicksand":                         0x0A,
    "Remove Obstacle":                   0x40,
    "Resurrection":                      0x26,
    "Sacrifice":                         0x28,
    "Scuttle Boat":                      0x01,
    "Shield":                            0x1B,
    "Slayer":                            0x37,
    "Slow":                              0x36,
    "Sorrow":                            0x32,
    "Stone Skin":                        0x2E,
    "Summon Air Elemental":              0x45,
    "Summon Boat":                       0x00,
    "Summon Earth Elemental":            0x43,
    "Summon Fire Elemental":             0x42,
    "Summon Water Elemental":            0x44,
    "Teleport":                          0x3F,
    "Town Portal":                       0x09,
    "Water Walk":                        0x07,
    "Weakness":                          0x2D,
    "View Air":                          0x05,
    "View Earth":                        0x03,
    "Visions":                           0x02,
}


"""Artifact slots, with first being primary slot."""
ARTIFACT_SLOTS = {
    "Ambassador's Sash":                 ["cloak"],
    "Amulet of the Undertaker":          ["neck"],
    "Angel Feather Arrows":              ["side"],
    "Angel Wings":                       ["cloak"],
    "Armor of Wonder":                   ["armor"],
    "Arms of Legion":                    ["side"],
    "Badge of Courage":                  ["side"],
    "Bird of Perception":                ["side"],
    "Blackshard of the Dead Knight":     ["weapon"],
    "Boots of Levitation":               ["feet"],
    "Boots of Polarity":                 ["feet"],
    "Boots of Speed":                    ["feet"],
    "Bow of Elven Cherrywood":           ["side"],
    "Bowstring of the Unicorn's Mane":   ["side"],
    "Breastplate of Brimstone":          ["armor"],
    "Breastplate of Petrified Wood":     ["armor"],
    "Buckler of the Gnoll King":         ["shield"],
    "Cape of Conjuring":                 ["cloak"],
    "Cape of Velocity":                  ["cloak"],
    "Cards of Prophecy":                 ["side"],
    "Celestial Necklace of Bliss":       ["neck"],
    "Centaur's Axe":                     ["weapon"],
    "Charm of Mana":                     ["side"],
    "Clover of Fortune":                 ["side"],
    "Collar of Conjuring":               ["neck"],
    "Crest of Valor":                    ["side"],
    "Crown of Dragontooth":              ["helm"],
    "Crown of the Supreme Magi":         ["helm"],
    "Dead Man's Boots":                  ["feet"],
    "Diplomat's Ring":                   ["hand"],
    "Dragon Scale Armor":                ["armor"],
    "Dragon Scale Shield":               ["shield"],
    "Dragon Wing Tabard":                ["cloak"],
    "Dragonbone Greaves":                ["feet"],
    "Emblem of Cognizance":              ["side"],
    "Endless Bag of Gold":               ["side"],
    "Endless Purse of Gold":             ["side"],
    "Endless Sack of Gold":              ["side"],
    "Equestrian's Gloves":               ["hand"],
    "Everflowing Crystal Cloak":         ["cloak"],
    "Everpouring Vial of Mercury":       ["side"],
    "Eversmoking Ring of Sulfur":        ["hand"],
    "Garniture of Interference":         ["neck"],
    "Glyph of Gallantry":                ["side"],
    "Golden Bow":                        ["side"],
    "Greater Gnoll's Flail":             ["weapon"],
    "Head of Legion":                    ["side"],
    "Hellstorm Helmet":                  ["helm"],
    "Helm of Chaos":                     ["helm"],
    "Helm of Heavenly Enlightenment":    ["helm"],
    "Helm of the Alabaster Unicorn":     ["helm"],
    "Hourglass of the Evil Hour":        ["side"],
    "Inexhaustible Cart of Lumber":      ["side"],
    "Inexhaustible Cart of Ore":         ["side"],
    "Ladybird of Luck":                  ["side"],
    "Legs of Legion":                    ["side"],
    "Lion's Shield of Courage":          ["shield"],
    "Loins of Legion":                   ["side"],
    "Mystic Orb of Mana":                ["side"],
    "Necklace of Dragonteeth":           ["neck"],
    "Necklace of Ocean Guidance":        ["neck"],
    "Necklace of Swiftness":             ["neck"],
    "Ogre's Club of Havoc":              ["weapon"],
    "Orb of Driving Rain":               ["side"],
    "Orb of the Firmament":              ["side"],
    "Orb of Inhibition":                 ["side"],
    "Orb of Silt":                       ["side"],
    "Orb of Tempestuous Fire":           ["side"],
    "Orb of Vulnerability":              ["side"],
    "Pendant of Courage":                ["neck"],
    "Pendant of Death":                  ["neck"],
    "Pendant of Dispassion":             ["neck"],
    "Pendant of Free Will":              ["neck"],
    "Pendant of Holiness":               ["neck"],
    "Pendant of Life":                   ["neck"],
    "Pendant of Negativity":             ["neck"],
    "Pendant of Second Sight":           ["neck"],
    "Pendant of Total Recall":           ["neck"],
    "Quiet Eye of the Dragon":           ["hand"],
    "Recanter's Cloak":                  ["cloak"],
    "Red Dragon Flame Tongue":           ["weapon"],
    "Rib Cage":                          ["armor"],
    "Ring of Conjuring":                 ["hand"],
    "Ring of Infinite Gems":             ["hand"],
    "Ring of Life":                      ["hand"],
    "Ring of the Wayfarer":              ["hand"],
    "Ring of Vitality":                  ["hand"],
    "Sandals of the Saint":              ["feet"],
    "Scales of the Greater Basilisk":    ["armor"],
    "Sea Captain's Hat":                 ["helm"],
    "Sentinel's Shield":                 ["shield"],
    "Shackles of War":                   ["side"],
    "Shield of the Damned":              ["shield"],
    "Shield of the Dwarven Lords":       ["shield"],
    "Shield of the Yawning Dead":        ["shield"],
    "Skull Helmet":                      ["helm"],
    "Speculum":                          ["side"],
    "Spellbinder's Hat":                 ["helm"],
    "Sphere of Permanence":              ["side"],
    "Spirit of Oppression":              ["side"],
    "Spyglass":                          ["side"],
    "Statesman's Medal":                 ["neck"],
    "Still Eye of the Dragon":           ["hand"],
    "Stoic Watchman":                    ["side"],
    "Surcoat of Counterpoise":           ["cloak"],
    "Sword of Hellfire":                 ["weapon"],
    "Sword of Judgement":                ["weapon"],
    "Talisman of Mana":                  ["side"],
    "Targ of the Rampaging Ogre":        ["shield"],
    "The Grail":                         ["inventory"],
    "Thunder Helmet":                    ["helm"],
    "Titan's Cuirass":                   ["armor"],
    "Titan's Gladius":                   ["weapon"],
    "Tome of Air":                       ["side"],
    "Tome of Earth":                     ["side"],
    "Tome of Fire":                      ["side"],
    "Tome of Water":                     ["side"],
    "Torso of Legion":                   ["side"],
    "Tunic of the Cyclops King":         ["armor"],
    "Vampire's Cowl":                    ["cloak"],
    "Vial of Lifeblood":                 ["side"],
}


"""Spells that artifacts make available to hero."""
ARTIFACT_SPELLS = {
    "Spellbinder's Hat":                 ["Dimension Door", "Fly", "Implosion",
                                          "Sacrifice", "Summon Air Elemental",
                                          "Summon Earth Elemental",
                                          "Summon Fire Elemental",
                                          "Summon Water Elemental"],

    "Tome of Air":                       ["Air Shield", "Chain Lightning", "Counterstrike",
                                          "Destroy Undead", "Dimension Door", "Disguise",
                                          "Disrupting Ray", "Fly", "Fortune", "Haste",
                                          "Hypnotize", "Lightning Bolt", "Magic Arrow",
                                          "Magic Mirror", "Precision", "Protection from Air",
                                          "Summon Air Elemental", "View Air", "Visions"],

    "Tome of Earth":                     ["Animate Dead", "Anti-Magic", "Death Ripple",
                                          "Earthquake", "Force Field", "Implosion",
                                          "Magic Arrow", "Meteor Shower", "Protection from Earth",
                                          "Quicksand", "Resurrection", "Shield", "Slow",
                                          "Sorrow", "Stone Skin", "Summon Earth Elemental",
                                          "Town Portal", "View Earth", "Visions"],

    "Tome of Fire":                      ["Armageddon", "Berserk", "Blind", "Bloodlust",
                                          "Curse", "Fire Shield", "Fire Wall", "Fireball",
                                          "Frenzy", "Inferno", "Land Mine", "Magic Arrow",
                                          "Misfortune", "Protection from Fire", "Sacrifice",
                                          "Slayer", "Summon Fire Elemental", "Visions"],

    "Tome of Water":                     ["Bless", "Clone", "Cure", "Dispel", "Forgetfulness",
                                          "Frost Ring", "Ice Bolt", "Magic Arrow", "Mirth",
                                          "Prayer", "Protection from Water", "Remove Obstacle",
                                          "Scuttle Boat", "Summon Boat", "Summon Water Elemental",
                                          "Teleport", "Visions", "Water Walk", "Weakness"],
}


"""Primary skill modifiers that artifacts give to hero."""
ARTIFACT_STATS = {
    "Crown of Dragontooth":              ( 0,  0, +4, +4),
    "Crown of the Supreme Magi":         ( 0,  0,  0, +4),
    "Hellstorm Helmet":                  ( 0,  0,  0, +5),
    "Helm of Chaos":                     ( 0,  0,  0, +3),
    "Helm of Heavenly Enlightenment":    (+6, +6, +6, +6),
    "Helm of the Alabaster Unicorn":     ( 0,  0,  0, +1),
    "Skull Helmet":                      ( 0,  0,  0, +2),
    "Thunder Helmet":                    ( 0,  0, -2, 10),

    "Celestial Necklace of Bliss":       (+3, +3, +3, +3),
    "Necklace of Dragonteeth":           ( 0,  0, +3, +3),

    "Blackshard of the Dead Knight":     (+3,  0,  0,  0),
    "Centaur's Axe":                     (+2,  0,  0,  0),
    "Greater Gnoll's Flail":             (+4,  0,  0,  0),
    "Ogre's Club of Havoc":              (+5,  0,  0,  0),
    "Red Dragon Flame Tongue":           (+2, +2,  0,  0),
    "Sword of Hellfire":                 (+6,  0,  0,  0),
    "Sword of Judgement":                (+5, +5, +5, +5),
    "Titan's Gladius":                   (12, -3,  0,  0),

    "Buckler of the Gnoll King":         ( 0, +4,  0,  0),
    "Dragon Scale Shield":               ( 0,  0, +3, +3),
    "Lion's Shield of Courage":          (+4, +4, +4, +4),
    "Sentinel's Shield":                 (-3, 12,  0,  0),
    "Shield of the Damned":              ( 0, +6,  0,  0),
    "Shield of the Dwarven Lords":       ( 0, +2,  0,  0),
    "Shield of the Yawning Dead":        ( 0, +3,  0,  0),
    "Targ of the Rampaging Ogre":        ( 0, +5,  0,  0),

    "Armor of Wonder":                   (+1, +1, +1, +1),
    "Rib Cage":                          ( 0,  0, +2,  0),
    "Breastplate of Brimstone":          ( 0,  0, +5,  0),
    "Breastplate of Petrified Wood":     ( 0,  0, +1,  0),
    "Dragon Scale Armor":                (+4, +4,  0,  0),
    "Scales of the Greater Basilisk":    ( 0,  0, +3,  0),
    "Titan's Cuirass":                   ( 0,  0, 10, -2),
    "Tunic of the Cyclops King":         ( 0,  0, +4,  0),

    "Quiet Eye of the Dragon":           (+1, +1,  0,  0),

    "Dragonbone Greaves":                ( 0,  0, +1, +1),
    "Sandals of the Saint":              (+2, +2, +2, +2),
}


"""
Spell scroll artifacts, IDs like "01 00 00 00 09 00 00 00",
with 01 standing for spell scroll and 09 for Town Portal.
"""
SCROLL_ARTIFACTS = []
for t in SPELLS:
    n = "%s: %s" % ("Spell Scroll", t)
    ARTIFACTS.append(n)
    ARTIFACT_SLOTS[n]  = ["side"]
    ARTIFACT_SPELLS[n] = [t]
    IDS[n] = (IDS[t] << 32) + IDS["Spell Scroll"]
    SCROLL_ARTIFACTS.append(n)



@contextlib.contextmanager
def patch_gzip_for_partial():
    """
    Context manager replacing gzip.GzipFile._read_eof() with a version not throwing CRC error.
    For decompressing partial files.
    """

    def read_eof_py3(self):
        if not all(self._fp.read(1) for _ in range(8)): # Consume and require 8 bytes of CRC
            raise EOFError("Compressed file ended before the end-of-stream marker was reached")
        c = b"\x00"
        while c == b"\x00": c = self._fp.read(1) # Consume stream until first non-zero byte
        if c: self._fp.prepend(c)

    def read_eof_py2(self):
        c = "\x00"
        while c == "\x00": c = self.fileobj.read(1) # Consume stream until first non-zero byte
        if c: self.fileobj.seek(-1, 1)

    readercls = getattr(gzip, "_GzipReader", gzip.GzipFile)  # Py3/Py2
    read_eof_original = readercls._read_eof
    readercls._read_eof = read_eof_py2 if readercls is gzip.GzipFile else read_eof_py3

    try: yield
    finally: readercls._read_eof = read_eof_original



class Savefile(object):
    """Game savefile."""

    RGX_MAGIC = re.compile(b"^H3SV[GC]")

    RGX_HEADER = re.compile(b"""
        H3SV[GC]            # file header
        .{0,100}[^\x00]     # unknown content, unknown length
        \x00{3}.            # unknown
        (?P<name>..)        # map name length, unsigned 16-bit big-endian
        [^\x00]+            # map name
        ..                  # map description length, unsigned 16-bit big-endian
        [^\x00]+            # map description
    """, re.VERBOSE | re.DOTALL)

    HEADER_TEXTS = OrderedDict([("name", 2), ("desc", 2)])  # {name in mapdata: byte length count}


    def __init__(self, filename, parse_heroes=True):
        self.filename = filename
        self.raw      = None
        self.raw0     = None
        self.version  = None
        self.dt       = None
        self.mapdata  = {}
        self.size     = 0
        self.usize    = 0
        self.heroes   = []
        self.read(parse_heroes)


    def patch(self, bytes, span):
        """Patches unpacked contents with bytes from span[0] to span[1]."""
        if not span or not bytes: return
        self.raw = self.raw[0:span[0]] + bytes + self.raw[span[1]:]
        self.usize = len(self.raw)


    def realize(self):
        """Validates and updates changed hero data, patches savefile unpacked contents for write."""
        heroes_changed = [h for h in self.heroes if h.is_changed()]
        for hero in heroes_changed: hero.serialize()
        for hero in self.heroes: self.patch(hero.bytes, hero.span)


    def read(self, parse_heroes=True):
        """Reads in file raw contents and main attributes."""
        with patch_gzip_for_partial():
            with gzip.GzipFile(self.filename, "rb") as f: raw = bytearray(f.read())
        self.raw0 = self.raw = raw
        self.mapdata = {}
        self.heroes = []
        self.detect_version()
        self.parse_metadata()
        if parse_heroes: self.parse_heroes()
        self.update_info()
        logger.info("Opened %s (%s, unzipped %s).", self.filename,
                    util.format_bytes(self.size), util.format_bytes(self.usize))


    def write(self, filename=None):
        """Writes out gzipped file."""
        filename = filename or self.filename
        try: os.makedirs(os.path.dirname(filename))
        except Exception: pass
        with gzip.GzipFile(filename, "wb") as f: f.write(bytes(self.raw))
        self.raw0 = self.raw
        self.update_info(filename)
        for hero in self.heroes:
            if hero.is_patched(self): hero.mark_saved()
        logger.info("Saved %s (%s, unzipped %s).", filename,
                    util.format_bytes(self.size), util.format_bytes(self.usize))


    def write_ranges(self, spans, filename=None):
        """Writes out gzipped file with specified byte ranges only."""
        filename = filename or self.filename
        raw = self.raw0
        for start, end in spans: raw = raw[0:start] + self.raw[start:end] + raw[end:]
        with gzip.GzipFile(filename, "wb") as f: f.write(bytes(raw))
        self.raw0 = raw
        self.update_info(filename)
        for hero in self.heroes:
            if any(hero.span[0] >= start and hero.span[1] < end for start, end in spans):
                if hero.is_patched(self): hero.mark_saved()
        logger.info("Saved %s byte %s %s (%s, unzipped %s).", filename,
                    util.plural("range", spans, numbers=False),
                    " and ".join("..".join(map(str, x)) for x in spans),
                    util.format_bytes(self.size), util.format_bytes(self.usize))


    def detect_version(self):
        """Auto-detects game version, raises error if savefile not recognizable."""
        RGX_MAGIC = h3sed.version.adapt("savefile_magic_regex", self.RGX_MAGIC)
        if not RGX_MAGIC.match(self.raw):
            raise ValueError("Not recognized as Heroes3 savefile.")
        self.version = h3sed.version.detect(self) # Raises ValueError if not detected
        self.mapdata["game"] = self.version
        if self.version in h3sed.version.VERSIONS:
            self.mapdata["game"] = h3sed.version.VERSIONS[self.version].TITLE
        logger.info("Detected %s as version %r.", self.filename, self.version)


    def parse_metadata(self):
        """Populates savefile map name and description."""
        RGX_HEADER = h3sed.version.adapt("savefile_header_regex", self.RGX_HEADER)
        match = RGX_HEADER.match(self.raw[:2048])
        if not match:
            logger.warning("Failed to parse map name and description from %s.", self.filename)
            return
        cpos = match.start(next(iter(self.HEADER_TEXTS)))  # Start of field length count
        for n, clen in self.HEADER_TEXTS.items():  # Parse consecutive length-value fields
            try:
                nlen = util.bytoi(self.raw[cpos:cpos + clen])
                nraw = self.raw[cpos + clen:cpos + clen + nlen]
                if not re.match(b"^[^\x00]+$", nraw):
                    raise ValueError("Unexpected content in map %s: %r" % (n, nraw))
                self.mapdata[n] = util.to_unicode(nraw)
                cpos += clen + nlen
            except Exception:
                logger.exception("Failed to parse map name and description from %s.", self.filename)
        if "game" in self.mapdata: self.mapdata["game"] = self.mapdata.pop("game") # Order last


    def parse_heroes(self):
        """Populates and parses all savefile heroes in detail."""
        if not self.heroes: self.populate_heroes()
        for hero in self.heroes: hero.parse()


    def populate_heroes(self):
        """Populates raw data on savefile heroes."""
        heroes = []

        rgx_strip = re.compile(br"^(?!\xFF+\x00+$)([^\x00-\x19]+)\x00+$")
        rgx_nulls = re.compile(br"^(\x00+)|(\x00{4}\xFF{4})+$")
        REGEX = h3sed.version.adapt("hero_regex", HERO_REGEX, version=self.version)

        # Jump over potential campaign carry-over heroes, stored in savefile with their
        # original armies+artifacts; the structs used by game come later.
        pos = 30000
        m = re.search(REGEX, self.raw[pos:])
        while m:
            start, end = m.span()
            if rgx_strip.match(m.group("name")) and not rgx_nulls.match(m.group("equipment")):
                blob = bytearray(self.raw[pos + start:pos + end])
                name = util.to_unicode(rgx_strip.match(m.group("name")).group(1))
                hero = h3sed.hero.Hero(name, version=self.version)
                hero.set_file_data(blob, len(heroes), (start + pos, end + pos)) #, self)
                heroes.append(hero)
                pos += end
            else:
                pos += start + 1
            # Continue in small chunks once heroes section reached:
            # regex can get pathologically slow for the entire remainder beyond heroes
            m = re.search(REGEX, self.raw[pos:pos+5000])

        dupe_counts = Counter(x.name for x in heroes)
        heroes.sort(key=lambda x: x.name.lower())
        for hero in heroes[::-1]:
            if dupe_counts[hero.name] > 1:
                hero.name_counter = dupe_counts[hero.name]
                dupe_counts.subtract([hero.name])
        logger.info("%s heroes detected in %s as version %r.",
                    len(heroes) or "No ", self.filename, self.version)
        self.heroes = heroes


    def find_heroes(self, *texts, **keywords):
        """Yields heroes matching given texts and specific keywords, like skill="Luck"."""
        for hero in self.heroes:
            if hero.matches(*texts, **keywords): yield hero


    def update_info(self, filename=None):
        """Updates file modification and size information."""
        filename = filename or self.filename
        self.dt    = datetime.datetime.fromtimestamp(os.path.getmtime(filename))
        self.size  = os.path.getsize(filename)
        self.usize = len(self.raw)


    def is_changed(self):
        """Returns whether loaded contents have changed."""
        return self.raw != self.raw0


    def match_byte_ranges(self, positions, ranges):
        """
        Returns whether byte values in savefile uncompressed bytes match given ranges.

        @param   positions  {key: byte index in savefile uncompressed bytes}
        @param   ranges     {key in positions: (min, max)}, with negative values skipped
        """
        if not positions or not ranges or not all(k in positions for k in ranges): return False
        for k, (minv, maxv) in ranges.items():
            v = self.raw[positions[k]] if positions[k] < len(self.raw) else None
            if v is None or (minv >= 0 and v < minv) or (maxv >= 0 and v > maxv):
                return False
        return True



class Store(object):
    """
    Simple data container, allowing to store and retrieve data by subcategory and game version.

    By default, retrieved data gets combined from multiple versions.
    """

    # {typename: {version: {category: {None: all, category1: filtered, ..}, ..}}}
    DATA = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

    CACHE = {} # {(name, category, verdion): prepared result}
    
    SEPARATES = set() # {data names to not combine over versions}

    @staticmethod
    def add(name, data, category=None, version=None, separate=False):
        stype = list if isinstance(data, tuple) else type(data)
        store = Store.DATA[name][version].setdefault(category, stype())
        if isinstance(store, list):
            store.extend(x for x in copy.deepcopy(data) if x not in store)
        elif isinstance(store, dict): store.update(copy.deepcopy(data))
        if separate: Store.SEPARATES.add(name)

    @staticmethod
    def get(name, category=None, version=None):
        """
        Returns specified data, by subcategory like "inventory" if specified.

        Combines version data with default data, unless data was added as separate.

        If version is not specified, returns data from all versions.
        """
        result = Store.CACHE.get((name, category, version))
        if result is not None: return result

        vv = [None, version] if version else [None] + list(Store.DATA.get(name, {}))
        if name in Store.SEPARATES:
            vv = [version] if version and version in Store.DATA.get(name, {}) else [None]
        for v in sorted(set(vv), key=lambda x: x or ""):
            r = Store.DATA.get(name, {}).get(v, {}).get(category)
            if r is None: continue # for v
            if result is None: result = copy.deepcopy(r)
            elif isinstance(result, list):
                result.extend(x for x in copy.deepcopy(r) if x not in result)
            elif isinstance(result, dict): result.update(copy.deepcopy(r))
        Store.CACHE[(name, category, version)] = result
        return result



Store.add("artifacts", ARTIFACTS)
Store.add("artifacts", ARTIFACTS, category="inventory")
Store.add("artifacts", ["Spellbook", "The Grail"], category="inventory")
Store.add("artifacts", SCROLL_ARTIFACTS, category="scroll")
for slot in set(sum(ARTIFACT_SLOTS.values(), [])):
    Store.add("artifacts", [k for k, v in ARTIFACT_SLOTS.items() if v[0] == slot], category=slot)

Store.add("artifact_slots",      ARTIFACT_SLOTS)
Store.add("artifact_spells",     ARTIFACT_SPELLS)
Store.add("artifact_stats",      ARTIFACT_STATS)
Store.add("creatures",           CREATURES)
Store.add("equipment_slots",     EQUIPMENT_SLOTS, separate=True)  # Versions without side5 e.g. RoE
Store.add("experience_levels",   EXPERIENCE_LEVELS, separate=True) # Versions can cap level e.g. HoTA
Store.add("hero_byte_positions", HERO_BYTE_POSITIONS)
Store.add("hero_ranges",         HERO_RANGES)
Store.add("ids",                 IDS)
Store.add("skills",              SKILLS)
Store.add("skill_levels",        SKILL_LEVELS)
Store.add("special_artifacts",   SPECIAL_ARTIFACTS)
Store.add("spells",              SPELLS)
Store.add("bannable_spells",     []) # Initialize empty array for version modules to update
for artifact, spells in ARTIFACT_SPELLS.items():
    Store.add("spells", spells, category=artifact)
