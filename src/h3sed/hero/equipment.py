# -*- coding: utf-8 -*-
"""
Handles parsing, serializing and managing hero equipment - artifacts worn.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   16.03.2020
@modified  01.05.2026
------------------------------------------------------------------------------
"""
import functools
import logging

try: import wx
except ImportError: wx = None

import h3sed
from .. lib import util
from .. lib.i18n import format_nested, translate as __
from .. import conf
from .. import metadata


logger = logging.getLogger(__name__)


PROPS = {"name": "equipment", "label": "Equipment", "index": 3}
DATAPROPS = [{
    "name":     "helm",
    "label":    "Helm",
    "type":     "combo",
    "nullable": True,
    "choices":  None, # Populated later
    "format":   None, # Populated later
    "menu":     None, # Populated later
    "info":     None, # Populated later
}, {
    "name":     "neck",
    "label":    "Neck",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "format":   None,
    "menu":     None,
    "info":     None,
}, {
    "name":     "armor",
    "label":    "Armor",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "format":   None,
    "menu":     None,
    "info":     None,
}, {
    "name":     "weapon",
    "label":    "Weapon",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "format":   None,
    "menu":     None,
    "info":     None,
}, {
    "name":     "shield",
    "label":    "Shield",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "format":   None,
    "menu":     None,
    "info":     None,
}, {
    "name":     "lefthand",
    "label":    "Left hand",
    "type":     "combo",
    "slot":     "hand",
    "nullable": True,
    "choices":  None,
    "format":   None,
    "menu":     None,
    "info":     None,
}, {
    "name":     "righthand",
    "label":    "Right hand",
    "type":     "combo",
    "slot":     "hand",
    "nullable": True,
    "choices":  None,
    "format":   None,
    "menu":     None,
    "info":     None,
}, {
    "name":     "cloak",
    "label":    "Cloak",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "format":   None,
    "menu":     None,
    "info":     None,
}, {
    "name":     "feet",
    "label":    "Feet",
    "type":     "combo",
    "nullable": True,
    "choices":  None,
    "format":   None,
    "menu":     None,
    "info":     None,
}, {
    "name":     "side1",
    "label":    "Side 1",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
    "format":   None,
    "menu":     None,
    "info":     None,
}, {
    "name":     "side2",
    "label":    "Side 2",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
    "format":   None,
    "menu":     None,
    "info":     None,
}, {
    "name":     "side3",
    "label":    "Side 3",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
    "format":   None,
    "menu":     None,
    "info":     None,
}, {
    "name":     "side4",
    "label":    "Side 4",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
    "format":   None,
    "menu":     None,
    "info":     None,
}, {
    "name":     "side5",
    "label":    "Side 5",
    "type":     "combo",
    "slot":     "side",
    "nullable": True,
    "choices":  None,
    "format":   None,
    "menu":     None,
    "info":     None,
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
            myprop = dict(prop)
            if "choices" in prop:
                choices = metadata.Store.get("artifacts", category=slot, version=self.version)
                myprop["choices"] = choices
            if "format"  in prop: myprop["format"] = self.format_artifact
            if "menu"    in prop: myprop["menu"]   = self.make_item_menu
            if "info"    in prop: myprop["info"]   = self.format_stats_bonus
            result.append(myprop)
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
            self._panel.Freeze()
            for prop in self.props():
                name, slot = prop["name"], prop.get("slot", prop["name"])
                cc = [""] + metadata.Store.get("artifacts", category=slot, version=self.version)
                choices, value = cc, self._state.get(name) or ""
                if value and value not in choices: choices.insert(0, value)
                labels = self.format_artifact(choices)
                choices, labels = zip(*sorted(zip(choices, labels), key=lambda x: x[1].lower()))

                ctrl = self._ctrls[name]
                if list(labels) != ctrl.GetItems():
                    ctrl.SetItems(labels)
                    for j, x in enumerate(choices): ctrl.SetClientData(j, x)
                ctrl.Value = self.format_artifact(value) or ""
                infoctrl = self._ctrls["%s-info" % name]
                infoctrl.Label = self.format_stats_bonus(prop)
                infoctrl.ToolTip = infoctrl.Label
            self._panel.Thaw()
        else:
            self._ctrls, result = h3sed.gui.build(self, self._panel), True
        self.update_reserved_slots()
        return result


    def make_common_menu(self):
        """Returns wx.Menu with plugin-specific actions, like removing all equipment."""
        menu = wx.Menu()
        item_clear = menu.Append(wx.ID_ANY, __("Remove all"))
        item_send  = menu.Append(wx.ID_ANY, __("Send all equipment to inventory"))
        item_recv  = menu.Append(wx.ID_ANY, __("Equip all possible equipment from inventory"))
        item_swap  = menu.Append(wx.ID_ANY, __("Swap all possible equipment with inventory"))
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_all),                       item_clear)
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_all, send=True),            item_send)
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_all, recv=True),            item_recv)
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_all, send=True, recv=True), item_swap)
        return menu


    def make_item_menu(self, plugin, prop, rowindex):
        """Returms wx.Menu for equipment location options."""
        ARTIFACT_TO_SLOTS = metadata.Store.get("artifact_slots", version=self.version)
        COMBINATION_ARTIFACTS = metadata.Store.get("combination_artifacts", version=self.version)
        LOCATION_TO_SLOT = metadata.Store.get("equipment_slots", version=self.version)
        SLOT_TO_LOCATIONS = {slot: [l for l, slot2 in LOCATION_TO_SLOT.items() if slot == slot2]
                             for slot in LOCATION_TO_SLOT.values()}
        location, slot = prop["name"], LOCATION_TO_SLOT[prop["name"]]
        reserved_locations = self._state.get_reserved_locations()

        swap_label = "Swap with" if self._state[location] else "Equip from"
        menu = wx.Menu()
        menu_equip = wx.Menu()
        item_send  = menu.Append(wx.ID_ANY, __("Send to inventory"))
        item_equip = menu.AppendSubMenu(menu_equip, __("%s inventory" % swap_label) + " ..")

        sorted_inv = sorted(enumerate(self._hero.inventory),
                            key=lambda x: ("" if x[1] is None else x[1], x[0])) \
                     if location not in reserved_locations else []
        for inventory_index, artifact_name in sorted_inv:
            if artifact_name is None: continue # for inventory_index,
            artifact_slot = ARTIFACT_TO_SLOTS[artifact_name][0]
            if artifact_slot != slot: continue # for inventory_index,

            label = "%s:\t%s" % (inventory_index + 1, self.format_artifact(artifact_name))
            item = menu_equip.Append(wx.ID_ANY, label)
            kwargs = dict(location=location, inventory_index=inventory_index)
            menu.Bind(wx.EVT_MENU, functools.partial(self.on_transact_inventory, **kwargs), item)

        if len(SLOT_TO_LOCATIONS[slot]) > 1:
            menu_swap = wx.Menu()
            for location2 in SLOT_TO_LOCATIONS[slot]:
                artifact_equipped = self._hero.equipment[location2]
                if artifact_equipped is None and location2 in reserved_locations:
                    label = __("<taken by %s>", __(self._hero.equipment[reserved_locations[location2]]))
                elif artifact_equipped is None: label = __("<blank>")
                else: label = self.format_artifact(artifact_equipped)
                item = menu_swap.Append(wx.ID_ANY, "%s:\t%s" % (__(location2), label))
                kwargs = dict(location=location, location2=location2)
                menu.Bind(wx.EVT_MENU, functools.partial(self.on_swap_location, **kwargs), item)
                if location == location2:
                    menu_swap.Enable(item.Id, False)
            item_swap = menu.AppendSubMenu(menu_swap, __("Swap with location") + " ..")
            if not any(self._state[l] for l in SLOT_TO_LOCATIONS[slot]):
                menu.Enable(item_swap.Id, False)

        if location in reserved_locations or self._state[location] in COMBINATION_ARTIFACTS:
            item_combo = menu.Append(wx.ID_ANY, __("Disassemble combination artifact"))
            kwargs = dict(location=location)
            menu.Bind(wx.EVT_MENU, functools.partial(self.on_combo_artifact, **kwargs), item_combo)
        elif self._state[location]:
            combo, others = next(((a, bb) for a, bb in COMBINATION_ARTIFACTS.items()
                                  if self._state[location] in bb), (None, None))
            if combo and all(x in self._state for x in others):
                menu_combo = wx.Menu()
                menu.AppendSubMenu(menu_combo, __("Assemble combination artifact"))
                item = menu_combo.Append(wx.ID_ANY, __(combo))
                kwargs = dict(location=location)
                menu.Bind(wx.EVT_MENU, functools.partial(self.on_combo_artifact, **kwargs), item)

        if not self._state[location]:
            menu.Enable(item_send.Id, False)
        if not menu_equip.MenuItemCount:
            menu.Enable(item_equip.Id, False)
        kwargs = dict(location=location)
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_transact_inventory, **kwargs), item_send)
        return menu


    def format_artifact(self, value):
        """Returns label for display, for a single artifact or a list of artifacts."""
        return h3sed.hero.format_artifacts(value, version=self.version)


    def format_stats_bonus(self, prop):
        """Returns item primaty stats modifier text like "+1 Attack, +1 Defense", or "" if no effect."""
        value = self._state.get(prop.get("name"))
        if not value: return ""
        STATS = metadata.Store.get("artifact_stats", version=self.version)
        if value not in STATS: return ""
        return ", ".join("%s%s %s" % ("" if v < 0 else "+", v, __(k))
                         for k, v in zip(metadata.PRIMARY_ATTRIBUTES.values(), STATS[value]) if v)


    def change_artifacts(self, equipment, inventory=None):
        """Carries out change of equipment and inventory, propagates change to hero and savefile."""
        changes = {} # {property name: whether changed from action}
        if equipment != self._state:
            self._hero.equipment.update(equipment), changes.update(equipment=True, stats=True)
        if inventory is not None and inventory != self._hero.inventory:
            self._hero.inventory[:], changes["inventory"] = inventory, True
        self._hero.realize()
        if not any(changes.values()): return True
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
                cc = metadata.Store.get("artifacts", category=slot, version=self.version)
                choices = [""] + cc
                if artifact and artifact not in choices: choices.insert(0, artifact)

                ctrl = self._ctrls[location]
                if not ctrl.Enabled:
                    labels = self.format_artifact(choices)
                    choices, labels = zip(*sorted(zip(choices, labels), key=lambda x: x[1].lower()))
                    if list(labels) != ctrl.GetItems():
                        ctrl.SetItems(labels)
                        for j, x in enumerate(choices): ctrl.SetClientData(j, x)
                    ctrl.Value = self.format_artifact(artifact) or ""
                    ctrl.Enable()

                if not artifact and location in reserved_locations:
                    combo_artifact = self._state[reserved_locations[location]]
                    label = __("<taken by %s>", __(combo_artifact))
                    ctrl.SetItems([label])
                    ctrl.Value = label
                    ctrl.Disable()
        finally: self._panel.Thaw()


    def on_change(self, prop, value, ctrl, rowindex=None):
        """
        Handler for equipment slot change, updates state, returns whether action succeeded.

        Rolls back change if lacking free slot due to a combination artifact.
        """
        v1, v2 = self._state[prop["name"]], value or None
        if v1 == v2: return False

        try: self._state[prop["name"]] = v2
        except Exception as e:
            ctrl.Value = self.format_artifact(v1) or ""
            wx.MessageBox(str(e), conf.Title, wx.OK | wx.ICON_WARNING)
            return False

        self._hero.realize()
        evt = h3sed.gui.PluginEvent(self._panel.Id, action="render", name="stats")
        wx.PostEvent(self._panel, evt)
        self.update_reserved_slots()
        ctrl_info = self._ctrls["%s-info" % prop["name"]]
        ctrl_info.Label = ctrl_info.ToolTip = self.format_stats_bonus(prop)
        return True


    def on_change_all(self, event, send=False, recv=False):
        """
        Handler for removing or donning or doffing or swapping all equipment,
        carries out and propagates change.
        """
        if send and recv:
            eq2, inv2 = self._hero.make_equipment_swap()
            afterargs = ("swap all", "with inventory")
        elif not send and not recv:
            eq2, inv2 = h3sed.hero.Equipment.factory(self.version), None
            afterargs = ("remove all", )
        elif recv:
            eq2, inv2 = self._hero.make_artifacts_transfer(to_inventory=False)
            afterargs = ("equip all", "from inventory")
        else:
            eq2, inv2 = self._hero.make_artifacts_transfer(to_inventory=True)
            afterargs = ("send all", "to inventory")
        afterlbl = " ".join(["%s"] * len(afterargs))

        if eq2 == self._state and inv2 in (None, self._hero.inventory):
            h3sed.guibase.status(format_nested("No change from: %s", (afterlbl, afterargs),
                                               do_translate=True),
                                 flash=conf.StatusShortFlashLength)
            return

        # "change HERO equipment: swap all with inventory"
        # "change HERO equipment: remove all"
        # "change HERO equipment: equip all from inventory"
        # "change HERO equipment: send all to inventory"
        actionlbl, actionargs = "%s %s", ("change", ("%s {}".format(self.name), self._hero.name))
        cname, cargs = "%s: %s", ((actionlbl, actionargs), (afterlbl, afterargs))
        logger.info("Doing action: %s.", format_nested(cname, *cargs))
        h3sed.guibase.status(__("Doing %s", format_nested(cname, *cargs, do_translate=True)),
                             flash=conf.StatusShortFlashLength)
        callable = functools.partial(self.change_artifacts, eq2, inv2)
        self.parent.command(callable, name=(cname, cargs))
        return


    def on_combo_artifact(self, event, location):
        """Handler for assembling or disassembling a combination artifact, propagates change."""
        ARTIFACT_TO_SLOTS = metadata.Store.get("artifact_slots", version=self.version)
        COMBINATION_ARTIFACTS = metadata.Store.get("combination_artifacts", version=self.version)
        LOCATION_TO_SLOT = metadata.Store.get("equipment_slots", version=self.version)
        SLOT_TO_LOCATIONS = {slot: [l for l, slot2 in LOCATION_TO_SLOT.items() if slot == slot2]
                             for slot in LOCATION_TO_SLOT.values()}

        eq2 = self._state.copy()
        combo_artifact = None
        reserved_locations = self._state.get_reserved_locations()
        if location in reserved_locations or self._state[location] in COMBINATION_ARTIFACTS:
            action = "disassemble"
            combo_artifact = self._state[location] or self._state[reserved_locations[location]]
            components = COMBINATION_ARTIFACTS[combo_artifact]
            primary_location = reserved_locations.get(location, location)
            locations = [a for a in eq2 if reserved_locations.get(a) == primary_location]
            locations.insert(0, primary_location)
            eq2[primary_location] = None
            for component_artifact in components:
                location_candidates = SLOT_TO_LOCATIONS[ARTIFACT_TO_SLOTS[component_artifact][0]]
                component_location = next(l for l in location_candidates if l in locations)
                eq2[component_location] = component_artifact
                locations.remove(component_location)
        else:
            action = "assemble"
            combo_artifact = next(a for a, bb in COMBINATION_ARTIFACTS.items()
                                  if self._state[location] in bb)
            components = COMBINATION_ARTIFACTS[combo_artifact]
            locations = [location]
            component_candidates = [x for x in components if x != self._state[location]]
            locations.extend(l for l, c in eq2.items() if c in component_candidates)
            primary_location_candidates = SLOT_TO_LOCATIONS[ARTIFACT_TO_SLOTS[combo_artifact][0]]
            primary_location = next(l for l in locations if l in primary_location_candidates)
            eq2.update({l: None for l in locations})
            eq2[primary_location] = combo_artifact

        # "change HERONAME equipment: assemble|disassemble ARTIFACT"
        actionlbl, actionargs = "%s %s", ("change", ("%s {}".format(self.name), self._hero.name))
        cname, cargs = "%s: %s %s", ((actionlbl, actionargs), action, combo_artifact)
        logger.info("Doing action: %s.", format_nested(cname, *cargs))
        h3sed.guibase.status(__("Doing %s", format_nested(cname, *cargs, do_translate=True)),
                             flash=conf.StatusShortFlashLength)
        callable = functools.partial(self.change_artifacts, eq2)
        self.parent.command(callable, name=(cname, cargs))


    def on_transact_inventory(self, event, location, inventory_index=None):
        """Handler for swapping artifact with inventory, carries out and propagates change."""
        try: eq2, inv2 = self._hero.make_artifact_swap(location, inventory_index)
        except Exception as e:
            wx.MessageBox(str(e), conf.Title, wx.OK | wx.ICON_WARNING)
            return
        if (eq2, inv2) == (self._state, self._hero.inventory):
            return
        inv2 = inv2.make_compact()
        artifact_name1 = self._state[location]
        artifact_name2 = None if inventory_index is None else self._hero.inventory[inventory_index]

        # "change HERO equipment: send ARTIFACT to inventory"
        # "change HERO equipment: swap ARTIFACT with ARTIFACT from inventory"
        # "change HERO equipment: set LOCATION ARTIFACT from inventory"
        actionlbl, actionargs = "%s %s", ("change", ("%s {}".format(self.name), self._hero.name))
        if inventory_index is None:
            afterargs = ("send", artifact_name1, "to inventory")
        elif artifact_name1 is not None:
            afterargs = ("swap", artifact_name1, "with", artifact_name2, "from inventory")
        else:
            afterargs = ("set", location, artifact_name2, "from inventory")
        afterlbl = " ".join(["%s"] * len(afterargs))
        cname, cargs = "%s: %s", ((actionlbl, actionargs), (afterlbl, afterargs))
        logger.info("Doing action: %s.", format_nested(cname, *cargs))
        h3sed.guibase.status(__("Doing %s", format_nested(cname, *cargs, do_translate=True)),
                             flash=conf.StatusShortFlashLength)
        callable = functools.partial(self.change_artifacts, eq2, inv2)
        self.parent.command(callable, name=(cname, cargs))


    def on_swap_location(self, event, location, location2):
        """Handler for swapping artifact between locations, carries out and propagates change."""
        if self._state[location] == self._state[location2]: return

        eq2 = self._state.copy()
        eq2.update({location: eq2[location2], location2: eq2[location]})

        # "swap HERONAME equipment: LOCATION and LOCATION"
        actionlbl, actionargs = "%s %s", ("swap", ("%s {}".format(self.name), self._hero.name))
        cname, cargs = "%s: %s %s %s", ((actionlbl, actionargs), location, "and", location2)
        logger.info("Doing action: %s.", format_nested(cname, *cargs))
        h3sed.guibase.status(__("Doing %s", format_nested(cname, *cargs, do_translate=True)),
                             flash=conf.StatusShortFlashLength)
        callable = functools.partial(self.change_artifacts, eq2)
        self.parent.command(callable, name=(cname, cargs))


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
        if artifact_id and artifact_id not in ARTIFACT_NAMES:
            logger.warning("Unknown artifact for version %r: 0x%X.", version, artifact_id)
            artifact_name = __("<unknown 0x%X>", artifact_id)
            slot = metadata.Store.get("equipment_slots", version=version)[location]
            metadata.Store.add("artifacts", [artifact_name], category="inventory", version=version)
            metadata.Store.add("artifacts", [artifact_name], category=slot, version=version)
            metadata.Store.add("artifact_slots", {artifact_name: [slot]}, version=version)
            metadata.Store.add("ids", {artifact_name: artifact_id}, version=version)
            ARTIFACT_NAMES[artifact_id] = artifact_name
        equipment[location] = ARTIFACT_NAMES.get(artifact_id)
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
        artifact_name0 = hero.original.get("equipment", {}).get(location) if hero else None
        if artifact_name == artifact_name0 and hero:
            # Retain original bytes unchanged, as game uses both 0x00 and 0xFF
            binary = hero.bytes0[location_pos:location_pos + 8]
        elif artifact_name in SCROLL_ARTIFACTS:
            binary = util.itoby(artifact_id, 8) # XY 00 00 00 00 00 00 00
        elif artifact_id:
            binary = util.itoby(artifact_id, 4) + metadata.BLANK * 4 # XY 00 00 00 FF FF FF FF
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
