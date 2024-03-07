# -*- coding: utf-8 -*-
"""
Plugins framework. All specific functionality is handled by plugin subdirectories
in file directory, auto-loaded.


Plugin modules are expected to have the following API (all methods optional):

    def init():
        '''Called at plugin load.'''

    def props():
        '''
        Returns plugin props {name, ?label, ?index, ?icon}.
        Label is used as plugin tab label, falling back to plugin name.
        Index is used for sorting plugins.
        Icon is wx.Bitmap, used as plugin tab icon in rendering notebook.
        '''

    def factory(savefile, panel, commandprocessor):
        '''
        Returns new plugin instance, if plugin instantiable.

        @param   savefile          data.Savefile instance
        @param   panel             wx.Panel to use for plugin render
        @param   commandprocessor  wx.CommandProcessor for undo-redo
        '''

    def adapt(source, category, value):
        '''
        Returns value adapted by plugin specifics.

        @param   source    plugin (or subplugin) requesting adaptation
        @param   category  value category like "props"
        '''


Plugin instances are expected to have the following API (all methods mandatory except get_changes):

    def render(self, reparse=False, reload=False, log=True):
        '''
        Renders plugin into panel given in factory().

        @param   reparse  whether plugin should re-parse state from savefile
        @param   reload   whether plugin should reload state from current serialization
        @param   log      whether plugin should log actions
        '''

    def get_data(self):
        '''Returns copy of currently selected data (like a hero), for undo-redo.'''

    def set_data(self, data):
        '''Sets currently selected data (like a hero), on undo-redo.'''

    def patch(self):
        '''Serializes current state (like selected hero), and patches savefile binary.'''

    def action(self, **kwargs):
        '''Invokes plugin action, like (load='Adela').'''

    def get_changes(self, html=True):
        '''Optional. Returns unsaved changes, as HTML diff content or plain text brief.'''


------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   14.03.2020
@modified  06.03.2024
------------------------------------------------------------------------------
"""
import os
import glob
import importlib
import logging
import time

import wx

from h3sed import conf
from h3sed.lib import wx_accel

logger = logging.getLogger(__package__)


PLUGINS = [] # Loaded plugins as [{name, module}, ]


def init():
    """Loads main plugins list."""
    global PLUGINS
    basefile = os.path.join(conf.PluginDirectory, "__init__.py")
    PLUGINS[:] = load_modules(__package__, basefile, dirsonly=True)


def load_modules(basepackage, basefile, dirsonly=False):
    """Returns plugins loaded from under package and file."""
    result = []
    myname = os.path.realpath(basefile)
    for f in glob.glob(os.path.join(os.path.dirname(myname), "*")):
        if f == myname or f.endswith("__") or f.endswith(".pyc"): continue # for f
        if dirsonly and not os.path.isdir(f): continue # for f

        name = os.path.splitext(os.path.split(f)[-1])[0]
        modulename = "%s.%s" % (basepackage, name)
        module = importlib.import_module(modulename)
        result.append({"name": name, "module": module})
        if callable(getattr(module, "props", None)):
            result[-1].update(module.props())
    result.sort(key=lambda x: (x.get("index", 1), x["name"]))
    for p in result:
        logger.info("Loading plugin %s.%s.", basepackage, p["name"])
        if callable(getattr(p["module"], "init",  None)): p["module"].init()
    return result


def populate(savefile, notebook, commandprocessor):
    """
    Populates notebook with main plugin tabs, returns plugin instances.

    @return   [plugin instance, ..]
    """
    result = []
    for i, p in enumerate(PLUGINS):
        if not callable(getattr(p["module"], "factory", None)):
            continue # for i, p
        panel = wx.Panel(notebook)
        notebook.AddPage(panel, p.get("label", p["name"]))
        if p.get("icon"):
            try:
                icon = p["icon"]
                if hasattr(icon, "Bitmap"): icon = icon.Bitmap
                idx = notebook.GetImageList().Add(icon)
                notebook.SetPageImage(i, idx)
            except Exception:
                logger.warning("Failed to load plugin '%s' icon.", p["name"])
        result.append(p["module"].factory(savefile, panel, commandprocessor))
    return result


def adapt(source, category, value):
    """
    Runs value through adapt() of any and all plugins.

    @param   source    source plugin or subplugin
    @param   category  value category like "props"
    """
    for p in PLUGINS:
        if callable(getattr(p["module"], "adapt", None)):
            value = p["module"].adapt(source, category, value)
    return value



class PluginCommand(wx.Command):
    """
    Undoable-redoable action by plugin.
    """

    def __init__(self, plugin, do, name=""):
        super(PluginCommand, self).__init__(canUndo=True, name=name)
        self._do = do
        self._done = False
        self._data1 = None
        self._data2 = None
        self._plugin = plugin
        self._timestamp = time.time()

    def Do(self):
        if self._done:
            self._plugin.set_data(self._data2)
            self._plugin.render(reload=True, log=False)
            self._plugin.patch()
        else:
            self._data1 = self._plugin.get_data()
            if self._do():
                self._data2, self._done = self._plugin.get_data(), True
        return self._done

    def Undo(self):
        self._plugin.set_data(self._data1)
        self._plugin.render(reload=True, log=False)
        self._plugin.patch()
        return True

    @property
    def Timestamp(self):
        """Returns command creation timestamp, as UNIX epoch."""
        return self._timestamp
