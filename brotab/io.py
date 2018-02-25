import os
from tempfile import NamedTemporaryFile
from subprocess import check_call, CalledProcessError


def save_tabs_to_file(tabs, filename):
    with open(filename, 'w') as file_:
        file_.write('\n'.join(tabs))


def load_tabs_from_file(filename):
    with open(filename) as file_:
        return [line.strip() for line in file_.readlines()]


def edit_tabs_in_editor(tabs_before):
    with NamedTemporaryFile() as file_:
        save_tabs_to_file(tabs_before, file_.name)
        try:
            check_call([os.environ.get('EDITOR', 'nvim'), file_.name])
            tabs_after = load_tabs_from_file(file_.name)
            return tabs_after
        except CalledProcessError:
            return None
