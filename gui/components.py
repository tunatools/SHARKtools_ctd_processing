
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog

import datetime

from pathlib import Path

from ..events import post_event

from sharkpylib.tklib import tkinter_widgets as tkw


class MonospaceLabel(tk.Label):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        # self.config(font=("Courier", 10))
        self.config(font='TkFixedFont')


class LabelDropdownList(tk.Frame):

    def __init__(self,
                 parent,
                 id,
                 title='dropdown list',
                 width=10,
                 state='readonly',
                 **kwargs):

        self.grid_frame = {'padx': 5,
                           'pady': 5,
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)

        self._id = id
        self.title = title
        self.width = width
        self.state = state

        super().__init__(parent)
        self.grid(**self.grid_frame)

        self._old_value = None

        self._create_frame()

    def _create_frame(self):
        MonospaceLabel(self, text=self.title).grid(column=0, padx=5, pady=5, sticky='w')

        self._stringvar = tk.StringVar()
        self.combobox = ttk.Combobox(self, width=self.width, textvariable=self._stringvar, state=self.state)
        self.combobox.bind("<<ComboboxSelected>>", self._on_select)
        self.combobox.bind("<<FocusIn>>", self._on_focus_in)
        self.combobox.bind("<<FocusOut>>", self._on_focus_out)
        self.combobox.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        tkw.grid_configure(self, nr_columns=2)

    def _has_new_value(self):
        current_value = self._stringvar.get()
        if current_value == self._old_value:
            return False
        self._old_value = current_value
        return True

    def _on_focus_in(self, *args):
        self._old_value = self._stringvar.get()

    def _on_focus_out(self, *args):
        if not self._has_new_value():
            return
        post_event(f'focus_out_{self._id}', self.value)

    def _on_select(self, *args):
        if not self._has_new_value():
            return
        post_event(f'select_{self._id}', self.value)

    @property
    def values(self):
        return self.combobox['values']

    @values.setter
    def values(self, items):
        current_value = self._stringvar.get()
        self.combobox['values'] = items
        if current_value not in items:
            self._stringvar.set('')

    @property
    def value(self):
        return self._stringvar.get()

    @value.setter
    def value(self, item):
        self._stringvar.set(item)

    def get(self):
        return self.value

    def set(self, item):
        self.value = item


class LabelText(tk.Frame):

    def __init__(self,
                 parent,
                 id,
                 title='LabelText',
                 **kwargs):

        self.grid_frame = {'padx': 5,
                           'pady': 5,
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)

        self._id = id
        self.title = title

        super().__init__(parent)
        self.grid(**self.grid_frame)

        self._create_frame()

    def _create_frame(self):
        self._stringvar = tk.StringVar()
        self.label = tk.Label(self, text=self.title)
        self.label.grid(column=0, row=0, padx=5, pady=5, sticky='nw')
        tk.Label(self, textvariable=self._stringvar).grid(column=1, row=0, padx=5, pady=5, sticky='nw')

    @property
    def value(self):
        string = self._stringvar.get()
        if not string:
            return False
        return string

    @value.setter
    def value(self, item):
        if not item:
            self._stringvar.set('')
        else:
            self._stringvar.set(str(item))


class Checkbutton(tk.Frame):

    def __init__(self,
                 parent,
                 id,
                 title='CheckboxText',
                 **kwargs):

        self.grid_frame = {'padx': 5,
                           'pady': 5,
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)

        self._id = id
        self.title = title

        super().__init__(parent)
        self.grid(**self.grid_frame)

        self._create_frame()

    def _create_frame(self):
        self._booleanvar = tk.BooleanVar()
        self.checkbutton = tk.Checkbutton(self, text=self.title, variable=self._booleanvar, command=self._on_checkbutton_click)
        self.checkbutton.grid(column=0, row=0, padx=5, pady=5, sticky='nw')
        # tk.Label(self, textvariable=self._stringvar).grid(column=1, row=0, padx=5, pady=5, sticky='nw')

    def _on_checkbutton_click(self):
        post_event(f'change_{self._id}', self.value)

    @property
    def value(self):
        return self._booleanvar.get()

    @value.setter
    def value(self, value):
        self._booleanvar.set(bool(value))

    def get(self):
        return self.value

    def set(self, value):
        self.value = value



