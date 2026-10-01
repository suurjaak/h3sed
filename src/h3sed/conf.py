# -*- coding: utf-8 -*-
"""
Application settings, and functionality to save/load some of them from
an external file. Configuration file has simple INI file format,
and all values are kept in JSON.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   14.03.2020
@modified  01.10.2026
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
Version = "3.9.dev18"
VersionDate = "01.10.2026"

Frozen = getattr(sys, "frozen", False)
if Frozen:
    # Running as a pyinstaller executable
    ApplicationDirectory = os.path.dirname(sys.executable)
    FunctionDirectory = os.path.join(getattr(sys, "_MEIPASS", ""), "functions")
    ResourceDirectory = os.path.join(getattr(sys, "_MEIPASS", ""), "res")
    TranslationDirectory = os.path.join(getattr(sys, "_MEIPASS", ""), "i18n")
    EtcDirectory = ApplicationDirectory
else:
    ApplicationDirectory = os.path.realpath(os.path.dirname(__file__))
    FunctionDirectory = os.path.join(ApplicationDirectory, "functions")
    ResourceDirectory = os.path.join(ApplicationDirectory, "res")
    TranslationDirectory = os.path.join(ApplicationDirectory, "etc", "i18n")
    EtcDirectory = os.path.join(ApplicationDirectory, "etc")

"""Name of file where FileDirectives are kept."""
ConfigFile = "%s.ini" % os.path.join(EtcDirectory, Name.lower())

"""List of attribute names that can be saved to and loaded from ConfigFile."""
FileDirectives = [
    "Backup", "ConfirmUnsaved", "ConsoleHistoryCommands", "RecentFiles", "RecentHeroes",
    "SelectedPath", "UpdateCheckAutomatic", "UpdateCheckLast", "WindowPosition", "WindowSize",
]
"""List of user-modifiable attributes, saved if changed from default."""
OptionalFileDirectives = [
    "DarkTheme", "FileExtensions", "Language", "MaxConsoleHistory", "MaxRecentFiles",
    "PopupUnexpectedErrors", "SavegameNewFormat", "Settings", "StatusFlashLength",
    "Translations", "UpdateCheckInterval", "UserFunctions",
]
Defaults = {}

"""---------------------------- FileDirectives: ----------------------------"""

"""Current selected path in directory list."""
SelectedPath = None

"""Create a backup of savegame file before saving edits."""
Backup = True

"""Confirm on closing files with unsaved changes."""
ConfirmUnsaved = True

"""Whether to apply dark mode colours, None for autodetect from system."""
DarkTheme = None

"""Savefile filename extensions, as {'description': ('.ext1', '.ext2')}."""
FileExtensions = [("Heroes3 savefiles",               (".cgm", ".gm1", ".gm2", ".gm3", ".gm4", ".gm5", ".gm6", ".gm7", ".gm8")),
                  ("Heroes3 single player savefiles", (".gm1", )),
                  ("Heroes3 multi-player savefiles",  (".gm2", ".gm3", ".gm4", ".gm5", ".gm6", ".gm7", ".gm8")),
                  ("Heroes3 campaign savefiles",      (".cgm", ))]

"""History of commands entered in console."""
ConsoleHistoryCommands = []

"""Current application language."""
Language = "en"

"""Various UI selection states."""
Settings = {"savefile.filter_index": 0, "savepage.page_index": 0, "savepage.splitter_pos": 36,
            "hero.manifest_view": "normal", "town.manifest_view": "normal",
            "hero.sort_col": "index", "hero.sort_asc": True, "hero.tab_index": 0,
            "hero.sort_col": "index", "hero.sort_asc": True, "town.tab_index": 0}

"""Contents of Recent Files menu."""
RecentFiles = []

"""Contents of Recent Heroes menu, as [[hero name, file path, ?name counter if duplicate name]]."""
RecentHeroes = []

"""Whether to assume new savegame format when ambiguous e.g. updated Armageddon's Blade."""
SavegameNewFormat = True

"""Additional internationalization languages, as {language code: {"name", "path"}}."""
Translations = {}

"""Whether the program checks for updates every UpdateCheckInterval."""
UpdateCheckAutomatic = True

"""Days between automatic update checks."""
UpdateCheckInterval = 7

"""Date string of last time updates were checked."""
UpdateCheckLast = None

"""User-defined plugins, as [{title, ?body, ?name, ?active, ?__builtin__}]."""
UserFunctions = []

"""Main window position, (x, y)."""
WindowPosition = None

"""Main window size in pixels, [w, h] or [-1, -1] for maximized."""
WindowSize = (700, 820)

"""---------------------------- /FileDirectives ----------------------------"""

"""Whether logging to log window is enabled."""
LogEnabled = True

"""Whether to pop up message dialogs for unhandled errors."""
PopupUnexpectedErrors = True

"""Currently opened savefiles, as {filename, }."""
FilesOpen = set()

"""URLs for download list and homepage."""
DownloadURL = "https://erki.lap.ee/downloads/h3sed/"
HomeUrl     = "https://suurjaak.github.io/h3sed"

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

    # Added in v3.9 to migrate Positions and HeroToggles to Settings. TO BE DONE: remove next year.
    ADAPT_SETTINGS = {"Positions": {"filefilter_index": "savefile.filter_index",
                                    "hero_sort_col": "hero.sort_col",
                                    "hero_sort_asc": "hero.sort_asc",
                                    "herotab_index": "hero.tab_index",
                                    "charsheet_view": "hero.charsheet_view",
                                    "savepage_splitter": "savepage.splitter_pos"},
                      "HeroToggles": {None: "hero.toggle_%s"}}

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
        for name in ADAPT_SETTINGS:
            value, ok = parse_value(name)
            if not ok or not isinstance(value, dict): continue # for name
            for key1, key2 in ADAPT_SETTINGS[name].items():
                if None == key1:
                    Settings.update({key2 % k: v for k, v in value.items()})
                elif key1 in value:
                    Settings[key2] = value[key1]
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
        f.write("# %s configuration written on %s.\n" %
                (Title, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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
