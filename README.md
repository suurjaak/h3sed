h3sed
=====

h3sed is a Heroes3 Savegame Editor, written in Python.

It opens savegame files from Heroes of Might and Magic III,
allowing to see an overview of all heroes, and edit any and all hero attributes:

- primary skills, like Attack
- other primary attributes, like level, experience points, spell points etc
- war machines, like Ballista
- secondary skills, like Logistics (more than 8 skills can be added)
- artifacts, like Boots of Speed, both worn and inventory items
- spells, like Slow
- army creatures, like Golden Dragons

Attributes can be copied from one hero and pasted to another.

Hero data can be exported as HTML or spreadsheet.

Supports savegames from: Restoration of Erathia, Armageddon's Blade, Shadow of Death,
Heroes Chronicles, and Horn of the Abyss.

Downloads at https://suurjaak.github.io/h3sed.


Usage
-----

Navigate the file view to Heroes3 games-folder and open a savegame file to edit,
or drag and drop a savegame file onto the program window.

Choose a hero to modify, change attributes to your liking, and save the file.
Changes will be available in Heroes3 after loading the changed savegame.

Attributes from one hero can be copied to clipboard as text,
and pasted onto another hero, overwriting their data.

A timestamped daily backup copy is automatically created of the savegame file, one per day.

![Screenshot](https://raw.githubusercontent.com/suurjaak/h3sed/gh-pages/img/screen.png)

Note: savegames from different releases of Armageddon's Blade may have different
structure for equipment and inventory. For working with savegames from an earlier
version, uncheck "New format in Armageddon's Blade" in program menu File -> Options.

**Warning:** as Heroes3 savefile format is not publicly known,
loaded data and saved results may be invalid and cause problems in game.
This program is based on unofficial information
gathered from observation and online forums.


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
If running straight from source code, open a terminal to `h3sed/src`
and run `python -m h3sed`.


Source Dependencies
-------------------

If running from source code, h3sed needs Python 2.7 or Python 3.6 or higher,
and the following 3rd-party Python packages:
* pyyaml (https://pyyaml.org)
* step (https://pypi.org/project/step-template)
* wxPython 4.0+ (https://wxpython.org)


Attribution
-----------

Knowledge on Heroes3 savegames gathered mostly from Heroes Community forum,
http://heroescommunity.com/viewthread.php3?TID=18817.

Contains several icons from Heroes of Might and Magic III, (c) 1999 3DO.

Binaries compiled with PyInstaller, https://www.pyinstaller.org.

Installers created with Nullsoft Scriptable Install System,
https://nsis.sourceforge.net/.


License
-------

Copyright (c) 2020 by Erki Suurjaak.
Released as free open source software under the MIT License,
see [LICENSE.md](LICENSE.md) for full license text.
