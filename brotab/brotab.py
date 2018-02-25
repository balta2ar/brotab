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
from getpass import getuser
from json import loads
from telnetlib import Telnet
# from json import dumps
from urllib.parse import quote_plus
from subprocess import check_call, CalledProcessError
from tempfile import NamedTemporaryFile
from traceback import print_exc

import requests

# from pprint import pprint


MAX_NUMBER_OF_TABS = 1000


def _get_old_index(tab, tabs_before):
    for index, value in enumerate(tabs_before):
        if value == tab:
            return index

    raise ValueError('Tab %s not found' % tab)


def _get_tab_id(tab):
    index = tab.split('\t')[0]
    str_index = index.split('.')[1]
    return int(str_index)


def _get_index_by_tab_id(tab_id, tabs):
    for index, tab in enumerate(tabs):
        if tab_id == _get_tab_id(tab):
            return index

    return None


def get_longest_increasing_subsequence(X):
    """Returns the Longest Increasing Subsequence in the Given List/Array"""
    N = len(X)
    P = [0] * N
    M = [0] * (N+1)
    L = 0
    for i in range(N):
       lo = 1
       hi = L
       while lo <= hi:
           mid = (lo+hi)//2
           if (X[M[mid]] < X[i]):
               lo = mid+1
           else:
               hi = mid-1

       newL = lo
       P[i] = M[newL-1]
       M[newL] = i

       if (newL > L):
           L = newL

    S = []
    k = M[L]
    for i in range(L-1, -1, -1):
        S.append(X[k])
        k = P[k]
    return S[::-1]


def infer_delete_commands(tabs_before, tabs_after):
    commands = []
    after = set(tabs_after)
    for index in range(len(tabs_before) - 1, -1, -1):
        tab = tabs_before[index]
        if tab not in after:
            commands.append(_get_tab_id(tab))
    return commands


def infer_move_commands(tabs_before, tabs_after):
    """
    `tabs_before` and `tabs_after` contain an integer in the beginning
    but that's a tab ID, not a position. Thus, a move command means:

        move <tab_id> <to_index>

    where <to_index> is an index within a browser window. Consider this:

    Before:         After:
    f.4\ta          f.8\ta
    f.8\ta          f.4\ta
    f.1\aa          f.1\ta

    The correspoding move commands:

        move f.8 0

    """
    # Remember which tab corresponds to which index in the old list
    tab_to_old_index = {tab: index for index, tab in enumerate(tabs_before)}
    # Now see how indices have been reordered by user
    reordered_indices = [tab_to_old_index[tab] for tab in tabs_after]
    # These indices are in correct order, we should not touch them
    correctly_ordered_new_indices = set(get_longest_increasing_subsequence(
        reordered_indices))

    commands = []
    for new_index, old_index in enumerate(reordered_indices):
        if old_index not in correctly_ordered_new_indices:
            tab = tabs_before[old_index]
            tab_id = _get_tab_id(tab)
            commands.append((tab_id, new_index))
    return commands


def apply_delete_commands(tabs_before, delete_commands):
    tabs = tabs_before[:]
    for tab_id in delete_commands:
        #tab_id = int(command.split()[1])
        del tabs[_get_index_by_tab_id(tab_id, tabs)]
    return tabs


def apply_move_commands(tabs_before, move_commands):
    tabs = tabs_before[:]
    for tab_id, index_to in move_commands:
        index_from = _get_index_by_tab_id(tab_id, tabs)
        tabs.insert(index_to, tabs.pop(index_from))
    return tabs


def infer_delete_and_move_commands(tabs_before, tabs_after):
    """
    This command takes browser tabs before the edit and after the edit and
    infers a sequence of commands that need to be executed in a browser
    to make transform state from `tabs_before` to `tabs_after`.

    Sample input:
        f.0	GMail
        f.1	Posix man
        f.2	news

    Sample output:
        m 0 5,m 1 1,d 2
    Means:
        move 0 to index 5,
        move 1 to index 1,
        delete 2

    Note that after moves and deletes, indices do not need to be adjusted on the
    browser side. All the indices are calculated by the client program so that
    the JS extension can simply execute the commands without thinking.
    """
    delete_commands = infer_delete_commands(tabs_before, tabs_after)
    tabs_before = apply_delete_commands(tabs_before, delete_commands)
    move_commands = infer_move_commands(tabs_before, tabs_after)
    return delete_commands, move_commands


def save_tabs_to_file(tabs, filename):
    with open(filename, 'w') as file_:
        file_.write('\n'.join(tabs))


def load_tabs_from_file(filename):
    with open(filename) as file_:
        return [line.strip() for line in file_.readlines()]


def edit_tabs_in_editor(tabs_before):
    with NamedTemporaryFile() as file_:
        save_tabs_to_file(tabs_before, file_.name)
        try:
            check_call([os.environ.get('EDITOR', 'nvim'), file_.name])
            tabs_after = load_tabs_from_file(file_.name)
            return tabs_after
        except CalledProcessError:
            return None


