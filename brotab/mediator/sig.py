import signal
from typing import Callable

from brotab.mediator.log import logger


def pipe(shutdown: Callable, e):
    logger.info('Pipe has been closed (%s)', e)
    shutdown()


def setup(shutdown: Callable):
    def handler(signum, _frame):
        logger.info('Got signal %s', signum)
        shutdown()

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
