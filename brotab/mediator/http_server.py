import os
from json import loads
from threading import Thread
from urllib.parse import unquote_plus
from wsgiref.simple_server import make_server

from flask import Flask
from flask import request

from brotab.mediator.const import DEFAULT_GET_HTML_DELIMITER_REGEX
from brotab.mediator.const import DEFAULT_GET_HTML_REPLACE_WITH
from brotab.mediator.const import DEFAULT_GET_TEXT_DELIMITER_REGEX
from brotab.mediator.const import DEFAULT_GET_TEXT_REPLACE_WITH
from brotab.mediator.const import DEFAULT_GET_WORDS_JOIN_WITH
from brotab.mediator.const import DEFAULT_GET_WORDS_MATCH_REGEX
from brotab.mediator.log import mediator_logger
from brotab.mediator.remote_api import BrowserRemoteAPI
from brotab.mediator.runner import Runner
from brotab.mediator.support import is_valid_integer
from brotab.mediator.transport import TransportError
from brotab.utils import decode_query


class MediatorHttpServer:
    def __init__(self, host: str, port: int, remote_api: BrowserRemoteAPI, poll_interval: float):
        self.host: str = host
        self.port: int = port
        self.remote_api: BrowserRemoteAPI = remote_api
        self.pid: int = os.getpid()
        self.app = Flask(__name__)
        self.http_server = make_server(host=host, port=port, app=self.app)
        self._setup_routes()

        def serve():
            mediator_logger.info('Serving mediator on %s:%s', host, port)
            self.http_server.serve_forever(poll_interval=poll_interval)

        def shutdown(join: bool):
            mediator_logger.info('Closing mediator http server on %s:%s', host, port)
            self.http_server.server_close()
            mediator_logger.info('Shutting down mediator http server on %s:%s', host, port)
            thread = Thread(target=self.http_server.shutdown)
            thread.daemon = True
            thread.start()
            if join:
                thread.join()
            mediator_logger.info('Done shutting down mediator (is_alive=%s) http server on %s:%s',
                                 thread.is_alive(), host, port)

        self.run = Runner(serve, shutdown)

    def _setup_routes(self) -> None:
        mediator_logger.info('Starting mediator http server on %s:%s pid=%s', self.host, self.port, self.pid)
        self.app.register_error_handler(ConnectionError, self.error_handler)
        self.app.register_error_handler(TimeoutError, self.error_handler)
        self.app.register_error_handler(ValueError, self.error_handler)
        self.app.register_error_handler(TransportError, self.error_handler)
        self.app.route('/', methods=['GET'])(self.root_handler)
        self.app.route('/shutdown', methods=['GET'])(self.shutdown)
        self.app.route('/list_tabs', methods=['GET'])(self.list_tabs)
        self.app.route('/query_tabs/<query_info>', methods=['GET'])(self.query_tabs)
        self.app.route('/move_tabs/<query_info>', methods=['GET'])(self.move_tabs)
        self.app.route('/open_urls/<int:window_id>', methods=['POST'])(self.open_urls)
        self.app.route('/update_tabs', methods=['POST'])(self.update_tabs)
        self.app.route('/open_urls', methods=['POST'])(self.open_urls)
        self.app.route('/close_tabs/<tab_ids>', methods=['GET'])(self.close_tabs)
        self.app.route('/new_tab/<query>', methods=['GET'])(self.new_tab)
        self.app.route('/activate_tab/<int:tab_id>', methods=['GET'])(self.activate_tab)
        self.app.route('/get_active_tabs', methods=['GET'])(self.get_active_tabs)
        self.app.route('/get_words/<string:tab_id>', methods=['GET'])(self.get_words)
        self.app.route('/get_words', methods=['GET'])(self.get_words)
        self.app.route('/get_text', methods=['GET'])(self.get_text)
        self.app.route('/get_html', methods=['GET'])(self.get_html)
        self.app.route('/get_pid', methods=['GET'])(self.get_pid)
        self.app.route('/get_browser', methods=['GET'])(self.get_browser)
        self.app.route('/echo', methods=['GET'])(self.echo)

    def error_handler(self, e: Exception):
        mediator_logger.exception('Shutting down mediator http server due to exception: %s', e)
        # can't wait for shutdown here because we're processing a request right now,
        # we will get deadlocked if we wait (join=True)
        self.run.shutdown(join=False)
        return '<ERROR>'

    def root_handler(self):
        links = []
        for rule in self.app.url_map.iter_rules():
            methods = ','.join(rule.methods)
            line = '{0}\t{1}\t{2}'.format(rule.endpoint, methods, rule)
            links.append(line)
        return '\n'.join(links)

    def shutdown(self):
        # can't wait for shutdown here because we're processing a request right now,
        # we will get deadlocked if we wait (join=True)
        self.run.shutdown(join=False)
        return 'OK'

    def list_tabs(self):
        tabs = self.remote_api.list_tabs()
        return '\n'.join(tabs)

    def query_tabs(self, query_info):
        tabs = self.remote_api.query_tabs(query_info)
        return '\n'.join(tabs)

    def move_tabs(self, move_triplets):
        return self.remote_api.move_tabs(unquote_plus(move_triplets))

    def open_urls(self, window_id=None):
        urls = request.files.get('urls')
        if urls is None:
            return 'ERROR: Please provide urls file in the request'
        urls = urls.stream.read().decode('utf8').splitlines()
        mediator_logger.info('Open urls (window_id = %s): %s', window_id, urls)
        result = self.remote_api.open_urls(urls, window_id)
        mediator_logger.info('Open urls result: %s', str(result))
        return '\n'.join(result)

    def update_tabs(self):
        updates = request.files.get('updates')
        if updates is None:
            return 'ERROR: Please provide updates in the request'
        updates = loads(updates.stream.read().decode('utf8'))
        mediator_logger.info('Sending tab updates: %s', updates)
        result = self.remote_api.update_tabs(updates)
        mediator_logger.info('Update tabs result: %s', str(result))
        return '\n'.join(result)

    def close_tabs(self, tab_ids):
        return self.remote_api.close_tabs(tab_ids)

    def new_tab(self, query):
        return self.remote_api.new_tab(query)

    def activate_tab(self, tab_id):
        focused = bool(request.args.get('focused', False))
        self.remote_api.activate_tab(tab_id, focused)
        return 'OK'

    def get_active_tabs(self):
        return self.remote_api.get_active_tabs()

    def get_words(self, tab_id=None):
        tab_id = int(tab_id) if is_valid_integer(tab_id) else None
        match_regex = request.args.get('match_regex', DEFAULT_GET_WORDS_MATCH_REGEX)
        join_with = request.args.get('join_with', DEFAULT_GET_WORDS_JOIN_WITH)
        words = self.remote_api.get_words(tab_id,
                                          decode_query(match_regex),
                                          decode_query(join_with))
        mediator_logger.info('words for tab_id %s (match_regex %s, join_with %s): %s',
                             tab_id, match_regex, join_with, words)
        return '\n'.join(words)

    def get_text(self):
        delimiter_regex = request.args.get('delimiter_regex', DEFAULT_GET_TEXT_DELIMITER_REGEX)
        replace_with = request.args.get('replace_with', DEFAULT_GET_TEXT_REPLACE_WITH)
        lines = self.remote_api.get_text(decode_query(delimiter_regex),
                                         decode_query(replace_with))
        return '\n'.join(lines)

    def get_html(self):
        delimiter_regex = request.args.get('delimiter_regex', DEFAULT_GET_HTML_DELIMITER_REGEX)
        replace_with = request.args.get('replace_with', DEFAULT_GET_HTML_REPLACE_WITH)
        lines = self.remote_api.get_html(decode_query(delimiter_regex),
                                         decode_query(replace_with))
        return '\n'.join(lines)

    def get_pid(self):
        mediator_logger.info('getting pid')
        return str(os.getpid())

    def get_browser(self):
        mediator_logger.info('getting browser name')
        return self.remote_api.get_browser()

    def echo(self):
        title = request.args.get('title', 'title')
        body = request.args.get('body', 'body')
        reply = ('<html><head><title>%s</title></head>'
                 '<body>%s</body></html>'
                 % (title, body))
        return reply
