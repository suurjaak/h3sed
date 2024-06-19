# -*- coding: utf-8 -*-
"""
Subplugin for HOMM3 version "Armageddon's Blade".

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   22.05.2024
@modified  19.06.2024
------------------------------------------------------------------------------
"""
import logging
import re

from h3sed.lib import util
from h3sed.metadata import BytePositions, Store


logger = logging.getLogger(__package__)


PROPS = {"name": "ab", "label": "Armageddon's Blade", "index": 1}


"""Game major and minor version byte ranges, as (min, max)."""
VersionByteRanges = {
    "version_major":  (42, 42),
    "version_minor":  ( 1,  1),
}


"""Hero artifacts, for wearing and side slots, excluding spell scrolls."""
Artifacts = [
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
IDs = {
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
ArtifactSlots = {
    "Armageddon's Blade":                ["weapon"],
    "Vial of Dragon Blood":              ["side"],
}


"""Primary skill modifiers that artifacts give to hero."""
ArtifactStats = {
    "Armageddon's Blade":                (+3, +3, +3, +6),
}


"""Spells that artifacts make available to hero."""
ArtifactSpells = {
    "Armageddon's Blade":                ["Armageddon"],
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

                             # 144 bytes: 18 8-byte equipments worn            351-494
                             # Blank spots:   FF FF FF FF XY XY XY XY
                             # Artifacts:     XY 00 00 00 FF FF FF FF
                             # Scrolls:       XY 00 00 00 00 00 00 00
    (?P<artifacts>(          # Catapult etc:  XY 00 00 00 XY XY 00 00
      (\xFF{4} .{4}) | (.\x00{3} (\x00{4} | \xFF{4})) | (.\x00{3}.{2}\x00{2})
    ){18})

                             # 512 bytes: 64 8-byte artifacts in backpack      495-1006
    ( ((.\x00{3}) | \xFF{4}){2} ){64}
""", re.VERBOSE | re.DOTALL)


"""Hero pattern for RoE in newer releases like GOG Complete."""
RGX_HERO_NEWFORMAT = re.compile(b"""
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



def init():
    """Initializes artifacts and creatures for Armageddon's Blade."""
    Store.add("artifacts", Artifacts, version=PROPS["name"])
    Store.add("artifacts", Artifacts, version=PROPS["name"], category="inventory")
    for slot in set(sum(ArtifactSlots.values(), [])):
        Store.add("artifacts", [k for k, v in ArtifactSlots.items() if v[0] == slot],
                  version=PROPS["name"], category=slot)

    Store.add("artifact_slots",  ArtifactSlots,  version=PROPS["name"])
    Store.add("artifact_spells", ArtifactSpells, version=PROPS["name"])
    Store.add("artifact_stats",  ArtifactStats,  version=PROPS["name"])
    Store.add("creatures",       Creatures,      version=PROPS["name"])
    Store.add("ids",             IDs,            version=PROPS["name"])
    for artifact, spells in ArtifactSpells.items():
        Store.add("spells", spells, version=PROPS["name"], category=artifact)


def props():
    """Returns props as {label, index}."""
    return PROPS


def adapt(source, category, value):
    """
    Adapts certain categories:

    - "pos"   for hero sub-plugins: dropping slot "side5", shifting slot "inventory" if older format
    - "props" for artifacts-plugin: dropping slot "side5", dropping "reserved"
    - "regex" for hero-plugin:      dropping one slot from artifacts
    """
    root = util.get(source, "parent", default=source)
    savefile = getattr(root, "savefile", None)
    if not savefile or getattr(savefile, "version", None) != PROPS["name"]: return value
    is_new_format = getattr(savefile, "assume_newformat", False)

    result = value
    if "props" == category and "artifacts" == util.get(source, "name"):
        result = [x for x in value if x.get("name") != "side5"]
    elif "regex" == category and "hero" == util.get(source, "name"):
        # Replace hero regex with one expecting 18 artifact slots
        result = RGX_HERO_NEWFORMAT if is_new_format else RGX_HERO
    elif "pos" == category and "hero" == util.get(root, "name"):
        # Move inventory start to side5 position, drop side5 unless new format
        result = value.copy()
        if is_new_format: result.pop("side5")
        else: result["inventory"] = result.pop("side5")
        result.pop("reserved", None)
    return result


def detect(savefile):
    """Returns whether savefile bytes match Armageddon's Blade."""
    return savefile.match_byte_ranges(BytePositions, VersionByteRanges)
