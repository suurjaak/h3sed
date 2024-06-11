# -*- coding: utf-8 -*-
"""
h3sed UI application main window class and savepage class.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     14.03.2020
@modified    11.06.2024
------------------------------------------------------------------------------
"""
import datetime
import functools
import logging
import math
import os
import shutil
import sys
import tempfile
import time

import step
import wx
import wx.adv
import wx.html
import wx.lib.agw.flatnotebook
import wx.lib.agw.labelbook
import wx.lib.newevent

from h3sed.lib import controls
from h3sed.lib.controls import ColourManager
from h3sed.lib import util
from h3sed.lib import wx_accel
from h3sed import conf
from h3sed import guibase
from h3sed import images
from h3sed import metadata
from h3sed import plugins
from h3sed import templates

logger = logging.getLogger(__name__)


OpenSavefileEvent, EVT_OPEN_SAVEFILE = wx.lib.newevent.NewCommandEvent()
SavefilePageEvent, EVT_SAVEFILE_PAGE = wx.lib.newevent.NewCommandEvent()
PluginEvent,       EVT_PLUGIN        = wx.lib.newevent.NewCommandEvent()



class MainWindow(guibase.TemplateFrameMixIn, wx.Frame):
    """Program main window."""

    def __init__(self):
        # Override default wx images with ones from 4.1.1 for better looks
        art_imgs = {wx.ART_COPY:  images.ToolbarCopy,  wx.ART_FILE_OPEN: images.ToolbarFileOpen,
                    wx.ART_PASTE: images.ToolbarPaste, wx.ART_FILE_SAVE: images.ToolbarFileSave,
                    wx.ART_UNDO:  images.ToolbarUndo,  wx.ART_FOLDER:    images.ToolbarFolder,
                    wx.ART_FILE_SAVE_AS: images.ToolbarFileSaveAs,
                    wx.ART_REDO:  images.ToolbarRedo} if "win32" == sys.platform else {}
        controls.Patch.patch_wx(art={k: v.Bitmap for k, v in art_imgs.items()})
        wx.Frame.__init__(self, parent=None, title=conf.Title, size=conf.WindowSize)
        guibase.TemplateFrameMixIn.__init__(self)

        ColourManager.Init(self, conf, colourmap={
            "FgColour":                wx.SYS_COLOUR_BTNTEXT,
            "BgColour":                wx.SYS_COLOUR_WINDOW,
            "MainBgColour":            wx.SYS_COLOUR_WINDOW,
            "WidgetColour":            wx.SYS_COLOUR_BTNFACE,
        }, darkcolourmap={
            "LinkColour":              wx.SYS_COLOUR_HOTLIGHT,
            "MainBgColour":            wx.SYS_COLOUR_BTNFACE,
        })

        self.files = {} # {filename: {name, title, savefile, page}, }
        self.page_file_latest = None  # Last opened savefile page
        # List of Notebook pages user has visited, used for choosing page to
        # show when closing one.
        self.pages_visited = []

        icons = images.get_appicons()
        self.SetIcons(icons)
        self.frame_console.SetIcons(icons)

        panel = self.panel_main = wx.Panel(self)
        notebook = self.notebook = wx.lib.agw.flatnotebook.FlatNotebook(panel,
            agwStyle=wx.lib.agw.flatnotebook.FNB_DROPDOWN_TABS_LIST |
                     wx.lib.agw.flatnotebook.FNB_MOUSE_MIDDLE_CLOSES_TABS |
                     wx.lib.agw.flatnotebook.FNB_NO_NAV_BUTTONS |
                     wx.lib.agw.flatnotebook.FNB_NO_TAB_FOCUS |
                     wx.lib.agw.flatnotebook.FNB_NO_X_BUTTON |
                     wx.lib.agw.flatnotebook.FNB_FF2)
        ColourManager.Manage(notebook, "ActiveTabColour",        wx.SYS_COLOUR_WINDOW)
        ColourManager.Manage(notebook, "ActiveTabTextColour",    wx.SYS_COLOUR_BTNTEXT)
        ColourManager.Manage(notebook, "NonActiveTabTextColour", wx.SYS_COLOUR_BTNTEXT)
        ColourManager.Manage(notebook, "TabAreaColour",          wx.SYS_COLOUR_BTNFACE)
        ColourManager.Manage(notebook, "GradientColourBorder",   wx.SYS_COLOUR_BTNSHADOW)
        ColourManager.Manage(notebook, "GradientColourTo",       wx.SYS_COLOUR_ACTIVECAPTION)
        ColourManager.Manage(notebook, "ForegroundColour",       wx.SYS_COLOUR_BTNTEXT)
        ColourManager.Manage(notebook, "BackgroundColour",       wx.SYS_COLOUR_WINDOW)

        self.create_page_main(notebook)
        self.page_log = self.create_log_panel(notebook)
        notebook.AddPage(self.page_log, "Log")
        notebook.RemovePage(notebook.GetPageCount() - 1) # Hide log window
        # Kludge for being able to close log window repeatedly, as SavefilePage
        # get automatically deleted on closing.
        self.page_log.is_hidden = True

        sizer = panel.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(notebook, proportion=1, flag=wx.GROW)
        self.create_menu()
        self.create_toolbar()
        self.populate_statusbar()

        # Memory file system for showing images in wx.HtmlWindow
        self.memoryfs = {"files": {}, "handler": wx.MemoryFSHandler()}
        wx.FileSystem.AddHandler(self.memoryfs["handler"])
        self.load_fs_images()

        self.Bind(EVT_OPEN_SAVEFILE, self.on_open_savefile_event)
        self.Bind(EVT_SAVEFILE_PAGE, self.on_savefile_page_event)

        self.Bind(wx.EVT_CLOSE, self.on_exit)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOVE, self.on_move)
        notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_change_page, notebook)
        notebook.Bind(wx.lib.agw.flatnotebook.EVT_FLATNOTEBOOK_PAGE_CLOSING,
                      self.on_close_page, notebook)
        notebook.Bind(wx.lib.agw.flatnotebook.EVT_FLATNOTEBOOK_PAGE_DROPPED,
                      self.on_dragdrop_page, notebook)


        # Register Ctrl-F4 close and Ctrl-1..9 tab handlers
        def on_close_hotkey(event=None):
            notebook and notebook.DeletePage(notebook.GetSelection())
        def on_tab_hotkey(number, event=None):
            if notebook and notebook.GetSelection() != number \
            and number < notebook.GetPageCount():
                notebook.SetSelection(number)
                self.on_change_page()

        id_close = controls.NewId()
        accelerators = [(wx.ACCEL_CMD, k, id_close) for k in [wx.WXK_F4, ord("W")]]
        for i in range(9):
            id_tab = controls.NewId()
            accelerators += [(wx.ACCEL_CMD, ord(str(i + 1)), id_tab)]
            notebook.Bind(wx.EVT_MENU, functools.partial(on_tab_hotkey, i), id=id_tab)

        notebook.Bind(wx.EVT_MENU, on_close_hotkey, id=id_close)
        notebook.SetAcceleratorTable(wx.AcceleratorTable(accelerators))


        class FileDrop(wx.FileDropTarget):
            """A simple file drag-and-drop handler for application window."""
            def __init__(self, window):
                super(self.__class__, self).__init__()
                self.window = window

            def OnDropFiles(self, x, y, filenames):
                # CallAfter to allow UI to clear up the dragged icons
                wx.CallAfter(self.ProcessFiles, filenames)
                return True

            def ProcessFiles(self, filenames):
                if not self: return
                filenames = filter(os.path.isfile, filenames)
                if filenames: self.window.load_savefile_pages(filenames)

        self.DropTarget     = FileDrop(self)
        notebook.DropTarget = FileDrop(self)

        self.MinSize = conf.MinWindowSize
        if conf.WindowPosition and conf.WindowSize:
            if [-1, -1] != conf.WindowSize:
                self.Size, self.Position = conf.WindowSize, conf.WindowPosition
            else:
                self.Maximize()
        else:
            self.Center(wx.HORIZONTAL)
            self.Position.top = 50
        self.dir_ctrl.SetFocus()
        if conf.Positions.get("filefilter_index") \
        and conf.Positions["filefilter_index"] < len(metadata.wildcard()):
            self.dir_ctrl.UnselectAll()
            self.dir_ctrl.SetFilterIndex(conf.Positions["filefilter_index"])
            self.dir_ctrl.GetFilterListCtrl().Select(conf.Positions["filefilter_index"])
            self.dir_ctrl.ReCreateTree()
        if conf.SelectedPath: self.dir_ctrl.ExpandPath(conf.SelectedPath)

        self.Show(True)
        logger.info("Started application.")
        def after():
            if not self: return
            plugins.init()
        wx.CallAfter(after)


    def create_page_main(self, notebook):
        """Creates the main page with directory list and buttons."""
        page = self.page_main = wx.Panel(notebook)
        ColourManager.Manage(page, "BackgroundColour", "MainBgColour")
        notebook.AddPage(page, "Choose file")
        sizer = page.Sizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        text_file = self.text_file = wx.TextCtrl(page)
        button_open   = self.button_open   = wx.Button(page, label="&Open")
        button_browse = self.button_browse = wx.Button(page, label="&Browse..")
        dir_ctrl = self.dir_ctrl = wx.GenericDirCtrl(page,
            style=wx.DIRCTRL_SHOW_FILTERS, filter=metadata.wildcard(), defaultFilter=0)
        dialog = self.dialog_browse = wx.FileDialog(
            parent=self, message="Select file", wildcard=metadata.wildcard(),
            style=wx.FD_FILE_MUST_EXIST | wx.FD_OPEN | wx.RESIZE_BORDER
        )

        text_file.SetEditable(False)
        button_open.SetDefault()
        button_open.ToolTip = "Open currently selected file"
        button_browse.ToolTip = "Open dialog for selecting a file"
        dir_ctrl.ShowHidden(True)
        choice, tree = dir_ctrl.GetFilterListCtrl(), dir_ctrl.GetTreeCtrl()
        ColourManager.Manage(dir_ctrl, "ForegroundColour", wx.SYS_COLOUR_WINDOWTEXT)
        ColourManager.Manage(dir_ctrl, "BackgroundColour", wx.SYS_COLOUR_WINDOW)
        # Tree colours not get updated automatically from parent control
        ColourManager.Manage(tree, "ForegroundColour", wx.SYS_COLOUR_WINDOWTEXT)
        ColourManager.Manage(tree, "BackgroundColour", wx.SYS_COLOUR_WINDOW)

        page.Bind(wx.EVT_CHAR_HOOK, self.on_refresh_dir_ctrl)
        dir_ctrl.Bind(wx.EVT_DIRCTRL_SELECTIONCHANGED, self.on_change_dir_ctrl)
        dir_ctrl.Bind(wx.EVT_DIRCTRL_FILEACTIVATED,    self.on_open_from_dir_ctrl)
        choice.Bind(wx.EVT_CHOICE,                     self.on_choose_filter)
        button_browse.Bind(wx.EVT_BUTTON,              self.on_browse)
        button_open.Bind(wx.EVT_BUTTON,                self.on_open_current_savefile)

        hsizer.Add(text_file,     border=5, proportion=1, flag=wx.BOTTOM | wx.GROW)
        hsizer.Add(button_open,   border=5, flag=wx.BOTTOM | wx.LEFT)
        hsizer.Add(button_browse, border=5, flag=wx.BOTTOM | wx.LEFT)
        sizer.Add(hsizer, border=10, flag=wx.ALL ^ wx.BOTTOM | wx.GROW)
        sizer.Add(dir_ctrl, border=10, proportion=1, flag=wx.ALL ^ wx.TOP | wx.GROW)

        def after():
            choice.Size = (1, choice.BestSize[1]) # Can be set too high
            page.Sizer.Layout()
        wx.CallAfter(after)


    def create_menu(self):
        """Creates the program menu."""
        menu = wx.MenuBar()
        self.SetMenuBar(menu)

        menu_file = wx.Menu()
        menu.Append(menu_file, "&File")

        menu_open = self.menu_open = menu_file.Append(
            wx.ID_ANY, "&Open savefile...\tCtrl-O", "Choose a savefile to open"
        )
        menu_close = self.menu_close = menu_file.Append(
            wx.ID_ANY, "&Close file\tCtrl-F4", "Close current savefile"
        )
        menu_reload = self.menu_reload = menu_file.Append(
            wx.ID_ANY, "Re&load", "Reload savefile, losing any current changes"
        )
        menu_save = self.menu_save = menu_file.Append(
            wx.ID_ANY, "&Save", "Save the active file"
        )
        menu_save_as = self.menu_save_as = menu_file.Append(
            wx.ID_ANY, "Save &as...", "Save the active file under a new name"
        )
        menu_recent = wx.Menu()
        menu_file.AppendSubMenu(menu_recent, "&Recent files", "Recently opened files")
        menu_file.AppendSeparator()
        menu_recent_hero = wx.Menu()
        menu_file.AppendSubMenu(menu_recent_hero, "Recent &heroes", "Recently opened heroes")
        menu_file.AppendSeparator()
        menu_options = wx.Menu()
        menu_file.AppendSubMenu(menu_options, "Opt&ions")
        menu_backup = self.menu_backup = menu_options.Append(
            wx.ID_ANY, "&Back up files before saving", "Create backup copy of savefile before saving changes",
            kind=wx.ITEM_CHECK
        )
        menu_backup.Check(conf.Backup)
        menu_confirm = self.menu_confirm = menu_options.Append(
            wx.ID_ANY, "&Confirm unsaved changes", "Ask for confirmation on closing files with unsaved changes",
            kind=wx.ITEM_CHECK
        )
        menu_options.AppendSeparator()
        menu_clear = self.menu_clear = menu_options.Append(
            wx.ID_ANY, "Clear &recent items", "Clear recent files and heroes list",
        )
        menu_confirm.Check(conf.ConfirmUnsaved)
        menu_file.AppendSeparator()
        menu_exit = self.menu_exit = \
            menu_file.Append(wx.ID_ANY, "E&xit\tAlt-X", "Exit")


        menu_edit = self.menu_edit = wx.Menu()
        menu.Append(menu_edit, "&Edit")
        menu_undo = self.menu_undo = menu_edit.Append(
            wx.ID_UNDO, "&Undo", "Undo the last action"
        )
        menu_redo = self.menu_redo = menu_edit.Append(
            wx.ID_REDO, "&Redo", "Redo the previously undone action"
        )
        menu_history = self.menu_history = menu_edit.Append(
            wx.ID_ANY, "Command &history", "View current changes done to savegame"
        )
        menu_edit.AppendSeparator()
        menu_changes = self.menu_changes = menu_edit.Append(
            wx.ID_ANY, "Show unsaved &changes", "Show pending changes to savegame"
        )

        menu_help = wx.Menu()
        menu.Append(menu_help, "&Help")

        menu_log = self.menu_log = menu_help.Append(wx.ID_ANY,
            "Show &log window", "Show/hide the log messages window",
            kind=wx.ITEM_CHECK)
        menu_console = self.menu_console = menu_help.Append(wx.ID_ANY,
            "Show Python &console\tCtrl-E",
            "Show/hide a Python shell environment window", kind=wx.ITEM_CHECK)
        menu_help.AppendSeparator()
        menu_about = self.menu_about = menu_help.Append(
            wx.ID_ANY, "&About %s" % conf.Title,
            "Show program information and copyright")

        for x in (menu_close, menu_reload, menu_save, menu_save_as): x.Enable(False)
        for x in menu_edit.MenuItems: x.Enable(False)

        self.history_file = wx.FileHistory(conf.MaxRecentFiles)
        self.history_file.UseMenu(menu_recent)
        for f in conf.RecentFiles[::-1]: self.history_file.AddFileToHistory(f)
        self.Bind(wx.EVT_MENU_RANGE, self.on_recent_file, id=self.history_file.BaseId,
                  id2=self.history_file.BaseId + conf.MaxRecentFiles)
        self.history_hero = controls.ItemHistory(conf.MaxRecentHeroes)
        self.history_hero.UseMenu(menu_recent_hero)
        self.history_hero.Formatter = "\t".join
        for x in conf.RecentHeroes[::-1]: self.history_hero.AddItem(x)
        self.Bind(wx.EVT_MENU_RANGE, self.on_recent_hero, id=self.history_hero.BaseId,
                  id2=self.history_hero.BaseId + conf.MaxRecentHeroes)

        self.Bind(wx.EVT_MENU, self.on_open_savefile,    menu_open)
        self.Bind(wx.EVT_MENU, self.on_close_savefile,   menu_close)
        self.Bind(wx.EVT_MENU, self.on_reload_savefile,  menu_reload)
        self.Bind(wx.EVT_MENU, self.on_save_savefile,    menu_save)
        self.Bind(wx.EVT_MENU, self.on_save_savefile_as, menu_save_as)
        self.Bind(wx.EVT_MENU, self.on_menu_backup,      menu_backup)
        self.Bind(wx.EVT_MENU, self.on_menu_confirm,     menu_confirm)
        self.Bind(wx.EVT_MENU, self.on_clear_recent,     menu_clear)
        self.Bind(wx.EVT_MENU, self.on_exit,             menu_exit)
        self.Bind(wx.EVT_MENU, self.on_undo_savefile,    menu_undo)
        self.Bind(wx.EVT_MENU, self.on_redo_savefile,    menu_redo)
        self.Bind(wx.EVT_MENU, self.on_showhide_log,     menu_log)
        self.Bind(wx.EVT_MENU, self.on_toggle_console,   menu_console)
        self.Bind(wx.EVT_MENU, self.on_about,            menu_about)
        self.Bind(wx.EVT_MENU, self.on_show_changes,     menu_changes)
        self.Bind(wx.EVT_MENU, self.on_open_history,     menu_history)


    def create_toolbar(self):
        """Creates the program toolbar."""
        TOOLS = [("Open",    wx.ID_OPEN,     wx.ART_FILE_OPEN,    self.on_open_savefile),
                 ("Save",    wx.ID_SAVE,     wx.ART_FILE_SAVE,    self.on_save_savefile),
                 ("Save as", wx.ID_SAVEAS,   wx.ART_FILE_SAVE_AS, self.on_save_savefile_as),
                 (),
                 ("Undo",    wx.ID_UNDO,     wx.ART_UNDO,         self.on_undo_savefile),
                 ("Redo",    wx.ID_REDO,     wx.ART_REDO,         self.on_redo_savefile),
                 (),
                 ("Reload",  wx.ID_REFRESH,  "ToolbarRefresh",    self.on_reload_savefile),
                 (),
                 ("Folder",  wx.ID_HARDDISK, wx.ART_FOLDER,       self.on_open_folder)]
        TOOL_HELPS = {wx.ID_OPEN:     "Choose a savefile to open",
                      wx.ID_SAVE:     "Save the active file",
                      wx.ID_SAVEAS:   "Save the active file under a new name",
                      wx.ID_UNDO:     "Undo the last action",
                      wx.ID_REDO:     "Redo the previously undone action",
                      wx.ID_REFRESH:  "Reload savefile, losing any current changes",
                      wx.ID_HARDDISK: "Open file directory in file manager program"}
        tb = self.CreateToolBar(wx.TB_FLAT | wx.TB_HORIZONTAL | wx.TB_TEXT)
        tb.SetToolBitmapSize((20, 20))
        for tool in TOOLS:
            if not tool: tb.AddSeparator()
            if not tool: continue  # for tool
            label, toolid, art, handler = tool
            bmp = getattr(images, art).Bitmap if isinstance(art, str) and hasattr(images, art) else \
                  wx.ArtProvider.GetBitmap(art, wx.ART_TOOLBAR, (16, 16))
            tb.AddTool(toolid, label, bmp, shortHelp=TOOL_HELPS[toolid])
            tb.EnableTool(toolid, False)
            tb.Bind(wx.EVT_TOOL, handler, id=toolid)

        tb.EnableTool(wx.ID_OPEN, True)
        tb.EnableTool(wx.ID_HARDDISK, True)
        tb.Realize()


    def load_fs_images(self):
        """Loads content to MemoryFS."""
        if not self: return
        abouticon = "%s.png" % conf.Title.lower() # Program icon shown in About window
        img = images.Icon_32x32_32bit
        if abouticon in self.memoryfs["files"]:
            self.memoryfs["handler"].RemoveFile(abouticon)
        self.memoryfs["handler"].AddFile(abouticon, img.Image, wx.BITMAP_TYPE_PNG)
        self.memoryfs["files"][abouticon] = 1


    def load_savefile(self, filename, silent=False):
        """
        Tries to load the specified savefile, returns (Savefile instance, error).

        @param   silent  if true, no error popups on failing to open the file
        """
        savefile, err = None, None
        if os.path.exists(filename):
            try:
                savefile = metadata.Savefile(filename)
            except Exception as e:
                err = e
                logger.exception("Error opening %s.", filename)
                if not silent:
                    wx.MessageBox("Error opening %s.\n\n%s" % (filename, e),
                                  conf.Title, wx.OK | wx.ICON_ERROR)
            if savefile:
                # Add filename to Recent Files menu and conf, if needed
                if filename in conf.RecentFiles: # Remove earlier position
                    idx = conf.RecentFiles.index(filename)
                    try: self.history_file.RemoveFileFromHistory(idx)
                    except Exception: pass
                self.history_file.AddFileToHistory(filename)
                util.add_unique(conf.RecentFiles, filename, -1,
                                conf.MaxRecentFiles)
                conf.save()
        elif not silent:
            err = ValueError("No such file.")
            wx.MessageBox("Nonexistent file: %s." % filename,
                          conf.Title, wx.OK | wx.ICON_ERROR)
        return savefile, err


    def load_savefile_page(self, filename, savefile=None):
        """
        Tries to load the specified file, if not already open, create a
        subpage for it, if not already created, and focuses the subpage.

        @param   savefile  opened Savefile instance, if any
        @return            savefile page instance
        """
        opts = self.files.get(filename) or {}
        page = opts.get("page")
        if page:
            for i in range(self.notebook.GetPageCount()):
                if self.notebook.GetPage(i) == page:
                    self.notebook.SetSelection(i)
                    break # for i
            self.on_change_page()
            return

        savefile = savefile or self.load_savefile(filename)[0]
        if not savefile: return

        guibase.status("Opening page for %s." % filename, flash=True)
        tab_title = self.get_unique_tab_title(filename)
        opts.update(filename=filename, savefile=savefile, title=tab_title)
        page = opts["page"] = SavefilePage(self.notebook, tab_title, savefile)
        self.files[filename] = opts
        conf.FilesOpen.add(filename)
        conf.SelectedPath = filename
        self.dir_ctrl.ExpandPath(conf.SelectedPath)
        conf.save()
        for i in range(self.notebook.GetPageCount()):
            if self.notebook.GetPage(i) == page:
                self.notebook.SetSelection(i)
                wx.CallAfter(self.update_notebook_header)
                break # for i
        self.SendSizeEvent() # DirCtrl choice may need resizing
        return page


    def load_savefile_pages(self, filenames):
        """
        Tries to load the specified savefiles, if not already open, create
        subpages for them, if not already created, and focus the subpages.
        Skips files that are not recognizable as savefiles.
        """
        savefiles, notsave_filenames, files0 = {}, [], set(self.files)
        for f in filenames:
            if f in self.files: savefile, err = self.files[f]["savefile"], None
            else: savefile, err = self.load_savefile(f, silent=True)
            if savefile: savefiles[f] = savefile
            else:
                notsave_filenames.append(f)
                err = err if isinstance(err, ValueError) else "Not a valid gzipped file?"
                guibase.status("Failed to open %s. %s", f, err, log=True, flash=True)

        for filename, savefile in savefiles.items():
            self.load_savefile_page(filename, savefile)
        if notsave_filenames:
            t = "valid savefiles"
            if len(notsave_filenames) == 1: t = "a " + t[:-1]
            wx.MessageBox("Not %s:\n\n%s" % (t, "\n".join(notsave_filenames)),
                          conf.Title, wx.OK | wx.ICON_ERROR)


    def populate_statusbar(self):
        """Adds file status fields to program statusbar."""
        self.StatusBar.SetFieldsCount(3)
        extent1 = self.StatusBar.GetTextExtent("222.22 KB")[0]
        extent2 = self.StatusBar.GetTextExtent("2222-22-22 22:22:22")[0]
        WPLUS = 10 if "nt" == os.name else 30
        self.StatusBar.SetStatusStyles([wx.SB_SUNKEN] * 3)
        self.StatusBar.SetStatusWidths([-2, extent1 + WPLUS, extent2 + WPLUS])


    def get_unique_tab_title(self, title):
        """
        Returns a title that is unique for the current notebook - if the
        specified title already exists, appends a counter to the end,
        e.g. "..longpath\myname.gm1 (2)". Title is shortened from the left
        if longer than allowed.
        """
        if len(title) > conf.MaxTabTitleLength:
            title = "..%s" % title[-conf.MaxTabTitleLength:]
        all_titles = [self.notebook.GetPageText(i)
                      for i in range(self.notebook.GetPageCount())]
        return util.make_unique(title, all_titles, suffix=" (%s)", case=True)


    def update_notebook_header(self):
        """
        Removes or adds X to notebook tab style, depending on whether current
        page can be closed.
        """
        if not self: return

        p = self.notebook.GetCurrentPage()
        style = self.notebook.GetAGWWindowStyleFlag()
        if isinstance(p, SavefilePage):
            if not style & wx.lib.agw.flatnotebook.FNB_X_ON_TAB:
                style |= wx.lib.agw.flatnotebook.FNB_X_ON_TAB
        elif self.page_log == p:
            style |= wx.lib.agw.flatnotebook.FNB_X_ON_TAB
        elif style & wx.lib.agw.flatnotebook.FNB_X_ON_TAB: # Hide close box
            style ^= wx.lib.agw.flatnotebook.FNB_X_ON_TAB  # on main page
        if style != self.notebook.GetAGWWindowStyleFlag():
            self.notebook.SetAGWWindowStyleFlag(style)


    def update_title(self, page):
        """Updates program title with name and state of given page."""
        subtitle = ""
        if isinstance(page, SavefilePage):
            path, file = os.path.split(page.filename)
            # Use parent/file.gm1 or C:/file.gm1
            subtitle = os.path.join(os.path.split(path)[-1] or path, file)
            if page.get_unsaved(): subtitle += " *"
        self.Title = " - ".join(filter(bool, (conf.Title, subtitle)))


    def update_toolbar(self, page):
        """Updates program toolbar for given page."""
        if not page: return
        for i in range(self.ToolBar.ToolsCount):
            self.ToolBar.EnableTool(self.ToolBar.GetToolByPos(i).Id, False)
        self.ToolBar.EnableTool(wx.ID_OPEN,     True)
        self.ToolBar.EnableTool(wx.ID_HARDDISK, True)
        if isinstance(page, SavefilePage):
            self.ToolBar.EnableTool(wx.ID_SAVE,    True)
            self.ToolBar.EnableTool(wx.ID_SAVEAS,  True)
            self.ToolBar.EnableTool(wx.ID_UNDO,    page.undoredo.CanUndo())
            self.ToolBar.EnableTool(wx.ID_REDO,    page.undoredo.CanRedo())
            self.ToolBar.EnableTool(wx.ID_SAVEAS,  True)
            self.ToolBar.EnableTool(wx.ID_REFRESH, True)


    def on_change_page(self, event=None):
        """
        Handler for changing a page in the main Notebook, remembers the visit.
        """
        if getattr(self, "_ignore_paging", False): return
        if event: event.Skip() # Pass event along to next handler
        page = self.notebook.GetCurrentPage()
        if not self.pages_visited or self.pages_visited[-1] != page:
            self.pages_visited.append(page)

        for x in (self.menu_close, self.menu_reload, self.menu_save, self.menu_save_as,
                  self.menu_undo, self.menu_redo, self.menu_changes, self.menu_history):
            x.Enable(False)
        self.Title, subtitle = conf.Title, ""

        if isinstance(page, SavefilePage):
            self.page_file_latest = page
            for x in (self.menu_close, self.menu_reload, self.menu_save, self.menu_save_as):
                x.Enable(True)
            self.menu_changes.Enable(page.get_unsaved())
            self.menu_history.Enable(bool(page.undoredo.Commands))
            page.undoredo.SetEditMenu(self.menu_edit)
            page.undoredo.SetMenuStrings()
        self.update_toolbar(page)
        self.update_fileinfo()
        self.update_title(page)
        wx.CallAfter(self.update_notebook_header)


    def on_dragdrop_page(self, event=None):
        """
        Handler for dragging notebook tabs, keeps main-tab first and log-tab last.
        """
        self.notebook.Freeze()
        self._ignore_paging = True
        try:
            cur_page = self.notebook.GetCurrentPage()
            idx_main = self.notebook.GetPageIndex(self.page_main)
            if idx_main > 0:
                text = self.notebook.GetPageText(idx_main)
                self.notebook.RemovePage(idx_main)
                self.notebook.InsertPage(0, page=self.page_main, text=text)
            idx_log = self.notebook.GetPageIndex(self.page_log)
            if 0 <= idx_log < self.notebook.GetPageCount() - 1:
                text = self.notebook.GetPageText(idx_log)
                self.notebook.RemovePage(idx_log)
                self.notebook.AddPage(page=self.page_log, text=text)
            if self.notebook.GetCurrentPage() != cur_page:
                self.notebook.SetSelection(self.notebook.GetPageIndex(cur_page))
        finally:
            delattr(self, "_ignore_paging")
            self.notebook.Thaw()


    def on_size(self, event=None):
        """Handler for window size event, saves size, fixes layout."""
        if event: event.Skip()
        conf.WindowSize = [-1, -1] if self.IsMaximized() else self.Size[:]
        conf.save()
        def after():
            choice = self.dir_ctrl.GetFilterListCtrl()
            choice.Size = (1, choice.BestSize[1]) # Can be set too high
            self.page_main.Sizer.Layout()
        wx.CallAfter(after)


    def on_move(self, event):
        """Handler for window move event, saves position."""
        event.Skip()
        if not self.IsIconized():
            conf.WindowPosition = event.Position[:]
            conf.save()


    def on_showhide_log(self, event=None):
        """Handler for clicking to show/hide the log window."""
        if self.notebook.GetPageIndex(self.page_log) < 0:
            self.notebook.AddPage(self.page_log, "Log")
            self.page_log.is_hidden = False
            self.page_log.Show()
            self.notebook.SetSelection(self.notebook.GetPageCount() - 1)
            self.on_change_page()
            self.menu_log.Check(True)
        elif self.notebook.GetPageIndex(self.page_log) != self.notebook.GetSelection():
            self.notebook.SetSelection(self.notebook.GetPageCount() - 1)
            self.on_change_page()
            self.menu_log.Check(True)
        else:
            self.page_log.is_hidden = True
            self.notebook.RemovePage(self.notebook.GetPageIndex(self.page_log))
            self.menu_log.Check(False)


    def on_savefile_page_event(self, event):
        """Handler for notification from SavefilePage, updates UI."""
        page, idx = event.source, self.notebook.GetPageIndex(event.source)

        if all(getattr(event, k, None) for k in ("plugin", "load")) and "hero" == event.plugin:
            item = [event.load, page.filename]
            self.history_hero.AddItem(item)
            util.add_unique(conf.RecentHeroes, item, -1, conf.MaxRecentHeroes)
            conf.save()
            return

        ready, modified, rename = (getattr(event, x, None) for x in ("ready", "modified", "rename"))
        filename1, filename2 = (getattr(event, x, None) for x in ("filename1", "filename2"))

        if filename1 and filename2 and filename1 in self.files:
            self.files[filename2] = self.files.pop(filename1)
            self.files[filename2]["filename"] = filename2

        if ready or rename: self.update_notebook_header()

        self.update_fileinfo()
        self.menu_changes.Enable(page.get_unsaved())
        self.menu_history.Enable(bool(page.undoredo.Commands))

        if modified is not None or rename:
            suffix = "*" if modified else ""
            title1 = not rename and self.files[event.source.filename].get("title") \
                     or self.get_unique_tab_title(event.source.filename)
            self.files[event.source.filename]["title"] = title1
            title2 = title1 + suffix
            if self.notebook.GetPageText(idx) != title2:
                self.notebook.SetPageText(idx, title2)
            self.update_toolbar(page)
            self.update_title(page)


    def on_undo_savefile(self, event=None):
        """Handler for clicking undo, invokes current page CommandProcessor."""
        page = self.notebook.GetCurrentPage()
        if not isinstance(page, SavefilePage) and len(self.files) == 1:
            page = next(iter(self.files.values()))["page"]
        if isinstance(page, SavefilePage) and page.undoredo.CanUndo():
            guibase.status("Undoing %s" % page.undoredo.CurrentCommand.Name,
                           flash=conf.StatusShortFlashLength, log=True)
            page.undoredo.Undo()


    def on_redo_savefile(self, event=None):
        """Handler for clicking redo, invokes current page CommandProcessor."""
        page = self.notebook.GetCurrentPage()
        if not isinstance(page, SavefilePage) and len(self.files) == 1:
            page = next(iter(self.files.values()))["page"]
        if isinstance(page, SavefilePage) and page.undoredo.CanRedo():
            cmdpos = 0 if not page.undoredo.CurrentCommand else \
                     page.undoredo.Commands.index(page.undoredo.CurrentCommand) + 1
            guibase.status("Redoing %s" % page.undoredo.Commands[cmdpos].Name,
                           flash=conf.StatusShortFlashLength, log=True)
            page.undoredo.Redo()


    def on_menu_backup(self, event):
        """Handler for clicking to toggle backup-option."""
        conf.Backup = event.IsChecked()
        conf.save()


    def on_menu_confirm(self, event):
        """Handler for clicking to toggle confirm-option."""
        conf.ConfirmUnsaved = event.IsChecked()
        conf.save()


    def on_clear_recent(self, event):
        """Handler for clearing recent files and heroes list."""
        while self.history_file.Count: self.history_file.RemoveFileFromHistory(0)
        self.history_hero.Clear()
        conf.RecentFiles, conf.RecentHeroes = [], []
        conf.save()


    def on_show_changes(self, event=None):
        """Handler for clicking to show unsaved changes, pops up info dialog."""        
        page = self.notebook.GetCurrentPage()
        if isinstance(page, SavefilePage): page.show_changes()


    def on_open_history(self, event=None):
        """Handler for clicking to show command history, pops up history dialog."""
        page = self.notebook.GetCurrentPage()
        if not isinstance(page, SavefilePage): return
        dlg = controls.CommandHistoryDialog(self, page.undoredo)
        if dlg.ShowModal() != wx.ID_OK: return

        count, cando, do = dlg.GetSelection(), page.undoredo.CanUndo, page.undoredo.Undo
        if count >= 0: cando, do = page.undoredo.CanRedo, page.undoredo.Redo
        verb = "Undo" if count < 0 else "Redo"
        guibase.status("%sing %s", verb, util.plural("action", abs(count)),
                       flash=conf.StatusShortFlashLength, log=True)
        for _ in range(abs(count)):
            if not cando(): break  # for
            cmd = page.undoredo.CurrentCommand or page.undoredo.Commands[0]
            if count >= 0 and page.undoredo.CurrentCommand:
                cmd = page.undoredo.Commands[page.undoredo.Commands.index(cmd) + 1]
            guibase.status("%sing %s", verb, cmd.Name, flash=conf.StatusShortFlashLength, log=True)
            do()


    def on_about(self, event=None):
        """Handler for clicking "About program" menu, opens a small info frame."""
        maketext = lambda: step.Template(templates.ABOUT_HTML).expand()
        controls.HtmlDialog(self, "About %s" % conf.Title, maketext).ShowModal()


    def on_browse(self, event=None):
        """Handler for clicking Browse-button, opens file dialog."""
        if wx.ID_OK != self.dialog_browse.ShowModal(): return
        self.dir_ctrl.SetPath(self.dialog_browse.GetPath())


    def on_choose_filter(self, event):
        """Handler for choosing extension filter in file control."""
        if event.Selection == conf.Positions["filefilter_index"]:
            return
        if event: event.Skip() # Pass event along to next handler
        conf.Positions["filefilter_index"] = event.Selection
        path = self.dir_ctrl.Path
        # Workaround for DirCtrl raising error if any selection during populate
        self.dir_ctrl.UnselectAll()
        wx.CallAfter(lambda: self and self.dir_ctrl.ExpandPath(path))


    def on_save_savefile(self, event=None):
        """Handler for clicking to save changes to the active file."""
        page = self.notebook.GetCurrentPage()
        if not isinstance(page, SavefilePage) and len(self.files) == 1:
            page = next(iter(self.files.values()))["page"]
        if isinstance(page, SavefilePage): page.save_file()


    def on_save_savefile_as(self, event=None):
        """
        Handler for clicking to save the active savefile under a new name,
        opens a save as dialog, copies file and commits unsaved changes.
        """
        page = self.notebook.GetCurrentPage()
        if not isinstance(page, SavefilePage) and len(self.files) == 1:
            page = next(iter(self.files.values()))["page"]
        if isinstance(page, SavefilePage): page.save_file(rename=True)


    def on_close_savefile(self, event=None):
        """
        Handler for close savefile menu, asks for confirmation if changed.
        """
        page = self.notebook.GetCurrentPage()
        if not isinstance(page, SavefilePage) and len(self.files) == 1:
            page = next(iter(self.files.values()))["page"]
        if isinstance(page, SavefilePage):
            self.notebook.DeletePage(self.notebook.GetPageIndex(page))


    def on_reload_savefile(self, event=None):
        """
        Handler for reload savefile menu, asks for confirmation before reloading.
        """
        page = self.notebook.GetCurrentPage()
        if not isinstance(page, SavefilePage) and len(self.files) == 1:
            page = next(iter(self.files.values()))["page"]
        if isinstance(page, SavefilePage): page.reload_file()


    def on_open_savefile(self, event=None):
        """
        Handler for open savefile menu or button, displays a file dialog and
        loads the chosen file.
        """
        dialog = wx.FileDialog(self, message="Open", wildcard=metadata.wildcard(),
            style=wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE | wx.FD_OPEN | wx.RESIZE_BORDER
        )
        if wx.ID_OK == dialog.ShowModal():
            self.load_savefile_pages(dialog.GetPaths())


    def on_open_savefile_event(self, event):
        """Handler for OpenSavefileEvent, loads the event savefile."""
        self.load_savefile_pages([os.path.realpath(event.filename)])


    def on_open_folder(self, event=None):
        """Opens folder to savefile location."""
        page = self.notebook.GetCurrentPage()
        filename = page.filename if isinstance(page, SavefilePage) else self.dir_ctrl.GetPath()
        util.select_file(filename)


    def on_recent_file(self, event):
        """Handler for clicking an entry in Recent Files menu."""
        filename = self.history_file.GetHistoryFile(event.Id - self.history_file.BaseId)
        self.load_savefile_page(filename)


    def on_recent_hero(self, event):
        """Handler for clicking an entry in Recent Heroes menu."""
        heroname, filename = self.history_hero.GetItem(event.Id - self.history_hero.BaseId)
        self.load_savefile_page(filename)
        if filename in self.files:
            self.files[filename]["page"].plugin_action("hero", load=heroname)


    def on_change_dir_ctrl(self, event):
        """Handler for selecting a file in dir list, refreshes file controls."""
        filename = event.EventObject.GetPath()
        self.text_file.Value = filename if os.path.isfile(filename) else ""
        self.button_open.Enable(os.path.isfile(filename))
        self.update_fileinfo()


    def update_fileinfo(self):
        """Updates file data in statusbar."""
        sz, dt, page, filename = "", "", self.notebook.GetCurrentPage(), None
        if self.notebook.GetCurrentPage() is self.page_main: filename = self.dir_ctrl.GetPath()
        elif isinstance(page, SavefilePage): filename = page.filename
        if filename and os.path.isfile(filename):
            sz = util.format_bytes(os.path.getsize(filename))
            stamp = datetime.datetime.fromtimestamp(os.path.getmtime(filename))
            dt = stamp.strftime("%Y-%m-%d %H:%M:%S")
        self.StatusBar.SetStatusText(sz, 1)
        self.StatusBar.SetStatusText(dt, 2)


    def on_open_current_savefile(self, event=None):
        """Handler for clicking to open selected file from dir list."""
        if os.path.isfile(self.dir_ctrl.GetPath()):
            self.load_savefile_pages([self.dir_ctrl.GetPath()])


    def on_open_from_dir_ctrl(self, event):
        """Handler for clicking to open selected files from directory list."""
        self.load_savefile_pages([event.EventObject.GetPath()])


    def on_refresh_dir_ctrl(self, event):
        """Handler for pressing F5 on directory tab, refreshes contents."""
        event and event.Skip()
        if isinstance(event, wx.KeyEvent) and wx.WXK_F5 != event.KeyCode: return
        path = self.dir_ctrl.Path
        self.page_main.Freeze()
        try:
            # Workaround for DirCtrl raising error if any selection during populate
            self.dir_ctrl.UnselectAll()
            self.dir_ctrl.ReCreateTree()
            self.dir_ctrl.ExpandPath(path)
        finally:
            self.page_main.Thaw()


    def on_exit(self, event=None):
        """
        Handler on application exit, asks about unsaved changes, if any.
        """
        unsaved_pages = {} # {SavefilePage: filename, }
        for fn, opts in self.files.items() if conf.ConfirmUnsaved else ():
            if not opts.get("page"): continue # for fn, opts
            if opts["page"].get_unsaved(): unsaved_pages[fn] = opts["page"]

        if unsaved_pages:
            resp = wx.MessageBox(
                "There are unsaved changes in %s:\n\n%s\n\n"
                "Do you want to save the changes?" % (
                    util.plural("file", unsaved_pages, single="this"),
                    "\n".join(sorted(unsaved_pages))
                ),
                conf.Title, wx.YES | wx.NO | wx.CANCEL | wx.ICON_INFORMATION
            )
            if wx.CANCEL == resp: return
            for fn, page in unsaved_pages.items() if wx.YES == resp else ():
                if not page.save_file(): return

        conf.SelectedPath = self.dir_ctrl.GetPath()
        if not self.IsIconized(): conf.WindowPosition = self.Position[:]
        conf.WindowSize = [-1, -1] if self.IsMaximized() else self.Size[:]
        conf.save()
        self.Hide()
        sys.exit()


    def on_close_page(self, event):
        """
        Handler for closing a page, asks the user about saving unsaved data,
        if any, removes page from main notebook.
        """
        if getattr(self, "_ignore_paging", False): return
        if event.EventObject == self.notebook:
            page = self.notebook.GetPage(event.GetSelection())
        else:
            page = event.EventObject
            page.Show(False)
        if self.page_log == page:
            if not self.page_log.is_hidden:
                event.Veto() # Veto delete event
                self.on_showhide_log(None) # Fire remove event
            self.pages_visited = [x for x in self.pages_visited if x != page]
            self.page_log.Show(False)
            return
        elif not isinstance(page, SavefilePage): return event.Veto()

        if conf.ConfirmUnsaved and page.get_unsaved():
            msg = "%s has modifications.\n\n" % page.filename
            resp = wx.MessageBox(msg + "Do you want to save the changes?", conf.Title,
                                 wx.YES | wx.NO | wx.CANCEL | wx.ICON_INFORMATION)
            if wx.CANCEL == resp: return event.Veto()
            if wx.YES == resp:
                if not page.save_file(): return event.Veto()

        page.undoredo.ClearCommands()
        page.undoredo.SetMenuStrings()

        self.files.pop(page.filename, None)
        conf.FilesOpen.discard(page.filename)
        logger.info("Closed tab for %s.", page.filename)
        conf.save()

        # Remove any dangling references
        self.pages_visited = [x for x in self.pages_visited if x != page]
        if self.page_file_latest == page:
            self.page_file_latest = next((i for i in self.pages_visited[::-1]
                                        if isinstance(i, SavefilePage)), None)
        self.SendSizeEvent() # Multiline wx.Notebooks need redrawing

        # Change notebook page to last visited
        index_new = 0
        if self.pages_visited:
            for i in range(self.notebook.GetPageCount()):
                if self.notebook.GetPage(i) == self.pages_visited[-1]:
                    index_new = i
                    break
        self.notebook.SetSelection(index_new)



