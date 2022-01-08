# -*- coding: utf-8 -*-
"""
Main stats subplugin for hero-plugin, shows primary skills like attack-defense,
hero level, movement and experience and spell points, spellbook toggle, 
and war machines.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   16.03.2020
@modified  12.04.2020
------------------------------------------------------------------------------
"""
import logging
import math

import wx

from h3sed import data
from h3sed import gui
from h3sed import plugins
from h3sed.lib import util
from h3sed.plugins.hero import POS


logger = logging.getLogger(__package__)


PROPS = {"name": "stats", "label": "Main attributes", "index": 0}
UIPROPS = [{
    "name":   "attack",
    "label":  "Attack",
    "type":   "number",
    "len":    1,
    "min":    0,
    "max":    99,
}, {
    "name":   "defense",
    "label":  "Defense",
    "type":   "number",
    "len":    1,
    "min":    0,
    "max":    99,
}, {
    "name":   "power",
    "label":  "Spell Power",
    "type":   "number",
    "len":    1,
    "min":    0,
    "max":    99,
}, {
    "name":   "knowledge",
    "label":  "Knowledge",
    "type":   "number",
    "len":    1,
    "min":    0,
    "max":    99,
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
    "name":   "movement_total",
    "label":  "Movement points in total",
    "type":   "number",
    "len":    4,
    "min":    0,
    "max":    2**32 - 1,
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


def factory(parent, hero, panel):
    """Returns a new stats-plugin instance."""
    return StatsPlugin(parent, hero, panel)



class StatsPlugin(object):
    """Encapsulates stats-plugin state and behaviour."""


    def __init__(self, parent, hero, panel):
        self.name    = PROPS["name"]
        self.parent  = parent
        self._hero   = hero
        self._panel  = panel # Plugin contents panel
        self._state  = {}    # {attack, defense, ..}
        if hero:
            self.parse(hero.bytes)
            hero.stats = self._state


    def props(self):
        """Returns props for stats-tab, as [{type: "number", ..}]."""
        result = []
        IDS = data.Store.get("ids")
        for prop in UIPROPS:
            if "value" in prop: prop = dict(prop, value=IDS[prop["label"]])
            result.append(prop)
        return plugins.adapt(self, "props", result)


    def state(self):
        """Returns data state for stats-plugin, as {mana, exp, ..}."""
        return plugins.adapt(self, "state", self._state)


    def load(self, hero, panel=None):
        """Loads hero to plugin."""
        self._hero = hero
        self._state.clear()
        if panel: self._panel = panel
        if hero:
            self.parse(hero.bytes)
            hero.stats = self._state


    def on_change(self, prop, row, ctrl, value):
        """
        Handler for artifact slot change, updates state,
        and hero stats if old or new artifact affects primary skills.
        Rolls back change if lacking free slot due to a combination artifact.
        Returns whether action succeeded.
        """
        v2, v1 = None if value == "" else value, self._state[prop["name"]]
        if v2 == v1: return False

        self._state[prop["name"]] = v2

        if "spellbook" == prop["name"]:
            evt = gui.PluginEvent(self._panel.Id, action="render", name="spells")
            wx.PostEvent(self._panel, evt)
        return True



    def parse(self, bytes):
        """Builds stats state from hero bytearray."""
        result = {}

        NAMES = {x[y]: y for x in [data.Store.get("ids")]
                 for y in data.Store.get("special_artifacts")}
        MYPOS = plugins.adapt(self, "pos", POS)

        def parse_special(pos):
            b, v = bytes[pos:pos + 4], util.bytoi(bytes[pos:pos + 4])
            return None if all(x == ord(data.Blank) for x in b) else v

        for prop in self.props():
            pos = MYPOS[prop["name"]]
            if "check" == prop["type"]:
                v = parse_special(pos) is not None
            elif "number" == prop["type"]:
                v = util.bytoi(bytes[pos:pos + prop["len"]])
            elif "combo" == prop["type"]:
                v = NAMES.get(parse_special(pos), "")
            result[prop["name"]] = v

        self._state.clear(); self._state.update(result)


    def serialize(self):
        """Returns new hero bytearray, with edited stats sections."""
        result = self._hero.bytes[:]

        IDS = data.Store.get("ids")
        MYPOS = plugins.adapt(self, "pos", POS)

        for prop in self.props():
            v, pos = self._state[prop["name"]], MYPOS[prop["name"]]
            if "check" == prop["type"]:
                b = (util.itoby(prop["value"], 4) if v else data.Blank * 4)
                b = b[:4] + result[pos + 4:pos + 8]
            elif "number" == prop["type"]: b = util.itoby(v, prop["len"])
            elif "combo" == prop["type"]:
                if v:
                    v = IDS.get(v)
                    if v is None:
                        logger.warn("Unknown stats %s value: %s.", prop["name"],
                                    self._state[prop["name"]])
                        continue # for prop
                    b = util.itoby(v, 4)[:4] + result[pos + 4:pos + 8]
                else: b = data.Blank * 4
            result[pos:pos + len(b)] = b

        #if result[:MYPOS["spells_available"]] != self._hero.bytes[:MYPOS["spells_available"]] \
        #or result[MYPOS["ballista"]:MYPOS["side5"]] != self._hero.bytes[MYPOS["ballista"]:MYPOS["side5"]]: # @todo remove
        #    logger.info("stats: changed. %s vs %s.", map(int, self._hero.bytes), map(int, result))

        return result
