# -*- coding: utf-8 -*-
"""
Profile subplugin for town-plugin, parses town profile like player faction.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   16.09.2026
@modified  13.11.2026
------------------------------------------------------------------------------
"""
import functools

try: import wx
except ImportError: wx = None

import h3sed
from .. lib.i18n import translate as __
from .. import conf


PROPS = {"name": "profile", "label": "Profile"}
DATAPROPS = [{
    "name":      "faction",
    "label":     "Faction",
    "type":      None,  # Populated later
    "readonly":  True,
}, {
    "name":      "type",
    "label":     "Type",
    "type":      "text",
    "readonly":  True,
    "format":    None,  # Populated later
}, {
    "name":      "location",
    "label":     "Location",
    "type":      "text",
    "readonly":  True,
    "format":    None,  # Populated later
    "tooltip":   None,  # Populated later
}, {
    "name":      "garrison_hero",
    "label":     "Garrisoned",
    "type":      None,  # Populated later
    "readonly":  True,
}, {
    "name":      "visiting_hero",
    "label":     "Visiting",
    "type":      None,  # Populated later
    "readonly":  True,
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
            if "type" == prop["name"] and "type" in prop:
                prop = dict(prop, format=lambda: __(self._state.format_type()))
            if "location" == prop["name"] and "format" in prop:
                prop = dict(prop, format=self._state.format_location)
            if "location" == prop["name"] and "tooltip" in prop:
                prop = dict(prop, tooltip=lambda: self._state.format_location(long=True))
            if prop["name"] in ("faction", "garrison_hero", "visiting_hero"):
                if prop.get("type") is None:
                    prop = dict(prop, type=functools.partial(self.make_optional_link, prop))
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


    def make_optional_link(self, prop):
        """Returns wx component for displaying a clickable link or text, depending on prop content."""
        target = self._state[prop["name"]]
        label = str(target or "")
        if "faction" == prop["name"]: label = self._state.format_faction()

        if not label or ("faction" == prop["name"] and "neutral" == label):
            result = wx.TextCtrl(self._panel, style=wx.TE_READONLY | wx.BORDER_NONE, name=prop["name"])
            result.Value = __(label)
        else:
            kind, label = ("faction", __(label)) if "faction" == prop["name"] else ("hero", label)
            handler = lambda: self.on_click_entity(target, kind)
            result = h3sed.lib.controls.make_hyperlink(self._panel, label, handler, conf.LinkColour)
            result.ToolTip = __("Open %s page for %%s" % kind, label.format())
        return result


    def on_click_entity(self, value, kind):
        """Handler for clicking hero or faction, propagates event to open relevant page."""
        name = value.get_name_ident() if isinstance(value, h3sed.common.NamedEntity) else value
        evt_args = {"action": "open", "kind": kind, "name": name}
        wx.PostEvent(self._panel, h3sed.gui.PluginEvent(self._panel.Id, **evt_args))