class SavefilePage(wx.Panel):
    """
    A notebook page for managing a single savefile, has its own
    Notebook with a number of pages for various editing.
    """

    def __init__(self, parent_notebook, title, savefile):
        wx.Panel.__init__(self, parent_notebook)

        self.savefile = savefile
        self.filename = savefile.filename
        self.plugins = [] # Instantiated plugins
        self.edit_name = None
        self.edit_desc = None
        self.edit_vers = None
        self.undoredo = wx.CommandProcessor()
        self.undoredo.MarkAsSaved()

        parent_notebook.InsertPage(1, self, title)
        busy = controls.BusyPanel(self, 'Loading "%s".' % self.filename)
        ColourManager.Manage(self, "BackgroundColour", "WidgetColour")

        splitter = wx.SplitterWindow(self, style=wx.BORDER_NONE)
        filepanel = wx.Panel(splitter)

        nlabel = wx.StaticText(filepanel, label="Map:", name="label_name")
        nctrl  = self.edit_name = wx.TextCtrl(filepanel, style=wx.BORDER_NONE, name="name")
        vlabel = wx.StaticText(filepanel, label="Game version:", name="label_version")
        vctrl = self.edit_vers = wx.TextCtrl(filepanel, style=wx.BORDER_NONE, name="version")
        dlabel = wx.StaticText(filepanel, label="Description:", name="label_desc")
        dctrl  = self.edit_desc = wx.TextCtrl(filepanel, style=wx.TE_MULTILINE | wx.BORDER_NONE, name="desc")

        for c in (nctrl, vctrl, dctrl): c.SetEditable(False), c.SetMargins(0)
        dctrl.MinSize = -1, nctrl.Size.Height
        SASH_DEFAULTPOS = 2 * nctrl.Size.Height + 10
        SASH_STARTPOS = conf.Positions.get("savepage_splitter") or SASH_DEFAULTPOS

        bookstyle = wx.lib.agw.fmresources.INB_LEFT
        if (wx.version().startswith("2.8") and sys.version_info.major == 2
        and sys.version_info < (2, 7, 3)):
            # wx 2.8 + Python below 2.7.3: labelbook can partly cover tab area
            bookstyle |= wx.lib.agw.fmresources.INB_FIT_LABELTEXT
        notebook = self.notebook = wx.lib.agw.labelbook.FlatImageBook(
            splitter, agwStyle=bookstyle, style=wx.BORDER_STATIC)
        il = wx.ImageList(32, 32)
        il.Add(images.Icon_32x32_32bit.Bitmap)
        notebook.AssignImageList(il)

        self.TopLevelParent.page_file_latest = self
        self.Bind(EVT_SAVEFILE_PAGE, self.on_page_event)
        splitter.Bind(wx.EVT_SPLITTER_DCLICK, lambda e: (splitter.SetSashPosition(SASH_DEFAULTPOS),
                      conf.Positions.update(savepage_splitter=SASH_DEFAULTPOS)))
        splitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED,
                      lambda e: conf.Positions.update(savepage_splitter=e.SashPosition))
        self.TopLevelParent.run_console("page = self.page_file_latest # Savefile tab")

        sizer = self.Sizer = wx.BoxSizer(wx.VERTICAL)
        filepanel.Sizer = wx.BoxSizer(wx.VERTICAL)
        isizer = wx.GridBagSizer(hgap=5, vgap=2)
        isizer.SetCols(4)
        isizer.AddGrowableCol(1)
        isizer.AddGrowableRow(1)

        isizer.Add(nlabel, pos=(0, 0), border=5, flag=wx.LEFT)
        isizer.Add(nctrl,  pos=(0, 1), flag=wx.GROW)
        isizer.Add(vlabel, pos=(0, 2))
        isizer.Add(vctrl,  pos=(0, 3))
        isizer.Add(dlabel, pos=(1, 0), border=5, flag=wx.LEFT)
        isizer.Add(dctrl,  pos=(1, 1), span=(1, 3), flag=wx.GROW)

        filepanel.Sizer.Add(isizer, border=5, flag=wx.GROW | wx.TOP, proportion=1)
        sizer.Add(splitter, proportion=1, border=5, flag=wx.GROW | wx.ALL)
        splitter.SetMinimumPaneSize(nctrl.Size.Height + 8)
        splitter.SplitHorizontally(filepanel, notebook, sashPosition=SASH_STARTPOS)
        self.Layout()

        wx_accel.accelerate(self)
        try:
            self.load_data()
            guibase.status("Opened %s." % self.filename, flash=True)
        finally:
            busy.Close()


    def get_unsaved(self):
        """Returns whether page has unsaved changes."""
        return self.savefile.is_changed()


    def reload_file(self):
        """Asks for confirmation if changed and reloads current file."""
        if self.savefile.is_changed() and wx.CANCEL == wx.MessageBox(
            "Are you sure you want to lose all changes?", conf.Title,
            wx.OK | wx.CANCEL | wx.ICON_INFORMATION
        ): return
        try: self.savefile.read()
        except Exception as e:
            logger.exception("Error reloading %s.", self.filename)
            return wx.MessageBox("Error reloading %s:\n\n%s" %
                                 (self.filename, util.format_exc(e)),
                                 wx.OK | wx.ICON_ERROR)
        self.undoredo.ClearCommands()
        self.undoredo.SetMenuStrings()
        evt = SavefilePageEvent(self.Id, source=self, modified=False)
        wx.PostEvent(self.Parent, evt)
        busy = controls.BusyPanel(self.Parent, "Reloading file.")
        self.Freeze()
        try:
            self.update_metadata()
            for p in self.plugins: p.render(reparse=True)
            self.SendSizeEvent()
        finally:
            self.Thaw()
            busy.Close()


    def save_file(self, rename=False):
        """Saves the file, under a new name if specified, returns success."""
        filename1, filename2, tempname, error = self.filename, self.filename, None, None

        if rename:
            title = "Save %s as.." % os.path.split(self.filename)[-1]
            dialog = wx.FileDialog(self,
                message=title, wildcard=metadata.wildcard(),
                defaultDir=os.path.split(self.filename)[0],
                defaultFile=os.path.basename(self.filename),
                style=wx.FD_OVERWRITE_PROMPT | wx.FD_SAVE | wx.RESIZE_BORDER
            )
            if wx.ID_OK != dialog.ShowModal(): return

            filename2 = dialog.GetPath()
            if filename1 != filename2 and filename2 in conf.FilesOpen: return wx.MessageBox(
                "%s is already open in %s." % (filename2, conf.Title),
                conf.Title, wx.OK | wx.ICON_WARNING
            )
        rename = (filename1 != filename2)
        logger.info("Saving %s%s.", filename1, " as %s" % filename2 if rename else "")
        changes = "\n\n".join(p.get_changes(html=False) for p in self.plugins
                              if hasattr(p, "get_changes"))
        if changes: logger.info("Saving changes:\n\n%s", changes)

        if rename:
            # Use a tertiary file in case something fails
            fh, tempname = tempfile.mkstemp(".gm1")
            os.close(fh)

        try:
            if rename: shutil.copy(filename1, tempname)
        except Exception as e:
            logger.exception("Error saving %s as %s.", filename1, filename2)
            try: os.unlink(tempname)
            except Exception: pass
            wx.MessageBox("Error saving %s as %s:\n\n%s" %
                          (filename1, filename2, util.format_exc(e)),
                          conf.Title, wx.OK | wx.ICON_ERROR)
            return

        if conf.Backup and os.path.exists(filename2):
            backupname = "%s.%s" % (filename2, datetime.datetime.now().strftime("%Y%m%d"))
            if os.path.exists(backupname):
                logger.info("Skipping saving backup file, %s already exists.", backupname) 
            else:
                logger.info("Saving backup file %s.", backupname)
                try:
                    shutil.copy(filename2, backupname)
                except Exception as e:
                    logger.warning("Error saving backup of %s as %s.",
                                   filename2, backupname, exc_info=True)

        try:
            self.savefile.write(tempname)
        except Exception as e:
            logger.exception("Error saving changes in %s.", self.filename)
            error = "Error saving changes:\n\n%s" % util.format_exc(e)

        if not error and rename:
            try:
                shutil.copy(tempname, filename2)
            except Exception as e:
                error = "Error saving %s as %s:\n\n%s" % \
                        (self.filename, filename2, util.format_exc(e))
                logger.exception("Error saving temporary file %s as %s.", tempname, filename2)

        try: tempname and os.unlink(tempname)
        except Exception: pass

        if error:
            wx.MessageBox(error, conf.Title, wx.OK | wx.ICON_ERROR)
            return

        self.filename = self.savefile.filename = filename2
        try: self.savefile.read()
        except Exception: logger.warning("Error re-reading %s.", filename2, exc_info=True)
        if rename:
            evt = SavefilePageEvent(self.Id, source=self, rename=True,
                                    filename1=filename1, filename2=filename2)
        else:
            evt = SavefilePageEvent(self.Id, source=self, modified=False)
        wx.PostEvent(self.Parent, evt)
        for p in self.plugins: p.action(save=True)
        guibase.status("Saved %s." % filename2, flash=conf.StatusShortFlashLength)
        return True


    def load_data(self):
        """Loads data from our file."""
        if not self.plugins:
            self.plugins = plugins.populate(self.savefile, self.notebook, self.undoredo)
            if self.notebook.PageCount < 2:
                tabarea = next((x for x in self.notebook.Children
                                if isinstance(x, wx.lib.agw.labelbook.ImageContainer)), None)
                tabarea and (tabarea.Hide(), self.notebook.Layout())
            self.update_metadata()
            self.Refresh()
            for p in self.plugins: p.render()
            wx_accel.accelerate(self.notebook)
        evt = SavefilePageEvent(self.Id, source=self, modified=False)
        wx.PostEvent(self.Parent, evt)


    def update_metadata(self):
        """Populates savefile metadata controls."""
        v = self.savefile.version
        if getattr(plugins, "version", None):
            v = next((x["label"] for x in plugins.version.PLUGINS if x["name"] == v), v)
        self.edit_name.Value = self.savefile.mapdata.get("name", "")
        self.edit_desc.Value = self.savefile.mapdata.get("desc", "")
        self.edit_vers.Value = v or ""


    def plugin_action(self, name, **kwargs):
        """Sends action to plugin specified by name."""
        plugin = next((p for p in self.plugins if p.name == name), None)
        if plugin: plugin.action(**kwargs)


    def show_changes(self):
        """Shows unsaved changes in a popup dialog."""
        title = "Changes in %s" % self.savefile.filename
        content = "".join(p.get_changes() for p in self.plugins)
        controls.HtmlDialog(self, title, content, style=wx.RESIZE_BORDER).ShowModal()


    def on_page_event(self, event):
        """Handler for notification from subtabs, updates UI if modified."""
        changed = self.savefile.is_changed()
        args = event.ClientData if isinstance(event.ClientData, dict) else {}
        evt = SavefilePageEvent(self.Id, **dict(args, source=self, modified=changed))
        wx.PostEvent(self.Parent, evt)



