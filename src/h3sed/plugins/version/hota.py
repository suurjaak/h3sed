# -*- coding: utf-8 -*-
"""
Subplugin for HOMM3 version "Horn of the Abyss".

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   22.03.2020
@modified  23.05.2024
------------------------------------------------------------------------------
"""
import logging
import re

from h3sed.lib import util
from h3sed.metadata import BytePositions, Store


logger = logging.getLogger(__package__)


PROPS = {"name": "hota", "label": "Horn of the Abyss", "index": 3}


"""Game major and minor version byte ranges, as (min, max)."""
VersionByteRanges = {
    "version_major":  (44, -1),
    "version_minor":  ( 5, -1),
}


"""Hero skills, in file order, added to default skills."""
Skills = ["Interference"]

"""Hero artifacts, for wearing and side slots, excluding spell scrolls."""
Artifacts = [
    "Admiral's Hat",
    "Angelic Alliance",
    "Armageddon's Blade",
    "Armor of the Damned",
    "Bow of the Sharpshooter",
    "Cape of Silence",
    "Charm of Eclipse",
    "Cloak of the Undead King",
    "Cornucopia",
    "Crown of the Five Seas",
    "Demon's Horseshoe",
    "Diplomat's Cloak",
    "Elixir of Life",
    "Golden Goose",
    "Hideous Mask",
    "Horn of the Abyss",
    "Ironfist of the Ogre",
    "Pendant of Downfall",
    "Pendant of Reflection",
    "Plate of Dying Light",
    "Power of the Dragon Father",
    "Ring of Oblivion",
    "Ring of Suppression",
    "Ring of the Magi",
    "Royal Armor of Nix",
    "Runes of Imminency",
    "Seal of Sunset",
    "Shaman's Puppet",
    "Shield of Naval Glory",
    "Sleepkeeper",
    "Statue of Legion",
    "Titan's Thunder",
    "Trident of Dominion",
    "Vial of Dragon Blood",
    "Wayfarer's Boots",
    "Wizard's Well",
]


"""Special artifacts like Ballista."""
SpecialArtifacts = [
    "Cannon",
]


"""Creatures for hero army slots."""
Creatures = [
    "Armadillo",
    "Automaton",
    "Ayssid",
    "Bellwether Armadillo",
    "Bounty Hunter",
    "Corsair",
    "Couatl",
    "Crew Mate",
    "Crimson Couatl",
    "Dreadnought",
    "Engineer",
    "Fangarm",
    "Gunslinger",
    "Halfing Grenadier",
    "Halfing",
    "Haspid",
    "Juggernaut",
    "Leprechaun",
    "Mechanic",
    "Nix Warrior",
    "Nix",
    "Nymph",
    "Oceanid",
    "Olgoi-Khorkhoi",
    "Pirate",
    "Sandworm",
    "Satyr",
    "Sea Dog",
    "Sea Serpent",
    "Sea Witch",
    "Seaman",
    "Sentinel Automaton",
    "Sorceress",
    "Steel Golem",
    "Stormbird",
]


