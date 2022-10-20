#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Copyright (c) 2018 SMHI, Swedish Meteorological and Hydrological Institute
# License: MIT License (see LICENSE.txt or http://opensource.org/licenses/mit).
import logging
import shutil
import time
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import messagebox

import ctd_processing
import file_explorer
from ctd_processing import exceptions
from ctd_processing import file_handler
from ctd_processing.processing.sbe_processing import SBEProcessing
from ctd_processing.processing.sbe_processing_paths import SBEProcessingPaths
from ctd_processing.standard_format import StandardFormatComments
from ctd_processing.visual_qc.vis_qc import VisQC
from ctdpy.core import session as ctdpy_session
from ctdpy.core.utils import get_reversed_dictionary
from file_explorer.seabird import paths
from profileqc import qc
from sharkpylib import plot
from sharkpylib.tklib import tkinter_widgets as tkw
# from profileqc.specific import get_specific_qc_settings

from . import components
from . import frames
from ..events import subscribe
from ..saves import SaveComponents
from ..utils import get_files_in_directory

logger = logging.getLogger(__name__)


LISTBOX_TITLES = dict(title_items=dict(text='Välj filer genom att dubbelklicka',
                                       fg='red',
                                       font='Helvetica 12 bold'),
                      title_selected=dict(text='Valda filer',
                                          fg='red',
                                          font='Helvetica 12 bold'),)


