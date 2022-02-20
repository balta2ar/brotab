import os
import sqlite3

import psutil


def assert_file_absent(filename):
    if os.path.isfile(filename):
        os.remove(filename)
    assert not os.path.isfile(filename)


def assert_file_not_empty(filename):
    assert os.path.isfile(filename)
    assert os.path.getsize(filename) > 0


def assert_file_contents(filename, expected_contents):
    with open(filename) as file_:
        actual_contents = file_.read()
        assert expected_contents == actual_contents, \
            '"%s" != "%s"' % (expected_contents, actual_contents)


def assert_sqlite3_table_contents(db_filename, table_name, expected_contents):
    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()
    cursor.execute('select * from %s' % (table_name,))
    actual_contents = '\n'.join(['\t'.join(line) for line in cursor.fetchall()])
    assert expected_contents == actual_contents, \
        '"%s" != "%s"' % (expected_contents, actual_contents)


def kill_by_substring(substring):
    mypid = os.getpid()
    for proc in psutil.process_iter():
        line = ' '.join(proc.cmdline())
        if substring in line and proc.pid != mypid:
            print('>', proc.name(), line)
            proc.kill()


class TimeoutException(Exception):
    pass
