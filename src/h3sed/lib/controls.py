# -*- coding: utf-8 -*-
"""
Stand-alone GUI components for wx:

- BusyPanel(wx.Window):
  Primitive hover panel with a message that stays in the center of parent window.

- ColourManager(object):
  Updates managed component colours on Windows system colour change.

- CommandHistoryDialog(wx.Dialog):
  Popup dialog for wx.CommandProcessor history, allows selecting a range to undo or redo.

- HtmlDialog(wx.Dialog):
  Popup dialog showing a wx.HtmlWindow.

- ItemHistory(wx.Object):
  Like wx.HileHistory but for any kind of items.

- Patch(object):
  Monkey-patches wx API for general compatibility over different versions.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     14.03.2020
@modified    11.06.2024
------------------------------------------------------------------------------
"""
import collections
import datetime
import functools
import os
import sys
import time
import webbrowser

import wx
import wx.html
import wx.lib.agw.labelbook
import wx.lib.gizmos
import wx.lib.wordwrap


try: text_types = (str, unicode)        # Py2
except Exception: text_types = (str, )  # Py3

PY3 = sys.version_info > (3, )

# wx.NewId() deprecated from around wxPython 4
NewId = (lambda: wx.NewIdRef().Id) if hasattr(wx, "NewIdRef") else wx.NewId



