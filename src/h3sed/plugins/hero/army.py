# -*- coding: utf-8 -*-
"""
Army subplugin for hero-plugin, shows hero army creatures and counts.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   21.03.2020
@modified  27.01.2024
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


PROPS = {"name": "army", "label": "Army", "index": 2}
UIPROPS = [{
    "type":        "itemlist",
    "orderable":   True,
    "nullable":    True,
    "min":         1,
    "max":         7,
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
        "min":     1,
        "max":     2**32 - 1,
      }, {
        "name":    "placeholder",
        "type":    "window",
    }]
}]


def props():
    """Returns props for army-tab, as {label, index}."""
    return PROPS


def factory(savefile, parent, panel):
    """Returns a new army-plugin instance."""
    return ArmyPlugin(savefile, parent, panel)



class ArmyPlugin(object):
    """Encapsulates army-plugin state and behaviour."""


    def __init__(self, savefile, parent, panel):
        self.name      = PROPS["name"]
        self.parent    = parent
        self._savefile = savefile
        self._hero     = None
        self._panel    = panel  # Plugin contents panel
        self._state    = []     # [{"name": "Roc", "count": 6}, {}, ]
        self._ctrls    = []     # [{"name": wx.ComboBox, "count": wx.SpinCtrl}, ]


    def props(self):
        """Returns props for army-tab, as [{type: "itemlist", ..}]."""
        result = []
        cc = sorted(metadata.Store.get("creatures", self._savefile.version))
        for prop in UIPROPS:
            myprop = dict(prop, item=[])
            for item in prop["item"]:
                myitem = dict(item, choices=cc) if "choices" in item else item
                myprop["item"].append(myitem)
            result.append(myprop)
        return result


    def state(self):
        """Returns data state for army-plugin, as [{"name": "Roc", "count": 6}, {}, ]."""
        return self._state


    def item(self):
        """Returns current hero."""
        return self._hero


    def load(self, hero, panel=None):
        """Loads hero to plugin."""
        self._hero = hero
        self._state[:] = self.parse([hero])[0]
        hero.army = self._state
        if panel:
            panel.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.on_colour_change)
            self._panel = panel


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values. Returns whether state changed."""
        MYPROPS = self.props()
        state0 = type(self._state)(self._state)
        cmap = {x.lower(): x for x in metadata.Store.get("creatures", self._savefile.version)}
        countitem = next(x for x in MYPROPS[0]["item"] if "count" == x.get("name"))
        MIN, MAX = countitem["min"], countitem["max"]
        state = state + [{}] * (MYPROPS[0]["max"] - len(state))
        for i, v in enumerate(state[:MYPROPS[0]["max"]]):
            self._state[i] = {}
            if not isinstance(v, (dict, type(None))):
                logger.warning("Invalid data type in army #%s: %r", i + 1, v)
                continue  # for
            name, count = v and v.get("name"), v and v.get("count")
            if name and hasattr(name, "lower") and name.lower() in cmap \
            and isinstance(count, int) and MIN <= count <= MAX:
                self._state[i] = {"name": cmap[name.lower()], "count": count}
            elif v:
                logger.warning("Invalid army #%s: %r", i + 1, v)
        return state0 != self._state


    def render(self):
        """
        Populates controls from state, using existing if already built.

        Returns whether new controls were created.
        """
        result, MYPROPS = False, self.props()
        if self._ctrls and all(all(x.values()) for x in self._ctrls):
            cc = [""] + sorted(metadata.Store.get("creatures", self._savefile.version))
            for i, row in enumerate(self._state):
                creature = None
                for prop in MYPROPS[0]["item"]:
                    if "name" not in prop: continue # for prop
                    name, choices = prop["name"], cc
                    ctrl, value = self._ctrls[i][name], self._state[i].get(name)
                    if "choices" in prop:
                        choices = ([value] if value and value not in cc else []) + cc
                        if choices != ctrl.GetItems(): ctrl.SetItems(choices)
                        else: ctrl.Value = ""
                        creature = value
                    else: ctrl.Show(not creature if "window" == prop.get("type") else bool(creature))
                    if value is not None and hasattr(ctrl, "Value"): ctrl.Value = value
        else:
            self._ctrls, result = gui.build(self, self._panel)[0], True
            # Hide count controls where no creature type selected
            for i, row in enumerate(self._state):
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
            row[idx] = value
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
                if isinstance(c, wx.SpinCtrl) and not c.Shown: c.Show(), c.Hide()
            wx.CallAfter(lambda: self._panel and self._panel.Refresh())
        wx.CallLater(100, after)  # Hidden SpinCtrl arrows can become visible on colour change


    def parse(self, heroes):
        """Returns army states parsed from hero bytearrays, as [[{name, count} or {}, ], ]."""
        result = []
        NAMES = {x[y]: y for x in [metadata.Store.get("ids", self._savefile.version)]
                 for y in metadata.Store.get("creatures", self._savefile.version)}
        MYPOS = plugins.adapt(self, "pos", POS)

        for hero in heroes:
            values = []
            for prop in self.props():
                for i in range(prop["max"]):
                    unit, count = (util.bytoi(hero.bytes[MYPOS[k]  + i * 4:MYPOS[k]  + i * 4 + 4])
                                   for k in ("army_types", "army_counts"))
                    name = NAMES.get(unit)
                    if not unit or not count or not name: values.append({})
                    else: values.append({"name": name, "count": count})
            result.append(values)
        return result


    def serialize(self):
        """Returns new hero bytearray, with edited army section."""
        result = self._hero.bytes[:]
        bytes0 = self._hero.get_bytes(original=True)

        IDS = {y: x[y] for x in [metadata.Store.get("ids", self._savefile.version)]
               for y in metadata.Store.get("creatures", self._savefile.version)}
        MYPOS = plugins.adapt(self, "pos", POS)

        state0 = self._hero.state0.get("army") or []
        for prop in self.props():
            for i in range(prop["max"]):
                name, count = (self._state[i].get(x) for x in ("name", "count"))
                if (not name or not count) and i < len(state0) and not state0[i].get("name"):
                    # Retain original bytes unchanged, as game uses both 0x00 and 0xFF
                    b1 = bytes0[MYPOS["army_types"]  + i * 4:MYPOS["army_types"]  + i * 4 + 4]
                    b2 = bytes0[MYPOS["army_counts"] + i * 4:MYPOS["army_counts"] + i * 4 + 4]
                else:
                    b1, b2 = metadata.Blank * 4, metadata.Null * 4
                    if count and name in IDS:
                        b1 = util.itoby(IDS[name], 4)
                        b2 = util.itoby(count,     4)
                result[MYPOS["army_types"]  + i * 4:MYPOS["army_types"]  + i * 4 + 4] = b1
                result[MYPOS["army_counts"] + i * 4:MYPOS["army_counts"] + i * 4 + 4] = b2

        return result
