import logging
import pathlib
import secrets
import shutil
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from queue import Queue
from typing import TYPE_CHECKING

from google.cloud import storage  # type: ignore

from pg_dump.config import settings

if TYPE_CHECKING:
    from pg_dump import core

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

    def action(self) -> None:
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
    __MAX_RUN__ = settings.PD_COOLING_PERIOD_RETRIES + 1
    __COOLING_SECS__ = settings.PD_COOLING_PERIOD_SECS

    def __init__(self, pg_dump_database: "core.PgDumpDatabase") -> None:
        super().__init__()
        self.pg_dump_database = pg_dump_database

    def action(self):
        log.info("%s start action", self.__NAME__)
        out_folder = self.pg_dump_database.get_new_backup_full_path()
        try:

            self.pg_dump_database.run_pg_dump(out=out_folder)
            if out_folder.exists() and not out_folder.stat().st_size:
                log.error(
                    "%s error: backup folder empty: %s", self.__NAME__, out_folder
                )
                raise ValueError()
        except Exception as err:
            log.error(
                "%s error performing pg_dump file %s: %s",
                self.__NAME__,
                out_folder,
                err,
                exc_info=True,
            )
            if out_folder.exists():
                shutil.rmtree(out_folder)
                log.error(
                    "%s removed empty or not valid backup folder: %s",
                    self.__NAME__,
                    out_folder,
                )
            raise JobCoolingError()


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

    def __init__(self, foldername: pathlib.Path, cleanup_queue: Queue) -> None:
        super().__init__()
        self.foldername = foldername
        self.cleanup_queue = cleanup_queue

    def action(self):
        if settings.PD_UPLOAD_PROVIDER == "google":
            base_dest = "{}/{}/{}".format(
                settings.PD_UPLOAD_GOOGLE_BUCKET_DESTINATION_PATH,
                self.foldername.parent.name,
                self.foldername.name,
            )
            storage_client = storage.Client()
            bucket = storage_client.bucket(settings.PD_UPLOAD_GOOGLE_BUCKET_NAME)
            for file in self.foldername.iterdir():
                dest = f"{base_dest}/{file.name}"
                log.debug("%s Start uploading %s to %s", self.__NAME__, file, dest)
                try:
                    blob = bucket.blob(dest)
                    blob.upload_from_filename(file)
                    log.debug("%s Uploaded %s to %s", self.__NAME__, file, dest)
                except Exception as err:
                    log.error(
                        "%s Error during google bucket uploading %s to %s: %s",
                        self.__NAME__,
                        file,
                        dest,
                        err,
                        exc_info=True,
                    )
                    raise JobCoolingError()
        self.cleanup_queue.put(DeleteFolderJob(foldername=self.foldername))

    @staticmethod
    def test_gcs_upload():
        if settings.PD_UPLOAD_PROVIDER == "google":
            test_filename = f"test_gcp_pg_dump_{secrets.token_urlsafe(4)}"
            test_file = pathlib.Path(f"/tmp/{test_filename}").absolute()
            test_file.touch(exist_ok=True)

            dest = "{}/{}".format(
                settings.PD_UPLOAD_GOOGLE_BUCKET_DESTINATION_PATH,
                test_filename,
            )
            log.info("test_gcs_upload upload dummy file to bucket at %s", dest)
            try:
                storage_client = storage.Client()
                bucket = storage_client.bucket(settings.PD_UPLOAD_GOOGLE_BUCKET_NAME)
                blob = bucket.blob(dest)
                blob.upload_from_filename(str(test_file))
                blob.delete()
                test_file.unlink()
                log.info(
                    "test_gcs_upload test GCS file deleted from bucket at %s", dest
                )
            except Exception as err:
                log.error(
                    "test_gcs_upload error during google bucket upload: %s",
                    err,
                    exc_info=True,
                )
                log.error(
                    "test_gcs_upload test upload failed. Check your bucket env variables and permissions"
                )
                exit(1)
