# -*- coding: utf-8 -*-
"""
Handles parsing, serializing and managing hero equipment - artifacts worn.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   16.03.2020
@modified  17.09.2025
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


logger = logging.getLogger(__name__)


def format_stats(plugin, prop, state, artifact_stats=None):
    """Returns item primaty stats modifier text like "+1 Attack, +1 Defense", or "" if no effect."""
    value = state.get(prop.get("name"))
    if not value: return ""
    STATS = artifact_stats or metadata.Store.get("artifact_stats", version=plugin.version)
    if value not in STATS: return ""
    return ", ".join("%s%s %s" % ("" if v < 0 else "+", v, k)
                     for k, v in zip(metadata.PRIMARY_ATTRIBUTES.values(), STATS[value]) if v)


PROPS = {"name": "equipment", "label": "Equipment", "index": 3}
DATAPROPS = [{
    "name":     "helm",
    "label":    "Helm slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None, # Populated later
    "menu":     None, # Populated later
    "info":     format_stats,
}, {
    "name":     "neck",
    "label":    "Neck slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "menu":     None,
    "info":     format_stats,
}, {
    "name":     "armor",
    "label":    "Armor slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "menu":     None,
    "info":     format_stats,
}, {
    "name":     "weapon",
    "label":    "Weapon slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "menu":     None,
    "info":     format_stats,
}, {
    "name":     "shield",
    "label":    "Shield slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "menu":     None,
    "info":     format_stats,
}, {
    "name":     "lefthand",
    "label":    "Left hand slot",
    "type":     "combo",
    "slot":     "hand",
    "nullable": True,
    "choices":  None,
    "menu":     None,
    "info":     format_stats,
}, {
    "name":     "righthand",
    "label":    "Right hand slot",
    "type":     "combo",
    "slot":     "hand",
    "nullable": True,
    "choices":  None,
    "menu":     None,
    "info":     format_stats,
}, {
    "name":     "cloak",
    "label":    "Cloak slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "menu":     None,
    "info":     format_stats,
}, {
    "name":     "feet",
    "label":    "Feet slot",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "menu":     None,
    "info":     format_stats,
}, {
    "name":     "side1",
    "label":    "Side slot 1",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
    "menu":     None,
    "info":     format_stats,
}, {
    "name":     "side2",
    "label":    "Side slot 2",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
    "menu":     None,
    "info":     format_stats,
}, {
    "name":     "side3",
    "label":    "Side slot 3",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
    "menu":     None,
    "info":     format_stats,
}, {
    "name":     "side4",
    "label":    "Side slot 4",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
    "menu":     None,
    "info":     format_stats,
}, {
    "name":     "side5",
    "label":    "Side slot 5",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
    "menu":     None,
    "info":     format_stats,
}]



def props():
    """Returns props for equipment-tab, as {label, index}."""
    return PROPS


def factory(parent, panel, version):
    """Returns a new equipment-plugin instance."""
    return EquipmentPlugin(parent, panel, version)



class EquipmentPlugin(object):
    """Provides UI functionality for listing and changing equipment worn by hero."""


    def __init__(self, parent, panel, version):
        self.name    = PROPS["name"]
        self.parent  = parent
        self.version = version
        self._panel  = panel  # Plugin contents panel
        self._state  = h3sed.hero.Equipment.factory(version)
        self._hero   = None
        self._ctrls  = {}     # {"helm": wx.ComboBox, "helm-info": wx.StaticText, }


    def props(self):
        """Returns UI props for equipment-tab, as [{type: "combo", ..}]."""
        result = []
        LOCATION_TO_SLOT = metadata.Store.get("equipment_slots", version=self.version)
        for prop in DATAPROPS:
            slot = LOCATION_TO_SLOT.get(prop["name"])
            if slot is None: continue # for prop
            choices = metadata.Store.get("artifacts", category=slot, version=self.version)
            result.append(dict(prop, choices=[""] + choices, menu=self.make_item_menu))
        return h3sed.version.adapt("hero.equipment.DATAPROPS", result, version=self.version)


    def state(self):
        """Returns data state for equipment-plugin, as {helm, ..}."""
        return self._state


    def item(self):
        """Returns current hero."""
        return self._hero


    def load(self, hero):
        """Loads hero to plugin."""
        self._hero = hero
        self._state = hero.equipment


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values."""
        state0 = self._state.copy()
        for location, artifact in state.items():
            if location in self._state and self._state[location] != artifact:
                try: self._state[location] = artifact
                except Exception as e: logger.warning(str(e))

        result = (state0 != self._state)
        return result


    def render(self):
        """
        Populates controls from state, using existing if already built.
        
        Returns whether new controls were created.
        """
        result = False
        if self._ctrls and all(self._ctrls.values()): # All built and still valid
            STATS = metadata.Store.get("artifact_stats", version=self.version)
            for prop in self.props():
                name, slot = prop["name"], prop.get("slot", prop["name"])
                cc = [""] + metadata.Store.get("artifacts", category=slot, version=self.version)

                ctrl, value, choices = self._ctrls[name], self._state.get(name), cc
                if value and value not in choices: choices = [value] + cc
                if choices != ctrl.GetItems(): ctrl.SetItems(choices)
                ctrl.Value = value or ""
                infoctrl = self._ctrls["%s-info" % name]
                infoctrl.Label = infoctrl.ToolTip = format_stats(self, prop, self._state, STATS)
        else:
            self._ctrls, result = h3sed.gui.build(self, self._panel), True
        self.update_reserved_slots()
        return result


    def make_common_menu(self):
        """Returns wx.Menu with plugin-specific actions, like removing all equipment."""
        menu = wx.Menu()
        item_clear = menu.Append(wx.ID_ANY, "Remove all equipment")
        item_send  = menu.Append(wx.ID_ANY, "Send all equipment to inventory")
        item_recv  = menu.Append(wx.ID_ANY, "Equip all possible equipment from inventory")
        item_swap  = menu.Append(wx.ID_ANY, "Swap all possible equipment with inventory")
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_all),                       item_clear)
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_all, send=True),            item_send)
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_all, recv=True),            item_recv)
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_all, send=True, recv=True), item_swap)
        return menu


    def make_item_menu(self, plugin, prop, rowindex):
        """Returms wx.Menu for equipment location options."""
        ARTIFACT_TO_SLOTS = metadata.Store.get("artifact_slots", version=self.version)
        LOCATION_TO_SLOT = metadata.Store.get("equipment_slots", version=self.version)
        SLOT_TO_LOCATIONS = {slot: [l for l, slot2 in LOCATION_TO_SLOT.items() if slot == slot2]
                             for slot in LOCATION_TO_SLOT.values()}

        location, slot = prop["name"], LOCATION_TO_SLOT[prop["name"]]
        swap_label = "Swap with" if self._state[location] else "Equip from"
        menu = wx.Menu()
        menu_equip = wx.Menu()
        item_send  = menu.Append(wx.ID_ANY, "Send to inventory")
        item_equip = menu.AppendSubMenu(menu_equip, "%s inventory .." % swap_label)

        sorted_inv = sorted(enumerate(self._hero.inventory),
                            key=lambda x: ("" if x[1] is None else x[1], x[0]))
        for inventory_index, artifact_name in sorted_inv:
            if artifact_name is None: continue # for inventory_index,
            artifact_slot = ARTIFACT_TO_SLOTS[artifact_name][0]
            if artifact_slot != slot: continue # for inventory_index,

            label = "%s:\t%s" % (inventory_index + 1, artifact_name)
            item = menu_equip.Append(wx.ID_ANY, label)
            kwargs = dict(location=location, inventory_index=inventory_index)
            menu.Bind(wx.EVT_MENU, functools.partial(self.on_send_to_inventory, **kwargs), item)

        if len(SLOT_TO_LOCATIONS[slot]) > 1:
            menu_swap = wx.Menu()
            reserved_locations = self._hero.equipment.get_reserved_locations()
            for location2 in SLOT_TO_LOCATIONS[slot]:
                artifact_equipped = self._hero.equipment[location2]
                if artifact_equipped is None and location2 in reserved_locations:
                    label = "<taken by %s>" % self._hero.equipment[reserved_locations[location2]]
                else: label = "<blank>" if artifact_equipped is None else artifact_equipped
                item = menu_swap.Append(wx.ID_ANY, "%s:\t%s" % (location2, label))
                kwargs = dict(location=location, location2=location2)
                menu.Bind(wx.EVT_MENU, functools.partial(self.on_swap_location, **kwargs), item)
                if location == location2:
                    menu_swap.Enable(item.Id, False)
            item_swap = menu.AppendSubMenu(menu_swap, "Swap with location ..")
            if not any(self._state[l] for l in SLOT_TO_LOCATIONS[slot]):
                menu.Enable(item_swap.Id, False)

        if not self._state[location]:
            menu.Enable(item_send.Id, False)
        if not menu_equip.MenuItemCount:
            menu.Enable(item_equip.Id, False)
        kwargs = dict(location=location)
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_send_to_inventory, **kwargs), item_send)
        return menu


    def change_artifacts(self, equipment, inventory):
        """Carries out change of equipment and inventory, propagates change to hero and savefile."""
        changes = {} # {property name: whether changed from action}
        if equipment != self._state:
            self._hero.equipment.update(equipment), changes.update(equipment=True)
        if inventory != self._hero.inventory:
            self._hero.inventory[:], changes["inventory"] = inventory, True
        changes["stats"] = (self._hero.stats != self._hero.realized.stats)
        if not any(changes.values()): return True
        self._hero.realize()
        self.parent.patch()
        for name in (name for name, changed in changes.items() if changed):
            evt = h3sed.gui.PluginEvent(self._panel.Id, action="render", name=name)
            wx.PostEvent(self._panel, evt)
        return True


    def update_reserved_slots(self):
        """Updates slots availability in UI."""
        LOCATION_TO_SLOT = metadata.Store.get("equipment_slots", version=self.version)
        reserved_locations = self._state.get_reserved_locations()
        self._panel.Freeze()
        try:
            for location, artifact in self._state.items():
                slot = LOCATION_TO_SLOT[location]
                choices = [""] + metadata.Store.get("artifacts", category=slot, version=self.version)
                ctrl = self._ctrls[location]

                if not ctrl.Enabled:
                    if artifact and artifact not in choices:
                        choices = [artifact] + choices
                    if choices != ctrl.GetItems(): ctrl.SetItems(choices)
                    ctrl.Value = artifact or ""
                    ctrl.Enable()

                if not artifact and location in reserved_locations:
                    label = "<taken by %s>" % self._state[reserved_locations[location]]
                    ctrl.SetItems([label])
                    ctrl.Value = label
                    ctrl.Disable()
        finally: self._panel.Thaw()


    def on_change(self, prop, row, ctrl, value):
        """
        Handler for equipment slot change, updates state, returns whether action succeeded.

        Rolls back change if lacking free slot due to a combination artifact.
        """
        v1, v2 = self._state[prop["name"]], value or None
        if v1 == v2: return False

        try: self._state[prop["name"]] = v2
        except Exception as e:
            ctrl.Value = v1 or ""
            wx.MessageBox(str(e), conf.Title, wx.OK | wx.ICON_WARNING)
            return False

        stats0 = self._hero.stats.copy()
        self._hero.realize()
        if stats0 != self._hero.stats:
            evt = h3sed.gui.PluginEvent(self._panel.Id, action="render", name="stats")
            wx.PostEvent(self._panel, evt)
        self.update_reserved_slots()
        self._ctrls["%s-info" % prop["name"]].Label = format_stats(self, prop, self._state)
        return True


    def on_change_all(self, event, send=False, recv=False):
        """
        Handler for removing or donning or doffing or swapping all equipment,
        carries out and propagates change.
        """
        if send and recv:
            eq2, inv2 = self._hero.make_equipment_swap()
            acting, action = "Swapping all equipment with inventory", "swap all with inventory"
        elif not send and not recv:
            eq2, inv2 = h3sed.hero.Equipment.factory(self.version), None
            acting, action = "Removing all equipment", "remove all"
        elif recv:
            eq2, inv2 = self._hero.make_artifacts_transfer(to_inventory=False)
            acting, action = "Equipping all from inventory", "equip all from inventory"
        else:
            eq2, inv2 = self._hero.make_artifacts_transfer(to_inventory=True)
            acting, action = "Sending all equipment to inventory", "send all to inventory"

        if (eq2, inv2) == (self._state, self._hero.inventory):
            h3sed.guibase.status("No change from %s" % acting.lower(),
                                 flash=conf.StatusShortFlashLength, log=True)
            return
        label = "change %s equipment: %s" % (self._hero.name, action)
        h3sed.guibase.status(acting, flash=conf.StatusShortFlashLength, log=True)
        callable = functools.partial(self.change_artifacts, eq2, inv2)
        self.parent.command(callable, name=label)


    def on_send_to_inventory(self, event, location, inventory_index=None):
        """Handler for swapping artifact with inventory, carries out and propagates change."""
        try: eq2, inv2 = self._hero.make_artifact_swap(location, inventory_index)
        except Exception as e:
            wx.MessageBox(str(e), conf.Title, wx.OK | wx.ICON_WARNING)
            return
        if (eq2, inv2) == (self._state, self._hero.inventory):
            return
        artifact_name1 = self._state[location]
        artifact_name2 = None if inventory_index is None else self._hero.inventory[inventory_index]
        action = "send %s" % artifact_name1 if inventory_index is None else \
                 "swap %s with" % artifact_name1 if artifact_name1 else "equip %s from" % location
        label = "%s equipment: %s inventory %s" % (self._hero.name, action, artifact_name2)
        h3sed.guibase.status("Changing %s" % label, flash=conf.StatusShortFlashLength, log=True)
        callable = functools.partial(self.change_artifacts, eq2, inv2)
        self.parent.command(callable, name="change %s" % label)


    def on_swap_location(self, event, location, location2):
        """Handler for swapping artifact between locations, carries out and propagates change."""
        if self._state[location] == self._state[location2]: return

        eq2, inv2 = self._state.copy(), self._hero.inventory.copy()
        eq2.update({location: eq2[location2], location2: eq2[location]})
        label = "%s equipment: swap %s with %s" % (self._hero.name, location, location2)
        h3sed.guibase.status("Changing %s" % label, flash=conf.StatusShortFlashLength, log=True)
        callable = functools.partial(self.change_artifacts, eq2, inv2)
        self.parent.command(callable, name="change %s" % label)


