#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Copyright (c) 2018 SMHI, Swedish Meteorological and Hydrological Institute
# License: MIT License (see LICENSE.txt or http://opensource.org/licenses/mit).

import tkinter as tk
import traceback
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox

import ctd_processing
import file_explorer
from file_explorer.seabird.paths import SBEPaths
from sharkpylib.tklib import tkinter_widgets as tkw

from ..saves import SaveComponents

from .packs_info import PacksInfo


class StringVar:
    def __init__(self, id_string=None):
        self._id = id_string
        self._stringvar = tk.StringVar()

    def __call__(self, *args, **kwargs):
        return self._stringvar

    def set(self, value):
        self._stringvar.set(value)

    def get(self):
        return self._stringvar.get()


class PageInspect(tk.Frame):

    def __init__(self, parent, parent_app, **kwargs):
        tk.Frame.__init__(self, parent, **kwargs)
        # parent is the frame "container" in App. controller is the App class
        self.parent = parent
        self.parent_app = parent_app
        self._saves = SaveComponents('inspect')

        self._all_packs_in_source_directory = []
        self._selected_packs = []

        self._stringvars_path = {}
        self._stringvars_stat_source = {}

    @property
    def user(self):
        return self.parent_app.user

    def startup(self):
        self._build()
        self._add_to_save()
        # self._on_select_source_dir()
        # self._on_select_local_dir()

    def _add_to_save(self):
        self._saves.add_components(*list(self._stringvars_path.values()))
        self._saves.load()

    def _create_stringvars(self):
        self._stringvars_path['source_dir'] = StringVar('source_dir')
        self._stringvars_path['local_dir'] = StringVar('local_dir')
        self._stringvars_path['ctd_config_dir'] = StringVar('ctd_config_dir')
        self._stringvars_path['sharkweb_path'] = StringVar('sharkweb_path')

    def _build(self):
        self._create_stringvars()

        self._frame_paths = tk.LabelFrame(self, text='Sökvägar')
        self._frame_paths.grid(row=0, column=0)

        self._frame_create = tk.LabelFrame(self, text='Skapa standardformat')
        self._frame_create.grid(row=0, column=1)

        self._notebook = tkw.NotebookWidget(self, frames=['Inspektera källmappen',
                                                          'Inspektera lokala rootmappen'], row=1, column=0, columnspan=2)

        tkw.grid_configure(self, nr_rows=2, nr_columns=2)

        self._build_frame_paths()
        self._build_frame_create()
        self._build_source_frame()
        self._build_local_frame()

    def _build_frame_paths(self):
        frame = self._frame_paths
        r = 0
        opt = dict(width=30)
        grid = dict(padx=5, pady=5)

        tk.Button(frame, text='Välj källmapp', command=self._select_source_dir, **opt).grid(row=r, column=0, **grid)
        tk.Label(frame, textvariable=self._stringvars_path['source_dir']()).grid(row=r, column=1, **grid,
                                                                                 sticky='w')
        r += 1
        tk.Button(frame, text='Välj lokal rotmapp', command=self._select_local_dir, **opt).grid(row=r, column=0, **grid)
        tk.Label(frame, textvariable=self._stringvars_path['local_dir']()).grid(row=r, column=1, **grid,
                                                                                sticky='w')

        tkw.grid_configure(frame, nr_rows=r + 1, nr_columns=2)

    def _build_frame_create(self):
        frame = self._frame_create
        r = 0
        opt = dict(width=30)
        grid = dict(padx=5, pady=5)

        tk.Button(frame, text='Välj ctd_config-mapp', command=self._select_ctd_config_dir, **opt).grid(row=r, column=0, **grid)
        tk.Label(frame, textvariable=self._stringvars_path['ctd_config_dir']()).grid(row=r, column=1, **grid,
                                                                                 sticky='w')
        r += 1
        tk.Button(frame, text='Välj sharkweb data (radformat)', command=self._select_sharkweb_path, **opt).grid(row=r, column=0, **grid)
        tk.Label(frame, textvariable=self._stringvars_path['sharkweb_path']()).grid(row=r, column=1, **grid,
                                                                                sticky='w')

        r += 1
        tk.Label(frame, text='Mätprogram:').grid(row=r, column=0, **grid, sticky='e')
        self._stringvar_mprog = tk.StringVar()
        tk.Entry(frame, textvariable=self._stringvar_mprog).grid(row=r, column=1, **grid, sticky='w')

        r += 1
        self._intvar_overwrite = tk.IntVar()
        tk.Checkbutton(frame, text='Skriv över filer', variable=self._intvar_overwrite).grid(row=r, column=1, **grid,
                                                                                             sticky='w')
        r += 1
        tk.Button(frame, text='Kopiera filer till lokal mapp',
                  command=self._copy_to_local, **opt).grid(row=r, column=0, **grid)

        tk.Button(frame, text='Skapa standardformat i lokal mapp',
                  command=self._create_standard_format, **opt).grid(row=r, column=1, **grid)

        tkw.grid_configure(frame, nr_rows=r+1, nr_columns=2)

    def _build_source_frame(self):
        frame = self._notebook.get_frame('Inspektera källmappen')

        grid = dict(padx=5, pady=5)
        r = 0
        self._info_frame_source = PacksInfo(frame)
        self._info_frame_source.grid(row=r, column=0, columnspan=2, **grid, sticky='w')
        tkw.grid_configure(frame, nr_rows=r + 1, nr_columns=2)

    def _build_local_frame(self):
        frame = self._notebook.get_frame('Inspektera lokala rootmappen')
        grid = dict(padx=5, pady=5)
        r = 0
        self._info_frame_local = PacksInfo(frame)
        self._info_frame_local.grid(row=r, column=0, columnspan=2, **grid, sticky='w')
        tkw.grid_configure(frame, nr_rows=r + 1, nr_columns=2)
        
    def _copy_to_local(self):
        packs = self._info_frame_source.selected_packs
        overwrite = bool(self._intvar_overwrite.get())
        local_root_path = self._stringvars_path['local_dir'].get()
        if not packs:
            messagebox.showwarning('Kopiera till lokal mapp', 'Inga paket valda!')
            return

        if not local_root_path or not Path(local_root_path).exists():
            messagebox.showwarning('Kopiera till lokal mapp', 'Ingen lokal sökväg angiven!')
            return
        sbe_paths = SBEPaths()
        sbe_paths.set_local_root_directory(local_root_path)
        nr_created = 0
        nr_not_created = 0
        for pack in packs:
            try:
                file_handler.copy_package_to_local(pack, sbe_paths, rename=True, overwrite=overwrite)
                nr_created += 1
            except FileExistsError:
                nr_not_created += 1
        text = f'{nr_created} paket har kopierats. '
        if nr_not_created:
            text = text + f'{nr_not_created} paket kunde inte skapas pga. att överskrivning av filer inte tilläts.'
        messagebox.showinfo('Kopiera till lokal mapp', text)
        self._on_select_local_dir()

    def _create_standard_format(self):
        packs = self._info_frame_local.selected_packs
        local_root_path = self._stringvars_path['local_dir'].get()
        ctd_config_path = self._stringvars_path['ctd_config_dir'].get()
        sharkweb_path = self._stringvars_path['sharkweb_path'].get() or None
        mprog = self._stringvar_mprog.get().strip() or None

        if not packs:
            messagebox.showwarning('Skapa standardformat', 'Inga paket valda!')
            return

        if not local_root_path or not Path(local_root_path).exists():
            messagebox.showwarning('Skapa standardformat', 'Ingen lokal sökväg angiven!')
            return

        if not ctd_config_path or not Path(ctd_config_path).exists():
            messagebox.showwarning('Skapa standardformat', 'Ingen sökväg till ctd_config angiven')
            return

        if sharkweb_path and not Path(sharkweb_path).exists():
            ans = messagebox.askyesno('Skapa standardformat', 'Kan inte hitta sökvägen till angiven sharkweb-fil. '
                                                        'Vill du fortsätta utan den?')
            self._stringvars_path['sharkweb_path'].set('')
            sharkweb_path = None
            if not ans:
                return

        try:
            ctd_processing.create_standard_format_for_packages(packs,
                                                target_root_directory=local_root_path,
                                                config_root_directory=ctd_config_path,
                                                overwrite=bool(self._intvar_overwrite.get()),
                                                sharkweb_btl_row_file=sharkweb_path,
                                                MPROG=mprog,
                                                               )
            self._on_select_local_dir()
        except FileExistsError:
            messagebox.showwarning('Skapa standardformat', 'Kunde inte skapa standardformatfiler pga. att överskrivning av filer inte tilläts.')

    def _select_source_dir(self):
        directory = filedialog.askdirectory(title='Välj källmapp')
        if not directory:
            return
        self._stringvars_path['source_dir'].set(directory)
        self._on_select_source_dir()

    def _select_local_dir(self):
        directory = filedialog.askdirectory(title='Välj lokal rotmapp')
        if not directory:
            return
        self._stringvars_path['local_dir'].set(directory)
        self._on_select_local_dir()

    def _select_ctd_config_dir(self):
        directory = filedialog.askdirectory(title='Välj ctd_config-mapp')
        if not directory:
            return
        self._stringvars_path['ctd_config_dir'].set(directory)

    def _select_sharkweb_path(self):
        path = filedialog.askopenfilename(title='Välj sharkweb-fil (radformat)')
        if not path:
            return
        self._stringvars_path['sharkweb_path'].set(path)

    def _on_select_source_dir(self):
        directory = self._stringvars_path.get('source_dir').get()
        if not directory:
            return
        packs = file_explorer.get_packages_in_directory(directory, exclude_directory='temp', as_list=True)
        self._info_frame_source.set_packs(packs)

    def _on_select_local_dir(self):
        directory = self._stringvars_path.get('local_dir').get()
        if not directory:
            return
        packs = file_explorer.get_packages_in_directory(directory, exclude_directory='temp', as_list=True)
        self._info_frame_local.set_packs(packs)

    def close(self):
        self._saves.save()

    def update_page(self):
        print('UPDATE')

