"""
Simple small script for generating a nicely formatted Python module with
embedded binary resources and docstrings.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     21.03.2020
@modified    11.06.2023
------------------------------------------------------------------------------
"""
import base64
import datetime
import os
import shutil
import wx.tools.img2py

"""Target Python script to write."""
TARGET = os.path.join("..", "src", "h3sed", "images.py")

Q3 = '"""'

LF = "\n"

"""Application icons of different size and colour depth."""
APPICONS = [("Icon_{0}x{0}_{1}bit.png".format(s, b),
             "Heroes3 Savegame Editor application {0}x{0} icon, {1}-bit colour.".format(s, b))
            for s in (16, 24, 32) for b in (32, 16)]
IMAGES = {
    "ExportBg.png":
        "Background pattern image for export HTML.",
    "PageHero.png":
        "Icon for the Hero page in a savefile tab.",
    "ToolbarCopy.png":
        "Toolbar icon for clipboard copy buttons.",
    "ToolbarFileOpen.png":
        "Toolbar icon for open-file buttons.",
    "ToolbarFileSave.png":
        "Toolbar icon for save-file buttons.",
    "ToolbarFileSaveAs.png":
        "Toolbar icon for save-file-as buttons.",
    "ToolbarFolder.png":
        "Toolbar icon for folder buttons.",
    "ToolbarPaste.png":
        "Toolbar icon for clipboard paste buttons.",
    "ToolbarRedo.png":
        "Toolbar icon for undo buttons.",
    "ToolbarRefresh.png":
        "Toolbar icon for refresh button.",
    "ToolbarUndo.png":
        "Toolbar icon for undo buttons.",
}
HEADER = """%s
Contains embedded image and icon resources. Auto-generated.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     21.03.2020
@modified    %s
------------------------------------------------------------------------------
%s
try:
    import wx
    from wx.lib.embeddedimage import PyEmbeddedImage
except ImportError:
    class PyEmbeddedImage(object):
        \"\"\"Data stand-in for wx.lib.embeddedimage.PyEmbeddedImage.\"\"\"
        def __init__(self, data):
            self.data = data
""" % (Q3, datetime.date.today().strftime("%d.%m.%Y"), Q3)


def create_py(target):
    global HEADER, APPICONS, IMAGES
    f = open(target, "wb")
    fwrite = lambda s: f.write(s.replace("\n", LF))
    fwrite(HEADER)
    icons = [os.path.splitext(x)[0] for x, _ in APPICONS]
    icon_parts = [", ".join(icons[2*i:2*i+2]) for i in range(len(icons) / 2)]
    iconstr = ",\n        ".join(icon_parts)
    fwrite("\n\n%s%s%s\ndef get_appicons():\n    icons = wx.IconBundle()\n"
            "    [icons.AddIcon(i.Icon) "
            "for i in [\n        %s\n    ]]\n    return icons\n" % (Q3,
        "Returns the application icon bundle, "
        "for several sizes and colour depths.",
        Q3, iconstr.replace("'", "").replace("[", "").replace("]", "")
    ))
    for filename, desc in APPICONS:
        name, extension = os.path.splitext(filename)
        fwrite("\n\n%s%s%s\n%s = PyEmbeddedImage(\n" % (Q3, desc, Q3, name))
        data = base64.b64encode(open(filename, "rb").read())
        while data:
            fwrite("    \"%s\"\n" % data[:72])
            data = data[72:]
        fwrite(")\n")
    for filename, desc in sorted(IMAGES.items()):
        name, extension = os.path.splitext(filename)
        fwrite("\n\n%s%s%s\n%s = PyEmbeddedImage(\n" % (Q3, desc, Q3, name))
        data = base64.b64encode(open(filename, "rb").read())
        while data:
            fwrite("    \"%s\"\n" % data[:72])
            data = data[72:]
        fwrite(")\n")
    f.close()


if "__main__" == __name__:
    create_py(TARGET)
