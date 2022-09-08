import tkinter as tk
from tkinter import ttk
from typing import Callable
from file_explorer import Package
from sharkpylib import plot
import sharkpylib.tklib.tkinter_widgets as tkw


class PlotOptionsFrame(tk.Toplevel):
    def __init__(self, parent: tk.Frame, pack: Package, callback: Callable = None, **kwargs):
        self._pack = pack
        self._config = plot.get_parameter_config_for_pack(pack)
        self._callback = callback
        super().__init__(parent, **kwargs)
        self.attributes('-topmost', 'true')
        self.grab_set()
        self._build()

    def _build(self):
        self._config_stringvars = {}
        layout = dict(
            padx=5,
            pady=5,
            sticky='w'
        )

        r = 0
        tk.Label(self, text='Plotta data för fil:').grid(row=r, column=0, columnspan=3, **layout)
        r += 1
        tk.Label(self, text=self._pack.key).grid(row=r, column=0, columnspan=3, **layout)

        r += 1
        tk.Button(self, text='Skapa plottar med förbestämda värden',
                  command=self._create_without_config).grid(row=r, column=0, columnspan=3, **layout)

        r += 1
        ttk.Separator(self, orient='horizontal').grid(row=r, column=0, columnspan=3, **layout)

        r += 1
        tk.Label(self, text='Parameter').grid(row=r, column=0, **layout)
        tk.Label(self, text='Min och max i data').grid(row=r, column=1, **layout)
        tk.Label(self, text='xmin').grid(row=r, column=2, **layout)
        tk.Label(self, text='xmax').grid(row=r, column=3, **layout)

        r += 1
        for key, par in self._config.items():
            self._config_stringvars[key] = {}
            xmin, xmax = self._pack.get_file(suffix='.txt', prefix=None).get_par_range(par['data_par'])
            tk.Label(self, text=par['title']).grid(row=r, column=0, **layout)
            range_str = f'{str(xmin).ljust(10)} - {str(xmax).rjust(10)}'
            tk.Label(self, text=range_str).grid(row=r, column=1, **layout)
            var_min = tk.StringVar()
            var_max = tk.StringVar()
            var_min.set(str(par['xmin']))
            var_max.set(str(par['xmax']))
            ent_min = tk.Entry(self, textvariable=var_min)
            ent_min.grid(row=r, column=2, **layout)
            ent_max = tk.Entry(self, textvariable=var_max)
            ent_max.grid(row=r, column=3, **layout)
            var_min.trace("w", lambda name, index, mode, sv=var_min, ent=ent_min: tkw.check_float_entry(sv, ent))
            var_max.trace("w", lambda name, index, mode, sv=var_max, ent=ent_max: tkw.check_float_entry(sv, ent))
            self._config_stringvars[key]['xmin'] = var_min
            self._config_stringvars[key]['xmax'] = var_max
            r += 1

        tk.Button(self, text='Skapa plottar med manuellt satta värden',
                  command=self._create_with_config).grid(row=r, column=0, columnspan=3, **layout)

    def _get_config(self):
        config = {}
        for key, par in self._config.items():
            config[key] = {}
            config[key]['xmin'] = float(self._config_stringvars[key]['xmin'].get())
            config[key]['xmax'] = float(self._config_stringvars[key]['xmax'].get())
        return config

    def _create_without_config(self, *args):
        if not self._callback:
            return
        self._callback(self._pack)

    def _create_with_config(self, *args):
        if not self._callback:
            return
        config = self._get_config()
        self._callback(self._pack, **config)
