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

from pg_dump.cleanup_thread import CleanupThread
from pg_dump.config import settings
from pg_dump.jobs import PgDumpJob, UploaderJob
from pg_dump.pg_dump_thread import PgDumpThread
from pg_dump.scheduler_thread import SchedulerThread
from pg_dump.upload_thread import UploadThread

log = logging.getLogger(__name__)


class PgDumpDaemon:
    """pg_dump service"""

    def __init__(self) -> None:
        log.info("PgDumpDaemon start initialize...")
        log.info("PgDumpDaemon start checks")
        # pgpass file
        core.recreate_pgpass_file()
        # check postgres connection
        core.get_postgres_version()
        # check gpg settings or skip
        core.recreate_gpg_public_key()

        self.upload_thread = None
        if settings.PD_UPLOAD_PROVIDER == "google":
            required = {
                "PD_GPG_PUBLIC_KEY_BASE64": settings.PD_GPG_PUBLIC_KEY_BASE64,
                "GPG_PUBLIC_KEY_BASE64_PATH": settings.GPG_PUBLIC_KEY_BASE64_PATH,
                "PD_UPLOAD_GOOGLE_BUCKET_NAME": settings.PD_UPLOAD_GOOGLE_BUCKET_NAME,
                "PD_UPLOAD_GOOGLE_BUCKET_DESTINATION_PATH": settings.PD_UPLOAD_GOOGLE_BUCKET_DESTINATION_PATH,
                "PD_UPLOAD_GOOGLE_SERVICE_ACCOUNT_BASE64": settings.PD_UPLOAD_GOOGLE_SERVICE_ACCOUNT_BASE64,
            }
            if not all(required.values()):
                log.error(
                    "PD_UPLOAD_PROVIDER defined but no environemnt variables %s",
                    [env for env in required if not required[env]],
                )
                exit(1)
            self.upload_thread = UploadThread()
            # create google service account file
            core.setup_google_auth_account()
            # test upload of empty file to bucket to be sure it works
            UploaderJob.test_upload()
        log.info("PgDumpDaemon finished checks")
        self.cleanup_thread = CleanupThread()
        self.scheduler_thread = SchedulerThread()
        self.pg_dump_threads: list[PgDumpThread] = []
        for _ in range(settings.PD_NUMBER_PD_THREADS):
            self.pg_dump_threads.append(PgDumpThread())

        signal.signal(signalnum=signal.SIGINT, handler=self.exit)
        signal.signal(signalnum=signal.SIGTERM, handler=self.exit)
        log.info("PgDumpDaemon initialization finished")

    def run(self):
        self.initialize_pg_dump_queue_from_picle()
        self.scheduler_thread.start()
        self.cleanup_thread.start()
        for thread in self.pg_dump_threads:
            thread.start()
        if self.upload_thread:
            self.upload_thread.start()

    def initialize_pg_dump_queue_from_picle(self):
        if settings.PD_PICKLE_PD_QUEUE_NAME.is_file():
            with open(settings.PD_PICKLE_PD_QUEUE_NAME, "rb") as file:
                queue_elements: list[PgDumpJob] = pickle.loads(file.read())
                for item in queue_elements:
                    core.PD_QUEUE.put(item, block=False)
                log.info(
                    "initialize_pg_dump_queue_from_picle found %s elements in queue",
                    len(queue_elements),
                )
        else:
            log.info(
                "initialize_pg_dump_queue_from_picle no picke queue file, skipping"
            )

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
        if self.upload_thread:
            self.upload_thread.stop()
        for thread in self.pg_dump_threads:
            thread.stop()
        self.cleanup_thread.join()
        if self.upload_thread:
            self.upload_thread.join()
        for thread in self.pg_dump_threads:
            thread.join()
        with open(settings.PD_PICKLE_PD_QUEUE_NAME, "wb") as file:
            pickle.dump(list(core.PD_QUEUE.queue), file)
        log.info("exit saved pickled pg_dump_queue to file")
        log.info("exit PgDumpDaemon exits gracefully")


if __name__ == "__main__":
    pg_dump_daemon = PgDumpDaemon()
    pg_dump_daemon.run()
    pg_dump_daemon.scheduler_thread.join()
    pg_dump_daemon.cleanup_thread.join()
    for thread in pg_dump_daemon.pg_dump_threads:
        thread.join()
