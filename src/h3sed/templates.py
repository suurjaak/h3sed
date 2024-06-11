# -*- coding: utf-8 -*-
"""
HTML templates.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     14.03.2020
@modified    11.06.2024
------------------------------------------------------------------------------
"""
import difflib, re
# Modules imported inside templates:
#import datetime, json, os, sys, step, wx
#from h3sed.lib import util
#from h3sed import conf, images, plugins, templates


def make_category_diff(v1, v2):
    """
    Returns diff for hero charsheet category texts.

    @param   v1  text with old values
    @param   v2  text with new values
    @return      [(old line, new line), ] with empty string standing for total change
    """
    LF, LFMARKER, ADDED, REMOVED, SAME = "\n", "\\n", "+ ", "- ", "  "

    def make_entries(s1, s2):
        """Produces line diff for texts, as [(old, new), ]."""
        entries, pending = [], None
        finalize = lambda a, b="": entries.append([a, b][::-1 if a.startswith(ADDED) else 1])
        for line in difflib.Differ().compare(s1.splitlines(), s2.splitlines()):
            if line.startswith(SAME):  # No change
                if pending: finalize(pending)
                entries.append((line, line))
                pending = None
            elif line.startswith((REMOVED, ADDED)):
                if pending: finalize(pending, "" if line[:2] == pending[:2] else line)
                pending = line if not pending or line[:2] == pending[:2] else None
        if pending: finalize(pending)
        return [[l[2:] for l in ll] for ll in entries]  # Strip difflib prefixes

    # 1st pass: merge multi-line items to one line, to avoid difflib combining different items
    ll1, ll2 = v1.splitlines(), v2.splitlines()
    for ll in (ll1, ll2):
        for i, l in enumerate(ll[::-1]):
            ix = len(ll) - i - 1
            if l and ix and not re.match(r"(\s*-)|^$", ll[ix]) and re.match(r"\s*-\s.+", ll[ix-1]):
                ll[ix-1] += LFMARKER + ll.pop(ix)
    v1, v2 = LF.join(ll1), LF.join(ll2)

    # 2nd pass: produce preliminary diff
    diff = make_entries(v1, v2)

    # 3rd pass: split merged items back to multi-line, produce line diff from within item
    LEN = len(diff)
    for i, (s1, s2) in enumerate(diff[::-1]):
        if LFMARKER in s1 or LFMARKER in s2:
            diff[LEN-i-1:LEN-i] = make_entries(*(s.replace(LFMARKER, LF) for s in (s1, s2)))

    return diff


"""HTML text shown in Help -> About dialog."""
ABOUT_HTML = """<%
import os, sys, wx
from h3sed.lib import util
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

%if conf.LicenseFile and os.path.isfile(conf.LicenseFile):
<br /><br />
Licensing for bundled software:
<a href="{{ util.path_to_url(conf.LicenseFile) }}"><font color="{{ conf.LinkColour }}">{{ os.path.basename(conf.LicenseFile) }}</font></a>
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
import step
from h3sed import conf, templates
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
from h3sed import conf, templates
%>
<font face="{{ conf.HtmlFontName }}" color="{{ conf.FgColour }}">
%if isdef("name") and name:
<b>{{ name }}</b>
%endif
<font size="2"><table cellpadding="0" cellspacing="0">
%for v1, v2 in changes:
<%
entries = templates.make_category_diff(v1, v2)
entries = [[escape(l).replace(" ", "&nbsp;") for l in ll] for ll in entries]
%>
    %for i, (l1, l2) in enumerate(entries):
        %if not i:
    <tr><td colspan="2"><code>{{! l1 }}</code></td></tr>
        %elif l1 == l2:
    <tr><td><code>{{! l1 }}</code></td><td><code>{{! l2 }}</code></td></tr>
        %elif l1 != l2 and ":" not in l1 + l2:
    <tr><td bgcolor="{{ conf.DiffOldColour }}"><code>{{! l1 }}</code></td>
        <td><code></code></td></tr>
    <tr><td><code></code></td>
        <td bgcolor="{{ conf.DiffNewColour }}"><code>{{! l2 }}</code></td></tr>
        %else:
    <tr><td bgcolor="{{ conf.DiffOldColour if l1 else "" }}"><code>{{! l1 }}</code></td>
        <td bgcolor="{{ conf.DiffNewColour if l2 else "" }}"><code>{{! l2 }}</code></td></tr>
        %endif
    %endfor
%endfor
</table></font>
</font>
"""


