import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
import traceback

import sharkpylib.tklib.tkinter_widgets as tkw
from sharkpylib import ftp

from .. import components
from ...events import subscribe
from ...events import post_event
from ...saves import SaveComponents

LISTBOX_TITLES = dict(title_items=dict(text='Välj filer genom att dubbelklicka',
                                       fg='red',
                                       font='Helvetica 12 bold'),
                      title_selected=dict(text='Valda filer',
                                          fg='red',
                                          font='Helvetica 12 bold'),)


class FtpFrame(tk.Frame):

    def __init__(self, *args, **kwargs):
        self._listbox_prop = {'width': 45, 'height': 6}
        self._listbox_prop.update(kwargs.get('listbox_prop', {}))
        super().__init__(*args, **kwargs)

        self._save_obj = SaveComponents(key='ftp')

        self._file_handler = None

        self._build()
        self._save_obj.add_components(
                                      self._ftp_credentials_path,
                                      )

        self._save_obj.load()

        subscribe('change_ftp_credentials_path', self._update_files_ftp)

        self._update_files_ftp()

    def set_file_handler(self, handler):
        self._file_handler = handler

    def close(self):
        self._save_obj.save()

    def _get_ftp_title(self):
        return f'Filer på FTP: {self._get_ftp_destination()}'

    def _get_ftp_destination(self):
        cred = self.ftp_credentials
        if not cred:
            return ''
        obj = get_ftp_object(cred)
        return f'{cred.get("host", "")}/{obj.destination}'

    def _build(self):
        layout = dict(padx=5, pady=2, sticky='nw')

        left_frame = tk.Frame(self)
        right_frame = tk.Frame(self)

        left_frame.grid(row=0, column=0, **layout)
        right_frame.grid(row=0, column=1, **layout)

        tkw.grid_configure(self, nr_columns=2)

        # Left frame
        self._local_data_path_ftp = components.DirectoryLabelText(left_frame, 'local_data_path_ftp',
                                                                  title='Sökväg till lokala standardformatfiler:',
                                                                  disabled=True,
                                                                  row=0, column=0,
                                                                  columnspan=2, **layout)

        listbox_prop = {'bg': '#fcec03'}
        listbox_prop.update(self._listbox_prop)
        self._files_local_ftp = tkw.ListboxSelectionWidget(left_frame, row=1, column=0,
                                                           columnspan=2,
                                                           count_text='filer',
                                                           only_unique_items=False,
                                                           sort_items=False,
                                                           prop=listbox_prop,
                                                           **LISTBOX_TITLES,
                                                           **layout)

        self._ftp_credentials_path = components.FilePathButtonText(left_frame, 'ftp_credentials_path',
                                                                   title='Sökväg till inloggningsuppgifter till FTP',
                                                                   row=2, column=0, **layout)

        tkw.grid_configure(left_frame, nr_rows=3, nr_columns=1)

        # Right frame
        self._ftp_test_checkbutton = tkw.CheckbuttonWidgetSingle(right_frame, name='Skicka till test',
                                                                 callback=self._on_toggle_ftp_test, row=0, column=0, **layout)

        self._also_send_cnv_files = tkw.CheckbuttonWidgetSingle(right_frame, name='Skicka även cnv-filer', row=1, column=0, **layout)

        self._stringvar_title_ftp = tk.StringVar()
        tk.Label(right_frame, textvariable=self._stringvar_title_ftp).grid(row=2, column=0, **layout)

        self._files_on_ftp = tkw.ListboxWidget(right_frame, row=3, column=0,
                                               prop_listbox=listbox_prop,
                                               include_delete_button=False,
                                               only_unique_items=False,
                                               sort_items=False,
                                               padx=5, pady=2, sticky='e')
        self._stringvar_ftp_status = tk.StringVar()
        self._label_ftp_status = tk.Label(right_frame, textvariable=self._stringvar_ftp_status)
        self._label_ftp_status.grid(row=4, column=0, **layout)

        self._button_send_files_via_ftp = tk.Button(right_frame, text='Skicka filer via ftp',
                                                    command=self._callback_continue_ftp)
        self._button_send_files_via_ftp.grid(row=4, column=1, padx=5, pady=2, sticky='se')

        self._button_back_to_pre_system = tk.Button(right_frame, text='Till Försystemet',
                                                    command=self._callback_pre_system)
        self._button_back_to_pre_system.grid(row=5, column=1, padx=5, pady=2, sticky='se')

        tkw.grid_configure(right_frame, nr_rows=6, nr_columns=2)

    def _on_toggle_ftp_test(self):
        self._update_files_ftp()
        self._stringvar_title_ftp.set(self._get_ftp_title())

    def _update_files_ftp(self, *args):
        self._files_on_ftp.update_items()
        cred = self.ftp_credentials
        if not cred:
            return
        obj = get_ftp_object(cred)
        file_list = sorted(obj.server_files[:], key=lambda x: x.lower(), reverse=True)
        file_list = [item for item in file_list if '.' in item] + [item for item in file_list if '.' not in item]
        self._files_on_ftp.update_items(file_list)

    def update_frame(self):
        self._local_data_path_ftp.set(path=self._file_handler.get_dir('local', 'data'))
        self._update_items()
        self._on_toggle_ftp_test()

    @property
    def ftp_credentials(self):
        cred_path = self._ftp_credentials_path.get()
        if not cred_path or not cred_path.exists():
            return {}
        with open(cred_path) as fid:
            cred = json.load(fid)
        cred['test'] = bool(self._ftp_test_checkbutton.get())
        return cred

    def _callback_continue_ftp(self):
        self._update_ftp_status('')

        cred = self.ftp_credentials
        if not cred:
            messagebox.showwarning('Skicka till FTP', 'Sökvägen till inloggningsuppgifter saknas eller är fel!')
            return

        files = self._files_local_ftp.get_selected()
        if not files:
            messagebox.showwarning('Skicka till FTP', 'Inga filer valda att skicka till ftp!')
            return

        self._update_ftp_status('Börjar skicka filer...')

        try:
            directory = self._local_data_path_ftp.get()
            paths = [Path(directory, file) for file in files]
            paths.extend(self._get_cnv_paths_matching_file_names(files))
            obj = get_ftp_object(cred, status_callback=self._ftp_progress)
            obj.add_files_to_send(*paths)
            obj.send_files()
            self._files_local_ftp.deselect_all()
            self._update_files_ftp()

            messagebox.showinfo('Skicka till FTP',
                                f'{len(paths)} filer har skickats till {self._get_ftp_destination()}')
        except ftp.FtpConnectionError:
            messagebox.showerror('Skicka filer till FTP', 'Kunde inte skicka filer. Kunde inte koppla upp mot ftp. Internet kanske inte fungerar.')
        except:
            messagebox.showerror('Skicka filer till FTP',
                                 f'Något gick fel: {traceback.format_exc()}')
        finally:
            self._update_ftp_status('')

    def _ftp_progress(self, status):
        t = status[0]
        n = status[1]
        percent = int(t/n*100)
        tail = '...'
        if percent == 100:
            tail = '!'
        self._update_ftp_status(f'{percent}% ({t} av {n} filer) skickat{tail}')

    def _update_ftp_status(self, string):
        self._stringvar_ftp_status.set(string)
        self._label_ftp_status.update_idletasks()

    def _callback_pre_system(self, *args):
        post_event('goto_pre_system_svea', None)

    def _get_cnv_paths_matching_file_names(self, file_names):
        if not self._also_send_cnv_files.get():
            return []
        matching_paths = []
        file_stems = [name.split('.')[0] for name in file_names]
        for path in self._file_handler.get_files('local', 'cnv').values():
            if path.suffix != '.cnv':
                continue
            if path.stem not in file_stems:
                continue
            matching_paths.append(path)
        return matching_paths

    def _update_items(self):
        if not self._local_data_path_ftp.get():
            return
        directory = Path(self._local_data_path_ftp.get()).resolve()
        if not directory.exists():
            return
        items = sorted([path.name for path in directory.iterdir()], reverse=True)
        self._files_local_ftp.update_items(items)

    def get_all_items(self):
        return self._files_local_ftp.get_all_items()

    def get_all_keys(self):
        return [item.split('.')[0] for item in self.get_all_items()]

    def deselect_all(self):
        self._files_local_ftp.deselect_all()

    def move_keys_to_selected(self, keys):
        items = [f'{key}.txt' for key in keys]
        self._files_local_ftp.move_items_to_selected(items)


def get_ftp_object(credentials, **kwargs):
    test = credentials.pop('test', True)
    obj = ftp.Ftp(**credentials, **kwargs)
    if test:
        obj.change_directory('test')
    return obj
