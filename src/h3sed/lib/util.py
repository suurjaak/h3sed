# -*- coding: utf-8 -*-
"""
Miscellaneous utility functions.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     19.11.2011
@modified    22.08.2025
------------------------------------------------------------------------------
"""
import codecs
import copy
import csv
import ctypes
import locale
import math
import os
import re
import subprocess
import sys
import struct
import warnings

try: import collections.abc as collections_abc             # Py3
except ImportError: import collections as collections_abc  # Py2
try: from urllib.parse import urljoin                      # Py3
except ImportError: from urlparse import urljoin           # Py2
try: from urllib.request import pathname2url               # Py3
except ImportError: from urllib import pathname2url        # Py2

try: int_types = (int, long)            # Py2
except Exception: int_types = (int, )   # Py3
try: text_types = (str, unicode)        # Py2
except Exception: text_types = (str, )  # Py3
try: string_type = unicode              # Py2
except Exception: string_type = str     # Py3


class AttrDict(dict):
    """Dictionary supporting string keys as directly accessible attributes."""

    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class OrderedSet(set):
    """
    An ordered set with a custom key function, elements are returned in insert order or key order.

    Elements need to be homogenous: comparable types, or tuples of comparable types, or None.

    Override spawn() in child classes to retain child type in set operations.
    """

    def __init__(self, key, iterable=None, insertorder=False, cast=False):
        """
        @param   key          callable(element) returning a comparable hashable key for any element
        @param   iterable     iterable to populate this set from, if any
        @param   insertorder  whether to iterate elements in insert order or key order
        @param   cast         whether to use key as element cast function
        """
        self._data = {} # {key(element): element}
        self._vals = [] # [element, ]
        self._order = bool(insertorder)
        self._cast  = bool(cast)
        self._ = key
        if iterable: self.update(iterable)

    def add(self, elem):
        """Adds an element to the set, unless already present."""
        key = self._(elem)
        if key not in self._data:
            if self._cast: elem = key
            self._data[key] = elem
            self._vals.append(elem)

    def clear(self):
        """Removes all elements of this set."""
        self._data.clear()
        del self._vals[:]

    def copy(self):
        """Returns shallow copy of this set."""
        result = self.spawn()
        result._data.update(self._data)
        result._vals.extend(self._vals)
        return result

    def difference(self, *others):
        """Returns new set with elements present in this set but not in any of the others."""
        result = self.copy()
        for other in others:
            otherset = other if isinstance(other, OrderedSet) else self.spawn(other)
            for elem in list(result):
                if elem in otherset:
                    result.remove(elem)
        return result

    def difference_update(self, *others):
        """Updates this set, removing elements found in any of the others."""
        for other in others:
            otherset = other if isinstance(other, OrderedSet) else self.spawn(other)
            for elem in list(self):
                if elem in otherset:
                    self.remove(elem)

    def discard(self, elem):
        """Removes element from the set if present."""
        key = self._(elem)
        if key in self._data:
            elem = self._data.pop(key)
            self._vals.remove(elem)

    def intersection(self, *others):
        """Returns new set with elements present in this set and all of the others."""
        result = self.copy()
        for other in others:
            otherset = other if isinstance(other, OrderedSet) else self.spawn(other)
            for elem in list(result):
                if elem not in otherset:
                    result.remove(elem)
        return result

    def intersection_update(self, *others):
        """Updates this set, keeping elements present in this set and all of the others."""
        for other in others:
            otherset = other if isinstance(other, OrderedSet) else self.spawn(other)
            for elem in list(self):
                if elem not in otherset:
                    self.remove(elem)

    def isdisjoint(self, other):
        """Returns whether this set and the other set have no common elements."""
        return bool(self.intersection(other))

    def issubset(self, other):
        """Returns whether this set is a subset of the other (fully contained in the other)."""
        otherset = other if isinstance(other, OrderedSet) else self.spawn(other)
        return all(v in otherset for v in self)

    def issuperset(self, other):
        """Returns whether this set is a superset of the other (other fully contained in this)."""
        return all(v in self for v in other)

    def pop(self):
        """Removes and returns arbitrary element from this set; raises KeyError if empty."""
        if not self._data: raise KeyError("pop from an empty set")
        key = next(iter(self._data))
        elem = self._data.pop(key)
        self._vals.remove(key)
        return elem

    def remove(self, elem):
        """Removes specified element from this set; raises KeyError if not present"""
        key = self._(elem)
        if key not in self._data: raise KeyError(elem)
        elem = self._data.pop(key)
        self._vals.remove(elem)

    def spawn(self, other=()):
        """Returns new OrderedSet from iterable, using same key function and insert order flag."""
        return OrderedSet(self._, other, insertorder=self._order, cast=self._cast)

    def symmetric_difference(self, other):
        """Returns new set with elements present in either this set or the other, but not in both."""
        result = self.spawn()
        otherset = other if isinstance(other, OrderedSet) else self.spawn(other)
        for elements, skip in [(self, otherset), (otherset, self)]:
            for elem in elements:
                if elem not in skip:
                    result.add(elem)
        return result

    def symmetric_difference_update(self, other):
        """Updates this set, keeping only elements present in either this set or the other, but not in both."""
        keys0 = list(self._data)
        otherset = other if isinstance(other, OrderedSet) else self.spawn(other)
        for key, elem in list(self._data.items()):
            if key in otherset:
                self._data.pop(key)
                self._vals.remove(elem)
        for elem in otherset:
            if self._(elem) not in keys0:
                self.add(elem)

    def union(self, *others):
        """Returns new set containing all elements in this set plus all elements in all other sets."""
        result = self.copy()
        for other in others:
            result.update(other)
        return result

    def update(self, *others):
        """Updates this set, adding elements from all others."""
        for other in others:
            for v in other: self.add(v)

    def __and__(self, other):
        """Returns self & other; equivalent to self.intersection(other)."""
        return self.intersection(other)

    def __copy__(self):
        """Returns a shallow copy of this."""
        return self.copy()

    def __deepcopy__(self, memo=None):
        """Returns a deep copy of this."""
        result = self.spawn()
        result._data.update(copy.deepcopy(self._data, memo))
        result._vals.extend(copy.deepcopy(self._vals, memo))
        return result

    def __ge__(self, other):
        """Returns self >= other; equivalent to self.issuperset(other)."""
        return self.issuperset(other)

    def __gt__(self, other):
        """Returns self > other; equivalent to self.issuperset(other) and self != other."""
        return self.issuperset(other) and self != other

    def __iand__(self, other):
        """Performs self &= other; equivalent to self.intersection_update(other)."""
        self.intersection_update(other)
        return self

    def __ior__(self, other):
        """Returns self |= other; equivalent to self.update(other)."""
        self.update(other)
        return self

    def __ixor__(self, other):
        """Returns self ^= other; equivalent to self.symmetric_difference_update(other)."""
        self.symmetric_difference_update(other)
        return self

    def __or__(self, other):
        """Returns self | other; new set containing all from this and the other set.."""
        return self.union(other)

    def __rand__(self, other):
        """Returns other & self; equivalent to OrderedSet(other).intersection(self)."""
        otherset = other if isinstance(other, OrderedSet) else self.spawn(other)
        return otherset.intersection(self)

    def __ror__(self, other):
        """Returns other | self; equivalent to OrderedSet(other).union(self)."""
        otherset = other if isinstance(other, OrderedSet) else self.spawn(other)
        return otherset.union(self)

    def __rsub__(self, other):
        """Returns other - self; equivalent to OrderedSet(other).difference(self)."""
        otherset = other if isinstance(other, OrderedSet) else self.spawn(other)
        return otherset.difference(self)

    def __rxor__(self, other):
        """Returns other ^ self; equivalent to OrderedSet(other).symmetric_difference(self)."""
        otherset = other if isinstance(other, OrderedSet) else self.spawn(other)
        return otherset.symmetric_difference(self)

    def __sub__(self, other):
        """Returns self - other; equivalent to self.difference(other)."""
        return self.difference(other)

    def __xor__(self, other):
        """Returns self ^ value; equivalent to self.symmetric_difference(other)."""
        return self.symmetric_difference(other)

    def __bool__(self): return bool(self._data)

    def __contains__(self, elem): return self._(elem) in self._data

    def __eq__(self, other):
        return isinstance(other, type(self)) and set(self._vals) == set(other._vals)

    def __ne__(self, other):
        return not (self == other)

    def __len__(self): return len(self._data)

    def __iter__(self):
        if self._order:
            return iter(self._vals)
        sortkey = lambda x: () if x[0] is None else tuplefy(x[0])
        return iter(v for k, v in sorted(self._data.items(), key=sortkey))

    def __str__(self): return repr(self)

    def __repr__(self): return "%s(%s)" % (type(self).__name__, list(self))


