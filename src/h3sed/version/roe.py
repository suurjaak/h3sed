# -*- coding: utf-8 -*-
"""
Subplugin for HOMM3 version "Restoration of Erathia".

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   22.05.2024
@modified  27.07.2025
------------------------------------------------------------------------------
"""
import re

from .. import hero
from .. import metadata
from .. hero import make_artifact_cast


NAME  = "roe"
TITLE = "Restoration of Erathia"


"""Game major and minor version byte ranges, as (min, max)."""
VERSION_BYTE_RANGES = {
    "version_major":  (16, 41),
    "version_minor":  ( 0,  0),
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

                             # 512 bytes: 64 8-byte artifacts in backpack      495-1006
    ( ((.\x00{3}) | \xFF{4}){2} ){64}
""", re.VERBOSE | re.DOTALL)



class DataClass(hero.DataClass):

    def get_version(self):
        """Returns game version."""
        return NAME


class Equipment(DataClass, hero.Equipment):
    __slots__ = {k: make_artifact_cast(k, version=NAME) for k in hero.Equipment.__slots__
                 if "side5" != k}


class ArmyStack(DataClass, hero.ArmyStack):   pass

class Army(DataClass, hero.Army):             pass

class Attributes(DataClass, hero.Attributes): pass

class Inventory(DataClass, hero.Inventory):   pass

class Skill(DataClass, hero.Skill):           pass

class Skills(DataClass, hero.Skills):         pass

class Spells(DataClass, hero.Spells):         pass



def init():
    """Adds Restoration of Erathia data to metadata stores."""
    EQUIPMENT_SLOTS = {k: v for k, v in metadata.EQUIPMENT_SLOTS.items() if "side5" != k}
    metadata.Store.add("equipment_slots", EQUIPMENT_SLOTS, version=NAME)


def adapt(name, value):
    """
    Adapts certain categories:

    - "hero.equipment.DATAPROPS":  dropping slot "side5"
    - "hero_byte_positions"        dropping slot "side5", shifting slot "inventory"
    - "hero_regex" :               dropping one slot from equipment to expect 18 items
    - all hero property classes:   returning version-specific data class, without slot "side5"
    """
    result = value
    if "hero.equipment.DATAPROPS" == name:
        result = [x for x in value if x.get("name") != "side5"]
    elif "hero_byte_positions" == name:
        result = value.copy()
        result["inventory"] = result.pop("side5")
        result.pop("reserved", None) # Combination artifacts reservations
    elif "hero_regex" == name:
        result = HERO_REGEX
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
    """Returns whether savefile bytes match Restoration of Erathia."""
    return savefile.match_byte_ranges(metadata.BYTE_POSITIONS, VERSION_BYTE_RANGES)
