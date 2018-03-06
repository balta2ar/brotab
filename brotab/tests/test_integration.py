import time
import signal
import pytest
from unittest import TestCase

import delegator

from brotab.tests.utils import wait_net_service
from brotab.tests.utils import kill_by_substring


class TestChromium(TestCase):
    def setUp(self):
        # xvfb-run chromium-browser --no-sandbox --no-first-run --disable-gpu --remote-debugging-port=10222 --remote-debugging-address=0.0.0.0 --load-extension=/brotab/brotab/firefox_extension
        self._chrome = delegator.run(
            'xvfb-run chromium-browser --no-sandbox --no-first-run '
            '--disable-gpu --remote-debugging-port=10222 '
            '--remote-debugging-address=0.0.0.0 '
            '--load-extension=/brotab/brotab/firefox_extension',
            block=False)
        wait_net_service('localhost', 10222, 5)
        wait_net_service('localhost', 4625, 5)
        print('SETUP DONE:', self._chrome.pid)

    def tearDown(self):
        print('CHROME', self._chrome)
        # This is supposed to be run in Docker only
        # kill_by_substring('xvfb')
        # kill_by_substring('brotab')
        # psutil.Process(11970).children(recursive=True)
        print('BLOCK DONE')

    def test_smoke(self):
        print('>>>>>>>>> SMOKE')
