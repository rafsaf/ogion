import logging
import queue
import time
import traceback
from datetime import datetime, timedelta
from threading import Thread

from pg_dump import core, jobs
from pg_dump.config import settings

log = logging.getLogger(__name__)


class PgDumpThread(Thread):
    def __init__(self, number: int) -> None:
        self.number = number
        self._running = False
        self.job: jobs.PgDumpJob | None = None
        self.cooling: bool = False
        Thread.__init__(self, target=self.action)

    def running(self):
        return self._running

    def start(self) -> None:
        self._running = True
        return super().start()

    def action(self):
        log.info("Start pgdump thread %s", self.number)
        while self.running():
            try:
                self.job = core.PGDUMP_QUEUE.get(block=False)
            except queue.Empty:
                time.sleep(0.02)
                continue

            self.job.filename = self.job.get_current_filename()
            log.info(
                "Pgdump thread %s processing filename '%s' started at %s, try %s",
                self.number,
                self.job.filename,
                self.job.start,
                f"{self.job.retries + 1}/{settings.PGDUMP_COOLING_PERIOD_RETRIES}",
            )
            if self.job.retries >= settings.PGDUMP_COOLING_PERIOD_RETRIES:
                log.warning(
                    "Pgdump thread job started at %s has exceeded max number of retries"
                )
                continue
            try:
                core.run_pg_dump(self.job.filename)
                if not core.backup_folder_path(self.job.filename).stat().st_size:
                    log.error("Error pgdump thread %s: backup file empty", self.number)
                    raise core.CoreSubprocessError()
            except core.CoreSubprocessError:
                error_message = traceback.format_exc()
                log.error(error_message)
                log.error(
                    "Error pgdump thread %s: error performing pgdump", self.number
                )
                core.backup_folder_path(self.job.filename).unlink()
                log.error("Removed empty backup file %s", self.job.filename)
                self.cooling_period()
                self.job.retries += 1
                core.PGDUMP_QUEUE.put(self.job)

    def cooling_period(self):
        self.cooling = True
        release_time = datetime.utcnow() + timedelta(
            seconds=settings.PGDUMP_COOLING_PERIOD_SECS
        )
        log.info(
            "Pgdump thread %s starting cooling period, release time is: %s",
            self.number,
            release_time,
        )
        while self.running:
            now = datetime.utcnow()
            if now > release_time:
                log.info("Pgdump thread %s finished cooling period", self.number)
                self.cooling = False
                return
            time.sleep(0.02)

    def stop(self):
        log.info("Stopping pgdump thread %s", self.number)
        self._running = False
        self.join()
        log.info("Pgdump thread %s has stopped", self.number)
