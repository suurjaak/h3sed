# -*- coding: utf-8 -*-
"""
Spells subplugin for hero-plugin, shows hero learned spells list.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   20.03.2020
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


PROPS = {"name": "spells", "label": "Spells", "index": 5}
UIPROPS = [{
    "type":       "checklist",
    "choices":    None, # Populated later
    "columns":    4,
    "vertical":   True,
}]


def props():
    """Returns props for spells-tab, as {label, index}."""
    return PROPS


def factory(parent, hero, panel):
    """Returns a new spells-plugin instance."""
    return SpellsPlugin(parent, hero, panel)



class SpellsPlugin(object):
    """Encapsulates spells-plugin state and behaviour."""


    def __init__(self, savefile, parent, panel):
        self.name      = PROPS["name"]
        self.parent    = parent
        self._savefile = savefile
        self._hero     = None
        self._panel    = panel  # Plugin contents panel
        self._state    = []     # ["Haste", "Slow", ..]


    def props(self):
        """Returns props for spells-tab, as [{type: "checklist", ..}]."""
        result = []
        for prop in UIPROPS:
            cc = metadata.Store.get("spells", self._savefile.version)
            result.append(dict(prop, choices=sorted(cc)))
        return result


    def state(self):
        """Returns data state for spells-plugin, as [spell name, ..]."""
        return self._state


    def item(self):
        """Returns current hero."""
        return self._hero


    def load(self, hero, panel=None):
        """Loads hero to plugin."""
        self._hero = hero
        self._state[:] = self.parse([hero])[0]
        hero.spells = self._state
        if panel: self._panel = panel


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values. Returns whether state changed."""
        state0 = type(self._state)(self._state)
        self._state = []
        cmap = {x.lower(): x for x in metadata.Store.get("spells", self._savefile.version)}
        for i, v in enumerate(state):
            if v and hasattr(v, "lower") and v.lower() in cmap:
                self._state += [cmap[v.lower()]]
            elif v:
                logger.warning("Invalid spell #%s: %s", i + 1, v)
        self._state.sort()
        return state0 != self._state


    def render(self):
        """Creates controls from state, disabling all if no spellbook. Returns True."""
        gui.build(self, self._panel)
        if not util.get(self._hero, "stats", "spellbook"):
            for c in self._panel.Children: c.Disable()
        return True


    def on_add(self, prop, value):
        """Adds spell to current hero spells, returns whether state changed."""
        if value in self._state: return False
        self._state.append(value)
        self._state.sort()
        return True


    def parse(self, heroes):
        """Returns spells states parsed from hero bytearrays, as [[name, ], ]."""
        result = [] # Lists of values like ["Haste", ..]
        IDS = {y: x[y] for x in [metadata.Store.get("ids", self._savefile.version)]
               for y in metadata.Store.get("spells", self._savefile.version)}
        MYPOS = plugins.adapt(self, "pos", POS)

        for hero in heroes:
            values = []
            for name, pos in IDS.items():
                if hero.bytes[MYPOS["spells_book"] + pos]: values.append(name)
            result.append(sorted(values))
        return result


    def serialize(self):
        """Returns new hero bytearray, with edited spells sections."""
        result = self._hero.bytes[:]
        version = self._savefile.version

        IDS = {y: x[y] for x in [metadata.Store.get("ids", version)]
               for y in metadata.Store.get("spells", version)}
        MYPOS = plugins.adapt(self, "pos", POS)
        state = self._state

        artispells, condspells = set(), set()
        if getattr(self._hero, "artifacts", None):
            SPELL_ARTIFACTS = metadata.Store.get("artifact_spells", version)
            artispells0 = set(y for x in self._hero.state0.get("artifacts", {}).values()
                              for y in SPELL_ARTIFACTS.get(x, []))
            artispells  = set(y for x in self._hero.artifacts.values()
                              for y in SPELL_ARTIFACTS.get(x, []))
            condspells  = set(metadata.Store.get("bannable_spells", version))
            condspells &= artispells0 & artispells
        for name, pos in IDS.items():
            in_book   = name in state
            available = in_book or name in artispells

            # Some maps may have certain spells banned, e.g. Summon Boat on maps with no water
            # in Horn of the Abyss; savefiles will not have these spell bits set.
            # At least try to avoid a needless file change if we can detect the ban being in effect.
            if available and not in_book and not result[MYPOS["spells_available"] + pos] \
            and name in condspells: available = False

            result[MYPOS["spells_book"] + pos]      = in_book
            result[MYPOS["spells_available"] + pos] = available

        return result
