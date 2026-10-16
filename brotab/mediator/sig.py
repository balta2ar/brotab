import signal
from typing import Callable

from brotab.mediator.log import mediator_logger


def setup(shutdown: Callable[[], None]) -> None:
    def handler(signum, _frame):
        mediator_logger.info('Got signal %s', signum)
        shutdown()

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
