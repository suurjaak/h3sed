# -*- coding: utf-8 -*-
"""
HTML templates.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     14.03.2020
@modified    12.02.2023
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
