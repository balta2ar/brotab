import io
import mimetypes
import os
import socket
import sys
import tempfile
import uuid
from subprocess import CalledProcessError
from subprocess import check_call
from tempfile import NamedTemporaryFile
from typing import BinaryIO
from typing import Iterable
from typing import Union

from select import select

from brotab.platform import get_editor

MIN_MEDIATOR_PORT = 4625
MAX_MEDIATOR_PORT = MIN_MEDIATOR_PORT + 10


def slurp(filename):
    with open(filename) as file_:
        return file_.read()


def slurp_lines(filename):
    with open(filename) as file_:
        return [line.strip() for line in file_.readlines()]


def spit(filename, contents):
    with open(filename, 'w', encoding='utf-8') as file_:
        file_.write(contents)


def in_temp_dir(filename) -> str:
    temp_dir = tempfile.gettempdir()
    return os.path.join(temp_dir, filename)


def get_mediator_ports() -> Iterable:
    return range(MIN_MEDIATOR_PORT, MAX_MEDIATOR_PORT)


def get_available_tcp_port(start=1025, end=65536, host='127.0.0.1'):
    for port in range(start, end):
        if not is_port_accepting_connections(port, host):
            return port
    return RuntimeError('Cannot find available port in range %d:%d' % (start, end))


def is_port_accepting_connections(port, host='127.0.0.1'):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.100)
    result = s.connect_ex((host, port))
    s.close()
    return result == 0


def save_tabs_to_file(tabs, filename):
    with open(filename, 'w', encoding='utf-8') as file_:
        file_.write('\n'.join(tabs))


def maybe_remove_file(filename):
    if os.path.exists(filename):
        os.remove(filename)


def load_tabs_from_file(filename):
    with open(filename, encoding='utf-8') as file_:
        return [line.strip() for line in file_.readlines()]


def run_editor(executable: str, filename: str):
    return check_call([executable, filename])


def edit_tabs_in_editor(tabs_before):
    with NamedTemporaryFile() as file_:
        file_name = file_.name
        file_.close()
        save_tabs_to_file(tabs_before, file_name)
        try:
            run_editor(get_editor(), file_name)
            tabs_after = load_tabs_from_file(file_name)
            maybe_remove_file(file_name)
            return tabs_after
        except CalledProcessError:
            return None


def read_stdin(timeout=1.0):
    if select([sys.stdin, ], [], [], timeout)[0]:
        return sys.stdin.read()
    return ''


def read_stdin_lines():
    return [line.strip() for line in sys.stdin.readlines()]


def marshal(obj):
    if isinstance(obj, str):
        return obj.encode('utf-8')
    if isinstance(obj, list):
        data = '\n'.join(obj) + '\n'
        return data.encode('utf-8')
    return str(obj).encode('utf-8')


def stdout_buffer_write(message):
    return sys.stdout.buffer.write(message)


# Taken from https://pymotw.com/3/urllib.request/
class MultiPartForm:
    """Accumulate the data to be used when posting a form."""

    def __init__(self):
        self.form_fields = []
        self.files = []
        # Use a large random byte string to separate
        # parts of the MIME data.
        self.boundary = uuid.uuid4().hex.encode('utf-8')
        return

    def get_content_type(self):
        return 'multipart/form-data; boundary={}'.format(
            self.boundary.decode('utf-8'))

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, value))

    def add_file(self, fieldname, filename, fileHandle,
                 mimetype=None):
        """Add a file to be uploaded."""
        body = fileHandle.read()
        if mimetype is None:
            mimetype = (
                    mimetypes.guess_type(filename)[0] or
                    'application/octet-stream'
            )
        self.files.append((fieldname, filename, mimetype, body))
        return

    @staticmethod
    def _form_data(name):
        return ('Content-Disposition: form-data; '
                'name="{}"\r\n').format(name).encode('utf-8')

    @staticmethod
    def _attached_file(name, filename):
        return ('Content-Disposition: file; '
                'name="{}"; filename="{}"\r\n').format(
            name, filename).encode('utf-8')

    @staticmethod
    def _content_type(ct):
        return 'Content-Type: {}\r\n'.format(ct).encode('utf-8')

    def __bytes__(self):
        """Return a byte-string representing the form data,
        including attached files.
        """
        buffer = io.BytesIO()
        boundary = b'--' + self.boundary + b'\r\n'

        # Add the form fields
        for name, value in self.form_fields:
            buffer.write(boundary)
            buffer.write(self._form_data(name))
            buffer.write(b'\r\n')
            buffer.write(value.encode('utf-8'))
            buffer.write(b'\r\n')

        # Add the files to upload
        for f_name, filename, f_content_type, body in self.files:
            buffer.write(boundary)
            buffer.write(self._attached_file(f_name, filename))
            buffer.write(self._content_type(f_content_type))
            buffer.write(b'\r\n')
            buffer.write(body)
            buffer.write(b'\r\n')

        buffer.write(b'--' + self.boundary + b'--\r\n')
        return buffer.getvalue()


class TimeoutIO(io.BytesIO):
    def __init__(self, file_: Union[BinaryIO, int], timeout: float):
        super().__init__()
        self.file_ = file_
        self.timeout = timeout
        if isinstance(file_, int):
            self._write = lambda *args, **kwargs: os.write(file_, *args, **kwargs)
            self._read = lambda *args, **kwargs: os.read(file_, *args, **kwargs)
            self._close = lambda: os.close(file_)
            self._flush = lambda: None
        elif isinstance(file_, io.BufferedIOBase):
            self._write = file_.write
            self._read = file_.read
            self._close = file_.close
            self._flush = file_.flush
        else:
            raise TypeError('file_ must be an int or BinaryIO: %', type(file_))

    def read(self, *args, **kwargs) -> bytes:
        rlist, _, _ = select([self.file_], [], [], self.timeout)
        if rlist:
            return self._read(*args, **kwargs)
        else:
            raise TimeoutError('Read timeout ({}s)'.format(self.timeout))

    def write(self, *args, **kwargs) -> int:
        _, wlist, _ = select([], [self.file_], [], self.timeout)
        if wlist:
            return self._write(*args, **kwargs)
        else:
            raise TimeoutError('Write timeout ({}s)'.format(self.timeout))

    def flush(self) -> None:
        self._flush()

    def close(self) -> None:
        self._close()


# http://code.activestate.com/recipes/576655-wait-for-network-service-to-appear/
def wait_net_service(server, port, timeout=None):
    """ Wait for network service to appear
        @param timeout: in seconds, if None or 0 wait forever
        @return: True of False, if timeout is None may return only True or
                 throw unhandled network exception
    """
    s = socket.socket()
    if timeout:
        from time import time as now
        # time module is needed to calc timeout shared between two exceptions
        end = now() + timeout

    while True:
        try:
            if timeout:
                next_timeout = end - now()
                if next_timeout < 0:
                    raise TimeoutError('Timed out: %s' % timeout)
                else:
                    s.settimeout(next_timeout)

            s.connect((server, port))

        except socket.timeout as err:
            # this exception occurs only if timeout is set
            if timeout:
                raise TimeoutError('Timed out: %s' % timeout)

        except socket.error as err:
            # catch timeout exception from underlying network library
            # this one is different from socket.timeout
            if type(err.args) != tuple:  # or err[0] != errno.ETIMEDOUT:
                raise
        else:
            s.close()
            return
