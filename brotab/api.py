import io
import json
import logging
import socket
import sys
from collections.abc import Mapping
from copy import deepcopy
from functools import partial
from http.client import RemoteDisconnected
from json import dumps
from traceback import print_exc
from typing import List
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import quote_plus
from urllib.request import Request
from urllib.request import urlopen

from brotab.env import http_iface
from brotab.inout import MultiPartForm
from brotab.inout import edit_tabs_in_editor
from brotab.operations import infer_all_commands
from brotab.parallel import call_parallel
from brotab.tab import parse_tab_lines
from brotab.utils import encode_query
from brotab.wait import ConditionTrue
from brotab.wait import Waiter

logger = logging.getLogger('brotab')

HTTP_TIMEOUT = 10.0
MAX_NUMBER_OF_TABS = 5000


class HttpClient:
    def __init__(self, host='localhost', port=4625, timeout=HTTP_TIMEOUT):
        self._host: str = host
        self._port: int = port
        self._timeout: float = timeout

    def get(self, path, data=None):
        url = 'http://%s:%s%s' % (self._host, self._port, path)
        logger.info('GET %s' % url)
        if data is not None:
            data = data.encode('utf8')
        request = Request(url=url, data=data, method='GET')

        with urlopen(request, timeout=self._timeout) as response:
            return response.read().decode('utf8')

    def post(self, path, files=None):
        url = 'http://%s:%s%s' % (self._host, self._port, path)
        logger.info('POST %s' % url)
        form = MultiPartForm()
        for filename, content in files.items():
            form.add_file(filename, filename,
                          io.BytesIO(content.encode('utf8')))

        data = bytes(form)
        request = Request(url=url, data=data, method='POST')
        request.add_header('Content-Type', form.get_content_type())
        request.add_header('Content-Length', str(len(data)))

        with urlopen(request, timeout=self._timeout) as response:
            return response.read().decode('utf8')


class StartupTimeout(BaseException):
    pass


