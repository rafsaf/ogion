import logging
import queue
import time
from threading import Thread

from pg_dump import core

log = logging.getLogger(__name__)


class PgDumpThread(Thread):
    def __init__(self) -> None:
        self._running = False
        Thread.__init__(self, target=self.action)

    def running(self):
        return self._running

    def start(self) -> None:
        self._running = True
        return super().start()

    def action(self):
        log.info("PgDumpThread start")
        while self.running():
            try:
                job = core.PD_QUEUE.get(block=False)
            except queue.Empty:
                time.sleep(1)
                continue

            success = job.run(running=self.running)
            if success or not job.run_numbers_left():
                continue
            else:
                try:
                    core.PD_QUEUE.put(job, block=False)
                except queue.Full:
                    log.warning(
                        "PgDumpThread cannot add job back to PD_QUEUE, already full, skipping"
                    )
        log.info("PgDumpThread has stopped")

    def stop(self):
        log.info("PgDumpThread stopping")
        self._running = False