class BusyPanel(wx.Window):
    """
    Primitive hover panel with a message that stays in the center of parent window.

    Acts as an auto-closing context manager.
    """
    FOREGROUND_COLOUR = wx.WHITE
    BACKGROUND_COLOUR = wx.Colour(110, 110, 110, 255)
    REFRESH_INTERVAL  = 500

    def __init__(self, parent, label):
        wx.Window.__init__(self, parent)
        self.Hide() # Avoid initial flicker

        timer = self._timer = wx.Timer(self)

        label = wx.StaticText(self, label=label, style=wx.ST_ELLIPSIZE_END)

        self.BackgroundColour  = self.BACKGROUND_COLOUR
        label.ForegroundColour = self.FOREGROUND_COLOUR

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(label, border=15, flag=wx.ALL | wx.ALIGN_CENTER_HORIZONTAL)
        self.Fit()

        maxsize = [self.Parent.Size.width // 2, self.Parent.Size.height * 2 // 3]
        self.Size = tuple(min(a, b) for a, b in zip(self.Size, maxsize))

        self.Bind(wx.EVT_PAINT, lambda e: (e.Skip(), self.Refresh()))
        self.Bind(wx.EVT_TIMER, lambda e: (e.Skip(), self.Refresh()))
        self.Bind(wx.EVT_WINDOW_DESTROY, self._OnDestroy)

        self.Layout()
        self.CenterOnParent()
        self.Show()
        parent.Refresh()
        wx.Yield()
        timer.Start(self.REFRESH_INTERVAL)


    def __enter__(self):
        """Context manager entry, does nothing, returns self."""
        return self


    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager exit, destroys panel."""
        self.Close()


    def _OnDestroy(self, event):
        event.Skip()
        try: self._timer.Stop()
        except Exception: pass


    def Close(self):
        try: self.Destroy(); self.Parent.Refresh()
        except Exception: pass



class ColourManager(object):
    """
    Updates managed component colours on Windows system colour change.
    """
    colourcontainer   = None
    colourmap         = {} # {colour name in container: wx.SYS_COLOUR_XYZ}
    darkcolourmap     = {} # {colour name in container: wx.SYS_COLOUR_XYZ}
    darkoriginals     = {} # {colour name in container: original value}
    # {ctrl: (prop name: colour name in container)}
    ctrls             = collections.defaultdict(dict)


    @classmethod
    def Init(cls, window, colourcontainer, colourmap, darkcolourmap):
        """
        Hooks WM_SYSCOLORCHANGE on Windows, updates colours in container
        according to map.

        @param   window           application main window
        @param   colourcontainer  object with colour attributes
        @param   colourmap        {"attribute": wx.SYS_COLOUR_XYZ}
        @param   darkcolourmap    colours changed if dark background,
                                  {"attribute": wx.SYS_COLOUR_XYZ or wx.Colour}
        """

        cls.colourcontainer = colourcontainer
        cls.colourmap.update(colourmap)
        cls.darkcolourmap.update(darkcolourmap)
        for name in darkcolourmap:
            if not hasattr(colourcontainer, name): continue # for name
            cls.darkoriginals[name] = getattr(colourcontainer, name)

        cls.UpdateContainer()
        if "nt" != os.name: return

        # Hack: monkey-patch FlatImageBook with non-hardcoded background
        class HackContainer(wx.lib.agw.labelbook.ImageContainer):
            WHITE_BRUSH = wx.WHITE_BRUSH
            def OnPaint(self, event):
                bgcolour = cls.ColourHex(wx.SYS_COLOUR_WINDOW)
                if "#FFFFFF" != bgcolour:
                    wx.WHITE_BRUSH = wx.TheBrushList.FindOrCreateBrush(bgcolour)
                try: result = HackContainer.__base__.OnPaint(self, event)
                finally: wx.WHITE_BRUSH = HackContainer.WHITE_BRUSH
                return result
        wx.lib.agw.labelbook.ImageContainer = HackContainer

        # Hack: monkey-patch TreeListCtrl with working Colour properties
        wx.lib.gizmos.TreeListCtrl.BackgroundColour = property(
            wx.lib.gizmos.TreeListCtrl.GetBackgroundColour,
            wx.lib.gizmos.TreeListCtrl.SetBackgroundColour
        )
        wx.lib.gizmos.TreeListCtrl.ForegroundColour = property(
            wx.lib.gizmos.TreeListCtrl.GetForegroundColour,
            wx.lib.gizmos.TreeListCtrl.SetForegroundColour
        )

        window.Bind(wx.EVT_SYS_COLOUR_CHANGED, cls.OnSysColourChange)


    @classmethod
    def Manage(cls, ctrl, prop, colour):
        """
        Starts managing a control colour property.

        @param   ctrl    wx component
        @param   prop    property name like "BackgroundColour",
                         tries using ("Set" + prop)() if no such property
        @param   colour  colour name in colour container like "BgColour",
                         or system colour ID like wx.SYS_COLOUR_WINDOW
        """
        cls.ctrls[ctrl][prop] = colour
        cls.UpdateControlColour(ctrl, prop, colour)


    @classmethod
    def OnSysColourChange(cls, event):
        """
        Handler for system colour change, refreshes configured colours
        and updates managed controls.
        """
        event.Skip()
        cls.UpdateContainer()
        cls.UpdateControls()


    @classmethod
    def ColourHex(cls, idx):
        """Returns wx.Colour or system colour as HTML colour hex string."""
        colour = idx if isinstance(idx, wx.Colour) \
                 else wx.SystemSettings.GetColour(idx)
        return colour.GetAsString(wx.C2S_HTML_SYNTAX)


    @classmethod
    def GetColour(cls, colour):
        return wx.Colour(getattr(cls.colourcontainer, colour)) \
               if isinstance(colour, text_types) \
               else wx.SystemSettings.GetColour(colour)


    @classmethod
    def UpdateContainer(cls):
        """Updates configuration colours with current system theme values."""
        for name, colourid in cls.colourmap.items():
            setattr(cls.colourcontainer, name, cls.ColourHex(colourid))

        if "#FFFFFF" != cls.ColourHex(wx.SYS_COLOUR_WINDOW):
            for name, colourid in cls.darkcolourmap.items():
                setattr(cls.colourcontainer, name, cls.ColourHex(colourid))
        else:
            for name, value in cls.darkoriginals.items():
                setattr(cls.colourcontainer, name, value)


    @classmethod
    def UpdateControls(cls):
        """Updates all managed controls."""
        for ctrl, props in list(cls.ctrls.items()):
            if not ctrl: # Component destroyed
                cls.ctrls.pop(ctrl, None)
                continue # for ctrl, props

            for prop, colour in props.items():
                cls.UpdateControlColour(ctrl, prop, colour)


    @classmethod
    def UpdateControlColour(cls, ctrl, prop, colour):
        """Sets control property or invokes "Set" + prop."""
        mycolour = cls.GetColour(colour)
        if hasattr(ctrl, prop):
            setattr(ctrl, prop, mycolour)
        elif hasattr(ctrl, "Set" + prop):
            getattr(ctrl, "Set" + prop)(mycolour)



class CommandHistoryDialog(wx.Dialog):
    """
    Popup dialog for wx.CommandProcessor history, allows selecting a range to undo or redo.

    A "Time since" column is included in the history
    if the commands in CommandProcessor have `Timestamp` attributes as UNIX epoch.
    """

    def __init__(self, parent, cmdproc, title="Command History", style=0):
        wx.Dialog.__init__(self, parent, title=title,
                           style=wx.CAPTION | wx.CLOSE_BOX | wx.RESIZE_BORDER | style)
        self.edge = -1  # Choice index for first undo command
        cmdpos = cmdproc.Commands.index(cmdproc.CurrentCommand) if cmdproc.CurrentCommand else None
        if cmdpos is not None: self.edge = len(cmdproc.Commands) - cmdpos - 1
        headertext, choices = self._MakeTexts(cmdproc)

        label = wx.StaticText(self, label="Select command(s) to undo or redo:")
        header = wx.StaticText(self)
        listbox = wx.ListBox(self, choices=choices, style=wx.LB_MULTIPLE)
        sizer_buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)

        header.Label = headertext
        okbutton = next(c for c in self.Children if isinstance(c, wx.Button) and wx.ID_OK == c.Id)
        okbutton.Label = "Redo" if self.edge < 0 else "Undo"
        self.listbox = listbox
        self.okbutton = okbutton

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(label,         border=8, flag=wx.ALL)
        self.Sizer.Add(header,        border=8, flag=wx.LEFT)
        self.Sizer.Add(listbox,       border=8, flag=wx.LEFT | wx.RIGHT | wx.GROW, proportion=1)
        self.Sizer.Add(sizer_buttons, border=8, flag=wx.ALL | wx.ALIGN_CENTER)
        self.Layout()
        self.Size = self.MinSize = (400, 250)

        self._EnsureSelection()
        listbox.SetFocus()
        self.Bind(wx.EVT_LISTBOX, self._OnSelectChange, listbox)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self._OnSubmit, listbox)
        self.CenterOnParent()


    def GetSelection(self):
        """Returns the number of entries selected, negative if Undo."""
        sels = self.listbox.GetSelections()
        return (1 if self.edge < 0 or sels[0] < self.edge else -1) * len(sels) if sels else 0


    def _EnsureSelection(self, index=None):
        """
        Ensures a valid range of undo or redo entries being selected.

        @param   index  listbox index changed
        """
        if index is None:
            if self.edge >= 0: self.listbox.Select(self.edge)  # Select first undo
            for i in range(self.listbox.Count) if self.edge < 0 else ():
                self.listbox.Select(i)  # Select all redos if only redos
        else:
            rng = [self.edge, index]  # Undo range
            if self.edge < 0 or index < self.edge:  # Redo range
                rng = [index, self.listbox.Count - 1 if self.edge < 0 else self.edge - 1]
            for i in range(self.listbox.Count):
                (self.listbox.SetSelection if rng[0] <= i <= rng[1] else self.listbox.Deselect)(i)
            self.okbutton.Label = "Redo" if self.edge < 0 or index < self.edge else "Undo"


    def _MakeTexts(self, cmdproc):
        """Returns a list of texts for populating command history listbox."""
        choices = []
        columns, maxwidths, now = ["Number", "", "Command"], {}, time.time()
        has_stamps = cmdproc.Commands and all(
            isinstance(getattr(x, "Timestamp", None), (int, float)) and x.Timestamp > 0
            for x in cmdproc.Commands
        )
        if has_stamps: columns.insert(1, "Time since")
        headertext, INTER = "", " " * 6
        getw = lambda x: self.GetTextExtent(str(x))[0]
        spacew = self.GetTextExtent(" ")[0]
        for i, c in enumerate(columns):
            inter = "" if not i else INTER + ("" if c else " " * int(getw("Undo") / spacew))
            headertext += inter + c
            maxwidths[i] = max(maxwidths.get(i, 0), getw(c))
        for index, c in enumerate(x.Name for x in reversed(cmdproc.Commands)):
            category = "Redo" if self.edge < 0 or index < self.edge else "Undo"
            item = [len(cmdproc.Commands) - index, category, c]
            if has_stamps:
                cmd = cmdproc.Commands[len(cmdproc.Commands) - index - 1]
                since = str(datetime.timedelta(seconds=int(now - cmd.Timestamp)))
                item.insert(1, since[2:] if since.startswith("0:") else since)
            text = ""
            for i, (c, v) in enumerate(zip(columns, item)):
                pad = " " * int((maxwidths[i] - getw(v)) / spacew) if i < len(columns) - 1 else ""
                lpad, rpad = ("", pad) if i > 1 else (pad[:-1], " ")
                text += ("%s%s%s%s" % (INTER if i else "", lpad, v, rpad))
            choices.append(text)
        return headertext, choices


    def _OnSelectChange(self, event):
        """Handler for changing selection, ensures a valid range is selected."""
        self._EnsureSelection(event.Selection)


    def _OnSubmit(self, event):
        """Handler for double-clicking listbox, submits dialog."""
        self.EndModal(wx.ID_OK)


class HtmlDialog(wx.Dialog):
    """Popup dialog showing a wx.HtmlWindow, with an OK-button."""

    def __init__(self, parent, title, content,
                 links=None, buttons=None, autowidth_links=None, style=0):
        """
        @param   links            {href: page text or function(href) to return page text to show}
        @param   buttons          {label: function() to invoke}
        @param   autowidth_links  whether to auto-size dialog width to links content;
                                  None auto-sizes to links with texts only, False skips,
                                  True autosizes all links including callable content
        """
        wx.Dialog.__init__(self, parent, title=title, style=wx.CAPTION | wx.CLOSE_BOX | style)
        self.html = None
        self.content = content
        self.links = links.copy() if isinstance(links, dict) else {}

        wrapper = wx.ScrolledWindow(self) if style & wx.RESIZE_BORDER else None
        html = self.html = wx.html.HtmlWindow(wrapper or self)

        if wrapper:
            wrapper.Sizer = wx.BoxSizer(wx.VERTICAL)
            wrapper.Sizer.Add(html, proportion=1, flag=wx.GROW)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(wrapper or html, proportion=1, flag=wx.GROW)
        sizer_buttons = self.CreateButtonSizer(wx.OK)
        for label, handler in buttons.items() if buttons else ():
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, lambda e, f=handler: handler())
            sizer_buttons.Add(button, border=3, flag=wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER)
        self.Sizer.Add(sizer_buttons, border=8, flag=wx.ALIGN_CENTER | wx.ALL)
        self.Layout()

        if callable(content): content = content()
        html.SetPage(content)
        contentwidth = html.VirtualSize[0]
        for k, v in links.items() if links and autowidth_links is not False else ():
            v = v(k) if callable(v) and autowidth_links else v
            if isinstance(v, text_types):
                html.SetPage(v)
                contentwidth = max(contentwidth, html.VirtualSize[0])
            html.SetPage(content)
        html.BackgroundColour = ColourManager.GetColour(wx.SYS_COLOUR_WINDOW)
        html.ForegroundColour = ColourManager.GetColour(wx.SYS_COLOUR_BTNTEXT)

        html.Bind(wx.html.EVT_HTML_LINK_CLICKED, self.OnLink)
        self.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.OnSysColourChange)

        disparg = self if PY3 else 0
        BARWH = [wx.SystemSettings.GetMetric(x, self) for x in (wx.SYS_HSCROLL_Y, wx.SYS_VSCROLL_X)]
        MAXW = wx.Display(disparg).ClientArea.Size[0]
        MAXH = (parent.TopLevelParent if parent else wx.Display(disparg).ClientArea).Size[1]
        FRAMEH = 2 * wx.SystemSettings.GetMetric(wx.SYS_FRAMESIZE_Y, self) + \
                 wx.SystemSettings.GetMetric(wx.SYS_CAPTION_Y, self)
        width = contentwidth + 2*BARWH[0]
        height = FRAMEH + html.VirtualSize[1] + sizer_buttons.Size[1] + BARWH[1]
        self.Size = min(width, MAXW - 2*BARWH[0]), min(height, MAXH - 2*BARWH[1])
        self.MinSize = (400, 300)
        self.CenterOnParent()


    def OnLink(self, event):
        """Handler for clicking a link, sets new content if registered link else opens webbrowser."""
        href = event.GetLinkInfo().Href
        if href in self.links:
            page = self.links[href]
            if callable(page): page = page(href)
            if isinstance(page, text_types):
                bcol, fcol = event.EventObject.BackgroundColour, event.EventObject.ForegroundColour
                event.EventObject.SetPage(page)
                event.EventObject.BackgroundColour, event.EventObject.ForegroundColour = bcol, fcol
        else: webbrowser.open(href)


    def OnSysColourChange(self, event):
        """Handler for system colour change, refreshes content."""
        event.Skip()
        def dorefresh():
            if not self: return
            self.html.SetPage(self.content() if callable(self.content) else self.content)
            self.html.BackgroundColour = ColourManager.GetColour(wx.SYS_COLOUR_WINDOW)
            self.html.ForegroundColour = ColourManager.GetColour(wx.SYS_COLOUR_BTNTEXT)
        wx.CallAfter(dorefresh) # Postpone to allow conf to update


class ItemHistory(wx.Object):
    """Like wx.HileHistory but for any kind of items."""

    def __init__(self, maxItems=9, baseId=None):
        """
        @param   maxItems  maximum number of items to retain in menu
        @param   baseId    ID given to the first menu item
        """
        super(ItemHistory, self).__init__()
        self._max       = max(0, maxItems)
        self._baseId    = NewId() if baseId is None else baseId
        self._formatter = lambda x: u"%s" % (x, )
        self._items     = []
        self._menus     = []  # [wx.Menu, ]
        self._item_ids  = {}  # {wx.Menu: {Id: index}}


    def UseMenu(self, menu):
        """Adds given menu to the list of menus managed by this history object."""
        if menu not in self._menus:
            self._menus.append(menu)
            menu.Bind(wx.EVT_MENU, self._OnMenuItem)
            self.Populate()


    def RemoveMenu(self, menu):
        """Removes given menu from the list of menus managed by this history object."""
        if menu in self._menus:
            self._menus.remove(menu)
            menu.Unbind(wx.EVT_MENU, handler=self._OnMenuItem)


    def GetMenus(self):
        """Returns the list of menus managed by this history object."""
        return self._menus[:]
    Menus = property(GetMenus)


    def AddItem(self, item):
        """Adds item to history, as latest (first position in menus), repopulates menus."""
        if self._items and item == self._items[0]: return
        if item in self._items: self._items.remove(item)
        self._items.insert(0, item)
        if self._max > len(self._items):
            del self._items[self._max:]
        self.Populate()


    def RemoveItem(self, item):
        """Removes item from history, repopulates menus."""
        if item in self._items:
            self._items.remove(item)
            self.Populate()


    def Clear(self):
        """Removes all items from history and menu."""
        del self._items[:]
        self.Populate()


    def GetCount(self):
        """Returns the number of items currently in history."""
        return len(self._items)
    Count = property(GetCount)


    def GetMaxItems(self):
        """Returns the maximum number of items that can be stored."""
        return self._max
    def SetMaxItems(self, maxItems):
        """Sets the maximum number of items that can be stored, repopulates menus if needed."""
        self._max = max(0, maxItems)
        if self._max > len(self._items):
            del self._items[self._max:]
            self.Populate()
    MaxItems = property(GetMaxItems, SetMaxItems)


    def GetBaseId(self):
        """Returns the base identifier for menu items."""
        return self._baseId
    def SetBaseId(self, baseId):
        """Sets the base identifier for menu items, repopulates menus if needed."""
        if baseId is None: baseId = NewId()
        if baseId != self._baseId:
            self._baseId = baseId
            self.Populate()
    BaseId = property(GetBaseId, SetBaseId)


    def GetItems(self):
        """Returns current content items."""
        return self._items[:]
    def SetItems(self, items):
        """Sets current content items, repopulates menus."""
        self._items[:] = items
        self.Populate()
    Items = property(GetItems, SetItems)


    def GetItem(self, index):
        """Returns content item at specified index."""
        return self._items[index]


    def GetFormatter(self):
        """Returns menu label formatter function."""
        return self._hint
    def SetFormatter(self, formatter):
        """Sets menu label formatter function, as func(item), and repopulates menu."""
        if formatter != self._formatter:
            self._formatter = formatter
            self.Populate()
    Formatter = property(GetFormatter, SetFormatter)


    def Populate(self):
        """Clears and populates menus from current content items."""
        for m in self._menus:
            for x in m.MenuItems: m.Delete(x)
        self._item_ids.clear()
        for i, item in enumerate(self._items):
            label = "&%s %s" % (i + 1, self._formatter(item))
            for m in self._menus:
                menuitem = m.Append(wx.ID_ANY, label)
                self._item_ids.setdefault(m, {})[menuitem.Id] = i


    def _OnMenuItem(self, event):
        """Handler for clicking a menu item in an associated menu, fires EVT_MENU_RANGE."""
        menu = event.EventObject
        if event.Id not in self._item_ids.get(menu, {}): return
        evtId = self._baseId + self._item_ids[menu][event.Id]
        evt = wx.CommandEvent(wx.wxEVT_COMMAND_MENU_SELECTED, evtId)
        evt.EventObject = menu
        wx.PostEvent(menu.Window, evt)


class Patch(object):
    """Monkey-patches wx API for general compatibility over different versions."""

    _PATCHED = False

    @staticmethod
    def patch_wx(art=None):
        """
        Patches wx object methods to smooth over version and setup differences.

        @param   art  image overrides for wx.ArtProvider, as {image ID: wx.Bitmap}
        """
        if Patch._PATCHED: return

        if wx.VERSION >= (4, 2):
            # Previously, ToolBitmapSize was set to largest, and smaller bitmaps were padded
            ToolBar__Realize = wx.ToolBar.Realize
            def Realize__Patched(self):
                sz = tuple(self.GetToolBitmapSize())
                for i in range(self.GetToolsCount()):
                    t = self.GetToolByPos(i)
                    for b in filter(bool, (t.NormalBitmap, t.DisabledBitmap)):
                        sz = max(sz[0], b.Width), max(sz[1], b.Height)
                self.SetToolBitmapSize(sz)
                for i in range(self.GetToolsCount()):
                    t = self.GetToolByPos(i)
                    if t.NormalBitmap:   t.NormalBitmap   = resize_img(t.NormalBitmap,   sz)
                    if t.DisabledBitmap: t.DisabledBitmap = resize_img(t.DisabledBitmap, sz)
                return ToolBar__Realize(self)
            wx.ToolBar.Realize = Realize__Patched

            def resize_bitmaps(func):
                """Returns function pass-through wrapper, resizing any Bitmap arguments."""
                def inner(self, *args, **kwargs):
                    sz = self.GetToolBitmapSize()
                    args = [resize_img(v, sz) if v and isinstance(v, wx.Bitmap) else v for v in args]
                    kwargs = {k: resize_img(v, sz) if v and isinstance(v, wx.Bitmap) else v
                              for k, v in kwargs.items()}
                    return func(self, *args, **kwargs)
                return functools.update_wrapper(inner, func)
            wx.ToolBar.SetToolNormalBitmap   = resize_bitmaps(wx.ToolBar.SetToolNormalBitmap)
            wx.ToolBar.SetToolDisabledBitmap = resize_bitmaps(wx.ToolBar.SetToolDisabledBitmap)

        if wx.VERSION >= (4, 2) and art:
            # Patch wx.ArtProvider.GetBitmap to return given bitmaps for overridden images instead
            ArtProvider__GetBitmap = wx.ArtProvider.GetBitmap
            def GetBitmap__Patched(id, client=wx.ART_OTHER, size=wx.DefaultSize):
                if id in art and size == art[id].Size:
                    return art[id]
                return ArtProvider__GetBitmap(id, client, size)
            wx.ArtProvider.GetBitmap = GetBitmap__Patched

        Patch._PATCHED = True



def get_dialog_path(dialog):
    """
    Returns the file path chosen in FileDialog, adding extension if dialog result
    has none even though a filter has been selected, or if dialog result has a
    different extension than what is available in selected filter.
    """
    result = dialog.GetPath()

    # "SQLite database (*.db;*.sqlite;*.sqlite3)|*.db;*.sqlite;*.sqlite3|All files|*.*"
    wcs = dialog.Wildcard.split("|")
    wcs = wcs[1::2] if len(wcs) > 1 else wcs
    wcs = [[y.lstrip("*") for y in x.split(";")] for x in wcs] # [['.ext1', '.ext2'], ..]

    extension = os.path.splitext(result)[-1].lower()
    selexts = wcs[dialog.FilterIndex] if 0 <= dialog.FilterIndex < len(wcs) else None
    if result and selexts and extension not in selexts and dialog.ExtraStyle & wx.FD_SAVE:
        ext = next((x for x in selexts if "*" not in x), None)
        if ext: result += ext

    return result


def resize_img(img, size, aspect_ratio=True, bg=(-1, -1, -1)):
    """Returns a resized wx.Image or wx.Bitmap, centered in free space if any."""
    if not img or not size or list(size) == list(img.GetSize()): return img

    result = img if isinstance(img, wx.Image) else img.ConvertToImage()
    size1, size2 = list(result.GetSize()), list(size)
    align_pos = None
    if size1[0] < size[0] and size1[1] < size[1]:
        size2 = tuple(size1)
        align_pos = [(a - b) // 2 for a, b in zip(size, size2)]
    elif aspect_ratio:
        ratio = size1[0] / float(size1[1]) if size1[1] else 0.0
        size2[ratio > 1] = int(size2[ratio > 1] * (ratio if ratio < 1 else 1 / ratio))
        align_pos = [(a - b) // 2 for a, b in zip(size, size2)]
    if size1[0] > size[0] or size1[1] > size[1]:
        if result is img: result = result.Copy()
        result.Rescale(*size2)
    if align_pos:
        if result is img: result = result.Copy()
        result.Resize(size, align_pos, *bg)
    return result.ConvertToBitmap() if isinstance(img, wx.Bitmap) else result
