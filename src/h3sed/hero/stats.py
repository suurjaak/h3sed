# -*- coding: utf-8 -*-
"""
Main stats subplugin for hero-plugin, shows primary skills like attack-defense,
hero level, movement and experience and spell points, spellbook toggle,
and war machines.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   16.03.2020
@modified  05.04.2025
------------------------------------------------------------------------------
"""
import functools
import logging

try: import wx
except ImportError: wx = None

import h3sed
from .. lib import util
from .. import conf
from .. import metadata


logger = logging.getLogger(__package__)


PROPS = {"name": "stats", "label": "Main attributes", "index": 0}
## Valid raw values for primary stats range from 0..127.
## 100..127 is probably used as a buffer for artifact boosts;
## game will only show and use a maximum of 99.
## 128 or higher will cause overflow wraparound to 0.
DATAPROPS = [{
    "name":   "attack",
    "label":  "Attack",
    "type":   "number",
    "len":    1,
    "min":    None,  # Populated later
    "max":    None,  # Populated later
    "info":   None,  # Populated later
}, {
    "name":   "defense",
    "label":  "Defense",
    "type":   "number",
    "len":    1,
    "min":    None,  # Populated later
    "max":    None,  # Populated later
    "info":   None,  # Populated later
}, {
    "name":   "power",
    "label":  "Spell Power",
    "type":   "number",
    "len":    1,
    "min":    None,  # Populated later
    "max":    None,  # Populated later
    "info":   None,  # Populated later
}, {
    "name":   "knowledge",
    "label":  "Knowledge",
    "type":   "number",
    "len":    1,
    "min":    None,  # Populated later
    "max":    None,  # Populated later
    "info":   None,  # Populated later
}, {
    "name":   "exp",
    "label":  "Experience",
    "type":   "number",
    "len":    4,
    "min":    None,  # Populated later
    "max":    None,  # Populated later
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
    "min":    None,  # Populated later
    "max":    None,  # Populated later
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
    "min":      None,  # Populated later
    "max":      None,  # Populated later
    "readonly": True,
}, {
    "name":   "movement_left",
    "label":  "Movement points remaining",
    "type":   "number",
    "len":    4,
    "min":    None,  # Populated later
    "max":    None,  # Populated later
}, {
    "name":   "mana_left",
    "label":  "Spell points remaining",
    "type":   "number",
    "len":    2,
    "min":    None,  # Populated later
    "max":    None,  # Populated later
}, {
    "name":   "spellbook",
    "type":   "check",
    "label":  "Spellbook",
    "value":  None, # Populated later
}, {
    "name":   "ballista",
    "type":   "check",
    "label":  "Ballista",
    "value":  None, # Populated later
}, {
    "name":   "ammo",
    "type":   "check",
    "label":  "Ammo Cart",
    "value":  None, # Populated later
}, {
    "name":   "tent",
    "type":   "check",
    "label":  "First Aid Tent",
    "value":  None, # Populated later
}]



def props():
    """Returns props for stats-tab, as {label, index}."""
    return PROPS


def factory(parent, panel, version):
    """Returns a new stats-plugin instance."""
    return StatsPlugin(parent, panel, version)



