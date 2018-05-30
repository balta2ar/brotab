import os
import time
import signal
import pytest
import threading
from unittest import TestCase

#import delegator
from subprocess import check_output, Popen

from brotab.tests.utils import wait_net_service
from brotab.tests.utils import kill_by_substring

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


def run(cmd):
    return check_output(cmd, shell=True).decode('utf-8').splitlines()


TIMEOUT = 5


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
        print('TITLE', title, 'BODY', body)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        reply = ('<html><head><title>%s</title></head>'
                 '<body>%s</body></html>'
                 % (title, body)).encode('utf-8')
        self.send_header("Content-Length", str(len(reply)))
        self.end_headers()
        self.wfile.write(reply)
        #self.wfile.close()


ECHO_SERVER_HOST = 'localhost'
ECHO_SERVER_PORT = 9000

class EchoServer:
    def __init__(self):
        self._thread = None
        self._server = None

    def run(self, host=ECHO_SERVER_HOST, port=ECHO_SERVER_PORT):
        self._server = HTTPServer((host, port), EchoRequestHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        self._server.shutdown()
        self._server.socket.close()
        self._thread.join(TIMEOUT)

    @staticmethod
    def url(title='', body=''):
        return 'http://%s:%s?title=%s&body=%s' % (
            ECHO_SERVER_HOST, ECHO_SERVER_PORT, title, body)


class BtWrapper:
    @staticmethod
    def list():
        return run('bt list')

    @staticmethod
    def open(window_id, url):
        return run('echo "%s" | bt open %s' % (
            EchoServer.url('tab1'), window_id))


class TestChromium(TestCase):
    def setUp(self):
        # xvfb-run chromium-browser --no-sandbox --no-first-run --disable-gpu --remote-debugging-port=10222 --remote-debugging-address=0.0.0.0 --load-extension=/brotab/brotab/firefox_extension
        #self._chrome = delegator.run(

        self._fake_server = EchoServer()
        self._fake_server.run()

        # cmd = ('xvfb-run chromium-browser --no-sandbox --no-first-run '
        #        '--disable-gpu '
        #        '--load-extension=/brotab/brotab/extension/chrome')
        cmd = ('xvfb-run web-ext run')
        #cwd = None
        cwd = '/brotab/brotab/extension/firefox'
        print('CMD', cmd, 'CWD', cwd)
        # Used a trick from here: https://stackoverflow.com/a/22582602/258421
        self._chrome = Popen(cmd, shell=True, cwd=cwd, preexec_fn=os.setsid)
        print('PID', self._chrome.pid)
        #wait_net_service('localhost', 10222, 5)
        wait_net_service('localhost', 4625, 5)
        print('SETUP DONE:', self._chrome.pid)

    def tearDown(self):
        print('CHROME', self._chrome)
        # This is supposed to be run in Docker only
        # kill_by_substring('xvfb')
        # kill_by_substring('brotab')
        # psutil.Process(11970).children(recursive=True)
        # self._chrome.kill()
        # self._chrome.send('SIGTERM', signal=True)

        #self._chrome.terminate()
        #self._chrome.kill()
        os.killpg(os.getpgid(self._chrome.pid), signal.SIGTERM)
        self._chrome.wait(TIMEOUT)

        self._fake_server.stop()
        print('BLOCK DONE')

    # def test_smoke(self):
    #     print('>>>>>>>>> SMOKE')

    def test_open_single(self):
        print('SINGLE START')

        tabs = BtWrapper.list()
        assert 'tab1' not in ''.join(tabs)
        BtWrapper.open('a.1', EchoServer.url('tab1'))

        tabs = BtWrapper.list()
        assert 'tab1' in ''.join(tabs)

        print('SINGLE END')


if __name__ == '__main__':
    server = EchoServer()
    server.run('0.0.0.0', 8087)