"""IDs of all items in savefile."""
IDs = {
    # Artifacts
    "Admiral's Hat":                     0x88,
    "Angelic Alliance":                  0x81,
    "Armageddon's Blade":                0x80,
    "Armor of the Damned":               0x84,
    "Bow of the Sharpshooter":           0x89,
    "Cape of Silence":                   0x9F,
    "Charm of Eclipse":                  0xA2,
    "Cloak of the Undead King":          0x82,
    "Cornucopia":                        0x8C,
    "Crown of the Five Seas":            0x96,
    "Demon's Horseshoe":                 0x99,
    "Diplomat's Cloak":                  0x8D,
    "Elixir of Life":                    0x83,
    "Golden Goose":                      0xA0,
    "Hideous Mask":                      0x9B,
    "Horn of the Abyss":                 0xA1,
    "Ironfist of the Ogre":              0x8F,
    "Pendant of Downfall":               0x9D,
    "Pendant of Reflection":             0x8E,
    "Plate of Dying Light":              0xA4,
    "Power of the Dragon Father":        0x86,
    "Ring of Oblivion":                  0x9E,
    "Ring of Suppression":               0x9C,
    "Ring of the Magi":                  0x8B,
    "Royal Armor of Nix":                0x95,
    "Runes of Imminency":                0x98,
    "Seal of Sunset":                    0xA3,
    "Shaman's Puppet":                   0x9A,
    "Shield of Naval Glory":             0x94,
    "Sleepkeeper":                       0xA5,
    "Statue of Legion":                  0x85,
    "Titan's Thunder":                   0x87,
    "Trident of Dominion":               0x93,
    "Vial of Dragon Blood":              0x7F,
    "Wayfarer's Boots":                  0x97,
    "Wizard's Well":                     0x8A,

    # Special artifacts
    "Cannon":                            0x92,

    # Creatures
    "Armadillo":                         0xAE,
    "Automaton":                         0xB0,
    "Ayssid":                            0xA0,
    "Azure Dragon":                      0x84,
    "Bellwether Armadillo":              0xAF,
    "Boar":                              0x8C,
    "Bounty Hunter":                     0xB5,
    "Corsair":                           0x9E,
    "Couatl":                            0xB6,
    "Crew Mate":                         0x9B,
    "Crimson Couatl":                    0xB7,
    "Crystal Dragon":                    0x85,
    "Dreadnought":                       0xB8,
    "Enchanter":                         0x88,
    "Energy Elemental":                  0x81,
    "Engineer":                          0xAD,
    "Faerie Dragon":                     0x86,
    "Fangarm":                           0xA8,
    "Firebird":                          0x82,
    "Gunslinger":                        0xB4,
    "Halfing Grenadier":                 0xAB,
    "Halfing":                           0x8A,
    "Halfling":                          0x8A,
    "Haspid":                            0xA6,
    "Ice Elemental":                     0x7B,
    "Juggernaut":                        0xB9,
    "Leprechaun":                        0xA9,
    "Magic Elemental":                   0x79,
    "Magma Elemental":                   0x7D,
    "Mechanic":                          0xAC,
    "Mummy":                             0x8D,
    "Nix Warrior":                       0xA4,
    "Nix":                               0xA3,
    "Nomad":                             0x8E,
    "Nymph":                             0x99,
    "Oceanid":                           0x9A,
    "Olgoi-Khorkhoi":                    0xB3,
    "Peasant":                           0x8B,
    "Phoenix":                           0x83,
    "Pirate":                            0x9D,
    "Pixie":                             0x76,
    "Psychic Elemental":                 0x78,
    "Rogue":                             0x8F,
    "Rust Dragon":                       0x87,
    "Sandworm":                          0xB2,
    "Satyr":                             0xA7,
    "Sea Dog":                           0x97,
    "Sea Serpent":                       0xA5,
    "Sea Witch":                         0xA1,
    "Seaman":                            0x9C,
    "Sentinel Automaton":                0xB1,
    "Sharpshooter":                      0x89,
    "Sorceress":                         0xA2,
    "Sprite":                            0x77,
    "Steel Golem":                       0xAA,
    "Storm Elemental":                   0x7F,
    "Stormbird":                         0x9F,
    "Troll":                             0x90,

    # Skills
    "Interference":                      0x1C,

    # Spells
    "Titan's Lightning Bolt":            0x39,
}


"""Artifact slots, with first being primary slot."""
ArtifactSlots = {
    "Admiral's Hat":                     ["helm", "neck"],
    "Angelic Alliance":                  ["weapon", "helm", "neck", "armor", "shield", "feet"],
    "Armageddon's Blade":                ["weapon"],
    "Armor of the Damned":               ["armor", "helm", "weapon", "shield"],
    "Bow of the Sharpshooter":           ["side", "side", "side"],
    "Cape of Silence":                   ["cloak"],
    "Charm of Eclipse":                  ["side"],
    "Cloak of the Undead King":          ["cloak", "neck", "feet"],
    "Cornucopia":                        ["side", "hand", "hand", "cloak"],
    "Crown of the Five Seas":            ["helm"],
    "Demon's Horseshoe":                 ["side"],
    "Diplomat's Cloak":                  ["cloak", "neck", "hand"],
    "Elixir of Life":                    ["side", "hand", "hand"],
    "Golden Goose":                      ["side"],
    "Hideous Mask":                      ["side"],
    "Horn of the Abyss":                 ["side"],
    "Ironfist of the Ogre":              ["weapon", "helm", "armor", "shield",],
    "Pendant of Downfall":               ["neck"],
    "Pendant of Reflection":             ["neck"],
    "Plate of Dying Light":              ["armor"],
    "Power of the Dragon Father":        ["armor", "helm", "neck", "weapon", "shield", "hand", "hand", "cloak", "feet"],
    "Ring of Oblivion":                  ["hand"],
    "Ring of Suppression":               ["hand"],
    "Ring of the Magi":                  ["hand", "neck", "cloak"],
    "Royal Armor of Nix":                ["armor"],
    "Runes of Imminency":                ["side"],
    "Seal of Sunset":                    ["hand"],
    "Shaman's Puppet":                   ["side"],
    "Shield of Naval Glory":             ["shield"],
    "Sleepkeeper":                       ["side"],
    "Statue of Legion":                  ["side", "side", "side", "side", "side"],
    "Titan's Thunder":                   ["weapon", "helm", "armor", "shield"],
    "Trident of Dominion":               ["weapon"],
    "Vial of Dragon Blood":              ["side"],
    "Wayfarer's Boots":                  ["feet"],
}


"""Primary skill modifiers that artifacts give to hero."""
ArtifactStats = {
    "Angelic Alliance":                  (21, 21, 21, 21),
    "Armageddon's Blade":                (+3, +3, +3, +6),
    "Armor of the Damned":               (+3, +3, +2, +2),
    "Crown of the Five Seas":            ( 0,  0,  0, +6),
    "Ironfist of the Ogre":              (+5, +5, +4, +4),
    "Power of the Dragon Father":        (16, 16, 16, 16),
    "Royal Armor of Nix":                ( 0,  0, +6,  0),
    "Shield of Naval Glory":             ( 0, +7,  0,  0),
    "Titan's Thunder":                   (+9, +9, +8, +8),
    "Trident of Dominion":               (+7,  0,  0,  0),
}


