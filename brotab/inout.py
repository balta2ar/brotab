import io
import os
import sys
import uuid
import select
import socket
import mimetypes
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
    if select.select([sys.stdin, ], [], [], 1.0)[0]:
        return sys.stdin.read()
    return ''


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