class SlotsDict(dict):
    """
    Simple attrdict with fixed keys and typed values, attributes defined in subclass __slots__.

    If blanks are not allowed in subclass, dict is either always empty, or fully populated.

    Also, if blanks are not allowed, dropping any key clears every key;
    and adding any key ensures other elements are populated.
    """

    ## {attribute name: callback used as cast(value) for value and cast() for default}
    __slots__ = {}

    ## Dict always populated with defaults if empty, otherwise attribute names to require as input
    __required__ = ()

    def __init__(self, *args, **kwargs):
        if len(args) > 1: raise TypeError("%s expected at most 1 argument, got %s" %
                                          (type(self).__name__, len(args)))
        super(SlotsDict, self).__init__()
        data = kwargs if not args else dict(args[0], **kwargs)
        bad = next((key for key in data if key not in self.__slots__), None)
        if bad: raise TypeError("%r is an invalid argument for %s()" % (bad, type(self).__name__))
        if not self.__required__: # Populate all keys with default values
            self.update(((k, None) for k in self.__slots__))
        if data: self.update(data)

    def copy(self):
        """Returns a deep copy of this."""
        return type(self)(self)

    def clear(self):
        """Clears all items, or populates with defaults if blanks allowed."""
        if self.__required__: dict.clear(self)
        else: # Populate all keys with default values
            dict.update(self, [(key, cast()) for key, cast in self.__slots__.items()])

    def pop(self, key, *args):
        """
        Removes specified key and returns corresponding value; clears all if blanks not allowed.

        If key not found, returns given default or raises KeyError if default not given.
        """
        if len(args) > 1:
            raise TypeError("pop expected at most 2 arguments, got %s" % (len(args) + 1))
        if key in self.__slots__:
            value = self[key] if not args or key in self else args[0] # KeyError if no default given
            dict.clear(self) if self.__required__ else dict.pop(self, key)
            return value
        elif args: return args[0]
        else: raise KeyError(key)

    def popitem(self):
        """
        Removes and returns a (key, value) pair as a 2-tuple; clears all if blanks not allowed.

        Pairs are returned in LIFO (last-in, first-out) order. Raises KeyError if empty.
        """
        if not self: raise KeyError("popitem(): dictionary is empty")
        key, value = next(reversed(self.items()))
        dict.clear(self) if self.__required__ else dict.pop(self, key)
        return key, value

    def setdefault(self, key, value):
        """
        Inserts key with a value of default if key not present.

        Returns existing value if present else given value.

        If blanks not allowed and the only required key given, populates other keys with defaults.
        If blanks not allowed and a non-required key given, does nothing.
        """
        if key not in self: self[key] = value
        return self[key] if key in self else value

    def update(self, iterable=None, **kwargs):
        """
        Updates items from iterable and keywords.

        Raises KeyError if key not in slots, or ValueError if invalid value.

        If blanks not allowed and any value blanked, clears all items.
        If blanks not allowed and all required keys given, populates missing keys with defaults.
        """
        items = []
        if callable(getattr(iterable, "keys", None)):
            iterable = [(k, iterable[k]) for k in iterable.keys()]
        for collection in (iterable or (), kwargs.items()):
            for key, value in collection:
                cast = self.__slots__[key] # KeyError if unknown key
                if value is not None or not self.__required__ or key in self.__required__:
                    value = cast(value)
                items.append((key, value))

        error = self.validate_update(items)
        if error: raise ValueError(error)

        for key, value in items:
            dict.__setitem__(self, key, value)

        if not self.__required__: return
        if any(self.get(k) is None for k in self.__required__) \
        or any(self.get(k, self) is None for k in self.__slots__):
            dict.clear(self)
            return
        for key in self.__slots__:
            if key not in self:
                dict.__setitem__(self, key, self.__slots__[key]())

    def validate_update(self, *args, **kwargs):
        """Returns error string if given update would be invalid (stub for subclass)."""
        return None

    def __getattr__(self, name):
        """Returns value if name in slots else attribute; raises AttributeError if unknown name."""
        if name in self.__slots__:
            if name not in self:
                raise AttributeError("%r attribute %r is unset" % (type(self).__name__, name))
            return self[name]
        return self.__getattribute__(name)

    def __setattr__(self, key, value):
        """
        Sets key value if key in slots, else raises AttributeError.

        Raises ValueError if invalid value.
        """
        if key in self.__slots__:
            self.__setitem__(key, value)
            return
        raise AttributeError("setattr: type object %r has no attribute %r" % (type(self).__name__, key))

    def __delattr__(self, name):
        """
        Deletes item if name in slots, and clears all if blanks not allowed.
        
        Raises AttributeError if unknown name.
        """
        if name not in self.__slots__:
            raise AttributeError("type object %r has no attribute %r" % (type(self).__name__, name))
        if self.__required__: dict.clear(self)
        else:
            dict.__setitem__(self, name, self.__slots__[name]())

    def __delitem__(self, key):
        """
        Deletes item if key in slots, and clears all if blanks not allowed.
        
        Raises KeyError if unknown key.
        """
        if key not in self.__slots__:
            raise KeyError(key)
        if self.__required__: dict.clear(self)
        else:
            dict.__setitem__(self, key, self.__slots__[key]())

    def __setitem__(self, key, value):
        """
        Sets self[key] to value.

        Raises KeyError if key not in slots, or ValueError if invalid value.

        If blanks not allowed and any value blanked, clears all items.
        If blanks not allowed and all required keys given, populates missing keys with defaults.
        """
        if key not in self.__slots__:
            raise KeyError(key)

        if value is None and self.__required__:
            dict.clear(self)
            return

        value = self.__slots__[key](value)
        error = self.validate_update(**{key: value})
        if error: raise ValueError(error)
        dict.__setitem__(self, key, value)

        if not self.__required__: return
        for key2 in self.__slots__:
            if key2 in self: continue # for key2
            if key2 in self.__required__:
                dict.clear(self)
                break # for key2
            else:
                dict.__setitem__(self, key2, self.__slots__[key2]())


