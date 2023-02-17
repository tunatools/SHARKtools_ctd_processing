
subscribers = dict()
subscribers_before = dict()
subscribers_after = dict()


class InvalidEventType(Exception):
    pass


class EventTypes:
    def __init__(self):
        self.event_types = [
            'select_platform',
            'select_surfacesoak',
            'change_local_data_path_source',
            'change_local_data_path_root',
            'change_config_path',
            'change_server_data_path_root',
            'change_tau',
            'change_overwrite',
            'change_simple_old_key',
            'update_series_local_source',
            'change_local_data_path_raw',
            'change_year',
            'change_ftp_credentials_path',
            'goto_pre_system_svea',
            'change_metadata_packs_source',
            'change_metadata_packs_target',
            'change_metadata_packs_sharkweb_path',
            'change_metadata_packs_lims_path',
        ]

        for item in self.event_types:
            setattr(self, item, item)

    def __contains__(self, item):
        if item in self.event_types:
            return True
        return False


def _remove_existing(event_type, func):
    func_part = str(func).split()[2]
    for sub in [subscribers_before, subscribers, subscribers_after]:
        for f in list(sub.get(event_type, [])):
            if func_part == str(f).split()[2]:
                print('REMOVING:', func_part)
                sub[event_type].remove(f)


def subscribe(event_type, func, before=False, after=False):
    _remove_existing(event_type, func)
    # print('ADDING event:', event_type)
    if event_type not in EventTypes():
        raise InvalidEventType(event_type)
    if before:
        if event_type not in subscribers_before:
            subscribers_before[event_type] = set()
        subscribers_before[event_type].add(func)
    elif after:
        if event_type not in subscribers_after:
            subscribers_after[event_type] = set()
        subscribers_after[event_type].add(func)
    else:
        if event_type not in subscribers:
            subscribers[event_type] = set()
        subscribers[event_type].add(func)


def post_event(event_type, data, **kwargs):
    for sub in [subscribers_before, subscribers, subscribers_after]:
        if event_type not in sub:
            continue
        for func in sub[event_type]:
            func(data, **kwargs)


def nr_subscribers(event_type):
    return len(subscribers[event_type])


def print_even_types():
    print('=' * 50)
    print('Current event_types (before) are:')
    print('-' * 50)
    for event_type in sorted(subscribers_before):
        print(' ' * 4, event_type)
    print('-' * 50)
    print('Current event_types are:')
    print('-' * 50)
    for event_type in sorted(subscribers):
        print(' ' * 4, event_type)
    print('=' * 50)


def print_subscribers():
    print('=' * 50)
    print('Current subscribers_before are:')
    print('-' * 50)
    for event_type in sorted(subscribers_before):
        print(' ' * 4, 'event_type:', event_type)
        for func in subscribers_before[event_type]:
            print(' ' * 8, func)
    print('-' * 50)
    print('Current subscribers are:')
    print('-' * 50)
    for event_type in sorted(subscribers):
        print(' ' * 4, 'event_type:', event_type)
        for func in subscribers[event_type]:
            print(' ' * 8, func)
    print('=' * 50)


def test_subscriber():
    print('I am a test subscriber function!')


if __name__ == '__main__':
    subscribe('select_instrument', test_subscriber)
    et = EventTypes()
