# -*- coding: utf-8 -*-
"""
Skills subplugin for hero-plugin, shows skills list.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   14.03.2020
@modified  27.01.2024
------------------------------------------------------------------------------
"""
import logging

import wx

from h3sed.lib import controls
from h3sed import gui
from h3sed import metadata
from h3sed import plugins
from h3sed.plugins.hero import POS


logger = logging.getLogger(__package__)


PROPS = {"name": "skills", "label": "Skills", "index": 1}
UIPROPS = [{
    "type":         "itemlist",
    "addable":      True,
    "removable":    True,
    "orderable":    True,
    "exclusive":    True,
    "min":           0,
    "max":          28,
    "choices":      None, # Populated later
    "item":         [{
        "name":     "name",
        "type":     "label",
    }, {
        "name":     "level",
        "type":     "combo",
        "choices":  None
    }],
}]
HINT = ("More than 8 skills can be added.\n"
        "Game will not show them on the hero screen,\n"
        "but they will be in effect.")



def props():
    """Returns props for skills-tab, as {label, index}."""
    return PROPS


def factory(savefile, parent, panel):
    """Returns a new skills-plugin instance."""
    return SkillsPlugin(savefile, parent, panel)



class SkillsPlugin(object):
    """Encapsulates skills-plugin state and behaviour."""


    def __init__(self, savefile, parent, panel):
        self.name      = PROPS["name"]
        self.parent    = parent
        self._savefile = savefile
        self._hero     = None
        self._panel    = panel  # Plugin contents panel
        self._state    = []     # [{"name": "Estates", "level": "Basic"}, {..}]


    def props(self):
        """Returns props for skills-tab, as {type: "itemlist", ..}."""
        result = []
        version = self._savefile.version
        ss = sorted(metadata.Store.get("skills", version))
        ll = metadata.Store.get("skill_levels", version)
        for prop in UIPROPS:
            myprop = dict(prop)
            if "itemlist" == prop["type"]:
                myprop.update(item=[], choices=ss)
                for item in prop["item"]:
                    myitem = dict(item, choices=ll) if "choices" in item else item
                    myprop["item"].append(myitem)
            result.append(myprop)
        return plugins.adapt(self, "props", result)


    def state(self):
        """Returns data state for skills-plugin, as [{name, level}]."""
        return self._state


    def item(self):
        """Returns current hero."""
        return self._hero


    def load(self, hero, panel=None):
        """Loads hero to plugin."""
        self._hero = hero
        self._state[:] = self.parse([hero])[0]
        hero.skills = self._state
        if panel: self._panel = panel


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values. Returns whether state changed."""
        state0 = type(self._state)(self._state)
        state = state[:self.props()[0]["max"]]
        version = self._savefile.version
        smap = {x.lower(): x for x in metadata.Store.get("skills", version)}
        lmap = {x.lower(): x for x in metadata.Store.get("skill_levels", version)}
        self._state = type(self._state)()
        for i, v in enumerate(state):
            if not isinstance(v, dict):
                logger.warning("Invalid data type in skill #%s: %r", i + 1, v)
                continue  # for
            name, level = v.get("name"), v.get("level")
            if name and name.lower() in smap and level and level.lower() in lmap:
                self._state += [{"name": smap[name.lower()], "level": lmap[level.lower()]}]
            else:
                logger.warning("Invalid skill #%s: %r", i + 1, v)
        return state0 != self._state


    def on_add(self, prop, value):
        """Adds skill at first level."""
        if any(value == x["name"] for x in self._state):
            return False
        level = next(iter(metadata.Store.get("skill_levels", self._savefile.version)))
        self._state.append({"name": value, "level": level})
        return True


    def render(self):
        """Builds plugin controls into panel. Returns True."""
        gui.build(self, self._panel)
        label = wx.StaticText(self._panel, label=HINT)
        controls.ColourManager.Manage(label, "ForegroundColour", wx.SYS_COLOUR_GRAYTEXT)
        self._panel.Sizer.Add(label, border=10, flag=wx.TOP, proportion=1)
        self._panel.Layout()
        return True


    def parse(self, heroes):
        """Returns skills states parsed from hero bytearrays, as [{name, level, slot}]."""
        result = []
        version = self._savefile.version
        IDS = {y: x[y] for x in [metadata.Store.get("ids", version)]
               for y in metadata.Store.get("skills", version)}
        LEVELNAMES = {x[y]: y for x in [metadata.Store.get("ids", version)]
                      for y in metadata.Store.get("skill_levels", version)}
        MYPOS = plugins.adapt(self, "pos", POS)

        for hero in heroes:
            values = []
            count = hero.bytes[MYPOS["skills_count"]]
            for name in metadata.Store.get("skills", version):
                pos = IDS.get(name)
                level, slot = (hero.bytes[MYPOS[k] + pos] for k in ("skills_level", "skills_slot"))
                if not level or not slot or slot > count:
                    continue # for i
                values.append({"name": name, "level": LEVELNAMES[level], "slot": slot})
            result.append(sorted(values, key=lambda x: x.pop("slot")))
        return result


    def serialize(self):
        """Returns new hero bytearray, with edited skills sections."""
        result = self._hero.bytes[:]
        version = self._savefile.version
        IDS    = {y: x[y] for x in [metadata.Store.get("ids", version)]
                  for y in metadata.Store.get("skills", version)}
        LEVELS = {y: x[y] for x in [metadata.Store.get("ids", version)]
                  for y in metadata.Store.get("skill_levels", version)}
        MYPOS = plugins.adapt(self, "pos", POS)

        levels, count = bytearray(len(IDS)), 0
        slots         = bytearray(len(IDS))
        for slot, skill in enumerate(self._state, 1):
            name, level = skill["name"], skill["level"]
            pos = IDS.get(name)
            if pos is None:
                logger.warning("Unknown skill at slot #%s: %s.", slot + 1, name)
                continue # for slot, skill
            count += 1
            levels[pos] = LEVELS[level]
            slots[pos] = slot
        result[MYPOS["skills_level"]:MYPOS["skills_level"] + len(IDS)] = levels
        result[MYPOS["skills_slot"] :MYPOS["skills_slot"]  + len(IDS)] = slots
        result[MYPOS["skills_count"]] = count

        return result
