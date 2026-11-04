# -*- coding: utf-8 -*-
"""
Heroes subplugin for faction-plugin, manages player on-map hero order and lists others.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   02.11.2026
@modified  04.11.2026
------------------------------------------------------------------------------
"""
import functools
import logging

try: import wx
except ImportError: wx = None

import h3sed
try: from .. lib import controls
except ImportError: controls = None
from .. lib.i18n import translate as __
from .. lib import util
from .. import conf
from .. import metadata


logger = logging.getLogger(__package__)


PROPS = {"name": "heroes", "label": "Heroes"}
DATAPROPS = [{
    "type":          "label",
    "label":         "Adventuring",
}, {
    "type":          "itemlist",
    "orderable":     True,
    "item":          [{
        "type":      "label",
        "label":     " ",
    }, {
        "name":      "hero",
        "type":      "link",
        "format":    str,
        "handler":   None,  # Populated later
        "tooltip":   None,  # Populated later
    }, {
        "name":      "town",
        "type":      "link",
        "format":    lambda hero: str(hero.profile.town) if hero.profile.town else "",
        "handler":   None,  # Populated later
        "tooltip":   None,  # Populated later
    }],
}]



def props():
    """Returns props for heroes-tab, as {label, index}."""
    return PROPS


def factory(parent, panel, version):
    """Returns a new hero order plugin instance."""
    return FactionHeroesPlugin(parent, panel, version)



class FactionHeroesPlugin(object):
    """Provides UI functionality for listing and rearranging faction heroes."""

    def __init__(self, parent, panel, version):
        self.name     = PROPS["name"]
        self.parent   = parent
        self.version  = version
        self._panel   = panel # Plugin contents panel
        self._state   = []
        self._faction = None


    def props(self):
        """Returns props for hero order tab, as [{type: "link", ..}]."""
        result = []
        binder = lambda f, kind: (lambda index: f(self._state[index], kind))
        for prop in DATAPROPS:
            myprop = dict(prop)
            if "itemlist" == prop["type"]:
                myprop.update(item=[])
                for item in prop["item"]:
                    if "handler" in item:
                        item = dict(item, handler=binder(self.on_click_entity, item["name"]))
                    if "tooltip" in item:
                        item = dict(item, tooltip=binder(self.make_entity_tooltip, item["name"]))
                    myprop["item"].append(item)
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
        self._state = faction.hero_order


    def load_state(self, state):
        """Loads plugin state from given data, ignoring invalid values. Returns whether state changed."""
        if any(not isinstance(x, h3sed.hero.Hero) for x in state):
            heromap = {str(h): h for h in self._state}
            state = [heromap.get(name) for name in state]
        state = [hero for hero in state if hero in self._state] 
        if len(state) != len(self._state):
            return False

        state0 = self._state.copy()
        self._state.clear()
        for hero in state:
            self._state.append(hero)
        return state0 != self._state


    def render(self):
        """Builds plugin controls into panel. Returns True."""
        h3sed.gui.build(self, self._panel)

        gridsizer = self._panel.Sizer.Children[0].Sizer
        header = wx.StaticText(self._panel, label=__("Garrisoned"))
        controls.ColourManager.Manage(header, "ForegroundColour", wx.SYS_COLOUR_GRAYTEXT)
        gridsizer.Add(header, pos=(gridsizer.Rows, 0), span=(1, 2))

        link_args = {"parent": self._panel, "size": (80, -1), "colour": conf.LinkColour}
        garrisoned_heroes = [h for h in self._faction.heroes if h not in self._state]
        for i, hero in enumerate(garrisoned_heroes, len(self._state)):
            c0 = wx.StaticText(self._panel, label="%s." % (i + 1))

            handler = functools.partial(self.on_click_entity, hero, "hero")
            c1 = controls.make_hyperlink(label=str(hero), handler=handler, **link_args)
            c1.ToolTip = self.make_entity_tooltip(hero, "hero")

            handler = functools.partial(self.on_click_entity, hero, "town")
            c2 = controls.make_hyperlink(label=str(hero.profile.town), handler=handler, **link_args)
            c2.ToolTip = self.make_entity_tooltip(hero, "town")

            bsizer = wx.BoxSizer(wx.HORIZONTAL)
            bsizer.Add(c1, flag=wx.ALIGN_CENTER_VERTICAL)
            bsizer.Add(c2, flag=wx.ALIGN_CENTER_VERTICAL)
            gridsizer.Add(c0, pos=(gridsizer.Rows, 0), flag=wx.ALIGN_CENTER_VERTICAL)
            gridsizer.Add(bsizer, pos=(gridsizer.Rows - 1, 1))
        self._panel.Layout()
        return True


    def make_entity_tooltip(self, hero, kind):
        """Returns tooltip string for hero or town name link."""
        if not hero: return ""
        entity = hero.profile.town if "town" == kind else hero
        return __("Open %s page for %%s" % kind, entity)


    def on_click_entity(self, hero, kind):
        """Handler for clicking a hero or town, propagates event to open entity page."""
        entity = hero.profile.town if "town" == kind else hero
        evt_args = {"action": "open", "kind": kind, "name": entity.get_name_ident()}
        wx.PostEvent(self._panel, h3sed.gui.PluginEvent(self._panel.Id, **evt_args))



def parse(faction_bytes, version, savefile):
    """Returns heroes list parsed from faction bytearray."""
    DATA_RANGES = h3sed.version.adapt("data_ranges", metadata.DATA_RANGES, version=version)
    BYTEPOS = h3sed.version.adapt("faction_byte_positions", metadata.FACTION_BYTE_POSITIONS,
                                  version=version)

    heroes_by_index = {h.index: h for h in savefile.heroes}

    hero_order = []
    for hero_index in range(DATA_RANGES["faction.heroes"][1]):
        pos = BYTEPOS["hero_order"] + hero_index
        binary, value = faction_bytes[pos:pos + 1], None
        if binary == metadata.BLANK:
            break # for hero_index

        try:
            value = util.bytoi(binary)
            hero_order.append(heroes_by_index[value])
        except Exception as e:
            logger.warning("Failed to parse faction hero #%s with index %s: %s",
                           hero_index, value, e)
    return hero_order


def serialize(hero_order, faction_bytes, version):
    """Returns new faction bytearray with updated resource sections."""
    DATA_RANGES = h3sed.version.adapt("data_ranges", metadata.DATA_RANGES, version=version)
    BYTEPOS = h3sed.version.adapt("faction_byte_positions", metadata.FACTION_BYTE_POSITIONS,
                                  version=version)

    new_bytes = faction_bytes[:]
    for hero_index in range(DATA_RANGES["faction.heroes"][1]):
        pos = BYTEPOS["hero_order"] + hero_index
        # Retain original bytes if possible: some savegames have 00 after FF
        binary = new_bytes[pos:pos + 1]
        if hero_index < len(hero_order):
            binary = util.itoby(hero_order[hero_index].index, 1)
        new_bytes[pos:pos + 1] = binary
    return new_bytes
