# -*- coding: utf-8 -*-
"""
Profile subplugin for hero-plugin, parses hero background like player faction.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   22.01.2026
@modified  22.01.2026
------------------------------------------------------------------------------
"""
import h3sed
from .. import metadata


def parse(hero_bytes, version):
    """Returns h3sed.hero.Profile() parsed from hero bytearray."""
    BYTEPOS = h3sed.version.adapt("hero_byte_positions", metadata.HERO_BYTE_POSITIONS,
                                  version=version)

    profile = h3sed.hero.Profile.factory(version)
    profile.faction = hero_bytes[BYTEPOS["faction"]]
    return profile
