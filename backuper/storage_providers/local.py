import logging
import os
from pathlib import Path

from backuper import config
from backuper.storage_providers import base_provider

log = logging.getLogger(__name__)


class LocalFiles(base_provider.BaseBackupProvider):
    """Represent local folder `data` for storing backups.

    If docker volume/persistant volume is lost, so are backups.
    """

    NAME = config.BackupProviderEnum.LOCAL_FILES

    def _post_save(self, backup_file: Path):
        return True

    def _clean(self, backup_file: Path):
        files: list[str] = []
        for backup_path in backup_file.parent.iterdir():
            files.append(str(backup_path.absolute()))
        files.sort(reverse=True)
        while len(files) > config.BACKUP_MAX_NUMBER:
            backup_to_remove = files.pop()
            try:
                os.unlink(backup_to_remove)
                log.info("removed file %s", backup_to_remove)
            except Exception as e:
                log.error(
                    "could not remove file %s: %s", backup_to_remove, e, exc_info=True
                )
