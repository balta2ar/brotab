from unittest import TestCase
from unittest.mock import patch
from threading import Thread

from brotab.main import run_commands
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


class TestActivate(TestCase):
    def setUp(self):
        self.mediator = MockedMediator('a')

    def tearDown(self):
        self.mediator.shutdown_and_wait()

    def _run_commands(self, commands):
        with patch('brotab.main.get_mediator_ports') as mocked:
            mocked.side_effect = [range(self.mediator.port, self.mediator.port + 1)]
            return run_commands(commands)

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
