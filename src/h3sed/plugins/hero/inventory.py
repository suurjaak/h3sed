# -*- coding: utf-8 -*-
"""
Inventory subplugin for hero-plugin, shows inventory artifacts list.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   16.03.2020
@modified  27.01.2024
------------------------------------------------------------------------------
"""
import logging

from h3sed import gui
from h3sed import metadata
from h3sed import plugins
from h3sed.lib import util
from h3sed.plugins.hero import POS


logger = logging.getLogger(__package__)



PROPS = {"name": "inventory", "label": "Inventory", "index": 4}
UIPROPS = [{
    "type":        "itemlist",
    "orderable":   True,
    "nullable":    True,
    "min":          0,
    "max":         64,
    "item": [{
        "type":    "label",
        "label":   "Inventory slot",
      }, {
        "type":    "combo",
        "choices": None, # Populated later
    }]
}]



def props():
    """Returns props for inventory-tab, as {label, index}."""
    return PROPS


def factory(savefile, parent, panel):
    """Returns a new inventory-plugin instance."""
    return InventoryPlugin(savefile, parent, panel)



class InventoryPlugin(object):
    """Encapsulates inventory-plugin state and behaviour."""


    def __init__(self, savefile, parent, panel):
        self.name      = PROPS["name"]
        self.parent    = parent
        self._savefile = savefile
        self._hero     = None
        self._panel    = panel  # Plugin contents panel
        self._state    = []     # ["Skull Helmet", None, ..]
        self._ctrls    = []     # [wx.ComboBox, ]


    def props(self):
        """Returns props for inventory-tab, as [{type: "itemlist", ..}]."""
        result = []
        cc = sorted(metadata.Store.get("artifacts", self._savefile.version, category="inventory"))
        for prop in UIPROPS:
            myprop = dict(prop, item=[])
            for item in prop["item"]:
                myitem = dict(item, choices=cc) if "choices" in item else item
                myprop["item"].append(myitem)
            result.append(myprop)
        return result


    def state(self):
        """Returns data state for inventory-plugin, as ["Skull Helmet", None, ..]."""
        return self._state


    def item(self):
        """Returns current hero."""
        return self._hero


    def load(self, hero, panel=None):
        """Loads hero to plugin."""
        self._hero = hero
        self._state[:] = self.parse([hero])[0]
        hero.inventory = self._state
        if panel: self._panel = panel


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values. Returns whether state changed."""
        state0 = type(self._state)(self._state)
        state = state + [None] * (self.props()[0]["max"] - len(state))
        version = self._savefile.version
        cmap = {x.lower(): x
                for x in metadata.Store.get("artifacts", version, category="inventory")}
        for i, v in enumerate(state):
            if v and hasattr(v, "lower") and v.lower() in cmap:
                self._state[i] = cmap[v.lower()]
            elif v in ("", None):
                self._state[i] = None
            else:
                logger.warning("Invalid inventory item #%s: %r", i + 1, v)
        return state0 != self._state


    def render(self):
        """
        Populates controls from state, using existing if already built.

        Returns whether new controls were created.
        """
        if self._ctrls and all(self._ctrls):
            for i, value in enumerate(self._state):
                self._ctrls[i].Value = value or ""
            return False
        else:
            self._ctrls = gui.build(self, self._panel)[0]
            return True


    def parse(self, heroes):
        """Returns inventory states parsed from hero bytearrays, as [[item or None, ..], ]."""
        result = []
        IDS   = metadata.Store.get("ids", self._savefile.version)
        NAMES = {x[y]: y for x in [IDS] for y in
                 metadata.Store.get("artifacts", self._savefile.version, category="inventory")}
        MYPOS = plugins.adapt(self, "pos", POS)

        def parse_item(hero, pos):
            b, v = hero.bytes[pos:pos + 4], util.bytoi(hero.bytes[pos:pos + 4])
            if all(x == metadata.Blank for x in b): return None # Blank
            return util.bytoi(hero.bytes[pos:pos + 8]) if v == IDS["Spell Scroll"] else v

        for hero in heroes:
            values = []
            for prop in self.props():
                for i in range(prop["max"]):
                    v = parse_item(hero, MYPOS["inventory"] + i*8)
                    values.append(NAMES.get(v))
            result.append(values)
        return result


    def serialize(self):
        """Returns new hero bytearray, with edited inventory section."""
        result = self._hero.bytes[:]
        bytes0 = self._hero.get_bytes(original=True)

        IDS = metadata.Store.get("ids", self._savefile.version)
        SCROLL_ARTIFACTS = metadata.Store.get("artifacts", self._savefile.version, category="scroll")
        MYPOS = plugins.adapt(self, "pos", POS)
        pos = MYPOS["inventory"]

        state0 = self._hero.state0.get("inventory") or []
        for prop in self.props():
            for i, name in enumerate(self._state) if "itemlist" == prop["type"] else ():
                v = IDS.get(name)
                if name in SCROLL_ARTIFACTS:
                    b = util.itoby(v, 8)
                elif v:
                    b = util.itoby(v, 4) + metadata.Blank * 4
                elif i < len(state0) and not state0[i]:
                    # Retain original bytes unchanged, as game uses both 0x00 and 0xFF
                    b = bytes0[pos + i * 8:pos + (i + 1) * 8]
                else:
                    b = metadata.Blank * 4 + metadata.Null * 4
                result[pos + i * len(b):pos + (i + 1) * len(b)] = b

        return result
