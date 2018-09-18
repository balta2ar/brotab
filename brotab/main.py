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
import re
import io
import sys
import shutil
import logging
from string import ascii_lowercase
from argparse import ArgumentParser
from functools import partial
from itertools import chain, groupby
from traceback import print_exc
from urllib.request import Request, urlopen
from urllib.error import URLError

from brotab.inout import edit_tabs_in_editor
from brotab.inout import is_port_accepting_connections
from brotab.inout import read_stdin
from brotab.inout import MultiPartForm
from brotab.parallel import call_parallel
from brotab.operations import infer_delete_and_move_commands
from brotab.tab import parse_tab_lines
from brotab.utils import split_tab_ids
from brotab.search.query import query
from brotab.search.index import index


# from pprint import pprint

MAX_NUMBER_OF_TABS = 1000
MIN_MEDIATOR_PORT = 4625
MAX_MEDIATOR_PORT = MIN_MEDIATOR_PORT + 10
HTTP_TIMEOUT = 2.0

FORMAT = '%(asctime)-15s %(levelname)-10s %(message)s'
logging.basicConfig(
    format=FORMAT,
    filename='/tmp/brotab.log',
    level=logging.DEBUG)
logger = logging.getLogger('brotab')
logger.info('Logger has been created')


class FirefoxMediatorAPI(object):
    # BROWSER_PREFIX = 'f.'

    def __init__(self, prefix, host='localhost', port=4625):
        self._prefix = '%s.' % prefix
        self._host = host
        self._port = port
        self._pid = self._get_pid()
        self._browser = self._get_browser()

    def __str__(self):
        return '%s\t%s:%s\t%s\t%s' % (
            self._prefix, self._host, self._port, self._pid, self._browser)

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

    def _get_pid(self):
        """Get process ID from the mediator."""
        return int(self._get('/get_pid'))

    def _get_browser(self):
        """Get browser name from the mediator."""
        return self._get('/get_browser')

    def close_tabs(self, args):
        # tabs = ','.join(self.filter_tabs(args))
        tabs = ','.join(tab_id for _prefix, _window_id,
                        tab_id in self._split_tabs(args))
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
        for line in result.splitlines()[:num_tabs]:
            # for line in result.split('\n')[:num_tabs]:
            # line = '%s%s' % (self._prefix, line)
            # print(line)
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
        self._get('/move_tabs/%s' % commands)

    def open_urls(self, urls, window_id=None):
        data = '\n'.join(urls)
        logger.info('FirefoxMediatorAPI: open_urls: %s', data)
        files = {'urls': data}
        if window_id is not None:
            files['window_id'] = window_id
        self._post('/open_urls', files)

    def get_words(self, tab_ids):
        words = set()

        for tab_id in tab_ids:
            prefix, _window_id, tab_id = tab_id.split('.')
            if prefix + '.' != self._prefix:
                continue

            logger.info('FirefoxMediatorAPI: get_words: %s', tab_id)
            words |= set(self._get('/get_words/%s' % tab_id).splitlines())

        if not tab_ids:
            words = set(self._get('/get_words').splitlines())

        return sorted(list(words))

    def get_text(self, args):
        num_tabs = MAX_NUMBER_OF_TABS
        if len(args) > 0:
            num_tabs = int(args[0])

        result = self._get('/get_text')
        lines = []
        for line in result.splitlines()[:num_tabs]:
            lines.append(line)
        return self.prefix_tabs(lines)

    def _get(self, path, data=None):
        url = 'http://%s:%s%s' % (self._host, self._port, path)
        logger.info('GET %s' % url)
        if data is not None:
            data = data.encode('utf8')
        request = Request(url=url, data=data, method='GET')

        with urlopen(request, timeout=HTTP_TIMEOUT) as response:
            return response.read().decode('utf8')

    def _post(self, path, files=None):
        url = 'http://%s:%s%s' % (self._host, self._port, path)
        logger.info('POST %s' % url)
        form = MultiPartForm()
        for filename, content in files.items():
            form.add_file(filename, filename,
                          io.BytesIO(content.encode('utf8')))

        data = bytes(form)
        request = Request(url=url, data=data, method='POST')
        request.add_header('Content-Type', form.get_content_type())
        request.add_header('Content-Length', len(data))

        with urlopen(request, timeout=HTTP_TIMEOUT) as response:
            return response.read().decode('utf8')


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

    def list_tabs(self, args, print_error=False):
        functions = [partial(api.list_tabs_safe, args, print_error)
                     for api in self._apis]
        tabs = sum(call_parallel(functions), [])
        return tabs

    def _move_tabs_if_changed(self, api, tabs_before, tabs_after):
        delete_commands, move_commands = infer_delete_and_move_commands(
            parse_tab_lines(tabs_before),
            parse_tab_lines(tabs_after))

        if delete_commands:
            api.close_tabs(delete_commands)

        if move_commands:
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
        client.open_urls(urls, window_id)

    def get_words(self, tab_ids):
        words = set()
        import time
        for api in self._apis:
            start = time.time()
            words |= set(api.get_words(tab_ids))
            delta = time.time() - start
            #print('DELTA', delta, file=sys.stderr)
        return sorted(list(words))

    def get_text(self, args):
        tabs = []
        for api in self._apis:
            try:
                import time
                start = time.time()
                tabs.extend(api.get_text(args))
                delta = time.time() - start
                logger.info('get text (single client) took %s', delta)
            except ValueError as e:
                print("Cannot decode JSON: %s: %s" % (api, e), file=sys.stderr)
            except URLError as e:
                print("Cannot access API %s: %s" % (api, e), file=sys.stderr)
        return tabs


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
    api.move_tabs([])


