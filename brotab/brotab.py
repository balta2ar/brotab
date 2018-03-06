#!/usr/bin/env python3

"""
This is a browser tab client. It allows listing, closing and creating
tabs in browsers from command line. Currently Firefox and Chrome are
supported.

To enable RPC in Chrome, run it as follows:

    chromium-browser --remote-debugging-port=9222 &!

To enable RPC in Firefox, install Mozrepl plugin:

    https://addons.mozilla.org/en-US/firefox/addon/mozrepl/
    https://github.com/bard/mozrepl/wiki

    Change port to 4242, and tick Tools -> MozRepl -> Activate on startup

Todo:
    [_] add rt-browsers support for Chromium (grab tabs from from database)
    [_] add rt-browsers-history to grab rt tickets from browser history

News:

    Starting from Firefox 55 mozrepl is not working anymore. Even worse, they
    guarantee that since Firefox 57 extensions that have not transitioned to
    WebExtensions technology will stop working. I need to find a replacement
    for mozrepl. As I need only a limited set of its potential functionality,
    implementing my own extension sounds like a viable idea. Two things are
    required:

        0. extensions setup basics:

        https://developer.mozilla.org/en-US/Add-ons/WebExtensions/What_are_WebExtensions

        1. tabs api:

        https://developer.mozilla.org/en-US/Add-ons/WebExtensions/API/tabs
        https://developer.mozilla.org/en-US/Add-ons/WebExtensions/API/tabs/query
        https://github.com/mdn/webextensions-examples/blob/master/tabs-tabs-tabs/tabs.js

        2. native messaging:

        https://developer.mozilla.org/en-US/Add-ons/WebExtensions/Native_messaging
        https://developer.mozilla.org/en-US/Add-ons/WebExtensions/manifest.json/permissions
        https://github.com/mdn/webextensions-examples/tree/master/native-messaging

"""

import os
import sys
import logging
from string import ascii_lowercase
from argparse import ArgumentParser
from functools import partial
from itertools import chain
from getpass import getuser
from json import loads
from telnetlib import Telnet
# from json import dumps
from urllib.parse import quote_plus
from traceback import print_exc

import requests

from brotab.io import edit_tabs_in_editor
from brotab.io import is_port_accepting_connections
from brotab.operations import infer_delete_and_move_commands
from brotab.tab import parse_tab_lines
from brotab.utils import split_tab_ids
from brotab.io import read_stdin


# from pprint import pprint

MAX_NUMBER_OF_TABS = 1000
MIN_MEDIATOR_PORT = 4625
MAX_MEDIATOR_PORT = MIN_MEDIATOR_PORT + 10

FORMAT = '%(asctime)-15s %(levelname)-10s %(message)s'
logging.basicConfig(
    format=FORMAT,
    filename='/tmp/brotab.log',
    level=logging.DEBUG)
logger = logging.getLogger('brotab')
logger.info('Logger has been created')


class ChromeAPI(object):
    BROWSER_PREFIX = 'c.'

    def __init__(self, host='localhost', port=9222):
        self._host = host
        self._port = port

    def _get(self, path):
        return requests.get('http://%s:%s%s' % (self._host, self._port, path))

    def filter_tabs(self, tabs):
        return [tab[len(ChromeAPI.BROWSER_PREFIX):] for tab in tabs
                if tab.startswith(ChromeAPI.BROWSER_PREFIX)]

    def _list_tabs(self, num_tabs):
        response = self._get('/json')
        result = loads(response.text)
        result = [tab for tab in result if tab['type'] == 'page']
        return result[:num_tabs]

    def close_tabs(self, args):
        current_tabs = self._list_tabs(MAX_NUMBER_OF_TABS)
        for tab in self.filter_tabs(args):
            tab_id = current_tabs[int(tab)]['id']
            self._get('/json/close/%s' % tab_id)

    def activate_tab(self, args):
        args = self.filter_tabs(args)
        if len(args) == 0:
            return

        tab = args[0]
        current_tabs = self._list_tabs(MAX_NUMBER_OF_TABS)
        tab_id = current_tabs[int(tab)]['id']
        self._get('/json/activate/%s' % tab_id)

    def new_tab(self, args):
        if args[0] != ChromeAPI.BROWSER_PREFIX:
            return

        query = ' '.join(args[1:])
        url = "https://www.google.com/search?q=%s" % quote_plus(query)
        self._get('/json/new?%s' % url)

    def list_tabs(self, args):
        num_tabs = MAX_NUMBER_OF_TABS
        if len(args) > 0:
            num_tabs = int(args[0])

        lines = []
        for i, tab in enumerate(self._list_tabs(num_tabs)):
            line = '%s%s\t%s\t%s' % (ChromeAPI.BROWSER_PREFIX, i,
                                     tab['title'], tab['url'])
            print(line)
            lines.append(line)
        return lines


