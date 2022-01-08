# -*- coding: utf-8 -*-
"""
Skills subplugin for hero-plugin, shows skills list.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   14.03.2020
@modified  12.04.2020
------------------------------------------------------------------------------
"""
from collections import OrderedDict
import logging

from h3sed import data
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
}, {
    "type":     "label",
    "label":    "More than 8 skills can be added.\n"
                "Game will not show them on the hero screen,\n"
                "but they will be in effect.",
}]



def props():
    """Returns props for skills-tab, as {label, index}."""
    return PROPS


def factory(parent, hero, panel):
    """Returns a new skills-plugin instance."""
    return SkillsPlugin(parent, hero, panel)



class SkillsPlugin(object):
    """Encapsulates skills-plugin state and behaviour."""


    def __init__(self, parent, hero, panel):
        self.name    = PROPS["name"]
        self.parent  = parent
        self._hero   = hero
        self._panel  = panel # Plugin contents panel
        self._state  = []    # [{"name": "Estates", "level": "Basic"}, {..}]
        if hero:
            self.parse(hero.bytes)
            hero.skills = self._state


    def props(self):
        """Returns props for skills-tab, as {type: "itemlist", ..}."""
        result = []
        ver = self._hero.savefile.version
        ss = sorted(data.Store.get("skills", version=ver))
        ll = data.Store.get("skill_levels", version=ver)
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


    def load(self, hero, panel=None):
        """Loads hero to plugin."""
        self._hero = hero
        self._state[:] = []
        if panel: self._panel = panel
        if hero:
            self.parse(hero.bytes)
            hero.skills = self._state


    def on_add(self, prop, value):
        """Adds skill at first level."""
        if any(value == x["name"] for x in self._state):
            return False
        level = next(iter(data.Store.get("skill_levels")))
        self._state.append({"name": value, "level": level})
        return True


    def parse(self, bytes):
        """Builds skills state from hero bytearray."""
        result = []
        IDS    = {y: x[y] for x in [data.Store.get("ids")]
                  for y in data.Store.get("skills")}
        LEVELNAMES = {x[y]: y for x in [data.Store.get("ids")]
                      for y in data.Store.get("skill_levels")}
        MYPOS = plugins.adapt(self, "pos", POS)

        count = bytes[MYPOS["skills_count"]]
        ver = self._hero.savefile.version
        for name in data.Store.get("skills", version=ver):
            pos = IDS.get(name)
            level, slot = bytes[MYPOS["skills_level"] + pos], bytes[MYPOS["skills_slot"] + pos]
            if not level or not slot or slot > count:
                continue # for i
            result.append({"name": name, "level": LEVELNAMES[level], "slot": slot})
        self._state[:] = sorted(result, key=lambda x: x.pop("slot"))


    def serialize(self):
        """Returns new hero bytearray, with edited skills sections."""
        result = self._hero.bytes[:]
        ver = self._hero.savefile.version
        IDS    = {y: x[y] for x in [data.Store.get("ids")]
                  for y in data.Store.get("skills", version=ver)}
        LEVELS = {y: x[y] for x in [data.Store.get("ids")]
                  for y in data.Store.get("skill_levels")}
        MYPOS = plugins.adapt(self, "pos", POS)

        levels, count = bytearray(len(IDS)), 0
        slots         = bytearray(len(IDS))
        for slot, skill in enumerate(self._state, 1):
            name, level = skill["name"], skill["level"]
            pos = IDS.get(name)
            if pos is None:
                logger.warn("Unknown skill at slot #%s: %s.", slot + 1, name)
                continue # for slot, skill
            count += 1
            levels[pos] = LEVELS[level]
            slots[pos] = slot
        result[MYPOS["skills_level"]:MYPOS["skills_level"] + len(IDS)] = levels
        result[MYPOS["skills_slot"] :MYPOS["skills_slot"]  + len(IDS)] = slots
        result[MYPOS["skills_count"]] = count

        #if result[MYPOS["skills_level"]:MYPOS["skills_level"] + len(IDS)] != self._hero.bytes[MYPOS["skills_level"]:MYPOS["skills_level"] + len(IDS)]: # @todo remove
        #    logger.info("skills: changed. %s vs %s.", map(int, self._hero.bytes), map(int, result))

        return result