"""
Text shown for hero unsaved changes diff for logging.

@param  ?name     hero name, if any
@param   changes  [(category content1, category content2), ]
"""
HERO_DIFF_TEXT = """<%
import re
from h3sed import conf, templates
%>
%if isdef("name") and name:
{{ name }}:
%endif
%for v1, v2 in ((a, b) for a, b in changes if a != b):
<%
entries = templates.make_category_diff(v1, v2)
# Merge multi-line items to one line
ll1, ll2 = map(list, zip(*entries))
for i, (l1, l2) in enumerate(entries[::-1]):
    ix = len(entries) - i - 1
    if ix and (not re.match(r"(\s*-)|^$", ll1[ix]) and re.match(r"\s*-\s.+", ll1[ix-1])
    or not re.match(r"(\s*-)|^$", ll2[ix]) and re.match(r"\s*-\s.+", ll2[ix-1])):
        ll1[ix-1] += " " + ll1.pop(ix)
        ll2[ix-1] += " " + ll2.pop(ix)
entries = list(zip(ll1, ll2))
shift_pending = shift = False
%>
    %for i, (l1, l2) in enumerate(entries):
<%
shift_pending = shift_pending or (l1.strip() + l2.strip() == "-")
l1, l2 = (re.sub("(^\s*-\s*)|(\s{2,})", " ", x).strip() for x in (l1, l2))
l1, l2 = ("" if i and l.endswith(":") else l for l in (l1, l2))
shift = shift_pending and bool(l1 or l2)
if shift: shift_pending = False
%>
        %if not i:
  {{ l1 }}
        %elif l1 and not l2:
    removed  {{ l1 }}
        %elif l2 and not l1:
    added  {{ l2 }}
        %elif l1 != l2 and ":" in l1 + l2:
    changed  {{ l1 }}  to  {{ l2 }}
        %elif l1 != l2:
    removed  {{ l1 }}
    added  {{ l2 }}
        %elif shift:
    shifted  {{ l2 }}
        %endif
    %endfor
%endfor
"""


"""
Text to search for filtering heroes index.

@param   hero       Hero instance
@param   pluginmap  {name: plugin instance}
@param  ?category   category to produce if not all, or empty string for hero name only
"""
HERO_SEARCH_TEXT = """<%
from h3sed import conf, metadata
deviceprops = pluginmap["stats"].props()
deviceprops = deviceprops[next(i for i, x in enumerate(deviceprops) if "spellbook" == x["name"]):]
category = category if isdef("category") else None
%>
%if category is None or not category:
{{ hero.name }}
%endif
%if category is None or "stats" == category:
{{ hero.stats["level"] }}
    %for name in metadata.PrimaryAttributes:
{{ hero.stats[name] }}
    %endfor
%endif
%if category is None or "devices" == category:
    %for prop in deviceprops:
        %if hero.stats.get(prop["name"]):
{{ prop["label"] if isinstance(hero.stats[prop["name"]], bool) else hero.stats[prop["name"]] }}
        %endif
    %endfor
%endif
%if category is None or "skills" == category:
    %for skill in hero.skills:
{{ skill["name"] }}: {{ skill["level"] }}
    %endfor
%endif
%if category is None or "army" == category:
    %for army in filter(bool, hero.army):
{{ army["name"] }}: {{ army["count"] }}
    %endfor
%endif
%if category is None or "spells" == category:
    %for item in hero.spells:
{{ item }}
    %endfor
%endif
%if category is None or "artifacts" == category:
    %for item in filter(bool, hero.artifacts.values()):
{{ item }}
    %endfor
%endif
%if category is None or "inventory" == category:
    %for item in filter(bool, hero.inventory):
{{ item }}
    %endfor
%endif
"""


