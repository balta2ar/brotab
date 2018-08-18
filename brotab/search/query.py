
import argparse
import csv
import sqlite3
import string
import logging
from collections import namedtuple

logger = logging.getLogger('brotab')

QueryResult = namedtuple('QueryResult', 'tab_id title snippet')


def query(sqlite_filename, user_query,
          text_column_index=3,
          max_tokens=30,
          max_results=5):
    logger.info('sqlite db %s query "%s"', sqlite_filename, user_query)
    conn = sqlite3.connect(sqlite_filename)
    cursor = conn.cursor()
    query = f"""
    select rank, tab_id, title, snippet(tabs, {text_column_index}, '<b>', '</b>', '...', {max_tokens}) body
    from tabs where tabs match ? order by rank limit {max_results};
"""
    # print('query: ', query)
    results = []
    for (_rank, tab_id, title, snippet) in cursor.execute(query, (user_query,)):
        # print(row)
        # print('\t'.join([tab_id, title, snippet]))
        results.append(QueryResult(tab_id, title, snippet))

    conn.close()
    return results


def main():
    parser = argparse.ArgumentParser(description='Query text DB')
    parser.add_argument('sqlite', help='sqlite DB filename')
    parser.add_argument('query', help='sqlite query')
    args = parser.parse_args()
    print(args)

    for result in query(args.sqlite, args.query):
        print('\t'.join([result.tab_id, result.title, result.snippet]))


if __name__ == '__main__':
    main()
