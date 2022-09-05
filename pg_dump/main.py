import logging
import pathlib
import pickle
import signal
import sys

try:
    from pg_dump import core
except ImportError:
    BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.absolute()
    sys.path.insert(0, str(BASE_DIR))

    from pg_dump import core

from pg_dump.config import BASE_DIR, settings
from pg_dump.jobs import PgDumpJob
from pg_dump.pg_dump_thread import PgDumpThread
from pg_dump.scheduler_thread import SchedulerThread
from pg_dump.cleanup_thread import CleanupThread

log = logging.getLogger(__name__)


class PgDumpDaemon:
    """pg_dump service"""

    def __init__(self) -> None:
        log.info("Initialize pg_dump...")
        core.recreate_pgpass_file()
        log.info("Recreated pgpass file")
        self.check_postgres_connection()
        log.info("Recreating last saved queue")
        self.initialize_pg_dump_queue_from_picle()
        log.info("Recreating GPG public key")
        core.recreate_gpg_public_key()
        log.info("Initialization finished")
        self.upload_thread = None
        if settings.PG_DUMP_UPLOAD_GOOGLE_SERVICE_ACCOUNT_BASE64:
            core.setup_google_auth_account()

        self.cleanup_thread = CleanupThread()
        self.scheduler_thread = SchedulerThread()
        self.pg_dump_threads: list[PgDumpThread] = []
        for _ in range(settings.PG_DUMP_NUMBER_PG_DUMP_THREADS):
            self.pg_dump_threads.append(PgDumpThread())

        signal.signal(signalnum=signal.SIGINT, handler=self.exit)
        signal.signal(signalnum=signal.SIGTERM, handler=self.exit)

    def run(self):
        self.scheduler_thread.start()
        self.cleanup_thread.start()
        for thread in self.pg_dump_threads:
            thread.start()

    def initialize_pg_dump_queue_from_picle(self):
        if settings.PG_DUMP_PICKLE_PG_DUMP_QUEUE_NAME.is_file():
            with open(settings.PG_DUMP_PICKLE_PG_DUMP_QUEUE_NAME, "rb") as file:
                queue_elements: list[PgDumpJob] = pickle.loads(file.read())
                for item in queue_elements:
                    core.PG_DUMP_QUEUE.put(item, block=False)
                log.info(
                    "initialize_pg_dump_queue_from_picle found %s elements in queue",
                    len(queue_elements),
                )
        else:
            log.info(
                "initialize_pg_dump_queue_from_picle no picke queue file, skipping"
            )

    def check_postgres_connection(self):
        try:
            db_version = core.get_postgres_version()
        except core.CoreSubprocessError as err:
            log.error(err, exc_info=True)
            log.error(
                "check_postgres_connection unable to connect to database, exiting"
            )
            exit(1)
        else:
            settings.PRIV_PG_DUMP_DB_VERSION = db_version

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
        for thread in self.pg_dump_threads:
            thread.stop()
        self.cleanup_thread.join()
        for thread in self.pg_dump_threads:
            thread.join()
        with open(settings.PG_DUMP_PICKLE_PG_DUMP_QUEUE_NAME, "wb") as file:
            pickle.dump(list(core.PG_DUMP_QUEUE.queue), file)
        log.info("exit saved pickled pg_dump_queue to file")
        log.info("exit PgDumpDaemon exits gracefully")


if __name__ == "__main__":
    pg_dump_daemon = PgDumpDaemon()
    pg_dump_daemon.run()
    pg_dump_daemon.scheduler_thread.join()
    pg_dump_daemon.cleanup_thread.join()
    for thread in pg_dump_daemon.pg_dump_threads:
        thread.join()
