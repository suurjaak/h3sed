# -*- coding: utf-8 -*-
"""
API for hero properties.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   14.03.2020
@modified  15.02.2026
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
from . import profile
from . import skills
from . import spells
from . import stats


logger = logging.getLogger(__name__)


## Modules for hero properties in order of showing
PROPERTIES = collections.OrderedDict([
    ("profile",   profile),
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
            minmax[:] = metadata.Store.get("hero_ranges", version=version)[name]

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


def format_artifacts(value, version=None, reverse=False):
    """
    Adds or removes combination artifact text from artifact names.

    @param   value    a single value, or a list of values
    @param   version  game version like "sod", if any
    @param   reverse  strip combination artifact text instead of adding
    """
    COMBINATION_ARTIFACTS = metadata.Store.get("combination_artifacts", version=version)
    COMBINATION_SUFFIX = "  (combined artifact)"
    if not value or not COMBINATION_ARTIFACTS: return value
    result = []
    for v in (value if isinstance(value, list) else [value]):
        if reverse:
            if v and v.endswith(COMBINATION_SUFFIX): v = v[:-len(COMBINATION_SUFFIX)]
        elif v in COMBINATION_ARTIFACTS: v += COMBINATION_SUFFIX
        result.append(v)
    return result if isinstance(value, list) else result[0]



class DataClass(object):
    """Mix-in for hero property classes."""

    @classmethod
    def factory(cls, version):
        return h3sed.version.adapt("hero.%s" % cls.__name__, cls, version)()

    version = property(lambda self: None, doc="Game version, optionally as tuple (name, minor)")

    def realize(self, hero=None):
        """Checks and finalizes changes to data, possibly modifying other hero properies."""
        pass


class SlotCheckerMixin(object):
    """SlotsDict/TypedArray mixin for __contains__() by nested property, e.g. "orc" in hero.army."""

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
    """TypedArray mixin for index() by nested property, e.g. "luck" in hero.skills."""

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
    """Hero army single entry."""
    __slots__ = {"name":  make_string_cast("creatures"),
                 "count": make_integer_cast("army.count")}

    __required__ = ("name", )


class Skill(SlotCheckerMixin, SlotsDict, DataClass):
    """Hero skill single entry."""
    __slots__ = {"name":  make_string_cast("skills"),
                 "level": make_string_cast("skill_levels", default=True)}

    __required__ = ("name", )


class Army(TypedArrayCheckerMixin, TypedArray, DataClass):
    """Hero army property."""

    def __init__(self):
        dataclass = h3sed.version.adapt("hero.%s" % ArmyStack.__name__, ArmyStack, self.version)
        minmax = metadata.Store.get("hero_ranges", version=self.version)["army"]
        TypedArray.__init__(self, cls=dataclass, size=minmax[1], default=dataclass)


class Attributes(SlotsDict, DataClass):
    """Hero main attributes property."""
    __slots__ = dict({k: make_integer_cast(k) for k in (
        "attack", "defense", "power", "knowledge", "exp",
        "level", "movement_left", "movement_total", "mana_left",
    )}, **{k: bool for k in ("spellbook", "ballista", "ammo", "tent")})

    def get_experience_level(self):
        """Returns hero level that ought to match current experience."""
        EXP_LEVELS = metadata.Store.get("experience_levels", version=self.version)
        orderlist = sorted(EXP_LEVELS.items(), reverse=True)
        return next((k for k, v in orderlist if v <= self.exp), None)

    def get_level_experience(self):
        """Returns hero experience that ought to match current level."""
        EXP_LEVELS = metadata.Store.get("experience_levels", version=self.version)
        value = EXP_LEVELS.get(self.level)
        if value is not None and value <= self.exp < EXP_LEVELS.get(self.level + 1, sys.maxsize):
            value = self.exp  # Do not reset experience if already at level
        elif value is None and self.level == 0:
            value = 0
        return value

    def wrap_primary_attribute(self, value):
        """Returns primary attribute wrapped to legal byte range."""
        return value % (metadata.PRIMARY_ATTRIBUTE_RANGE[1] + 1) # Wrap around if overflow

    def make_game_value(self, attribute_name, value):
        """Returns attribute value as used in-game, like knowledge constrained to 1-99."""
        if attribute_name not in metadata.PRIMARY_ATTRIBUTES: return value
        RANGES = metadata.Store.get("primary_attribute_game_ranges", version=self.version)
        MINV, MAXV, OVERFLOW = RANGES[attribute_name]
        if value < MINV or value > MAXV:
            value = MINV if value < MINV or value >= OVERFLOW else MAXV
        return value


class Equipment(SlotCheckerMixin, SlotsDict, DataClass):
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
        data = dict(args[0], **kwargs) if args else kwargs
        eq2 = dict(self)
        eq2.update((location, None) for location in data)
        for location in filter(data.get, self):
            artifact = data[location]
            selected_locations, slot_conflicts = self.solve_locations(artifact, location, eq2)
            if slot_conflicts:
                errors.append(self.format_conflict(artifact, location, slot_conflicts, eq2))
            else:
                eq2[location] = artifact
        return "\n\n".join(errors) if errors else None

    def solve_locations(self, artifact, location=None, equipment=None):
        """
        Analyzes whether and how artifact can be donned, either at any suitable free location,
        or on given location replacing current artifact if any, returns (locations, conflicts).

        @param   equipment  optional Equipment or data dictionary to use if not self
        @return             [primary location and other selected locations for artifact on success],
                            {slot: [primary location of all conflicting artifacts in slot on error]}
        """
        selected_locations, conflicts = {}, {}

        ARTIFACT_TO_SLOTS = metadata.Store.get("artifact_slots",  version=self.version)
        LOCATION_TO_SLOT  = metadata.Store.get("equipment_slots", version=self.version)
        SLOT_TO_LOCATIONS = {slot: [l for l, slot2 in LOCATION_TO_SLOT.items() if slot == slot2]
                             for slot in LOCATION_TO_SLOT.values()}

        if location and location not in SLOT_TO_LOCATIONS[ARTIFACT_TO_SLOTS[artifact][0]]:
            raise ValueError("Cannot equip %s at %s slot" % (artifact, location)) # Wrong location
        if any(slot not in SLOT_TO_LOCATIONS for slot in ARTIFACT_TO_SLOTS[artifact]):
            raise ValueError("Cannot equip %s" % artifact) # Like The Grail: only in inventory

        eq = dict(self if equipment is None else equipment)
        if location is not None: eq[location] = None

        conflict_locations = {} # {location: primary location of conflicting artifact}
        reserved_locations = self.get_reserved_locations(desired_location=location, equipment=eq)
        for i, artifact_slot in enumerate(ARTIFACT_TO_SLOTS[artifact]):
            matched = False
            slot_locations = [location] if location and not i else SLOT_TO_LOCATIONS[artifact_slot]
            # Reverse, as secondary side slots get reserved from last free to first
            for location_candidate in slot_locations[::-1 if i else 1]:
                if eq[location_candidate] is None \
                and location_candidate not in selected_locations \
                and location_candidate not in reserved_locations:
                    selected_locations[location_candidate] = artifact_slot
                    matched = True
                    break # for location_candidate
            if matched: continue # for i, artifact_slot

            for location_candidate in slot_locations:
                if eq[location_candidate] is not None:
                    conflict_locations[location_candidate] = location_candidate
                elif location_candidate in reserved_locations:
                    conflict_locations[location_candidate] = reserved_locations[location_candidate]
                    
        if len(selected_locations) != len(ARTIFACT_TO_SLOTS[artifact]):
            for conflicting_location, artifact_primary_slot in conflict_locations.items():
                slot = LOCATION_TO_SLOT[conflicting_location]
                conflicts.setdefault(slot, []).append(artifact_primary_slot)

        return ([] if conflicts else list(selected_locations)), conflicts

    def get_reserved_locations(self, desired_location=None, equipment=None):
        """
        Returns locations taken by combination artifacts, as {reserved location: primary location}.

        @param   desired_location  optional location to keep free if alternatives possible
        @param   equipment         optional Equipment or data dictionary to use if not self
        """
        ARTIFACT_TO_SLOTS = metadata.Store.get("artifact_slots",  version=self.version)
        LOCATION_TO_SLOT  = metadata.Store.get("equipment_slots", version=self.version)
        SLOT_TO_LOCATIONS = {slot: [l for l, slot2 in LOCATION_TO_SLOT.items() if slot == slot2]
                             for slot in LOCATION_TO_SLOT.values()}

        reserved_locations = {} # {reserved location: primary location holding combo item}
        eq = dict(self if equipment is None else equipment)
        for primary_location, artifact in eq.items():
            slots = ARTIFACT_TO_SLOTS.get(artifact, [])
            for slot in slots[1:]: # Skip artifact first slot as primary
                reserved = False
                # Reverse, as secondary side slots get reserved from last free to first
                for combo_location in SLOT_TO_LOCATIONS[slot][::-1]:
                    if eq[combo_location] is None and combo_location not in reserved_locations:
                        if desired_location is None or combo_location != desired_location:
                            reserved_locations[combo_location] = primary_location
                            reserved = True
                            break # for combo_location
                if not reserved and desired_location and desired_location in SLOT_TO_LOCATIONS[slot]:
                    # Desired location is reserved by existing artifact without alternative
                    reserved_locations[desired_location] = primary_location
        return reserved_locations

    def format_conflict(self, artifact, location, slot_conflicts, equipment=None):
        """
        Returns error string for slot conflict on equipping given artifact in given location.

        @param   equipment  optional Equipment or data dictionary to use if not self
        """
        ARTIFACT_TO_SLOTS = metadata.Store.get("artifact_slots", version=self.version)
        eq = dict(self if equipment is None else equipment)
        lines = []
        for slot, others in slot_conflicts.items():
            needed_count = sum(s == slot for s in ARTIFACT_TO_SLOTS[artifact][1:])
            countstr = "; need %s free" % needed_count if needed_count > 1 else ""
            items, conflict_counts = [], collections.Counter(others)
            for location2 in others:
                count = conflict_counts.pop(location2, None)
                if count:
                    items.append("%s%s" % (eq[location2], " x %s" % count if count > 1 else ""))
            lines.append("- %s (by %s)%s" % (slot, ", ".join(items), countstr))
        return "Cannot equip %s on %s, required slot taken:\n\n%s" % \
               (artifact, location, "\n".join(lines))


class Inventory(TypedArray, DataClass):
    """Hero inventory property."""

    def __init__(self):
        minmax = metadata.Store.get("hero_ranges", version=self.version)["inventory"]
        TypedArray.__init__(self, cls=make_artifact_cast("inventory", self.version), size=minmax[1])

    def make_compact(self, order=(), reverse=False):
        """Returns new inventory with items compacted to top, in specified order if any."""
        items = [x for x in self if x]
        if order:
            ARTIFACT_SLOTS = metadata.Store.get("artifact_slots", version=self.version)
            LOCATION_TO_SLOT = metadata.Store.get("equipment_slots", version=self.version)
            EQUIPMENT_LOCATIONS = list(Equipment.factory(self.version).__slots__)
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
        if reverse: items = items[::-1]
        result = type(self)()
        for i, item in enumerate(items): list.__setitem__(result, i, item)
        return result


class Profile(SlotsDict, DataClass):
    """Hero profile property."""
    __slots__ = {"faction": make_integer_cast("faction", nullable=True)}

    def format_faction(self):
        """Returns hero player faction as text."""
        return self.make_faction_text(self.faction, self.version)
        
    @staticmethod
    def make_faction_text(faction, version=None):
        FACTIONS = metadata.Store.get("player_factions", version=version)
        if faction in FACTIONS:
            return "%s Player" % FACTIONS[faction]
        if faction == metadata.BLANK[0]:
            return "neutral"
        return "0x%X" % faction if isinstance(faction, int) else "unknown"


class Skills(TypedArrayCheckerMixin, TypedArray, DataClass):
    """Hero skills property."""

    def __init__(self):
        dataclass = h3sed.version.adapt("hero.%s" % Skill.__name__, Skill, self.version)
        minmax = metadata.Store.get("hero_ranges", version=self.version)["skills"]
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

        self.profile   = Profile   .factory(version)
        self.stats     = Attributes.factory(version)
        self.skills    = Skills    .factory(version)
        self.army      = Army      .factory(version)
        self.equipment = Equipment .factory(version)
        self.inventory = Inventory .factory(version)
        self.spells    = Spells    .factory(version)
        ## Primary attributes without artifact bonuses, to track changes beyond attribute range
        self.basestats = {}
        ## Primary attributes as used in-game, constrained below 100
        self.gamestats = {}

        ## All properties in one structure
        self.properties = AttrDict((k, getattr(self, k)) for k in list(PROPERTIES))
        ## Deep copy of initial or saved properties, for tracking unsaved changes
        self.original = AttrDict((k, v.copy()) for k, v in self.properties.items())
        ## Deep copy of initial or realized properties, for tracking unrealized changes
        self.realized = AttrDict((k, v.copy()) for k, v in self.properties.items())
        ## Deep copy of initial or serialized properties, for tracking unpatched changes
        self.serialed = AttrDict((k, v.copy()) for k, v in self.properties.items())
        self.ensure_primary_stats()


    def copy(self):
        """Returns a copy of this hero."""
        hero = Hero(self.name, self.version)
        hero.update(self)
        hero.original = AttrDict((k, v.copy()) for k, v in self.original.items())
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
        self.realized = AttrDict((k, v.copy()) for k, v in self.properties.items())
        self.ensure_primary_stats(force=True)


    def ensure_primary_stats(self, force=False):
        """Populates hero primary attributes as base and as used in-game, if not already done."""
        if self.gamestats and self.basestats and not force: return
        ARTIFACT_STATS = metadata.Store.get("artifact_stats", version=self.version)
        diff = [0] * len(metadata.PRIMARY_ATTRIBUTES)
        for artifact in filter(ARTIFACT_STATS.get, self.equipment.values()):
            diff = [a + b for a, b in zip(diff, ARTIFACT_STATS[artifact])]
        for attribute_name, artifacts_bonus in zip(metadata.PRIMARY_ATTRIBUTES, diff):
            base_value = self.stats[attribute_name] - artifacts_bonus
            self.basestats[attribute_name] = self.stats.wrap_primary_attribute(base_value)
            self.gamestats[attribute_name] = self.stats.make_game_value(attribute_name, self.stats[attribute_name])


    def update_primary_stats(self):
        """Updates hero primary attributes, from base stats and current equipment."""
        ARTIFACT_STATS = metadata.Store.get("artifact_stats", version=self.version)
        diff = [0] * len(metadata.PRIMARY_ATTRIBUTES)
        for artifact in filter(ARTIFACT_STATS.get, self.equipment.values()):
            diff = [a + b for a, b in zip(diff, ARTIFACT_STATS[artifact])]
        for attribute_name, artifacts_bonus in zip(metadata.PRIMARY_ATTRIBUTES, diff):
            value = self.basestats[attribute_name] + artifacts_bonus
            self.stats[attribute_name] = self.stats.wrap_primary_attribute(value)
            self.gamestats[attribute_name] = self.stats.make_game_value(attribute_name, self.stats[attribute_name])


    def update_primary_attribute(self, attribute_name, value):
        """Updates hero primary attribute and its base and in-game value."""
        if attribute_name not in metadata.PRIMARY_ATTRIBUTES: return
        value = self.stats.__slots__[attribute_name](value) # Ensure valid range and type; raises
        diff = value - self.stats[attribute_name]
        base_value = self.basestats[attribute_name] + diff
        self.stats    [attribute_name] = value
        self.basestats[attribute_name] = self.stats.wrap_primary_attribute(base_value)
        self.gamestats[attribute_name] = self.stats.make_game_value(attribute_name, value)


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
        self.ensure_primary_stats(force=True)
        self.original = AttrDict((k, v.copy()) for k, v in self.properties.items())
        self.realized = AttrDict((k, v.copy()) for k, v in self.properties.items())
        self.serialed = AttrDict((k, v.copy()) for k, v in self.properties.items())


    def serialize(self):
        """Updates hero bytes with current properties state."""
        self.realize()
        for section, module in PROPERTIES.items():
            if not callable(getattr(module, "serialize", None)): continue # for section
            self.bytes = module.serialize(self.properties[section], self.bytes, self.version, self)
        self.serialed = AttrDict((k, v.copy()) for k, v in self.properties.items())


    def realize(self):
        """Validates changes, propagates across dependent properties, raises on errors in data."""
        if not self.is_changed(): return

        errors = [] # [error message, ]
        self.ensure_primary_stats()
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
        self.update_primary_stats()
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

        collection = dict(self.properties, name=self.name, faction=self.profile.format_faction())
        process_patterns(collection, text_regexes)
        process_keywords(collection)
        return all(r in matches for r in text_regexes) and \
               all((k, r) in matches for k, rr in kw_regexes.items() for r in rr)


    def make_artifact_swap(self, location, inventory_index=None):
        """
        Returns result of swapping contents of equipment location with inventory index,
        as a new pair of (Equipment, Inventory).

        @param   inventory_index  if None, equipped artifact at location is sent to top of inventory
        """
        eq2, inv2 = self.equipment.copy(), self.inventory.copy()
        inventory_filled_size = sum(map(bool, inv2))
        noop = False
        if eq2[location]: noop = (inventory_index is None and inventory_filled_size >= len(inv2))
        else:             noop = (inventory_index is None or  inv2[inventory_index] is None)
        if noop:
            return (eq2, inv2)

        if inventory_index is None:
            inventory_index = 0
            inv2 = inv2.make_compact()
            inv2.insert(inventory_index, None)

        artifact1, artifact2 = eq2[location], inv2[inventory_index]
        if artifact2:
            artifact_locations, slot_conflicts = eq2.solve_locations(artifact2, location)
            if slot_conflicts:
                raise ValueError(eq2.format_conflict(artifact2, location, slot_conflicts))
        eq2[location] = artifact2
        inv2[inventory_index] = artifact1
        return (eq2, inv2)


    def make_artifacts_transfer(self, to_inventory=True):
        """
        Returns result of either sending all possible equipped artifacts to inventory,
        or equipping all possible inventory artifacts, as a new pair of (Equipment, Inventory).
        """
        eq2, inv2 = self.equipment.copy(), self.inventory.copy()
        inventory_filled_size = sum(map(bool, inv2))
        noop = False
        if to_inventory:
            noop = (inventory_filled_size >= len(inv2) or not any(eq2.values()))
        else: noop = all(eq2.values())
        if noop:
            return (eq2, inv2)

        if to_inventory:
            inv2 = inv2.make_compact()
            artifacts_to_inventory, locations_emptied = [], []
            for location, artifact in list(eq2.items()):
                if not artifact: continue # for location,
                locations_emptied.append(location)
                artifacts_to_inventory.append(artifact)
                if inventory_filled_size + len(artifacts_to_inventory) >= len(inv2):
                    break # for location,
            inv2[:0] = artifacts_to_inventory
            for location in locations_emptied: eq2[location] = None
            return (eq2, inv2)

        ARTIFACT_TO_SLOTS = metadata.Store.get("artifact_slots", version=self.version)
        LOCATION_TO_SLOT = metadata.Store.get("equipment_slots", version=self.version)
        SLOT_TO_LOCATIONS = {slot: [l for l, slot2 in LOCATION_TO_SLOT.items() if slot == slot2]
                             for slot in LOCATION_TO_SLOT.values()}

        artifacts_to_equipment = []
        for inventory_index, artifact in enumerate(list(inv2)):
            if artifact is None: continue # for inventory_index,
            if any(slot not in SLOT_TO_LOCATIONS for slot in ARTIFACT_TO_SLOTS[artifact]):
                continue # for inventory_index,
            artifact_locations, slot_conflicts = eq2.solve_locations(artifact)
            if not slot_conflicts:
                eq2[artifact_locations[0]] = artifact
                inv2[inventory_index] = None
                artifacts_to_equipment.append(artifact)
        if artifacts_to_equipment:
            inv2 = inv2.make_compact()
        return (eq2, inv2)


    def make_equipment_swap(self):
        """
        Returns result of swapping current equipment artifacts with suitable inventory artifacts,
        as a new pair of (Equipment, Inventory).
        """
        eq2, inv2 = self.equipment.copy(), self.inventory.copy()

        ARTIFACT_TO_SLOTS = metadata.Store.get("artifact_slots", version=self.version)
        LOCATION_TO_SLOT = metadata.Store.get("equipment_slots", version=self.version)
        SLOT_TO_LOCATIONS = {slot: [l for l, slot2 in LOCATION_TO_SLOT.items() if slot == slot2]
                             for slot in LOCATION_TO_SLOT.values()}
        inventory_slots = {slot: [] for slot in set(LOCATION_TO_SLOT.values())} # {slot: [index, ]}
        for inventory_index, artifact in enumerate(inv2):
            if artifact is None: continue # for inventory_index,
            inventory_slots[ARTIFACT_TO_SLOTS[artifact][0]].append(inventory_index)
        reserved_locations = eq2.get_reserved_locations()

        locations_handled = set()
        artifacts_to_equipment, artifacts_to_inventory = [], []
        inventory_filled_size = sum(map(bool, inv2))
        for location in list(eq2):
            if location in locations_handled: continue # for location
            candidates = inventory_slots[LOCATION_TO_SLOT[location]]
            if not candidates: continue # for location

            artifact1, artifacts_removed, inventory_index2 = eq2[location], [], None
            locations_emptied = set()
            for inventory_index in candidates:
                artifact2 = inv2[inventory_index]
                if artifact1 == artifact2: continue # for inventory_index

                artifact_locations = [] # Locations selected, like ["lefthand", "neck", "cloak"]
                for i, artifact_slot in enumerate(ARTIFACT_TO_SLOTS[artifact2]):
                    # Like ["hand", "neck", "cloak"] for "Ring of the Magi"
                    # Reverse, as secondary side slots get reserved from last free to first
                    for location_candidate in SLOT_TO_LOCATIONS[artifact_slot][::-1 if i else 1]:
                        # Like [["lefthand", "righthand"], ["neck"], ["cloak"]]
                        if location_candidate not in locations_handled \
                        and location_candidate not in artifact_locations:
                            artifact_locations.append(location_candidate)
                            break # for location_candidate
                if len(artifact_locations) != len(ARTIFACT_TO_SLOTS[artifact2]):
                    continue # for inventory_index

                for location_selected in artifact_locations:
                    if eq2[location_selected] is not None: locations_emptied.add(location_selected)
                    elif location_selected in reserved_locations:
                        locations_emptied.add(reserved_locations[location_selected])
                artifacts_removed = [eq2[loc] for loc in locations_emptied]
                if inventory_filled_size + len(artifacts_removed) - 1 < len(inv2):
                    inventory_index2 = inventory_index
                    break # for inventory_index

            if inventory_index2 is None:
                continue # for location

            locations_affected = set(artifact_locations) | locations_emptied
            for location_to_empty in locations_emptied:
                eq2[location_to_empty] = None
            eq2[location] = artifact2
            inv2[inventory_index2] = None

            candidates.remove(inventory_index2)
            for reserved, primary in list(reserved_locations.items()):
                if primary in locations_affected or reserved in locations_affected:
                    reserved_locations.pop(reserved, None)
            locations_handled.update(artifact_locations)
            artifacts_to_equipment.append(artifact2)
            artifacts_to_inventory.extend(artifacts_removed)
            inventory_filled_size += len(artifacts_removed) - 1

        if artifacts_to_equipment or artifacts_to_inventory:
            inv2 = inv2.make_compact()
        if artifacts_to_inventory:
            inv2[:0] = artifacts_to_inventory

        return (eq2, inv2)


    def __eq__(self, other):
        """Returns whether this hero is the same as given (same name and index)."""
        return isinstance(other, Hero) and (self.name, self.index) == (other.name, other.index)


    def __hash__(self):
        """Returns hero hash code from name and index."""
        return hash((self.name, self.index))


    def __lt__(self, other):
        """Returns whether this hero < other hero, by case-insensitive name and index."""
        if not isinstance(other, Hero): return NotImplemented
        mykey    = (self.name .lower(), self .name_counter, self .index or 0)
        otherkey = (other.name.lower(), other.name_counter, other.index or 0)
        return mykey < otherkey


    def __str__(self):
        """Returns hero name, with name counter suffix if marked as duplicate name."""
        result = self.name
        if self.name_counter > 1: result += " (%s)" % self.name_counter
        return result
