# -*- coding: utf-8 -*-
"""
API for common properties and plugins.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   15.09.2026
@modified  25.09.2026
------------------------------------------------------------------------------
"""
import collections
import copy
import logging
import re
import sys

import h3sed
from .. lib.i18n import translate as __
from .. lib.util import AttrDict, OrderedSet, SlotsDict, TypedArray, call_filtered, tuplefy
from .. import metadata
from . import army


logger = logging.getLogger(__name__)


def make_artifact_cast(location, version=None):
    """
    Returns function(value=None) for casting to artifact value in proper case.

    Function raises ValueError if unknown value given.

    @param   location  artifacts location, like "lefthand" or "inventory"
    @param   version   game version like "sod", if any
    @param   default   whether function returns first possible choice if empty value given
    """
    slot = []
    choices = [] # [artifact, ]
    lower_to_cased = {} # {lowercase artifact: artifact}

    def cast(value=None):
        if not value: return None

        if not slot: # First run: populate cache
            if "inventory" == location: slot[:] = [location]
            else: slot[:] = [metadata.Store.get("equipment_slots", version=version)[location]]
            choices[:] = metadata.Store.get("artifacts", category=slot[0], version=version)
            lower_to_cased.update((x.lower(), x) for x in choices)
        else: # Check for cache change
            choices2 = metadata.Store.get("artifacts", category=slot[0], version=version)
            if choices2 != choices:
                choices[:] = choices2
                lower_to_cased.clear()
                lower_to_cased.update((x.lower(), x) for x in choices)

        if value in choices: return value
        match = lower_to_cased.get(str(value).lower())
        if match is None:
            raise ValueError("Invalid value for %s artifacts: %r" % (slot[0], value))
        return match
    return cast


def make_integer_cast(name, version=None, nullable=False):
    """
    Returns function(value=None) for casting value to integer in allowed range.

    @param   name      thing to cast, like "attack" or "army.count"
    @param   nullable  whether empty value is allowed
    """
    minmax = []
    def inner(value=None):
        if not minmax: # First run: populate cache
            minmax[:] = metadata.Store.get("data_ranges", version=version)[name]

        if value is None: return None if nullable else minmax[0]
        return min(minmax[1], max(int(value), minmax[0]))
    return inner


def make_string_cast(name, version=None, nullable=True, default=False, choices=()):
    """
    Returns function(value=None) for casting to value of required type in proper case.

    Function returns None if empty value given for nullable.
    
    Function raises ValueError if unknown value givne, or empty value for not nullable.

    @param   name      name for metadata.Store like "artifacts"
    @param   version   game version like "sod", if any
    @param   nullable  whether empty value is allowed
    @param   default   whether to return first choice as default for empty value
    @param   choices   pre-defined choices if not taking from metadata.Store
    """
    is_fixed = bool(choices)
    choices = list(choices)
    lower_to_cased = {} # {lowercase value: value}

    def cast(*value):
        if not choices or not is_fixed:
            choices2 = metadata.Store.get(name, version=version)
            if choices2 != choices:
                choices[:] = choices2
                lower_to_cased.clear()
        if not lower_to_cased:
            lower_to_cased.update((x.lower(), x) for x in choices)

        if not value and default: return choices[0]
        value = value[0] if value else None
        if value in (None, ""):
            if nullable: return None
            else: raise ValueError("Invalid value for %s: %r" % (name, value))
        if value in choices: return value
        match = lower_to_cased.get(str(value).lower())
        if match is None: raise ValueError("Invalid value for %s: %r" % (name, value))
        return match
    return cast


def format_artifacts(value, version=None):
    """
    Returns artifact name for display, translating and adding combination artifact suffix if any.

    @param   value    a single value, or a list of values
    @param   version  game version like "sod", if any
    """
    if not value: return value
    COMBINATION_ARTIFACTS = metadata.Store.get("combination_artifacts", version=version)
    COMBINATION_SUFFIX = "  (%s)" % __("combined artifact")
    if not COMBINATION_ARTIFACTS: return __(value)
    result = []
    for v in (value if isinstance(value, list) else [value]):
        v2 = __(v)
        if v in COMBINATION_ARTIFACTS: v2 += COMBINATION_SUFFIX
        result.append(v2)
    return result if isinstance(value, list) else result[0]