def parse(hero_bytes, version):
    """Returns h3sed.hero.Equipment() parsed from hero bytearray equipment section."""
    EQUIPMENT_LOCATIONS = list(metadata.Store.get("equipment_slots", version=version))
    BYTEPOS = h3sed.version.adapt("hero_byte_positions", metadata.HERO_BYTE_POSITIONS,
                                  version=version)
    IDS = metadata.Store.get("ids", version=version)
    ARTIFACTS = metadata.Store.get("artifacts", category="inventory", version=version)
    ARTIFACT_NAMES = {IDS[n]: n for n in ARTIFACTS}

    def parse_id(hero_bytes, pos):
        binary, integer = hero_bytes[pos:pos + 4], util.bytoi(hero_bytes[pos:pos + 4])
        if all(x == ord(metadata.BLANK) for x in binary): return None # Blank
        if integer == IDS["Spell Scroll"]: return util.bytoi(hero_bytes[pos:pos + 8])
        return integer

    equipment = h3sed.hero.Equipment.factory(version)
    for location in EQUIPMENT_LOCATIONS:
        artifact_id = parse_id(hero_bytes, BYTEPOS[location])
        if artifact_id: equipment[location] = ARTIFACT_NAMES[artifact_id]
    return equipment


def serialize(equipment, hero_bytes, version, hero=None):
    """Returns new hero bytearray with updated equipment section."""
    IDS = metadata.Store.get("ids", version=version)
    EQUIPMENT_LOCATIONS = list(metadata.Store.get("equipment_slots", version=version))
    ARTIFACT_SLOTS = metadata.Store.get("artifact_slots", version=version)
    SCROLL_ARTIFACTS = metadata.Store.get("artifacts", category="scroll", version=version)
    BYTEPOS = h3sed.version.adapt("hero_byte_positions", metadata.HERO_BYTE_POSITIONS,
                                  version=version)
    HAS_COMBOS = "reserved" in BYTEPOS

    new_bytes = hero_bytes[:]
    reserved_sets = set()  # [pos updated in combination artifact flags, ]
    if HAS_COMBOS:
        pos_reserved = min(BYTEPOS["reserved"].values())
        len_reserved = len(BYTEPOS["reserved"])
        new_bytes[pos_reserved:pos_reserved + len_reserved] = metadata.NULL * len_reserved

    for location in EQUIPMENT_LOCATIONS:
        artifact_name = equipment.get(location)
        artifact_id, location_pos = IDS.get(artifact_name), BYTEPOS[location]
        if artifact_name in SCROLL_ARTIFACTS:
            binary = util.itoby(artifact_id, 8) # XY 00 00 00 00 00 00 00
        elif artifact_id:
            binary = util.itoby(artifact_id, 4) + metadata.BLANK * 4 # XY 00 00 00 FF FF FF FF
        elif hero and not hero.original.get("equipment", {}).get(location):
            # Retain original bytes unchanged, as game uses both 0x00 and 0xFF
            binary = hero.bytes0[location_pos:location_pos + 8]
        else:
            binary = metadata.BLANK * 8 # FF FF FF FF FF FF FF FF
        new_bytes[location_pos:location_pos + len(binary)] = binary

        for slot in ARTIFACT_SLOTS.get(artifact_name, [])[1:] if HAS_COMBOS else ():
            new_bytes[BYTEPOS["reserved"][slot]] += 1
            reserved_sets.add(BYTEPOS["reserved"][slot])

    for pos in range(pos_reserved, pos_reserved + len_reserved) if HAS_COMBOS else ():
        if hero and pos not in reserved_sets and hero.bytes0[pos] > 5:
            # Retain original bytes unchanged, Horn of the Abyss uses them for unknown purpose
            new_bytes[pos] = hero.bytes0[pos]

    return new_bytes
