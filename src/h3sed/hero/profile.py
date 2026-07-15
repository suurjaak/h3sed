# -*- coding: utf-8 -*-
"""
Profile subplugin for hero-plugin, parses hero background like player faction.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   22.01.2026
@modified  14.07.2026
------------------------------------------------------------------------------
"""
import h3sed
from .. lib import util
from .. lib.i18n import translate as __
from .. import metadata


PROPS = {"name": "profile", "label": "Profile", "index": 6}
DATAPROPS = [{
    "name":      "faction",
    "type":      "text",
    "label":     "Faction",
    "readonly":  True,
    "format":    None,  # Populated later
}, {
    "name":      "location",
    "type":      "text",
    "label":     "Location",
    "readonly":  True,
    "format":    None,  # Populated later
}, {
    "name":      "biography",
    "type":      "text",
    "label":     "Biography",
    "multiline": True,
    "readonly":  True,
}]


def props():
    """Returns props for profile-tab, as {label, index}."""
    return PROPS


def factory(parent, panel, version):
    """Returns a new profile-plugin instance."""
    return ProfilePlugin(parent, panel, version)



class ProfilePlugin(object):
    """Provides UI functionality for viewing hero profile data like biography."""


    def __init__(self, parent, panel, version):
        self.name    = PROPS["name"]
        self.parent  = parent
        self.version = version
        self._panel  = panel  # Plugin contents panel
        self._state  = h3sed.hero.Profile.factory(version)
        self._hero   = None


    def props(self):
        """Returns UI props for profile-tab, as [{type: "text", ..}]."""
        result = []
        for prop in DATAPROPS:
            if "faction" == prop["name"] and "format" in prop:
                prop = dict(prop, format=lambda: __(self._state.format_faction()))
            elif "location" == prop["name"] and "format" in prop:
                prop = dict(prop, format=self._state.format_location)
            result.append(prop)
        return result


    def state(self):
        """Returns data state for profile-plugin, as h3sed.hero.Profile."""
        return self._state


    def item(self):
        """Returns current hero."""
        return self._hero


    def load(self, hero):
        """Loads hero to plugin."""
        self._hero = hero
        self._state = hero.profile


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values. Returns whether state changed."""
        state0 = self._state.copy()
        self._state.clear()
        for attribute, value in state.items():
            if attribute in self._state:
                self._state[attribute] = value
        return state0 != self._state


def parse(hero_bytes, version, savefile=None, span=None):
    """Returns h3sed.hero.Profile() parsed from hero bytearray, and preceding bytes if available."""
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
    if "neutral" == profile.format_faction():
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
