import logging
import pathlib
import shutil
import time
from datetime import datetime, timedelta
from typing import Callable

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
        log.info(
            "%s created job at %s, try %s/%s",
            self.__NAME__,
            self.created_at,
            self.run_number,
            self.__MAX_RUN__,
        )
        self.created_at: datetime = datetime.utcnow()
        self.run_number: int = 0

    def action(self):
        raise NotImplementedError()

    def run_numbers_left(self):
        return self.run_number < self.__MAX_RUN__

    def cooling(self, running: Callable[[], bool]):
        log.warning(
            "%s start cooling period %s secs", self.__NAME__, self.__COOLING_SECS__
        )
        release_time = datetime.utcnow() + timedelta(seconds=self.__COOLING_SECS__)
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

    def action(self):
        foldername = core.get_new_backup_foldername()
        log.info("%s start action processing foldername: %s", self.__NAME__, foldername)
        path = core.backup_folder_path(foldername)
        try:
            core.run_pg_dump(foldername)
            if path.exists() and not path.stat().st_size:
                log.error("%s error: backup folder empty", self.__NAME__)
                raise core.CoreSubprocessError()
        except core.CoreSubprocessError as err:
            log.error(
                "%s error performing run_pg_dump: %s", self.__NAME__, err, exc_info=True
            )
            if path.exists():
                shutil.rmtree(core.backup_folder_path(foldername))
                log.error(
                    "%s removed empty backup folder: %s",
                    self.__NAME__,
                    foldername,
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

    def __init__(self, foldername: pathlib.Path) -> None:
        super().__init__()
        self.foldername = foldername

    def action(self):
        log.info(
            "%s start action deleting foldername: %s", self.__NAME__, self.foldername
        )
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