class TypedArray(list):
    """
    Constrained-length array with typed primitive or structured elements.

    Can be used as fixed-length, or as having mininum and maximum length.

    Adding an element populates the first empty slot, or does nothing if array is full.

    Removing an element within minimum length replaces it with empty value.
    """

    def __init__(self, cls, size, default=None):
        """
        @param   cls       element type, a primitive like str or structured like SlotsDict
        @param   size      number of elements in array, single number for fixed-length array
                           or (min, max) for constrained range
        @param   default   empty element value or constructor
        """
        minmax = tuple(map(int, size if isinstance(size, (list, tuple)) else [size] * 2))[:2]
        super(TypedArray, self).__init__()
        self._cls = cls
        self._minlen = minmax[0]
        self._maxlen = minmax[1]
        self._default = default
        self[:] = [self.new() for _ in range(self._minlen)]

    def append(self, *value, **attributes):
        """
        Populates first empty element in array; does nothing if already full.

        @param   value       element value to set, if not using structured attributes
        @param   attributes  attributes to populate structured element with
        @return              index populated, or None if full
        """
        blank = self.new()
        index = next((i for i, v in enumerate(self) if v == blank), None)
        if index is not None:
            self[index] = self.new(*value, **attributes)
        elif len(self) < self._maxlen:
            list.append(self, self.new(*value, **attributes))
            index = len(self) - 1
        return index

    def clear(self):
        """Populates array with empty values."""
        self[:] = [self.new() for _ in range(self._minlen)]

    def copy(self):
        """Returns a deep copy of this array."""
        return self.spawn(self)

    def extend(self, other):
        """Populates empty elements in array with values from iterable while not full."""
        for value in other:
            if self.append(value) is None:
                break # for value

    def index(self, *value, **attributes):
        """
        Returns index of value; raises ValueError if not present.

        @param   value       value to find, if not using structured attributes
        @param   attributes  attributes to match in structured elements
        """
        if attributes:
            index = next((i for i, x in enumerate(self)
                          if all(getattr(x, k, None) == v for k, v in attributes.items())), None)
            if index is None: raise ValueError("%s is not in list" % attributes)
            return index
        return list.index(self, value[0]) # Raises valueerror

    def insert(self, index, *value, **attributes):
        """Inserts value before index, drops last array element if overflow."""
        index = max(0, min(index, len(self) - 1))
        list.insert(self, index, self.new(*value, **attributes))
        if len(self) > self._maxlen: list.__delitem__(self, -1)

    def pop(self, index=None):
        """
        Removes and returns item at index, by default last; raises IndexError if out of range.

        If index within minimum required length, populates index with a new empty element.
        """
        if not self: raise IndexError("pop from empty list")
        if index is None: index = len(self) - 1
        if index < 0: index += len(self)
        if index < 0 or index > len(self) - 1:
            raise IndexError("list index out of range")

        if len(self) > self._minlen: value = list.pop(self, index)
        else: value, self[index] = self[index], self.new()
        return value

    def remove(self, *value, **attributes):
        """
        Removes first occurrence of value; raises ValueError if not present.

        If index within minimum required length, populates index with a new empty element.
        """
        if attributes:
            index = next((i for i, x in enumerate(self)
                          if all(getattr(x, k, None) == v for k, v in attributes.items())), None)
            if index is None: raise ValueError("%s is not in list" % attributes)
        else:
            index = list.index(self, value[0]) # Raises ValueError
        self.pop(index)

    def spawn(self, other=(), size=None):
        """
        Returns new array of same type, with values from iterable if any.

        @param   size  override new array length or range
        """
        result = type(self)()
        if size is None: size = (self._minlen, self._maxlen)
        elif isinstance(size, int): size = (size, size)
        result._minlen, result._maxlen = size
        list.__delitem__(result, slice(None))
        result[:] = [result.new() for _ in range(result._minlen)]
        for i, v in enumerate(other):
            if i >= result._maxlen: break # for i, v
            if i < len(result): list.__setitem__(result, i, self.new(v))
            else: list.append(result, self.new(v))
        return result

    def new(self, *value, **attributes):
        """Returns value for new typed element, or blank value if nothing given."""
        if attributes:
            return self._cls(**attributes)
        blank = self._default() if callable(self._default) else self._default
        if value and value[0] != blank: return self._cls(value[0])
        return blank

    def __add__(self, other):
        """Returns new array with empty elements populated from iterable."""
        return self.spawn(other)

    def __delitem__(self, index):
        """Clears element value at index or slice."""
        if isinstance(index, slice):
            self.__setitem__(index, (self.new() for _ in range(self._maxlen)))
        else:
            if len(self) > self._minlen:
                list.__delitem__(self, index)
            else:
                list.__setitem__(self, index, self.new())

    def __getitem__(self, y):
        """Returns element at given position or slice in given range."""
        if isinstance(y, slice):
            other = list.__getitem__(self, y)
            #result = self.spawn(size=(min(self._minlen, len(other)), self._maxlen))
            result = self.spawn(other, size=(min(self._minlen, len(other)), self._maxlen))
            #for value in other: list.append(result, value)
            return result
        else:
            return list.__getitem__(self, y) 

    def __iadd__(self, other):
        """Populates empty elements in array with values from iterable, returns self."""
        self.extend(other)
        return self

    def __imul__(self, value):
        """Returns self multiplied N times (effectively no-op unless N<=0 which clears array)."""
        if not isinstance(value, int):
            raise TypeError("can't multiply sequence by non-int of type %r" % type(value))
        if value <= 0: self.clear()
        return self

    def __mul__(self, value):
        """Returns new array of this multiplied N times (copy unless N<=0 which gives empty array)."""
        if not isinstance(value, int):
            raise TypeError("can't multiply sequence by non-int of type %r" % type(value))
        return self.spawn() if value <= 0 else self.copy()

    def __ne__(self, other):
        """Returns whether this array equals other: same elements in same order."""
        return not (self == other)

    def __setitem__(self, index, value):
        """Replaces value at index or slice; discards overflow from array end."""
        if isinstance(index, slice):
            slice_values = []
            for v in value:
                slice_values.append(self.new(v))
                if len(slice_values) >= self._maxlen: break # for v
            list.__setitem__(self, index, slice_values)
            if len(self) > self._maxlen:
                list.__delitem__(self, slice(self._maxlen - len(self), None))
            elif len(self) < self._minlen:
                for _ in range(self._minlen - len(self)): list.append(self, self.new())
        else:
            list.__setitem__(self, index, self.new(value))

    # Py2
    def __getslice__(self, i, j):      return self.__getitem__(slice(i, j))
    def __setslice__(self, i, j, seq): return self.__setitem__(slice(i, j), seq)
    def __delslice__(self, i, j):      return self.__delitem__(slice(i, j))


