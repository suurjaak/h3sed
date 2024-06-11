# -*- coding: utf-8 -*-
"""
Miscellaneous utility functions.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     19.11.2011
@modified    11.06.2024
------------------------------------------------------------------------------
"""
import collections
import codecs
import csv
import ctypes
import datetime
import locale
import math
import os
import re
import subprocess
import sys
import struct
import time
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


def m(o, name, case_insensitive=True):
    """Returns the members of the object or dict, filtered by name."""
    members = o.keys() if isinstance(o, dict) else dir(o)
    if case_insensitive:
        return [i for i in members if name.lower() in i.lower()]
    else:
        return [i for i in members if name in i]


def bytoi(blob):
    """Converts a string of bytes or a bytearray to unsigned integer."""
    fmt = {1: "<B", 2: "<H", 4: "<L", 8: "<Q"}[len(blob)]
    return struct.unpack(fmt, blob)[0]


def itoby(v, length):
    """
    Converts an unsigned integer to a bytearray of specified length.
    """
    fmt = {1: "<B", 2: "<H", 4: "<L", 8: "<Q"}[length]
    return bytearray(struct.pack(fmt, v))


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


def select_file(filepath):
    """
    Tries to open the file directory and select file.
    Falls back to opening directory only (select is Windows-only).
    """
    if not os.path.exists(filepath):
        return start_file(os.path.split(filepath)[0])
    try: subprocess.Popen('explorer /select, "%s"' % shortpath(filepath))
    except Exception: start_file(os.path.split(filepath)[0])


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


def path_to_url(path):
    """Returns path as file URL, e.g. "/my file" as "file:///my%20file"."""
    return urljoin('file:', pathname2url(path))


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