class ButtonText(tk.Frame):

    def __init__(self,
                 parent,
                 id,
                 title='ButtonText',
                 **kwargs):

        self.grid_frame = {'padx': 5,
                           'pady': 5,
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)

        self._id = id
        self.title = title

        super().__init__(parent)
        self.grid(**self.grid_frame)

        self._create_frame()

    def _create_frame(self):
        self._stringvar = tk.StringVar()
        self.button = tk.Button(self, text=self.title, command=self._on_button_click)
        self.button.grid(column=0, row=0, padx=5, pady=5, sticky='nw')
        tk.Label(self, textvariable=self._stringvar).grid(column=1, row=0, padx=5, pady=5, sticky='nw')

    def _on_button_click(self, event):
        post_event(f'button_click_{self._id}', self.value)

    @property
    def value(self):
        return self._stringvar.get()

    @value.setter
    def value(self, item):
        self._stringvar.set(item)


class DirectoryButtonText(tk.Frame):

    def __init__(self,
                 parent,
                 id,
                 title='ButtonText',
                 **kwargs):

        self.grid_frame = {'padx': 5,
                           'pady': 5,
                           'sticky': 'nsew'}

        self._id = id
        self.title = title

        self._end_with_folders_original = kwargs.pop('end_with_folders', [])
        self._end_with_folders = self._end_with_folders_original[:]
        self._hard_press = kwargs.pop('hard_press', False)
        self._root_folder = None

        self.grid_frame.update(kwargs)
        super().__init__(parent)
        self.grid(**self.grid_frame)

        self._create_frame()

    def _create_frame(self):
        self._stringvar = tk.StringVar()
        self.button = tk.Button(self, text=self.title, command=self._on_button_click)
        self.button.grid(column=0, row=0, padx=5, pady=5, sticky='nw')
        tk.Label(self, textvariable=self._stringvar).grid(column=1, row=0, padx=5, pady=5, sticky='nw')
        if self._hard_press:
            self.button.bind('<Control-Button-1>', self._on_button_click_hard)

    def _open_dialog(self):
        directory = filedialog.askdirectory(title=self.title)
        if not directory:
            return
        directory = Path(directory)
        self._fix_ends_with_folders()
        directory = self._fix_path(directory)

        self._stringvar.set(str(directory))
        post_event(f'change_{self._id}', directory)

    def _on_button_click(self):
        if self._hard_press:
            return
        self._open_dialog()

    def _on_button_click_hard(self, event):
        self._open_dialog()

    def _fix_path(self, path):
        if not path:
            return ''
        parts = list(path.parts)
        for folder in reversed(self._end_with_folders):
            if folder == parts[-1]:
                parts = parts[:-1]
        self._root_folder = Path(*parts)
        all_parts = parts + self._end_with_folders
        return Path(*all_parts)

    def _fix_ends_with_folders(self, year=None):
        year = year or datetime.datetime.now().year
        new_list = []
        for item in self._end_with_folders_original:
            if item.upper() == '<YEAR>':
                item = str(year)
            new_list.append(item)
        self._end_with_folders = new_list

    @property
    def value(self):
        string = self._stringvar.get()
        if not string:
            return False
        return string

    @value.setter
    def value(self, item):
        if not item:
            self._stringvar.set('')
        else:
            self._stringvar.set(str(item))

    def get(self):
        return self._root_folder

    def set(self, path=None, year=None):
        if not path:
            path = self._root_folder
        else:
            path = Path(path)
        if year:
            self._fix_ends_with_folders(year)
        path = self._fix_path(path)
        self.value = path


