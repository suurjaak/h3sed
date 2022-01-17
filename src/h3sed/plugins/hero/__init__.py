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

    def load(self, hero, panel=None):
        '''Mandatory. Loads subplugin state from hero, optionally resetting panel.'''

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
@modified  17.01.2022
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

import yaml
import wx

from h3sed import conf
from h3sed import gui
from h3sed import guibase
from h3sed import images
from h3sed import metadata
from h3sed import plugins
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
    # until a 4-byte span giving bio length (which always ends with \x00
    # because bio can't be gigabytes long).

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
    (?P<name>[^\x00-\x20,\xF0-\xFF].{12})
    [\x00-\x03]{28}          #  28 bytes: skill levels                         151-178
    [\x00-\x1C]{28}          #  28 bytes: skill slots                          179-206
    .{4}                     #   4 bytes: primary stats                        207-210

    [\x00-\x01]{70}          #  70 bytes: spells in book                       211-280
    [\x00-\x01]{70}          #  70 bytes: spells available                     281-350

                             # 152 bytes: 19 8-byte equipments worn            351-502
                             # Blank spots:   FF FF FF FF 00 00 00 00
                             # Artifacts:     XY 00 00 00 FF FF FF FF
                             # Scrolls:       XY 00 00 00 00 00 00 00
                             # Catapult etc:  XY 00 00 00 XY XY 00 00
    ( ((.\x00{3}) | \xFF{4}) (\x00{4} | \xFF{4} | (.{2}\x00{2})) ){19}

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
    """Container for all hero attributes."""

    def __init__(self, name, bytes, span, savefile):
        self.name     = name
        self.bytes    = bytes
        self.span     = span
        self.savefile = savefile

    def get_bytes(self, original=False):
        """Returns hero bytearray, current or original."""
        if not original: return copy.copy(self.bytes)
        return bytearray(self.savefile.raw0[self.span[0]:self.span[1]])



