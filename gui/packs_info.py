from sharkpylib.tklib import tkinter_widgets as tkw
import tkinter as tk


class PacksInfo(tk.Frame):
    suffixes = ['.txt', '.cnv', '.hex', '.hdr', '.bl', '.btl', '.ros', '.xmlcon', '.con', '.jpg', '.deliverynote',
                  '.metadata', '.sensorinfo']
    compilation = ['Första tid', 'Sista tid',
                    'Antal paket',
                    'Antal paket med rätt nyckel',
                    'Antal processerade paket',
                    'Antal paket med standardformat']

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._all_packs = None
        self._selected_packs = None
        self._selected_packs_info = {}
        self._stringvars_nr_files = {}
        self._stringvars_compilation = {}
        self._labels_compilation = {}

        self._callback_select = kwargs.pop('callback_select', None)

        self._create_variables()
        self._build()

    def _create_variables(self):
        self._stringvars_nr_files = {}
        for item in self.suffixes:
            self._stringvars_nr_files[item] = tk.StringVar()

        for item in self.compilation:
            self._stringvars_compilation[item] = tk.StringVar()

    def _build(self):

        self._frame_key = tk.LabelFrame(self, text='Matchande nycklar')
        self._frame_key.grid(row=0, column=0)

        self._notebook = tkw.NotebookWidget(self, frames=['Sammanställning', 'Metadata'], row=1, column=0)

        tkw.grid_configure(self, nr_rows=2, nr_columns=0)

        self._build_frame_keys()
        self._build_frame_compilation()
        self._build_frame_metadata()

    def _build_frame_keys(self):
        frame = self._frame_key
        props = dict(width=82, height=8, font=("Consolas", 10))
        self._listbox_keys = tkw.ListboxSelectionWidget(frame,
                                                      callback=self._on_select_keys,
                                                      prop_items=props,
                                                      prop_selected=props,
                                                      row=0, column=0)

        tkw.grid_configure(frame, nr_rows=1, nr_columns=1)

    def _build_frame_compilation(self):
        frame = self._notebook.get_frame('Sammanställning')
        left_frame = tk.Frame(frame)
        left_frame.grid(row=0, column=0)
        right_frame = tk.Frame(frame)
        right_frame.grid(row=0, column=1)
        tkw.grid_configure(frame, nr_rows=0, nr_columns=2)
        grid = dict(padx=5, pady=2)

        # Left frame
        r = 0
        for meta, stringvar in self._stringvars_compilation.items():
            tk.Label(left_frame, text=meta).grid(row=r, column=0, **grid, sticky='e')
            label = tk.Label(left_frame, textvariable=stringvar)
            label.grid(row=r, column=1, **grid, sticky='w')
            self._labels_compilation[meta] = label
            r += 1
        tkw.grid_configure(left_frame, nr_rows=r, nr_columns=2)

        # Right frame
        r = 0
        for suffix, stringvar in self._stringvars_nr_files.items():
            tk.Label(right_frame, text=f'Antal {suffix}-filer:').grid(row=r, column=0, **grid, sticky='e')
            tk.Label(right_frame, textvariable=stringvar).grid(row=r, column=1, **grid, sticky='w')
            r += 1
        tkw.grid_configure(right_frame, nr_rows=r, nr_columns=2)

    def _build_frame_metadata(self):
        frame = self._notebook.get_frame('Metadata')
        grid = dict(padx=5, pady=2)
        r = 0
        self._stringvar_meta_item = tk.StringVar()
        tk.Label(frame, text=f'Metadatavariabel:').grid(row=r, column=0, **grid, sticky='e')
        self._entry_meta_item = tk.Entry(frame, textvariable=self._stringvar_meta_item)
        self._entry_meta_item.grid(row=r, column=1, **grid, sticky='w')
        self._entry_meta_item.bind('<Return>', self._update_metadata)
        tk.Button(frame, text='Visa', command=self._update_metadata).grid(row=r, column=2, **grid, sticky='w')
        r += 1

        self._stringvar_meta_unique = tk.StringVar()
        tk.Label(frame, text=f'Unika förekomster:').grid(row=r, column=0, **grid, sticky='e')
        tk.Label(frame, textvariable=self._stringvar_meta_unique).grid(row=r, column=1, **grid, sticky='w')
        r += 1

        props = dict(width=100, height=8, font=("Consolas", 10))
        self._listbox_meta = tkw.ListboxWidget(frame, prop_listbox=props, include_delete_button=False,
                                               row=r, column=0, columnspan=3)

        tkw.grid_configure(frame, nr_rows=r+1, nr_columns=2)

    def _on_select_keys(self):
        selected_keys = self._listbox_keys.get_selected()
        self._selected_packs = []
        all_patterns = {}
        for item in selected_keys:
            pat, key = [part.strip() for part in item.split('::')]
            all_patterns[pat] = True
        self._selected_packs = [pack for pack in self._all_packs if all_patterns.get(pack.pattern)]
        self._selected_packs_info = self._get_packs_info(self._selected_packs)
        self._update_on_selected()
        if self._callback_select:
            self._callback_select(self._selected_packs)

    def set_packs(self, packs):
        self._reset()
        self._all_packs = packs
        self._update_listbox_keys()

    def _reset(self):
        for stringvar in self._stringvars_nr_files.values():
            stringvar.set('')

        self._packs = None
        self._selected_packs = None
        self._selected_packs_info = {}

    def _update_listbox_keys(self):
        self._listbox_keys.update_items()  # This will reset the listbox
        if not self._all_packs:
            return
        file_names = []
        for pack in self._all_packs:
            string = f'{pack.pattern.ljust(35)}  ::  {pack.key}'
            file_names.append(string)
        self._listbox_keys.update_items(file_names)

    def _update_on_selected(self):
        self._update_compilation()

    def _update_compilation(self):
        self._reset_compilation()
        compilation = self._selected_packs_info.get('compilation', {})
        nr_packs = compilation['Antal paket']
        for key, value in compilation.items():
            self._stringvars_compilation[key].set(str(value))
            if key.startswith('Antal') and value < nr_packs:
                self._labels_compilation[key].configure(fg='red')

        nr_files = self._selected_packs_info.get('nr_files', {})
        for suffix, nr in nr_files.items():
            if not self._stringvars_nr_files.get(suffix):
                continue
            self._stringvars_nr_files[suffix].set(str(nr or 0))

    def _update_metadata(self, *args):
        self._reset_metadata()
        if not self._selected_packs:
            return
        key = self._stringvar_meta_item.get().strip().lower()
        if not key:
            return
        string_list = []
        meta_set = set()
        for pack in self._selected_packs:
            if key.startswith('.'):
                value = bool(pack[key])
            else:
                value = pack(key)
            meta_set.add(str(value))
            string_list.append(f'{str(value).ljust(70)}   =>   {pack.key}')
        self._listbox_meta.update_items(sorted(string_list))

        import textwrap
        string = '; '.join(sorted(meta_set))
        string = textwrap.fill(string, 100)
        self._stringvar_meta_unique.set(string)

    def _reset_compilation(self):
        for key in self._stringvars_compilation:
            self._stringvars_compilation[key].set('')
            self._labels_compilation[key].configure(fg='black')

    def _reset_metadata(self):
        self._stringvar_meta_unique.set('')
        self._listbox_meta.update_items()

    @staticmethod
    def _get_packs_info(packs_list):
        if not packs_list:
            return {}
        nr_files = {}
        compilation = {}
        time_format = '%Y-%m-%d %H:%M:%S (%A vecka %W)'
        sorted_packs = sorted(packs_list)
        compilation['Första tid'] = sorted_packs[0].datetime.strftime(time_format)
        compilation['Sista tid'] = sorted_packs[-1].datetime.strftime(time_format)
        compilation['Antal paket'] = len(sorted_packs)
        nr_correct_keys = 0
        nr_processed_packs = 0
        nr_standard_format = 0
        for pack in sorted_packs:
            for file in pack.files:
                nr_files.setdefault(file.suffix, 0)
                nr_files[file.suffix] += 1
            cnv = pack['cnv']
            if cnv:
                nr_processed_packs += 1
            txt = pack['txt']
            if txt:
                nr_standard_format += 1
            if pack.pattern == pack.key:
                nr_correct_keys += 1
        compilation['Antal processerade paket'] = nr_processed_packs
        compilation['Antal paket med standardformat'] = nr_standard_format
        compilation['Antal paket med rätt nyckel'] = nr_correct_keys

        info = dict(nr_files=nr_files,
                    compilation=compilation)
        return info

    @property
    def selected_packs(self):
        return self._selected_packs
