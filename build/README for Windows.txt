Heroes3 Savegame Editor
=======================

h3sed opens savegame files from Heroes of Might and Magic III,
allowing to edit any and all hero attributes:

- primary skills, like Attack
- other primary attributes, like level, experience points, spell points etc
- war machines, like Ballista
- secondary skills, like Logistics (more than 8 skills can be added)
- artifacts, like Boots of Speed, both worn and inventory items
- spells, like Slow
- army creatures, like Golden Dragons

Attributes can be copied from one hero and pasted to another.

Supports savegames from Shadow of Death and Horn of the Abyss.

Downloads at http://suurjaak.github.io/h3sed.


Usage
-----

Navigate the file view to Heroes3 games-folder, and open a savegame file to edit.

Choose a hero to modify, change attributes to your liking, and save the file.
Changes will be available in Heroes3 after loading the changed savegame.

Attributes from one hero can be copied to clipboard as text,
and pasted onto another hero, overwriting their data.

A timestamped backup copy is automatically created of the savegame file.

**Warning:** as Heroes3 savefile format is not publicly known,
loaded data and saved results may be invalid and cause problems in game.
This program is based on unofficial information
gathered from observation and online forums.

Always choose the correct game version. A wrong choice will result
in file data being misinterpreted, and saving later version items
or creatures to an earlier version savefile may cause the game to crash.


Attribution
-----------

Knowledge on Heroes3 savegames gathered mostly from Heroes Community forum,
http://heroescommunity.com/viewthread.php3?TID=18817.

Includes a modified version of step, Simple Template Engine for Python,
(c) 2012, Daniele Mazzocchio, https://github.com/dotpy/step.

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
