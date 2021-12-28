import os
import signal
import time
from multiprocessing import Process
from threading import Thread
from typing import Callable

from psutil import pid_exists

from brotab.mediator.log import disable_logging
from brotab.mediator.log import mediator_logger


class NotStarted(Exception):
    pass


class Runner:
    def __init__(self, serve, shutdown: Callable[[], None]):
        self._serve = serve
        self._shutdown = shutdown

    def shutdown(self) -> None:
        # TODO: break this to test ctrl-c
        if not self._shutdown:
            raise NotStarted('start the runner first')
        mediator_logger.info('Runner: calling terminate (pid=%s): %s', os.getpid(), self._shutdown)
        self._shutdown()

    def here(self) -> None:
        mediator_logger.info('Started mediator process, pid=%s', os.getpid())
        disable_logging()
        return self._serve()

    def in_thread(self) -> Thread:
        thread = Thread(target=self.here)
        thread.daemon = True
        thread.start()
        return thread

    def in_process(self) -> Process:
        process = Process(target=self.here)
        process.daemon = True
        process.start()

        def shutdown():
            mediator_logger.info('Runner: shutdown in in_process, process.terminate')
            process.terminate()

        self._shutdown = shutdown
        self._watcher(os.getpid(), os.getppid(), interval=1.0)
        return process

    def parent_watcher(self):
        self._watcher(os.getpid(), os.getppid(), interval=1.0)

    def _watcher(self, target_pid, parent_pid: int, interval: float) -> Process:
        def watch():
            mediator_logger.info('Watching parent process pid=%s', parent_pid)
            while True:
                time.sleep(interval)
                if not pid_exists(parent_pid):
                    mediator_logger.info('Parent process died pid=%s, shutting down mediator', parent_pid)
                    self.shutdown()
                    mediator_logger.info('Sending SIGTERM & SIGKILL to pid=%s', target_pid)
                    os.killpg(target_pid, signal.SIGTERM)
                    os.killpg(target_pid, signal.SIGKILL)
                    break

        process = Process(target=watch)
        process.daemon = True
        process.start()
        return process