class HeroPlugin(object):
    """Encapsulates hero-plugin state and behaviour."""


    def __init__(self, savefile, panel, commandprocessor):
        self.name = PROPS["name"]
        self.savefile  = savefile
        self._panel    = panel # wxPanel container for hero components
        self._undoredo = commandprocessor # wx.CommandProcessor
        self._plugins  = []    # [{name, label, instance, panel}, ]
        self._heroes   = []    # [{name, span: (start, stop), bytes: bytearray()}, ]
        self._tabs     = []    # [{name, }]
        self._ctrls    = {}    # {name: wx.Control, }
        self._hero     = None  # Currently selected Hero instance
        self._pending  = None  # Hero selected but not yet loaded
        self.parse(detect_version=True)
        panel.Bind(gui.EVT_PLUGIN, self.on_plugin_event)


    def build(self):
        """Builds UI components."""
        self._panel.DestroyChildren()
        label = wx.StaticText(self._panel, label="&Select hero:")
        combo = wx.ComboBox(self._panel, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        tb    = wx.ToolBar(self._panel, style=wx.TB_FLAT | wx.TB_NODIVIDER)
        nb    = wx.Notebook(self._panel)

        combo.SetItems([x.name for x in self._heroes])
        combo.Value = self._hero.name if self._hero else ""
        combo.Bind(wx.EVT_COMBOBOX, self.on_select_hero)

        bmp1 = wx.ArtProvider.GetBitmap(wx.ART_COPY,  wx.ART_TOOLBAR, (16, 16))
        bmp2 = wx.ArtProvider.GetBitmap(wx.ART_PASTE, wx.ART_TOOLBAR, (16, 16))
        tb.AddTool(wx.ID_COPY,  "", bmp1, shortHelp="Copy current hero data to clipboard")
        tb.AddTool(wx.ID_PASTE, "", bmp2, shortHelp="Paste data from clipboard to current hero")
        tb.EnableTool(wx.ID_COPY,  False)
        tb.EnableTool(wx.ID_PASTE, False)
        tb.Bind(wx.EVT_TOOL, self.on_copy_hero,  id=wx.ID_COPY)
        tb.Bind(wx.EVT_TOOL, self.on_paste_hero, id=wx.ID_PASTE)
        tb.Realize()

        for p in self._plugins:
            subpanel = p["panel"] = wx.ScrolledWindow(nb)
            if p.get("instance"): p["instance"].load(self._hero, subpanel)
            title = p.get("label", p["name"])
            nb.AddPage(subpanel, title)

        sizer = self._panel.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_top           = wx.BoxSizer(wx.HORIZONTAL)
        sizer_top.Add(label, flag=wx.RIGHT | wx.ALIGN_CENTER, border=10)
        sizer_top.Add(combo, flag=wx.GROW)
        sizer_top.Add(tb, border=10, flag=wx.LEFT)
        sizer.Add(sizer_top, border=10, flag=wx.LEFT | wx.TOP | wx.GROW)
        sizer.Add(nb,        border=10, proportion=1, flag=wx.ALL | wx.GROW)

        self._ctrls["hero"] = combo
        self._ctrls["toolbar"] = tb
        wx_accel.accelerate(self._panel)
        for p in self._plugins if self._hero else ():
            self.render_plugin(p["name"])
        if conf.Populate and self._heroes:
            index = next((i for i, h in enumerate(self._heroes) if h is self._hero), 0)
            self._hero = None
            wx.CallAfter(lambda: self and (combo.SetSelection(index), self.on_select_hero(index=index)))


    def command(self, callable, name=None):
        """"""
        self._undoredo.Submit(plugins.PluginCommand(self, callable, name))


    def render(self, reparse=False, reload=False):
        """
        Renders hero selection and editing subtabs into our panel.

        @param   reparse  whether plugins should re-parse state from savefile
        @param   reload   whether plugins should reload state from hero
        """
        if not PLUGINS: init()
        self._plugins = self._plugins or [x.copy() for x in PLUGINS]
        if reparse:
            self.parse()
            self._hero = self._hero and next((x for x in self._heroes
                                              if self._hero.name == x.name), None)
            self.build()
        elif self._panel.Children and self._hero:
            for p in self._plugins: self.render_plugin(p["name"], reload=reparse or reload)
        else: self.build()


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


    def on_plugin_event(self, event):
        """Handler for a plugin event like serialize or re-render."""
        action = getattr(event, "action", None)
        if "patch" == action:
            event.Skip()
            self.patch()
        if "render" == action and getattr(event, "name", None):
            event.Skip()
            self.render_plugin(event.name)


    def on_select_hero(self, event=None, index=None):
        """Handler for selecting a hero, populates tabs with hero data."""
        if self._pending: return
        if event: index = event.EventObject.Selection
        hero2 = self._heroes[index] if index < len(self._heroes) else None
        if self._hero and hero2 is self._hero: return
        name = hero2.name if hero2 else event.EventObject.Value if event else None
        if not hero2:
            wx.MessageBox("Hero '%s' not found." % name,
                          conf.Title, wx.OK | wx.ICON_ERROR)
            return

        def do():
            if not self._panel: return
            busy = controls.BusyPanel(self._panel, 'Loading %s.' % hero2.name)
            self._panel.Freeze()
            try:
                if self._hero: self.patch()
                logger.info("Loading hero %s (bytes %s-%s in savefile).",
                            name, hero2.span[0], hero2.span[1] - 1)
                self._hero = hero2
                for p in self._plugins: self.render_plugin(p["name"], reload=True)
            finally:
                self._pending = None
                self._ctrls["toolbar"].EnableTool(wx.ID_COPY,  True)
                self._ctrls["toolbar"].EnableTool(wx.ID_PASTE, True)
                self._panel.Thaw()
                busy.Close()
            return True
        self._pending = hero2
        if self._hero: wx.CallAfter(self.command, do, "select hero: %s" % hero2.name)
        else: wx.CallAfter(do)


    def parse(self, detect_version=False):
        """
        Populates the list of hero bytearrays parsed from savefile binary,
        as [{"name": hero name, "bytes": bytearray()}], sorted by name.

        @param   detect_version  whether to try parsing with all version plugins
                                 instead of savefile current
        """
        result, raw = [], self.savefile.raw

        ver0 = self.savefile.version
        versions, version_results = [], {}
        if detect_version and getattr(plugins, "version", None):
            versions = [x["name"] for x in plugins.version.PLUGINS]
        if not versions: versions = [self.savefile.version]
        all_versions = versions[:]
        rgx_strip = re.compile(br"[\x00-\x19]")

        while versions:
            ver = versions.pop()
            self.savefile.version = ver
            RGX = plugins.adapt(self, "regex", RGX_HERO)
            vresult = version_results.setdefault(ver, [])

            pos = 10000 # Hero structs are more to the end of the file
            m = re.search(RGX, raw[pos:])
            while m and rgx_strip.sub(b"", m.group("name")):
                start, end = m.span()
                blob = bytearray(raw[pos + start:pos + end])
                vresult.append(Hero(util.to_unicode(rgx_strip.sub(b"", m.group("name"))),
                                    blob, tuple(x + pos for x in m.span()),
                                    self.savefile))
                pos += start + len(blob)
                m = re.search(RGX, raw[pos:])
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
            result = sorted(version_results[ver], key=lambda x: x.name.lower())
            logger.info("Interpreting %s as version '%s' with %s heroes.",
                        self.savefile.filename, ver, len(result))
        else:
            self.savefile.version = ver0
            wx.CallAfter(guibase.status, "No heroes identified in %s.",
                         self.savefile.filename, flash=True, log=True)

        self._heroes[:] = result


    def parse_yaml(self, value):
        """Populates current hero with value parsed as YAML."""
        try:
            states = next(iter(yaml.safe_load(value).values()))
            assert isinstance(states, dict)
        except Exception as e:
            logger.warn("Error loading hero data from clipboard: %s", e)
            guibase.status("No valid hero data in clipboard.", flash=True)
            return
        pluginmap = {p["name"]: p["instance"] for p in self._plugins}
        usables = {}  # {plugin name: state}
        for category, state in states.items():
            plugin = pluginmap.get(category)
            if not callable(getattr(plugin, "load_state", None)):
                continue  # for
            if not plugin:
                logger.warn("Unknown category in hero data: %r", category)
                continue  # for
            state0 = plugin.state()
            if state is None: state = type(state0)()
            if not isinstance(state0, type(state)):
                logger.warn("Invalid data type in hero data %r for %s: %s",
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
            if changeds:
                self.patch()
                for name in changeds:
                    self.render_plugin(name)
            return bool(changeds)

        cname = "paste hero data from clipboard"
        self.command(functools.partial(on_do, usables), cname)


    def serialize_yaml(self):
        """Returns current hero data as YAML."""
        LF, INDENT = os.linesep, "  "
        maxlen = 0
        states = []  # [(category, [(prefix, value), ])]
        fmt = lambda v: "" if v in (None, {}) else \
                        next((x[1:-1] if isinstance(v, util.text_types)
                              and re.match(r"[\x20-\x7e]+$", x) else x for x in [json.dumps(v)]))
        for p in self._plugins:  # Assemble YAML by hand for more readable indentation
            pairs = []
            props, state = p["instance"].props(), copy.copy(p["instance"].state())
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
                    pairs += [("%s%s:" % (INDENT, prop["name"]), fmt(state[prop["name"]]))]
            states.append((p["name"], pairs))

        maxlen += len(INDENT) + 3
        formatted = LF + "".join(
            "%s%s:%s%s%s%s" % (
                INDENT, category, LF if pairs else "", INDENT if pairs else "",
                (LF + INDENT).join("%s%s" % (a.ljust(maxlen) if a.strip() != "-" else a, b)
                                   for a, b in pairs), LF
            ) for category, pairs in states
        )
        return yaml.safe_dump({self._hero.name: None}).replace(" null\n", formatted)


    def get_data(self):
        """Returns copy of current hero object."""
        if not self._hero: return None
        hero = Hero(None, None, None, None)
        for k, v in vars(self._hero).items():
            v2 = v if isinstance(v, metadata.Savefile) else copy.deepcopy(v)
            setattr(hero, k, v2)
        return hero


    def set_data(self, hero):
        """Sets current hero object."""
        self._hero = Hero(hero.name, hero.bytes, hero.span, hero.savefile)
        for k, v in vars(hero).items():
            v2 = v if isinstance(v, metadata.Savefile) else copy.deepcopy(v)
            setattr(self._hero, k, v2)
        self._ctrls["hero"].Value = hero.name


    def patch(self):
        """Serializes current plugin state to hero bytes, patches savefile binary."""
        for p in self._plugins:
            if callable(getattr(p.get("instance"), "serialize", None)):
                self._hero.bytes = p["instance"].serialize()
        self.savefile.patch(self._hero.bytes, self._hero.span)
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

        if   callable(getattr(obj, "render", None)): obj.render()
        elif callable(getattr(obj, "props",  None)): gui.build(obj, p["panel"])
        if not obj0 or reload: wx_accel.accelerate(p["panel"])
