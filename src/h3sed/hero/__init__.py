# -*- coding: utf-8 -*-
"""
API for hero properties.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   14.03.2020
@modified  22.08.2025
------------------------------------------------------------------------------
"""
import collections
import copy
import logging
import re
import sys

import h3sed
from .. lib.util import AttrDict, OrderedSet, SlotsDict, TypedArray, tuplefy
from .. import metadata
from . import army
from . import equipment
from . import inventory
from . import skills
from . import spells
from . import stats


logger = logging.getLogger(__name__)


## Modules for hero properties in order of showing
PROPERTIES = collections.OrderedDict([
    ("stats",     stats),
    ("skills",    skills),
    ("army",      army),
    ("equipment", equipment),
    ("inventory", inventory),
    ("spells",    spells),
])


def make_artifact_cast(location, version=None):
    """
    Returns function(value=None) for casting to artifact value in proper case.

    Function raises ValueError if unknown value given.

    @param   location  artifacts location, like "lefthand" or "inventory"
    @param   version   game version like "sod", if any
    @param   default   whether function returns first possible choice if empty value given
    """
    error_template = [] # List for mutability from cast()
    choices = [] # [artifact, ]
    lower_to_cased = {} # {lowercase artifact: artifact}

    def cast(value=None):
        if not lower_to_cased: # First run: populate cache
            if "inventory" == location: slot = location
            else: slot = metadata.Store.get("equipment_slots", version=version)[location]
            error_template[:] = ["Invalid value for %s artifacts: %%r" % slot]
            choices[:] = metadata.Store.get("artifacts", category=slot, version=version)
            lower_to_cased.update((x.lower(), x) for x in choices)

        if not value: return None
        if value in choices: return value
        match = lower_to_cased.get(str(value).lower())
        if match is None: raise ValueError(error_template[0] % value)
        return match
    return cast


def make_integer_cast(name, version=None):
    """
    Returns function(value=None) for casting value to integer in allowed range.

    @param   name  thing to cast, like "attack" or "army.count"
    """
    minmax = []
    def inner(value=None):
        if not minmax: # First run: populate cache
            minmax[:] = metadata.Store.get("hero_ranges", version=version)[name]

        if value is None: return minmax[0]
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
    choices = list(choices)
    lower_to_cased = {} # {lowercase value: value}
    error_template = "Invalid value for %s: %%r" % name

    def cast(*value):
        if not lower_to_cased: # First run: populate cache
            if not choices: choices[:] = metadata.Store.get(name, version=version)
            lower_to_cased.update((x.lower(), x) for x in choices)

        if not value and default: return choices[0]
        value = value[0] if value else None
        if value in (None, ""):
            if nullable: return None
            else: raise ValueError(error_template % value)
        if value in choices: return value
        match = lower_to_cased.get(str(value).lower())
        if match is None: raise ValueError(error_template % value)
        return match
    return cast



class DataClass(object):
    """Mix-in for hero property classes."""

    @classmethod
    def factory(cls, version):
        return h3sed.version.adapt("hero.%s" % cls.__name__, cls, version)()

    def get_version(self):
        """Returns game version."""
        return None

    def realize(self, hero=None):
        """Checks and finalizes changes to data, possibly modifying other hero properies."""
        pass


class ArmyStack(SlotsDict, DataClass):
    """Hero army single entry."""
    __slots__ = {"name":  make_string_cast("creatures"),
                 "count": make_integer_cast("army.count")}

    __required__ = ("name", )


class Skill(SlotsDict, DataClass):
    """Hero skill single entry."""
    __slots__ = {"name":  make_string_cast("skills"),
                 "level": make_string_cast("skill_levels", default=True)}

    __required__ = ("name", )


class Army(TypedArray, DataClass):
    """Hero army property."""

    def __init__(self):
        version = self.get_version()
        dataclass = h3sed.version.adapt("hero.%s" % ArmyStack.__name__, ArmyStack, version)
        minmax = metadata.Store.get("hero_ranges", version=version)["army"]
        TypedArray.__init__(self, cls=dataclass, size=minmax[1], default=dataclass)


