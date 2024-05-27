"""
Creates h3sed source distribution archive from current version in
h3sed\. Sets execute flag permission on .sh files.

@author    Erki Suurjaak
@created   12.04.2020
@modified  27.05.2024
"""
import glob
import importlib
import os
import sys
import time
import zipfile
import zlib


def pathjoin(*args):
    # Cannot have ZIP system UNIX with paths like Windows
    return "/".join(filter(None, args))


def add_files(zf, filenames, subdir="", basedir="", zipdir="", subdir_local=None):
    """
    Adds files to ZipFile.

    @param   zf            zipfile.ZipFile instance
    @param   filenames     list of file names to add
    @param   subdir        name of filenames directory on disk and in zip
    @param   basedir       path to prepend to subdir/filename for reading file
    @param   zipdir        root directory in zip
    @param   subdir_local  name of filenames directory on disk if different from zip
    """
    size = 0
    for filename in filenames:
        if filename.lower().endswith(".exe"): continue # for filename

        fullpath = os.path.join(basedir,
            subdir_local if subdir_local is not None else subdir, filename)
        zi = zipfile.ZipInfo()
        zi.filename = pathjoin(zipdir, subdir, filename)
        zi.date_time = time.localtime(os.path.getmtime(fullpath))[:6]
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.create_system = 3 # UNIX
        zi.external_attr = 0o644 << 16 # Permission flag -rw-r--r--
        if os.path.splitext(filename)[-1] in [".sh"]:
            zi.external_attr = 0o755 << 16 # Permission flag -rwxr-xr-x
        print("Adding %s, %s bytes" % (zi.filename, os.path.getsize(fullpath)))
        zf.writestr(zi, open(fullpath, "rb").read())
        size += os.path.getsize(fullpath)
    return size


def make_archive(package, wildcards, rootfiles=()):
    """
    Creates a ZIP archive for source package.

    @param   package    package name
    @param   wildcards  list of (subdir, wildcard) to include from package root
    @param   rootfiles  list of single files to include from package root
    """
    INITIAL_DIR = os.getcwd()
    ROOT_DIR    = os.path.dirname(os.path.realpath(os.path.dirname(__file__)))

    sys.path.insert(0, os.path.join(ROOT_DIR, "src"))
    conf = importlib.import_module("%s.conf" % package)

    BASE_DIR  = ""
    ZIP_DIR   = "%s_%s" % (package, conf.Version)
    DEST_FILE = "%s_%s-src.zip" % (package, conf.Version)
    print("Creating source distribution %s.\n" % DEST_FILE)

    os.chdir(ROOT_DIR)
    with zipfile.ZipFile(os.path.join(INITIAL_DIR, DEST_FILE), mode="w") as zf:
        size = 0
        for subdir, wildcard in wildcards:
            entries = glob.glob(os.path.join(BASE_DIR, subdir, wildcard))
            files = sorted([os.path.basename(x) for x in entries if os.path.isfile(x)],
                           key=str.lower)
            files = [x for x in files if not x.lower().endswith("*.pyc")]
            files = [x for x in files if x != os.path.basename(zf.filename)]
            size += add_files(zf, files, subdir, BASE_DIR, ZIP_DIR)
        size += add_files(zf, rootfiles, "", BASE_DIR, ZIP_DIR)

    os.chdir(INITIAL_DIR)
    size_zip = os.path.getsize(DEST_FILE)
    print ("\nCreated %s, %s bytes (from %s, %.2f compression ratio)." % 
           (DEST_FILE, size_zip, size, float(size_zip) / size))



if "__main__" == __name__:
    PACKAGE   = "h3sed"
    CODEPATH  = pathjoin("src", PACKAGE)
    WILDCARDS = [("build", "*"), ("res", "*"),
        (CODEPATH, "*.py"), (pathjoin(CODEPATH, "lib"), "*.py"), 
        (pathjoin(CODEPATH, "lib", "vendor"), "*.py"),
        (pathjoin(CODEPATH, "plugins"), "*"), 
        (pathjoin(CODEPATH, "plugins", "hero"), "*"),
        (pathjoin(CODEPATH, "plugins", "version"), "*"), 
        (pathjoin(CODEPATH, "etc"), "%s.ini" % PACKAGE)
    ]
    ROOTFILES = ["CHANGELOG.md", "LICENSE.md", "MANIFEST.in", "README.md",
                 "requirements.txt", "setup.py"]
    make_archive(PACKAGE, WILDCARDS, ROOTFILES)
