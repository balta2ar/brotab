import os
import socket
import errno
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


# http://code.activestate.com/recipes/576655-wait-for-network-service-to-appear/
def wait_net_service(server, port, timeout=None):
    """ Wait for network service to appear
        @param timeout: in seconds, if None or 0 wait forever
        @return: True of False, if timeout is None may return only True or
                 throw unhandled network exception
    """
    s = socket.socket()
    if timeout:
        from time import time as now
        # time module is needed to calc timeout shared between two exceptions
        end = now() + timeout

    while True:
        try:
            if timeout:
                next_timeout = end - now()
                if next_timeout < 0:
                    raise TimeoutError('Timed out: %s' % timeout)
                else:
                    s.settimeout(next_timeout)

            s.connect((server, port))

        except socket.timeout as err:
            # this exception occurs only if timeout is set
            if timeout:
                raise TimeoutError('Timed out: %s' % timeout)

        except socket.error as err:
            # catch timeout exception from underlying network library
            # this one is different from socket.timeout
            if type(err.args) != tuple:  # or err[0] != errno.ETIMEDOUT:
                raise
        else:
            s.close()
            return
