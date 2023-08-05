import logging
import shutil
from pathlib import Path

from backuper import config, core
from backuper.providers.base_provider import BaseBackupProvider

log = logging.getLogger(__name__)


class LocalDebugFiles(
    BaseBackupProvider,
    name=config.BackupProviderEnum.LOCAL_FILES_DEBUG,
):
    """Represent local folder `data` for storing backups.

    If docker volume/persistant volume is lost, so are backups.
    """

    def __init__(self, **kwargs: str) -> None:
        pass

    def _post_save(self, backup_file: Path) -> str:
        zip_file = core.run_create_zip_archive(backup_file=backup_file)
        return str(zip_file)

    def _clean(self, backup_file: Path) -> None:
        if backup_file.is_file():
            backup_file.unlink()
        else:
            shutil.rmtree(backup_file)
        files: list[str] = []
        for backup_path in backup_file.parent.iterdir():
            files.append(str(backup_path.absolute()))
        files.sort(reverse=True)
        while len(files) > config.BACKUP_MAX_NUMBER:
            backup_to_remove = Path(files.pop())
            try:
                if backup_to_remove.is_file():
                    backup_to_remove.unlink()
                else:
                    shutil.rmtree(backup_to_remove)
                log.info("removed path %s", backup_to_remove)
            except Exception as e:  # pragma: no cover
                log.error(
                    "could not remove path %s: %s", backup_to_remove, e, exc_info=True
                )
