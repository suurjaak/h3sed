# -*- coding: utf-8 -*-
"""
Artifacts subplugin for hero-plugin, shows artifact selection slots like helm etc.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   16.03.2020
@modified  15.01.2022
------------------------------------------------------------------------------
"""
from collections import defaultdict
import logging

import wx

from h3sed import conf
from h3sed import data
from h3sed import gui
from h3sed import plugins
from h3sed.lib import util
from h3sed.plugins.hero import POS


logger = logging.getLogger(__package__)


PROPS = {"name": "artifacts", "label": "Artifacts", "index": 2}
UIPROPS = [{
    "name":     "helm",
    "label":    "Helm slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None, # Populated later
}, {
    "name":     "neck",
    "label":    "Neck slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
}, {
    "name":     "armor",
    "label":    "Armor slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
}, {
    "name":     "weapon",
    "label":    "Weapon slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
}, {
    "name":     "shield",
    "label":    "Shield slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
}, {
    "name":     "lefthand",
    "label":    "Left hand slot",
    "type":     "combo",
    "slot":     "hand",
    "nullable": True,
    "choices":  None,
}, {
    "name":     "righthand",
    "label":    "Right hand slot",
    "type":     "combo",
    "slot":     "hand",
    "nullable": True,
    "choices":  None,
}, {
    "name":     "cloak",
    "label":    "Cloak slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
}, {
    "name":     "feet",
    "label":    "Feet slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
}, {
    "name":     "side1",
    "label":    "Side slot 1",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
}, {
    "name":     "side2",
    "label":    "Side slot 2",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
}, {
    "name":     "side3",
    "label":    "Side slot 3",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
}, {
    "name":     "side4",
    "label":    "Side slot 4",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
}, {
    "name":     "side5",
    "label":    "Side slot 5",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
}]



def props():
    """Returns props for artifacts-tab, as {label, index}."""
    return PROPS


def factory(parent, hero, panel):
    """Returns a new artifacts-plugin instance."""
    return ArtifactsPlugin(parent, hero, panel)



