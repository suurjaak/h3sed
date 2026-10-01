# -*- coding: utf-8 -*-
"""
Profile subplugin for town-plugin, parses town profile like player faction.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   16.09.2026
@modified  01.10.2026
------------------------------------------------------------------------------
"""
try: import wx
except ImportError: wx = None

import h3sed
from .. lib.i18n import translate as __


PROPS = {"name": "profile", "label": "Profile", "index": 6}
DATAPROPS = [{
    "name":      "faction",
    "type":      "text",
    "label":     "Faction",
    "readonly":  True,
    "format":    None,  # Populated later
}, {
    "name":      "type",
    "type":      "text",
    "label":     "Type",
    "readonly":  True,
    "format":    None,  # Populated later
}, {
    "name":      "location",
    "type":      "text",
    "label":     "Location",
    "readonly":  True,
    "format":    None,  # Populated later
    "tooltip":   None,  # Populated later
}, {
    "name":      "garrison",
    "type":      "link",
    "label":     "Garrisoned",
    "readonly":  True,
    "format":    None,  # Populated later
    "handler":   None,  # Populated later
    "tooltip":   None,  # Populated later
}, {
    "name":      "visiting",
    "type":      "link",
    "label":     "Visiting",
    "readonly":  True,
    "format":    None,  # Populated later
    "handler":   None,  # Populated later
    "tooltip":   None,  # Populated later
}]


def props():
    """Returns props for profile-tab, as {label, index}."""
    return PROPS


def factory(parent, panel, version):
    """Returns a new profile-plugin instance."""
    return ProfilePlugin(parent, panel, version)



class ProfilePlugin(object):
    """Provides UI functionality for viewing town profile data like location."""


    def __init__(self, parent, panel, version):
        self.name    = PROPS["name"]
        self.parent  = parent
        self.version = version
        self._panel  = panel  # Plugin contents panel
        self._state  = h3sed.town.Profile.factory(version)
        self._town   = None


    def props(self):
        """Returns UI props for profile-tab, as [{type: "text", ..}]."""
        result = []
        for prop in DATAPROPS:
            if "faction" == prop["name"] and "format" in prop:
                prop = dict(prop, format=lambda: __(self._state.format_faction()))
            if "type" == prop["name"] and "type" in prop:
                prop = dict(prop, format=lambda: __(self._state.format_type()))
            if "location" == prop["name"] and "format" in prop:
                prop = dict(prop, format=self._state.format_location)
            if "location" == prop["name"] and "tooltip" in prop:
                prop = dict(prop, tooltip=lambda: self._state.format_location(long=True))
            if "garrison" == prop["name"] and "format" in prop:
                prop = dict(prop, format=lambda: str(self._state.garrison_hero or ""))
            if "garrison" == prop["name"] and "handler" in prop:
                prop = dict(prop, handler=lambda: self.on_click_hero(self._state.garrison_hero))
            if "garrison" == prop["name"] and "tooltip" in prop:
                prop = dict(prop, tooltip=lambda: self.make_hero_tooltip(self._state.garrison_hero))
            if "visiting" == prop["name"] and "format" in prop:
                prop = dict(prop, format=lambda: str(self._state.visiting_hero or ""))
            if "visiting" == prop["name"] and "handler" in prop:
                prop = dict(prop, handler=lambda: self.on_click_hero(self._state.visiting_hero))
            if "visiting" == prop["name"] and "tooltip" in prop:
                prop = dict(prop, tooltip=lambda: self.make_hero_tooltip(self._state.visiting_hero))
            result.append(prop)
        return result


    def state(self):
        """Returns data state for profile-plugin, as h3sed.town.Profile."""
        return self._state


    def item(self):
        """Returns current town."""
        return self._town


    def load(self, town):
        """Loads town to plugin."""
        self._town = town
        self._state = town.profile


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values. Returns whether state changed."""
        state0 = self._state.copy()
        self._state.clear()
        for attribute, value in state.items():
            if attribute in self._state:
                self._state[attribute] = value
        return state0 != self._state


    def make_hero_tooltip(self, hero):
        """Returns tooltip string for hero name link."""
        return __("Open hero page for %s", hero) if hero else ""


    def on_click_hero(self, hero):
        """Handler for clicking garrisoned or visiting hero, propagates event to open hero page."""
        evt_args = {"action": "open", "kind": "hero", "name": hero.get_name_ident()}
        wx.PostEvent(self._panel, h3sed.gui.PluginEvent(self._panel.Id, **evt_args))
