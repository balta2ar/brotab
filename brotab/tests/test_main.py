from string import ascii_letters
from time import sleep
from typing import List
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from brotab.api import SingleMediatorAPI
from brotab.env import http_iface
from brotab.env import min_http_port
from brotab.files import in_temp_dir
from brotab.files import spit
from brotab.inout import get_available_tcp_port
from brotab.main import create_clients
from brotab.main import run_commands
from brotab.mediator.http_server import MediatorHttpServer
from brotab.mediator.remote_api import default_remote_api
from brotab.mediator.transport import Transport
from brotab.tests.utils import assert_file_absent
from brotab.tests.utils import assert_file_contents
from brotab.tests.utils import assert_file_not_empty
from brotab.tests.utils import assert_sqlite3_table_contents


class MockedLoggingTransport(Transport):
    def __init__(self):
        self._sent = []
        self._received = []

    def reset(self):
        self._sent = []
        self._received = []

    @property
    def sent(self):
        return self._sent

    @property
    def received(self):
        return self._received

    def received_extend(self, values) -> None:
        for value in values:
            self._received.append(value)

    def send(self, message) -> None:
        self._sent.append(message)

    def recv(self):
        if self._received:
            return self._received.pop(0)

    def close(self):
        pass


class MockedMediator:
    def __init__(self, prefix='a', port=None, remote_api=None):
        self.port = get_available_tcp_port() if port is None else port
        self.transport = MockedLoggingTransport()
        self.remote_api = default_remote_api(self.transport) if remote_api is None else remote_api
        self.server = MediatorHttpServer(http_iface(), self.port, self.remote_api, 0.050)
        self.thread = self.server.run.in_thread()
        self.transport.received_extend(['mocked'])
        self.api = SingleMediatorAPI(prefix, port=self.port, startup_timeout=1)
        assert self.api.browser == 'mocked'
        self.transport.reset()

    def join(self):
        self.server.shutdown()
        self.thread.join()

    def __enter__(self):
        return self

    def __exit__(self, type_, value, tb):
        self.join()


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

    def get_html(self, delimiter_regex, replace_with):
        return ['1.1\ttitle\turl\t<body>some body</body>']

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
    start_port = min_http_port() + default_port_offset
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
    port = get_available_tcp_port() if port is None else port
    server = MediatorHttpServer(http_iface(), port, remote_api, 0.050)
    server.run.here()


class WithMediator(TestCase):
    def setUp(self):
        self.mediator = MockedMediator('a')

    def tearDown(self):
        self.mediator.join()

    def _run_commands(self, commands):
        with patch('brotab.main.get_mediator_ports') as mocked:
            mocked.side_effect = [range(self.mediator.port, self.mediator.port + 1)]
            return run_commands(commands)

    def _assert_init(self):
        """Pop get_browser commands from the beginning until we have none."""
        expected = {'name': 'get_browser'}
        popped = 0
        while self.mediator.transport.sent:
            if expected != self.mediator.transport.sent[0]:
                break
            self.mediator.transport.sent.pop(0)
            popped += 1
        assert popped > 0, 'Expected to pop at least one get_browser command'


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
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'activate_tab', 'tab_id': 2, 'focused': False}
        ]

    def test_activate_focused_ok(self):
        self._run_commands(['activate', '--focused', 'a.1.2'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'activate_tab', 'tab_id': 2, 'focused': True}
        ]


class TestText(WithMediator):
    def test_text_no_arguments_ok(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.1\ttitle\turl\tbody'],
        ])

        output = []
        with patch('brotab.main.stdout_buffer_write', output.append):
            self._run_commands(['text'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'delimiter_regex': '/\\n|\\r|\\t/g', 'name': 'get_text', 'replace_with': '" "'},
        ]
        assert output == [b'a.1.1\ttitle\turl\tbody\n']

    def test_text_with_tab_id_ok(self):
        self.mediator.transport.received_extend([
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
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'delimiter_regex': '/\\n|\\r|\\t/g', 'name': 'get_text', 'replace_with': '" "'},
        ]
        assert output == [b'a.1.2\ttitle\turl\tbody\na.1.3\ttitle\turl\tbody\n']


class TestHtml(WithMediator):
    def test_html_no_arguments_ok(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.1\ttitle\turl\tbody'],
        ])

        output = []
        with patch('brotab.main.stdout_buffer_write', output.append):
            self._run_commands(['html'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'delimiter_regex': '/\\n|\\r|\\t/g', 'name': 'get_html', 'replace_with': '" "'},
        ]
        assert output == [b'a.1.1\ttitle\turl\tbody\n']

    def test_html_with_tab_id_ok(self):
        self.mediator.transport.received_extend([
            'mocked',
            [
                '1.1\ttitle\turl\tbody',
                '1.2\ttitle\turl\tbody',
                '1.3\ttitle\turl\tbody',
            ],
        ])

        output = []
        with patch('brotab.main.stdout_buffer_write', output.append):
            self._run_commands(['html', 'a.1.2', 'a.1.3'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'delimiter_regex': '/\\n|\\r|\\t/g', 'name': 'get_html', 'replace_with': '" "'},
        ]
        assert output == [b'a.1.2\ttitle\turl\tbody\na.1.3\ttitle\turl\tbody\n']


class TestIndex(WithMediator):
    def test_index_no_arguments_ok(self):
        self.mediator.transport.received_extend([
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
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'delimiter_regex': '/\\n|\\r|\\t/g',
             'name': 'get_text', 'replace_with': '" "'},
        ]
        assert_file_not_empty(sqlite_filename)
        assert_file_not_empty(tsv_filename)
        assert_file_contents(tsv_filename, 'a.1.1\ttitle\turl\tbody\n')
        assert_sqlite3_table_contents(
            sqlite_filename, 'tabs', 'a.1.1\ttitle\turl\tbody')

    def test_index_custom_filename(self):
        self.mediator.transport.received_extend([
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
            sqlite_filename, 'tabs', 'a.1.1\ttitle\turl\tbody')
        assert_file_absent(sqlite_filename)
        assert_file_absent(tsv_filename)


class TestOpen(WithMediator):
    def test_three_urls_ok(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.1', '1.2', '1.3'],
        ])

        urls = ['url1', 'url2', 'url3']
        output = []
        with patch('brotab.main.stdout_buffer_write', output.append):
            with patch('brotab.main.read_stdin_lines', return_value=urls):
                self._run_commands(['open', 'a.1'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'open_urls', 'urls': ['url1', 'url2', 'url3'], 'window_id': 1},
        ]
        assert output == [b'a.1.1\na.1.2\na.1.3\n']
