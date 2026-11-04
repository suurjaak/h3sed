# -*- coding: utf-8 -*-
"""
Resources subplugin for faction-plugin, manages faction resources like gold.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   02.11.2026
@modified  04.11.2026
------------------------------------------------------------------------------
"""
import logging

import h3sed
from .. lib import util
from .. import metadata


logger = logging.getLogger(__package__)


PROPS = {"name": "resources", "label": "Resources"}
DATAPROPS = [{
    "name":   "wood",
    "label":  "Wood",
    "type":   "number",
    "len":    4,
    "min":    metadata.DATA_RANGES["resource.wood"][0],
    "max":    metadata.DATA_RANGES["resource.wood"][1],
}, {
    "name":   "mercury",
    "label":  "Mercury",
    "type":   "number",
    "len":    4,
    "min":    metadata.DATA_RANGES["resource.mercury"][0],
    "max":    metadata.DATA_RANGES["resource.mercury"][1],
}, {
    "name":   "ore",
    "label":  "Ore",
    "type":   "number",
    "len":    4,
    "min":    metadata.DATA_RANGES["resource.ore"][0],
    "max":    metadata.DATA_RANGES["resource.ore"][1],
}, {
    "name":   "sulfur",
    "label":  "Sulfur",
    "type":   "number",
    "len":    4,
    "min":    metadata.DATA_RANGES["resource.sulfur"][0],
    "max":    metadata.DATA_RANGES["resource.sulfur"][1],
}, {
    "name":   "crystal",
    "label":  "Crystal",
    "type":   "number",
    "len":    4,
    "min":    metadata.DATA_RANGES["resource.crystal"][0],
    "max":    metadata.DATA_RANGES["resource.crystal"][1],
}, {
    "name":   "gems",
    "label":  "Gems",
    "type":   "number",
    "len":    4,
    "min":    metadata.DATA_RANGES["resource.gems"][0],
    "max":    metadata.DATA_RANGES["resource.gems"][1],
}, {
    "name":   "gold",
    "label":  "Gold",
    "type":   "number",
    "len":    4,
    "min":    metadata.DATA_RANGES["resource.gold"][0],
    "max":    metadata.DATA_RANGES["resource.gold"][1],
}, ]



def props():
    """Returns props for resources-tab, as {label, index}."""
    return PROPS


def factory(parent, panel, version):
    """Returns a new resources-plugin instance."""
    return ResourcesPlugin(parent, panel, version)



class ResourcesPlugin(object):
    """Provides UI functionality for listing and changing faction resources."""

    def __init__(self, parent, panel, version):
        self.name     = PROPS["name"]
        self.parent   = parent
        self.version  = version
        self._panel   = panel # Plugin contents panel
        self._state   = h3sed.faction.Resources.factory(version)
        self._faction = None


    def props(self):
        """Returns props for resources-tab, as [{type: "number", ..}]."""
        result = [dict(x) for x in DATAPROPS]
        return h3sed.version.adapt("faction.resources.DATAPROPS", result, version=self.version)


    def state(self):
        """Returns data state for resources-plugin, as {wood, mercury, ..}."""
        return self._state


    def item(self):
        """Returns current faction."""
        return self._faction


    def load(self, faction):
        """Loads faction to plugin."""
        self._faction = faction
        self._state = faction.resources


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values. Returns whether state changed."""
        state0 = self._state.copy()
        for name, value in state.items():
            if name not in self._state or self._state[name] == value: continue # for
            try: self._state[name] = value
            except Exception as e: logger.warning(str(e))
        return state0 != self._state



def parse(faction_bytes, version):
    """Returns h3sed.faction.Resources() parsed from faction bytearray resource sections."""
    BYTEPOS = h3sed.version.adapt("faction_byte_positions", metadata.FACTION_BYTE_POSITIONS,
                                  version=version)

    resources = h3sed.faction.Resources.factory(version)
    for prop in h3sed.version.adapt("faction.resources.DATAPROPS", DATAPROPS, version=version):
        pos = BYTEPOS["resource.%s" % prop["name"]]
        value = util.bytoi(faction_bytes[pos:pos + prop["len"]])
        resources[prop["name"]] = value
    return resources


def serialize(resources, faction_bytes, version):
    """Returns new faction bytearray with updated resource sections."""
    BYTEPOS = h3sed.version.adapt("faction_byte_positions", metadata.FACTION_BYTE_POSITIONS,
                                  version=version)

    new_bytes = faction_bytes[:]
    for prop in h3sed.version.adapt("faction.resources.DATAPROPS", DATAPROPS, version=version):
        pos = BYTEPOS["resource.%s" % prop["name"]]
        value = resources[prop["name"]]
        binary = util.itoby(value, prop["len"])
        new_bytes[pos:pos + len(binary)] = binary
    return new_bytes
