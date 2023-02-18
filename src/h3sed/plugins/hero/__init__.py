# -*- coding: utf-8 -*-
"""
Hero plugin, parses savefile for heroes.

All hero specifics are handled by subplugins in file directory, auto-loaded.

If version-plugin is available, tries to parse file as the latest version,
working backwards to earliest, chooses version which yields more heroes.


Subplugin modules are expected to have the following API (all methods optional):

    def init():
        '''Called at plugin load.'''

    def props():
        '''
        Returns plugin props {name, ?label, ?index}.
        Label is used as plugin tab label, falling back to plugin name.
        Index is used for sorting plugins.
        '''

    def factory(parent, hero, panel):
        '''
        Returns new plugin instance, if plugin instantiable.

        @param   parent  parent plugin (hero-plugin)
        @param   hero    plugins.hero.Hero instance
        @param   panel   wx.Panel for plugin render
        '''


Subplugin instances are expected to have the following API:

    def props(self):
        '''Optional. Returns props for subplugin, if using gui.build().'''

    def state(self):
        '''Optional. Returns subplugin state for gui.build().'''

    def item(self):
        '''Mandatory. Returns current hero.'''

    def load(self, hero, panel=None):
        '''Mandatory. Loads subplugin state from hero, optionally resetting panel.'''

    def load_state(self, state):
        '''Optional. Loads subplugin state from given data. Returns whether state changed.'''

    def serialize(self):
        '''Mandatory. Returns new hero bytearray from subplugin state.'''

    def render(self):
        '''
        Optional. Renders subplugin into panel given in factory(),
        if subplugin not renderable with gui.build().
        '''

    def on_add(self, prop, value):
        '''
        Optional. Handler for adding something in subplugin
        (like a secondary skill), returning operation success.
        '''

    def on_change(self, prop, row, ctrl, value):
        '''
        Optional. Handler for changing something in subplugin
        (like secondary skill level), returning operation success.
        '''

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   14.03.2020
@modified  18.02.2023
------------------------------------------------------------------------------
"""
import copy
import functools
import glob
import importlib
import json
import logging
import os
import re
import sys

import yaml
import wx
import wx.lib.agw.flatnotebook

from h3sed import conf
from h3sed import gui
from h3sed import guibase
from h3sed import images
from h3sed import metadata
from h3sed import plugins
from h3sed import templates
from h3sed.lib.vendor import step
from h3sed.lib import controls
from h3sed.lib import util
from h3sed.lib import wx_accel

logger = logging.getLogger(__package__)


PLUGINS = [] # Loaded plugins as [{name, module}, ]
PROPS   = {"name": "hero", "label": "Hero", "icon": images.PageHero}


# Index for byte start of various attributes in hero bytearray
POS = {
    "movement_total":     0, # Movement points in total
    "movement_left":      4, # Movement points remaining

    "exp":                8, # Experience points
    "mana":              16, # Spell points remaining
    "level":             18, # Hero level

    "skills_count":      12, # Skills count
    "skills_level":     151, # Skill levels
    "skills_slot":      179, # Skill slots

    "army_types":        82, # Creature type IDs
    "army_counts":      110, # Creature counts

    "spells_book":      211, # Spells in book
    "spells_available": 281, # All spells available for casting

    "attack":           207, # Primary attribute: Attack
    "defense":          208, # Primary attribute: Defense
    "power":            209, # Primary attribute: Spell Power
    "knowledge":        210, # Primary attribute: Knowledge

    "helm":             351, # Helm slot
    "cloak":            359, # Cloak slot
    "neck":             367, # Neck slot
    "weapon":           375, # Weapon slot
    "shield":           383, # Shield slot
    "armor":            391, # Armor slot
    "lefthand":         399, # Left hand slot
    "righthand":        407, # Right hand slot
    "feet":             415, # Feet slot
    "side1":            423, # Side slot 1
    "side2":            431, # Side slot 2
    "side3":            439, # Side slot 3
    "side4":            447, # Side slot 4
    "ballista":         455, # Ballista slot
    "ammo":             463, # Ammo Cart slot
    "tent":             471, # First Aid Tent slot
    "catapult":         479, # Catapult slot
    "spellbook":        487, # Spellbook slot
    "side5":            495, # Side slot 5
    "inventory":        503, # Inventory start

    "reserved": {            # Slots reserved by combination artifacts
        "helm":        1016,
        "cloak":       1017,
        "neck":        1018,
        "weapon":      1019,
        "shield":      1020,
        "armor":       1021,
        "hand":        1022, # For both left and right hand, \x00-\x02
        "feet":        1023,
        "side":        1024, # For all side slots, \x00-\x05
    },

}

