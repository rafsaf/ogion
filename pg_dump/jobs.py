import logging
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
                "%s start, try %s/%s", self.__NAME__, self.run_number, self.__MAX_RUN__
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

    def get_current_foldername(self):
        return core.get_new_backup_foldername(
            now=datetime.utcnow(), db_version=settings.PRIV_PG_DUMP_DB_VERSION
        )

    def action(self):
        foldername = self.get_current_foldername()
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
