# -*- coding: utf-8 -*-
"""
Main stats subplugin for hero-plugin, shows primary skills like attack-defense,
hero level, movement and experience and spell points, spellbook toggle,
and war machines.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   16.03.2020
@modified  10.01.2024
------------------------------------------------------------------------------
"""
import logging

import wx

from h3sed import gui
from h3sed import metadata
from h3sed import plugins
from h3sed.lib import util
from h3sed.plugins.hero import POS


logger = logging.getLogger(__package__)


PROPS = {"name": "stats", "label": "Main attributes", "index": 0}
## Valid raw values for primary stats range from 0..127.
## 100..127 is probably used as a buffer for artifact boosts;
## game will only show and use a maximum of 99.
## 128 or higher will cause overflow wraparound to 0.
UIPROPS = [{
    "name":   "attack",
    "label":  "Attack",
    "type":   "number",
    "len":    1,
    "min":    metadata.PrimaryAttributeRange[0],
    "max":    metadata.PrimaryAttributeRange[1],
}, {
    "name":   "defense",
    "label":  "Defense",
    "type":   "number",
    "len":    1,
    "min":    metadata.PrimaryAttributeRange[0],
    "max":    metadata.PrimaryAttributeRange[1],
}, {
    "name":   "power",
    "label":  "Spell Power",
    "type":   "number",
    "len":    1,
    "min":    metadata.PrimaryAttributeRange[0],
    "max":    metadata.PrimaryAttributeRange[1],
}, {
    "name":   "knowledge",
    "label":  "Knowledge",
    "type":   "number",
    "len":    1,
    "min":    metadata.PrimaryAttributeRange[0],
    "max":    metadata.PrimaryAttributeRange[1],
}, {
    "name":   "exp",
    "label":  "Experience",
    "type":   "number",
    "len":    4,
    "min":    0,
    "max":    2**32 - 1,
}, {
    "name":   "level",
    "label":  "Level",
    "type":   "number",
    "len":    1,
    "min":    0,
    "max":    2**8 - 1,
}, {
    "name":     "movement_total",
    "label":    "Movement points in total",
    "type":     "number",
    "len":      4,
    "min":      0,
    "max":      2**32 - 1,
    "readonly": True,
}, {
    "name":   "movement_left",
    "label":  "Movement points remaining",
    "type":   "number",
    "len":    4,
    "min":    0,
    "max":    2**32 - 1,
}, {
    "name":   "mana",
    "label":  "Spell points remaining",
    "type":   "number",
    "len":    2,
    "min":    0,
    "max":    2**16 - 1,
}, {
    "name":   "spellbook",
    "type":   "check",
    "label":  "Spellbook",
    "value":  None, # Populated later
}, {
    "name":   "ballista",
    "type":   "check",
    "label":  "Ballista",
    "value":  None,
}, {
    "name":   "ammo",
    "type":   "check",
    "label":  "Ammo Cart",
    "value":  None,
}, {
    "name":   "tent",
    "type":   "check",
    "label":  "First Aid Tent",
    "value":  None,
}]



def props():
    """Returns props for stats-tab, as {label, index}."""
    return PROPS


def factory(savefile, parent, panel):
    """Returns a new stats-plugin instance."""
    return StatsPlugin(savefile, parent, panel)



class StatsPlugin(object):
    """Encapsulates stats-plugin state and behaviour."""


    def __init__(self, savefile, parent, panel):
        self.name      = PROPS["name"]
        self.parent    = parent
        self._savefile = savefile
        self._hero     = None
        self._panel    = panel  # Plugin contents panel
        self._state    = {}     # {attack, defense, ..}


    def props(self):
        """Returns props for stats-tab, as [{type: "number", ..}]."""
        result = []
        IDS = metadata.Store.get("ids", self._savefile.version)
        for prop in UIPROPS:
            if "value" in prop: prop = dict(prop, value=IDS[prop["label"]])
            result.append(prop)
        return plugins.adapt(self, "props", result)


    def state(self):
        """Returns data state for stats-plugin, as {mana, exp, ..}."""
        return plugins.adapt(self, "state", self._state)


    def item(self):
        """Returns current hero."""
        return self._hero


    def load(self, hero, panel=None):
        """Loads hero to plugin."""
        self._hero = hero
        self._state.clear()
        if panel: self._panel = panel
        if hero:
            self._state.clear()
            self._state.update(self.parse([hero])[0])
            hero.stats = self._state
            hero.ensure_basestats()


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values. Returns whether state changed."""
        state0 = type(self._state)(self._state)
        for prop in self.props():
            if prop["name"] not in state:
                continue  # for
            v = state[prop["name"]]
            if "check" == prop["type"] and isinstance(v, bool):
                self._state[prop["name"]] = v
            elif "number" == prop["type"] and isinstance(v, int):
                self._state[prop["name"]] = min(prop["max"], max(prop["min"], v))
            else:
                logger.warning("Invalid stats item %r: %r", prop["name"], v)
        return state0 != self._state


    def on_change(self, prop, row, ctrl, value):
        """
        Handler for stats change, updates state, notifies other plugins if spellbook was toggled.
        Returns whether anything changed in stats.
        """
        v2, v1 = None if value == "" else value, self._state[prop["name"]]
        if v2 == v1: return False

        self._state[prop["name"]] = v2

        if prop["name"] in self._hero.basestats:
            self._hero.basestats[prop["name"]] += v2 - v1
        if "spellbook" == prop["name"]:
            evt = gui.PluginEvent(self._panel.Id, action="render", name="spells")
            wx.PostEvent(self._panel, evt)
        return True


    def parse(self, heroes):
        """Returns stats states parsed from hero bytearrays, as [{attack, defense, ..}, ]."""
        result = []
        NAMES = {x[y]: y for x in [metadata.Store.get("ids", self._savefile.version)]
                 for y in metadata.Store.get("special_artifacts", self._savefile.version)}
        MYPOS = plugins.adapt(self, "pos", POS)

        def parse_special(hero, pos):
            b, v = hero.bytes[pos:pos + 4], util.bytoi(hero.bytes[pos:pos + 4])
            return None if all(x == ord(metadata.Blank) for x in b) else v

        for hero in heroes:
            values = {}
            for prop in self.props():
                pos = MYPOS[prop["name"]]
                if "check" == prop["type"]:
                    v = parse_special(hero, pos) is not None
                elif "number" == prop["type"]:
                    v = util.bytoi(hero.bytes[pos:pos + prop["len"]])
                elif "combo" == prop["type"]:
                    v = NAMES.get(parse_special(hero, pos), "")
                values[prop["name"]] = v
            result.append(values)
        return result


    def serialize(self):
        """Returns new hero bytearray, with edited stats sections."""
        result = self._hero.bytes[:]

        IDS = metadata.Store.get("ids", self._savefile.version)
        MYPOS = plugins.adapt(self, "pos", POS)

        for prop in self.props():
            v, pos = self._state[prop["name"]], MYPOS[prop["name"]]
            if "check" == prop["type"]:
                b = (util.itoby(prop["value"], 4) if v else metadata.Blank * 4)
                b = b[:4] + result[pos + 4:pos + 8]
            elif "number" == prop["type"]: b = util.itoby(v, prop["len"])
            elif "combo" == prop["type"]:
                if v:
                    v = IDS.get(v)
                    if v is None:
                        logger.warning("Unknown stats %s value: %s.", prop["name"],
                                       self._state[prop["name"]])
                        continue # for prop
                    b = util.itoby(v, 4)[:4] + result[pos + 4:pos + 8]
                else: b = metadata.Blank * 4
            result[pos:pos + len(b)] = b

        return result
