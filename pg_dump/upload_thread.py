import logging
import queue
import time
from threading import Thread

from pg_dump import core

log = logging.getLogger(__name__)


class UploadThread(Thread):
    def __init__(self) -> None:
        self._running = False
        Thread.__init__(self, target=self.action)

    def running(self):
        return self._running

    def start(self) -> None:
        self._running = True
        return super().start()

    def action(self):
        log.info("UploadThread start")
        while self.running():
            try:
                job = core.UPLOADER_QUEUE.get(block=False)
            except queue.Empty:
                time.sleep(1)
                continue
            job.run(running=self.running)
        log.info("UploadThread has stopped")

    def stop(self):
        log.info("UploadThread stopping")
        self._running = False
