import logging
import signal
import sys
import traceback

from config import BASE_DIR, settings

try:
    from pg_dump import core
except ImportError:
    sys.path.insert(0, str(BASE_DIR))

    from pg_dump import core

from pg_dump.pgdump_thread import PgDumpThread
from pg_dump.scheduler_thread import SchedulerThread

log = logging.getLogger(__name__)


class PgDumpDaemon:
    """pg_dump service"""

    def __init__(self) -> None:
        signal.signal(signalnum=signal.SIGINT, handler=self.exit)
        signal.signal(signalnum=signal.SIGTERM, handler=self.exit)
        log.info("Initialize pg_dump...")
        core.recreate_pgpass_file()
        log.info("Recreated pgpass file")
        self.check_postgres_connection()
        log.info("Initialization finished.")

        self.scheduler_thread = SchedulerThread(db_version=self.db_version)
        self.pgdump_threads: list[PgDumpThread] = []
        for i in range(settings.PGDUMP_NUMBER_PGDUMP_THREADS):
            self.pgdump_threads.append(PgDumpThread(number=i))

    def run(self):
        self.scheduler_thread.start()
        for thread in self.pgdump_threads:
            thread.start()

    def check_postgres_connection(self):
        try:
            db_version = core.get_postgres_version()
        except core.CoreSubprocessError:
            error_message = traceback.format_exc()
            log.critical(error_message)
            log.critical("Unable to connect to database, aborted")
            exit(1)
        self.db_version = db_version

    def exit(self, sig, frame):
        self.scheduler_thread.stop()
        for thread in self.pgdump_threads:
            thread.stop()


if __name__ == "__main__":
    pg_dump_daemon = PgDumpDaemon()
    pg_dump_daemon.run()
