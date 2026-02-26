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
@modified    26.02.2026
------------------------------------------------------------------------------
"""
import collections
import datetime
import functools
import math
import os
import sys
import time
import webbrowser

import wx
import wx.html
import wx.lib.agw.labelbook
import wx.lib.gizmos
import wx.lib.wordwrap


try:
    integer_types, text_type = (int, long), basestring  # Py2
except NameError:
    integer_types, text_type = (int, ), str  # Py3

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
    Sets and manages component colours, handles system colour changes and dark themes.
    """
    colourcontainer = None # object with color attributes, like a class or config module
    isdarkmode      = None # True-False-None for darkened-default-autodetect
    colourmap       = {} # {colour name in container: wx.SYS_COLOUR_XYZ}
    darkcolourmap   = {} # {colour name in container: wx.SYS_COLOUR_XYZ}
    darkoriginals   = {} # {colour name in container: original value}
    regctrls        = set() # {ctrl, }
    # {ctrl: (prop name: colour name in container or wx.SYS_COLOUR_XYZ)}
    ctrlprops       = collections.defaultdict(dict)
    ctrlchildren    = collections.defaultdict(set) # {managed parent ctrl: {managed child controls}}


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
        if not ctrl: return
        cls.ctrlprops[ctrl][prop] = colour
        if isinstance(ctrl, wx.stc.StyledTextCtrl):
            cls.UpdateSTCColours(ctrl, {prop: colour})
        else:
            cls.UpdateControlColour(ctrl, prop, colour)
        if hasattr(ctrl, "GetParent") and ctrl.GetParent() and ctrl.GetParent() in cls.ctrlprops:
            cls.ctrlchildren[ctrl.GetParent()].add(ctrl)


    @classmethod
    def Register(cls, ctrl):
        """
        Registers a control for special handling, e.g. refreshing STC colours
        for instances of wx.py.shell.Shell on system colour change.
        """
        if isinstance(ctrl, wx.py.shell.Shell):
            cls.regctrls.add(ctrl)
            cls.SetShellStyles(ctrl)
            if ctrl.GetParent() in cls.ctrlprops:
                cls.ctrlchildren[ctrl.GetParent()].add(ctrl)


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
    def ColourHex(cls, colour, adjust=True):
        """
        Returns wx.Colour or system colour as HTML colour hex string.

        @param   adjust  whether to adapt for current dark mode if system colour ID
        """
        if not isinstance(colour, wx.Colour):
            colour = cls.EnsureModeColour(colour) if adjust else wx.SystemSettings.GetColour(colour)
        if colour.Alpha() != wx.ALPHA_OPAQUE:
            colour = wx.Colour(colour[:3])  # GetAsString(C2S_HTML_SYNTAX) can raise if transparent
        return colour.GetAsString(wx.C2S_HTML_SYNTAX)


    @classmethod
    def GetColour(cls, colour, adjust=True):
        """
        Returns wx.Colour or configured colour or system colour as wx.Colour.

        @param   adjust  whether to adapt for current dark mode if system colour ID
        """
        if isinstance(colour, wx.Colour): return colour
        if isinstance(colour, text_type): return wx.Colour(getattr(cls.colourcontainer, colour))
        if adjust: return cls.EnsureModeColour(colour)
        return wx.SystemSettings.GetColour(colour)


    @classmethod
    def Luminance(cls, colour):
        """Returns luminance value for wx.Colour or system colour, as a percentage ratio 0..1."""
        if isinstance(colour, integer_types): colour = wx.SystemSettings.GetColour(colour)
        r, g, b = colour[:3]
        # From HSP Color Model: https://alienryderflex.com/hsp.html
        return math.sqrt(0.299 * (r * r) + 0.587 * (g * g) + 0.114 * (b * b)) / 255


    @classmethod
    def Adjust(cls, colour1, colour2, ratio=0.5):
        """
        Returns first colour adjusted towards second, as wx.Colour.

        @param   colour1  wx.Colour, RGB tuple, colour hex string, or wx.SystemSettings colour index
        @param   colour2  wx.Colour, RGB tuple, colour hex string, or wx.SystemSettings colour index
        @param   ratio    RGB channel adjustment ratio towards second colour
        """
        colour1 = wx.SystemSettings.GetColour(colour1) \
                  if isinstance(colour1, integer_types) else wx.Colour(colour1)
        colour2 = wx.SystemSettings.GetColour(colour2) \
                  if isinstance(colour2, integer_types) else wx.Colour(colour2)
        rgb1, rgb2 = tuple(colour1)[:3], tuple(colour2)[:3]
        delta  = tuple(a - b for a, b in zip(rgb1, rgb2))
        result = tuple(a - int(d * ratio) for a, d in zip(rgb1, delta))
        result = tuple(min(255, max(0, x)) for x in result)
        return wx.Colour(result)


    @classmethod
    def Diff(cls, colour1, colour2):
        """
        Returns difference between two colours, as wx.Colour of absolute deltas over channels.

        @param   colour1  wx.Colour, RGB tuple, colour hex string, or wx.SystemSettings colour index
        @param   colour2  wx.Colour, RGB tuple, colour hex string, or wx.SystemSettings colour index
        """
        colour1 = wx.SystemSettings.GetColour(colour1) \
                  if isinstance(colour1, integer_types) else wx.Colour(colour1)
        colour2 = wx.SystemSettings.GetColour(colour2) \
                  if isinstance(colour2, integer_types) else wx.Colour(colour2)
        rgb1, rgb2 = tuple(colour1)[:3], tuple(colour2)[:3]
        result = tuple(abs(a - b) for a, b in zip(rgb1, rgb2))
        return wx.Colour(result)


    @classmethod
    def IsDarkDisplay(cls):
        """Returns whether display is in dark mode (Win10+ flag or judged from system colours)."""
        try:
            if wx.SystemSettings.GetAppearance().IsDark(): return True
        except Exception: pass
        bg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        fg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
        return sum(bg[:3]) < sum(fg[:3])


    @classmethod
    def IsDarkMode(cls):
        """Returns whether colour theme is in dark mode, either set here or detected from system."""
        return cls.IsDarkDisplay() if cls.isdarkmode is None else cls.isdarkmode


    @classmethod
    def SetDarkMode(cls, mode):
        """
        Sets whether darkened theme is forced (True), not used (False), or auto-detected (None).

        Refreshes controls if setting changed.
        """
        if mode is not None: mode = bool(mode)
        if mode is cls.isdarkmode: return
        cls.isdarkmode = mode
        cls.UpdateContainer()
        for window in wx.GetTopLevelWindows():
            window.Refresh()
            wx.PostEvent(window, wx.SysColourChangedEvent()) # Will invoke cls.OnSysColourChange()


    @classmethod
    def UpdateContainer(cls):
        """Updates configuration colours with current system theme values."""
        for name, colourid in cls.colourmap.items():
            setattr(cls.colourcontainer, name, cls.ColourHex(colourid))

        if cls.IsDarkMode():
            for name, colourid in cls.darkcolourmap.items():
                setattr(cls.colourcontainer, name, cls.ColourHex(colourid))
        else:
            for name, value in cls.darkoriginals.items():
                if name in cls.colourmap:
                    value = cls.ColourHex(cls.colourmap[name])
                setattr(cls.colourcontainer, name, value)


    @classmethod
    def UpdateControls(cls):
        """Updates all managed controls."""
        cls.ClearDestroyed()
        for ctrl, props in list(cls.ctrlprops.items()):
            if cls.DiscardIfDead(ctrl):
                continue # for ctrl, props

            if isinstance(ctrl, wx.stc.StyledTextCtrl):
                cls.UpdateSTCColours(ctrl, props)
            else:
                for prop, colour in props.items():
                    cls.UpdateControlColour(ctrl, prop, colour)

        for ctrl in list(cls.regctrls):
            if not cls.DiscardIfDead(ctrl) and isinstance(ctrl, wx.py.shell.Shell):
                cls.SetShellStyles(ctrl)


    @classmethod
    def UpdateControl(cls, ctrl):
        """Updates colours for specific managed control."""
        if cls.DiscardIfDead(ctrl):
            return
        if ctrl in cls.ctrlprops:
            if isinstance(ctrl, wx.stc.StyledTextCtrl):
                cls.UpdateSTCColours(ctrl, cls.ctrlprops[ctrl])
            else:
                for prop, colour in cls.ctrlprops[ctrl].items():
                    cls.UpdateControlColour(ctrl, prop, colour)
        if ctrl in cls.regctrls:
            if isinstance(ctrl, wx.py.shell.Shell): cls.SetShellStyles(ctrl)
        ctrl.Refresh()


    @classmethod
    def UpdateControlColour(cls, ctrl, prop, colour):
        """Sets control property or invokes "Set" + prop."""
        mycolour = cls.GetColour(colour)
        if "FoldMarginColour" == prop and isinstance(ctrl, wx.stc.StyledTextCtrl):
            ctrl.SetFoldMarginColour(True, mycolour)
        elif hasattr(ctrl, prop):
            setattr(ctrl, prop, mycolour)
        elif hasattr(ctrl, "Set" + prop):
            getattr(ctrl, "Set" + prop)(mycolour)


    @classmethod
    def UpdateSTCColours(cls, ctrl, props):
        """Updates colours for a StyledTextCtrl."""
        SPEC_PROPS = {"StyleBackground": "back", "StyleForeground": "fore"}
        style_specs = collections.OrderedDict() # {style number: ["name:value"]}
        for prop, colour in ((k, v) for k, v in props.items() if k in SPEC_PROPS):
            spec = "%s:%s" % (SPEC_PROPS[prop], cls.ColourHex(colour))
            if not ctrl.Lexer: # Must not override lexed syntax colouring
                style_specs.setdefault(wx.stc.STC_STYLE_DEFAULT, []).append(spec)
            if "StyleBackground" == prop:
                # Line number margin backgrounds need additional explicit setting
                style_specs.setdefault(wx.stc.STC_STYLE_LINENUMBER, []).append(spec)
        for style, specs in style_specs.items():
            ctrl.StyleSetSpec(style, ",".join(specs))
            if wx.stc.STC_STYLE_DEFAULT == style:
                ctrl.StyleClearAll() # NB: DEFAULT must be first in order, as it resets all
        for prop, colour in props.items():
            if prop not in SPEC_PROPS:
                cls.UpdateControlColour(ctrl, prop, colour)


    @classmethod
    def SetShellStyles(cls, stc):
        """Sets system colours to Python shell console."""

        fg    = cls.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
        bg    = cls.GetColour(wx.SYS_COLOUR_WINDOW)
        btbg  = cls.GetColour(wx.SYS_COLOUR_BTNFACE)
        grfg  = cls.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        ibg   = cls.GetColour(wx.SYS_COLOUR_INFOBK)
        ifg   = cls.GetColour(wx.SYS_COLOUR_INFOTEXT)
        hlfg  = cls.GetColour(wx.SYS_COLOUR_HOTLIGHT)
        q3bg  = cls.GetColour(wx.SYS_COLOUR_INFOBK)
        q3sfg = wx.Colour(127,   0,   0) # brown  #7F0000
        deffg = wx.Colour(  0, 127, 127) # teal   #007F7F
        eolbg = wx.Colour(224, 192, 224) # pink   #E0C0E0
        strfg = wx.Colour(127,   0, 127) # purple #7F007F

        if sum(fg) > sum(bg): # Background darker than foreground
            deffg = cls.Adjust(deffg, bg, -1)
            eolbg = cls.Adjust(eolbg, bg, -1)
            q3bg  = cls.Adjust(q3bg,  bg)
            q3sfg = cls.Adjust(q3sfg, bg, -1)
            strfg = cls.Adjust(strfg, bg, -1)

        faces = dict(wx.py.editwindow.FACES,
                     q3bg =cls.ColourHex(q3bg),  backcol  =cls.ColourHex(bg),
                     q3fg =cls.ColourHex(ifg),   forecol  =cls.ColourHex(fg),
                     deffg=cls.ColourHex(deffg), calltipbg=cls.ColourHex(ibg),
                     eolbg=cls.ColourHex(eolbg), calltipfg=cls.ColourHex(ifg),
                     q3sfg=cls.ColourHex(q3sfg), linenobg =cls.ColourHex(btbg),
                     strfg=cls.ColourHex(strfg), linenofg =cls.ColourHex(grfg),
                     keywordfg=cls.ColourHex(hlfg))

        # Default style
        stc.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT, "face:%(mono)s,size:%(size)d,"
                                                   "back:%(backcol)s,fore:%(forecol)s" % faces)
        stc.SetCaretForeground(fg)
        stc.StyleClearAll()
        stc.SetSelForeground(True, cls.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))
        stc.SetSelBackground(True, cls.GetColour(wx.SYS_COLOUR_HIGHLIGHT))

        # Built in styles
        stc.StyleSetSpec(wx.stc.STC_STYLE_LINENUMBER,  "back:%(linenobg)s,fore:%(linenofg)s,"
                                                       "face:%(mono)s,size:%(lnsize)d" % faces)
        stc.StyleSetSpec(wx.stc.STC_STYLE_CONTROLCHAR, "face:%(mono)s" % faces)
        stc.StyleSetSpec(wx.stc.STC_STYLE_BRACELIGHT,  "fore:#0000FF,back:#FFFF88")
        stc.StyleSetSpec(wx.stc.STC_STYLE_BRACEBAD,    "fore:#FF0000,back:#FFFF88")

        # Python styles
        stc.StyleSetSpec(wx.stc.STC_P_DEFAULT,      "face:%(mono)s" % faces)
        stc.StyleSetSpec(wx.stc.STC_P_COMMENTLINE,  "fore:#007F00,face:%(mono)s" % faces)
        stc.StyleSetSpec(wx.stc.STC_P_NUMBER,       "")
        stc.StyleSetSpec(wx.stc.STC_P_STRING,       "fore:%(strfg)s,face:%(mono)s" % faces)
        stc.StyleSetSpec(wx.stc.STC_P_CHARACTER,    "fore:%(strfg)s,face:%(mono)s" % faces)
        stc.StyleSetSpec(wx.stc.STC_P_WORD,         "fore:%(keywordfg)s,bold" % faces)
        stc.StyleSetSpec(wx.stc.STC_P_TRIPLE,       "fore:%(q3sfg)s" % faces)
        stc.StyleSetSpec(wx.stc.STC_P_TRIPLEDOUBLE, "fore:%(q3fg)s,back:%(q3bg)s" % faces)
        stc.StyleSetSpec(wx.stc.STC_P_CLASSNAME,    "fore:%(deffg)s,bold" % faces)
        stc.StyleSetSpec(wx.stc.STC_P_DEFNAME,      "fore:%(deffg)s,bold" % faces)
        stc.StyleSetSpec(wx.stc.STC_P_OPERATOR,     "")
        stc.StyleSetSpec(wx.stc.STC_P_IDENTIFIER,   "")
        stc.StyleSetSpec(wx.stc.STC_P_COMMENTBLOCK, "fore:#7F7F7F")
        stc.StyleSetSpec(wx.stc.STC_P_STRINGEOL,    "fore:#000000,face:%(mono)s,"
                                                    "back:%(eolbg)s,eolfilled" % faces)

        stc.CallTipSetBackground(faces['calltipbg'])
        stc.CallTipSetForeground(faces['calltipfg'])


    @classmethod
    def EnsureModeColour(cls, sys_colour):
        """
        Returns wx.Colour for given wx.SYS_COLOUR_XYZ, adjusted for dark mode per configuration.

        In dark mode, light backgrounds get darkened and dark foregrounds lightened.
        """
        GROUNDS = {wx.SYS_COLOUR_3DDKSHADOW:               -1, # -1 for background colour
                   wx.SYS_COLOUR_3DLIGHT:                   1, #  1 for foreground colour
                   wx.SYS_COLOUR_ACTIVEBORDER:              1,
                   wx.SYS_COLOUR_ACTIVECAPTION:             1,
                   wx.SYS_COLOUR_APPWORKSPACE:             -1,
                   wx.SYS_COLOUR_BTNFACE:                  -1,
                   wx.SYS_COLOUR_BTNHIGHLIGHT:             -1,
                   wx.SYS_COLOUR_BTNSHADOW:                -1,
                   wx.SYS_COLOUR_BTNTEXT:                   1,
                   wx.SYS_COLOUR_CAPTIONTEXT:               1,
                   wx.SYS_COLOUR_DESKTOP:                  -1,
                   wx.SYS_COLOUR_GRADIENTACTIVECAPTION:    -1,
                   wx.SYS_COLOUR_GRADIENTINACTIVECAPTION:  -1,
                   wx.SYS_COLOUR_GRAYTEXT:                  1,
                   wx.SYS_COLOUR_HIGHLIGHT:                -1,
                   wx.SYS_COLOUR_HIGHLIGHTTEXT:             1,
                   wx.SYS_COLOUR_HOTLIGHT:                  1,
                   wx.SYS_COLOUR_INACTIVEBORDER:            1,
                   wx.SYS_COLOUR_INACTIVECAPTION:          -1,
                   wx.SYS_COLOUR_INACTIVECAPTIONTEXT:       1,
                   wx.SYS_COLOUR_INFOBK:                   -1,
                   wx.SYS_COLOUR_INFOTEXT:                  1,
                   wx.SYS_COLOUR_LISTBOX:                  -1,
                   wx.SYS_COLOUR_LISTBOXHIGHLIGHTTEXT:      1,
                   wx.SYS_COLOUR_LISTBOXTEXT:               1,
                   wx.SYS_COLOUR_MENU:                     -1,
                   wx.SYS_COLOUR_MENUBAR:                  -1,
                   wx.SYS_COLOUR_MENUHILIGHT:              -1,
                   wx.SYS_COLOUR_MENUTEXT:                  1,
                   wx.SYS_COLOUR_SCROLLBAR:                -1,
                   wx.SYS_COLOUR_WINDOW:                   -1,
                   wx.SYS_COLOUR_WINDOWFRAME:               1,
                   wx.SYS_COLOUR_WINDOWTEXT:                1}
        if sys_colour not in GROUNDS: return sys_colour

        colour = wx.SystemSettings.GetColour(sys_colour)
        if cls.isdarkmode is False or cls.isdarkmode is None and not cls.IsDarkDisplay():
            return colour

        is_background = (GROUNDS[sys_colour] < 0)
        is_already_dark = (cls.Luminance(colour) < 0.5)
        if is_background == is_already_dark: return colour

        ratio = 0.5 if wx.SYS_COLOUR_GRAYTEXT == sys_colour else 0.8 if is_background else 0.9
        return cls.Adjust(colour, wx.BLACK if is_background else wx.WHITE, ratio)


    @classmethod
    def Patch(cls, ctrl):
        """
        Ensures foreground and background system colours on control and all its nested child controls.

        Sets certain pre-defined component types to have managed colours, adjusting for dark mode.

        @return  ctrl
        """
        PROPS = {wx.Button:     {"ForegroundColour":  wx.SYS_COLOUR_BTNTEXT,
                                 "BackgroundColour":  wx.SYS_COLOUR_BTNFACE},
                 wx.Choice:     {"ForegroundColour":  wx.SYS_COLOUR_WINDOWTEXT,
                                 "BackgroundColour":  wx.SYS_COLOUR_WINDOW},
                 wx.ComboBox:   {"ForegroundColour":  wx.SYS_COLOUR_BTNTEXT,
                                 "BackgroundColour":  wx.SYS_COLOUR_BTNFACE},
                 wx.CheckBox:   {"ForegroundColour":  wx.SYS_COLOUR_BTNTEXT},
                 wx.Dialog:     {"BackgroundColour":  wx.SYS_COLOUR_WINDOW},
                 wx.ListBox:    {"ForegroundColour":  wx.SYS_COLOUR_WINDOWTEXT,
                                 "BackgroundColour":  wx.SYS_COLOUR_WINDOW},
                 wx.ListCtrl:   {"ForegroundColour":  wx.SYS_COLOUR_WINDOWTEXT,
                                 "BackgroundColour":  wx.SYS_COLOUR_WINDOW},
                 wx.Notebook:   {"ForegroundColour":  wx.SYS_COLOUR_BTNTEXT,
                                 "BackgroundColour":  wx.SYS_COLOUR_BTNFACE},
                 wx.SpinCtrl:   {"ForegroundColour":  wx.SYS_COLOUR_BTNTEXT,
                                 "BackgroundColour":  wx.SYS_COLOUR_BTNFACE},
                 wx.StaticText: {"ForegroundColour":  wx.SYS_COLOUR_BTNTEXT},
                 wx.TextCtrl:   {"ForegroundColour":  wx.SYS_COLOUR_WINDOWTEXT,
                                 "BackgroundColour":  wx.SYS_COLOUR_WINDOW},
                 wx.ToolBar:    {"ForegroundColour":  wx.SYS_COLOUR_BTNTEXT,
                                 "BackgroundColour":  wx.SYS_COLOUR_BTNFACE},
                 wx.stc.StyledTextCtrl:
                                {"CaretForeground":  wx.SYS_COLOUR_WINDOWTEXT,
                                 "FoldMarginColour": wx.SYS_COLOUR_WINDOW,
                                 "StyleForeground":  wx.SYS_COLOUR_WINDOWTEXT,
                                 "StyleBackground":  wx.SYS_COLOUR_WINDOW}, }
        for myctrl in [ctrl] + get_all_children(ctrl):
            for proptype in (t for t in PROPS if issubclass(type(myctrl), t)):
                for prop, colour in PROPS[proptype].items():
                    if myctrl not in cls.ctrlprops or prop not in cls.ctrlprops[myctrl]:
                        cls.Manage(myctrl, prop, colour)
        cls.ClearDestroyed()
        return ctrl


    @classmethod
    def ClearDestroyed(cls):
        """Discards destroyed components from managed controls."""
        children = sum(map(list, cls.ctrlchildren.values()), [])
        for ctrl in set(cls.ctrlprops) | set(cls.regctrls) | set(cls.ctrlchildren) | set(children):
            cls.DiscardIfDead(ctrl)


    @classmethod
    def DiscardIfDead(cls, ctrl):
        """Discards component from managed controls if destroyed, returns whether was discarded."""
        ctrl_collections = [cls.ctrlprops, cls.regctrls, cls.ctrlchildren]
        ctrl_collections.extend(cls.ctrlchildren.values())
        if not any(ctrl in collection for collection in ctrl_collections): return False

        is_alive = ctrl and not ctrl.IsBeingDeleted()
        if is_alive: return False

        # Must track parents and children explicitly: in Linux, dialog ButtonSizer buttons
        # remain undestroyed but very crash-prone to examine: discard them along with the dialog.
        children = lambda c: [] if c not in cls.ctrlchildren else \
                             list(cls.ctrlchildren[c]) + sum(map(children, cls.ctrlchildren[c]), [])
        for ctrl in [ctrl] + children(ctrl):
            for collection in ctrl_collections:
                if ctrl in collection:
                    (collection.discard if isinstance(collection, set) else collection.pop)(ctrl)
        return True



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
        ColourManager.Patch(self)


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
        for label, handler in reversed(buttons.items()) if buttons else ():
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, lambda e, f=handler: handler())
            sizer_buttons.Insert(0, button, border=50, flag=wx.RIGHT)
        self.Sizer.Add(sizer_buttons, border=8, flag=wx.ALIGN_CENTER | wx.ALL)
        self.Layout()

        if callable(content): content = content()
        html.SetPage(content)
        contentwidth = html.VirtualSize[0]
        for k, v in links.items() if links and autowidth_links is not False else ():
            v = v(k) if callable(v) and autowidth_links else v
            if isinstance(v, text_type):
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
        ColourManager.Patch(self)


    def OnLink(self, event):
        """Handler for clicking a link, sets new content if registered link else opens webbrowser."""
        href = event.GetLinkInfo().Href
        if href in self.links:
            page = self.links[href]
            if callable(page): page = page(href)
            if isinstance(page, text_type):
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
        return self._formatter
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



def get_all_children(ctrl, keep=(), skip=()):
    """
    Returns a list of all nested children of given wx component.

    @param   keep  specific classes to return if not all
    @param   skip  specific classes to skip processing
    """
    result, stack = [], [ctrl]
    while stack:
        ctrl = stack.pop(0)
        for child in ctrl.GetChildren() if hasattr(ctrl, "GetChildren") else []:
            if skip and isinstance(child, skip): continue # for child
            if not keep or isinstance(child, keep): result.append(child)
            stack.append(child)
    return result


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