class Equipment(SlotsDict, DataClass):
    """Hero equipment property."""
    __slots__ = {k: make_artifact_cast(k) for k in (
        "helm", "neck", "armor", "weapon", "shield", "lefthand", "righthand", "cloak", "feet",
        "side1", "side2", "side3", "side4", "side5",
    )}

    def validate_update(self, *args, **kwargs):
        """
        Returns error string if updating given locations would cause slot conflicts, else None.

        SlotsDict.validate_update() override.
        """
        errors = []

        location_to_slot = metadata.Store.get("equipment_slots", version=self.get_version())
        artifact_to_slots = metadata.Store.get("artifact_slots", version=self.get_version())

        data = dict(args[0], **kwargs) if args else kwargs
        combined = dict(self, **data)
        slots_free, slots_content = collections.defaultdict(int), collections.defaultdict(list)
        for location in self:
            slot = location_to_slot[location]
            slots_free[slot] += 1
        for artifact in combined.values():
            for slot in artifact_to_slots.get(artifact, ()):
                slots_free[slot] -= 1
                slots_content[slot].append(artifact)

        for location, artifact in data.items():
            slot_conflicts = {} # {slot: [other artifacts]}
            for slot in artifact_to_slots.get(artifact, ()):
                if slots_free[slot] < 0:
                    others = list(slots_content[slot])
                    others.remove(artifact)
                    slot_conflicts[slot] = others
            if slot_conflicts:
                lines = ["- %s (by %s)" % (slot, ", ".join(others))
                         for slot, others in slot_conflicts.items()]
                errors.append("Cannot don %s, required slot taken:\n\n%s" % 
                              (artifact, "\n".join(lines)))
        return "\n\n".join(errors) if errors else None


    def realize(self, hero=None):
        """Updates hero primary attributes from changed equipment, if hero given."""
        if not hero: return

        ARTIFACT_STATS = metadata.Store.get("artifact_stats", version=self.get_version())
        HERO_RANGES = metadata.Store.get("hero_ranges", version=self.get_version())
        diff = [0] * len(metadata.PRIMARY_ATTRIBUTES)
        for item in filter(bool, hero.equipment.values()):
            if item in ARTIFACT_STATS: diff = [a + b for a, b in zip(diff, ARTIFACT_STATS[item])]
        hero.ensure_basestats()
        for attribute, value in zip(metadata.PRIMARY_ATTRIBUTES, diff):
            MIN, MAX = HERO_RANGES[attribute]
            v1, v2 = hero.stats[attribute], min(max(MIN, hero.basestats[attribute] + value), MAX)
            if v1 != v2: hero.stats[attribute] = v2



class Attributes(SlotsDict, DataClass):
    """Hero main attributes property."""
    __slots__ = dict({k: make_integer_cast(k) for k in (
        "attack", "defense", "power", "knowledge", "exp",
        "level", "movement_left", "movement_total", "mana_left",
    )}, **{k: bool for k in ("spellbook", "ballista", "ammo", "tent")})

    def get_experience_level(self):
        """Returns hero level that ought to match current experience."""
        EXP_LEVELS = metadata.Store.get("experience_levels", version=self.get_version())
        orderlist = sorted(EXP_LEVELS.items(), reverse=True)
        return next((k for k, v in orderlist if v <= self.exp), None)

    def get_level_experience(self):
        """Returns hero experience that ought to match current level."""
        EXP_LEVELS = metadata.Store.get("experience_levels", version=self.get_version())
        value = EXP_LEVELS.get(self.level)
        if value is not None and value <= self.exp < EXP_LEVELS.get(self.level + 1, sys.maxsize):
            value = self.exp  # Do not reset experience if already at level
        elif value is None and self.level == 0:
            value = 0
        return value


