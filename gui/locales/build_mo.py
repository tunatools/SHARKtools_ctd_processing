import os, pathlib, polib
for root, dirs, files in os.walk(pathlib.Path(__file__).parent):
    for name in files:
        file_path = pathlib.Path(root, name)
        if file_path.suffix == '.po':
            po = polib.pofile(file_path)
            mo = file_path.with_suffix('.mo')
            po.save_as_mofile(mo)
