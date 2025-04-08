# -*- coding: utf-8 -*-
"""
Main program entrance: launches GUI or CLI application.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     14.03.2020
@modified    08.04.2025
------------------------------------------------------------------------------
"""
import argparse
import datetime
import glob
import locale
import logging
import os
import sys
import tempfile
import threading
import traceback

try:
    import wx
    is_gui_possible = True
except ImportError:
    is_gui_possible, wx = False, None
import yaml

import h3sed
from . lib import util
from . import conf
if is_gui_possible:
    from . import guibase
    from . import gui

logger = logging.getLogger(__package__)


ARGUMENTS = {
    "description": "%s - %s." % (conf.Name, conf.Title),
    "arguments": [
        {"args": ["-v", "--version"], "action": "version",
         "version": "%s %s, %s." % (conf.Title, conf.Version, conf.VersionDate)},
    ],
    "commands": [
        {"name": "gui",
         "help": "launch %s graphical program (default option)" % conf.Name,
         "description": "Launch %s graphical program (default option)." % conf.Name,
         "arguments": [
             {"args": ["FILE"], "metavar": "SAVEGAME", "nargs": "*",
              "help": "Heroes3 savegames(s) to open on startup, if any (supports * wildcards)"},
        ]},
        {"name": "info",
         "help": "print information on savegame",
         "description": "Print information on given savegame(s).",
         "arguments": [
             {"args": ["FILE"], "metavar": "SAVEGAME", "nargs": "+",
              "help": "Heroes3 savegame(s) to read (supports * wildcards)"},
        ]},
        {"name": "export",
         "help": "export heroes from savegame",
         "description": "Export heroes from savegame as CSV, HTML, JSON or YAML.",
         "arguments": [
             {"args": ["FILE"], "metavar": "SAVEGAME", "nargs": "+",
              "help": "Heroes3 savegame(s) to read (supports * wildcards)"},
             {"args": ["-f", "--format"], "dest": "format", "default": "yaml",
              "choices": ["csv", "html", "json", "yaml"], "type": str.lower,
              "help": 'output format (defaults to yaml)'},
             {"args": ["-o", "--output"], "dest": "OUTFILE", "metavar": "OUTFILE",
                       "nargs": "?", "const": "",
              "help": "write output to file instead of printing to console;\n"
                      "filename will be auto-generated if not given;\n"
                      "automatic for non-printable formats (csv, html)"},
        ]},
    ],
}


class MainApp(wx.App if wx else object):

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


def run_info(filenames):
    """Parses given files and prints metadata."""
    for filename in filenames:
        if not os.path.isfile(filename):
            print("\nFile not found: %s" % filename)
            continue # for filename

        try: savefile = h3sed.metadata.Savefile(filename, parse_heroes=False)
        except Exception as e:
            print("\nError reading %s: %s" % (filename, e))
            continue # for filename

        savefile.populate_heroes()
        content = yaml.safe_dump(h3sed.templates.make_savefile_data(savefile), sort_keys=False)
        print()
        print(content)


def run_export(filenames, format, outname):
    """Parses given files and prints or writes output files with hero data."""
    format = format.lower()
    is_printable = format not in ("csv", "html")
    for filename in filenames:
        if not os.path.isfile(filename):
            print("\nFile not found: %s" % filename)
            continue # for filename

        try: savefile = h3sed.metadata.Savefile(filename)
        except Exception as e:
            print("\nError reading %s: %s" % (filename, e))
            continue # for filename

        if outname is None and is_printable:
            with tempfile.NamedTemporaryFile() as f:
                outfile = f.name
        elif not outname:
            now = datetime.datetime.now()
            outfile = ".".join([os.path.basename(filename), now.strftime("%Y%m%d_%H%M%S"), format])
            outfile = util.unique_path(outfile, suffix="_%(counter)s%(ext)s")
        else: outfile = util.unique_path(outname, suffix="_%(counter)s%(ext)s")
        h3sed.templates.export_heroes(outfile, format, savefile.heroes, savefile)

        if is_printable and outname is None:
            with open(outfile) as f: print(f.read())
            try: os.remove(outfile)
            except Exception: pass
        else:
            print()
            print("Wrote %s of %s bytes." % (outfile, os.path.getsize(outfile)))


def run_gui(filenames):
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
    for filename in filenames:
        if os.path.isfile(filename):
            wx.CallAfter(wx.PostEvent, window, gui.OpenSavefileEvent(-1, filename=filename))
    app.MainLoop()


def run():
    """Parses command-line arguments and runs application GUI or CLI."""
    conf.load()
    argparser = argparse.ArgumentParser(description=ARGUMENTS["description"], prog=conf.Name)
    for arg in map(dict, ARGUMENTS["arguments"]):
        argparser.add_argument(*arg.pop("args"), **arg)
    subparsers = argparser.add_subparsers(dest="command")
    for cmd in ARGUMENTS["commands"]:
        kwargs = dict((k, cmd[k]) for k in ["help", "description"] if k in cmd)
        kwargs.update(formatter_class=argparse.RawTextHelpFormatter)
        subparser = subparsers.add_parser(cmd["name"], **kwargs)
        for arg in map(dict, cmd["arguments"]):
            subparser.add_argument(*arg.pop("args"), **arg)

    argv = sys.argv[1:]
    if "nt" == os.name: # Fix Unicode arguments, otherwise converted to ?
        argv = util.win32_unicode_argv()[1:]

    rootflags = tuple(subparsers.choices) + ("-h", "--help", "-v", "--version")
    if not argv or not any(x in argv for x in rootflags):
        argv[:0] = ["gui"] # argparse hack: force default argument
    if len(argv) > 1 and ("-h" in argv or "--help" in argv) and argv[-1] not in ("-h", "--help"):
        argv = [x for x in argv if x not in ("-h", "--help")] + ["-h"] # "-h option" to "option -h"

    arguments = argparser.parse_args(argv)

    if arguments.FILE:
        filearg = sorted(set(util.to_unicode(f) for f in util.tuplefy(arguments.FILE)))
        filearg = sum([sorted(glob.glob(f)) if "*" in f else [f] for f in filearg], [])
        filearg = list(map(util.longpath, filearg))
        arguments.FILE = filearg

    if "gui" == arguments.command and not is_gui_possible:
        argparser.print_help()
        sys.exit("\n\nwxPython not found. %s graphical program will not run." % conf.Name)

    if "gui" == arguments.command:
        run_gui(arguments.FILE)
    elif "info" == arguments.command:
        run_info(arguments.FILE)
    elif "export" == arguments.command:
        run_export(arguments.FILE, arguments.format, arguments.OUTFILE)


if "__main__" == __name__:
    run()
