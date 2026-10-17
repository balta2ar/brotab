#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

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

import json
import os
import re
import sys
import time
import argcomplete
from base64 import b64decode
from argparse import ArgumentParser, SUPPRESS
from importlib import resources
from functools import partial
from itertools import groupby
from json import loads, dumps
from string import ascii_lowercase
from typing import List
from typing import Tuple
from urllib.parse import quote_plus

from rich.json import JSON
from rich import box
from rich.table import Table
from rich.console import Console
from rich.text import Text
from rich_argparse import RichHelpFormatter

from bruvtab.api import MultipleMediatorsAPI
from bruvtab.api import SingleMediatorAPI
from bruvtab.const import DEFAULT_GET_HTML_DELIMITER_REGEX
from bruvtab.const import DEFAULT_GET_HTML_REPLACE_WITH
from bruvtab.const import DEFAULT_GET_TEXT_DELIMITER_REGEX
from bruvtab.const import DEFAULT_GET_TEXT_REPLACE_WITH
from bruvtab.const import DEFAULT_GET_WORDS_JOIN_WITH
from bruvtab.const import DEFAULT_GET_WORDS_MATCH_REGEX
from bruvtab.files import in_temp_dir
from bruvtab.inout import get_mediator_ports
from bruvtab.inout import is_port_accepting_connections
from bruvtab.inout import marshal
from bruvtab.inout import read_stdin
from bruvtab.inout import read_stdin_lines
from bruvtab.inout import stdout_buffer_write
from bruvtab.mediator.log import bruvtab_logger
from bruvtab.operations import make_update
from bruvtab.platform import is_windows
from bruvtab.platform import make_windows_path_double_sep
from bruvtab.platform import register_native_manifest_windows_brave
from bruvtab.platform import register_native_manifest_windows_chrome
from bruvtab.platform import register_native_manifest_windows_firefox
from bruvtab.search.index import index
from bruvtab.search.query import query
from bruvtab.ui import print_error
from bruvtab.ui import print_info
from bruvtab.ui import print_warning
from bruvtab.ui import stdout_console
from bruvtab.ui import stdout_supports_rich
from bruvtab.utils import get_file_size
from bruvtab.utils import split_tab_ids
from bruvtab.utils import which


RichHelpFormatter.styles.update({
    'argparse.args': 'bold cyan',
    'argparse.groups': 'bold dark_orange',
    'argparse.help': 'default',
    'argparse.metavar': 'bold cyan',
    'argparse.prog': 'bold green',
    'argparse.syntax': 'bold yellow',
})


def make_help_formatter(*args, **kwargs):
    rich_enabled = stdout_supports_rich()
    console = Console(
        color_system='standard' if rich_enabled else None,
        force_terminal=rich_enabled,
        highlight=False,
        soft_wrap=True,
    )
    return RichHelpFormatter(*args, console=console, **kwargs)


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


def _normalize_client_selector(selector):
    if selector is None:
        return None
    selector = selector.lower()
    return selector[:-1] if selector.endswith('.') else selector


def _client_matches_selector(client, selector):
    selector = _normalize_client_selector(selector)
    if selector is None:
        return True

    prefix = _normalize_client_selector(client._prefix)
    if selector == prefix:
        return True

    browser = client.browser.lower()
    if selector in ('chrome', 'chromium'):
        return 'chrome' in browser or 'chromium' in browser
    if selector == 'firefox':
        return 'firefox' in browser
    if selector == 'brave':
        return 'brave' in browser
    return selector in browser


def create_clients(target_hosts=None, client_selector=None) -> List[SingleMediatorAPI]:
    if target_hosts is None:
        ports = list(get_mediator_ports())
        hosts = ['localhost'] * len(ports)
    else:
        hosts, ports = parse_target_hosts(target_hosts)

    clients = [SingleMediatorAPI(prefix, host=host, port=port)
               for prefix, host, port in zip(ascii_lowercase, hosts, ports)
               if is_port_accepting_connections(port, host)]
    result = [client for client in clients
              if _client_matches_selector(client, client_selector)]
    bruvtab_logger.info('Created clients: %s', result)
    return result


def create_clients_from_args(args) -> List[SingleMediatorAPI]:
    return create_clients(args.target_hosts, getattr(args, 'client_selector', None))


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


def is_prefix_window_id(value):
    return re.fullmatch(r'[A-Za-z](?:\.(?:\d+)?)?', value) is not None


def parse_open_arguments(values):
    prefix_window_id = None
    urls = values
    if values and is_prefix_window_id(values[0]):
        prefix_window_id = values[0]
        urls = values[1:]

    if prefix_window_id is None:
        return None, None, urls

    prefix, window_id = parse_prefix_and_window_id(prefix_window_id)
    return prefix, window_id, urls


def filter_apis_by_tab_id(apis, tab_id):
    prefix, _window_id, _tab_id = tab_id.split('.')
    prefix += '.'
    return [api for api in apis if api._prefix == prefix]


def api_for_tab_id(apis, tab_id):
    prefix, _window_id, _tab_id = tab_id.split('.')
    prefix += '.'
    for api in apis:
        if api._prefix == prefix:
            return api
    return None


def describe_tab_target(apis, tab_id):
    api = api_for_tab_id(apis, tab_id)
    if api is None:
        return tab_id
    browser = api.browser
    return '%s (%s)' % (tab_id, browser)


def is_tab_id(value):
    return re.fullmatch(r'[A-Za-z]\.\d+\.\d+', value) is not None


def tab_id_from_line(line):
    return line.split('\t', 1)[0]


def tab_fields_from_line(line):
    parts = line.split('\t', 2)
    if len(parts) < 3:
        return None
    return parts


def tab_matches_selector(line, selector):
    parts = tab_fields_from_line(line)
    if parts is None:
        return False
    _tab_id, title, url = parts
    selector = selector.lower()
    return selector in title.lower() or selector in url.lower()