def format_faction(faction, version=None):
    """Returns given faction as text, like "Red Player" or "neutral"."""
    FACTIONS = metadata.Store.get("player_factions", version=version)
    if faction in FACTIONS:
        return "%s Player" % FACTIONS[faction]
    if faction == metadata.BLANK[0]:
        return "neutral"
    return "0x%X" % faction if isinstance(faction, int) else "unknown"


def format_location(x, y, z, long=False):
    """Returns map coordinates as text."""
    if None in (x, y, z): return ""
    if not long: return "(%s, %s, %s)" % (x, y, z)
    return "x=%s y=%s %s" % (x, y, __("underground" if z else "surface"))



class DataClass(object):
    """Mix-in for property classes."""

    @classmethod
    def factory(cls, version):
        name = ".".join((cls.__module__, cls.__qualname__))[6:] # "common.DataClass"
        return h3sed.version.adapt(name, cls, version)()

    version = property(lambda self: None, doc="Game version, optionally as tuple (name, minor)")

    def realize(self, owner=None):
        """Checks and finalizes changes to data, possibly modifying other sibling properties."""
        pass


class SlotCheckerMixin(object):
    """SlotsDict/TypedArray mixin for __contains__() by nested property, e.g. "orc" in Army."""

    def __contains__(self, elem):
        """Returns whether value is present as element or in any structured property."""
        cls = type(self) if isinstance(self, SlotsDict) else self.cls
        if isinstance(self, TypedArray) and isinstance(elem, cls):
            return list.__contains__(self, elem)

        if isinstance(elem, str) and elem in cls.__slots__:
            items = self if isinstance(self, TypedArray) else [self]
            return any(dict.__contains__(x, elem) for x in items)

        data = {}
        for key, cast in cls.__slots__.items():
            try: data[key] = cast(elem)
            except Exception: pass
        if not data: return False
        for item in (self if isinstance(self, TypedArray) else [self]):
            if any(data[k] == item.get(k, item) for k in data): return True
        return False


class TypedArrayCheckerMixin(SlotCheckerMixin):
    """TypedArray mixin for index() by nested property, e.g. "luck" in Skills."""

    def iterindex(self, *value, **attributes):
        """
        Yields indexes of items matching value; raises ValueError if nothing matches.

        @param   value       value to find, if not using attributes
        @param   attributes  attributes to match in structured properties
        """
        if not value and not attributes:
            raise TypeError("expected at least 1 argument, got 0")
        if value and attributes:
            raise TypeError("expected either positional or keyword arguments, got both")
        if value and len(value) > 1:
            raise TypeError("expected a single positional argument, got %s" % len(value))

        found = False
        if attributes: # Match items having same attribute values
            try: data = {k: self.cls.__slots__[k](v) for k, v in attributes.items()}
            except Exception: data = None
            for index, item in enumerate(self) if data is not None else ():
                if all(data[k] == item.get(k, item) for k in data):
                    found = True
                    yield index
            if not found: raise ValueError("%s is not in list" % attributes)
            return

        elem = value[0]
        try: check_key = elem in self.cls.__slots__
        except Exception: check_key = False
        for index, item in enumerate(self): # Match items equaling value or having it as key
            if elem == item or (check_key and dict.__contains__(item, elem)):
                found = True
                yield index
        if found: return

        data = {} # Match any item having this cast value in any attribute
        for key, cast in self.cls.__slots__.items() if hasattr(self.cls, "__slots__") else ():
            try: data[key] = cast(elem)
            except Exception: pass
        for index, item in enumerate(self) if data else ():
            if any(data[k] == item.get(k, item) for k in data):
                found = True
                yield index
        if not found: raise ValueError("%s is not in list" % (elem, ))


