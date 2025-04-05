# -*- coding: utf-8 -*-
"""
Main program entrance: launches GUI application,
handles logging and status calls.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     14.03.2020
@modified    03.04.2025
------------------------------------------------------------------------------
"""
import argparse
import locale
import logging
import os
import sys
import threading
import traceback

import wx

from . lib import util
from . import conf
from . import guibase
from . import gui

logger = logging.getLogger(__package__)


ARGUMENTS = {
    "description": conf.Title,
    "arguments": [
        {"args": ["-v", "--version"], "action": "version",
         "version": "%s %s, %s." % (conf.Title, conf.Version, conf.VersionDate)},
        {"args": ["FILE"], "nargs": "?",
         "help": "Savegame to open on startup, if any"},
    ],
}


class MainApp(wx.App):

    def InitLocale(self):
        self.ResetLocale()
        if "win32" == sys.platform:  # Avoid dialog buttons in native language
            mylocale = wx.Locale(wx.LANGUAGE_ENGLISH_US, wx.LOCALE_LOAD_DEFAULT)
            mylocale.AddCatalog("wxstd")
            self._initial_locale = mylocale  # Override wx.App._initial_locale
            # Workaround for MSW giving locale as "en-US"; standard format is "en_US".
            # Py3 provides "en[-_]US" in wx.Locale names and accepts "en" in locale.setlocale();
            # Py2 provides "English_United States.1252" in wx.Locale.SysName and accepts only that.
            name = mylocale.SysName if sys.version_info < (3, ) else mylocale.Name.split("_", 1)[0]
            try: locale.setlocale(locale.LC_ALL, name)
            except Exception:
                logger.warning("Failed to set locale %r.", name, exc_info=True)
                try: locale.setlocale(locale.LC_ALL, "")
                except Exception: logger.warning("Failed to set locale ''.", exc_info=True)



def except_hook(etype, evalue, etrace):
    """Handler for all unhandled exceptions."""
    text = "".join(traceback.format_exception(etype, evalue, etrace)).strip()
    log = "An unexpected error has occurred:\n\n%s"
    logger.error(log, text)
    if not conf.PopupUnexpectedErrors: return
    msg = "An unexpected error has occurred:\n\n%s\n\n" \
          "See log for full details." % util.format_exc(evalue)
    wx.CallAfter(wx.MessageBox, msg, conf.Title, wx.OK | wx.ICON_ERROR)


def install_thread_excepthook():
    """
    Workaround for sys.excepthook not catching threading exceptions.

    @from   https://bugs.python.org/issue1230540
    """
    init_old = threading.Thread.__init__
    def init(self, *args, **kwargs):
        init_old(self, *args, **kwargs)
        run_old = self.run
        def run_with_except_hook(*a, **b):
            try: run_old(*a, **b)
            except Exception: sys.excepthook(*sys.exc_info())
        self.run = run_with_except_hook
    threading.Thread.__init__ = init


def run_gui(filename):
    """Main GUI program entrance."""
    global logger

    # Set up logging to GUI log window
    logger.addHandler(guibase.GUILogHandler())
    logger.setLevel(logging.DEBUG)

    install_thread_excepthook()
    sys.excepthook = except_hook

    # Create application main window
    app = MainApp(redirect=True) # stdout and stderr redirected to wx popup
    window = gui.MainWindow()
    app.SetTopWindow(window) # stdout/stderr popup closes with MainWindow

    # Some debugging support
    window.run_console("import datetime, math, os, re, time, sys, wx")
    window.run_console("# All %s standard modules:" % conf.Title)
    window.run_console("import h3sed")
    window.run_console("from h3sed import conf, guibase, gui, hero, images, "
                       "main, metadata, templates, version")
    window.run_console("from h3sed.lib import controls, util, wx_accel")

    window.run_console("")
    window.run_console("self = wx.GetApp().TopWindow # Application main window")
    if filename and os.path.isfile(filename):
        wx.CallAfter(wx.PostEvent, window, gui.OpenSavefileEvent(-1, filename=filename))
    app.MainLoop()



def run():
    """Parses command-line arguments and runs GUI."""
    conf.load()
    argparser = argparse.ArgumentParser(description=ARGUMENTS["description"], prog=conf.Name)
    for arg in ARGUMENTS["arguments"]:
        argparser.add_argument(*arg.pop("args"), **arg)

    argv = sys.argv[1:]
    if "nt" == os.name: # Fix Unicode arguments, otherwise converted to ?
        argv = util.win32_unicode_argv()[1:]
    arguments, _ = argparser.parse_known_args(argv)

    if arguments.FILE: arguments.FILE = util.longpath(arguments.FILE)

    run_gui(arguments.FILE)


if "__main__" == __name__:
    run()
