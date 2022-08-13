import logging
import queue
import time
from datetime import datetime
from threading import Thread

from pg_dump import core, jobs

log = logging.getLogger(__name__)


class SchedulerThread(Thread):
    def __init__(self, db_version: str) -> None:
        self._running = False
        self.db_version = db_version
        self.next_backup_time = core.get_next_backup_time()
        Thread.__init__(self, target=self.action)

    def running(self):
        return self._running

    def start(self) -> None:
        self._running = True
        return super().start()

    def action(self):
        log.info("Start scheduler thread")
        log.info("Next backup time %s", self.next_backup_time)
        while self.running():
            now = datetime.utcnow()
            if now > self.next_backup_time:
                log.info("Start schedulig new backup, putting pgdump job to queue")
                try:
                    core.PGDUMP_QUEUE.put(
                        jobs.PgDumpJob(start=now, db_version=self.db_version),
                        block=False,
                    )
                except queue.Full:
                    log.warning("PGDUMP_QUEUE is full, skip scheduling pgdump job")
                self.next_backup_time = core.get_next_backup_time()
                log.info("Next backup time %s.", self.next_backup_time)
            time.sleep(0.02)
        log.info("Scheduler thread has stopped")

    def stop(self):
        log.info("Stopping scheduler thread")
        self._running = False
