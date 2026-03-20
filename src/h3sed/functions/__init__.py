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


KEYS = ("title", "body", "name", "active", "target")

## [{"body", "title", ?"name", ?"target", ?"active"}]
FUNCTIONS = []

## Default namespace for compiled functions
NAMESPACE = {}


def init_functions(functions, namespace=None, directory=None):
    """
    Initializes plugins from configuration, compiling their code and validating namespace.

    @param   functions  configuration as [{?"body", ?"title", ?"name", ?"active"}]
    @param   namespace  globals() dictionary used for compiled function eval
    @param   directory  path to user functions directory if not using current
    """
    NAMESPACE.clear()
    NAMESPACE.update(namespace or {})
    set_functions(functions, make_targets=True)


def get_functions():
    """
    Returns a list of initialized functions
    as [{"body", ?"title", ?"name", ?"target", ?"active"}].
    """
    return [dict(x) for x in FUNCTIONS]


def set_functions(functions, make_targets=False):
    """
    Sets functions content, as [{"body", "title", ?"name", ?"target", ?"active"}].
    """
    del FUNCTIONS[:]
    for entry in functions:
        if not entry.get("title"):
            continue # for entry

        entry = {k: entry[k] for k in entry if k in KEYS}
        entry.setdefault("body", "")
        if make_targets and not callable(entry.get("target")):
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
    """
    opts = [{k: v for k, v in entry.items() if not callable(v)} for entry in FUNCTIONS]
    for entry in opts: entry.get("active") and entry.pop("active") # Discard default setting
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


def has_same_text(entry1, entry2, key):
    """Returns whether entries have the same key value, ignoring OS-specific line separators."""
    a, b = ("" if x.get(key) is None else x[key] for x in (entry1, entry2))
    a, b = (x if hasattr(x, "splitlines") else str(x) for x in (a, b))
    return a.splitlines() == b.splitlines()


def make_target(entry):
    """Compiles item code, updates item with name and target on success, logs error."""
    name = entry.get("name")
    ns, err = compile_code(entry["body"])
    if err:
        logger.warning("Error compiling function %r: %s", name or entry["title"], err)
        return
    if validate_function(ns.get(name)): candidate = name
    else: candidate = next((k for k, v in ns.items() if validate_function(v)), None)
    if validate_function(ns.get(candidate)):
        entry.update(name=candidate, target=ns[candidate])