class ArtifactsPlugin(object):
    """Encapsulates artifacts-plugin state and behaviour."""


    def __init__(self, parent, hero, panel):
        self.name    = PROPS["name"]
        self.parent  = parent
        self._hero   = hero
        self._panel  = panel # Plugin contents panel
        self._state  = {}    # {helm: "Skull Helmet", ..}
        self._ctrls  = {}    # {"head": wx.ComboBox, }
        if hero:
            self.parse(hero.bytes)
            hero.artifacts = self._state


    def props(self):
        """Returns props for artifacts-tab, as [{type: "combo", ..}]."""
        result = []
        ver = self._hero.savefile.version
        for prop in UIPROPS:
            slot = prop.get("slot", prop["name"])
            cc = [""] + sorted(data.Store.get("artifacts", version=ver, category=slot))
            result.append(dict(prop, choices=cc))
        return result


    def state(self):
        """Returns data state for artifacts-plugin, as {helm, ..}."""
        return self._state


    def load(self, hero, panel):
        """Loads hero to plugin."""
        self._hero = hero
        self._state.clear()
        if panel: self._panel = panel
        if hero:
            self.parse(hero.bytes)
            hero.artifacts = self._state


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values."""
        state0 = type(self._state)(self._state)
        ver = self._hero.savefile.version
        stats_diff = [0, 0, 0, 0]

        for prop in self.props():  # First pass: don items
            name, slot = prop["name"], prop.get("slot", prop["name"])
            if name not in state:
                continue  # for
            v = state[name]
            cmap = {x.lower(): x for x in data.Store.get("artifacts", version=ver, category=slot)}

            if not v or hasattr(v, "lower") and v.lower() in cmap:
                v0 = self._state[name]
                stats_diff = [a + b for a, b in zip(stats_diff, self._get_stats_diff(v0, v))]
                self._state[name] = v
            else:
                logger.warning("Invalid artifact for %r: %r", name, v)

        for prop in self.props():  # Second pass: validate slots and drop invalid states
            name, slot = prop["name"], prop.get("slot", prop["name"])
            v = self._state[name]
            if not v: continue  # for prop

            slots_free, slots_owner = self._slots(prop, v)
            slots_full = [k for k, x in slots_free.items() if x < 0]
            if slots_full:
                logger.warning("Cannot don %s, required slot taken:\n\n%s.",
                               v, "\n".join("- %s (by %s)" % (x, ", ".join(sorted(slots_owner[x])))
                                            for x in sorted(slots_full)))
                stats_diff = [a + b for a, b in zip(stats_diff, self._get_stats_diff(v, None))]
                self._state[name] = None

        self._apply_stats_diff(stats_diff)
        return state0 != self._state


    def render(self):
        """Populates controls from state, using existing if already built."""
        ver = self._hero.savefile.version
        if self._ctrls and all(self._ctrls.values()):
            for prop in self.props():
                name, slot = prop["name"], prop.get("slot", prop["name"])
                cc = [""] + sorted(data.Store.get("artifacts", version=ver, category=slot))

                ctrl, value, choices = self._ctrls[name], self._state.get(name), cc
                if value and value not in choices: choices = [value] + cc
                if choices != ctrl.GetItems(): ctrl.SetItems(choices)
                ctrl.Value = value or ""
        else:
            self._ctrls = gui.build(self, self._panel)
        self.update_slots()


    def update_slots(self):
        """Updates slots availability."""
        ver = self._hero.savefile.version
        slots_free, slots_owner = self._slots()
        SLOTS = data.Store.get("artifact_slots")
        self._panel.Freeze()
        try:
            for prop in self.props():
                name, slot = prop["name"], prop.get("slot", prop["name"])
                cc = [""] + sorted(data.Store.get("artifacts", version=ver, category=slot))

                ctrl, value = self._ctrls[name], self._state.get(name)

                if not ctrl.Enabled:
                    if value and value not in cc:
                        cc = [value] + cc
                    ctrl.SetItems(cc)
                    ctrl.Value = value or ""
                    ctrl.Enable()

                if not value and slot in slots_owner:
                    if slots_free.get(slot, 0):
                        slots_free[slot] -= 1
                    else:
                        owner = next(x for x in slots_owner[slot] if len(SLOTS[x]) > 1)
                        l = "<taken by %s>" % owner
                        ctrl.SetItems([l])
                        ctrl.Value = l
                        ctrl.Disable()
        finally: self._panel.Thaw()


    def on_change(self, prop, row, ctrl, value):
        """
        Handler for artifact slot change, updates state,
        and hero stats if old or new artifact affects primary skills.
        Rolls back change if lacking free slot due to a combination artifact.
        Returns whether action succeeded.
        """
        v2, v1 = value or None, self._state[prop["name"]]
        if v2 == v1: return False

        # Check whether combination artifacts leave sufficient slots free
        slots_free, slots_owner = self._slots(prop, v2)
        slots_full = [k for k, v in slots_free.items() if v < 0]
        if slots_full:
            wx.MessageBox("Cannot don %s, required slot taken:\n\n%s." %
                (v2, "\n".join("- %s (by %s)" % (x, ", ".join(sorted(slots_owner[x])))
                               for x in sorted(slots_full))),
                conf.Title, wx.OK | wx.ICON_WARNING
            )
            ctrl.Value = v1 or ""
            return False

        self._state[prop["name"]] = v2
        if self._apply_stats_diff(self._get_stats_diff(v1, v2)):
            evt = gui.PluginEvent(self._panel.Id, action="render", name="stats")
            wx.PostEvent(self._panel, evt)
        self.update_slots()
        return True


    def _get_stats_diff(self, item1, item2):
        """Returns change in hero stats from swapping item1 for item2, as [int, int, int, int]."""
        stats_diff = [0, 0, 0, 0]
        STATS = data.Store.get("artifact_stats")
        if item1 in STATS:
            stats_diff = [a - b for a, b in zip(stats_diff, STATS[item1])]
        if item2 in STATS:
            stats_diff = [a + b for a, b in zip(stats_diff, STATS[item2])]
        return stats_diff


    def _apply_stats_diff(self, stats_diff):
        """Apply change in hero main stats, returns whether anything was changed."""
        apply = any(stats_diff) and hasattr(self._hero, "stats")
        if apply:
            # Artifact bonuses like +2 Attack are kept in primary stats
            for n, v in zip(["attack", "defense", "power", "knowledge"], stats_diff):
                self._hero.stats[n] += v
                self._hero.stats[n] = min(max(0, self._hero.stats[n]), 127)
        return apply


    def _slots(self, prop=None, value=None):
        """Returns free and taken slots as {"side": 4, }, {"helm": "Skull Helmet", }."""
        MYPROPS, SLOTS = self.props(), data.Store.get("artifact_slots")

        # Check whether combination artifacts leave sufficient slots free
        slots_free, slots_owner = defaultdict(int), defaultdict(list)
        for myprop in MYPROPS:
            slots_free[myprop.get("slot", myprop["name"])] += 1
        for prop1 in MYPROPS:
            if prop and prop1["name"] == prop["name"]: continue # for prop
            v = self._state.get(prop1["name"])
            if not v: continue # for prop1
            for slot in SLOTS.get(v, ()):
                slots_free[slot] -= 1
                if v not in slots_owner[slot]: slots_owner[slot] += [v]
        if prop: slots_free[prop.get("slot", prop["name"])] -= 1
        for slot in SLOTS.get(value, ())[1:]: # First element is primary slot
            slots_free[slot] -= 1
        return slots_free, slots_owner


    def parse(self, bytes):
        """Builds artifacts list from hero bytearray, as {helm, ..}."""
        result = {}
        IDS   = data.Store.get("ids")
        NAMES = {x[y]: y for x in [IDS]
                 for y in data.Store.get("artifacts", category="inventory")}
        MYPOS = plugins.adapt(self, "pos", POS)

        def parse_item(pos):
            b, v = bytes[pos:pos + 4], util.bytoi(bytes[pos:pos + 4])
            if all(x == ord(data.Blank) for x in b): return None # Blank
            return util.bytoi(bytes[pos:pos + 8]) if v == IDS["Spell Scroll"] else v

        for prop in self.props():
            result[prop["name"]] = NAMES.get(parse_item(MYPOS[prop["name"]]))
        self._state.clear(); self._state.update(result)


    def serialize(self):
        """Returns new hero bytearray, with edited artifacts section."""
        result = self._hero.bytes[:]

        IDS = {y: x[y] for x in [data.Store.get("ids")]
               for y in data.Store.get("artifacts", category="inventory")}
        MYPOS = plugins.adapt(self, "pos", POS)
        SLOTS = data.Store.get("artifact_slots")

        pos_reserved, len_reserved = min(MYPOS["reserved"].values()), len(MYPOS["reserved"])
        result[pos_reserved:pos_reserved + len_reserved] = [0] * len_reserved

        for prop in self.props():
            name = self._state[prop["name"]]
            v, pos = IDS.get(name), MYPOS[prop["name"]]
            b = data.Blank * 8 if v is None else util.itoby(v, 4) + data.Blank * 4
            result[pos:pos + len(b)] = b
            for slot in SLOTS.get(name, [])[1:]:
                result[MYPOS["reserved"][slot]] += 1

        return result