class ChromeAPI(object):
    BROWSER_PREFIX = 'c.'

    def __init__(self, host='localhost', port=9222):
        self._host = host
        self._port = port

    def _get(self, path):
        return requests.get('http://%s:%s%s' % (self._host, self._port, path))

    def _filter_tabs(self, tabs):
        return [tab[len(ChromeAPI.BROWSER_PREFIX):] for tab in tabs
                if tab.startswith(ChromeAPI.BROWSER_PREFIX)]

    def _list_tabs(self, num_tabs):
        response = self._get('/json')
        result = loads(response.text)
        result = [tab for tab in result if tab['type'] == 'page']
        return result[:num_tabs]

    def close_tabs(self, args):
        current_tabs = self._list_tabs(MAX_NUMBER_OF_TABS)
        for tab in self._filter_tabs(args):
            tab_id = current_tabs[int(tab)]['id']
            self._get('/json/close/%s' % tab_id)

    def activate_tab(self, args):
        args = self._filter_tabs(args)
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
#     def _filter_tabs(self, tabs):
#         return [tab[len(FirefoxAPI.BROWSER_PREFIX):] for tab in tabs
#                 if tab.startswith(FirefoxAPI.BROWSER_PREFIX)]
#
#     def close_tabs(self, args):
#         with Mozrepl() as mozrepl:
#             tabs = ' '.join(self._filter_tabs(args))
#             result = mozrepl.js('close_tabs("%s");' % tabs)
#             result = loads(result)
#
#     def activate_tab(self, args):
#         args = self._filter_tabs(args)
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
#         args = self._filter_tabs(args)
#         if len(args) == 0:
#             return
#
#         pass


class FirefoxMediatorAPI(object):
    BROWSER_PREFIX = 'f.'

    def __init__(self, host='localhost', port=4625):
        self._host = host
        self._port = port

    def prefix_tabs(self, tabs):
        return ['%s%s' % (self.BROWSER_PREFIX, tab) for tab in tabs]

    def _filter_tabs(self, tabs):
        prefix_len = len(FirefoxMediatorAPI.BROWSER_PREFIX)
        return [tab[prefix_len:] for tab in tabs
                if tab.startswith(FirefoxMediatorAPI.BROWSER_PREFIX)]

    def close_tabs(self, args):
        tabs = ','.join(self._filter_tabs(args))
        self._get('/close_tabs/%s' % tabs)

    def activate_tab(self, args):
        args = self._filter_tabs(args)
        if len(args) == 0:
            return

        strWindowTab = args[0]
        self._get('/activate_tab/%s' % strWindowTab)

    def new_tab(self, args):
        if args[0] != FirefoxMediatorAPI.BROWSER_PREFIX:
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
            line = '%s%s' % (FirefoxMediatorAPI.BROWSER_PREFIX, line)
            print(line)
            lines.append(line)
        return lines

    def move_tabs(self, args):
        print('SENDING MOVE COMMANDS:', args)
        commands = ','.join('%s %s' % (tab_id, new_index) for tab_id, new_index in args)
        self._get('/move_tabs/%s' % commands)

    def _get(self, path):
        return requests.get('http://%s:%s%s' % (self._host, self._port, path))


class BrowserAPI(object):
    def __init__(self, apis):
        self._apis = apis

    def close_tabs(self, args):
        if len(args) == 0:
            print('Usage: brotab_client.py close_tabs <#tab ...>')
            return 2

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
        exit_code = 0
        for api in self._apis:
            try:
                api.list_tabs(args)
            except ValueError as e:
                print("Cannot decode JSON: %s: %s" % (api, e), file=sys.stderr)
                exit_code = 1
            except requests.exceptions.ConnectionError as e:
                print("Cannot access API %s: %s" % (api, e), file=sys.stderr)
                exit_code = 1
        return exit_code

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
        exit_code = 0
        for api in self._apis:
            try:
                print('MOVING START')
                tabs_before = api.list_tabs([])
                # from pprint import pprint
                # pprint(tabs_before)
                tabs_after = edit_tabs_in_editor(tabs_before)
                print('TABS AFTER', tabs_after)
                if tabs_after is not None:
                    delete_commands, move_commands = infer_delete_and_move_commands(
                        tabs_before, tabs_after)
                    print('DELETE COMMANDS', delete_commands)

                    if delete_commands:
                        api.close_tabs(api.prefix_tabs(delete_commands))
                        # raise RuntimeError('DELETE COMMANDS ARE NOT SUPPORTED YET')

                    print('MOVE COMMANDS', move_commands)
                    api.move_tabs(move_commands)
                print('MOVING END')
            except ValueError as e:
                print("Cannot decode JSON: %s: %s" % (api, e), file=sys.stderr)
                print_exc(file=sys.stderr)
                exit_code = 1
            except requests.exceptions.ConnectionError as e:
                print("Cannot access API %s: %s" % (api, e), file=sys.stderr)
                print_exc(file=sys.stderr)
                exit_code = 1
        return exit_code


def run_commands(args):
    command = args[0]
    rest = args[1:]

    #api = BrowserAPI([FirefoxMediatorAPI(), ChromeAPI()])
    api = BrowserAPI([FirefoxMediatorAPI()])

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
    else:
        print('Unknown command: %s' % command)
        return 2

    return 0


def main():
    if len(sys.argv) == 1:
        print('Usage: brotab_client.py <list_tabs | ...>')
        exit(1)
    exit(run_commands(sys.argv[1:]))


if __name__ == '__main__':
    main()