class GenericCommand(wx.Command):
    """Undoable-redoable action."""

    def __init__(self, do, undo, name=""):
        super(GenericCommand, self).__init__(canUndo=True, name=name)
        self._do, self._undo = do, undo
        self._timestamp = time.time()

    def Do(self):   return bool(self._do())

    def Undo(self): return bool(self._undo())

    @property
    def Timestamp(self):
        """Returns command creation timestamp, as UNIX epoch."""
        return self._timestamp



def build(plugin, panel):
    """
    Builds generic components into given panel according to plugin props,
    populated with plugin state.
    Returns a list of created controls, in similar structure as state.
    """
    props = plugin.props()
    state = plugin.state() if callable(getattr(plugin, "state", None)) else {}
    result = type(state)()

    panel.Freeze()
    panel.DestroyChildren()
    sizer = wx.GridBagSizer(vgap=10, hgap=10)
    panel.SetScrollRate(0, 20)
    panel.Sizer = wx.BoxSizer(wx.HORIZONTAL)
    panel.Sizer.Add(sizer, border=10, proportion=1, flag=wx.ALL ^ wx.BOTTOM | wx.GROW)

    def make_value_handler(ctrl, myprops, rowindex=None):
        name, key = myprops.get("name"), myprops.get("name", rowindex)

        def on_do(value):
            result = False
            state  = plugin.state() if callable(getattr(plugin, "state", None)) else {}
            row    = state[rowindex] if rowindex is not None and isinstance(state, list) else state
            target = next((x for x in (row, state) if isinstance(x, (list, dict))), None)
            if None not in (key, target) and util.get(target, key) == value:
                return result
            if callable(getattr(plugin, "on_change", None)):
                result = plugin.on_change(myprops, row, ctrl, value)
            elif None not in (key, target):
                target[key], result = value, True
            if result: plugin.parent.patch()
            return result

        def handler(event):
            value = event.EventObject.Value
            label = " ".join(map(str, filter(bool, [plugin.item(), plugin.name])))
            namelbl = "" if rowindex is None else "slot %s" % (rowindex + 1)
            if name is not None: namelbl += (" " if namelbl else "") + name
            valuelbl = "<blank>" if value in ("", False, None) else value
            cname = "set %s: %s %s" % (label, namelbl, valuelbl)
            logger.info("Setting %s: %s to %s.", label, namelbl, valuelbl)
            plugin.parent.command(functools.partial(on_do, value), cname)
        return handler

    def make_move_handler(ctrl, index, direction, labels=()):
        def on_do():
            state = plugin.state() if callable(getattr(plugin, "state", None)) else {}
            index2 = index + direction
            state[index], state[index2] = state[index2], state[index]

            stepper = wx.Window.GetNextSibling if direction > 0 else wx.Window.GetPrevSibling
            ctrl2, label2 = next(stepper(x) if x else x for x in [stepper(ctrl)]), ctrl.Label
            if len(labels) > 1 and label2 in labels and index + direction in (0, len(state) - 1):
                label2 = labels[labels.index(label2) - 1] # Reached edge: focus reverse button
            while ctrl2 and (type(ctrl2), ctrl2.Label) != (type(ctrl), label2):
                ctrl2 = stepper(ctrl2)
            ctrl2 and ctrl2.SetFocus() # Move focus to button of new index row

            plugin.parent.patch()
            wx.PostEvent(panel, PluginEvent(panel.Id, action="render", name=plugin.name))
            return True

        def handler(event):
            state = plugin.state() if callable(getattr(plugin, "state", None)) else {}
            if state[index] == state[index + direction]: return
            label = " ".join(map(str, filter(bool, [plugin.item(), plugin.name])))
            cname = "swap %s: #%s and #%s" % (label, index + 1, index + direction + 1)
            logger.info("Swapping %s: #%s and #%s.", label, index + 1, index + direction + 1)
            plugin.parent.command(on_do, cname)
        return handler

    def make_add_handler(ctrl, myprops):
        def on_do(value):
            state = plugin.state() if callable(getattr(plugin, "state", None)) else {}
            if callable(getattr(plugin, "on_add", None)): plugin.on_add(myprops, value)
            else: state.append({"name": value})
            plugin.parent.patch()
            wx.PostEvent(panel, PluginEvent(panel.Id, action="render", name=plugin.name))
            return True

        def handler(event):
            if not ctrl.Value: return
            label = " ".join(map(str, filter(bool, [plugin.item(), plugin.name])))
            cname = "add %s: %s" % (label, ctrl.Value)
            logger.info("Adding %s: %s.", label, ctrl.Value)
            plugin.parent.command(functools.partial(on_do, ctrl.Value), cname)
        return handler

    def make_remove_handler(ctrl, index):
        def on_do():
            state = plugin.state() if callable(getattr(plugin, "state", None)) else {}
            del state[index]
            plugin.parent.patch()
            wx.PostEvent(panel, PluginEvent(panel.Id, action="render", name=plugin.name))
            return True

        def handler(event):
            state = plugin.state() if callable(getattr(plugin, "state", None)) else {}
            v = state[index]
            if isinstance(v, dict): v = v.get("name", v)
            label = " ".join(map(str, filter(bool, [plugin.item(), plugin.name])))
            cname = "remove %s: %s" % (label, v)
            logger.info("Removing %s: %s.", label, v)
            plugin.parent.command(on_do, cname)
        return handler

    def make_clear_handler(ctrl, myprops, rowindex=None):
        name, key = myprops.get("name"), myprops.get("name", rowindex)

        def on_do():
            target = plugin.state() if callable(getattr(plugin, "state", None)) else {}
            value0 = util.get(target, key)
            if not value0:
                return False
            value = {} if isinstance(value0, dict) else None
            if callable(getattr(plugin, "on_change", None)):
                plugin.on_change(myprops, target, ctrl, value)
            else:
                target[key] = value
            wx.PostEvent(panel, PluginEvent(panel.Id, action="render", name=plugin.name))
            plugin.parent.patch()
            return True

        def handler(event):
            label = " ".join(map(str, filter(bool, [plugin.item(), plugin.name])))
            namelbl = "" if rowindex is None else "slot %s" % (rowindex + 1)
            if name is not None: namelbl += (" " if namelbl else "") + name
            cname = "set %s: %s <blank>" % (label, namelbl)
            logger.info("Setting %s: %s to <blank>.", label, namelbl)
            plugin.parent.command(on_do, cname)
        return handler

    def make_check_handler(ctrl, myprops, value):
        def on_do(checked):
            state = plugin.state() if callable(getattr(plugin, "state", None)) else {}
            if callable(getattr(plugin, "on_add" if checked else "on_remove", None)):
                (plugin.on_add if value else plugin.on_remove)(myprops, value)
            else:
                if isinstance(state, list):
                    (state.append if checked else state.remove)(value)
                else:
                    state.update({value: True}) if checked else state.pop(value)
            plugin.parent.patch()
            return True

        def handler(event):
            action, doing = ("add", "Adding") if ctrl.Value else ("remove", "Removing")
            label = " ".join(map(str, filter(bool, [plugin.item(), plugin.name])))
            cname = "%s %s: %s" % (action, label, value)
            logger.info("%s %s: %s.", doing, label, value)
            plugin.parent.command(functools.partial(on_do, ctrl.Value), cname)
        return handler

    def make_info(prop, sizer, pos):
        value = prop["info"](plugin, prop, state) if callable(prop["info"]) else prop["info"]
        c = wx.StaticText(panel, label=value)
        ColourManager.Manage(c, "ForegroundColour", wx.SYS_COLOUR_GRAYTEXT)
        sizer.Add(c, pos=pos)
        result["%s-info" % prop["name"]] = c


    count = 0
    BTN_WPLUS  = 0 if "nt" == os.name else 20
    SPIN_WPLUS = 0 if "nt" == os.name else 80
    for prop in props if isinstance(props, (list, tuple)) else [props]:
        if "itemlist" == prop.get("type"):
            values_present = []
            resultitems = []
            for i, row in enumerate(state):
                bsizer = wx.BoxSizer(wx.HORIZONTAL)
                resultitem = {}
                for itemprop in prop["item"]:
                    c, v = None, row.get(itemprop.get("name")) if isinstance(row, dict) else row
                    if "label" == itemprop.get("type"):
                        values_present.append(v)
                        if itemprop.get("label"): v = itemprop["label"]
                        if prop.get("orderable"): v = "%s. %s" % (i + 1, v)
                        c0 = wx.StaticText(panel, label=v, name="%s_%s_label" % (plugin.name, i))
                        sizer.Add(c0, pos=(count, 0), flag=wx.ALIGN_CENTER_VERTICAL)
                    elif "combo" == itemprop.get("type"):
                        choices = itemprop["choices"]
                        if isinstance(choices, dict): choices = list(choices.values())
                        if prop.get("nullable") and "" not in choices: choices = [""] + choices
                        if v and v not in choices: choices = [v] + choices
                        c = wx.ComboBox(panel, style=wx.CB_DROPDOWN | wx.CB_READONLY,
                                        name="%s_%s" % (plugin.name, i))
                        c.SetItems(choices)
                        if v is not None: c.Value = v
                        elif "" in choices: c.Value = ""
                        c.Bind(wx.EVT_COMBOBOX, make_value_handler(c, itemprop, rowindex=i))
                        bsizer.Add(c, flag=wx.GROW)
                    elif "number" == itemprop.get("type"):
                        c = wx.SpinCtrl(panel, name=itemprop["name"], size=(80 + SPIN_WPLUS, -1),
                                        style=wx.ALIGN_RIGHT)
                        rng = list(c.Range)
                        if "min" in itemprop: rng[0] = min(itemprop["min"], 2**30) # SpinCtrl limit
                        if "max" in itemprop: rng[1] = min(itemprop["max"], 2**30)
                        c.SetRange(*rng)
                        if itemprop["name"] in row: c.Value = row[itemprop["name"]]
                        c.Bind(wx.EVT_TEXT, make_value_handler(c, itemprop, rowindex=i))
                        bsizer.Add(c, flag=wx.GROW)
                    elif "window" == itemprop.get("type"):
                        c = wx.StaticText(panel)
                        bsizer.Add(c)

                    if c:
                        if isinstance(row, dict) and "name" in itemprop:
                            resultitem[itemprop["name"]] = c
                        else: resultitem = c
                if resultitem: resultitems.append(resultitem)

                if prop.get("orderable"):
                    c1, c2 = (wx.Button(panel, label=x, size=(40 + BTN_WPLUS, -1))
                              for x in ("down", "up"))
                    c1.Enabled, c2.Enabled = (i < len(state) - 1), bool(i)
                    c1.Bind(wx.EVT_BUTTON, make_move_handler(c1, i, +1, ("down", "up")))
                    c2.Bind(wx.EVT_BUTTON, make_move_handler(c2, i, -1, ("down", "up")))
                    bsizer.Add(c1, border=10, flag=wx.LEFT), bsizer.Add(c2)
                if prop.get("removable"):
                    c = wx.Button(panel, label="remove", size=(50 + BTN_WPLUS, -1))
                    c.Bind(wx.EVT_BUTTON, make_remove_handler(c, i))
                    bsizer.Add(c)
                if prop.get("nullable"):
                    c = wx.Button(panel, label="remove", size=(50 + BTN_WPLUS, -1))
                    c.Bind(wx.EVT_BUTTON, make_clear_handler(c, prop, rowindex=i))
                    bsizer.Add(c)
                if bsizer.Children: sizer.Add(bsizer, pos=(count, 1))
                else: sizer.AddSpacer(10)
                count += 1

            if prop.get("addable") and ("max" not in prop or len(state) < prop["max"]):
                choices = prop.get("choices") or []
                if isinstance(choices, dict): choices = list(choices.values())
                if prop.get("exclusive"):
                    choices = [x for x in choices if x not in values_present]
                c1 = wx.ComboBox(panel, style=wx.CB_DROPDOWN | wx.CB_READONLY)
                c2 = wx.Button(panel, label="Add")
                c1.SetItems(choices)
                c2.Bind(wx.EVT_BUTTON, make_add_handler(c1, prop))

                sizer.Add(c1, pos=(count, 0))
                sizer.Add(c2, pos=(count, 1), border=5, flag=wx.LEFT)
                count += 1
            if resultitems and isinstance(result, list):
                result.append(resultitems)


        elif "checklist" == prop.get("type"):
            dx, dy = (1, 0) if prop.get("vertical") else (0, 1)
            maxrows, maxcols = math.ceil(len(prop["choices"]) / prop["columns"]), prop["columns"]
            row, column = row0, col0 = count, 0
            for value in prop["choices"]:
                c = wx.CheckBox(panel, label=value)
                c.Value = bool(state.get(value)) if isinstance(state, dict) else value in state
                c.Bind(wx.EVT_CHECKBOX, make_check_handler(c, prop, value))
                sizer.Add(c, pos=(row, column), border=10, flag=wx.TOP if row == row0 else 0)
                result.append(c)
                row, column = row + dx, column + dy
                if   dx and row    > maxrows:  row, column = row0,    column + 1
                elif dy and column >= maxcols: row, column = row + 1, col0
            count += maxrows


        elif "number" == prop.get("type"):
            c1 = wx.StaticText(panel, label=prop.get("label", prop["name"]),
                               name="%s_label" % prop["name"])
            c2 = wx.SpinCtrl(panel, name=prop["name"], size=(80 + SPIN_WPLUS, -1),
                             style=wx.ALIGN_RIGHT)
            rng = list(c2.Range)
            if "min" in prop: rng[0] = min(prop["min"], 2**30) # SpinCtrl limit
            if "max" in prop: rng[1] = min(prop["max"], 2**30)
            c2.SetRange(*rng)
            c2.Value = state[prop["name"]]
            if prop.get("readonly"): c2.Enable(False)
            c2.Bind(wx.EVT_TEXT,     make_value_handler(c2, prop))
            c2.Bind(wx.EVT_SPINCTRL, make_value_handler(c2, prop))

            sizer.Add(c1, pos=(count, 0), flag=wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(c2, pos=(count, 1))
            result[prop["name"]] = c2
            if "info" in prop: make_info(prop, sizer, (count, 2))
            count += 1


        elif "combo" == prop.get("type"):
            c1 = wx.StaticText(panel, label="%s: " % prop.get("label", prop["name"]),
                               name="%s_label" % prop["name"])
            c2 = wx.ComboBox(panel, style=wx.CB_DROPDOWN | wx.CB_READONLY, name=prop["name"])

            v = state[prop["name"]]
            choices = prop["choices"]
            if isinstance(choices, dict):
                choices = list(choices.values())
                v = next((y for x, y in prop["choices"].items() if v == x), v)
            if prop.get("nullable") and "" not in choices: choices = [""] + choices
            if v and v not in choices: choices = [v] + choices
            c2.SetItems(choices)
            if v is not None: c2.Value = v
            if prop.get("readonly"): c2.Enable(False)
            c2.Bind(wx.EVT_COMBOBOX, make_value_handler(c2, prop))

            sizer.Add(c1, pos=(count, 0), flag=wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(c2, pos=(count, 1), flag=wx.GROW)
            if prop.get("nullable"):
                c3 = wx.Button(panel, label="remove", size=(50 + BTN_WPLUS, -1))
                c3.Bind(wx.EVT_BUTTON, make_clear_handler(c3, prop))
                sizer.Add(c3, pos=(count, 2))
            result[prop["name"]] = c2
            if "info" in prop: make_info(prop, sizer, (count, 2 + bool(prop.get("nullable"))))
            count += 1


        elif "check" == prop.get("type"):
            c1 = wx.StaticText(panel, label="%s: " % prop.get("label", prop["name"]),
                               name="%s_label" % prop["name"])
            c2 = wx.CheckBox(panel, name=prop["name"])

            c2.Value = bool(state[prop["name"]])
            if prop.get("readonly"): c2.Enable(False)
            c2.Bind(wx.EVT_CHECKBOX, make_value_handler(c2, prop))

            sizer.Add(c1, pos=(count, 0), flag=wx.ALIGN_CENTER_VERTICAL)
            sizer.Add(c2, pos=(count, 1))
            result[prop["name"]] = c2
            if "info" in prop: make_info(prop, sizer, (count, 2))
            count += 1


        elif "label" == prop.get("type"):
            c = wx.StaticText(panel, label=prop.get("label", ""))
            ColourManager.Manage(c, "ForegroundColour", wx.SYS_COLOUR_GRAYTEXT)
            sizer.Add(c, pos=(count, 0), span=(1, 2))
            count += 1


    panel.Layout()
    panel.SendSizeEvent()
    panel.Thaw()
    return result
