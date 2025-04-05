# -*- coding: utf-8 -*-
"""
Subplugin for HOMM3 version "Restoration of Erathia" in GOG Complete.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   22.05.2024
@modified  05.04.2025
------------------------------------------------------------------------------
"""
import re

from .. import metadata


NAME  = "roe_gog"
TITLE = "Restoration of Erathia (GOG Complete)"


"""Game major and minor version byte ranges, as (min, max)."""
VERSION_BYTE_RANGES = {
    "version_major":  (42, 42),
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
    (?P<artifacts>(          # Catapult etc:  XY 00 00 00 XY XY 00 00
      (\xFF{4} .{4}) | (.\x00{3} (\x00{4} | \xFF{4})) | (.\x00{3}.{2}\x00{2})
    ){18})
    .{8}                     # 8 bytes: side5 slot unused in RoE               494-502

                             # 512 bytes: 64 8-byte artifacts in backpack      503-1014
    ( ((.\x00{3}) | \xFF{4}){2} ){64}
""", re.VERBOSE | re.DOTALL)



def adapt(name, value):
    """
    Adapts certain categories:

    - "hero.artifacts.DATAPROPS":  dropping slot "side5"
    - "hero_byte_positions"        dropping slot "side5"
    - "hero_regex" :               dropping one slot from artifacts to expect 18 items
    """
    result = value
    if "hero.artifacts.DATAPROPS" == name:
        result = [x for x in value if x.get("name") != "side5"]
    elif "hero_regex" == name:
        result = HERO_REGEX
    elif "hero_byte_positions" == name:
        result = value.copy()
        result.pop("side5")
        result.pop("reserved", None) # Combination artifacts reservations
    return result


def detect(savefile):
    """Returns whether savefile bytes match Restoration of Erathia."""
    return savefile.match_byte_ranges(metadata.BYTE_POSITIONS, VERSION_BYTE_RANGES)
