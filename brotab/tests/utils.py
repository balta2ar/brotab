import os
import socket
import errno

import psutil


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
                    # return False
                else:
                    s.settimeout(next_timeout)

            s.connect((server, port))

        except socket.timeout as err:
            # this exception occurs only if timeout is set
            if timeout:
                raise TimeoutError('Timed out: %s' % timeout)
                # return False

        except socket.error as err:
            # catch timeout exception from underlying network library
            # this one is different from socket.timeout
            if type(err.args) != tuple:  # or err[0] != errno.ETIMEDOUT:
                raise
        else:
            s.close()
            return
            # return True
