#!/usr/bin/env python2

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
    implementing my own exsension sounds like a viable idea. Two things are
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

import sys
from telnetlib import Telnet
from json import loads
# from json import dumps
from urllib import quote_plus
from getpass import getuser
import requests

# from pprint import pprint


MAX_NUMBER_OF_TABS = 1000


def infer_delete_commands(tabs_before, tabs_after):
    commands = []
    after = set(tabs_after)
    for index in range(len(tabs_before)-1, -1, -1):
        value = tabs_before[index]
        if value not in after:
            commands.append('delete %d' % index)
    return commands

def infer_move_commands(tabs_before, tabs_after):
    pass


def infer_delete_and_move_commands(tabs_before, tabs_after):
    """
    This command takes browser tabs before the edit and after the edit and
    infers a sequence of commands that need to be executed in a browser
    to make transform state from `tabs_before` to `tabs_after`.

    Sample input:
        f.0.0	GMail
        f.0.1	Posix man
        f.0.2	news

    Sample output:
        m 0.0 5,m 0.1 1,d 0.2
    Means:
        move 0.0 to index 5,
        move 0.1 to index 1,
        delete 0.2

    Note that after moves and deletes, indices do not need to be adjusted on the
    browser side. All the indices are calculated by the client program so that
    the JS extension can simply execute the commands without thinking.
    """
    commands = infer_delete_commands(tabs_before, tabs_after)
    return commands


class ChromeAPI(object):
    BROWSER_PREFIX = 'c.'

    def __init__(self, host='localhost', port=9222):
        self._host = host
        self._port = port

    def _filter_tabs(self, tabs):
        return [tab[len(ChromeAPI.BROWSER_PREFIX):] for tab in tabs
                if tab.startswith(ChromeAPI.BROWSER_PREFIX)]

    def _list_tabs(self, num_tabs):
        response = requests.get("http://%s:%s/json" % (self._host, self._port))
        result = loads(response.text)
        result = [tab for tab in result if tab['type'] == 'page']
        return result[:num_tabs]

    def close_tabs(self, args):
        current_tabs = self._list_tabs(MAX_NUMBER_OF_TABS)
        for tab in self._filter_tabs(args):
            tab_id = current_tabs[int(tab)]['id']
            requests.get("http://%s:%s/json/close/%s" % (
                self._host, self._port, tab_id))

    def activate_tab(self, args):
        args = self._filter_tabs(args)
        if len(args) == 0:
            return

        tab = args[0]
        current_tabs = self._list_tabs(MAX_NUMBER_OF_TABS)
        tab_id = current_tabs[int(tab)]['id']
        requests.get("http://%s:%s/json/activate/%s" % (
            self._host, self._port, tab_id))

    def new_tab(self, args):
        if args[0] != ChromeAPI.BROWSER_PREFIX:
            return

        query = ' '.join(args[1:])
        url = "https://www.google.com/search?q=%s" % quote_plus(query)
        requests.get("http://%s:%s/json/new?%s" % (
            self._host, self._port, url))

    def list_tabs(self, args):
        num_tabs = MAX_NUMBER_OF_TABS
        if len(args) > 0:
            num_tabs = int(args[0])

        lines = []
        for i, tab in enumerate(self._list_tabs(num_tabs)):
            line = '%s%s\t%s\t%s\n' % (ChromeAPI.BROWSER_PREFIX, i,
                                       tab['title'], tab['url'])
            line = line.encode('utf8')
            lines.append(line)
        sys.stdout.writelines(lines)


class Mozrepl(object):
    LOAD_CODE = 'repl.load("file:///home/%s/rc.arch/bz/.config/mozrepl/mozrepl.js");' % getuser()

    def __init__(self, ip="127.0.0.1", port=4242):
        self.ip = ip
        self.port = port
        self.prompt = b"repl>"

    def __enter__(self):
        self.t = Telnet(self.ip, self.port)

        while True:
            index, match, text = self.t.expect([r'.*\n', # match greeting line
                                                r'repl\d+>'], # match repl line
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


class FirefoxAPI(object):
    BROWSER_PREFIX = 'f.'

    def _filter_tabs(self, tabs):
        return [tab[len(FirefoxAPI.BROWSER_PREFIX):] for tab in tabs
                if tab.startswith(FirefoxAPI.BROWSER_PREFIX)]

    def close_tabs(self, args):
        with Mozrepl() as mozrepl:
            tabs = ' '.join(self._filter_tabs(args))
            result = mozrepl.js('close_tabs("%s");' % tabs)
            result = loads(result)

    def activate_tab(self, args):
        args = self._filter_tabs(args)
        if len(args) == 0:
            return

        strWindowTab = args[0]
        with Mozrepl() as mozrepl:
            result = mozrepl.js('activate_tab("%s");' % strWindowTab)
            result = loads(result)

    def new_tab(self, args):
        if args[0] != FirefoxAPI.BROWSER_PREFIX:
            return 2

        query = ' '.join(args[1:])
        with Mozrepl() as mozrepl:
            result = mozrepl.js('new_tab("https://www.google.com/search?q=%s", true);' % quote_plus(query))
            result = loads(result)

    def list_tabs(self, args):
        num_tabs = MAX_NUMBER_OF_TABS
        if len(args) > 0:
            num_tabs = int(args[0])

        with Mozrepl() as mozrepl:
            result = loads(mozrepl.js('list_tabs(%d);' % num_tabs))
            lines = []
            for tab in result:
                line = '%s%s.%s\t%s\t%s\n' % (FirefoxAPI.BROWSER_PREFIX,
                                              tab['windowId'], tab['tabId'],
                                              tab['title'], tab['url'])
                line = line.encode('utf8')
                lines.append(line)
            sys.stdout.writelines(lines)


class BrowserAPI(object):
    def __init__(self, apis):
        self._apis = apis

    def close_tabs(self, args):
        if len(args) == 0:
            print('Usage: mozrepl-client.py close_tabs <#tab ...>')
            return 2

        for api in self._apis:
            api.close_tabs(args)

    def activate_tab(self, args):
        if len(args) == 0:
            print('Usage: mozrepl-client.py activate_tab <#tab>')
            return 2

        for api in self._apis:
            api.activate_tab(args)

    def new_tab(self, args):
        if len(args) <= 1:
            print('Usage: mozrepl-client.py new_tab <f.|c.> <search query>')
            return 2

        for api in self._apis:
            api.new_tab(args)

    def list_tabs(self, args):
        for api in self._apis:
            try:
                api.list_tabs(args)
            except ValueError as e:
                print >> sys.stderr, "Cannot decode JSON: %s: %s" % (api, e)

    def move_tabs(self, args):
        """
        This command allows to close tabs and move them around.

        It lists current tabs, opens an editor, and when editor is done, it
        detects which tabs where deleted and which where moved. It closes
        remove tabs, and moves the rest accordingly.
        """
        raise NotImplementedError()


def main(args):
    command = args[0]
    rest = args[1:]

    api = BrowserAPI([FirefoxAPI(), ChromeAPI()])

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


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('Usage: mozrepl-client.py <list_tabs | ...>')
        exit(1)
    exit(main(sys.argv[1:]))
