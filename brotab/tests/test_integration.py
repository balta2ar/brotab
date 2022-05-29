import os
import signal
import threading
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from json import dumps
from subprocess import Popen
from subprocess import check_output
from unittest import TestCase
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pytest

from brotab.api import api_must_ready
from brotab.inout import get_available_tcp_port
from brotab.inout import wait_net_service
from brotab.mediator.const import DEFAULT_MIN_HTTP_PORT
from brotab.operations import make_update
from brotab.tab import parse_tab_lines


def run(args):
    return check_output(args, shell=True).decode('utf-8').strip().splitlines()


def git_root():
    return run(['git rev-parse --show-toplevel'])[0]


def requires_integration_env():
    value = os.environ.get('INTEGRATION_TEST')
    return pytest.mark.skipif(
        value is None,
        reason=f"Skipped because INTEGRATION_TEST=1 is not set"
    )


TIMEOUT = 60  # 15
ECHO_SERVER_PORT = 8087


class EchoRequestHandler(BaseHTTPRequestHandler):
    """
    Sample URL:

        localhost:9000?title=tab1&body=tab1
    """

    def _get_str_arg(self, path, arg_name):
        args = parse_qs(urlparse(path).query)
        return ''.join(args.get(arg_name, ''))

    def do_GET(self):
        title = self._get_str_arg(self.path, 'title')
        body = self._get_str_arg(self.path, 'body')
        print('EchoServer received TITLE "%s" BODY "%s"' % (title, body))

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        reply = ('<html><head><title>%s</title></head>'
                 '<body>%s</body></html>'
                 % (title, body)).encode('utf-8')
        self.send_header("Content-Length", str(len(reply)))
        self.end_headers()
        self.wfile.write(reply)
        # self.wfile.close()


ECHO_SERVER_HOST = 'localhost'
ECHO_SERVER_PORT = 9000


class EchoServer:
    """
    This EchoServer is used to customize page title and content using URL
    parameters.
    """

    def __init__(self):
        self._thread = None
        self._server = None

    def run(self, host=ECHO_SERVER_HOST, port=ECHO_SERVER_PORT):
        self._server = HTTPServer((host, port), EchoRequestHandler)
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        self._server.shutdown()
        self._server.socket.close()
        self._thread.join(TIMEOUT)

    @staticmethod
    def url(title='', body=''):
        return 'http://%s:%s?title=%s&body=%s' % (
            ECHO_SERVER_HOST, ECHO_SERVER_PORT, title, body)


class Brotab:
    def __init__(self, target_hosts: str):
        """
        target_hosts: e.g. 'localhost:4625,localhost:4626'
        """
        self.targets = target_hosts
        self.options = '--target %s' % self.targets if self.targets else ''

    def list(self):
        return run(f'bt {self.options} list')

    def tabs(self):
        return parse_tab_lines(self.list())

    def open(self, window_id, url):
        return run(f'echo "{url}" | bt {self.options} open {window_id}')

    def active(self):
        return run(f'bt {self.options} active')

    def windows(self):
        return run(f'bt {self.options} windows')

    def navigate(self, tab_id, url):
        return run(f'bt {self.options} navigate {tab_id} "{url}"')

    def update_stdin(self, updates):
        updates = dumps(updates)
        return run(f'echo \'{updates}\' | bt {self.options} update')

    def update(self, args):
        return run(f'bt {self.options} update {args}')


class Browser:
    CMD = ''
    CWD = ''
    PROFILE = ''

    def __init__(self):
        print('CMD', self.CMD, 'CWD', self.CWD)
        # Used a trick from here: https://stackoverflow.com/a/22582602/258421
        os.makedirs('/dev/shm/%s' % self.PROFILE, exist_ok=True)
        self._browser = Popen(self.CMD, shell=True,
                              cwd=self.CWD, preexec_fn=os.setsid)
        print('PID', self._browser.pid)
        wait_net_service('localhost', DEFAULT_MIN_HTTP_PORT, TIMEOUT)
        print('init done PID', self._browser.pid)

    def stop(self):
        os.killpg(os.getpgid(self._browser.pid), signal.SIGTERM)
        self._browser.wait(TIMEOUT)

    @property
    def pid(self):
        return self._browser.pid


