import pathlib
import os
import traceback


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
    get_files_in_directory.counter.setdefault(directory, 0)
    get_files_in_directory.counter[directory] += 1
    print()
    print()
    print('='*50)
    stack = []
    for line in traceback.format_stack():
        text = line.strip().replace('\n', ' ')
        if 'page_start' not in text:
            continue
        split_text = text.split(',')
        line = split_text[1].split()[-1]
        fn = split_text[2].split()[1]
        stack.append(fn)
    stack.append(directory.name)
    get_files_in_directory.counter.setdefault('stack', [])
    get_files_in_directory.counter['stack'].append(' -> '.join(stack))
    print('='*50)
    print('get_files_in_directory')
    print('='*50)
    for key, value in get_files_in_directory.counter.items():
        if key == 'stack':
            print('STACK')
            for val in value:
                print(f'    {val}')
        else:
            print(f'{key=}, {value=}')
    print('-'*50)
    print()
    print()
    print()

    return files


get_files_in_directory.counter = {}


def open_path_in_default_program(path):
    os.startfile(str(path))


def open_paths_in_default_program(paths):
    for path in paths:
        open_path_in_default_program(path)