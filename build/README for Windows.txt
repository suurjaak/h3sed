Heroes3 Savegame Editor
=======================

h3sed opens savegame files from Heroes of Might and Magic III,
allowing to edit any and all hero attributes:

- primary skills, like Attack
- other primary attributes, like level, experience points, spell points etc
- war machines, like Ballista
- secondary skills, like Logistics (more than 8 skills can be added)
- artifacts, like Boots of Speed, both equipment and inventory items
- spells, like Slow
- army creatures, like Golden Dragons

Attributes can be copied from one hero and pasted to another.

Hero data can be exported as HTML or spreadsheet or JSON/YAML data.

Supports savegames from: Restoration of Erathia, Armageddon's Blade, Shadow of Death,
Heroes Chronicles, and Horn of the Abyss.

Usable as a graphical program, command-line program, or library.

Downloads at http://suurjaak.github.io/h3sed.


Usage
-----

Navigate the file view to Heroes3 games-folder and open a savegame file to edit,
or drag and drop a savegame file onto the program window.

Choose a hero to modify, change attributes to your liking, and save the file.
Changes will be available in Heroes3 after loading the changed savegame.

Attributes from one hero can be copied to clipboard as text,
and pasted onto another hero, overwriting their data.

A timestamped backup copy is automatically created of the savegame file, one per day.

Note: savegames from different releases of Armageddon's Blade may have different
structure for equipment and inventory. For working with savegames from an earlier
version, uncheck "New format in Armageddon's Blade" in program menu File -> Options.

**Warning:** as Heroes3 savefile format is not publicly known,
loaded data and saved results may be invalid and cause problems in game.
This program is based on unofficial information
gathered from observation and online forums.


Command-line Interface
----------------------

$ h3sed -h

usage: h3sed [-h] [-v] {gui,info,export} ...

h3sed - Heroes3 Savegame Editor.

positional arguments:
  {gui,info,export}
    gui              launch h3sed graphical program (default option)
    info             print information on savegame
    export           export heroes from savegame

optional arguments:
  -h, --help         show this help message and exit
  -v, --version      show program's version number and exit


$ h3sed -h gui

usage: h3sed gui [SAVEGAME [SAVEGAME ...]]

Launch h3sed graphical program (default option).

positional arguments:
  SAVEGAME    Heroes3 savegames(s) to open on startup, if any (supports * wildcards)


$ h3sed -h info

usage: h3sed info SAVEGAME [SAVEGAME ...]

Print information on given savegame(s).

positional arguments:
  SAVEGAME    Heroes3 savegame(s) to read (supports * wildcards)


$ h3sed -h export

usage: h3sed export [-f {csv,html,json,yaml}] [-s [TEXT [TEXT ...]]] [-o [OUTFILE]]
                    SAVEGAME [SAVEGAME ...]

Export heroes from savegame as CSV, HTML, JSON or YAML.

positional arguments:
  SAVEGAME              Heroes3 savegame(s) to read (supports * wildcards)

optional arguments:
  -h, --help            show this help message and exit
  -f {csv,html,json,yaml}, --format {csv,html,json,yaml}
                        output format
  -s [TEXT [TEXT ...]], --search [TEXT [TEXT ...]]
                        filter heroes by name or any matching properties
                        (supports keyword search like "skill=Luck")
  -o [FILE], --output [FILE]
                        write output to file instead of printing to console;
                        filename will be auto-generated if not given;
                        automatic for non-printable formats (csv, html)


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

(The MIT License)

Copyright (C) 2020 by Erki Suurjaak

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

The software is provided "as is", without warranty of any kind, express or
implied, including but not limited to the warranties of merchantability,
fitness for a particular purpose and noninfringement. In no event shall the
authors or copyright holders be liable for any claim, damages or other
liability, whether in an action of contract, tort or otherwise, arising from,
out of or in connection with the software or the use or other dealings in
the software.


For licenses of included libraries, see "3rd-party licenses.txt".
