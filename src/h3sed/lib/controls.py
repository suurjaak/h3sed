# -*- coding: utf-8 -*-
"""
Stand-alone GUI components for wx:

- HtmlDialog(wx.Dialog):
  Popup dialog showing a wx.HtmlWindow.

- BusyPanel(wx.Window):
  Primitive hover panel with a message that stays in the center of parent
  window.

- ColourManager(object):
  Updates managed component colours on Windows system colour change.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     14.03.2020
@modified    04.02.2023
------------------------------------------------------------------------------
"""
import collections
import os
import webbrowser

import wx
import wx.html
import wx.lib.agw.labelbook
import wx.lib.gizmos
import wx.lib.wordwrap


try: text_types = (str, unicode)        # Py2
except Exception: text_types = (str, )  # Py3


class HtmlDialog(wx.Dialog):
    """Popup dialog showing a wx.HtmlWindow, with an OK-button."""

    def __init__(self, parent, title, content, style=0):
        wx.Dialog.__init__(self, parent, title=title,
                           style=wx.CAPTION | wx.CLOSE_BOX | style)
        wrapper = wx.ScrolledWindow(self) if style & wx.RESIZE_BORDER else None
        html = self.html = wx.html.HtmlWindow(wrapper or self)
        self.content = content

        html.SetPage(content() if callable(content) else content)
        html.BackgroundColour = ColourManager.GetColour(wx.SYS_COLOUR_WINDOW)
        html.ForegroundColour = ColourManager.GetColour(wx.SYS_COLOUR_BTNTEXT)
        html.Bind(wx.html.EVT_HTML_LINK_CLICKED,
                  lambda e: webbrowser.open(e.GetLinkInfo().Href))

        if wrapper:
            wrapper.Sizer = wx.BoxSizer(wx.VERTICAL)
            wrapper.Sizer.Add(html, proportion=1, flag=wx.GROW)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(wrapper or html, proportion=1, flag=wx.GROW)
        sizer_buttons = self.CreateButtonSizer(wx.OK)
        self.Sizer.Add(sizer_buttons, border=8, flag=wx.ALIGN_CENTER | wx.ALL)
        self.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.OnSysColourChange)

        self.Layout()
        DISPSIZE = wx.Display(self).ClientArea.Size
        FRAMEH = 2 * wx.SystemSettings.GetMetric(wx.SYS_FRAMESIZE_Y, self) + \
                 wx.SystemSettings.GetMetric(wx.SYS_CAPTION_Y, self)
        width = html.VirtualSize[0] + 2*8
        height = FRAMEH + html.VirtualSize[1] + sizer_buttons.Size[1] + 2*8
        self.Size = min(width, DISPSIZE.Width), min(height, DISPSIZE.Height)
        self.MinSize = (400, 300)
        self.CenterOnParent()


    def OnSysColourChange(self, event):
        """Handler for system colour change, refreshes content."""
        event.Skip()
        def dorefresh():
            if not self: return
            self.html.SetPage(self.content() if callable(self.content) else self.content)
            self.html.BackgroundColour = ColourManager.GetColour(wx.SYS_COLOUR_WINDOW)
            self.html.ForegroundColour = ColourManager.GetColour(wx.SYS_COLOUR_BTNTEXT)
        wx.CallAfter(dorefresh) # Postpone to allow conf to update



class BusyPanel(wx.Window):
    """
    Primitive hover panel with a message that stays in the center of parent
    window.
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
