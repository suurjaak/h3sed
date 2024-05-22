# -*- coding: utf-8 -*-
"""
Constants, data store and savefile functionality.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     22.03.2020
@modified    22.05.2024
------------------------------------------------------------------------------
"""
from collections import defaultdict, OrderedDict
import copy
import datetime
import gzip
import logging
import os
import re
import sys

from h3sed import conf
from h3sed import plugins
from h3sed.lib import util


logger = logging.getLogger(__package__)


"""Blank value bytes."""
Blank = b"\xFF"
Null  = b"\x00"


"""Index for various byte starts in savefile bytearray."""
BytePositions = {
    "version_major":    8,  # Game major version byte
    "version_minor":   12,  # Game minor version byte
}


"""Hero primary attributes, in file order, as {name: label}."""
PrimaryAttributes = OrderedDict([
    ('attack', 'Attack'),      ('defense',   'Defense'),
    ('power',  'Spell Power'), ('knowledge', 'Knowledge')
])


"""Hero skills, in file order."""
Skills = [
    "Pathfinding", "Archery", "Logistics", "Scouting", "Diplomacy", "Navigation",
    "Leadership", "Wisdom", "Mysticism", "Luck", "Ballistics", "Eagle Eye",
    "Necromancy", "Estates", "Fire Magic", "Air Magic", "Water Magic",
    "Earth Magic", "Scholar", "Tactics", "Artillery", "Learning", "Offense",
    "Armorer", "Intelligence", "Sorcery", "Resistance", "First Aid",
]


"""Hero skill levels, in ascending order."""
SkillLevels = ["Basic", "Advanced", "Expert"]


"""Hero primary attribute value range, as (min, max)."""
PrimaryAttributeRange = (0, 127)


