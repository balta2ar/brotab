# -*- coding: utf-8 -*-

"""
The extension searches your indexed browser tabs' contents.

To install put into:
    ~/.local/share/albert/org.albert.extension.python/modules/brotab_search.py
"""

import os
import time
import subprocess

from albert import QueryHandler, Item, info, Action, runDetachedProcess

from brotab.search.query import query as brotab_query

__title__ = "BroTab Search"
__version__ = "0.1"
__triggers__ = "s "
__authors__ = ["Yuri Bochkarev"]
__dependencies__ = []
__exec_deps__ = ["bt"]

md_iid = "0.5"
md_version = "0.1"
md_id = "brotab"
md_name = "BroTab Search"
md_description = "Search your indexed browser tabs' contents."
md_license = "BSD-2"
md_url = "https://github.com/balta2ar/brotab"
md_maintainers = "@balta2ar"

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
    # if not query.isTriggered:
    #     return None

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
            id=__name__,
            text='Reindex browser tabs',
            subtext='> bt index',
            actions=[
                Action(
                    id='reindex',
                    text='Reindex browser tabs',
                    callable=lambda: runDetachedProcess(cmdln=['bt', 'index'], workdir='~'),
                )
            ]
        ))

    info('query %s' % user_query)
    query_results = brotab_query(
        SQL_DB_FILENAME, user_query, max_tokens=20, max_results=100, marker_cut='')
    info('brotab search: %s results' % len(query_results))
    for query_result in query_results:
        items.append(Item(
            id=__name__,
            text=query_result.snippet,
            subtext=query_result.title,
            actions=[
                Action(
                    id='activate',
                    text='Activate',
                    callable=lambda: runDetachedProcess(cmdln=['bt', 'activate', query_result.tab_id], workdir='~'),
                )
            ]
        ))

    #return items
    query.add(items)

class Plugin(QueryHandler):
    def id(self): return md_id
    def name(self): return md_name
    def description(self): return md_description
    def initialize(self): info('brotab initialize')
    def finalize(self): info('brotab finalize')
    def defaultTrigger(self): return __triggers__
    def handleQuery(self, query):
        info('brotab handleQuery')
        return handleQuery(query)
