# -*- coding: utf-8 -*-
"""
Spells subplugin for hero-plugin, shows hero learned spells list.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   20.03.2020
@modified  05.04.2025
------------------------------------------------------------------------------
"""
import logging

import h3sed
from .. import metadata


logger = logging.getLogger(__name__)


PROPS = {"name": "spells", "label": "Spells", "index": 5}
DATAPROPS = [{
    "type":       "checklist",
    "choices":    None, # Populated later
    "columns":    4,
    "vertical":   True,
}]


def props():
    """Returns props for spells-tab, as {label, index}."""
    return PROPS


def factory(parent, panel, version):
    """Returns a new spells-plugin instance."""
    return SpellsPlugin(parent, panel, version)



class SpellsPlugin(object):
    """Provides UI functionality for listing and changing spells in hero spellbook."""


    def __init__(self, parent, panel, version):
        self.name    = PROPS["name"]
        self.parent  = parent
        self.version = version
        self._panel  = panel  # Plugin contents panel
        self._state  = h3sed.hero.Spells.factory(version)
        self._hero   = None


    def props(self):
        """Returns UI props for spells-tab, as [{type: "checklist", ..}]."""
        result = []
        for prop in DATAPROPS:
            choices = metadata.Store.get("spells", version=self.version)
            result.append(dict(prop, choices=sorted(choices)))
        return result


    def state(self):
        """Returns data state for spells-plugin, as h3sed.hero.Spells."""
        return self._state


    def item(self):
        """Returns current hero."""
        return self._hero


    def load(self, hero):
        """Loads hero to plugin."""
        self._hero = hero
        self._state = hero.spells


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values. Returns whether state changed."""
        state0 = self._state.copy()
        self._state.clear()
        for v in state:
            try: self._state.add(v)
            except Exception as e: logger.warning(e)
        return state0 != self._state


    def render(self):
        """Creates controls from state, disabling all if no spellbook. Returns True."""
        h3sed.gui.build(self, self._panel)
        if not self._hero.stats.spellbook:
            for c in self._panel.Children: c.Disable()
        return True


    def on_add(self, prop, value):
        """Adds spell to current hero spells, returns whether state changed."""
        if value in self._state: return False
        self._state.add(value)
        return True


def parse(hero_bytes, version):
    """Returns h3sed.hero.Spells() parsed from hero bytearray spellbook section."""
    SPELL_POSES = {y: x[y] for x in [metadata.Store.get("ids", version=version)]
                   for y in metadata.Store.get("spells", version=version)}
    SPELLBOOK_POS = h3sed.version.adapt("hero_byte_positions", metadata.HERO_BYTE_POSITIONS,
                                        version=version)["spells_book"]

    spells = h3sed.hero.Spells.factory(version)
    for spell_name, spell_pos in SPELL_POSES.items():
        if hero_bytes[SPELLBOOK_POS + spell_pos]: spells.add(spell_name)
    return spells


def serialize(spells, hero_bytes, version, hero=None):
    """
    Returns new hero bytearray with updated spells section: spellbook and artifact spells.

    @param   hero  used for checking spellbook availability and artifact spells, if given
    """
    SPELL_POSES = {y: x[y] for x in [metadata.Store.get("ids", version=version)]
                   for y in metadata.Store.get("spells", version=version)}
    BYTEPOS = h3sed.version.adapt("hero_byte_positions", metadata.HERO_BYTE_POSITIONS,
                                  version=version)
    SPELLBOOK_POS, ALLSPELLS_POS = BYTEPOS["spells_book"], BYTEPOS["spells_available"]
    ARTIFACT_SPELLS = metadata.Store.get("artifact_spells", version=version)
    BANNABLE_SPELLS = metadata.Store.get("bannable_spells", version=version)

    artifact_spells0 = set(y for x in hero.original.get("equipment", {}).values()
                           for y in ARTIFACT_SPELLS.get(x, [])) if hero else set()
    artifact_spells  = set(y for x in hero.equipment.values()
                           for y in ARTIFACT_SPELLS.get(x, [])) if hero else set()
    conditional_spells  = set(BANNABLE_SPELLS)
    conditional_spells &= artifact_spells0 & artifact_spells
    has_spellbook = True if hero is None else hero.stats.spellbook

    new_bytes = hero_bytes[:]
    for spell_name, spell_pos in SPELL_POSES.items():
        in_book   = has_spellbook and spell_name in spells
        available = in_book or spell_name in artifact_spells

        # Some maps may have certain spells banned, e.g. Summon Boat on maps with no water
        # in Horn of the Abyss; savefiles will not have these spell bits set.
        # At least try to avoid a needless file change if we can detect the ban being in effect.
        if available and not in_book and not new_bytes[ALLSPELLS_POS + spell_pos] \
        and spell_name in conditional_spells: available = False

        new_bytes[SPELLBOOK_POS + spell_pos] = in_book
        new_bytes[ALLSPELLS_POS + spell_pos] = available

    return new_bytes
