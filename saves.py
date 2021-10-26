
import yaml
from yaml.loader import SafeLoader
import pathlib
import json


class Defaults:

    def __init__(self):
        self.file_path = pathlib.Path(pathlib.Path(__file__).parent, 'defaults.yaml')

        self.data = {}

        self._load()

    def _load(self):
        """
        Loads dict from json
        :return:
        """
        if self.file_path.exists():
            with open(self.file_path) as fid:
                self.data = yaml.load(fid, Loader=SafeLoader)

    def get(self, key, default=None):
        return self.data.get(key, default)


class Saves:

    def __init__(self):
        self.file_path = pathlib.Path(pathlib.Path(__file__).parent, 'saves.json')

        self.data = {}

        self._load()

    def _load(self):
        """
        Loads dict from json
        :return:
        """
        if self.file_path.exists():
            with open(self.file_path) as fid:
                self.data = json.load(fid)

    def _save(self):
        """
        Writes information to json file.
        :return:
        """
        with open(self.file_path, 'w') as fid:
            json.dump(self.data, fid, indent=4, sort_keys=True)

    def set(self, key, value):
        self.data[key] = value
        self._save()

    def get(self, key, default=''):
        return self.data.get(key, default)


class SaveSelection:
    _saves = Saves()
    _defaults = Defaults()
    _saves_id_key = ''
    _selections_to_store = []

    def save_selection(self):
        data = {}
        if type(self._selections_to_store) == dict:
            for name, comp in self._selections_to_store.items():
                try:
                    data[name] = comp.get()
                except:
                    pass
        else:
            for comp in self._selections_to_store:
                try:
                    data[comp] = getattr(self, comp).get()
                except:
                    pass
        self._saves.set(self._saves_id_key, data)

    def load_selection(self):
        data = self._saves.get(self._saves_id_key)
        if type(self._selections_to_store) == dict:
            for name, comp in self._selections_to_store.items():
                try:
                    value = self._defaults.get(name)
                    if value is None:
                        value = data.get(name, None)
                        if value is None:
                            continue
                    comp.set(value)
                except:
                    pass
        else:
            for comp in self._selections_to_store:
                try:
                    value = self._defaults.get(self._saves_id_key)
                    if value is None:
                        value = data.get(comp, None)
                        if value is None:
                            continue
                    getattr(self, comp).set(value)
                except:
                    raise


class SaveComponents:

    def __init__(self, key):
        self._saves = Saves()
        self._defaults = Defaults()
        self._saves_id_key = key
        self._components_to_store = set()

    def add_components(self, *args):
        for comp in args:
            self._components_to_store.add(comp)

    def save(self):
        data = {}
        for comp in self._components_to_store:
            try:
                data[comp._id] = str(comp.get())
                # print(f'SAVING: {comp._id} - {data[comp._id]}')
            except:
                pass
        self._saves.set(self._saves_id_key, data)

    def load(self):
        data = self._saves.get(self._saves_id_key)
        for comp in self._components_to_store:
            try:
                item = self._defaults.get(comp._id, None)
                if item is None:
                    item = data.get(comp._id, None)
                if item is None:
                    continue
                comp.set(item)
            except:
                pass

