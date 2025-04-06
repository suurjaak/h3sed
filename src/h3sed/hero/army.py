# -*- coding: utf-8 -*-
"""
Army subplugin for hero-plugin, shows hero army creatures and counts.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   21.03.2020
@modified  06.04.2025
------------------------------------------------------------------------------
"""
import logging

try: import wx
except ImportError: wx = None

import h3sed
from .. lib import util
from .. import metadata


logger = logging.getLogger(__package__)


PROPS = {"name": "army", "label": "Army", "index": 2}
DATAPROPS = [{
    "type":        "itemlist",
    "orderable":   True,
    "nullable":    True,
    "min":         None,  # Populated later
    "max":         None,  # Populated later
    "item": [{
        "type":    "label",
        "label":   "Army slot",
      }, {
        "name":    "name",
        "type":    "combo",
        "choices": None,  # Populated later
      }, {
        "name":    "count",
        "type":    "number",
        "min":     None,  # Populated later
        "max":     None,  # Populated later
      }, {
        "name":    "placeholder",
        "type":    "window",
    }]
}]


def props():
    """Returns props for army-tab, as {label, index}."""
    return PROPS


def factory(parent, panel, version):
    """Returns a new army-plugin instance."""
    return ArmyPlugin(parent, panel, version)



class ArmyPlugin(object):
    """Provides UI functionality for listing and changing hero army stacks."""


    def __init__(self, parent, panel, version):
        self.name    = PROPS["name"]
        self.parent  = parent
        self.version = version
        self._panel  = panel  # Plugin contents panel
        self._state  = h3sed.hero.Army.factory(version)
        self._hero   = None
        self._ctrls  = []  # [{"name": wx.ComboBox, "count": wx.SpinCtrlDouble}, ]

        panel.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.on_colour_change)


    def props(self):
        """Returns props for army-tab, as [{type: "itemlist", ..}]."""
        result = []
        HERO_RANGES = metadata.Store.get("hero_ranges", version=self.version)
        CHOICES = sorted(metadata.Store.get("creatures", version=self.version))
        for prop in DATAPROPS:
            myprop = dict(prop, item=[], min=HERO_RANGES["army"][0], max=HERO_RANGES["army"][1])
            for item in prop["item"]:
                if "choices" in item: item = dict(item, choices=CHOICES)
                if "min"     in item: item = dict(item, min=HERO_RANGES["army." + item["name"]][0])
                if "max"     in item: item = dict(item, max=HERO_RANGES["army." + item["name"]][1])
                myprop["item"].append(item)
            result.append(myprop)
        return result


    def state(self):
        """Returns data state for army-plugin, as [{"name": "Roc", "count": 6}, {}, ]."""
        return self._state


    def item(self):
        """Returns current hero."""
        return self._hero


    def load(self, hero):
        """Loads hero to plugin."""
        self._hero = hero
        self._state = hero.army


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values. Returns whether state changed."""
        state0 = self._state.copy()
        self._state.clear()
        for i, stack in enumerate(state[:len(self._state)]):
            if not isinstance(stack, (dict, type(None))):
                logger.warning("Invalid data type in army #%s: %r", i + 1, stack)
                continue  # for
            try: self._state[i].update(name=stack.get("name"), count=stack.get("count"))
            except Exception as e: logger.warning(e)
        return state0 != self._state


    def render(self):
        """
        Populates controls from state, using existing if already built.

        Returns whether new controls were created.
        """
        result, MYPROPS = False, self.props()
        if self._ctrls and all(all(x.values()) for x in self._ctrls): # All built and still valid
            CHOICES = [""] + sorted(metadata.Store.get("creatures", version=self.version))
            for i in range(len(self._state)):
                creature = None
                for prop in MYPROPS[0]["item"]:
                    if "name" not in prop: continue # for prop

                    name, choices = prop["name"], CHOICES
                    ctrl, value = self._ctrls[i][name], self._state[i].get(name)
                    if "choices" in prop:
                        choices = ([value] if value and value not in CHOICES else []) + CHOICES
                        if choices != ctrl.GetItems(): ctrl.SetItems(choices)
                        else: ctrl.Value = ""
                        creature = value
                    else: ctrl.Show(not creature if "window" == prop.get("type") else bool(creature))
                    if value is not None and hasattr(ctrl, "Value"): ctrl.Value = value
        else:
            self._ctrls, result = h3sed.gui.build(self, self._panel)[0], True
            # Hide count controls where no creature type selected
            for i in range(len(self._state)):
                creature, size = None, None
                for prop in MYPROPS[0]["item"]:
                    if "name" not in prop: continue # for prop

                    name = prop["name"]
                    ctrl, value = self._ctrls[i][name], self._state[i].get(name)
                    if "choices" in prop: creature = value
                    else:  # Show blank placeholder instead of count-control
                        if "window" == prop.get("type"): ctrl.Size = ctrl.MinSize = size
                        ctrl.Show(not creature if "window" == prop.get("type") else bool(creature))
                    size = ctrl.Size
        self._panel.Layout()
        return result


    def on_change(self, prop, row, ctrl, value):
        """
        Handler for army change, enables or disables creature count.
        Returns True.
        """
        ctrls = [x.Window for x in ctrl.ContainingSizer.Children]
        namectrl  = next(x for x in ctrls if isinstance(x, wx.ComboBox))
        countctrl = namectrl.GetNextSibling()
        placectrl = countctrl.GetNextSibling()
        if prop.get("nullable") and ctrl and "remove" == ctrl.Label:  # Clearing army slot
            idx = next(i for i, cc in enumerate(self._ctrls) if namectrl in cc.values())
            row[idx].clear()
            namectrl.Value = ""
            countctrl.Show(False)
            placectrl.Show(True)
            return True

        row[prop["name"]] = value
        if "name" == prop["name"]:
            if value and not row.get("count"):
                row["count"] = countctrl.Value = 1
            countctrl.Show(bool(value))
            placectrl.Show(not value)
        return True


    def on_colour_change(self, event):
        """Handler for system colour change, refreshes panel to clear any display issues."""
        event.Skip()
        def after():
            if not self._panel: return
            for c in self._panel.Children:
                if isinstance(c, (wx.SpinCtrl, wx.SpinCtrlDouble)) and not c.Shown:
                    c.Show(), c.Hide()
            wx.CallAfter(lambda: self._panel and self._panel.Refresh())
        wx.CallLater(100, after)  # Hidden SpinCtrl arrows can become visible on colour change


def parse(hero_bytes, version):
    """Returns h3sed.hero.Army() parsed from hero bytearray army section."""
    HERO_RANGES = metadata.Store.get("hero_ranges", version=version)
    IDS = metadata.Store.get("ids", version=version)
    ID_TO_NAME = {IDS[n]: n for n in metadata.Store.get("creatures", version=version)}
    BYTEPOS = h3sed.version.adapt("hero_byte_positions", metadata.HERO_BYTE_POSITIONS,
                                  version=version)
    NAMES_POS, COUNT_POS = BYTEPOS["army_types"], BYTEPOS["army_counts"]

    army = h3sed.hero.Army.factory(version)
    for i in range(HERO_RANGES["army"][1]):
        stack = h3sed.hero.ArmyStack.factory(version)
        creature_id = util.bytoi(hero_bytes[NAMES_POS + i*4:NAMES_POS + i*4 + 4])
        count       = util.bytoi(hero_bytes[COUNT_POS + i*4:COUNT_POS + i*4 + 4])
        if count and creature_id in ID_TO_NAME:
            stack.update(name=ID_TO_NAME[creature_id], count=count)
        army[i] = stack
    return army


def serialize(army, hero_bytes, version, hero=None):
    """Returns new hero bytearray with updated army section."""
    HERO_RANGES = metadata.Store.get("hero_ranges", version=version)
    IDS = metadata.Store.get("ids", version=version)
    NAME_TO_ID = {n: IDS[n] for n in metadata.Store.get("creatures", version=version)}
    BYTEPOS = h3sed.version.adapt("hero_byte_positions", metadata.HERO_BYTE_POSITIONS,
                                  version=version)
    NAMES_POS, COUNT_POS = BYTEPOS["army_types"], BYTEPOS["army_counts"]

    new_bytes = hero_bytes[:]
    army0 = [] if hero is None else hero.original.get("army", [])
    for i in range(HERO_RANGES["army"][1]):
        name, count = None, None
        if i < len(army) and army[i]: name, count = army[i]["name"], army[i]["count"]
        if (not name or not count) and i < len(army0) and not (army0[i] and army0[i].get("name")):
            # Retain original bytes unchanged, as game uses both 0x00 and 0xFF
            word1 = hero.bytes0[NAMES_POS + i*4:NAMES_POS + i*4 + 4]
            word2 = hero.bytes0[COUNT_POS + i*4:COUNT_POS + i*4 + 4]
        elif count and name in NAME_TO_ID:
            word1 = util.itoby(NAME_TO_ID[name], 4)
            word2 = util.itoby(count,  4)
        else:
            word1, word2 = metadata.BLANK * 4, metadata.NULL * 4
        new_bytes[NAMES_POS + i * 4:NAMES_POS + i * 4 + 4] = word1
        new_bytes[COUNT_POS + i * 4:COUNT_POS + i * 4 + 4] = word2

    return new_bytes
