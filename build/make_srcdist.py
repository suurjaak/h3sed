"""
Creates h3sed source distribution archive from current version in
h3sed\. Sets execute flag permission on .sh files.

@author    Erki Suurjaak
@created   12.04.2020
@modified  09.01.2022
"""
import glob
import os
import sys
import time
import zipfile
import zlib


def pathjoin(*args):
    # Cannot have ZIP system UNIX with paths like Windows
    return "/".join(filter(None, args))


if "__main__" == __name__:
    NAME = "h3sed"
    INITIAL_DIR   = os.getcwd()
    PACKAGING_DIR = os.path.realpath(os.path.dirname(__file__))
    ROOT_DIR      = os.path.dirname(PACKAGING_DIR)

    def add_files(zf, filenames, subdir="", subdir_local=None):
        global BASE_DIR
        size = 0
        for filename in filenames:
            if filename.lower().endswith(".exe"): continue # for filename

            fullpath = os.path.join(BASE_DIR,
                subdir_local if subdir_local is not None else subdir, filename)
            zi = zipfile.ZipInfo()
            zi.filename = pathjoin(ZIP_DIR, subdir, filename)
            zi.date_time = time.localtime(os.path.getmtime(fullpath))[:6]
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.create_system = 3 # UNIX
            zi.external_attr = 0644 << 16L # Permission flag -rw-r--r--
            if os.path.splitext(filename)[-1] in [".sh"]:
                zi.external_attr = 0755 << 16L # Permission flag -rwxr-xr-x
            print("Adding %s, %s bytes" % (zi.filename, os.path.getsize(fullpath)))
            zf.writestr(zi, open(fullpath, "rb").read())
            size += os.path.getsize(fullpath)
        return size

    sys.path.insert(0, os.path.join(ROOT_DIR, "src"))
    from h3sed import conf

    BASE_DIR = ""
    ZIP_DIR = "%s_%s" % (NAME, conf.Version)
    DEST_FILE = "%s_%s-src.zip" % (NAME, conf.Version)
    print("Creating source distribution %s.\n" % DEST_FILE)

    os.chdir(ROOT_DIR)
    CODEPATH = pathjoin("src", NAME)
    with zipfile.ZipFile(os.path.join(INITIAL_DIR, DEST_FILE), mode="w") as zf:
        size = 0
        for subdir, wildcard in [("build", "*"), ("res", "*"),
            (CODEPATH, "*.py"), (pathjoin(CODEPATH, "lib"), "*.py"), 
            (pathjoin(CODEPATH, "lib", "vendor"), "*.py"),
            (pathjoin(CODEPATH, "plugins"), "*"), 
            (pathjoin(CODEPATH, "plugins", "hero"), "*"),
            (pathjoin(CODEPATH, "plugins", "version"), "*"), 
            (pathjoin(CODEPATH, "etc"), "%s.ini" % NAME)
        ]:
            entries = glob.glob(os.path.join(BASE_DIR, subdir, wildcard))
            files = sorted([os.path.basename(x) for x in entries
                          if os.path.isfile(x)], key=str.lower)
            files = filter(lambda x: not x.lower().endswith(".zip"), files)
            files = filter(lambda x: not x.lower().endswith(".pyc"), files)
            size += add_files(zf, files, subdir)
        rootfiles = ["LICENSE.md", "MANIFEST.in", "README.md",
                     "requirements.txt", "setup.py"]
        size += add_files(zf, rootfiles)

    os.chdir(INITIAL_DIR)
    size_zip = os.path.getsize(DEST_FILE)
    print ("\nCreated %s, %s bytes (from %s, %.2f compression ratio)." % 
           (DEST_FILE, size_zip, size, float(size_zip) / size))
