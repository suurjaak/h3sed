# -*- coding: utf-8 -*-
"""
Subplugin for HOMM3 version "Heroes Chronicles".

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   13.09.2024
@modified  27.07.2025
------------------------------------------------------------------------------
"""
import re

from .. import hero
from .. import metadata
from .. hero import make_artifact_cast

NAME  = "hc"
TITLE = "Heroes Chronicles"

SAVEFILE_MAGIC = b"HCHRONSVG"


class DataClass(hero.DataClass):

    def get_version(self):
        """Returns game version."""
        return NAME


class Equipment(DataClass, hero.Equipment):
    __slots__ = {k: make_artifact_cast(k, version=NAME) for k in hero.Equipment.__slots__}


class ArmyStack(DataClass, hero.ArmyStack):   pass

class Army(DataClass, hero.Army):             pass

class Attributes(DataClass, hero.Attributes): pass

class Inventory(DataClass, hero.Inventory):   pass

class Skill(DataClass, hero.Skill):           pass

class Skills(DataClass, hero.Skills):         pass

class Spells(DataClass, hero.Spells):         pass



def adapt(name, value):
    """
    Adapts certain categories:

    - "savefile_magic_regex":       adds support for Chronicles savefiles
    - "savefile_header_regex":      adds support for Chronicles savefiles
    - "hero.PropertyName" classes:  returning version-specific data class
    """
    result = value
    if "hero.ArmyStack" == name:
        result = ArmyStack
    elif "hero.Army" == name:
        result = Army
    elif "hero.Attributes" == name:
        result = Attributes
    elif "hero.Equipment" == name:
        result = Equipment
    elif "hero.Inventory" == name:
        result = Inventory
    elif "hero.Skill" == name:
        result = Skill
    elif "hero.Skills" == name:
        result = Skills
    elif "hero.Spells" == name:
        result = Spells
    elif "savefile_magic_regex" == name:
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
