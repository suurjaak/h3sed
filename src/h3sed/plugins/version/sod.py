# -*- coding: utf-8 -*-
"""
Subplugin for HOMM3 version "Shadow of Death".

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   22.03.2020
@modified  23.05.2024
------------------------------------------------------------------------------
"""
import logging

from h3sed.metadata import BytePositions, Store


logger = logging.getLogger(__package__)


PROPS = {"name": "sod", "label": "Shadow of Death", "index": 2}


"""Game major and minor version byte ranges, as (min, max)."""
VersionByteRanges = {
    "version_major":  (42, 43),
    "version_minor":  ( 2,  4),
}


"""Hero artifacts, for wearing and side slots, excluding spell scrolls."""
Artifacts = [
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
Creatures = [
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


"""Spells for hero to cast."""
Spells = [
    "Titan's Lightning Bolt",
]


"""IDs of artifacts, creatures and spells in savefile."""
IDs = {
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
ArtifactSlots = {
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
}


"""Primary skill modifiers that artifacts give to hero."""
ArtifactStats = {
    "Angelic Alliance":                  (21, 21, 21, 21),
    "Armageddon's Blade":                (+3, +3, +3, +6),
    "Armor of the Damned":               (+3, +3, +2, +2),
    "Power of the Dragon Father":        (16, 16, 16, 16),
    "Titan's Thunder":                   (+9, +9, +8, +8),
}


"""Spells that artifacts make available to hero."""
ArtifactSpells = {
    "Admiral's Hat":                     ["Scuttle Boat", "Summon Boat"],
    "Armageddon's Blade":                ["Armageddon"],
    "Titan's Thunder":                   ["Titan's Lightning Bolt"],
}



def init():
    """Initializes artifacts and creatures for Shadow of Death."""
    Store.add("artifacts", Artifacts, version=PROPS["name"])
    Store.add("artifacts", Artifacts, version=PROPS["name"], category="inventory")
    for slot in set(sum(ArtifactSlots.values(), [])):
        Store.add("artifacts", [k for k, v in ArtifactSlots.items() if v[0] == slot],
                  version=PROPS["name"], category=slot)

    Store.add("artifact_slots",  ArtifactSlots,  version=PROPS["name"])
    Store.add("artifact_spells", ArtifactSpells, version=PROPS["name"])
    Store.add("artifact_stats",  ArtifactStats,  version=PROPS["name"])
    Store.add("creatures",       Creatures,      version=PROPS["name"])
    Store.add("ids",             IDs,            version=PROPS["name"])
    for artifact, spells in ArtifactSpells.items():
        Store.add("spells", spells, version=PROPS["name"], category=artifact)


def props():
    """Returns props as {label, index}."""
    return PROPS


def detect(savefile):
    """Returns whether savefile bytes match Shadow of Death."""
    return savefile.match_byte_ranges(BytePositions, VersionByteRanges)
