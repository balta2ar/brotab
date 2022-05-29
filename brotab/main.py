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
import sys
import time
from argparse import ArgumentParser
from functools import partial
from itertools import groupby
from json import loads
from string import ascii_lowercase
from typing import List
from typing import Tuple
from urllib.parse import quote_plus

from brotab.api import MultipleMediatorsAPI
from brotab.api import SingleMediatorAPI
from brotab.const import DEFAULT_GET_HTML_DELIMITER_REGEX
from brotab.const import DEFAULT_GET_HTML_REPLACE_WITH
from brotab.const import DEFAULT_GET_TEXT_DELIMITER_REGEX
from brotab.const import DEFAULT_GET_TEXT_REPLACE_WITH
from brotab.const import DEFAULT_GET_WORDS_JOIN_WITH
from brotab.const import DEFAULT_GET_WORDS_MATCH_REGEX
from brotab.inout import get_mediator_ports
from brotab.files import in_temp_dir
from brotab.inout import is_port_accepting_connections
from brotab.inout import marshal
from brotab.inout import read_stdin
from brotab.inout import read_stdin_lines
from brotab.inout import stdout_buffer_write
from brotab.mediator.log import brotab_logger
from brotab.operations import make_update
from brotab.platform import is_windows
from brotab.platform import make_windows_path_double_sep
from brotab.platform import register_native_manifest_windows_brave
from brotab.platform import register_native_manifest_windows_chrome
from brotab.platform import register_native_manifest_windows_firefox
from brotab.search.index import index
from brotab.search.query import query
from brotab.utils import get_file_size
from brotab.utils import split_tab_ids
from brotab.utils import which


def parse_target_hosts(target_hosts: str) -> Tuple[List[str], List[int]]:
    """
    Input: localhost:2000,127.0.0.1:3000
    Output: (['localhost', '127.0.0.1'], [2000, 3000])
    """
    hosts, ports = [], []
    for pair in target_hosts.split(','):
        host, port = pair.split(':')
        hosts.append(host)
        ports.append(int(port))
    return hosts, ports


def create_clients(target_hosts=None) -> List[SingleMediatorAPI]:
    if target_hosts is None:
        ports = list(get_mediator_ports())
        hosts = ['localhost'] * len(ports)
    else:
        hosts, ports = parse_target_hosts(target_hosts)

    result = [SingleMediatorAPI(prefix, host=host, port=port)
              for prefix, host, port in zip(ascii_lowercase, hosts, ports)
              if is_port_accepting_connections(port, host)]
    brotab_logger.info('Created clients: %s', result)
    return result


def parse_prefix_and_window_id(prefix_window_id):
    prefix, window_id = None, None
    try:
        prefix, window_id = prefix_window_id.split('.')
        prefix += '.'
        window_id = window_id or None
    except ValueError:
        prefix = prefix_window_id
        prefix += '' if prefix.endswith('.') else '.'

    return prefix, window_id


def move_tabs(args):
    brotab_logger.info('Moving tabs')
    api = MultipleMediatorsAPI(create_clients(args.target_hosts))
    api.move_tabs([])


def list_tabs(args):
    """
    Use this to show duplicates:
        bt list | sort -k3 | uniq -f2 -D | cut -f1 | bt close
    """
    brotab_logger.info('Listing tabs')
    api = MultipleMediatorsAPI(create_clients(args.target_hosts))
    tabs = api.list_tabs([])
    message = '\n'.join(tabs) + '\n'
    sys.stdout.buffer.write(message.encode('utf8'))


def close_tabs(args):
    # Try stdin if arguments are empty
    tab_ids = args.tab_ids
    if len(args.tab_ids) == 0:
        tab_ids = split_tab_ids(read_stdin().strip())

    brotab_logger.info('Closing tabs: %s', tab_ids)
    api = MultipleMediatorsAPI(create_clients(args.target_hosts))
    tabs = api.close_tabs(tab_ids)


def activate_tab(args):
    brotab_logger.info('Activating tab: %s', args.tab_id)
    api = MultipleMediatorsAPI(create_clients(args.target_hosts))
    api.activate_tab(args.tab_id, args.focused)


