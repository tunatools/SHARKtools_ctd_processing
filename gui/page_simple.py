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
from ctd_processing import standard_format
from ctd_processing.processing.sbe_processing import SBEProcessing
from ctd_processing.processing.sbe_processing_paths import SBEProcessingPaths
from ctd_processing.standard_format import StandardFormatComments
from ctd_processing.visual_qc.vis_qc import VisQC
from ctdpy.core import session as ctdpy_session
from ctdpy.core.utils import get_reversed_dictionary
from file_explorer.seabird import paths
from sharkpylib.plot import create_seabird_like_plots_for_package
from sharkpylib.qc.qc_default import QCBlueprint
from sharkpylib.tklib import tkinter_widgets as tkw
import logging

from . import components
from . import frames
from ..events import subscribe
from ..saves import SaveComponents
from ..utils import open_paths_in_default_program

logger = logging.getLogger(__name__)

LISTBOX_TITLES = dict(title_items=dict(text='Välj filer genom att dubbelklicka',
                                       fg='red',
                                       font='Helvetica 12 bold'),
                      title_selected=dict(text='Valda filer',
                                          fg='red',
                                          font='Helvetica 12 bold'),)


class PageSimple(tk.Frame):

    def __init__(self, parent, parent_app, **kwargs):
        tk.Frame.__init__(self, parent, **kwargs)
        # parent is the frame "container" in App. controller is the App class
        self.parent = parent
        self.parent_app = parent_app

        self._save_obj = SaveComponents(key='ctd_processing_simple')

        self.sbe_paths = paths.SBEPaths()
        self.sbe_processing_paths = SBEProcessingPaths(self.sbe_paths)

        self.sbe_processing = SBEProcessing(sbe_paths=self.sbe_paths,
                                            sbe_processing_paths=self.sbe_processing_paths)

        self.bokeh_server = None

        self._unprocessed_packs = {}
        self._active_keys = []
        # self._active_keys_mapping = {}

        self._button_bg_color = None
        self._yes_color = '#00e025'
        self._no_color = '#2ba828'

        self._listbox_prop = {'width': 45, 'height': 6}

        self._stringvar_nr_packs_tot = tk.StringVar()
        self._stringvar_nr_packs_missing_local = tk.StringVar()
        self._stringvar_nr_packs_missing_server = tk.StringVar()
        self._stringvar_nr_packs_missing_tot = tk.StringVar()

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
                                      self._delete_old_asvp_files,
                                      self._config_path,
                                      self._surfacesoak,
                                      # self._tau,
                                      self._platform,
        )

        self._save_obj.load()

        subscribe('change_config_path', self._callback_change_config_path)
        subscribe('change_local_data_path_source', self._update_files)
        subscribe('change_local_data_path_root', self._update_files)
        subscribe('change_server_data_path_root', self._update_files)
        subscribe('change_simple_old_key', self._update_files)
        subscribe('select_platform', self._callback_select_platform)

    def update_page(self):
        self._update_lists()
        self._save_obj.load(component=self._surfacesoak)
        self._update_files()
        self._notebook.select_frame('Processering')

    def close(self):
        self._close_manual_qc()
        self._ftp_frame.close()
        self._save_obj.save()

    def _update_lists(self):
        self._callback_change_config_path()
        self._callback_select_platform()
        self._update_surfacesaok_list()

    def _build_frame(self):
        layout = dict(padx=20,
                      pady=20,
                      sticky='nsew')

        self._frame_paths = tk.LabelFrame(self, text='Sökvägar')
        self._frame_paths.grid(row=0, column=0, **layout)

        self._notebook = tkw.NotebookWidget(self, frames=['Processering', 'Skicka via FTP'], row=1, column=0, **layout)

        tkw.grid_configure(self, nr_rows=2)

        self._build_processing_frame()
        self._build_ftp_frame()

    def _build_processing_frame(self):
        frame = self._notebook.get_frame('Processering')
        layout = dict(padx=20,
                      pady=20,
                      sticky='nsew')

        self._frame_options = tk.LabelFrame(frame, text='Val')
        self._frame_options.grid(row=0, column=0, **layout)

        self._frame_files = tk.LabelFrame(frame, text='Filer i källmappen')
        self._frame_files.grid(row=0, column=1, **layout)

        self._frame_actions = tk.LabelFrame(frame, text='Vad vill du göra?')
        self._frame_actions.grid(row=0, column=2, **layout)

        tkw.grid_configure(frame, nr_rows=1, nr_columns=3)

        self._build_frame_path()
        self._build_frame_options()
        self._build_frame_files()
        self._build_frame_actions()

    def _build_ftp_frame(self):
        frame = self._notebook.get_frame('Skicka via FTP')
        layout = dict(padx=20,
                      pady=20,
                      sticky='nsew')
        self._ftp_frame = frames.FtpFrame(frame, sbe_paths=self.sbe_paths)
        self._ftp_frame.grid(row=0, column=0, **layout)

        tkw.grid_configure(frame)

    def _build_frame_path(self):
        layout = dict(padx=5,
                      pady=5,
                      sticky='nw')
        frame = tk.Frame(self._frame_paths)
        frame.grid(sticky='nw')
        tkw.grid_configure(self._frame_paths)

        r = 0
        self._config_path = components.DirectoryLabelText(frame, 'config_path',
                                                                   title='Rotkatalog för configfiler:',
                                                                   row=r, column=0, **layout)

        r += 1
        self._local_data_path_source = components.DirectoryButtonText(frame, 'local_data_path_source',
                                                                      title='Välj källmapp',
                                                                      row=r, column=0, **layout)

        r += 1
        self._local_data_path_root = components.DirectoryLabelText(frame, 'local_data_path_root',
                                                                          title='Rotkatalog för lokal data:',
                                                                          row=r, column=0, **layout)

        r += 1
        self._server_data_path_root = components.DirectoryButtonText(frame, 'server_data_path_root',
                                                                      title='Rotkatalog för data på servern:',
                                                                      row=r, column=0, **layout)

        r += 1
        self._asvp_files_directory = components.DirectoryButtonText(frame, 'asvp_files_directory',
                                                                     title='Spara asvp filer här:',
                                                                     row=r, column=0, **layout)

        r += 1
        self._delete_old_asvp_files = components.Checkbutton(frame, 'delete_old_asvp_files', title='Ta bort gamla asvp-filer', row=r,
                                               column=0, **layout)


        r += 1
        self._button_update = tk.Button(self._frame_paths, text='Uppdatera',
                                        command=self._update_files)
        self._button_update.grid(row=1, column=0, padx=5, pady=5, sticky='sw')

        tkw.grid_configure(frame, nr_rows=r + 1, nr_columns=1)

    def _build_frame_options(self):
        layout = dict(padx=5,
                      pady=5,
                      sticky='nw')
        frame = tk.Frame(self._frame_options)
        frame.grid(sticky='nw')
        tkw.grid_configure(self._frame_options)

        r = 0
        self._platform = components.LabelDropdownList(frame, 'platform', title='Platform', row=r, column=0,
                                                      **layout)

        r += 1
        self._surfacesoak = components.LabelDropdownList(frame, 'surfacesoak', title='Surfacesoak',
                                                                width=15,
                                                                row=r, column=0, **layout)

        # r += 1
        # self._tau = components.Checkbutton(frame, 'tau', title='Tau', row=r, column=0, **layout)

        r += 1
        self._old_key = components.Checkbutton(frame, 'simple_old_key', title='Generera gammalt filnamn', row=r, column=0, **layout)
        self._old_key.set(False)
        self._old_key.checkbutton.config(state='disabled')



        tkw.grid_configure(frame, nr_rows=r+1, nr_columns=1)

    def _build_frame_files(self):
        layout = dict(padx=5,
                      pady=5,
                      sticky='nw')
        frame = tk.Frame(self._frame_files)
        frame.grid(sticky='nw')
        tkw.grid_configure(self._frame_files)

        r = 0
        tk.Label(frame, textvariable=self._stringvar_nr_packs_tot).grid(row=r, column=0, **layout)
        tk.Label(frame, text='profiler finns i källmappen').grid(row=r, column=1, **layout)

        r += 1
        tk.Label(frame, textvariable=self._stringvar_nr_packs_missing_local).grid(row=r, column=0, **layout)
        tk.Label(frame, text='profiler i källmappen finns inte lokalt').grid(row=r, column=1, **layout)

        r += 1
        tk.Label(frame, textvariable=self._stringvar_nr_packs_missing_server).grid(row=r, column=0, **layout)
        tk.Label(frame, text='profiler i källmappen finns inte på servern').grid(row=r, column=1, **layout)

        r += 1
        tk.Label(frame, textvariable=self._stringvar_nr_packs_missing_tot, fg=self._yes_color, font='bold').grid(row=r, column=0, **layout)
        tk.Label(frame, text='profiler i källmappen finns varken lokalt eller på servern', fg=self._yes_color, font='bold').grid(row=r, column=1, **layout)

        r += 1
        listbox_prop_items = {}
        listbox_prop_items.update(self._listbox_prop)
        listbox_prop_selected = {'bg': self._yes_color}
        listbox_prop_selected.update(self._listbox_prop)
        self._files_source = tkw.ListboxSelectionWidget(frame, row=r, column=0, columnspan=2,
                                                        count_text='filer',
                                                        prop_items=listbox_prop_items,
                                                        prop_selected=listbox_prop_selected,
                                                        **LISTBOX_TITLES,
                                                        **layout)
        # self._files_source = tkw.ListboxWidget(frame,
        #                                        prop_listbox=listbox_prop, row=r, column=0, columnspan=2, **layout)

        tkw.grid_configure(frame, nr_rows=r + 1, nr_columns=1)

    def _build_frame_actions(self):
        layout = dict(padx=5,
                      pady=5,
                      sticky='nw')
        frame = tk.Frame(self._frame_actions)
        frame.grid(sticky='nw')
        tkw.grid_configure(self._frame_actions)

        r = 0

        self._button_run = tk.Button(frame, text='Processera', command=self._start_process, width=20, bg=self._yes_color)
        self._button_run.grid(row=r, column=0, **layout)

        r += 1
        self._button_open_qc = tk.Button(frame, text='Öppna manuell granskning', command=self._open_manual_qc, width=20, bg=self._yes_color)
        self._button_open_qc.grid(row=r, column=0, **layout)

        r += 1
        self._button_close_qc = tk.Button(frame, text='Stäng manuell granskning\nKopiera till server', command=self._close_manual_qc, width=20)
        self._button_close_qc.grid(row=r, column=0, **layout)

        tkw.grid_configure(frame, nr_rows=r + 1, nr_columns=1)

    def _start_process(self):
        all_keys = self._files_source.get_selected()

        if not self._config_path.get():
            messagebox.showwarning('Kör processering', 'Ingen rotkatalog för ctd_config vald!')
            return

        if not self._local_data_path_root.get():
            messagebox.showwarning('Kör processering', 'Ingen rotkatalog för lokal data vald!')
            return

        if not self._server_data_path_root.get():
            messagebox.showwarning('Kör processering', 'Ingen rotkatalog för data på servern vald!')
            return

        if not self._platform.value:
            messagebox.showwarning('Kör processering', 'Ingen platform vald!')
            return

        if not self._surfacesoak.value:
            messagebox.showwarning('Kör processering', 'Ingen surfacesoak vald!')
            return

        if not all_keys:
            messagebox.showwarning('Kör processering', 'Ingen filer är valda för processering!')
            return

        self._button_run.configure(state='disable')

        self._process_files()
        self._create_standard_format()
        self._update_ftp_frame()
        self._preform_automatic_qc()
        self._open_manual_qc()

    def _process_files(self):
        self._active_ids = []
        local_root = self._local_data_path_root.value
        server_root = self._server_data_path_root.value
        self.sbe_paths.set_local_root_directory(local_root)
        self.sbe_paths.set_server_root_directory(server_root)

        active_patterns = self._files_source.get_selected()
        self._active_ids = [self._source_patterns_to_id[pat] for pat in active_patterns]
        active_paths = [pack.path('hex') for _id, pack in self._id_to_source_pack.items() if _id in self._active_ids]

        create_asvp_file = False
        asvp_output_dir = self._asvp_files_directory.get()
        if asvp_output_dir:
            create_asvp_file = True

        for path in active_paths:
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
                                                           # tau=self._tau.value,
                                                           psa_paths=None,
                                                           ignore_mismatch=ignore_mismatch,
                                                           try_fixing_mismatch=try_fixing_mismatch,
                                                           old_key=self._old_key.value,
                                                           create_asvp_file=create_asvp_file,
                                                           asvp_output_dir=asvp_output_dir,
                                                           delete_old_asvp_files=self._delete_old_asvp_files.get()
                                                           )
                    continue_trying = False
                except FileExistsError:
                    messagebox.showerror('File exists',
                                         f'Could not overwrite file. Select overwrite and try again.\n{path}')
                    return
                except file_explorer.seabird.MismatchWarning as e:
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
                finally:
                    self._button_run.configure(state='normal')

    def _create_standard_format(self):
        try:
            all_packs = file_explorer.get_packages_in_directory(self.sbe_paths.get_local_directory('cnv'),
                                                                with_id_as_key=True, old_key=self._old_key.value)
            packs = []
            for _id in self._active_ids:
                pack = all_packs.get(_id)
                if not pack:
                    continue
                packs.append(pack)
            if not packs:
                messagebox.showerror('Skapar standardformat', 'Inga CNV filer valda för att skapa standardformat!')
                return
            new_packs = ctd_processing.create_standard_format_for_packages(packs,
                                                                           target_root_directory=self._local_data_path_root.value,
                                                                           config_root_directory=self._config_path.value,
                                                                           sharkweb_btl_row_file=None,
                                                                           old_key=self._old_key.value)
        except PermissionError as e:
            messagebox.showerror('Skapa standardformat',
                                 f'Det verkar som att en file är öppen. Stäng den och försök igen: {e}')
        except Exception:
            messagebox.showerror('Skapa standardformat', f'Internt fel: \n{traceback.format_exc()}')

    def _get_active_packs(self):
        all_packs = file_explorer.get_packages_in_directory(self.sbe_paths.get_local_directory('nsf'),
                                                            with_id_as_key=True, old_key=self._old_key.value)
        return [pack for key, pack in all_packs.items() if key in self._active_ids]

    def _preform_automatic_qc(self):
        packs = self._get_active_packs()
        # all_packs = file_explorer.get_packages_in_directory(self.sbe_paths.get_local_directory('nsf'),
        #                                                     with_id_as_key=True, old_key=self._old_key.value)
        # print(all_packs.keys())
        # print(self._active_ids)
        files = [pack['txt'] for pack in packs]
        if not files:
            messagebox.showwarning('Automatisk granskning', 'Inga filer att granska!')
            return

        tkw.disable_buttons_in_class(self)
        try:
            session = ctdpy_session.Session(filepaths=files,
                                            reader='ctd_stdfmt')

            datasets = session.read()

            for data_key, item in datasets[0].items():
                parameter_mapping = get_reversed_dictionary(session.settings.pmap, item['data'].keys())
                qc_run = QCBlueprint(item, parameter_mapping=parameter_mapping)
                qc_run()

            data_path = session.save_data(datasets,
                                          writer='ctd_standard_template', return_data_path=True,
                                          save_path=self.sbe_paths.get_local_directory('temp'),
                                          )

            # Den här metoden använder therading vilket innebär att vi måste vänta på att filerna skapats innan vi kan kopiera dem.
            data_path = Path(data_path)
            time.sleep(.5)
            for source_path in Path(data_path).iterdir():
                target_path = Path(self.sbe_paths.get_local_directory('nsf'), source_path.name)
                shutil.copyfile(source_path, target_path)
            return data_path
        except Exception:
            messagebox.showwarning('Automatisk granskning', traceback.format_exc())

    def _open_manual_qc(self):
        tkw.enable_buttons_in_class(self)
        self._button_run.config(state='disabled')
        self._button_open_qc.config(state='disabled')
        self._button_close_qc.config(bg=self._no_color)
        self.bokeh_server = VisQC(data_directory=self.sbe_paths.get_local_directory('nsf'),
                                  visualize_setting='smhi_expedition_vis')
        self.bokeh_server.start()
        # self._button_close_qc.config(state='normal')

    def _close_manual_qc(self):
        if not self.bokeh_server:
            return
        self.bokeh_server.stop()
        self.bokeh_server = None
        image_paths = self._create_plots()
        open_paths_in_default_program(image_paths)
        self._button_run.config(state='normal')
        self._button_open_qc.config(state='normal')
        self._button_close_qc.config(bg=self._button_bg_color)
        self._copy_files_to_server()
        self._update_files()
        self._notebook.select_frame('Skicka via FTP')

    def _create_plots(self):
        packs = self._get_active_packs()
        image_paths = []
        for pack in packs:
            img_paths = create_seabird_like_plots_for_package(pack, self.sbe_paths.get_local_directory('plot'))
            image_paths.extend(img_paths)
        return image_paths

    def _copy_files_to_server(self):
        local_packs = file_explorer.get_packages_in_directory(self.sbe_paths.get_local_directory('nsf'), with_id_as_key=True,
                                                              old_key=self._old_key.value, exclude_directory='temp')
        for _id in self._active_ids:
            pack = local_packs.get(_id)
            if not pack:
                messagebox.showerror('Något gick fel', 'Kunde inte kopiera till server. Hittar inga filer att kopiera...')
                return
            if 'test' in pack.pattern:
                continue
            handler = file_handler.SBEFileHandler(self.sbe_paths)
            handler.select_pack(pack)
            handler.copy_files_to_server()

    def _update_files(self, data=None):
        tkw.disable_buttons_in_class(self)
        # self._button_run.configure(state='disable')
        self._button_run.update_idletasks()
        self._active_ids = []
        self._files_source.update_items([])

        source_dir = self._local_data_path_source.value
        local_dir = self._local_data_path_root.value
        server_dir = self._server_data_path_root.value

        self.sbe_paths.set_local_root_directory(local_dir)
        self.sbe_paths.set_server_root_directory(server_dir)

        if not all([source_dir, local_dir, server_dir]):
            return
        source_packs = file_explorer.get_packages_in_directory(source_dir, with_id_as_key=True,
                                                               old_key=self._old_key.value, exclude_directory='temp',
                                                               exclude_string='sbe19')
        local_packs = file_explorer.get_packages_in_directory(local_dir, with_id_as_key=True,
                                                              old_key=self._old_key.value, exclude_directory='temp',
                                                              exclude_string='sbe19')
        server_packs = file_explorer.get_packages_in_directory(server_dir, with_id_as_key=True,
                                                               old_key=self._old_key.value, exclude_directory='temp',
                                                               exclude_string='sbe19')

        nr_packs_total = len(source_packs)
        nr_packs_not_local = 0
        nr_packs_not_server = 0
        unprocessed_keys = []
        for key in source_packs:
            if key not in local_packs:
                nr_packs_not_local += 1
            if key not in server_packs:
                nr_packs_not_server += 1
            if key not in local_packs and key not in server_packs:
                unprocessed_keys.append(key)

        self._stringvar_nr_packs_tot.set(nr_packs_total)
        self._stringvar_nr_packs_missing_local.set(nr_packs_not_local)
        self._stringvar_nr_packs_missing_server.set(nr_packs_not_server)

        self._source_patterns_to_id = {}
        self._id_to_source_pack = {}
        self._source_patterns_to_pack = {}
        for _id, pack in source_packs.items():
            if _id not in unprocessed_keys:
                continue
            self._id_to_source_pack[_id] = pack
            self._source_patterns_to_pack[pack.pattern] = pack
            self._source_patterns_to_id[pack.pattern] = _id

        keys = sorted(self._source_patterns_to_id)
        self._stringvar_nr_packs_missing_tot.set(len(unprocessed_keys))
        self._files_source.update_items(keys)
        self._files_source.move_items_to_selected(keys)

        self._update_ftp_frame()

        # self._button_run.configure(state='normal')
        tkw.enable_buttons_in_class(self)

        # print('='*50)
        # for key, value in self._source_patterns_to_id.items():
        #     print(key, value)
        # raise

    def _callback_change_config_path(self, *args):
        logger.debug('=')
        self.sbe_paths.set_config_root_directory(self._config_path.value)
        self._update_surfacesaok_list()
        self._update_platform_list()

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

    def _callback_select_platform(self, *args):
        self.sbe_processing.set_platform(self._platform.value)
        self._update_surfacesaok_list()

    def _update_ftp_frame(self):
        nsf_path = self.sbe_paths.get_local_directory('nsf')
        if not nsf_path:
            return
        self._ftp_frame.update_frame()

