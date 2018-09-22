#!/usr/bin/env python3

import json
import logging
import struct
import os
import sys
import socket
import signal
import requests
from urllib.parse import quote_plus, unquote_plus
from typing import List

import flask
from flask import request

app = flask.Flask(__name__)

FORMAT = '%(asctime)-15s %(process)-5d %(levelname)-10s %(message)s'
logging.basicConfig(
    format=FORMAT,
    filename='/tmp/brotab_mediator.log',
    level=logging.DEBUG)
logger = logging.getLogger('brotab_mediator')
logger.info('Logger has been created')

DEFAULT_HTTP_IFACE = '127.0.0.1'
DEFAULT_MIN_HTTP_PORT = 4625
DEFAULT_MAX_HTTP_PORT = DEFAULT_MIN_HTTP_PORT + 10
actual_port = None


class StdTransport:
    def __init__(self, input_file, output_file):
        self._in = input_file
        self._out = output_file

    def send(self, message):
        encoded = self._encode(message)
        logger.info('SENDING: %s', message)
        self._out.write(encoded['length'])
        self._out.write(encoded['content'])
        self._out.flush()

    def recv(self):
        raw_rength = self._in.read(4)
        if len(raw_rength) == 0:
            sys.exit(0)
        message_length = struct.unpack('@I', raw_rength)[0]
        message = self._in.read(message_length).decode('utf8')
        logger.info('RECEIVED: %s', message.encode('utf8'))
        return json.loads(message)

    def _encode(self, message):
        encoded_content = json.dumps(message).encode('utf8')
        encoded_length = struct.pack('@I', len(encoded_content))
        return {'length': encoded_length, 'content': encoded_content}


class BrowserRemoteAPI:
    """
    Communicates with a browser using stdin/stdout. This mediator is supposed
    to be run by the browser after a request from the helper extension.
    """

    def __init__(self):
        self._transport = StdTransport(sys.stdin.buffer, sys.stdout.buffer)

    def list_tabs(self):
        command = {'name': 'list_tabs'}
        self._transport.send(command)
        return self._transport.recv()

    def move_tabs(self, move_triplets: str):
        """
        :param move_triplets: Comma-separated list of:
            <tabID> <windowID> <newIndex>
        """
        logger.info('move_tabs, move_triplets: %s', move_triplets)

        triplets = [list(map(int, triplet.split(' ')))
                    for triplet in move_triplets.split(',')]
        logger.info('moving tab ids: %s', triplets)
        command = {'name': 'move_tabs', 'move_triplets': triplets}
        self._transport.send(command)
        return self._transport.recv()

    def open_urls(self, urls: List[str], window_id=None):
        """
        Open specified list of URLs in a window, specified by window_id.

        If window_id is None, currently active window is used.
        """
        logger.info('open urls: %s', urls)

        command = {'name': 'open_urls', 'urls': urls}
        if window_id is not None:
            command['window_id'] = window_id
        self._transport.send(command)
        return self._transport.recv()

    def close_tabs(self, tab_ids: str):
        """
        :param tab_ids: Comma-separated list of tab IDs to close.
        """
        int_tab_ids = [int(id_) for id_ in tab_ids.split(',')]
        logger.info('closing tab ids: %s', int_tab_ids)
        command = {'name': 'close_tabs', 'tab_ids': int_tab_ids}
        self._transport.send(command)
        return self._transport.recv()

    def new_tab(self, query):
        url = "https://www.google.com/search?q=%s" % quote_plus(query)
        logger.info('opening url: %s', url)
        command = {'name': 'new_tab', 'url': url}
        self._transport.send(command)
        return self._transport.recv()

    def activate_tab(self, tab_id):
        logger.info('activating tab id: %s', tab_id)
        command = {'name': 'activate_tab', 'tab_id': tab_id}
        self._transport.send(command)

    def get_active_tab(self) -> str:
        logger.info('getting active tab')
        command = {'name': 'get_active_tab'}
        self._transport.send(command)
        return self._transport.recv()

    def get_words(self, tab_id):
        logger.info('getting tab words: %s', tab_id)
        command = {'name': 'get_words', 'tab_id': tab_id}
        self._transport.send(command)
        return self._transport.recv()

    def get_text(self):
        logger.info('getting text')
        command = {'name': 'get_text'}
        self._transport.send(command)
        return self._transport.recv()

    def get_browser(self):
        logger.info('getting browser name')
        command = {'name': 'get_browser'}
        self._transport.send(command)
        return self._transport.recv()