class SingleMediatorAPI(object):
    """
    This API is designed to work with a single mediator.
    """

    def __init__(self, prefix, host='localhost', port=4625, startup_timeout: float = None, client: HttpClient = None):
        self._prefix = '%s.' % prefix
        self._host = host
        self._port = port
        self._client = HttpClient(host=host, port=port) if client is None else client
        if startup_timeout is not None:
            self.must_ready(timeout=startup_timeout)
        self._pid = self.get_pid()
        self._browser = self.get_browser()

    def must_ready(self, timeout: float) -> None:
        condition = ConditionTrue(lambda: self.get_pid() != -1)
        if not Waiter(condition).wait(timeout=timeout):
            raise StartupTimeout('Failed to start in %s seconds' % timeout)

    def pid_ready(self) -> bool:
        return self.get_pid() != -1

    def pid_not_ready(self) -> bool:
        return not self.pid_ready()

    @property
    def browser(self) -> str:
        return self._browser

    @property
    def ready(self) -> bool:
        return self._browser != '<ERROR>'

    def __str__(self):
        return '%s\t%s:%s\t%s\t%s' % (
            self._prefix, self._host, self._port, self._pid, self._browser)

    def prefix_tab(self, tab):
        return '%s%s' % (self._prefix, tab)

    def prefix_tabs(self, tabs):
        return list(map(self.prefix_tab, tabs))

    def unprefix_tabs(self, tabs):
        num = len(self._prefix)
        return [tab[num:]
                if tab.startswith(self._prefix)
                else tab for tab in tabs]

    def prefix_match(self, tab):
        return tab.startswith(self._prefix)

    def filter_tabs(self, tabs):
        # N = len(self._prefix)
        # return [tab[N:] for tab in tabs
        return [tab for tab in tabs if self.prefix_match(tab)]

    def _split_tabs(self, tabs):
        return [tab.split('.') for tab in tabs]

    def get_pid(self):
        """Get process ID from the mediator."""
        try:
            return int(self._get('/get_pid'))
        except (URLError, HTTPError, socket.timeout, RemoteDisconnected, ConnectionResetError) as e:
            logger.info('_get_pid failed: %s', e)
        return -1

    def get_browser(self):
        """Get browser name from the mediator."""
        try:
            return self._get('/get_browser')
        except (URLError, HTTPError, socket.timeout, RemoteDisconnected, ConnectionResetError) as e:
            logger.info('_get_browser failed: %s', e)
        return '<ERROR>'

    def close_tabs(self, args):
        tabs = ','.join(tab_id for _prefix, _window_id,
                                   tab_id in self._split_tabs(args))
        return self._get('/close_tabs/%s' % tabs)

    def activate_tab(self, args: List[str], focused: bool):
        if len(args) == 0:
            return

        # args: ['a.1.2']
        _prefix, _window_id, tab_id = args[0].split('.')
        self._get('/activate_tab/%s%s' % (tab_id, '?focused=1' if focused else ''))

    def get_active_tabs(self, args) -> List[str]:
        return [self.prefix_tab(tab) for tab in self._get('/get_active_tabs').split(',')]

    def query_tabs(self, args):
        query = args
        if isinstance(query, str):
            try:
                query = json.loads(query)
                if not isinstance(query, Mapping):
                    raise json.JSONDecodeError("json has attributes unsupported by brotab.", "", 0)
            except json.JSONDecodeError as e:
                print("Cannot decode JSON: %s: %s" % (__name__, e), file=sys.stderr)
                return []

        result = self._get('/query_tabs/%s' % encode_query(json.dumps(query)))
        lines = result.splitlines()[:MAX_NUMBER_OF_TABS]
        return self.prefix_tabs(lines)

    def query_tabs_safe(self, args, print_error=False):
        args = args or []
        tabs = []
        try:
            tabs = self.query_tabs(args)
        except ValueError as e:
            print("Cannot decode JSON: %s: %s" % (self, e), file=sys.stderr)
            if print_error:
                print_exc(file=sys.stderr)
        except URLError as e:
            print("Cannot access API %s: %s" % (self, e), file=sys.stderr)
            if print_error:
                print_exc(file=sys.stderr)
        return tabs

    def list_tabs(self, args):
        num_tabs = MAX_NUMBER_OF_TABS
        if len(args) > 0:
            num_tabs = int(args[0])

        result = self._get('/list_tabs')
        lines = []
        for line in result.splitlines()[:num_tabs]:
            lines.append(line)
        return self.prefix_tabs(lines)

    def list_tabs_safe(self, args, print_error=False):
        args = args or []
        tabs = []
        try:
            tabs = self.list_tabs(args)
        except ValueError as e:
            print("Cannot decode JSON: %s: %s" % (self, e), file=sys.stderr)
            if print_error:
                print_exc(file=sys.stderr)
        except URLError as e:
            print("Cannot access API %s: %s" % (self, e), file=sys.stderr)
            if print_error:
                print_exc(file=sys.stderr)
        return tabs

    def move_tabs(self, args):
        logger.info('SENDING MOVE COMMANDS: %s', args)
        commands = ','.join(
            '%s %s %s' % (tab_id, window_id, new_index)
            for tab_id, window_id, new_index in args)
        return self._get('/move_tabs/%s' % quote_plus(commands))

    def open_urls(self, urls, window_id=None):
        data = '\n'.join(urls)
        logger.info('SingleMediatorAPI: open_urls: %s', urls)
        files = {'urls': data}
        ids = self._post('/open_urls'
                         if window_id is None
                         else ('/open_urls/%s' % window_id),
                         files)
        return self.prefix_tabs(ids.splitlines())

    def update_tabs(self, updates):
        logger.info('SingleMediatorAPI: update_tabs: %s', updates)
        files = {'updates': dumps(updates)}
        ids = self._post('/update_tabs', files)
        return self.prefix_tabs(ids.splitlines())

    def get_words(self, tab_ids, match_regex, join_with):
        words = set()
        match_regex = encode_query(match_regex)
        join_with = encode_query(join_with)

        for tab_id in tab_ids:
            prefix, _window_id, tab_id = tab_id.split('.')
            if prefix + '.' != self._prefix:
                continue

            logger.info(
                'SingleMediatorAPI: get_words: %s, match_regex: %s, join_with: %s',
                tab_id, match_regex, join_with)
            words |= set(self._get(
                '/get_words/%s?match_regex=%s&join_with=%s' % (tab_id, match_regex, join_with)
            ).splitlines())

        if not tab_ids:
            words = set(self._get(
                '/get_words?match_regex=%s&join_with=%s' % (match_regex, join_with)
            ).splitlines())

        return sorted(list(words))

    def get_text_or_html(self, command, args, delimiter_regex, replace_with):
        num_tabs = MAX_NUMBER_OF_TABS
        if len(args) > 0:
            num_tabs = int(args[0])

        result = self._get(
            '/%s?delimiter_regex=%s&replace_with=%s' % (
                command,
                encode_query(delimiter_regex),
                encode_query(replace_with),
            ),
        )
        lines = []
        for line in result.splitlines()[:num_tabs]:
            lines.append(line)
        return self.prefix_tabs(lines)

    def get_text(self, args, delimiter_regex, replace_with):
        return self.get_text_or_html('get_text', args, delimiter_regex, replace_with)

    def get_html(self, args, delimiter_regex, replace_with):
        return self.get_text_or_html('get_html', args, delimiter_regex, replace_with)

    def shutdown(self):
        return self._get('/shutdown')

    def _get(self, path, data=None):
        return self._client.get(path, data)

    def _post(self, path, files=None):
        return self._client.post(path, files)


def api_must_ready(port: int, browser: str,
                   prefix='a',
                   client_timeout: float = 0.1,
                   startup_timeout: float = 1.0) -> SingleMediatorAPI:
    client = HttpClient(http_iface(), port, timeout=client_timeout)
    api = SingleMediatorAPI(prefix=prefix, port=port, startup_timeout=startup_timeout, client=client)
    assert api.browser == browser
    return api


