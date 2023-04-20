import logging
import os

from pg_dump import config
from pg_dump.storage_providers import common

log = logging.getLogger(__name__)


class LocalFiles(common.BaseBackupProvider):
    """Represent local folder `data` for storing backups.

    If docker volume/persistant volume is lost, so are backups.
    """

    NAME = config.BackupProviderEnum.LOCAL_FILES

    def post_save(self, backup_file: str):
        return True

    def clean(self, success: bool):
        files: list[str] = []
        for backup_path in config.CONST_BACKUP_FOLDER_PATH.iterdir():
            files.append(str(backup_path.absolute()))
        files.sort(reverse=True)
        while len(files) > config.BACKUP_MAX_NUMBER:
            backup_to_remove = files.pop()
            try:
                os.unlink(backup_to_remove)
                log.info("Removed file %s", backup_to_remove)
            except Exception as e:
                log.error(
                    "Could not remove file %s: %s", backup_to_remove, e, exc_info=True
                )
