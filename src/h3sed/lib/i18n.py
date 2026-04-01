# -*- coding: utf-8 -*-
"""
Internationalization support, uses gettext-based translation files (.po and .mo).

Translations by default are case-sensitive, with case-insensitve fallback.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     23.03.2026
@modified    01.04.2026
------------------------------------------------------------------------------
"""
import functools
import glob
import inspect
import logging
import os
import re

import polib


logger = logging.getLogger(__name__)


## {language code: {"code", "name", ?"path", ?"data", ?"auto", ?"extra", ?"lower"}}
LANGUAGES = {"en": {"code": "en", "name": "English"}}

## Supported translation file formats, as {dotless format suffix: format label}
FORMATS = {"mo": "Machine Object translation file", "po": "Portable Object translation file"}

## Directory-loaded translations, as {language code: {"code", "name", "path", "data", "lower"}}
AUTOLOADED = {}

DEFAULTLANG = "en"
DEFAULTNAME = "English"
CURRENTLANG = "en"


def init(directory, config=None):
    """
    Initializes translation

    @param   directory  path where to seek translation files
    @param   config     additional configuration as {language code: {path, ?name}}
    """
    for path in glob.glob(os.path.join(directory, "*")):
        if not os.path.isfile(path) or not os.path.getsize(path) \
        or not path.lower().endswith(tuple(".%s" % x for x in FORMATS)):
            continue # for path
        opts, err = read_translation(path)
        if opts:
            lang = opts["code"]
            AUTOLOADED[lang] = opts
            LANGUAGES[lang] = dict(opts, auto=True)

    for lang, opts in config.items() if config else ():
        myopts = {"name": opts["name"]} if opts.get("name") else {}
        if not opts.get("path") and myopts and lang in LANGUAGES:
            LANGUAGES[lang].update(myopts, extra=True)
            continue # for lang
        if not os.path.isfile(opts.get("path") or ""):
            logger.warning("Nonexistent translation file for language %r: %s.", lang, opts)
            continue # for lang
        opts, err = read_translation(opts["path"])
        if opts:
            lang = opts["code"]
            LANGUAGES.setdefault(lang, {}).update(opts, extra=True)


def get_current_language():
    """Returns current translation language."""
    return CURRENTLANG


def set_current_language(lang):
    """Sets current translation language."""
    global CURRENTLANG
    if lang in LANGUAGES:
        CURRENTLANG = lang


def get_language(lang):
    """Returns language options, as {"name", ?"path", ?"extra", ..}."""
    return dict(LANGUAGES[lang]) if lang in LANGUAGES else None


def get_all_languages():
    """Returns current configured languages, as {language code: {"name", ?"path", ?"extra", ..}}."""
    return {lang: dict(opts) for lang, opts in LANGUAGES.items()}


def add_translation(filepath):
    """Adds a language from translation file, returns (language options, None) or (None, error)."""
    opts, err = read_translation(filepath)
    if err: return (None, err)
    lang = opts["code"]
    if lang in LANGUAGES and lang == opts["name"]:
        opts["name"] = LANGUAGES[lang]["name"] # Hopefully the existing name is more than just code

    LANGUAGES.setdefault(lang, {}).update(opts, extra=True)
    if lang in AUTOLOADED:
        for key in ("data", "lower"): # Retain auto-loaded base texts
            LANGUAGES[lang][key] = dict(AUTOLOADED[lang][key], **opts[key])
    return (dict(LANGUAGES[lang]), None)


def drop_language(lang):
    """Drops an added translation language."""
    opts = LANGUAGES.get(lang, {})
    if not opts.get("extra"): return

    if lang in AUTOLOADED:
        LANGUAGES[lang] = dict(AUTOLOADED[lang], auto=True)
    else:
        if lang == DEFAULTLANG:
            LANGUAGES[lang] = {"code": lang, "name": DEFAULTNAME}
        else: LANGUAGES.pop(lang)
        if lang == CURRENTLANG: set_current_language(DEFAULTLANG)


def get_config():
    """
    Returns configuration suitable for init_translations and serialization.
    
    Excludes configuration loaded from additional paths.
    """
    result = {}
    for lang, opts in LANGUAGES.items():
        if opts.get("extra"):
            result[lang] = {"name": opts["name"], "path": opts["path"]}
    return result


def translate(text, *args, **kwargs):
    """
    Returns text translated to current language, or original text if no translation available.

    Optionally formatted with positional and keyword arguments.
    """
    return translate_from_context(2, text, *args, **kwargs)


