# -*- coding: utf-8 -*-
"""
Skills subplugin for hero-plugin, shows skills list.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   14.03.2020
@modified  17.09.2025
------------------------------------------------------------------------------
"""
import functools
import logging

try: import wx
except ImportError: wx = None

import h3sed
from .. lib import controls
from .. import metadata
from .. import conf


logger = logging.getLogger(__package__)


PROPS = {"name": "skills", "label": "Skills", "index": 1}
DATAPROPS = [{
    "type":         "itemlist",
    "addable":      True,
    "removable":    True,
    "orderable":    True,
    "exclusive":    True,
    "min":          None, # Populated later
    "max":          None, # Populated later
    "choices":      None, # Populated later
    "menu":         None, # Populated later
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


def factory(parent, panel, version):
    """Returns a new skills-plugin instance."""
    return SkillsPlugin(parent, panel, version)



class SkillsPlugin(object):
    """Provides UI functionality for listing and changing skills learned by hero."""


    def __init__(self, parent, panel, version):
        self.name    = PROPS["name"]
        self.parent  = parent
        self.version = version
        self._panel  = panel  # Plugin contents panel
        self._state  = h3sed.hero.Skills.factory(version)
        self._hero   = None


    def props(self):
        """Returns props for skills-tab, as {type: "itemlist", ..}."""
        result = []
        MIN, MAX = metadata.Store.get("hero_ranges", version=self.version)["skills"]
        SKILLS = sorted(metadata.Store.get("skills", version=self.version))
        SKILL_LEVELS = metadata.Store.get("skill_levels", version=self.version)
        for prop in DATAPROPS:
            myprop = dict(prop)
            if "itemlist" == prop["type"]:
                myprop.update(item=[], choices=SKILLS, min=MIN, max=MAX, menu=self.make_item_menu)
                for item in prop["item"]:
                    if "choices" in item: item = dict(item, choices=SKILL_LEVELS)
                    myprop["item"].append(item)
            result.append(myprop)
        return result


    def state(self):
        """Returns data state for skills-plugin, as [{name, level}]."""
        return self._state


    def item(self):
        """Returns current hero."""
        return self._hero


    def load(self, hero):
        """Loads hero to plugin."""
        self._hero = hero
        self._state = hero.skills


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values. Returns whether state changed."""
        MIN, MAX = metadata.Store.get("hero_ranges", version=self.version)["skills"]
        state0 = self._state.copy()
        self._state.clear()
        for i, skill in enumerate(state[:MAX]):
            if not isinstance(skill, dict):
                logger.warning("Invalid data type in skill #%s: %r", i + 1, skill)
                continue  # for
            try: self._state.append(name=skill.get("name"), level=skill.get("level"))
            except Exception as e: logger.warning(e)
        return state0 != self._state


    def render(self):
        """Builds plugin controls into panel. Returns True."""
        focused_index = -1 # Remember focused position, as all controls get destroyed and rebuilt
        focused_ctrl = self._panel.FindFocus()
        if isinstance(focused_ctrl, wx.Button) and focused_ctrl.Parent is self._panel \
        and isinstance(focused_ctrl.ContainingSizer, wx.BoxSizer): # One of up-down-remove buttons
            focused_index = self._panel.Children.index(focused_ctrl)

        h3sed.gui.build(self, self._panel)
        label = wx.StaticText(self._panel, label=HINT)
        controls.ColourManager.Manage(label, "ForegroundColour", wx.SYS_COLOUR_GRAYTEXT)
        self._panel.Sizer.Add(label, border=10, flag=wx.TOP, proportion=1)
        self._panel.Layout()

        if focused_index > len(self._panel.Children) - 1:
            focused_index -= 5 # Last row removed: shift to previous by label+combo+up+down+remove
        if focused_index > 0:
            self._panel.Children[focused_index].SetFocus()

        return True


    def make_common_menu(self):
        """Returns wx.Menu with plugin-specific actions, like removing all skills."""
        SKILL_LEVELS = metadata.Store.get("skill_levels", version=self.version)

        menu = wx.Menu()
        menu_level = wx.Menu()
        item_clear = menu.Append(wx.ID_ANY, "Remove all skills")
        menu.AppendSubMenu(menu_level, "Set skill levels to ..")
        for level_name in SKILL_LEVELS:
            item = menu_level.Append(wx.ID_ANY, level_name)
            menu.Bind(wx.EVT_MENU, functools.partial(self.on_set_level, level_name=level_name), item)
        menu.Bind(wx.EVT_MENU, self.on_remove_all, item_clear)
        return menu


    def make_item_menu(self, plugin, prop, rowindex):
        """Returms wx.Menu for a skills-row options."""
        SKILLS = sorted(metadata.Store.get("skills", version=self.version))

        menu = wx.Menu()
        menu_change = wx.Menu()
        menu_swap   = wx.Menu()
        item_change = menu.AppendSubMenu(menu_change, "Change skill to ..")
        item_swap   = menu.AppendSubMenu(menu_swap,   "Swap skill slot with ..")
        for skill_name in SKILLS:
            #if skill_name in self._state: continue # for skill_name
            item = menu_change.Append(wx.ID_ANY, skill_name)
            kwargs = dict(rowindex=rowindex, skill_name2=skill_name)
            menu.Bind(wx.EVT_MENU, functools.partial(self.on_item_menu_option, **kwargs), item)
            if skill_name in self._state:
                menu_change.Enable(item.Id, False)
        for index, skill in enumerate(self._state):
            label = "%s. %s\t(%s)" % (index + 1, skill.name, skill.level)
            item = menu_swap.Append(wx.ID_ANY, label)
            kwargs = dict(rowindex=rowindex, rowindex2=index)
            menu.Bind(wx.EVT_MENU, functools.partial(self.on_item_menu_option, **kwargs), item)
            if index == rowindex:
                menu_swap.Enable(item.Id, False)
        if not menu_change.MenuItemCount:
            menu.Enable(item_change.Id, False)
        if not menu_swap.MenuItemCount:
            menu.Enable(item_swap.Id, False)
        return menu


    def on_add(self, prop, value):
        """Adds skill at first level."""
        if any(value == x["name"] for x in self._state):
            return False
        self._state.append(name=value)
        return True


    def on_item_menu_option(self, event, rowindex, rowindex2=None, skill_name2=None):
        """Handler for selection in row options-menu, carries out and propagates change."""
        def on_do(self, rowindex, rowindex2, skill_name2):
            state = self._state
            if rowindex2 is not None:
                state[rowindex], state[rowindex2] = state[rowindex2], state[rowindex]
            else:
                state[rowindex].name = skill_name2
            self.parent.patch()
            evt = h3sed.gui.PluginEvent(self._panel.Id, action="render", name=self.name)
            wx.PostEvent(self._panel, evt)
            return True

        skill_name1 = self._state[rowindex].name
        skill_name2 = skill_name2 if rowindex2 is None else self._state[rowindex2].name
        if rowindex2 is None: acting, action, adverb = ("Changing", "change", "to")
        else: acting, action, adverb = ("Swapping", "swap", "with")
        label = "%s skills: %s %s %s" % (self._hero.name, skill_name1, adverb, skill_name2)
        h3sed.guibase.status("%s %s" % (acting, label), flash=conf.StatusShortFlashLength, log=True)
        callable = functools.partial(on_do, self, rowindex, rowindex2, skill_name2)
        self.parent.command(callable, name="%s %s" % (action, label))


    def on_remove_all(self, event):
        """Handler for removing all hero skills, carries out and propagates change."""
        def on_do(self):
            self._state.clear()
            self.parent.patch()
            evt = h3sed.gui.PluginEvent(self._panel.Id, action="render", name=self.name)
            wx.PostEvent(self._panel, evt)
            return True

        if not self._state:
            return
        h3sed.guibase.status("Removing all %s skills" % self._hero.name,
                             flash=conf.StatusShortFlashLength, log=True)
        callable = functools.partial(on_do, self)
        self.parent.command(callable, name="remove %s skills" % self._hero.name)


    def on_set_level(self, event, level_name):
        """Handler for removing all hero skills, carries out and propagates change."""
        def on_do(self, level_name):
            for skill in self._state: skill.level = level_name
            self.parent.patch()
            evt = h3sed.gui.PluginEvent(self._panel.Id, action="render", name=self.name)
            wx.PostEvent(self._panel, evt)
            return True

        if not self._state or all(x.level == level_name for x in self._state):
            return
        label = "%s skills to %s" % (self._hero.name, level_name)
        h3sed.guibase.status("Setting %s" % label, flash=conf.StatusShortFlashLength, log=True)
        callable = functools.partial(on_do, self, level_name)
        self.parent.command(callable, name="set %s" % label)


def parse(hero_bytes, version):
    """Returns h3sed.hero.Skills() parsed from hero bytearray skills section."""
    IDS = metadata.Store.get("ids", version=version)
    LEVEL_ID_TO_NAME = {IDS[n]: n for n in metadata.Store.get("skill_levels", version=version)}
    BYTEPOS = h3sed.version.adapt("hero_byte_positions", metadata.HERO_BYTE_POSITIONS,
                                  version=version)

    skills = h3sed.hero.Skills.factory(version)
    count = hero_bytes[BYTEPOS["skills_count"]]
    values = []
    for skill_name in metadata.Store.get("skills", version=version):
        skill_pos = IDS.get(skill_name)
        level, slot = (hero_bytes[BYTEPOS[k] + skill_pos] for k in ("skills_level", "skills_slot"))
        if not level or not slot or slot > count:
            continue # for skill_name
        values.append({"name": skill_name, "level": LEVEL_ID_TO_NAME[level], "slot": slot})

    skills.extend(sorted(values, key=lambda x: x.pop("slot")))
    return skills


def serialize(skills, hero_bytes, version, hero=None):
    """Returns new hero bytearray with updated skills section."""
    IDS = metadata.Store.get("ids", version=version)
    SKILLS = metadata.Store.get("skills", version=version)
    SKILL_TO_ID = {n: IDS[n] for n in SKILLS}
    LEVEL_TO_ID = {n: IDS[n] for n in metadata.Store.get("skill_levels", version=version)}
    BYTEPOS = h3sed.version.adapt("hero_byte_positions", metadata.HERO_BYTE_POSITIONS,
                                  version=version)

    new_bytes = hero_bytes[:]
    count = 0
    levels, slots = bytearray(len(SKILLS)), bytearray(len(SKILLS))
    for slot, skill in enumerate(skills, 1):
        skill_pos = SKILL_TO_ID.get(skill.name)
        if skill_pos is None:
            logger.warning("Unknown skill at slot #%s: %s.", slot, skill.name)
            continue # for slot, skill
        count += 1
        levels[skill_pos] = LEVEL_TO_ID[skill.level]
        slots[skill_pos] = slot

    new_bytes[BYTEPOS["skills_count"]] = count
    new_bytes[BYTEPOS["skills_level"]:BYTEPOS["skills_level"] + len(SKILLS)] = levels
    new_bytes[BYTEPOS["skills_slot" ]:BYTEPOS["skills_slot" ] + len(SKILLS)] = slots
    return new_bytes
