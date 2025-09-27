# -*- coding: utf-8 -*-
"""
Spells subplugin for hero-plugin, shows hero learned spells list.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   20.03.2020
@modified  27.09.2025
------------------------------------------------------------------------------
"""
import functools
import logging
import math

try: import wx
except ImportError: wx = None

import h3sed
from .. import conf
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
            result.append(dict(prop, choices=metadata.Store.get("spells", version=self.version)))
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
        checkboxes = h3sed.gui.build(self, self._panel)
        if not self._hero.stats.spellbook:
            for c in checkboxes: c.Disable()

            prop = DATAPROPS[0]
            sizer = checkboxes[-1].ContainingSizer
            drow, dcol = (1, 0) if prop.get("vertical") else (0, 1)
            maxrows, maxcols = math.ceil(len(checkboxes) / prop["columns"]), prop["columns"]
            lastrow, lastcolumn = sizer.GetItemPosition(checkboxes[-1])
            row, column = lastrow + drow * 2, lastcolumn + dcol
            if   drow and row    > maxrows:  row, column = 0, column + 1
            elif dcol and column >= maxcols: row, column = row + 1, 0
            infolabel = wx.StaticText(self._panel, label="Hero has no spellbook.")
            sizer.Add(infolabel, pos=(row, column), border=10)
            sizer.Layout()
        return True


    def make_common_menu(self):
        """Returns wx.Menu with plugin-specific actions, like selecting or clearing all spells."""
        menu = wx.Menu()
        menu_schools = wx.Menu()
        item_select = menu.Append(wx.ID_ANY, "Add all spells")
        item_clear  = menu.Append(wx.ID_ANY, "Remove all spells")
        item_school = menu.AppendSubMenu(menu_schools, "Toggle all ..")
        for school_name in sorted(metadata.Store.get("spell_schools", version=self.version)):
            item = menu_schools.Append(wx.ID_ANY, "%s spells" % school_name)
            menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_all, school=school_name), item)
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_all, clear=False), item_select)
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_change_all, clear=True),  item_clear)
        if not self._hero or not self._hero.stats.spellbook:
            menu.Enable(item_select.Id, False)
            menu.Enable(item_clear.Id, False)
            menu.Enable(item_school.Id, False)
        return menu


    def on_change_all(self, event, clear=False, school=None):
        """
        Handler for selecting or clearing all spells, carries out and propagates change.

        @param   school  if given, toggles all given school spells on or off instead (off if all on)
        """
        def on_do(self, spells2):
            self._state.clear()
            self._state.update(spells2)
            self.parent.patch()
            evt = h3sed.gui.PluginEvent(self._panel.Id, action="render", name=self.name)
            wx.PostEvent(self._panel, evt)
            return True

        acting, action = ("Toggling all %s" % school, "toggle all %s" % school) if school else \
                         ("Removing all", "remove all") if clear else ("Adding all", "add all")
        spells2 = self._state.copy()
        if school:
            school_spells = metadata.Store.get("spell_schools", version=self.version)[school]
            if all(s in spells2 for s in school_spells): spells2.difference_update(school_spells)
            else: spells2.update(school_spells)
        elif not clear:
            spells2.update(metadata.Store.get("spells", version=self.version))
        else: spells2.clear()
        if spells2 == self._state:
            return

        label = "change %s spells: %s" % (self._hero.name, action)
        h3sed.guibase.status("%s spells" % acting, flash=conf.StatusShortFlashLength, log=True)
        callable = functools.partial(on_do, self, spells2)
        self.parent.command(callable, name=label)


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
