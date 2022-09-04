import logging
import queue
import time
from datetime import datetime
from threading import Thread

from pg_dump import core, jobs
from pg_dump.config import settings

log = logging.getLogger(__name__)


class SchedulerThread(Thread):
    def __init__(self) -> None:
        self._running = False
        self.next_backup_time = core.get_next_backup_time()
        Thread.__init__(self, target=self.action)

    def running(self):
        return self._running

    def start(self) -> None:
        self._running = True
        return super().start()

    def action(self):
        log.info("SchedulerThread start")
        log.info("SchedulerThread next backup time %s", self.next_backup_time)
        while self.running():
            now = datetime.utcnow()
            if now > self.next_backup_time:
                log.info(
                    "SchedulerThread start schedulig new backup, putting PgDumpJob to queue"
                )
                try:
                    core.PG_DUMP_QUEUE.put(
                        jobs.PgDumpJob(),
                        block=False,
                    )
                except queue.Full:
                    log.warning(
                        "SchedulerThread PG_DUMP_QUEUE is full, skip scheduling PgDumpJob"
                    )
                self.next_backup_time = core.get_next_backup_time()
                log.info("SchedulerThread next backup time %s.", self.next_backup_time)

            time.sleep(1)

        log.info("SchedulerThread has stopped")

    def stop(self):
        log.info("SchedulerThread stopping ")
        self._running = False