class csv_writer(object):
    """Convenience wrapper for csv.Writer, with Python2/3 compatbility."""

    def __init__(self, file_or_name):
        if isinstance(file_or_name, text_types):
            self._name = file_or_name
            self._file = open(self._name, "wb") if sys.version_info < (3, ) else \
                         codecs.open(self._name, "w", "utf-8")
        else:
            self._name = None
            self._file = file_or_name
        # csv.excel.delimiter default "," is not actually used by Excel.
        self._writer = csv.writer(self._file, csv.excel, delimiter=";")

    def __enter__(self):
        """Context manager entry, does nothing, returns self."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager exit, closes file."""
        self.close()

    def writerow(self, sequence=()):
        """Writes a CSV record from a sequence of fields."""
        REPLS = {"\r\n": "\r\n", "\r": "\r\n", "\n": "\r\n", "\x00": "\\x00", '"': '""', "'": "''"}
        RGX = re.compile("|".join(map(re.escape, REPLS)))
        QRGX = re.compile("|".join(map(re.escape, '",')))
        values = []
        for v in sequence:
            if sys.version_info < (3, ):
                v = to_unicode(v).encode("utf-8", "backslashreplace")
            if isinstance(v, text_types) and RGX.search(v):
                v = RGX.sub(lambda m: REPLS[m.group()], v)
            if isinstance(v, text_types) and QRGX.search(v):
                v = '"%s"' % v
            values.append(v)
        self._writer.writerow(values)

    def close(self):
        """Closes CSV file writer."""
        if self._name: self._file.close()


