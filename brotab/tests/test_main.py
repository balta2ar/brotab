from unittest import TestCase
from unittest.mock import patch
from threading import Thread

from brotab.main import run_commands
from brotab.main import create_clients
from brotab.inout import get_free_tcp_port
from brotab.api import SingleMediatorAPI
from brotab.mediator.brotab_mediator import run_mediator
from brotab.mediator.brotab_mediator import create_browser_remote_api


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


def _run_mediator_in_thread(port, transport) -> Thread:
    remote_api = create_browser_remote_api(transport)
    thread = Thread(target=lambda: run_mediator(port, remote_api, no_logging=True))
    thread.daemon = True
    thread.start()
    return thread


class MockedMediator:
    def __init__(self, prefix='a'):
        self.port = get_free_tcp_port()
        self.transport = MockedLoggingTransport()
        self.transport.received = ['mocked']
        self.thread = _run_mediator_in_thread(self.port, self.transport)
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
