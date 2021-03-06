# -*- coding: utf-8 -*-
"""
Spells subplugin for hero-plugin, shows hero learned spells list.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   20.03.2020
@modified  18.01.2022
------------------------------------------------------------------------------
"""
import logging

from h3sed import gui
from h3sed import metadata
from h3sed import plugins
from h3sed.lib import util
from h3sed.plugins.hero import POS


logger = logging.getLogger(__package__)


PROPS = {"name": "spells", "label": "Spells", "index": 4}
UIPROPS = [{
    "type":       "itemlist",
    "addable":    True,
    "removable":  True,
    "exclusive":  True,
    "choices":    None, # Populated later
    "item": [{
        "name":   "name",
        "type":   "label",
    }],
}]



def props():
    """Returns props for spells-tab, as {label, index}."""
    return PROPS


def factory(parent, hero, panel):
    """Returns a new spells-plugin instance."""
    return SpellsPlugin(parent, hero, panel)



class SpellsPlugin(object):
    """Encapsulates spells-plugin state and behaviour."""


    def __init__(self, parent, hero, panel):
        self.name    = PROPS["name"]
        self.parent  = parent
        self._hero   = hero
        self._panel  = panel # Plugin contents panel
        self._state  = []    # ["Haste", "Slow", ..]
        if hero:
            self.parse(hero.bytes)
            hero.spells = self._state


    def props(self):
        """Returns props for spells-tab, as [{type: "number", ..}]."""
        result = []
        ver = self._hero.savefile.version
        for prop in UIPROPS:
            cc = metadata.Store.get("spells", version=ver)
            result.append(dict(prop, choices=sorted(cc)))
        return result


    def state(self):
        """Returns data state for spells-plugin, as {mana, exp, ..}."""
        return self._state


    def load(self, hero, panel=None):
        """Loads hero to plugin."""
        self._hero = hero
        self._state[:] = []
        if panel: self._panel = panel
        if hero:
            self.parse(hero.bytes)
            hero.spells = self._state


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values. Returns whether state changed."""
        state0 = type(self._state)(self._state)
        self._state = []
        ver = self._hero.savefile.version
        cmap = {x.lower(): x for x in metadata.Store.get("spells", version=ver)}
        for i, v in enumerate(state):
            if v and hasattr(v, "lower") and v.lower() in cmap:
                self._state += [cmap[v.lower()]]
            elif v:
                logger.warning("Invalid spell #%s: %s", i + 1, v)
        self._state.sort()
        return state0 != self._state


    def render(self):
        """Creates controls from state, disabling all if no spellbook."""
        gui.build(self, self._panel)
        if not util.get(self._hero, "stats", "spellbook"):
            for c in self._panel.Children: c.Disable()


    def on_add(self, prop, value):
        """Adds skill at first level."""
        if value in self._state: return False
        self._state.append(value)
        self._state.sort()
        return True


    def parse(self, bytes):
        """Builds spells state from hero bytearray."""
        result = [] # List of values like ["Haste", ..]
        IDS = {y: x[y] for x in [metadata.Store.get("ids")]
               for y in metadata.Store.get("spells")}
        MYPOS = plugins.adapt(self, "pos", POS)

        for name, pos in IDS.items():
            if bytes[MYPOS["spells_book"] + pos]: result.append(name)
        self._state[:] = sorted(result)


    def serialize(self):
        """Returns new hero bytearray, with edited spells sections."""
        result = self._hero.bytes[:]

        IDS = {y: x[y] for x in [metadata.Store.get("ids")]
               for y in metadata.Store.get("spells")}
        MYPOS = plugins.adapt(self, "pos", POS)
        state = self._state

        artispells = set()
        if getattr(self._hero, "artifacts", None):
            SPELL_ARTIFACTS = metadata.Store.get("artifact_spells")
            artispells = set(y for x in self._hero.artifacts.values()
                             for y in SPELL_ARTIFACTS.get(x, []))
        for name, pos in IDS.items():
            in_book   = name in state
            available = in_book or name in artispells
            result[MYPOS["spells_book"] + pos]      = in_book
            result[MYPOS["spells_available"] + pos] = available

        return result
