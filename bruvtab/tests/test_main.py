from argparse import Namespace
from io import StringIO
from string import ascii_letters
from time import sleep
from typing import List
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from rich.console import Console
from rich.json import JSON

from bruvtab.api import SingleMediatorAPI
from bruvtab.env import http_iface
from bruvtab.env import min_http_port
from bruvtab.files import in_temp_dir
from bruvtab.files import spit
from bruvtab.inout import get_available_tcp_port
from bruvtab.main import create_clients
from bruvtab.main import build_parser
from bruvtab.main import complete_clients
from bruvtab.main import complete_client_or_window
from bruvtab.main import complete_open_args
from bruvtab.main import complete_playing_tab_ids
from bruvtab.main import complete_tab_ids
from bruvtab.main import completion_validator
from bruvtab.main import parse_args
from bruvtab.main import print_json
from bruvtab.main import run_commands
from bruvtab.mediator.http_server import MediatorHttpServer
from bruvtab.mediator.remote_api import default_remote_api
from bruvtab.mediator.transport import Transport
from bruvtab.tests.utils import assert_file_absent
from bruvtab.tests.utils import assert_file_contents
from bruvtab.tests.utils import assert_file_not_empty
from bruvtab.tests.utils import assert_sqlite3_table_contents
from bruvtab.utils import encode_query


AUDIBLE_QUERY = encode_query('{"audible": true}')
MUTED_QUERY = encode_query('{"muted": true}')


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
        self.transport = MockedLoggingTransport()
        self.remote_api = default_remote_api(self.transport) if remote_api is None else remote_api
        self.port = get_available_tcp_port() if port is None else port
        for _attempt in range(10):
            try:
                self.server = MediatorHttpServer(http_iface(), self.port, self.remote_api, 0.050)
                break
            except OSError:
                self.port = get_available_tcp_port(start=self.port + 1)
        else:
            raise RuntimeError('Could not allocate a port for MockedMediator')
        self.thread = self.server.run.in_thread()
        self.transport.received_extend(['mocked'])
        self.api = SingleMediatorAPI(prefix, port=self.port, startup_timeout=1)
        expected_browser = getattr(remote_api, 'browser', 'mocked')
        assert self.api.browser == expected_browser
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
    def __init__(self, browser='mocked'):
        self.browser = browser

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

    def media_control(self, window_id: int, tab_id: int, action: str):
        return ['%s.%s\t%s\t0\t0' % (window_id, tab_id, action)]

    def get_words(self, tab_id, match_regex, join_with):
        return ['a', 'b']

    def get_text(self, delimiter_regex, replace_with, tab_id=None):
        return ['1.1\ttitle\turl\tbody']

    def get_html(self, delimiter_regex, replace_with, tab_id=None):
        return ['1.1\ttitle\turl\t<body>some body</body>']

    def get_screenshot(self, tab_id=None):
        return {'tab': 1, 'window': 1, 'data': 'data:image/png;base64,'}

    def get_browser(self):
        return self.browser