class Container:
    NAME = 'chrome/chromium'

    def __init__(self):
        root = git_root()
        self.guest_port = 4625
        self.host_port = get_available_tcp_port()
        display = os.environ.get('DISPLAY', ':0')
        args = ['docker', 'run', '-v',
                f'"{root}:/brotab"',
                # '-p', '19222:9222',
                '-p', f'{self.host_port}:{self.guest_port}',
                '--detach --rm --cpuset-cpus 0',
                '--memory 512mb -v /tmp/.X11-unix:/tmp/.X11-unix',
                f'-e DISPLAY=unix{display}',
                '-v /dev/shm:/dev/shm',
                'brotab-integration']
        cmd = ' '.join(args)
        self.container_id = run(cmd)[0]
        api_must_ready(self.host_port, self.NAME, 'a', client_timeout=3.0, startup_timeout=10.0)

    def stop(self):
        run(f'docker kill {self.container_id}')

    def __enter__(self):
        return self

    def __exit__(self, type_, value, tb):
        self.stop()

    @property
    def guest_addr(self):
        return f'localhost:{self.guest_port}'

    @property
    def host_addr(self):
        return f'localhost:{self.host_port}'

    def echo_url(self, title=None, body=None):
        url = f'http://{self.guest_addr}/echo?'
        url += 'title=' + title if title else ''
        url += '&body=' + body if body else ''
        return url


def targets(containers: [Container]) -> str:
    return ','.join([c.host_addr for c in containers])


@requires_integration_env()
class TestIntegration(TestCase):
    def test_open_single(self):
        with Container() as c:
            bt = Brotab(targets([c]))
            tabs = bt.list()
            assert 'tab1' not in ''.join(tabs)
            tab_ids = bt.open('a.1', c.echo_url('tab1'))
            assert len(tab_ids) == 1

            tabs = bt.list()
            assert 'tab1' in ''.join(tabs)
            assert tab_ids[0] in ''.join(tabs)

    def test_active_tabs(self):
        with Container() as c:
            bt = Brotab(targets([c]))
            bt.open('a.1', c.echo_url('tab1'))
            bt.open('a.1', c.echo_url('tab2'))
            bt.open('a.1', c.echo_url('tab3'))
            assert len(bt.tabs()) == 4
            active_id = bt.active()[0].split('\t')[0]
            assert active_id == bt.tabs()[-1].id

    def test_navigate_single(self):
        with Container() as c:
            bt = Brotab(targets([c]))
            tab_ids = bt.open('a.1', c.echo_url('tab1'))
            assert len(tab_ids) == 1

            tabs = bt.list()
            assert 'tab1' in ''.join(tabs)
            assert tab_ids[0] in ''.join(tabs)

            bt.navigate(tab_ids[0], c.echo_url('tab2'))
            tabs = bt.list()
            assert 'tab2' in ''.join(tabs)
            assert tab_ids[0] in ''.join(tabs)

    def test_update_three(self):
        with Container() as c:
            bt = Brotab(targets([c]))
            bt.open('a.1', c.echo_url('tab1'))
            bt.open('a.1', c.echo_url('tab1'))
            lines = sorted(bt.list())
            assert len(lines) == 3
            assert 'tab2' not in ''.join(lines)

            tabs = parse_tab_lines(lines)
            bt.update_stdin([make_update(tabId=tabs[0].id, url=c.echo_url('tab2'))])
            bt.update_stdin([make_update(tabId=tabs[1].id, url=c.echo_url('tab2'))])
            bt.update('-tabId {0} -url="{1}"'.format(tabs[2].id, c.echo_url('tab2')))

            lines = bt.list()
            assert 'tab1' not in ''.join(lines)
            assert 'tab2' in ''.join(lines)


@pytest.mark.skip
class TestChromium(TestCase):
    def setUp(self):
        self._echo_server = EchoServer()
        self._echo_server.run()
        self.addCleanup(self._echo_server.stop)

        self._browser = Chromium()
        # self._browser = Firefox()
        # self.addCleanup(self._browser.stop)
        print('SETUP DONE:', self._browser.pid)

    def tearDown(self):
        print('CHROME', self._browser)
        print('BLOCK DONE')

    def test_open_single(self):
        print('SINGLE START')

        tabs = Brotab.list()
        assert 'tab1' not in ''.join(tabs)
        Brotab.open('a.1', EchoServer.url('tab1'))

        tabs = Brotab.list()
        assert 'tab1' in ''.join(tabs)

        print('SINGLE END')

    def test_active_tabs(self):
        Brotab.open('a.1', EchoServer.url('tab1'))
        Brotab.open('a.2', EchoServer.url('tab2'))
        Brotab.open('a.3', EchoServer.url('tab3'))
        assert len(Brotab.tabs()) == 4
        assert Brotab.active()[0] == Brotab.tabs()[-1].id


if __name__ == '__main__':
    server = EchoServer()
    server.run(ECHO_SERVER_HOST, ECHO_SERVER_PORT)
    print('Running EchoServer at %s:%s. Press Enter to terminate' % (
        ECHO_SERVER_HOST, ECHO_SERVER_PORT))
    input()