class StatsPlugin(object):
    """Provides UI functionality for listing and changing hero main attributes."""


    def __init__(self, parent, panel, version):
        self.name    = PROPS["name"]
        self.parent  = parent
        self.version = version
        self._panel  = panel # Plugin contents panel
        self._state  = h3sed.hero.Attributes.factory(version)
        self._hero   = None


    def props(self):
        """Returns props for stats-tab, as [{type: "number", ..}]."""
        result = []
        IDS = metadata.Store.get("ids", version=self.version)
        HERO_RANGES = metadata.Store.get("hero_ranges", version=self.version)
        for prop in DATAPROPS:
            if "value" in prop: prop = dict(prop, value=IDS[prop["label"]])
            if "min"   in prop: prop = dict(prop, min=HERO_RANGES[prop["name"]][0])
            if "max"   in prop: prop = dict(prop, max=HERO_RANGES[prop["name"]][1])
            if prop["name"] in metadata.PRIMARY_ATTRIBUTES and prop.get("info", prop) is None:
                prop = dict(prop, info=self.format_stat_bonus)
            if prop["name"] in ("exp", "level") and "extra" in prop:
                prop = dict(prop, extra=dict(prop["extra"], handler=self.on_experience_level))
            result.append(prop)
        return h3sed.version.adapt("hero.stats.DATAPROPS", result, version=self.version)


    def state(self):
        """Returns data state for stats-plugin, as {mana, exp, ..}."""
        return self._state


    def item(self):
        """Returns current hero."""
        return self._hero


    def load(self, hero):
        """Loads hero to plugin."""
        self._hero = hero
        self._state = hero.stats


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values. Returns whether state changed."""
        state0 = self._state.copy()
        for attribute, value in state.items():
            if attribute not in self._state or self._state[attribute] == value: continue # for
            try: self._state[attribute] = value
            except Exception as e: logger.warning(str(e))
        return state0 != self._state


    def on_change(self, prop, row, ctrl, value):
        """
        Handler for stats change, updates state, notifies other plugins if spellbook was toggled.
        Returns whether anything changed in stats.
        """
        v1, v2 = self._state[prop["name"]], None if value == "" else value
        if v1 == v2: return False

        self._state[prop["name"]] = v2

        if prop["name"] in self._hero.basestats:
            self._hero.basestats[prop["name"]] += v2 - v1
        if "spellbook" == prop["name"]:
            evt = h3sed.gui.PluginEvent(self._panel.Id, action="render", name="spells")
            wx.PostEvent(self._panel, evt)
        return True


    def on_experience_level(self, plugin, prop, state, event=None):
        """Handler for "Set from level|experience" buttons, updates hero attribute."""
        SOURCE, TARGET = ("level", "exp") if "exp" == prop["name"] else ("exp", "level")
        source_prop = next(x for x in self.props() if x["name"] == SOURCE)
        value = None
        if "level" == TARGET:
            value = self._state.get_experience_level()
        elif "exp" == TARGET:
            value = self._state.get_level_experience()
        if value == self._state[TARGET]:
            h3sed.guibase.status("%s already matching %s %s", prop["label"].capitalize(),
                                 source_prop["label"].lower(), self._state[source_prop["name"]])
            value = None
        if value is None:
            return

        def on_do(self, state):
            self._state.update(state)
            self.parent.patch()
            evt = h3sed.gui.PluginEvent(self._panel.Id, action="render", name=self.name)
            wx.PostEvent(self._panel, evt)
            return True
        label = "%s stats: %s %s" % (self._hero.name, TARGET, value)
        h3sed.guibase.status("Setting %s from %s", label, source_prop["label"].lower(),
                             flash=conf.StatusShortFlashLength, log=True)
        callable = functools.partial(on_do, self, {TARGET: value})
        self.parent.command(callable, name="set %s" % label)


    def format_stat_bonus(self, plugin, prop, state, artifact_stats=None):
        """
        Return (text, tooltip) for primaty attribute bonuses or "" if no bonus,
        like ("base 3 +1 Armo.. +2 Cent..", "base 3\n+1 Armor of Wonder\n+2 Centaur's Axe").
        """
        if not self._hero.equipment: return None
        MAXLEN = 65
        STATS = artifact_stats or metadata.Store.get("artifact_stats", version=self.version)
        INDEX = list(metadata.PRIMARY_ATTRIBUTES).index(prop["name"])
        base = self._hero.basestats[prop["name"]]
        artifacts = list(self._hero.equipment.values())
        artifacts = [n for n in artifacts if n in STATS and STATS[n][INDEX]]
        if not artifacts:
            return ""

        pairs = [(("%s" if v < 0 else "+%s") % v, k) for k in artifacts for v in [STATS[k][INDEX]]]
        textpairs, toolpairs = ([(v, k[:i] + ".." if i else k) for v, k in pairs] for i in (4, 0))
        text    = "base %s %s"  % (base, " " .join(map(" ".join, textpairs)))
        tooltip = "base %s\n%s" % (base, "\n".join(map(" ".join, toolpairs)))
        if len(tooltip) <= MAXLEN: text = tooltip.replace("\n", " ")  # Show full text if fits
        if len(text) > MAXLEN + 4: text = text[:MAXLEN] + " ..."  # Shorten further if too long
        return text, tooltip



def parse(hero_bytes, version):
    """Returns h3sed.hero.Attributes() parsed from hero bytearray attribute sections."""
    IDS = metadata.Store.get("ids", version=version)
    ID_TO_SPECIAL = {IDS[n]: n for n in metadata.Store.get("special_artifacts", version=version)}
    BYTEPOS = h3sed.version.adapt("hero_byte_positions", metadata.HERO_BYTE_POSITIONS,
                                  version=version)

    def parse_special(hero_bytes, pos):
        binary, integer = hero_bytes[pos:pos + 4], util.bytoi(hero_bytes[pos:pos + 4])
        if all(x == ord(metadata.BLANK) for x in binary): return None # Blank
        return integer

    attributes = h3sed.hero.Attributes.factory(version)
    for prop in h3sed.version.adapt("hero.stats.DATAPROPS", DATAPROPS):
        pos = BYTEPOS[prop["name"]]
        if "check" == prop["type"]:
            value = parse_special(hero_bytes, pos) is not None
        elif "number" == prop["type"]:
            value = util.bytoi(hero_bytes[pos:pos + prop["len"]])
        elif "combo" == prop["type"]:
            value = ID_TO_SPECIAL.get(parse_special(hero_bytes, pos), "")
        else:
            continue # for prop
        attributes[prop["name"]] = value
    return attributes


def serialize(attributes, hero_bytes, version, hero=None):
    """Returns new hero bytearray with updated attribute sections."""
    IDS = metadata.Store.get("ids", version=version)
    BYTEPOS = h3sed.version.adapt("hero_byte_positions", metadata.HERO_BYTE_POSITIONS,
                                  version=version)

    new_bytes = hero_bytes[:]
    for prop in h3sed.version.adapt("hero.stats.DATAPROPS", DATAPROPS):
        value, pos = attributes[prop["name"]], BYTEPOS[prop["name"]]
        if "check" == prop["type"]:
            binary = (util.itoby(IDS[prop["label"]], 4) if value else metadata.BLANK * 4)
            binary = binary[:4] + new_bytes[pos + 4:pos + 8]
        elif "number" == prop["type"]:
            binary = util.itoby(value, prop["len"])
        elif "combo" == prop["type"]:
            if value:
                value_id = IDS.get(value)
                if value_id is None:
                    logger.warning("Unknown stats %s value: %s.", prop["name"], value)
                    continue # for prop
                binary = util.itoby(value_id, 4)[:4] + new_bytes[pos + 4:pos + 8]
            else: binary = metadata.BLANK * 4
        new_bytes[pos:pos + len(binary)] = binary
    return new_bytes
