# -*- coding: utf-8 -*-
"""
Version-plugin, provides support for different game versions.

All versions specifics are handled by subplugins in file directory, auto-loaded.


Subplugin modules are expected to have the following API (most methods optional):

    def init():
        '''Called at plugin load.'''

    def detect(savefile):
        '''Mandatory. Returns whether savefile matches game version.'''

    def props():
        '''
        Returns plugin props {name, ?label, ?index}.
        Label is used as plugin tab label, falling back to plugin name.
        Index is used for sorting plugins.
        Icon is wx.Bitmap, used as plugin tab icon in rendering notebook.
        '''

    def adapt(source, category, value):
        '''
        Returns value adapted by plugin specifics.

        @param   source    plugin (or subplugin) requesting adaptation
        @param   category  value category like "props"
        '''

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created   22.03.2020
@modified  22.05.2024
------------------------------------------------------------------------------
"""
import copy
import glob
import importlib
import logging
import os
import re

import wx

from h3sed import conf
from h3sed import gui
from h3sed import images
from h3sed import plugins
from h3sed.lib import util
from h3sed.lib import wx_accel

logger = logging.getLogger(__package__)


PLUGINS = [] # Loaded plugins as [{name, module}, ]


def init():
    """Loads hero plugins list."""
    global PLUGINS
    basefile = os.path.join(conf.PluginDirectory, "version", "__init__.py")
    PLUGINS[:] = plugins.load_modules(__package__, basefile)


def adapt(source, category, value):
    """
    Runs value through adapt() of subplugins.

    @param   source    source plugin or subplugin
    @param   category  value category like "props"
    """
    for p in PLUGINS:
        if callable(getattr(p["module"], "adapt", None)):
            value = p["module"].adapt(source, category, value)
    return value