class Mozrepl(object):
    LOAD_CODE = 'repl.load("file:///home/%s/rc.arch/bz/.config/mozrepl/mozrepl.js");' % getuser()

    def __init__(self, ip="127.0.0.1", port=4242):
        self.ip = ip
        self.port = port
        self.prompt = b"repl>"

    def __enter__(self):
        self.t = Telnet(self.ip, self.port)

        while True:
            index, match, text = self.t.expect([r'.*\n',  # match greeting line
                                                r'repl\d+>'],  # match repl line
                                               1)
            if text.startswith('repl'):
                self.prompt = text
                self.t.read_very_eager()
                break
        return self

    def __exit__(self, type, value, traceback):
        self.t.close()
        del self.t

    def js(self, command):
        command = '%s %s' % (Mozrepl.LOAD_CODE, command)
        # print('executing', command)
        self.t.write(('%s\n' % command).encode('utf8'))
        result = self.t.read_until(self.prompt).decode('utf8')
        result = result.splitlines()[0]
        result = result[1:-1]
        # print(result)
        return result


# class FirefoxAPI(object):
#     """
#     This API uses mozrepl plugin which does not work since Firefox 55. Thus
#     this API is deprecated and is not used.
#     """
#     BROWSER_PREFIX = 'f.'
#
#     def filter_tabs(self, tabs):
#         return [tab[len(FirefoxAPI.BROWSER_PREFIX):] for tab in tabs
#                 if tab.startswith(FirefoxAPI.BROWSER_PREFIX)]
#
#     def close_tabs(self, args):
#         with Mozrepl() as mozrepl:
#             tabs = ' '.join(self.filter_tabs(args))
#             result = mozrepl.js('close_tabs("%s");' % tabs)
#             result = loads(result)
#
#     def activate_tab(self, args):
#         args = self.filter_tabs(args)
#         if len(args) == 0:
#             return
#
#         strWindowTab = args[0]
#         with Mozrepl() as mozrepl:
#             result = mozrepl.js('activate_tab("%s");' % strWindowTab)
#             result = loads(result)
#
#     def new_tab(self, args):
#         if args[0] != FirefoxAPI.BROWSER_PREFIX:
#             return 2
#
#         query = ' '.join(args[1:])
#         with Mozrepl() as mozrepl:
#             result = mozrepl.js(
#                 'new_tab("https://www.google.com/search?q=%s", true);' % quote_plus(query))
#             result = loads(result)
#
#     def list_tabs(self, args):
#         num_tabs = MAX_NUMBER_OF_TABS
#         if len(args) > 0:
#             num_tabs = int(args[0])
#
#         with Mozrepl() as mozrepl:
#             result = loads(mozrepl.js('list_tabs(%d);' % num_tabs))
#             lines = []
#             for tab in result:
#                 line = '%s%s.%s\t%s\t%s\n' % (FirefoxAPI.BROWSER_PREFIX,
#                                               tab['windowId'], tab['tabId'],
#                                               tab['title'], tab['url'])
#                 line = line.encode('utf8')
#                 lines.append(line)
#             sys.stdout.writelines(lines)
#         return lines
#
#     def move_tabs(self, args):
#         args = self.filter_tabs(args)
#         if len(args) == 0:
#             return
#
#         pass


