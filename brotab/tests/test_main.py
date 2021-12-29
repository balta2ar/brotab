import os
import signal
from multiprocessing import Barrier
from multiprocessing import Process
from multiprocessing import Queue
from string import ascii_letters
from time import sleep
from typing import List
from unittest import TestCase
from unittest.mock import patch
from urllib.error import URLError
from uuid import uuid4

from brotab.api import HttpClient
from brotab.api import SingleMediatorAPI
from brotab.inout import MIN_MEDIATOR_PORT
from brotab.inout import get_available_tcp_port
from brotab.inout import in_temp_dir
from brotab.inout import spit
from brotab.main import create_clients
from brotab.main import run_commands
from brotab.mediator import sig
from brotab.mediator.const import DEFAULT_HTTP_IFACE
from brotab.mediator.http_server import MediatorHttpServer
from brotab.mediator.log import mediator_logger
from brotab.mediator.remote_api import default_remote_api
from brotab.mediator.transport import Transport
from brotab.mediator.transport import transport_with_timeout
from brotab.tests.utils import assert_file_absent
from brotab.tests.utils import assert_file_contents
from brotab.tests.utils import assert_file_not_empty
from brotab.tests.utils import assert_sqlite3_table_contents
from brotab.wait import ConditionTrue
from brotab.wait import Waiter


class MockedLoggingTransport(Transport):
    MAX_SIZE = 1000

    def __init__(self):
        self._sent = Queue(self.MAX_SIZE)
        self._received = Queue(self.MAX_SIZE)

    def reset(self):
        self._read_queue(self._sent)
        self._read_queue(self._received)

    def _read_queue(self, queue: Queue) -> list:
        result = []
        while not queue.empty():
            result.append(queue.get())
        return result

    @property
    def sent(self):
        return self._read_queue(self._sent)

    @property
    def received(self):
        return self._read_queue(self._received)

    def received_extend(self, values) -> None:
        for value in values:
            self._received.put(value)

    def send(self, message) -> None:
        self._sent.put(message)

    def recv(self):
        if not self._received.empty():
            return self._received.get()

    def close(self):
        pass


# tests todo:
# 1. mediator cannot write/read, terminates
# 2. terminate mediator on ctrl-c, sigint, sigterm
# 3. terminate mediator when parent terminates
# 4. make sure that stdin & stdout passed to mediator are passed correctly to http server process
class MockedMediator:
    def __init__(self, prefix='a', port=None, remote_api=None):
        self.port = get_available_tcp_port() if port is None else port
        self.transport = MockedLoggingTransport()
        self.remote_api = default_remote_api(self.transport) if remote_api is None else remote_api
        self.server = MediatorHttpServer(DEFAULT_HTTP_IFACE, self.port, self.remote_api, 0.050)
        self.thread = self.server.run.in_thread()
        self.transport.received_extend(['mocked'])
        self.api = SingleMediatorAPI(prefix, port=self.port, startup_timeout=1)
        assert self.api.browser == 'mocked'
        self.transport.reset()

    def shutdown_and_wait(self):
        self.server.shutdown()
        self.thread.join()

    def __enter__(self):
        return self

    def __exit__(self, type_, value, tb):
        self.shutdown_and_wait()


class TestMediatorThreadTerminates(TestCase):
    def setUp(self):
        port = get_available_tcp_port()
        input_r, input_w = os.pipe()
        output_r, self.output_w = os.pipe()
        self.transport_browser = transport_with_timeout(output_r, input_w, 0.050)
        transport_mediator = transport_with_timeout(input_r, self.output_w, 0.050)
        remote_api = default_remote_api(transport_mediator)
        server = MediatorHttpServer(DEFAULT_HTTP_IFACE, port, remote_api, poll_interval=0.050)
        self.thread = server.run.in_thread()
        self.transport_browser.send('mocked')
        client = HttpClient('localhost', port, timeout=0.1)
        self.api = SingleMediatorAPI(prefix='a', port=port, startup_timeout=1, client=client)
        assert self.api.browser == 'mocked'

    def tearDown(self):
        pass

    def test_if_cannot_read(self):
        self.api.list_tabs([])
        self.thread.join()  # this should complete without manual shutdown

    def test_if_cannot_write(self):
        self.transport_browser.send(['1.1\ttitle\turl'])  # make reads work
        self.transport_browser.close()
        self.api.list_tabs([])
        self.thread.join()  # this should complete without manual shutdown


class TestMediatorProcessTerminates(TestCase):
    def test_when_parent_died(self):
        port = get_available_tcp_port()
        mediator_logger.info('starting test pid=%s', os.getpid())
        kill_parent = Barrier(2)

        def run_threaded_mediator():
            mediator_logger.info('starting mediator pid=%s', os.getpid())
            input_r, input_w = os.pipe()
            output_r, self.output_w = os.pipe()
            transport_browser = transport_with_timeout(output_r, input_w, 0.050)
            transport_mediator = transport_with_timeout(input_r, self.output_w, 0.050)
            remote_api = default_remote_api(transport_mediator)
            server = MediatorHttpServer(DEFAULT_HTTP_IFACE, port, remote_api, poll_interval=0.050)
            thread = server.run.in_thread()
            transport_browser.send('mocked')

            sig.setup(lambda: server.run.shutdown(join=False))
            server.run.parent_watcher(thread.is_alive, interval=0.050)  # this is crucial
            thread.join()

        def run_doomed_parent_browser():
            mediator_logger.info('doomed_parent_browser pid=%s', os.getpid())
            mediator_process = Process(target=run_threaded_mediator)
            mediator_process.start()
            mediator_process.join()

        def on_sig_child(signum, frame):
            pid, status = os.wait()
            mediator_logger.info('reaped child signum=%s pid=%s status=%s', signum, pid, status)

        def run_supervisor():
            signal.signal(signal.SIGCHLD, on_sig_child)
            doomed_parent_browser = Process(target=run_doomed_parent_browser)
            doomed_parent_browser.start()
            kill_parent.wait()
            doomed_parent_browser.terminate()
            doomed_parent_browser.join()

        signal.signal(signal.SIGCHLD, on_sig_child)
        supervisor = Process(target=run_supervisor)
        supervisor.start()

        client = HttpClient('localhost', port, timeout=0.1)
        api = SingleMediatorAPI(prefix='a', port=port, startup_timeout=1, client=client)
        assert api.browser == 'mocked'

        # kill parent and expect mediator to terminate as well
        kill_parent.wait()
        condition = ConditionTrue(lambda: api.get_pid() == -1)
        self.assertTrue(Waiter(condition).wait(timeout=1.0))
        supervisor.join()


# def _run_commands(commands):
#     with MockedMediator('a') as mediator:
#         get_mediator_ports_mock.side_effect = \
#             [range(mediator.port, mediator.port + 1)]
#         run_commands(commands)


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
    port = get_available_tcp_port() if port is None else port
    server = MediatorHttpServer(DEFAULT_HTTP_IFACE, port, remote_api, 0.050)
    server.run.here()


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
        self.mediator.transport.received_extend([
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
        assert self.mediator.transport.sent == [
            {'name': 'get_browser'},
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
        assert self.mediator.transport.sent == [
            {'name': 'get_browser'},
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
        assert self.mediator.transport.sent == [
            {'name': 'get_browser'},
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
        assert self.mediator.transport.sent == [
            {'name': 'get_browser'},
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
