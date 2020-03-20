from uuid import uuid4
from time import sleep
from threading import Thread
from string import ascii_letters
from unittest import TestCase
from unittest.mock import patch
from typing import List

from brotab.main import run_commands
from brotab.main import create_clients
from brotab.inout import get_free_tcp_port
from brotab.inout import in_temp_dir
from brotab.inout import spit
from brotab.inout import MIN_MEDIATOR_PORT
from brotab.api import SingleMediatorAPI
from brotab.mediator.brotab_mediator import run_mediator
from brotab.mediator.brotab_mediator import create_browser_remote_api

from brotab.tests.utils import assert_file_absent
from brotab.tests.utils import assert_file_not_empty
from brotab.tests.utils import assert_file_contents
from brotab.tests.utils import assert_sqlite3_table_contents


class MockedLoggingTransport:
    def __init__(self):
        self.reset()
    def reset(self):
        self.sent = []
        self.received = []
    def send(self, message):
        self.sent.append(message)
    def recv(self):
        if self.received:
            result = self.received[0]
            self.received = self.received[1:]
            return result


def _run_mediator_in_thread(port, transport, remote_api=None) -> Thread:
    remote_api = create_browser_remote_api(transport) if remote_api is None else remote_api
    thread = Thread(target=lambda: run_mediator(port, remote_api, no_logging=True))
    thread.daemon = True
    thread.start()
    return thread


class MockedMediator:
    def __init__(self, prefix='a', port=None, remote_api=None):
        self.port = get_free_tcp_port() if port is None else port
        self.transport = MockedLoggingTransport()
        self.transport.received = ['mocked']
        self.thread = _run_mediator_in_thread(self.port, self.transport, remote_api)
        self.api = SingleMediatorAPI(prefix, port=self.port, startup_timeout=1)
        assert self.api._browser == 'mocked'
        self.transport.reset()
    def shutdown_and_wait(self):
        self.api.shutdown()
        self.thread.join()
    def __enter__(self):
        return self
    def __exit__(self, type_, value, tb):
        self.shutdown_and_wait()


def _run_commands(commands):
    with MockedMediator('a') as mediator:
        get_mediator_ports_mock.side_effect = \
            [range(mediator.port, mediator.port + 1)]
        run_commands(commands)


class DummyBrowserRemoteAPI:
    """
    Dummy version of browser API for integration smoke tests.
    """

    def list_tabs(self):
        return ['1.1\ttitle\turl']
    def query_tabs(self, query_info: str):
        raise NotImplementedError()
    def move_tabs(self, move_triplets: str):
        raise NotImplementedError()
    def open_urls(self, urls: List[str], window_id=None):
        raise NotImplementedError()
    def close_tabs(self, tab_ids: str):
        raise NotImplementedError()
    def new_tab(self, query):
        raise NotImplementedError()
    def activate_tab(self, tab_id: int, focused: bool):
        raise NotImplementedError()
    def get_active_tabs(self) -> str:
        return '1.1'
    def get_words(self, tab_id, match_regex, join_with):
        return ['a', 'b']
    def get_text(self, delimiter_regex, replace_with):
        return ['1.1\ttitle\turl\tbody']
    def get_browser(self):
        return 'mocked'


def run_mocked_mediators(count, default_port_offset, delay):
    """
    How to run:

    python -c 'from brotab.tests.test_main import run_mocked_mediators as run; run(3, 0, 0)'
    python -c 'from brotab.tests.test_main import run_mocked_mediators as run; run(count=3, default_port_offset=10, delay=0)'
    """
    assert count > 0
    print('Creating %d mediators' % count)
    start_port = MIN_MEDIATOR_PORT + default_port_offset
    ports = range(start_port, start_port + count)
    mediators = [MockedMediator(letter, port, DummyBrowserRemoteAPI())
                 for i, letter, port in zip(range(count), ascii_letters, ports)]
    sleep(delay)
    print('Ready')
    for mediator in mediators:
        print(mediator.port)
    mediators[0].thread.join()


def run_mocked_mediator_current_thread(port):
    """
    How to run:

    python -c 'from brotab.tests.test_main import run_mocked_mediator_current_thread as run; run(4635)'
    """
    remote_api = DummyBrowserRemoteAPI()
    port = get_free_tcp_port() if port is None else port
    run_mediator(port, remote_api, no_logging=False)


class WithMediator(TestCase):
    def setUp(self):
        self.mediator = MockedMediator('a')

    def tearDown(self):
        self.mediator.shutdown_and_wait()

    def _run_commands(self, commands):
        with patch('brotab.main.get_mediator_ports') as mocked:
            mocked.side_effect = [range(self.mediator.port, self.mediator.port + 1)]
            return run_commands(commands)


