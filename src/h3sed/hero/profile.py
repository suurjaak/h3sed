# -*- coding: utf-8 -*-
"""
Profile subplugin for hero-plugin, parses hero background like player faction.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   22.01.2026
@modified  13.07.2026
------------------------------------------------------------------------------
"""
import h3sed
from .. lib import util
from .. import metadata


def parse(hero_bytes, version, savefile=None, span=None):
    """Returns h3sed.hero.Profile() parsed from hero bytearray."""
    BYTEPOS = h3sed.version.adapt("hero_byte_positions", metadata.HERO_BYTE_POSITIONS,
                                  version=version)

    profile = h3sed.hero.Profile.factory(version)
    profile.faction = hero_bytes[BYTEPOS["faction"]]
    if not span or not savefile:
        return profile

    fixed_start, fixed_end = span
    ptr = fixed_start
    while savefile.raw[ptr - 1] != 0: # Move pointer to bio start if any
        ptr -= 1
    if ptr != fixed_start: # Has bio
        profile.biography = util.to_unicode(savefile.raw[ptr:fixed_start])
    if "neutral" == h3sed.hero.Profile.make_faction_text(profile.faction, version):
        return profile

    location = {}
    ptr += BYTEPOS["location"] # Shift pointer to coordinates start before unknown bytes
    COORD_LENGTHS = {"x": 2, "y": 2, "z": 1}
    for coord in "xyz":
        coord_bytes = savefile.raw[ptr:ptr + COORD_LENGTHS[coord]]
        if metadata.BLANK not in coord_bytes:
            location[coord] = util.bytoi(coord_bytes)
        ptr += COORD_LENGTHS[coord]
    if len(location) == len(COORD_LENGTHS):
        profile.update(location)

    return profile
