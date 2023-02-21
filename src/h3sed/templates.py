# -*- coding: utf-8 -*-
"""
HTML templates.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     14.03.2020
@modified    21.02.2023
------------------------------------------------------------------------------
"""

# Modules imported inside templates:
#import difflib, sys, wx
#from h3sed.lib.vendor import step
#from h3sed import conf, templates


"""HTML text shown in Help -> About dialog."""
ABOUT_HTML = """<%
import sys, wx
from h3sed import conf
%>
<font size="2" face="{{ conf.HtmlFontName }}" color="{{ conf.FgColour }}">
<table cellpadding="0" cellspacing="0"><tr><td valign="middle">
<img src="memory:{{ conf.Title.lower() }}.png" /></td><td width="10"></td><td valign="center">
<b>{{ conf.Title }} version {{ conf.Version }}</b>, {{ conf.VersionDate }}.<br /><br />

&copy; 2020, Erki Suurjaak.
<a href="{{ conf.HomeUrl }}"><font color="{{ conf.LinkColour }}">{{ conf.HomeUrl.replace("https://", "").replace("http://", "") }}</font></a>
</td></tr></table><br /><br />

Savefile editor for Heroes of Might and Magic III.<br />
Released as free open source software under the MIT License.<br /><br />

<b>Warning:</b> as Heroes3 savefile format is not publicly known,
loaded data and saved results may be invalid and cause problems in game.
This program is based on unofficial information gathered from observation and online forums.
<br /><br />
Always choose the correct game version.
A wrong choice will result in file data being misinterpreted,
and saving later version items or creatures to an earlier version savefile
may cause the game to crash.

<hr />

{{ conf.Title }} has been built using the following open source software:
<ul>
  <li>Python,
      <a href="https://www.python.org/"><font color="{{ conf.LinkColour }}">python.org</font></a></li>
  <li>pyyaml,
      <a href="https://pyyaml.org/"><font color="{{ conf.LinkColour }}">pyyaml.org</font></a></li>
  <li>step, Simple Template Engine for Python,
      <a href="https://github.com/dotpy/step"><font color="{{ conf.LinkColour }}">github.com/dotpy/step</font></a></li>
  <li>wxPython{{ " %s" % getattr(wx, "__version__", "") if getattr(sys, 'frozen', False) else "" }},
      <a href="https://wxpython.org"><font color="{{ conf.LinkColour }}">wxpython.org</font></a></li>
</ul>
%if getattr(sys, 'frozen', False):
<br /><br />
Installer and binary executable created with:
<ul>
  <li>Nullsoft Scriptable Install System, <a href="https://nsis.sourceforge.net/"><font color="{{ conf.LinkColour }}">nsis.sourceforge.net</font></a></li>
  <li>PyInstaller, <a href="https://www.pyinstaller.org"><font color="{{ conf.LinkColour }}">pyinstaller.org</font></a></li>
</ul>
%endif

</font>
"""


"""
HTML text shown for hero full character sheet, toggleable between unsaved changes view.

@param   name     hero name
@param   texts    [category current content, ]
@param  ?texts0   [category original content, ] if any, to show changes against current
@param  ?changes  show changes against current

"""
HERO_CHARSHEET_HTML = """<%
import difflib, wx
from h3sed.lib.vendor import step
from h3sed import conf, templates
COLOUR_DISABLED = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT).GetAsString(wx.C2S_HTML_SYNTAX)
texts0 = isdef("texts0") and texts0 or []
changes = isdef("changes") and changes
%>
<font face="{{ conf.HtmlFontName }}" color="{{ conf.FgColour }}">
<table cellpadding="0" cellspacing="0" width="100%"><tr>
  <td><b>{{ name }}{{ " unsaved changes" if changes else "" }}</b></td>
%if texts0:
  <td align="right">
    <a href="{{ "normal" if changes else "changes" }}"><font color="{{ conf.LinkColour }}">{{ "Normal view" if changes else "Unsaved changes" }}</font></a>
  </td>
%endif
</tr></table>
<font size="2">
%if changes:
{{! step.Template(templates.HERO_DIFF_HTML, escape=True).expand(changes=list(zip(texts0, texts))) }}
%else:
<table cellpadding="0" cellspacing="0">
    %for text in texts:
        %for line in text.rstrip().splitlines():
  <tr><td><code>{{! escape(line).rstrip().replace(" ", "&nbsp;") }}</code></td></tr>
        %endfor
    %endfor
%endif
</table>
</font>
</font>
"""


