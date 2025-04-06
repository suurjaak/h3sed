# -*- coding: utf-8 -*-
"""
Inventory subplugin for hero-plugin, shows inventory artifacts list.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   16.03.2020
@modified  06.04.2025
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



PROPS = {"name": "inventory", "label": "Inventory", "index": 4}
DATAPROPS = [{
    "type":        "itemlist",
    "orderable":   True,
    "nullable":    True,
    "min":         None, # Populated later
    "max":         None, # Populated later
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


def factory(parent, panel, version):
    """Returns a new inventory-plugin instance."""
    return InventoryPlugin(parent, panel, version)



class InventoryPlugin(object):
    """Provides UI functionality for listing and changing artifacts in hero inventory."""


    def __init__(self, parent, panel, version):
        self.name    = PROPS["name"]
        self.parent  = parent
        self.version = version
        self._panel  = panel  # Plugin contents panel
        self._state  = h3sed.hero.Inventory.factory(version)
        self._hero   = None
        self._ctrls  = []  # [wx.ComboBox, ]


    def props(self):
        """Returns props for inventory-tab, as [{type: "itemlist", ..}]."""
        result = []
        MIN, MAX = metadata.Store.get("hero_ranges", version=self.version)["inventory"]
        CHOICES = sorted(metadata.Store.get("artifacts", category="inventory", version=self.version))
        for prop in DATAPROPS:
            myprop = dict(prop, item=[], min=MIN, max=MAX)
            for item in prop["item"]:
                if "choices" in item: item = dict(item, choices=CHOICES)
                myprop["item"].append(item)
            result.append(myprop)
        return result


    def state(self):
        """Returns data state for inventory-plugin, as ["Skull Helmet", None, ..]."""
        return self._state


    def item(self):
        """Returns current hero."""
        return self._hero


    def load(self, hero):
        """Loads hero to plugin."""
        self._hero = hero
        self._state = hero.inventory


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values. Returns whether state changed."""
        state0 = self._state.copy()
        self._state.clear()
        for i, artifact in enumerate(state[:len(self._state)]):
            try: self._state[i] = artifact
            except Exception as e: logger.warning(str(e))
        return state0 != self._state


    def on_compact_menu(self, event):
        """Handler for clicking the Compact button, opens popup menu."""
        menu = wx.Menu()
        item_current   = wx.MenuItem(menu, -1, "In &current order")
        item_name      = wx.MenuItem(menu, -1, "In &name order")
        item_slot_name = wx.MenuItem(menu, -1, "In &slot and name order")
        item_reverse   = wx.MenuItem(menu, -1, "In &reverse order")
        menu.Append(item_current)
        menu.Append(item_name)
        menu.Append(item_slot_name)
        menu.Append(item_reverse)
        menu.Bind(wx.EVT_MENU, lambda e: self.compact_items(),                 item_current)
        menu.Bind(wx.EVT_MENU, lambda e: self.compact_items(reverse=True),     item_reverse)
        menu.Bind(wx.EVT_MENU, lambda e: self.compact_items(["name"]),         item_name)
        menu.Bind(wx.EVT_MENU, lambda e: self.compact_items(["slot", "name"]), item_slot_name)
        event.EventObject.PopupMenu(menu, (0, event.EventObject.Size.Height))


    def compact_items(self, order=(), reverse=False):
        """Compacts inventory items to top, in specified order if any."""
        items = self._state.make_compact(order, reverse)
        if items == self._state:
            h3sed.guibase.status("No change from compacting inventory",
                                 flash=conf.StatusShortFlashLength)
            return

        def on_do(self, items):
            self._state[:] = items
            self.parent.patch()
            self.render()
            return True

        label = " and ".join(order) if order else "reverse" if reverse else "current"
        h3sed.guibase.status("Compacting inventory in %s order", label,
                             flash=conf.StatusShortFlashLength, log=True)
        callable = functools.partial(on_do, self, items)
        self.parent.command(callable, name="compact inventory in %s order" % label)


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
            self._ctrls = h3sed.gui.build(self, self._panel)[0]
            button = wx.Button(self._panel, label="Compact ..")
            button.Bind(wx.EVT_BUTTON, self.on_compact_menu)
            button.ToolTip = "Pack inventory artifacts to top"
            self._panel.Sizer.Add(button, border=20, flag=wx.TOP | wx.LEFT)
            self._panel.Sizer.AddStretchSpacer()
            self._panel.Layout()
            return True


def parse(hero_bytes, version):
    """Returns h3sed.hero.Inventory() parsed from hero bytearray inventory section."""
    HERO_RANGES = metadata.Store.get("hero_ranges", version=version)
    IDS = metadata.Store.get("ids", version=version)
    ARTIFACTS = metadata.Store.get("artifacts", category="inventory", version=version)
    ID_TO_NAME = {IDS[n]: n for n in ARTIFACTS}
    BYTEPOS = h3sed.version.adapt("hero_byte_positions", metadata.HERO_BYTE_POSITIONS,
                                  version=version)

    def parse_id(hero_bytes, pos):
        binary, integer = hero_bytes[pos:pos + 4], util.bytoi(hero_bytes[pos:pos + 4])
        if all(x == metadata.BLANK for x in binary): return None # Blank
        if integer == IDS["Spell Scroll"]: return util.bytoi(hero_bytes[pos:pos + 8])
        return integer

    inventory = h3sed.hero.Inventory.factory(version)
    for i in range(HERO_RANGES["inventory"][1]):
        artifact_id = parse_id(hero_bytes, BYTEPOS["inventory"] + i*8)
        inventory[i] = ID_TO_NAME.get(artifact_id)
    return inventory


def serialize(inventory, hero_bytes, version, hero=None):
    """Returns new hero bytearray with updated inventory section."""
    HERO_RANGES = metadata.Store.get("hero_ranges", version=version)
    IDS = metadata.Store.get("ids", version=version)
    SCROLL_ARTIFACTS = metadata.Store.get("artifacts", category="scroll", version=version)
    BYTEPOS = h3sed.version.adapt("hero_byte_positions", metadata.HERO_BYTE_POSITIONS,
                                  version=version)
    INVENTORY_POS = BYTEPOS["inventory"]

    new_bytes = hero_bytes[:]
    inventory0 = [] if hero is None else hero.original.get("inventory", [])
    for i in range(HERO_RANGES["inventory"][1]):
        artifact_name = inventory[i]
        artifact_id = IDS.get(artifact_name)
        if artifact_name in SCROLL_ARTIFACTS:
            binary = util.itoby(artifact_id, 8) # X0 00 00 00 00 00 00 00
        elif artifact_id:
            binary = util.itoby(artifact_id, 4) + metadata.BLANK * 4 # XY 00 00 00 FF FF FF FF
        elif i < len(inventory0) and not inventory0[i]:
            # Retain original bytes unchanged, as game uses both 0x00 and 0xFF
            binary = hero.bytes0[INVENTORY_POS + i * 8:INVENTORY_POS + (i + 1) * 8]
        else:
            binary = metadata.BLANK * 4 + metadata.NULL * 4 # 00 00 00 00 FF FF FF FF
        new_bytes[INVENTORY_POS + i * len(binary):INVENTORY_POS + (i + 1) * len(binary)] = binary

    return new_bytes
