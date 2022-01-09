# -*- coding: utf-8 -*-
"""
Setup.py for h3sed.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@author      Erki Suurjaak
@created     12.04.2020
@modified    09.01.2022
------------------------------------------------------------------------------
"""
import os
import re
import sys

import setuptools

ROOTPATH  = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOTPATH, "src"))

from h3sed import conf


PACKAGE = conf.Name.lower()


def readfile(path):
    """Returns contents of path, relative to current file."""
    root = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(root, path)) as f: return f.read()

def get_description():
    """Returns package description from README."""
    LINK_RGX = r"\[([^\]]+)\]\(([^\)]+)\)"  # 1: content in [], 2: content in ()
    linkify = lambda s: "#" + re.sub(r"[^\w -]", "", s).lower().replace(" ", "-")
    # Unwrap local links like [Page link](#page-link) and [LICENSE.md](LICENSE.md)
    repl = lambda m: m.group(1 if m.group(2) in (m.group(1), linkify(m.group(1))) else 0)
    return re.sub(LINK_RGX, repl, readfile("README.md"))


setuptools.setup(
    name                 = PACKAGE,
    version              = conf.Version,
    description          = conf.Title,
    url                  = "https://github.com/suurjaak/h3sed",

    author               = "Erki Suurjaak",
    author_email         = "erki@lap.ee",
    license              = "MIT",
    platforms            = ["any"],
    keywords             = "homm homm3 heroes3 savegame",

    install_requires     = ["wxPython"],
    entry_points         = {"gui_scripts": ["{0} = {0}.main:run".format(PACKAGE)]},

    package_dir          = {"": "src"},
    packages             = [PACKAGE],
    include_package_data = True, # Use MANIFEST.in for data files
    classifiers          = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Unix",
        "Operating System :: MacOS",
        "Topic :: Games/Entertainment",
        "Topic :: Utilities",
        "Topic :: Desktop Environment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
    ],

    long_description_content_type = "text/markdown",
    long_description = get_description(),
)
