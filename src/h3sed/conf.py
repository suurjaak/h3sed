# -*- coding: utf-8 -*-
"""
Application settings, and functionality to save/load some of them from
an external file. Configuration file has simple INI file format,
and all values are kept in JSON.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     14.03.2020
@modified    11.06.2024
------------------------------------------------------------------------------
"""
try: from ConfigParser import RawConfigParser                 # Py2
except ImportError: from configparser import RawConfigParser  # Py3
import copy
import datetime
import io
import json
import os
import re
import sys


"""Program title, version number and version date."""
Name = "h3sed"
Title = "Heroes3 Savegame Editor"
Version = "2.3"
VersionDate = "11.06.2024"

Frozen = getattr(sys, "frozen", False)
if Frozen:
    # Running as a pyinstaller executable
    ApplicationDirectory = os.path.dirname(sys.executable)
    PluginDirectory = os.path.join(getattr(sys, "_MEIPASS", ""), "h3sed", "plugins")
    ResourceDirectory = os.path.join(getattr(sys, "_MEIPASS", ""), "res")
    EtcDirectory = ApplicationDirectory
else:
    ApplicationDirectory = os.path.realpath(os.path.dirname(__file__))
    PluginDirectory = os.path.join(ApplicationDirectory, "plugins")
    ResourceDirectory = os.path.join(ApplicationDirectory, "res")
    EtcDirectory = os.path.join(ApplicationDirectory, "etc")

"""Name of file where FileDirectives are kept."""
ConfigFile = "%s.ini" % os.path.join(EtcDirectory, Name.lower())

"""List of attribute names that can be saved to and loaded from ConfigFile."""
FileDirectives = [
    "Backup", "ConfirmUnsaved", "ConsoleHistoryCommands", "RecentFiles", "RecentHeroes",
    "SelectedPath", "WindowPosition", "WindowSize",
]
"""List of user-modifiable attributes, saved if changed from default."""
OptionalFileDirectives = [
    "FileExtensions", "HeroToggles", "MaxConsoleHistory", "MaxRecentFiles",
    "PopupUnexpectedErrors", "Positions", "StatusFlashLength",
]
Defaults = {}

"""---------------------------- FileDirectives: ----------------------------"""

"""Current selected path in directory list."""
SelectedPath = None

"""Create a backup of savegame file before saving edits."""
Backup = True

"""Confirm on closing files with unsaved changes."""
ConfirmUnsaved = True

"""Savefile filename extensions, as {'description': ('.ext1', '.ext2')}."""
FileExtensions = [("Heroes3 savefiles",               (".cgm", ".gm1", ".gm2", ".gm3", ".gm4", ".gm5", ".gm6", ".gm7", ".gm8")),
                  ("Heroes3 single player savefiles", (".gm1", )),
                  ("Heroes3 multi-player savefiles",  (".gm2", ".gm3", ".gm4", ".gm5", ".gm6", ".gm7", ".gm8")),
                  ("Heroes3 campaign savefiles",      (".cgm", ))]

"""History of commands entered in console."""
ConsoleHistoryCommands = []

"""Hero index categories toggle state, as {name: false}."""
HeroToggles = {}

"""Various index and location selection states."""
Positions = {"filefilter_index": 0, "herotab_index": 0, "charsheet_view": "normal",
             "savepage_splitter": 36}

"""Contents of Recent Files menu."""
RecentFiles = []

"""Contents of Recent Heroes menu, as [[hero name, file path]]."""
RecentHeroes = []

"""Main window position, (x, y)."""
WindowPosition = None

"""Main window size in pixels, [w, h] or [-1, -1] for maximized."""
WindowSize = (650, 700)

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
MaxTabTitleLength = 30

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

"""Colour for original value in savegame diff."""
DiffOldColour = "#FFAAAA"

"""Colour for new value in savegame diff."""
DiffNewColour = "#AAFFAA"

"""Default duration of "flashed" status message on StatusBar, in seconds."""
StatusFlashLength = 20

"""Short duration of "flashed" status message on StatusBar, in seconds."""
StatusShortFlashLength = 5

"""How many items in the Recent Files menu."""
MaxRecentFiles = 20

"""How many items in the Recent Heroes menu."""
MaxRecentHeroes = 20

"""Path for licences of bundled open-source software."""
LicenseFile = os.path.join(ResourceDirectory, "3rd-party licenses.txt") if Frozen else None


def load():
    """Loads FileDirectives from ConfigFile into this module's attributes."""
    global Defaults

    try: VARTYPES = (basestring, bool, int, long, list, tuple, dict, type(None))         # Py2
    except Exception: VARTYPES = (bytes, str, bool, int, list, tuple, dict, type(None))  # Py3

    def safecopy(v):
        """Tries to return a deep copy, or a shallow copy, or given value if copy fails."""
        for f in (copy.deepcopy, copy.copy, lambda x: x):
            try: return f(v)
            except Exception: pass

    section = "*"
    module = sys.modules[__name__]
    Defaults = {k: safecopy(v) for k, v in vars(module).items()
                if not k.startswith("_") and isinstance(v, VARTYPES)}

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
        reader = getattr(parser, "read_file", getattr(parser, "readfp", None))  # Py3/Py2
        reader(io.StringIO(txt), ConfigFile)

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
