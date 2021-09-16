
from pathlib import Path
import json


class Saves:

    def __init__(self):
        self.file_path = Path(Path(__file__).parent, 'saves.json')

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
        print('DATA', self.data)
        with open(self.file_path, 'w') as fid:
            json.dump(self.data, fid, indent=4, sort_keys=True)

    def set(self, key, value):
        self.data[key] = value
        self._save()

    def get(self, key, default=''):
        return self.data.get(key, default)


class SaveComponents:

    def __init__(self, key):
        self._saves = Saves()
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
                item = data.get(comp._id, None)
                if item is None:
                    continue
                comp.set(item)
            except:
                pass

