import logging
import time
from datetime import datetime
from threading import Thread

from pg_dump import core, jobs

log = logging.getLogger(__name__)


class SchedulerThread(Thread):
    def __init__(self, pg_dump: core.PgDump) -> None:
        self._running = False
        self.pg_dump = pg_dump
        Thread.__init__(self, target=self.action)

    def running(self):
        return self._running

    def start(self) -> None:
        self._running = True
        return super().start()

    def action(self):
        log.info("SchedulerThread start")
        while self.running():
            now = datetime.utcnow()
            for db in self.pg_dump.pg_dump_databases:
                if now > db.next_backup:
                    log.info(
                        "SchedulerThread start schedulig new backup, putting PgDumpJob to queue"
                    )
                    core.PD_QUEUE.put(
                        jobs.PgDumpJob(pg_dump_database=db),
                    )
                    db.next_backup = db.get_next_backup_time()
            time.sleep(1)

        log.info("SchedulerThread has stopped")

    def stop(self):
        log.info("SchedulerThread stopping ")
        self._running = False
