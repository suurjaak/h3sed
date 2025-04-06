# -*- coding: utf-8 -*-
"""
Interface to game version differences.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   22.03.2020
@modified  06.04.2025
------------------------------------------------------------------------------
"""
import collections

from . import ab
from . import hc
from . import hota
from . import roe
from . import roe_gog
from . import sod


## Modules for game versions in order of release
VERSIONS = collections.OrderedDict([
    ("roe",     roe),     # Restoration of Erathia
    ("ab",      ab),      # Armageddon's Blade
    ("sod",     sod),     # Shadow of Death
    ("hc",      hc),      # Heroes Chronicles
    ("hota",    hota),    # Horn of The Abyss
    ("roe_gog", roe_gog), # Restoration of Erathia (GOG Complete)
])

ADAPT_CACHE = {} # {(name, value, version): value}


def adapt(name, value, version=None):
    """
    Returns value adapted either for specified game version, or run through all versions.

    @param   name     value name like "hero.regex"
    @param   value    the value to adapt
    @param   version  specific game version to adapt for, if any, like "sod" for Shadow of Death
    """
    cachekey = (name, value, version)
    try:
        if cachekey in ADAPT_CACHE: return ADAPT_CACHE[cachekey]
    except Exception: pass # TypeError if value in cachekey is not hashable

    if version:
        if hasattr(VERSIONS[version], "adapt"):
            value = VERSIONS[version].adapt(name, value)
    else:
        for module in VERSIONS.values():
            if hasattr(module, "adapt"):
                value = module.adapt(name, value)
    try: ADAPT_CACHE[cachekey] = value
    except Exception: pass # TypeError if value in cachekey is not hashable
    return value


def detect(savefile):
    """Returns savefile game version, like "sod" for Shadow of Death. Raises if unknown."""
    for version, module in VERSIONS.items():
        if module.detect(savefile):
            return version
    raise ValueError("Not recognized as Heroes3 savefile of any supported game version.")


def init():
    """Initializes version data."""
    for module in VERSIONS.values():
        if hasattr(module, "init"): module.init()


def title(version):
    """Returns version title, like "Shadow of Death" for "sod"."""
    return VERSIONS[version].TITLE