def get_query_tab_ids(api, query):
    return {tab_id_from_line(tab) for tab in api.query_tabs(query)}


def get_playing_tab_ids(api):
    return get_query_tab_ids(api, {'audible': True})


def get_muted_tab_ids(api):
    return get_query_tab_ids(api, {'muted': True})


def resolve_muted_tab_id(api):
    tabs = api.query_tabs({'muted': True})
    if not tabs:
        print_error('No muted tabs found')
        return None

    if len(tabs) > 1:
        print_error('Multiple tabs are muted; using %s' % tab_id_from_line(tabs[0]))

    return tab_id_from_line(tabs[0])


def resolve_playing_tab_id(api):
    tabs = api.query_tabs({'audible': True})
    if not tabs:
        print_error('No currently playing tabs found')
        return None

    if len(tabs) > 1:
        print_error('Multiple tabs are currently playing; using %s' % tab_id_from_line(tabs[0]))

    return tab_id_from_line(tabs[0])


def resolve_tab_selector(apis, selector):
    if is_tab_id(selector):
        return selector

    tabs = MultipleMediatorsAPI(apis).list_tabs([])
    matches = [tab for tab in tabs if tab_matches_selector(tab, selector)]
    if not matches:
        print_error('No tabs match "%s"' % selector)
        return None

    if len(matches) > 1:
        print_error('Multiple tabs match "%s"; using %s' % (selector, tab_id_from_line(matches[0])))

    return tab_id_from_line(matches[0])


def resolve_tab_selectors(apis, selectors):
    tab_ids = []
    for selector in selectors:
        tab_id = resolve_tab_selector(apis, selector)
        if tab_id is None:
            return None
        tab_ids.append(tab_id)
    return tab_ids


def get_active_tab_ids(apis):
    tab_ids = []
    for api in apis:
        tab_ids.extend(api.get_active_tabs([]))
    return tab_ids


def resolve_control_tab_ids(apis, args, default_target):
    if args.tab is not None:
        tab_id = resolve_tab_selector(apis, args.tab)
        return [] if tab_id is None else [tab_id]

    api = MultipleMediatorsAPI(apis)
    if args.playing or default_target == 'playing':
        tab_id = resolve_playing_tab_id(api)
        return [] if tab_id is None else [tab_id]

    if args.target_muted or default_target == 'muted':
        tab_id = resolve_muted_tab_id(api)
        return [] if tab_id is None else [tab_id]

    tab_ids = get_active_tab_ids(apis)
    if not tab_ids:
        print_error('No active tabs found')
    return tab_ids


def _compact_completion_token(value):
    return ''.join(char for char in value.lower() if char.isalnum())


def _completion_matches(candidate, prefix):
    if not prefix:
        return True
    candidate = candidate.lower()
    prefix = prefix.lower()
    if candidate.startswith(prefix):
        return True
    compact_prefix = _compact_completion_token(prefix)
    if not compact_prefix:
        return False
    return _compact_completion_token(candidate).startswith(compact_prefix)


def _completion_description(*parts, limit=120):
    text = ' | '.join(part.strip() for part in parts if part and part.strip())
    if len(text) <= limit:
        return text
    return text[:limit - 3] + '...'


def _list_tabs_for_completion(parsed_args):
    apis = create_clients(
        getattr(parsed_args, 'target_hosts', None),
        getattr(parsed_args, 'client_selector', None),
    )
    if not apis:
        return []
    return MultipleMediatorsAPI(apis).list_tabs([])


def _query_tabs_for_completion(parsed_args, query):
    apis = create_clients(
        getattr(parsed_args, 'target_hosts', None),
        getattr(parsed_args, 'client_selector', None),
    )
    if not apis:
        return []
    return MultipleMediatorsAPI(apis).query_tabs(query)


def _tab_completion_matches(tab_id, prefix):
    return _completion_matches(tab_id, prefix)


def _complete_tab_lines(prefix, tab_lines):
    matches = {}
    for line in tab_lines:
        parts = line.split('\t', 2)
        if len(parts) < 3:
            continue
        tab_id, title, url = parts
        if not _tab_completion_matches(tab_id, prefix):
            continue
        matches[tab_id] = _completion_description(title, url)
    return matches


def complete_tab_ids(prefix, parsed_args, **_kwargs):
    return _complete_tab_lines(prefix, _list_tabs_for_completion(parsed_args))


def complete_playing_tab_ids(prefix, parsed_args, **_kwargs):
    return _complete_tab_lines(prefix, _query_tabs_for_completion(parsed_args, {'audible': True}))


def complete_clients(prefix, parsed_args, **_kwargs):
    matches = {}
    seen_browsers = set()
    for client in create_clients(getattr(parsed_args, 'target_hosts', None), None):
        client_prefix = client._prefix[:-1]
        if _completion_matches(client_prefix, prefix) or _completion_matches(client._prefix, prefix):
            matches[client_prefix] = _completion_description(client.browser, '%s:%s' % (client._host, client._port))
        browser = client.browser.lower()
        if browser not in seen_browsers and _completion_matches(browser, prefix):
            seen_browsers.add(browser)
            matches[browser] = 'browser selector'
    for browser in ('chrome', 'chromium', 'firefox', 'brave'):
        if browser not in matches and _completion_matches(browser, prefix):
            matches[browser] = 'browser selector'
    return matches


def complete_windows(prefix, parsed_args, **_kwargs):
    windows = {}
    for line in _list_tabs_for_completion(parsed_args):
        tab_id, _title, _url = line.split('\t', 2)
        client_id, window_id, _tab_id = tab_id.split('.')
        key = '%s.%s' % (client_id, window_id)
        windows[key] = windows.get(key, 0) + 1
    return {
        window_id: '%s tab%s' % (count, '' if count == 1 else 's')
        for window_id, count in windows.items()
        if _completion_matches(window_id, prefix)
    }


