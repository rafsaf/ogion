import logging
import queue
import time
from datetime import datetime, timedelta
from threading import Thread

from pg_dump import core, jobs
from pg_dump.config import settings

log = logging.getLogger(__name__)


class PgDumpThread(Thread):
    def __init__(self) -> None:
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
        log.info("PgDumpThread start")
        while self.running():
            try:
                self.job = core.PG_DUMP_QUEUE.get(block=False)
            except queue.Empty:
                time.sleep(1)
                continue

            self.job.foldername = self.job.get_current_foldername()
            log.info(
                "PgDumpThread processing foldername '%s' started at %s, try %s",
                self.job.foldername,
                self.job.start,
                f"{self.job.retries + 1}/{settings.PG_DUMP_COOLING_PERIOD_RETRIES}",
            )
            if self.job.retries >= settings.PG_DUMP_COOLING_PERIOD_RETRIES:
                log.warning(
                    "PgDumpThread job started at %s has exceeded max number of retries",
                    self.job.start,
                )
                continue
            path = core.backup_folder_path(self.job.foldername)
            try:
                core.run_pg_dump(self.job.foldername)
                if path.exists() and not path.stat().st_size:
                    log.error("PgDumpThread error %s: backup folder empty")
                    raise core.CoreSubprocessError()
            except core.CoreSubprocessError as err:
                log.error(
                    "PgDumpThread error performing run_pg_dump: %s", err, exc_info=True
                )
                if path.exists():
                    core.backup_folder_path(self.job.foldername).unlink()
                    log.error(
                        "PgDumpThread removed empty backup folder: %s",
                        self.job.foldername,
                    )
                self.cooling_period()
                self.job.retries += 1
                log.error(
                    "PgDumpThread add job back to PG_DUMP_QUEUE after error, job foldername: %s",
                    self.job.foldername,
                )
                core.PG_DUMP_QUEUE.put(self.job)
        log.info("PgDumpThread has stopped")

    def cooling_period(self):
        self.cooling = True
        release_time = datetime.utcnow() + timedelta(
            seconds=settings.PG_DUMP_COOLING_PERIOD_SECS
        )
        log.info(
            "PgDumpThread starting cooling period, release time is: %s",
            release_time,
        )
        while self.running():
            now = datetime.utcnow()
            if now > release_time:
                self.cooling = False
                log.info("PgDumpThread finished cooling period")
                return
            time.sleep(1)
        log.info("PgDumpThread skipping cooling period")

    def stop(self):
        log.info("Stopping PgDumpThread")
        self._running = False
