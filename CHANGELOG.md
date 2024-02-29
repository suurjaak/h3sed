CHANGELOG
=========

1.9, 2024-02-29
---------------
- show savefile map name and description, in program and in HTML export
- detect game version from fixed bytes not heuristically from hero parsing
- arrange hero spells as a check box grid
- add remove-buttons to hero army, artifacts and inventory sections
- ignore swapping blank or otherwise identical slots in inventory and army
- remember view mode in hero full character sheet dialog
- remember savefile extension filter
- remember hero tab selection
- remember savepage splitter position
- reorder hero attribute categories in UI and exports
- optimize loading hero
- ensure hero index page refreshing from local changes
- ensure uniform heights in hero component rows
- move up-down button focus to new row after swap
- fix unfinished tag in HTML export if some categories omitted
- fix redo action being logged with name of last action
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