def complete_client_or_window(prefix, parsed_args, **_kwargs):
    if prefix.startswith(('http://', 'https://', 'file://')):
        return {}
    completions = complete_windows(prefix, parsed_args)
    completions.update({
        key: value
        for key, value in complete_clients(prefix, parsed_args).items()
        if '.' not in key
    })
    return completions


def complete_open_args(prefix, parsed_args, **_kwargs):
    open_args = getattr(parsed_args, 'open_args', []) or []
    if open_args and is_prefix_window_id(open_args[0]):
        return {}
    return complete_client_or_window(prefix, parsed_args)


def completion_validator(candidate, current_input):
    if current_input.startswith('-'):
        return candidate.startswith(current_input)
    return _completion_matches(candidate, current_input)


def print_json(data):
    if stdout_supports_rich():
        stdout_console.print(JSON.from_data(data))
    else:
        print(json.dumps(data, indent=2))


def print_table(columns, rows, right_aligned_columns=None, no_wrap=False):
    right_aligned_columns = set() if right_aligned_columns is None else set(right_aligned_columns)
    table = Table(box=None, padding=(0, 1, 0, 0), show_header=True, show_edge=False, show_lines=False)
    styles = ["cyan", "green", "blue", "magenta", "yellow", "red"]
    for i, column in enumerate(columns):
        justify = 'right' if column in right_aligned_columns else 'left'
        table.add_column(column.upper(), justify=justify, style=styles[i % len(styles)], no_wrap=no_wrap)
    for row in rows:
        formatted_row = []
        for i, value in enumerate(row):
            if columns[i] in ('Playing', 'Muted') and isinstance(value, bool):
                formatted_row.append(Text('TRUE', style='bold green') if value else Text('false', style='dim red'))
            elif columns[i] == 'URL' and str(value).startswith(('http://', 'https://')):
                formatted_row.append(f"[link={value}]{value}[/link]")
            else:
                formatted_row.append(str(value))
        table.add_row(*formatted_row)
    stdout_console.print(table)


def move_tabs(args):
    bruvtab_logger.info('Moving tabs')
    api = MultipleMediatorsAPI(create_clients_from_args(args))
    api.move_tabs([])


def list_tabs(args):
    """
    Use this to show duplicates:
        bruvtab list | sort -k3 | uniq -f2 -D | cut -f1 | bruvtab close
    """
    bruvtab_logger.info('Listing tabs')
    api = MultipleMediatorsAPI(create_clients_from_args(args))
    tabs = api.list_tabs([])
    for selector in args.selectors:
        tabs = [tab for tab in tabs if tab_matches_selector(tab, selector)]
    rich_output = stdout_supports_rich()
    include_status = args.playing or args.muted or args.json or rich_output
    playing_ids = get_playing_tab_ids(api) if include_status else set()
    muted_ids = get_muted_tab_ids(api) if include_status else set()
    if args.playing:
        tabs = [tab for tab in tabs if tab_id_from_line(tab) in playing_ids]
    if args.muted:
        tabs = [tab for tab in tabs if tab_id_from_line(tab) in muted_ids]
    if args.json:
        tabs_json = [
            {
                "id": tab_id,
                "title": title,
                "url": url,
                "playing": tab_id in playing_ids,
                "muted": tab_id in muted_ids,
            }
            for tab_id, title, url in [tab_fields_from_line(y) for y in tabs]
        ]
        print_json(tabs_json)
    elif rich_output:
        rows = [
            [
                tab_id,
                tab_id in playing_ids,
                tab_id in muted_ids,
                title,
                url,
            ]
            for tab_id, title, url in [tab_fields_from_line(tab) for tab in tabs]
        ]
        print_table(['ID', 'Playing', 'Muted', 'Title', 'URL'], rows, no_wrap=args.no_wrap)
    else:
        message = "\n".join(tabs) + "\n"
        sys.stdout.buffer.write(message.encode("utf8"))


def close_tabs(args):
    api = MultipleMediatorsAPI(create_clients_from_args(args))

    if getattr(args, 'playing', False):
        tab_ids = list(get_playing_tab_ids(api))
        if not tab_ids:
            print_error('No currently playing tabs found')
            return 1
    elif getattr(args, 'muted', False):
        tab_ids = list(get_muted_tab_ids(api))
        if not tab_ids:
            print_error('No muted tabs found')
            return 1
    else:
        tab_ids = args.tab_ids
        if len(tab_ids) == 0:
            tab_ids = split_tab_ids(read_stdin().strip())

    bruvtab_logger.info('Closing tabs: %s', tab_ids)
    api.close_tabs(tab_ids)


def activate_tab(args):
    bruvtab_logger.info('Activating tab: %s', args.tab_id)
    apis = create_clients_from_args(args)
    api = MultipleMediatorsAPI(apis)
    if args.playing:
        tab_id = resolve_playing_tab_id(api)
        if tab_id is None:
            return 1
        args.tab_id = [tab_id]
    elif args.tab_id is None:
        print_error('Please specify a tab ID or use --playing')
        return 1
    else:
        args.tab_id = [args.tab_id]
    api.activate_tab(args.tab_id, args.focused)


def show_active_tabs(args):
    bruvtab_logger.info('Showing active tabs: %s', args)
    apis = create_clients_from_args(args)
    active_tabs = []
    for api in apis:
        tabs = api.get_active_tabs(args)
        for tab in tabs:
            active_tabs.append({"id": tab, "client": str(api)})

    if args.json:
        print_json(active_tabs)
    elif stdout_supports_rich():
        print_table(['ID', 'Client'], [[tab['id'], tab['client']] for tab in active_tabs],
                    no_wrap=args.no_wrap)
    else:
        for tab in active_tabs:
            print('%s\t%s' % (tab['id'], tab['client']))


