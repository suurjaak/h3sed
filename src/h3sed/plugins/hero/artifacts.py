# -*- coding: utf-8 -*-
"""
Artifacts subplugin for hero-plugin, shows artifact selection slots like helm etc.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   16.03.2020
@modified  23.05.2024
------------------------------------------------------------------------------
"""
from collections import defaultdict
import logging

import wx

from h3sed import conf
from h3sed import gui
from h3sed import metadata
from h3sed import plugins
from h3sed.lib import util
from h3sed.plugins.hero import POS


logger = logging.getLogger(__package__)


def format_stats(plugin, prop, state, artifact_stats=None):
    """Return item primaty stats modifer text like "+1 Attack, +1 Defense", or "" if no effect."""
    value = state.get(prop.get("name"))
    if not value: return ""
    STATS = artifact_stats or metadata.Store.get("artifact_stats", plugin._savefile.version)
    if value not in STATS: return ""
    return ", ".join("%s%s %s" % ("" if v < 0 else "+", v, k)
                     for k, v in zip(metadata.PrimaryAttributes.values(), STATS[value]) if v)


PROPS = {"name": "artifacts", "label": "Artifacts", "index": 3}
UIPROPS = [{
    "name":     "helm",
    "label":    "Helm slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None, # Populated later
    "info":     format_stats,
}, {
    "name":     "neck",
    "label":    "Neck slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "info":     format_stats,
}, {
    "name":     "armor",
    "label":    "Armor slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "info":     format_stats,
}, {
    "name":     "weapon",
    "label":    "Weapon slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "info":     format_stats,
}, {
    "name":     "shield",
    "label":    "Shield slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "info":     format_stats,
}, {
    "name":     "lefthand",
    "label":    "Left hand slot",
    "type":     "combo",
    "slot":     "hand",
    "nullable": True,
    "choices":  None,
    "info":     format_stats,
}, {
    "name":     "righthand",
    "label":    "Right hand slot",
    "type":     "combo",
    "slot":     "hand",
    "nullable": True,
    "choices":  None,
    "info":     format_stats,
}, {
    "name":     "cloak",
    "label":    "Cloak slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "info":     format_stats,
}, {
    "name":     "feet",
    "label":    "Feet slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "info":     format_stats,
}, {
    "name":     "side1",
    "label":    "Side slot 1",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
    "info":     format_stats,
}, {
    "name":     "side2",
    "label":    "Side slot 2",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
    "info":     format_stats,
}, {
    "name":     "side3",
    "label":    "Side slot 3",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
    "info":     format_stats,
}, {
    "name":     "side4",
    "label":    "Side slot 4",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
    "info":     format_stats,
}, {
    "name":     "side5",
    "label":    "Side slot 5",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
    "info":     format_stats,
}]



def props():
    """Returns props for artifacts-tab, as {label, index}."""
    return PROPS


def factory(savefile, parent, panel):
    """Returns a new artifacts-plugin instance."""
    return ArtifactsPlugin(savefile, parent, panel)



