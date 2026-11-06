# -*- coding: utf-8 -*-
"""
Tavern heroes subplugin for faction-plugin, manages heroes available in player tavern.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   06.11.2026
@modified  06.11.2026
------------------------------------------------------------------------------
"""
import logging

try: import wx
except ImportError: wx = None

import h3sed
from .. lib.i18n import translate as __
from .. lib import util
from .. import metadata


logger = logging.getLogger(__package__)


PROPS = {"name": "tavern_heroes", "label": "Tavern heroes"}
DATAPROPS = [{
    "type":         "itemlist",
    "orderable":    True,
    "item": [{
        "type":     "label",
        "label":    "slot",
    }, {
        "type":     "combo",
        "choices":  None, # Populated later
        "format":   lambda x: [str(y) for y in x] if isinstance(x, list) else str(x),
    }],
    "extra":  {
        "type":     "button",
        "label":    "Open",
        "handler":  None,  # Populated later
    },
}, {
    "name":     "warning",
    "type":     "label",
    "label":    "Warning: a neutral hero may currently be in prison.\n"
                "Assigning and hiring them can result in invalid game state.",
}]



def props():
    """Returns props for resources-tab, as {label, index}."""
    return PROPS


def factory(parent, panel, version):
    """Returns a new hero order plugin instance."""
    return TavernHeroesPlugin(parent, panel, version)



class TavernHeroesPlugin(object):
    """Provides UI functionality for listing and rearranging faction heroes."""

    def __init__(self, parent, panel, version):
        self.name     = PROPS["name"]
        self.parent   = parent
        self.version  = version
        self._panel   = panel # Plugin contents panel
        self._state   = []
        self._faction = None
        self._ctrls   = []    # {wx.ComboBox, ]
        self._heroes_available = []


    def props(self):
        """Returns props for hero order tab, as [{type: "link", ..}]."""
        result = []
        self.collect_available_heroes()
        for prop in DATAPROPS:
            myprop = dict(prop)
            if "itemlist" == prop["type"]:
                myprop.update(item=[])
                for item in prop["item"]:
                    if "choices" in item:
                        item["choices"] = self._heroes_available[:]
                    myprop["item"].append(item)
            if "extra" in prop:
                myprop = dict(myprop, extra=dict(prop["extra"], handler=self.on_open_hero))
            result.append(myprop)
        return result


    def state(self):
        """Returns data state for stats-plugin, as [Hero, ..]."""
        return self._state


    def item(self):
        """Returns current faction."""
        return self._faction


    def load(self, faction):
        """Loads faction to plugin."""
        self._faction = faction
        self._state = faction.tavern_heroes
        self.collect_available_heroes()


    def load_state(self, state):
        """Loads plugin state from given data, returns whether state changed."""
        self.collect_available_heroes()
        heroes_by_name = {str(h): h for h in self._heroes_available + [h for h in self._state if h]}
        state0 = self._state.copy()
        for slot, hero0 in enumerate(self._state):
            hero = heroes_by_name.get(state[slot] if slot < len(state) else None)
            if not hero0 or not hero: continue # for slot
            if slot and hero in self._state[:slot]: continue # for slot
            self._state[slot] = hero
        if any(self._state) and len(set(self._state)) < len(self._state):
            self._state[:] = state0 # Duplicates formed: reject change
        else: self.collect_available_heroes()
        return state0 != self._state


    def render(self):
        """Builds plugin controls into panel. Returns True."""
        result = False
        if self._ctrls and all(self._ctrls): # All built and still valid
            for slot in range(len(self._state)):
                choices, value = self._heroes_available[:], None
                if self._state[slot]:
                    choices = sorted(choices + [self._state[slot]])
                    value = str(self._state[slot])
                labels = [str(x) for x in choices]
                ctrl = self._ctrls[0][slot]
                h3sed.lib.controls.set_combo_choices(ctrl, labels, choices, value)
        else:
            self._ctrls, result = h3sed.gui.build(self, self._panel), True

        for slot, hero in enumerate(self._state):
            self._ctrls[0][slot].Enable(bool(hero))
            sibling = self._ctrls[0][slot].GetNextSibling()
            while sibling: # Enable-disable buttons for blank slots
                if isinstance(sibling, wx.Button):
                    if not hero: sibling.Enable(False)
                    else:
                        do_enable = True
                        if not all(self._state): do_enable = False
                        elif "down" == sibling.Name: do_enable = (slot < len(self._state) - 1)
                        elif   "up" == sibling.Name: do_enable = (slot > 0)
                        sibling.Enable(do_enable)
                sibling = sibling.GetNextSibling()
        return result


    def collect_available_heroes(self):
        """Assembles list of neutral heroes assignable in tavern."""
        candidates = list(self.parent.savefile.find_heroes(faction="neutral"))
        assigneds = [h for f in self.parent.savefile.factions for h in f.tavern_heroes if h]
        candidates = [h for h in candidates if h not in assigneds]
        self._heroes_available[:] = candidates


    def on_change(self, prop, value, ctrl, rowindex):
        """
        Handler for equipment slot change, updates state, returns whether action succeeded.

        Rolls back change if lacking free slot due to a combination artifact.
        """
        v1, v2 = self._state[rowindex], value or None
        if v1 == v2: return False

        self._state[rowindex] = value
        self.collect_available_heroes()
        self.render()
        return True


    def on_open_hero(self, prop, rowindex, event=None):
        """Handler for clicking to open a selected hero, propagates event to open hero page."""
        hero = self._state[rowindex]
        if not hero: return
        evt_args = {"action": "open", "kind": "hero", "name": hero.get_name_ident()}
        wx.PostEvent(self._panel, h3sed.gui.PluginEvent(self._panel.Id, **evt_args))



def parse(faction_bytes, version, savefile):
    """Returns tavern heroes parsed from faction bytearray."""
    DATA_RANGES = h3sed.version.adapt("data_ranges", metadata.DATA_RANGES, version=version)
    BYTEPOS = h3sed.version.adapt("faction_byte_positions", metadata.FACTION_BYTE_POSITIONS,
                                  version=version)

    heroes_by_index = {h.index: h for h in savefile.heroes}

    tavern_heroes = []
    for slot in range(DATA_RANGES["faction.tavern_heroes"][1]):
        pos = BYTEPOS["tavern_heroes"] + slot
        binary, value = faction_bytes[pos:pos + 1], None
        if binary == metadata.BLANK:
            tavern_heroes.append(None)
            continue # for slot

        try:
            value = util.bytoi(binary)
            tavern_heroes.append(heroes_by_index[value])
        except Exception as e:
            logger.warning("Failed to parse tavern %s hero with index %s: %s", slot, value, e)
    return tavern_heroes


def serialize(tavern_heroes, faction_bytes, version):
    """Returns new faction bytearray with updated tavern heroes section."""
    DATA_RANGES = h3sed.version.adapt("data_ranges", metadata.DATA_RANGES, version=version)
    BYTEPOS = h3sed.version.adapt("faction_byte_positions", metadata.FACTION_BYTE_POSITIONS,
                                  version=version)

    new_bytes = faction_bytes[:]
    for slot in range(DATA_RANGES["faction.tavern_heroes"][1]):
        pos = BYTEPOS["tavern_heroes"] + slot
        binary = metadata.BLANK
        if slot < len(tavern_heroes) and tavern_heroes[slot]:
            binary = util.itoby(tavern_heroes[slot].index, 1)
        new_bytes[pos:pos + 1] = binary
    return new_bytes