"""
HTML text shown in heroes index.

@param   heroes      [Hero instance, ]
@param   links       [link for hero, ]
@param   count       total number of heroes
@param   pluginmap   {name: plugin instance}
@param  ?categories  {category: whether to show category columns} if not showing all
@param  ?text        current search text if any
"""
HERO_INDEX_HTML = """<%
from h3sed import conf, metadata
deviceprops = pluginmap["stats"].props()
deviceprops = deviceprops[next(i for i, x in enumerate(deviceprops) if "spellbook" == x["name"]):]
categories = categories if isdef("categories") else None
%>
<font face="{{ conf.HtmlFontName }}" color="{{ conf.FgColour }}">
%if heroes:
<table>
  <tr>
    <th align="left" valign="bottom">Name</th>
%if not categories or categories["stats"]:
    <th align="left" valign="bottom">Level</th>
    %for name, label in metadata.PrimaryAttributes.items():
    <th align="left" valign="bottom">{{ next(x[:5] if len(x) > 7 else x for x in [label.split()[-1]]) }}</th>
    %endfor
%endif
%if not categories or categories["devices"]:
    <th align="left" valign="bottom">Devices</th>
%endif
%if not categories or categories["skills"]:
    <th align="left" valign="bottom">Skills</th>
%endif
%if not categories or categories["army"]:
    <th align="left" valign="bottom">Army</th>
%endif
%if not categories or categories["artifacts"]:
    <th align="left" valign="bottom">Artifacts</th>
%endif
%if not categories or categories["inventory"]:
    <th align="left" valign="bottom">Inventory</th>
%endif
%if not categories or categories["spells"]:
    <th align="left" valign="bottom">Spells</th>
%endif
  </tr>
%elif count and isdef("text") and text.strip():
   <i>No heroes to display for "{{ text }}"</i>
%else:
   <i>No heroes to display.</i>
%endif
%for i, hero in enumerate(heroes):
  <tr>
    <td align="left" valign="top" nowrap><a href="{{ links[i] }}"><font color="{{ conf.LinkColour }}">{{ hero.name }}</font></a></td>
%if not categories or categories["stats"]:
    <td align="left" valign="top" nowrap>{{ hero.stats["level"] }}</td>
    %for name in metadata.PrimaryAttributes:
    <td align="left" valign="top" nowrap>{{ hero.stats[name] }}</td>
    %endfor
%endif
%if not categories or categories["devices"]:
    <td align="left" valign="top" nowrap>
    %for prop in deviceprops:
        %if hero.stats.get(prop["name"]):
        {{ prop["label"] if isinstance(hero.stats[prop["name"]], bool) else hero.stats[prop["name"]] }}<br />
        %endif
    %endfor
    </td>
%endif
%if not categories or categories["skills"]:
    <td align="left" valign="top" nowrap>
    %for skill in hero.skills:
    <b>{{ skill["name"] }}:</b> {{ skill["level"] }}<br />
    %endfor
    </td>
%endif
%if not categories or categories["army"]:
    <td align="left" valign="top" nowrap>
    %for army in filter(bool, hero.army):
    {{ army["name"] }}: {{ army["count"] }}<br />
    %endfor
    </td>
%endif
%if not categories or categories["artifacts"]:
    <td align="left" valign="top" nowrap>
    %for item in filter(bool, hero.artifacts.values()):
    {{ item }}<br />
    %endfor
    </td>
%endif
%if not categories or categories["inventory"]:
    <td align="left" valign="top" nowrap>
    %for item in filter(bool, hero.inventory):
    {{ item }}<br />
    %endfor
    </td>
  </tr>
%endif
%if not categories or categories["spells"]:
    <td align="left" valign="top" nowrap>
    %for item in hero.spells:
    {{ item }}<br />
    %endfor
    </td>
%endif
%endfor
%if heroes:
</table>
%endif
</font>
"""


