# -*- coding: utf-8 -*-
"""
GUI frame template:
- auto-accelerated control shortcuts, "&OK" will turn Alt-O into shortcut
- Python console window, initially hidden,
  with auto-saved command history kept in conf.ConsoleHistoryCommands
- wx widget inspector window, initially hidden
- option for log panel, handles logging messages via wx events

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     14.03.2020
@modified    20.08.2025
------------------------------------------------------------------------------
"""
import datetime
import logging
import os
import re
import traceback

import wx
import wx.lib.inspection
import wx.lib.newevent
import wx.py

from . lib.controls import ColourManager, NewId
from . lib import util, wx_accel
from . import conf

logger = logging.getLogger(__name__)


def status(text, *args, **kwargs):
    """
    Sets main window status text, optionally logs the message.

    @param   args   string format arguments, if any, to substitute in text
    @param   flash  whether to clear the status after timeout,
                    by default after conf.StatusFlashLength if not given seconds
    @param   log    whether to log the message to main window
    """
    window = wx.GetApp() and wx.GetApp().GetTopWindow()
    if not window: return

    try: msg = text % args if args else text
    except UnicodeError:
        args = tuple(map(util.to_unicode, args))
        msg = text % args if args else text
    msg = re.sub("[\n\r\t]+", " ", msg)
    log, flash = (kwargs.get(x) for x in ("log", "flash"))
    if log: logger.info(msg)
    window.set_status(msg, timeout=flash)



