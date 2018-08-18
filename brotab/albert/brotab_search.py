# -*- coding: utf-8 -*-

"""The extension searches your indexed browser tabs' contents."""

import time

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
QUERY_DELAY = 0.4


def handleQuery(query):
    if not query.isTriggered:
        return None

    user_query = query.string.strip()
    if not user_query:
        return None

    time.sleep(QUERY_DELAY)
    if not query.isValid:
        return None

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
        SQL_DB_FILENAME, user_query, max_tokens=20, max_results=10, marker_cut='')
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
