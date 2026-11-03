# -*- coding: utf-8 -*-
"""
Towns subplugin for faction-plugin, shows faction towns.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   03.11.2026
@modified  03.11.2026
------------------------------------------------------------------------------
"""
import logging

try: import wx
except ImportError: wx = None

import h3sed
try: from .. lib import controls
except ImportError: controls = None
from .. lib.i18n import translate as __


logger = logging.getLogger(__package__)


PROPS = {"name": "towns", "label": "Towns", "index": 2}
DATAPROPS = [{
    "type":          "itemlist",
    "header":        None, # Populated later
    "numbered":      True,
    "item":          [{
        "type":      "label",
        "label":     " ",
    }, {
        "name":      "town",
        "type":      "link",
        "format":    str,
        "handler":   None,  # Populated later
        "tooltip":   None,  # Populated later
    }, {
        "name":      "visiting_hero",
        "type":      "link",
        "format":    lambda town: str(town.profile.visiting_hero) if town.profile.visiting_hero else "",
        "handler":   None,  # Populated later
        "tooltip":   None,  # Populated later
    }, {
        "name":      "garrison_hero",
        "type":      "link",
        "format":    lambda town: str(town.profile.garrison_hero) if town.profile.garrison_hero else "",
        "handler":   None,  # Populated later
        "tooltip":   None,  # Populated later
    }],
}]



def props():
    """Returns props for towns-tab, as {label, index}."""
    return PROPS


def factory(parent, panel, version):
    """Returns a new towns plugin instance."""
    return FactionTownsPlugin(parent, panel, version)



class FactionTownsPlugin(object):
    """Provides UI functionality for listing faction towns."""

    def __init__(self, parent, panel, version):
        self.name     = PROPS["name"]
        self.parent   = parent
        self.version  = version
        self._panel   = panel # Plugin contents panel
        self._state   = []
        self._faction = None


    def props(self):
        """Returns props for faction towns tab, as [{type: "link", ..}]."""
        result = []
        binder = lambda f, kind: (lambda index: f(self._state[index], kind))
        for prop in DATAPROPS:
            myprop = dict(prop)
            if "itemlist" == prop["type"]:
                if "header" in prop:
                    myprop = dict(myprop, header=self.make_header)
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
        self._state = faction.towns


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values. Returns whether state changed."""
        state0 = self._state.copy()
        self._state.clear()
        for town in state:
            self._state.append(town)
        return state0 != self._state


    def make_header(self, sizer):
        """Adds header row to sizer, if any towns with a hero, returns whether header added."""
        if not any(t.profile.visiting_hero or t.profile.garrison_hero for t in self._state):
            return False

        t1 = wx.StaticText(self._panel, label="", size=(80, -1))
        t2 = wx.StaticText(self._panel, label=__("Visiting hero"), size=(80, -1))
        t3 = wx.StaticText(self._panel, label=__("Garrison hero"), size=(120, -1))
        controls.ColourManager.Manage(t2, "ForegroundColour", wx.SYS_COLOUR_GRAYTEXT)
        controls.ColourManager.Manage(t3, "ForegroundColour", wx.SYS_COLOUR_GRAYTEXT)
        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        bsizer.Add(t1, flag=wx.ALIGN_CENTER_VERTICAL)
        bsizer.Add(t2, flag=wx.ALIGN_CENTER_VERTICAL)
        bsizer.Add(t3, flag=wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(bsizer, pos=(sizer.Rows, 1), span=(1, 2))
        return True


    def is_readonly(self):
        """Returns True."""
        return True


    def make_entity_tooltip(self, town, kind):
        """Returns tooltip string for town or hero name link."""
        if not town: return ""
        entity = town.profile.visiting_hero if "visiting_hero" == kind else \
                 town.profile.garrison_hero if "garrison_hero" == kind else town
        return __("Open %s page for %%s" % ("town" if "town" == kind else "hero"), entity)


    def on_click_entity(self, town, kind):
        """Handler for clicking a town or hero, propagates event to open entity page."""
        if "town" == kind: entity = town
        else: kind, entity = "hero", town.profile[kind]
        evt_args = {"action": "open", "kind": kind, "name": entity.get_name_ident()}
        wx.PostEvent(self._panel, h3sed.gui.PluginEvent(self._panel.Id, **evt_args))