def list_tabs(args):
    """
    Use this to show duplicates:
        bt list | sort -k3 | uniq -f2 -D | cut -f1 | bt close
    """
    logger.info('Listing tabs')
    api = BrowserAPI(create_clients())
    tabs = api.list_tabs([])
    #print('\n'.join([tab.encode('utf8') for tab in tabs]))
    # print(u'\n'.join(tabs).encode('utf8'))
    # print(u'\n'.join(tabs))

    message = '\n'.join(tabs) + '\n'
    sys.stdout.buffer.write(message.encode('utf8'))


def close_tabs(args):
    #urls = [line.strip() for line in sys.stdin.readlines()]

    # Try stdin if arguments are empty
    tab_ids = args.tab_ids
    # print(read_stdin())
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


def show_active_tab(args):
    logger.info('Showing active tabs: %s', args)
    #api = BrowserAPI([FirefoxMediatorAPI('f')])
    api = BrowserAPI(create_clients())
    # api.activate_tab(args.tab_id)


def search_tabs(args):
    for result in query(args.sqlite, args.query):
        print('\t'.join([result.tab_id, result.title, result.snippet]))


def index_tabs(args):
    if args.tsv is None:
        args.tsv = '/tmp/tabs.tsv'
        args.cleanup = True
        logger.info(
            'index_tabs: retrieving tabs from browser into file %s', args.tsv)
        import time
        start = time.time()
        get_text(args)
        delta = time.time() - start
        logger.info('getting text took %s', delta)

    start = time.time()
    index(args.sqlite, args.tsv)
    delta = time.time() - start
    logger.info('sqlite create took %s', delta)


def open_urls(args):
    """
    curl -X POST 'http://localhost:4626/open_urls' -F 'urls=@urls.txt'
    curl -X POST 'http://localhost:4627/open_urls' -F 'urls=@urls.txt' -F 'window_id=749'

    where urls.txt containe one url per line (not JSON)
    """
    prefix, window_id = None, None
    try:
        prefix, window_id = args.prefix_window_id.split('.')
        prefix += '.'
    except ValueError:
        prefix = args.prefix_window_id

    urls = [line.strip() for line in sys.stdin.readlines()]
    logger.info('Openning URLs from stdin, prefix "%s", window_id "%s": %s',
                prefix, window_id, urls)
    api = BrowserAPI(create_clients())
    api.open_urls(urls, prefix, window_id)


def get_words(args):
    # return tab.execute({javascript: "
    # [...new Set(document.body.innerText.match(/\w+/g))].sort().join('\n');
    # "})
    import time
    start = time.time()
    logger.info('Get words from tabs: %s', args.tab_ids)
    api = BrowserAPI(create_clients())
    words = api.get_words(args.tab_ids)
    print('\n'.join(words))
    delta = time.time() - start
    #print('DELTA TOTAL', delta, file=sys.stderr)