def make_translate(stack_depth):
    """Returns translate-function for file name and line context at given stack depth."""
    return functools.partial(translate_from_context, stack_depth) # 2 to skip this and partial()


def translate_from_context(stack_depth, text, *args, **kwargs):
    """
    Returns text translated to current language, with translation entry closest to calling context.

    Optionally formatted with positional and keyword arguments.
    """
    entries = get_entries(CURRENTLANG, text) # [(translation, filename, line number)]
    if not entries:
        return format_text(text, *args, **kwargs)
    if len(entries) > 1:
        filename, line = get_calling_stack(stack_depth)
        entries2 = [e for e in entries if e[1] == filename]
        if entries2: # Narrow to closest line number in source file
            entries = sorted(entries2, key=lambda e: abs(line - e[2]))
    return format_text(entries[0][0], *args, **kwargs)


def get_entries(lang, text):
    """Returns translations matching text, as [(translation, filename, line number)] if any."""
    if lang not in LANGUAGES or not LANGUAGES[lang].get("data"): return []
    if text in LANGUAGES[lang]["data"]: return LANGUAGES[lang]["data"][text]

    lowertext = text.lower() if hasattr(text, "lower") else text
    textkey = LANGUAGES[lang]["lower"].get(lowertext, lowertext) # Case-insensitive match
    if textkey in LANGUAGES[lang]["data"]:
        xform = str.lower
        if text != lowertext:
            CASE_TRANSFORMERS = (str.upper, str.title, str.capitalize)
            xform = next((f for f in CASE_TRANSFORMERS if f(text) == text), xform)
        return [(xform(t), f, n) for t, f, n in LANGUAGES[lang]["data"][textkey]]
    return []


def get_calling_stack(depth=1):
    """Returns (filename, line number) for calling stack at given depth."""
    filename, line = None, None
    frame = inspect.currentframe()
    try:
        for _ in range(depth + 1):
            frame = frame.f_back
            if frame is None: break
        if frame:
            filename, line = frame.f_code.co_filename, frame.f_lineno
            relname = "%s.py" % os.path.join(*__name__.split(".")[1:]) # submodule/submodule/mymodule.py
            prefix = re.sub("%s$" % re.escape(relname), "", __file__)
            filename = filename[len(prefix):].lstrip("\\/") # Retain only package-relative path
    finally:
        del frame # Required to avoid inspection reference cycle problems
    return (filename, line)


def format_text(text, *args, **kwargs):
    """Returns text formatted with positional/keyword arguments, % or {}-style."""
    result = text
    if not args and not kwargs: return result

    for fmter in [lambda x: x % (tuple(args) if args else kwargs), 
                  lambda x: x.format(*args, **kwargs)]:
        try:   result = fmter(result) # Try both printf-style % and format-style {}
        except (KeyError, IndexError, TypeError, ValueError): pass
        else:   break # for fmter
    return result


def read_translation(filepath):
    """
    Parses and returns translation file contents and metadata.

    @return  ({"code", "name", "path", "data": {text: [(translation, filename, line)]}}, None)
             or (None, error)
    """
    ctor = polib.mofile if filepath.lower().endswith(".mo") else polib.pofile
    try: langfile = ctor(filepath)
    except Exception as e:
        logger.exception("Error in translation file %s.", filepath)
        return (None, str(e))

    lang = langfile.metadata.get("Language")
    if not lang: # Detect from filename like myfile.en.po
        parts = os.path.basename(filepath).rsplit(".", 2)
        if len(parts) > 1: lang = parts[-2]
    if not lang:
        logger.warning("Error in translation file %s: no language information.", filepath)
        del langfile
        return (None, "No language information in file")

    data = {}
    to_os = lambda x: os.sep.join(re.split(r"[\\/]", x)) # To OS-specific separators
    to_int = lambda x: int(x) if x.isdigit() else 0 # Line numbers to integer
    name = langfile.metadata.get("Language-Name") or lang
    for entry in langfile:
        if not entry.msgstr: continue # for entry
        records = [(entry.msgstr, to_os(fname), to_int(line)) for fname, line in entry.occurrences]
        if not records: records = [(entry.msgstr, None, 0)]
        data.setdefault(entry.msgid, []).extend(records)
    lowers = {ltext: text for text in data for ltext in [text.lower()] if text != ltext}
    del langfile
    if not data:
        return (None, "No translations in file")

    logger.info("Read %r %s %s", filepath, lang, name)
    return ({"code": lang, "name": name, "path": filepath, "data": data, "lower": lowers}, None)