"""
HTML text shown for hero unsaved changes diff.

@param  ?name     hero name, if any
@param   changes  [(category content1, category content2), ]
"""
HERO_DIFF_HTML = """<%
import difflib
from h3sed import conf
%>
<font face="{{ conf.HtmlFontName }}" color="{{ conf.FgColour }}">
%if isdef("name") and name:
<b>{{ name }}</b>
%endif
<font size="2"><table cellpadding="0" cellspacing="0">
%for v1, v2 in changes:
<%
entries, entry = [], []
for line in difflib.Differ().compare(v1.splitlines(), v2.splitlines()):
    if line.startswith("  "):
        if entry: entries.append(entry + [""])
        entries.append((line, line))
        entry = []
    elif line.startswith("- "):
        if entry: entries.append(entry + [""])
        entry = [line]
    elif line.startswith("+ "):
        entries.append((entry or [""]) + [line])
        entry = []
if entry: entries.append(entry + [""])
entries = [[escape(l[2:].rstrip()).replace(" ", "&nbsp;") for l in ll] for ll in entries]
%>
    %for i, (l1, l2) in enumerate(entries):
        %if not i:
    <tr><td colspan="2"><code>{{! l1 }}</code></td></tr>
        %elif l1 == l2:
    <tr><td><code>{{! l1 }}</code></td><td><code>{{! l2 }}</code></td></tr>
        %else:
    <tr><td bgcolor="{{ conf.DiffOldColour }}"><code>{{! l1 }}</code></td>
        <td bgcolor="{{ conf.DiffNewColour }}"><code>{{! l2 }}</code></td></tr>
        %endif
    %endfor
%endfor
</table></font>
</font>
"""


"""
Text to search for filtering heroes index.

@param   hero     Hero instance
@param   plugins  {name: plugin instance}
"""
HERO_SEARCH_TEXT = """<%
from h3sed import conf, metadata
deviceprops = plugins["stats"].props()
deviceprops = deviceprops[next(i for i, x in enumerate(deviceprops) if "spellbook" == x["name"]):]
%>
{{ hero.name }}
%for name in metadata.PrimaryAttributes:
{{ hero.basestats[name] }}
%endfor
{{ hero.stats["level"] }}
%for prop in deviceprops:
    %if hero.stats.get(prop["name"]):
{{ prop["label"] if isinstance(hero.stats[prop["name"]], bool) else hero.stats[prop["name"]] }}
    %endif
%endfor
%for skill in hero.skills:
{{ skill["name"] }}: {{ skill["level"] }}
%endfor
%for army in filter(bool, hero.army):
{{ army["name"] }}: {{ army["count"] }}
%endfor
%for item in hero.spells:
{{ item }}
%endfor
%for item in filter(bool, hero.artifacts.values()):
{{ item }}
%endfor
%for item in filter(bool, hero.inventory):
{{ item }}
%endfor
"""


"""
HTML text shown in heroes index.

@param   heroes   [Hero instance, ]
@param   links    [link for hero, ]
@param   count    total number of heroes
@param   plugins  {name: plugin instance}
@param  ?text     current search text if any
"""
HERO_INDEX_HTML = """<%
from h3sed import conf, metadata
deviceprops = plugins["stats"].props()
deviceprops = deviceprops[next(i for i, x in enumerate(deviceprops) if "spellbook" == x["name"]):]
%>
<font face="{{ conf.HtmlFontName }}" color="{{ conf.FgColour }}">
%if heroes:
<table>
  <tr>
    <th align="left" valign="bottom">Name</th>
%for label in metadata.PrimaryAttributes.values():
    <th align="left" valign="bottom">{{ label.split()[-1] }}</th>
%endfor
    <th align="left" valign="bottom">Level</th>
    <th align="left" valign="bottom">Devices</th>
    <th align="left" valign="bottom">Skills</th>
    <th align="left" valign="bottom">Army</th>
    <th align="left" valign="bottom">Spells</th>
    <th align="left" valign="bottom">Artifacts</th>
    <th align="left" valign="bottom">Inventory</th>
  </tr>
%elif count and isdef("text") and text.strip():
   <i>No heroes to display for "{{ text }}"</i>
%else:
   <i>No heroes to display.</i>
%endif
%for i, hero in enumerate(heroes):
  <tr>
    <td align="left" valign="top" nowrap><a href="{{ links[i] }}"><font color="{{ conf.LinkColour }}">{{ hero.name }}</font></a></td>
%for name in metadata.PrimaryAttributes:
    <td align="left" valign="top" nowrap>{{ hero.basestats[name] }}</td>
%endfor
    <td align="left" valign="top" nowrap>{{ hero.stats["level"] }}</td>
    <td align="left" valign="top" nowrap>
%for prop in deviceprops:
    %if hero.stats.get(prop["name"]):
        {{ prop["label"] if isinstance(hero.stats[prop["name"]], bool) else hero.stats[prop["name"]] }}<br />
    %endif
%endfor
    </td>
    <td align="left" valign="top" nowrap>
%for skill in hero.skills:
    <b>{{ skill["name"] }}:</b> {{ skill["level"] }}<br />
%endfor
    </td>
    <td align="left" valign="top" nowrap>
%for army in filter(bool, hero.army):
    {{ army["name"] }}: {{ army["count"] }}<br />
%endfor
    </td>
    <td align="left" valign="top" nowrap>
%for item in hero.spells:
    {{ item }}<br />
%endfor
    </td>
    <td align="left" valign="top" nowrap>
%for item in filter(bool, hero.artifacts.values()):
    {{ item }}<br />
%endfor
    </td>
    <td align="left" valign="top" nowrap>
%for item in filter(bool, hero.inventory):
    {{ item }}<br />
%endfor
    </td>
  </tr>
%endfor
%if heroes:
</table>
%endif
</font>
"""
