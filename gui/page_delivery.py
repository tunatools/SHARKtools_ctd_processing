#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Copyright (c) 2018 SMHI, Swedish Meteorological and Hydrological Institute
# License: MIT License (see LICENSE.txt or http://opensource.org/licenses/mit).

import tkinter as tk
from tkinter import messagebox

import datetime
from pathlib import Path
import shutil

from . import components
from ..saves import SaveComponents

from ..events import post_event
from ..events import subscribe

from sharkpylib.tklib import tkinter_widgets as tkw

from ctd_processing import processing
from ctd_processing import paths
from ctd_processing import ctd_files
from ctd_processing import file_handler

from ctdpy.core import session as ctdpy_session


class PageStart(tk.Frame):

    def __init__(self, parent, parent_app, **kwargs):
        tk.Frame.__init__(self, parent, **kwargs)
        # parent is the frame "container" in App. controller is the App class
        self.parent = parent
        self.parent_app = parent_app

        # self._save_obj = SaveComponents(key='ctd_processing')

        self.sbe_paths = paths.SBEPaths()

    @property
    def user(self):
        return self.parent_app.user

    def startup(self):
        """

        :return:
        """
        self._build_frame()
        # self._save_obj.add_components(
        # )

        # self._save_obj.load()

    def close(self):
        pass
        # self._save_obj.save()

    def _build_frame(self):
        layout = dict(padx=5,
                      pady=5,
                      sticky='nw')



