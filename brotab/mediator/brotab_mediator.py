#!/usr/bin/env python3

import logging
import logging.handlers
import os
import re
import socket

from brotab.inout import get_mediator_ports
from brotab.inout import is_port_accepting_connections
from brotab.mediator import sig
from brotab.mediator.const import DEFAULT_HTTP_IFACE
from brotab.mediator.http_server import MediatorHttpServer
from brotab.mediator.log import disable_click_echo
from brotab.mediator.log import mediator_logger
from brotab.mediator.remote_api import default_remote_api
# TODO:
# 1. Run HTTP server and accept the following commands:
#    - /list_tabs
#    - /close_tabs
#    - /move_tabs ???
#    - /open_tab
#    - /open_urls
#    - /new_tab (google search)
#    - /get_tab_text
#    - /get_active_tabs_text
#
# TODO: fix bug when the number of tabs > 1100
# TODO: read stdin continuously in a separate thraed,
#       detect if it's closed, shutdown the server, and exit.
#       make sure this threaded reader and server reader are mutually exclusive.
# TODO: all commands should be synchronous and should only terminate after
#       the action has been actually executed in the browser.
from brotab.mediator.transport import default_transport


# app = flask.Flask(__name__)


def monkeypatch_socket_bind_allow_port_reuse():
    """Allow port reuse by default"""
    socket.socket._bind = socket.socket.bind

    def my_socket_bind(self, *args, **kwargs):
        mediator_logger.info('Custom bind called: %s, %s', args, kwargs)
        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return socket.socket._bind(self, *args, **kwargs)

    socket.socket.bind = my_socket_bind


def blacklist_loggers():
    blacklist = r'.*pyppeteer.*|.*urllib.*|.*socks.*|.*requests.*|.*dotenv.*'
    for name in logging.root.manager.loggerDict:
        match = re.match(blacklist, name) is not None
        # print(name, match)
        if match:
            logger = logging.getLogger(name)
            logger.setLevel(logging.ERROR)
            logger.propagate = False


def mediator_main():
    monkeypatch_socket_bind_allow_port_reuse()
    disable_click_echo()

    port_range = list(get_mediator_ports())
    transport = default_transport()
    remote_api = default_remote_api(transport)
    host = DEFAULT_HTTP_IFACE

    for port in port_range:
        mediator_logger.info('Starting mediator on %s:%s...', host, port)
        if is_port_accepting_connections(port):
            continue
        try:
            server = MediatorHttpServer(host, port, remote_api)
            process = server.run.in_process()
            sig.setup(server.run.shutdown)
            process.join()
            mediator_logger.info('Exiting mediator pid=%s on %s:%s...', os.getpid(), host, port)
            break
        except OSError as e:
            # TODO: fixme: we won't get this if we run in a process
            mediator_logger.info('Cannot bind on port %s: %s', port, e)
        except BrokenPipeError as e:
            # TODO: probably also won't work with processes, also a race
            sig.pipe(server.run.shutdown, e)

    else:
        mediator_logger.error('No TCP ports available for bind in range %s', port_range)


def main():
    mediator_main()


if __name__ == '__main__':
    main()
