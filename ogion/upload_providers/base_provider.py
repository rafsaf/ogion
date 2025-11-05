# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
import pathlib
from abc import ABC, abstractmethod
from pathlib import Path

from ogion.models.upload_provider_models import ProviderModel

log = logging.getLogger(__name__)


class BaseUploadProvider(ABC):
    def __init__(self, target_provider: ProviderModel) -> None:  # pragma: no cover
        pass

    @abstractmethod
    def all_target_backups(self, env_name: str) -> list[str]:  # pragma: no cover
        pass

    @abstractmethod
    def download_backup(self, path: str) -> pathlib.Path:  # pragma: no cover
        pass

    @abstractmethod
    def post_save(self, backup_file: Path) -> str:  # pragma: no cover
        pass

    @abstractmethod
    def clean(
        self, backup_file: Path, max_backups: int, min_retention_days: int
    ) -> None:  # pragma: no cover
        pass

    @abstractmethod
    def close(self) -> None:  # pragma: no cover
        pass
