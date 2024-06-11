# -*- coding: utf-8 -*-
"""
Subplugin for HOMM3 version "Restoration of Erathia".

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   22.05.2024
@modified  11.06.2024
------------------------------------------------------------------------------
"""
import logging
import re

from h3sed.lib import util
from h3sed.metadata import BytePositions


logger = logging.getLogger(__package__)


PROPS = {"name": "roe", "label": "Restoration of Erathia", "index": 0}


"""Game major and minor version byte ranges, as (min, max)."""
VersionByteRanges = {
    "version_major":  (16, 42),
    "version_minor":  ( 0,  0),
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
    [\x00-\x03]{28}          #  28 bytes: skill levels                         151-178
    [\x00-\x1C]{28}          #  28 bytes: skill slots                          179-206
    .{4}                     #   4 bytes: primary stats                        207-210

    [\x00-\x01]{70}          #  70 bytes: spells in book                       211-280
    [\x00-\x01]{70}          #  70 bytes: spells available                     281-350

                             # 148 bytes: 18 8-byte equipments worn            351-502
                             # Blank spots:   FF FF FF FF XY XY XY XY
                             # Artifacts:     XY 00 00 00 FF FF FF FF
                             # Scrolls:       XY 00 00 00 00 00 00 00
    (?P<artifacts>(          # Catapult etc:  XY 00 00 00 XY XY 00 00
      (\xFF{4} .{4}) | (.\x00{3} (\x00{4} | \xFF{4})) | (.\x00{3}.{2}\x00{2})
    ){18})

                             # 512 bytes: 64 8-byte artifacts in backpack      503-1014
    ( ((.\x00{3}) | \xFF{4}){2} ){64}
""", re.VERBOSE | re.DOTALL)



def props():
    """Returns props as {label, index}."""
    return PROPS


def adapt(source, category, value):
    """
    Adapts certain categories:

    - "pos"   for hero sub-plugins: dropping slot "side5", shifting slot "inventory"
    - "props" for artifacts-plugin: dropping slot "side5", dropping "reserved"
    - "regex" for hero-plugin:      dropping one slot from artifacts
    """
    root = util.get(source, "parent", default=source)
    if util.get(root, "savefile", "version") != PROPS["name"]: return value

    result = value
    if "props" == category and "artifacts" == util.get(source, "name"):
        result = [x for x in value if x.get("name") != "side5"]
    elif "regex" == category and "hero" == util.get(source, "name"):
        # Replace hero regex with one expecting 18 artifact slots
        result = RGX_HERO
    elif "pos" == category and "hero" == util.get(root, "name"):
        # Move inventory start to side5 position, drop side5
        result = value.copy()
        result["inventory"] = result.pop("side5")
        result.pop("reserved", None)
    return result


def detect(savefile):
    """Returns whether savefile bytes match Restoration of Erathia."""
    return savefile.match_byte_ranges(BytePositions, VersionByteRanges)
