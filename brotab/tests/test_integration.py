import os
import signal
import threading
from subprocess import check_output, Popen
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from unittest import TestCase
import pytest


from brotab.tests.utils import wait_net_service
from brotab.mediator.brotab_mediator import DEFAULT_MIN_HTTP_PORT
from brotab.tab import parse_tab_lines


def run(cmd):
    return check_output(cmd, shell=True).decode('utf-8').strip().splitlines()


TIMEOUT = 60 # 15
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


class BtCommandWrapper:
    @staticmethod
    def list():
        return run('bt list')

    @staticmethod
    def tabs():
        return parse_tab_lines(BtCommandWrapper.list())

    @staticmethod
    def open(window_id, url):
        return run('echo "%s" | bt open %s' % (url, window_id))

    @staticmethod
    def active():
        return run('bt active')


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


class Firefox(Browser):
    #CMD = 'xvfb-run web-ext run --verbose --no-input --no-reload -p /dev/shm/firefox'
    CMD = 'web-ext run --verbose --no-reload -p /dev/shm/firefox'
    CWD = '/brotab/brotab/extension/firefox'
    PROFILE = 'firefox'


class Chromium(Browser):
    #CMD = ('xvfb-run chromium-browser --no-sandbox '
    CMD = ('chromium-browser --no-sandbox '
           '--no-first-run --disable-gpu '
           # '--enabled-logging=stderr '
           '--enabled-logging --v=1 '
           '--user-data-dir=/dev/shm/chromium '
           '--load-extension=/brotab/brotab/extension/chrome_tests ')
    #    '--user-data-dir=/dev/shm/chromium')
    CWD = '/brotab/brotab/extension/chrome'
    PROFILE = 'chromium'


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

    # def test_smoke(self):
    #     print('>>>>>>>>> SMOKE')

    def test_open_single(self):
        print('SINGLE START')

        tabs = BtCommandWrapper.list()
        assert 'tab1' not in ''.join(tabs)
        BtCommandWrapper.open('a.1', EchoServer.url('tab1'))

        tabs = BtCommandWrapper.list()
        assert 'tab1' in ''.join(tabs)

        print('SINGLE END')

    def test_active_tabs(self):
        BtCommandWrapper.open('a.1', EchoServer.url('tab1'))
        BtCommandWrapper.open('a.2', EchoServer.url('tab2'))
        BtCommandWrapper.open('a.3', EchoServer.url('tab3'))
        assert len(BtCommandWrapper.tabs()) == 4
        assert BtCommandWrapper.active()[0] == BtCommandWrapper.tabs()[-1].id


if __name__ == '__main__':
    server = EchoServer()
    server.run(ECHO_SERVER_HOST, ECHO_SERVER_PORT)
    print('Running EchoServer at %s:%s. Press Enter to terminate' % (
        ECHO_SERVER_HOST, ECHO_SERVER_PORT))
    input()