class FilePathButtonText(tk.Frame):

    def __init__(self,
                 parent,
                 id,
                 title='FilePathButtonText',
                 **kwargs):

        self.grid_frame = {'padx': 5,
                           'pady': 5,
                           'sticky': 'nsew'}

        self._id = id
        self.title = title
        self._hard_press = kwargs.pop('hard_press', False)

        self.grid_frame.update(kwargs)
        super().__init__(parent)
        self.grid(**self.grid_frame)

        self._create_frame()

    def _create_frame(self):
        self._stringvar = tk.StringVar()
        self.button = tk.Button(self, text=self.title, command=self._on_button_click)
        self.button.grid(column=0, row=0, padx=5, pady=5, sticky='nw')
        tk.Label(self, textvariable=self._stringvar).grid(column=1, row=0, padx=5, pady=5, sticky='nw')
        if self._hard_press:
            self.button.bind('<Control-Button-1>', self._on_button_click_hard)

    def _open_dialog(self):
        path = filedialog.askopenfilename(title=self.title)
        if not path:
            return
        path = Path(path)

        self._stringvar.set(str(path))
        post_event(f'change_{self._id}', path)

    def _on_button_click(self):
        if self._hard_press:
            return
        self._open_dialog()

    def _on_button_click_hard(self, event):
        self._open_dialog()

    @property
    def value(self):
        string = self._stringvar.get()
        if not string:
            return False
        return Path(string)

    @value.setter
    def value(self, item):
        if not item:
            self._stringvar.set('')
        else:
            self._stringvar.set(str(item))

    def get(self):
        return self.value

    def set(self, path=None):
        if not path:
            return
        path = Path(path)
        self.value = path


class DirectoryLabelText(LabelText):

    def __init__(self, *args, **kwargs):
        self._end_with_folders_original = kwargs.pop('end_with_folders', [])
        self._disabled = kwargs.pop('disabled', False)
        self._end_with_folders = self._end_with_folders_original[:]
        self._root_folder = None
        super().__init__(*args, **kwargs)
        if not self._disabled:
            self.label.bind('<Control-Button-1>', self._on_select_directory)

    def _on_select_directory(self, event):
        directory = filedialog.askdirectory()
        if not directory:
            return
        directory = Path(directory)
        self._fix_ends_with_folders()
        directory = self._fix_path(directory)

        self._stringvar.set(str(directory))
        post_event(f'change_{self._id}', directory)

    def _fix_path(self, path):
        if not path:
            return ''
        parts = list(path.parts)
        for folder in reversed(self._end_with_folders):
            if folder == parts[-1]:
                parts = parts[:-1]
        self._root_folder = Path(*parts)
        all_parts = parts + self._end_with_folders
        return Path(*all_parts)

    def _fix_ends_with_folders(self, year=None):
        year = year or datetime.datetime.now().year
        new_list = []
        for item in self._end_with_folders_original:
            if item.upper() == '<YEAR>':
                item = str(year)
            new_list.append(item)
        self._end_with_folders = new_list

    @property
    def value(self):
        return self._stringvar.get()

    @value.setter
    def value(self, item):
        self._stringvar.set(str(item))

    def get(self):
        return self.value

    def set(self, path=None, year=None):
        if not path and not self._end_with_folders_original:
            self.value = ''
            return
        if not path:
            path = self._root_folder
        else:
            path = Path(path)
        if year:
            self._fix_ends_with_folders(year)
        path = self._fix_path(path)
        self.value = path


class LabelEntry(tk.Frame):

    def __init__(self,
                 parent,
                 id,
                 title='entry',
                 width=8,
                 state='normal',
                 data_type=None,
                 **kwargs):

        self.grid_frame = {'padx': 5,
                           'pady': 5,
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)

        self._id = id
        self.title = title
        self.width = width
        self.data_type = data_type
        self.state = state

        super().__init__(parent)
        self.grid(**self.grid_frame)

        self._create_frame()

    def _create_frame(self):
        layout = dict(padx=5,
                      pady=5,
                      sticky='nsew')
        MonospaceLabel(self, text=self.title).grid(column=0, **layout)

        self._stringvar = tk.StringVar()
        self._stringvar.trace("w", self._on_change_entry)

        self.entry = tk.Entry(self, textvariable=self._stringvar, width=self.width)
        self.entry.bind('<FocusOut>', self._on_focus_out)
        self.entry.bind('<Return>', self._on_focus_out)
        self.entry.grid(row=0, column=1, **layout)
        self.entry.configure(state=self.state)

        tkw.grid_configure(self, nr_columns=3)

    def _on_focus_out(self, *args):
        post_event(f'focus_out_{self._id}', self.value)
        # for func in self._cb:
        #     func(self.value)

    def _on_change_entry(self, *args):
        string = self._stringvar.get()
        if self.data_type == int:
            string = ''.join([s for s in string if s.isdigit()])
            self._stringvar.set(string)
        elif self.data_type == float:
            return_list = []
            for s in string:
                if s.isdigit():
                    return_list.append(s)
                elif s == '.' and '.' not in return_list:
                    return_list.append(s)

            return_string = ''.join(return_list)
            self._stringvar.set(return_string)

    @property
    def value(self):
        return self._stringvar.get()

    @value.setter
    def value(self, value):
        self._stringvar.set(str(value))
        self._on_change_entry()

    def get(self):
        return self.value

    def set(self, item):
        self.value = item


