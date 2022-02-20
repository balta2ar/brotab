import os
import signal
import time
from multiprocessing import Process
from threading import Thread
from typing import Callable

# from psutil import pid_exists

from brotab.mediator.log import disable_logging
from brotab.mediator.log import mediator_logger


class NotStarted(Exception):
    pass


class Runner:
    def __init__(self, serve: Callable[[], None], shutdown: Callable[[bool], None]):
        self._serve = serve
        self._shutdown = shutdown

    def shutdown(self, join: bool) -> None:
        # TODO: break this to test ctrl-c
        if not self._shutdown:
            raise NotStarted('start the runner first')
        mediator_logger.info('Runner: calling terminate (pid=%s): %s', os.getpid(), self._shutdown)
        self._shutdown(join)

    def here(self) -> None:
        mediator_logger.info('Started mediator process, pid=%s', os.getpid())
        disable_logging()
        return self._serve()

    def in_thread(self) -> Thread:
        thread = Thread(target=self.here)
        thread.daemon = True
        thread.start()
        return thread

    # def parent_watcher(self, running: Callable, interval: float):
    #     self._watcher(running, os.getppid(), interval=interval)
    #
    # def _watcher(self, running: Callable, parent_pid: int, interval: float) -> None:
    #     mediator_logger.info('Watching parent process parent=%s current pid=%s',
    #                          parent_pid, os.getpid())
    #     while True:
    #         time.sleep(interval)
    #         if not running():  # someone shutdown mediator, let's bail
    #             break
    #         if not pid_exists(parent_pid):
    #             mediator_logger.info('Parent process died pid=%s, shutting down mediator', parent_pid)
    #             self.shutdown(join=False)
    #             break
