# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar, final

from croniter import croniter

from ogion.models.backup_target_models import TargetModel

log = logging.getLogger(__name__)

TM = TypeVar("TM", bound=TargetModel)


class BaseBackupTarget(ABC):
    def __init__(self, target_model: TargetModel) -> None:
        self.target_model = target_model
        self.last_backup_time: datetime = datetime.now(UTC)
        self.next_backup_time: datetime = self._get_next_backup_time()
        log.info(
            "first calculated backup of target `%s` will be: %s",
            self.target_model.env_name,
            self.next_backup_time,
        )

    @property
    def cron_rule(self) -> str:
        return self.target_model.cron_rule

    @property
    def env_name(self) -> str:
        return self.target_model.env_name

    @property
    def max_backups(self) -> int:
        return self.target_model.max_backups

    @property
    def min_retention_days(self) -> int:
        return self.target_model.min_retention_days

    @final
    def make_backup(self) -> Path:
        try:
            return self._backup()
        except Exception as err:
            log.error(err, exc_info=True)
            raise

    @final
    def _get_next_backup_time(self) -> datetime:
        now = datetime.now(UTC)
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
