# -*- coding: utf-8 -*-
"""
Internationalization support, uses gettext-based translation files (.po and .mo).

Translations by default are case-sensitive, with case-insensitve fallback,
finally with fuzzy match fallback (without normalization characters).

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     23.03.2026
@modified    12.05.2026
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


## {language code: {"code", "name", ?"path", ?"data", ?"auto", ?"extra", ?"normal"}}
LANGUAGES = {"en": {"code": "en", "name": "English"}}

## Supported translation file formats, as {dotless format suffix: format label}
FORMATS = {"mo": "Machine Object translation file", "po": "Portable Object translation file"}

## Directory-loaded translations, as {language code: {"code", "name", "path", "data", "normal"}}
AUTOLOADED = {}

NORMALIZE = "&"
DEFAULTLANG = "en"
DEFAULTNAME = "English"
CURRENTLANG = "en"


def init(directory=None, config=None, normalize="&"):
    """
    Initializes translation

    @param   directory  path where to seek translation files
    @param   config     additional configuration as {language code: {path, ?name}}
    @param   normalize  characters to strip when falling back to fuzzy match
    """
    global NORMALIZE
    NORMALIZE = normalize or ""
    
    for path in glob.glob(os.path.join(directory, "*")) if directory else ():
        if not os.path.isfile(path) or not os.path.getsize(path) \
        or not path.lower().endswith(tuple(".%s" % x for x in FORMATS)):
            continue # for path
        opts, err = read_translation(path)
        if opts:
            lang = opts["code"]
            AUTOLOADED[lang] = opts
            LANGUAGES[lang] = dict(opts, auto=True)

    for lang, opts in config.items() if config else ():
        if not opts.get("path") and opts.get("name") and lang in LANGUAGES:
            LANGUAGES[lang].update(name=opts["name"], extra=True) # Allow adding name for language
            continue # for lang
        if not os.path.isfile(opts.get("path") or ""):
            logger.warning("Nonexistent translation file for language %r: %s.", lang, opts)
            continue # for lang
        add_translation(opts["path"], name=opts.get("name"))


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


def add_translation(filepath, name=None):
    """Adds a language from translation file, returns (language options, None) or (None, error)."""
    opts, err = read_translation(filepath)
    if err: return (None, err)
    if name: opts["name"] = name
    lang = opts["code"]
    if lang in LANGUAGES and lang == opts["name"]:
        opts["name"] = LANGUAGES[lang]["name"] # Hopefully the existing name is more than just code

    if lang in AUTOLOADED:
        opts["data"] = dict(AUTOLOADED[lang]["data"], **opts["data"]) # Override auto with new
        for textkey, texts in AUTOLOADED[lang]["normal"].items():
            opts["normal"].setdefault(textkey, set()).update(texts)
    LANGUAGES.setdefault(lang, {}).update(opts, extra=True)
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
    Returns text translated to current language, or given text if no translation available.

    Optionally formatted with positional and keyword arguments.
    """
    return translate_from_context(2, text, *args, **kwargs)


def translate_back(text):
    """Returns original text for given translation in current language, or given text if no match."""
    if not isinstance(text, str): return text
    lang = CURRENTLANG
    if lang not in LANGUAGES or not LANGUAGES[lang].get("data"): return text

    has_entry = lambda entries, text, conv=None: any(text == (t if conv is None else conv(t))
                                                     for t, _, _ in entries)
    results = [k for k, v in LANGUAGES[lang]["data"].items() if has_entry(v, text)]
    if not results:
        ltext = text.lower()
        results = [k for k, v in LANGUAGES[lang]["data"].items() if has_entry(v, ltext, str.lower)]
    return min(results, default=text, key=lambda x: abs(len(x) - len(text))) # Closest-length match


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
    if len(entries) > 1 and any(f for t, f, n in entries):
        filename, line = get_calling_stack(stack_depth)
        entries2 = [e for e in entries if e[1] == filename]
        if entries2: # Narrow to closest line number in source file
            entries = sorted(entries2, key=lambda e: abs(line - e[2]))
    return format_text(entries[0][0], *args, **kwargs)


def get_entries(lang, text):
    """Returns translations matching text, as [(translation, filename, line number)] if any."""
    if not isinstance(text, str): return []
    OPTS = LANGUAGES.get(lang) or {}
    if not OPTS.get("data"): return []

    if text in OPTS["data"]:
        return OPTS["data"][text][:] # Perfect case-sensitive match

    matchkey = text.translate({ord(c): "" for c in NORMALIZE}).lower()
    textkeys = OPTS["normal"].get(matchkey) or ([matchkey] if matchkey in OPTS["data"] else [])
    if not textkeys: return []

    closest_len = min(map(len, textkeys), key=lambda x: abs(x - len(text)))
    textkeys = [x for x in textkeys if len(x) == closest_len]
    strip = lambda x: x
    if len(textkeys[0]) != len(text):
        strip = lambda x: x.translate({ord(c): "" for c in NORMALIZE})
    CASE_TRANSFORMERS = (str.lower, str.capitalize, str.title, str.upper)
    transform = next((f for f in CASE_TRANSFORMERS if f(strip(text)) == strip(text)), lambda x: x)
    return [(transform(strip(t)), f, n) for k in textkeys for t, f, n in OPTS["data"][k]]


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


def format_nested(text, *args, do_translate=False):
    """
    Returns text formatted with positional % arguments, arguments processed recursively
    for nested (text, *args), all texts and arguments optionally translated.
    """
    args2 = []
    for arg in args:
        if isinstance(arg, (list, tuple)) and len(arg) > 1 and isinstance(arg[0], str):
            subargs = arg[1] if isinstance(arg[1], (list, tuple)) else arg[1:]
            arg = format_nested(arg[0], *subargs, do_translate=do_translate)
        elif do_translate: arg = translate_from_context(2, arg)
        args2.append(arg)
    if do_translate: return translate_from_context(2, text, *args2)
    return format_text(text, *args2)


def make_normalized(texts):
    """Returns normalized texts mapped to originals, as {normalized: set([text, ])}."""
    result = {}
    for text in texts:
        textkey = text.translate({ord(c): "" for c in NORMALIZE}).lower()
        if text != textkey:
            result.setdefault(textkey, set()).add(text)
    return result


def read_translation(filepath):
    """
    Parses and returns translation file contents and metadata.

    @return  (result, None) or (None, error string), where result is
             {"code", "name", "path", "data": {text: [(translation, filename, line)],
              "normal": {normalized text: set([original text, ])}}
    """
    ctor = polib.mofile if filepath.lower().endswith(".mo") else polib.pofile
    try: langfile = ctor(filepath)
    except Exception as e:
        logger.exception("Error in translation file %s.", filepath)
        return (None, str(e))

    lang = langfile.metadata.get("Language")
    if not lang: # Detect from filename like myfile.pl.po
        parts = os.path.basename(filepath).rsplit(".", 2)
        if len(parts) > 1: lang = parts[-2]
    if not lang:
        logger.warning("Error in translation file %s: no language information.", filepath)
        del langfile # Mandatory for polib to close the file handle
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
    del langfile # Mandatory for polib to close the file handle
    if not data:
        return (None, "No translations in file")

    logger.info("Read %r %s %s (%s entries).", filepath, lang, name, sum(map(len, data.values())))
    normaled = make_normalized(data)
    return ({"code": lang, "name": name, "path": filepath, "data": data, "normal": normaled}, None)