class TestCreateClients(WithMediator):
    def test_default_target_hosts(self):
        with patch('brotab.main.get_mediator_ports') as mocked:
            mocked.side_effect = [range(self.mediator.port, self.mediator.port + 1)]
            clients = create_clients()
        assert 1 == len(clients)
        assert self.mediator.port == clients[0]._port

    def test_one_custom_target_hosts(self):
        clients = create_clients('127.0.0.1:%d' % self.mediator.port)
        assert 1 == len(clients)
        assert self.mediator.port == clients[0]._port

    def test_two_custom_target_hosts(self):
        clients = create_clients('127.0.0.1:%d,localhost:%d' %
                                 (self.mediator.port, self.mediator.port))
        assert 2 == len(clients)
        assert self.mediator.port == clients[0]._port
        assert self.mediator.port == clients[1]._port


class TestActivate(WithMediator):
    def test_activate_ok(self):
        self._run_commands(['activate', 'a.1.2'])
        assert self.mediator.transport.sent == [
            {'name': 'get_browser'},
            {'name': 'activate_tab', 'tab_id': 2, 'focused': False}
        ]

    def test_activate_focused_ok(self):
        self._run_commands(['activate', '--focused', 'a.1.2'])
        assert self.mediator.transport.sent == [
            {'name': 'get_browser'},
            {'name': 'activate_tab', 'tab_id': 2, 'focused': True}
        ]


class TestText(WithMediator):
    def test_text_no_arguments_ok(self):
        self.mediator.transport.received.extend([
            'mocked',
            ['1.1\ttitle\turl\tbody'],
        ])

        output = []
        with patch('brotab.main.stdout_buffer_write', output.append):
            self._run_commands(['text'])
        assert self.mediator.transport.sent == [
            {'name': 'get_browser'},
            {'delimiter_regex': '/\\n|\\r|\\t/g', 'name': 'get_text', 'replace_with': '" "'},
        ]
        assert output == [b'a.1.1\ttitle\turl\tbody\n']

    def test_text_with_tab_id_ok(self):
        self.mediator.transport.received.extend([
            'mocked',
            [
                '1.1\ttitle\turl\tbody',
                '1.2\ttitle\turl\tbody',
                '1.3\ttitle\turl\tbody',
            ],
        ])

        output = []
        with patch('brotab.main.stdout_buffer_write', output.append):
            self._run_commands(['text', 'a.1.2', 'a.1.3'])
        assert self.mediator.transport.sent == [
            {'name': 'get_browser'},
            {'delimiter_regex': '/\\n|\\r|\\t/g', 'name': 'get_text', 'replace_with': '" "'},
        ]
        assert output == [b'a.1.2\ttitle\turl\tbody\na.1.3\ttitle\turl\tbody\n']


class TestIndex(WithMediator):
    def test_index_no_arguments_ok(self):
        self.mediator.transport.received.extend([
            'mocked',
            ['1.1\ttitle\turl\tbody'],
        ])

        sqlite_filename = in_temp_dir('tabs.sqlite')
        tsv_filename = in_temp_dir('tabs.tsv')
        assert_file_absent(sqlite_filename)
        assert_file_absent(tsv_filename)
        output = []
        with patch('brotab.main.stdout_buffer_write', output.append):
            self._run_commands(['index'])
        assert self.mediator.transport.sent == [
            {'name': 'get_browser'},
            {'delimiter_regex': '/\\n|\\r|\\t/g',
                'name': 'get_text', 'replace_with': '" "'},
        ]
        assert_file_not_empty(sqlite_filename)
        assert_file_not_empty(tsv_filename)
        assert_file_contents(tsv_filename, 'a.1.1\ttitle\turl\tbody\n')
        assert_sqlite3_table_contents(
            sqlite_filename,  'tabs', 'a.1.1\ttitle\turl\tbody')

    def test_index_custom_filename(self):
        self.mediator.transport.received.extend([
            'mocked',
            ['1.1\ttitle\turl\tbody'],
        ])

        sqlite_filename = in_temp_dir(uuid4().hex + '.sqlite')
        tsv_filename = in_temp_dir(uuid4().hex + '.tsv')
        assert_file_absent(sqlite_filename)
        assert_file_absent(tsv_filename)
        spit(tsv_filename, 'a.1.1\ttitle\turl\tbody\n')

        output = []
        with patch('brotab.main.stdout_buffer_write', output.append):
            self._run_commands(
                ['index', '--sqlite', sqlite_filename, '--tsv', tsv_filename])
        assert self.mediator.transport.sent == []
        assert_file_not_empty(sqlite_filename)
        assert_file_not_empty(tsv_filename)
        assert_file_contents(tsv_filename, 'a.1.1\ttitle\turl\tbody\n')
        assert_sqlite3_table_contents(
            sqlite_filename,  'tabs', 'a.1.1\ttitle\turl\tbody')
        assert_file_absent(sqlite_filename)
        assert_file_absent(tsv_filename)
