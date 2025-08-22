# -*- coding: utf-8 -*-
"""
UI plugin for managing heroes in a savefile.


Subplugin modules are expected to have the following API (all methods mandatory):

    def props():
        '''
        Returns plugin props {name, ?label, ?index}.
        Label is used as plugin tab label, falling back to plugin name.
        Index is used for sorting plugins.
        '''

    def factory(parent, panel, version):
        '''
        Returns new plugin instance.

        @param   parent   parent plugin (hero-plugin)
        @param   panel    wx.Panel for plugin render
        @param   version  game version
        '''


Subplugin instances are expected to have the following API:

    def props(self):
        '''Mandatory. Returns props for subplugin, if using gui.build().'''

    def state(self):
        '''Mandatory. Returns subplugin state for gui.build().'''

    def load(self, hero):
        '''Mandatory. Loads hero to subplugin state.'''

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
@modified  22.08.2025
------------------------------------------------------------------------------
"""
import collections
import functools
import logging
import os
import sys

import step
import yaml
import wx
import wx.html
import wx.lib.agw.flatnotebook

import h3sed
from .. lib import controls
from .. lib import util
from .. lib import wx_accel
from .. import conf
from .. import guibase
from .. import templates


logger = logging.getLogger(__package__)



class HeroPlugin(object):
    """Provides UI functionality for viewing and updating hero data in savegame."""

    """Milliseconds to wait after edit before applying search filter"""
    SEARCH_INTERVAL = 300


    def __init__(self, savefile, panel, commandprocessor):
        self.name        = "hero"
        self.savefile    = savefile
        self._panel      = panel   # wxPanel container for plugin components
        self._undoredo   = commandprocessor # wx.CommandProcessor
        self._plugins    = []      # [{name, label, instance, panel}, ]
        self._heroes     = []      # [h3sed.hero.Hero] ordered by name
        self._ctrls      = {}      # {name: wx.Control, }
        self._pages      = {}      # {wx.Window from self._ctrls["tabs"]: hero index in self._heroes}
        self._indexpanel = None    # Heroes index panel
        self._hero       = None    # Currently selected Hero instance
        self._heropanel  = None    # Container for hero components
        self._hero_yamls = {}      # {hero: {full, originals, currents}}
        self._pages_visited = []   # Visited tabs, as [hero index in self._heroes or None if index page]
        self._ignore_events = False  # For ignoring change events from programmatic selections et al
        self._index = {
            "herotexts": [],       # [hero contents to search in, as [{category: plaintext}] ]
            "html":      "",       # Current hero search results HTML
            "text":      "",       # Current search text
            "stale":     True,     # Whether should repopulate index before display
            "timer":     None,     # wx.Timer for filtering heroes index
            "ids":       {},       # {category: wx ID for toolbar toggle}
            "visible":   [],       # List of heroes visible
            "sort_col":  "index",  # Field being sorted by
            "sort_asc":  True,     # Sort ascending or descending
            "toggles":   collections.OrderedDict(),  # {category: toggled state}
        }
        self._dialog_export = wx.FileDialog(panel, "Export heroes to file",
            wildcard="CSV spreadsheet (*.csv)|*.csv|HTML document (*.html)|*.html|"
                     "JSON document (*.json)|*.json|YAML document (*.yaml)|*.yaml",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT | wx.FD_CHANGE_DIR | wx.RESIZE_BORDER
        )
        self._dialog_export.FilterIndex = 1

        self._heroes = self.savefile.heroes[:]
        self.prebuild()
        panel.Bind(h3sed.gui.EVT_PLUGIN, self.on_plugin_event)


    def prebuild(self):
        """Builds general UI components."""
        self._panel.Freeze()
        label  = wx.StaticText(self._panel, label="&Select hero:")
        combo  = wx.ComboBox(self._panel, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        search = wx.SearchCtrl(self._panel)
        tabs = wx.lib.agw.flatnotebook.FlatNotebook(self._panel,
            agwStyle=wx.lib.agw.flatnotebook.FNB_DROPDOWN_TABS_LIST |
                     wx.lib.agw.flatnotebook.FNB_MOUSE_MIDDLE_CLOSES_TABS |
                     wx.lib.agw.flatnotebook.FNB_NO_NAV_BUTTONS |
                     wx.lib.agw.flatnotebook.FNB_NO_TAB_FOCUS |
                     wx.lib.agw.flatnotebook.FNB_NO_X_BUTTON |
                     wx.lib.agw.flatnotebook.FNB_FF2)

        indexpanel = self._indexpanel = wx.Panel(self._panel)

        bmpx = wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE_AS, wx.ART_TOOLBAR, (16, 16))
        tb_index = wx.ToolBar(indexpanel, style=wx.TB_FLAT | wx.TB_NODIVIDER | wx.TB_NOICONS | wx.TB_TEXT)
        info = wx.StaticText(indexpanel)
        export = wx.Button(indexpanel, label="Expo&rt")
        export.SetBitmap(bmpx)
        export.SetBitmapMargins(0, 0)
        export.ToolTip = "Export heroes to HTML or data file"
        export.Bind(wx.EVT_BUTTON, self.on_export_heroes)

        for category in templates.HERO_PROPERTY_CATEGORIES:
            b = tb_index.AddCheckTool(wx.ID_ANY, category.capitalize(), wx.NullBitmap,
                                      shortHelp="Show or hide %s column%s" %
                                                (category, "s" if "stats" == category else ""))
            tb_index.ToggleTool(b.Id, conf.HeroToggles.get(category, True))
            tb_index.Bind(wx.EVT_TOOL, self.on_toggle_category, id=b.Id)
            self._index["ids"][category] = b.Id
            self._index["toggles"][category] = conf.HeroToggles.get(category, True)
        tb_index.Realize()

        html = wx.html.HtmlWindow(self._indexpanel)
        tabs.AddPage(wx.Window(tabs), " INDEX ")

        search.SetDescriptiveText("Search heroes")
        search.ShowSearchButton(True)
        search.ShowCancelButton(True)
        search.ToolTip = "Filter hero index on any matching text (%s-F)" % \
                         ("Cmd" if "darwin" == sys.platform else "Ctrl")
        search.Bind(wx.EVT_CHAR, self.on_search)
        search.Bind(wx.EVT_TEXT, self.on_search)
        search.Bind(wx.EVT_SEARCH, self.on_search) if hasattr(wx, "EVT_SEARCH") else None
        controls.ColourManager.Manage(html, "ForegroundColour", wx.SYS_COLOUR_BTNTEXT)
        controls.ColourManager.Manage(html, "BackgroundColour", wx.SYS_COLOUR_WINDOW)
        html.SetBorders(0)
        html.Bind(wx.html.EVT_HTML_LINK_CLICKED, self.on_index_link)
        html.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.on_sys_colour_change)

        tb = wx.ToolBar(self._panel, style=wx.TB_FLAT | wx.TB_NODIVIDER)

        combo.Bind(wx.EVT_COMBOBOX, self.on_select_hero)
        combo.Bind(wx.EVT_KEY_DOWN, self.on_key_select)

        CTRL = "Cmd" if "darwin" == sys.platform else "Ctrl"
        bmp1 = wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, wx.ART_TOOLBAR, (20, 20))
        bmp2 = wx.ArtProvider.GetBitmap(wx.ART_COPY,        wx.ART_TOOLBAR, (20, 20))
        bmp3 = wx.ArtProvider.GetBitmap(wx.ART_PASTE,       wx.ART_TOOLBAR, (20, 20))
        bmp4 = wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE,   wx.ART_TOOLBAR, (16, 16))
        tb.AddTool(wx.ID_INFO,    "", bmp1, shortHelp="Show hero full character sheet\t%s-I" % CTRL)
        tb.AddSeparator()
        tb.AddTool(wx.ID_COPY,    "", bmp2, shortHelp="Copy current hero data to clipboard")
        tb.AddTool(wx.ID_PASTE,   "", bmp3, shortHelp="Paste data from clipboard to current hero")
        tb.AddSeparator()
        tb.AddTool(wx.ID_SAVE,    "", bmp4, shortHelp="Save current hero to file")
        tb.Bind(wx.EVT_TOOL, self.on_charsheet,  id=wx.ID_INFO)
        tb.Bind(wx.EVT_TOOL, self.on_copy_hero,  id=wx.ID_COPY)
        tb.Bind(wx.EVT_TOOL, self.on_paste_hero, id=wx.ID_PASTE)
        tb.Bind(wx.EVT_TOOL, self.on_save_hero,  id=wx.ID_SAVE)
        self._panel.Bind(wx.EVT_MENU, self.on_charsheet, id=wx.ID_INFO)
        tb.Realize()
        tb.Disable()
        tb.Hide()

        tabs.MinSize = -1, tabs.GetTabArea().MinSize[1]
        tabs.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_change_page, tabs)
        tabs.Bind(wx.lib.agw.flatnotebook.EVT_FLATNOTEBOOK_PAGE_CLOSING,
                  self.on_close_page, tabs)
        tabs.Bind(wx.lib.agw.flatnotebook.EVT_FLATNOTEBOOK_PAGE_DROPPED,
                  self.on_dragdrop_page, tabs)
        controls.ColourManager.Manage(tabs, "ActiveTabColour",        wx.SYS_COLOUR_WINDOW)
        controls.ColourManager.Manage(tabs, "ActiveTabTextColour",    wx.SYS_COLOUR_BTNTEXT)
        controls.ColourManager.Manage(tabs, "NonActiveTabTextColour", wx.SYS_COLOUR_BTNTEXT)
        controls.ColourManager.Manage(tabs, "TabAreaColour",          wx.SYS_COLOUR_BTNFACE)
        controls.ColourManager.Manage(tabs, "GradientColourBorder",   wx.SYS_COLOUR_BTNSHADOW)
        controls.ColourManager.Manage(tabs, "GradientColourTo",       wx.SYS_COLOUR_ACTIVECAPTION)
        controls.ColourManager.Manage(tabs, "ForegroundColour",       wx.SYS_COLOUR_BTNTEXT)
        controls.ColourManager.Manage(tabs, "BackgroundColour",       wx.SYS_COLOUR_WINDOW)

        indexpanel.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_opts = wx.BoxSizer(wx.HORIZONTAL)
        sizer_labels = wx.BoxSizer(wx.VERTICAL)
        sizer_labels.Add(tb_index)
        sizer_labels.Add(info)
        sizer_opts.Add(sizer_labels, border=5, flag=wx.BOTTOM)
        sizer_opts.AddStretchSpacer()
        sizer_opts.Add(export, border=5, flag=wx.BOTTOM | wx.ALIGN_BOTTOM)
        indexpanel.Sizer.Add(html, border=10, flag=wx.LEFT | wx.RIGHT | wx.GROW, proportion=1)
        indexpanel.Sizer.Add(sizer_opts, border=10, flag=wx.LEFT | wx.RIGHT | wx.GROW)

        self._heropanel = wx.Panel(self._panel)
        self._heropanel.Sizer = wx.BoxSizer(wx.VERTICAL)

        sizer = self._panel.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_top = wx.BoxSizer(wx.HORIZONTAL)
        sizer_top.Add(label,  border=10, flag=wx.RIGHT | wx.ALIGN_CENTER)
        sizer_top.Add(combo,  border=5,  flag=wx.TOP  | wx.BOTTOM | wx.GROW)
        sizer_top.AddStretchSpacer()
        sizer_top.Add(search, border=5, flag=wx.ALL, proportion=1)
        sizer_top.AddSpacer(5)
        sizer.Add(sizer_top,  border=10, flag=wx.LEFT | wx.GROW)
        sizer.Add(tabs,       border=5,  flag=wx.BOTTOM | wx.GROW)
        sizer.Add(indexpanel, border=5, flag=wx.GROW, proportion=1)
        sizer.Add(tb,         border=10, flag=wx.LEFT)
        sizer.Add(self._heropanel, border=5, flag=wx.TOP | wx.GROW, proportion=1)
        self._panel.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        wx_accel.accelerate(self._panel, accelerators=[(wx.ACCEL_CMD, ord("I"), wx.ID_INFO)])
        self._panel.Layout()
        self._panel.Thaw()

        self._ctrls["tabs"] = tabs
        self._ctrls["hero"] = combo
        self._ctrls["search"] = search
        self._ctrls["count"] = info
        self._ctrls["html"] = html
        self._ctrls["toolbar"] = tb
        controls.ColourManager.Patch(self._panel)


    def build(self):
        """Builds hero UI components."""
        self._panel.Freeze()
        self._heropanel.DestroyChildren()
        self._heropanel.Sizer.Clear()
        del self._plugins[:]
        self._ctrls["hero"].SetItems([str(x) for x in self._heroes])

        nb = wx.Notebook(self._heropanel)
        self._plugins = [dict(m.props(), module=m) for m in h3sed.hero.PROPERTIES.values()]
        for props in self._plugins:
            subpanel = props["panel"] = wx.ScrolledWindow(nb)
            title = props.get("label", props["name"])
            nb.AddPage(subpanel, title)
            controls.ColourManager.Manage(subpanel, "BackgroundColour", wx.SYS_COLOUR_BTNFACE)
            props["instance"] = props["module"].factory(self, subpanel, self.savefile.version)

        self._heropanel.Sizer.Add(nb, border=10, flag=wx.ALL ^ wx.TOP | wx.GROW, proportion=1)

        if conf.Positions.get("herotab_index") \
        and conf.Positions["herotab_index"] < len(self._plugins):
            nb.SetSelection(conf.Positions["herotab_index"])
        nb.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,
                lambda e: conf.Positions.update(herotab_index=e.Selection))

        self._heropanel.Hide()
        self._panel.Thaw()
        with controls.BusyPanel(self._panel, "Loading heroes."):
            self.populate_index()


    def command(self, callable, name=None):
        """Submits callable to undo-redo command processor to be invoked."""
        if not self._panel: return
        self._index["stale"] = True
        self._undoredo.Submit(h3sed.gui.PluginCommand(self, callable, name))


    def render(self, reparse=False, reload=False, log=True):
        """
        Renders hero selection and editing subtabs into our panel.

        @param   reparse  whether plugins should re-parse state from savefile
        @param   reload   whether plugins should reload state from hero
        @param   log      whether plugin should log actions
        """
        if reparse or reload: self._index["stale"] = True

        if reparse:
            self.refresh_file()
        elif self._hero and self._heropanel.Children:
            for p in self._plugins:
                self.render_plugin(p["name"], reload=reload, log=log)
        else: self.build()


    def action(self, **kwargs):
        """Handler for action (load=hero name|index) or (save=True, ?rename=True, ?spans=[..])."""
        if kwargs.get("load") is not None:
            value = kwargs["load"]
            if isinstance(value, int): # Hero absolute index
                index = max(0, min(value, len(self._heroes) - 1))
            elif isinstance(value, (list, tuple)): # (hero name, name counter if duplicate)
                hero_name, name_counter = value[:2] if len(value) > 1 else (value[0], 1)
                candidates = [i for i, x in enumerate(self._heroes) if x.name == hero_name]
                index = candidates[min(name_counter, len(candidates)) - 1] if candidates else -1
            else: index = next((i for i, x in enumerate(self._heroes) if x.name == value), -1)
            if index >= 0 and self._heroes:
                self.select_hero(index)

        if kwargs.get("save"):
            tabs = self._ctrls["tabs"]
            heroes_open = []
            for index, hero in enumerate(self._heroes):
                if kwargs.get("spans") \
                and not any(a <= hero.span[0] and hero.span[1] <= b for a, b in kwargs["spans"]):
                    continue  # for index, hero

                hero.mark_saved()
                self._hero_yamls[hero] = templates.make_hero_yamls(hero)
                page = next((p for p, i in self._pages.items() if i == index), None)
                if page is not None:
                    heroes_open.append(hero)
                    tabs.SetPageText(tabs.GetPageIndex(page), str(hero))
            if kwargs.get("rename") and heroes_open:
                evt = h3sed.gui.SavefilePageEvent(self._panel.Id)
                evt.SetClientData(dict(plugin=self.name,
                                       load=[x.get_name_ident() for x in heroes_open]))
                wx.PostEvent(self._panel, evt)  # Propagate to parent


    def refresh_file(self):
        """Reloads heroes and refreshes UI."""
        tabs = self._ctrls["tabs"]
        hero0 = self._hero if self._pages_visited[-1:] not in ([], [None]) else None
        pages0 = [self._pages[p] for i in range(tabs.GetPageCount())
                  for p in [tabs.GetPage(i)] if p in self._pages]  # [hero index, ]
        heroes0  = self._heroes[:]
        visited0 = self._pages_visited[:]
        self._hero = None
        self._pages.clear()
        del self._pages_visited[:]
        for k, v in list(self._index.items()):
            if isinstance(v, (str, list)): self._index[k] = type(v)()

        self._heroes = self.savefile.heroes[:]
        self._index["herotexts"] = []
        self._hero_yamls.clear()
        self._panel.Freeze()
        self._ignore_events = True
        try:
            while tabs.GetPageCount() > 1: tabs.DeletePage(1)
            self.build()
            hero = None
            for index in pages0:
                hero1 = heroes0[index]
                hero2 = index < len(self._heroes) and self._heroes[index]
                if hero1 != hero2:
                    hero2 = next((x for x in self._heroes if x == hero1), None)  # Match name+index
                    hero2 = hero2 or next((x for x in self._heroes if x.name == hero1.name), None)
                if not hero2:
                    visited0 = [i for i in visited0 if i != index]
                    continue  # for index
                page = wx.Window(tabs)
                self._pages[page] = index
                if not hero and hero0 and hero2.name == hero0.name: hero = hero2
                tabs.AddPage(page, str(hero2), select=hero2 is hero)

            visited0 = [v for i, v in enumerate(visited0) if not i or v != visited0[i - 1]]
            self._pages_visited[:] = visited0
            if not hero and visited0[-1:] not in ([], [None]): hero = self._heroes[visited0[-1]]
            index = next(i for i, x in enumerate(self._heroes) if x is hero) if hero else None
            self.select_index() if index is None else self.select_hero(index, status=False)
            self._panel.Layout()
        finally:
            self._ignore_events = False
            self._panel.Thaw()


    def populate_index(self, focus=False, force=False):
        """Populates heroes index page, filtered by current search if any."""
        if not self._panel: return
        html, searchtext = self._ctrls["html"], self._ctrls["search"].Value.strip()
        if not self._index["stale"] and not force \
        and self._index["text"] == searchtext and self._index["herotexts"]:
            return

        heroes, links = self._heroes[:], list(range(len(self._heroes)))
        tpl = step.Template(templates.HERO_SEARCH_TEXT)
        tplargs = dict(sort_col=self._index["sort_col"], sort_asc=self._index["sort_asc"],
                       categories=self._index["toggles"])
        maketexts = lambda h: {c: tpl.expand(hero=h, category=c, **tplargs).lower()
                               for c in (["name"] + templates.HERO_PROPERTY_CATEGORIES)}
        if not self._index["herotexts"]:
            for hero in heroes:
                self._hero_yamls[hero] = templates.make_hero_yamls(hero)
            self._index["herotexts"] = [maketexts(h) for h in heroes]
        elif self._hero:
            index = next(i for i, h in enumerate(self._heroes) if h == self._hero)
            self._index["herotexts"][index] = maketexts(self._hero)

        if searchtext:
            words, herotexts = searchtext.strip().lower().split(), self._index["herotexts"]
            texts = ["\n".join(t for c, t in tt.items() if "name" == c or self._index["toggles"][c])
                     for tt in herotexts]
            matches = [(i, h) for i, (h, t) in enumerate(zip(heroes, texts))
                       if all(w in t for w in words)]
            links, heroes = zip(*matches) if matches else ([], [])
        self._index["text"] = searchtext
        self._index["visible"] = heroes
        tplargs.update(heroes=heroes, count=len(self._heroes), links=links, text=searchtext,
                       herotexts=self._index["herotexts"], savefile=self.savefile)
        page = step.Template(templates.HERO_INDEX_HTML, escape=True).expand(**tplargs)
        if page != self._index["html"]:
            info = util.plural("hero", heroes) if len(heroes) == len(self._heroes) else \
                   "%s visible (%s total)" % (util.plural("hero", heroes), len(self._heroes))
            self._ctrls["count"].Label = info
            self._index["html"] = page
            html.SetPage(page)
            html.Scroll(html.GetScrollPos(wx.HORIZONTAL), 0)
            html.BackgroundColour = controls.ColourManager.GetColour(wx.SYS_COLOUR_WINDOW)
            html.ForegroundColour = controls.ColourManager.GetColour(wx.SYS_COLOUR_BTNTEXT)
        self._index["stale"] = False
        if focus:
            self.select_index()


    def on_copy_hero(self, event=None):
        """Handler for copying a hero, adds hero data to clipboard."""
        if self._hero and wx.TheClipboard.Open():
            d = wx.TextDataObject(self._hero_yamls[self._hero]["full"])
            wx.TheClipboard.SetData(d), wx.TheClipboard.Close()
            guibase.status("Copied hero %s data to clipboard.",
                           self._hero, flash=conf.StatusShortFlashLength, log=True)


    def on_paste_hero(self, event=None):
        """Handler for pasting a hero, sets data from clipboard to hero."""
        value = None
        if self._hero and wx.TheClipboard.Open():
            if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)):
                o = wx.TextDataObject()
                wx.TheClipboard.GetData(o)
                value = o.Text
            wx.TheClipboard.Close()
        if value:
            guibase.status("Pasting data to hero %s from clipboard.",
                           self._hero, flash=conf.StatusShortFlashLength, log=True)
            self.parse_hero_yaml(value)


    def on_save_hero(self, event=None):
        """Handler for saving a hero, sends event to save current hero span."""
        changes = ""
        if self._hero.is_changed():
            yamls = self._hero_yamls[self._hero]
            pairs = [(v1, v2) for v1, v2 in zip(yamls["originals"], yamls["currents"]) if v1 != v2]
            tpl = step.Template(templates.HERO_DIFF_TEXT)
            changes = tpl.expand(name=self._hero.name, changes=pairs)
        logger.info("Saving hero %s to file.", self._hero)
        evt = h3sed.gui.SavefilePageEvent(self._panel.Id)
        evt.SetClientData(dict(save=True, spans=[self._hero.span], changes=changes))
        wx.PostEvent(self._panel, evt)


    def on_charsheet(self, event=None):
        """Opens popup with full hero profile."""
        tpl = step.Template(templates.HERO_CHARSHEET_HTML, escape=True)
        texts, texts0 = self._hero_yamls[self._hero]["currents"], None
        if self._hero.is_changed(): texts0 = self._hero_yamls[self._hero]["originals"]
        tplargs = dict(name=str(self._hero), texts=texts, texts0=texts0)
        normal, changes = tpl.expand(**tplargs), tpl.expand(changes=True, **tplargs)
        content = changes if texts0 and "normal" != conf.Positions.get("charsheet_view") else normal
        dlg = None
        def on_link(mode):
            if dlg: conf.Positions["charsheet_view"] = mode
            return changes if "normal" != mode else normal
        links = {k: on_link for k in (["normal", "changes"] if texts0 else ["normal"])}
        buttons = {"Copy data": self.on_copy_hero}
        dlg = controls.HtmlDialog(self._panel.TopLevelParent, "Hero character sheet", content,
                                  links, buttons, autowidth_links=True, style=wx.RESIZE_BORDER)
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
        if self._ignore_events or event.GetOldSelection() < 0: return
        page = self._ctrls["tabs"].GetCurrentPage()
        if page not in self._pages: self.select_index()
        else: self.select_hero(self._pages[page], status=False)


    def on_close_page(self, event):
        """Handler for closing a hero page, selects a previous hero page, if any."""
        if self._ignore_events: return
        tabs = self._ctrls["tabs"]
        page = tabs.GetPage(event.GetSelection())
        if page not in self._pages:
            event.Veto()  # Disallow closing index
            return
        page0 = tabs.GetCurrentPage()
        index = next((i for p, i in self._pages.items() if p == page), 0)
        self._pages.pop(page, None)
        visited = [x for x in self._pages_visited if x != index]
        self._pages_visited = [v for i, v in enumerate(visited) if not i or v != visited[i - 1]]
        if page0 is page:  # Closed the active page
            self._hero = None
            if self._pages_visited[-1:] in ([], [None]): self.select_index()
            else: self.select_hero(self._pages_visited[-1], status=False)
        elif self._hero == self._heroes[index]:  # Closed last active page from index
            self._hero = None


    def on_dragdrop_page(self, event=None):
        """Handler for dragging a page, keeps index-page first."""
        tabs = self._ctrls["tabs"]
        tabs.Freeze()
        self._ignore_events = True
        try:
            cur_page = tabs.GetCurrentPage()
            idx_index, idx_page = next((i, p) for i in range(tabs.GetPageCount())
                                       for p in [tabs.GetPage(i)] if p not in self._pages)
            if idx_index > 0:
                text = tabs.GetPageText(idx_index)
                tabs.RemovePage(idx_index)
                tabs.InsertPage(0, page=idx_page, text=text)
            if tabs.GetCurrentPage() != cur_page:
                tabs.SetSelection(tabs.GetPageIndex(cur_page))
        finally:
            self._ignore_events = False
            tabs.Thaw()


    def on_index_link(self, event):
        """Handler for clicking a link in index page, opens hero or sorts index."""
        href = event.GetLinkInfo().Href
        if href.isnumeric(): self.select_hero(int(href))
        elif href.startswith("sort:"):
            col = href[len("sort:"):]
            if self._index["sort_col"] == col:
                self._index["sort_asc"] = not self._index["sort_asc"]
            else:
                self._index["sort_col"], self._index["sort_asc"] = col, True
            self.populate_index(force=True)


    def on_key(self, event):
        """Handler for pressing a key, focuses filter on Ctrl-F."""
        event.Skip()
        if event.KeyCode in [ord("F")] and event.CmdDown():
            self._ctrls["search"].SetFocus()


    def on_search(self, event):
        """Handler for changing search text, filters heroes index after a delay."""
        event.Skip()
        self._index["timer"], _ = None, self._index["timer"] and self._index["timer"].Stop()
        if getattr(event, "KeyCode", None) == wx.WXK_ESCAPE:
            event.EventObject.Value = ""
        self._index["timer"] = wx.CallLater(self.SEARCH_INTERVAL, self.populate_index, focus=True)


    def on_select_hero(self, event):
        """Handler for selecting a hero in combobox, populates tabs with hero data."""
        if self._ignore_events: return
        index = event.EventObject.Selection
        hero2 = self._heroes[index] if index < len(self._heroes) else None
        if not hero2:
            wx.MessageBox("Hero '%s' not found." % event.EventObject.Value,
                          conf.Title, wx.OK | wx.ICON_ERROR)
            return
        self.select_hero(index, status=index not in self._pages.values())


    def on_key_select(self, event):
        """Handler for keypress in hero combobox, queues restoring selection if Escape pressed."""
        event.Skip()
        if event.KeyCode == wx.WXK_ESCAPE: # Workaround for Escape selecting keyboard-focused item
            prev_index = self._ctrls["hero"].Selection
            self._ignore_events = True
            wx.CallAfter(self._ctrls["hero"].Select, prev_index)
            wx.CallAfter(setattr, self, "_ignore_events", False)


    def on_export_heroes(self, event):
        """Handler for exporting heroes to file, opens file dialog and exports data."""
        if not self._index["visible"]: return
        basename = os.path.splitext(os.path.basename(self.savefile.filename))[0]
        self._dialog_export.Filename = "Heroes from %s" % basename
        if wx.ID_OK != self._dialog_export.ShowModal(): return

        wx.YieldIfNeeded() # Allow dialog to disappear
        path = controls.get_dialog_path(self._dialog_export)
        format = os.path.splitext(path)[-1].strip(".").lower()
        guibase.status("Exporting %s..", path, flash=True)
        templates.export_heroes(path, format, self._index["visible"], self.savefile,
                                categories=self._index["toggles"])
        guibase.status("Exported %s (%s).", path, util.format_bytes(os.path.getsize(path)),
                       flash=True)
        util.start_file(path)


    def on_toggle_category(self, event):
        """Handler for toggling a category in index toolbar, refreshes heroes index."""
        category = next(k for k, v in self._index["ids"].items() if v == event.Id)
        on = not self._index["toggles"][category]
        self._index["toggles"][category] = on
        self.populate_index(force=True)
        conf.HeroToggles.pop(category, None) if on else conf.HeroToggles.update({category: False})


    def on_sys_colour_change(self, event):
        """Handler for system colour change, refreshes hero index HTML."""
        event.Skip()
        wx.CallAfter(lambda: self._panel and self.populate_index())
        wx.CallLater(100, lambda: self._panel and self._panel.Layout())


    def select_hero(self, index, status=True):
        """
        Populates panel with hero data and ensures hero tab focus.

        @param   index     hero index in local structure
        @param   status    whether to show status messages
        """
        if not self._panel: return
        hero2 = self._heroes[index] if index < len(self._heroes) else None
        if not hero2: return
        if hero2 is self._hero and index in self._pages.values():
            self.select_hero_tab(index)
            return

        combo, tabs, tb = self._ctrls["hero"], self._ctrls["tabs"], self._ctrls["toolbar"]
        busy = controls.BusyPanel(self._panel, "Loading %s." % hero2) if status else None
        if status: guibase.status("Loading %s.", hero2, flash=True)

        self._ignore_events = True
        self._panel.Freeze()
        combo.SetSelection(index)
        page_existed = index in self._pages.values()
        if not page_existed:
            page = wx.Window(tabs)
            self._pages[page] = index
            title = "%s%s" % (hero2, "*" if hero2.is_changed() else "")
            tabs.AddPage(page, title, select=True)
            style = tabs.GetAGWWindowStyleFlag() | wx.lib.agw.flatnotebook.FNB_X_ON_TAB
            if tabs.GetAGWWindowStyleFlag() != style: tabs.SetAGWWindowStyleFlag(style)
        else:
            self.select_hero_tab(index)

        self._indexpanel.Hide()
        self._heropanel.Show()
        tb.Enable()
        tb.Show()
        try:
            if self._hero: self.patch()
            if not page_existed:
                logger.info("Loading hero %s (bytes %s-%s in savefile).",
                            hero2, hero2.span[0], hero2.span[1] - 1)
            self._hero = hero2
            for p in self._plugins:
                self.render_plugin(p["name"], reload=True, log=not page_existed)

        finally:
            if self._pages_visited[-1:] != [index]: self._pages_visited.append(index)
            self._panel.Layout()
            self._panel.Thaw()
            self._ignore_events = False
            if status: busy.Close(), wx.CallLater(500, guibase.status, "")
            evt = h3sed.gui.SavefilePageEvent(self._panel.Id)
            evt.SetClientData(dict(plugin=self.name, load=hero2.get_name_ident()))
            wx.PostEvent(self._panel, evt)


    def select_hero_tab(self, index):
        """Ensures hero tab is selected and hero panel shown."""
        combo, tabs, tb = self._ctrls["hero"], self._ctrls["tabs"], self._ctrls["toolbar"]
        page = next(p for p, i in self._pages.items() if i == index)
        idx  = next(i for i in range(tabs.GetPageCount()) if page is tabs.GetPage(i))
        if tabs.GetSelection() != idx: tabs.SetSelection(idx)
        style = tabs.GetAGWWindowStyleFlag() | wx.lib.agw.flatnotebook.FNB_X_ON_TAB
        if tabs.GetAGWWindowStyleFlag() != style: tabs.SetAGWWindowStyleFlag(style)
        if not self._heropanel.Shown:
            tb.Enable()
            tb.Show()
            self._indexpanel.Hide()
            self._heropanel.Show()
            self._panel.Layout()
        if combo.Selection != index: combo.SetSelection(index)


    def select_index(self):
        """Switches to index page if not already there."""
        combo, tabs, tb, search = (self._ctrls[k] for k in ("hero", "tabs", "toolbar", "search"))
        searchsel = search.GetSelection()
        focusctrl = self._panel.FindFocus()
        self.populate_index()
        if tabs.GetSelection(): tabs.SetSelection(0)
        style = tabs.GetAGWWindowStyleFlag() & (~wx.lib.agw.flatnotebook.FNB_X_ON_TAB)
        if tabs.GetAGWWindowStyleFlag() != style: tabs.SetAGWWindowStyleFlag(style)
        if not self._indexpanel.Shown:
            tb.Hide()
            tb.Disable()
            self._heropanel.Hide()
            self._indexpanel.Show()
            self._panel.Layout()
        if combo.Selection >= 0: combo.SetSelection(-1)
        if self._pages_visited[-1:] != [None]: self._pages_visited.append(None)
        if focusctrl is search and not search.HasFocus():
            search.SetFocus()
            search.SetSelection(*searchsel)


    def parse_hero_yaml(self, value):
        """Populates current hero with value parsed as YAML."""
        try:
            states = next(iter(yaml.safe_load(value).values()))
            assert isinstance(states, dict)
        except Exception as e:
            logger.warning("Error loading hero data from clipboard: %s", e)
            guibase.status("No valid hero data in clipboard.", flash=conf.StatusShortFlashLength)
            return

        new_states = {}  # {property name: state}
        pluginmap = {p["name"]: p["instance"] for p in self._plugins}
        for category, state in states.items():
            plugin = pluginmap.get(category)
            if not plugin:
                logger.warning("Unknown category in hero data: %r", category)
                continue  # for

            state0 = plugin.state()
            if state is None:
                state = state0.copy()
                state.clear()

            if isinstance(state0, type(state)) \
            or isinstance(state0, (list, set)) and isinstance(state, (list, set)):
                new_states[category] = state
            else:
                logger.warning("Invalid data type in hero data %r for %s: %s",
                               category, type(state0).__name__, state)
        if not new_states: return

        def on_do(states):
            changeds = []  # [property name, ]
            pluginmap = {p["name"]: p["instance"] for p in self._plugins}
            for category, state in states.items():
                if pluginmap[category].load_state(state):
                    changeds.append(category)
            self._hero.realize()
            self._hero_yamls[self._hero] = templates.make_hero_yamls(self._hero)
            if changeds:
                self.patch()
                for name in changeds:
                    self.render_plugin(name)
            return bool(changeds)
        self.command(functools.partial(on_do, new_states), "paste hero data from clipboard")


    def get_data(self):
        """Returns copy of current hero object."""
        return self._hero.copy() if self._hero else None


    def set_data(self, hero):
        """Sets current hero object."""
        combo, tabs = self._ctrls["hero"], self._ctrls["tabs"]
        index = next(i for i, h in enumerate(self._heroes) if h == hero)
        if index in self._pages.values():
            self.select_hero_tab(index)
        else:
            page = wx.Window(tabs)
            self._pages[page] = index
            tabs.AddPage(page, str(hero), select=True)
            self._indexpanel.Hide()
            self._heropanel.Show()
        if self._hero != hero:
            self._hero = self._heroes[index]
        self._hero.update(hero)
        self._hero_yamls[self._hero] = templates.make_hero_yamls(self._hero)
        combo.SetSelection(index)


    def get_changes(self, html=True):
        """Returns changes to current heroes, as HTML diff content or plain text brief."""
        TEMPLATE = templates.HERO_DIFF_HTML if html else templates.HERO_DIFF_TEXT
        changes, tpl = [], step.Template(TEMPLATE, escape=html, strip=html)
        for hero in self._heroes:
            if not hero.is_changed(): continue # for hero
            yamls = self._hero_yamls[hero]
            pairs = [(v1, v2) for v1, v2 in zip(yamls["originals"], yamls["currents"]) if v1 != v2]
            changes.append(tpl.expand(name=str(hero), changes=pairs))
        return "\n".join(changes)


    def patch(self):
        """Serializes current plugin state to hero bytes, patches savefile binary."""
        self._hero.serialize()
        self.savefile.patch(self._hero.bytes, self._hero.span)

        self._hero_yamls[self._hero] = templates.make_hero_yamls(self._hero)

        title = "%s%s" % (self._hero, "*" if self._hero.is_changed() else "")
        index = next(i for i, h in enumerate(self._heroes) if h == self._hero)
        page = next(p for p, i in self._pages.items() if i == index)
        self._ctrls["tabs"].SetPageText(self._ctrls["tabs"].GetPageIndex(page), title)
        wx.PostEvent(self._panel, h3sed.gui.SavefilePageEvent(self._panel.Id))


    def render_plugin(self, name, reload=False, log=True):
        """
        Renders or re-renders panel for the specified plugin.

        @param   reload  whether plugins should re-parse state from hero bytes
        @param   log     whether should log actions
        """
        p = next((x for x in self._plugins if x["name"] == name), None)
        if not p:
            logger.warning("Call to render unknown plugin %s.", name)
            return

        def fmt(state):
            if isinstance(state, set):  return list(state)
            if isinstance(state, dict): return {k: v for k, v in state.items() if v is not None}
            if isinstance(state, list) and state[-2:] == [None, None]: # Collapse trailing blanks
                count = next((i for i, x in enumerate(state[::-1]) if x is not None), len(state))
                return (("%s + " % state[:len(state) - count]) if count < len(state) else "") + \
                       "%s * %s" % ([None], count)
            return state

        plugin, item0 = p["instance"], p["instance"].item()
        if reload or item0 is None:
            plugin.load(self._hero)
            if log: logger.info("Loaded hero %s %s %s.", self._hero, p["name"], fmt(plugin.state()))
        p["panel"].Freeze()
        try:
            do_accelerate = False
            if callable(getattr(plugin, "render", None)):
                do_accelerate = plugin.render()
            elif callable(getattr(plugin, "props",  None)):
                h3sed.gui.build(plugin, p["panel"])
                do_accelerate = True
            if do_accelerate or item0 is None:
                wx_accel.accelerate(p["panel"])
        finally:
            controls.ColourManager.Patch(p["panel"])
            p["panel"].Thaw()