"""Spells that artifacts make available to hero."""
ArtifactSpells = {
    "Armageddon's Blade":                ["Armageddon"],
    "Titan's Thunder":                   ["Titan's Lightning Bolt"],
}


"""Spells that may be banned on certain maps, like boat spells on maps with no water."""
BannableSpells = [
    "Scuttle Boat",
    "Summon Boat",
    "Water Walk",
]



# Index for byte start of various attributes in hero bytearray
POS = {
    "skills_slot":     1061, # Skill slots
}

# Since savefile format is unknown, hero structs are identified heuristically,
# by matching byte patterns.
RGX_HERO = re.compile(b"""
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
    [\x00-\x03]{29}          #  29 bytes: skill levels (Interference last)     151-179
    .{27}                    #  27 bytes: skill slots (legacy, unused)         180-206
    .{4}                     #   4 bytes: primary stats                        207-210

    [\x00-\x01]{70}          #  70 bytes: spells in book                       211-280
    [\x00-\x01]{70}          #  70 bytes: spells available                     281-350

                             # 152 bytes: 19 8-byte equipments worn            351-502
                             # Blank spots:   FF FF FF FF XY XY XY XY
                             # Artifacts:     XY 00 00 00 FF FF FF FF
                             # Scrolls:       XY 00 00 00 00 00 00 00
    (?P<artifacts>           # Catapult etc:  XY 00 00 00 XY XY 00 00
      (\xFF{4} .{4}) | (.\x00{3} (\x00{4} | \xFF{4})) | (.\x00{3}.{2}\x00{2})
    ){19}

                             # 512 bytes: 64 8-byte artifacts in backpack      503-1014
    ( ((.\x00{3}) | \xFF{4}){2} ){64}

                             # 10 bytes: slots taken by combination artifacts 1015-1024
                             # Values should only be [\x00-\x05] as the count reserved,
    .{10}                    # but HotA appears to encode additional information here.

    .{36}                    #  36 bytes: unknown                             1025-1060
    [\x00-\x1C]{29}          #  29 bytes: skill slots                         1061-1089
""", re.VERBOSE | re.DOTALL)



def init():
    """Initializes artifacts and creatures for Horn of the Abyss."""
    Store.add("artifacts", Artifacts, version=PROPS["name"])
    Store.add("artifacts", Artifacts, version=PROPS["name"], category="inventory")
    for slot in set(sum(ArtifactSlots.values(), [])):
        Store.add("artifacts", [k for k, v in ArtifactSlots.items() if v[0] == slot],
                  version=PROPS["name"], category=slot)

    Store.add("artifact_slots",    ArtifactSlots,    version=PROPS["name"])
    Store.add("artifact_spells",   ArtifactSpells,   version=PROPS["name"])
    Store.add("artifact_stats",    ArtifactStats,    version=PROPS["name"])
    Store.add("creatures",         Creatures,        version=PROPS["name"])
    Store.add("ids",               IDs,              version=PROPS["name"])
    Store.add("skills",            Skills,           version=PROPS["name"])
    Store.add("special_artifacts", SpecialArtifacts, version=PROPS["name"])
    Store.add("bannable_spells",   BannableSpells,   version=PROPS["name"])
    for artifact, spells in ArtifactSpells.items():
        Store.add("spells", spells, version=PROPS["name"], category=artifact)


def props():
    """Returns props as {label, index}."""
    return PROPS


def adapt(source, category, value):
    """
    Adapts certain categories:

    - "pos"   for hero sub-plugins: adding Interference-skill support
    - "props" for skills-plugin:    adding Interference-skill support
    - "props" for stats-plugin:     adding cannon support
    - "regex" for hero-plugin:      adding Interference-skill support
    """
    root = util.get(source, "parent", default=source)
    if util.get(root, "savefile", "version") != PROPS["name"]: return value

    result = value
    if "props" == category and "stats" == util.get(source, "name"):
        # Replace ballista-prop checkbox with combobox including cannon
        result = []
        for prop in value:
            if "ballista" == prop["name"]:
                cc = ["", "Ballista", "Cannon"]
                prop = dict(prop, type="combo", choices=cc)
            result.append(prop)
    elif "props" == category and "skills" == util.get(source, "name"):
        result = []
        for prop in value:
            if "max" in prop: prop = dict(prop, max=prop["max"] + len(Skills))
            result.append(prop)
    elif "regex" == category and "hero" == util.get(source, "name"):
        # Replace hero regex with one expecting 29 skill choices
        result = RGX_HERO
    elif "pos" == category and "hero" == util.get(root, "name"):
        # Update skill slots position
        result = dict(value, **POS)
    return result


def detect(savefile):
    """Returns whether savefile bytes match Horn of the Abyss."""
    return savefile.match_byte_ranges(BytePositions, VersionByteRanges)