def screenshot(args):
    bruvtab_logger.info('Getting screenshot: %s', args)
    apis = create_clients_from_args(args)
    if args.tab is not None:
        tab_id = resolve_tab_selector(apis, args.tab)
        if tab_id is None:
            return 1
        args.tab_id = tab_id
        apis = filter_apis_by_tab_id(apis, tab_id)
        if not apis:
            print_error('No client available for tab ID %s' % tab_id)
            return 1
    for api in apis:
        try:
            result = loads(api.get_screenshot(args))
        except Exception as e:
            print("Cannot get screenshot from API %s: %s" % (api, e), file=sys.stderr)
            continue
        if isinstance(result, dict) and result.get('error'):
            print("Cannot get screenshot from API %s: %s" % (api, result['error']), file=sys.stderr)
            continue
        if args.raw:
            data = result.get('data', '')
            _header, _separator, data = data.partition(',')
            sys.stdout.buffer.write(b64decode(data))
            return 0
        result['api'] = api._prefix[:1]
        result = dumps(result)
        print(result)
    if args.raw:
        return 1


def search_tabs(args):
    for result in query(args.sqlite, args.query):
        print('\t'.join([result.tab_id, result.title, result.snippet]))


def query_tabs(args):
    bruvtab_logger.info('Querying tabs: %s', args)
    d = vars(args)
    if d['info'] is not None:
        queryInfo = d['info']
    else:
        queryInfo = command_specific_args(args)
    api = MultipleMediatorsAPI(create_clients_from_args(args))
    for tab in api.query_tabs(queryInfo):
        print(tab)


def index_tabs(args):
    if args.tsv is None:
        args.tsv = in_temp_dir('tabs.tsv')
        args.cleanup = True
        bruvtab_logger.info(
            'index_tabs: retrieving tabs from browser into file %s', args.tsv)
        start = time.time()
        get_text(args)
        delta = time.time() - start
        bruvtab_logger.info('getting text took %s', delta)

    start = time.time()
    index(args.sqlite, args.tsv)
    delta = time.time() - start
    bruvtab_logger.info('sqlite create took %s, size %s',
                       delta, get_file_size(args.sqlite))


def new_tab(args):
    prefix, window_id = parse_prefix_and_window_id(args.prefix_window_id)
    search_query = ' '.join(args.query)
    bruvtab_logger.info('Opening search for "%s", prefix "%s", window_id "%s"',
                       search_query, prefix, window_id)
    url = "https://www.google.com/search?q=%s" % quote_plus(search_query)
    api = MultipleMediatorsAPI(create_clients_from_args(args))
    ids = api.open_urls([url], prefix, window_id)
    stdout_buffer_write(marshal(ids))


def open_urls(args):
    """
    curl -X POST 'http://localhost:4626/open_urls' -F 'urls=@urls.txt'
    curl -X POST 'http://localhost:4627/open_urls' -F 'urls=@urls.txt' -F 'window_id=749'

    where urls.txt contains one url per line (not JSON)
    """
    prefix, window_id, urls = parse_open_arguments(args.open_args)
    if not urls:
        urls = read_stdin_lines()
    bruvtab_logger.info('Opening URLs, prefix "%s", window_id "%s": %s',
                       prefix, window_id, urls)
    api = MultipleMediatorsAPI(create_clients_from_args(args))
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
    bruvtab_logger.info('Navigating: %s', updates)
    api = MultipleMediatorsAPI(create_clients_from_args(args))
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
            updates = command_specific_args(args)
            if 'tabId' not in updates: raise ValueError('tabId is required')
            updates = [make_update(**updates)]
    bruvtab_logger.info('Updating tabs: %s', updates)
    api = MultipleMediatorsAPI(create_clients_from_args(args))
    results = api.update_tabs(updates)
    stdout_buffer_write(marshal(results))


def split_error_results(results):
    ok_results = []
    errors = []
    for result in results:
        if result.startswith('ERROR\t'):
            parts = result.split('\t', 2)
            if len(parts) == 3:
                errors.append((parts[1], parts[2]))
            else:
                errors.append(('', result))
            continue
        ok_results.append(result)
    return ok_results, errors


def log_tab_action(action, apis, tab_ids, debug=False):
    for tab_id in tab_ids:
        print_warning('%s %s' % (action, describe_tab_target(apis, tab_id)))
    if debug:
        clients = ', '.join(str(api) for api in apis)
        print_warning('Clients: %s' % clients)


def control_media(args):
    apis = create_clients_from_args(args)
    default_target = 'playing' if args.media_action == 'pause' else 'active'
    tab_ids = resolve_control_tab_ids(apis, args, default_target)
    if not tab_ids:
        return 1

    action = 'Pausing' if args.media_action == 'pause' else 'Playing'
    log_tab_action('%s media in' % action, apis, tab_ids, args.debug)
    api = MultipleMediatorsAPI(apis)
    results = api.media_control(tab_ids, args.media_action)
    results, errors = split_error_results(results)
    if args.debug:
        for result in results:
            print_warning('Result: %s' % result)
    for tab_id, error in errors:
        if args.debug:
            print_error('%s: %s' % (tab_id, error))
        else:
            print_error('Could not %s media in %s; rerun with --debug for details' % (args.media_action, tab_id))
    if results:
        stdout_buffer_write(marshal(results))
    if errors:
        return 1