class Inventory(TypedArray, DataClass):
    """Hero inventory property."""

    def __init__(self):
        version = self.get_version()
        minmax = metadata.Store.get("hero_ranges", version=version)["inventory"]
        TypedArray.__init__(self, cls=make_artifact_cast("inventory", version), size=minmax[1])

    def make_compact(self, order=(), reverse=False):
        """Returns new inventory with items compacted to top, in specified order if any."""
        items = [x for x in self if x]
        if order:
            ARTIFACT_SLOTS = metadata.Store.get("artifact_slots", version=self.get_version())
            LOCATION_TO_SLOT = metadata.Store.get("equipment_slots", version=self.get_version())
            EQUIPMENT_LOCATIONS = list(Equipment.factory(self.get_version()).__slots__)
            SLOT_ORDER = [LOCATION_TO_SLOT[location] for location in EQUIPMENT_LOCATIONS]
            SLOT_ORDER.extend(("inventory", "unknown")) # "unknown" just in case
            get_primary_slot = lambda x: ARTIFACT_SLOTS.get(x, SLOT_ORDER[-1:])[0]
            sortkeys = []
            for name in order:
                if "name" == name:
                    sortkeys.append(lambda x: x.lower())
                elif "slot" == name:
                    sortkeys.append(lambda x: SLOT_ORDER.index(get_primary_slot(x)))
            items.sort(key=lambda x: tuple(f(x) for f in sortkeys))
        if reverse:  items = items[::-1]
        result = type(self)()
        result.extend(items)
        return result


class Skills(TypedArray, DataClass):
    """Hero skills property."""

    def __init__(self):
        version = self.get_version()
        dataclass = h3sed.version.adapt("hero.%s" % Skill.__name__, Skill, version)
        minmax = metadata.Store.get("hero_ranges", version=version)["skills"]
        TypedArray.__init__(self, cls=dataclass, size=minmax, default=dataclass)

    def realize(self, hero=None):
        """Drops empty and duplicate entries."""
        drop_indexes, seen = [], set()
        for index in range(len(self)):
            item = self[index]
            if not item or item.name in seen: drop_indexes.append(index)
            else: seen.add(item.name)

        for index in reversed(drop_indexes): # Reverse for stable indexes
            self.pop(index)


class Spells(OrderedSet, DataClass):
    """Hero spells property."""

    def __init__(self, iterable=None):
        key = make_string_cast("spells", nullable=False)
        OrderedSet.__init__(self, key, iterable, cast=True)

    def spawn(self, other=()):
        """Returns new Spells instance from iterable (OrderedSet override)."""
        return type(self)(other)



