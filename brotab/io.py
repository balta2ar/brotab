import os
import sys
import select
import socket
from tempfile import NamedTemporaryFile
from subprocess import check_call, CalledProcessError


def is_port_accepting_connections(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.100)
    result = s.connect_ex(('127.0.0.1', port))
    s.close()
    return result == 0


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


def read_stdin():
    if select.select([sys.stdin,], [], [], 1.0)[0]:
        return sys.stdin.read()
    return ''