def set_tabs_muted(args):
    apis = create_clients_from_args(args)
    default_target = 'playing' if args.mute_value else 'active'
    tab_ids = resolve_control_tab_ids(apis, args, default_target)
    if not tab_ids:
        return 1

    action = 'Muting' if args.mute_value else 'Unmuting'
    log_tab_action(action, apis, tab_ids, args.debug)
    api = MultipleMediatorsAPI(apis)
    updates = [make_update(tabId=tab_id, muted=args.mute_value) for tab_id in tab_ids]
    results = api.update_tabs(updates)
    if args.debug:
        for result in results:
            print_warning('Result: %s' % result)
    stdout_buffer_write(marshal(results))


def get_words(args):
    # return tab.execute({javascript: "
    # [...new Set(document.body.innerText.match(/\w+/g))].sort().join('\n');
    # "})
    start = time.time()
    bruvtab_logger.info('Get words from tabs: %s, match_regex=%s, join_with=%s',
                       args.tab_ids, args.match_regex, args.join_with)
    apis = create_clients_from_args(args)
    tab_ids = resolve_tab_selectors(apis, args.tab_ids) if args.tab_ids else []
    if tab_ids is None:
        return 1
    api = MultipleMediatorsAPI(apis)
    words = api.get_words(tab_ids, args.match_regex, args.join_with)
    print('\n'.join(words))
    delta = time.time() - start
    # print('DELTA TOTAL', delta, file=sys.stderr)


def get_text_or_html(getter, args):
    tabs = getter(args.resolved_tab_ids, args.delimiter_regex, args.replace_with)

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
    bruvtab_logger.info('Get text from tabs')
    apis = create_clients_from_args(args)
    args.resolved_tab_ids = resolve_tab_selectors(apis, args.tab_ids) if args.tab_ids else []
    if args.resolved_tab_ids is None:
        return 1
    api = MultipleMediatorsAPI(apis)
    return get_text_or_html(api.get_text, args)


def get_html(args):
    bruvtab_logger.info('Get html from tabs')
    apis = create_clients_from_args(args)
    args.resolved_tab_ids = resolve_tab_selectors(apis, args.tab_ids) if args.tab_ids else []
    if args.resolved_tab_ids is None:
        return 1
    api = MultipleMediatorsAPI(apis)
    return get_text_or_html(api.get_html, args)


def show_duplicates(args):
    # I'm not using uniq here because it's not easy to get duplicates
    # only by a single column. awk is much easier in this regard.
    # print('bruvtab list | sort -k3 | uniq -f2 -D | cut -f1 | bruvtab close')
    title_command = "bruvtab list | sort -k2 | awk -F$'\\t' '{ if (a[$2]++ > 0) print }' | cut -f1 | bruvtab close"
    url_command = "bruvtab list | sort -k3 | awk -F$'\\t' '{ if (a[$3]++ > 0) print }' | cut -f1 | bruvtab close"

    if stdout_supports_rich():
        stdout_console.print('Close duplicates by Title:', style='bold cyan')
        stdout_console.print(title_command, style='green')
        stdout_console.print()
        stdout_console.print('Close duplicates by URL:', style='bold cyan')
        stdout_console.print(url_command, style='green')
        return

    print("Close duplicates by Title:")
    print(title_command)
    print("")
    print("Close duplicates by URL:")
    print(url_command)


def _get_window_id(tab):
    ids, _title, _url = tab.split('\t')
    client_id, window_id, tab_id = ids.split('.')
    return '%s.%s' % (client_id, window_id)


def _print_available_windows(tabs, as_json=False, no_wrap=False):
    windows = []
    for key, group in groupby(sorted(tabs), _get_window_id):
        group = list(group)
        windows.append((key, len(group)))

    if as_json:
        print_json([{"window": key, "tabs": count} for key, count in windows])
        return

    if stdout_supports_rich():
        print_table(['Window', 'Tabs'], windows, right_aligned_columns={'Tabs'},
                    no_wrap=no_wrap)
        return

    for window_id, tab_count in windows:
        print('%s\t%s' % (window_id, tab_count))


def show_windows(args):
    bruvtab_logger.info('Showing windows')
    api = MultipleMediatorsAPI(create_clients_from_args(args))
    tabs = api.list_tabs([])
    _print_available_windows(tabs, args.json, args.no_wrap)


def show_clients(args):
    bruvtab_logger.info('Showing clients')
    clients = create_clients_from_args(args)

    if args.json:
        clients_json = [
            {
                "prefix": client._prefix,
                "host": client._host,
                "port": client._port,
                "pid": client._pid,
                "browser": client._browser,
            }
            for client in clients
        ]
        print_json(clients_json)
        return

    if stdout_supports_rich():
        print_table(
            ['Prefix', 'Host', 'Port', 'PID', 'Browser'],
            [
                [client._prefix, client._host, client._port, client._pid, client._browser]
                for client in clients
            ],
            right_aligned_columns={'Port', 'PID'},
            no_wrap=args.no_wrap,
        )
        return

    for client in clients:
        print(client)


