# -*- coding: utf-8 -*-
"""
Handles parsing, serializing and managing hero equipment - artifacts worn.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   16.03.2020
@modified  26.07.2025
------------------------------------------------------------------------------
"""
import logging

try: import wx
except ImportError: wx = None

import h3sed
from .. lib import util
from .. import conf
from .. import metadata


logger = logging.getLogger(__name__)


def format_stats(plugin, prop, state, artifact_stats=None):
    """Return item primaty stats modifier text like "+1 Attack, +1 Defense", or "" if no effect."""
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
            result.append(dict(prop, choices=[""] + choices))
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
        self.update_slots()
        return result


    def update_slots(self):
        """Updates slots availability in UI."""
        ARTIFACT_SLOTS = metadata.Store.get("artifact_slots", version=self.version)
        LOCATION_TO_SLOT = metadata.Store.get("equipment_slots", version=self.version)

        slot_owners = {} # {slot: [artifact, ]}
        for location, artifact in self._state.items():
            slots = ARTIFACT_SLOTS.get(artifact, [])
            for slot in slots[1:]: # Artifact first slot is primary
                slot_owners.setdefault(slot, []).append(artifact)

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

                if not artifact and slot_owners.get(slot):
                    owner_artifact = slot_owners[slot].pop()
                    label = "<taken by %s>" % owner_artifact
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
            wx.MessageBox(str(e), conf.Title, wx.OK | wx.ICON_WARNING)
            ctrl.Value = v1 or ""
            return False

        stats0 = self._hero.stats.copy()
        self._hero.realize()
        if stats0 != self._hero.stats:
            evt = h3sed.gui.PluginEvent(self._panel.Id, action="render", name="stats")
            wx.PostEvent(self._panel, evt)
        self.update_slots()
        self._ctrls["%s-info" % prop["name"]].Label = format_stats(self, prop, self._state)
        return True


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