class Hero(object):

    def __init__(self, name, version=None):
        self.name    = name
        self.version = version
        self.bytes   = None    # Hero bytearray
        self.bytes0  = None    # Hero original or saved bytearray
        self.index   = None    # Hero index in savefile
        self.span    = None    # Hero byte span in uncompressed savefile
        self.name_counter = 1  # 1-based index for hero name, tracking duplicate names

        self.stats     = Attributes.factory(version)
        self.skills    = Skills    .factory(version)
        self.army      = Army      .factory(version)
        self.equipment = Equipment .factory(version)
        self.inventory = Inventory .factory(version)
        self.spells    = Spells    .factory(version)
        ## Primary attributes without artifact bonuses, to track changes beyond attribute range
        self.basestats = {}

        ## All properties in one structure
        self.properties = AttrDict((k, getattr(self, k)) for k in list(PROPERTIES))
        ## Deep copy of initial or saved properties
        self.original = AttrDict((k, v.copy()) for k, v in self.properties.items())
        ## Deep copy of initial or realized properties
        self.realized = AttrDict((k, v.copy()) for k, v in self.properties.items())
        ## Deep copy of initial or serialized properties
        self.serialed = AttrDict((k, v.copy()) for k, v in self.properties.items())
        self.ensure_basestats()


    def copy(self):
        """Returns a copy of this hero."""
        hero = Hero(self.name, self.version)
        hero.update(self)
        hero.set_file_data(self.bytes, self.index, self.span)
        hero.name_counter = self.name_counter
        return hero


    def update(self, hero):
        """Replaces hero properties with those of given hero."""
        for section in PROPERTIES:
            if section not in hero.properties: continue # for section
            prop2 = hero.properties[section].copy()
            self.properties[section] = prop2
            setattr(self, section, prop2)
        self.original = AttrDict((k, v.copy()) for k, v in self.original.items())
        self.realized = AttrDict((k, v.copy()) for k, v in self.realized.items())
        self.ensure_basestats(force=True)


    def ensure_basestats(self, force=False):
        """Populates internal hero stats without artifact bonuses, if not already populated."""
        if self.basestats and not force: return
        ARTIFACT_STATS = metadata.Store.get("artifact_stats", version=self.version)
        diff = [0] * len(metadata.PRIMARY_ATTRIBUTES)
        for artifact_name in filter(ARTIFACT_STATS.get, self.equipment.values()):
            diff = [a + b for a, b in zip(diff, ARTIFACT_STATS[artifact_name])]
        for attribute_name, value in zip(metadata.PRIMARY_ATTRIBUTES, diff):
            self.basestats[attribute_name] = self.stats[attribute_name] - value


    def get_name_ident(self):
        """Returns hero name, or (name, name counter) if marked as duplicate name."""
        return (self.name, self.name_counter) if self.name_counter > 1 else self.name


    def set_file_data(self, bytes, index, span): #, savefile):
        """Sets data on hero raw content and position in savefile."""
        self.bytes  = copy.copy(bytes)
        self.bytes0 = copy.copy(bytes)
        self.index  = index
        self.span   = span
        self.serialed = AttrDict((k, v.copy()) for k, v in self.properties.items())


    def parse(self):
        """Parses hero bytes to properties."""
        for section, module in PROPERTIES.items():
            prop = getattr(self, section)
            state = module.parse(self.bytes, self.version)
            if isinstance(prop, list): prop[:] = state
            else:
                prop.clear()
                prop.update(state)
        self.ensure_basestats(force=True)
        self.original = AttrDict((k, v.copy()) for k, v in self.properties.items())
        self.realized = AttrDict((k, v.copy()) for k, v in self.properties.items())
        self.serialed = AttrDict((k, v.copy()) for k, v in self.properties.items())


    def serialize(self):
        """Updates hero bytes with current properties state."""
        self.realize()
        for section, module in PROPERTIES.items():
            self.bytes = module.serialize(self.properties[section], self.bytes, self.version, self)
        self.serialed = AttrDict((k, v.copy()) for k, v in self.properties.items())


    def realize(self):
        """Validates changes, propagates across dependent properties, raises on errors in data."""
        if not self.is_changed(): return

        errors = [] # [error message, ]
        self.ensure_basestats()
        for section in PROPERTIES:
            prop = getattr(self, section)
            if prop == self.realized[section]: continue # for section
            try: prop.realize(self)
            except Exception as e:
                logger.exception("Invalid data in hero %s %s.", self.get_name_ident(), section)
                errors.append(str(e))
        if errors:
            raise ValueError("Invalid data in hero %s:\n- %s" %
                             (self.get_name_ident(), "\n- ".join(errors)))
        self.realized = AttrDict((k, v.copy()) for k, v in self.properties.items())


    def is_changed(self):
        """Returns whether hero has any unsaved changes."""
        return self.properties != self.original


    def is_patched(self, savefile):
        """Returns whether hero bytes match its span in savefile unpacked contents."""
        if not self.bytes or not self.span or self.properties != self.serialed: return False
        return self.bytes == bytearray(savefile.raw[self.span[0]:self.span[1]])


    def mark_saved(self):
        """Marks hero as saved in savefile."""
        self.bytes0 = copy.copy(self.bytes)
        self.original = AttrDict((k, v.copy()) for k, v in self.properties.items())
        self.realized = AttrDict((k, v.copy()) for k, v in self.properties.items())
        self.serialed = AttrDict((k, v.copy()) for k, v in self.properties.items())


    def matches(self, *texts, **keywords):
        """
        Returns whether this hero matches given texts in properties.

        @param   texts     texts to match in any property value
        @param   keywords  specific keywords to match, like "army" or "skill" or "spell";
                           each valu may be a collection of values like list or tuple
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

        process_patterns(dict(self.properties, name=self.name), text_regexes)
        process_keywords(dict(self.properties, name=self.name))
        return all(r in matches for r in text_regexes) and \
               all((k, r) in matches for k, rr in kw_regexes.items() for r in rr)


    def __eq__(self, other):
        """Returns whether this hero is the same as given (same name and index)."""
        return isinstance(other, Hero) and (self.name, self.index) == (other.name, other.index)


    def __hash__(self):
        """Returns hero hash code from name and index."""
        return hash((self.name, self.index))


    def __str__(self):
        """Returns hero name, with name counter suffix if marked as duplicate name."""
        result = self.name
        if self.name_counter > 1: result += " (%s)" % self.name_counter
        return result
