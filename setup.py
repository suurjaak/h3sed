# -*- coding: utf-8 -*-
"""
Setup.py for h3sed.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@author      Erki Suurjaak
@created     12.04.2020
@modified    14.04.2020
------------------------------------------------------------------------------
"""
import setuptools

ROOTPATH  = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOTPATH, "src"))

from conf import conf

PACKAGE = conf.Title.lower()


setuptools.setup(
    name=PACKAGE,
    version=conf.Version,
    description="Heroes3 Savegame Editor",
    url="https://github.com/suurjaak/h3sed",

    author="Erki Suurjaak",
    author_email="erki@lap.ee",
    license="MIT",
    platforms=["any"],
    keywords="homm, homm3, heroes3",

    install_requires=["wxPython"],
    entry_points={"gui_scripts": ["h3sed = h3sed.main:run"]},

    package_dir={"": "src"},
    packages=[PACKAGE],
    include_package_data=True, # Use MANIFEST.in for data files
    classifiers=[
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
    ],

    long_description="h3sed is a Heroes3 Savegame Editor, written in Python.",
)