def show_active_tabs(args):
    brotab_logger.info('Showing active tabs: %s', args)
    apis = create_clients(args.target_hosts)
    for api in apis:
        tabs = api.get_active_tabs(args)
        for tab in tabs:
            print('%s\t%s' % (tab, api))


def search_tabs(args):
    for result in query(args.sqlite, args.query):
        print('\t'.join([result.tab_id, result.title, result.snippet]))


def query_tabs(args):
    brotab_logger.info('Querying tabs: %s', args)
    d = vars(args)
    if d['info'] is not None:
        queryInfo = d['info']
    else:
        queryInfo = {k: v for k, v in d.items()
                     if v is not None and k not in ['func', 'info', 'target_hosts']}
    api = MultipleMediatorsAPI(create_clients(args.target_hosts))
    for tab in api.query_tabs(queryInfo):
        print(tab)


def index_tabs(args):
    if args.tsv is None:
        args.tsv = in_temp_dir('tabs.tsv')
        args.cleanup = True
        brotab_logger.info(
            'index_tabs: retrieving tabs from browser into file %s', args.tsv)
        start = time.time()
        get_text(args)
        delta = time.time() - start
        brotab_logger.info('getting text took %s', delta)

    start = time.time()
    index(args.sqlite, args.tsv)
    delta = time.time() - start
    brotab_logger.info('sqlite create took %s, size %s',
                       delta, get_file_size(args.sqlite))


def new_tab(args):
    prefix, window_id = parse_prefix_and_window_id(args.prefix_window_id)
    search_query = ' '.join(args.query)
    brotab_logger.info('Opening search for "%s", prefix "%s", window_id "%s"',
                       search_query, prefix, window_id)
    url = "https://www.google.com/search?q=%s" % quote_plus(search_query)
    api = MultipleMediatorsAPI(create_clients(args.target_hosts))
    ids = api.open_urls([url], prefix, window_id)
    stdout_buffer_write(marshal(ids))


def open_urls(args):
    """
    curl -X POST 'http://localhost:4626/open_urls' -F 'urls=@urls.txt'
    curl -X POST 'http://localhost:4627/open_urls' -F 'urls=@urls.txt' -F 'window_id=749'

    where urls.txt contains one url per line (not JSON)
    """
    prefix, window_id = parse_prefix_and_window_id(args.prefix_window_id)
    urls = read_stdin_lines()
    brotab_logger.info('Opening URLs from stdin, prefix "%s", window_id "%s": %s',
                       prefix, window_id, urls)
    api = MultipleMediatorsAPI(create_clients(args.target_hosts))
    ids = api.open_urls(urls, prefix, window_id)
    stdout_buffer_write(marshal(ids))


def navigate_urls(args):
    """
    curl -X POST 'http://localhost:4626/update_tabs' --data '{"tab_id": 20, "properties": { "url": "https://www.google.com" }}'
    """
    raw = read_stdin(timeout=0.05)
    if raw:
        pairs = [x.strip().split('\t') for x in raw.splitlines()]
        updates = [make_update(tabId=tab_id, url=url) for tab_id, url in pairs]
    else:
        updates = [make_update(tabId=args.tab_id, url=args.url)]
    brotab_logger.info('Navigating: %s', updates)
    api = MultipleMediatorsAPI(create_clients(args.target_hosts))
    results = api.update_tabs(updates)
    stdout_buffer_write(marshal(results))


def update_tabs(args):
    """
    curl -X POST 'http://localhost:4626/update_tabs' --data '{"tab_id": 20, "properties": { "url": "https://www.google.com" }}'
    """
    raw = read_stdin(timeout=0.01).strip()
    if raw:
        updates = loads(raw)
    else:
        d = vars(args)
        if d['info'] is not None:
            updates = [d['info']]
        else:
            updates = {k: v for k, v in d.items()
                       if v is not None and k not in ['func', 'info', 'target_hosts']}
            if 'tabId' not in updates: raise ValueError('tabId is required')
            updates = [make_update(**updates)]
    brotab_logger.info('Updating tabs: %s', updates)
    api = MultipleMediatorsAPI(create_clients(args.target_hosts))
    results = api.update_tabs(updates)
    stdout_buffer_write(marshal(results))


