import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import final

from backuper import config

log = logging.getLogger(__name__)


class BaseUploadProvider(ABC):
    NAME: config.UploadProviderEnum

    def __init_subclass__(cls, name: config.UploadProviderEnum) -> None:
        cls.NAME = name
        super().__init_subclass__()

    @final
    def post_save(self, backup_file: Path) -> str:
        try:
            return self._post_save(backup_file=backup_file)
        except Exception as err:
            log.error(err, exc_info=True)
            raise

    @final
    def clean(self, backup_file: Path, max_backups: int) -> None:
        try:
            return self._clean(backup_file=backup_file, max_backups=max_backups)
        except Exception as err:
            log.error(err, exc_info=True)
            raise

    @abstractmethod
    def _post_save(self, backup_file: Path) -> str:  # pragma: no cover
        pass

    @abstractmethod
    def _clean(self, backup_file: Path, max_backups: int) -> None:  # pragma: no cover
        pass
