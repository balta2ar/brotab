import os
import signal
from contextlib import contextmanager
from multiprocessing import Barrier
from multiprocessing import Process
from unittest import TestCase

from brotab.api import api_must_ready
from brotab.inout import get_available_tcp_port
from brotab.mediator import sig
from brotab.mediator.const import DEFAULT_HTTP_IFACE
from brotab.mediator.http_server import MediatorHttpServer
from brotab.mediator.log import mediator_logger
from brotab.mediator.remote_api import default_remote_api
# from brotab.mediator.transport import transport_with_timeout
from brotab.wait import Waiter


# class MockedPiperMediator:
#     def __init__(self, prefix='a', port=None, remote_api=None):
#         mediator_logger.info('starting mediator pid=%s', os.getpid())
#         self.prefix = prefix
#         self.port = get_available_tcp_port() if port is None else port
#         input_r, input_w = os.pipe()
#         output_r, output_w = os.pipe()
#         self.transport_browser = transport_with_timeout(output_r, input_w, 0.050)
#         self.transport_mediator = transport_with_timeout(input_r, output_w, 0.050)
#         self.remote_api = default_remote_api(self.transport_mediator) if remote_api is None else remote_api
#         self.server = MediatorHttpServer(DEFAULT_HTTP_IFACE, self.port, self.remote_api, poll_interval=0.050)
#         self.thread = None
#         self.api = None
#
#     def start(self):
#         self.thread = self.server.run.in_thread()
#         self.transport_browser.send('mocked')
#
#     def wait_api_ready(self):
#         self.api = api_must_ready(port=self.port, browser='mocked', prefix=self.prefix,
#                                   client_timeout=0.1, startup_timeout=1)
#
#     def join(self):
#         # sig.setup(lambda: server.run.shutdown(join=False))
#         self.server.run.parent_watcher(self.thread.is_alive, interval=0.050)  # this is crucial
#         self.thread.join()
#
#     def __enter__(self):
#         return self
#
#     def __exit__(self, type_, value, tb):
#         self.join()
#
#
# class TestMediatorThreadTerminates(TestCase):
#     def setUp(self):
#         self.mediator = MockedPiperMediator()
#         self.mediator.start()
#         self.mediator.wait_api_ready()
#
#     def tearDown(self):
#         pass
#
#     def test_if_cannot_read(self):
#         self.mediator.api.list_tabs([])
#         self.mediator.join()  # this should complete without manual shutdown
#
#     def test_if_cannot_write(self):
#         self.mediator.transport_browser.send(['1.1\ttitle\turl'])  # make reads work
#         self.mediator.transport_browser.close()
#         self.mediator.api.list_tabs([])
#         self.mediator.join()  # this should complete without manual shutdown
#
#
# class TestMediatorProcessTerminates(TestCase):
#     def test_when_parent_died(self):
#         port = get_available_tcp_port()
#         mediator_logger.info('starting test pid=%s', os.getpid())
#         kill_parent = Barrier(2)
#
#         def run_threaded_mediator():
#             mediator = MockedPiperMediator(port=port)
#             mediator.start()
#             mediator.join()
#
#         def run_doomed_parent_browser():
#             mediator_logger.info('doomed_parent_browser pid=%s', os.getpid())
#             mediator_process = Process(target=run_threaded_mediator)
#             mediator_process.start()
#             mediator_process.join()
#
#         def on_sig_child(signum, frame):
#             pid, status = os.wait()
#             mediator_logger.info('reaped child signum=%s pid=%s status=%s', signum, pid, status)
#
#         def run_supervisor():
#             signal.signal(signal.SIGCHLD, on_sig_child)
#             doomed_parent_browser = Process(target=run_doomed_parent_browser)
#             doomed_parent_browser.start()
#             kill_parent.wait()
#             doomed_parent_browser.terminate()
#             doomed_parent_browser.join()
#
#         signal.signal(signal.SIGCHLD, on_sig_child)
#         supervisor = Process(target=run_supervisor)
#         supervisor.start()
#         api = api_must_ready(port, 'mocked')
#
#         # kill parent and expect mediator to terminate as well
#         kill_parent.wait()
#         self.assertTrue(Waiter(api.pid_not_ready).wait(timeout=1.0))
#         supervisor.join()
#
#     @contextmanager
#     def run_as_child_process(self):
#         port = get_available_tcp_port()
#         mediator_logger.info('starting test pid=%s', os.getpid())
#
#         def run_threaded_mediator():
#             mediator = MockedPiperMediator(port=port)
#             mediator.start()
#             sig.setup(lambda: mediator.server.run.shutdown(join=False))
#             mediator.join()
#
#         mediator_process = Process(target=run_threaded_mediator)
#         mediator_process.start()
#         api = api_must_ready(port, 'mocked')
#
#         yield mediator_process
#
#         self.assertTrue(Waiter(api.pid_not_ready).wait(timeout=1.0))
#         mediator_process.join()
#
#     def test_when_sigint_received(self):
#         with self.run_as_child_process() as mediator_process:
#             os.kill(mediator_process.pid, signal.SIGINT)
#
#     def test_when_sigterm_received(self):
#         with self.run_as_child_process() as mediator_process:
#             os.kill(mediator_process.pid, signal.SIGTERM)
