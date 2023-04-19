#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Copyright (c) 2018 SMHI, Swedish Meteorological and Hydrological Institute
# License: MIT License (see LICENSE.txt or http://opensource.org/licenses/mit).

import logging
import tkinter as tk
import traceback
from tkinter import messagebox

import file_explorer
from ctd_processing import metadata
from sharkpylib.tklib import tkinter_widgets as tkw

from . import components
from .. import events
from ..saves import SaveComponents

META_COLUMNS = metadata.get_metadata_columns()

logger = logging.getLogger(__name__)


class PageEditRaw(tk.Frame):

    def __init__(self, parent, parent_app, **kwargs):
        tk.Frame.__init__(self, parent, **kwargs)
        self.parent = parent
        self.parent_app = parent_app
        self._saves = SaveComponents('edit')

        self._all_packs = {}

    @property
    def user(self):
        return self.parent_app.user

    def startup(self):
        """
        :return:
        """
        self._build()
        self._add_to_save()
        self._add_events()

    def _add_to_save(self):
        self._saves.add_components(
            self._target_dir,
            self._sharkweb_path,
            self._lims_path,
        )
        self._saves.load()

    def _add_events(self):
        events.subscribe('change_metadata_packs_source', self._on_change_source)
        events.subscribe('change_metadata_packs_target', self._on_change_target)
        events.subscribe('change_metadata_packs_sharkweb_path', self._on_change_sharkweb_path)
        events.subscribe('change_metadata_packs_lims_path', self._on_change_lims_path)

    def close(self):
        self._saves.save()

    def update_page(self):
        pass

    def _build(self):
        self._frame_metadata_enrichment = tk.LabelFrame(self, text='Uppdatera metadata i råfiler')
        self._frame_metadata_enrichment.grid()
        tkw.grid_configure(self)

        self._build_metadata_enrichment()

    def _build_metadata_enrichment(self):
        frame = self._frame_metadata_enrichment
        r = 0
        c = 0

        LISTBOX_TITLES = dict(title_items=dict(text='Ej valda serier',
                                               fg='red',
                                               font='Helvetica 12 bold'),
                              title_selected=dict(text='Valda serier',
                                                  fg='green',
                                                  font='Helvetica 12 bold'), )

        self._source_dir = components.DirectoryButtonText(frame,
                                                          'metadata_packs_source',
                                                          title='Välj serier från mapp',
                                                          row=r,
                                                          column=c)
        r += 1
        prop = dict(
            width=40
        )
        self._packs_listbox = tkw.ListboxSelectionWidget(frame,
                                                         title_items=LISTBOX_TITLES['title_items'],
                                                         title_selected=LISTBOX_TITLES['title_selected'],
                                                         callback=self._on_select_packs,
                                                         prop_items=prop.copy(),
                                                         prop_selected=prop.copy(),
                                                         row=r,
                                                         column=c)

        r += 1
        self._target_dir = components.DirectoryButtonText(frame, 'metadata_packs_target',
                                                          title='Spara filer till mapp',
                                                          row=r,
                                                          column=c)

        r += 1
        frame_sharkweb = tk.Frame(frame)
        frame_sharkweb.grid(row=r, column=c, sticky='w')
        self._boolvar_sharkweb = tk.BooleanVar()
        tk.Checkbutton(frame_sharkweb, variable=self._boolvar_sharkweb).grid(row=0, column=0)
        self._sharkweb_path = components.FilePathButtonText(frame_sharkweb,
                                                            'metadata_packs_sharkweb_path',
                                                            title='Välj SHARKweb-fil',
                                                            row=0,
                                                            column=1)
        tkw.grid_configure(frame_sharkweb, nr_columns=2)

        r += 1
        frame_lims = tk.Frame(frame)
        frame_lims.grid(row=r, column=c, sticky='w')
        self._boolvar_lims = tk.BooleanVar()
        tk.Checkbutton(frame_lims, variable=self._boolvar_lims).grid(row=0, column=0)
        self._lims_path = components.FilePathButtonText(frame_lims,
                                                            'metadata_packs_lims_path',
                                                            title='Välj LIMS-fil',
                                                            row=0,
                                                            column=1)
        tkw.grid_configure(frame_lims, nr_columns=2)

        r += 1
        tk.Button(frame, text='Uppdatera metadata', command=self._update_metadata).grid(row=r, column=c, sticky='w')

        tkw.grid_configure(frame, nr_rows=r+1, nr_columns=c+1)

    def _on_change_source(self, path):
        self._all_packs = file_explorer.get_packages_in_directory(path)
        self._packs_listbox.update_items(sorted(self._all_packs))

    def _on_change_target(self, path):
        pass

    def _on_select_packs(self):
        pass

    def _on_change_sharkweb_path(self, path=None):
        self._boolvar_sharkweb.set(True)

    def _on_change_lims_path(self, path=None):
        self._boolvar_lims.set(True)

    def _update_metadata(self, event=None):
        logger.info('Updating metadata')
        sharkweb_file_path = None
        lims_file_path = None
        if self._boolvar_sharkweb.get():
            sharkweb_file_path = self._sharkweb_path.get()
            if not sharkweb_file_path:
                msg = 'Ingen sharkweb-fil vald'
                logger.warning(msg)
                messagebox.showwarning('Använd sharkweb-fil', msg)
                return
            logger.info(f'Updating metadata from {sharkweb_file_path=}')

        if self._boolvar_lims.get():
            lims_file_path = self._lims_path.get()
            if not lims_file_path:
                msg = 'Ingen LIMS-file vald'
                logger.warning(msg)
                messagebox.showwarning('Använd LIMS-fil', msg)
                return
            logger.info(f'Updating metadata from {lims_file_path=}')

        output_dir = self._target_dir.get()
        if not output_dir:
            msg = 'Ingen mapp att spara till vald'
            logger.warning(msg)
            messagebox.showwarning('Uppdatera metadata', msg)
            return

        packs = [self._all_packs[key] for key in self._packs_listbox.get_selected()]
        if not packs:
            msg = 'Inga filer valda'
            logger.warning(msg)
            messagebox.showwarning('Uppdatera metadata', msg)
            return
        try:
            file_explorer.edit_seabird_raw_files_in_packages(
                packs=packs,
                output_dir=output_dir,
                sharkweb_file_path=sharkweb_file_path,
                lims_file_path=lims_file_path,
                columns=META_COLUMNS,
            )
            msg = f'Metadata har lagts till i {len(packs)} profiler.'
            logger.info(msg)
            messagebox.showinfo('Uppdatera metadata', msg)
        except Exception:
            msg = traceback.format_exc()
            logger.critical(msg)
            messagebox.showerror('Uppdatera metadata', msg)
            raise

