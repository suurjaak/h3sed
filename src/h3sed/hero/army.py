# -*- coding: utf-8 -*-
"""
Army subplugin for hero-plugin, shows hero army creatures and counts.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   21.03.2020
@modified  08.01.2026
------------------------------------------------------------------------------
"""
import logging
import functools

try: import wx
except ImportError: wx = None

import h3sed
from .. lib import util
from .. import conf
from .. import metadata


logger = logging.getLogger(__package__)


PROPS = {"name": "army", "label": "Army", "index": 2}
DATAPROPS = [{
    "type":        "itemlist",
    "orderable":   True,
    "nullable":    True,
    "min":         None,  # Populated later
    "max":         None,  # Populated later
    "menu":        None, # Populated later
    "item": [{
        "type":    "label",
        "label":   "Army slot",
      }, {
        "name":    "name",
        "type":    "combo",
        "choices": None,  # Populated later
      }, {
        "name":    "count",
        "type":    "number",
        "min":     None,  # Populated later
        "max":     None,  # Populated later
      }, {
        "name":    "placeholder",
        "type":    "window",
    }]
}]


def props():
    """Returns props for army-tab, as {label, index}."""
    return PROPS


def factory(parent, panel, version):
    """Returns a new army-plugin instance."""
    return ArmyPlugin(parent, panel, version)