"""
Text to provide for hero columns in CSV export.

@param   hero       Hero instance
@param   column     column to provide like "level" or "devices"
@param   pluginmap  {name: plugin instance}
"""
HERO_EXPORT_CSV = """<%
deviceprops = pluginmap["stats"].props()
deviceprops = deviceprops[next(i for i, x in enumerate(deviceprops) if "spellbook" == x["name"]):]
%>
%if "name" == column:
{{ hero.name }}
%elif column in hero.stats:
{{ hero.stats[column] }}
%elif "devices" == column:
    %for prop in deviceprops:
        %if hero.stats.get(prop["name"]):
{{ prop["label"] if isinstance(hero.stats[prop["name"]], bool) else hero.stats[prop["name"]] }}
        %endif
    %endfor
%elif "skills" == column:
    %for skill in hero.skills:
{{ skill["name"] }}: {{ skill["level"] }}
    %endfor
%elif "army" == column:
    %for army in filter(bool, hero.army):
{{ army["name"] }}: {{ army["count"] }}
    %endfor
%elif "spells" == column:
    %for item in hero.spells:
{{ item }}
    %endfor
%elif "artifacts" == column:
    %for slot, item in ((k, v) for k, v in hero.artifacts.items() if v):
{{ slot }}: {{ item }}
    %endfor
%elif "inventory" == column:
    %for item in filter(bool, hero.inventory):
{{ item }}
    %endfor
%endif
"""


