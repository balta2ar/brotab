import os
import signal
import time
from multiprocessing import Process
from typing import Callable
from typing import Optional

from psutil import pid_exists

from brotab.mediator.log import disable_logging
from brotab.mediator.log import mediator_logger


class NotStarted(Exception):
    pass


class Runner:
    def __init__(self, target: Callable[[], None]):
        self.target = target
        self._shutdown: Optional[Callable] = None

    def shutdown(self) -> None:
        # TODO: break this to test ctrl-c
        if not self._shutdown:
            raise NotStarted('start the runner first')
        mediator_logger.info('Runner: calling terminate: %s', self._shutdown)
        self._shutdown()

    def _here(self) -> None:
        # global browser
        # TODO: fix this
        # reassign this variable again so that tests could mock it
        # browser = remote_api
        # TODO: does not really work, I still see logs in unittests
        # global logger
        mediator_logger.info('Started mediator process, pid=%s', os.getpid())
        disable_logging()

        def shutdown():
            pid = os.getpid()
            mediator_logger.info('Runner: shutdown in here, os.kill(%s)', pid)
            os.kill(pid, signal.SIGTERM)

        self._shutdown = shutdown
        return self.target()

    # def in_thread(self, port: int) -> Thread:
    #     thread = Thread(target=lambda: self.here(port))
    #     thread.daemon = True
    #     thread.start()
    #     return thread

    def in_process(self) -> Process:
        process = Process(target=self._here)
        process.daemon = True
        process.start()

        def shutdown():
            mediator_logger.info('Runner: shutdown in in_process, process.terminate')
            process.terminate()

        self._shutdown = shutdown
        self._watcher(os.getppid(), interval=1.0)
        return process

    def _watcher(self, parent_pid: int, interval: float) -> Process:
        def watch():
            mediator_logger.info('Watching parent process pid=%s', parent_pid)
            while True:
                time.sleep(interval)
                if not pid_exists(parent_pid):
                    mediator_logger.info('Parent process died pid=%s, shutting down mediator', parent_pid)
                    self.shutdown()
                    break

        process = Process(target=watch)
        process.daemon = True
        process.start()
        return process