def install_mediator(args):
    bruvtab_logger.info('Installing mediators')
    mediator_path = which('bruvtab_mediator')
    if is_windows():
        mediator_path = make_windows_path_double_sep(mediator_path)

    native_app_manifests = [
        ('mediator/firefox_mediator.json',
         '~/.mozilla/native-messaging-hosts/bruvtab_mediator.json'),
        ('mediator/chromium_mediator.json',
         '~/.config/chromium/NativeMessagingHosts/bruvtab_mediator.json'),
        ('mediator/chromium_mediator.json',
         '~/.config/google-chrome/NativeMessagingHosts/bruvtab_mediator.json'),
        ('mediator/chromium_mediator.json',
         '~/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts/bruvtab_mediator.json'),
    ]

    # Filter by requested browser; default is chrome to avoid touching Firefox
    # on systems where its path may be read-only (e.g., NixOS managed setups).
    browser_token = None
    if getattr(args, 'browser', None) and args.browser != 'all':
        browser_map = {
            'firefox': 'mozilla',
            'chromium': 'chromium',
            'chrome': 'google-chrome',
            'brave': 'Brave-Browser',
        }
        browser_token = browser_map.get(args.browser)
        native_app_manifests = [
            (src, dst) for (src, dst) in native_app_manifests if browser_token in dst
        ]

    if args.tests:
        tests_targets = [
            ('mediator/chromium_mediator_tests.json',
             '~/.config/chromium/NativeMessagingHosts/bruvtab_mediator.json'),
            ('mediator/chromium_mediator_tests.json',
             '~/.config/google-chrome/NativeMessagingHosts/bruvtab_mediator.json'),
        ]
        if browser_token:
            tests_targets = [(s, d) for (s, d) in tests_targets if browser_token in d]
        native_app_manifests.extend(tests_targets)

    for filename, destination in native_app_manifests:
        destination = os.path.expanduser(os.path.expandvars(destination))
        template = resources.files('bruvtab').joinpath(filename).read_text(encoding='utf8')
        manifest = template.replace(r'$PWD/bruvtab_mediator.py', mediator_path)
        bruvtab_logger.info('Installing template %s into %s', filename, destination)
        print_info('Installing mediator manifest %s' % destination)

        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, 'w') as file_:
            file_.write(manifest)

        if is_windows() and 'mozilla' in destination:
            register_native_manifest_windows_firefox(destination)
        if is_windows() and 'chrome' in destination:
            register_native_manifest_windows_chrome(destination)
        if is_windows() and 'Brave' in destination:
            register_native_manifest_windows_brave(destination)

    print_info('Firefox extension is bundled in the BruvTab package output.')
    print_info('Chrome extension is bundled in the BruvTab package output.')


def executejs(args):
    pass


def no_command(parser, args):
    print_error('No command has been specified')
    parser.print_help()
    return 1


def normalize_global_args(args):
    install_args = 'install' in args
    global_args = []
    remaining_args = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in ('--json', '-j'):
            global_args.append('--json')
            index += 1
            continue
        if arg == '--debug':
            global_args.append(arg)
            index += 1
            continue
        if arg == '--target':
            if index + 1 >= len(args):
                remaining_args.append(arg)
                index += 1
                continue
            global_args.extend([arg, args[index + 1]])
            index += 2
            continue
        if arg.startswith('--target='):
            global_args.append(arg)
            index += 1
            continue
        if arg in ('--client', '--browser') and not install_args:
            if index + 1 >= len(args):
                remaining_args.append(arg)
                index += 1
                continue
            global_args.extend(['--client', args[index + 1]])
            index += 2
            continue
        if (arg.startswith('--client=') or arg.startswith('--browser=')) and not install_args:
            _name, value = arg.split('=', 1)
            global_args.append('--client=%s' % value)
            index += 1
            continue
        if arg in ('--firefox', '--chrome', '--chromium', '--brave'):
            global_args.extend(['--client', arg[2:]])
            index += 1
            continue
        remaining_args.append(arg)
        index += 1
    return global_args + remaining_args


def add_global_arguments(parser, default=None):
    parser.add_argument('--target', dest='target_hosts', default=default,
                        help='Target hosts IP:Port')
    parser_client = parser.add_argument('--client', '--browser', dest='client_selector', default=default,
                                        help='Target client prefix or browser name')
    parser.add_argument('--firefox', dest='client_selector', action='store_const', const='firefox',
                        default=default, help='Target Firefox clients')
    parser.add_argument('--chrome', dest='client_selector', action='store_const', const='chrome',
                        default=default, help='Target Chrome clients')
    parser.add_argument('--chromium', dest='client_selector', action='store_const', const='chromium',
                        default=default, help='Target Chromium clients')
    parser.add_argument('--brave', dest='client_selector', action='store_const', const='brave',
                        default=default, help='Target Brave clients')
    parser.add_argument('-j', '--json', action='store_true', default=False if default is None else default,
                        help='Pretty JSON output (colored on terminals)')
    parser.add_argument('--debug', action='store_true', default=False if default is None else default,
                        help='Print debug details for command failures')
    parser.add_argument('--no-wrap', action='store_true', default=False if default is None else default,
                        help='Disable wrapping of table columns')
    return parser_client


def command_specific_args(args):
    """Return the non-None arguments of args that belong to the subcommand itself."""
    parser = ArgumentParser(add_help=False)
    add_global_arguments(parser)
    excluded = {'func', 'info', 'command'} | set(vars(parser.parse_args([])))
    return {k: v for k, v in vars(args).items() if v is not None and k not in excluded}


