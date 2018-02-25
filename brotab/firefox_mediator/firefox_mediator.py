#!/usr/bin/env python3

import json
import logging
import struct
import sys
import urllib

import flask

app = flask.Flask(__name__)

FORMAT = '%(asctime)-15s %(levelname)-10s %(message)s'
logging.basicConfig(
    format=FORMAT,
    filename='/tmp/firefox_mediator.log',
    level=logging.DEBUG)
logger = logging.getLogger('firefox_mediator')
logger.info('Logger has been created')

# try:

# Python 3.x version
# Read a message from stdin and decode it.

DEFAULT_HTTP_IFACE = '0.0.0.0'
DEFAULT_HTTP_PORT = 4625


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
        rawLength = self._in.read(4)
        if len(rawLength) == 0:
            sys.exit(0)
        message_length = struct.unpack('@I', rawLength)[0]
        message = self._in.read(message_length).decode('utf-8')
        logger.info('RECEIVED: %s', message)
        return json.loads(message)

    def _encode(self, message):
        encoded_content = json.dumps(message).encode('utf-8')
        encoded_lenght = struct.pack('@I', len(encoded_content))
        return {'length': encoded_lenght, 'content': encoded_content}


class FirefoxRemoteAPI:
    """
    Communicates with Firefox using stdin/stdout. This mediator is supposed
    to be run by Firefox after request by the helper extension.
    """

    def __init__(self):
        self._transport = StdTransport(sys.stdin.buffer, sys.stdout.buffer)

    def list_tabs(self):
        command = {'name': 'list_tabs'}
        self._transport.send(command)
        return self._transport.recv()

    def move_tabs(self, tab_pairs: str):
        """
        :param tab_pairs: Comma-separated list of tab IDs to close.
        """
        logger.info('move_tabs, tab_pairs: %s', tab_pairs)

        pairs = [list(map(int, pair.split(' ')))
                 for pair in tab_pairs.split(',')]
        logger.info('moving tab ids: %s', pairs)
        command = {'name': 'move_tabs', 'move_pairs': pairs}
        self._transport.send(command)

    def close_tabs(self, tab_ids: str):
        """
        :param tab_ids: Comma-separated list of tab IDs to close.
        """
        int_tab_ids = [int(id_) for id_ in tab_ids.split(',')]
        logger.info('closing tab ids: %s', int_tab_ids)
        command = {'name': 'close_tabs', 'tab_ids': int_tab_ids}
        self._transport.send(command)

    def new_tab(self, query):
        url = "https://www.google.com/search?q=%s" % urllib.parse.quote_plus(
            query)
        logger.info('opening url: %s', url)
        command = {'name': 'new_tab', 'url': url}
        self._transport.send(command)

    def activate_tab(self, tab_id):
        logger.info('activating tab id: %s', tab_id)
        command = {'name': 'activate_tab', 'tab_id': tab_id}
        self._transport.send(command)


firefox = FirefoxRemoteAPI()
logger.info('FirefoxRemoteAPI has been created')


@app.route('/list_tabs')
def list_tabs():
    tabs = firefox.list_tabs()
    return '\n'.join(tabs)


@app.route('/move_tabs/<tab_pairs>')
def move_tabs(tab_pairs):
    firefox.move_tabs(tab_pairs)
    return 'OK'


@app.route('/close_tabs/<tab_ids>')
def close_tabs(tab_ids):
    firefox.close_tabs(tab_ids)
    return 'OK'


@app.route('/new_tab/<query>')
def new_tab(query):
    firefox.new_tab(query)
    return 'OK'


@app.route('/activate_tab/<int:tab_id>')
def activate_tab(tab_id):
    firefox.activate_tab(tab_id)
    return 'OK'


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

if __name__ == '__main__':
    logger.info('Starting mediator on %s:%s...',
                DEFAULT_HTTP_IFACE, DEFAULT_HTTP_PORT)
    app.run('0.0.0.0', DEFAULT_HTTP_PORT)

    logger.info('Exiting mediator...')