class ArmyPlugin(object):
    """Provides UI functionality for listing and changing hero army stacks."""


    def __init__(self, parent, panel, version):
        self.name    = PROPS["name"]
        self.parent  = parent
        self.version = version
        self._panel  = panel  # Plugin contents panel
        self._state  = h3sed.hero.Army.factory(version)
        self._hero   = None
        self._ctrls  = []  # [{"name": wx.ComboBox, "count": wx.SpinCtrlDouble}, ]

        panel.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.on_colour_change)


    def props(self):
        """Returns props for army-tab, as [{type: "itemlist", ..}]."""
        result = []
        HERO_RANGES = metadata.Store.get("hero_ranges", version=self.version)
        CHOICES = metadata.Store.get("creatures", version=self.version)
        for prop in DATAPROPS:
            myprop = dict(prop, item=[], min=HERO_RANGES["army"][0], max=HERO_RANGES["army"][1],
                          menu=self.make_item_menu)
            for item in prop["item"]:
                if "choices" in item: item = dict(item, choices=CHOICES)
                if "min"     in item: item = dict(item, min=HERO_RANGES["army." + item["name"]][0])
                if "max"     in item: item = dict(item, max=HERO_RANGES["army." + item["name"]][1])
                myprop["item"].append(item)
            result.append(myprop)
        return result


    def state(self):
        """Returns data state for army-plugin, as [{"name": "Roc", "count": 6}, {}, ]."""
        return self._state


    def item(self):
        """Returns current hero."""
        return self._hero


    def load(self, hero):
        """Loads hero to plugin."""
        self._hero = hero
        self._state = hero.army


    def load_state(self, state):
        """Loads plugin state from given data, ignoring unknown values. Returns whether state changed."""
        state0 = self._state.copy()
        self._state.clear()
        for i, stack in enumerate(state[:len(self._state)]):
            if not isinstance(stack, (dict, type(None))):
                logger.warning("Invalid data type in army #%s: %r", i + 1, stack)
                continue  # for
            try: self._state[i].update(name=stack.get("name"), count=stack.get("count"))
            except Exception as e: logger.warning(e)
        return state0 != self._state


    def render(self):
        """
        Populates controls from state, using existing if already built.

        Returns whether new controls were created.
        """
        result, MYPROPS = False, self.props()
        if self._ctrls and all(all(x.values()) for x in self._ctrls): # All built and still valid
            CHOICES = [""] + metadata.Store.get("creatures", version=self.version)
            for i in range(len(self._state)):
                creature = None
                for prop in MYPROPS[0]["item"]:
                    if "name" not in prop: continue # for prop

                    name, choices = prop["name"], CHOICES
                    ctrl, value = self._ctrls[i][name], self._state[i].get(name)
                    if "choices" in prop:
                        choices = ([value] if value and value not in CHOICES else []) + CHOICES
                        if choices != ctrl.GetItems(): ctrl.SetItems(choices)
                        else: ctrl.Value = ""
                        creature = value
                    else: ctrl.Show(not creature if "window" == prop.get("type") else bool(creature))
                    if value is not None and hasattr(ctrl, "Value"): ctrl.Value = value
        else:
            self._ctrls, result = h3sed.gui.build(self, self._panel)[0], True
            # Hide count controls where no creature type selected
            for i in range(len(self._state)):
                creature, size = None, None
                for prop in MYPROPS[0]["item"]:
                    if "name" not in prop: continue # for prop

                    name = prop["name"]
                    ctrl, value = self._ctrls[i][name], self._state[i].get(name)
                    if "choices" in prop: creature = value
                    else:  # Show blank placeholder instead of count-control
                        if "window" == prop.get("type"): ctrl.Size = ctrl.MinSize = size
                        ctrl.Show(not creature if "window" == prop.get("type") else bool(creature))
                    size = ctrl.Size
        self._panel.Layout()
        return result


    def make_common_menu(self):
        """Returns wx.Menu with plugin-specific actions, like removing all army stacks."""
        menu = wx.Menu()
        item_clear = menu.Append(wx.ID_ANY, "Remove all army")
        item_reset = menu.Append(wx.ID_ANY, "Set army counts to 1")
        menu.AppendSubMenu(self.make_rounding_menu(), "Round army counts to ..")
        menu.Bind(wx.EVT_MENU, functools.partial(self.on_round_army, number=-1), item_reset)
        menu.Bind(wx.EVT_MENU, self.on_remove_all, item_clear)
        return menu


    def make_item_menu(self, plugin, prop, rowindex):
        """Returms wx.Menu for army row options."""
        menu = wx.Menu()
        menu_swap = wx.Menu()
        menu.AppendSubMenu(menu_swap, "Swap army slot with ..")
        for stack_index, army_stack in enumerate(self._state):
            label = "%s: %s" % (army_stack.name, army_stack.count) if army_stack else "<blank>"
            item = menu_swap.Append(wx.ID_ANY, "%s. %s" % (stack_index + 1, label))
            kwargs = dict(index1=rowindex, index2=stack_index)
            menu.Bind(wx.EVT_MENU, functools.partial(self.on_swap_stack, **kwargs), item)
            if stack_index == rowindex:
                menu_swap.Enable(item.Id, False)
        item_round = menu.AppendSubMenu(self.make_rounding_menu(rowindex), "Round army count to ..")
        if not self._state[rowindex]: menu.Enable(item_round.Id, False)
        return menu


    def make_rounding_menu(self, rowindex=None):
        """Returns wx.Menu with options to round army counts, all if not specific index."""
        menu = wx.Menu()
        for number in (-10, -100, -1000, None, 10, 100, 1000):
            if number is None:
                menu.AppendSeparator()
                continue # for number
            label = "Lower %s" % abs(number) if number < 0 else "Upper %s" % number
            item = menu.Append(wx.ID_ANY, label)
            kwargs = dict(number=number, rowindex=rowindex)
            menu.Bind(wx.EVT_MENU, functools.partial(self.on_round_army, **kwargs), item)
        return menu


    def on_round_army(self, event, number, rowindex=None):
        """
        Handler for rounding army stacks to nearest number, carries out and propagates change.

        @param   rowindex  index of single army stack to round if not all
        """
        down, number = (number < 0), abs(number)
        def on_do(self, state2):
            self._state[:] = state2
            self.parent.patch()
            evt = h3sed.gui.PluginEvent(self._panel.Id, action="render", name=self.name)
            wx.PostEvent(self._panel, evt)
            return True

        if not self._state: return
        state2 = self._state.copy()
        MIN, MAX = metadata.Store.get("hero_ranges", version=self.version)["army.count"]
        for i, army in enumerate(state2):
            if not army or rowindex is not None and i != rowindex: continue # for i, army
            if number == 1: army.count = 1
            elif army.count % number and (not down or army.count > number):
                army.count += (0 if down else number) - (army.count % number)
                army.count = min(MAX, max(MIN, army.count))

        label = "%s army " % self._hero.name
        label += "counts " if rowindex is None else "slot %s count " % (rowindex + 1)
        label += "%s to %s" % ("down " if down else "up", number)
        if state2 == self._state:
            h3sed.guibase.status("No change from rounding %s" % label,
                                 flash=conf.StatusShortFlashLength)
            return

        h3sed.guibase.status("Rounding %s" % label, flash=conf.StatusShortFlashLength, log=True)
        callable = functools.partial(on_do, self, state2)
        self.parent.command(callable, name="round %s" % label)


    def on_swap_stack(self, event, index1, index2):
        """Handler for swapping two arny positions, carries out and propagates change."""
        def on_do(self, index1, index2):
            self._state[index1], self._state[index2] = self._state[index2], self._state[index1]
            self.parent.patch()
            evt = h3sed.gui.PluginEvent(self._panel.Id, action="render", name=self.name)
            wx.PostEvent(self._panel, evt)
            return True

        if not self._state or (not self._state[index1] and not self._state[index2]):
            return
        label = "%s army slot %s and %s" % (self._hero.name, index1 + 1, index2 + 1)
        h3sed.guibase.status("Swapping %s" % label, flash=conf.StatusShortFlashLength, log=True)
        callable = functools.partial(on_do, self, index1, index2)
        self.parent.command(callable, name="swap %s" % label)


    def on_remove_all(self, event):
        """Handler for removing all hero army stacks, carries out and propagates change."""
        def on_do(self):
            self._state.clear()
            self.parent.patch()
            evt = h3sed.gui.PluginEvent(self._panel.Id, action="render", name=self.name)
            wx.PostEvent(self._panel, evt)
            return True

        if not self._state:
            return
        h3sed.guibase.status("Removing all %s army stacks" % self._hero.name,
                             flash=conf.StatusShortFlashLength, log=True)
        callable = functools.partial(on_do, self)
        self.parent.command(callable, name="remove %s army" % self._hero.name)


    def on_change(self, prop, value, ctrl, rowindex):
        """
        Handler for army change, enables or disables creature count.
        Returns True.
        """
        ctrls = [x.Window for x in ctrl.ContainingSizer.Children]
        namectrl  = next(x for x in ctrls if isinstance(x, wx.ComboBox))
        countctrl = namectrl.GetNextSibling()
        placectrl = countctrl.GetNextSibling()

        if value:
            if not self._state[rowindex]: countctrl.Value = 1
            self._state[rowindex][prop["name"]] = value
        else:
            namectrl.Value = ""
            self._state[rowindex].clear()
        countctrl.Show(bool(value))
        placectrl.Show(not value)
        return True


    def on_colour_change(self, event):
        """Handler for system colour change, refreshes panel to clear any display issues."""
        event.Skip()
        def after():
            if not self._panel: return
            for c in self._panel.Children:
                if isinstance(c, (wx.SpinCtrl, wx.SpinCtrlDouble)) and not c.Shown:
                    c.Show(), c.Hide()
            wx.CallAfter(lambda: self._panel and self._panel.Refresh())
        wx.CallLater(100, after)  # Hidden SpinCtrl arrows can become visible on colour change


