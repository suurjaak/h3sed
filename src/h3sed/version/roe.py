# -*- coding: utf-8 -*-
"""
Subplugin for HOMM3 version "Restoration of Erathia".

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   22.05.2024
@modified  22.01.2026
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
    .                        #   1 byte:  player faction 0-7 or 255            000-000
    .{30}                    #  30 bytes: unknown                              001-031
    .{4}                     #   4 bytes: movement points in total             031-034
    .{4}                     #   4 bytes: movement points remaining            035-038
    .{4}                     #   4 bytes: experience                           039-042
    [\x00-\x1C][\x00]{3}     #   4 bytes: skill slots used                     043-046
    .{2}                     #   2 bytes: spell points remaining               047-048
    .{1}                     #   1 byte:  hero level                           049-049

    .{63}                    #  63 bytes: unknown                              050-112

    .{28}                    #  28 bytes: 7 4-byte creature IDs                113-150
    .{28}                    #  28 bytes: 7 4-byte creature counts             151-168

                             #  13 bytes: hero name, null-padded               169-181
    (?P<name>[^\x00-\x20].{11}\x00)
    [\x00-\x03]{28}          #  28 bytes: skill levels                         182-209
    [\x00-\x1C]{28}          #  28 bytes: skill slots                          210-237
    .{4}                     #   4 bytes: primary stats                        238-241

    [\x00-\x01]{70}          #  70 bytes: spells in book                       242-311
    [\x00-\x01]{70}          #  70 bytes: spells available                     312-381

                             # 144 bytes: 18 8-byte equipments worn            382-525
                             # Blank spots:   FF FF FF FF XY XY XY XY
                             # Artifacts:     XY 00 00 00 FF FF FF FF
                             # Scrolls:       XY 00 00 00 00 00 00 00
    (?P<equipment>(          # Catapult etc:  XY 00 00 00 XY XY 00 00
      (\xFF{4} .{4}) | (.\x00{3} (\x00{4} | \xFF{4})) | (.\x00{3}.{2}\x00{2})
    ){18})

                             # 512 bytes: 64 8-byte artifacts in inventory     526-1037
    ( ((.\x00{3}) | \xFF{4}){2} ){64}
""", re.VERBOSE | re.DOTALL)



class DataClass(hero.DataClass):

    version = property(lambda self: NAME, doc="Game version in use")


class Equipment(DataClass, hero.Equipment):
    __slots__ = {k: make_artifact_cast(k, version=NAME) for k in hero.Equipment.__slots__
                 if "side5" != k}


class ArmyStack(DataClass, hero.ArmyStack):   pass

class Army(DataClass, hero.Army):             pass

class Attributes(DataClass, hero.Attributes): pass

class Inventory(DataClass, hero.Inventory):   pass

class Profile(DataClass, hero.Profile):       pass

class Skill(DataClass, hero.Skill):           pass

class Skills(DataClass, hero.Skills):         pass

class Spells(DataClass, hero.Spells):         pass



def init():
    """Adds Restoration of Erathia data to metadata stores."""
    EQUIPMENT_SLOTS = {k: v for k, v in metadata.EQUIPMENT_SLOTS.items() if "side5" != k}
    metadata.Store.add("equipment_slots", EQUIPMENT_SLOTS, version=NAME)


def adapt(name, value, version=None):
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
    elif "hero.Profile" == name:
        result = Profile
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
