# -*- coding: utf-8 -*-
"""
Subplugin for HOMM3 version "Shadow of Death".

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   22.03.2020
@modified  26.07.2025
------------------------------------------------------------------------------
"""
from .. import hero
from .. import metadata
from .. hero import make_artifact_cast, make_integer_cast, make_string_cast


NAME  = "sod"
TITLE = "Shadow of Death"


"""Game major and minor version byte ranges, as (min, max)."""
VERSION_BYTE_RANGES = {
    "version_major":  (42, 43),
    "version_minor":  ( 2,  4),
}


"""Hero artifacts, for wearing and side slots, excluding spell scrolls."""
ARTIFACTS = [
    "Admiral's Hat",
    "Angelic Alliance",
    "Armageddon's Blade",
    "Armor of the Damned",
    "Bow of the Sharpshooter",
    "Cloak of the Undead King",
    "Cornucopia",
    "Elixir of Life",
    "Power of the Dragon Father",
    "Ring of the Magi",
    "Statue of Legion",
    "Titan's Thunder",
    "Vial of Dragon Blood",
    "Wizard's Well",
]


"""Creatures for hero army slots."""
CREATURES = [
    "Azure Dragon",
    "Boar",
    "Crystal Dragon",
    "Enchanter",
    "Energy Elemental",
    "Faerie Dragon",
    "Firebird",
    "Halfling",
    "Ice Elemental",
    "Magic Elemental",
    "Magma Elemental",
    "Mummy",
    "Nomad",
    "Peasant",
    "Phoenix",
    "Pixie",
    "Psychic Elemental",
    "Rogue",
    "Rust Dragon",
    "Sharpshooter",
    "Sprite",
    "Storm Elemental",
    "Troll",
]


"""IDs of artifacts, creatures and spells in savefile."""
IDS = {
    # Artifacts
    "Admiral's Hat":                     0x88,
    "Angelic Alliance":                  0x81,
    "Armageddon's Blade":                0x80,
    "Armor of the Damned":               0x84,
    "Bow of the Sharpshooter":           0x89,
    "Cloak of the Undead King":          0x82,
    "Cornucopia":                        0x8C,
    "Elixir of Life":                    0x83,
    "Power of the Dragon Father":        0x86,
    "Ring of the Magi":                  0x8B,
    "Statue of Legion":                  0x85,
    "Titan's Thunder":                   0x87,
    "Vial of Dragon Blood":              0x7F,
    "Wizard's Well":                     0x8A,

    # Creatures
    "Azure Dragon":                      0x84,
    "Boar":                              0x8C,
    "Crystal Dragon":                    0x85,
    "Enchanter":                         0x88,
    "Energy Elemental":                  0x81,
    "Faerie Dragon":                     0x86,
    "Firebird":                          0x82,
    "Halfling":                          0x8A,
    "Ice Elemental":                     0x7B,
    "Magic Elemental":                   0x79,
    "Magma Elemental":                   0x7D,
    "Mummy":                             0x8D,
    "Nomad":                             0x8E,
    "Peasant":                           0x8B,
    "Phoenix":                           0x83,
    "Pixie":                             0x76,
    "Psychic Elemental":                 0x78,
    "Rogue":                             0x8F,
    "Rust Dragon":                       0x87,
    "Sharpshooter":                      0x89,
    "Sprite":                            0x77,
    "Storm Elemental":                   0x7F,
    "Troll":                             0x90,

    # Spells
    "Titan's Lightning Bolt":            0x39,
}


"""Artifact slots, with first being primary slot."""
ARTIFACT_SLOTS = {
    "Admiral's Hat":                     ["helm", "neck"],
    "Angelic Alliance":                  ["weapon", "helm", "neck", "armor", "shield", "feet"],
    "Armageddon's Blade":                ["weapon"],
    "Armor of the Damned":               ["armor", "helm", "weapon", "shield"],
    "Bow of the Sharpshooter":           ["side", "side", "side"],
    "Cloak of the Undead King":          ["cloak", "neck", "feet"],
    "Cornucopia":                        ["side", "hand", "hand", "cloak"],
    "Elixir of Life":                    ["side", "hand", "hand"],
    "Power of the Dragon Father":        ["armor", "helm", "neck", "weapon", "shield", "hand", "hand", "cloak", "feet"],
    "Ring of the Magi":                  ["hand", "neck", "cloak"],
    "Statue of Legion":                  ["side", "side", "side", "side", "side"],
    "Titan's Thunder":                   ["weapon", "helm", "armor", "shield"],
    "Vial of Dragon Blood":              ["side"],
    "Wizard's Well":                     ["side", "side", "side"],
}


"""Primary skill modifiers that artifacts give to hero."""
ARTIFACT_STATS = {
    "Angelic Alliance":                  (21, 21, 21, 21),
    "Armageddon's Blade":                (+3, +3, +3, +6),
    "Armor of the Damned":               (+3, +3, +2, +2),
    "Power of the Dragon Father":        (16, 16, 16, 16),
    "Titan's Thunder":                   (+9, +9, +8, +8),
}


"""Spells that artifacts make available to hero."""
ARTIFACT_SPELLS = {
    "Admiral's Hat":                     ["Scuttle Boat", "Summon Boat"],
    "Armageddon's Blade":                ["Armageddon"],
    "Titan's Thunder":                   ["Titan's Lightning Bolt"],
}



class DataClass(hero.DataClass):

    def get_version(self):
        """Returns game version."""
        return NAME


class ArmyStack(DataClass, hero.ArmyStack):
    __slots__ = {"name":  make_string_cast("creatures", version=NAME),
                 "count": make_integer_cast("army.count", version=NAME)}



class Equipment(DataClass, hero.Equipment):
    __slots__ = {k: make_artifact_cast(k, version=NAME) for k in hero.Equipment.__slots__}
                 
                 
class Army(DataClass, hero.Army):             pass

class Attributes(DataClass, hero.Attributes): pass

class Inventory(DataClass, hero.Inventory):   pass

class Skill(DataClass, hero.Skill):           pass

class Skills(DataClass, hero.Skills):         pass

class Spells(DataClass, hero.Spells):         pass



def init():
    """Initializes artifacts and creatures for Shadow of Death."""
    metadata.Store.add("artifacts", ARTIFACTS, version=NAME)
    metadata.Store.add("artifacts", ARTIFACTS, category="inventory", version=NAME)
    for slot in set(sum(ARTIFACT_SLOTS.values(), [])):
        metadata.Store.add("artifacts", [k for k, v in ARTIFACT_SLOTS.items() if v[0] == slot],
                           category=slot, version=NAME)

    metadata.Store.add("artifact_slots",  ARTIFACT_SLOTS,  version=NAME)
    metadata.Store.add("artifact_spells", ARTIFACT_SPELLS, version=NAME)
    metadata.Store.add("artifact_stats",  ARTIFACT_STATS,  version=NAME)
    metadata.Store.add("creatures",       CREATURES,      version=NAME)
    metadata.Store.add("ids",             IDS,            version=NAME)
    for artifact, spells in ARTIFACT_SPELLS.items():
        metadata.Store.add("spells", spells, category=artifact, version=NAME)


def adapt(name, value):
    """
    Adapts certain categories:

    - all hero property classes:  returning version-specific data class,
                                  with support for new artifacts-creatures-spells
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
    return result


def detect(savefile):
    """Returns whether savefile bytes match Shadow of Death."""
    return savefile.match_byte_ranges(metadata.BYTE_POSITIONS, VERSION_BYTE_RANGES)