def parse(hero_bytes, version):
    """Returns h3sed.hero.Army() parsed from hero bytearray army section."""
    HERO_RANGES = metadata.Store.get("hero_ranges", version=version)
    IDS = metadata.Store.get("ids", version=version)
    ID_TO_NAME = {IDS[n]: n for n in metadata.Store.get("creatures", version=version)}
    BYTEPOS = h3sed.version.adapt("hero_byte_positions", metadata.HERO_BYTE_POSITIONS,
                                  version=version)
    NAMES_POS, COUNT_POS = BYTEPOS["army_types"], BYTEPOS["army_counts"]

    army = h3sed.hero.Army.factory(version)
    for i in range(HERO_RANGES["army"][1]):
        id_bytes, count_bytes = (hero_bytes[n + i*4:n + i*4 + 4] for n in (NAMES_POS, COUNT_POS))
        creature_id, count = util.bytoi(id_bytes), util.bytoi(count_bytes)
        if not count or all(x == ord(metadata.BLANK) for x in id_bytes): continue # for i

        if creature_id not in ID_TO_NAME:
            logger.warning("Unknown army creature for version %r: 0x%X.", version, creature_id)
            creature_name = "<unknown 0x%X>" % creature_id
            metadata.Store.add("creatures", [creature_name], version=version)
            metadata.Store.add("ids", {creature_name: creature_id}, version=version)
            ID_TO_NAME[creature_id] = creature_name
        army[i].update(name=ID_TO_NAME[creature_id], count=count)
    return army


def serialize(army, hero_bytes, version, hero=None):
    """Returns new hero bytearray with updated army section."""
    HERO_RANGES = metadata.Store.get("hero_ranges", version=version)
    IDS = metadata.Store.get("ids", version=version)
    NAME_TO_ID = {n: IDS[n] for n in metadata.Store.get("creatures", version=version)}
    BYTEPOS = h3sed.version.adapt("hero_byte_positions", metadata.HERO_BYTE_POSITIONS,
                                  version=version)
    NAMES_POS, COUNT_POS = BYTEPOS["army_types"], BYTEPOS["army_counts"]

    new_bytes = hero_bytes[:]
    army0 = [] if hero is None else hero.original.get("army", [])
    for i in range(HERO_RANGES["army"][1]):
        name, count = None, None
        if i < len(army) and army[i]: name, count = army[i]["name"], army[i]["count"]
        if (not name or not count) and i < len(army0) and not (army0[i] and army0[i].get("name")):
            # Retain original bytes unchanged, as game uses both 0x00 and 0xFF
            word1 = hero.bytes0[NAMES_POS + i*4:NAMES_POS + i*4 + 4]
            word2 = hero.bytes0[COUNT_POS + i*4:COUNT_POS + i*4 + 4]
        elif count and name in NAME_TO_ID:
            word1 = util.itoby(NAME_TO_ID[name], 4)
            word2 = util.itoby(count,  4)
        else:
            word1, word2 = metadata.BLANK * 4, metadata.NULL * 4
        new_bytes[NAMES_POS + i * 4:NAMES_POS + i * 4 + 4] = word1
        new_bytes[COUNT_POS + i * 4:COUNT_POS + i * 4 + 4] = word2

    return new_bytes
