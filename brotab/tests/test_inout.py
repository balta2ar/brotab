import os
from unittest import TestCase
from unittest.mock import patch

from brotab.inout import edit_tabs_in_editor
from brotab.inout import TimeoutIO


class TestEditor(TestCase):
    @patch('brotab.inout.run_editor')
    @patch('platform.system', side_effect=['Linux'])
    @patch('os.environ', new={})
    def test_run_editor_linux(self, _system_mock, _run_editor_mock):
        assert ['1'] == edit_tabs_in_editor(['1'])
        editor, filename = _run_editor_mock.call_args[0]
        assert editor == 'nvim'
        assert not os.path.exists(filename)

    @patch('brotab.inout.run_editor')
    @patch('platform.system', side_effect=['Windows'])
    @patch('os.environ', new={})
    def test_run_editor_windows(self, _system_mock, _run_editor_mock):
        assert ['1'] == edit_tabs_in_editor(['1'])
        editor, filename = _run_editor_mock.call_args[0]
        assert editor == 'notepad'
        assert not os.path.exists(filename)

    @patch('brotab.inout.run_editor')
    @patch('platform.system', side_effect=['Windows'])
    @patch('os.environ', new={'EDITOR': 'custom'})
    def test_run_editor_windows_custom(self, _system_mock, _run_editor_mock):
        assert ['1'] == edit_tabs_in_editor(['1'])
        editor, filename = _run_editor_mock.call_args[0]
        assert editor == 'custom'
        assert not os.path.exists(filename)


class TestTimeoutIO(TestCase):
    def test_reads_from_buffered_file_without_losing_prefetched_bytes(self):
        read_fd, write_fd = os.pipe()
        try:
            with os.fdopen(read_fd, 'rb') as read_file:
                wrapped = TimeoutIO(read_file, 0.1)
                os.write(write_fd, b'12345678')

                assert wrapped.read(4) == b'1234'
                assert wrapped.read(4) == b'5678'
        finally:
            os.close(write_fd)