def build_parser():
    parser = ArgumentParser(
        formatter_class=make_help_formatter,
        description='bruvtab (bruvtab = Browser Tabs) is a command-line tool that helps you manage '
                    'browser tabs. It can help you list, close, reorder, open and activate '
                    'your tabs.')

    parser_client = add_global_arguments(parser)

    subparsers = parser.add_subparsers(dest='command')
    parser.set_defaults(func=partial(no_command, parser))

    parser_move_tabs = subparsers.add_parser(
        'move',
        help='Move tabs around. This command lists available tabs and runs '
             'the editor. In the editor you can 1) reorder tabs -- tabs will '
             'be moved in the browser 2) delete tabs -- tabs will be closed '
             '3) change window ID of the tabs -- tabs will be moved to '
             'specified windows')
    parser_move_tabs.set_defaults(func=move_tabs)

    parser_list_tabs = subparsers.add_parser(
        'list',
        aliases=['tabs'],
        help='List available tabs. The command will request all available clients '
             '(browser plugins, mediators), and will display browser tabs in the '
             'following format: '
             '"<prefix>.<window_id>.<tab_id><Tab>Page title<Tab>URL"')
    parser_list_tabs.set_defaults(func=list_tabs)
    parser_list_tabs.add_argument('selectors', type=str, nargs='*',
                                  help='Optional title or URL fragments to match')
    parser_list_tabs.add_argument('--playing', action='store_true', default=False,
                                  help='Only list tabs that are currently audible')
    parser_list_tabs.add_argument('--muted', action='store_true', default=False,
                                  help='Only list tabs that are muted')

    parser_close_tabs = subparsers.add_parser(
        'close',
        help='Close specified tab IDs. Tab IDs should be in the following format: '
             '"<prefix>.<window_id>.<tab_id>". You can use "list" command to obtain '
             'tab IDs (first column)')
    parser_close_tabs.set_defaults(func=close_tabs)
    parser_close_tabs_ids = parser_close_tabs.add_argument('tab_ids', type=str, nargs='*',
                                                           help='Tab IDs to close')
    parser_close_tabs.add_argument('--playing', action='store_true', default=False,
                                   help='Close all currently audible tabs')
    parser_close_tabs.add_argument('--muted', action='store_true', default=False,
                                   help='Close all muted tabs')

    parser_activate_tab = subparsers.add_parser(
        'activate',
        help='Activate given tab ID. Tab ID should be in the following format: '
             '"<prefix>.<window_id>.<tab_id>"')
    parser_activate_tab.set_defaults(func=activate_tab)
    parser_activate_tab_id = parser_activate_tab.add_argument('tab_id', type=str, nargs='?',
                                                              help='Tab ID to activate')
    parser_activate_tab.add_argument('--focused', action='store_const', const=True, default=None,
                                     help='make browser focused after tab activation (default: False)')
    parser_activate_tab.add_argument('--playing', action='store_true', default=False,
                                     help='Activate the first currently audible tab')

    parser_active_tab = subparsers.add_parser(
        'active',
        help='Display active tab for each client/window in the following format: '
             '"<prefix>.<window_id>.<tab_id>"')
    parser_active_tab.set_defaults(func=show_active_tabs)

    def add_media_target_arguments(command_parser):
        tab_arg = command_parser.add_argument('tab', type=str, nargs='?',
                                              help='Optional tab ID, title, or URL fragment to target')
        command_parser.add_argument('--playing', action='store_true', default=False,
                                    help='Target the first currently audible tab')
        command_parser.add_argument('--muted', dest='target_muted', action='store_true', default=False,
                                    help='Target the first muted tab')
        return tab_arg

    parser_play = subparsers.add_parser(
        'play',
        help='Play audio/video elements in a tab. Defaults to active tabs.')
    parser_play.set_defaults(func=control_media, media_action='play')
    parser_play_tab = add_media_target_arguments(parser_play)

    parser_pause = subparsers.add_parser(
        'pause',
        help='Pause audio/video elements in a tab. Defaults to the first currently audible tab.')
    parser_pause.set_defaults(func=control_media, media_action='pause')
    parser_pause_tab = add_media_target_arguments(parser_pause)

    parser_mute = subparsers.add_parser(
        'mute',
        help='Mute a browser tab. Defaults to the first currently audible tab.')
    parser_mute.set_defaults(func=set_tabs_muted, mute_value=True)
    parser_mute_tab = add_media_target_arguments(parser_mute)

    parser_unmute = subparsers.add_parser(
        'unmute',
        help='Unmute a browser tab. Defaults to active tabs.')
    parser_unmute.set_defaults(func=set_tabs_muted, mute_value=False)
    parser_unmute_tab = add_media_target_arguments(parser_unmute)

    parser_screenshot = subparsers.add_parser(
        'screenshot',
        help="Return base64 screenshot in json object with keys: 'data' (base64 png), "
             "'tab' (tab id of visible tab), 'window' (window id of visible tab), "
             "'api' (prefix of client api). Optionally target a specific tab ID.")
    parser_screenshot.set_defaults(func=screenshot)
    parser_screenshot_tab = parser_screenshot.add_argument('tab', type=str, nargs='?',
                                                           help='Optional tab ID, title, or URL fragment to capture')
    parser_screenshot.add_argument('--raw', action='store_true', default=False,
                                   help='Output raw image bytes to stdout')
    parser_screenshot.add_argument('--wait', type=float, default=0,
                                   help='Wait time in seconds before taking the screenshot')

    parser_search_tabs = subparsers.add_parser(
        'search',
        help='Search across your indexed tabs using sqlite fts5 plugin.')
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
    parser_query_tabs.add_argument('+windowFocused', action='store_const', const=True, default=None,
                                   help='tabs are in the focused window.')
    parser_query_tabs.add_argument('-windowFocused', action='store_const', const=False, default=None,
                                   help='tabs are not in the focused window.')
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
                                   help='the queryInfo parameter as outlined here: https://developer.chrome.com/extensions/tabs#method-query. '
                                        'All other query arguments are ignored if this argument is present.')

    parser_index_tabs = subparsers.add_parser(
        'index',
        help="Index the text from browser's tabs. Text is put into sqlite fts5 table.")
    parser_index_tabs.set_defaults(func=index_tabs)
    parser_index_tabs_ids = parser_index_tabs.add_argument('tab_ids', type=str, nargs='*',
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
        help='Open new tab with the Google search results of the arguments that follow. '
             'One positional argument is required: <prefix>.<window_id> OR <client>. '
             'If window_id is not specified, URL will be opened in the active window of the specifed client')
    parser_new_tab.set_defaults(func=new_tab)
    parser_new_tab_target = parser_new_tab.add_argument(
        'prefix_window_id', type=str,
        help='Client prefix and (optionally) window id, e.g. b.20')
    parser_new_tab.add_argument('query', type=str, nargs='*',
                                help='Query to search for in Google')

    parser_open_urls = subparsers.add_parser(
        'open',
        help='Open URLs from arguments or stdin (one URL per line). The optional '
             'first argument is <prefix>.<window_id> OR <client>. If window_id is '
             'not specified, URLs will be opened in the active window of the '
             'specified client. If no client is specified, the first ready client is '
             'used. If window_id is 0, URLs will be opened in new window.')
    parser_open_urls.set_defaults(func=open_urls)
    parser_open_urls_args = parser_open_urls.add_argument('open_args', type=str, nargs='*',
                                                          help='Optional client/window followed by URLs')

    parser_navigate_urls = subparsers.add_parser(
        'navigate',
        help='Navigate to URLs. There are two ways to specify tab ids and URLs: '
             '1. stdin: lines with pairs of "tab_id<tab>url" '
             '2. arguments: bruvtab navigate <tab_id> "<url>", e.g. bruvtab navigate b.20.1 "https://google.com". '
             'Stdin has the priority.')
    parser_navigate_urls.set_defaults(func=navigate_urls)
    parser_navigate_urls_tab = parser_navigate_urls.add_argument('tab_id', type=str, help='Tab id e.g. b.20.130')
    parser_navigate_urls.add_argument('url', type=str, help='URL to navigate to')

    parser_update_tabs = subparsers.add_parser(
        'update',
        help='Update tabs state, e.g. URL. There are two ways to specify updates: '
             '1. stdin, pass JSON of the form: '
             '[{"tab_id": "b.20.130", "properties": {"url": "http://www.google.com"}}] '
             'Where "properties" can be anything defined here: '
             'https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/tabs/update. '
             '2. arguments, e.g.: bruvtab update -tabId b.1.862 -url="http://www.google.com" +muted',
        prefix_chars='-+')
    parser_update_tabs.set_defaults(func=update_tabs)
    parser_update_tabs_tab = parser_update_tabs.add_argument('-tabId', type=str,
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
                                    help='JSON in the following format: '
                                         'bruvtab update -info \'[{"tab_id": "b.20.130", "properties": {"url": "http://www.google.com"}}]\'. '
                                         'All other update arguments are ignored if this argument is present.')

    parser_get_words = subparsers.add_parser(
        'words',
        help='Show sorted unique words from all active tabs of all clients or from '
             'specified tabs. This is a helper for webcomplete plugin that helps complete '
             'words from the browser')
    parser_get_words.set_defaults(func=get_words)
    parser_get_words_ids = parser_get_words.add_argument('tab_ids', type=str, nargs='*',
                                                         help='Tab IDs to get words from')
    parser_get_words.add_argument(
        '--match-regex', type=str, default=DEFAULT_GET_WORDS_MATCH_REGEX,
        help='Regex that is used to match words in the page text')
    parser_get_words.add_argument(
        '--join-with', type=str, default=DEFAULT_GET_WORDS_JOIN_WITH,
        help='String that is used to join matched words')

    parser_get_text = subparsers.add_parser(
        'text',
        help='Show text from all tabs or from specified tabs')
    parser_get_text.set_defaults(func=get_text)
    parser_get_text_ids = parser_get_text.add_argument('tab_ids', type=str, nargs='*',
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
        help='Show html from all tabs or from specified tabs')
    parser_get_html.set_defaults(func=get_html)
    parser_get_html_ids = parser_get_html.add_argument('tab_ids', type=str, nargs='*',
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
        help='Display reminder on how to show duplicate tabs using command-line tools')
    parser_show_duplicates.set_defaults(func=show_duplicates)

    parser_show_windows = subparsers.add_parser(
        'windows',
        help='Display available prefixes and window IDs, along with the number of tabs in every window')
    parser_show_windows.set_defaults(func=show_windows)

    parser_show_clients = subparsers.add_parser(
        'clients',
        help='Display available browser clients (mediators), their prefixes and address (host:port), '
             'native app PIDs, and browser names')
    parser_show_clients.set_defaults(func=show_clients)

    parser_install_mediator = subparsers.add_parser(
        'install',
        help='Configure browser settings to use bruvtab mediator (native messaging app)')
    parser_install_mediator.add_argument(
        '--browser', choices=['all', 'chrome', 'chromium', 'firefox', 'brave'],
        default='chrome',
        help='Install mediator only for the specified browser (default: chrome)'
    )
    parser_install_mediator.add_argument('--tests', action='store_true',
                                         default=False,
                                         help='install testing version of '
                                              'manifest for chromium')
    parser_install_mediator.set_defaults(func=install_mediator)

    subparser_clients = []
    seen_subparsers = set()
    for subparser_name, subparser in subparsers.choices.items():
        if subparser_name == 'install' or id(subparser) in seen_subparsers:
            continue
        seen_subparsers.add(id(subparser))
        subparser_clients.append(add_global_arguments(subparser, default=SUPPRESS))

    for client_action in [parser_client] + subparser_clients:
        client_action.completer = complete_clients
    parser_close_tabs_ids.completer = complete_tab_ids
    parser_activate_tab_id.completer = complete_tab_ids
    parser_play_tab.completer = complete_tab_ids
    parser_pause_tab.completer = complete_playing_tab_ids
    parser_mute_tab.completer = complete_playing_tab_ids
    parser_unmute_tab.completer = complete_tab_ids
    parser_screenshot_tab.completer = complete_tab_ids
    parser_index_tabs_ids.completer = complete_tab_ids
    parser_new_tab_target.completer = complete_client_or_window
    parser_open_urls_args.completer = complete_open_args
    parser_navigate_urls_tab.completer = complete_tab_ids
    parser_update_tabs_tab.completer = complete_tab_ids
    parser_get_words_ids.completer = complete_tab_ids
    parser_get_text_ids.completer = complete_tab_ids
    parser_get_html_ids.completer = complete_tab_ids

    return parser


def parse_args(args):
    parser = build_parser()
    argcomplete.autocomplete(parser, validator=completion_validator)
    args = normalize_global_args(args)
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