def get_text(args):
    logger.info('Get text from tabs')
    api = BrowserAPI(create_clients())
    tabs = api.get_text([])

    if args.cleanup:
        pattern = re.compile(r'\s+')
        old_tabs = tabs
        tabs = []
        for line in old_tabs:
            tab_id, title, url, text = line.split('\t')
            text = re.sub(pattern, ' ', text)
            tabs.append('\t'.join([tab_id, title, url, text]))

    message = '\n'.join(tabs) + '\n'
    if args.tsv is None:
        sys.stdout.buffer.write(message.encode('utf8'))
    else:
        with open(args.tsv, 'w') as file_:
            file_.write(message)


def show_duplicates(args):
    # I'm not using uniq here because it's not easy to get duplicates
    # only by a single column. awk is much easier in this regard.
    #print('bt list | sort -k3 | uniq -f2 -D | cut -f1 | bt close')
    print("Show duplicates by Title:")
    print(
        "bt list | sort -k2 | awk -F$'\\t' '{ if (a[$2]++ > 0) print }' | cut -f1 | bt close")
    print("")
    print("Show duplicates by URL:")
    print(
        "bt list | sort -k3 | awk -F$'\\t' '{ if (a[$3]++ > 0) print }' | cut -f1 | bt close")


def _get_window_id(tab):
    ids, _title, _url = tab.split('\t')
    client_id, window_id, tab_id = ids.split('.')
    return '%s.%s' % (client_id, window_id)


def _print_available_windows(tabs):
    for key, group in groupby(sorted(tabs), _get_window_id):
        group = list(group)
        print('%s\t%s' % (key, len(group)))


def show_windows(args):
    logger.info('Showing windows')
    api = BrowserAPI(create_clients())
    tabs = api.list_tabs([])
    _print_available_windows(tabs)


def show_clients(args):
    logger.info('Showing clients')
    for client in create_clients():
        print(client)


def install_mediator(args):
    logger.info('Installing mediators')
    bt_mediator_path = shutil.which('bt_mediator')

    native_app_manifests = [
        ('mediator/firefox_mediator.json',
         '~/.mozilla/native-messaging-hosts/brotab_mediator.json'),
        ('mediator/chromium_mediator.json',
         '~/.config/chromium/NativeMessagingHosts/brotab_mediator.json'),
        ('mediator/chromium_mediator.json',
         '~/.config/google-chrome/NativeMessagingHosts/brotab_mediator.json'),
    ]

    from pkg_resources import resource_string
    for filename, destination in native_app_manifests:
        destination = os.path.expanduser(os.path.expandvars(destination))
        template = resource_string(__name__, filename).decode('utf8')
        manifest = template.replace(r'$PWD/brotab_mediator.py',
                                    bt_mediator_path)
        logger.info('Installing template %s into %s', filename, destination)
        print('Installing mediator manifest %s' % destination)

        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, 'w') as file_:
            file_.write(manifest)

    print('Link to Firefox extension: https://addons.mozilla.org/en-US/firefox/addon/brotab/')
    print('Link to Chrome (Chromium) extension: https://chrome.google.com/webstore/detail/brotab/mhpeahbikehnfkfnmopaigggliclhmnc/')


def executejs(args):
    pass


def no_command(parser, args):
    print('No command has been specified')
    parser.print_help()
    return 1


