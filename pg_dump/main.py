import logging
import pathlib
import signal
import sys

try:
    from pg_dump import core
except ImportError:
    BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.absolute()
    sys.path.insert(0, str(BASE_DIR))

    from pg_dump import core

from pg_dump.cleanup_thread import CleanupThread
from pg_dump.config import settings
from pg_dump.pg_dump_thread import PgDumpThread
from pg_dump.scheduler_thread import SchedulerThread
from pg_dump.upload_thread import UploadThread

log = logging.getLogger(__name__)


class PgDumpDaemon:
    """pg_dump service"""

    def __init__(self) -> None:
        log.info("PgDumpDaemon start initialize...")
        pg_dump = core.PgDump()

        self.upload_thread = UploadThread()
        self.cleanup_thread = CleanupThread()
        self.scheduler_thread = SchedulerThread(pg_dump=pg_dump)
        self.pg_dump_threads: list[PgDumpThread] = []
        for _ in range(settings.PD_NUMBER_PD_THREADS):
            self.pg_dump_threads.append(PgDumpThread())

        signal.signal(signalnum=signal.SIGINT, handler=self.exit)
        signal.signal(signalnum=signal.SIGTERM, handler=self.exit)
        log.info("PgDumpDaemon initialization finished")

    def run(self):
        self.scheduler_thread.start()
        self.cleanup_thread.start()
        for thread in self.pg_dump_threads:
            thread.start()
        self.upload_thread.start()

    def healthcheck(self):
        healthy = True
        if not self.scheduler_thread.is_alive():
            log.critical("healthcheck SchedulerThread is not alive")
            healthy = False
        for thread in self.pg_dump_threads:
            if not thread.is_alive():
                log.critical("healthcheck PgDumpThread %s is not alive", thread.name)
                healthy = False
        return healthy

    def exit(self, sig, frame):
        self.scheduler_thread.stop()
        self.scheduler_thread.join()
        self.cleanup_thread.stop()
        self.upload_thread.stop()
        for thread in self.pg_dump_threads:
            thread.stop()
        self.cleanup_thread.join()
        self.upload_thread.join()
        for thread in self.pg_dump_threads:
            thread.join()
        log.info("exit PgDumpDaemon exits gracefully")


if __name__ == "__main__":
    pg_dump_daemon = PgDumpDaemon()
    pg_dump_daemon.run()
    pg_dump_daemon.scheduler_thread.join()
    pg_dump_daemon.cleanup_thread.join()
    for thread in pg_dump_daemon.pg_dump_threads:
        thread.join()
