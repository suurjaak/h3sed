# -*- coding: utf-8 -*-
"""
Subplugin for HOMM3 version "Heroes Chronicles".

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   13.09.2024
@modified  02.04.2025
------------------------------------------------------------------------------
"""
import re

from .. import metadata

NAME  = "hc"
TITLE = "Heroes Chronicles"

SAVEFILE_MAGIC = b"HCHRONSVG"


def adapt(name, value):
    """
    Adapts certain categories:

    - "savefile_magic_regex":   adds support for Chronicles savefiles
    - "savefile_header_regex":  adds support for Chronicles savefiles
    """
    result = value
    if "savefile_magic_regex" == name:
        if hasattr(value, "pattern") and SAVEFILE_MAGIC not in value.pattern:
            result = re.compile(value.pattern + b"|^%s" % SAVEFILE_MAGIC)
    elif "savefile_header_regex" == name:
        if hasattr(value, "pattern") and SAVEFILE_MAGIC not in value.pattern:
            DEFAULT_MAGIC = metadata.Savefile.RGX_MAGIC.pattern.replace(b"^", b"")
            if DEFAULT_MAGIC in value.pattern:
                repl = b"(%s|%s)" % (DEFAULT_MAGIC, SAVEFILE_MAGIC)
                pattern = value.pattern.replace(DEFAULT_MAGIC, repl, 1)
                result = re.compile(pattern, value.flags)
    return result


def detect(savefile):
    """Returns whether savefile bytes match Heroes Chronicles."""
    return savefile.raw.startswith(SAVEFILE_MAGIC)