# Since savefile format is unknown, hero structs are identified heuristically,
# by matching byte patterns.
RGX_HERO = re.compile(b"""
    # There are at least 60 bytes more at front, but those can also include
    # hero biography, making length indeterminate.
    # Bio ends at position -32 from total movement point start.
    # If bio end position is \x00, then bio is empty, otherwise bio extends back
    # until a 4-byte span giving bio length (which always ends with \x00).

    .{4}                     #   4 bytes: movement points in total             000-003
    .{4}                     #   4 bytes: movement points remaining            004-007
    .{4}                     #   4 bytes: experience                           008-011
    [\x00-\x1C][\x00]{3}     #   4 bytes: skill slots used                     012-015
    .{2}                     #   2 bytes: spell points remaining               016-017
    .{1}                     #   1 byte:  hero level                           018-018

    .{63}                    #  63 bytes: unknown                              019-081

    .{28}                    #  28 bytes: 7 4-byte creature IDs                082-109
    .{28}                    #  28 bytes: 7 4-byte creature counts             110-137

                             #  13 bytes: hero name, null-padded               138-150
    (?P<name>[^\x00-\x20,\xF0-\xFF].{11}\x00)
    [\x00-\x03]{28}          #  28 bytes: skill levels                         151-178
    [\x00-\x1C]{28}          #  28 bytes: skill slots                          179-206
    .{4}                     #   4 bytes: primary stats                        207-210

    [\x00-\x01]{70}          #  70 bytes: spells in book                       211-280
    [\x00-\x01]{70}          #  70 bytes: spells available                     281-350

                             # 152 bytes: 19 8-byte equipments worn            351-502
                             # Blank spots:   FF FF FF FF XY XY XY XY
                             # Artifacts:     XY 00 00 00 FF FF FF FF
                             # Scrolls:       XY 00 00 00 00 00 00 00
    (?P<artifacts>(          # Catapult etc:  XY 00 00 00 XY XY 00 00
      (\xFF{4} .{4}) | (.\x00{3} (\x00{4} | \xFF{4})) | (.\x00{3}.{2}\x00{2})
    ){19})

                             # 512 bytes: 64 8-byte artifacts in backpack      503-1014
    ( ((.\x00{3}) | \xFF{4}) (\x00{4} | \xFF{4}) ){64}

                             # 10 bytes: slots taken by combination artifacts 1015-1024
    .[\x00-\x01]{6}[\x00-\x02][\x00-\x01][\x00-\x05]
""", re.VERBOSE | re.DOTALL)



def init():
    """Loads hero plugins list."""
    global PLUGINS
    basefile = os.path.join(conf.PluginDirectory, "hero", "__init__.py")
    PLUGINS[:] = plugins.load_modules(__package__, basefile)


def props():
    """Returns props for hero-tab, as {label, icon}."""
    return PROPS


def factory(savefile, panel, commandprocessor):
    """Returns a new hero-plugin instance."""
    return HeroPlugin(savefile, panel, commandprocessor)



class Hero(object):
    """
    Container for all hero attributes.

    Plugins will add their own specific attributes like `inventory`.
    """

    def __init__(self, name, bytes, place, span, savefile):
        self.name      = name
        self.bytes     = bytes
        self.place     = place
        self.span      = span
        self.savefile  = savefile
        self.basestats = {}  # Primary attributes without artifact bonuses
        self.yamls1    = []  # Data after first load, as [category YAML, ]
        self.yamls2    = []  # Data after last change, as [category YAML, ]

    def copy(self):
        """Returns a copy of this hero."""
        hero = Hero(self.name, self.bytes, self.place, self.span, self.savefile)
        hero.update(self)
        return hero

    def update(self, hero):
        """Replaces attributes on hero with copies from given hero."""
        for k, v in vars(hero).items():
            v2 = v if isinstance(v, metadata.Savefile) else copy.deepcopy(v)
            setattr(self, k, v2)

    def get_bytes(self, original=False):
        """Returns hero bytearray, current or original."""
        if not original: return copy.copy(self.bytes)
        return bytearray(self.savefile.raw0[self.span[0]:self.span[1]])

    def ensure_basestats(self, clear=False):
        """Populates internal hero stats without artifacts, if not already populated."""
        if clear: self.basestats.clear()
        if self.basestats or not hasattr(self, "artifacts"): return
        STATS, diff = metadata.Store.get("artifact_stats"), [0] * len(metadata.PrimaryAttributes)
        for item in filter(STATS.get, self.artifacts.values()):
            diff = [a + b for a, b in zip(diff, STATS[item])]
        for k, v in zip(metadata.PrimaryAttributes, diff):
            self.basestats[k] = self.stats[k] - v

    def __eq__(self, other):
        """Returns whether this hero is the same as given (same name and place)."""
        return isinstance(other, Hero) and (self.name, self.place) == (other.name, other.place)

    def __str__(self):
        """Returns hero name."""
        return self.name