class ArtifactsPlugin(object):
    """Encapsulates artifacts-plugin state and behaviour."""


    def __init__(self, savefile, parent, panel):
        self.name      = PROPS["name"]
        self.parent    = parent
        self._savefile = savefile
        self._hero     = None
        self._panel    = panel  # Plugin contents panel
        self._state    = {}     # {"helm": "Skull Helmet", ..}
        self._ctrls    = {}     # {"helm": wx.ComboBox, "helm-info": wx.StaticText, }
        self._cache    = {}     # Cached {slot: [..all choices..], ..}


    def props(self):
        """Returns props for artifacts-tab, as [{type: "combo", ..}]."""
        result = []
        version = self._savefile.version
        for prop in UIPROPS:
            slot = prop.get("slot", prop["name"])
            result.append(dict(prop, choices=[""] + self._cache.get(slot, [])))
        return plugins.adapt(self, "props", result)


    def state(self):
        """Returns data state for artifacts-plugin, as {helm, ..}."""
        return self._state


    def item(self):
        """Returns current hero."""
        return self._hero


    def load(self, hero, panel):
        """Loads hero to plugin."""
        self._hero = hero
        self._state.clear()
        self._state.update(self.parse([hero])[0])
        hero.artifacts = self._state
        hero.ensure_basestats()
        if panel: self._panel = panel


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values."""
        state0 = type(self._state)(self._state)
        version = self._savefile.version

        for prop in self.props():  # First pass: don items
            name, slot = prop["name"], prop.get("slot", prop["name"])
            if name not in state:
                continue  # for
            v = state[name]
            cmap = {x.lower(): x for x in self._cache[slot]}

            if not v or hasattr(v, "lower") and v.lower() in cmap:
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
                self._state[name] = None

        result = (state0 != self._state)
        self._hero.artifacts = self._state
        if result: self._apply_artifact_stats()
        return result


    def render(self):
        """
        Populates controls from state, using existing if already built.
        
        Returns whether new controls were created.
        """
        result, version = False, self._savefile.version
        if self._ctrls and all(self._ctrls.values()):
            STATS = metadata.Store.get("artifact_stats", version)
            for prop in self.props():
                name, slot = prop["name"], prop.get("slot", prop["name"])
                cc = [""] + self._cache[slot]

                ctrl, value, choices = self._ctrls[name], self._state.get(name), cc
                if value and value not in choices: choices = [value] + cc
                if choices != ctrl.GetItems(): ctrl.SetItems(choices)
                ctrl.Value = value or ""
                self._ctrls["%s-info" % name].Label = format_stats(self, prop, self._state, STATS)
        else:
            self._ctrls, result = gui.build(self, self._panel), True
        self.update_slots()
        return result


    def update_slots(self):
        """Updates slots availability."""
        version = self._savefile.version
        slots_free, slots_owner = self._slots()
        SLOTS = metadata.Store.get("artifact_slots", version)
        self._panel.Freeze()
        try:
            for prop in self.props():
                name, slot = prop["name"], prop.get("slot", prop["name"])
                cc = [""] + self._cache[slot]

                ctrl, value = self._ctrls[name], self._state.get(name)

                if not ctrl.Enabled:
                    if value and value not in cc:
                        cc = [value] + cc
                    if cc != ctrl.GetItems(): ctrl.SetItems(cc)
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
        self._hero.artifacts = self._state
        if self._apply_artifact_stats():
            evt = gui.PluginEvent(self._panel.Id, action="render", name="stats")
            wx.PostEvent(self._panel, evt)
        self.update_slots()
        self._ctrls["%s-info" % prop["name"]].Label = format_stats(self, prop, self._state)
        return True


    def _apply_artifact_stats(self):
        """
        Applies current artifact stats to hero primary stats, returns whether anything changed.
        """
        result = False
        if not all(getattr(self._hero, k, None) for k in ("stats", "basestats")): return result

        STATS = metadata.Store.get("artifact_stats", self._savefile.version)
        MIN, MAX = metadata.PrimaryAttributeRange
        diff = [0] * len(metadata.PrimaryAttributes)
        for prop in self.props():
            item = self._state[prop["name"]]
            if item in STATS: diff = [a + b for a, b in zip(diff, STATS[item])]
        for k, v in zip(metadata.PrimaryAttributes, diff):
            v1, v2 = self._hero.stats[k], min(max(MIN, self._hero.basestats[k] + v), MAX)
            if v1 != v2: result, self._hero.stats[k] = True, v2
        return result


    def _slots(self, prop=None, value=None):
        """Returns free and taken slots as {"side": 4, }, {"helm": "Skull Helmet", }."""
        MYPROPS, SLOTS = self.props(), metadata.Store.get("artifact_slots", self._savefile.version)

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


    def parse(self, heroes):
        """Returns artifacts states parsed from hero bytearrays, as [{helm, ..}, ]."""
        result = []
        version = self._savefile.version
        slots = set(p.get("slot", p["name"]) for p in self.props()) | set(["inventory", "scroll"])
        self._cache = {slot: sorted(metadata.Store.get("artifacts", version, category=slot))
                       for slot in slots}
        IDS   = metadata.Store.get("ids", version)
        NAMES = {x[y]: y for x in [IDS] for y in self._cache["inventory"]}
        MYPOS = plugins.adapt(self, "pos", POS)

        def parse_item(hero, pos):
            b, v = hero.bytes[pos:pos + 4], util.bytoi(hero.bytes[pos:pos + 4])
            if all(x == ord(metadata.Blank) for x in b): return None # Blank
            return util.bytoi(hero.bytes[pos:pos + 8]) if v == IDS["Spell Scroll"] else v

        for hero in heroes:
            values = {}
            for prop in self.props():
                values[prop["name"]] = NAMES.get(parse_item(hero, MYPOS[prop["name"]]))
            result.append(values)
        return result


    def serialize(self):
        """Returns new hero bytearray, with edited artifacts section."""
        result = self._hero.bytes[:]
        bytes0 = self._hero.get_bytes(original=True)
        version = self._savefile.version

        IDS = {y: x[y] for x in [metadata.Store.get("ids", version)]
               for y in self._cache["inventory"]}
        SCROLL_ARTIFACTS = self._cache["scroll"]
        MYPOS = plugins.adapt(self, "pos", POS)
        SLOTS = metadata.Store.get("artifact_slots", version)
        HAS_COMBOS = bool(MYPOS.get("reserved"))

        if HAS_COMBOS:
            pos_reserved, len_reserved = min(MYPOS["reserved"].values()), len(MYPOS["reserved"])
            result[pos_reserved:pos_reserved + len_reserved] = [0] * len_reserved
            reserved_sets = set()  # [pos updated in combination artifact flags, ]

        state0 = self._hero.state0.get("artifacts") or {}
        for prop in self.props():
            name = self._state[prop["name"]]
            v, pos = IDS.get(name), MYPOS[prop["name"]]
            if name in SCROLL_ARTIFACTS:
                b = util.itoby(v, 8)
            elif v:
                b = util.itoby(v, 4) + metadata.Blank * 4
            elif not state0.get(prop["name"]):
                # Retain original bytes unchanged, as game uses both 0x00 and 0xFF
                b = bytes0[pos:pos + 8]
            else:
                b = metadata.Blank * 8
            result[pos:pos + len(b)] = b
            for slot in SLOTS.get(name, [])[1:] if HAS_COMBOS else ():
                result[MYPOS["reserved"][slot]] += 1
                reserved_sets.add(MYPOS["reserved"][slot])

        for pos in range(pos_reserved, pos_reserved + len_reserved) if HAS_COMBOS else ():
            if pos not in reserved_sets and bytes0[pos] > 5:
                # Retain original bytes unchanged, Horn of the Abyss uses them for unknown purpose.
                result[pos] = bytes0[pos]

        return result
