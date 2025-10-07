# -*- coding: utf-8 -*-
"""
Inventory subplugin for hero-plugin, shows inventory artifacts list.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   16.03.2020
@modified  07.10.2025
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
    "menu":        None, # Populated later
    "info":        None, # Populated later
    "item": [{
        "type":    "label",
        "label":   "Inventory slot",
      }, {
        "type":    "combo",
        "choices": None, # Populated later
        "convert": None, # Populated later
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
        ARTIFACTS = metadata.Store.get("artifacts", category="inventory", version=self.version)
        def format_artifact(props, value, reverse=False):
            return h3sed.hero.format_artifacts(value, version=self.version, reverse=reverse)
        choices = h3sed.hero.format_artifacts(ARTIFACTS)
        for prop in DATAPROPS:
            myprop = dict(prop, item=[], min=MIN, max=MAX, menu=self.make_item_menu,
                          info=self.format_stats_bonus)
            for item in prop["item"]:
                if "choices" in item: item = dict(item, choices=choices)
                if "convert" in item: item = dict(item, convert=format_artifact)
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


    def render(self):
        """
        Populates controls from state, using existing if already built.

        Returns whether new controls were created.
        """
        if self._ctrls and all(self._ctrls):
            for i, value in enumerate(self._state):
                self._ctrls[i].Value = h3sed.hero.format_artifacts(value or "")
                sibling = self._ctrls[i].GetNextSibling()
                while sibling and not isinstance(sibling, wx.StaticText):
                    sibling = sibling.GetNextSibling()
                if isinstance(sibling, wx.StaticText):
                    sibling.Label = self.format_stats_bonus(DATAPROPS[0], i)
                    sibling.ToolTip = sibling.Label
            return False
        self._ctrls = h3sed.gui.build(self, self._panel)[0]
        return True


    def make_common_menu(self):
        """Returns wx.Menu with plugin-specific actions, like removing all inventory."""
        menu = wx.Menu()
        menu_compact = wx.Menu()
        item_clear = menu.Append(wx.ID_ANY, "Remove all inventory")
        item_send  = menu.Append(wx.ID_ANY, "Equip all possible inventory")
        item_swap  = menu.Append(wx.ID_ANY, "Swap all possible inventory with equipment")
        menu.AppendSubMenu(menu_compact,    "Compact inventory ..")
        item_current   = menu_compact.Append(wx.ID_ANY, "In &current order")
        item_name      = menu_compact.Append(wx.ID_ANY, "In &name order")
        item_slot_name = menu_compact.Append(wx.ID_ANY, "In &slot and name order")
        item_reverse   = menu_compact.Append(wx.ID_ANY, "In &reverse order")
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_all, swap=None),  item_clear)
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_all, swap=False), item_send)
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_all, swap=True),  item_swap)
        menu.Bind(wx.EVT_MENU, lambda e: self.compact_items(),                    item_current)
        menu.Bind(wx.EVT_MENU, lambda e: self.compact_items(reverse=True),        item_reverse)
        menu.Bind(wx.EVT_MENU, lambda e: self.compact_items(["name"]),            item_name)
        menu.Bind(wx.EVT_MENU, lambda e: self.compact_items(["slot", "name"]),    item_slot_name)
        return menu


    def make_item_menu(self, plugin, prop, rowindex):
        """Returms wx.Menu for inventory item options."""
        ARTIFACT_TO_SLOTS = metadata.Store.get("artifact_slots", version=self.version)
        COMBINATION_ARTIFACTS = metadata.Store.get("combination_artifacts", version=self.version)
        SCROLL_ARTIFACTS = metadata.Store.get("artifacts", category="scroll", version=self.version)
        LOCATION_TO_SLOT = metadata.Store.get("equipment_slots", version=self.version)
        SLOT_TO_LOCATIONS = {slot: [l for l, slot2 in LOCATION_TO_SLOT.items() if slot == slot2]
                             for slot in LOCATION_TO_SLOT.values()}
        COMBINATION_COMPONENTS = {b: a for a, bb in COMBINATION_ARTIFACTS.items() for b in bb}
        artifact_on_row = self._state[rowindex]

        menu = wx.Menu()
        menu_equip = wx.Menu()
        menu_set   = wx.Menu()
        menu_swap  = wx.Menu()
        menu_move  = wx.Menu()
        item_set   = menu.AppendSubMenu(menu_set,   "Set artifact by category ..")
        item_equip = menu.AppendSubMenu(menu_equip, "Swap with equipment slot ..")

        if artifact_on_row in COMBINATION_ARTIFACTS:
            item_combo = menu.Append(wx.ID_ANY, "Disassemble combination artifact")
            kwargs = dict(rowindex=rowindex)
            menu.Bind(wx.EVT_MENU, functools.partial(self.on_combo_artifact, **kwargs), item_combo)
        elif artifact_on_row in COMBINATION_COMPONENTS:
            components = COMBINATION_ARTIFACTS[COMBINATION_COMPONENTS[artifact_on_row]]
            if all(x in self._state for x in components):
                menu_combo = wx.Menu()
                menu.AppendSubMenu(menu_combo, "Assemble combination artifact")
                item = menu_combo.Append(wx.ID_ANY, COMBINATION_COMPONENTS[artifact_on_row])
                kwargs = dict(rowindex=rowindex)
                menu.Bind(wx.EVT_MENU, functools.partial(self.on_combo_artifact, **kwargs), item)

        menu.AppendSeparator()
        item_blank = menu.Append(wx.ID_ANY, "Insert blank")
        item_drop  = menu.Append(wx.ID_ANY, "Remove row")
        item_move  = menu.AppendSubMenu(menu_move,  "Move to inventory ..")
        item_swap  = menu.AppendSubMenu(menu_swap,  "Swap with inventory slot ..")

        for category in list(SLOT_TO_LOCATIONS) + ["scroll", "inventory", "combined"]:
            candidates = metadata.Store.get("artifacts", category=category, version=self.version)
            if "inventory" == category:
                candidates = [x for x in candidates
                              if ARTIFACT_TO_SLOTS.get(x, [])[:1] == ["inventory"]]
            elif "side" == category:
                candidates = [x for x in candidates if x not in SCROLL_ARTIFACTS]
            elif "combined" == category:
                candidates = sorted(COMBINATION_ARTIFACTS)
            if not candidates: continue # for category

            menu_category = wx.Menu()
            item_category = wx.MenuItem(menu_set, wx.ID_ANY, category, subMenu=menu_category)
            if artifact_on_row in ARTIFACT_TO_SLOTS:
                if ARTIFACT_TO_SLOTS[artifact_on_row][0] == category \
                or "scroll" == category and artifact_on_row in SCROLL_ARTIFACTS \
                or "combined" == category and artifact_on_row in COMBINATION_ARTIFACTS:
                    item_category.Font = item_category.Font.Bold()
            menu_set.Append(item_category)
            for artifact_candidate in candidates:
                label = h3sed.hero.format_artifacts(artifact_candidate)
                item_candidate = wx.MenuItem(menu_category, wx.ID_ANY, label)
                if artifact_candidate == artifact_on_row:
                    item_candidate.Font = item_candidate.Font.Bold()
                menu_category.Append(item_candidate)
                kwargs = dict(rowindex=rowindex, artifact=artifact_candidate)
                menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_row, **kwargs), item_candidate)

        reserved_locations = self._hero.equipment.get_reserved_locations()
        candidate_locations = []
        if artifact_on_row in ARTIFACT_TO_SLOTS:
            candidate_locations = SLOT_TO_LOCATIONS.get(ARTIFACT_TO_SLOTS[artifact_on_row][0], [])
        elif artifact_on_row is None:
            candidate_locations = list(self._hero.equipment)
        for location in candidate_locations:
            if location not in self._hero.equipment: continue # for location
            artifact_equipped = self._hero.equipment[location]
            if artifact_equipped is None and location in reserved_locations:
                label = "<taken by %s>" % self._hero.equipment[reserved_locations[location]]
            elif artifact_equipped is None: label = "<blank>"
            else: label = h3sed.hero.format_artifacts(artifact_equipped)
            item_location = menu_equip.Append(wx.ID_ANY, "%s:\t%s" % (location, label))
            kwargs = dict(rowindex=rowindex, location=location)
            menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_row, **kwargs), item_location)

        for direction, label in [(-1, "top"), (1, "bottom")]:
            item = menu_move.Append(wx.ID_ANY, label)
            kwargs = dict(rowindex=rowindex, direction=direction)
            menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_row, **kwargs), item)

        for i, artifact in enumerate(self._state):
            label = h3sed.hero.format_artifacts(artifact) or "<blank>"
            item_slot = menu_swap.Append(wx.ID_ANY, "%s:\t%s" % (i + 1, label))
            kwargs = dict(rowindex=rowindex, rowindex2=i)
            menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_row, **kwargs), item_slot)
            if i == rowindex:
                menu_swap.Enable(item_slot.Id, False)

        if not menu_set.MenuItemCount:
            menu.Enable(item_set.Id, False)
        if not menu_equip.MenuItemCount:
            menu.Enable(item_equip.Id, False)
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_row, rowindex=rowindex), item_blank)
        kwargs = dict(rowindex=rowindex, delete=True)
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_row, **kwargs), item_drop)
        return menu


    def format_stats_bonus(self, prop, rowindex):
        """Returns item primaty stats modifier text like "+1 Attack, +1 Defense", or "" if no effect."""
        artifact = self._state[rowindex]
        if not artifact: return ""
        STATS = metadata.Store.get("artifact_stats", version=self.version)
        if artifact not in STATS: return ""
        return ", ".join("%s%s %s" % ("" if v < 0 else "+", v, k)
                         for k, v in zip(metadata.PRIMARY_ATTRIBUTES.values(), STATS[artifact]) if v)


    def change_artifacts(self, inventory, equipment=None):
        """Carries out change of inventory and equipment, propagates change to hero and savefile."""
        changes = {} # {property name: whether changed from action}
        if inventory != self._state:
            self._state[:], changes["inventory"] = inventory, True
        if equipment is not None and equipment != self._hero.equipment:
            self._hero.equipment.update(equipment), changes.update(equipment=True, stats=True)
        self._hero.realize()
        if not any(changes.values()): return True
        self.parent.patch()
        for name in (name for name, changed in changes.items() if changed):
            evt = h3sed.gui.PluginEvent(self._panel.Id, action="render", name=name)
            wx.PostEvent(self._panel, evt)
        return True


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


    def on_change(self, prop, value, ctrl, rowindex):
        """
        Handler for equipment slot change, updates state, returns whether action succeeded.

        Rolls back change if lacking free slot due to a combination artifact.
        """
        self._state[rowindex] = value
        sibling = ctrl.GetNextSibling()
        while sibling and not isinstance(sibling, wx.StaticText): sibling = sibling.GetNextSibling()
        if isinstance(sibling, wx.StaticText):
            sibling.Label = self.format_stats_bonus(prop, rowindex)
            sibling.ToolTip = sibling.Label
        return True


    def on_change_all(self, event, swap):
        """
        Handler for removing or donning or swapping all inventory, carries out and propagates change.

        @param   swap  None to remove all, False to send to equipment, True to swap with equipment
        """
        if not any(self._state):
            return
        acting, action = ("Swapping", "swap") if swap else ("Removing", "remove") if swap is None \
                         else ("Equipping", "equip")
        if swap:
            eq2, inv2 = self._hero.make_equipment_swap()
        elif swap is None:
            eq2, inv2 = None, h3sed.hero.Inventory.factory(self.version)
        else:
            eq2, inv2 = self._hero.make_artifacts_transfer(to_inventory=False)
        if inv2 == self._state and eq2 in (None, self._hero.equipment):
            h3sed.guibase.status("No change from %s all inventory" % acting.lower(),
                                 flash=conf.StatusShortFlashLength, log=True)
            return
        label = "change %s inventory: %s all" % (self._hero.name, action)
        h3sed.guibase.status("%s all inventory" % acting, flash=conf.StatusShortFlashLength, log=True)
        callable = functools.partial(self.change_artifacts, inv2, eq2)
        self.parent.command(callable, name=label)


    def on_change_row(self, event, rowindex,
                      rowindex2=None, artifact=None, location=None, direction=None, delete=False):
        """
        Handler for inventory item options menu, carries out and propagates change.

        @param   rowindex   index of inventory item operated on
        @param   rowindex2  index of inventory item to swap with
        @param   artifact   artifact to change inventory item to; None will insert blank instead
        @param   location   equipment location to swap out for current inventory item
        @param   direction  -1 to move to inventory top, +1 to move to inventory bottom
        @param   delete     whether to delete inventory row instead
        """
        if location is not None:
            try: eq2, inv2 = self._hero.make_artifact_swap(location, rowindex)
            except Exception as e:
                wx.MessageBox(str(e), conf.Title, wx.OK | wx.ICON_WARNING)
                return
            action, detail = "change", "swap with equipment %s" % location
        elif rowindex2 is not None:
            eq2, inv2 = None, self._state.copy()
            inv2[rowindex], inv2[rowindex2] = inv2[rowindex2], inv2[rowindex]
            action, detail = "change", "swap with slot %s" % (rowindex2 + 1)
        elif direction:
            eq2, inv2 = None, self._state.copy()
            current_value = inv2[rowindex]
            inv2.pop(rowindex)
            if direction > 0:
                lastindex = next((len(inv2) - i for i, x in enumerate(inv2[::-1], 1) if x), -1)
                inv2[lastindex + 1] = current_value
            else: inv2.insert(0, current_value)
            action, detail = ("change", "move to %s" % ("top" if direction < 0 else "bottom"))
        elif delete:
            eq2, inv2 = None, self._state.copy()
            inv2.pop(rowindex)
            action, detail = ("change", "delete")
        elif artifact:
            eq2, inv2 = None, self._state.copy()
            inv2[rowindex] = artifact
            action, detail = ("set", artifact)
        else:
            eq2, inv2 = None, self._state.copy()
            inv2.insert(rowindex, None)
            action, detail = ("change", "insert <blank>")

        if inv2 == self._state and eq2 in (None, self._hero.equipment):
            return
        label = "%s %s inventory: slot %s %s" % (action, self._hero.name, rowindex + 1, detail)
        callable = functools.partial(self.change_artifacts, inv2, eq2)
        self.parent.command(callable, name=label)


    def on_combo_artifact(self, event, rowindex):
        """Handler for assembling or disassembling a combination artifact, propagates change."""
        COMBINATION_ARTIFACTS = metadata.Store.get("combination_artifacts", version=self.version)
        COMBINATION_COMPONENTS = {b: a for a, bb in COMBINATION_ARTIFACTS.items() for b in bb}
        artifact_on_row = self._state[rowindex]

        inv2 = self._state.copy()
        if artifact_on_row in COMBINATION_ARTIFACTS:
            action, acting = "disassemble", "Disassembling"
            combo_artifact = artifact_on_row
            components = COMBINATION_ARTIFACTS[combo_artifact]
            if len(components) + sum(map(bool, self._state)) - 1 > len(self._state):
                h3sed.guibase.status("Inventory too full to disassemble %s" % combo_artifact,
                                     flash=conf.StatusShortFlashLength)
                return # Inventory too full
            inv2[rowindex] = components[0]
            inv2 = inv2.make_compact()
            inv2.extend(components[1:])
        else:
            action, acting = "assemble", "Assembling"
            combo_artifact = COMBINATION_COMPONENTS[artifact_on_row]
            components = list(COMBINATION_ARTIFACTS[combo_artifact])
            components.remove(artifact_on_row)
            inv2[rowindex] = combo_artifact
            while components: inv2.remove(components.pop())
            inv2 = inv2.make_compact()

        label = "change %s inventory: %s %s" % (self._hero.name, action, combo_artifact)
        h3sed.guibase.status("%s inventory %s" % (acting, combo_artifact),
                             flash=conf.StatusShortFlashLength, log=True)
        callable = functools.partial(self.change_artifacts, inv2)
        self.parent.command(callable, name=label)


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
