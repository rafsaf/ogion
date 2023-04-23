import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import final

log = logging.getLogger(__name__)


class BaseBackupProvider(ABC):
    NAME = "provider"

    @final
    def safe_post_save(self, backup_file: Path) -> bool:
        try:
            return self._post_save(backup_file=backup_file)
        except Exception as err:
            log.error(err, exc_info=True)
            return False

    @final
    def safe_clean(self, backup_file: Path) -> None:
        try:
            return self._clean(backup_file=backup_file)
        except Exception as err:
            log.error(err, exc_info=True)

    @abstractmethod
    def _post_save(self, backup_file: Path) -> bool:
        return

    @abstractmethod
    def _clean(self, backup_file: Path) -> None:
        return
