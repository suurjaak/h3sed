# -*- coding: utf-8 -*-
"""
Subplugin for HOMM3 version "Armageddon's Blade".

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   22.05.2024
@modified  27.07.2025
------------------------------------------------------------------------------
"""
import re

from .. import conf
from .. import hero
from .. import metadata
from .. hero import make_artifact_cast, make_integer_cast, make_string_cast


NAME  = "ab"
TITLE = "Armageddon's Blade"


"""Game major and minor version byte ranges, as (min, max)."""
VERSION_BYTERANGES = {
    "version_major":  (42, 42),
    "version_minor":  ( 1,  1),
}


"""Hero artifacts, for wearing and side slots, excluding spell scrolls."""
ARTIFACTS = [
    "Armageddon's Blade",
    "Vial of Dragon Blood",
]


"""Creatures for hero army slots."""
Creatures = [
    "Azure Dragon",
    "Boar",
    "Crystal Dragon",
    "Enchanter",
    "Faerie Dragon",
    "Halfling",
    "Mummy",
    "Nomad",
    "Peasant",
    "Rogue",
    "Rust Dragon",
    "Sharpshooter",
    "Troll",
]


"""IDs of artifacts, creatures and spells in savefile."""
IDS = {
    # Artifacts
    "Armageddon's Blade":                0x80,
    "Vial of Dragon Blood":              0x7F,

    # Creatures
    "Azure Dragon":                      0x84,
    "Boar":                              0x8C,
    "Crystal Dragon":                    0x85,
    "Enchanter":                         0x88,
    "Faerie Dragon":                     0x86,
    "Halfling":                          0x8A,
    "Mummy":                             0x8D,
    "Nomad":                             0x8E,
    "Peasant":                           0x8B,
    "Rogue":                             0x8F,
    "Rust Dragon":                       0x87,
    "Sharpshooter":                      0x89,
    "Troll":                             0x90,
}


"""Artifact slots, with first being primary slot."""
ARTIFACT_SLOTS = {
    "Armageddon's Blade":                ["weapon"],
    "Vial of Dragon Blood":              ["side"],
}


"""Primary skill modifiers that artifacts give to hero."""
ARTIFACT_STATS = {
    "Armageddon's Blade":                (+3, +3, +3, +6),
}


"""Spells that artifacts make available to hero."""
ARTIFACT_SPELLS = {
    "Armageddon's Blade":                ["Armageddon"],
}



"""Regulax expression for finding hero struct in savefile bytes."""
HERO_REGEX = re.compile(b"""
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

                             # 144 bytes: 18 8-byte equipments worn            351-494
                             # Blank spots:   FF FF FF FF XY XY XY XY
                             # Artifacts:     XY 00 00 00 FF FF FF FF
                             # Scrolls:       XY 00 00 00 00 00 00 00
    (?P<equipment>(          # Catapult etc:  XY 00 00 00 XY XY 00 00
      (\xFF{4} .{4}) | (.\x00{3} (\x00{4} | \xFF{4})) | (.\x00{3}.{2}\x00{2})
    ){18})

                             # 512 bytes: 64 8-byte artifacts in inventory     495-1006
    ( ((.\x00{3}) | \xFF{4}){2} ){64}
""", re.VERBOSE | re.DOTALL)


"""Regulax expression for finding hero struct in newer releases like GOG Complete."""
HERO_REGEX_NEWFORMAT = re.compile(b"""
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

                             # 144 bytes: 18 8-byte equipments worn            351-494
                             # Blank spots:   FF FF FF FF XY XY XY XY
                             # Artifacts:     XY 00 00 00 FF FF FF FF
                             # Scrolls:       XY 00 00 00 00 00 00 00
    (?P<equipment>(          # Catapult etc:  XY 00 00 00 XY XY 00 00
      (\xFF{4} .{4}) | (.\x00{3} (\x00{4} | \xFF{4})) | (.\x00{3}.{2}\x00{2})
    ){18})
    .{8}                     # 8 bytes: side5 slot unused in RoE               494-502

                             # 512 bytes: 64 8-byte artifacts in inventory     503-1014
    ( ((.\x00{3}) | \xFF{4}){2} ){64}
""", re.VERBOSE | re.DOTALL)



class DataClass(hero.DataClass):

    def get_version(self):
        """Returns game version."""
        return NAME


class ArmyStack(DataClass, hero.ArmyStack):
    __slots__ = {"name":  make_string_cast("creatures", version=NAME),
                 "count": make_integer_cast("army.count", version=NAME)}


class Equipment(DataClass, hero.Equipment):
    __slots__ = {k: make_artifact_cast(k, version=NAME) for k in hero.Equipment.__slots__
                 if "side5" != k}


class Army(DataClass, hero.Army):             pass

class Attributes(DataClass, hero.Attributes): pass

class Inventory(DataClass, hero.Inventory):   pass

class Skill(DataClass, hero.Skill):           pass

class Skills(DataClass, hero.Skills):         pass

class Spells(DataClass, hero.Spells):         pass



def init():
    """Adds Armageddon's Blade data to metadata stores."""
    metadata.Store.add("artifacts", ARTIFACTS, version=NAME)
    metadata.Store.add("artifacts", ARTIFACTS, version=NAME, category="inventory")
    for slot in set(sum(ARTIFACT_SLOTS.values(), [])):
        metadata.Store.add("artifacts", [k for k, v in ARTIFACT_SLOTS.items() if v[0] == slot],
                  version=NAME, category=slot)

    metadata.Store.add("artifact_slots",  ARTIFACT_SLOTS,  version=NAME)
    metadata.Store.add("artifact_spells", ARTIFACT_SPELLS, version=NAME)
    metadata.Store.add("artifact_stats",  ARTIFACT_STATS,  version=NAME)
    metadata.Store.add("creatures",       Creatures,      version=NAME)
    metadata.Store.add("ids",             IDS,            version=NAME)
    for artifact, spells in ARTIFACT_SPELLS.items():
        metadata.Store.add("spells", spells, version=NAME, category=artifact)


def adapt(name, value):
    """
    Adapts certain categories:

    - "hero.equipment.DATAPROPS":   dropping slot "side5"
    - "hero_byte_positions":        dropping slot "side5", shifting slot "inventory" if older format
    - "hero_regex":                 dropping one slot from artifacts
    - "hero.PropertyName" classes:  returning version-specific data class, without slot "side5",
                                    with support for new artifacts/creatures/spells
    """
    result = value
    if "hero.equipment.DATAPROPS" == name:
        result = [x for x in value if x.get("name") != "side5"]
    elif "hero_byte_positions" == name:
        result = value.copy()
        if conf.SavegameNewFormat: result.pop("side5")
        else: result["inventory"] = result.pop("side5")
        result.pop("reserved", None)
    elif "hero_regex" == name:
        result = HERO_REGEX_NEWFORMAT if conf.SavegameNewFormat else HERO_REGEX
    elif "hero.ArmyStack" == name:
        result = ArmyStack
    elif "hero.Army" == name:
        result = Army
    elif "hero.Attributes" == name:
        result = Attributes
    elif "hero.Equipment" == name:
        result = Equipment
    elif "hero.Inventory" == name:
        result = Inventory
    elif "hero.Skill" == name:
        result = Skill
    elif "hero.Skills" == name:
        result = Skills
    elif "hero.Spells" == name:
        result = Spells
    return result


def detect(savefile):
    """Returns whether savefile bytes match Armageddon's Blade."""
    return savefile.match_byte_ranges(metadata.BYTE_POSITIONS, VERSION_BYTERANGES)
