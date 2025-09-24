CHANGELOG
=========

3.2, 2025-09-24
---------------
- add button with mass change options menu to hero property tabs
- add individual row options menu to hero skills, army, equipment, and inventory
- add option to refill hero movement points
- add option to assemble and disassemble combination artifacts
- add info text to inventory artifacts with hero main stats bonuses
- add info text to spells on missing spellbook
- fix opening savefiles from Armageddon's Blade (issue #18)
- fix opening savefiles from GOG Heroes 3 Complete (issue #19)
- fix not saving Ballista in versions other than Horn of the Abyss (issue #20)


3.1, 2025-09-01
---------------
- order equipment slots always by position not alphabet
- show duplicate hero names with a counter suffix
- add save-as option to files list context menu
- remove files from recent files and heroes lists upon deleting
- fix error on opening savefiles from Restoration of Erathia Steam edition (issue #16)
- fix saving invalid data if Pendant of Reflection or Golden Goose equipped (issue #17)
- fix showing hero as changed upon opening for some game versions
- fix showing hero as unchanged on undo or redo after multiple changes
- fix file extension filter in files list getting narrowed after deleting file
- fix rejecting spells when pasting hero data
- retain button focus on skills page properly over removing or reordering
- start with a larger default window size


3.0, 2025-04-09
---------------
- add command-line interface
- add Python library interface
- add JSON and YAML export
- add savefile modification date to HTML export
- fix console output error for compiled binaries
- rename hero artifacts to equipment


2.8, 2024-12-04
---------------
- add program version update check
- fix wrong IDs and spelling for a number of army creatures (pull request #15)
- fix saving slots that were initially empty then populated then emptied again
- fix tracking changes over undo-redo after saving
- fix error after confirming to save changes when closing file
- improve support for dark mode in Windows 10+


2.7, 2024-09-14
---------------
- add support for Heroes Chronicles savefiles
- use _x86 suffix for 32-bit binaries, drop _x64 suffix from 64-bit binaries


2.6, 2024-06-25
---------------
- add option to delete from disk in files list
- add right-click menu to files list
- fix missing creatures in Horn of the Abyss (pull request #13)
- fix Halfling having duplicate name Halfing (pull request #13)
- fix Halfling Grenadier being named Halfing Grenadier (pull request #13)
- add missing Energy Elemental in Horn of the Abyss
- ensure padding around file list selection upon refresh


2.5, 2024-06-19
---------------
- add save-button to individual heroes
- add buttons to set hero level from experience and vice versa
- add info texts on artifact bonuses to hero main attributes
- fix game version name not being fully visible (issue #11)
- fix not showing Pikeman units in hero army (issue #12)
- fix renamed file not being added to recent files
- fix not being able to modify experience points over 2^30
- add opened heroes to recent heroes list upon file rename
- cap hero level at 75 (74 in Horn of the Abyss)
- cap hero experience at 2^31 - 1 instead of 2^32 - 1
- show different error on trying to open files no longer on disk
- use current directory and extension filter in file dialogs


2.4, 2024-06-14
---------------
- fix parsing campaign savefiles with carry-over heroes (issue #10)
- fix parsing Restoration of Erathia savegames from newer versions (issue #9)
- add menu option for Armageddon's Blade savegames from newer versions (issue #9)
- fix Statesman's Medal having wrong artifact slot (issue #9)
- fix Pendant of Negativity being named Pendant of Agitation (issue #9)
- fix a number of other errors in artifact names
- fix Shield of the Damned not having artifact slot
- fix Quicksand spell being named Quick Sand
- fix Wizard's Well not having artifact slot
- add sorting to hero index page
- add Refresh-button to files list


2.3, 2024-06-11
---------------
- fix recognizing Restoration of Erathia savefiles from GOG Heroes 3 Complete (issue #8)
- upgrade wxPython from 4.1.1 to 4.2.1 in compiled binaries
- include third-party license texts in stand-alone exes
- drop step as a vendored library, use from public package index instead


2.2, 2024-05-28
---------------
- fix opening savefiles in newer versions of Python (issue #6)
- use latest custom-built PyInstaller 6.7 for producing binaries (issue #7)


2.1, 2024-05-24
---------------
- add support for Armageddon's Blade savefiles (issue #5)
- add support for Restoration of Erathia savefiles
- add item compacting option to hero inventory
- fix Vial of Dragon Blood being labelled as Vial of Dragonblood in Shadow of Death savefiles
- tweak game description layout in HTML export


2.0, 2024-03-11
---------------
- show savefile map name and description, in program and in HTML export
- detect game version from fixed bytes not heuristically from hero parsing
- arrange hero spells as a check box grid
- optimize parsing heroes
- optimize creating hero page
- improve showing changes in hero charsheet
- add remove-buttons to hero army, artifacts, and inventory sections
- move folder-button to program main toolbar
- ignore swapping blank or otherwise identical slots in inventory and army
- remember hero tab selection
- remember savefile extension filter
- remember savepage splitter position
- remember view mode in hero full character sheet dialog
- reorder hero attribute categories in UI and exports
- ensure hero index page refreshing from local changes
- ensure uniform heights in hero component rows
- move up-down button focus to new row after swap
- log changes on save
- fix parsing heroes with exotic character codes in name (issue #3)
- fix undo-redo when multiple heroes open
- fix hero index page showing base stats without artifact bonuses
- fix hero tab not selected properly on undo/redo from hero index page
- fix unfinished tag in HTML export if some categories omitted
- fix redo action being logged with name of last action
- fix statusbar not showing stats for currently open file but directory control selection only
- tweak column titles in hero index table
- tweak logging and status messages


1.8, 2024-01-11
---------------
- add support for Factory creatures in Horn of the Abyss (issue #2)
- add support for Sleepkeeper artifact in Horn of the Abyss
- fix name of Vial of Dragon Blood artifact in Horn of the Abyss
- fix error on closing last active hero page from hero index page


1.7, 2023-08-06
---------------
- improve hero parsing regex for spell scrolls in inventory (issue #1)
- improve hero parsing regex for combination artifacts in Horn of the Abyss (issue #1)
- avoid needless serialization on opening first hero
- skip saving artifact spells as available if detectably banned by map
- fix not showing index on changing game version if no heroes parsed
- fix escaping special characters in exported HTML search bar
- improve compatibility between different Python major and minor versions


1.6, 2023-03-28
---------------
- add hero CSV/HTML export
- show donned artifact stats
- improve hero parsing regex


1.5, 2023-02-24
---------------
- add category toggles to hero index
- drop obsolete auto-load option


1.4, 2023-02-21
---------------
- add hero index page


1.3, 2023-02-17
---------------
- add hero charsheet view
- add recent heroes menu
- add separate toolbar for selected hero
- improve hero parsing regex
- make "movement points in total" read-only, as the game overwrites it on each turn
- save backup only if not already saved for current date
- fix not saving backup before overwriting


1.2, 2023-02-07
---------------
- add undo-redo command history dialog
- add toolbar button to open savefile folder
- add "Show unsaved changes" to edit-menu
- improve hero parsing regex
- improve tracking updates in hero primary attributes from artifact change
- fix army paste retaining previous values in new blank slots
- fix army SpinCtrl hidden arrows becoming visible on system colour change


1.1, 2023-01-29
---------------
- support multiple hero tabs
- show donned artifact stats
- fix using wx locale in Py2


1.0, 2022-01-20
---------------
- first public release