"""Hero artifacts, for wearing and side slots, excluding spell scrolls."""
Artifacts = [
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
    "Bowstring of the Unicorns's Mane",
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
    "Inexhaustable Cart of Lumber",
    "Inexhaustable Cart of Ore",
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
    "Orb of Firmament",
    "Orb of Inhibition",
    "Orb of Silt",
    "Orb of Tempestous Fire",
    "Orb of Vulnerability",
    "Pendant of Agitation",
    "Pendant of Courage",
    "Pendant of Death",
    "Pendant of Dispassion",
    "Pendant of Free Will",
    "Pendant of Holiness",
    "Pendant of Life",
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
    "Scales of the Greater Balilisk",
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
SpecialArtifacts = [
    "Ammo Cart",
    "Ballista",
    "Catapult",
    "First Aid Tent",
    "Spellbook",
]


"""Creatures for hero army slots."""
Creatures = [
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
    "Chaos hydra",
    "Crusader",
    "Cyclops",
    "Cyclops King",
    "Daemon",
    "Dread Knight",
    "Dendroid Guard",
    "Dendroid Soldier",
    "Devil",
    "Diamond Golem",
    "Dragonfly",
    "Dwarf",
    "Earth Elemental",
    "Efreet",
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
    "Golem",
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
Spells = [
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
    "Quick Sand",
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
IDs = {
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
    "Bowstring of the Unicorns's Mane":  0x3D,
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
    "Inexhaustable Cart of Lumber":      0x72,
    "Inexhaustable Cart of Ore":         0x70,
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
    "Orb of Firmament":                  0x4F,
    "Orb of Inhibition":                 0x7E,
    "Orb of Silt":                       0x50,
    "Orb of Tempestous Fire":            0x51,
    "Orb of Vulnerability":              0x5D,
    "Pendant of Agitation":              0x6A,
    "Pendant of Courage":                0x6C,
    "Pendant of Death":                  0x68,
    "Pendant of Dispassion":             0x64,
    "Pendant of Free Will":              0x69,
    "Pendant of Holiness":               0x66,
    "Pendant of Life":                   0x67,
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
    "Scales of the Greater Balilisk":    0x1B,
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
    "Basilisk":                          0x68,
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
    "Chaos hydra":                       0x6F,
    "Crusader":                          0x07,
    "Cyclops":                           0x5E,
    "Cyclops King":                      0x5F,
    "Daemon":                            0x30,
    "Dread Knight":                      0x43,
    "Dendroid Guard":                    0x16,
    "Dendroid Soldier":                  0x17,
    "Devil":                             0x36,
    "Diamond Golem":                     0x75,
    "Dragonfly":                         0x67,
    "Dwarf":                             0x10,
    "Earth Elemental":                   0x71,
    "Efreet":                            0x34,
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
    "Golem":                             0x74,
    "Gorgon":                            0x6A,
    "Grand Elf":                         0x13,
    "Greater Basilisk":                  0x69,
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
    "Mighty Gorgon":                     0x6B,
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
    "Serpent Fly":                       0x66,
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
    "Quick Sand":                        0x0A,
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
ArtifactSlots = {
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
    "Bowstring of the Unicorns's Mane":  ["side"],
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
    "Inexhaustable Cart of Lumber":      ["side"],
    "Inexhaustable Cart of Ore":         ["side"],
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
    "Orb of Firmament":                  ["side"],
    "Orb of Inhibition":                 ["side"],
    "Orb of Silt":                       ["side"],
    "Orb of Tempestous Fire":            ["side"],
    "Orb of Vulnerability":              ["side"],
    "Pendant of Agitation":              ["neck"],
    "Pendant of Courage":                ["neck"],
    "Pendant of Death":                  ["neck"],
    "Pendant of Dispassion":             ["neck"],
    "Pendant of Free Will":              ["neck"],
    "Pendant of Holiness":               ["neck"],
    "Pendant of Life":                   ["neck"],
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
    "Scales of the Greater Balilisk":    ["armor"],
    "Sea Captain's Hat":                 ["helm"],
    "Sentinel's Shield":                 ["shield"],
    "Shackles of War":                   ["side"],
    "Shield of the Dwarven Lords":       ["shield"],
    "Shield of the Yawning Dead":        ["shield"],
    "Skull Helmet":                      ["helm"],
    "Speculum":                          ["side"],
    "Spellbinder's Hat":                 ["helm"],
    "Sphere of Permanence":              ["side"],
    "Spirit of Oppression":              ["side"],
    "Spyglass":                          ["side"],
    "Statesman's Medal":                 ["side"],
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
ArtifactSpells = {
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
ArtifactStats = {
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
ScrollArtifacts = []
for t in Spells:
    n = "%s: %s" % ("Spell Scroll", t)
    Artifacts.append(n)
    ArtifactSlots[n]  = ["side"]
    ArtifactSpells[n] = [t]
    IDs[n] = (IDs[t] << 32) + IDs["Spell Scroll"]
    ScrollArtifacts.append(n)



def wildcard():
    """Returns wildcard string for file controls, as "label (*.ext)|*.ext|.."."""
    result = "All files (*.*)|*.*"
    for name, exts in conf.FileExtensions[::-1]:
        exts1 = exts2 = ";".join("*" + x for x in exts)
        if "linux" in sys.platform:  # Case-sensitive operating system
            exts2 = ";".join("*%s;*%s" % (x.lower(), x.upper()) for x in exts)
        result = "%s (%s)|%s|%s" % (name, exts1, exts2, result)
    return result



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


    def __init__(self, filename):
        self.filename = filename
        self.raw      = None
        self.raw0     = None
        self.version  = None
        self.dt       = None
        self.mapdata  = {}
        self.size     = 0
        self.usize    = 0
        self.read()


    def patch(self, bytes, span):
        """Patches unpacked contents with bytes from span[0] to span[1]."""
        if not span or not bytes: return
        self.raw = self.raw[0:span[0]] + bytes + self.raw[span[1]:]
        self.usize = len(self.raw)


    def read(self):
        """Reads in file contents and attributes."""
        with gzip.GzipFile(self.filename, "rb") as f: raw = bytearray(f.read())
        self.raw0 = self.raw = raw
        self.detect_version()
        self.parse_metadata()
        self.update_info()
        logger.info("Opened %s (%s, unzipped %s).", self.filename,
                    util.format_bytes(self.size), util.format_bytes(self.usize))


    def write(self, filename=None):
        """Writes out gzipped file."""
        filename = filename or self.filename
        with gzip.GzipFile(filename, "wb") as f: f.write(bytes(self.raw))
        self.raw0 = self.raw
        self.update_info(filename)
        logger.info("Saved %s (%s, unzipped %s).", filename,
                    util.format_bytes(self.size), util.format_bytes(self.usize))


    def detect_version(self):
        """Auto-detects game version, raises error if savefile not recognizable."""
        if not self.RGX_MAGIC.match(self.raw):
            raise ValueError("Not recognized as Heroes3 savefile.")
        if getattr(plugins, "version", None):
            for p in plugins.version.PLUGINS:
                if p["module"].detect(self):
                    logger.info("Detected %s as version %r.", self.filename, p["name"])
                    self.version = p["name"]
                    break  # for p
            if self.version is None:
                raise ValueError("Not recognized as Heroes3 savefile "
                                 "of any supported game version.")


    def parse_metadata(self):
        """Populates savefile map name and description."""
        match = self.RGX_HEADER.match(self.raw[:2048])
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
    Simple data container, allowing to store and retrieve data by version
    and subcategory.
    """

    # {typename: {version: {category: {None: all, category1: filtered, ..}, ..}}}
    DATA = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

    @staticmethod
    def add(name, data, version=None, category=None):
        stype = list if isinstance(data, tuple) else type(data)
        store = Store.DATA[name][version].setdefault(category, stype())
        if isinstance(store, list):
            store.extend(x for x in copy.deepcopy(data) if x not in store)
        elif isinstance(store, dict): store.update(copy.deepcopy(data))

    @staticmethod
    def get(name, version=None, category=None):
        """If version is not specified, returns data from all versions."""
        result = None

        vv = [None, version] if version else [None] + list(Store.DATA.get(name, {}))
        for v in sorted(set(vv), key=lambda x: x or ""):
            r = Store.DATA.get(name, {}).get(v, {}).get(category)
            if r is None: continue # for v
            if result is None: result = copy.deepcopy(r)
            elif isinstance(result, list):
                result.extend(x for x in copy.deepcopy(r) if x not in result)
            elif isinstance(result, dict): result.update(copy.deepcopy(r))
        return result



Store.add("artifacts", Artifacts)
Store.add("artifacts", Artifacts, category="inventory")
Store.add("artifacts", ["Spellbook", "The Grail"], category="inventory")
Store.add("artifacts", ScrollArtifacts, category="scroll")
for slot in set(sum(ArtifactSlots.values(), [])):
    Store.add("artifacts", [k for k, v in ArtifactSlots.items() if v[0] == slot],
              category=slot)

Store.add("artifact_slots",    ArtifactSlots)
Store.add("artifact_spells",   ArtifactSpells)
Store.add("artifact_stats",    ArtifactStats)
Store.add("creatures",         Creatures)
Store.add("ids",               IDs)
Store.add("skills",            Skills)
Store.add("skill_levels",      SkillLevels)
Store.add("special_artifacts", SpecialArtifacts)
Store.add("spells",            Spells)
Store.add("bannable_spells",   [])
for artifact, spells in ArtifactSpells.items():
    Store.add("spells", spells, category=artifact)
