import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import final

from croniter import croniter

from backuper import config

log = logging.getLogger(__name__)


class BaseBackupTarget(ABC):
    NAME: config.BackupTargetEnum

    def __init__(
        self, cron_rule: str, env_name: str, max_backups: int, settings: config.Settings
    ) -> None:
        self.settings: config.Settings = settings
        self.cron_rule: str = cron_rule
        self.env_name: str = env_name
        self.max_backups: int = max_backups
        self.last_backup_time: datetime = datetime.utcnow()
        self.next_backup_time: datetime = self._get_next_backup_time()
        log.info(
            "first calculated backup of target `%s` will be: %s",
            env_name,
            self.next_backup_time,
        )

    def __init_subclass__(cls, target_model_name: config.BackupTargetEnum) -> None:
        cls.NAME = target_model_name
        super().__init_subclass__()

    @final
    def make_backup(self) -> Path:
        try:
            return self._backup()
        except Exception as err:
            log.error(err, exc_info=True)
            raise

    @final
    def _get_next_backup_time(self) -> datetime:
        now = datetime.utcnow()
        cron = croniter(
            self.cron_rule,
            start_time=now,
        )
        next_backup: datetime = cron.get_next(ret_type=datetime)
        return next_backup

    @final
    def next_backup(self) -> bool:
        backup_time = self._get_next_backup_time()
        if backup_time > self.next_backup_time:
            self.last_backup_time = self.next_backup_time
            self.next_backup_time = backup_time
            return True
        return False

    @abstractmethod
    def _backup(self) -> Path:  # pragma: no cover
        pass
