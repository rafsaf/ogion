import logging
import pathlib
import secrets
import shutil
import threading
import time
from datetime import datetime, timedelta
from typing import Callable

from google.cloud import storage

from pg_dump import core
from pg_dump.config import settings

log = logging.getLogger(__name__)


class JobCoolingError(Exception):
    pass


class BaseJob:
    __NAME__ = "BaseJob"
    __MAX_RUN__ = 1
    __COOLING_SECS__ = 60

    def __init__(self) -> None:
        """Base interface for any job runned in threads"""
        self.created_at: datetime = datetime.utcnow()
        self.run_number: int = 0
        log.info(
            "%s created job at %s",
            self.__NAME__,
            self.created_at,
        )

    def action(self):
        raise NotImplementedError()

    def run_numbers_left(self):
        return self.run_number < self.__MAX_RUN__

    def cooling(self, running: Callable[[], bool]):
        log.warning(
            "%s start cooling period %s secs", self.__NAME__, self.__COOLING_SECS__
        )
        release_time: datetime = datetime.utcnow() + timedelta(
            seconds=self.__COOLING_SECS__
        )
        while running() and datetime.utcnow() < release_time:
            time.sleep(1)
        log.info("%s finished cooling period", self.__NAME__)

    def run(self, running: Callable[[], bool]):
        while running() and self.run_numbers_left():
            self.run_number += 1
            log.info(
                "%s start job created at %s, try %s/%s",
                self.__NAME__,
                self.created_at,
                self.run_number,
                self.__MAX_RUN__,
            )
            try:
                self.action()
            except JobCoolingError:
                if self.run_numbers_left():
                    log.warning("%s failed", self.__NAME__)
                    self.cooling(running=running)
                else:
                    break
            else:
                log.info("%s success", self.__NAME__)
                return True
        log.error("%s failed", self.__NAME__)
        return False


class PgDumpJob(BaseJob):
    __NAME__ = "PgDumpJob"
    __MAX_RUN__ = settings.PG_DUMP_COOLING_PERIOD_RETRIES + 1
    __COOLING_SECS__ = settings.PG_DUMP_COOLING_PERIOD_SECS
    _backups_number_lock = threading.Lock()

    def action(self):
        foldername = core.get_new_backup_foldername()
        log.info("%s start action processing foldername: %s", self.__NAME__, foldername)
        path = core.backup_folder_path(foldername)
        try:
            out_folder = core.run_pg_dump(foldername)
            if path.exists() and not path.stat().st_size:
                log.error("%s error: backup folder empty", self.__NAME__)
                raise core.CoreSubprocessError()
        except core.CoreSubprocessError as err:
            log.error(
                "%s error performing pg_dump: %s", self.__NAME__, err, exc_info=True
            )
            if path.exists():
                shutil.rmtree(path)
                log.error(
                    "%s removed empty backup folder: %s",
                    self.__NAME__,
                    foldername,
                )
            raise JobCoolingError()
        else:
            if settings.PG_DUMP_UPLOAD_PROVIDER:
                core.gpg_encrypt_folder_for_upload_and_delete_it(out_folder)
                return
            with self._backups_number_lock:
                backups = []
                for folder in settings.PG_DUMP_BACKUP_FOLDER_PATH.iterdir():
                    backups.append(folder)

                if len(backups) > settings.PG_DUMP_MAX_NUMBER_BACKUPS_LOCAL:
                    backups.sort(key=lambda path: path.name, reverse=True)
                    for to_delete in backups[
                        settings.PG_DUMP_MAX_NUMBER_BACKUPS_LOCAL :
                    ]:
                        core.CLEANUP_QUEUE.put(DeleteFolderJob(foldername=to_delete))


class DeleteFolderJob(BaseJob):
    __NAME__ = "DeleteFolderJob"
    __MAX_RUN__ = 1
    __COOLING_SECS__ = 0

    def __init__(self, foldername: pathlib.Path) -> None:
        super().__init__()
        self.foldername = foldername

    def action(self):
        log.info(
            "%s start action deleting foldername: %s", self.__NAME__, self.foldername
        )
        if not self.foldername.exists():
            log.info(
                "%s foldername already deleted: %s", self.__NAME__, self.foldername
            )
            return
        try:
            shutil.rmtree(self.foldername)
        except Exception as err:
            log.error(
                "%s cannot delete foldername %s: %s",
                self.__NAME__,
                self.foldername,
                err,
                exc_info=True,
            )
            raise JobCoolingError()
        else:
            log.info("%s deleted foldername %s", self.__NAME__, self.foldername)


class UploaderJob(BaseJob):
    __NAME__ = "UploaderJob"
    __MAX_RUN__ = 3
    __COOLING_SECS__ = 120

    def __init__(self, foldername: pathlib.Path) -> None:
        super().__init__()
        self.foldername = foldername

    def action(self):
        if settings.PG_DUMP_UPLOAD_PROVIDER == "google":
            base_dest = "{}/{}".format(
                settings.PG_DUMP_UPLOAD_GOOGLE_BUCKET_DESTINATION_PATH,
                self.foldername.name,
            )
            try:
                storage_client = storage.Client()
                bucket = storage_client.bucket(
                    settings.PG_DUMP_UPLOAD_GOOGLE_BUCKET_NAME
                )
                for file in self.foldername.iterdir():
                    dest = f"{base_dest}/{file.name}"
                    log.info(dest)
                    blob = bucket.blob(dest)
                    blob.upload_from_filename(str(file.absolute()))
                    log.info("Uploaded %s to %s", file, dest)
            except Exception as err:
                log.error("Error during google bucket update: %s", err, exc_info=True)
                raise JobCoolingError()

    @staticmethod
    def test_upload():
        if settings.PG_DUMP_UPLOAD_PROVIDER == "google":
            test_filename = f"test_gcp_pg_dump_{secrets.token_urlsafe(4)}"
            test_file = pathlib.Path(f"/tmp/{test_filename}").absolute()
            test_file.touch(exist_ok=True)
            log.info("Test GCP upload created file %s", test_file)
            dest = "{}/{}".format(
                settings.PG_DUMP_UPLOAD_GOOGLE_BUCKET_DESTINATION_PATH,
                test_filename,
            )
            try:
                storage_client = storage.Client()
                bucket = storage_client.bucket(
                    settings.PG_DUMP_UPLOAD_GOOGLE_BUCKET_NAME
                )
                blob = bucket.blob(dest)
                blob.upload_from_filename(str(test_file))
                log.info("Test GCP file uploaded %s to %s", test_file, dest)
                blob.delete()
                test_file.unlink()
                log.info("Test GCP file deleted %s", dest)
            except Exception as err:
                log.error("Error during google bucket upload: %s", err, exc_info=True)
                log.error(
                    "Test upload failed. Check your bucket env variables and permissions"
                )
                exit(1)