class FirefoxMediatorAPI(object):
    # BROWSER_PREFIX = 'f.'

    def __init__(self, prefix, host='localhost', port=4625):
        self._prefix = '%s.' % prefix
        self._host = host
        self._port = port

    def prefix_tabs(self, tabs):
        return ['%s%s' % (self._prefix, tab) for tab in tabs]

    def unprefix_tabs(self, tabs):
        N = len(self._prefix)
        return [tab[N:] if tab.startswith(self._prefix) else tab for tab in tabs]

    def filter_tabs(self, tabs):
        # N = len(self._prefix)
        # return [tab[N:] for tab in tabs
        return [tab for tab in tabs
                if tab.startswith(self._prefix)]

    def _split_tabs(self, tabs):
        return [tab.split('.') for tab in tabs]

    def close_tabs(self, args):
        # tabs = ','.join(self.filter_tabs(args))
        tabs = ','.join(tab_id for _prefix, _window_id, tab_id in self._split_tabs(args))
        self._get('/close_tabs/%s' % tabs)

    def activate_tab(self, args):
        # args = self.filter_tabs(args)
        if len(args) == 0:
            return

        strWindowTab = args[0]
        prefix, window_id, tab_id = strWindowTab.split('.')
        self._get('/activate_tab/%s' % tab_id)
        #self._get('/activate_tab/%s' % strWindowTab)

    def new_tab(self, args):
        if args[0] != self._prefix:
            return 2

        query = ' '.join(args[1:])
        self._get('/new_tab/%s' % query)

    def list_tabs(self, args):
        num_tabs = MAX_NUMBER_OF_TABS
        if len(args) > 0:
            num_tabs = int(args[0])

        result = self._get('/list_tabs')
        lines = []
        for line in result.text.splitlines()[:num_tabs]:
        #for line in result.text.split('\n')[:num_tabs]:
            # line = '%s%s' % (self._prefix, line)
            # print(line)
            lines.append(line)
        return self.prefix_tabs(lines)

    def move_tabs(self, args):
        logger.info('SENDING MOVE COMMANDS: %s', args)
        commands = ','.join(
            '%s %s %s' % (tab_id, window_id, new_index)
            for tab_id, window_id, new_index in args)
        self._get('/move_tabs/%s' % commands)

    def open_urls(self, args):
        data = '\n'.join(args)
        logger.info('FirefoxMediatorAPI: open_urls: %s', data)
        files = {'urls': data}
        self._post('/open_urls', files)

    def get_words(self, tab_ids):
        words = set()

        for tab_id in tab_ids:
            prefix, _window_id, tab_id = tab_id.split('.')
            if prefix + '.' != self._prefix:
                continue

            logger.info('FirefoxMediatorAPI: get_words: %s', tab_id)
            words |= set(self._get('/get_words/%s' % tab_id).text.splitlines())

        if not tab_ids:
            words = set(self._get('/get_words').text.splitlines())

        return sorted(list(words))

    def _get(self, path, data=None):
        return requests.get('http://%s:%s%s' % (self._host, self._port, path),
                            data=data)

    def _post(self, path, files=None):
        return requests.post('http://%s:%s%s' % (self._host, self._port, path),
                             files=files)


