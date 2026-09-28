# -*- coding: utf-8 -*-
"""
Subplugin for HOMM3 version "Restoration of Erathia".

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   22.05.2024
@modified  28.09.2026
------------------------------------------------------------------------------
"""
import re

from .. import common
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


"""Allowed (min, max) ranges and other configuration for various hero and town properties."""
DATA_RANGES = {
    "town.bytelen":   (393, 393),
}


HERO_BYTE_POSITIONS = {
    "location":         -20, # Hero XYZ map coordinates start; not fixed (potential bio after)
    "on_map":           -14, # On the map, or garrison/inactive; not fixed (potential bio after)
}


"""Regulax expression for finding potential hero struct in savefile bytes."""
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

    .{28}                    #  28 bytes: 7 4-byte creature IDs                113-140
    .{28}                    #  28 bytes: 7 4-byte creature counts             141-168

                             #  13 bytes: hero name, null-padded               169-181
    (?P<name>[^\x00-\x20].{11}\x00)
    [\x00-\x03]{28}          #  28 bytes: skill levels                         182-209
    [\x00-\x1C]{28}          #  28 bytes: skill slots                          210-237
    .{4}                     #   4 bytes: primary stats                        238-241

    [\x00-\x01]{70}          #  70 bytes: spells in book                       242-311
    [\x00-\x01]{70}          #  70 bytes: spells available                     312-381

    (?P<equipment>(          # 144 bytes: 18 8-byte equipments worn            382-525
      (\xFF{4} .{4}) | (.\x00{3} .{4})
    ){18})

                             # 512 bytes: 64 8-byte artifacts in inventory     526-1037
    ( ((.\x00{3}) | \xFF{4}){2} ){64}
""", re.VERBOSE | re.DOTALL)


"""Regulax expression for finding potential town struct in savefile bytes."""
TOWN_REGEX = re.compile(b"""
    # Town name length is given in two bytes, but maximum length is actually 14

    (?P<faction>[\x00-\x07,\xFF])  #   1 byte:  town faction 0-7 or 255              000-000
    .{3}                           #   3 bytes: unknown                              001-003
    (?P<x>[\x00-\xFC])             #   1 byte:  X coordinate                         004-004
    (?P<y>[\x00-\xFC])             #   1 byte:  Y coordinate                         005-005
    (?P<z>[\x00-\x01])             #   1 byte:  Z coordinate                         006-006
    .{2}                           #   2 bytes: unknown                              007-008
    (?P<army_names>(               #  28 bytes: 7 4-byte creature IDs                009-036
      (.[\x00,\xFF]{3})
    ){7})
    (?P<army_counts>.{28})         #  28 bytes: 7 4-byte creature counts             037-064
    .{2}                           #   2 bytes: unknown                              065-066
    (?P<name_len>\x00\x00)         #   2 bytes: name length, always 0                067-068
    (?P<name>                      #   X bytes: name; 0-terminated or max 14         069-
      [^\x00-\x20,^\xFF][^\x00-\x1F,^\xFF]{0,13}
    )
                                   #   X bytes: unknown
""", re.VERBOSE | re.DOTALL)



class DataClass(common.DataClass):

    version = property(lambda self: NAME, doc="Game version in use")


class Equipment(DataClass, hero.Equipment):
    __slots__ = {k: make_artifact_cast(k, version=NAME) for k in hero.Equipment.__slots__
                 if "side5" != k}


class ArmyStack(DataClass, common.ArmyStack): pass

class Army(DataClass, common.Army):           pass

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
    metadata.Store.add("data_ranges",     DATA_RANGES,     version=NAME)


def adapt(name, value, version=None):
    """
    Adapts certain categories:

    - "hero.equipment.DATAPROPS":  dropping slot "side5"
    - "hero_byte_positions"        dropping slot "side5", shifting slot "inventory",
                                   adjusting location and map positions
    - "hero_regex" :               dropping one slot from equipment to expect 18 items
    - "town_regex" :               town name length set to zeroes
    - all hero property classes:   returning version-specific data class, without slot "side5"
    - common property classes:     returning version-specific army data class
    """
    result = value
    if "common.ArmyStack" == name:
        result = ArmyStack
    elif "common.Army" == name:
        result = Army
    elif "hero.equipment.DATAPROPS" == name:
        result = [x for x in value if x.get("name") != "side5"]
    elif "hero_byte_positions" == name:
        result = dict(value, **HERO_BYTE_POSITIONS)
        result["inventory"] = result.pop("side5")
        result.pop("reserved", None) # Combination artifacts reservations
    elif "hero_regex" == name:
        result = HERO_REGEX
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
    elif "town_regex" == name:
        result = TOWN_REGEX
    return result


def detect(savefile):
    """Returns whether savefile bytes match Restoration of Erathia."""
    return savefile.match_byte_ranges(metadata.BYTE_POSITIONS, VERSION_BYTE_RANGES)