class GUILogHandler(logging.Handler):
    """Logging handler that forwards logging messages to GUI log window."""

    def __init__(self):
        self.deferred = [] # Messages logged before main window available
        super(GUILogHandler, self).__init__()


    def emit(self, record):
        """Adds message to GUI log window, or postpones if window unavailable."""
        now = datetime.datetime.now()
        text = record.msg if isinstance(record.msg, util.text_types) else str(record.msg)
        try: text = text % record.args if record.args else text
        except UnicodeError:
            try: text = text % tuple(map(util.to_unicode, record.args))
            except Exception: pass
        if record.exc_info:
            text += "\n\n" + "".join(traceback.format_exception(*record.exc_info))
        if "\n" in text:
            text = text.replace("\n", "\n\t\t") # Indent linebreaks
            text = re.sub(r"^\s+$", "", text, flags=re.M) # Unindent whitespace-only lines
        msg = "%s.%03d\t%s" % (now.strftime("%H:%M:%S"), now.microsecond // 1000, text)

        window = wx.GetApp() and wx.GetApp().GetTopWindow()
        if window:
            msgs = self.deferred + [msg]
            for m in msgs: wx.CallAfter(window.log_message, m)
            del self.deferred[:]
        else: self.deferred.append(msg)



class TemplateFrameMixIn(wx_accel.AutoAcceleratorMixIn):
    """Application main window."""

    def __init__(self):
        wx_accel.AutoAcceleratorMixIn.__init__(self)

        self.Bind(wx.EVT_CLOSE, self.on_exit)

        self.console_commands = set() # Commands from run_console()
        self.frame_console = wx.py.shell.ShellFrame(parent=self,
            title=u"%s Console" % conf.Title, size=conf.ConsoleSize)
        self.frame_console.Bind(wx.EVT_CLOSE, self.on_toggle_console)
        self.frame_console_shown = False # Init flag
        console = self.console = self.frame_console.shell
        if not isinstance(conf.ConsoleHistoryCommands, list):
            conf.ConsoleHistoryCommands = []
        for cmd in conf.ConsoleHistoryCommands:
            console.addHistory(cmd)
        console.Bind(wx.EVT_KEY_DOWN, self.on_keydown_console)
        self.widget_inspector = wx.lib.inspection.InspectionTool()

        self.CreateStatusBar()


    def create_log_panel(self, parent):
        """Creates and returns the log output panel."""
        panel = wx.Panel(parent)
        sizer = panel.Sizer = wx.BoxSizer(wx.VERTICAL)
        ColourManager.Manage(panel, "BackgroundColour", wx.SYS_COLOUR_BTNFACE)

        button_clear = wx.Button(parent=panel, label="C&lear log", size=(100, -1))
        button_clear.Bind(wx.EVT_BUTTON, lambda event: self.log.Clear())
        edit_log = self.log = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
        edit_log.SetEditable(False)
        # Read-only controls tend to be made grey by default
        ColourManager.Manage(edit_log, "ForegroundColour", wx.SYS_COLOUR_GRAYTEXT)
        ColourManager.Manage(edit_log, "BackgroundColour", wx.SYS_COLOUR_WINDOW)

        sizer.Add(button_clear, border=5, flag=wx.ALIGN_RIGHT | wx.TOP |
                  wx.RIGHT)
        sizer.Add(edit_log, border=5, proportion=1, flag=wx.GROW | wx.ALL)
        return panel


    def create_menu(self):
        """Creates the program menu."""
        menu = wx.MenuBar()
        menu_file = wx.Menu()
        menu.Insert(0, menu_file, "&File")
        menu_recent = self.menu_recent = wx.Menu()
        menu_file.AppendMenu(id=NewId(), text="&Recent files",
            submenu=menu_recent, help="Recently opened files.")
        menu_file.AppendSeparator()
        menu_console = self.menu_console = menu_file.Append(
            id=NewId(), kind=wx.ITEM_CHECK, text="Show &console\tCtrl-E",
            help="Show/hide a Python shell environment window")
        menu_inspect = self.menu_inspect = menu_file.Append(
            id=NewId(), kind=wx.ITEM_CHECK, text="Show &widget inspector",
            help="Show/hide the widget inspector")

        self.file_history = wx.FileHistory(conf.MaxRecentFiles)
        self.file_history.UseMenu(menu_recent)
        for f in conf.RecentFiles[::-1]: # Backwards - FileHistory is a stack
            os.path.exists(f) and self.file_history.AddFileToHistory(f)
        wx.EVT_MENU_RANGE(self, wx.ID_FILE1, wx.ID_FILE9, self.on_recent_file)
        menu_file.AppendSeparator()
        m_exit = menu_file.Append(-1, "E&xit\tAlt-X", "Exit")

        self.Bind(wx.EVT_MENU, self.on_toggle_console, menu_console)
        self.Bind(wx.EVT_MENU, self.on_open_widget_inspector, menu_inspect)
        self.Bind(wx.EVT_MENU, self.on_exit, m_exit)
        self.SetMenuBar(menu)


    def on_exit(self, event):
        """Handler on application exit, saves configuration."""
        conf.save()
        self.Destroy()


    def on_keydown_console(self, event):
        """Handler for keydown in console, saves entered command in history."""
        event.Skip()
        if (event.KeyCode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER)
        and not event.ShiftDown() and self.console.history):
            # Defer saving until command is inserted into console history
            wx.CallAfter(self.save_last_command)


    def run_console(self, command):
        """
        Runs the command in the Python console. Will not be saved to console
        commands history.
        """
        self.console.run(command)
        self.console_commands.add(command)


    def save_last_command(self):
        """
        Saves the last console command in conf, minus the commands given via
        run_console().
        """
        h = [x for x in self.console.history if x not in self.console_commands]
        history = h[:conf.MaxConsoleHistory][::-1]
        if history != conf.ConsoleHistoryCommands:
            conf.ConsoleHistoryCommands[:] = history
            conf.save()


    def set_status(self, text, timeout=False):
        """Sets main window status bar text, optionally clears after timeout."""
        self.SetStatusText(text)
        if not timeout or not text: return

        if timeout is True: timeout = conf.StatusFlashLength
        clear = lambda sb: sb and sb.StatusText == text and self.SetStatusText("")
        wx.CallLater(timeout * 1000, clear, self.StatusBar)


    def log_message(self, text):
        """Adds a message to the log control."""
        if not hasattr(self, "log") \
        or hasattr(conf, "LogEnabled") and not conf.LogEnabled: return

        try: self.log.AppendText(text + "\n")
        except Exception:
            try: self.log.AppendText(text.decode("utf-8", "replace") + "\n")
            except Exception as e: print("Exception %s: %s in log_message" %
                                         (e.__class__.__name__, e))


    def on_toggle_console(self, *_):
        """Toggles the console shown/hidden."""
        show = not self.frame_console.IsShown()
        if show and not self.frame_console_shown:
            # First showing of console, set height to a fraction of main
            # form, and position it immediately under the main form, or
            # covering its bottom if no room.
            self.frame_console_shown = True
            size = wx.Size(self.Size.width, max(200, self.Size.height // 3))
            self.frame_console.Size = size
            display = wx.GetDisplaySize()
            y = 0
            min_bottom_space = 130 # Leave space for autocomplete dropdown
            if size.height > display.height - self.Size.height \
            - self.Position.y - min_bottom_space:
                y = display.height - self.Size.height - self.Position.y \
                    - size.height - min_bottom_space
            self.frame_console.Position = (
                self.Position.x, self.Position.y + self.Size.height + y
            )
        if show: self.console.ScrollToLine(self.console.LineCount + 3 - (
            self.console.Size.height // self.console.GetTextExtent(" ")[1]
        )) # Scroll to the last line
        self.frame_console.Show(show)
        if hasattr(self, "menu_console"): self.menu_console.Check(show)


    def on_open_widget_inspector(self, *_):
        """Toggles the widget inspection tool shown/hidden."""
        visible = not (self.widget_inspector.initialized
                       and self.widget_inspector._frame)
        if visible:
            self.widget_inspector.Init()
            self.widget_inspector.Show(selectObj=self, refreshTree=True)
            self.widget_inspector._frame.Bind(wx.EVT_CLOSE, lambda e: e.Skip())
        else:
            self.widget_inspector._frame.Close()
        if hasattr(self, "menu_inspect"):
            self.menu_inspect.Check(visible)


    def on_recent_file(self, event):
        """Handler for clicking an entry in Recent Files menu."""
        filename = self.file_history.GetHistoryFile(event.GetId() - wx.ID_FILE1)
        self.open_file(filename)
