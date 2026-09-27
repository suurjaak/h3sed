# -*- coding: utf-8 -*-
"""
UI plugin for managing named entities like heroes in a savefile.


Subplugin modules are expected to have the following API (all methods either mandatory or missing):

    def props():
        '''
        Returns plugin props {name, ?label, ?index}.
        Label is used as plugin tab label, falling back to plugin name.
        Index is used for sorting plugins.
        '''

    def factory(parent, panel, version):
        '''
        Returns new plugin instance.

        @param   parent   parent plugin (entity-plugin instance)
        @param   panel    wx.Panel for plugin render
        @param   version  game version
        '''


Subplugin instances are expected to have the following API:

    def props(self):
        '''Mandatory. Returns props for subplugin, if using gui.build().'''

    def state(self):
        '''Mandatory. Returns subplugin state for gui.build().'''

    def load(self, entity):
        '''Mandatory. Loads entity to subplugin state.'''

    def render(self):
        '''
        Optional. Renders subplugin into panel given in factory(),
        if subplugin not renderable with gui.build().
        '''

    def make_common_menu(self):
        '''Optional. Returns wx.Menu with plugin-specific actions.'''

    def on_add(self, prop, value):
        '''
        Optional. Handler for adding something in subplugin
        (like a secondary skill), returning operation success.
        '''

    def on_change(self, prop, value, ctrl, rowindex=None):
        '''
        Optional. Handler for changing something in subplugin
        (like secondary skill level), returning operation success.
        '''

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   14.03.2020
@modified  26.09.2026
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
from .. lib import i18n
from .. lib import util
from .. lib import wx_accel
from .. lib.i18n import translate as __
from .. import conf
from .. import guibase
from .. import templates


logger = logging.getLogger(__package__)


class EntityPlugin(object):
    """Provides UI functionality for viewing and updating entity data in savegame."""

    """Milliseconds to wait after edit before applying search filter"""
    SEARCH_INTERVAL = 300


    def __init__(self, kind, savefile, panel, commandprocessor):
        self.name         = kind
        self.savefile     = savefile
        self._panel       = panel  # wxPanel container for plugin components
        self._undoredo    = commandprocessor # wx.CommandProcessor
        self._plugins     = []     # [{name, label, instance, panel}, ]
        self._entities    = []     # Entities ordered by name
        self._ctrls       = {}     # {name: wx.Control, }
        self._pages       = {}     # {wx.Window from self._ctrls["tabs"]: index in self._entities}
        self._indexpanel  = None   # Entities index panel
        self._entitypanel = None   # Container for all components of selected entity
        self._propspanel  = None   # Container for entity property components
        self._entity      = None   # Currently selected entity instance
        self._entity_yamls  = {}   # {entity: {full, originals, currents}}
        self._pages_visited = []   # Visited tabs, as [index in self._entities or None if index page]
        self._subtab_focus = {}    # {entity index in self._entities: focused subtab index}
        self._ignore_events = False  # For ignoring change events from programmatic selections et al
        self._index = {
            "entitytexts": [],     # [entity contents to search in, as [{category: plaintext}] ]
            "html":       "",      # Current entity search results HTML
            "text":       "",      # Current search text
            "stale":      True,    # Whether should repopulate index before display
            "timer":      None,    # wx.Timer for filtering entities index
            "ids":        {},      # {category: wx ID for toolbar toggle}
            "visible":    [],      # List of entities visible, ordered by name
            "toggles":    collections.OrderedDict(),  # {category: toggled state}
            "sort_col":   conf.Settings.get("%s.sort_col" % kind, "index"),  # Field being sorted by
            "sort_asc":   conf.Settings.get("%s.sort_asc" % kind, True),     # Sort ascending or descending
        }
        self._dialog_export = wx.FileDialog(panel, __("Export %s to file" % util.plural(kind)),
            wildcard="|".join("{0} (*.{1})|*.{1}".format(__(label), format)
                              for format, label in sorted(templates.EXPORT_FORMATS.items())),
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT | wx.FD_CHANGE_DIR | wx.RESIZE_BORDER
        )
        self._dialog_export.FilterIndex = 1

        self._entities = self.savefile.heroes[:]
        self.prebuild()
        panel.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        panel.Bind(h3sed.gui.EVT_PLUGIN, self.on_plugin_event)
        panel.TopLevelParent.bind_status_clearer(self._panel)


    def prebuild(self):
        """Builds general UI components."""
        self._panel.Freeze()
        self._panel.DestroyChildren()
        self._panel.Sizer and self._panel.Sizer.Clear()
        label  = wx.StaticText(self._panel, name="selectentitylabel",
                               label=__("&Select %s" % self.name) + ":")
        combo  = wx.ComboBox(self._panel, name="selectentity", style=wx.CB_DROPDOWN | wx.CB_READONLY)
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
        export = wx.Button(indexpanel, label=__("Expo&rt"))
        export.SetBitmap(bmpx)
        export.SetBitmapMargins(0, 0)
        export.ToolTip = __("Export %s to HTML or data file" % util.plural(self.name))
        if "hero" != self.name: export.Hide()
        export.Bind(wx.EVT_BUTTON, self.on_export_entities)

        PROPERTY_CATEGORIES = templates.HERO_PROPERTY_CATEGORIES
        for category in PROPERTY_CATEGORIES:
            togglename = "%s.toggle_%s" % (self.name, category)
            help = __("Show or hide %s column" + ("s" if "stats" == category else ""), __(category))
            b = tb_index.AddCheckTool(wx.ID_ANY, __(category.capitalize()), wx.NullBitmap,
                                      shortHelp=help)
            tb_index.ToggleTool(b.Id, conf.Settings.get(togglename, True))
            tb_index.Bind(wx.EVT_TOOL, self.on_toggle_category, id=b.Id)
            self._index["ids"][category] = b.Id
            self._index["toggles"][category] = conf.Settings.get(togglename, True)
        tb_index.Realize()

        html = wx.html.HtmlWindow(indexpanel)
        tabs.AddPage(wx.Window(tabs), " %s " % __("INDEX"))

        CTRL = "Cmd" if "darwin" == sys.platform else "Ctrl"
        search.SetDescriptiveText(__("Search %s" % util.plural(self.name)))
        search.ShowSearchButton(True)
        search.ShowCancelButton(True)
        search.ToolTip = __("Filter %s index on any matching text" % self.name) + " (%s-F)" % CTRL
        search.Bind(wx.EVT_CHAR, self.on_search)
        search.Bind(wx.EVT_TEXT, self.on_search)
        search.Bind(wx.EVT_SEARCH, self.on_search) if hasattr(wx, "EVT_SEARCH") else None
        controls.ColourManager.Manage(html, "ForegroundColour", wx.SYS_COLOUR_BTNTEXT)
        controls.ColourManager.Manage(html, "BackgroundColour", wx.SYS_COLOUR_WINDOW)
        html.SetBorders(0)
        html.Bind(wx.html.EVT_HTML_LINK_CLICKED, self.on_index_link)
        html.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.on_sys_colour_change)

        entitypanel = self._entitypanel = wx.Panel(self._panel)
        entitypanel.Sizer = wx.BoxSizer(wx.VERTICAL)

        tb = wx.ToolBar(entitypanel, style=wx.TB_FLAT | wx.TB_NODIVIDER)

        combo.Bind(wx.EVT_COMBOBOX, self.on_select_entity)
        combo.Bind(wx.EVT_KEY_DOWN, self.on_key_select)

        bmp1 = wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, wx.ART_TOOLBAR, (20, 20))
        bmp2 = wx.ArtProvider.GetBitmap(wx.ART_COPY,        wx.ART_TOOLBAR, (20, 20))
        bmp3 = wx.ArtProvider.GetBitmap(wx.ART_PASTE,       wx.ART_TOOLBAR, (20, 20))
        bmp4 = wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE,   wx.ART_TOOLBAR, (16, 16))
        tb.AddTool(wx.ID_INFO,  "", bmp1, shortHelp=__("Show %s full character sheet" % self.name) + "\t%s-I" % CTRL)
        tb.AddSeparator()
        tb.AddTool(wx.ID_COPY,  "", bmp2, shortHelp=__("Copy current %s data to clipboard" % self.name))
        tb.AddTool(wx.ID_PASTE, "", bmp3, shortHelp=__("Paste data from clipboard to current %s" % self.name))
        tb.AddSeparator()
        tb.AddTool(wx.ID_SAVE,  "", bmp4, shortHelp=__("Save current %s to file" % self.name))
        tb.Bind(wx.EVT_TOOL, self.on_charsheet,    id=wx.ID_INFO)
        tb.Bind(wx.EVT_TOOL, self.on_copy_entity,  id=wx.ID_COPY)
        tb.Bind(wx.EVT_TOOL, self.on_paste_entity, id=wx.ID_PASTE)
        tb.Bind(wx.EVT_TOOL, self.on_save_entity,  id=wx.ID_SAVE)
        self._panel.Bind(wx.EVT_MENU, self.on_charsheet, id=wx.ID_INFO)
        tb.Realize()

        menubutton = wx.Button(entitypanel, label=__("Change %s", __("all")) + " ..")
        menubutton.ToolTip = __("Change multiple properties on page")
        menubutton.Bind(wx.EVT_BUTTON, self.on_entity_subtab_button)

        tabs.MinSize = -1, tabs.GetTabArea().MinSize[1]
        tabs.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_change_page, tabs)
        tabs.Bind(wx.lib.agw.flatnotebook.EVT_FLATNOTEBOOK_PAGE_CLOSING,
                  self.on_close_page, tabs)
        tabs.Bind(wx.lib.agw.flatnotebook.EVT_FLATNOTEBOOK_PAGE_DROPPED,
                  self.on_dragdrop_page, tabs)
        controls.ColourManager.Manage(tabs, "TabAreaColour", wx.SYS_COLOUR_BTNFACE)

        indexpanel.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_opts = wx.BoxSizer(wx.VERTICAL)
        sizer_footer = wx.BoxSizer(wx.HORIZONTAL)
        sizer_footer.Add(info)
        sizer_footer.AddStretchSpacer()
        sizer_footer.Add(export)
        sizer_opts.Add(tb_index)
        sizer_opts.Add(sizer_footer, flag=wx.GROW)
        indexpanel.Sizer.Add(html, border=10, flag=wx.LEFT | wx.RIGHT | wx.GROW, proportion=1)
        indexpanel.Sizer.Add(sizer_opts, border=10, flag=wx.LEFT | wx.RIGHT | wx.GROW)

        propspanel = self._propspanel = wx.Panel(entitypanel)
        propspanel.Sizer = wx.BoxSizer(wx.VERTICAL)

        sizer = self._panel.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer_top = wx.BoxSizer(wx.HORIZONTAL)
        sizer_top.Add(label,  border=10, flag=wx.RIGHT | wx.ALIGN_CENTER)
        sizer_top.Add(combo,  border=5,  flag=wx.TOP  | wx.BOTTOM | wx.GROW)
        sizer_top.AddStretchSpacer()
        sizer_top.Add(search, border=5, flag=wx.ALL, proportion=1)
        sizer_top.AddSpacer(5)
        sizer_tabtop = wx.BoxSizer(wx.HORIZONTAL)
        sizer_tabtop.Add(tb)
        sizer_tabtop.AddStretchSpacer()
        sizer_tabtop.Add(menubutton)
        sizer.Add(sizer_top,    border=10, flag=wx.LEFT | wx.GROW)
        sizer.Add(tabs,         border=5,  flag=wx.BOTTOM | wx.GROW)
        sizer.Add(indexpanel,   border=5,  flag=wx.GROW, proportion=1)
        entitypanel.Sizer.Add(sizer_tabtop, border=10, flag=wx.LEFT | wx.RIGHT | wx.GROW)
        entitypanel.Sizer.Add(propspanel, border=5, flag=wx.TOP | wx.GROW, proportion=1)
        sizer.Add(entitypanel, flag=wx.TOP | wx.GROW, proportion=1)
        entitypanel.Disable()
        entitypanel.Hide()

        wx_accel.accelerate(self._panel, accelerators=[(wx.ACCEL_CMD, ord("I"), wx.ID_INFO)])
        self._panel.Layout()
        self._panel.Thaw()

        self._ctrls["tabs"] = tabs
        self._ctrls["entity"] = combo
        self._ctrls["search"] = search
        self._ctrls["count"] = info
        self._ctrls["html"] = html
        self._ctrls["toolbar"] = tb
        self._ctrls["menubutton"] = menubutton
        controls.ColourManager.Patch(self._panel)


    def build(self):
        """Builds entity UI components."""
        self._panel.Freeze()
        self._entitypanel.Enable()
        self._entitypanel.Show()
        self._propspanel.DestroyChildren()
        self._propspanel.Sizer.Clear()
        del self._plugins[:]
        self._ctrls["entity"].SetItems([str(x) for x in self._entities])

        nb = wx.Notebook(self._propspanel)
        PROPERTIES = h3sed.hero.PROPERTIES
        self._plugins = [dict(m.props(), module=m) for m in PROPERTIES.values()
                         if callable(getattr(m, "props", None))]
        for props in self._plugins:
            subpanel = props["panel"] = wx.ScrolledWindow(nb)
            title = props.get("label", props["name"])
            nb.AddPage(subpanel, __(title))
            controls.ColourManager.Manage(subpanel, "BackgroundColour", wx.SYS_COLOUR_BTNFACE)
            plugin = props["module"].factory(self, subpanel, self.savefile.version_id)
            has_menu = hasattr(plugin, "make_common_menu") and bool(plugin.make_common_menu())
            props["instance"] = plugin
            props["has_menu"] = has_menu

        self._propspanel.Sizer.Add(nb, border=10, flag=wx.ALL ^ wx.TOP | wx.GROW, proportion=1)

        if conf.Settings.get("%s.tab_index" % self.name) \
        and conf.Settings["%s.tab_index" % self.name] < len(self._plugins):
            nb.SetSelection(conf.Settings["%s.tab_index" % self.name])
        self._ctrls["menubutton"].Enable(self._plugins[nb.Selection]["has_menu"])

        nb.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_change_entity_subtab)

        self._entitypanel.Disable()
        self._entitypanel.Hide()
        self._panel.Thaw()
        self._ctrls["properties"] = nb
        with controls.BusyPanel(self._panel, __("Loading %s." % util.plural(self.name))):
            self.populate_index()


    def rebuild(self):
        """Rebuilds all current UI state from scratch."""
        wildcard = "|".join("{0} (*.{1})|*.{1}".format(__(label), format)
                            for format, label in sorted(templates.EXPORT_FORMATS.items()))
        self._dialog_export.Wildcard = wildcard

        indexes_open = [self._pages[p] for i in range(self._ctrls["tabs"].GetPageCount())
                        for p in [self._ctrls["tabs"].GetPage(i)] if p in self._pages]
        entity0 = self._entity if self._ctrls["tabs"].GetSelection() else None
        self.prebuild()

        self._entity = None
        self._pages.clear()
        for k, v in list(self._index.items()):
            if isinstance(v, (str, list)): self._index[k] = type(v)()
        self._entity_yamls.clear()

        self._panel.Freeze()
        self._ignore_events = True
        try:
            self.build()
            for index in indexes_open:
                entity = self._entities[index]
                page = wx.Window(self._ctrls["tabs"])
                self._pages[page] = index
                self._ctrls["tabs"].AddPage(page, str(entity), select=entity is self._entity)

            index = None
            if entity0:  index = next(i for i, x in enumerate(self._entities) if x is entity0)
            self.select_index() if index is None else self.select_entity(index, status=False)
            self._panel.Layout()
        finally:
            self._ignore_events = False
            self._panel.Thaw()


    def command(self, callable, name=None):
        """Submits callable to undo-redo command processor to be invoked."""
        if not self._panel: return
        self._index["stale"] = True
        self._undoredo.Submit(h3sed.gui.PluginCommand(self, callable, name))


    def render(self, reparse=False, reload=False, rebuild=False, log=True):
        """
        Renders entity selection and editing subtabs into our panel.

        @param   reparse  whether plugins should re-parse state from savefile
        @param   reload   whether plugins should reload state from entity
        @param   rebuild  whether all UI should be rebuilt
        @param   log      whether plugin should log actions
        """
        if reparse or reload or rebuild: self._index["stale"] = True

        if rebuild:
            self.rebuild()
        elif reparse:
            self.refresh_file()
        elif self._entity and self._propspanel.Children:
            for p in self._plugins:
                self.render_plugin(p["name"], reload=reload, log=log)
        else: self.build()


    def action(self, **kwargs):
        """Handler for action (load=entity name|index) or (save=True, ?rename=True, ?spans=[..])."""
        if kwargs.get("load") is not None:
            value = kwargs["load"]
            if isinstance(value, int): # Entity absolute index
                index = max(0, min(value, len(self._entities) - 1))
            elif isinstance(value, (list, tuple)): # (entity name, name counter if duplicate)
                entity_name, name_counter = value[:2] if len(value) > 1 else (value[0], 1)
                candidates = [i for i, x in enumerate(self._entities) if x.name == entity_name]
                index = candidates[min(name_counter, len(candidates)) - 1] if candidates else -1
            else: index = next((i for i, x in enumerate(self._entities) if x.name == value), -1)
            if index >= 0 and self._entities:
                self.select_entity(index)

        if kwargs.get("save"):
            tabs = self._ctrls["tabs"]
            entities_open = []
            for index, entity in enumerate(self._entities):
                if kwargs.get("spans") \
                and not any(a <= entity.span[0] and entity.span[1] <= b for a, b in kwargs["spans"]):
                    continue  # for index, entity

                entity.mark_saved()
                self._entity_yamls[entity] = templates.make_entity_yamls(entity)
                page = next((p for p, i in self._pages.items() if i == index), None)
                if page is not None:
                    entities_open.append(entity)
                    tabs.SetPageText(tabs.GetPageIndex(page), str(entity))
            if kwargs.get("rename") and entities_open:
                evt = h3sed.gui.SavefilePageEvent(self._panel.Id)
                evt.SetClientData(dict(plugin=self.name,
                                       load=[x.get_name_ident() for x in entities_open]))
                wx.PostEvent(self._panel, evt)  # Propagate to parent


    def refresh_file(self):
        """Reloads entities and refreshes UI."""
        tabs = self._ctrls["tabs"]
        entity0 = self._entity if self._pages_visited[-1:] not in ([], [None]) else None
        pages0 = [self._pages[p] for i in range(tabs.GetPageCount())
                  for p in [tabs.GetPage(i)] if p in self._pages]  # [entity index, ]
        entities0  = self._entities[:]
        visited0 = self._pages_visited[:]
        self._entity = None
        self._pages.clear()
        del self._pages_visited[:]
        for k, v in list(self._index.items()):
            if isinstance(v, (str, list)): self._index[k] = type(v)()

        self._entities = self.savefile.heroes[:]
        self._entity_yamls.clear()
        self._panel.Freeze()
        self._ignore_events = True
        try:
            while tabs.GetPageCount() > 1: tabs.DeletePage(1)
            self.build()
            entity = None
            for index in pages0:
                entity1 = entities0[index]
                entity2 = index < len(self._entities) and self._entities[index]
                if entity1 != entity2:
                    entity2 = next((x for x in self._entities if x == entity1), None)  # Match name+index
                    entity2 = entity2 or next((x for x in self._entities if x.name == entity1.name), None)
                if not entity2:
                    visited0 = [i for i in visited0 if i != index]
                    continue  # for index
                page = wx.Window(tabs)
                self._pages[page] = index
                if not entity and entity0 and entity2.name == entity0.name: entity = entity2
                tabs.AddPage(page, str(entity2), select=entity2 is entity)

            visited0 = [v for i, v in enumerate(visited0) if not i or v != visited0[i - 1]]
            self._pages_visited[:] = visited0
            if not entity and visited0[-1:] not in ([], [None]): entity = self._entities[visited0[-1]]
            index = next(i for i, x in enumerate(self._entities) if x is entity) if entity else None
            self.select_index() if index is None else self.select_entity(index, status=False)
            self._panel.Layout()
        finally:
            self._ignore_events = False
            self._panel.Thaw()


    def populate_index(self, focus=False, force=False):
        """Populates entities index page, filtered by current search if any."""
        if not self._panel: return
        html, searchtext = self._ctrls["html"], self._ctrls["search"].Value.strip()
        if not self._index["stale"] and not force \
        and self._index["text"] == searchtext and self._index["entitytexts"]:
            return

        TPL, PROPERTY_CATEGORIES = templates.HERO_SEARCH_TEXT, templates.HERO_PROPERTY_CATEGORIES

        entities, links = self._entities[:], list(range(len(self._entities)))
        tpl = step.Template(TPL)
        tplargs = dict(sort_col=self._index["sort_col"], sort_asc=self._index["sort_asc"],
                       categories=self._index["toggles"])
        maketexts = lambda x: {c: tpl.expand(**{self.name: x, "category": c}, **tplargs).lower()
                               for c in (["name"] + PROPERTY_CATEGORIES)}
        if not self._index["entitytexts"]:
            for entity in entities:
                self._entity_yamls[entity] = templates.make_entity_yamls(entity)
            self._index["entitytexts"] = [maketexts(h) for h in entities]
        elif self._entity:
            index = next(i for i, h in enumerate(self._entities) if h == self._entity)
            self._index["entitytexts"][index] = maketexts(self._entity)
        entitytexts = self._index["entitytexts"]

        if searchtext:
            words, entitytexts = searchtext.strip().lower().split(), self._index["entitytexts"]
            texts = ["\n".join(t for c, t in tt.items() if "name" == c or self._index["toggles"][c])
                     for tt in entitytexts]
            matches = [(i, h) for i, (h, t) in enumerate(zip(entities, texts))
                       if all(w in t for w in words)]
            links, entities = zip(*matches) if matches else ([], [])
            entitytexts = [self._index["entitytexts"][i] for i in links]
        self._index["text"] = searchtext
        self._index["visible"] = entities
        tplargs.update(count=len(self._entities), links=links, text=searchtext, savefile=self.savefile)
        tplargs.update({util.plural(self.name): entities, "%stexts" % self.name: entitytexts})
        page = step.Template(templates.HERO_INDEX_HTML, escape=True).expand(**tplargs)
        if page != self._index["html"]:
            info = "%s %s" % (len(entities), __(util.plural("entity", entities, numbers=False)))
            if len(entities) != len(self._entities):
                info = __("%s visible (%s total)", info, len(self._entities))
            self._ctrls["count"].Label = info
            self._index["html"] = page
            html.SetPage(page)
            html.Scroll(html.GetScrollPos(wx.HORIZONTAL), 0)
            html.BackgroundColour = controls.ColourManager.GetColour(wx.SYS_COLOUR_WINDOW)
            html.ForegroundColour = controls.ColourManager.GetColour(wx.SYS_COLOUR_BTNTEXT)
        self._index["stale"] = False
        if focus:
            self.select_index()


    def on_copy_entity(self, event=None):
        """Handler for copying an entity, adds entity data to clipboard."""
        if self._entity and wx.TheClipboard.Open():
            content = "%s:%s" % (templates.encode_yaml_scalar(self._entity.name), os.linesep)
            content += self._entity_yamls[self._entity]["full"]
            d = wx.TextDataObject(content)
            wx.TheClipboard.SetData(d), wx.TheClipboard.Close()
            guibase.status("Copied %s %%s data to clipboard." % self.name, self._entity,
                           flash=conf.StatusShortFlashLength, log=True, translate=True)


    def on_paste_entity(self, event=None):
        """Handler for pasting an entity, sets data from clipboard to entity."""
        value = None
        if self._entity and wx.TheClipboard.Open():
            if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)):
                o = wx.TextDataObject()
                wx.TheClipboard.GetData(o)
                value = o.Text
            wx.TheClipboard.Close()
        if value:
            guibase.status("Pasting data to %s %%s from clipboard." % self.name, self._entity,
                           flash=conf.StatusShortFlashLength, log=True, translate=True)
            self.parse_entity_yaml(value)


    def on_save_entity(self, event=None):
        """Handler for saving an entity, sends event to save current entity span."""
        changes = ""
        if self._entity.is_changed():
            yamls = self._entity_yamls[self._entity]
            pairs = [(v1, v2) for v1, v2 in zip(yamls["originals"], yamls["currents"]) if v1 != v2]
            tpl = step.Template(templates.ENTITY_DIFF_TEXT)
            changes = tpl.expand(name=self._entity.name, changes=pairs)
        logger.info("Saving %s %s to file.", self.name, self._entity)
        evt = h3sed.gui.SavefilePageEvent(self._panel.Id)
        evt.SetClientData(dict(save=True, spans=[self._entity.span], changes=changes))
        wx.PostEvent(self._panel, evt)


    def on_charsheet(self, event=None):
        """Opens popup with full entity profile."""
        if not self._entitypanel.Shown: return

        tpl = step.Template(templates.ENTITY_MANIFEST_HTML, escape=True)
        mode = "normal"
        texts, htmls = {"normal": self._entity_yamls[self._entity]["full"]}, {}
        if self._entity.is_changed():
            for k in ("currents", "originals"):
                texts[k] = self._entity_yamls[self._entity][k]
        tplargs = dict(name=str(self._entity), texts=texts)
        htmls["normal"] = tpl.expand(**tplargs)
        if self._entity.is_changed():
            htmls["changes"] = tpl.expand(mode="changes", **tplargs)
            htmls["changesonly"] = tpl.expand(mode="changesonly", **tplargs)
            mode = conf.Settings.get("%s.manifest_view" % self.name)
            if mode not in htmls: mode = "normal"

        dlg = None
        def on_link(mode):
            if dlg: conf.Settings["%s.manifest_view" % self.name] = mode
            return htmls.get(mode, htmls["normal"])
        links = {k: on_link for k in htmls} if self._entity.is_changed() else None
        buttons = {__("Copy data"): self.on_copy_entity}
        title = "Hero character sheet"
        dlg = controls.HtmlDialog(self._panel.TopLevelParent, __(title), htmls[mode],
                                  links, buttons, autowidth_links=True, style=wx.RESIZE_BORDER)
        def after(dlg):
            if not self._panel: return
            with dlg: dlg.ShowModal()
        wx.CallAfter(after, dlg) # After to allow clicked toolbar icon to lose focus


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
        """Handler for changing a page in the entities notebook, loads entity data."""
        if self._ignore_events or event.GetOldSelection() < 0: return
        page = self._ctrls["tabs"].GetCurrentPage()
        if page not in self._pages: self.select_index()
        else: self.select_entity(self._pages[page], status=False)


    def on_change_entity_subtab(self, event):
        """Handler for changing a page in the entity properties notebook, updates UI and settings."""
        conf.Settings.update({"%s.tab_index" % self.name: event.Selection})
        self._ctrls["menubutton"].Enable(self._plugins[event.Selection]["has_menu"])
        index = next(i for i, h in enumerate(self._entities) if h == self._entity)
        self._subtab_focus[index] = event.Selection


    def on_entity_subtab_button(self, event):
        """Handler for clicking plugin top menu button, opens plugin menu."""
        plugin = self._plugins[self._ctrls["properties"].Selection]["instance"]
        menu = hasattr(plugin, "make_common_menu") and plugin.make_common_menu()
        if not menu: return
        self._ctrls["menubutton"].PopupMenu(menu, pos=(0, self._ctrls["menubutton"].Size.Height))


    def on_close_page(self, event):
        """Handler for closing an entity page, selects a previous entity page, if any."""
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
            self._entity = None
            if self._pages_visited[-1:] in ([], [None]): self.select_index()
            else: self.select_entity(self._pages_visited[-1], status=False)
        elif self._entity == self._entities[index]:  # Closed last active page from index
            self._entity = None


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
        """Handler for clicking a link in index page, opens entity or sorts index."""
        href = event.GetLinkInfo().Href
        if href.isnumeric(): self.select_entity(int(href))
        elif href.startswith("sort:"):
            col = href[len("sort:"):]
            if self._index["sort_col"] == col:
                self._index["sort_asc"] = not self._index["sort_asc"]
            else:
                self._index["sort_col"], self._index["sort_asc"] = col, True
            conf.Settings.update({"%s.sort_col" % self.name: self._index["sort_col"],
                                  "%s.sort_asc" % self.name: self._index["sort_asc"]})
            self.populate_index(force=True)


    def on_key(self, event):
        """Handler for pressing a key, focuses filter on Ctrl-F."""
        event.Skip()
        if event.KeyCode == ord("F") and event.CmdDown():
            self._ctrls["search"].SetFocus()


    def on_search(self, event):
        """Handler for changing search text, filters entities index after a delay."""
        event.Skip()
        self._index["timer"], _ = None, self._index["timer"] and self._index["timer"].Stop()
        if getattr(event, "KeyCode", None) == wx.WXK_ESCAPE:
            event.EventObject.Value = ""
        self._index["timer"] = wx.CallLater(self.SEARCH_INTERVAL, self.populate_index, focus=True)


    def on_select_entity(self, event):
        """Handler for selecting an entity in combobox, populates tabs with entity data."""
        if self._ignore_events: return
        index = event.EventObject.Selection
        entity2 = self._entities[index] if index < len(self._entities) else None
        if not entity2:
            wx.MessageBox(__("%s '%%s' not found." % self.name.title(), event.EventObject.Value),
                          conf.Title, wx.OK | wx.ICON_ERROR)
            return
        focusctrl = self._panel.FindFocus()
        self.select_entity(index, status=index not in self._pages.values())
        if focusctrl is self._ctrls["entity"] and not self._ctrls["entity"].HasFocus():
            self._ctrls["entity"].SetFocus()


    def on_key_select(self, event):
        """Handler for keypress in entity combobox, queues restoring selection if Escape pressed."""
        if event.CmdDown(): # Avoid combobox selecting entity on keyboard shortcuts like Ctrl-F
            return
        event.Skip()
        if event.KeyCode == wx.WXK_ESCAPE: # Workaround for Escape selecting keyboard-focused item
            prev_index = self._ctrls["entity"].Selection
            self._ignore_events = True
            wx.CallAfter(self._ctrls["entity"].Select, prev_index)
            wx.CallAfter(setattr, self, "_ignore_events", False)


    def on_export_entities(self, event):
        """Handler for exporting entities to file, opens file dialog and exports data."""
        if not self._index["visible"]: return
        basename = os.path.splitext(os.path.basename(self.savefile.filename))[0]
        self._dialog_export.Filename = __("%s from %%s" % util.plural(self.name).title(), basename)
        if wx.ID_OK != self._dialog_export.ShowModal(): return

        wx.YieldIfNeeded() # Allow dialog to disappear
        path = controls.get_dialog_path(self._dialog_export)
        format = os.path.splitext(path)[-1].strip(".").lower()
        guibase.status(__("Exporting %s", path) + "..", flash=True)
        templates.export_heroes(path, format, self._index["visible"], self.savefile,
                                categories=self._index["toggles"])
        guibase.status("Exported %s (%s).", path, util.format_bytes(os.path.getsize(path)),
                       flash=True, log=True, translate=True)
        util.start_file(path)


    def on_toggle_category(self, event):
        """Handler for toggling a category in index toolbar, refreshes entities index."""
        category = next(k for k, v in self._index["ids"].items() if v == event.Id)
        on = not self._index["toggles"][category]
        self._index["toggles"][category] = on
        self.populate_index(force=True)
        if on: conf.Settings.pop("%s.toggle_%s" % (self.name, category), None)
        else: conf.Settings.update({"%s.toggle_%s" % (self.name, category): False})


    def on_sys_colour_change(self, event):
        """Handler for system colour change, refreshes entity index HTML."""
        event.Skip()
        wx.CallAfter(lambda: self._panel and self.populate_index(force=True))
        wx.CallLater(100, lambda: self._panel and self._panel.Layout())


    def select_entity(self, index, status=True):
        """
        Populates panel with entity data and ensures entity tab focus.

        @param   index     entity index in local structure
        @param   status    whether to show status messages
        """
        if not self._panel: return
        entity2 = self._entities[index] if index < len(self._entities) else None
        if not entity2: return
        if entity2 is self._entity and index in self._pages.values():
            self.select_entity_tab(index)
            return

        combo, tabs = self._ctrls["entity"], self._ctrls["tabs"]
        busy = controls.BusyPanel(self._panel, __("Loading %s.", entity2)) if status else None
        if status: guibase.status(__("Loading %s.", entity2), flash=True)

        self._ignore_events = True
        self._panel.Freeze()
        combo.SetSelection(index)
        page_existed = index in self._pages.values()
        if not page_existed:
            page = wx.Window(tabs)
            self._pages[page] = index
            title = "%s%s" % (entity2, "*" if entity2.is_changed() else "")
            tabs.InsertPage(1, page, title, select=True)
            style = tabs.GetAGWWindowStyleFlag() | wx.lib.agw.flatnotebook.FNB_X_ON_TAB
            if tabs.GetAGWWindowStyleFlag() != style: tabs.SetAGWWindowStyleFlag(style)
        else:
            self.select_entity_tab(index)

        self._indexpanel.Hide()
        self._entitypanel.Enable()
        self._entitypanel.Show()
        try:
            if self._entity: self.patch()
            if not page_existed and status:
                logger.info("Loading %s %s (bytes %s-%s in savefile).",
                            self.name, entity2, entity2.span[0], entity2.span[1] - 1)
            self._entity = entity2
            for p in self._plugins:
                self.render_plugin(p["name"], reload=True, log=not page_existed and status)

        finally:
            if not self._panel: return
            if index in self._subtab_focus:
                self._ctrls["properties"].SetSelection(self._subtab_focus[index])
            else:
                self._subtab_focus[index] = self._ctrls["properties"].Selection
            if self._pages_visited[-1:] != [index]: self._pages_visited.append(index)
            self._panel.Layout()
            self._panel.Thaw()
            self._ignore_events = False
            if status: busy.Close(), wx.CallLater(500, guibase.status, "")
            evt = h3sed.gui.SavefilePageEvent(self._panel.Id)
            evt.SetClientData(dict(plugin=self.name, load=entity2.get_name_ident()))
            wx.PostEvent(self._panel, evt)


    def select_entity_tab(self, index):
        """Ensures entity tab is selected and entity panel shown."""
        combo, tabs = self._ctrls["entity"], self._ctrls["tabs"]
        page = next(p for p, i in self._pages.items() if i == index)
        idx  = next(i for i in range(tabs.GetPageCount()) if page is tabs.GetPage(i))
        if tabs.GetSelection() != idx:
            tabs.SetSelection(idx)
        style = tabs.GetAGWWindowStyleFlag() | wx.lib.agw.flatnotebook.FNB_X_ON_TAB
        if tabs.GetAGWWindowStyleFlag() != style:
            tabs.SetAGWWindowStyleFlag(style)
        if not self._entitypanel.Shown:
            self._indexpanel.Hide()
            self._entitypanel.Enable()
            self._entitypanel.Show()
            self._panel.Layout()
        if combo.Selection != index:
            combo.SetSelection(index)


    def select_index(self):
        """Switches to index page if not already there."""
        combo, tabs, search = (self._ctrls[k] for k in ("entity", "tabs", "search"))
        searchsel = search.GetSelection()
        focusctrl = self._panel.FindFocus()
        self.populate_index()
        if tabs.GetSelection(): tabs.SetSelection(0)
        style = tabs.GetAGWWindowStyleFlag() & (~wx.lib.agw.flatnotebook.FNB_X_ON_TAB)
        if tabs.GetAGWWindowStyleFlag() != style: tabs.SetAGWWindowStyleFlag(style)
        if not self._indexpanel.Shown:
            self._entitypanel.Hide()
            self._entitypanel.Disable()
            self._indexpanel.Show()
            self._panel.Layout()
        if combo.Selection >= 0: combo.SetSelection(-1)
        if self._pages_visited[-1:] != [None]: self._pages_visited.append(None)
        if focusctrl is search and not search.HasFocus():
            search.SetFocus()
            search.SetSelection(*searchsel)


    def parse_entity_yaml(self, value):
        """Populates current entity with value parsed as YAML."""
        try:
            states = next(iter(yaml.safe_load(value).values()))
            assert isinstance(states, dict)
        except Exception as e:
            logger.warning("Error loading %s data from clipboard: %s", self.name, e)
            guibase.status(__("No valid %s data in clipboard." % self.name),
                           flash=conf.StatusShortFlashLength)
            return

        new_states = {}  # {property name: state}
        pluginmap = {p["name"]: p["instance"] for p in self._plugins}
        states = util.recurse_convert(states, {str: i18n.translate_back})
        PROPERTIES = h3sed.hero.PROPERTIES
        for category, state in states.items():
            plugin = pluginmap.get(category)
            if not plugin:
                if category not in PROPERTIES:
                    logger.warning("Unknown category in %s data: %r", self.name, category)
                continue  # for

            state0 = plugin.state()
            if state is None:
                state = state0.copy()
                state.clear()

            if not isinstance(state0, type(state)) \
            and not all(isinstance(x, (list, set)) for x in (state0, state)):
                logger.warning("Invalid data type in %s data %r for %s: %s",
                               self.name, category, type(state0).__name__, state)
                continue # for category, state

            if isinstance(state, dict):
                named_props = [p for p in plugin.props() if isinstance(p, dict) and p.get("name")]
                keep = set(p["name"] for p in named_props if not p.get("readonly"))
                state = {k: v for k, v in state.items() if k in keep}
                if not state:
                    continue # for category, state

            new_states[category] = state
        if not new_states: return

        def on_do(states):
            changeds = []  # [property name, ]
            pluginmap = {p["name"]: p["instance"] for p in self._plugins}
            for category, state in states.items():
                if pluginmap[category].load_state(state):
                    changeds.append(category)
            self._entity.realize()
            self._entity_yamls[self._entity] = templates.make_entity_yamls(self._entity)
            if "equipment" in changeds and "stats" not in changeds:
                changeds.append("stats") # Artifact bonus texts may need refreshing
            if changeds:
                self.patch()
                for name in changeds:
                    self.render_plugin(name)
            return bool(changeds)
        self.command(functools.partial(on_do, new_states), "paste %s data from clipboard" % self.name)


    def get_data(self):
        """Returns copy of current entity object."""
        return self._entity.copy() if self._entity else None


    def set_data(self, entity):
        """Sets current entity object."""
        combo, tabs = self._ctrls["entity"], self._ctrls["tabs"]
        index = next(i for i, h in enumerate(self._entities) if h == entity)
        if index in self._pages.values():
            self.select_entity_tab(index)
        else:
            page = wx.Window(tabs)
            self._pages[page] = index
            tabs.InsertPage(1, page, str(entity), select=True)
            self._indexpanel.Hide()
            self._entitypanel.Show()
        if self._entity != entity:
            self._entity = self._entities[index]
        self._entity.update(entity)
        self._entity_yamls[self._entity] = templates.make_entity_yamls(self._entity)
        combo.SetSelection(index)


    def get_changes(self, html=True):
        """Returns changes to current entities, as HTML diff content or plain text brief."""
        TEMPLATE = templates.ENTITY_DIFF_HTML if html else templates.ENTITY_DIFF_TEXT
        changes, tpl = [], step.Template(TEMPLATE, escape=html, strip=html)
        for entity in self._entities:
            if not entity.is_changed(): continue # for entity
            yamls = self._entity_yamls[entity]
            pairs = [(v1, v2) for v1, v2 in zip(yamls["originals"], yamls["currents"]) if v1 != v2]
            changes.append(tpl.expand(name=str(entity), changes=pairs))
        return "\n".join(changes)


    def get_function_arguments(self):
        """
        Returns a dictionary of keyword arguments with current state for user functions.
        
        @return  {"hero": current entity, "heroes": visible entities,
                  "heroes_open": all open entities}
        """
        plural = util.plural(self.name)
        result = {self.name: self._entity, plural: self._index["visible"][:],
                  "%s_open" % plural: [self._entities[index] for index in self._pages.values()]}
        return result


    def patch(self):
        """Serializes current plugin state to entity bytes, patches savefile binary."""
        self._entity.serialize()
        self.savefile.patch(self._entity.bytes, self._entity.span)

        self._entity_yamls[self._entity] = templates.make_entity_yamls(self._entity)

        title = "%s%s" % (self._entity, "*" if self._entity.is_changed() else "")
        index = next(i for i, h in enumerate(self._entities) if h == self._entity)
        page = next(p for p, i in self._pages.items() if i == index)
        self._ctrls["tabs"].SetPageText(self._ctrls["tabs"].GetPageIndex(page), title)
        wx.PostEvent(self._panel, h3sed.gui.SavefilePageEvent(self._panel.Id))


    def render_plugin(self, name, reload=False, log=True):
        """
        Renders or re-renders panel for the specified plugin.

        @param   reload  whether plugins should re-parse state from entity bytes
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
            plugin.load(self._entity)
            if log: logger.info("Loaded %s %s %s %s.",
                                self.name, self._entity, p["name"], fmt(plugin.state()))
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
            p["panel"] and p["panel"].Thaw()
