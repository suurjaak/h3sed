# -*- mode: python -*-
"""
Pyinstaller spec file for h3sed, produces a 32-bit or 64-bit executable,
depending on current environment.

Pyinstaller-provided names and variables: Analysis, EXE, PYZ, SPEC, TOC.

@created   12.04.2020
@modified  09.04.2025
"""
import atexit
import os
import struct
import sys

DEBUG = False
NAME = "h3sed"
BUILDPATH = os.path.dirname(os.path.abspath(SPEC))
ROOTPATH  = os.path.dirname(BUILDPATH)
APPPATH   = os.path.join(ROOTPATH, "src", NAME)

sys.path.insert(0, os.path.join(ROOTPATH, "src"))
from h3sed import conf


def cleanup():
    try: os.unlink(entrypoint)
    except Exception: pass


entrypoint = os.path.join(ROOTPATH, "launch.py")
with open(entrypoint, "w") as f:
    f.write("from %s import main; main.run()" % NAME)
atexit.register(cleanup)

a = Analysis(
    [entrypoint],
    excludes=["FixTk", "numpy", "tcl", "tk", "_tkinter", "tkinter", "Tkinter"],
)
a.datas += [("res/3rd-party licenses.txt",  "3rd-party licenses.txt", "DATA")]
a.binaries = a.binaries - TOC([
    ('tcl85.dll', None, None),
    ('tk85.dll',  None, None),
    ('_tkinter',  None, None)
])


is_64bit = (struct.calcsize("P") * 8 == 64)
ext = ".exe" if "nt" == os.name else ""
app_file = "%s_%s%s%s" % (NAME, conf.Version, "" if is_64bit else "_x86", ext)

exe = EXE(
    PYZ(a.pure),
    a.scripts + ([("v", "", "OPTION")] if DEBUG else []),
    a.binaries,
    a.datas,
    name=app_file,

    debug=DEBUG, # Verbose or non-verbose debug statements printed
    exclude_binaries=False, # Binaries not left out of PKG
    strip=False,   # EXE and all shared libraries run through cygwin's strip, tends to render Win32 DLLs unusable
    upx=True,      # Using Ultimate Packer for eXecutables
    console=DEBUG, # Use the Windows subsystem executable instead of the console one
    icon=os.path.join(BUILDPATH, "h3sed.ico"),
)