class HeroPlugin(object):
    """Encapsulates hero-plugin state and behaviour."""


    def __init__(self, savefile, panel, commandprocessor):
        self.name        = PROPS["name"]
        self.savefile    = savefile
        self._panel      = panel   # wxPanel container for plugin components
        self._undoredo   = commandprocessor # wx.CommandProcessor
        self._plugins    = []      # [{name, label, instance, panel}, ]
        self._heroes     = []      # [Hero(name, bytes, place, span, ..), ] ordered by name
        self._ctrls      = {}      # {name: wx.Control, }
        self._pages      = {}      # {wx.Window from self._ctrls["tabs"]: hero index in self._heroes}
        self._hero       = None    # Currently selected Hero instance
        self._heropanel  = None    # Container for hero components
        self._pending    = False   # Whether hero selected but not yet loaded
        self._autoloaded = None    # Whether current hero was auto-populated
        self._pages_visited = []   # List of visited hero tabs, as [hero index in self._heroes, ]
        self.parse(detect_version=True)
        self.prebuild()
        panel.Bind(gui.EVT_PLUGIN, self.on_plugin_event)


    def prebuild(self):
        """Builds general UI components."""
        label = wx.StaticText(self._panel, label="&Select hero:")
        combo = wx.ComboBox(self._panel, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        tbtop = wx.ToolBar(self._panel, style=wx.TB_FLAT | wx.TB_NODIVIDER)
        tabs  = wx.lib.agw.flatnotebook.FlatNotebook(self._panel,
            agwStyle=wx.lib.agw.flatnotebook.FNB_DROPDOWN_TABS_LIST |
                     wx.lib.agw.flatnotebook.FNB_MOUSE_MIDDLE_CLOSES_TABS |
                     wx.lib.agw.flatnotebook.FNB_NO_NAV_BUTTONS |
                     wx.lib.agw.flatnotebook.FNB_NO_TAB_FOCUS |
                     wx.lib.agw.flatnotebook.FNB_NO_X_BUTTON |
                     wx.lib.agw.flatnotebook.FNB_X_ON_TAB |
                     wx.lib.agw.flatnotebook.FNB_FF2)
        tb    = wx.ToolBar(self._panel, style=wx.TB_FLAT | wx.TB_NODIVIDER)
        self._heropanel = wx.Panel(self._panel)

        combo.Bind(wx.EVT_COMBOBOX, self.on_select_hero)
        tabs.Hide()

        CTRL = "Cmd" if "darwin" == sys.platform else "Ctrl"
        bmp1 = wx.ArtProvider.GetBitmap(wx.ART_FOLDER,      wx.ART_TOOLBAR, (16, 16))
        bmp2 = wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, wx.ART_TOOLBAR, (16, 16))
        bmp3 = wx.ArtProvider.GetBitmap(wx.ART_COPY,        wx.ART_TOOLBAR, (16, 16))
        bmp4 = wx.ArtProvider.GetBitmap(wx.ART_PASTE,       wx.ART_TOOLBAR, (16, 16))
        tbtop.AddTool(wx.ID_OPEN, "", bmp1, shortHelp="Show savefile in folder")
        tb.AddTool(wx.ID_INFO,    "", bmp2, shortHelp="Show hero full character sheet\t%s-I" % CTRL)
        tb.AddSeparator()
        tb.AddTool(wx.ID_COPY,    "", bmp3, shortHelp="Copy current hero data to clipboard")
        tb.AddTool(wx.ID_PASTE,   "", bmp4, shortHelp="Paste data from clipboard to current hero")
        tbtop.Bind(wx.EVT_TOOL, self.on_open_folder, id=wx.ID_OPEN)
        tb.Bind(wx.EVT_TOOL,    self.on_charsheet,   id=wx.ID_INFO)
        tb.Bind(wx.EVT_TOOL,    self.on_copy_hero,   id=wx.ID_COPY)
        tb.Bind(wx.EVT_TOOL,    self.on_paste_hero,  id=wx.ID_PASTE)
        self._panel.Bind(wx.EVT_MENU, self.on_charsheet, id=wx.ID_INFO)
        tbtop.Realize()
        tb.Realize()
        tb.Disable()
        tb.Hide()

        tabs.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_change_page, tabs)
        tabs.Bind(wx.lib.agw.flatnotebook.EVT_FLATNOTEBOOK_PAGE_CLOSING,
                  self.on_close_page, tabs)
        controls.ColourManager.Manage(tabs, "ActiveTabColour",        wx.SYS_COLOUR_WINDOW)
        controls.ColourManager.Manage(tabs, "ActiveTabTextColour",    wx.SYS_COLOUR_BTNTEXT)
        controls.ColourManager.Manage(tabs, "NonActiveTabTextColour", wx.SYS_COLOUR_BTNTEXT)
        controls.ColourManager.Manage(tabs, "TabAreaColour",          wx.SYS_COLOUR_BTNFACE)
        controls.ColourManager.Manage(tabs, "GradientColourBorder",   wx.SYS_COLOUR_BTNSHADOW)
        controls.ColourManager.Manage(tabs, "GradientColourTo",       wx.SYS_COLOUR_ACTIVECAPTION)
        controls.ColourManager.Manage(tabs, "ForegroundColour",       wx.SYS_COLOUR_BTNTEXT)
        controls.ColourManager.Manage(tabs, "BackgroundColour",       wx.SYS_COLOUR_WINDOW)

        self._heropanel.Sizer = wx.BoxSizer(wx.VERTICAL)

        sizer = self._panel.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_top = wx.BoxSizer(wx.HORIZONTAL)
        sizer_top.Add(label,  border=10, flag=wx.RIGHT | wx.ALIGN_CENTER)
        sizer_top.Add(combo,  border=5,  flag=wx.TOP  | wx.BOTTOM | wx.GROW)
        sizer_top.Add(tbtop,  border=5,  flag=wx.LEFT | wx.TOP | wx.BOTTOM)
        sizer.Add(sizer_top,  border=10, flag=wx.LEFT | wx.GROW)
        sizer.Add(tabs,       border=5,  flag=wx.BOTTOM | wx.GROW)
        sizer.Add(tb,         border=10, flag=wx.LEFT)
        sizer.Add(self._heropanel, border=5, flag=wx.TOP | wx.GROW, proportion=1)
        wx_accel.accelerate(self._panel, accelerators=[(wx.ACCEL_CMD, ord("I"), wx.ID_INFO)])

        self._ctrls["tabs"] = tabs
        self._ctrls["hero"] = combo
        self._ctrls["toolbar"] = tb


    def build(self):
        """Builds hero UI components."""
        self._heropanel.DestroyChildren()
        self._heropanel.Sizer.Clear()
        tabs, combo, tb = self._ctrls["tabs"], self._ctrls["hero"], self._ctrls["toolbar"]
        nb = wx.Notebook(self._heropanel)

        tabs.Show()
        tabs.DeleteAllPages()
        combo.SetItems([x.name for x in self._heroes])
        tb.Show()

        for p in self._plugins:
            subpanel = p["panel"] = wx.ScrolledWindow(nb)
            if p.get("instance"): p["instance"].load(self._hero, subpanel)
            title = p.get("label", p["name"])
            nb.AddPage(subpanel, title)

        self._heropanel.Sizer.Add(nb, border=10, flag=wx.ALL ^ wx.TOP | wx.GROW, proportion=1)

        for p in self._plugins if self._hero else ():
            self.render_plugin(p["name"])
        tabs.Hide()
        tb.Hide()
        self._heropanel.Hide()


    def command(self, callable, name=None):
        """Submits callable to undo-redo command processor to be invoked."""
        if self._panel: self._undoredo.Submit(plugins.PluginCommand(self, callable, name))


    def render(self, reparse=False, reload=False):
        """
        Renders hero selection and editing subtabs into our panel.

        @param   reparse  whether plugins should re-parse state from savefile
        @param   reload   whether plugins should reload state from hero
        """
        if not PLUGINS: init()
        self._plugins = self._plugins or [x.copy() for x in PLUGINS]
        if reparse: self.reparse()
        elif self._hero and self._heropanel.Children:
            for p in self._plugins: self.render_plugin(p["name"], reload=reload)
        else: self.build()


    def action(self, **kwargs):
        """Handler for action (load=hero name or index, ?auto=bool)"""
        if kwargs.get("load") is not None:
            name = kwargs["load"]
            if isinstance(name, int):
                index = max(0, min(name, len(self._heroes) - 1))
            else: index = next((i for i, x in enumerate(self._heroes) if x.name == name), -1)
            if index >= 0 and self._heroes: self.select_hero(index, autoload=kwargs.get("auto"))


    def reparse(self):
        """Reparses state from savefile and refreshes UI."""
        tabs = self._ctrls["tabs"]
        hero0 = self._hero
        pages0 = [self._pages[p] for i in range(tabs.GetPageCount())
                  for p in [tabs.GetPage(i)] if p in self._pages]  # [hero index, ]
        heroes0  = self._heroes[:]
        visited0 = self._pages_visited[:]
        self._hero = None
        self._pages.clear()
        del self._pages_visited[:]

        self.parse()
        self.build()

        self._panel.Freeze()
        try:
            tabs.DeleteAllPages()
            hero = None
            for index in pages0:
                hero1 = heroes0[index]
                hero2 = index < len(self._heroes) and self._heroes[index]
                if hero1 != hero2:
                    hero2 = next((x for x in self._heroes if x == hero1), None)  # Match name+place
                    hero2 = hero2 or next((x for x in self._heroes if x.name == hero1.name), None)
                if not hero2:
                    visited0 = [i for i in visited0 if i != index]
                    continue  # for index
                page = wx.Window(tabs)
                self._pages[page] = index
                if not hero and hero0 and hero2.name == hero0.name: hero = hero2
                tabs.AddPage(page, hero2.name, select=hero2 is hero)

            visited0 = [v for i, v in enumerate(visited0) if not i or v != visited0[i - 1]]
            self._pages_visited[:] = visited0
            if not hero and visited0: hero = self._heroes[visited0[-1]]
            index = next(i for i, x in enumerate(self._heroes) if x is hero) if hero else None
            if index is not None: self.select_hero(index, status=False, autoload=self._autoloaded)
            self._panel.Layout()
        finally:
            self._panel.Thaw()


    def on_copy_hero(self, event=None):
        """Handler for copying a hero, adds hero data to clipboard."""
        if self._hero and wx.TheClipboard.Open():
            d = wx.TextDataObject(self.serialize_yaml())
            wx.TheClipboard.SetData(d), wx.TheClipboard.Close()
            guibase.status("Copied hero %s data to clipboard.",
                           self._hero.name, flash=True, log=True)


    def on_paste_hero(self, event=None):
        """Handler for copying a hero, adds hero data to clipboard."""
        value = None
        if self._hero and wx.TheClipboard.Open():
            if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)):
                o = wx.TextDataObject()
                wx.TheClipboard.GetData(o)
                value = o.Text
            wx.TheClipboard.Close()
        if value:
            guibase.status("Pasting data to hero %s from clipboard.",
                           self._hero.name, flash=True, log=True)
            self.parse_yaml(value)


    def on_open_folder(self, event=None):
        """Opens folder to savefile location."""
        util.select_file(self.savefile.filename)


    def on_charsheet(self, event=None):
        """Opens popup with full hero profile."""
        tpl = step.Template(templates.HERO_CHARSHEET_HTML, escape=True)
        texts, texts0 = self._hero.yamls2 or self._hero.yamls1, None
        if self._hero.yamls2 and self._hero.yamls1 != self._hero.yamls2: texts0 = self._hero.yamls1 
        tplargs = dict(name=self._hero.name, texts=texts, texts0=texts0)
        content, content2 = tpl.expand(**tplargs), tpl.expand(changes=True, **tplargs)
        links = {"normal": content, "changes": content2}
        buttons = {"Copy data": self.on_copy_hero}
        dlg = controls.HtmlDialog(self._panel.TopLevelParent, "Hero character sheet", content,
                                  links=links, buttons=buttons, style=wx.RESIZE_BORDER)
        wx.CallAfter(dlg.ShowModal)


    def on_plugin_event(self, event):
        """Handler for a plugin event like serialize or re-render."""
        action = getattr(event, "action", None)
        if "patch" == action:
            event.Skip()
            self.patch()
        if "render" == action and getattr(event, "name", None):
            event.Skip()
            self.render_plugin(event.name)


    def on_change_page(self, event):
        """Handler for changing a page in the heroes notebook, loads hero data."""
        if event.GetOldSelection() < 0: return
        self.select_hero(self._pages[self._ctrls["tabs"].GetCurrentPage()], status=False)


    def on_close_page(self, event):
        """Handler for closing a hero page, selects a previous hero page, if any."""
        tabs = self._ctrls["tabs"]
        page = tabs.GetPage(event.GetSelection())
        page0 = tabs.GetCurrentPage()
        index = next((i for p, i in self._pages.items() if p == page), 0)
        self._pages.pop(page, None)
        visited = [x for x in self._pages_visited if x != index]
        self._pages_visited = [v for i, v in enumerate(visited) if not i or v != visited[i - 1]]
        if page0 is page and self._pages_visited:
            self.select_hero(self._pages_visited[-1], status=False)
        elif not self._pages:
            self._ctrls["hero"].SetSelection(-1)
            self._ctrls["toolbar"].Disable()
            self._ctrls["toolbar"].Hide()
            self._ctrls["tabs"].Hide()
            self._heropanel.Hide()
            self._hero = None


    def on_select_hero(self, event):
        """Handler for selecting a hero in combobox, populates tabs with hero data."""
        if self._pending: return
        index = event.EventObject.Selection
        hero2 = self._heroes[index] if index < len(self._heroes) else None
        if self._hero and hero2 is self._hero: return
        if not hero2:
            wx.MessageBox("Hero '%s' not found." % event.EventObject.Value,
                          conf.Title, wx.OK | wx.ICON_ERROR)
            return
        self.select_hero(index, status=index not in self._pages.values())


    def select_hero(self, index, status=True, autoload=False):
        """
        Populates panel with hero data.

        @param   index     hero index in local structure
        @param   status    whether to show status messages
        @param   autoload  whether auto-populating
        """
        if not self._panel: return
        hero2 = self._heroes[index] if index < len(self._heroes) else None
        if not hero2 or self._hero and hero2 is self._hero: return

        self._pending = True
        hero2.ensure_basestats()
        busy = controls.BusyPanel(self._panel, "Loading %s." % hero2.name) if status else None
        if status: guibase.status("Loading %s." % hero2.name, flash=True)
        combo, tabs, tb = self._ctrls["hero"], self._ctrls["tabs"], self._ctrls["toolbar"]
        combo.SetSelection(index)
        self._panel.Freeze()
        tabs.Show()
        self._heropanel.Show()
        try:
            if self._hero: self.patch()
            logger.info("Loading hero %s (bytes %s-%s in savefile).",
                        hero2.name, hero2.span[0], hero2.span[1] - 1)
            self._hero = hero2
            for p in self._plugins: self.render_plugin(p["name"], reload=True)
            if not self._hero.yamls1:
                self._hero.yamls1 = self.serialize_yaml(split=True)
        finally:
            self._pending = False
            if (autoload or self._autoloaded) and not self.savefile.is_changed():
                tabs.DeleteAllPages()  # Replace auto-populated tab
                self._pages.clear()
                del self._pages_visited[:]
            self._autoloaded = autoload
            if index not in self._pages.values():
                page = wx.Window(tabs)
                self._pages[page] = index
                tabs.AddPage(page, hero2.name, select=True)
                tb.Enable()
                tb.Show()
            else:
                page = next(p for p, i in self._pages.items() if i == index)
                idx  = next(i for i in range(tabs.GetPageCount()) if page is tabs.GetPage(i))
                tabs.SetSelection(idx)
            if not self._pages_visited or self._pages_visited[-1] != index:
                self._pages_visited.append(index)
            self._panel.Layout()
            self._panel.Thaw()
            if status: busy.Close(), wx.CallLater(500, guibase.status, "")
            if not autoload:
                evt = gui.SavefilePageEvent(self._panel.Id)
                evt.SetClientData(dict(plugin=self.name, load=hero2.name))
                wx.PostEvent(self._panel, evt)


    def parse(self, detect_version=False):
        """
        Populates the list of hero bytearrays parsed from savefile binary,
        as [{"name": hero name, "bytes": bytearray()}], sorted by name.

        @param   detect_version  whether to try parsing with all version plugins
                                 instead of savefile current
        """
        heroes = []

        ver0 = self.savefile.version
        versions, version_results = [], {}
        if detect_version and getattr(plugins, "version", None):
            versions = [x["name"] for x in plugins.version.PLUGINS]
        if not versions: versions = [self.savefile.version]
        all_versions = versions[:]
        rgx_strip = re.compile(br"^([^\x00-\x19,\xF0-\xFF]+)\x00+$")
        rgx_nulls = re.compile(br"^(\x00+)|(\x00{4}\xFF{4})+$")

        while versions:
            ver = versions.pop()
            self.savefile.version = ver
            RGX = plugins.adapt(self, "regex", RGX_HERO)
            vresult = version_results.setdefault(ver, [])

            pos = 10000 # Hero structs are more to the end of the file
            m = re.search(RGX, self.savefile.raw[pos:])
            while m:
                start, end = m.span()
                if rgx_strip.match(m.group("name")) and not rgx_nulls.match(m.group("artifacts")):
                    blob = bytearray(self.savefile.raw[pos + start:pos + end])
                    name = util.to_unicode(rgx_strip.match(m.group("name")).group(1))
                    hero = Hero(name, blob, len(vresult), (start + pos, end + pos), self.savefile)
                    vresult.append(hero)
                    pos += end
                else:
                    pos += start + 1
                m = re.search(RGX, self.savefile.raw[pos:])
            if not vresult:
                logger.warning("No heroes detected in %s as version '%s'.",
                               self.savefile.filename, ver)
                continue  # while versions
            logger.info("Detected %s heroes in %s as version '%s'.",
                        len(vresult), self.savefile.filename, ver)

        vcounts = {k: len(v) for k, v in version_results.items()}
        maxcount_vers = [k for k in all_versions if vcounts[k] == max(vcounts.values())]
        ver = maxcount_vers[-1] if maxcount_vers else None
        if ver:
            self.savefile.version = ver
            heroes = sorted(version_results[ver], key=lambda x: x.name.lower())
            logger.info("Interpreting %s as version '%s' with %s heroes.",
                        self.savefile.filename, ver, len(heroes))
        else:
            self.savefile.version = ver0
            wx.CallAfter(guibase.status, "No heroes identified in %s.",
                         self.savefile.filename, flash=True, log=True)

        self._heroes[:] = heroes


    def parse_yaml(self, value):
        """Populates current hero with value parsed as YAML."""
        try:
            states = next(iter(yaml.safe_load(value).values()))
            assert isinstance(states, dict)
        except Exception as e:
            logger.warning("Error loading hero data from clipboard: %s", e)
            guibase.status("No valid hero data in clipboard.", flash=True)
            return
        pluginmap = {p["name"]: p["instance"] for p in self._plugins}
        usables = {}  # {plugin name: state}
        for category, state in states.items():
            plugin = pluginmap.get(category)
            if not callable(getattr(plugin, "load_state", None)):
                continue  # for
            if not plugin:
                logger.warning("Unknown category in hero data: %r", category)
                continue  # for
            state0 = plugin.state()
            if state is None: state = type(state0)()
            if not isinstance(state0, type(state)):
                logger.warning("Invalid data type in hero data %r for %s: %s",
                               category, type(state0).__name__, state)
                continue  # for
            usables[category] = state
        if not usables: return

        def on_do(states):
            pluginmap = {p["name"]: p["instance"] for p in self._plugins}
            changeds = []  # [plugin name, ]
            for category, state in states.items():
                plugin = pluginmap.get(category)
                state0 = plugin.state()
                if state is None: state = type(state0)()
                if plugin.load_state(state): changeds.append(category)
                self._hero.ensure_basestats(clear=True)
            if changeds:
                self.patch()
                for name in changeds:
                    self.render_plugin(name)
            return bool(changeds)
        self.command(functools.partial(on_do, usables), "paste hero data from clipboard")


    def serialize_yaml(self, split=False):
        """
        Returns current hero data as YAML.

        @param   split   whether to return as [category YAML, ] instead of hero full YAML
        """
        LF, INDENT = os.linesep, "  "
        states, maxlen = [], 0, # [(category, [(prefix, value), ])]
        for p in self._plugins:  # Assemble YAML by hand for more readable indentation
            pairs, prefixlen = self.serialize_plugin_yaml(p["instance"], INDENT)
            states.append((p["name"], pairs))
            maxlen = max(maxlen, prefixlen)
        maxlen += len(INDENT) + 3
        formatteds = ["%s%s:%s%s%s%s" % (
            INDENT, category, LF if pairs else "", INDENT if pairs else "",
            (LF + INDENT).join("%s%s" % (a.ljust(maxlen) if b and a.strip() != "-" else a, b)
                               for a, b in pairs), LF
        ) for category, pairs in states]
        name = yaml.safe_dump([self._hero.name], default_flow_style=True).strip()[1:-1]
        return formatteds if split else name + ":" + LF + "".join(formatteds)


    def serialize_plugin_yaml(self, plugin, indent="  "):
        """
        Returns current hero data from plugin as YAML components.

        @param   plugin  plugin instance
        @param   indent  line leading indent
        @return          [(formatted prefix, formatted value)], raw prefix maxlen
        """
        pairs, maxlen = [], 0
        fmt = lambda v: "" if v in (None, {}) else \
                        next((x[1:-1] if isinstance(v, util.text_types)
                              and re.match(r"[\x20-\x7e]+$", x) else x for x in [json.dumps(v)]))
        props, state = plugin.props(), copy.copy(plugin.state())
        for prop in props if isinstance(props, (list, tuple)) else [props]:
            if "itemlist" == prop["type"]:
                while state and not state[-1]: state.pop()  # Strip empty trailing values
                for v in state:
                    itempairs = []
                    if not v or not isinstance(v, dict):
                        itempairs += [("-%s" % ("" if v in (None, {}) else " "), fmt(v))]
                    else:
                        for itemprop in prop["item"]:
                            if "name" in itemprop and itemprop["name"] in v:
                                maxlen = max(maxlen, len(itemprop["name"]))
                                lead = " " if itempairs else "-"
                                itempairs += [("%s %s:" % (lead, itemprop["name"]),
                                               fmt(v[itemprop["name"]]))]
                    pairs.extend(itempairs)
            elif "label" != prop["type"]:
                maxlen = max(maxlen, len(prop["name"]))
                pairs += [("%s%s:" % (indent, prop["name"]), fmt(state[prop["name"]]))]
        return pairs, maxlen


    def get_data(self):
        """Returns copy of current hero object."""
        return self._hero.copy() if self._hero else None


    def set_data(self, hero):
        """Sets current hero object."""
        tabs = self._ctrls["tabs"]
        index = next(i for i, h in enumerate(self._heroes) if h == hero)
        if index in self._pages.values():
            page = next(p for p, i in self._pages.items() if i == index)
            idx  = next(i for i in range(tabs.GetPageCount()) if page is tabs.GetPage(i))
            tabs.SetSelection(idx)
        else:
            page = wx.Window(tabs)
            self._pages[page] = index
            tabs.AddPage(page, hero.name, select=True)
            self._heropanel.Show()
        if not self._hero:
            self._hero = next(h for h in self._heroes if h == hero)
        self._hero.update(hero)


    def get_changes(self):
        """Returns changes to current heroes, as HTML diff content."""
        changes, tpl = [], step.Template(templates.HERO_DIFF_HTML, escape=True)
        for hero in self._heroes:
            if hero.yamls1 and hero.yamls2 and hero.yamls1 != hero.yamls2:
                changes.append(tpl.expand(name=hero.name, changes=[
                    (v1, v2) for v1, v2 in zip(hero.yamls1, hero.yamls2) if v1 != v2
                ]))
        return "\n".join(changes)


    def patch(self):
        """Serializes current plugin state to hero bytes, patches savefile binary."""
        for p in self._plugins:
            if callable(getattr(p.get("instance"), "serialize", None)):
                self._hero.bytes = p["instance"].serialize()
        self.savefile.patch(self._hero.bytes, self._hero.span)
        self._hero.yamls2 = self.serialize_yaml(split=True)
        wx.PostEvent(self._panel, gui.SavefilePageEvent(self._panel.Id))


    def render_plugin(self, name, reload=False):
        """
        Renders or re-renders panel for the specified plugin.

        @param   reload  whether plugins should re-parse state from hero bytes
        """
        p = next((x for x in self._plugins if x["name"] == name), None)
        if not p:
            logger.warning("Call to render unknown plugin %s.", name)
            return

        obj = obj0 = p.get("instance")
        if not obj:
            try:
                obj = p["module"].factory(self, self._hero, p["panel"])
            except Exception:
                logger.exception("Error instantiating %s plugin.", p["name"])
                return
            p["instance"] = obj
        elif reload: obj.load(self._hero, p["panel"])
        if reload or not obj0:
            logger.info("Loaded hero %s %s %s.", self._hero.name, p["name"], obj.state())

        p["panel"].Freeze()
        try:
            if   callable(getattr(obj, "render", None)): obj.render()
            elif callable(getattr(obj, "props",  None)): gui.build(obj, p["panel"])
            if not obj0 or reload: wx_accel.accelerate(p["panel"])
        finally:
            p["panel"].Thaw()
