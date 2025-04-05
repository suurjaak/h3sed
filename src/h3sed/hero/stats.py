# -*- coding: utf-8 -*-
"""
Main stats subplugin for hero-plugin, shows primary skills like attack-defense,
hero level, movement and experience and spell points, spellbook toggle,
and war machines.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   16.03.2020
@modified  02.12.2024
------------------------------------------------------------------------------
"""
import functools
import logging
import sys

import wx

from h3sed import conf
from h3sed import gui
from h3sed import guibase
from h3sed import metadata
from h3sed import plugins
from h3sed.lib import util
from h3sed.plugins.hero import POS
from h3sed.plugins.hero.artifacts import UIPROPS as ARTIFACT_PROPS


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
    "info":   None,  # Populated later
}, {
    "name":   "defense",
    "label":  "Defense",
    "type":   "number",
    "len":    1,
    "min":    metadata.PrimaryAttributeRange[0],
    "max":    metadata.PrimaryAttributeRange[1],
    "info":   None,  # Populated later
}, {
    "name":   "power",
    "label":  "Spell Power",
    "type":   "number",
    "len":    1,
    "min":    metadata.PrimaryAttributeRange[0],
    "max":    metadata.PrimaryAttributeRange[1],
    "info":   None,  # Populated later
}, {
    "name":   "knowledge",
    "label":  "Knowledge",
    "type":   "number",
    "len":    1,
    "min":    metadata.PrimaryAttributeRange[0],
    "max":    metadata.PrimaryAttributeRange[1],
    "info":   None,  # Populated later
}, {
    "name":   "exp",
    "label":  "Experience",
    "type":   "number",
    "len":    4,
    "min":    0,
    "max":    2**31 - 1,
    "extra":  {
        "type":     "button",
        "label":    "Set from level",
        "tooltip":  "Recalculate experience points from hero level",
        "handler":  None,  # Populated later
    },
}, {
    "name":   "level",
    "label":  "Level",
    "type":   "number",
    "len":    1,
    "min":    0,
    "max":    max(metadata.ExperienceLevels),
    "extra":  {
        "type":     "button",
        "label":    "Set from experience",
        "tooltip":  "Recalculate level from hero experience points",
        "handler":  None,  # Populated later
    },
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
            if prop["name"] in metadata.PrimaryAttributes and prop.get("info", prop) is None:
                prop = dict(prop, info=self.format_stat_bonus)
            if prop["name"] in ("exp", "level") and "extra" in prop:
                prop = dict(prop, extra=dict(prop["extra"], handler=self.on_experience_level))
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


    def on_experience_level(self, plugin, prop, state, event=None):
        """Handler for "Set from level|experience" buttons, updates hero attribute."""
        EXP_LEVELS = plugins.adapt(self, "exp_levels", metadata.ExperienceLevels)
        SOURCE, TARGET = ("level", "exp") if "exp" == prop["name"] else ("exp", "level")
        source_prop = next(x for x in self.props() if x["name"] == SOURCE)
        exp, level = self._state["exp"], self._state["level"]
        value = None
        if "level" == TARGET:
            orderlist = sorted(EXP_LEVELS.items(), reverse=True)
            value = next((k for k, v in orderlist if v <= exp), None)
        elif "exp" == TARGET:
            value = EXP_LEVELS.get(level)
            if value is not None and value <= exp < EXP_LEVELS.get(level + 1, sys.maxsize):
                value = exp  # Do not reset experience if already at level
            elif value is None and level == 0:
                value = 0
        if value == self._state[TARGET]:
            guibase.status("%s already matching %s %s", prop["label"].capitalize(),
                           source_prop["label"].lower(), self._state[source_prop["name"]])
            value = None
        if value is None:
            return

        def on_do(self, state):
            self._state.update(state)
            self.parent.patch()
            evt = gui.PluginEvent(self._panel.Id, action="render", name=self.name)
            wx.PostEvent(self._panel, evt)
            return True
        label = "%s stats: %s %s" % (self._hero.name, TARGET, value)
        guibase.status("Setting %s from %s", label, source_prop["label"].lower(),
                       flash=conf.StatusShortFlashLength, log=True)
        callable = functools.partial(on_do, self, {TARGET: value})
        self.parent.command(callable, name="set %s" % label)


    def format_stat_bonus(self, plugin, prop, state, artifact_stats=None):
        """
        Return (text, tooltip) for primaty attribute bonuses or "" if no bonus,
        like ("base 3 +1 Armo.. +2 Cent..", "base 3\n+1 Armor of Wonder\n+2 Centaur's Axe").
        """
        if not getattr(self._hero, "artifacts", None): return
        MAXLEN = 65
        STATS = artifact_stats or metadata.Store.get("artifact_stats", plugin._savefile.version)
        IDX = list(metadata.PrimaryAttributes).index(prop["name"])
        base = self._hero.basestats[prop["name"]]
        artifacts = [self._hero.artifacts[x["name"]] for x in ARTIFACT_PROPS
                     if self._hero.artifacts.get(x["name"])]
        artifacts = [n for n in artifacts if n in STATS and STATS[n][IDX]]
        if not artifacts:
            return ""

        pairs = [(("%s" if v < 0 else "+%s") % v, k) for k in artifacts for v in [STATS[k][IDX]]]
        textpairs, toolpairs = ([(v, k[:i] + ".." if i else k) for v, k in pairs] for i in (4, 0))
        text    = "base %s %s"  % (base, " " .join(map(" ".join, textpairs)))
        tooltip = "base %s\n%s" % (base, "\n".join(map(" ".join, toolpairs)))
        if len(tooltip) <= MAXLEN: text = tooltip.replace("\n", " ")  # Show full text if fits
        if len(text) > MAXLEN + 4: text = text[:MAXLEN] + " ..."  # Shorten further if too long
        return text, tooltip


    def parse(self, heroes, original=False):
        """Returns stats states parsed from hero bytearrays, as [{attack, defense, ..}, ]."""
        result = []
        NAMES = {x[y]: y for x in [metadata.Store.get("ids", self._savefile.version)]
                 for y in metadata.Store.get("special_artifacts", self._savefile.version)}
        MYPOS = plugins.adapt(self, "pos", POS)

        def parse_special(hero_bytes, pos):
            b, v = hero_bytes[pos:pos + 4], util.bytoi(hero_bytes[pos:pos + 4])
            return None if all(x == ord(metadata.Blank) for x in b) else v

        for hero in heroes:
            values = {}
            hero_bytes = hero.get_bytes(original=True) if original else hero.bytes
            for prop in self.props():
                pos = MYPOS[prop["name"]]
                if "check" == prop["type"]:
                    v = parse_special(hero_bytes, pos) is not None
                elif "number" == prop["type"]:
                    v = util.bytoi(hero_bytes[pos:pos + prop["len"]])
                elif "combo" == prop["type"]:
                    v = NAMES.get(parse_special(hero_bytes, pos), "")
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