def int_tab_id(tab_id: str) -> int:
    """Convert from str(b.20.123) to int(123)"""
    return int(tab_id.split('.')[-1])


class MultipleMediatorsAPI(object):
    """
    This API is designed to work with multiple mediators.
    """

    def __init__(self, apis):
        self._apis = apis

    @property
    def ready_apis(self):
        return [api for api in self._apis if api.ready]

    def close_tabs(self, args):
        for api in self._apis:
            api.close_tabs(args)

    def activate_tab(self, args: List[str], focused: bool):
        if len(args) == 0:
            print('Usage: brotab_client.py activate_tab [--focused] <#tab>')
            return 2

        for api in self._apis:
            api.activate_tab(args, focused)

    def get_active_tabs(self, args):
        return [api.get_active_tabs(args) for api in self._apis]

    def query_tabs(self, args, print_error=False):
        functions = [partial(api.query_tabs_safe, args, print_error)
                     for api in self.ready_apis]
        if not functions:
            return []
        tabs = sum(call_parallel(functions), [])
        return tabs

    def list_tabs(self, args, print_error=False):
        functions = [partial(api.list_tabs_safe, args, print_error)
                     for api in self.ready_apis]
        if not functions:
            return []
        tabs = sum(call_parallel(functions), [])
        return tabs

    def _move_tabs_if_changed(self, api, tabs_before, tabs_after):
        delete_commands, move_commands, update_commands = infer_all_commands(
            parse_tab_lines(tabs_before),
            parse_tab_lines(tabs_after))

        if delete_commands:
            print('DELETE', delete_commands)
            api.close_tabs(delete_commands)

        if move_commands:
            print('MOVE', move_commands)
            api.move_tabs(move_commands)

        if update_commands:
            print('UPDATE', update_commands)
            api.update_tabs(update_commands)

    def update_tabs(self, all_updates):
        results = []
        for api in self._apis:
            updates = [deepcopy(u) for u in all_updates if api.prefix_match(u['tab_id'])]
            for u in updates:
                u['tab_id'] = int_tab_id(u['tab_id'])
            results.extend(api.update_tabs(updates))
        return results

    def move_tabs(self, args):
        """
        This command allows closing tabs and move them around.

        It lists current tabs, opens an editor, and when editor is done, it
        detects which tabs where deleted and which where moved. It closes/
        removes tabs, and moves the rest accordingly.

        Alg:
        1. find maximum sequence of ordered tabs in the output
        2. take another tab from the input,
            - find a position in the output where to put that new tab,
              using binary search
            - insert that tab
        3. continue until no input tabs out of order are left
        """
        tabs_before = self.list_tabs(args, print_error=True)
        tabs_after = edit_tabs_in_editor(tabs_before)
        if tabs_after is None:
            return

        for api in self._apis:
            self._move_tabs_if_changed(
                api,
                api.filter_tabs(tabs_before),
                api.filter_tabs(tabs_after))

    def _get_api_by_prefix(self, prefix):
        for api in self._apis:
            if api._prefix == prefix:
                return api
        raise ValueError('No such client with prefix "%s"' % prefix)

    def open_urls(self, urls, prefix, window_id=None):
        assert len(self._apis) > 0, \
            'There should be at least one client connected: %s' % self._apis
        # client = self._apis[0]
        client = self._get_api_by_prefix(prefix)
        return client.open_urls(urls, window_id)

    def get_words(self, tab_ids, match_regex, join_with):
        words = set()
        import time
        for api in self.ready_apis:
            start = time.time()
            words |= set(api.get_words(tab_ids, match_regex, join_with))
            delta = time.time() - start
            # print('DELTA', delta, file=sys.stderr)
        return sorted(list(words))

    def _get_text_or_html(self, api, getter, args, delimiter_regex, replace_with):
        result = []
        try:
            import time
            start = time.time()
            result = getter(args, delimiter_regex, replace_with)
            delta = time.time() - start
            logger.info('get text/html (single client) took %s', delta)
        except ValueError as e:
            print("Cannot decode JSON: %s: %s" % (api, e), file=sys.stderr)
            logger.error("Cannot decode JSON: %s: %s" % (api, e))
        except URLError as e:
            print("Cannot access API %s: %s" % (api, e), file=sys.stderr)
            logger.error("Cannot access API %s: %s" % (api, e))
        except Exception as e:
            logger.error("Unknown exception: %s %s" % (api, e))
        return result

    def get_text(self, args, delimiter_regex, replace_with):
        tabs = []
        for api in self.ready_apis:
            tabs.extend(self._get_text_or_html(api, api.get_text, args,
                                               delimiter_regex, replace_with))
        return tabs

    def get_html(self, args, delimiter_regex, replace_with):
        tabs = []
        for api in self.ready_apis:
            tabs.extend(self._get_text_or_html(api, api.get_html, args,
                                               delimiter_regex, replace_with))
        return tabs
