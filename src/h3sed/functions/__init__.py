"""
User-defined plugins functionality.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     12.03.2026
@modified    20.03.2026
------------------------------------------------------------------------------
"""
import glob
import inspect
import io
import logging
import os
import sys
import types

import h3sed
from . import show_combination_artifacts


logger = logging.getLogger(__name__)


KEYS = ("title", "body", "name", "active", "target", "__builtin__")

## [{"body", "title", ?"name", ?"target", ?"active", ?"__builtin__"}]
FUNCTIONS = []

## {id: {"body", "title", ?"name", ?"target"}}
BUILTINS = {}

## Default namespace for compiled functions
NAMESPACE = {}


def init_functions(functions, namespace=None, directory=None):
    """
    Initializes plugins from configuration, compiling their code and validating namespace.

    @param   functions  configuration as [{?"body", ?"title", ?"name", ?"active", ?"__builtin__"}]
    @param   namespace  globals() dictionary used for compiled function eval
    @param   directory  path to user functions directory if not using current
    """
    NAMESPACE.clear()
    NAMESPACE.update(namespace or {})
    load_builtins(directory)
    set_functions(functions, make_targets=True)
    ids_present = set(x["__builtin__"] for x in FUNCTIONS if x.get("__builtin__"))
    addables = [dict(x, __builtin__=k) for k, x in BUILTINS.items() if k not in ids_present]
    FUNCTIONS[:0] = sorted(addables, key=lambda k: BUILTINS[k["__builtin__"]]["title"].lower())


def get_functions():
    """
    Returns a list of initialized functions
    as [{"body", ?"title", ?"name", ?"target", ?"active", ?"__builtin__"}].
    """
    return [dict(x) for x in FUNCTIONS]


def set_functions(functions, make_targets=False):
    """
    Sets functions content, as [{"body", "title", ?"name", ?"target", ?"active", ?"__builtin__"}].
    """
    del FUNCTIONS[:]
    for entry in functions:
        if not entry.get("title") and not entry.get("__builtin__"):
            continue # for entry

        entry = {k: entry[k] for k in entry if k in KEYS}
        needs_target = make_targets
        if entry.get("__builtin__") in BUILTINS:
            for k, v in BUILTINS[entry["__builtin__"]].items():
                entry.setdefault(k, v)
            needs_target = not has_same_text(BUILTINS[entry["__builtin__"]], entry, "body")
        else:
            entry.pop("__builtin__", None)
            entry.setdefault("body", "")
            if needs_target and not callable(entry.get("target")):
                make_target(entry)
        FUNCTIONS.append(entry)


def validate_function(function, **kwargs):
    """Returns whether function is a plain callable, invocable with some given arguments or none."""
    if not isinstance(function, types.FunctionType):
        return False # Allow only plain callables
    if not kwargs:
        return True # Nothing to validate

    PY3 = sys.version_info > (3, )
    argspec = (inspect.getfullargspec if PY3 else inspect.getargspec)(function)
    named_args = list(argspec.args) + (argspec.kwonlyargs if PY3 else [])
    if not named_args:
        return True # Needs no arguments at all

    arg_defaults = dict(zip(argspec.args, argspec.defaults or []))
    if PY3: arg_defaults.update(argspec.kwonlydefaults or {})
    for name in named_args:
        if name not in kwargs and name not in arg_defaults:
            return False # Needs mandatory argument not in given keywords
    return True


def execute_function(function, **kwargs):
    """Executes given function, with arguments supported by name, returns function result."""
    PY3 = sys.version_info > (3, )
    argspec = (inspect.getfullargspec if PY3 else inspect.getargspec)(function)
    named_args = list(argspec.args) + (argspec.kwonlyargs if PY3 else [])
    has_varkw = bool(getattr(argspec, "varkw" if PY3 else "keywords", None))
    myargs = kwargs if has_varkw else {k: kwargs[k] for k in kwargs if k in named_args}
    return function(**myargs)


def get_config():
    """
    Returns functions configuration suitable for init_functions() and serialization.

    Minimizes built-in function inclusion, returning only the parts where settings have changed.
    """
    opts = [{k: v for k, v in entry.items() if not callable(v)} for entry in FUNCTIONS]
    for entry in opts: entry.get("active") and entry.pop("active") # Discard default setting

    # See if built-ins can be discarded from config as having all defaults
    expected_order = sorted(BUILTINS, key=lambda k: BUILTINS[k]["title"].lower())
    current_order = [x.get("__builtin__") for x in FUNCTIONS]
    if expected_order == current_order[:len(expected_order)]: # Same order: check if same insides
        is_changed = lambda a, b: b.get("active") is False or \
                                  any(not has_same_text(a, b, k) for k in ["body", "title", "name"])
        if not any(is_changed(BUILTINS[x["__builtin__"]], x) for x in opts if x.get("__builtin__")):
            opts = [x for x in opts if not x.get("__builtin__")]

    for entry in (x for x in opts if x.get("__builtin__")):
        for k in ("title", "body", "name"):
            if has_same_text(BUILTINS[entry["__builtin__"]], entry, k):
                entry.pop(k) # Do not store unchanged body and other props for built-ins

    return opts


def compile_code(text):
    """
    Compiles and evaluates a Python code string.

    @param   text  Python code as text
    @return        (resulting eval namespace, None) or (None, error message)
    """
    result, err = {}, None
    try: eval(compile(text, "", "exec"), dict(NAMESPACE), result)
    except Exception as e: result, err = None, str(e)
    return result, err


def get_source(qualname, path):
    """Returns source code of given Python module at path, or empty string on failure."""
    source = ""
    try: source = inspect.getsource(qualname)
    except Exception:
        try:
            with io.open(path, encoding="utf-8") as f:
                source = f.read()
        except Exception:
            logger.exception("Error loading function module %r.", path)
    return source


def has_same_text(entry1, entry2, key):
    """Returns whether entries have the same key value, ignoring OS-specific line separators."""
    a, b = ("" if x.get(key) is None else x[key] for x in (entry1, entry2))
    a, b = (x if hasattr(x, "splitlines") else str(x) for x in (a, b))
    return a.splitlines() == b.splitlines()


def load_builtins(directory=None):
    """Loads all Python source files in module directory as built-in functions."""
    basefile = os.path.realpath(__file__)
    basedir = directory or os.path.dirname(basefile)
    for path in glob.glob(os.path.join(basedir, "*.py")):
        if not os.path.isfile(path) or os.path.basename(path).startswith("__"):
            continue # for path

        ident = os.path.splitext(os.path.basename(path))[0]
        if ident in BUILTINS and BUILTINS[ident].get("body"): continue # for f

        body = get_source("%s.%s" % (__package__, ident), path)
        if ident in BUILTINS:
            BUILTINS[ident].setdefault("body", body)
            continue # for path

        entry = {"__builtin__": ident, "body": body, "title": ident.replace("_", " ").capitalize()}
        make_target(entry)
        BUILTINS[ident] = entry


def make_target(entry):
    """Compiles item code, updates item with name and target on success, logs error."""
    name = entry.get("name") or entry.get("__builtin__")
    ns, err = compile_code(entry["body"])
    if err:
        logger.warning("Error compiling function %r: %s", name or entry["title"], err)
        return
    if validate_function(ns.get(name)): candidate = name
    else: candidate = next((k for k, v in ns.items() if validate_function(v)), None)
    if validate_function(ns.get(candidate)):
        entry.update(name=candidate, target=ns[candidate])
