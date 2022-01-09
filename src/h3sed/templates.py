# -*- coding: utf-8 -*-
"""
HTML templates.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     14.03.2020
@modified    09.01.2022
------------------------------------------------------------------------------
"""
import datetime
import re

from . import conf

# Modules imported inside templates:
#from h3sed import conf


"""Text shown in Help -> About dialog (HTML content)."""
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

<b>Warning:</b> this program was written mainly for personal use,
based on savefile information gathered from observation and online forums.
Since Heroes3 savefile format is not publicly known, 
loaded data and saved results may be invalid and cause problems in game.
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
  <li>step, Simple Template Engine for Python,
      <a href="https://github.com/dotpy/step"><font color="{{ conf.LinkColour }}">github.com/dotpy/step</font></a></li>
  <li>wxPython{{ " %s" % getattr(wx, "__version__", "") if getattr(sys, 'frozen', False) else "" }},
      <a href="http://wxpython.org"><font color="{{ conf.LinkColour }}">wxpython.org</font></a></li>
</ul>
%if getattr(sys, 'frozen', False):
<br /><br />
Installer and binary executable created with:
<ul>
  <li>Nullsoft Scriptable Install System, <a href="https://nsis.sourceforge.net/"><font color="{{ conf.LinkColour }}">nsis.sourceforge.net</font></a></li>
  <li>PyInstaller, <a href="https://www.pyinstaller.org"><font color="{{ conf.LinkColour }}">pyinstaller.org</font></a></li>
</ul><br /><br />
%endif

%if getattr(sys, 'frozen', False):
<br /><br />
Installer created with Nullsoft Scriptable Install System,
<a href="http://nsis.sourceforge.net/"><font color="{{ conf.LinkColour }}">nsis.sourceforge.net</font></a>
%endif

</font>
"""