class YearEntry(LabelEntry):
    def s__init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.entry.configure(state='disabled')
        self.entry.bind('<Control-Button-1>', self._on_click_entry)
        self.entry.bind('<FocusIn>', self._on_click_entry)
        self.entry.bind('<FocusOut>', self._on_focus_out)
        self.entry.bind('<Return>', self._on_focus_out)

    def _on_click_entry(self, event):
        # self.entry.configure(state='normal')
        if self.value:
            self.entry.selection_range(0, 'end')
        else:
            self.entry.focus_set()

    def _on_focus_out(self, event):
        # self.entry.configure(state='disabled')
        post_event(f'change_{self._id}', self.value)

    def _on_change_entry(self, *args):
        string = self._stringvar.get()
        string = ''.join([s for s in string if s.isdigit()])[:4]
        self._stringvar.set(string)


class ListboxWidget(tk.Frame):
    def __init__(self,
                 parent,
                 id,
                 title='SeriesSelection',
                 prop_listbox={},
                 **kwargs):

        self.grid_frame = {'padx': 5,
                           'pady': 5,
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)

        self._id = id
        self.title = title
        self.prop_listbox = {'width': 50, 'height': 8}
        self.prop_listbox.update(prop_listbox)

        super().__init__(parent)
        self.grid(**self.grid_frame)

        self._create_frame()

    def _create_frame(self):
        layout = dict(padx=5,
                      pady=1,
                      sticky='nw')

        tk.Label(self, text=self.title).grid(row=0, column=0, **layout)

        self.selection_widget = tkw.ListboxWidget(self,
                                                  prop_listbox=self.prop_listbox,
                                                  include_delete_button=False,
                                                  row=1, column=0, **layout)

        tkw.grid_configure(self, nr_rows=2)

    def set(self, paths=[]):
        items = [Path(path).name for path in paths]
        self.selection_widget.update_items(items)


class SeriesSelection(tk.Frame):

    def __init__(self,
                 parent,
                 id,
                 title='SeriesSelection',
                 **kwargs):

        self.grid_frame = {'padx': 5,
                           'pady': 5,
                           'sticky': 'nsew'}
        self.grid_frame.update(kwargs)

        self._id = id
        self.title = title

        super().__init__(parent)
        self.grid(**self.grid_frame)

        self._create_frame()

    def _create_frame(self):
        layout = dict(padx=5,
                      pady=1,
                      sticky='nw')

        tk.Label(self, text=self.title).grid(row=0, column=0, **layout)

        prop = {'width': 45,
                'height': 8}
        self.selection_widget = tkw.ListboxSelectionWidget(self,
                                                           callback_select=self._on_select,
                                                           callback_deselect=self._on_deselect,
                                                           prop_items=prop,
                                                           prop_selected=prop,
                                                           row=1, column=0, **layout)

        tkw.grid_configure(self, nr_rows=2)

    def _on_select(self):
        post_event(f'update_{self._id}', self.selection_widget.get_selected())

    def _on_deselect(self):
        post_event(f'update_{self._id}', self.selection_widget.get_selected())

    def set(self, items=[]):
        self.selection_widget.update_items(sorted(items))

    def get_selected(self):
        return self.selection_widget.get_selected()


