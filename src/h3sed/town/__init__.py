# -*- coding: utf-8 -*-
"""
API for hero properties.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   16.09.2026
@modified  01.10.2026
------------------------------------------------------------------------------
"""
import collections
import re
import sys

import h3sed
from .. lib.util import AttrDict, OrderedSet, SlotsDict, TypedArray, tuplefy
from .. import common
from .. import metadata
from . import profile


## Modules for army properties in order of showing
PROPERTIES = collections.OrderedDict([
    ("profile",   profile),
    ("army",      common.army),
])


class Profile(common.SlotsDict, common.DataClass):
    """Town profile property."""
    __slots__ = {"faction": common.make_integer_cast("faction", nullable=True),
                 "type": common.make_integer_cast("town.type", nullable=True),
                 "x": common.make_integer_cast("location_x", nullable=True),
                 "y": common.make_integer_cast("location_y", nullable=True),
                 "z": common.make_integer_cast("location_z", nullable=True),
                 "garrison_hero": lambda x=None: x,
                 "visiting_hero": lambda x=None: x}

    def format_faction(self):
        """Returns town player faction as text."""
        return common.format_faction(self.faction, self.version)

    def format_location(self, long=False):
        """Returns town map coordinates as text."""
        return common.format_location(self.x, self.y, self.z)

    def format_type(self):
        """Returns town type as text."""
        return common.format_town_type(self.type, self.version)



class Town(common.NamedEntity):

    def __init__(self, name, version=None):
        self.army    = h3sed.common.Army.factory(version)
        self.profile = Profile.factory(version)
        super(Town, self).__init__("town", name, PROPERTIES, version)
