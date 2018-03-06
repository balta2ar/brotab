from unittest import TestCase

from brotab.utils import split_tab_ids


class TestUtils(TestCase):
    def test_split_tab_ids(self):
        text = 'c.1.0 c.1.1\tc.1.2\r\nc.1.3 \r\t\n'
        expected = ['c.1.0', 'c.1.1', 'c.1.2', 'c.1.3']
        self.assertEqual(expected, split_tab_ids(text))
