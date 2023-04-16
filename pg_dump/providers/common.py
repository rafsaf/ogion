import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import final

log = logging.getLogger(__name__)


class Provider(ABC):
    NAME = "provider"

    @final
    def safe_post_save(self, backup_file: Path) -> bool:
        try:
            return self.post_save(backup_file=backup_file)
        except Exception as err:
            log.error(err, exc_info=True)
            return False

    @final
    def safe_clean(self, success: bool) -> None:
        try:
            return self.clean(success=success)
        except Exception as err:
            log.error(err, exc_info=True)

    @abstractmethod
    def post_save(self, backup_file: Path) -> bool:
        return

    @abstractmethod
    def clean(self, success: bool) -> None:
        return
