import pathlib


def get_files_in_directory(directory, suffix=None):
    files = []
    directory = pathlib.Path(directory)
    if not directory.exists():
        return []
    for path in directory.iterdir():
        if not path.is_file():
            continue
        if suffix and suffix != path.suffix:
            continue
        files.append(path.name)
    return files