browser = BrowserRemoteAPI()
logger.info('BrowserRemoteAPI has been created')


@app.route('/shutdown')
def shutdown():
    # Taken from: https://stackoverflow.com/a/17053522/258421
    logger.info('Shutting down the server...')
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'OK'


@app.route('/list_tabs')
def list_tabs():
    tabs = browser.list_tabs()
    return '\n'.join(tabs)


@app.route('/move_tabs/<move_triplets>')
def move_tabs(move_triplets):
    return browser.move_tabs(unquote_plus(move_triplets))


@app.route('/open_urls', methods=['POST'])
@app.route('/open_urls/<int:window_id>', methods=['POST'])
def open_urls(window_id=None):
    urls = request.files.get('urls')
    if urls is None:
        return 'ERROR: Please provide urls file in the request'
    urls = urls.stream.read().decode('utf8').splitlines()
    logger.info('Open urls (window_id = %s): %s', window_id, urls)
    return browser.open_urls(urls, window_id)


@app.route('/close_tabs/<tab_ids>')
def close_tabs(tab_ids):
    return browser.close_tabs(tab_ids)


@app.route('/new_tab/<query>')
def new_tab(query):
    return browser.new_tab(query)


@app.route('/activate_tab/<int:tab_id>')
def activate_tab(tab_id):
    browser.activate_tab(tab_id)
    return 'OK'


@app.route('/get_active_tab')
def get_active_tab():
    return browser.get_active_tab()


@app.route('/get_words')
@app.route('/get_words/<int:tab_id>')
def get_words(tab_id=None):
    words = browser.get_words(tab_id)
    logger.info('words for tab_id %s: %s', tab_id, words)
    return '\n'.join(words)


@app.route('/get_text')
def get_text():
    lines = browser.get_text()
    return '\n'.join(lines)


@app.route('/get_pid')
def get_pid():
    return str(os.getpid())


@app.route('/get_browser')
def get_browser():
    return browser.get_browser()


# TODO:
# 1. Run HTTP server and accept the following commands:
#    - /list_tabs
#    - /close_tabs
#    - /move_tabs ???
#    - /open_tab
#    - /open_urls
#    - /new_tab (google search)
#    - /get_tab_text
#    - /get_active_tab_text
#
# TODO: fix bug when the number of tabs > 1100
# TODO: read stdin continuously in a separate thraed,
#       detect if it's closed, shutdown the server, and exit.
#       make sure this threaded reader and server reader are mutually exclusive.
# TODO: all commands should be synchronous and should only terminate after
#       the action has been actually executed in the browser.


def signal_pipe(e):
    logger.info('Pipe has been closed...')
    requests.get('http://%s:%s/shutdown' % (DEFAULT_HTTP_IFACE, actual_port))


def disable_click_echo():
    """Stupid flask started using click which unconditionally prints stupid
    messages"""
    def numb_echo(*args, **kwargs):
        pass

    import click
    click.echo = numb_echo
    click.secho = numb_echo


def monkeypatch_socket_bind():
    """Allow port reuse by default"""
    socket.socket._bind = socket.socket.bind

    def my_socket_bind(self, *args, **kwargs):
        logger.info('Custom bind called: %s, %s', args, kwargs)
        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return socket.socket._bind(self, *args, **kwargs)
    socket.socket.bind = my_socket_bind


def main():
    signal.signal(signal.SIGPIPE, signal_pipe)
    monkeypatch_socket_bind()
    disable_click_echo()

    global actual_port
    for port in range(DEFAULT_MIN_HTTP_PORT, DEFAULT_MAX_HTTP_PORT):
        logger.info('Starting mediator on %s:%s...',
                    DEFAULT_HTTP_IFACE, port)
        actual_port = port
        try:
            app.run(DEFAULT_HTTP_IFACE, port, debug=False)
            logger.info('Exiting mediator...')
            break
        except OSError as e:
            logger.info('Cannot bind on port %s: %s', port, e)

    else:
        logger.error(
            'No TCP ports available for bind in range from %s to %s',
            DEFAULT_MIN_HTTP_PORT, DEFAULT_MAX_HTTP_PORT)


if __name__ == '__main__':
    main()