def parse_args(args):
    parser = ArgumentParser(
        description='''
        bt (brotab = Browser Tabs) is a command-line tool that helps you manage
        browser tabs. It can help you list, close, reorder, open and activate
        your tabs.
        ''')

    subparsers = parser.add_subparsers()
    parser.set_defaults(func=partial(no_command, parser))

    parser_move_tabs = subparsers.add_parser(
        'move',
        help='''
        move tabs around. This command lists available tabs and runs
        the editor. In the editor you can 1) reorder tabs -- tabs will
        be moved in the browser 2) delete tabs -- tabs will be closed
        3) change window ID of the tabs -- tabs will be moved to
        specified windows
        ''')
    parser_move_tabs.set_defaults(func=move_tabs)

    parser_list_tabs = subparsers.add_parser(
        'list',
        help='''
        list available tabs. The command will request all available clients
        (browser plugins, mediators), and will display browser tabs in the
        following format:
        "<prefix>.<window_id>.<tab_id><Tab>Page title<Tab>URL"
        ''')
    parser_list_tabs.set_defaults(func=list_tabs)

    parser_close_tabs = subparsers.add_parser(
        'close',
        help='''
        close specified tab IDs. Tab IDs should be in the following format:
        "<prefix>.<window_id>.<tab_id>". You can use "list" command to obtain
        tab IDs (first column)
        ''')
    parser_close_tabs.set_defaults(func=close_tabs)
    parser_close_tabs.add_argument('tab_ids', type=str, nargs='*',
                                   help='Tab IDs to close')

    parser_activate_tab = subparsers.add_parser(
        'activate',
        help='''
        activate given tab ID. Tab ID should be in the following format:
        "<prefix>.<window_id>.<tab_id>"
        ''')
    parser_activate_tab.set_defaults(func=activate_tab)
    parser_activate_tab.add_argument('tab_id', type=str, nargs=1,
                                     help='Tab ID to activate')

    parser_active_tab = subparsers.add_parser(
        'active',
        help='''
        display active tab for each client/window in the following format:
        "<prefix>.<window_id>.<tab_id>"
        ''')
    parser_active_tab.set_defaults(func=show_active_tab)

    parser_search_tabs = subparsers.add_parser(
        'search',
        help='''
        Search across your indexed tabs using sqlite fts5 plugin.
        ''')
    parser_search_tabs.set_defaults(func=search_tabs)
    parser_search_tabs.add_argument('--sqlite', type=str, default='/tmp/tabs.sqlite',
                                    help='sqlite DB filename')
    parser_search_tabs.add_argument('query', type=str, help='Search query')

    parser_index_tabs = subparsers.add_parser(
        'index',
        help='''
        Index the text from browser's tabs. Text is put into sqlite fts5 table.
        ''')
    parser_index_tabs.set_defaults(func=index_tabs)
    parser_index_tabs.add_argument('--sqlite', type=str, default='/tmp/tabs.sqlite',
                                   help='sqlite DB filename')
    parser_index_tabs.add_argument('--tsv', type=str, default=None,
                                   help='get text from tabs and index the results')

    parser_open_urls = subparsers.add_parser(
        'open',
        help='''
        open URLs from the stdin (one URL per line). One positional argument is
        required: <prefix>.<window_id> OR <client>. If window_id is not
        specified, URL will be opened in the active window of the specifed
        client
        ''')
    parser_open_urls.set_defaults(func=open_urls)
    parser_open_urls.add_argument(
        'prefix_window_id', type=str,
        help='Client prefix and window id, e.g. b.20')

    parser_get_words = subparsers.add_parser(
        'words',
        help='''
        show sorted unique words from all active tabs of all clients. This is
        a helper for webcomplete deoplete plugin that helps complete words
        from the browser
        ''')
    parser_get_words.set_defaults(func=get_words)
    parser_get_words.add_argument('tab_ids', type=str, nargs='*',
                                  help='Tab IDs to get words from')

    parser_get_text = subparsers.add_parser(
        'text',
        help='''
        show text form all tabs
        ''')
    parser_get_text.set_defaults(func=get_text)
    parser_get_text.add_argument('--tsv', type=str, default=None,
                                 help='tsv file to save results to')
    parser_get_text.add_argument('--cleanup', action='store_true', default=False,
                                 help='force removal of extra whitespace')

    parser_show_duplicates = subparsers.add_parser(
        'dup',
        help='''
        display reminder on how to show duplicate tabs using command-line tools
        ''')
    parser_show_duplicates.set_defaults(func=show_duplicates)

    parser_show_windows = subparsers.add_parser(
        'windows',
        help='''
        display available prefixes and window IDs, along with the number of
        tabs in every window
        ''')
    parser_show_windows.set_defaults(func=show_windows)

    parser_show_clients = subparsers.add_parser(
        'clients',
        help='''
        display available browser clients (mediators), their prefixes and
        address (host:port), native app PIDs, and browser names
        ''')
    parser_show_clients.set_defaults(func=show_clients)

    parser_install_mediator = subparsers.add_parser(
        'install',
        help='''
        configure browser settings to use bt mediator (native messaging app)
        ''')
    parser_install_mediator.set_defaults(func=install_mediator)

    return parser.parse_args(args)


def run_commands(args):
    args = parse_args(args)
    result = 0
    try:
        result = args.func(args)
    except BrokenPipeError:
        pass
    return result


def main():
    exit(run_commands(sys.argv[1:]))


if __name__ == '__main__':
    main()