"""
HTML text for exporting heroes to file.

@param   heroes      [Hero instance, ]
@param   pluginmap   {name: plugin instance}
@param   savefile    metadata.Savefile instance
@param   count       total number of heroes
@param   categories  {category: whether to show category columns initially}
"""
HERO_EXPORT_HTML = """<%
import datetime, json
from h3sed.lib import util
from h3sed import conf, images, metadata, plugins
deviceprops = pluginmap["stats"].props()
deviceprops = deviceprops[next(i for i, x in enumerate(deviceprops) if "spellbook" == x["name"]):]
%><!DOCTYPE HTML><html lang="en">
<head>
  <meta http-equiv='Content-Type' content='text/html;charset=utf-8'>
  <meta name="author" content="{{ conf.Title }}">
  <meta name="generator" content="{{ conf.Name }} v{{ conf.Version }} ({{ conf.VersionDate }})">
  <title>Heroes of Might & Magic III - Savegame export - Heroes</title>
  <link rel="shortcut icon" type="image/png" href="data:image/png;base64,{{! images.Icon_16x16_16bit.data }}">
  <style>
    * { font-family: Tahoma, "DejaVu Sans", "Open Sans", Verdana; color: black; font-size: 11px; }
    body {
      background-image: url("data:image/png;base64,{{! images.ExportBg.data }}");
      margin: 0;
      padding: 0;
    }
    a, a.visited {
      color: blue;
      text-decoration: none;
    }
    table#heroes { border-spacing: 2px; empty-cells: show; width: 100%; }
    table#heroes td, table#heroes th { border: 1px solid #C0C0C0; padding: 5px; }
    table#heroes th { text-align: left; white-space: nowrap; }
    table#heroes td { vertical-align: top; white-space: nowrap; }
    td.index, th.index { color: gray; width: 10px; }
    td.index { color: gray; text-align: right; }
    .long { display: inline-block; max-width: 600px; white-space: pre-wrap; }
    a.toggle { font-weight: normal; }
    a.toggle:hover { cursor: pointer; text-decoration: none; }
    a.toggle::after { content: ".. \\25b6"; }
    a.toggle.open::after { content: " \\25b2"; font-size: 0.7em; }
    a.sort { display: block; }
    a.sort:hover { cursor: pointer; text-decoration: none; }
    a.sort::after      { content: ""; display: inline-block; min-width: 6px; position: relative; left: 3px; top: -1px; }
    a.sort.asc::after  { content: "↓"; }
    a.sort.desc::after { content: "↑"; }
    .hidden { display: none !important; }
    #content {
      background-color: white;
      border-radius: 5px;
      margin: 10px auto 0 auto;
      max-width: fit-content;
      overflow-x: auto;
      padding: 20px;
    }
    table#info {
      border-spacing: 0;
      margin-bottom: 10px;
    }
    table#info td { padding: 0; vertical-align: top; }
    table#info td:first-child { padding-right: 5px; }
    table#info td:last-child { font-weight: bold; }
    #opts { display: flex; justify-content: space-between; margin-right: 2px; }
    #toggles { display: flex; }
    #toggles > label { display: flex; align-items: center; margin-right: 5px; }
    #toggles > .last-child { margin-left: auto; }
    #footer {
      color: white;
      padding: 10px 0;
      text-align: center;
    }
    #overlay {
      display: flex;
      align-items: center;
      bottom: 0;
      justify-content: center;
      left: 0;
      position: fixed;
      right: 0;
      top: 0;
      z-index: 10000;
    }
    #overlay #overshadow {
      background: black;
      bottom: 0;
      height: 100%;
      left: 0;
      opacity: 0.5;
      position: fixed;
      right: 0;
      top: 0;
      width: 100%;
    }
    #overlay #overbox {
      background: white;
      opacity: 1;
      padding: 10px;
      z-index: 10001;
      max-width: calc(100% - 2 * 10px);
      max-height: calc(100% - 2 * 10px - 20px);
      overflow: auto;
      position: relative;
    }
    #overlay #overbox > a {
      position: absolute;
      right: 5px;
      top: 2px;
    }
    #overlay #overcontent {
      font-family: monospace;
      white-space: pre;
    }
  </style>
  <script>
<%
MULTICOLS = {"stats": [3, 4, 5, 6, 7]}
colptr = 7 if categories["stats"] else 3  # 1: index 2: name
%>
  var CATEGORIES = {  // {category: [table column index, ]}
%for i, (category, state) in enumerate(categories.items()):
    %if state:
    "{{ category }}": {{! MULTICOLS.get(category) or [colptr] }},
    %endif
<%
colptr += state
%>
%endfor
  };
  var HEROES = [
%for i, hero in enumerate(heroes):
    {{! json.dumps(hero.yaml) }},
%endfor
  ];
  var toggles = {
%for category in (k for k, v in categories.items() if v):
    "{{ category }}": true,
%endfor
  };
  var SEARCH_DELAY = 200;  // Milliseconds to delay search after input
  var searchText = "";
  var searchTimer = null;


  /** Schedules search after delay. */
  var onSearch = function(evt) {
    window.clearTimeout(searchTimer); // Avoid reacting to rapid changes

    var mysearch = evt.target.value.trim();
    if (27 == evt.keyCode) mysearch = evt.target.value = "";
    var mytimer = searchTimer = window.setTimeout(function() {
      if (mytimer == searchTimer && mysearch != searchText) {
        searchText = mysearch;
        doSearch("heroes", mysearch);
      };
      searchTimer = null;
    }, SEARCH_DELAY);
  };


  /** Sorts table by column of given table header link. */
  var onSort = function(link) {
    var col = null;
    var prev_col = null;
    var prev_direction = null;
    var table = link.closest("table");
    var linklist = table.querySelector("tr").querySelectorAll("a.sort");
    for (var i = 0; i < linklist.length; i++) {
      if (linklist[i] == link) col = i;
      if (linklist[i].classList.contains("asc") || linklist[i].classList.contains("desc")) {
        prev_col = i;
        prev_direction = linklist[i].classList.contains("asc");
      };
      linklist[i].classList.remove("asc");
      linklist[i].classList.remove("desc");
    };
    var sort_col = col;
    var sort_direction = (sort_col == prev_col) ? !prev_direction : true;
    var rowlist = table.getElementsByTagName("tr");
    var rows = [];
    for (var i = 1, ll = rowlist.length; i != ll; rows.push(rowlist[i++]));
    rows.sort(sortfn.bind(this, sort_col, sort_direction));
    for (var i = 0; i < rows.length; i++) table.tBodies[0].appendChild(rows[i]);

    linklist[sort_col].classList.add(sort_direction ? "asc" : "desc")
    return false;
  };


  /** Toggles class "open" on link and given class on given elements; class defaults to "hidden". */
  var onToggle = function(a, elem1, elem2, cls) {
    cls = cls || "hidden";
    elem1 = (elem1 instanceof Element) ? elem1 : document.querySelector(elem1);
    elem2 = (elem2 instanceof Element) ? elem2 : document.querySelector(elem2);
    a.classList.toggle("open");
    elem1 && elem1.classList.toggle(cls);
    elem2 && elem2.classList.toggle(cls);
  };


  /** Shows or hides category columns. */
  var onToggleCategory = function(category, elem) {
    toggles[category] = elem.checked;
    CATEGORIES[category].forEach(function(col) {
      document.querySelectorAll("#heroes > tbody > tr > :nth-child(" + col + ")").forEach(function(elem) {
        toggles[category] ? elem.classList.remove("hidden") : elem.classList.add("hidden");
      })
    });
    doSearch("heroes", searchText);
  };


  /** Filters table by given text, retaining row if all words find a match in row cells. */
  var doSearch = function(table_id, text) {
    var words = String(text).split(/\s/g).filter(Boolean);
    var regexes = words.map(function(word) { return new RegExp(escapeRegExp(word), "i"); });
    var table = document.getElementById(table_id);
    table.classList.add("hidden");
    var rowlist = table.getElementsByTagName("tr");
    var HIDDENCOLS = Object.keys(CATEGORIES).reduce(function(o, v, i) {
      if (!toggles[v]) Array.prototype.push.apply(o, CATEGORIES[v]);
      return o;
    }, [])
    for (var i = 1, ll = rowlist.length; i < ll; i++) {
      var matches = {};  // {regex index: bool}
      var show = !words.length;
      var tr = rowlist[i];
      for (var j = 0, cc = tr.childElementCount; j < cc && !show; j++) {
        var ctext = (HIDDENCOLS.indexOf(j + 1) < 0) ? tr.children[j].innerText : "";
        ctext && regexes.forEach(function(rgx, k) { if (ctext.match(rgx)) matches[k] = true; });
      };
      show = show || regexes.every(function(_, k) { return matches[k]; });
      tr.classList[show ? "remove" : "add"]("hidden");
    };
    table.classList.remove("hidden");
  };


  /** Returns string with special characters escaped for RegExp. */
  var escapeRegExp = function(string) {
    return string.replace(/[\\\^$.|?*+()[{]/g, "\\\$&");
  };


  /** Toggles modal dialog with hero charsheet. */
  var showHero = function(index) {
    document.getElementById("overcontent").innerText = HEROES[index];
    document.getElementById("overlay").classList.toggle("hidden");
  };


  /** Returns comparison result of given children in a vs b. */
  var sortfn = function(sort_col, sort_direction, a, b) {
    var v1 = a.children[sort_col].innerText.toLowerCase();
    var v2 = b.children[sort_col].innerText.toLowerCase();
    var result = String(v1).localeCompare(String(v2), undefined, {numeric: true});
    return sort_direction ? result : -result;
  };


  window.addEventListener("load", function() {
    document.location.hash = "";
    document.body.addEventListener("keydown", function(evt) {
      if (evt.keyCode == 27 && !document.getElementById("overlay").classList.contains("hidden")) showHero();
    });
  });
  </script>
</head>
<body>
<div id="content">
  <table id="info">
    <tr><td>Source:</td><td>{{ savefile.filename }}</td></tr>
    <tr><td>Size:</td><td title="{{ savefile.size }}">{{ util.format_bytes(savefile.size) }}</td></tr>
    <tr><td>Heroes:</td><td>{{ len(heroes) if len(heroes) == count else "%s exported (%s total)" % (len(heroes), count) }}</td></tr>
%if hasattr(plugins, "version"):
    <tr><td>Game version:</td><td>{{ next((x["label"] for x in plugins.version.PLUGINS if x["name"] == savefile.version), "unknown") }}</td></tr>
%endif
%if savefile.mapdata.get("name"):
    <tr><td>Map:</td><td>{{ savefile.mapdata["name"] }}</td></tr>
%endif
%if savefile.mapdata.get("desc"):
  <tr>
    <td>Description:</td>
    <td>
      <span class="short" title="{{ savefile.mapdata["desc"] }}">{{ savefile.mapdata["desc"].splitlines()[0].strip()[:100] }}</span>
      <span class="hidden long">{{ savefile.mapdata["desc"] }}</span>
      <a class="toggle" title="Toggle full description" onclick="onToggle(this, '.short', '.long')"> </a>
    </td>
  </tr>
%endif
  </table>

<div id="opts">
  <div id="toggles">
%for category in (k for k, v in categories.items() if v):
    <label for="toggle-{{ category }}" title="Show or hide {{ category }} column{{ "s" if "stats" == category else "" }}"><input type="checkbox" id="toggle-{{ category }}" onclick="onToggleCategory('{{ category }}', this)" checked />{{ category.capitalize() }}</label>
%endfor
  </div>
  <input type="search" placeholder="Filter heroes" title="Filter heroes on any matching text" onkeyup="onSearch(event)" onsearch="onSearch(event)">
</div>
<table id="heroes">
  <tr>
    <th class="index asc"><a class="sort asc" title="Sort by index" onclick="onSort(this)">#</a></th>
    <th><a class="sort" title="Sort by name" onclick="onSort(this)">Name</a></th>
%if not categories or categories["stats"]:
    <th><a class="sort" title="Sort by level" onclick="onSort(this)">Level</a></th>
    %for label in metadata.PrimaryAttributes.values():
    <th><a class="sort" title="Sort by {{ label.lower() }}" onclick="onSort(this)">{{ label.split()[-1] }}</a></th>
    %endfor
%endif
%if not categories or categories["devices"]:
    <th><a class="sort" title="Sort by devices" onclick="onSort(this)">Devices</a></th>
%endif
%if not categories or categories["skills"]:
    <th><a class="sort" title="Sort by skills" onclick="onSort(this)">Skills</a></th>
%endif
%if not categories or categories["army"]:
    <th><a class="sort" title="Sort by army" onclick="onSort(this)">Army</a></th>
%endif
%if not categories or categories["artifacts"]:
    <th><a class="sort" title="Sort by artifacts" onclick="onSort(this)">Artifacts</a></th>
%endif
%if not categories or categories["inventory"]:
    <th><a class="sort" title="Sort by inventory" onclick="onSort(this)">Inventory</a></th>
%endif
%if not categories or categories["spells"]:
    <th><a class="sort" title="Sort by spells" onclick="onSort(this)">Spells</a></th>
%endif
  </tr>

%for i, hero in enumerate(heroes):
  <tr>
    <td class="index">{{ i + 1 }}</td>
    <td><a href="#{{ hero.name }}" title="Show {{ hero.name }} character sheet" onclick="showHero({{ i }})">{{ hero.name }}</a></td>
%if not categories or categories["stats"]:
    <td>{{ hero.stats["level"] }}</td>
    %for name in metadata.PrimaryAttributes:
    <td>{{ hero.stats[name] }}</td>
    %endfor
%endif
%if not categories or categories["devices"]:
    <td>
    %for prop in deviceprops:
        %if hero.stats.get(prop["name"]):
        {{ prop["label"] if isinstance(hero.stats[prop["name"]], bool) else hero.stats[prop["name"]] }}<br />
        %endif
    %endfor
    </td>
%endif
%if not categories or categories["skills"]:
    <td>
    %for skill in hero.skills:
    <b>{{ skill["name"] }}:</b> {{ skill["level"] }}<br />
    %endfor
    </td>
%endif
%if not categories or categories["army"]:
    <td>
    %for army in filter(bool, hero.army):
    {{ army["name"] }}: {{ army["count"] }}<br />
    %endfor
    </td>
%endif
%if not categories or categories["artifacts"]:
    <td>
    %for item in filter(bool, hero.artifacts.values()):
    {{ item }}<br />
    %endfor
    </td>
%endif
%if not categories or categories["inventory"]:
    <td>
    %for item in filter(bool, hero.inventory):
    {{ item }}<br />
    %endfor
    </td>
%endif
%if not categories or categories["spells"]:
    <td>
    %for item in hero.spells:
    {{ item }}<br />
    %endfor
    </td>
%endif
  </tr>
%endfor

</table>
</div>
<div id="footer">{{ "Exported with %s on %s." % (conf.Title, datetime.datetime.now().strftime("%d.%m.%Y %H:%M")) }}</div>
<div id="overlay" class="hidden"><div id="overshadow" onclick="showHero()"></div><div id="overbox"><a href="" title="Close" onclick="showHero()">x</a><div id="overcontent"></div></div></div>
</body>
"""
