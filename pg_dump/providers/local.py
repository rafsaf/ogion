import logging
import os

from pg_dump import config
from pg_dump.providers import common

log = logging.getLogger(__name__)


class LocalFiles(common.Provider):
    """Represent local folder `data` for storing backups.

    If docker volume/persistant volume is lost, so are backups.
    """

    @staticmethod
    def post_save(backup_file: str):
        return True

    @staticmethod
    def clean(success: bool):
        files: list[str] = []
        for backup_path in config.BACKUP_FOLDER_PATH.iterdir():
            files.append(str(backup_path.absolute()))
        files.sort(reverse=True)
        while len(files) > config.BACKUP_MAX_NUMBER:
            backup_to_remove = files.pop()
            try:
                os.unlink(backup_to_remove)
            except Exception as e:
                log.error(
                    "Could not remove file %s: %s", backup_to_remove, e, exc_info=True
                )
