# Copyright (c) 2018 SMHI, Swedish Meteorological and Hydrological Institute 
# License: MIT License (see LICENSE.txt or http://opensource.org/licenses/mit).

# To use basemap you might need to install Microsoft Visual C++: https://visualstudio.microsoft.com/visual-cpp-build-tools/


import os
import tkinter as tk

import sharkpylib.tklib.tkinter_widgets as tkw

import core
from plugins.SHARKtools_ctd_processing import gui
from plugins.plugin_app import PluginApp

from .events import subscribe

ALL_PAGES = dict()
ALL_PAGES['PageStart'] = gui.PageStart
ALL_PAGES['PageInspect'] = gui.PageInspect
ALL_PAGES['PageSimple'] = gui.PageSimple
ALL_PAGES['PageEditRaw'] = gui.PageEditRaw

APP_TO_PAGE = dict()
for page_name, page in ALL_PAGES.items():
    APP_TO_PAGE[page] = page_name


class App(PluginApp):
    """
    """
    def __init__(self, parent, main_app, **kwargs):
        PluginApp.__init__(self, parent, main_app, **kwargs)
        # parent is the frame "container" in App. contoller is the App class
        self.parent = parent
        self.main_app = main_app
        self.version = ''

        self.info_popup = self.main_app.info_popup
        self.plugin_directory = os.path.dirname(os.path.abspath(__file__))
        self.root_directory = self.main_app.root_directory
        self.log_directory = self.main_app.log_directory

    @property
    def user(self):
        return self.main_app.user

    def startup(self):
        """
        """
        # Setting upp GUI logger
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)

        self.logger = self.main_app.logger

        self.paths = core.Paths(self.plugin_directory)

        self.user_manager = self.main_app.user_manager

        self._create_titles()

        self.all_ok = True
        
        self.active_page = None
        self.previous_page = None
        self.admin_mode = False
        self.progress_running = False
        self.progress_running_toplevel = False

        self.latest_loaded_sampling_type = ''

        self._set_frame()

        self.startup_pages()

        subscribe('goto_pre_system_svea', self._goto_pre_system_svea)

        self.page_history = ['PageUser']
        # self.show_frame('PageStart')

        # self.update_all()

    def _goto_pre_system_svea(self , *args):
        self.main_app.show_subframe('SHARKtools_pre_system_Svea', 'PageStart')

    def close(self):
        for page_name, frame in self.frames.items():
            if self.pages_started.get(page_name):
                try:
                    frame.close()
                except:
                    pass

    def update_page(self):
        self.update_all()

    def _set_frame(self):
        self.container = tk.Frame(self)
        self.container.grid(row=0, column=0, sticky="nsew")
        tkw.grid_configure(self)

    def startup_pages(self):
        # Tuple that store all pages
        self.pages_started = dict()

        # Dictionary to store all frame classes
        self.frames = {}
        
        # Looping all pages to make them active. 
        for page_name, Page in ALL_PAGES.items():  # Capital P to emphasize class
            # Destroy old page if called as an update
            try:
                self.frames[page_name].destroy()
                print(Page, u'Destroyed')
            except:
                pass
            frame = Page(self.container, self)
            frame.grid(row=0, column=0, sticky="nsew")

            self.container.rowconfigure(0, weight=1)
            self.container.columnconfigure(0, weight=1) 
            
            self.frames[page_name] = frame

    def _set_load_frame(self):
        pass

    def update_all(self):
        for page_name, frame in self.frames.items():
            if self.pages_started.get(page_name):
                # print('page_name', page_name)
                frame.update_page()

    def show_frame(self, page_name):
        """
        This method brings the given Page to the top of the GUI. 
        Before "raise" call frame startup method. 
        This is so that the Page only loads ones.
        """

        load_page = True
        frame = self.frames[page_name]
        # self.withdraw()
        if not self.pages_started.get(page_name, None):
            frame.startup()
            self.pages_started[page_name] = True
        frame.update_page()

        #-----------------------------------------------------------------------
        if load_page:
            frame.tkraise()
            self.previous_page = self.active_page
            self.active_page = page
            # Check page history
            if page in self.page_history:
                self.page_history.pop()
                self.page_history.append(page)
        self.update()


    #===========================================================================
    def goto_previous_page(self, event):
        if self.previous_page:
            self.show_frame(self.previous_page) 
        
    #===========================================================================
    def previous_page(self, event):
        self.page_history.index(self.active_page)
        
    
    #===========================================================================
    def update_app(self):
        """
        Updates all information about loaded series. 
        """
        self.update_all()


    #===========================================================================
    def _get_title(self, page):
        if page in self.titles:
            return self.titles[page]
        else:
            return ''
    
    #===========================================================================
    def _create_titles(self):
        self.titles = {}