def run_mocked_mediators(count, default_port_offset, delay):
    """
    How to run:

    python -c 'from bruvtab.tests.test_main import run_mocked_mediators as run; run(3, 0, 0)'
    python -c 'from bruvtab.tests.test_main import run_mocked_mediators as run; run(count=3, default_port_offset=10, delay=0)'
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

    python -c 'from bruvtab.tests.test_main import run_mocked_mediator_current_thread as run; run(4635)'
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
        with patch('bruvtab.main.get_mediator_ports') as mocked:
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
        with patch('bruvtab.main.get_mediator_ports') as mocked:
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

    def test_custom_target_hosts_can_be_filtered_by_prefix(self):
        clients = create_clients(
            '127.0.0.1:%d,localhost:%d' % (self.mediator.port, self.mediator.port),
            'b',
        )
        assert 1 == len(clients)
        assert clients[0]._prefix == 'b.'

    def test_custom_target_hosts_can_be_filtered_by_browser(self):
        other = MockedMediator('b', remote_api=DummyBrowserRemoteAPI('chrome/chromium'))
        self.addCleanup(other.join)
        clients = create_clients(
            '127.0.0.1:%d,localhost:%d' % (self.mediator.port, other.port),
            'chromium',
        )
        assert 1 == len(clients)
        assert clients[0]._prefix == 'b.'


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

    def test_activate_playing_ok(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.2\tPlaying\thttps://example.com'],
        ])

        self._run_commands(['activate', '--playing'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'query_tabs', 'query_info': AUDIBLE_QUERY},
            {'name': 'activate_tab', 'tab_id': 2, 'focused': False},
        ]

    def test_activate_playing_reports_no_match(self):
        self.mediator.transport.received_extend([
            'mocked',
            [],
        ])

        with patch('bruvtab.main.print_error') as print_error:
            result = self._run_commands(['activate', '--playing'])

        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'query_tabs', 'query_info': AUDIBLE_QUERY},
        ]
        print_error.assert_called_once_with('No currently playing tabs found')
        assert result == 1


class TestQueryUpdate(WithMediator):
    def test_query_sends_only_query_keys(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.2\tTicket\thttps://ticket.example.com/'],
        ])

        with patch('sys.stdout', new_callable=StringIO) as stdout:
            self._run_commands(['--no-wrap', 'query', '--debug', '-url', 'https://ticket.example.com/*', '+pinned'])

        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'query_tabs',
             'query_info': encode_query('{"pinned": true, "url": ["https://ticket.example.com/*"]}')},
        ]
        assert stdout.getvalue() == 'a.1.2\tTicket\thttps://ticket.example.com/\n'

    def test_update_sends_only_update_keys(self):
        self.mediator.transport.received_extend([
            'mocked',
            [],
        ])

        with patch('bruvtab.main.read_stdin', return_value=''), \
                patch('bruvtab.main.stdout_buffer_write'):
            self._run_commands(['--no-wrap', 'update', '--debug', '-tabId', 'a.1.2', '+pinned'])

        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'update_tabs', 'updates': [{'tab_id': 2, 'properties': {'pinned': True}}]},
        ]


class TestMediaControls(WithMediator):
    def test_pause_targets_explicit_tab(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.2\tpause\t1\t1'],
        ])

        output = []
        with patch('bruvtab.main.stdout_buffer_write', output.append):
            with patch('bruvtab.main.print_warning') as print_warning:
                self._run_commands(['pause', 'a.1.2'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'media_control', 'window_id': 1, 'tab_id': 2, 'action': 'pause'},
        ]
        print_warning.assert_called_once_with('Pausing media in a.1.2 (mocked)')
        assert output == [b'a.1.2\tpause\t1\t1\n']

    def test_pause_reports_media_control_error(self):
        self.mediator.transport.received_extend([
            'mocked',
            {'error': 'Unknown command: media_control'},
        ])

        output = []
        with patch('bruvtab.main.stdout_buffer_write', output.append):
            with patch('bruvtab.main.print_error') as print_error:
                result = self._run_commands(['pause', 'a.1.2'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'media_control', 'window_id': 1, 'tab_id': 2, 'action': 'pause'},
        ]
        print_error.assert_called_once_with('Could not pause media in a.1.2; rerun with --debug for details')
        assert output == []
        assert result == 1

    def test_pause_debug_reports_raw_media_control_error(self):
        self.mediator.transport.received_extend([
            'mocked',
            {'error': 'Unknown command: media_control'},
        ])

        with patch('bruvtab.main.print_error') as print_error:
            with patch('bruvtab.main.print_warning') as print_warning:
                result = self._run_commands(['pause', 'a.1.2', '--debug'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'media_control', 'window_id': 1, 'tab_id': 2, 'action': 'pause'},
        ]
        print_warning.assert_any_call('Pausing media in a.1.2 (mocked)')
        assert any(call.args[0].startswith('Clients: a.') for call in print_warning.call_args_list)
        print_error.assert_called_once_with('a.1.2: Unknown command: media_control')
        assert result == 1

    def test_play_defaults_to_active_tabs(self):
        self.mediator.transport.received_extend([
            'mocked',
            '1.2',
            ['1.2\tplay\t1\t1'],
        ])

        output = []
        with patch('bruvtab.main.stdout_buffer_write', output.append):
            with patch('bruvtab.main.print_warning') as print_warning:
                self._run_commands(['play'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'get_active_tabs'},
            {'name': 'media_control', 'window_id': 1, 'tab_id': 2, 'action': 'play'},
        ]
        print_warning.assert_called_once_with('Playing media in a.1.2 (mocked)')
        assert output == [b'a.1.2\tplay\t1\t1\n']

    def test_mute_defaults_to_playing_tab(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.2\tPlaying\thttps://example.com'],
            ['1.2'],
        ])

        output = []
        with patch('bruvtab.main.stdout_buffer_write', output.append):
            with patch('bruvtab.main.print_warning') as print_warning:
                self._run_commands(['mute'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'query_tabs', 'query_info': AUDIBLE_QUERY},
            {'name': 'update_tabs', 'updates': [{'tab_id': 2, 'properties': {'muted': True}}]},
        ]
        print_warning.assert_called_once_with('Muting a.1.2 (mocked)')
        assert output == [b'a.1.2\n']

    def test_unmute_targets_explicit_tab(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.2'],
        ])

        output = []
        with patch('bruvtab.main.stdout_buffer_write', output.append):
            with patch('bruvtab.main.print_warning') as print_warning:
                self._run_commands(['unmute', 'a.1.2'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'update_tabs', 'updates': [{'tab_id': 2, 'properties': {'muted': False}}]},
        ]
        print_warning.assert_called_once_with('Unmuting a.1.2 (mocked)')
        assert output == [b'a.1.2\n']

    def test_unmute_debug_reports_client_and_result(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.2'],
        ])

        output = []
        with patch('bruvtab.main.stdout_buffer_write', output.append):
            with patch('bruvtab.main.print_warning') as print_warning:
                self._run_commands(['unmute', 'a.1.2', '--debug'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'update_tabs', 'updates': [{'tab_id': 2, 'properties': {'muted': False}}]},
        ]
        print_warning.assert_any_call('Unmuting a.1.2 (mocked)')
        print_warning.assert_any_call('Result: a.1.2')
        assert any(call.args[0].startswith('Clients: a.') for call in print_warning.call_args_list)
        assert output == [b'a.1.2\n']


class TestText(WithMediator):
    def test_text_no_arguments_ok(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.1\ttitle\turl\tbody'],
        ])

        output = []
        with patch('bruvtab.main.stdout_buffer_write', output.append):
            self._run_commands(['text'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'delimiter_regex': '/\\n|\\r|\\t/g', 'name': 'get_text', 'replace_with': '" "'},
        ]
        assert output == [b'a.1.1\ttitle\turl\tbody\n']

    def test_text_with_tab_id_ok(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.2\ttitle\turl\tbody'],
        ])

        output = []
        with patch('bruvtab.main.stdout_buffer_write', output.append):
            self._run_commands(['text', 'a.1.2'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {
                'delimiter_regex': '/\\n|\\r|\\t/g',
                'name': 'get_text',
                'replace_with': '" "',
                'tab_id': 2,
            },
        ]
        assert output == [b'a.1.2\ttitle\turl\tbody\n']

    def test_text_with_multiple_tab_ids_ok(self):
        self.mediator.transport.received_extend([
            'mocked',
            [
                '1.1\ttitle\turl\tbody',
                '1.2\ttitle\turl\tbody',
                '1.3\ttitle\turl\tbody',
            ],
        ])

        output = []
        with patch('bruvtab.main.stdout_buffer_write', output.append):
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
        with patch('bruvtab.main.stdout_buffer_write', output.append):
            self._run_commands(['html'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'delimiter_regex': '/\\n|\\r|\\t/g', 'name': 'get_html', 'replace_with': '" "'},
        ]
        assert output == [b'a.1.1\ttitle\turl\tbody\n']

    def test_html_with_tab_id_ok(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.2\ttitle\turl\tbody'],
        ])

        output = []
        with patch('bruvtab.main.stdout_buffer_write', output.append):
            self._run_commands(['html', 'a.1.2'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {
                'delimiter_regex': '/\\n|\\r|\\t/g',
                'name': 'get_html',
                'replace_with': '" "',
                'tab_id': 2,
            },
        ]
        assert output == [b'a.1.2\ttitle\turl\tbody\n']

    def test_html_with_multiple_tab_ids_ok(self):
        self.mediator.transport.received_extend([
            'mocked',
            [
                '1.1\ttitle\turl\tbody',
                '1.2\ttitle\turl\tbody',
                '1.3\ttitle\turl\tbody',
            ],
        ])

        output = []
        with patch('bruvtab.main.stdout_buffer_write', output.append):
            self._run_commands(['html', 'a.1.2', 'a.1.3'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'delimiter_regex': '/\\n|\\r|\\t/g', 'name': 'get_html', 'replace_with': '" "'},
        ]
        assert output == [b'a.1.2\ttitle\turl\tbody\na.1.3\ttitle\turl\tbody\n']

    def test_html_with_url_match_targets_first_match(self):
        self.mediator.transport.received_extend([
            'mocked',
            [
                '1.2\tGoogle Search\thttps://google.com/search',
                '1.3\tOther\thttps://example.com',
            ],
            ['1.2\tGoogle Search\thttps://google.com/search\t<body>google</body>'],
        ])

        output = []
        with patch('bruvtab.main.stdout_buffer_write', output.append):
            self._run_commands(['html', 'google.com'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'list_tabs'},
            {
                'delimiter_regex': '/\\n|\\r|\\t/g',
                'name': 'get_html',
                'replace_with': '" "',
                'tab_id': 2,
            },
        ]
        assert output == [b'a.1.2\tGoogle Search\thttps://google.com/search\t<body>google</body>\n']


class TestWords(WithMediator):
    def test_words_with_tab_id_ok(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['word-a', 'word-b'],
        ])

        with patch('builtins.print') as mocked:
            self._run_commands(['words', 'a.1.2'])

        self._assert_init()
        assert self.mediator.transport.sent == [
            {
                'join_with': '"\\n"',
                'match_regex': '/\\w+/g',
                'name': 'get_words',
                'tab_id': 2,
            },
        ]
        mocked.assert_called_once_with('word-a\nword-b')


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
        with patch('bruvtab.main.stdout_buffer_write', output.append):
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
        with patch('bruvtab.main.stdout_buffer_write', output.append):
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
    def test_one_url_without_client_ok(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.1'],
        ])

        output = []
        with patch('bruvtab.main.stdout_buffer_write', output.append):
            self._run_commands(['open', 'url1'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'open_urls', 'urls': ['url1']},
        ]
        assert output == [b'a.1.1\n']

    def test_one_url_with_client_ok(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.1'],
        ])

        output = []
        with patch('bruvtab.main.stdout_buffer_write', output.append):
            self._run_commands(['open', 'a.', 'url1'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'open_urls', 'urls': ['url1']},
        ]
        assert output == [b'a.1.1\n']

    def test_one_url_with_global_client_ok(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.1'],
        ])

        output = []
        with patch('bruvtab.main.stdout_buffer_write', output.append):
            self._run_commands(['open', '--browser', 'a', 'url1'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'open_urls', 'urls': ['url1']},
        ]
        assert output == [b'a.1.1\n']

    def test_three_urls_ok(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.1', '1.2', '1.3'],
        ])

        urls = ['url1', 'url2', 'url3']
        output = []
        with patch('bruvtab.main.stdout_buffer_write', output.append):
            with patch('bruvtab.main.read_stdin_lines', return_value=urls):
                self._run_commands(['open', 'a.1'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'open_urls', 'urls': ['url1', 'url2', 'url3'], 'window_id': 1},
        ]
        assert output == [b'a.1.1\na.1.2\na.1.3\n']


class TestList(WithMediator):
    def test_tabs_alias_ok(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.1\ttitle\turl'],
        ])

        output = []
        with patch('bruvtab.main.sys.stdout.buffer.write', output.append):
            self._run_commands(['tabs'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'list_tabs'},
        ]
        assert output[-1:] == [b'a.1.1\ttitle\turl\n']

    def test_tabs_filters_by_title_or_url(self):
        self.mediator.transport.received_extend([
            'mocked',
            [
                '1.1\tGoogle Search\thttps://google.com/search',
                '1.2\tExample\thttps://example.com',
                '1.3\tMail\thttps://mail.google.com',
            ],
        ])

        output = []
        with patch('bruvtab.main.sys.stdout.buffer.write', output.append):
            self._run_commands(['tabs', 'google.com'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'list_tabs'},
        ]
        assert output[-1:] == [
            b'a.1.1\tGoogle Search\thttps://google.com/search\n'
            b'a.1.3\tMail\thttps://mail.google.com\n'
        ]

    def test_tabs_json_filters_by_title_or_url(self):
        self.mediator.transport.received_extend([
            'mocked',
            [
                '1.1\tGoogle Search\thttps://google.com/search',
                '1.2\tExample\thttps://example.com',
            ],
            ['1.1\tGoogle Search\thttps://google.com/search'],
            ['1.1\tGoogle Search\thttps://google.com/search'],
        ])

        with patch('bruvtab.main.stdout_supports_rich', return_value=False):
            with patch('builtins.print') as mocked:
                self._run_commands(['tabs', 'google', '--json'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'list_tabs'},
            {'name': 'query_tabs', 'query_info': AUDIBLE_QUERY},
            {'name': 'query_tabs', 'query_info': MUTED_QUERY},
        ]
        mocked.assert_called_once_with(
            '[\n'
            '  {\n'
            '    "id": "a.1.1",\n'
            '    "title": "Google Search",\n'
            '    "url": "https://google.com/search",\n'
            '    "playing": true,\n'
            '    "muted": true\n'
            '  }\n'
            ']'
        )

    def test_tabs_playing_filters_plain_tsv(self):
        self.mediator.transport.received_extend([
            'mocked',
            [
                '1.1\tGoogle Search\thttps://google.com/search',
                '1.2\tExample\thttps://example.com',
            ],
            ['1.2\tExample\thttps://example.com'],
            [],
        ])

        output = []
        with patch('bruvtab.main.sys.stdout.buffer.write', output.append):
            self._run_commands(['tabs', '--playing'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'list_tabs'},
            {'name': 'query_tabs', 'query_info': AUDIBLE_QUERY},
            {'name': 'query_tabs', 'query_info': MUTED_QUERY},
        ]
        assert output[-1:] == [b'a.1.2\tExample\thttps://example.com\n']

    def test_tabs_muted_filters_plain_tsv(self):
        self.mediator.transport.received_extend([
            'mocked',
            [
                '1.1\tGoogle Search\thttps://google.com/search',
                '1.2\tExample\thttps://example.com',
            ],
            [],
            ['1.1\tGoogle Search\thttps://google.com/search'],
        ])

        output = []
        with patch('bruvtab.main.sys.stdout.buffer.write', output.append):
            self._run_commands(['tabs', '--muted'])
        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'list_tabs'},
            {'name': 'query_tabs', 'query_info': AUDIBLE_QUERY},
            {'name': 'query_tabs', 'query_info': MUTED_QUERY},
        ]
        assert output[-1:] == [b'a.1.1\tGoogle Search\thttps://google.com/search\n']


class TestScreenshot(WithMediator):
    def test_raw_outputs_image_bytes(self):
        self.mediator.transport.received_extend([
            'mocked',
            {'tab': 1, 'window': 1, 'data': 'data:image/png;base64,cG5n'},
        ])

        output = []
        with patch('bruvtab.main.sys.stdout.buffer.write', output.append):
            result = self._run_commands(['screenshot', '--raw'])

        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'get_screenshot'},
        ]
        assert result == 0
        assert output[-1:] == [b'png']

    def test_tab_id_targets_specific_tab(self):
        self.mediator.transport.received_extend([
            'mocked',
            {'tab': 2, 'window': 1, 'data': 'data:image/png;base64,cG5n'},
        ])

        output = []
        with patch('bruvtab.main.sys.stdout.buffer.write', output.append):
            result = self._run_commands(['screenshot', 'a.1.2', '--raw'])

        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'get_screenshot', 'tab_id': 2},
        ]
        assert result == 0
        assert output[-1:] == [b'png']

    def test_selector_targets_first_matching_tab_and_warns_on_multiple_matches(self):
        self.mediator.transport.received_extend([
            'mocked',
            [
                '1.2\tGoogle Search\thttps://google.com/search',
                '1.3\tGoogle Mail\thttps://mail.google.com',
            ],
            {'tab': 2, 'window': 1, 'data': 'data:image/png;base64,cG5n'},
        ])

        output = []
        with patch('bruvtab.main.sys.stdout.buffer.write', output.append):
            with patch('bruvtab.main.print_error') as print_error:
                result = self._run_commands(['screenshot', 'google', '--raw'])

        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'list_tabs'},
            {'name': 'get_screenshot', 'tab_id': 2},
        ]
        print_error.assert_called_once_with('Multiple tabs match "google"; using a.1.2')
        assert result == 0
        assert output[-1:] == [b'png']


class TestJsonOutput(TestCase):
    def test_print_json_plain_pretty(self):
        with patch('bruvtab.main.stdout_supports_rich', return_value=False):
            with patch('builtins.print') as mocked:
                print_json([{'id': 'a.1.1'}])

        mocked.assert_called_once_with('[\n  {\n    "id": "a.1.1"\n  }\n]')

    def test_print_json_rich_pretty(self):
        with patch('bruvtab.main.stdout_supports_rich', return_value=True):
            with patch('bruvtab.main.stdout_console.print') as mocked:
                print_json([{'id': 'a.1.1'}])

        renderable = mocked.call_args.args[0]
        assert isinstance(renderable, JSON)
        assert renderable.text.plain == '[\n  {\n    "id": "a.1.1"\n  }\n]'

    def test_parse_args_accepts_json_after_subcommand(self):
        args = parse_args(['tabs', '--json'])

        assert args.json is True

    def test_parse_args_accepts_json_shorthand_after_subcommand(self):
        args = parse_args(['tabs', '-j'])

        assert args.json is True

    def test_parse_args_accepts_json_shorthand_before_subcommand(self):
        args = parse_args(['-j', 'tabs'])

        assert args.json is True

    def test_parse_args_accepts_debug_after_subcommand(self):
        args = parse_args(['tabs', '--debug'])

        assert args.debug is True

    def test_parse_args_accepts_target_after_subcommand(self):
        args = parse_args(['tabs', '--target', '127.0.0.1:4625'])

        assert args.target_hosts == '127.0.0.1:4625'

    def test_parse_args_accepts_browser_after_subcommand(self):
        args = parse_args(['tabs', '--browser', 'a'])

        assert args.client_selector == 'a'

    def test_parse_args_accepts_firefox_after_subcommand(self):
        args = parse_args(['open', '--firefox', 'url1'])

        assert args.client_selector == 'firefox'
        assert args.open_args == ['url1']

    def test_parse_args_accepts_raw_screenshot(self):
        args = parse_args(['screenshot', '--raw'])

        assert args.raw is True

    def test_parse_args_accepts_screenshot_tab_id(self):
        args = parse_args(['screenshot', 'a.1.2'])

        assert args.tab == 'a.1.2'

    def test_completion_validator_accepts_compact_tab_prefixes(self):
        assert completion_validator('a.1.2', 'a1.')
        assert not completion_validator('b.1.2', 'a1.')

    @patch('bruvtab.main._list_tabs_for_completion')
    def test_complete_tab_ids_matches_compact_prefixes(self, mocked_tabs):
        mocked_tabs.return_value = [
            'a.1.2\tAlpha One\thttps://example.com/a1',
            'a.1.3\tAlpha Two\thttps://example.com/a2',
            'b.2.1\tBeta\thttps://example.com/b1',
        ]

        matches = complete_tab_ids('a1.', Namespace(target_hosts=None, client_selector=None))

        assert matches == {
            'a.1.2': 'Alpha One | https://example.com/a1',
            'a.1.3': 'Alpha Two | https://example.com/a2',
        }

    @patch('bruvtab.main._query_tabs_for_completion')
    def test_complete_playing_tab_ids_uses_audible_query(self, mocked_tabs):
        mocked_tabs.return_value = [
            'a.1.2\tPlaying One\thttps://example.com/a1',
            'b.2.1\tPlaying Two\thttps://example.com/b1',
        ]

        matches = complete_playing_tab_ids('a', Namespace(target_hosts=None, client_selector=None))

        mocked_tabs.assert_called_once_with(Namespace(target_hosts=None, client_selector=None), {'audible': True})
        assert matches == {
            'a.1.2': 'Playing One | https://example.com/a1',
        }

    @patch('bruvtab.main.complete_clients')
    @patch('bruvtab.main.complete_windows')
    def test_complete_open_args_only_suggests_targets_for_first_argument(self, mocked_windows, mocked_clients):
        mocked_windows.return_value = {'a.1': '2 tabs'}
        mocked_clients.return_value = {'a': 'firefox | localhost:4625'}

        first_arg_matches = complete_open_args('', Namespace(open_args=[]))
        second_arg_matches = complete_open_args('https', Namespace(open_args=['a.1']))

        assert first_arg_matches == {
            'a.1': '2 tabs',
            'a': 'firefox | localhost:4625',
        }
        assert second_arg_matches == {}

    def test_parser_attaches_dynamic_completers(self):
        parser = build_parser()
        subparsers = next(action for action in parser._actions if getattr(action, 'choices', None))

        assert next(action for action in parser._actions if action.dest == 'client_selector').completer == complete_clients
        assert next(action for action in subparsers.choices['close']._actions if action.dest == 'tab_ids').completer == complete_tab_ids
        assert next(action for action in subparsers.choices['pause']._actions if action.dest == 'tab').completer == complete_playing_tab_ids
        assert next(action for action in subparsers.choices['mute']._actions if action.dest == 'tab').completer == complete_playing_tab_ids
        assert next(action for action in subparsers.choices['new']._actions if action.dest == 'prefix_window_id').completer == complete_client_or_window

    def test_parser_exposes_global_options_on_subcommands_for_completion(self):
        parser = build_parser()
        subparsers = next(action for action in parser._actions if getattr(action, 'choices', None))
        list_parser = subparsers.choices['list']

        option_strings = {
            option
            for action in list_parser._actions
            for option in action.option_strings
        }

        assert '--json' in option_strings
        assert '-j' in option_strings
        assert '--firefox' in option_strings
        assert '--chrome' in option_strings
        assert next(action for action in list_parser._actions if action.dest == 'client_selector').completer == complete_clients


class TestRichTableOutput(WithMediator):
    def _render_output(self, commands):
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=False, color_system=None, width=120)
        with patch('bruvtab.main.stdout_supports_rich', return_value=True):
            with patch('bruvtab.main.stdout_console', console):
                self._run_commands(commands)
        return buffer.getvalue()

    def test_tabs_are_rendered_as_ascii_table(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.1\ttitle\turl'],
            ['1.1\ttitle\turl'],
            ['1.1\ttitle\turl'],
        ])

        output = self._render_output(['tabs'])

        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'list_tabs'},
            {'name': 'query_tabs', 'query_info': AUDIBLE_QUERY},
            {'name': 'query_tabs', 'query_info': MUTED_QUERY},
        ]
        assert 'ID' in output.splitlines()[0]
        assert 'PLAYING' in output.splitlines()[0]
        assert 'MUTED' in output.splitlines()[0]
        assert 'TITLE' in output.splitlines()[0]
        assert 'URL' in output.splitlines()[0]
        assert 'a.1.1' in output
        assert 'TRUE' in output
        assert 'title' in output
        assert 'url' in output

    def test_tabs_render_false_status_in_table(self):
        self.mediator.transport.received_extend([
            'mocked',
            ['1.1\ttitle\turl'],
            [],
            [],
        ])

        output = self._render_output(['tabs'])

        self._assert_init()
        assert self.mediator.transport.sent == [
            {'name': 'list_tabs'},
            {'name': 'query_tabs', 'query_info': AUDIBLE_QUERY},
            {'name': 'query_tabs', 'query_info': MUTED_QUERY},
        ]
        assert 'false' in output

    def test_clients_rich_output_has_no_title(self):
        self.mediator.transport.received_extend(['mocked'])

        output = self._render_output(['clients'])

        assert 'Clients\n' not in output
        assert 'PREFIX' in output.splitlines()[0]
        assert 'BROWSER' in output.splitlines()[0]
        assert 'a.' in output
