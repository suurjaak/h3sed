# -*- coding: utf-8 -*-
"""
Main stats subplugin for hero-plugin, shows primary skills like attack-defense,
hero level, movement and experience and spell points, spellbook toggle,
and war machines.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   16.03.2020
@modified  04.10.2025
------------------------------------------------------------------------------
"""
import functools
import logging

try: import wx
except ImportError: wx = None

import h3sed
from .. lib import controls, util
from .. import conf
from .. import metadata


logger = logging.getLogger(__package__)


PROPS = {"name": "stats", "label": "Main attributes", "index": 0}
## Normal values for primary stats range from 0..99 for might and 1..99 for magic attributes.
## Values from 100 get capped to 99, and from 128 upwards become a handicap (from 231 in HoTA),
## with game showing and using minimum, but still increasing the value upon gaining points
## until it overflows and wraps around to actual minimum.
DATAPROPS = [{
    "name":   "attack",
    "label":  "Attack",
    "type":   "number",
    "len":    1,
    "min":    None,  # Populated later
    "max":    None,  # Populated later
    "extra":  None,  # Populated later
}, {
    "name":   "defense",
    "label":  "Defense",
    "type":   "number",
    "len":    1,
    "min":    None,  # Populated later
    "max":    None,  # Populated later
    "extra":  None,  # Populated later
}, {
    "name":   "power",
    "label":  "Spell Power",
    "type":   "number",
    "len":    1,
    "min":    None,  # Populated later
    "max":    None,  # Populated later
    "extra":  None,  # Populated later
}, {
    "name":   "knowledge",
    "label":  "Knowledge",
    "type":   "number",
    "len":    1,
    "min":    None,  # Populated later
    "max":    None,  # Populated later
    "extra":  None,  # Populated later
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
    "extra":  {
        "type":     "button",
        "label":    "Refill to total",
        "tooltip":  "Top up remaining movement points to hero total",
        "handler":  None,  # Populated later
    },
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
        self._ctrls  = {}    # {"helm": wx.ComboBox, "helm-info": wx.StaticText, }


    def props(self):
        """Returns props for stats-tab, as [{type: "number", ..}]."""
        result = []
        IDS = metadata.Store.get("ids", version=self.version)
        HERO_RANGES = metadata.Store.get("hero_ranges", version=self.version)
        for prop in DATAPROPS:
            if "value" in prop: prop = dict(prop, value=IDS[prop["label"]])
            if "min"   in prop: prop = dict(prop, min=HERO_RANGES[prop["name"]][0])
            if "max"   in prop: prop = dict(prop, max=HERO_RANGES[prop["name"]][1])
            if prop["name"] in metadata.PRIMARY_ATTRIBUTES and "extra" in prop:
                prop = dict(prop, extra=self.make_primary_extra)
            if prop["name"] in ("exp", "level") and "extra" in prop:
                prop = dict(prop, extra=dict(prop["extra"], handler=self.on_experience_level))
            if prop["name"] == "movement_left" and "extra" in prop:
                prop = dict(prop, extra=dict(prop["extra"], handler=self.on_refill_movement))
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


    def render(self):
        """Creates controls from state. Returns True."""
        self._ctrls.update(h3sed.gui.build(self, self._panel))
        return True


    def on_change(self, prop, value, ctrl, rowindex=None):
        """
        Handler for stats change, updates state, notifies other plugins if spellbook was toggled.
        Returns whether anything changed in stats.
        """
        v1, v2 = self._state[prop["name"]], None if value == "" else value
        if v1 == v2: return False

        if prop["name"] in metadata.PRIMARY_ATTRIBUTES:
            self.update_primary_attribute(prop, v2)
        else:
            self._state[prop["name"]] = v2
        if "spellbook" == prop["name"]:
            evt = h3sed.gui.PluginEvent(self._panel.Id, action="render", name="spells")
            wx.PostEvent(self._panel, evt)
        return True


    def on_experience_level(self, plugin, prop, state, event=None):
        """Handler for "Set from level|experience" buttons, updates hero attribute and propagates."""
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


    def on_refill_movement(self, plugin, prop, state, event=None):
        """Handler for setting hero movement points to total, updates attribute and propagates."""
        def on_do(self, state):
            self._state.update(state)
            self.parent.patch()
            evt = h3sed.gui.PluginEvent(self._panel.Id, action="render", name=self.name)
            wx.PostEvent(self._panel, evt)
            return True

        if self._state.movement_left >= self._state.movement_total: return
        label = "%s stats: refill movement points" % self._hero.name
        h3sed.guibase.status("Setting %s", label, flash=conf.StatusShortFlashLength, log=True)
        callable = functools.partial(on_do, self, {"movement_left": self._state.movement_total})
        self.parent.command(callable, name="set %s" % label)


    def make_primary_extra(self, prop):
        """Returns wx.Sizer with additional UI components for primary attribute."""
        GAME_RANGES = metadata.Store.get("primary_attribute_game_ranges", version=self.version)
        MINV, MAXV, OVERFLOW = GAME_RANGES[prop["name"]]

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        stat = wx.TextCtrl(self._panel, style=wx.TE_RIGHT)
        info = wx.StaticText(self._panel)
        stat.ToolTip = "Value shown and used in game.\n\n" \
                       "Values from %s display and function as %s, and from %s upwards " \
                       "become a handicap, keeping effective %s at %s.\n\n" \
                       "Gaining new points still increases the hidden value, " \
                       "until it overflows and wraps around to the actual minimum, " \
                       "after which it starts acting normally again." % \
                       (MAXV + 1, MAXV, OVERFLOW, metadata.PRIMARY_ATTRIBUTES[prop["name"]], MINV)
        stat.MinSize = stat.MaxSize = (25, -1)
        stat.SetEditable(False)
        controls.ColourManager.Manage(stat, "ForegroundColour", wx.SYS_COLOUR_GRAYTEXT)
        controls.ColourManager.Manage(info, "ForegroundColour", wx.SYS_COLOUR_GRAYTEXT)

        game_value = self._hero.gamestats[prop["name"]]
        infotext = infotip = self.format_stat_info(self, prop, self._state) or ""
        if isinstance(infotext, (list, tuple)): infotext, infotip = infotext
        stat.Value = str(game_value)
        info.Label, info.ToolTip = infotext, infotip
        stat.Show(game_value != self._state[prop["name"]])

        sizer.Add(stat)
        sizer.Add(info, border=5, flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL)
        self._ctrls["%s-game" % prop["name"]] = stat
        self._ctrls["%s-info" % prop["name"]] = info
        return sizer

    def update_primary_attribute(self, prop, value):
        """Refreshes  UI components for primary attribute in-game value and artifact bonus info."""
        self._hero.update_primary_attribute(prop["name"], value)
        infotext = infotip = self.format_stat_info(self, prop, self._state) or ""
        if isinstance(infotext, (list, tuple)): infotext, infotip = infotext
        stat, info = self._ctrls["%s-game" % prop["name"]], self._ctrls["%s-info" % prop["name"]]
        stat.Value = str(self._hero.gamestats[prop["name"]])
        stat.Show(self._hero.gamestats[prop["name"]] != self._state[prop["name"]])
        info.Label, info.ToolTip = infotext, infotip
        self._panel.Layout()


    def format_stat_info(self, plugin, prop, state, artifact_stats=None):
        """
        Return (text, tooltip) for primaty attribute bonuses and caps, or "" if no effects in play,
        like ("base 3 +1 Armo.. +2 Cent..", "base 3\n+1 Armor of Wonder\n+2 Centaur's Axe").
        """
        if not self._hero.equipment \
        and self._hero.stats[prop["name"]] == self._hero.gamestats[prop["name"]]: return ""

        MAXLEN = 65
        STATS = artifact_stats or metadata.Store.get("artifact_stats", version=self.version)
        GAME_RANGES = metadata.Store.get("primary_attribute_game_ranges", version=self.version)
        INDEX = list(metadata.PRIMARY_ATTRIBUTES).index(prop["name"])
        MINV, _, OVERFLOW = GAME_RANGES[prop["name"]]
        MAXRANGE = metadata.PRIMARY_ATTRIBUTE_RANGE[1] + 1
        base = self._hero.basestats[prop["name"]]
        if base >= OVERFLOW: base = base - MAXRANGE
        artifacts = list(self._hero.equipment.values())
        artifacts = [n for n in artifacts if n in STATS and STATS[n][INDEX]]

        captext = ""
        if self._hero.stats[prop["name"]] != self._hero.gamestats[prop["name"]]:
            action = "handicapped" if self._hero.gamestats[prop["name"]] == MINV else "capped"
            captext = "%s to %s" % (action, self._hero.gamestats[prop["name"]])

        if not artifacts and not captext:
            return ""

        pairs = [(("%s" if v < 0 else "+%s") % v, k) for k in artifacts for v in [STATS[k][INDEX]]]
        textpairs, toolpairs = ([(v, k[:i] + ".." if i else k) for v, k in pairs] for i in (4, 0))
        text = tooltip = "base %s" % base
        text    += " %s"  % " " .join(map(" ".join, textpairs)) if artifacts else ""
        tooltip += "\n%s" % "\n".join(map(" ".join, toolpairs)) if artifacts else ""
        if captext: text, tooltip = "%s %s" % (text, captext), "%s\n%s" % (tooltip, captext)
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
    for prop in h3sed.version.adapt("hero.stats.DATAPROPS", DATAPROPS, version=version):
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
    for prop in h3sed.version.adapt("hero.stats.DATAPROPS", DATAPROPS, version=version):
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
