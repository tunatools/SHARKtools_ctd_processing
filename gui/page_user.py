# -*- coding: utf-8 -*-
# Copyright (c) 2018 SMHI, Swedish Meteorological and Hydrological Institute
# License: MIT License (see LICENSE.txt or http://opensource.org/licenses/mit).

import tkinter as tk
from tkinter import ttk

import core

import sharkpylib.tklib.tkinter_widgets as tkw
from sharkpylib import utils

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

"""
================================================================================
================================================================================
================================================================================
"""
class PageUser(tk.Frame):
    """
    """
    def __init__(self, parent, parent_app, **kwargs):
        tk.Frame.__init__(self, parent, **kwargs)
        # parent is the frame "container" in App. contoller is the App class
        self.parent = parent
        self.parent_app = parent_app
        self.main_app = self.parent_app.main_app
        self.user_manager = parent_app.user_manager
        self.user = self.user_manager.user
        self.settings = parent_app.settings

        self.color_list = utils.ColorsList()
        self.marker_list = utils.MarkerList()

    #===========================================================================
    def startup(self):
        self._set_frame()
    
    #===========================================================================
    def update_page(self):
        self.user = self.user_manager.user

        
    #===========================================================================
    def _set_frame(self):
        tk.Label(self, text='User settings page').grid()
