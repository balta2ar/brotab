"""
This module contains helpers that query the indexed database of text from a
browser.
"""

import argparse
import sqlite3
import logging
from collections import namedtuple

logger = logging.getLogger('brotab')

QueryResult = namedtuple('QueryResult', 'tab_id title snippet')


def query(sqlite_filename, user_query,
          text_column_index=3,
          max_tokens=30,
          max_results=10,
          marker_start='<b>',
          marker_end='</b>',
          marker_cut='...'):
    logger.info('Executing sqlite db %s query "%s"',
                sqlite_filename, user_query)
    conn = sqlite3.connect(sqlite_filename)
    cursor = conn.cursor()
    query = """
    select
        rank,
        tab_id,
        title,
        snippet(tabs,
                {text_column_index},
                '{marker_start}',
                '{marker_end}',
                '{marker_cut}',
                {max_tokens}) body
    from tabs where tabs match ? order by rank limit {max_results};
""".format_map(locals())
    results = []
    try:
        for (_rank, tab_id, title, snippet) in cursor.execute(query, (user_query,)):
            results.append(QueryResult(tab_id, title, snippet))
    except sqlite3.OperationalError as e:
        logger.exception('Error: %s', e)

    conn.close()
    return results


def main():
    parser = argparse.ArgumentParser(description='Query text DB')
    parser.add_argument('sqlite', help='sqlite DB filename')
    parser.add_argument('query', help='sqlite query')
    args = parser.parse_args()

    for result in query(args.sqlite, args.query):
        print('\t'.join([result.tab_id, result.title, result.snippet]))


if __name__ == '__main__':
    main()