class ArmyStack(SlotCheckerMixin, SlotsDict, DataClass):
    """Army single entry."""
    __slots__ = {"name":  make_string_cast("creatures"),
                 "count": make_integer_cast("army.count")}

    __required__ = ("name", )


class Army(TypedArrayCheckerMixin, TypedArray, DataClass):
    """Army property."""

    def __init__(self):
        dataclass = h3sed.version.adapt(ArmyStack.__name__, ArmyStack, self.version)
        minmax = metadata.Store.get("data_ranges", version=self.version)["army"]
        TypedArray.__init__(self, cls=dataclass, size=minmax[1], default=dataclass)



class NamedEntity(object):
    """Base class for Hero and Town types."""

    def __init__(self, kind, name, modules, version=None):
        """
        @param   kind      entity category like "hero" or "town"
        @param   name      entity name like "Gelu"
        @param   modules   property modules as {name: module object}
        @param   version   game version like "sod", if any
        """
        self.kind     = kind
        self.name     = name
        self.version  = version
        self.modules  = modules.copy()
        self.bytes    = None    # Entity bytearray
        self.bytes0   = None    # Entity original or saved bytearray
        self.index    = None    # Entity index in savefile
        self.span     = None    # Entity byte span in uncompressed savefile
        self.name_counter = 1  # 1-based index for entity name, tracking duplicate names

        ## All properties in one structure
        self.properties = AttrDict((k, getattr(self, k)) for k in list(modules))
        ## Deep copy of initial or saved properties, for tracking unsaved changes
        self.original = AttrDict((k, v.copy()) for k, v in self.properties.items())
        ## Deep copy of initial or realized properties, for tracking unrealized changes
        self.realized = AttrDict((k, v.copy()) for k, v in self.properties.items())
        ## Deep copy of initial or serialized properties, for tracking unpatched changes
        self.serialed = AttrDict((k, v.copy()) for k, v in self.properties.items())


    def copy(self):
        """Returns a copy of this entity."""
        entity = type(self)(self.name, self.version)
        entity.update(self)
        entity.original = AttrDict((k, v.copy()) for k, v in self.original.items())
        entity.set_file_data(self.bytes, self.index, self.span)
        entity.name_counter = self.name_counter
        return entity


    def update(self, entity):
        """Replaces entity properties with those of given entity."""
        for section in self.modules:
            if section not in entity.properties: continue # for section
            prop2 = entity.properties[section].copy()
            self.properties[section] = prop2
            setattr(self, section, prop2)
        self.realized = AttrDict((k, v.copy()) for k, v in self.properties.items())


    def get_name_ident(self):
        """Returns entity name, or (name, name counter) if marked as duplicate name."""
        return (self.name, self.name_counter) if self.name_counter > 1 else self.name


    def set_file_data(self, bytes, index, span):
        """Sets data on entity raw content and position in savefile."""
        self.bytes  = copy.copy(bytes)
        self.bytes0 = copy.copy(bytes)
        self.index  = index
        self.span   = span
        self.serialed = AttrDict((k, v.copy()) for k, v in self.properties.items())


    def serialize(self):
        """Updates entity bytes with current properties state."""
        self.realize()
        for section, module in self.modules.items():
            if not callable(getattr(module, "serialize", None)): continue # for section
            kwargs = {"kind": self.kind, section: self.properties[section],
                      "entity_bytes": self.bytes, "%s_bytes" % self.kind: self.bytes,
                      "version": self.version, "entity": self, self.kind: self}
            self.bytes = call_filtered(module.serialize, **kwargs)
        self.serialed = AttrDict((k, v.copy()) for k, v in self.properties.items())


    def realize(self):
        """Validates changes, propagates across dependent properties, raises on errors in data."""
        if not self.is_changed(): return

        errors = [] # [error message, ]
        for section, prop in self.properties.items():
            if prop == self.realized[section]: continue # for section
            try: prop.realize(self)
            except Exception as e:
                logger.exception("Invalid data in %s %s %s.",
                                 self.kind, self.get_name_ident(), section)
                errors.append(str(e))
        if errors:
            raise ValueError("Invalid data in %s %s:\n- %s" %
                             (self.kind, self.get_name_ident(), "\n- ".join(errors)))
        self.realized = AttrDict((k, v.copy()) for k, v in self.properties.items())


    def is_changed(self):
        """Returns whether entity has any unsaved changes."""
        return self.properties != self.original


    def is_patched(self, savefile):
        """Returns whether entity bytes match its span in savefile unpacked contents."""
        if not self.bytes or not self.span or self.properties != self.serialed: return False
        return self.bytes == bytearray(savefile.raw[self.span[0]:self.span[1]])


    def mark_saved(self):
        """Marks entity as saved in savefile."""
        self.bytes0 = copy.copy(self.bytes)
        self.original = AttrDict((k, v.copy()) for k, v in self.properties.items())
        self.realized = AttrDict((k, v.copy()) for k, v in self.properties.items())
        self.serialed = AttrDict((k, v.copy()) for k, v in self.properties.items())


    def matches(self, *texts, **keywords):
        """
        Returns whether this entity matches given texts in properties.

        @param   texts     texts to match in any property value
        @param   keywords  specific keywords to match, like "army" or "skill" or "spell";
                           each value may be a collection of values like list or tuple
        """
        matches = set() # {patterns that found match}
        text_regexes = [re.compile(re.escape(str(t)), re.IGNORECASE) for t in texts]
        kw_regexes = {}
        for keyword, values in keywords.items():
            rgxs = [re.compile(re.escape(str(v)), re.IGNORECASE) for v in tuplefy(values)]
            if rgxs: kw_regexes.setdefault(keyword.lower(), []).extend(rgxs)
            for single, plural in [("skill", "skills"), ("spell", "spells")]:
                if single in kw_regexes:
                    kw_regexes.setdefault(plural, []).extend(kw_regexes.pop(single))

        def process_patterns(collection, regexes, prefix=None):
            for value in collection.values() if isinstance(collection, dict) else collection:
                if isinstance(value, dict): process_patterns(value, regexes)
                else:
                    value = str(value)
                    if prefix is None: matches.update(r for r in regexes if r.search(value))
                    else: matches.update((prefix, r) for r in regexes if r.search(value))

        def process_keywords(collection):
            if isinstance(collection, dict):
                for keyword in kw_regexes:
                    if keyword in collection:
                        process_patterns([collection[keyword]], kw_regexes[keyword], prefix=keyword)
                for value in collection.values():
                    if isinstance(value, (dict, list, set)): process_keywords(value)
            else:
                for value in collection:
                    if isinstance(value, dict): process_keywords(value)

        collection = dict(self.properties, name=self.name)
        if hasattr(self, "profile"): collection.update(faction=self.profile.format_faction())
        process_patterns(collection, text_regexes)
        process_keywords(collection)
        return all(r in matches for r in text_regexes) and \
               all((k, r) in matches for k, rr in kw_regexes.items() for r in rr)


    def __eq__(self, other):
        """Returns whether this entity is the same as given (same name and index)."""
        return isinstance(other, type(self)) and (self.name, self.index) == (other.name, other.index)


    def __hash__(self):
        """Returns entity hash code from name and index."""
        return hash((self.name, self.index))


    def __lt__(self, other):
        """Returns whether this entity < other entity, by case-insensitive name and index."""
        if not isinstance(other, type(self)): return NotImplemented
        mykey    = (self.name .lower(), self .name_counter, self .index or 0)
        otherkey = (other.name.lower(), other.name_counter, other.index or 0)
        return mykey < otherkey


    def __str__(self):
        """Returns entity name, with name counter suffix if marked as duplicate name."""
        result = self.name
        if self.name_counter > 1: result += " (%s)" % self.name_counter
        return result