class BrowserAPI(object):
    def __init__(self, apis):
        self._apis = apis

    def close_tabs(self, args):
        # if len(args) == 0:
        #     print('Usage: brotab_client.py close_tabs <#tab ...>')
        #     return 2

        for api in self._apis:
            api.close_tabs(args)

    def activate_tab(self, args):
        if len(args) == 0:
            print('Usage: brotab_client.py activate_tab <#tab>')
            return 2

        for api in self._apis:
            api.activate_tab(args)

    def new_tab(self, args):
        if len(args) <= 1:
            print('Usage: brotab_client.py new_tab <f.|c.> <search query>')
            return 2

        for api in self._apis:
            api.new_tab(args)

    def list_tabs(self, args):
        # exit_code = 0
        tabs = []
        for api in self._apis:
            try:
                tabs.extend(api.list_tabs(args))
            except ValueError as e:
                print("Cannot decode JSON: %s: %s" % (api, e), file=sys.stderr)
                # exit_code = 1
            except requests.exceptions.ConnectionError as e:
                print("Cannot access API %s: %s" % (api, e), file=sys.stderr)
                # exit_code = 1
        return tabs
        #return exit_code

    def _safe_list_tabs(self, api):
        try:
            return api.list_tabs([])
        except ValueError as e:
            print("Cannot decode JSON: %s: %s" % (api, e), file=sys.stderr)
            print_exc(file=sys.stderr)
        except requests.exceptions.ConnectionError as e:
            print("Cannot access API %s: %s" % (api, e), file=sys.stderr)
            print_exc(file=sys.stderr)
        return []

    def _move_tabs_if_changed(self, api, tabs_before, tabs_after):
        # if tabs_after is None:
            # return

        delete_commands, move_commands = infer_delete_and_move_commands(
            parse_tab_lines(tabs_before),
            parse_tab_lines(tabs_after))
        print('DELETE COMMANDS', delete_commands)

        if delete_commands:
            api.close_tabs(delete_commands)
            # raise RuntimeError('DELETE COMMANDS ARE NOT SUPPORTED YET')

        print('MOVE COMMANDS', move_commands)
        api.move_tabs(move_commands)

    def move_tabs(self, args):
        """
        This command allows to close tabs and move them around.

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
        tabs_before = list(chain.from_iterable(map(self._safe_list_tabs, self._apis)))
        tabs_after = edit_tabs_in_editor(tabs_before)
        # print('TABS BEFORE', tabs_before)
        # print('TABS AFTER', tabs_after)
        if tabs_after is None:
            return

        for api in self._apis:
            self._move_tabs_if_changed(
                api,
                api.filter_tabs(tabs_before),
                api.filter_tabs(tabs_after))
        # print('MOVING END')

    def open_urls(self, args):
        # Send open urls only to the first client
        assert len(self._apis) > 0, \
            'There should be at least one client connected: %s' % self._apis
        client = self._apis[0]
        client.open_urls(args)

    def get_words(self, tab_ids):
        words = set()
        for api in self._apis:
            words |= set(api.get_words(tab_ids))
        return sorted(list(words))


def create_clients():
    ports = range(MIN_MEDIATOR_PORT, MAX_MEDIATOR_PORT)
    result = [FirefoxMediatorAPI(prefix, port=port)
              for prefix, port in zip(ascii_lowercase, ports)
              if is_port_accepting_connections(port)]
    logger.info('Created clients: %s', result)
    return result


def move_tabs(args):
    logger.info('Moving tabs')
    api = BrowserAPI(create_clients())
    api.move_tabs(args)


def list_tabs(args):
    """
    Use this to show duplicates:
        bt list | sort -k3 | uniq -f2 -D | cut -f1 | bt close
    """
    logger.info('Listing tabs')
    api = BrowserAPI(create_clients())
    tabs = api.list_tabs([])
    print('\n'.join(tabs))


def close_tabs(args):
    #urls = [line.strip() for line in sys.stdin.readlines()]

    # Try stdin if arguments are empty
    tab_ids = args.tab_ids
    #print(read_stdin())
    if len(args.tab_ids) == 0:
        tab_ids = split_tab_ids(read_stdin().strip())

    logger.info('Closing tabs: %s', tab_ids)
    #api = BrowserAPI([FirefoxMediatorAPI('f')])
    api = BrowserAPI(create_clients())
    tabs = api.close_tabs(tab_ids)


def activate_tab(args):
    logger.info('Activating tab: %s', args.tab_id)
    #api = BrowserAPI([FirefoxMediatorAPI('f')])
    api = BrowserAPI(create_clients())
    api.activate_tab(args.tab_id)


def new_search():
    pass


def open_urls(args):
    urls = [line.strip() for line in sys.stdin.readlines()]
    logger.info('Openning URLs from stdin: %s', urls)
    api = BrowserAPI(create_clients())
    api.open_urls(urls)


def get_words(args):
    # return tab.execute({javascript: "
    # [...new Set(document.body.innerText.match(/\w+/g))].sort().join('\n');
    # "})
    logger.info('Get words from tabs: %s', args.tab_ids)
    api = BrowserAPI(create_clients())
    words = api.get_words(args.tab_ids)
    print('\n'.join(words))


def executejs(args):
    pass


def no_command(parser, args):
    print('No command has been specified')
    parser.print_help()
    return 1


def parse_args(args):
    parser = ArgumentParser()

    subparsers = parser.add_subparsers()
    parser.set_defaults(func=partial(no_command, parser))

    parser_move_tabs = subparsers.add_parser('move')
    parser_move_tabs.set_defaults(func=move_tabs)

    parser_list_tabs = subparsers.add_parser('list')
    parser_list_tabs.set_defaults(func=list_tabs)

    parser_close_tabs = subparsers.add_parser('close')
    parser_close_tabs.set_defaults(func=close_tabs)
    parser_close_tabs.add_argument('tab_ids', type=str, nargs='*',
        help='Tab IDs to close')

    parser_activate_tab = subparsers.add_parser('activate')
    parser_activate_tab.set_defaults(func=activate_tab)
    parser_activate_tab.add_argument('tab_id', type=str, nargs=1,
        help='Tab ID to activate')

    parser_new_search = subparsers.add_parser('search')
    parser_new_search.set_defaults(func=new_search)
    parser_new_search.add_argument('words', type=str, nargs='+',
        help='Search query')

    parser_open_urls = subparsers.add_parser('open')
    parser_open_urls.set_defaults(func=open_urls)

    parser_get_words = subparsers.add_parser('words')
    parser_get_words.set_defaults(func=get_words)
    parser_get_words.add_argument('tab_ids', type=str, nargs='*',
        help='Tab IDs to get words from')

    return parser.parse_args(args)


def run_commands(args):
    args = parse_args(args)
    return args.func(args)

    command = args[0]
    rest = args[1:]

    #api = BrowserAPI([FirefoxMediatorAPI(), ChromeAPI()])
    api = BrowserAPI([FirefoxMediatorAPI('f')])

    if command == 'move_tabs':
        return api.move_tabs(rest)
    if command == 'list_tabs':
        return api.list_tabs(rest)
    if command == 'close_tabs':
        return api.close_tabs(rest)
    if command == 'activate_tab':
        return api.activate_tab(rest)
    if command == 'new_tab':
        return api.new_tab(rest)
    if command == 'open_urls':
        raise NotImplementedError()
        # return api.new_tab(rest)
    else:
        print('Unknown command: %s' % command)
        return 2

    return 0


def main():
    # if len(sys.argv) == 1:
    #     print('Usage: brotab_client.py <list_tabs | ...>')
    #     exit(1)
    # exit(run_commands(sys.argv[1:]))
    exit(run_commands(sys.argv[1:]))


if __name__ == '__main__':
    main()