class PageStart(tk.Frame):

    def __init__(self, parent, parent_app, **kwargs):
        tk.Frame.__init__(self, parent, **kwargs)
        # parent is the frame "container" in App. controller is the App class
        self.parent = parent
        self.parent_app = parent_app

        self._save_obj = SaveComponents(key='ctd_processing')

        self.sbe_paths = paths.SBEPaths()
        self.sbe_processing_paths = SBEProcessingPaths(self.sbe_paths)

        self.sbe_processing = SBEProcessing(sbe_paths=self.sbe_paths,
                                            sbe_processing_paths=self.sbe_processing_paths)
        self.sbe_post_processing = None

        self.bokeh_server = None

        self._plot_config_popup = None

        self._processed_files = []
        self._converted_files = []

        self._button_bg_color = None

    @property
    def user(self):
        return self.parent_app.user

    def startup(self):
        """

        :return:
        """
        self._build_frame()
        self._save_obj.add_components(self._local_data_path_source,
                                      self._local_data_path_root,
                                      self._server_data_path_root,
                                      self._asvp_files_directory,
                                      self._config_path,
                                      self._surfacesoak,
                                      self._tau,
                                      self._create_asvp_files,
                                      self._platform,
                                      self._overwrite,
                                      self._year,
                                      self._create_plots_option
        )

        self._save_obj.load(user=self.user.name)

        subscribe('change_config_path', self._callback_change_config_path)
        subscribe('change_local_data_path_source', self._callback_change_local_source_directory)
        subscribe('change_local_data_path_root', self._callback_change_local_root_directory)
        subscribe('change_server_data_path_root', self._callback_change_server_root_directory)
        subscribe('update_series_local_source', self._callback_update_series_local_source)
        subscribe('change_year', self._callback_change_year)

        subscribe('select_platform', self._callback_select_platform)

        try:
            self._callback_change_year()
            self._update_all_local()
            self._update_all_server()
        except:
            pass

    def close(self):
        self._callback_stop_manual_qc()
        self._ftp_frame.close()
        self._save_obj.save(user=self.user.name)

    def _callback_select_platform(self, *args):
        self.sbe_processing.set_platform(self._platform.value)
        self._update_surfacesaok_list()

    def _make_config_root_updates(self, message=False):
        """ Makes updates relying on config root path being present """
        if not self._config_path.value:
            if message:
                messagebox.showwarning('Rotkatalog saknas', f'Rotkatalog för configfiler saknas!')
            return False
        self.sbe_paths.set_config_root_directory(self._config_path.value)
        self.sbe_processing_paths.update_paths()
        self._update_platform_list()
        if self._platform.value:
            self.sbe_processing.set_platform(self._platform.value)
            self._update_surfacesaok_list()

        return True

    def _make_local_root_updates(self, message=False):
        """ Makes updates relying on local root path being present """
        if not self._local_data_path_root.value:
            if message:
                messagebox.showwarning('Rotkatalog saknas', f'Lokal rootkatalog saknas!')
            return False
        self.sbe_paths.set_local_root_directory(self._local_data_path_root.value)
        self.sbe_processing_paths.update_paths()
        self._update_local_data_directories()
        self._update_local_file_lists()
        return True

    def _make_server_root_updates(self, message=False):
        """ Makes updates relying on local root path being present """
        if not self._local_data_path_root.value:
            if message:
                messagebox.showwarning('Rotkatalog saknas', f'Lokal rootkatalog saknas!')
            return False
        if not self._server_data_path_root.value:
            if message:
                messagebox.showwarning('Rotkatalog saknas', f'Server rootkatalog saknas!')
            return False
        self.sbe_paths.set_server_root_directory(self._server_data_path_root.value)
        self.sbe_processing_paths.update_paths()
        self._update_files_local_source()
        self._update_server_info()
        return True

    def update_page(self):
        print(f'{self.user=}')
        self._save_obj.load(user=self.user.name)
        self._make_config_root_updates(message=False)
        self._make_local_root_updates(message=False)
        self._make_server_root_updates(message=False)
        self._notebook_local.select_frame('Börja här')

    def _update_surfacesaok_list(self):
        if not self._config_path.value:
            self._surfacesoak.values = []
            return
        self._surfacesoak.values = list(self.sbe_processing.get_surfacesoak_options())

    def _update_platform_list(self):
        if not self._config_path.value:
            self._platform.values = []
            return
        self._platform.values = list(self.sbe_processing.get_platform_options())

    def _update_local_file_lists(self):
        self._update_files_local_raw()
        self._update_files_local_cnv()
        self._update_files_local_qc()
        self._update_files_local_nsf() # here 9

    def _clear_local_file_lists(self):
        self._files_local_raw.update_items([])
        self._files_local_cnv.update_items([])
        self._files_local_nsf_all.update_items([])
        self._files_local_nsf_missing.update_items([])

    def _build_frame(self):
        layout = dict(padx=5,
                      pady=5,
                      sticky='nw')

        self._listbox_prop = {'width': 45, 'height': 6}

        self._top_frame = tk.Frame(self)
        self._top_frame.grid(row=0, column=0, columnspan=2, **layout)

        self._frame_local_data = tk.LabelFrame(self, text='Filer som ligger lokalt')
        self._frame_local_data.grid(row=1, column=0, **layout)

        self._frame_server_data = tk.LabelFrame(self, text='Filer som ligger på servern')
        self._frame_server_data.grid(row=2, column=0, **layout)

        tkw.grid_configure(self, nr_rows=3, nr_columns=1)

        self._build_top_frame()
        self._build_frame_local_data()
        self._build_frame_server_data()

    def _build_top_frame(self):
        frame = self._top_frame
        layout = dict(padx=5,
                      pady=2,
                      sticky='nw')

        self._config_path = components.DirectoryLabelText(frame, 'config_path', title='Rotkatalog för configfiler:',
                                                          row=0,
                                                          column=0, **layout)

        self._overwrite = components.Checkbutton(frame, 'overwrite', title='Skriv över filer', row=1, column=0,
                                                 **layout)

        self._platform = components.LabelDropdownList(frame, 'platform', title='Platform', row=2, column=0,
                                                      **layout)

        self._year = components.YearEntry(frame, 'year', title='År', row=2, column=1, **layout)

        self._old_key = components.Checkbutton(frame, 'old_key', title='Generera gammalt filnamn', row=3, column=0,
                                                 **layout)
        self._old_key.set(False)
        self._old_key.checkbutton.config(state='disabled')

        self._asvp_files_directory = components.DirectoryButtonText(frame, 'asvp_files_directory',
                                                                    title='Spara asvp filer här:',
                                                                    row=4, column=0, **layout)

        # self._button_update = tk.Button(frame, text='Uppdatera mappinnehåll mm.',
        #                                  command=self._update_all_local)
        # self._button_update.grid(row=2, column=1, padx=5, pady=2, sticky='ne')

        tkw.grid_configure(frame, nr_rows=5, nr_columns=2)

    def _build_frame_local_data(self):
        frame = self._frame_local_data
        layout = dict(padx=5, pady=2, sticky='nw')
        
        self._local_data_path_root = components.DirectoryLabelText(frame, 'local_data_path_root',
                                                                   title='Rotkatalog för lokal data:',
                                                                   row=0, column=0, **layout)

        self._button_update = tk.Button(frame, text='Uppdatera lokalt mappinnehåll mm.', command=self._update_all_local)
        self._button_update.grid(row=0, column=1, padx=5, pady=2, sticky='ne')

        self._notebook_local = tkw.NotebookWidget(frame, 
                                                  frames=['Börja här', 'raw', 'cnv', 'Granskning', 'Standardformat', 'FTP'],
                                                  row=1, column=0, columnspan=2, **layout)

        tkw.grid_configure(frame, nr_rows=2)
        
        self._build_frame_local_source()
        self._build_frame_local_raw()
        self._build_frame_local_cnv()
        self._build_frame_local_qc()
        self._build_frame_local_nsf()
        self._build_frame_local_ftp()

    def _build_frame_local_source(self):
        frame = self._notebook_local('Börja här')
        layout = dict(padx=5, pady=2, sticky='nw')
        r = 0
        self._local_data_path_source = components.DirectoryButtonText(frame, 'local_data_path_source',
                                                                      title='Välj källmapp',
                                                                      row=r, column=0, columnspan=2, **layout)

        r += 1
        listbox_prop = {'bg': '#b5c1ff'}
        listbox_prop.update(self._listbox_prop)
        self._files_local_source = tkw.ListboxSelectionWidget(frame, row=r, column=0, columnspan=2,
                                                              count_text='filer',
                                                              callback=self._callback_update_series_local_source,
                                                              prop=listbox_prop,
                                                              **LISTBOX_TITLES,
                                                              **layout)

        r += 1
        option_frame = tk.Frame(frame)
        option_frame.grid(row=r, column=0, columnspan=2, **layout)

        self._surfacesoak = components.LabelDropdownList(option_frame, 'surfacesoak', title='Surfacesoak', width=15,
                                                         row=0, column=0, **layout)

        self._tau = components.Checkbutton(option_frame, 'tau', title='Tau', row=0, column=1, **layout)

        self._create_asvp_files = components.Checkbutton(option_frame, 'create_asvp_files',
                                                             title='Skapa asvp-filer', row=0,
                                                             column=2, **layout)
        tkw.grid_configure(option_frame, nr_rows=1, nr_columns=3)

        r += 1
        self._button_continue_source = tk.Button(frame, text='Kör processering', command=self._callback_continue_source)
        self._button_continue_source.grid(row=r, column=0, padx=5, pady=2, sticky='se')

        self._button_bg_color = self._button_continue_source.cget('bg')

        tkw.grid_configure(frame, nr_rows=4, nr_columns=2)

    def _build_frame_local_raw(self):
        frame = self._notebook_local('raw')
        layout = dict(padx=5, pady=2, sticky='nw')
        self._local_data_path_raw = components.DirectoryLabelText(frame, 'local_data_path_raw',
                                                                  title='Sökväg till lokala raw-filer:',
                                                                  row=0, column=0, columnspan=2, **layout)
        listbox_prop = {}
        listbox_prop.update(self._listbox_prop)
        listbox_prop.update({'bg': '#9deda3',
                             'width': 60})
        self._files_local_raw = tkw.ListboxWidget(frame, row=1, column=0, columnspan=2,
                                                  include_delete_button=False,
                                                  prop_listbox=listbox_prop, **layout)

        tkw.grid_configure(frame, nr_rows=2)

    def _build_frame_local_cnv(self):
        frame = self._notebook_local('cnv')
        layout = dict(padx=5, pady=2, sticky='nw')
        r = 0
        self._local_data_path_cnv = components.DirectoryLabelText(frame, 'local_data_path_cnv',
                                                                  title='Sökväg till lokala cnv-filer:',
                                                                  disabled=True,
                                                                  row=r, column=0, **layout)

        r += 1
        listbox_prop = {'bg': '#9deda3'}
        listbox_prop.update(self._listbox_prop)
        self._files_local_cnv = tkw.ListboxSelectionWidget(frame, row=r, column=0,
                                                           count_text='filer',
                                                           prop=listbox_prop,
                                                           **LISTBOX_TITLES,
                                                           **layout)

        r += 1
        self._button_continue_cnv = tk.Button(frame, text='Skapa standardformat', command=self._callback_continue_cnv)
        self._button_continue_cnv.grid(row=r, column=0, padx=5, pady=2, sticky='se')

        tkw.grid_configure(frame, nr_rows=r + 1)

    def _build_frame_local_qc(self):
        frame = self._notebook_local('Granskning')
        layout = dict(padx=5, pady=2, sticky='nw')

        left_frame = tk.Frame(frame)
        left_frame.grid(row=0, column=0)
        right_frame = tk.Frame(frame)
        right_frame.grid(row=0, column=1)
        tkw.grid_configure(frame, nr_rows=1, nr_columns=2)

        # Left frame
        self._local_data_path_qc = components.DirectoryLabelText(left_frame, 'local_data_path_qc',
                                                                  title='Sökväg till lokala standardformatfiler:',
                                                                  disabled=True,
                                                                  # end_with_folders=['data', '<YEAR>', 'raw'],
                                                                  row=0, column=0, **layout)

        listbox_prop = {'bg': '#e38484'}
        listbox_prop.update(self._listbox_prop)
        self._files_local_qc = tkw.ListboxSelectionWidget(left_frame, row=2, column=0,
                                                          count_text='filer',
                                                          prop=listbox_prop,
                                                          **LISTBOX_TITLES,
                                                          **layout)

        tkw.grid_configure(left_frame, nr_rows=3, nr_columns=1)

        # Right frame
        r = 0
        self._intvar_allow_automatic_qc_same_day = tk.IntVar()
        cb = tk.Checkbutton(right_frame, text='Tillåt automatisk granskning samma dag',  variable=self._intvar_allow_automatic_qc_same_day)
        cb.grid(row=r, column=0, padx=5, pady=2, sticky='se')

        r += 1
        self._create_plots_option = components.Checkbutton(right_frame, 'create_plots_option', title='Skapa plottar', row=r, column=0, padx=5, pady=2, sticky='se')
        self._create_plots_option.set(True)

        r += 1
        self._button_automatic_qc = tk.Button(right_frame, text='1) Utför automatisk granskning',
                                              command=self._callback_continue_automatic_qc)
        self._button_automatic_qc.grid(row=r, column=0, padx=5, pady=2, sticky='se')

        r += 1
        self._button_open_manual_qc = tk.Button(right_frame, text='2) Öppna manuell granskning (alla filer)',
                                                command=self._callback_start_manual_qc)
        self._button_open_manual_qc.grid(row=r, column=0, padx=5, pady=2, sticky='se')

        r += 1
        self._button_close_manual_qc = tk.Button(right_frame, text='3) Stäng manuell granskning',
                                                 command=self._callback_stop_manual_qc)
        self._button_close_manual_qc.grid(row=r, column=0, padx=5, pady=2, sticky='se')

        r += 1
        self._button_create_plots = tk.Button(right_frame, text='Skapa plottar',
                                                 command=self._callback_create_plots)
        self._button_create_plots.grid(row=r, column=0, padx=5, pady=2, sticky='se')

        tkw.grid_configure(right_frame, nr_rows=r+1, nr_columns=1)

    def _build_frame_local_nsf(self):
        frame = self._notebook_local('Standardformat')
        layout = dict(padx=5, pady=2, sticky='nw')
        self._local_data_path_nsf = components.DirectoryLabelText(frame, 'local_data_path_nsf',
                                                                  title='Sökväg till lokala standardformatfiler:',
                                                                  disabled=True,
                                                                  # end_with_folders=['data', '<YEAR>', 'raw'],
                                                                  row=0, column=0, columnspan=2, **layout)

        self._notebook_copy_to_server = tkw.NotebookWidget(frame, frames=['Välj', 'Alla'], row=1)
        self._notebook_copy_to_server.select_frame('Alla')

        tk.Button(frame, text='Gå till försystemet', command=self._goto_pre_system).grid(row=2, padx=5, pady=2, sticky='e')

        tkw.grid_configure(frame, nr_rows=3)

        frame_all_files = tk.Frame(self._notebook_copy_to_server.frame_alla)
        frame_all_files.grid(row=0, column=0, **layout)

        frame_missing_files = tk.Frame(self._notebook_copy_to_server.frame_alla)
        frame_missing_files.grid(row=0, column=1, **layout)

        frame_not_updated_files = tk.Frame(self._notebook_copy_to_server.frame_alla)
        frame_not_updated_files.grid(row=0, column=2, **layout)

        tkw.grid_configure(self._notebook_copy_to_server.frame_alla, nr_rows=1, nr_columns=2)

        # Frame all
        tk.Label(frame_all_files, text='Alla filer').grid( row=0, column=0)

        listbox_prop = {'bg': '#bad7f7'}
        listbox_prop.update(self._listbox_prop)
        self._files_local_nsf_all = tkw.ListboxWidget(frame_all_files, row=1, column=0,
                                                  include_delete_button=False,
                                                  prop_listbox=listbox_prop, **layout)

        self._button_continue_nsf_all = tk.Button(frame_all_files, text='Kopiera ALLT till servern',
                                              command=self._callback_copy_all_to_server)
        self._button_continue_nsf_all.grid(row=2, column=0, padx=5, pady=2, sticky='s')
        tkw.grid_configure(frame_all_files, nr_rows=3)

        # Frame missing
        tk.Label(frame_missing_files, text='Filer som inte finns på servern').grid(row=0, column=0)

        listbox_prop = {'bg': '#f77c7c'}
        listbox_prop.update(self._listbox_prop)
        self._files_local_nsf_missing = tkw.ListboxWidget(frame_missing_files, row=1, column=0,
                                                  include_delete_button=False,
                                                  prop_listbox=listbox_prop, **layout)

        self._button_continue_nsf_missing = tk.Button(frame_missing_files, text='Kopiera till servern',
                                              command=self._callback_copy_missing_to_server)
        self._button_continue_nsf_missing.grid(row=2, column=0, padx=5, pady=2, sticky='s')
        tkw.grid_configure(frame_missing_files, nr_rows=3)

        # Frame not updated
        tk.Label(frame_not_updated_files, text='Filer som inte är updaterade på servern').grid(row=0, column=0)

        listbox_prop = {'bg': '#fa8e8e'}
        listbox_prop.update(self._listbox_prop)
        self._files_local_nsf_not_updated = tkw.ListboxWidget(frame_not_updated_files, row=1, column=0,
                                                          include_delete_button=False,
                                                          prop_listbox=listbox_prop, **layout)

        self._button_continue_nsf_not_updated = tk.Button(frame_not_updated_files, text='Kopiera till servern',
                                                      command=self._callback_copy_not_updated_to_server)
        self._button_continue_nsf_not_updated.grid(row=2, column=0, padx=5, pady=2, sticky='s')
        tkw.grid_configure(frame_not_updated_files, nr_rows=3)

        # Selected
        listbox_prop = {'bg': '#89ed80'}
        listbox_prop.update(self._listbox_prop)
        self._files_local_nsf_select = tkw.ListboxSelectionWidget(self._notebook_copy_to_server.frame_valj,
                                                                  count_text='filer',
                                                                  callback=self._callback_on_select_local_nsf,
                                                                  prop=listbox_prop, **layout)
        self._button_continue_nsf_select = tk.Button(self._notebook_copy_to_server.frame_valj,
                                                     text='Kopiera valda till servern',
                                                     command=self._callback_copy_selected_to_server)
        self._button_continue_nsf_select.grid(row=2, column=0, padx=5, pady=2, sticky='s')
        tkw.grid_configure(self._notebook_copy_to_server.frame_valj, nr_rows=2)

    def _build_frame_local_ftp(self):
        frame = self._notebook_local('FTP')
        self._ftp_frame = frames.FtpFrame(frame, sbe_paths=self.sbe_paths)
        self._ftp_frame.grid(row=0, column=0, sticky='nsew')
        tkw.grid_configure(frame)

        # layout = dict(padx=5, pady=2, sticky='nw')
        # r = 0
        # self._local_data_path_ftp = components.DirectoryLabelText(frame, 'local_data_path_ftp',
        #                                                           title='Sökväg till lokala standardformatfiler:',
        #                                                           disabled=True,
        #                                                           row=r, column=0,
        #                                                           columnspan=2, **layout)
        #
        # r += 1
        # listbox_prop = {'bg': '#fcec03'}
        # listbox_prop.update(self._listbox_prop)
        # self._files_local_ftp = tkw.ListboxSelectionWidget(frame, row=r, column=0,
        #                                                    columnspan=2,
        #                                                    count_text='filer',
        #                                                    prop=listbox_prop,
        #                                                    **LISTBOX_TITLES,
        #                                                    **layout)
        #
        # self._files_on_ftp = tkw.ListboxWidget(frame, row=r, column=2,
        #                                        prop_listbox=listbox_prop,
        #                                        include_delete_button=False,
        #                                        padx=5, pady=2, sticky='e')
        #
        # r += 1
        # self._ftp_credentials_path = components.FilePathButtonText(frame, 'ftp_credentials_path',
        #                                                               title='Sökväg till inloggningsuppgifter till FTP',
        #                                                               row=r, column=0, **layout)
        #
        # self._ftp_test_checkbutton = tkw.CheckbuttonWidgetSingle(frame, name='Skicka till test',
        #                                                          callback=self._on_toggle_ftp_test, row=r, column=1)
        #
        # self._button_send_files_via_ftp = tk.Button(frame, text='Skicka filer via ftp', command=self._callback_continue_ftp)
        # self._button_send_files_via_ftp.grid(row=r, column=2, padx=5, pady=2, sticky='se')
        #
        # tkw.grid_configure(frame, nr_rows=r + 1, nr_columns=3)

    def _on_toggle_ftp_test(self):
        self._update_files_ftp()

    def _goto_pre_system(self):
        self.parent_app.main_app.show_subframe('SHARKtools_pre_system_Svea', 'PageStart')

    def _callback_continue_automatic_qc(self):
        file_names = self._files_local_qc.get_selected()
        if not file_names:
            messagebox.showwarning('Automatisk granskning', 'Inga filer är valda för granskning!')
            return
        files = []
        nr_files_qc = 0
        for name in file_names:
            handler = file_handler.SBEFileHandler(self.sbe_paths)
            handler.select_file(name)
            local_file_path = handler.get_local_file_path('nsf')
            if not local_file_path:
                continue
            if not self._intvar_allow_automatic_qc_same_day.get():
                sf = StandardFormatComments(local_file_path)
                if sf.has_automatic_qc_today():
                    continue
            files.append(str(local_file_path))
            nr_files_qc += 1

        if not files:
            messagebox.showwarning('Automatisk granskning', 'Valda filer är redan granskade idag. \nIngen granskning gjord!')
            return
        logger.info(f'{files=}')

        tkw.disable_buttons_in_class(self)
        try:
            session = ctdpy_session.Session(filepaths=files,
                                            reader='ctd_stdfmt')

            datasets = session.read()

            # qc_session = qc.SessionQC(None, advanced_settings_name='smhi_expedition')
            qc_session = qc.SessionQC(None)

            for dset_name, item in datasets[0].items():
                parameter_mapping = get_reversed_dictionary(session.settings.pmap, item['data'].keys())
                qc_session.update_data(item,
                                       parameter_mapping=parameter_mapping,
                                       dataset_name=dset_name)
                # qc_session.update_routines()
                qc_session.run()

            qc_session.write_log(Path(self.sbe_paths.get_local_directory('temp'), 'automatic_qc_log.yaml'), reset_log=True)


            # for data_key, item in datasets[0].items():
            #     parameter_mapping = get_reversed_dictionary(session.settings.pmap, item['data'].keys())
            #     routine_settings = get_specific_qc_settings(
            #         user='svea',
            #         lat=item['data']['LATITUDE_DD'][0],
            #         lon=item['data']['LONGITUDE_DD'][0],
            #         month=item['data']['MONTH'][0])
            #     qc_session = qc.SessionQC(data_item=item,
            #                               parameter_mapping=parameter_mapping,
            #                               routine_settings=routine_settings)
            #     qc_session.run()

            data_path = session.save_data(datasets,
                                          writer='ctd_standard_template', return_data_path=True,
                                          save_path=self.sbe_paths.get_local_directory('temp'),
                                          )

            # Den här metoden använder therading vilket innebär att vi måste vänta på att filerna skapats innan vi kan kopiera dem.
            data_path = Path(data_path)
            time.sleep(.5)
            for source_path in Path(data_path).iterdir():
                target_path = Path(self.sbe_paths.get_local_directory('nsf'), source_path.name)
                if target_path.exists() and not self._overwrite:
                    continue
                shutil.copyfile(source_path, target_path)

            messagebox.showinfo('Automatisk granskning', f'{nr_files_qc} av {len(file_names)} granskade!')
            return data_path
        except Exception:
            messagebox.showwarning('Automatisk granskning', traceback.format_exc())
            raise
        finally:
            tkw.enable_buttons_in_class(self)

    def _callback_start_manual_qc(self):
        self._button_open_manual_qc.config(state='disabled')
        self._button_automatic_qc.config(state='disabled')
        self._button_close_manual_qc.config(bg='red')
        file_names = self._files_local_qc.get_selected()
        self.bokeh_server = VisQC(data_directory=self.sbe_paths.get_local_directory('nsf'),
                                  visualize_setting='smhi_expedition_vis',
                                  filters={'file_names': file_names})
        self.bokeh_server.start()

    def _callback_stop_manual_qc(self):
        if not self.bokeh_server:
            return
        self.bokeh_server.stop()
        self.bokeh_server = None
        self._button_open_manual_qc.config(state='normal')
        self._button_automatic_qc.config(state='normal')
        self._button_close_manual_qc.config(bg=self._button_bg_color)
        self._update_files_local_nsf()
        self._update_ftp_frame()
        if self._create_plots_option.get():
            self._create_plots()
        self._notebook_local.select_frame('Standardformat')

    def _callback_create_plots(self):
        created = self._create_plots(with_config=True)
        if created:
            messagebox.showinfo('Skapa plottar', f"Plottar har skapats här: {self.sbe_paths.get_local_directory('plot')}")

    def _callback_on_select_local_nsf(self):
        selected = self._files_local_nsf_select.get_selected()
        if not selected:
            # self._callback_change_year() # here 6 in
            return
        last_selected = selected[-1]
        if not last_selected.startswith('SBE'):
            return
        year = last_selected.split('_')[2][:4]
        self._year.value = year
        self.sbe_paths.set_year(year)
        self._update_server_data_directories()
        self._update_server_file_lists()

    def _callback_copy_all_to_server(self):
        files = self._files_local_nsf_all.get_items()
        self._copy_to_server_and_update(files)
        messagebox.showinfo('Kopiera till servern', f'ALLT filer har kopierats till servern')

    def _callback_copy_missing_to_server(self):
        files = self._files_local_nsf_missing.get_items()
        self._copy_to_server_and_update(files)
        messagebox.showinfo('Kopiera till servern', f'Saknade filer har kopierats till servern')

    def _callback_copy_not_updated_to_server(self):
        files = self._files_local_nsf_not_updated.get_items()
        self._copy_to_server_and_update(files)
        messagebox.showinfo('Kopiera till servern', f'Alla icke uppdaterade filer har kopierats till servern')

    def _callback_copy_selected_to_server(self):
        files = self._files_local_nsf_select.get_selected()
        self._copy_to_server_and_update(files)
        messagebox.showinfo('Kopiera till servern', f'Valda filer har kopierats till servern')

    def _copy_to_server_and_update(self, files):
        for file in files:
            if 'test' in file:
                continue
            handler = file_handler.SBEFileHandler(self.sbe_paths)
            handler.select_file(file)
            handler.copy_files_to_server(update=self._overwrite.value)
        self._update_server_info()
        self._update_all_local()

    def _update_server_info(self):
        self._update_files_local_nsf_not_on_server()
        self._update_files_local_nsf_not_updated_on_server()
        self._update_server_data_directories()
        self._update_server_file_lists()
        year = self.sbe_paths.year or ''
        self._year.value = str(year)

    def _callback_continue_source(self):

        if not self._config_path.get():
            messagebox.showwarning('Kör processering', 'Ingen rotkatalog för ctd_config vald!')
            return

        if not self._local_data_path_root.get():
            messagebox.showwarning('Kör processering', 'Ingen rotkatalog för lokal data vald!')
            return

        if not self._platform.value:
            messagebox.showwarning('Kör processering', 'Ingen platform vald!')
            return

        if not self._surfacesoak.value:
            messagebox.showwarning('Kör processering', 'Ingen surfacesoak vald!')
            return

        selected = self._files_local_source.get_selected()
        if not selected:
            messagebox.showwarning('Kör processering', 'Ingen filer är valda för processering!')
            return

        local_root = self._local_data_path_root.value
        self.sbe_paths.set_local_root_directory(local_root)

        processed_files = []

        create_asvp_file = False
        asvp_output_dir = self._asvp_files_directory.get()
        if asvp_output_dir:
            create_asvp_file = self._create_asvp_files.get()

        for file_name in selected:
            path = Path(self._local_data_path_source.value, file_name)
            ignore_mismatch = False
            try_fixing_mismatch = False
            continue_trying = True
            while continue_trying:
                try:
                    pack = ctd_processing.process_sbe_file(path,
                                                           target_root_directory=self._local_data_path_root.value,
                                                           config_root_directory=self._config_path.value,
                                                           platform=self._platform.value,
                                                           surfacesoak=self._surfacesoak.value,
                                                           tau=self._tau.value,
                                                           overwrite=self._overwrite.value,
                                                           psa_paths=None,
                                                           ignore_mismatch=ignore_mismatch,
                                                           try_fixing_mismatch=try_fixing_mismatch,
                                                           old_key=self._old_key.value,
                                                           create_asvp_file=create_asvp_file,
                                                           asvp_output_dir=asvp_output_dir,
                                                           )
                    # self.sbe_processing.select_file(path)
                    # self.sbe_processing.select_file(path)
                    # new_path = self.sbe_processing.confirm_file(path)
                    # self.sbe_processing_paths.platform = self._platform.value
                    # self.sbe_processing.set_surfacesoak(self._surfacesoak.value)
                    # self.sbe_processing.set_tau_state(self._tau.value)
                    # self.sbe_processing.run_process(overwrite=self._overwrite.value, ignore_mismatch=ignore_mismatch)
                    # self.sbe_processing.create_zip_with_psa_files()
                    # self.sbe_processing.create_sensorinfo_file()
                    processed_files.append(pack['hex'])
                    continue_trying = False
                except FileExistsError:
                    messagebox.showerror('File exists', f'Could not overwrite file. Select overwrite and try again.\n{path}')
                    return
                except file_explorer.seabird.MismatchWarning as e:
                    # ans = messagebox.askyesno('Mismatch mellan filer',
                    #                                 f"""{e.data}
                    #                                                 Om parameter saknas i datcnv bör du fundera på att updatera ctd_config.
                    #                                                 Denna varning kan ignoreras, du får då hantera "problemet" vidare i Seasave.
                    #                                                 Vill du fortsätta?""")
                    ans = messagebox.askyesnocancel('Mismatch mellan filer',
                                                f"""{e.data}\n\n
                                                Välj "Ja" för att försöka lösa problemet. \nVälj "Nej" för att lösa problemet i seabird programvara. \nVälj "Avbryt" för att avbryta. """)
                    if ans is True:
                        try_fixing_mismatch = True
                    elif ans is False:
                        ignore_mismatch = True
                    else:
                        return
                except Exception as e:
                    messagebox.showerror('Något gick fel', traceback.format_exc())
                    raise

        self._processed_files = [path.stem for path in processed_files]
        self._update_files_local_cnv()
        self._notebook_local.select_frame('cnv')

    def _callback_continue_cnv(self):
        try:
            self._converted_files = []
            cnv_files = self._get_selected_local_cnv_file_paths()
            if not cnv_files:
                messagebox.showerror('Skapar standardformat', 'Inga CNV filer valda för att skapa standardformat!')
                return
            packs = file_explorer.get_packages_from_file_list(cnv_files, instrument_type='sbe', as_list=True, old_key=self._old_key.value)
            new_packs = ctd_processing.create_standard_format_for_packages(packs,
                                                                           target_root_directory=self._local_data_path_root.value,
                                                                           config_root_directory=self._config_path.value,
                                                                           overwrite=self._overwrite.value,
                                                                           sharkweb_btl_row_file=None,
                                                                           old_key=self._old_key.value)


            # self.standard_format = standard_format.CreateStandardFormat(paths_object=self.sbe_paths)
            # self.standard_format.create_files_from_cnv(cnv_files, overwrite=self._overwrite.value)
            self._update_files_local_qc()
            self._update_files_local_nsf() # here:1
            self._update_server_info()

            self._converted_files = [path.stem for path in cnv_files]
            self._update_files_local_qc()
            self._notebook_local.select_frame('Granskning')
        except PermissionError as e:
            messagebox.showerror('Skapa standardformat',
                                 f'Det verkar som att en file är öppen. Stäng den och försök igen: {e}')
        except Exception:
            messagebox.showerror('Skapa standardformat', f'Internt fel: \n{traceback.format_exc()}')
            raise

    def _get_selected_local_cnv_stems(self):
        files = self._files_local_cnv.get_selected()
        if not files:
            return
        stems = []
        for file in files:
            stems.append(Path(file).stem)
        return stems

    def _get_selected_local_cnv_file_paths(self):
        directory = self._local_data_path_cnv.value
        if not directory:
            return
        files = self._files_local_cnv.get_selected()
        if not files:
            return
        paths = []
        for file in files:
            paths.append(Path(directory, file))
        return paths

    def _build_frame_server_data(self):
        frame = self._frame_server_data
        layout = dict(padx=5,
                      pady=2,
                      sticky='nw')
        r = 0
        c = 0
        self._server_data_path_root = components.DirectoryButtonText(frame, 'server_data_path_root',
                                                                     title='Rotkatalog för data på servern:',
                                                                     hard_press=True,
                                                                     # end_with_folders=['data', '<YEAR>'],
                                                                     row=r, column=c, **layout)

        r += 1
        self._server_data_path_nsf = components.DirectoryLabelText(frame, 'server_data_path_nsf',
                                                                   title='Sökväg till standardformatfiler på servern:',
                                                                   disabled=True,
                                                                   column=c, **layout)

        r += 1
        listbox_prop = {'bg': '#e4e864'}
        listbox_prop.update(self._listbox_prop)
        self._files_server = tkw.ListboxWidget(frame,
                                               include_delete_button=False,
                                               prop_listbox=listbox_prop,
                                               row=r, column=c, **layout)

        tkw.grid_configure(frame, nr_rows=r+1)

    def _callback_change_local_source_directory(self, *args):
        """ Called when local source data path is selected """
        self._update_files_local_source()

    def _callback_change_local_root_directory(self, *args):
        """ Called when the the local root directory is changed """
        path = Path(self._local_data_path_root.value)
        if not path.exists():
            raise FileNotFoundError(path)
        self.sbe_paths.set_local_root_directory(path)
        # self._set_proper_local_root_path()
        self._update_local_data_directories()
        self._update_local_file_lists() # here 8

    def _callback_change_server_root_directory(self, *args):
        """ Called when the the server root directory is changed """
        path = Path(self._server_data_path_root.value)
        if not path.exists():
            raise FileNotFoundError(path)
        self.sbe_paths.set_server_root_directory(path)
        self._update_all_server()

    def _callback_update_series_local_source(self, *args):
        """ Called when one or more source files is selected. """
        # self._set_ctd_processing_object_with_latest_selected_file()
        self._update_server_data_directories()

    def _callback_change_config_path(self, *args):
        self.sbe_paths.set_config_root_directory(self._config_path.value)
        self._update_surfacesaok_list()
        self._update_platform_list()

    def _set_ctd_processing_object_with_latest_selected_file(self):
        """
        """
        selected = self._files_local_source.get_selected()
        if not selected:
            return None
        path = Path(self._local_data_path_source.value, selected[-1])
        self.sbe_processing.select_file(path)

    def _update_files_local_source(self):
        """Updates local file list based on files found in path: self._local_data_path_source"""
        if not self._local_data_path_source.value:
            self._files_local_source.update_items()
            self._local_data_path_source.value = ''
            return
            
        path = Path(self._local_data_path_source.value)
        if not path.exists():
            self._files_local_source.update_items()
            self._local_data_path_source.value = ''
            return
            # raise FileNotFoundError(path)
        # files = ctd_files.get_matching_files_in_directory(self._local_data_path_source.value)
        files = get_files_in_directory(self._local_data_path_source.value, suffix='.hex')
        self._files_local_source.update_items(sorted(files))

    def _update_files_local_raw(self):
        files = get_files_in_directory(self._local_data_path_raw.value)
        self._files_local_raw.update_items(files)

    def _update_files_local_cnv(self):
        files = get_files_in_directory(self._local_data_path_cnv.value, suffix='.cnv')
        self._files_local_cnv.update_items(files)
        self._files_local_cnv.deselect_all()
        all_cnv_files = {}
        for item in self._files_local_cnv.get_all_items():
            if not item.endswith('.cnv'):
                continue
            name, suffix = item.split('.')
            all_cnv_files[name] = item
        select_files = [all_cnv_files.get(name) for name in self._processed_files if all_cnv_files.get(name)]
        logger.debug(f'select_files: {select_files}')
        self._files_local_cnv.move_items_to_selected(select_files)

    def _update_files_local_qc(self):
        files = get_files_in_directory(self._local_data_path_qc.value)
        self._files_local_qc.update_items(files)
        self._files_local_qc.deselect_all()
        all_txt_files = {}
        for item in self._files_local_qc.get_all_items():
            if not item.endswith('.txt'):
                continue
            name, suffix = item.split('.')
            all_txt_files[name] = item
        select_files = [all_txt_files.get(name) for name in self._converted_files if all_txt_files.get(name)]
        self._files_local_qc.move_items_to_selected(select_files)

    def _update_files_local_nsf(self):
        self._update_files_local_nsf_all()
        self._update_files_local_nsf_selected() # here 2
        if self.sbe_paths.get_server_directory('root'):
            self._update_files_local_nsf_not_on_server()

    def _update_ftp_frame(self):
        self._ftp_frame.update_frame()
        all_keys = self._ftp_frame.get_all_keys()
        selected_keys = [key for key in all_keys if key in self._converted_files]
        self._ftp_frame.move_keys_to_selected(selected_keys)

    def _update_files_local_nsf_all(self):
        files = get_files_in_directory(self._local_data_path_nsf.value)
        self._files_local_nsf_all.update_items(files[:])

    def _update_files_local_nsf_not_on_server(self):
        files = get_files_in_directory(self._local_data_path_nsf.value)
        handler = file_handler.SBEFileHandler(self.sbe_paths)
        not_on_server = []
        for file in files:
            try:
                handler.select_file(file)
                if handler.not_on_server():
                    not_on_server.append(file)
            except exceptions.InvalidFileNameFormat:
                continue
        self._files_local_nsf_missing.update_items(not_on_server)

    def _update_files_local_nsf_not_updated_on_server(self):
        files = get_files_in_directory(self._local_data_path_nsf.value)
        handler = file_handler.SBEFileHandler(self.sbe_paths)
        not_updated_on_server = []
        for file in files:
            try:
                handler.select_file(file)
                if handler.not_updated_on_server():
                    not_updated_on_server.append(file)
            except exceptions.InvalidFileNameFormat:
                continue
        self._files_local_nsf_not_updated.update_items(not_updated_on_server)

    def _update_files_local_nsf_selected(self):
        files = get_files_in_directory(self._local_data_path_nsf.value)
        self._files_local_nsf_select.update_items(files)
        # Move to selected
        file_stems = self._get_selected_local_cnv_stems()
        if not file_stems:
            return
        all_files = self._files_local_nsf_select.get_all_items()
        select = []
        for file in all_files:
            if Path(file).stem in file_stems:
                select.append(file)
        self._files_local_nsf_select.deselect_all() # here 3
        self._files_local_nsf_select.move_items_to_selected(select)

    def _update_local_data_directories(self):
        """ Sets local data paths based on info in processing.CtdProcessing object. """
        self._local_data_path_raw.set(path=self.sbe_paths.get_local_directory('raw'))
        self._local_data_path_cnv.set(path=self.sbe_paths.get_local_directory('cnv'))
        self._local_data_path_qc.set(path=self.sbe_paths.get_local_directory('nsf'))
        self._local_data_path_nsf.set(path=self.sbe_paths.get_local_directory('nsf'))
        self._ftp_frame.update_frame()

    def _update_server_file_lists(self):
        """Updates server file list based on files found in path: self._server_data_path_nsf"""
        if not self._server_data_path_nsf.value:
            self._files_server.update_items()
            return
        path = Path(self._server_data_path_nsf.value)
        if not path.exists():
            self._files_server.update_items()
            return
        files = self.sbe_processing.get_file_names_in_server_directory('nsf')
        self._files_server.update_items(sorted(files))

    def _update_server_data_directories(self):
        # updatera filer på servern på ett smartare sätt
        # self._server_data_path_raw.set(path=self.sbe_paths.get_server_directory('raw', default=''))
        # self._server_data_path_cnv.set(path=self.sbe_paths.get_server_directory('cnv', default=''))
        self._server_data_path_nsf.set(path=self.sbe_paths.get_server_directory('nsf', default=''))

    def _callback_change_year(self, *args):
        year = self._year.value
        if not year:
            return
        self.sbe_paths.set_year(year)
        self._callback_change_local_root_directory() # here 7
        self._update_all_server()

    def _create_plots(self, with_config=False):
        directory = self.sbe_paths.get_local_directory('nsf')
        names = self._files_local_qc.get_selected()
        if not names:
            messagebox.showwarning('Skapa plottar', 'Inga filer valda för att skapa plottar!')
            return False
        if with_config and len(names) == 1:
            path = Path(directory, names[0])
            pack = file_explorer.get_package_for_file(path)
            self._show_config_plot_popup(pack)
        else:
            for name in names:
                path = Path(directory, name)
                pack = file_explorer.get_package_for_file(path)
                plot.create_seabird_like_plots_for_package(pack, self.sbe_paths.get_local_directory('plot'))
            return True

    def _show_config_plot_popup(self, pack):
        self._plot_config_popup = frames.PlotOptionsFrame(self, pack, callback=self._on_return_plot_config)

    def _on_return_plot_config(self, pack, **kwargs):
        plot.create_seabird_like_plots_for_package(pack, self.sbe_paths.get_local_directory('plot'), **kwargs)
        self._plot_config_popup.grab_release()
        self._plot_config_popup.destroy()
        self._plot_config_popup = None

    def _update_all_local(self):
        self._update_files_local_source()
        self._update_files_local_raw()
        self._update_files_local_cnv()
        self._update_files_local_nsf()
        self._update_files_local_qc()
        self._update_files_local_nsf_all()
        self._update_files_local_nsf_selected()
        self._update_files_local_nsf_not_on_server()
        self._update_files_local_nsf_not_updated_on_server()
        self._update_ftp_frame()

    def _update_all_server(self):
        self._update_server_data_directories()
        self._update_server_file_lists()

    def update_all(self):
        self._update_all_local()
        self._update_all_server()




