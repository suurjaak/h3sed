h3sed
=====

h3sed is a Heroes3 Savegame Editor, written in Python.

It can open savegame files from Heroes of Might and Magic III
(supported game versions: Shadow of Death and Horn of the Abyss),
and edit any and all hero attributes: primary skills, secondary skills,
spells, war machines, artifacts, armies etc.

Downloads at http://suurjaak.github.io/h3sed.


Installation
------------

Windows: download and launch the latest setup from
https://suurjaak.github.io/h3sed/downloads.html.

Mac/Linux/other: install Python and pip, run `pip install h3sed`.

The pip installation will add the `h3sed` command to path.

Windows installers have been provided for convenience. The program itself 
is stand-alone, can work from any directory, and does not need additional
installation. The installed program can be copied to a USB stick and used
elsewhere, same goes for the source code.

If running from pip installation, run `h3sed` from the command-line. 
If running straight from source code, launch `h3sed.sh` where shell 
scripts are supported, or `h3sed.bat` under Windows, or open 
a terminal and run `python -m h3sed.main` in h3sed directory.


Source Dependencies
-------------------

If running from source code, h3sed needs Python 2.7 or Python 3,
and the following 3rd-party Python packages:
* wxPython 4.0+ (https://wxpython.org)


Attribution
-----------

Includes a modified version of step, Simple Template Engine for Python,
(c) 2012, Daniele Mazzocchio, https://github.com/dotpy/step.

Contains several icons from Heroes of Might and Magic III, (c) 1999 3DO.

Binaries compiled with PyInstaller, https://www.pyinstaller.org.

Installers created with Nullsoft Scriptable Install System,
https://nsis.sourceforge.net/.


License
-------

Copyright (c) 2020 by Erki Suurjaak.
Released as free open source software under the MIT License,
see [LICENSE.md](LICENSE.md) for full license text.