def add_unique(lst, item, direction=1, maxlen=sys.maxsize):
    """
    Adds the item to the list from start or end. If item is already in list,
    removes it first. If list is longer than maxlen, shortens it.

    @param   direction  side from which item is added, -1/1 for start/end
    @param   maxlen     maximum length list is allowed to grow to before
                        shortened from the other direction
    """
    if item in lst:
        lst.remove(item)
    lst.insert(0, item) if direction < 0 else lst.append(item)
    if len(lst) > maxlen:
        lst[:] = lst[:maxlen] if direction < 0 else lst[-maxlen:]
    return lst


def bytoi(blob):
    """Converts a string of bytes or a bytearray to unsigned integer."""
    fmt = {1: "<B", 2: "<H", 4: "<L", 8: "<Q"}[len(blob)]
    return struct.unpack(fmt, blob)[0]


def canonic_version(v):
    """Returns a numeric version representation: "1.3.2a" to 10301,99885."""
    nums = [int(re.sub(r"[^\d]", "", x)) for x in v.split(".")][::-1]
    nums[0:0] = [0] * (3 - len(nums)) # Zero-pad if version like 1.4 or just 2
    # Like 1.4a: subtract 1 and add fractions to last number to make < 1.4
    if re.findall(r"\d+([\D]+)$", v):
        ords = [ord(x) for x in re.findall(r"\d+([\D]+)$", v)[0]]
        nums[0] += sum(x / (65536. ** (i + 1)) for i, x in enumerate(ords)) - 1
    return sum((x * 100 ** i) for i, x in enumerate(nums))


