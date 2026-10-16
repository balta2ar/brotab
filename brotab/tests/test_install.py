import json
import os
from argparse import Namespace
from unittest import TestCase
from unittest.mock import patch
from tempfile import TemporaryDirectory

from brotab.main import install_mediator

FIREFOX_DIR = '.mozilla/native-messaging-hosts'
CHROMIUM_DIR = '.config/chromium/NativeMessagingHosts'


class TestInstallMediator(TestCase):
    def setUp(self):
        self._home = TemporaryDirectory()
        self.home = self._home.name
        patches = [
            patch.dict(os.environ, {'HOME': self.home}),
            patch('brotab.main.which', return_value='/opt/bin/brotab_mediator'),
            patch('brotab.main.is_windows', return_value=False),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self._home.cleanup)

    def install(self, browser='all', tests=False):
        install_mediator(Namespace(browser=browser, tests=tests))

    def read(self, subdir, name):
        with open(os.path.join(self.home, subdir, name)) as f:
            return json.load(f)

    def test_brotab_host(self):
        self.install()
        firefox = self.read(FIREFOX_DIR, 'brotab_mediator.json')
        self.assertEqual(firefox['name'], 'brotab_mediator')
        self.assertEqual(firefox['path'], '/opt/bin/brotab_mediator')
        self.assertEqual(firefox['allowed_extensions'], ['brotab_mediator@example.org'])
        chromium = self.read(CHROMIUM_DIR, 'brotab_mediator.json')
        self.assertIn('chrome-extension://knldjmfmopnpolahpmmgbagdohdnhkik/',
                      chromium['allowed_origins'])

    def test_bruvtab_compat_host(self):
        # The signed bruvtab extensions from the browser stores connect to a
        # host named bruvtab_mediator; serve them with the brotab mediator.
        self.install()
        firefox = self.read(FIREFOX_DIR, 'bruvtab_mediator.json')
        self.assertEqual(firefox['name'], 'bruvtab_mediator')
        self.assertEqual(firefox['path'], '/opt/bin/brotab_mediator')
        self.assertEqual(firefox['allowed_extensions'], ['bruvtab_mediator@example.org'])
        chromium = self.read(CHROMIUM_DIR, 'bruvtab_mediator.json')
        self.assertEqual(chromium['name'], 'bruvtab_mediator')
        self.assertEqual(chromium['path'], '/opt/bin/brotab_mediator')
        self.assertEqual(sorted(chromium['allowed_origins']), [
            'chrome-extension://bkifkhiemhgpnomgdcbcbkifekkecnhk/',
            'chrome-extension://edpgjheobdplebiikjgjgpmonakingef/',
        ])

    def test_browser_filter(self):
        self.install(browser='firefox')
        self.read(FIREFOX_DIR, 'bruvtab_mediator.json')
        self.assertFalse(os.path.exists(os.path.join(self.home, CHROMIUM_DIR)))

    def test_browser_filter_chrome(self):
        self.install(browser='chrome')
        self.read('.config/google-chrome/NativeMessagingHosts', 'bruvtab_mediator.json')
        self.assertFalse(os.path.exists(os.path.join(self.home, CHROMIUM_DIR)))
        self.assertFalse(os.path.exists(os.path.join(self.home, FIREFOX_DIR)))

    def test_tests_manifest_gets_no_compat_host(self):
        # chromium_mediator_tests.json overwrites brotab_mediator.json, but must
        # not turn into a bruvtab_mediator host allowing the test extension.
        self.install(browser='chromium', tests=True)
        chromium = self.read(CHROMIUM_DIR, 'bruvtab_mediator.json')
        self.assertEqual(sorted(chromium['allowed_origins']), [
            'chrome-extension://bkifkhiemhgpnomgdcbcbkifekkecnhk/',
            'chrome-extension://edpgjheobdplebiikjgjgpmonakingef/',
        ])

    def test_replacing_other_bruvtab_host_is_reported(self):
        # A bruvtab install's own host gets repointed at brotab's mediator;
        # say so rather than doing it silently.
        os.makedirs(os.path.join(self.home, FIREFOX_DIR))
        with open(os.path.join(self.home, FIREFOX_DIR, 'bruvtab_mediator.json'), 'w') as f:
            json.dump({'name': 'bruvtab_mediator', 'path': '/usr/bin/bruvtab_mediator'}, f)
        with patch('brotab.main.print_info') as print_info:
            self.install(browser='firefox')
        messages = ' '.join(str(c.args[0]) for c in print_info.call_args_list)
        self.assertIn('/usr/bin/bruvtab_mediator', messages)
        self.assertEqual(self.read(FIREFOX_DIR, 'bruvtab_mediator.json')['path'],
                         '/opt/bin/brotab_mediator')
