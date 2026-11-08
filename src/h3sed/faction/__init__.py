# -*- coding: utf-8 -*-
"""
API for faction properties.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   02.11.2026
@modified  08.11.2026
------------------------------------------------------------------------------
"""
import collections

import h3sed
from .. lib.i18n import translate as __
from .. lib.util import AttrDict, call_filtered
from .. import common
from .. import metadata
from . import heroes
from . import resources
from . import tavern
from . import towns


## Modules for faction properties in order of showing
PROPERTIES = collections.OrderedDict([
    ("resources",     resources),
    ("hero_order",    heroes),
    ("towns",         towns),
    ("tavern_heroes", tavern),
])


class Resources(common.SlotsDict, common.DataClass):
    """Faction resources property."""
    __slots__ = {n: common.make_integer_cast("resource.%s" % n) for n in metadata.RESOURCES}



class Faction(common.NamedEntity):
    """Faction data container."""


    def __init__(self, faction, version=None):
        self.faction = faction
        self.heroes  = []
        self.towns   = []

        self.resources     = Resources.factory(version)
        self.hero_order    = []
        self.tavern_heroes = []
        name = metadata.PLAYER_FACTIONS[faction]
        super(Faction, self).__init__("faction", name, PROPERTIES, version)


    def copy(self):
        """Returns a copy of this faction."""
        entity = type(self)(self.faction, self.version)
        entity.update(self)
        entity.original = AttrDict((k, v.copy()) for k, v in self.original.items())
        entity.set_file_data(self.bytes, self.index, self.span)
        return entity


    def format(self):
        """Returns entity name for display."""
        return __(str(self))


    def __str__(self):
        """Returns faction name."""
        return common.format_faction(self.faction, version=self.version)