def format_bytes(size, precision=2, max_units=True, with_units=True):
    """
    Returns a formatted byte size (e.g. "421.45 MB" or "421,451,273 bytes").

    @param   precision   number of decimals to leave after converting to
                         maximum units
    @param   max_units   whether to convert value to corresponding maximum
                         unit, or leave as bytes and add thousand separators
    @param   with_units  whether to include units in result
    """
    size, formatted, unit = int(size), "0", "bytes"
    if size:
        byteunit = "byte" if 1 == size else "bytes"
        if max_units:
            UNITS = [byteunit, "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
            log = min(len(UNITS) - 1, math.floor(math.log(size, 1024)))
            formatted = "%.*f" % (precision, size / math.pow(1024, log))
            formatted = formatted.rstrip("0").rstrip(".")
            unit = UNITS[int(log)]
        else:
            formatted = "".join([x + ("," if i and not i % 3 else "")
                                 for i, x in enumerate(str(size)[::-1])][::-1])
            unit = byteunit
    return formatted + ((" " + unit) if with_units else "")


def format_exc(e):
    """Formats an exception as Class: message, or Class: (arg1, arg2, ..)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore") # DeprecationWarning on e.message
        msg = to_unicode(e.message) if getattr(e, "message", None) \
              else "(%s)" % ", ".join(map(to_unicode, e.args)) if e.args else ""
    result = u"%s%s" % (type(e).__name__, ": " + msg if msg else "")
    return result


def get(collection, *path, **kwargs):
    """
    Returns the value at specified collection path. If path not available,
    returns the first keyword argument if any given, or None.
    Collection can be a nested structure of dicts, lists, tuples or strings.
    E.g. util.get({"root": {"first": [{"k": "v"}]}}, "root", "first", 0, "k").
    Also supports named object attributes.
    """
    default = (list(kwargs.values()) + [None])[0]
    result = collection if path else default
    if len(path) == 1 and isinstance(path[0], list): path = path[0]
    for p in path:
        if isinstance(result, collections_abc.Sequence):  # Iterable with index
            if isinstance(p, int_types) and p < len(result):
                result = result[p]
            else:
                result = default
        elif isinstance(result, collections_abc.Mapping): # Container with lookup
            result = result.get(p, default)

        else:
            result = getattr(result, p, default)
        if result == default: break  # for p
    return result


def itoby(v, length):
    """
    Converts an unsigned integer to a bytearray of specified length.
    """
    fmt = {1: "<B", 2: "<H", 4: "<L", 8: "<Q"}[length]
    return bytearray(struct.pack(fmt, v))


def longpath(path):
    """Returns the path in long Windows form ("Program Files" not PROGRA~1)."""
    result = path
    try:
        buf = ctypes.create_unicode_buffer(65536)
        GetLongPathNameW = ctypes.windll.kernel32.GetLongPathNameW
        if GetLongPathNameW(string_type(path), buf, 65536):
            result = buf.value
        else:
            head, tail = os.path.split(path)
            if GetLongPathNameW(string_type(head), buf, 65536):
                result = os.path.join(buf.value, tail)
    except Exception: pass
    return result


def m(o, name, case_insensitive=True):
    """Returns the members of the object or dict, filtered by name."""
    members = o.keys() if isinstance(o, dict) else dir(o)
    if case_insensitive:
        return [i for i in members if name.lower() in i.lower()]
    else:
        return [i for i in members if name in i]


def make_unique(value, existing, suffix="_%s", counter=2, case=False):
    """
    Returns a unique string, appending suffix % counter as necessary.

    @param   existing  collection of existing strings to check
    @oaram   case      whether uniqueness should be case-sensitive
    """
    result, is_present = value, (lambda: result in existing)
    if not case:
        existing = [x.lower() for x in existing]
        is_present = lambda: result.lower() in existing
    while is_present(): result, counter = value + suffix % counter, counter + 1
    return result


def path_to_url(path):
    """Returns path as file URL, e.g. "/my file" as "file:///my%20file"."""
    return urljoin('file:', pathname2url(path))


def plural(word, items=None, numbers=True, single="1", sep="", pref="", suf=""):
    """
    Returns the word as 'count words', or '1 word' if count is 1,
    or 'words' if count omitted.

    @param   items      item collection or count,
                        or None to get just the plural of the word
             numbers    if False, count is omitted from final result
             single     prefix to use for word if count is 1, e.g. "a"
             sep        thousand-separator to use for count
             pref       prefix to prepend to count, e.g. "~150"
             suf        suffix to append to count, e.g. "150+"
    """
    count   = len(items) if hasattr(items, "__len__") else items or 0
    isupper = word[-1:].isupper()
    suffix = "es" if word and word[-1:].lower() in "oxyz" else "s" if word else ""
    if isupper: suffix = suffix.upper()
    if count != 1 and "y" == word[-1:].lower():
        word = word[:-1] + ("I" if isupper else "i")
    result = word + ("" if 1 == count else suffix)
    if numbers and items is not None:
        fmtcount = single if 1 == count else "".join([
            x + ("," if i and not i % 3 else "")
            for i, x in enumerate(str(count)[::-1])][::-1
        ]) if sep else str(count)
        fmtcount = pref + fmtcount + suf
        result = "%s %s" % (single if 1 == count else fmtcount, result)
    return result.strip()


def select_file(path):
    """
    Tries to open the file directory, and select file if path is a file.
    Falls back to opening directory only (select is Windows-only).
    """
    folder = path if os.path.isdir(path) else os.path.dirname(path)
    if "nt" != os.name or not os.path.exists(path) or path is folder:
        start_file(folder)
        return
    try: subprocess.Popen('explorer /select, "%s"' % shortpath(path))
    except Exception: start_file(folder)


def shortpath(path):
    """Returns the path in short Windows form (PROGRA~1 not "Program Files")."""
    if isinstance(path, str): return path
    from ctypes import wintypes

    ctypes.windll.kernel32.GetShortPathNameW.argtypes = [
        # lpszLongPath, lpszShortPath, cchBuffer
        wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD
    ]
    ctypes.windll.kernel32.GetShortPathNameW.restype = wintypes.DWORD
    buf = ctypes.create_unicode_buffer(4 * len(path))
    ctypes.windll.kernel32.GetShortPathNameW(path, buf, len(buf))
    return buf.value


def start_file(filepath):
    """
    Tries to open the specified file or directory in the operating system.

    @return  (success, error message)
    """
    success, error = True, ""
    try:
        if "nt" == os.name:
            try: os.startfile(filepath)
            except WindowsError as e:
                if 1155 == e.winerror: # ERROR_NO_ASSOCIATION
                    cmd = "Rundll32.exe SHELL32.dll, OpenAs_RunDLL %s"
                    os.popen(cmd % filepath)
                else: raise
        elif "mac" == os.name:
            subprocess.call(("open", filepath))
        elif "posix" == os.name:
            subprocess.call(("xdg-open", filepath))
    except Exception as e:
        success, error = False, format_exc(e)
    return success, error


def timedelta_seconds(timedelta):
    """Returns the total timedelta duration in seconds."""
    if hasattr(timedelta, "total_seconds"):
        result = timedelta.total_seconds()
    else: # Python 2.6 compatibility
        result = timedelta.days * 24 * 3600 + timedelta.seconds + \
                 timedelta.microseconds / 1000000.
    return result


def to_unicode(value, encoding=None):
    """
    Returns the value as a Unicode string. Tries decoding as UTF-8 if
    locale encoding fails.
    """
    result = value
    if not isinstance(value, string_type):
        encoding = encoding or locale.getpreferredencoding()
        if isinstance(value, bytearray): value = bytes(value)
        if isinstance(value, bytes):
            try:
                result = string_type(value, encoding)
            except Exception:
                result = string_type(value, "utf-8", errors="replace")
        else:
            result = str(value)
            if not isinstance(result, string_type):
                result = string_type(result, errors="replace")
    return result


def tuplefy(value):
    """Returns the value as a tuple if list/set/tuple else as a tuple of one."""
    return value if isinstance(value, tuple) \
           else tuple(value) if isinstance(value, (list, set)) else (value, )


def unique_path(pathname, suffix="%(ext)s_%(counter)s"):
    """
    Returns a unique version of the path. If a file or directory with the
    same name already exists, returns a unique version
    (e.g. "C:\config.sys_2" if ""C:\config.sys" already exists).

    @param   suffix  string to append, formatted with variables counter, ext
    """
    result = pathname
    if "linux" in sys.platform and isinstance(result, string_type) \
    and "utf-8" != sys.getfilesystemencoding():
        result = result.encode("utf-8") # Linux has trouble if locale not UTF-8
    path, name = os.path.split(result)
    base, ext = os.path.splitext(name)
    if len(name) > 255: # Filesystem limitation
        name = base[:255 - len(ext) - 2] + ".." + ext
        result = os.path.join(path, name)
    counter = 2
    while os.path.exists(result):
        mysuffix = suffix % {"ext": ext, "counter": counter}
        name = base + mysuffix
        if len(name) > 255:
            name = base[:255 - len(mysuffix) - 2] + ".." + mysuffix
        result = os.path.join(path, name)
        counter += 1
    return result


def win32_unicode_argv():
    """
    Returns Windows command-line arguments converted to Unicode.

    @from    http://stackoverflow.com/a/846931/145400
    """
    result = sys.argv[:]
    try:
        from ctypes import POINTER, byref, cdll, c_int, windll
        from ctypes.wintypes import LPCWSTR, LPWSTR
    except Exception: return result

    GetCommandLineW = cdll.kernel32.GetCommandLineW
    GetCommandLineW.argtypes = []
    GetCommandLineW.restype = LPCWSTR

    CommandLineToArgvW = windll.shell32.CommandLineToArgvW
    CommandLineToArgvW.argtypes = [LPCWSTR, POINTER(c_int)]
    CommandLineToArgvW.restype = POINTER(LPWSTR)

    argc = c_int(0)
    argv = CommandLineToArgvW(GetCommandLineW(), byref(argc))
    if argc.value:
        # Remove Python executable and commands if present
        start = argc.value - len(sys.argv)
        result = [argv[i] for i in range(start, argc.value)]
        #result = [argv[i].encode("utf-8") for i in range(start, argc.value)]
    return result