def get_words(args):
    # return tab.execute({javascript: "
    # [...new Set(document.body.innerText.match(/\w+/g))].sort().join('\n');
    # "})
    start = time.time()
    brotab_logger.info('Get words from tabs: %s, match_regex=%s, join_with=%s',
                       args.tab_ids, args.match_regex, args.join_with)
    api = MultipleMediatorsAPI(create_clients(args.target_hosts))
    words = api.get_words(args.tab_ids, args.match_regex, args.join_with)
    print('\n'.join(words))
    delta = time.time() - start
    # print('DELTA TOTAL', delta, file=sys.stderr)


def get_text_or_html(getter, args):
    tabs = getter([], args.delimiter_regex, args.replace_with)
    re_match_tabs = re.compile('|'.join(['^%s\t' % tab for tab in args.tab_ids]))
    tabs = [tab for tab in tabs if re_match_tabs.match(tab)]

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
        stdout_buffer_write(message.encode('utf8'))
    else:
        with open(args.tsv, 'w', encoding='utf-8') as file_:
            file_.write(message)


def get_text(args):
    brotab_logger.info('Get text from tabs')
    api = MultipleMediatorsAPI(create_clients(args.target_hosts))
    return get_text_or_html(api.get_text, args)


def get_html(args):
    brotab_logger.info('Get html from tabs')
    api = MultipleMediatorsAPI(create_clients(args.target_hosts))
    return get_text_or_html(api.get_html, args)


def show_duplicates(args):
    # I'm not using uniq here because it's not easy to get duplicates
    # only by a single column. awk is much easier in this regard.
    # print('bt list | sort -k3 | uniq -f2 -D | cut -f1 | bt close')
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
    brotab_logger.info('Showing windows')
    api = MultipleMediatorsAPI(create_clients(args.target_hosts))
    tabs = api.list_tabs([])
    _print_available_windows(tabs)


def show_clients(args):
    brotab_logger.info('Showing clients')
    for client in create_clients(args.target_hosts):
        print(client)


