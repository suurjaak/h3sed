# -*- coding: utf-8 -*-
"""
Application settings, and functionality to save/load some of them from
an external file. Configuration file has simple INI file format,
and all values are kept in JSON.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     14.03.2020
@modified    19.01.2022
------------------------------------------------------------------------------
"""
try: from ConfigParser import RawConfigParser                 # Py2
except ImportError: from configparser import RawConfigParser  # Py3
import datetime
import io
import json
import os
import re
import sys


"""Program title, version number and version date."""
Name = "h3sed"
Title = "Heroes3 Savegame Editor"
Version = "1.0"
VersionDate = "19.01.2022"

if getattr(sys, "frozen", False):
    # Running as a pyinstaller executable
    ApplicationDirectory = os.path.dirname(sys.executable)
    PluginDirectory = os.path.join(getattr(sys, "_MEIPASS", ""), "h3sed", "plugins")
    EtcDirectory = ApplicationDirectory
else:
    ApplicationDirectory = os.path.realpath(os.path.dirname(__file__))
    PluginDirectory = os.path.join(ApplicationDirectory, "plugins")
    EtcDirectory = os.path.join(ApplicationDirectory, "etc")

"""Name of file where FileDirectives are kept."""
ConfigFile = "%s.ini" % os.path.join(EtcDirectory, Name.lower())

"""List of attribute names that can be saved to and loaded from ConfigFile."""
FileDirectives = [
    "Backup", "ConfirmUnsaved", "ConsoleHistoryCommands", "GameVersion",
    "Populate", "RecentFiles", "SelectedPath", "WindowPosition", "WindowSize",
]
"""List of user-modifiable attributes, saved if changed from default."""
OptionalFileDirectives = [
    "FileExtensions", "MaxConsoleHistory", "MaxRecentFiles",
    "PopupUnexpectedErrors", "StatusFlashLength",
]
Defaults = {}

"""---------------------------- FileDirectives: ----------------------------"""

"""Current selected path in directory list."""
SelectedPath = None

"""Create a backup of savegame file before saving edits."""
Backup = True

"""Confirm on closing files with unsaved changes."""
ConfirmUnsaved = True

"""Load savefile content to UI upon opening."""
Populate = True

"""Savefile filename extensions, as {'description': ('.ext1', '.ext2')}."""
FileExtensions = [("Heroes3 savefiles",               (".cgm", ".gm1", ".gm2", ".gm3", ".gm4", ".gm5", ".gm6", ".gm7", ".gm8")),
                  ("Heroes3 single player savefiles", (".gm1", )),
                  ("Heroes3 multi-player savefiles",  (".gm2", ".gm3", ".gm4", ".gm5", ".gm6", ".gm7", ".gm8")),
                  ("Heroes3 campaign savefiles",      (".cgm", ))]

"""History of commands entered in console."""
ConsoleHistoryCommands = []

"""Default game version for savefiles."""
GameVersion = ""

"""Contents of Recent Files menu."""
RecentFiles = []

"""Main window position, (x, y)."""
WindowPosition = None

"""Main window size in pixels, [w, h] or [-1, -1] for maximized."""
WindowSize = (600, 700)

"""---------------------------- /FileDirectives ----------------------------"""

"""Whether logging to log window is enabled."""
LogEnabled = True

"""Whether to pop up message dialogs for unhandled errors."""
PopupUnexpectedErrors = True

"""Currently opened savefiles, as {filename, }."""
FilesOpen = set()

"""URL for homepage."""
HomeUrl = "https://suurjaak.github.io/h3sed"

"""Minimum allowed size for the main window, as (width, height)."""
MinWindowSize = (500, 400)

"""Console window size in pixels, (width, height)."""
ConsoleSize = (600, 300)

"""Maximum number of console history commands to store."""
MaxConsoleHistory = 1000

"""Maximum length of a tab title, overflow will be cut on the left."""
MaxTabTitleLength = 60

"""Name of font used in HTML content."""
HtmlFontName = "Tahoma"

"""Window background colour."""
BgColour = "#FFFFFF"

"""Text colour."""
FgColour = "#000000"

"""Main screen background colour."""
MainBgColour = "#FFFFFF"

"""Widget (button etc) background colour."""
WidgetColour = "#D4D0C8"

"""Colour for clickable links."""
LinkColour = "#0000FF"

"""Duration of "flashed" status message on StatusBar, in seconds."""
StatusFlashLength = 20

"""How many items in the Recent Files menu."""
MaxRecentFiles = 20


def load():
    """Loads FileDirectives from ConfigFile into this module's attributes."""
    global Defaults

    try: VARTYPES = (basestring, bool, int, long, list, tuple, dict, type(None))         # Py2
    except Exception: VARTYPES = (bytes, str, bool, int, list, tuple, dict, type(None))  # Py3

    section = "*"
    module = sys.modules[__name__]
    Defaults = {k: v for k, v in vars(module).items() if not k.startswith("_")
                and isinstance(v, VARTYPES)}

    parser = RawConfigParser()
    parser.optionxform = str # Force case-sensitivity on names
    try:
        def parse_value(name):
            try: # parser.get can throw an error if value not found
                value_raw = parser.get(section, name)
            except Exception:
                return None, False
            try: # Try to interpret as JSON, fall back on raw string
                value = json.loads(value_raw)
            except ValueError:
                value = value_raw
            return value, True

        with open(ConfigFile, "r") as f:
            txt = f.read()
        try: txt = txt.decode()
        except Exception: pass
        if not re.search("\\[\\w+\\]", txt): txt = "[DEFAULT]\n" + txt
        parser.readfp(io.StringIO(txt), ConfigFile)

        for name in FileDirectives:
            [setattr(module, name, v) for v, s in [parse_value(name)] if s]
        for name in OptionalFileDirectives:
            [setattr(module, name, v) for v, s in [parse_value(name)] if s]
    except Exception:
        pass # Fail silently


def save():
    """Saves FileDirectives into ConfigFile."""
    section = "*"
    module = sys.modules[__name__]
    parser = RawConfigParser()
    parser.optionxform = str # Force case-sensitivity on names
    parser.add_section(section)
    try:
        f = open(ConfigFile, "w")
        f.write("# %s %s configuration written on %s.\n" % (Title, Version,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        for name in FileDirectives:
            try: parser.set(section, name, json.dumps(getattr(module, name)))
            except Exception: pass
        for name in OptionalFileDirectives:
            try:
                value = getattr(module, name, None)
                if Defaults.get(name) != value:
                    parser.set(section, name, json.dumps(value))
            except Exception: pass
        parser.write(f)
        f.close()
    except Exception:
        pass # Fail silently
