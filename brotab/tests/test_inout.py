from unittest import TestCase
from unittest.mock import patch

from brotab.inout import edit_tabs_in_editor


class TestEditor(TestCase):
    @patch('brotab.inout.run_editor')
    @patch('platform.system', side_effect=['Linux'])
    @patch('os.environ', new={})
    def test_run_editor_linux(self, _system_mock, _run_editor_mock):
        assert ['1'] == edit_tabs_in_editor(['1'])
        editor, _filename = _run_editor_mock.call_args[0]
        assert editor == 'nvim'

    @patch('brotab.inout.run_editor')
    @patch('platform.system', side_effect=['Windows'])
    @patch('os.environ', new={})
    def test_run_editor_windows(self, _system_mock, _run_editor_mock):
        assert ['1'] == edit_tabs_in_editor(['1'])
        editor, _filename = _run_editor_mock.call_args[0]
        assert editor == 'notepad'

    @patch('brotab.inout.run_editor')
    @patch('platform.system', side_effect=['Windows'])
    @patch('os.environ', new={'EDITOR': 'custom'})
    def test_run_editor_windows_custom(self, _system_mock, _run_editor_mock):
        assert ['1'] == edit_tabs_in_editor(['1'])
        editor, _filename = _run_editor_mock.call_args[0]
        assert editor == 'custom'

