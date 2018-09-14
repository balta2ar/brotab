# -*- coding: utf-8 -*-

"""The extension searches your indexed browser tabs' contents."""

import os
import time
import subprocess

from albertv0 import *

from brotab.search.query import query as brotab_query

__iid__ = "PythonInterface/v0.1"
__prettyname__ = "BroTab Search"
__version__ = "1.0"
__trigger__ = "s "
__author__ = "Yuri Bochkarev"
__dependencies__ = []

iconPath = iconLookup("preferences-system-network")

SQL_DB_FILENAME = '/tmp/tabs.sqlite'
SQL_DB_TTL_SECONDS = 5 * 60
QUERY_DELAY = 0.3


def refresh_index():
    info('Brotab: refreshing index')
    subprocess.Popen(['bt', 'index'])


def need_refresh_index():
    if not os.path.isfile(SQL_DB_FILENAME):
        return True

    mtime = os.stat(SQL_DB_FILENAME).st_mtime
    return time.time() - mtime > SQL_DB_TTL_SECONDS


def handleQuery(query):
    # it's not our query
    if not query.isTriggered:
        return None

    # query is empty
    user_query = query.string.strip()
    if not user_query:
        return None

    # slight delay to avoid too many pointless lookups
    time.sleep(QUERY_DELAY)
    if not query.isValid:
        return None

    if need_refresh_index():
        refresh_index()

    items = []

    tokens = user_query.split()
    if tokens and tokens[0] == 'index':
        items.append(Item(
            id=__prettyname__,
            text='Reindex browser tabs',
            subtext='> bt index',
            actions=[
                ProcAction('Activate', ['bt', 'index'])
            ]
        ))

    info('query %s' % user_query)
    query_results = brotab_query(
        SQL_DB_FILENAME, user_query, max_tokens=20, max_results=100, marker_cut='')
    info('brotab search: %s results' % len(query_results))
    for query_result in query_results:
        items.append(Item(
            id=__prettyname__,
            # icon=iconPath,
            text=query_result.snippet,
            subtext=query_result.title,
            actions=[
                ProcAction('Activate', ['bt', 'activate', query_result.tab_id])
            ]
        ))

    return items
