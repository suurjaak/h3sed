# -*- coding: utf-8 -*-
"""
API for hero properties.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   14.03.2020
@modified  27.09.2026
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
from .. common import Army, DataClass, SlotCheckerMixin, TypedArrayCheckerMixin, \
                      make_artifact_cast, make_integer_cast, make_string_cast
from .. import common
from .. import metadata
from . import equipment
from . import inventory
from . import profile
from . import skills
from . import spells
from . import stats


logger = logging.getLogger(__name__)


## Modules for hero properties in order of showing
PROPERTIES = collections.OrderedDict([
    ("stats",     stats),
    ("skills",    skills),
    ("army",      common.army),
    ("equipment", equipment),
    ("inventory", inventory),
    ("spells",    spells),
    ("profile",   profile),
])


class Skill(SlotCheckerMixin, SlotsDict, DataClass):
    """Hero skill single entry."""
    __slots__ = {"name":  make_string_cast("skills"),
                 "level": make_string_cast("skill_levels", default=True)}

    __required__ = ("name", )


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
            countstr = ("; " + __("need %s free", needed_count)) if needed_count > 1 else ""
            items, conflict_counts = [], collections.Counter(others)
            for location2 in others:
                count = conflict_counts.pop(location2, None)
                if count:
                    items.append("%s%s" % (__(eq[location2]), " x %s" % count if count > 1 else ""))
            lines.append("- %s (%s)%s" % (__(slot), __("by %s", ", ".join(items)), countstr))
        return __("Cannot equip %s on %s, required slot taken", __(artifact), __(location)) + \
               "\n\n" + "\n".join(lines)


class Inventory(TypedArray, DataClass):
    """Hero inventory property."""

    def __init__(self):
        minmax = metadata.Store.get("data_ranges", version=self.version)["inventory"]
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
    __slots__ = {"faction": make_integer_cast("faction", nullable=True), "biography": str,
                 "on_map": make_integer_cast("on_map", nullable=True),
                 "town": lambda x=None: x,
                 "x": make_integer_cast("location_x", nullable=True),
                 "y": make_integer_cast("location_y", nullable=True),
                 "z": make_integer_cast("location_z", nullable=True)}

    def format_faction(self):
        """Returns hero player faction as text."""
        return self.make_faction_text(self.faction, self.version)

    def format_location(self, long=False):
        """Returns hero map coordinates as text."""
        if None in (self.x, self.y, self.z): return ""
        if not long: return "(%s, %s, %s)" % (self.x, self.y, self.z)
        return "x=%s y=%s %s" % (self.x, self.y, __("underground" if self.z else "surface"))

    def format_status(self):
        """Returns hero status as text, like "adventuring" or "inactive"."""
        if self.on_map is None: return ""
        if self.faction == metadata.BLANK[0]:
            return "inactive"
        if self.on_map:
            if self.town: return "visiting"
            return "adventuring"
        return "garrisoned"

    @staticmethod
    def make_faction_text(faction, version=None):
        """Returns given faction as text, like "Red Player" or "neutral"."""
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
        minmax = metadata.Store.get("data_ranges", version=self.version)["skills"]
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



class Hero(common.NamedEntity):

    def __init__(self, name, version=None):
        self.profile   = Profile    .factory(version)
        self.stats     = Attributes .factory(version)
        self.skills    = Skills     .factory(version)
        self.army      = common.Army.factory(version)
        self.equipment = Equipment  .factory(version)
        self.inventory = Inventory  .factory(version)
        self.spells    = Spells     .factory(version)
        ## Primary attributes without artifact bonuses, to track changes beyond attribute range
        self.basestats = {}
        ## Primary attributes as used in-game, constrained below 100
        self.gamestats = {}

        super(Hero, self).__init__("hero", name, PROPERTIES, version)

        self.ensure_primary_stats()


    def update(self, hero):
        """Replaces hero properties with those of given hero."""
        super(Hero, self).update(hero)
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


    def parse(self, savefile):
        """Parses hero bytes to properties."""
        for section, module in PROPERTIES.items():
            prop = getattr(self, section)
            kwargs = {"kind": self.kind, "entity_bytes": self.bytes, "%s_bytes" % self.kind: self.bytes,
                      "version": self.version, "savefile": savefile, "span": self.span}
            state = call_filtered(module.parse, **kwargs)
            if isinstance(prop, list): prop[:] = state
            else:
                prop.clear()
                prop.update(state)
        self.ensure_primary_stats(force=True)
        self.original = AttrDict((k, v.copy()) for k, v in self.properties.items())
        self.realized = AttrDict((k, v.copy()) for k, v in self.properties.items())
        self.serialed = AttrDict((k, v.copy()) for k, v in self.properties.items())


    def realize(self):
        """Validates changes, propagates across dependent properties, raises on errors in data."""
        if not self.is_changed(): return
        self.ensure_primary_stats()
        super(Hero, self).realize()
        self.update_primary_stats()
        self.realized = AttrDict((k, v.copy()) for k, v in self.properties.items())


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
            slot = ARTIFACT_TO_SLOTS[artifact][0]
            if slot in inventory_slots:
                inventory_slots[slot].append(inventory_index)
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