def install_mediator(args):
    brotab_logger.info('Installing mediators')
    bt_mediator_path = which('bt_mediator')
    if is_windows():
        bt_mediator_path = make_windows_path_double_sep(bt_mediator_path)

    native_app_manifests = [
        ('mediator/firefox_mediator.json',
         '~/.mozilla/native-messaging-hosts/brotab_mediator.json'),
        ('mediator/chromium_mediator.json',
         '~/.config/chromium/NativeMessagingHosts/brotab_mediator.json'),
        ('mediator/chromium_mediator.json',
         '~/.config/google-chrome/NativeMessagingHosts/brotab_mediator.json'),
        ('mediator/chromium_mediator.json',
         '~/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts/brotab_mediator.json'),
    ]

    if args.tests:
        native_app_manifests.append(
            ('mediator/chromium_mediator_tests.json',
             '~/.config/chromium/NativeMessagingHosts/brotab_mediator.json'))
        native_app_manifests.append(
            ('mediator/chromium_mediator_tests.json',
             '~/.config/google-chrome/NativeMessagingHosts/brotab_mediator.json'))

    from pkg_resources import resource_string
    for filename, destination in native_app_manifests:
        destination = os.path.expanduser(os.path.expandvars(destination))
        template = resource_string(__name__, filename).decode('utf8')
        manifest = template.replace(r'$PWD/brotab_mediator.py', bt_mediator_path)
        brotab_logger.info('Installing template %s into %s', filename, destination)
        print('Installing mediator manifest %s' % destination)

        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, 'w') as file_:
            file_.write(manifest)

        if is_windows() and 'mozilla' in destination:
            register_native_manifest_windows_firefox(destination)
        if is_windows() and 'chrome' in destination:
            register_native_manifest_windows_chrome(destination)
        if is_windows() and 'Brave' in destination:
            register_native_manifest_windows_brave(destination)

    print('Link to Firefox extension: https://addons.mozilla.org/en-US/firefox/addon/brotab/')
    print(
        'Link to Chrome (Chromium)/Brave extension: https://chrome.google.com/webstore/detail/brotab/mhpeahbikehnfkfnmopaigggliclhmnc/')


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

    parser.add_argument('--target', dest='target_hosts', default=None,
                        help='Target hosts IP:Port')

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
    parser_activate_tab.add_argument('--focused', action='store_const', const=True, default=None,
                                     help='make browser focused after tab activation (default: False)')

    parser_active_tab = subparsers.add_parser(
        'active',
        help='''
        display active tab for each client/window in the following format:
        "<prefix>.<window_id>.<tab_id>"
        ''')
    parser_active_tab.set_defaults(func=show_active_tabs)

    parser_search_tabs = subparsers.add_parser(
        'search',
        help='''
        Search across your indexed tabs using sqlite fts5 plugin.
        ''')
    parser_search_tabs.set_defaults(func=search_tabs)
    parser_search_tabs.add_argument('--sqlite', type=str, default=in_temp_dir('tabs.sqlite'),
                                    help='sqlite DB filename')
    parser_search_tabs.add_argument('query', type=str, help='Search query')

    parser_query_tabs = subparsers.add_parser(
        'query',
        help='Filter tabs using chrome.tabs api.',
        prefix_chars='-+')
    parser_query_tabs.set_defaults(func=query_tabs)
    parser_query_tabs.add_argument('+active', action='store_const', const=True, default=None,
                                   help='tabs are active in their windows')
    parser_query_tabs.add_argument('-active', action='store_const', const=False, default=None,
                                   help='tabs are not active in their windows')
    parser_query_tabs.add_argument('+pinned', action='store_const', const=True, default=None,
                                   help='tabs are pinned')
    parser_query_tabs.add_argument('-pinned', action='store_const', const=False, default=None,
                                   help='tabs are not pinned')
    parser_query_tabs.add_argument('+audible', action='store_const', const=True, default=None,
                                   help='tabs are audible')
    parser_query_tabs.add_argument('-audible', action='store_const', const=False, default=None,
                                   help='tabs are not audible')
    parser_query_tabs.add_argument('+muted', action='store_const', const=True, default=None,
                                   help='tabs are muted')
    parser_query_tabs.add_argument('-muted', action='store_const', const=False, default=None,
                                   help='tabs not are muted')
    parser_query_tabs.add_argument('+highlighted', action='store_const', const=True, default=None,
                                   help='tabs are highlighted')
    parser_query_tabs.add_argument('-highlighted', action='store_const', const=False, default=None,
                                   help='tabs not are highlighted')
    parser_query_tabs.add_argument('+discarded', action='store_const', const=True, default=None,
                                   help='tabs are discarded i.e. unloaded from memory but still visible in the tab strip.')
    parser_query_tabs.add_argument('-discarded', action='store_const', const=False, default=None,
                                   help='tabs are not discarded i.e. unloaded from memory but still visible in the tab strip.')
    parser_query_tabs.add_argument('+autoDiscardable', action='store_const', const=True, default=None,
                                   help='tabs can be discarded automatically by the browser when resources are low.')
    parser_query_tabs.add_argument('-autoDiscardable', action='store_const', const=False, default=None,
                                   help='tabs cannot be discarded automatically by the browser when resources are low.')
    parser_query_tabs.add_argument('+currentWindow', action='store_const', const=True, default=None,
                                   help='tabs are in the current window.')
    parser_query_tabs.add_argument('-currentWindow', action='store_const', const=False, default=None,
                                   help='tabs are not in the current window.')
    parser_query_tabs.add_argument('+lastFocusedWindow', action='store_const', const=True, default=None,
                                   help='tabs are in the last focused window.')
    parser_query_tabs.add_argument('-lastFocusedWindow', action='store_const', const=False, default=None,
                                   help='tabs are not in the last focused window.')
    parser_query_tabs.add_argument('-status', type=str, choices=['loading', 'complete'],
                                   help='whether the tabs have completed loading i.e. loading or complete.')
    parser_query_tabs.add_argument('-title', type=str,
                                   help='match page titles against a pattern.')
    parser_query_tabs.add_argument('-url', type=str, action='append',
                                   help='match tabs against one or more URL patterns. Fragment identifiers are not matched. see https://developer.chrome.com/extensions/match_patterns')
    parser_query_tabs.add_argument('-windowId', type=int,
                                   help='the ID of the parent window, or windows.WINDOW_ID_CURRENT for the current window.')
    parser_query_tabs.add_argument('-windowType', type=str, choices=['normal', 'popup', 'panel', 'app', 'devtools'],
                                   help='the type of window the tabs are in.')
    parser_query_tabs.add_argument('-index', type=int,
                                   help='the position of the tabs within their windows.')
    parser_query_tabs.add_argument('-info', type=str,
                                   help='''
        the queryInfo parameter as outlined here: https://developer.chrome.com/extensions/tabs#method-query.
        all other query arguments are ignored if this argument is present.
        ''')

    parser_index_tabs = subparsers.add_parser(
        'index',
        help='''
        Index the text from browser's tabs. Text is put into sqlite fts5 table.
        ''')
    parser_index_tabs.set_defaults(func=index_tabs)
    parser_index_tabs.add_argument('tab_ids', type=str, nargs='*',
                                   help='Tab IDs to get text from')
    parser_index_tabs.add_argument('--sqlite', type=str, default=in_temp_dir('tabs.sqlite'),
                                   help='sqlite DB filename')
    parser_index_tabs.add_argument('--tsv', type=str, default=None,
                                   help='get text from tabs and index the results')
    parser_index_tabs.add_argument(
        '--delimiter-regex', type=str, default=DEFAULT_GET_TEXT_DELIMITER_REGEX,
        help='Regex that is used to match delimiters in the page text')
    parser_index_tabs.add_argument(
        '--replace-with', type=str, default=DEFAULT_GET_TEXT_REPLACE_WITH,
        help='String that is used to replaced matched delimiters')

    parser_new_tab = subparsers.add_parser(
        'new',
        help='''
        open new tab with the Google search results of the arguments that
        follow. One positional argument is required:
        <prefix>.<window_id> OR <client>. If window_id is not specified,
        URL will be opened in the active window of the specifed client
        ''')
    parser_new_tab.set_defaults(func=new_tab)
    parser_new_tab.add_argument(
        'prefix_window_id', type=str,
        help='Client prefix and (optionally) window id, e.g. b.20')
    parser_new_tab.add_argument('query', type=str, nargs='*',
                                help='Query to search for in Google')

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
        help='Client prefix and (optionally) window id, e.g. b.20')

    parser_navigate_urls = subparsers.add_parser(
        'navigate',
        help='''
        navigate to URLs. There are two ways to specify tab ids and URLs:
        1. stdin: lines with pairs of "tab_id<tab>url"
        2. arguments: bt navigate <tab_id> "<url>", e.g. bt navigate b.20.1 "https://google.com"
        stdin has the priority.
        ''')
    parser_navigate_urls.set_defaults(func=navigate_urls)
    parser_navigate_urls.add_argument('tab_id', type=str, help='Tab id e.g. b.20.130')
    parser_navigate_urls.add_argument('url', type=str, help='URL to navigate to')

    parser_update_tabs = subparsers.add_parser(
        'update',
        help='''
        Update tabs state, e.g. URL. There are two ways to specify updates:
        1. stdin, pass JSON of the form:
        [{"tab_id": "b.20.130", "properties": {"url": "http://www.google.com"}}]
        Where "properties" can be anything defined here:
        https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/tabs/update
        Example:
        echo '[{"tab_id":"a.2118.2156", "properties":{"url":"https://google.com"}}]' | bt update
        
        2. arguments, e.g.: bt update -tabId b.1.862 -url="http://www.google.com" +muted
        ''',
        prefix_chars='-+')
    parser_update_tabs.set_defaults(func=update_tabs)
    parser_update_tabs.add_argument('-tabId', type=str,
                                    help='tab id to apply updates to')
    parser_update_tabs.add_argument('-url', type=str,
                                    help='a URL to navigate the tab to. JavaScript URLs are not supported')
    parser_update_tabs.add_argument('-openerTabId', type=str,
                                    help='the ID of the tab that opened this tab. If specified, the opener tab must be in the same window as this tab')
    parser_update_tabs.add_argument('+active', action='store_const', const=True, default=None,
                                    help='make tab active')
    parser_update_tabs.add_argument('-active', action='store_const', const=False, default=None,
                                    help='does nothing')
    parser_update_tabs.add_argument('+autoDiscardable', action='store_const', const=True, default=None,
                                    help='whether the tab should be discarded automatically by the browser when resources are low')
    parser_update_tabs.add_argument('-autoDiscardable', action='store_const', const=False, default=None,
                                    help='whether the tab should be discarded automatically by the browser when resources are low')
    parser_update_tabs.add_argument('+highlighted', action='store_const', const=True, default=None,
                                    help='adds the tab to the current selection')
    parser_update_tabs.add_argument('-highlighted', action='store_const', const=False, default=None,
                                    help='removes the tab from the current selection')
    parser_update_tabs.add_argument('+muted', action='store_const', const=True, default=None,
                                    help='mute tab')
    parser_update_tabs.add_argument('-muted', action='store_const', const=False, default=None,
                                    help='unmute tab')
    parser_update_tabs.add_argument('+pinned', action='store_const', const=True, default=None,
                                    help='pin tab')
    parser_update_tabs.add_argument('-pinned', action='store_const', const=False, default=None,
                                    help='unpin tab')
    parser_update_tabs.add_argument('-info', type=str,
                                    help='''
        JSON in the following format:
        $ bt update -info '[{"tab_id": "b.20.130", "properties": {"url": "http://www.google.com"}}]'
        all other update arguments are ignored if this argument is present.
        ''')

    parser_get_words = subparsers.add_parser(
        'words',
        help='''
        show sorted unique words from all active tabs of all clients. This is
        a helper for webcomplete plugin that helps complete words from the
        browser
        ''')
    parser_get_words.set_defaults(func=get_words)
    parser_get_words.add_argument('tab_ids', type=str, nargs='*',
                                  help='Tab IDs to get words from')
    parser_get_words.add_argument(
        '--match-regex', type=str, default=DEFAULT_GET_WORDS_MATCH_REGEX,
        help='Regex that is used to match words in the page text')
    parser_get_words.add_argument(
        '--join-with', type=str, default=DEFAULT_GET_WORDS_JOIN_WITH,
        help='String that is used to join matched words')

    parser_get_text = subparsers.add_parser(
        'text',
        help='''
        show text form all tabs
        ''')
    parser_get_text.set_defaults(func=get_text)
    parser_get_text.add_argument('tab_ids', type=str, nargs='*',
                                 help='Tab IDs to get text from')
    parser_get_text.add_argument('--tsv', type=str, default=None,
                                 help='tsv file to save results to')
    parser_get_text.add_argument('--cleanup', action='store_true',
                                 default=False,
                                 help='force removal of extra whitespace')
    parser_get_text.add_argument(
        '--delimiter-regex', type=str, default=DEFAULT_GET_TEXT_DELIMITER_REGEX,
        help='Regex that is used to match delimiters in the page text')
    parser_get_text.add_argument(
        '--replace-with', type=str, default=DEFAULT_GET_TEXT_REPLACE_WITH,
        help='String that is used to replaced matched delimiters')

    parser_get_html = subparsers.add_parser(
        'html',
        help='''
        show html form all tabs
        ''')
    parser_get_html.set_defaults(func=get_html)
    parser_get_html.add_argument('tab_ids', type=str, nargs='*',
                                 help='Tab IDs to get text from')
    parser_get_html.add_argument('--tsv', type=str, default=None,
                                 help='tsv file to save results to')
    parser_get_html.add_argument('--cleanup', action='store_true',
                                 default=False,
                                 help='force removal of extra whitespace')
    parser_get_html.add_argument(
        '--delimiter-regex', type=str, default=DEFAULT_GET_HTML_DELIMITER_REGEX,
        help='Regex that is used to match delimiters in the page text')
    parser_get_html.add_argument(
        '--replace-with', type=str, default=DEFAULT_GET_HTML_REPLACE_WITH,
        help='String that is used to replaced matched delimiters')

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
    parser_install_mediator.add_argument('--tests', action='store_true',
                                         default=False,
                                         help='install testing version of '
                                              'manifest for chromium')
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
